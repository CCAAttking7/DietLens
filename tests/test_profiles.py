from dataclasses import asdict

import pytest

from dietlens_mvp import DietLensAgent, Harness, InMemoryStore, SQLiteStore
from dietlens_mvp.cold_start import initialize_user
from dietlens_mvp.errors import ToolError
from dietlens_mvp.models import Execution, TaskState


@pytest.fixture(params=["memory", "sqlite"])
def agent(request, tmp_path):
    store = InMemoryStore() if request.param == "memory" else SQLiteStore(str(tmp_path / "profile.db"))
    yield DietLensAgent(Harness(store))
    if isinstance(store, SQLiteStore):
        store.close()


def confirm(agent, user="u", changes=None, consents=None):
    current = agent.harness.store.get_profile(user)
    draft = agent.preview_profile(user, changes if changes is not None else {"allergies": [], "budget": 30},
                                  expected_version=current.version if current else 0, consents=consents)
    return agent.confirm_profile(user, draft.task_id, operation_key=draft.task_id, expected_version=draft.expected_version)


def test_preview_and_cancel_never_write_authoritative_profile(agent):
    draft = agent.preview_profile("u", {"budget": 30}, expected_version=0, consents={"review_history": True})
    assert agent.harness.store.get_profile("u") is None
    assert agent.harness.store.list_profile_versions("u") == []
    agent.cancel_profile("u", draft.task_id)
    agent.cancel_profile("u", draft.task_id)
    assert agent.harness.store.get_profile("u") is None
    assert agent.harness.store.list_consent_events("u") == []
    with pytest.raises(ToolError, match="profile_not_awaiting_confirmation"):
        agent.confirm_profile("u", draft.task_id, operation_key="cancelled", expected_version=0)


def test_versioned_fields_and_separate_hard_soft_constraints(agent):
    original = confirm(agent, changes={"budget": 30, "allergies": [" 花生 ", "花生"], "hard_avoids": ["猪肉"], "dislikes": ["香菜"]})
    assert original.allergies == ["花生"]
    assert original.hard_avoids == ["猪肉"]
    assert original.dislikes == ["香菜"]
    assert original.field_sources["allergies"] == "user_confirmation"
    draft = agent.preview_profile("u", {"budget": 40}, expected_version=1)
    assert draft.changes == {"budget": {"before": 30, "after": 40}}
    agent.cancel_profile("u", draft.task_id)
    assert agent.harness.store.get_profile("u") == original
    updated = confirm(agent, changes={"budget": 50})
    assert updated.version == 2
    history = agent.harness.store.list_profile_versions("u")
    assert [p.budget for p in history] == [30, 50]
    assert updated.created_at == original.created_at
    task = agent.begin("u", "午餐", ["花生面", "猪肉饭", "香菜鸡肉饭"])
    assert len(task.candidates) == 1
    assert "香菜鸡肉饭" in task.candidates[0].behavior


def test_skipped_allergies_are_unknown_not_none(agent):
    profile = confirm(agent, changes={"goal": "少喝糖饮料"})
    assert "allergies" not in profile.confirmed_fields
    task = agent.begin("u", "午餐", ["鸡肉饭"])
    assert task.state == TaskState.STOPPED
    assert task.stopped_reason == "allergies_unconfirmed"
    confirm(agent, changes={"allergies": []})
    assert agent.begin("u", "午餐", ["鸡肉饭"]).state == TaskState.AWAITING_CONFIRMATION


def test_concurrent_drafts_conflict_instead_of_overwrite(agent):
    confirm(agent)
    first = agent.preview_profile("u", {"budget": 40}, expected_version=1)
    second = agent.preview_profile("u", {"budget": 50}, expected_version=1)
    agent.confirm_profile("u", first.task_id, operation_key="first", expected_version=1)
    with pytest.raises(ToolError, match="version_conflict"):
        agent.confirm_profile("u", second.task_id, operation_key="second", expected_version=1)
    assert agent.harness.store.get_profile("u").budget == 40
    assert agent.harness.store.get_task(second.task_id).state == TaskState.AWAITING_CONFIRMATION
    assert len(agent.harness.store.list_profile_versions("u")) == 2


