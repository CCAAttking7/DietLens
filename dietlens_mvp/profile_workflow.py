"""Deterministic profile workflow owned by Harness; no model output is persisted here."""
from copy import deepcopy
from dataclasses import asdict
from datetime import datetime, timezone
import math
from typing import TYPE_CHECKING

from .cleaning import clean_terms, clean_text
from .errors import ToolError
from .models import Profile, ProfileDraft, Task, TaskState

if TYPE_CHECKING:
    from .harness import Harness

CONSENT_SCOPES = ("history", "image_transfer", "review_history", "reminders")
PROFILE_FIELDS = ("goal", "budget", "allergies", "hard_avoids", "dislikes")


class ProfileWorkflow:
    def __init__(self, harness: "Harness") -> None:
        self.harness = harness
        self.store = harness.store

    def preview(self, user_id: str, changes: dict, *, expected_version: int,
                consents: dict | None = None) -> ProfileDraft:
        if not isinstance(user_id, str) or not clean_text(user_id):
            raise ToolError("invalid_user_id")
        user_id = clean_text(user_id)
        if type(expected_version) is not int or expected_version < 0:
            raise ToolError("invalid_profile_version")
        if not isinstance(changes, dict) or set(changes) - set(PROFILE_FIELDS):
            raise ToolError("invalid_profile_fields")
        if consents is not None and (not isinstance(consents, dict) or set(consents) - set(CONSENT_SCOPES) or any(type(v) is not bool for v in consents.values())):
            raise ToolError("invalid_consents")
        with self.store.transaction():
            previous = self.store.get_profile(user_id)
            if (previous.version if previous else 0) != expected_version:
                raise ToolError("version_conflict")
            proposed = deepcopy(previous) if previous else Profile(user_id=user_id)
            diff = {}
            for name, raw in changes.items():
                value = self._clean_field(name, raw)
                before = getattr(proposed, name)
                if value != before or name not in proposed.confirmed_fields or proposed.field_sources.get(name) != "user_confirmation":
                    diff[name] = {"before": before if previous else None, "after": value}
                setattr(proposed, name, value)
                if name not in proposed.confirmed_fields:
                    proposed.confirmed_fields.append(name)
                proposed.field_sources[name] = "user_confirmation"
            for scope, granted in (consents or {}).items():
                if proposed.consents.get(scope) != granted:
                    diff[f"consents.{scope}"] = {"before": proposed.consents.get(scope), "after": granted}
                proposed.consents[scope] = granted
                proposed.field_sources[f"consents.{scope}"] = "user_confirmation"
            proposed.version = expected_version + 1 if diff or previous is None else expected_version
            task = Task(user_id=user_id, task_type="profile_update")
            self.store.save_task(task)
            self.harness._event(task, "task.created", {"state": task.state.value, "task_type": task.task_type})
            draft = ProfileDraft(task.task_id, user_id, expected_version, proposed, diff)
            self.store.save_profile_draft(draft)
            self.harness._transition(task, TaskState.AWAITING_CONFIRMATION)
            self.harness._event(task, "profile.previewed", {"fields": sorted(diff), "expected_version": expected_version})
            self.store.save_task(task)
            return draft

    @staticmethod
    def _clean_field(name: str, value):
        if name == "budget":
            if value is not None and (type(value) not in (int, float) or not math.isfinite(value) or value < 0):
                raise ToolError("invalid_budget")
            return value
        if name == "goal":
            if value is not None and not isinstance(value, str):
                raise ToolError("invalid_goal")
            return clean_text(value) or None if value is not None else None
        if not isinstance(value, list) or any(not isinstance(v, str) for v in value):
            raise ToolError("invalid_profile_terms")
        cleaned = clean_terms(value)
        if value and not cleaned and name in {"allergies", "hard_avoids"}:
            raise ToolError("invalid_profile_terms")
        return cleaned

    def _owned(self, user_id: str, task_id: str) -> tuple[Task, ProfileDraft]:
        task = self.harness._task(task_id)
        draft = self.store.get_profile_draft(task_id)
        if task.user_id != user_id or draft is None or draft.user_id != user_id or task.task_type != "profile_update":
            raise ToolError("profile_draft_not_found")
        return task, draft

    def confirm(self, user_id: str, task_id: str, *, operation_key: str, expected_version: int) -> Profile:
        if not isinstance(operation_key, str) or not operation_key.strip():
            raise ToolError("operation_key_required")
        with self.harness._operation(task_id):
            task, draft = self._owned(user_id, task_id)
            request = {"kind": "profile_confirm", "task_id": task_id, "expected_version": expected_version}
            key = f"profile:{user_id}:{operation_key}"
            receipt = self.harness._receipt(key, request)
            if receipt:
                return Profile(**receipt["profile"])
            if task.state != TaskState.AWAITING_CONFIRMATION:
                raise ToolError("profile_not_awaiting_confirmation")
            if type(expected_version) is not int or expected_version != draft.expected_version:
                raise ToolError("version_conflict")
            self.harness._guard(task)
            result = self.harness._invoke(task, "save_profile", {}, confirmed=True)
            profile = self.store.get_profile(user_id)
            self.harness._event(task, "profile.confirmed", {"profile_version": result["profile_version"], "fields": sorted(draft.changes)}, key)
            self.harness._transition(task, TaskState.DONE, key)
            self.store.save_task(task)
            self.store.save_receipt(key, {"request": request, "profile": asdict(profile)})
            return profile

    def write_confirmed(self) -> dict:
        task = self.harness._active_task
        task, draft = self._owned(task.user_id, task.task_id)
        if task.state != TaskState.AWAITING_CONFIRMATION:
            raise ToolError("confirmation_required")
        previous = self.store.get_profile(task.user_id)
        if (previous.version if previous else 0) != draft.expected_version:
            raise ToolError("version_conflict")
        if previous is not None and not draft.changes:
            return {"profile_version": previous.version}
        proposed = deepcopy(draft.proposed)
        now = datetime.now(timezone.utc).isoformat()
        proposed.created_at = previous.created_at if previous else now
        proposed.updated_at = now
        # All writes are within Harness's confirmation transaction.
        self.store.put_profile_version(proposed, draft.expected_version, task.task_id, f"{task.task_id}:profile")
        return {"profile_version": proposed.version}

    def cancel(self, user_id: str, task_id: str) -> None:
        with self.harness._operation(task_id):
            task, _ = self._owned(user_id, task_id)
            if task.state == TaskState.CANCELLED:
                return
            if task.state != TaskState.AWAITING_CONFIRMATION:
                raise ToolError("profile_not_awaiting_confirmation")
            self.harness._transition(task, TaskState.CANCELLED)
            self.harness._event(task, "profile.cancelled", {})
            self.store.save_task(task)
