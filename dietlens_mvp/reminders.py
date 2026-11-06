"""Deterministic, opt-in reminder backoff for adopted actions."""
from __future__ import annotations

from datetime import datetime, timedelta, timezone

from .errors import ToolError
from .models import Action

BACKOFF = (timedelta(days=1), timedelta(days=3), timedelta(days=7), timedelta(days=14))


def next_reminder_at(action: Action) -> datetime | None:
    if action.decision is None or action.execution is not None:
        return None
    if action.reminder_count >= len(BACKOFF):
        return None
    anchor = action.last_reminded_at or action.created_at
    return anchor + BACKOFF[action.reminder_count]


def reminder_status(action: Action, *, at: datetime | None = None) -> dict:
    at = at or datetime.now(timezone.utc)
    due_at = next_reminder_at(action)
    return {"eligible": due_at is not None, "due": due_at is not None and at >= due_at,
            "next_at": due_at.isoformat() if due_at else None,
            "reminder_count": action.reminder_count}


def mark_reminded(action: Action, *, at: datetime | None = None) -> Action:
    at = at or datetime.now(timezone.utc)
    status = reminder_status(action, at=at)
    if not status["due"]:
        raise ToolError("reminder_not_due")
    action.last_reminded_at = at
    action.reminder_count += 1
    return action
