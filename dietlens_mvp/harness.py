from __future__ import annotations

from contextlib import contextmanager
from dataclasses import asdict
import json
import logging
from typing import Any
from uuid import uuid4

from .errors import ToolError
from .model_provider import ModelProvider, StubModelProvider, INTENT_SCHEMA, fallback_intent, parse_intent
from .models import CareState, Decision, Event, Execution, Task, TaskState
from .registry import ToolRegistry, ToolSpec
from .profile_workflow import ProfileWorkflow
from .repository import Repository
from .serialization import dumps
from .store import InMemoryStore
from .tools import build_context, filter_options, generate_actions, review, save_decision, save_feedback
from .reminders import mark_reminded, reminder_status

logger = logging.getLogger(__name__)


class Harness:
    """Transactional finite-state controller. Only explicit user commands confirm writes."""

    MAX_ITERATIONS = 8
    MAX_TOOL_CALLS = 3  # per user step, not over the whole task lifetime
    MAX_MODEL_CALLS = 2

    def __init__(self, store: Repository | None = None, provider: ModelProvider | None = None) -> None:
        self.store = store if store is not None else InMemoryStore()
        self.provider = provider or StubModelProvider()
        self.registry = ToolRegistry()
        self.profiles = ProfileWorkflow(self)
        text = {"type": "string"}
        specs = [
            ("build_context", "read", {"meal": text, "options": {"type": "array", "items": text}},
             lambda meal, options: asdict(build_context(self.store, self._active_user, meal, options))),
            ("save_decision", "write", {"index": {"type": "integer", "minimum": 0}, "decision": {"enum": ["adopt", "skip"]}}, self._write_decision),
            ("save_feedback", "write", {"execution": {"enum": [e.value for e in Execution]}, "note": {"type": "string", "maxLength": 1000}}, self._write_feedback),
            ("review", "read", {}, lambda: review(self.store, self._active_user)),
            ("save_profile", "write", {}, self.profiles.write_confirmed),
        ]
        for name, access, properties, handler in specs:
            schema = {"type": "object", "properties": properties, "required": list(properties), "additionalProperties": False}
            output_properties = {
                "build_context": {"user_id": text, "meal": text,
                                  "options": {"type": "array", "items": text},
                                  "budget": {"type": ["number", "null"]},
                                  "allergies": {"type": "array", "items": text},
                                  "dislikes": {"type": "array", "items": text},
                                  "source": text, "profile_version": {"type": "integer"},
                                  "allergies_confirmed": {"type": "boolean"},
                                  "hard_avoids": {"type": "array", "items": text},
                                  "allergy_status": text},
                "save_profile": {"profile_version": {"type": "integer", "minimum": 1}},
                "save_decision": {"action_id": text},
                "save_feedback": {"action_id": text},
                "review": {"adopted": {"type": "integer", "minimum": 0},
                           "completed": {"type": "integer", "minimum": 0},
                           "feedback_coverage": {"type": ["number", "null"], "minimum": 0, "maximum": 1},
                           "revision": {"type": "string"},
                           "actions": {"type": "array", "items": {"type": "object"}}},
            }[name]
            output = {"type": "object", "properties": output_properties,
                      "required": list(output_properties), "additionalProperties": False}
            self.registry.register(ToolSpec(name, access, access == "write", schema, output), handler)

    def _event(self, task: Task, name: str, payload: dict, operation_key: str | None = None) -> None:
        self.store.append_event(Event(name, task.task_id, task.user_id, payload, operation_key))

    def _transition(self, task: Task, state: TaskState, operation_key: str | None = None) -> None:
        previous = task.state
        task.state = state
        self._event(task, "task.state_changed", {"from": previous.value, "to": state.value}, operation_key)

    def _care(self, task: Task, state: CareState, operation_key: str | None = None) -> None:
        previous = task.care_state
        if previous == state:
            return
        task.care_state = state
        self._event(task, "care.state_changed", {"from": previous.value, "to": state.value}, operation_key)

    @contextmanager
    def _operation(self, task_id: str):
        try:
            with self.store.transaction():
                yield
        except ToolError as exc:
            # Failed writes roll back completely. Budget stops are then committed separately.
            with self.store.transaction():
                task = self.store.get_task(task_id)
                if task:
                    if exc.code in {"max_iterations", "tool_budget_exhausted", "budget_exhausted"}:
                        self._transition(task, TaskState.STOPPED)
                        task.stopped_reason = exc.code
                        self.store.save_task(task)
                    self._event(task, "task.error", {"code": exc.code})
            logger.info(json.dumps({"event": "task.error", "task_id": task_id, "code": exc.code}))
            raise
        else:
            logger.info(json.dumps({"event": "task.step_committed", "task_id": task_id}))

    def _guard(self, task: Task) -> None:
        if task.iteration >= self.MAX_ITERATIONS:
            raise ToolError("max_iterations")
        task.iteration += 1
        task.tool_calls = 0
        task.model_calls = 0

    def _invoke(self, task: Task, name: str, arguments: dict, *, confirmed: bool = False) -> dict:
        if task.tool_calls >= self.MAX_TOOL_CALLS:
            raise ToolError("tool_budget_exhausted")
        self._active_user = task.user_id
        self._active_task = task
        task.tool_calls += 1
        self._event(task, "tool.called", {"name": name, "confirmed": confirmed})
        return self.registry.invoke(name, arguments, confirmed=confirmed)

    def _write_decision(self, index: int, decision: str) -> dict:
        task = self._active_task
        if task.state != TaskState.AWAITING_CONFIRMATION:
            raise ToolError("task_not_awaiting_confirmation")
        if index >= len(task.candidates):
            raise ToolError("candidate_not_found")
        profile = self.store.get_profile(task.user_id)
        if task.task_type != "micro_action" or task.context is None or profile is None or profile.version != task.context.profile_version:
            raise ToolError("profile_changed")
        if profile.allergy_status not in {"none", "specified"}:
            raise ToolError("allergies_unconfirmed")
        action = save_decision(self.store, task.candidates[index], Decision(decision), task.task_id)
        if task.context and action.selected_option is None:
            action.selected_option = task.context.options[index] if index < len(task.context.options) else None
            action = self.store.save_action(action, f"{task.task_id}:decision:selected-option:{action.action_id}")
        return {"action_id": action.action_id}

    def _write_feedback(self, execution: str, note: str = "") -> dict:
        task = self._active_task
        if task.state != TaskState.ADOPTED or not task.selected_action_id:
            raise ToolError("task_not_awaiting_feedback")
        action = save_feedback(self.store, task.selected_action_id, Execution(execution), task.task_id, note)
        return {"action_id": action.action_id}

    def _receipt(self, key: str, request: dict) -> dict | None:
        receipt = self.store.get_receipt(key)
        if receipt and receipt["request"] != request:
            raise ToolError("operation_conflict")
        return receipt

    @staticmethod
    def _version(task: Task, expected_version: int | None) -> None:
        if expected_version is not None and task.version != expected_version:
            raise ToolError("version_conflict")

    def create_task(self, user_id: str, task_type: str = "micro_action") -> Task:
        if task_type not in {"micro_action", "quick_log", "plan", "explore", "reflect"}:
            raise ToolError("unsupported_task_type")
        with self.store.transaction():
            if self.store.get_profile(user_id) is None:
                raise ToolError("profile_not_found")
            task = Task(user_id=user_id, task_type=task_type)
            self.store.save_task(task)
            self._event(task, "task.created", {"state": task.state.value})
            return task

    def quick_log_preview(self, task_id: str, record: dict[str, Any]) -> Task:
        """Store a user-editable meal-record draft without writing intake."""
        with self._operation(task_id):
            task = self._task(task_id)
            if task.task_type != "quick_log" or task.state != TaskState.CREATED:
                raise ToolError("quick_log_not_collecting")
            self._guard(task)
            self._care(task, CareState.RECORDING)
            task.pending_record = dict(record)
            self._event(task, "quick_log.previewed", {"record_id": record.get("record_id"), "meal_slot": record.get("meal_slot")})
            return self.store.save_task(task)

    def quick_log_confirmed(self, task_id: str, record: dict[str, Any], operation_key: str) -> Task:
        """Close a quick-log task after the MealRecord write has succeeded."""
        with self._operation(task_id):
            task = self._task(task_id)
            if task.task_type != "quick_log" or task.state != TaskState.CREATED:
                raise ToolError("quick_log_not_confirmable")
            if task.pending_record and task.pending_record.get("record_id") != record.get("record_id"):
                raise ToolError("operation_conflict")
            self._guard(task)
            task.pending_record = None
            task.linked_objects = {**task.linked_objects, "meal_record_id": record.get("record_id"), "meal_record": record}
            self._care(task, CareState.REFLECTING, operation_key)
            self._transition(task, TaskState.DONE, operation_key)
            self._event(task, "quick_log.confirmed", {"record_id": record.get("record_id")}, operation_key)
            self.store.save_receipt(operation_key, {"task_id": task_id, "record_id": record.get("record_id")})
            return self.store.save_task(task)

    def plan_previewed(self, task_id: str, plan_id: str) -> Task:
        with self._operation(task_id):
            task = self._task(task_id)
            if task.task_type != "plan" or task.state != TaskState.CREATED:
                raise ToolError("plan_task_not_collecting")
            self._guard(task)
            self._care(task, CareState.RECORDING)
            task.linked_objects = {**task.linked_objects, "plan_id": plan_id}
            self._event(task, "plan.previewed", {"plan_id": plan_id})
            return self.store.save_task(task)

    def plan_confirmed(self, task_id: str, plan_id: str, operation_key: str) -> Task:
        with self._operation(task_id):
            task = self._task(task_id)
            if task.task_type != "plan" or task.state != TaskState.CREATED:
                raise ToolError("plan_task_not_confirmable")
            if task.linked_objects.get("plan_id") != plan_id:
                raise ToolError("operation_conflict")
            self._guard(task)
            self._care(task, CareState.REFLECTING, operation_key)
            self._transition(task, TaskState.DONE, operation_key)
            self._event(task, "plan.confirmed", {"plan_id": plan_id}, operation_key)
            self.store.save_receipt(operation_key, {"task_id": task_id, "plan_id": plan_id})
            return self.store.save_task(task)

    def plan_cancelled(self, task_id: str, plan_id: str, operation_key: str) -> Task:
        with self._operation(task_id):
            task = self._task(task_id)
            if task.task_type != "plan" or task.state != TaskState.CREATED:
                raise ToolError("plan_task_not_cancellable")
            if task.linked_objects.get("plan_id") != plan_id:
                raise ToolError("operation_conflict")
            self._guard(task)
            self._care(task, CareState.REFLECTING, operation_key)
            self._transition(task, TaskState.CANCELLED, operation_key)
            self._event(task, "plan.cancelled", {"plan_id": plan_id}, operation_key)
            self.store.save_receipt(operation_key, {"task_id": task_id, "plan_id": plan_id})
            return self.store.save_task(task)

    def start(self, user_id: str, meal: str, options: list[str], *, operation_key: str | None = None) -> Task:
        key = f"start:{user_id}:{operation_key or uuid4()}"
        request = {"user_id": user_id, "meal": meal, "options": options}
        with self.store.transaction():
            receipt = self._receipt(key, request)
            if receipt:
                return self._task(receipt["task_id"])
            task = Task(user_id=user_id)
            self.store.save_task(task)
            self._event(task, "task.created", {"state": task.state.value}, key)
            self.context(task.task_id, meal, options)
            self.store.save_receipt(key, {"request": request, "task_id": task.task_id})
            return self._task(task.task_id)

    def context(self, task_id: str, meal: str, options: list[str]) -> Task:
        from .models import Context
        with self._operation(task_id):
            task = self._task(task_id)
            if task.task_type != "micro_action" or task.state not in {TaskState.CREATED, TaskState.AWAITING_CONFIRMATION}:
                raise ToolError("task_not_collecting_context")
            self._guard(task)
            self._care(task, CareState.CHECKING)
            self._transition(task, TaskState.CONTEXT)
            data = self._invoke(task, "build_context", {"meal": meal, "options": options})
            task.context = Context(**data)
            self._transition(task, TaskState.CANDIDATES)
            task.candidates = generate_actions(task.context, filter_options(task.context), self.store.list_actions(task.user_id))
            # Distinct tasks must never overwrite each other's action history.
            for index, action in enumerate(task.candidates):
                action.action_id = f"{task.task_id}:action:{index}"
            self._event(task, "candidates.generated", {"count": len(task.candidates)})
            self._care(task, CareState.OFFERING)
            self._transition(task, TaskState.AWAITING_CONFIRMATION if task.candidates else TaskState.STOPPED)
            if not task.candidates:
                task.stopped_reason = "no_safe_candidate" if task.context.allergies_confirmed else "allergies_unconfirmed"
            return self.store.save_task(task)

    def decide(self, task_id: str, decision: Decision, action_index: int = 0, *, operation_key: str | None = None, expected_version: int | None = None) -> Task:
        with self._operation(task_id):
            task = self._task(task_id)
            key = f"{task_id}:command:{operation_key or 'decision'}"
            request = {"kind": "decision", "decision": decision.value, "index": action_index}
            if self._receipt(key, request):
                return task
            self._version(task, expected_version)
            if task.state != TaskState.AWAITING_CONFIRMATION:
                raise ToolError("task_not_awaiting_confirmation")
            self._guard(task)
            result = self._invoke(task, "save_decision", {"index": action_index, "decision": decision.value}, confirmed=True)
            task.selected_action_id = result["action_id"]
            self._care(task, CareState.AWAITING_FEEDBACK, key)
            self._transition(task, TaskState.ADOPTED if decision == Decision.ADOPT else TaskState.DONE, key)
            self._event(task, "action.decision_saved", {**result, "decision": decision.value}, key)
            self.store.save_receipt(key, {"request": request})
            return self.store.save_task(task)

    def feedback(self, task_id: str, execution: Execution, *, note: str = "", operation_key: str | None = None, expected_version: int | None = None) -> Task:
        with self._operation(task_id):
            task = self._task(task_id)
            key = f"{task_id}:command:{operation_key or 'feedback'}"
            request = {"kind": "feedback", "execution": execution.value, "note": note}
            if self._receipt(key, request):
                return task
            self._version(task, expected_version)
            if task.state != TaskState.ADOPTED or not task.selected_action_id:
                raise ToolError("task_not_awaiting_feedback")
            self._guard(task)
            result = self._invoke(task, "save_feedback", {"execution": execution.value, "note": note}, confirmed=True)
            self._care(task, CareState.REFLECTING, key)
            self._transition(task, TaskState.FEEDBACK, key)
            self._event(task, "action.feedback_saved", {**result, "execution": execution.value}, key)
            self.store.save_receipt(key, {"request": request})
            return self.store.save_task(task)

    def finish_review(self, task_id: str) -> dict[str, Any]:
        with self._operation(task_id):
            task = self._task(task_id)
            if task.task_type != "micro_action":
                raise ToolError("task_not_reviewable")
            profile = self.store.get_profile(task.user_id)
            if profile is None or not profile.consents.get("review_history", False):
                raise ToolError("review_consent_required")
            key = f"{task_id}:command:review"
            receipt = self._receipt(key, {"kind": "review"})
            if receipt:
                current = review(self.store, task.user_id)
                if receipt["result"].get("revision") == current.get("revision"):
                    return receipt["result"]
            if task.state not in {TaskState.FEEDBACK, TaskState.DONE}:
                raise ToolError("task_not_reviewable")
            self._guard(task)
            self._care(task, CareState.REFLECTING, key)
            self._transition(task, TaskState.REVIEW, key)
            result = self._invoke(task, "review", {})
            # Canonical JSON makes first and replayed responses identical.
            result = json.loads(dumps(result))
            self._transition(task, TaskState.DONE, key)
            self._event(task, "review.generated", {"adopted": result["adopted"], "completed": result["completed"]}, key)
            self.store.save_task(task)
            self.store.save_receipt(key, {"request": {"kind": "review"}, "result": result})
            return result

    def correct_feedback(self, task_id: str, execution: Execution, *, note: str = "",
                         operation_key: str | None = None, expected_version: int | None = None) -> Task:
        """Correct late feedback without creating a new action."""
        with self._operation(task_id):
            task = self._task(task_id)
            key = f"{task_id}:command:feedback-correction:{operation_key or 'default'}"
            request = {"kind": "feedback_correction", "execution": execution.value, "note": note}
            receipt = self._receipt(key, request)
            if receipt:
                return task
            self._version(task, expected_version)
            if task.state not in {TaskState.FEEDBACK, TaskState.REVIEW, TaskState.DONE} or not task.selected_action_id:
                raise ToolError("task_not_feedback_correctable")
            action = save_feedback(self.store, task.selected_action_id, execution, task.task_id, note)
            self._care(task, CareState.REFLECTING, key)
            self._transition(task, TaskState.FEEDBACK, key)
            self._event(task, "action.feedback_corrected", {"action_id": action.action_id, "execution": execution.value}, key)
            self.store.save_receipt(key, {"request": request})
            return self.store.save_task(task)

    def reminder_status(self, task_id: str) -> dict:
        task = self._task(task_id)
        profile = self.store.get_profile(task.user_id)
        if profile is None or not profile.consents.get("reminders", False):
            raise ToolError("reminder_consent_required")
        if not task.selected_action_id:
            return {"eligible": False, "due": False, "next_at": None, "reminder_count": 0}
        action = self.store.get_action(task.selected_action_id)
        if action is None:
            raise ToolError("reminder_not_available")
        return reminder_status(action)

    def remind(self, task_id: str, *, operation_key: str | None = None) -> Task:
        with self._operation(task_id):
            task = self._task(task_id)
            profile = self.store.get_profile(task.user_id)
            if profile is None or not profile.consents.get("reminders", False):
                raise ToolError("reminder_consent_required")
            if not task.selected_action_id:
                raise ToolError("reminder_not_available")
            key = f"{task_id}:command:reminder:{operation_key or 'default'}"
            request = {"kind": "reminder"}
            receipt = self._receipt(key, request)
            if receipt:
                return task
            action = self.store.get_action(task.selected_action_id)
            if action is None:
                raise ToolError("reminder_not_available")
            mark_reminded(action)
            self.store.save_action(action, key + ":action")
            self._event(task, "action.reminder_sent", {"action_id": action.action_id, "reminder_count": action.reminder_count}, key)
            self.store.save_receipt(key, {"request": request})
            return self.store.save_task(task)

    def interpret(self, task_id: str, messages: list[dict]) -> dict:
        """Reserve calls durably before network I/O; model output never grants writes."""
        with self._operation(task_id):
            task = self._task(task_id)
            if task.task_type == "profile_update":
                raise ToolError("model_task_not_supported")
            if task.state in {TaskState.STOPPED, TaskState.DONE, TaskState.CANCELLED}:
                raise ToolError("task_stopped")
            self._care(task, CareState.CHECKING)
            if task.model_calls >= self.MAX_MODEL_CALLS or task.budget_units <= 0:
                raise ToolError("model_budget_exhausted")
            task.model_calls += 1
            task.budget_units -= 1
            call_id = str(uuid4())
            provider = self.provider.for_task(task.task_type) if hasattr(self.provider, "for_task") else self.provider
            self._event(task, "model.called", {"call_id": call_id, "prompt_version": "intent-v1",
                                               "task_type": task.task_type, "model": getattr(provider, "model", "stub")})
            self.store.save_task(task)
        # Do not hold SQLite's write lock while waiting on a remote service.
        response = None
        error_code = None
        try:
            response = provider.complete(messages, [], INTENT_SCHEMA)
            result = parse_intent(response)
            outcome = "validated"
        except Exception as exc:
            result = fallback_intent(messages)
            outcome = "manual_fallback"
            error_code = exc.code if isinstance(exc, ToolError) else "model_dependency_failed"
        with self._operation(task_id):
            task = self._task(task_id)
            self._event(task, "model.result", {
                "call_id": call_id, "outcome": outcome, "error_code": error_code,
                "prompt_version": response.prompt_version if response else "intent-v1",
                "model": response.model if response else getattr(provider, "model", "unknown"),
                "input_tokens": response.input_tokens if response else None,
                "output_tokens": response.output_tokens if response else None,
            })
        return result

    def _task(self, task_id: str) -> Task:
        task = self.store.get_task(task_id)
        if task is None:
            raise ToolError("task_not_found")
        return task
