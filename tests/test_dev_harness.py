import json
import pytest

from dietlens_mvp.dev_harness import DEV_PLAN_SCHEMA, DevRole, DevState, DeveloperHarness
from dietlens_mvp.errors import ToolError
from dietlens_mvp.model_provider import ModelResponse


PLAN = {"summary":"add feature", "steps":["implement"], "files":["src/a.py"], "risks":["regression"], "test_commands":["pytest -q"]}


class Provider:
    def __init__(self, content=None): self.content = content or json.dumps(PLAN); self.calls = 0
    def complete(self, messages, tools, response_schema): self.calls += 1; return ModelResponse(self.content, model="dev-test")


def test_plan_patch_review_test_gate():
    provider = Provider(); harness = DeveloperHarness({DevRole.PLANNER: provider})
    task = harness.create("Implement a small feature")
    assert task.state == DevState.CREATED
    harness.plan(task.task_id)
    harness.begin_implementation(task.task_id)
    harness.submit_patch(task.task_id, summary="Implemented feature", changed_files=["src/a.py"])
    assert task.state == DevState.AWAITING_REVIEW
    with pytest.raises(ToolError, match="dev_tests_not_allowed"):
        harness.record_tests(task.task_id, passed=True, command="pytest -q")
    harness.review(task.task_id, approved=True)
    harness.record_tests(task.task_id, passed=True, command="pytest -q", output_digest="abc")
    assert task.state == DevState.COMPLETED
    assert provider.calls == 1


def test_rejected_patch_returns_to_implementation_without_writing_files():
    harness = DeveloperHarness({DevRole.PLANNER: Provider()})
    task = harness.create("Implement feature"); harness.plan(task.task_id); harness.begin_implementation(task.task_id)
    harness.submit_patch(task.task_id, summary="candidate", changed_files=["src/a.py"])
    harness.review(task.task_id, approved=False, note="needs changes")
    assert task.state == DevState.IMPLEMENTING
    assert task.changed_files == ["src/a.py"]


def test_invalid_model_output_and_missing_role_fail_closed():
    harness = DeveloperHarness({DevRole.PLANNER: Provider("not-json")})
    task = harness.create("Implement feature")
    with pytest.raises(ToolError, match="dev_invalid_model_output"):
        harness.plan(task.task_id)
    missing = DeveloperHarness({})
    task = missing.create("Implement feature")
    with pytest.raises(ToolError, match="dev_provider_not_configured"):
        missing.plan(task.task_id)


def test_iteration_and_model_budgets_are_bounded():
    harness = DeveloperHarness({DevRole.PLANNER: Provider()}, max_iterations=0)
    task = harness.create("Implement feature")
    with pytest.raises(ToolError, match="dev_max_iterations"):
        harness.plan(task.task_id)
    assert task.state == DevState.BLOCKED
    harness = DeveloperHarness({DevRole.PLANNER: Provider()}, max_model_calls=0)
    task = harness.create("Implement feature")
    with pytest.raises(ToolError, match="dev_model_budget_exhausted"):
        harness.plan(task.task_id)


def test_changed_paths_are_workspace_relative_and_memory_is_explicit():
    harness = DeveloperHarness({DevRole.PLANNER: Provider()})
    task = harness.create("Implement feature"); harness.plan(task.task_id); harness.begin_implementation(task.task_id)
    with pytest.raises(ToolError, match="dev_invalid_changed_file"):
        harness.submit_patch(task.task_id, summary="candidate", changed_files=["../outside.py"])
    harness.remember(task.task_id, "decision-log:123")
    assert task.memory_refs == ["decision-log:123"]
    assert all("candidate" not in event.payload.values() for event in task.events if event.event_type == "dev.patch_submitted")


def test_cancel_is_terminal_and_events_are_observable():
    harness = DeveloperHarness({DevRole.PLANNER: Provider()})
    task = harness.create("Implement feature")
    harness.cancel(task.task_id)
    harness.cancel(task.task_id)
    assert task.state == DevState.CANCELLED
    assert any(event.event_type == "dev.state_changed" for event in task.events)
    with pytest.raises(ToolError, match="dev_plan_not_allowed"):
        harness.plan(task.task_id)
