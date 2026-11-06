"""Phase-0 invariants, replayed against both repositories."""
from dataclasses import replace
from concurrent.futures import ThreadPoolExecutor
import json
import sqlite3
from pathlib import Path

import pytest

from dietlens_mvp import DietLensAgent, Harness, InMemoryStore, SQLiteStore
from dietlens_mvp.errors import ToolError
from dietlens_mvp.models import CareState, Decision, Execution, TaskState
from dietlens_mvp.model_provider import ModelResponse


@pytest.fixture(params=["memory", "sqlite"])
def store(request, tmp_path):
    repo = InMemoryStore() if request.param == "memory" else SQLiteStore(str(tmp_path / "test.db"))
    yield repo
    if isinstance(repo, SQLiteStore):
        repo.close()


def begin(store):
    agent = DietLensAgent(Harness(store))
    agent.onboard("u", budget=30, allergies=[], consents={"review_history": True})
    return agent, agent.begin("u", "午餐", ["米饭", "面条"])


def test_every_state_transition_is_recorded(store):
    agent, task = begin(store)
    agent.adopt(task.task_id)
    agent.report(task.task_id, Execution.COMPLETE)
    agent.review(task.task_id)
    transitions = [e.payload for e in store.list_events(task.task_id) if e.event_type == "task.state_changed"]
    state = TaskState.CREATED.value
    for event in transitions:
        assert event["from"] == state
        state = event["to"]
    assert state == TaskState.DONE.value
    assert len(transitions) == 7


def test_step_failure_rolls_back_action_task_and_receipt(store, monkeypatch):
    agent, task = begin(store)
    original = store.append_event
    def fail(event):
        if event.event_type == "action.decision_saved":
            raise RuntimeError("simulated disk failure")
        original(event)
    monkeypatch.setattr(store, "append_event", fail)
    before = store.list_events(task.task_id)
    with pytest.raises(RuntimeError):
        agent.adopt(task.task_id)
    assert store.list_actions("u") == []
    assert store.get_task(task.task_id) == task
    assert store.list_events(task.task_id) == before
    monkeypatch.setattr(store, "append_event", original)
    agent.adopt(task.task_id)
    assert len(store.list_actions("u")) == 1


def test_repeated_tasks_do_not_overwrite_action_history(store):
    agent, first = begin(store)
    agent.adopt(first.task_id)
    agent.report(first.task_id, Execution.COMPLETE)
    second = agent.begin("u", "午餐", ["米饭", "面条"])
    agent.skip(second.task_id)
    assert first.candidates[0].action_id != second.candidates[0].action_id
    result = agent.review(first.task_id)
    assert len(result["actions"]) == 2
    assert result["completed"] == 1


def test_retry_with_different_candidate_is_conflict(store):
    agent, task = begin(store)
    agent.adopt(task.task_id)
    with pytest.raises(ToolError, match="operation_conflict"):
        agent.adopt(task.task_id, 1)
    assert len(store.list_actions("u")) == 1


def test_version_conflict_does_not_write_action(store):
    agent, task = begin(store)
    with pytest.raises(ToolError, match="version_conflict"):
        agent.harness.decide(task.task_id, Decision.ADOPT, expected_version=task.version - 1)
    assert store.list_actions("u") == []


def test_stale_repository_write_is_rejected(store):
    _, task = begin(store)
    stale = replace(task)
    store.save_task(task)
    with pytest.raises(ToolError, match="version_conflict"):
        store.save_task(stale)


def test_budget_stop_is_persisted(store):
    agent, task = begin(store)
    task.iteration = Harness.MAX_ITERATIONS
    store.save_task(task)
    with pytest.raises(ToolError, match="max_iterations"):
        agent.adopt(task.task_id)
    stopped = store.get_task(task.task_id)
    assert stopped.state == TaskState.STOPPED
    assert stopped.stopped_reason == "max_iterations"
    assert store.list_actions("u") == []
    assert store.list_events(task.task_id)[-1].payload == {"code": "max_iterations"}


