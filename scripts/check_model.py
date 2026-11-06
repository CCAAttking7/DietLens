"""One explicitly invoked live call with synthetic input, without adopting an action."""
import argparse
import json
from pathlib import Path

from dietlens_mvp import Harness, SQLiteStore
from dietlens_mvp.config import Settings
from dietlens_mvp.errors import ToolError
from dietlens_mvp.models import Profile


def main() -> int:
    root = Path(__file__).resolve().parents[1]
    parser = argparse.ArgumentParser(description="DietLens 单次模型联通检查（合成情境，不记录实际用餐）")
    parser.add_argument("--env-file", default=str(root / ".env"))
    args = parser.parse_args()
    settings = Settings.from_env(args.env_file)
    try:
        provider = settings.create_provider()
    except ToolError as exc:
        print(json.dumps({"ok": False, "error_code": exc.code, "hint": "请在本地配置 API Key、Base URL 和模型名"}, ensure_ascii=False))
        return 2
    directory = root / "data"
    directory.mkdir(exist_ok=True)
    store = SQLiteStore(str(directory / "model_checks.db"))
    try:
        store.put_profile(Profile(user_id="synthetic-model-check"))
        harness = Harness(store, provider)
        task = harness.create_task("synthetic-model-check")
        intent = harness.interpret(task.task_id, [{"role": "user", "content": "这是一条联调合成数据：午餐可选鸡肉饭和番茄面，请提取餐次和选项。"}])
        audit = store.list_events(task.task_id)[-1].payload
        ok = audit.get("outcome") == "validated"
        print(json.dumps({"ok": ok, "task_id": task.task_id, "audit": audit, "intent": intent if ok else None}, ensure_ascii=False))
        return 0 if ok else 1
    finally:
        store.close()


if __name__ == "__main__":
    raise SystemExit(main())
