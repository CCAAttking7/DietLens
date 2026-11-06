"""Explicit user data export and deletion boundary."""
from __future__ import annotations

import json

from .errors import ToolError
from .serialization import dumps


class DataPortabilityService:
    def __init__(self, store):
        self.store = store

    def export(self, user_id: str) -> dict:
        profile = self.store.get_profile(user_id)
        if profile is None:
            raise ToolError("profile_not_found")
        tasks = self.store.list_tasks(user_id)
        return json.loads(dumps({
            "export_version": "1",
            "user_id": user_id,
            "profile": profile,
            "profile_versions": self.store.list_profile_versions(user_id),
            "consent_events": self.store.list_consent_events(user_id),
            "tasks": tasks,
            "events": [event for task in tasks for event in self.store.list_events(task.task_id)],
            "actions": self.store.list_actions(user_id),
            "food_observations": self.store.list_food_observations(user_id),
            "plans": self.store.list_plans(user_id),
            "shopping_lists": [item for plan in self.store.list_plans(user_id) for item in self.store.list_shopping_lists(plan.plan_id)],
            "inventory": self.store.list_inventory(user_id),
            "meal_records": self.store.list_meal_records(user_id, include_deleted=True),
        }))

    def delete(self, user_id: str, *, confirmed: bool) -> dict:
        if not confirmed:
            raise ToolError("delete_confirmation_required")
        return self.store.delete_user_data(user_id)
