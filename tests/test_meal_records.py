from datetime import date

import pytest

from dietlens_mvp import InMemoryStore, SQLiteStore
from dietlens_mvp.errors import ToolError
from dietlens_mvp.meal_records import MealRecordService
from dietlens_mvp.models import PlanItem
from dietlens_mvp.planning import PlanningService


def make_plan(service, user="u"):
    d = "2026-11-01"
    items = [PlanItem("b", d, "早餐", "燕麦", "oat", 50, "g"),
             PlanItem("l", d, "午餐", "鸡肉饭", "chicken", 200, "g"),
             PlanItem("d", d, "晚餐", "番茄面", "tomato", 1, "份")]
    plan = service.preview(user, start_date=d, days=1, servings=1, items=items)
    return service.confirm(plan.plan_id)


@pytest.fixture(params=["memory", "sqlite"])
def services(request, tmp_path):
    store = InMemoryStore() if request.param == "memory" else SQLiteStore(str(tmp_path / "records.db"))
    yield store, PlanningService(store), MealRecordService(store)
    if isinstance(store, SQLiteStore):
        store.close()


def test_prefill_is_read_only_and_confirm_creates_actual_record(services):
    store, plans, records = services
    plan = make_plan(plans)
    draft = records.prefill("u", plan.plan_id, "l")
    assert store.list_meal_records("u") == []
    saved = records.confirm(draft)
    assert saved.source == "plan_prefill"
    assert len(store.list_meal_records("u")) == 1


def test_unknown_quantity_is_not_zero_and_manual_source_is_preserved(services):
    _, _, records = services
    draft = records.preview(user_id="u", meal_date="2026-11-01", meal_slot="午餐", name="外卖", quantity=None)
    saved = records.confirm(draft)
    assert saved.quantity is None and saved.unit is None and saved.source == "user_self_report"
    assert records.coverage("u")["quantity_unknown"] == 1


def test_update_is_versioned_and_duplicate_update_is_idempotent(services):
    _, _, records = services
    saved = records.confirm(records.preview(user_id="u", meal_date="2026-11-01", meal_slot="午餐", name="鸡肉饭", quantity=1, unit="份"))
    updated = records.update(saved.record_id, expected_version=1, operation_key="edit-1", quantity=None, unit=None)
    again = records.update(saved.record_id, expected_version=1, operation_key="edit-1", quantity=999, unit="g")
    assert updated.version == 2 and updated.quantity is None
    assert again == updated
    with pytest.raises(ToolError, match="version_conflict"):
        records.update(saved.record_id, expected_version=1, quantity=2, unit="份")


def test_delete_is_tombstone_and_review_recalculates(services):
    store, plans, records = services
    plan = make_plan(plans)
    saved = records.confirm(records.prefill("u", plan.plan_id, "l"))
    assert records.coverage("u")["recorded_meals"] == 1
    deleted = records.delete(saved.record_id, expected_version=1)
    assert deleted.status == "deleted"
    assert records.list("u") == []
    assert records.coverage("u")["recorded_meals"] == 0
    assert records.list("u", include_deleted=True)[0].status == "deleted"


def test_reusing_operation_key_for_another_record_is_rejected(services):
    _, _, records = services
    first = records.confirm(records.preview(user_id="u", meal_date="2026-11-01", meal_slot="午餐", name="米饭"), operation_key="same")
    second = records.preview(user_id="u", meal_date="2026-11-01", meal_slot="晚餐", name="面条")
    with pytest.raises(ToolError, match="operation_conflict"):
        records.confirm(second, operation_key="same")


def test_plan_is_not_counted_as_actual_meal(services):
    _, plans, records = services
    make_plan(plans)
    result = records.coverage("u")
    assert result["planned_meals"] == 3 and result["recorded_meals"] == 0


def test_replaced_plan_is_not_counted_twice_in_coverage(services):
    _, plans, records = services
    make_plan(plans)
    make_plan(plans)
    assert records.coverage("u")["planned_meals"] == 3
