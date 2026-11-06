from __future__ import annotations

import hashlib
from dataclasses import asdict
from datetime import datetime, timedelta, timezone
from typing import Callable

from .models import Action, Context, Decision, Event, Execution, Profile
from .repository import Repository
from .errors import ToolError


def build_context(store: Repository, user_id: str, meal: str, options: list[str]) -> Context:
    profile = store.get_profile(user_id)
    if not profile:
        raise ToolError("profile_not_found")
    return Context(user_id, meal, options, profile.budget, profile.allergies, profile.dislikes, profile_version=profile.version, allergies_confirmed="allergies" in profile.confirmed_fields, hard_avoids=profile.hard_avoids)


def _contains(text: str, terms: list[str]) -> bool:
    return any(term.lower() in text.lower() for term in terms)


def filter_options(context: Context) -> list[str]:
    if not context.allergies_confirmed:
        return []
    safe = []
    for option in context.options:
        if _contains(option, context.allergies + context.hard_avoids):
            continue
        safe.append(option)
    return safe


def generate_actions(context: Context, options: list[str], prior_actions: list[Action] | None = None) -> list[Action]:
    if not options:
        return []
    prior_actions = prior_actions or []
    now = datetime.now(timezone.utc)
    cooled = {option for a in prior_actions if a.context and a.context.meal == context.meal
              and a.execution in {Execution.PARTIAL, Execution.NOT_DONE}
              and (a.cooldown_until is None or a.cooldown_until > now)
              for option in context.options if f"选择{option}" in a.behavior}
    if len(options) > 1:
        options = sorted(options, key=lambda option: option in cooled)
    dimensions = ("substitution", "add_on", "sequence", "timing")
    used_dimensions = {a.dimension for a in prior_actions if a.context and a.context.meal == context.meal}
    dimension = next((item for item in dimensions if item not in used_dimensions), dimensions[0])
    chosen = options[0]
    copy = {
        "substitution": (f"选择{chosen}，并把饮料换成无糖或白水", "保留当前餐食，只调整一个维度；已按餐名排除明确过敏/忌口词，配料仍需核对。", "低：只改变饮品"),
        "add_on": (f"选择{chosen}时，顺手加一份蔬菜或水果", "在原有选择上加一个容易执行的小动作，不要求改变整餐。", "低：只增加一项"),
        "sequence": (f"选择{chosen}后，先吃蔬菜和蛋白质，再吃主食", "通过进食顺序降低一次性改变整餐的负担。", "低：只改变顺序"),
        "timing": (f"准备{context.meal}前先喝几口水，前几口慢一点", "把注意力放回进食节奏，不把一次结果当成能力评价。", "低：只改变节奏"),
    }
    behavior, rationale, effort = copy[dimension]
    actions = [Action(
        action_id=f"act-{hashlib.sha1(f'{context.user_id}|{context.meal}|{chosen}'.encode()).hexdigest()[:10]}",
        user_id=context.user_id,
        context=context,
        cue=f"当你准备{context.meal}时",
        behavior=behavior,
        effort=effort,
        rationale=rationale,
        dimension=dimension,
    )]
    if len(options) > 1:
        alt = options[1]
        alternative_dimension = dimensions[(dimensions.index(dimension) + 1) % len(dimensions)]
        alt_copy = {
            "substitution": (f"选择{alt}，饮料优先选无糖或白水", "这是同一情境下的可替换候选，需由你选择是否尝试。", "低：只改变饮品"),
            "add_on": (f"选择{alt}时，加一份蔬菜或水果", "这是同一情境下的可替换候选，需由你选择是否尝试。", "低：只增加一项"),
            "sequence": (f"选择{alt}后，先吃蔬菜和蛋白质，再吃主食", "这是同一情境下的可替换候选，需由你选择是否尝试。", "低：只改变顺序"),
            "timing": (f"准备{context.meal}前先喝几口水，前几口慢一点", "这是同一情境下的可替换候选，需由你选择是否尝试。", "低：只改变节奏"),
        }
        alt_behavior, alt_rationale, alt_effort = alt_copy[alternative_dimension]
        actions.append(Action(
            action_id=f"act-{hashlib.sha1(f'{context.user_id}|{context.meal}|{alt}'.encode()).hexdigest()[:10]}",
            user_id=context.user_id,
            context=context,
            cue=f"当你准备{context.meal}时",
            behavior=alt_behavior,
            effort=alt_effort,
            rationale=alt_rationale,
            dimension=alternative_dimension,
        ))
    return actions


def save_decision(store: Repository, action: Action, decision: Decision, task_id: str) -> Action:
    if decision == Decision.ADOPT:
        action.decision = Decision.ADOPT
        action.execution = None
    elif decision == Decision.SKIP:
        action.decision = Decision.SKIP
        action.execution = None
    else:
        raise ToolError("unsupported_decision")
    return store.save_action(action, f"{task_id}:decision:{action.action_id}:{decision.value}")


def save_feedback(store: Repository, action_id: str, execution: Execution, task_id: str, note: str = "") -> Action:
    action = store.get_action(action_id)
    if not action or action.decision != Decision.ADOPT:
        raise ToolError("action_not_adopted")
    action.feedback_history = [*action.feedback_history, {
        "execution": execution.value,
        "note": note.strip()[:1000],
        "version": action.action_version + 1,
        "recorded_at": datetime.now(timezone.utc).isoformat(),
    }]
    action.execution = execution
    if execution == Execution.NOT_DONE:
        action.cooldown_until = datetime.now(timezone.utc) + timedelta(days=7)
    elif execution == Execution.PARTIAL:
        action.cooldown_until = datetime.now(timezone.utc) + timedelta(days=3)
    else:
        action.cooldown_until = None
    action.action_version += 1
    return store.save_action(action, f"{task_id}:feedback:{action_id}:{action.action_version}")


def review(store: Repository, user_id: str) -> dict:
    profile = store.get_profile(user_id)
    if profile is None or not profile.consents.get("review_history", False):
        raise ToolError("review_consent_required")
    actions = [a for a in store.list_actions(user_id) if a.user_id == user_id]
    adopted = [a for a in actions if a.decision == Decision.ADOPT]
    completed = [a for a in adopted if a.execution == Execution.COMPLETE]
    feedback = [a for a in adopted if a.execution in {Execution.COMPLETE, Execution.PARTIAL, Execution.NOT_DONE}]
    revision = hashlib.sha1("|".join(f"{a.action_id}:{a.action_version}:{a.execution.value if a.execution else ''}" for a in actions).encode()).hexdigest()
    return {
        "adopted": len(adopted),
        "completed": len(completed),
        "feedback_coverage": (len(feedback) / len(adopted) if adopted else None),
        "revision": revision,
        "actions": [asdict(a) for a in actions],
    }
