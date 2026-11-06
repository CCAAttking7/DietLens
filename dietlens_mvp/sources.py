from __future__ import annotations

import json
import os
import re
import urllib.parse
import urllib.request
import zipfile
import hashlib
from dataclasses import dataclass, field
from datetime import datetime, timezone
from xml.etree import ElementTree


@dataclass
class FoodRecord:
    name: str
    source: str
    source_id: str | None = None
    serving_size: float | None = None
    serving_unit: str | None = None
    nutrients: dict[str, float | None] = field(default_factory=dict)
    ingredients: list[str] = field(default_factory=list)
    allergens: list[str] = field(default_factory=list)
    retrieved_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    raw: dict = field(default_factory=dict)
    price: float | None = None
    price_currency: str | None = None
    data_version: str | None = None
    source_url: str | None = None


class SourceError(RuntimeError):
    """Read-source failure with a stable code and safe detail."""
    def __init__(self, code: str, detail: str = "") -> None:
        self.code = code
        super().__init__(code)

_STANDARD_NUTRIENTS = ("energy-kcal_100g", "fat_100g", "carbohydrates_100g", "sugars_100g", "proteins_100g", "salt_100g", "sodium_100g")


def _nutrients(values: dict) -> dict[str, float | None]:
    parsed = {k: _number(v) for k, v in values.items() if k.endswith(("_100g", "_100ml"))}
    for key in _STANDARD_NUTRIENTS:
        parsed.setdefault(key, None)
    return parsed


def _serving(value: object) -> tuple[float | None, str | None]:
    text = str(value or "")
    return _number(value), ("ml" if re.search(r"mL|ml|毫升", text) else "g" if re.search(r"g|克", text) else None)


class OpenFoodFactsSource:
    base_url = "https://world.openfoodfacts.org/api"

    def __init__(self, user_agent: str = "DietLens/0.1 (contact@example.com)") -> None:
        self.user_agent = user_agent

    def _get(self, path: str, params: dict[str, str] | None = None) -> dict:
        url = f"{self.base_url}/{path}"
        if params:
            url += "?" + urllib.parse.urlencode(params)
        request = urllib.request.Request(url, headers={"User-Agent": self.user_agent, "Accept": "application/json"})
        try:
            with urllib.request.urlopen(request, timeout=15) as response:
                return json.loads(response.read())
        except Exception as exc:
            raise SourceError("open_food_facts_request_failed") from exc

    def product(self, barcode: str) -> FoodRecord | None:
        data = self._get(f"v3/product/{urllib.parse.quote(barcode)}.json")
        if data.get("status") not in (1, "success") or not data.get("product"):
            return None
        p = data["product"]
        nutrients = p.get("nutriments", {})
        serving_size, serving_unit = _serving(p.get("serving_size"))
        return FoodRecord(
            name=p.get("product_name") or p.get("generic_name") or barcode,
            source="open_food_facts",
            source_id=barcode,
            serving_size=serving_size,
            serving_unit=serving_unit,
            nutrients=_nutrients(nutrients),
            ingredients=[x.strip() for x in (p.get("ingredients_text", "").split(",")) if x.strip()],
            allergens=[x.split(":", 1)[-1].strip() for x in p.get("allergens_tags", [])],
            raw=p,
            source_url=f"{self.base_url}/v3/product/{urllib.parse.quote(barcode)}.json",
        )

    def search(self, query: str, page_size: int = 10) -> list[FoodRecord]:
        # v3 is the current product API; structured search remains a v2 endpoint.
        data = self._get("v2/search", {"search_terms": query, "page_size": str(page_size), "json": "true"})
        return [self._from_product(p) for p in data.get("products", []) if p.get("code")]

    def _from_product(self, p: dict) -> FoodRecord:
        return FoodRecord(name=p.get("product_name") or p.get("generic_name") or p.get("code"), source="open_food_facts", source_id=p.get("code"), nutrients=_nutrients(p.get("nutriments", {})), ingredients=[x.strip() for x in p.get("ingredients_text", "").split(",") if x.strip()], allergens=[x.split(":", 1)[-1].strip() for x in p.get("allergens_tags", [])], raw=p, source_url=self.base_url + "/v3/product/" + urllib.parse.quote(str(p.get("code")), safe="") + ".json")


class USDAFoodDataCentralSource:
    base_url = "https://api.nal.usda.gov/fdc/v1"

    def __init__(self, api_key: str | None = None) -> None:
        self.api_key = api_key or os.getenv("USDA_FDC_API_KEY")
        if not self.api_key:
            raise SourceError("usda_api_key_required")

    def _get(self, path: str, params: dict[str, str]) -> dict:
        params = {**params, "api_key": self.api_key or ""}
        request = urllib.request.Request(f"{self.base_url}/{path}?{urllib.parse.urlencode(params)}", headers={"User-Agent": "DietLens/0.1"})
        try:
            with urllib.request.urlopen(request, timeout=15) as response:
                return json.loads(response.read())
        except Exception as exc:
            raise SourceError("usda_request_failed") from exc

    def search(self, query: str, page_size: int = 10) -> list[FoodRecord]:
        data = self._get("foods/search", {"query": query, "pageSize": str(page_size)})
        return [self._from_food(p) for p in data.get("foods", [])]

    def food(self, fdc_id: str) -> FoodRecord:
        return self._from_food(self._get(f"food/{urllib.parse.quote(str(fdc_id))}", {}))

    def _from_food(self, p: dict) -> FoodRecord:
        nutrients = {}
        for nutrient in p.get("foodNutrients", []):
            name = nutrient.get("nutrientName") or nutrient.get("nutrient", {}).get("name")
            value = nutrient.get("value")
            if name and name not in nutrients:
                nutrients[name] = _number(value)
        return FoodRecord(name=p.get("description", ""), source="usda_fooddata_central", source_id=str(p.get("fdcId")), nutrients=nutrients, raw=p)