def test_registry_blocks_unknown_tool_and_unconfirmed_write(store):
    agent, _ = begin(store)
    with pytest.raises(ToolError, match="tool_not_allowed"):
        agent.harness.registry.invoke("delete_everything", {})
    with pytest.raises(ToolError, match="confirmation_required"):
        agent.harness.registry.invoke("save_decision", {"index": 0, "decision": "adopt"})
    assert store.list_actions("u") == []


@pytest.mark.parametrize("content", ["not json", '{"intent":"plan"}', '[]', '{"confidence": NaN}'])
def test_invalid_model_output_falls_back_without_business_write(store, content):
    agent, task = begin(store)
    class BrokenProvider:
        def complete(self, *args):
            return ModelResponse(content)
    agent.harness.provider = BrokenProvider()
    advice = agent.harness.interpret(task.task_id, [])
    assert advice["missing_fields"] == ["meal", "options"]
    assert store.list_actions("u") == []
    assert store.get_task(task.task_id).state == task.state
    agent.adopt(task.task_id)  # deterministic path remains usable


def test_model_outage_and_call_budget(store):
    agent, task = begin(store)
    class OfflineProvider:
        def complete(self, *args):
            raise OSError("offline")
    agent.harness.provider = OfflineProvider()
    for _ in range(2):
        assert agent.harness.interpret(task.task_id, [])["confidence"] == 0
    with pytest.raises(ToolError, match="model_budget_exhausted"):
        agent.harness.interpret(task.task_id, [])
    assert store.get_task(task.task_id).state == task.state
    agent.adopt(task.task_id)


def test_model_outage_keeps_explicit_meal_options_usable(store):
    agent = DietLensAgent(Harness(store))
    agent.onboard("fallback-user", budget=30, allergies=[], consents={"review_history": True})
    task = agent.harness.create_task("fallback-user")

    class OfflineProvider:
        def complete(self, *args):
            raise TimeoutError("slow model")

    agent.harness.provider = OfflineProvider()
    result = agent.harness.interpret(task.task_id, [{"role": "user", "content": "午餐想在鸡肉饭和番茄面里选一个"}])
    assert result["entities"] == {"meal": "午餐", "options": ["鸡肉饭", "番茄面"]}


def test_start_operation_is_idempotent(store):
    agent, _ = begin(store)
    first = agent.harness.start("u", "晚餐", ["米饭"], operation_key="start-1")
    again = agent.harness.start("u", "晚餐", ["米饭"], operation_key="start-1")
    assert first == again
    with pytest.raises(ToolError, match="operation_conflict"):
        agent.harness.start("u", "晚餐", ["面条"], operation_key="start-1")


def test_restart_receipts_events_and_feedback_replay(tmp_path):
    path = str(tmp_path / "restart.db")
    store = SQLiteStore(path)
    agent, task = begin(store)
    agent.adopt(task.task_id)
    store.close()
    store = SQLiteStore(path)
    agent = DietLensAgent(Harness(store))
    agent.adopt(task.task_id)
    agent.report(task.task_id, Execution.COMPLETE)
    result = agent.review(task.task_id)
    count = len(store.list_events(task.task_id))
    store.close()
    store = SQLiteStore(path)
    agent = DietLensAgent(Harness(store))
    agent.report(task.task_id, Execution.COMPLETE)
    assert agent.review(task.task_id) == result
    assert len(store.list_events(task.task_id)) == count
    assert len(store.list_actions("u")) == 1
    store.close()


def test_action_receipt_replays_original_payload_after_restart(tmp_path):
    path = str(tmp_path / "receipt.db")
    store = SQLiteStore(path)
    _, task = begin(store)
    original = store.save_action(task.candidates[0], "operation-1")
    store.close()
    store = SQLiteStore(path)
    changed = replace(original, behavior="changed", execution=Execution.COMPLETE)
    assert store.save_action(changed, "operation-1") == original
    assert store.get_action(original.action_id) == original
    store.close()


