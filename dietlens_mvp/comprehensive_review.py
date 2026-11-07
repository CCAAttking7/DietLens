"""Bounded, deterministic review for the product workbench."""
from __future__ import annotations

from datetime import date, datetime, time, timedelta, timezone

from .errors import ToolError
from .models import Decision, Execution


def _ratio(numerator: int, denominator: int) -> dict:
    return {"numerator": numerator, "denominator": denominator,
            "value": (numerator / denominator if denominator else None),
            "status": "ok" if denominator else "not_applicable"}


def _execution_as_of(action, end: date):
    """Freeze feedback at the period boundary; later feedback is next-period data."""
    cutoff = datetime.combine(end, time.max, tzinfo=timezone.utc)
    history = []
    for item in action.feedback_history:
        try:
            timestamp = datetime.fromisoformat(item["recorded_at"])
            if timestamp <= cutoff:
                history.append((timestamp, item.get("execution")))
        except (KeyError, TypeError, ValueError):
            continue
    if history:
        history.sort(key=lambda item: item[0])
        return history[-1][1]
    if action.created_at <= cutoff and not action.feedback_history:
        return action.execution.value if action.execution else None
    return None


def resolve_period(period: str = "week", anchor_date: str | None = None) -> tuple[date, date]:
    anchor = date.fromisoformat(anchor_date) if anchor_date else datetime.now(timezone.utc).date()
    if period == "day":
        return anchor, anchor
    if period == "month":
        start = anchor.replace(day=1)
        next_month = (start.replace(day=28) + timedelta(days=4)).replace(day=1)
        return start, next_month - timedelta(days=1)
    if period == "week":
        start = anchor - timedelta(days=anchor.weekday())
        return start, start + timedelta(days=6)
    raise ToolError("invalid_review_period")


