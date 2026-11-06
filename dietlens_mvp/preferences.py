"""Evidence-only preference signals; never writes profile fields by itself."""
from __future__ import annotations

from collections import defaultdict
import hashlib

from .models import Decision, Execution


def suggestions(store, user_id: str) -> list[dict]:
    groups = defaultdict(list)
    for action in store.list_actions(user_id):
        if action.decision == Decision.ADOPT:
            # Group by the user-facing meal/option context, not exact wording:
            # the four action dimensions intentionally phrase the same option
            # differently over time.
            option = action.context.options[0] if action.context and action.context.options else action.behavior
            groups[(action.context.meal if action.context else "", option)].append(action)
    result = []
    for (_, option), actions in groups.items():
        completed = sum(a.execution == Execution.COMPLETE for a in actions)
        barriers = sum(a.execution in {Execution.PARTIAL, Execution.NOT_DONE} for a in actions)
        if completed < 2 and barriers < 2:
            continue
        if completed >= 2:
            text = "你似乎多次愿意尝试这个做法，可以把它加入长期偏好吗？"
            signal = "repeatedly_completed"
        else:
            text = "这个做法似乎多次遇到阻碍，要不要调整它，而不是把原因归结为你不够努力？"
            signal = "repeated_barrier"
        behavior = actions[-1].behavior
        key = hashlib.sha1(f"{option}|{behavior}".encode()).hexdigest()[:12]
        result.append({"suggestion_id": key, "signal": signal, "text": text,
                       "evidence_count": len(actions), "behavior": behavior,
                       "requires_confirmation": True})
    return result
