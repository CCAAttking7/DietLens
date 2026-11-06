"""Deterministic plan, shopping-list, and inventory services."""
from __future__ import annotations

from collections import defaultdict
from copy import deepcopy
from datetime import date, timedelta
import math
from uuid import uuid4

from .errors import ToolError
from .models import InventoryItem, Plan, PlanItem, ShoppingList, ShoppingListItem

MEAL_SLOTS = {"早餐", "午餐", "晚餐", "breakfast", "lunch", "dinner"}
UNITS = {"g", "kg", "ml", "l", "个", "份", "件", "包", "瓶"}


def _quantity(value: object) -> float:
    if type(value) not in (int, float) or not math.isfinite(value) or value < 0:
        raise ToolError("invalid_quantity")
    return float(value)


def validate_plan(start_date: str, days: int, servings: int, items: list[PlanItem]) -> None:
    try:
        first = date.fromisoformat(start_date)
    except ValueError as exc:
        raise ToolError("invalid_plan_date") from exc
    if days not in (1, 7) or type(servings) is not int or not 1 <= servings <= 20:
        raise ToolError("invalid_plan_shape")
    if not 1 <= len(items) <= days * 3:
        raise ToolError("meal_count_mismatch")
    expected_dates = {(first + timedelta(days=i)).isoformat() for i in range(days)}
    seen: set[tuple[str, str]] = set()
    for item in items:
        if item.meal_date not in expected_dates or item.meal_slot not in MEAL_SLOTS:
            raise ToolError("invalid_plan_meal")
        if (item.meal_date, item.meal_slot) in seen:
            raise ToolError("duplicate_plan_meal")
        seen.add((item.meal_date, item.meal_slot))
        if not item.name.strip() or not item.ingredient_id.strip() or item.unit not in UNITS:
            raise ToolError("invalid_plan_item")
        _quantity(item.quantity)
    # Unfilled slots remain unplanned; do not invent meals for completeness.


class PlanningService:
    def __init__(self, store):
        self.store = store

    def preview(self, user_id: str, *, start_date: str, days: int, servings: int, items: list[PlanItem], plan_id: str | None = None) -> Plan:
        validate_plan(start_date, days, servings, items)
        plan = Plan(plan_id or str(uuid4()), user_id, start_date, days, servings, 1, "draft", deepcopy(items))
        return self.store.save_plan(plan)

    def confirm(self, plan_id: str, *, operation_key: str | None = None) -> Plan:
        with self.store.transaction():
            return self._confirm(plan_id, operation_key=operation_key)

    def _confirm(self, plan_id: str, *, operation_key: str | None = None) -> Plan:
        plan = self.store.get_plan(plan_id)
        if not plan:
            raise ToolError("plan_not_found")
        if plan.status == "confirmed":
            return plan
        key = operation_key or f"plan-confirm:{plan_id}:{plan.version}"
        receipt = self.store.get_receipt(key)
        if receipt:
            return self.store.get_plan(receipt["plan_id"]) or plan
        if plan.status != "draft":
            raise ToolError("plan_not_awaiting_confirmation")
        start = date.fromisoformat(plan.start_date)
        end = start + timedelta(days=plan.days - 1)
        replacements = []
        for old in self.store.list_plans(plan.user_id):
            if old.plan_id == plan.plan_id or old.status != "confirmed":
                continue
            old_start = date.fromisoformat(old.start_date)
            old_end = old_start + timedelta(days=old.days - 1)
            if old_start <= end and start <= old_end:
                if (old_start, old_end) != (start, end):
                    raise ToolError("overlapping_plan_range")
                replacements.append(old)
        for old in replacements:
            old.status = "superseded"
            self.store.save_plan(old)
            for shopping in self.store.list_shopping_lists(old.plan_id):
                shopping.status = "stale"
                self.store.save_shopping_list(shopping)
        plan.status = "confirmed"
        saved = self.store.save_plan(plan)
        self.store.save_receipt(key, {"plan_id": plan.plan_id, "version": plan.version})
        return saved

    def cancel(self, plan_id: str) -> Plan:
        plan = self.store.get_plan(plan_id)
        if not plan or plan.status != "draft":
            raise ToolError("plan_not_cancellable")
        plan.status = "cancelled"
        return self.store.save_plan(plan)

    def generate_shopping_list(self, plan_id: str, *, operation_key: str | None = None) -> ShoppingList:
        plan = self.store.get_plan(plan_id)
        if not plan or plan.status != "confirmed":
            raise ToolError("plan_not_confirmed")
        key = operation_key or f"shopping:{plan_id}:{plan.version}"
        receipt = self.store.get_receipt(key)
        if receipt:
            existing = self.store.get_shopping_list(receipt["list_id"])
            if existing:
                return existing
        grouped: dict[tuple[str, str], dict] = {}
        for item in plan.items:
            group = grouped.setdefault((item.ingredient_id, item.unit), {"name": item.ingredient_name or item.name, "quantity": 0.0})
            group["quantity"] += item.quantity
        items = [ShoppingListItem(str(uuid4()), ingredient, value["name"], value["quantity"], unit, value["quantity"]) for (ingredient, unit), value in sorted(grouped.items())]
        shopping = ShoppingList(str(uuid4()), plan.user_id, plan.plan_id, plan.version, "active", items)
        self.store.save_shopping_list(shopping)
        self.store.save_receipt(key, {"list_id": shopping.list_id, "plan_id": plan_id, "plan_version": plan.version})
        return shopping

    def inventory_upsert(self, item: InventoryItem) -> InventoryItem:
        if not all(value.strip() for value in (item.inventory_id, item.user_id, item.ingredient_id, item.name)) or item.quantity < 0 or not math.isfinite(item.quantity) or not item.unit in UNITS:
            raise ToolError("invalid_inventory_item")
        with self.store.transaction():
            return self.store.save_inventory_item(item)

    def inventory_diff(self, shopping_list_id: str) -> list[ShoppingListItem]:
        shopping = self.store.get_shopping_list(shopping_list_id)
        if not shopping or shopping.status != "active":
            raise ToolError("shopping_list_not_active")
        stock = defaultdict(float)
        for item in self.store.list_inventory(shopping.user_id):
            stock[(item.ingredient_id, item.unit)] += item.quantity
        result = []
        for item in shopping.items:
            available = stock[(item.ingredient_id, item.unit)]
            result.append(ShoppingListItem(item.item_id, item.ingredient_id, item.name, item.quantity, item.unit, max(item.quantity - available, 0.0), item.purchased))
        return result
