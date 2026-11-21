from datetime import datetime, timezone

from dietlens_mvp import DietLensAgent, Harness, InMemoryStore
from dietlens_mvp.comprehensive_review import ComprehensiveReviewService
from dietlens_mvp.food import assess_record, summarize_record, source_conflicts
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
    complete = record(ingredients=["燕麦"], allergens=[], raw={"ingredients_text": "燕麦", "allergens_tags": [], "allergens_declared_absent": True})
    assert assess_record(complete, []).status == "safe"
    blocked = record(ingredients=["花生"], allergens=["花生"], raw={"ingredients_text": "花生", "allergens_tags": ["花生"]})
    assert assess_record(blocked, ["花生"]).status == "blocked"


def test_empty_and_null_source_fields_are_not_verified_absence():
    for raw in ({}, {"ingredients_text": None, "allergens_tags": None},
                {"ingredients_text": "   ", "allergens_tags": []}):
        result = assess_record(record(raw=raw), [])
        assert result.status == "needs_confirmation"
        assert set(result.unknown_fields) == {"ingredients", "allergens"}
        summary = summarize_record(record(raw=raw))
        assert summary["ingredients_known"] is False
        assert summary["allergens_known"] is False
    explicit = record(raw={"ingredients_text": "燕麦", "allergens_tags": [], "allergens_declared_absent": True}, ingredients=["燕麦"])
    assert assess_record(explicit, []).status == "safe"


def test_open_food_facts_adapter_keeps_empty_fields_unknown():
    from dietlens_mvp.sources import OpenFoodFactsSource
    item = OpenFoodFactsSource()._from_product({"code": "x", "product_name": "测试食品", "ingredients_text": "", "allergens_tags": []})
    assessment = assess_record(item, [])
    assert assessment.status == "needs_confirmation"
    assert set(assessment.unknown_fields) == {"ingredients", "allergens"}


def test_source_conflicts_remain_visible_for_same_food():
    records = [record(source="off", source_id="a", serving_size=100, raw={"ingredients_text": "燕麦"}),
               record(source="fixture", source_id="b", serving_size=80, raw={"ingredients_text": "燕麦"})]
    conflicts = source_conflicts(records)
    assert conflicts and conflicts[0].field == "serving_size"


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


def test_plan_prefill_does_not_copy_ingredient_quantity_to_actual_meal():
    from dietlens_mvp.meal_records import MealRecordService
    store = InMemoryStore()
    plans = PlanningService(store)
    plan = plans.preview("u", start_date="2026-11-07", days=1, servings=1,
                         items=[PlanItem("i", "2026-11-07", "午餐", "番茄鸡蛋面", "tomato", 500, "g")])
    plans.confirm(plan.plan_id)
    record = MealRecordService(store).prefill("u", plan.plan_id, "i")
    assert record.name == "番茄鸡蛋面" and record.plan_item_id == "i"
    assert record.quantity is None and record.unit is None


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


def test_review_uses_explicit_plan_link_and_action_option():
    store = InMemoryStore()
    agent = DietLensAgent(Harness(store))
    agent.onboard("u", budget=30, allergies=[], consents={"review_history": True})
    plan_service = PlanningService(store)
    plan = plan_service.preview("u", start_date="2026-11-07", days=1, servings=1,
                                items=[PlanItem("i", "2026-11-07", "午餐", "鸡肉饭", "rice", 1, "份")])
    plan_service.confirm(plan.plan_id)
    task = agent.begin("u", "午餐", ["鸡肉饭", "番茄面"])
    agent.adopt(task.task_id, action_index=1)
    action = store.list_actions("u")[0]
    assert action.selected_option == "番茄面"
    record = __import__("dietlens_mvp.meal_records", fromlist=["MealRecordService"]).MealRecordService(store)
    saved = record.confirm(record.preview(user_id="u", meal_date="2026-11-07", meal_slot="午餐", name="鸡肉饭", plan_id=plan.plan_id, plan_item_id="i"))
    result = ComprehensiveReviewService(store).generate("u", period="day", anchor_date="2026-11-07")
    assert result["plan"]["matched_meals"] == 1
    assert result["actual"]["coverage"]["numerator"] == 1
    assert result["actual"]["records"][0]["plan_item_id"] == "i"
