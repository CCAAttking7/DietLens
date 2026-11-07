from datetime import datetime, timezone

from dietlens_mvp import DietLensAgent, Harness, InMemoryStore
from dietlens_mvp.comprehensive_review import ComprehensiveReviewService
from dietlens_mvp.food import assess_record
from dietlens_mvp.models import Action, Decision, Execution, PlanItem, Profile
from dietlens_mvp.planning import PlanningService
from dietlens_mvp.sources import FoodRecord
from dietlens_mvp.tools import generate_actions


def record(**kwargs):
    data = dict(name="燕麦", source="fixture", source_id="1", ingredients=[], allergens=[], raw={}, nutrients={})
    data.update(kwargs)
    return FoodRecord(**data)


def test_allergy_state_is_explicit_and_legacy_empty_stays_unknown():
    agent = DietLensAgent(Harness(InMemoryStore()))
    unknown = agent.preview_profile("u", {"goal": "简单一点"}, expected_version=0)
    saved = agent.confirm_profile("u", unknown.task_id, operation_key="unknown", expected_version=0)
    assert saved.allergy_status == "unknown"
    assert agent.begin("u", "午餐", ["鸡肉饭"]).stopped_reason == "allergies_unconfirmed"

    draft = agent.preview_profile("u", {"allergy_status": "none", "allergies": []}, expected_version=1)
    saved = agent.confirm_profile("u", draft.task_id, operation_key="none", expected_version=1)
    assert saved.allergy_status == "none"
    assert agent.begin("u", "午餐", ["鸡肉饭"]).state.value == "awaiting_confirmation"

    draft = agent.preview_profile("u", {"allergy_status": "specified", "allergies": ["花生"]}, expected_version=2)
    saved = agent.confirm_profile("u", draft.task_id, operation_key="specified", expected_version=2)
    assert saved.allergy_status == "specified" and saved.allergies == ["花生"]

    legacy = Profile(user_id="legacy", allergies=[])
    assert legacy.allergy_status == "unknown"


def test_food_without_source_fields_needs_confirmation_even_without_constraints():
    assert assess_record(record(), []).status == "needs_confirmation"
    complete = record(ingredients=["燕麦"], allergens=[], raw={"ingredients_text": "燕麦", "allergens_tags": []})
    assert assess_record(complete, []).status == "safe"
    blocked = record(ingredients=["花生"], allergens=["花生"], raw={"ingredients_text": "花生", "allergens_tags": ["花生"]})
    assert assess_record(blocked, ["花生"]).status == "blocked"


def test_soft_dislike_changes_order_without_becoming_safety_exclusion():
    context = __import__("dietlens_mvp.models", fromlist=["Context"]).Context(
        "u", "午餐", ["香菜鸡肉饭", "鸡肉饭"], None, [], ["香菜"], allergies_confirmed=True
    )
    actions = generate_actions(context, context.options)
    assert actions and "鸡肉饭" in actions[0].behavior
    assert len(actions) == 2


def test_plan_without_ingredient_has_no_fake_shopping_item():
    store = InMemoryStore()
    plans = PlanningService(store)
    plan = plans.preview("u", start_date="2026-11-07", days=1, servings=1,
                         items=[PlanItem("i", "2026-11-07", "午餐", "番茄鸡蛋面", "", 0, "份")])
    plans.confirm(plan.plan_id)
    shopping = plans.generate_shopping_list(plan.plan_id)
    assert shopping.items == []


def test_review_only_calls_barriers_repeated_in_same_context():
    store = InMemoryStore()
    agent = DietLensAgent(Harness(store))
    agent.onboard("u", budget=30, allergies=[], consents={"review_history": True})
    for meal, option in (("午餐", "鸡肉饭"), ("晚餐", "番茄面")):
        task = agent.begin("u", meal, [option])
        agent.adopt(task.task_id)
        agent.report(task.task_id, Execution.PARTIAL)
    result = ComprehensiveReviewService(store).generate("u", period="week", anchor_date="2026-11-07")
    assert not any(item["kind"] == "barrier" for item in result["insights"])