def test_cross_user_confirmation_and_cancellation_are_blocked(agent):
    draft = agent.preview_profile("owner", {"budget": 30}, expected_version=0)
    with pytest.raises(ToolError, match="profile_draft_not_found"):
        agent.confirm_profile("other", draft.task_id, operation_key="attack", expected_version=0)
    with pytest.raises(ToolError, match="profile_draft_not_found"):
        agent.cancel_profile("other", draft.task_id)
    assert agent.harness.store.get_profile("owner") is None


def test_same_operation_key_cannot_confirm_another_draft(agent):
    first = agent.preview_profile("u", {"budget": 30}, expected_version=0)
    agent.confirm_profile("u", first.task_id, operation_key="once", expected_version=0)
    second = agent.preview_profile("u", {"budget": 40}, expected_version=1)
    with pytest.raises(ToolError, match="operation_conflict"):
        agent.confirm_profile("u", second.task_id, operation_key="once", expected_version=1)


def test_confirmation_failure_rolls_back_profile_history_and_consents(agent, monkeypatch):
    draft = agent.preview_profile("u", {"allergies": []}, expected_version=0, consents={"review_history": True})
    store = agent.harness.store
    original = store.append_event
    def fail(event):
        if event.event_type == "profile.confirmed":
            raise RuntimeError("simulated interruption")
        original(event)
    monkeypatch.setattr(store, "append_event", fail)
    with pytest.raises(RuntimeError):
        agent.confirm_profile("u", draft.task_id, operation_key="retry", expected_version=0)
    assert store.get_profile("u") is None
    assert store.list_profile_versions("u") == []
    assert store.list_consent_events("u") == []
    monkeypatch.setattr(store, "append_event", original)
    assert agent.confirm_profile("u", draft.task_id, operation_key="retry", expected_version=0).version == 1


def test_noop_does_not_add_profile_version(agent):
    original = confirm(agent)
    unchanged = confirm(agent)
    assert unchanged == original
    assert len(agent.harness.store.list_profile_versions("u")) == 1


def test_profile_change_invalidates_candidates_but_not_feedback_history(agent):
    confirm(agent)
    old = agent.begin("u", "午餐", ["鸡肉饭"])
    confirm(agent, changes={"hard_avoids": ["鸡肉"]})
    with pytest.raises(ToolError, match="profile_changed"):
        agent.adopt(old.task_id)
    assert agent.harness.store.list_actions("u") == []
    refreshed = agent.harness.context(old.task_id, "午餐", ["鸡肉饭"])
    assert refreshed.state == TaskState.STOPPED
    task = agent.begin("u", "晚餐", ["番茄面"])
    agent.adopt(task.task_id)
    confirm(agent, changes={"budget": 20})
    agent.report(task.task_id, Execution.UNKNOWN)
    assert agent.harness.store.get_action(task.selected_action_id or task.candidates[0].action_id).context.profile_version == 2


def test_revoking_consent_blocks_cached_and_fresh_reviews_without_reading_history(agent, monkeypatch):
    confirm(agent, consents={"review_history": True})
    task = agent.begin("u", "午餐", ["鸡肉饭"])
    agent.adopt(task.task_id)
    agent.report(task.task_id, Execution.COMPLETE)
    assert agent.review(task.task_id)["completed"] == 1
    confirm(agent, changes={}, consents={"review_history": False})
    def no_read(*args):
        raise AssertionError("history must not be read after revocation")
    monkeypatch.setattr(agent.harness.store, "list_actions", no_read)
    with pytest.raises(ToolError, match="review_consent_required"):
        agent.review(task.task_id)
    from dietlens_mvp.tools import review
    with pytest.raises(ToolError, match="review_consent_required"):
        review(agent.harness.store, "u")
    events = agent.harness.store.list_consent_events("u")
    assert [e["granted"] for e in events if e["scope"] == "review_history"] == [True, False]


def test_consents_default_closed_and_scopes_are_independent(agent):
    profile = confirm(agent, consents={"history": True})
    assert profile.consents.get("history") is True
    assert not profile.consents.get("image_transfer", False)
    assert not profile.consents.get("review_history", False)
    assert not profile.consents.get("reminders", False)


