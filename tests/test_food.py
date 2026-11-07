import time

import pytest

from dietlens_mvp.food import assess_record, compare_nutrient, search_result, source_conflicts, summarize_record
from dietlens_mvp.sources import FoodRecord, FoodSourceRegistry, SourceError


def record(name="燕麦", source="off", source_id="1", *, ingredients=None, allergens=None, raw=None, price=None, nutrients=None, serving_unit="g", serving_size=None):
    return FoodRecord(name=name, source=source, source_id=source_id, ingredients=ingredients or [], allergens=allergens or [], raw=raw or {}, price=price, nutrients=nutrients or {"energy_100g": 100}, serving_unit=serving_unit, serving_size=serving_size)


def test_explicit_allergen_blocks_even_if_other_fields_unknown():
    result = assess_record(record(ingredients=["燕麦", "花生粉"], raw={"ingredients_text": "燕麦, 花生粉"}), ["花生"])
    assert result.status == "blocked"
    assert "explicit_hard_constraint_match" in result.reasons


def test_unknown_key_ingredients_stop_affected_recommendation():
    result = assess_record(record(raw={}), ["花生"])
    assert result.status == "needs_confirmation"
    assert set(result.unknown_fields) == {"ingredients", "allergens"}


def test_no_constraints_does_not_turn_missing_fields_into_zero_or_block():
    result = assess_record(record(raw={}), [])
    assert result.status == "needs_confirmation"
    assert record(raw={}).nutrients.get("protein_100g") is None


def test_budget_only_blocks_known_price_and_unknown_price_remains_unknown():
    known = {"ingredients_text": "食物", "allergens_tags": []}
    result = search_result(FoodSourceRegistry(off=type("S", (), {"search": lambda self, q, limit: [record(price=40, raw=known), record(name="豆腐", source_id="2", price=None, raw=known)]})(), china=None), "食物", [], budget=30)
    assert [a.status for a in result["assessments"]] == ["blocked", "safe"]
    assert result["assessments"][0].reasons == ("price_over_budget",)


def test_source_conflict_is_visible_and_not_merged():
    records = [record(source="off", source_id="a", serving_size=100), record(source="china", source_id="b", serving_size=80)]
    conflicts = source_conflicts(records)
    assert conflicts and conflicts[0].field == "serving_size"
    assert set(conflicts[0].values) == {"off", "china"}


def test_g_and_ml_are_not_compared_as_same_unit():
    records = [record(source="a", source_id="a", nutrients={"sugar_100g": 5}, serving_unit="g", serving_size=None), record(source="b", source_id="b", nutrients={"sugar_100ml": 3}, serving_unit="ml")]
    comparison = compare_nutrient(records, "sugar_100g", unit="per_100g")
    assert comparison.comparable is False
    assert comparison.reason == "unit_or_field_mismatch"


def test_summary_preserves_unknown_nutrient_and_provenance():
    summary = summarize_record(record(raw={"ingredients_text": "燕麦"}, nutrients={"energy_100g": None}))
    assert summary["nutrients"]["energy_100g"] is None
    assert summary["ingredients_known"] is True
    assert summary["allergens_known"] is False
    assert summary["source_id"] == "1"


def test_summary_includes_traceable_source_and_lists_without_raw_payload():
    item=record(ingredients=['燕麦'],allergens=['小麦'],raw={'ingredients_text':'燕麦','allergens_tags':['小麦'],'private_fixture':'not-for-ui'})
    item.source_url='https://example.com/fixture'
    summary=summarize_record(item)
    assert summary['source_url']==item.source_url
    assert summary['ingredients']==['燕麦']
    assert summary['allergens']==['小麦']
    assert 'private_fixture' not in str(summary)


def test_off_search_has_per_product_provenance(monkeypatch):
    from dietlens_mvp.sources import OpenFoodFactsSource
    source=OpenFoodFactsSource()
    monkeypatch.setattr(source,'_get',lambda *args:{'products':[{'code':'123','product_name':'燕麦'}]})
    assert source.search('燕麦')[0].source_url.endswith('/v3/product/123.json')


