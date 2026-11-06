"""Check hosted schema through the browser-safe Supabase API."""
from __future__ import annotations
import json
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen
from dotenv import dotenv_values


def main() -> int:
    root = Path(__file__).resolve().parents[1]
    cfg = dotenv_values(root / "web/.env")
    url, key = cfg.get("VITE_SUPABASE_URL"), cfg.get("VITE_SUPABASE_PUBLISHABLE_KEY")
    if not url or not key:
        print(json.dumps({"ok": False, "code": "supabase_browser_config_missing"}))
        return 2
    try:
        tables = ["profiles", "tasks", "food_observations", "events", "plans", "shopping_lists", "inventory_items", "meal_records", "meal_record_versions"]
        statuses = {}
        for table in tables:
            request = Request(url.rstrip("/") + f"/rest/v1/{table}?select=*&limit=1",
                              headers={"apikey": key, "Authorization": "Bearer " + key})
            with urlopen(request, timeout=15) as response:
                statuses[table] = response.status
        print(json.dumps({"ok": True, "tables": statuses}, ensure_ascii=False))
        return 0
    except HTTPError as exc:
        body = exc.read(5000).decode("utf-8", errors="replace")
        try:
            data = json.loads(body)
            code = data.get("code", "http_error")
        except ValueError:
            code = "http_error"
        print(json.dumps({"ok": False, "status": exc.code, "code": code}, ensure_ascii=False))
        return 1
    except (URLError, TimeoutError):
        print(json.dumps({"ok": False, "code": "supabase_network_failed"}))
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
