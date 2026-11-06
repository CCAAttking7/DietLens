import json

import pytest

from dietlens_mvp import DietLensAgent, Harness, InMemoryStore
from dietlens_mvp.errors import ToolError
from dietlens_mvp.model_provider import INTENT_SCHEMA, ModelResponse
from dietlens_mvp.model_router import TaskModelRouter


class SpyProvider:
    def __init__(self, name):
        self.model = name
        self.calls = 0
    def complete(self, messages, tools, response_schema):
        self.calls += 1
        return ModelResponse(json.dumps({"intent": "micro_action", "entities": {}, "missing_fields": ["meal"],
                                        "candidate_tool": "", "user_message": "请补充餐次", "confidence": 0}), model=self.model)


def test_different_tasks_use_configured_models_without_extra_calls():
    default = SpyProvider("default")
    context = SpyProvider("context-model")
    plan = SpyProvider("plan-model")
    review = SpyProvider("review-model")
    router = TaskModelRouter(default, {"context": context, "plan": plan, "review": review})
    for task in ("micro_action", "plan", "review", "food_search"):
        router.for_task(task).complete([], [], INTENT_SCHEMA)
    assert [p.calls for p in (default, context, plan, review)] == [1, 1, 1, 1]
    with pytest.raises(ToolError, match="model_task_not_supported"):
        router.for_task("profile_update")


def test_harness_uses_task_route_and_audits_actual_model():
    default, context = SpyProvider("default"), SpyProvider("context-model")
    store = InMemoryStore()
    agent = DietLensAgent(Harness(store, TaskModelRouter(default, {"context": context})))
    agent.onboard("u", budget=30, allergies=[])
    task = agent.harness.create_task("u")
    agent.harness.interpret(task.task_id, [])
    assert context.calls == 1 and default.calls == 0
    assert store.list_events(task.task_id)[-1].payload["model"] == "context-model"
    assert store.list_actions("u") == []


def test_router_failure_does_not_call_another_paid_model():
    class Offline(SpyProvider):
        def complete(self, *args):
            self.calls += 1
            raise OSError("offline")
    default, context = SpyProvider("default"), Offline("context-model")
    store = InMemoryStore()
    agent = DietLensAgent(Harness(store, TaskModelRouter(default, {"context": context})))
    agent.onboard("u", budget=30, allergies=[])
    task = agent.harness.create_task("u")
    result = agent.harness.interpret(task.task_id, [])
    assert result["confidence"] == 0
    assert context.calls == 1 and default.calls == 0
    assert store.list_events(task.task_id)[-1].payload["outcome"] == "manual_fallback"


def test_settings_builds_independent_routes_without_network(monkeypatch):
    from dietlens_mvp.config import Settings
    monkeypatch.setenv("DIETLENS_API_KEY", "test-only")
    monkeypatch.setenv("DIETLENS_MODEL", "base-model")
    monkeypatch.setenv("DIETLENS_MODEL_CONTEXT", "context-model")
    monkeypatch.setenv("DIETLENS_MODEL_PLAN", "reasoning-model")
    monkeypatch.setenv("DIETLENS_MODEL_REVIEW", "review-model")
    router = Settings.from_env().create_provider()
    assert router.for_task("micro_action").model == "context-model"
    assert router.for_task("plan").model == "reasoning-model"
    assert router.for_task("review").model == "review-model"
    assert router.for_task("food_search").model == "base-model"


def test_response_format_compatibility_is_independent_per_route(monkeypatch):
    from dietlens_mvp.config import Settings
    monkeypatch.setenv("DIETLENS_API_KEY", "test-only")
    monkeypatch.setenv("DIETLENS_MODEL", "base-model")
    monkeypatch.setenv("DIETLENS_MODEL_JSON_MODE", "false")
    monkeypatch.setenv("DIETLENS_MODEL_CONTEXT", "context-model")
    monkeypatch.setenv("DIETLENS_MODEL_CONTEXT_JSON_MODE", "true")
    router = Settings.from_env().create_provider()
    assert router.for_task("micro_action").json_mode is True
    assert router.for_task("plan").json_mode is False
