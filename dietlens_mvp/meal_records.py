"""User-confirmed actual meal records.

The service deliberately keeps plan prefill read-only until ``confirm`` is
called.  It also treats an unknown portion as ``None`` throughout review
calculations instead of silently turning it into zero.
"""
from __future__ import annotations

from copy import deepcopy
from datetime import date, datetime, timezone
import math
from uuid import uuid4

from .errors import ToolError
from .models import MealRecord
from .planning import MEAL_SLOTS, UNITS


def _validate(record: MealRecord) -> None:
    try:
        date.fromisoformat(record.meal_date)
    except ValueError as exc:
        raise ToolError("invalid_meal_date") from exc
    if record.meal_slot not in MEAL_SLOTS or not record.name.strip():
        raise ToolError("invalid_meal_record")
    if record.status not in {"active", "deleted"}:
        raise ToolError("invalid_meal_record_status")
    if record.quantity is not None and (type(record.quantity) not in (int, float) or not math.isfinite(record.quantity) or record.quantity < 0):
        raise ToolError("invalid_meal_quantity")
    if record.quantity is not None and record.unit not in UNITS:
        raise ToolError("invalid_meal_unit")
    if record.quantity is None and record.unit is not None:
        raise ToolError("unknown_quantity_unit")
    if not record.source.strip():
        raise ToolError("invalid_meal_source")


class MealRecordService:
    def __init__(self, store):
        self.store = store

    def prefill(self, user_id: str, plan_id: str, plan_item_id: str) -> MealRecord:
        plan = self.store.get_plan(plan_id)
        if not plan or plan.user_id != user_id or plan.status != "confirmed":
            raise ToolError("plan_not_confirmed")
        item = next((item for item in plan.items if item.item_id == plan_item_id), None)
        if item is None:
            raise ToolError("plan_item_not_found")
        return MealRecord(str(uuid4()), user_id, item.meal_date, item.meal_slot, item.name,
                          item.ingredient_id, item.quantity, item.unit, None, "plan_prefill",
                          plan_id, item.item_id)

    def preview(self, user_id: str, *, meal_date: str, meal_slot: str, name: str,
                ingredient_id: str = "", quantity: float | None = None,
                unit: str | None = None, eaten_at: str | None = None,
                source: str = "user_self_report", plan_id: str | None = None,
                plan_item_id: str | None = None, record_id: str | None = None) -> MealRecord:
        record = MealRecord(record_id or str(uuid4()), user_id, meal_date, meal_slot, name,
                            ingredient_id, quantity, unit, eaten_at, source, plan_id, plan_item_id)
        if plan_id or plan_item_id:
            plan = self.store.get_plan(plan_id or "")
            if not plan or plan.user_id != user_id or plan.status != "confirmed":
                raise ToolError("plan_not_confirmed")
            if plan_item_id is None or not any(item.item_id == plan_item_id for item in plan.items):
                raise ToolError("plan_item_not_found")
        _validate(record)
        return record

    def confirm(self, record: MealRecord, *, operation_key: str | None = None) -> MealRecord:
        _validate(record)
        if record.status != "active":
            raise ToolError("meal_record_not_confirmable")
        key = operation_key or f"meal-record-confirm:{record.record_id}"
        receipt = self.store.get_receipt(key)
        if receipt:
            if receipt.get("record_id") != record.record_id:
                raise ToolError("operation_conflict")
            existing = self.store.get_meal_record(receipt["record_id"])
            if existing:
                return existing
        saved = self.store.save_meal_record(record, key)
        self.store.save_receipt(key, {"record_id": saved.record_id, "version": saved.version})
        return saved

    def update(self, record_id: str, *, expected_version: int, operation_key: str | None = None, **changes) -> MealRecord:
        key = operation_key or f"meal-record-update:{record_id}:{expected_version}"
        receipt = self.store.get_receipt(key)
        if receipt:
            if receipt.get("record_id") != record_id:
                raise ToolError("operation_conflict")
            existing = self.store.get_meal_record(record_id)
            if existing:
                return existing
        current = self.store.get_meal_record(record_id)
        if not current or current.status == "deleted":
            raise ToolError("meal_record_not_found")
        if current.version != expected_version:
            raise ToolError("version_conflict")
        allowed = {"meal_date", "meal_slot", "name", "ingredient_id", "quantity", "unit", "eaten_at", "source", "plan_id", "plan_item_id"}
        if set(changes) - allowed:
            raise ToolError("invalid_meal_record_field")
        updated = deepcopy(current)
        for key_name, value in changes.items():
            setattr(updated, key_name, value)
        updated.version += 1
        updated.updated_at = datetime.now(timezone.utc).isoformat()
        _validate(updated)
        saved = self.store.save_meal_record(updated, key)
        self.store.save_receipt(key, {"record_id": saved.record_id, "version": saved.version})
        return saved

    def delete(self, record_id: str, *, expected_version: int, operation_key: str | None = None) -> MealRecord:
        key = operation_key or f"meal-record-delete:{record_id}:{expected_version}"
        receipt = self.store.get_receipt(key)
        if receipt:
            if receipt.get("record_id") != record_id:
                raise ToolError("operation_conflict")
            existing = self.store.get_meal_record(record_id)
            if existing:
                return existing
        current = self.store.get_meal_record(record_id)
        if not current:
            raise ToolError("meal_record_not_found")
        if current.version != expected_version:
            raise ToolError("version_conflict")
        deleted = deepcopy(current)
        deleted.status = "deleted"
        deleted.version += 1
        deleted.updated_at = datetime.now(timezone.utc).isoformat()
        saved = self.store.save_meal_record(deleted, key)
        self.store.save_receipt(key, {"record_id": saved.record_id, "version": saved.version})
        return saved

    def list(self, user_id: str, *, include_deleted: bool = False) -> list[MealRecord]:
        return self.store.list_meal_records(user_id, include_deleted=include_deleted)

    def coverage(self, user_id: str, *, start_date: str | None = None, end_date: str | None = None) -> dict:
        start = date.fromisoformat(start_date) if start_date else None
        end = date.fromisoformat(end_date) if end_date else None
        planned = 0
        for plan in self.store.list_plans(user_id):
            if plan.status != "confirmed":
                continue
            for item in plan.items:
                item_date = date.fromisoformat(item.meal_date)
                if (start is None or item_date >= start) and (end is None or item_date <= end):
                    planned += 1
        records = []
        for record in self.store.list_meal_records(user_id):
            item_date = date.fromisoformat(record.meal_date)
            if (start is None or item_date >= start) and (end is None or item_date <= end):
                records.append(record)
        known = sum(record.quantity is not None for record in records)
        return {"planned_meals": planned, "recorded_meals": len(records),
                "coverage": (len(records) / planned if planned else None),
                "quantity_known": known, "quantity_unknown": len(records) - known,
                "quantity_coverage": (known / len(records) if records else None)}
