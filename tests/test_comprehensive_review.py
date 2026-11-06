from datetime import date
from datetime import datetime, timezone

import pytest

from dietlens_mvp import Harness, InMemoryStore
from dietlens_mvp.comprehensive_review import ComprehensiveReviewService, resolve_period
from dietlens_mvp.errors import ToolError
from dietlens_mvp.meal_records import MealRecordService
from dietlens_mvp.models import MealRecord, PlanItem
from dietlens_mvp.models import Execution
from dietlens_mvp.planning import PlanningService


def setup_user():
    store = InMemoryStore()
    from dietlens_mvp import DietLensAgent, Harness
    agent = DietLensAgent(Harness(store))
    agent.onboard("u", budget=30, allergies=[], consents={"review_history": True})
    return store, PlanningService(store), MealRecordService(store), ComprehensiveReviewService(store)


def test_period_boundaries():
    assert resolve_period("day", "2026-11-04") == (date(2026, 11, 4), date(2026, 11, 4))
    assert resolve_period("week", "2026-11-04") == (date(2026, 11, 2), date(2026, 11, 8))
    assert resolve_period("month", "2026-11-04") == (date(2026, 11, 1), date(2026, 11, 30))
    with pytest.raises(ToolError, match="invalid_review_period"):
        resolve_period("quarter", "2026-11-04")


def test_review_keeps_plan_actual_and_unknown_separate():
    store, plans, records, review = setup_user()
    items = [PlanItem("b", "2026-11-04", "早餐", "燕麦", "oat", 50, "g"),
             PlanItem("l", "2026-11-04", "午餐", "鸡肉饭", "chicken", 1, "份"),
             PlanItem("d", "2026-11-04", "晚餐", "番茄面", "tomato", 1, "份")]
    plan = plans.preview("u", start_date="2026-11-04", days=1, servings=1, items=items)
    plans.confirm(plan.plan_id)
    saved = records.confirm(records.preview(user_id="u", meal_date="2026-11-04", meal_slot="午餐", name="鸡肉饭"))
    result = review.generate("u", period="day", anchor_date="2026-11-04")
    assert result["plan"]["planned_meals"] == 3
    assert result["actual"]["recorded_meals"] == 1
    assert result["actual"]["coverage"]["numerator"] == 1
    assert result["actual"]["coverage"]["denominator"] == 3
    assert result["nutrition"]["coverage"]["value"] is None
    assert result["nutrition"]["coverage"]["status"] == "unknown"
    assert result["nutrition"]["unknown"] == 1
    assert result["actual"]["records"][0]["record_id"] == saved.record_id
    assert len(result["timeline"]) == 3
    assert sum(item["status"] == "same_slot" for item in result["timeline"]) == 1
    assert sum(item["status"] == "planned" for item in result["timeline"]) == 2
    assert result["source"] == "deterministic_template"


def test_zero_denominator_is_not_zero_ratio_and_consent_is_required():
    store, _, _, review = setup_user()
    result = review.generate("u", period="day", anchor_date="2026-11-04")
    assert result["actual"]["coverage"]["value"] is None
    assert result["nutrition"]["coverage"]["value"] is None
    store.profiles["u"].consents["review_history"] = False
    with pytest.raises(ToolError, match="review_consent_required"):
        review.generate("u", period="day", anchor_date="2026-11-04")


def test_frozen_period_does_not_count_later_feedback():
    store, _, _, review = setup_user()
    from dietlens_mvp import DietLensAgent
    agent = DietLensAgent(Harness(store))
    task = agent.begin("u", "午餐", ["鸡肉饭"])
    agent.adopt(task.task_id)
    action = store.list_actions("u")[0]
    action.created_at = datetime(2026, 11, 4, 9, tzinfo=timezone.utc)
    action.execution = Execution.COMPLETE
    action.feedback_history = [{"execution": "complete", "recorded_at": "2026-11-05T09:00:00+00:00", "version": 2, "note": ""}]
    store.actions[action.action_id] = action
    result = review.generate("u", period="day", anchor_date="2026-11-04")
    assert result["actions"]["completed"] == 0
    assert result["actions"]["feedback_received"] == 0


def test_review_emits_explanatory_insights_for_plan_gap_and_unknown_quantity():
    store, plans, records, review = setup_user()
    items = [PlanItem("b", "2026-11-04", "早餐", "燕麦", "oat", 50, "g"),
             PlanItem("l", "2026-11-04", "午餐", "鸡肉饭", "chicken", 1, "份")]
    plan = plans.preview("u", start_date="2026-11-04", days=1, servings=1, items=items)
    plans.confirm(plan.plan_id)
    records.confirm(records.preview(user_id="u", meal_date="2026-11-04", meal_slot="午餐", name="临时的一餐"))
    result = review.generate("u", period="day", anchor_date="2026-11-04")
    kinds = {item["kind"] for item in result["insights"]}
    assert "plan_gap" in kinds
    assert "unknown_quantity" in kinds
    assert all(item["body"] and item["evidence"] for item in result["insights"])
