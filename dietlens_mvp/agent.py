from __future__ import annotations

from .harness import Harness
from .models import Decision, Execution, Profile, Task
from .cleaning import clean_options, clean_text


class DietLensAgent:
    """Small intent layer; the Harness remains the authority on state and writes."""

    def __init__(self, harness: Harness | None = None) -> None:
        self.harness = harness or Harness()

    def preview_profile(self, user_id: str, changes: dict, *, expected_version: int, consents: dict | None = None):
        return self.harness.profiles.preview(user_id, changes, expected_version=expected_version, consents=consents)

    def confirm_profile(self, user_id: str, task_id: str, *, operation_key: str, expected_version: int) -> Profile:
        return self.harness.profiles.confirm(user_id, task_id, operation_key=operation_key, expected_version=expected_version)

    def cancel_profile(self, user_id: str, task_id: str) -> None:
        self.harness.profiles.cancel(user_id, task_id)

    def onboard(self, user_id: str, *, budget: float | None, allergies: list[str] | None = None,
                dislikes: list[str] | None = None, goal: str | None = None, consents: dict | None = None) -> Profile:
        """Trusted programmatic confirmation shortcut; interactive callers use preview/confirm."""
        user_id = clean_text(user_id)
        current = self.harness.store.get_profile(user_id)
        changes = {"budget": budget, "goal": goal}
        if allergies is not None:
            changes["allergies"] = allergies
            changes["allergy_status"] = "specified" if allergies else "none"
        if dislikes is not None:
            changes["dislikes"] = dislikes
        draft = self.preview_profile(user_id, changes, expected_version=current.version if current else 0, consents=consents)
        return self.confirm_profile(user_id, draft.task_id, operation_key=draft.task_id, expected_version=draft.expected_version)

    def begin(self, user_id: str, meal: str, options: list[str], *, operation_key: str | None = None) -> Task:
        return self.harness.start(user_id, clean_text(meal), clean_options(options), operation_key=operation_key)

    def adopt(self, task_id: str, action_index: int = 0) -> Task:
        return self.harness.decide(task_id, Decision.ADOPT, action_index)

    def skip(self, task_id: str, action_index: int = 0) -> Task:
        return self.harness.decide(task_id, Decision.SKIP, action_index)

    def report(self, task_id: str, execution: Execution, *, note: str = "") -> Task:
        return self.harness.feedback(task_id, execution, note=note)

    def correct_report(self, task_id: str, execution: Execution, *, note: str = "",
                       operation_key: str | None = None, expected_version: int | None = None) -> Task:
        return self.harness.correct_feedback(task_id, execution, note=note,
                                             operation_key=operation_key,
                                             expected_version=expected_version)

    def review(self, task_id: str) -> dict:
        return self.harness.finish_review(task_id)