class ChinaCDCFoodCompositionSource:
    """Official CDC public-health data-center resource, downloaded then indexed locally."""

    resource_url = "https://www.phsciencedata.cn/Share/getsetdoc/ccbc9017-7fc2-4391-b39e-09ed09379751?filename=%E9%A3%9F%E7%89%A9%E7%BC%96%E7%A0%81%E8%A1%A8.xlsx"

    def __init__(self, cache_path: str = "data/china_food_codes.xlsx") -> None:
        self.cache_path = cache_path
        self.rows: list[list[str]] = []

    def refresh(self) -> int:
        os.makedirs(os.path.dirname(self.cache_path) or ".", exist_ok=True)
        request = urllib.request.Request(self.resource_url, headers={"User-Agent": "DietLens/0.1"})
        with urllib.request.urlopen(request, timeout=30) as response, open(self.cache_path, "wb") as output:
            output.write(response.read())
        self.rows = _read_xlsx_rows(self.cache_path)
        return len(self.rows)

    def search(self, query: str, limit: int = 10) -> list[FoodRecord]:
        if not self.rows and os.path.exists(self.cache_path):
            self.rows = _read_xlsx_rows(self.cache_path)
        if not self.rows:
            raise SourceError("china_dataset_unavailable")
        q = query.casefold()
        records = []
        for row in self.rows:
            text = " ".join(row)
            if q in text.casefold():
                records.append(FoodRecord(name=row[-1] if row else query, source="china_cdc_food_composition", source_id=row[0] if row else None, raw={"row": row}, source_url=self.resource_url))
                if len(records) >= limit:
                    break
        return records


_DEFAULT = object()


class FoodSourceRegistry:
    """Fan-out read-only search with per-source failure isolation."""

    def __init__(self, off: OpenFoodFactsSource | None = None, usda: USDAFoodDataCentralSource | None = None, china: ChinaCDCFoodCompositionSource | None | object = _DEFAULT, *, cache_ttl_seconds: float = 900, max_cache_entries: int = 128) -> None:
        self.off = off or OpenFoodFactsSource()
        # USDA is accepted only for backwards-compatible injection in tests; it is never a default.
        self.usda = usda
        self.china = ChinaCDCFoodCompositionSource() if china is _DEFAULT else china
        self.cache_ttl_seconds = max(0.0, float(cache_ttl_seconds))
        self.max_cache_entries = max(1, int(max_cache_entries))
        self._cache: dict[tuple[str, str, int], tuple[float, list[FoodRecord]]] = {}

    def search(self, query: str, limit: int = 5) -> tuple[list[FoodRecord], dict[str, str]]:
        query = query.strip()
        if not query or len(query) > 120:
            return [], {"query": "invalid_query"}
        results: list[FoodRecord] = []
        failures: dict[str, str] = {}
        sources = (("open_food_facts", self.off), ("usda_fooddata_central", self.usda), ("china_cdc_food_composition", self.china))
        import time
        for name, source in sources:
            if source is None:
                continue
            key = (name, query.casefold(), int(limit))
            cached = self._cache.get(key)
            if cached and time.monotonic() - cached[0] <= self.cache_ttl_seconds:
                results.extend(cached[1])
                continue
            try:
                records = list(source.search(query, limit))
                self._cache[key] = (time.monotonic(), records)
                while len(self._cache) > self.max_cache_entries:
                    self._cache.pop(next(iter(self._cache)))
                results.extend(records)
            except SourceError as exc:
                failures[name] = exc.code
            except Exception:
                failures[name] = "source_failed"
        return results, failures

    def clear_cache(self) -> None:
        self._cache.clear()


def _number(value: object) -> float | None:
    if value is None or value == "":
        return None
    match = re.search(r"[-+]?\d+(?:\.\d+)?", str(value).replace(",", ""))
    return float(match.group()) if match else None


def _read_xlsx_rows(path: str) -> list[list[str]]:
    # Minimal XLSX reader avoids making the source connector depend on pandas/openpyxl.
    ns = {"x": "http://schemas.openxmlformats.org/spreadsheetml/2006/main", "r": "http://schemas.openxmlformats.org/officeDocument/2006/relationships"}
    with zipfile.ZipFile(path) as archive:
        strings = []
        if "xl/sharedStrings.xml" in archive.namelist():
            root = ElementTree.fromstring(archive.read("xl/sharedStrings.xml"))
            strings = ["".join(t.text or "" for t in si.iter("{http://schemas.openxmlformats.org/spreadsheetml/2006/main}t")) for si in root.findall("x:si", ns)]
        sheet = ElementTree.fromstring(archive.read("xl/worksheets/sheet1.xml"))
        rows = []
        for row in sheet.findall("x:sheetData/x:row", ns):
            values = []
            for cell in row.findall("x:c", ns):
                value = cell.find("x:v", ns)
                text = value.text if value is not None else ""
                if cell.get("t") == "s" and text.isdigit() and int(text) < len(strings):
                    text = strings[int(text)]
                values.append(text)
            rows.append(values)
        return rows
