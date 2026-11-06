import pytest

from dietlens_mvp import DietLensAgent, Harness, InMemoryStore, SQLiteStore
from dietlens_mvp.errors import ToolError
from dietlens_mvp.meal_records import MealRecordService
from dietlens_mvp.portability import DataPortabilityService
from dietlens_mvp.models import Execution


@pytest.fixture(params=["memory", "sqlite"])
def store(request, tmp_path):
    if request.param == "memory":
        return InMemoryStore()
    return SQLiteStore(str(tmp_path / "portability.db"))


def test_export_contains_user_records_and_delete_requires_explicit_confirmation(store):
    agent = DietLensAgent(Harness(store))
    agent.onboard("portable-user", budget=30, allergies=[], consents={"review_history": True})
    task = agent.begin("portable-user", "午餐", ["鸡肉饭"])
    agent.adopt(task.task_id)
    agent.report(task.task_id, Execution.UNKNOWN, note="还不知道")
    record = MealRecordService(store).preview(
        "portable-user", meal_date="2026-11-01", meal_slot="午餐", name="鸡肉饭"
    )
    MealRecordService(store).confirm(record)

    portability = DataPortabilityService(store)
    exported = portability.export("portable-user")
    assert exported["profile"]["user_id"] == "portable-user"
    # The interactive profile confirmation is also a durable task.
    assert len(exported["tasks"]) == 2
    assert len(exported["actions"]) == 1
    assert exported["meal_records"][0]["quantity"] is None

    with pytest.raises(ToolError, match="delete_confirmation_required"):
        portability.delete("portable-user", confirmed=False)

    counts = portability.delete("portable-user", confirmed=True)
    assert counts["profiles"] == 1
    assert store.get_profile("portable-user") is None
    assert store.list_tasks("portable-user") == []
    assert store.list_actions("portable-user") == []
    assert store.list_meal_records("portable-user", include_deleted=True) == []
    with pytest.raises(ToolError, match="profile_not_found"):
        portability.export("portable-user")

