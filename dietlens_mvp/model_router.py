"""Explicit task routing; no prompt-driven provider selection or hidden paid fallback."""
from .errors import ToolError
from .model_provider import ModelProvider

TASK_ROUTES = {"micro_action": "context", "context": "context", "food_search": "food",
               "menu_recommendation": "food", "plan": "plan", "review": "review"}


class TaskModelRouter:
    def __init__(self, default: ModelProvider, routes: dict[str, ModelProvider]) -> None:
        if set(routes) - set(TASK_ROUTES.values()):
            raise ValueError("unknown_model_route")
        self.default = default
        self.routes = dict(routes)

    def for_task(self, task_type: str) -> ModelProvider:
        if task_type not in TASK_ROUTES:
            raise ToolError("model_task_not_supported")
        return self.routes.get(TASK_ROUTES[task_type], self.default)

    def complete(self, messages: list[dict], tools: list[dict], response_schema: dict):
        return self.default.complete(messages, tools, response_schema)
