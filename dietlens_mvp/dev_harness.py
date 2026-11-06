"""Bounded developer-agent orchestration.

The developer Harness proposes plans and patches but never writes repository files.
An external review/apply step must explicitly approve a candidate and run tests.
It is intentionally separate from the end-user DietLens Harness.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
import json
from typing import Any
from uuid import uuid4

from jsonschema import ValidationError, validate

from .errors import ToolError
from .model_provider import ModelProvider, ModelResponse


class DevState(str, Enum):
    CREATED = "created"
    PLANNED = "planned"
    IMPLEMENTING = "implementing"
    AWAITING_REVIEW = "awaiting_review"
    TESTING = "testing"
    COMPLETED = "completed"
    FAILED = "failed"
    BLOCKED = "blocked"
    CANCELLED = "cancelled"


class DevRole(str, Enum):
    PLANNER = "planner"
    IMPLEMENTER = "implementer"
    TESTER = "tester"
    REVIEWER = "reviewer"
    DOCS = "docs"


DEV_PLAN_SCHEMA = {
    "type": "object",
    "additionalProperties": False,
    "required": ["summary", "steps", "files", "risks", "test_commands"],
    "properties": {
        "summary": {"type": "string", "minLength": 1},
        "steps": {"type": "array", "minItems": 1, "items": {"type": "string"}},
        "files": {"type": "array", "items": {"type": "string"}},
        "risks": {"type": "array", "items": {"type": "string"}},
        "test_commands": {"type": "array", "items": {"type": "string"}},
    },
}


@dataclass(frozen=True)
class DevEvent:
    event_type: str
    task_id: str
    payload: dict[str, Any]
    timestamp: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())


@dataclass
class DevTask:
    task_id: str = field(default_factory=lambda: str(uuid4()))
    objective: str = ""
    role: DevRole = DevRole.PLANNER
    state: DevState = DevState.CREATED
    iteration: int = 0
    max_iterations: int = 8
    model_calls: int = 0
    max_model_calls: int = 2
    plan: dict[str, Any] | None = None
    patch_summary: str | None = None
    changed_files: list[str] = field(default_factory=list)
    test_commands: list[str] = field(default_factory=list)
    test_results: list[dict[str, Any]] = field(default_factory=list)
    memory_refs: list[str] = field(default_factory=list)
    events: list[DevEvent] = field(default_factory=list)
    failure_code: str | None = None


class DeveloperHarness:
    """Plan-and-execute graph with human review before any repository mutation."""

    def __init__(self, providers: dict[DevRole | str, ModelProvider], *, max_iterations: int = 8, max_model_calls: int = 2) -> None:
        self.providers = {role.value if isinstance(role, DevRole) else role: provider for role, provider in providers.items()}
        self.tasks: dict[str, DevTask] = {}
        self.max_iterations = max_iterations
        self.max_model_calls = max_model_calls

    def _event(self, task: DevTask, name: str, payload: dict[str, Any]) -> None:
        # Event payloads contain metadata only; raw prompts and provider responses stay out of the audit log.
        task.events.append(DevEvent(name, task.task_id, payload))

    def _transition(self, task: DevTask, state: DevState) -> None:
        allowed = {
            DevState.CREATED: {DevState.PLANNED, DevState.BLOCKED, DevState.CANCELLED},
            DevState.PLANNED: {DevState.IMPLEMENTING, DevState.CANCELLED},
            DevState.IMPLEMENTING: {DevState.AWAITING_REVIEW, DevState.BLOCKED, DevState.FAILED},
            DevState.AWAITING_REVIEW: {DevState.TESTING, DevState.IMPLEMENTING, DevState.CANCELLED},
            DevState.TESTING: {DevState.COMPLETED, DevState.FAILED, DevState.IMPLEMENTING},
            DevState.FAILED: {DevState.IMPLEMENTING, DevState.CANCELLED},
            DevState.BLOCKED: {DevState.IMPLEMENTING, DevState.CANCELLED},
            DevState.COMPLETED: set(),
            DevState.CANCELLED: set(),
        }
        if state not in allowed[task.state]:
            raise ToolError("dev_invalid_state_transition")
        previous = task.state
        task.state = state
        self._event(task, "dev.state_changed", {"from": previous.value, "to": state.value})

    def create(self, objective: str, *, role: DevRole = DevRole.PLANNER) -> DevTask:
        if not objective.strip() or len(objective) > 4000:
            raise ToolError("dev_invalid_objective")
        task = DevTask(objective=objective.strip(), role=role, max_iterations=self.max_iterations, max_model_calls=self.max_model_calls)
        self.tasks[task.task_id] = task
        self._event(task, "dev.task_created", {"role": role.value})
        return task

    def _provider(self, role: DevRole) -> ModelProvider:
        try:
            return self.providers[role.value]
        except KeyError as exc:
            raise ToolError("dev_provider_not_configured") from exc

    def _call(self, task: DevTask, role: DevRole, messages: list[dict[str, str]]) -> ModelResponse:
        if task.iteration >= task.max_iterations:
            self._transition(task, DevState.BLOCKED)
            task.failure_code = "dev_max_iterations"
            raise ToolError("dev_max_iterations")
        if task.model_calls >= task.max_model_calls:
            task.failure_code = "dev_model_budget_exhausted"
            raise ToolError("dev_model_budget_exhausted")
        task.iteration += 1
        task.model_calls += 1
        self._event(task, "dev.model_called", {"role": role.value, "iteration": task.iteration, "call": task.model_calls})
        provider = self._provider(role)
        try:
            return provider.complete(messages, [], DEV_PLAN_SCHEMA)
        except Exception as exc:
            task.failure_code = "dev_model_failed"
            self._event(task, "dev.model_failed", {"role": role.value, "error_type": type(exc).__name__})
            raise ToolError("dev_model_failed") from exc

    @staticmethod
    def _json(response: ModelResponse) -> dict[str, Any]:
        try:
            data = json.loads(response.content, parse_constant=lambda value: (_ for _ in ()).throw(ValueError(value)))
            validate(data, DEV_PLAN_SCHEMA)
            return data
        except (ValueError, TypeError, ValidationError) as exc:
            raise ToolError("dev_invalid_model_output") from exc

    def plan(self, task_id: str) -> DevTask:
        task = self.get(task_id)
        if task.state != DevState.CREATED:
            raise ToolError("dev_plan_not_allowed")
        response = self._call(task, DevRole.PLANNER, [{"role": "user", "content": task.objective}])
        task.plan = self._json(response)
        task.test_commands = list(task.plan["test_commands"])
        self._transition(task, DevState.PLANNED)
        self._event(task, "dev.plan_created", {"step_count": len(task.plan["steps"]), "file_count": len(task.plan["files"])})
        return task

    def begin_implementation(self, task_id: str) -> DevTask:
        task = self.get(task_id)
        if task.state not in {DevState.PLANNED, DevState.FAILED, DevState.BLOCKED}:
            raise ToolError("dev_implementation_not_allowed")
        self._transition(task, DevState.IMPLEMENTING)
        self._event(task, "dev.implementation_started", {"files": task.plan["files"] if task.plan else []})
        return task

    def submit_patch(self, task_id: str, *, summary: str, changed_files: list[str]) -> DevTask:
        task = self.get(task_id)
        if task.state != DevState.IMPLEMENTING or not summary.strip() or not changed_files:
            raise ToolError("dev_patch_not_allowed")
        if any(not isinstance(path, str) or path.startswith("/") or ".." in path.split("/") for path in changed_files):
            raise ToolError("dev_invalid_changed_file")
        task.patch_summary = summary.strip()
        task.changed_files = list(dict.fromkeys(changed_files))
        self._transition(task, DevState.AWAITING_REVIEW)
        self._event(task, "dev.patch_submitted", {"changed_files": task.changed_files})
        return task

    def review(self, task_id: str, *, approved: bool, note: str = "") -> DevTask:
        task = self.get(task_id)
        if task.state != DevState.AWAITING_REVIEW:
            raise ToolError("dev_review_not_allowed")
        self._event(task, "dev.reviewed", {"approved": approved, "has_note": bool(note)})
        self._transition(task, DevState.TESTING if approved else DevState.IMPLEMENTING)
        return task

    def record_tests(self, task_id: str, *, passed: bool, command: str, output_digest: str = "") -> DevTask:
        task = self.get(task_id)
        if task.state != DevState.TESTING or not command.strip():
            raise ToolError("dev_tests_not_allowed")
        task.test_results.append({"command": command, "passed": bool(passed), "output_digest": output_digest[:128]})
        if passed:
            self._transition(task, DevState.COMPLETED)
            self._event(task, "dev.completed", {"command": command})
        else:
            task.failure_code = "dev_tests_failed"
            self._transition(task, DevState.FAILED)
            self._event(task, "dev.tests_failed", {"command": command})
        return task

    def remember(self, task_id: str, memory_ref: str) -> DevTask:
        task = self.get(task_id)
        if not memory_ref.strip() or len(memory_ref) > 300:
            raise ToolError("dev_invalid_memory_ref")
        task.memory_refs.append(memory_ref.strip())
        self._event(task, "dev.memory_referenced", {"count": len(task.memory_refs)})
        return task

    def cancel(self, task_id: str) -> DevTask:
        task = self.get(task_id)
        if task.state in {DevState.COMPLETED, DevState.CANCELLED}:
            return task
        self._transition(task, DevState.CANCELLED)
        return task

    def get(self, task_id: str) -> DevTask:
        try:
            return self.tasks[task_id]
        except KeyError as exc:
            raise ToolError("dev_task_not_found") from exc
