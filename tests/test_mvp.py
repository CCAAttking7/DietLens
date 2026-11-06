import pytest

from dietlens_mvp import DietLensAgent
from dietlens_mvp.models import CareState, Execution, TaskState
from dietlens_mvp.tools import ToolError


def test_vertical_slice_and_review():
    agent = DietLensAgent()
    agent.onboard("u1", budget=40, allergies=["花生"], goal="减少含糖饮料", consents={"review_history": True})
    task = agent.begin("u1", "午餐", ["鸡肉饭", "花生沙拉"])
    assert task.state == TaskState.AWAITING_CONFIRMATION
    assert task.care_state == CareState.OFFERING
    assert len(task.candidates) == 1
    agent.adopt(task.task_id)
    assert agent.harness.store.get_task(task.task_id).care_state == CareState.AWAITING_FEEDBACK
    agent.report(task.task_id, Execution.COMPLETE)
    assert agent.harness.store.get_task(task.task_id).care_state == CareState.REFLECTING
    result = agent.review(task.task_id)
    assert result["adopted"] == 1
    assert result["completed"] == 1
    assert result["feedback_coverage"] == 1.0


def test_idempotent_decision_does_not_duplicate_action():
    agent = DietLensAgent()
    agent.onboard("u1", budget=40, allergies=[], consents={"review_history": True})
    task = agent.begin("u1", "午餐", ["鸡肉饭"])
    agent.adopt(task.task_id)
    # Simulates a retry after an ambiguous response: it is a successful no-op.
    agent.adopt(task.task_id)
    assert len(agent.harness.store.actions) == 1


def test_unknown_allergy_stops_affected_recommendation():
    agent = DietLensAgent()
    agent.onboard("u1", budget=40, allergies=["花生"], consents={"review_history": True})
    task = agent.begin("u1", "午餐", ["花生拌面"])
    assert task.state == TaskState.STOPPED
    assert task.stopped_reason == "no_safe_candidate"


def test_feedback_requires_adoption():
    agent = DietLensAgent()
    agent.onboard("u1", budget=40, allergies=[], consents={"review_history": True})
    task = agent.begin("u1", "午餐", ["鸡肉饭"])
    with pytest.raises(ToolError, match="task_not_awaiting_feedback"):
        agent.report(task.task_id, Execution.COMPLETE)


def test_barrier_changes_only_the_next_candidate():
    agent = DietLensAgent()
    agent.onboard("u1", budget=40, allergies=[], consents={"review_history": True})
    first = agent.begin("u1", "午餐", ["鸡肉饭", "番茄面"])
    agent.adopt(first.task_id)
    agent.report(first.task_id, Execution.NOT_DONE, note="排队太久")
    second = agent.begin("u1", "午餐", ["鸡肉饭", "番茄面"])
    assert "番茄面" in second.candidates[0].behavior
    assert agent.harness.store.get_profile("u1").dislikes == []


def test_micro_action_dimensions_rotate_without_model_deciding_state():
    agent = DietLensAgent()
    agent.onboard("u1", budget=40, allergies=[], consents={"review_history": True})
    dimensions = []
    for _ in range(4):
        task = agent.begin("u1", "午餐", ["鸡肉饭"])
        dimensions.append(task.candidates[0].dimension)
        agent.adopt(task.task_id)
        agent.report(task.task_id, Execution.COMPLETE)
    assert dimensions == ["substitution", "add_on", "sequence", "timing"]


def test_late_feedback_corrects_same_action_and_recomputes_review():
    agent = DietLensAgent()
    agent.onboard("u1", budget=40, allergies=[], consents={"review_history": True})
    task = agent.begin("u1", "午餐", ["鸡肉饭"])
    agent.adopt(task.task_id)
    agent.report(task.task_id, Execution.COMPLETE)
    assert agent.review(task.task_id)["completed"] == 1
    current = agent.harness.store.get_task(task.task_id)
    agent.correct_report(task.task_id, Execution.NOT_DONE, note="后来发现其实没做到", expected_version=current.version)
    result = agent.review(task.task_id)
    assert result["completed"] == 0
    action = agent.harness.store.list_actions("u1")[0]
    assert len(action.feedback_history) == 2