def test_unavailable_local_dataset_is_not_reported_as_empty_search(tmp_path):
    from dietlens_mvp.sources import ChinaCDCFoodCompositionSource
    china=ChinaCDCFoodCompositionSource(str(tmp_path/'missing.xlsx'))
    off=type('Empty',(),{'search':lambda self,q,limit:[]})()
    records,failures=FoodSourceRegistry(off=off,china=china).search('燕麦')
    assert records==[]
    assert failures=={'china_cdc_food_composition':'china_dataset_unavailable'}


def test_registry_cache_avoids_duplicate_calls_and_is_bounded():
    class Source:
        def __init__(self): self.calls = 0
        def search(self, query, limit):
            self.calls += 1
            return [record()]
    source = Source()
    registry = FoodSourceRegistry(off=source, china=None, cache_ttl_seconds=60, max_cache_entries=1)
    registry.search("燕麦")
    registry.search("燕麦")
    assert source.calls == 1
    registry.search("豆腐")
    registry.search("燕麦")
    assert source.calls == 3


def test_registry_isolates_failure_and_does_not_leak_exception():
    class Broken:
        def search(self, query, limit): raise SourceError("off_timeout", "secret response")
    result = FoodSourceRegistry(off=Broken(), china=None).search("食物")
    assert result[0] == []
    assert result[1] == {"open_food_facts": "off_timeout"}
    assert "secret" not in str(result[1])


def test_query_is_bounded_before_external_call():
    class Source:
        def search(self, query, limit): raise AssertionError("must not call")
    result = FoodSourceRegistry(off=Source(), china=None).search("x" * 121)
    assert result == ([], {"query": "invalid_query"})


def test_english_allergen_alias_matches_chinese_constraint():
    result = assess_record(record(ingredients=["peanuts"], allergens=["peanuts"], raw={"ingredients_text": "peanuts", "allergens_tags": ["en:peanuts"]}), ["花生"])
    assert result.status == "blocked"


def test_food_observation_persistence_is_read_only_and_traceable(tmp_path):
    from dietlens_mvp import SQLiteStore
    from dietlens_mvp.food import persist_search_result
    registry = FoodSourceRegistry(off=type("S", (), {"search": lambda self, q, limit: [record(raw={"ingredients_text": "燕麦", "allergens_tags": []})]})(), china=None)
    result = search_result(registry, "燕麦", ["花生"])
    store = SQLiteStore(str(tmp_path / "food.db"))
    observations = persist_search_result(store, "u", result, task_id="task-1")
    assert len(observations) == 1
    saved = store.list_food_observations("u")[0]
    assert saved.task_id == "task-1"
    assert saved.record["source_id"] == "1"
    assert saved.record["retrieved_at"]
    assert saved.status == "safe"
    assert saved.record["nutrients"]["energy_100g"] == 100
    store.close()


def test_source_provenance_contains_url_for_off_product(monkeypatch):
    from dietlens_mvp.sources import OpenFoodFactsSource
    source = OpenFoodFactsSource()
    monkeypatch.setattr(source, "_get", lambda path, params=None: {"status": 1, "product": {"product_name": "燕麦", "code": "123", "nutriments": {}}})
    item = source.product("123")
    assert item.source_url.endswith("/v3/product/123.json")


def test_unconfirmed_hard_constraints_never_auto_promote_source_records():
    registry = FoodSourceRegistry(off=type("S", (), {"search": lambda self, q, limit: [record(raw={"ingredients_text": "燕麦"})]})(), china=None)
    result = search_result(registry, "燕麦", [], constraints_confirmed=False)
    assert result["safe"] == []
    assert result["assessments"][0].status == "needs_confirmation"
    assert result["assessments"][0].reasons == ("hard_constraints_unknown",)


def test_missing_standard_nutrients_are_explicit_unknown_and_serving_unit_is_preserved(monkeypatch):
    from dietlens_mvp.sources import OpenFoodFactsSource
    source = OpenFoodFactsSource()
    monkeypatch.setattr(source, "_get", lambda path, params=None: {"status": 1, "product": {"product_name": "饮料", "code": "123", "serving_size": "250 ml", "nutriments": {"energy-kcal_100g": 40}}})
    item = source.product("123")
    assert item.serving_size == 250 and item.serving_unit == "ml"
    assert item.nutrients["energy-kcal_100g"] == 40
    assert item.nutrients["proteins_100g"] is None
