from datetime import timedelta, timezone, datetime

import pytest

from dietlens_mvp import DietLensAgent
from dietlens_mvp.errors import ToolError
from dietlens_mvp.models import Decision, Execution
from dietlens_mvp.reminders import mark_reminded, reminder_status


def test_reminder_is_opt_in_and_uses_backoff():
    agent = DietLensAgent()
    agent.onboard("u", budget=30, allergies=[], consents={"review_history": True, "reminders": True})
    task = agent.begin("u", "午餐", ["鸡肉饭"])
    agent.adopt(task.task_id)
    action = agent.harness.store.list_actions("u")[0]
    before_due = reminder_status(action)
    assert before_due["eligible"] and not before_due["due"]
    mark_reminded(action, at=action.created_at + timedelta(days=1))
    assert action.reminder_count == 1
    assert reminder_status(action, at=action.last_reminded_at + timedelta(days=3))["due"]


def test_reminder_without_consent_is_blocked():
    agent = DietLensAgent()
    agent.onboard("u", budget=30, allergies=[], consents={"review_history": True})
    task = agent.begin("u", "午餐", ["鸡肉饭"])
    agent.adopt(task.task_id)
    with pytest.raises(ToolError, match="reminder_consent_required"):
        agent.harness.reminder_status(task.task_id)


def test_harness_reminder_is_due_and_idempotent():
    agent = DietLensAgent()
    agent.onboard("u", budget=30, allergies=[], consents={"review_history": True, "reminders": True})
    task = agent.begin("u", "午餐", ["鸡肉饭"])
    agent.adopt(task.task_id)
    action = agent.harness.store.list_actions("u")[0]
    action.created_at = action.created_at - timedelta(days=2)
    agent.harness.store.actions[action.action_id] = action
    assert agent.harness.reminder_status(task.task_id)["due"]
    agent.harness.remind(task.task_id, operation_key="r1")
    agent.harness.remind(task.task_id, operation_key="r1")
    assert agent.harness.store.get_action(action.action_id).reminder_count == 1


def test_cooldown_expires_without_changing_profile():
    agent = DietLensAgent()
    agent.onboard("u", budget=30, allergies=[], consents={"review_history": True})
    first = agent.begin("u", "午餐", ["鸡肉饭", "番茄面"])
    agent.adopt(first.task_id)
    agent.report(first.task_id, Execution.NOT_DONE)
    action = agent.harness.store.list_actions("u")[0]
    action.cooldown_until = datetime.now(timezone.utc) - timedelta(seconds=1)
    agent.harness.store.actions[action.action_id] = action
    second = agent.begin("u", "午餐", ["鸡肉饭", "番茄面"])
    assert "鸡肉饭" in second.candidates[0].behavior
    assert agent.harness.store.get_profile("u").dislikes == []
