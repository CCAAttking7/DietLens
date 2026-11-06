from dietlens_mvp import DietLensAgent
from dietlens_mvp.models import Execution
from dietlens_mvp.preferences import suggestions


def test_preference_signal_requires_repeated_evidence_and_never_writes_profile():
    agent = DietLensAgent()
    profile = agent.onboard("u", budget=30, allergies=[], consents={"review_history": True})
    for _ in range(2):
        task = agent.begin("u", "午餐", ["鸡肉饭"])
        agent.adopt(task.task_id)
        agent.report(task.task_id, Execution.COMPLETE)
    result = suggestions(agent.harness.store, "u")
    assert result[0]["requires_confirmation"] is True
    assert result[0]["signal"] == "repeatedly_completed"
    assert agent.harness.store.get_profile("u").version == profile.version


def test_barriers_produce_adjustment_signal_without_negative_label():
    agent = DietLensAgent()
    agent.onboard("u", budget=30, allergies=[], consents={"review_history": True})
    for _ in range(2):
        task = agent.begin("u", "午餐", ["鸡肉饭"])
        agent.adopt(task.task_id)
        agent.report(task.task_id, Execution.NOT_DONE)
    result = suggestions(agent.harness.store, "u")
    assert result[0]["signal"] == "repeated_barrier"
    assert "失败" not in result[0]["text"]