@pytest.mark.parametrize("changes", [{"budget": -1}, {"budget": float("nan")}, {"budget": float("inf")}, {"budget": True}, {"allergies": "花生"}, {"version": 999}])
def test_invalid_profile_never_creates_version(agent, changes):
    with pytest.raises(ToolError):
        agent.preview_profile("u", changes, expected_version=0)
    assert agent.harness.store.get_profile("u") is None


def test_invalid_consent_never_becomes_truthy_permission(agent):
    with pytest.raises(ToolError, match="invalid_consents"):
        agent.preview_profile("u", {}, expected_version=0, consents={"review_history": "false"})


def test_reuse_profile_does_not_ask_budget_or_change_version(agent):
    original = confirm(agent)
    answers = iter(["u", ""])
    prompts = []
    def ask(prompt):
        prompts.append(prompt)
        return next(answers)
    assert initialize_user(agent, input_fn=ask, output_fn=lambda _: None) == "u"
    assert len(prompts) == 2
    assert agent.harness.store.get_profile("u") == original


def test_cli_initialization_cancel_and_confirm(agent):
    # ID, goal, budget, allergies, avoids, dislikes, four separate consents, final confirmation.
    initial = ["u", "少喝糖饮料", "30", "无", "猪肉", "香菜", "n", "n", "y", "n"]
    answers = iter([*initial, "n"])
    assert initialize_user(agent, input_fn=lambda _: next(answers), output_fn=lambda _: None) is None
    assert agent.harness.store.get_profile("u") is None
    answers = iter([*initial, "y"])
    assert initialize_user(agent, input_fn=lambda _: next(answers), output_fn=lambda _: None) == "u"
    saved = agent.harness.store.get_profile("u")
    assert saved.allergies == [] and "allergies" in saved.confirmed_fields
    assert saved.hard_avoids == ["猪肉"] and saved.dislikes == ["香菜"]
    assert saved.consents["review_history"] is True
    assert saved.consents["image_transfer"] is False


def test_draft_restart_and_confirmation_receipt_snapshot(tmp_path):
    path = str(tmp_path / "restart.db")
    store = SQLiteStore(path)
    agent = DietLensAgent(Harness(store))
    draft = agent.preview_profile("u", {"allergies": [], "budget": 30}, expected_version=0)
    store.close()
    store = SQLiteStore(path)
    agent = DietLensAgent(Harness(store))
    first = agent.confirm_profile("u", draft.task_id, operation_key="once", expected_version=0)
    confirm(agent, changes={"budget": 40})
    store.close()
    store = SQLiteStore(path)
    agent = DietLensAgent(Harness(store))
    replay = agent.confirm_profile("u", draft.task_id, operation_key="once", expected_version=0)
    assert asdict(replay) == asdict(first)
    assert store.get_profile("u").budget == 40
    assert len(store.list_profile_versions("u")) == 2
    store.close()


def test_legacy_profile_is_not_implicitly_confirmed(agent):
    from dietlens_mvp.models import Profile
    store = agent.harness.store
    store.put_profile(Profile(user_id="legacy", allergies=[]))
    assert agent.begin("legacy", "午餐", ["鸡肉饭"]).stopped_reason == "allergies_unconfirmed"
    profile = confirm(agent, user="legacy", changes={"allergies": []})
    assert profile.version == 2
    assert len(store.list_profile_versions("legacy")) == 2
    assert "allergies" not in store.list_profile_versions("legacy")[0].confirmed_fields


def test_profile_task_cannot_be_used_as_review_or_model_task(agent):
    profile = confirm(agent, consents={"review_history": True})
    draft = agent.preview_profile("u", {"budget": 40}, expected_version=profile.version)
    with pytest.raises(ToolError, match="model_task_not_supported"):
        agent.harness.interpret(draft.task_id, [])
    agent.confirm_profile("u", draft.task_id, operation_key=draft.task_id, expected_version=profile.version)
    with pytest.raises(ToolError, match="task_not_reviewable"):
        agent.review(draft.task_id)


def test_whitespace_is_not_a_confirmation_of_no_allergies(agent):
    with pytest.raises(ToolError, match="invalid_profile_terms"):
        agent.preview_profile("u", {"allergies": [" ", ""]}, expected_version=0)
