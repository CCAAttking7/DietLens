from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any
from uuid import uuid4


class TaskState(str, Enum):
    CREATED = "created"
    CONTEXT = "context"
    CANDIDATES = "candidates"
    AWAITING_CONFIRMATION = "awaiting_confirmation"
    ADOPTED = "adopted"
    FEEDBACK = "feedback"
    REVIEW = "review"
    DONE = "done"
    STOPPED = "stopped"
    CANCELLED = "cancelled"


class CareState(str, Enum):
    """User-facing accompaniment state, separate from write/task state."""
    WELCOME = "welcome"
    LISTENING = "listening"
    CHECKING = "checking"
    OFFERING = "offering"
    AWAITING_FEEDBACK = "awaiting_feedback"
    REFLECTING = "reflecting"
    RECORDING = "recording"


class Decision(str, Enum):
    ADOPT = "adopt"
    SKIP = "skip"
    REPLACE = "replace"


class Execution(str, Enum):
    COMPLETE = "complete"
    PARTIAL = "partial"
    NOT_DONE = "not_done"
    UNKNOWN = "unknown"


@dataclass
class Profile:
    user_id: str
    budget: float | None = None
    dislikes: list[str] = field(default_factory=list)
    allergies: list[str] = field(default_factory=list)
    goal: str | None = None
    version: int = 1
    hard_avoids: list[str] = field(default_factory=list)
    confirmed_fields: list[str] = field(default_factory=list)
    field_sources: dict[str, str] = field(default_factory=dict)
    consents: dict[str, bool] = field(default_factory=dict)
    created_at: str | None = None
    updated_at: str | None = None


@dataclass
class FoodObservation:
    observation_id: str
    user_id: str
    task_id: str | None
    record: dict[str, Any]
    status: str
    unknown_fields: list[str] = field(default_factory=list)
    created_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())


@dataclass
class PlanItem:
    item_id: str
    meal_date: str
    meal_slot: str
    name: str
    ingredient_id: str
    quantity: float
    unit: str
    servings: int = 1
    source: str = "user_confirmed"
    ingredient_name: str = ""


@dataclass
class Plan:
    plan_id: str
    user_id: str
    start_date: str
    days: int
    servings: int
    version: int
    status: str
    items: list[PlanItem] = field(default_factory=list)
    created_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    updated_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    task_id: str | None = None


@dataclass
class ShoppingListItem:
    item_id: str
    ingredient_id: str
    name: str
    quantity: float
    unit: str
    needed: float
    purchased: float = 0


@dataclass
class ShoppingList:
    list_id: str
    user_id: str
    plan_id: str
    plan_version: int
    status: str
    items: list[ShoppingListItem] = field(default_factory=list)
    created_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    updated_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())


@dataclass
class InventoryItem:
    inventory_id: str
    user_id: str
    ingredient_id: str
    name: str
    quantity: float
    unit: str
    version: int = 1
    updated_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())


@dataclass
class MealRecord:
    """A user-confirmed account of food actually eaten.

    This is intentionally separate from PlanItem.  ``quantity=None`` means
    unknown and is never treated as zero; ``status=deleted`` keeps the audit
    version while excluding the record from current reviews.
    """

    record_id: str
    user_id: str
    meal_date: str
    meal_slot: str
    name: str
    ingredient_id: str = ""
    quantity: float | None = None
    unit: str | None = None
    eaten_at: str | None = None
    source: str = "user_self_report"
    plan_id: str | None = None
    plan_item_id: str | None = None
    status: str = "active"
    version: int = 1
    created_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    updated_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())


@dataclass
class ProfileDraft:
    task_id: str
    user_id: str
    expected_version: int
    proposed: Profile
    changes: dict[str, Any]


@dataclass
class Context:
    user_id: str
    meal: str
    options: list[str]
    budget: float | None
    allergies: list[str]
    dislikes: list[str]
    source: str = "user_self_report"
    profile_version: int = 1
    allergies_confirmed: bool = False
    hard_avoids: list[str] = field(default_factory=list)


@dataclass
class Action:
    action_id: str
    user_id: str
    context: Context
    cue: str
    behavior: str
    effort: str
    rationale: str
    dimension: str = "substitution"
    decision: Decision | None = None
    execution: Execution | None = None
    action_version: int = 1
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    feedback_history: list[dict[str, Any]] = field(default_factory=list)
    cooldown_until: datetime | None = None
    reminder_count: int = 0
    last_reminded_at: datetime | None = None


@dataclass
class Event:
    event_type: str
    task_id: str
    user_id: str
    payload: dict[str, Any]
    operation_key: str | None = None
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


@dataclass
class Task:
    task_id: str = field(default_factory=lambda: str(uuid4()))
    user_id: str = ""
    state: TaskState = TaskState.CREATED
    context: Context | None = None
    candidates: list[Action] = field(default_factory=list)
    selected_action_id: str | None = None
    iteration: int = 0
    tool_calls: int = 0
    budget_units: int = 10
    messages: list[dict[str, str]] = field(default_factory=list)
    stopped_reason: str | None = None
    version: int = 1
    created_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    updated_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    model_calls: int = 0
    task_type: str = "micro_action"
    care_state: CareState = CareState.WELCOME
    # A pending cross-flow draft, such as a quick meal log, stays behind the
    # same task confirmation boundary as micro-actions.
    pending_record: dict[str, Any] | None = None
    linked_objects: dict[str, Any] = field(default_factory=dict)