class ComprehensiveReviewService:
    def __init__(self, store):
        self.store = store

    def generate(self, user_id: str, *, period: str = "week", anchor_date: str | None = None) -> dict:
        profile = self.store.get_profile(user_id)
        if profile is None or not profile.consents.get("review_history", False):
            raise ToolError("review_consent_required")
        start, end = resolve_period(period, anchor_date)

        plans = [plan for plan in self.store.list_plans(user_id) if plan.status == "confirmed"]
        planned_items = [item for plan in plans for item in plan.items
                         if start <= date.fromisoformat(item.meal_date) <= end]
        records = [record for record in self.store.list_meal_records(user_id)
                   if start <= date.fromisoformat(record.meal_date) <= end]
        actions = [action for action in self.store.list_actions(user_id)
                   if start <= action.created_at.date() <= end]
        adopted = [action for action in actions if action.decision == Decision.ADOPT]
        effective = {action.action_id: _execution_as_of(action, end) for action in adopted}
        feedback = [action for action in adopted if effective[action.action_id] in {Execution.COMPLETE.value, Execution.PARTIAL.value, Execution.NOT_DONE.value}]
        completed = [action for action in feedback if effective[action.action_id] == Execution.COMPLETE.value]
        unknown_action_feedback = [action for action in adopted if effective[action.action_id] in {None, Execution.UNKNOWN.value}]

        links = {
            "plan_ids": sorted({plan.plan_id for plan in plans if any(item in planned_items for item in plan.items)}),
            "meal_record_ids": [record.record_id for record in records],
            "action_ids": [action.action_id for action in actions],
        }
        slot_order = {"早餐": 0, "早午餐": 1, "午餐": 2, "下午茶": 3, "晚餐": 4, "夜宵": 5}
        timeline_map = {}
        for item in planned_items:
            key = (item.meal_date, item.meal_slot)
            entry = timeline_map.setdefault(key, {"date": item.meal_date, "slot": item.meal_slot,
                                                  "planned": [], "recorded": [], "status": "planned"})
            entry["planned"].append({"item_id": item.item_id, "name": item.name, "quantity": item.quantity,
                                     "unit": item.unit, "plan_id": next(plan.plan_id for plan in plans if item in plan.items)})
        for record in records:
            key = (record.meal_date, record.meal_slot)
            entry = timeline_map.setdefault(key, {"date": record.meal_date, "slot": record.meal_slot,
                                                  "planned": [], "recorded": [], "status": "recorded"})
            entry["recorded"].append({"record_id": record.record_id, "name": record.name,
                                      "quantity": record.quantity, "unit": record.unit,
                                      "plan_id": record.plan_id, "plan_item_id": record.plan_item_id})
        timeline = sorted(timeline_map.values(), key=lambda item: (item["date"], slot_order.get(item["slot"], 99)))
        for entry in timeline:
            if entry["planned"] and entry["recorded"]:
                linked_ids = {record.get("plan_item_id") for record in entry["recorded"] if record.get("plan_item_id")}
                entry["status"] = "matched" if any(item["item_id"] in linked_ids for item in entry["planned"]) else "same_slot"
            elif entry["recorded"]:
                entry["status"] = "unplanned"
        matched_plan_item_ids = {record.plan_item_id for record in records if record.plan_item_id}
        matched_planned = sum(item.item_id in matched_plan_item_ids for item in planned_items)
        same_slot_records = sum(1 for entry in timeline if entry["status"] == "same_slot")
        unplanned_records = sum(1 for entry in timeline if entry["status"] == "unplanned")
        unmatched_planned = len(planned_items) - matched_planned
        unknowns = []
        if not records:
            unknowns.append({"kind": "meal_record", "count": 0, "message": "没有实际餐食记录；这不代表没有用餐。"})
        unknown_quantity = sum(record.quantity is None for record in records)
        if unknown_quantity:
            unknowns.append({"kind": "quantity", "count": unknown_quantity, "message": "有些份量未知，未按零计算。"})
        if unknown_action_feedback:
            unknowns.append({"kind": "action_feedback", "count": len(unknown_action_feedback), "message": "有些行动还没有反馈，不计作完成或失败。"})

        insights = []
        if planned_items and unmatched_planned == len(planned_items):
            insights.append({"kind": "plan_gap", "tone": "gentle", "title": "计划还没有遇到真实的一餐",
                             "body": "这不代表计划失败，只说明目前还缺少实际记录。下一次愿意的话，记下一餐就能让计划和生活重新对上。",
                             "evidence": f"已安排 {len(planned_items)} 餐，实际记录 0 餐"})
        elif planned_items and unmatched_planned:
            insights.append({"kind": "plan_gap", "tone": "warm", "title": "有些安排没有被记录下来",
                             "body": "可以先看看是时间、食材，还是临时变化让它没有发生；不需要为了补齐数字而回填。",
                             "evidence": f"已明确关联 {matched_planned} / {len(planned_items)} 餐；另有 {same_slot_records} 条同餐次记录待核对"})
        elif unplanned_records and planned_items:
            insights.append({"kind": "unplanned", "tone": "blue", "title": "生活里出现了计划之外的选择",
                             "body": "这些记录不是偏离，而是帮助下一次计划更贴近真实节奏的线索。",
                             "evidence": f"有 {unplanned_records} 条计划外记录；计划项按明确关联单独核对"})
        if unknown_quantity:
            insights.append({"kind": "unknown_quantity", "tone": "quiet", "title": "份量仍然留有余地",
                             "body": "份量未知不会被当成零，也不影响先看餐次和节奏。以后想补充时，只需要改这一项。",
                             "evidence": f"{unknown_quantity} 条记录没有份量"})
        barrier_actions = [action for action in adopted if effective[action.action_id] in {Execution.PARTIAL.value, Execution.NOT_DONE.value}]
        completed_actions = [action for action in adopted if effective[action.action_id] == Execution.COMPLETE.value]
        barrier_groups = {}
        for action in barrier_actions:
            option = action.selected_option
            if not option:
                continue
            key = (action.context.meal if action.context else "", option)
            barrier_groups[key] = barrier_groups.get(key, 0) + 1
        repeated_barriers = max(barrier_groups.values(), default=0)
        if repeated_barriers >= 2:
            insights.append({"kind": "barrier", "tone": "warm", "title": "同一类小行动反复遇到阻碍",
                             "body": "下一步可以调整行动的大小、触发时机或环境，而不是把原因归结为自控力。",
                             "evidence": f"同一餐食情境有 {repeated_barriers} 次反馈显示部分完成或未完成"})
        if len(completed_actions) >= 2:
            insights.append({"kind": "preference", "tone": "green", "title": "有做法已经被生活验证过",
                             "body": "这些行动曾被你完成多次，可以考虑把它们列为愿意继续尝试的选项；系统不会自动把它们当成长期偏好。",
                             "evidence": f"{len(completed_actions)} 次反馈显示完成"})

        next_steps = []
        if planned_items and unmatched_planned:
            next_steps.append("如果你愿意，可以先记录一餐；不需要补齐过去的每一餐。")
        if unknown_action_feedback:
            next_steps.append("可以在方便时补充一次行动反馈，也可以保持未知。")
        if not next_steps:
            next_steps.append("继续按你愿意的节奏记录；下一次可以从一个最容易执行的小改变开始。")

        return {
            "period": {"kind": period, "start": start.isoformat(), "end": end.isoformat()},
            "source": "deterministic_template",
            "model_failure_tolerant": True,
            "plan": {"planned_meals": len(planned_items), "matched_meals": matched_planned,
                     "unmatched_meals": unmatched_planned, "same_slot_records": same_slot_records,
                     "unplanned_records": unplanned_records, "plans": len(links["plan_ids"]), "items": [
                {"item_id": item.item_id, "date": item.meal_date, "slot": item.meal_slot, "name": item.name,
                 "plan_id": next(plan.plan_id for plan in plans if item in plan.items)} for item in planned_items]},
            "actual": {"recorded_meals": len(records), "records": [
                {"record_id": record.record_id, "date": record.meal_date, "slot": record.meal_slot,
                 "name": record.name, "quantity": record.quantity, "unit": record.unit,
                 "source": record.source, "plan_id": record.plan_id, "plan_item_id": record.plan_item_id} for record in records],
                "coverage": _ratio(matched_planned, len(planned_items))},
            "timeline": timeline,
            "nutrition": {"known": 0, "unknown": len(records), "coverage": {
                "numerator": 0, "denominator": len(records), "value": None,
                "status": "unknown" if records else "not_applicable"},
                          "message": "当前记录没有足够的可核验营养数据，未生成营养结论。"},
            "actions": {"adopted": len(adopted), "feedback_received": len(feedback), "completed": len(completed),
                        "feedback_coverage": _ratio(len(feedback), len(adopted)),
                        "completion_among_feedback": _ratio(len(completed), len(feedback))},
            "north_star": {"name": "用户主动留下的有效记录", "value": len(records), "unit": "meal_records",
                           "numerator": len(records), "denominator": None},
            "unknowns": unknowns,
            "insights": insights,
            "next_steps": next_steps,
            "links": links,
        }