def test_two_connections_read_fresh_state_and_reject_stale_write(tmp_path):
    path = str(tmp_path / "shared.db")
    first = SQLiteStore(path)
    _, task = begin(first)
    second = SQLiteStore(path)
    stale = second.get_task(task.task_id)
    task.stopped_reason = "test"
    first.save_task(task)
    assert second.get_task(task.task_id).stopped_reason == "test"
    with pytest.raises(ToolError, match="version_conflict"):
        second.save_task(stale)
    first.close()
    second.close()


def test_sqlite_repository_is_safe_for_fastapi_worker_threads(tmp_path):
    store = SQLiteStore(str(tmp_path / "threaded-api.db"))

    def onboard(user_id):
        return DietLensAgent(Harness(store)).onboard(
            user_id, budget=30, allergies=[], consents={"review_history": True}
        ).user_id

    try:
        with ThreadPoolExecutor(max_workers=2) as pool:
            assert sorted(pool.map(onboard, ["thread-a", "thread-b"])) == ["thread-a", "thread-b"]
        assert store.get_profile("thread-a") is not None
        assert store.get_profile("thread-b") is not None
    finally:
        store.close()


def test_legacy_unversioned_database_migrates_without_data_loss(tmp_path):
    path = str(tmp_path / "legacy.db")
    db = sqlite3.connect(path)
    migration = Path(__file__).parents[1] / "dietlens_mvp/migrations/001_initial.sql"
    db.executescript(migration.read_text())
    db.execute("INSERT INTO profiles VALUES (?,?)", ("old", json.dumps({"user_id": "old", "budget": 20})))
    db.execute("INSERT INTO tasks VALUES (?,?)", ("legacy-task", json.dumps({"task_id": "legacy-task", "user_id": "old", "state": "awaiting_confirmation"})))
    db.commit()
    db.close()
    for _ in range(2):
        store = SQLiteStore(path)
        assert store.get_profile("old").budget == 20
        assert store.get_task("legacy-task").version == 1
        assert store.get_task("legacy-task").created_at
        assert store.db.execute("SELECT count(*) FROM schema_migrations").fetchone()[0] == 6
        store.close()


def test_fixed_replay_cases(store):
    for case in json.loads((Path(__file__).parent / "fixtures/harness_replays.json").read_text()):
        agent = DietLensAgent(Harness(store))
        agent.onboard(case["id"], budget=20, allergies=case["allergies"], consents={"review_history": True})
        task = agent.begin(case["id"], "午餐", case["options"])
        assert task.state.value == case["expected_state"]
        if task.candidates:
            agent.adopt(task.task_id)
            if case.get("feedback"):
                agent.report(task.task_id, Execution(case["feedback"]))
        from dietlens_mvp.tools import review
        result = review(store, case["id"])
        assert result["completed"] == case["expected_completed"]


def test_cli_resumes_feedback_without_onboarding(store):
    from cli import continue_task
    agent, task = begin(store)
    adopted = agent.adopt(task.task_id)
    output = []
    continue_task(agent, adopted, input_fn=lambda _: "complete", output_fn=output.append)
    assert store.get_task(task.task_id).state == TaskState.DONE
    assert output[-1]["completed"] == 1


def test_tool_budget_stop_blocks_business_write(store):
    agent, task = begin(store)
    agent.harness.MAX_TOOL_CALLS = 0
    with pytest.raises(ToolError, match="tool_budget_exhausted"):
        agent.adopt(task.task_id)
    assert store.get_task(task.task_id).state == TaskState.STOPPED
    assert store.list_actions("u") == []


def test_registry_validates_input_and_output():
    from dietlens_mvp.registry import ToolRegistry, ToolSpec
    registry = ToolRegistry()
    schema = {"type": "object", "required": ["value"], "properties": {"value": {"type": "integer"}}}
    registry.register(ToolSpec("example", "read", False, schema, schema), lambda value: {"value": "wrong"})
    with pytest.raises(ToolError, match="invalid_tool_input"):
        registry.invoke("example", {"value": "wrong"})
    with pytest.raises(ToolError, match="invalid_tool_output"):
        registry.invoke("example", {"value": 1})
