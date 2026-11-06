"""Deterministic food-source normalization, safety gating, and comparisons."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Iterable
from uuid import uuid4

from .models import FoodObservation

from .cleaning import clean_text
from .sources import FoodRecord


@dataclass(frozen=True)
class FoodAssessment:
    record: FoodRecord
    status: str  # safe | blocked | needs_confirmation
    reasons: tuple[str, ...] = ()
    unknown_fields: tuple[str, ...] = ()


@dataclass(frozen=True)
class SourceConflict:
    field: str
    values: dict[str, object]
    source_ids: dict[str, str | None]


@dataclass(frozen=True)
class NutritionComparison:
    field: str
    unit: str
    values: dict[str, float | None]
    comparable: bool
    reason: str | None = None


_TERM_ALIASES = {
    "peanut": "花生", "peanuts": "花生", "groundnut": "花生",
    "milk": "牛奶", "dairy": "乳制品", "egg": "鸡蛋", "eggs": "鸡蛋",
    "soy": "大豆", "soya": "大豆", "wheat": "小麦", "gluten": "麸质",
    "sesame": "芝麻", "tree nuts": "坚果", "nuts": "坚果", "shellfish": "甲壳类",
}


def _terms(values: Iterable[str]) -> list[str]:
    result = []
    for value in values:
        cleaned = clean_text(value).casefold()
        if cleaned:
            result.append(_TERM_ALIASES.get(cleaned, cleaned))
    return result


def _contains_term(text: str, terms: list[str]) -> bool:
    text = clean_text(text).casefold()
    for alias, canonical in _TERM_ALIASES.items():
        text = text.replace(alias, canonical)
    return any(term in text for term in terms)


def _record_has_field(record: FoodRecord, field: str) -> bool:
    raw = record.raw or {}
    if field == "ingredients":
        return bool(record.ingredients) or "ingredients_text" in raw or "ingredients" in raw
    if field == "allergens":
        return bool(record.allergens) or "allergens_tags" in raw or "allergens" in raw
    return field in raw


def assess_record(record: FoodRecord, hard_constraints: Iterable[str], *, require_ingredients: bool = True) -> FoodAssessment:
    constraints = _terms(hard_constraints)
    if not constraints:
        return FoodAssessment(record, "safe")
    unknown: list[str] = []
    if require_ingredients and not _record_has_field(record, "ingredients"):
        unknown.append("ingredients")
    if not _record_has_field(record, "allergens"):
        unknown.append("allergens")
    searchable = " ".join([record.name, *record.ingredients, *record.allergens])
    if _contains_term(searchable, constraints):
        return FoodAssessment(record, "blocked", ("explicit_hard_constraint_match",), tuple(unknown))
    if unknown:
        return FoodAssessment(record, "needs_confirmation", ("key_ingredient_or_allergen_unknown",), tuple(sorted(set(unknown))))
    return FoodAssessment(record, "safe")


def filter_safe_records(records: Iterable[FoodRecord], hard_constraints: Iterable[str]) -> list[FoodAssessment]:
    return [assess_record(record, hard_constraints) for record in records]


def source_conflicts(records: Iterable[FoodRecord], fields: Iterable[str] = ("name", "serving_size", "serving_unit")) -> list[SourceConflict]:
    by_key: dict[str, list[FoodRecord]] = {}
    for record in records:
        key = (record.name or record.source_id or "").casefold().strip()
        if key:
            by_key.setdefault(key, []).append(record)
    conflicts: list[SourceConflict] = []
    for same_name in by_key.values():
        if len({r.source for r in same_name}) < 2:
            continue
        for field in fields:
            values = {r.source: getattr(r, field) for r in same_name}
            comparable = {repr(value) for value in values.values() if value is not None}
            if len(comparable) > 1:
                conflicts.append(SourceConflict(field, values, {r.source: r.source_id for r in same_name}))
    return conflicts


def compare_nutrient(records: Iterable[FoodRecord], field: str, *, unit: str = "per_100g") -> NutritionComparison:
    records = list(records)
    values: dict[str, float | None] = {}
    for record in records:
        values[record.source_id or f"{record.source}:{record.name}"] = record.nutrients.get(field)
    if not records:
        return NutritionComparison(field, unit, values, False, "no_records")
    # The source field names carry the unit. Never infer a solid/liquid conversion.
    expected = f"{field}_{unit}" if not field.endswith(("_100g", "_100ml")) else field
    if any(record.nutrients and expected not in record.nutrients for record in records):
        return NutritionComparison(field, unit, values, False, "unit_or_field_mismatch")
    if unit not in {"per_100g", "per_100ml"}:
        return NutritionComparison(field, unit, values, False, "unsupported_unit")
    return NutritionComparison(field, unit, values, True)


def summarize_record(record: FoodRecord) -> dict:
    """Stable UI payload; raw responses remain available only through explicit source data."""
    return {
        "name": record.name,
        "source": record.source,
        "source_id": record.source_id,
        "source_url": record.source_url,
        "retrieved_at": record.retrieved_at,
        "serving_size": record.serving_size,
        "serving_unit": record.serving_unit,
        "nutrients": dict(record.nutrients),
        "ingredients_known": _record_has_field(record, "ingredients"),
        "allergens_known": _record_has_field(record, "allergens"),
        "ingredients": list(record.ingredients),
        "allergens": list(record.allergens),
        "price": record.price,
        "price_currency": record.price_currency,
    }


def search_result(registry, query: str, hard_constraints: Iterable[str] = (), *, budget: float | None = None, limit: int = 5, constraints_confirmed: bool = True):
    """Search and gate candidates without claiming unknown fields are safe."""
    from dataclasses import dataclass
    records, failures = registry.search(query, limit)
    constraints = list(hard_constraints)
    if not constraints_confirmed:
        assessments = [FoodAssessment(record, "needs_confirmation", ("hard_constraints_unknown",), ("allergies",)) for record in records]
    else:
        assessments = filter_safe_records(records, constraints)
    gated: list[FoodAssessment] = []
    for assessment in assessments:
        if assessment.status == "safe" and budget is not None and assessment.record.price is not None and assessment.record.price > budget:
            assessment = FoodAssessment(assessment.record, "blocked", ("price_over_budget",), assessment.unknown_fields)
        gated.append(assessment)
    assessments = gated
    return {
        "query": query,
        "records": records,
        "assessments": assessments,
        "safe": [a.record for a in assessments if a.status == "safe"],
        "failures": failures,
        "conflicts": source_conflicts(records),
    }



def persist_search_result(store, user_id: str, result: dict, *, task_id: str | None = None) -> list[FoodObservation]:
    """Persist read observations only; this never confirms a recommendation or meal record."""
    by_key = {}
    for assessment in result.get("assessments", []):
        record = assessment.record
        key = f"{record.source}:{record.source_id or record.name}"
        by_key[key] = FoodObservation(
            observation_id=str(uuid4()), user_id=user_id, task_id=task_id,
            record={**summarize_record(record), "raw": record.raw},
            status=assessment.status, unknown_fields=list(assessment.unknown_fields),
        )
    observations = list(by_key.values())
    for observation in observations:
        store.save_food_observation(observation)
    return observations
