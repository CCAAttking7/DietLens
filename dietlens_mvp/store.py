from __future__ import annotations

from contextlib import contextmanager
from functools import wraps
from copy import deepcopy
from datetime import datetime, timezone
import json
from pathlib import Path
import sqlite3
import threading
from typing import Any

from .errors import ToolError
from .serialization import dumps
from .models import Action, CareState, Context, Decision, Event, Execution, FoodObservation, InventoryItem, MealRecord, Plan, PlanItem, Profile, ProfileDraft, ShoppingList, ShoppingListItem, Task, TaskState


def now() -> str:
    return datetime.now(timezone.utc).isoformat()


class InMemoryStore:
    """Test/demo repository with the same transaction semantics as SQLite."""

    def __init__(self) -> None:
        self.profiles: dict[str, Profile] = {}
        self.tasks: dict[str, Task] = {}
        self.actions: dict[str, Action] = {}
        self.events: list[Event] = []
        self._operations: dict[str, Any] = {}
        self.profile_drafts: dict[str, ProfileDraft] = {}
        self.profile_versions: dict[tuple[str, int], Profile] = {}
        self.consent_events: list[dict] = []
        self.meal_record_versions: list[dict] = []

    @contextmanager
    def transaction(self):
        snapshot = deepcopy((self.profiles, self.tasks, self.actions, self.events, self._operations, self.profile_drafts, self.profile_versions, self.consent_events, self.meal_record_versions))
        try:
            yield
        except BaseException:
            self.profiles, self.tasks, self.actions, self.events, self._operations, self.profile_drafts, self.profile_versions, self.consent_events, self.meal_record_versions = snapshot
            raise

    def put_profile(self, profile: Profile) -> Profile:
        self.profiles[profile.user_id] = deepcopy(profile)
        return deepcopy(profile)

    def get_profile(self, user_id: str) -> Profile | None:
        return deepcopy(self.profiles.get(user_id))

    def save_task(self, task: Task) -> Task:
        existing = self.tasks.get(task.task_id)
        if existing and existing.version != task.version:
            raise ToolError("version_conflict")
        if existing:
            task.version += 1
        task.updated_at = now()
        self.tasks[task.task_id] = deepcopy(task)
        return deepcopy(task)

    def get_task(self, task_id: str) -> Task | None:
        return deepcopy(self.tasks.get(task_id))

    def commit_once(self, operation_key: str, value: Any) -> Any:
        if operation_key not in self._operations:
            self._operations[operation_key] = deepcopy(value)
        return deepcopy(self._operations[operation_key])

    def save_action(self, action: Action, operation_key: str) -> Action:
        if operation_key in self._operations:
            return deepcopy(self._operations[operation_key])
        self.actions[action.action_id] = deepcopy(action)
        return self.commit_once(operation_key, action)

    def get_action(self, action_id: str) -> Action | None:
        return deepcopy(self.actions.get(action_id))

    def list_actions(self, user_id: str) -> list[Action]:
        return [deepcopy(a) for a in self.actions.values() if a.user_id == user_id]

    def append_event(self, event: Event) -> None:
        self.events.append(deepcopy(event))

    def list_events(self, task_id: str) -> list[Event]:
        return [deepcopy(e) for e in self.events if e.task_id == task_id]

    def get_receipt(self, operation_key: str) -> dict | None:
        return deepcopy(self._operations.get(operation_key))

    def save_receipt(self, operation_key: str, receipt: dict) -> None:
        self.commit_once(operation_key, receipt)

    def save_profile_draft(self, draft: ProfileDraft) -> None:
        self.profile_drafts[draft.task_id] = deepcopy(draft)

    def get_profile_draft(self, task_id: str) -> ProfileDraft | None:
        return deepcopy(self.profile_drafts.get(task_id))

    def list_profile_versions(self, user_id: str) -> list[Profile]:
        return [deepcopy(p) for (uid, _), p in sorted(self.profile_versions.items()) if uid == user_id]

    def put_profile_version(self, profile: Profile, expected_version: int, task_id: str, operation_key: str) -> None:
        with self.transaction():
            previous = self.get_profile(profile.user_id)
            if (previous.version if previous else 0) != expected_version:
                raise ToolError("version_conflict")
            if profile.version != expected_version + 1:
                raise ToolError("invalid_profile_version")
            # Preserve an existing low-level fixture/legacy profile before its first managed edit.
            if previous:
                self.profile_versions.setdefault((previous.user_id, previous.version), previous)
            self.profile_versions[(profile.user_id, profile.version)] = deepcopy(profile)
            self.put_profile(profile)
            for scope, granted in profile.consents.items():
                if previous is None or previous.consents.get(scope, False) != granted:
                    self.consent_events.append({"user_id": profile.user_id, "scope": scope, "granted": granted,
                                                "profile_version": profile.version, "task_id": task_id,
                                                "operation_key": operation_key, "source": "user_confirmation",
                                                "created_at": profile.updated_at, "updated_at": profile.updated_at})

    def list_consent_events(self, user_id: str) -> list[dict]:
        return [deepcopy(e) for e in self.consent_events if e["user_id"] == user_id]

    def save_food_observation(self, observation: FoodObservation) -> FoodObservation:
        self._operations[f"food-observation:{observation.observation_id}"] = deepcopy(observation)
        return deepcopy(observation)

    def list_food_observations(self, user_id: str) -> list[FoodObservation]:
        return [deepcopy(v) for k, v in self._operations.items() if k.startswith("food-observation:") and v.user_id == user_id]

    def save_plan(self, plan: Plan) -> Plan:
        current = self.tasks.get(f"plan:{plan.plan_id}")
        self._operations[f"plan:{plan.plan_id}"] = deepcopy(plan)
        return deepcopy(plan)

    def get_plan(self, plan_id: str) -> Plan | None:
        return deepcopy(self._operations.get(f"plan:{plan_id}"))

    def list_plans(self, user_id: str) -> list[Plan]:
        return [deepcopy(v) for k, v in self._operations.items() if k.startswith("plan:") and isinstance(v, Plan) and v.user_id == user_id]

    def save_shopping_list(self, shopping_list: ShoppingList) -> ShoppingList:
        self._operations[f"shopping:{shopping_list.list_id}"] = deepcopy(shopping_list)
        return deepcopy(shopping_list)

    def get_shopping_list(self, list_id: str) -> ShoppingList | None:
        return deepcopy(self._operations.get(f"shopping:{list_id}"))

    def list_shopping_lists(self, plan_id: str) -> list[ShoppingList]:
        return [deepcopy(v) for k, v in self._operations.items() if k.startswith("shopping:") and isinstance(v, ShoppingList) and v.plan_id == plan_id]

    def save_inventory_item(self, item: InventoryItem) -> InventoryItem:
        existing = self._operations.get(f"inventory:{item.inventory_id}")
        if existing and existing.user_id != item.user_id:
            raise ToolError("user_ownership_required")
        if item.version != (existing.version if existing else 1):
            raise ToolError("version_conflict")
        if any(other.inventory_id != item.inventory_id and other.ingredient_id == item.ingredient_id and other.unit == item.unit for other in self.list_inventory(item.user_id)):
            raise ToolError("inventory_duplicate")
        if existing:
            item.version += 1
        item.updated_at = now()
        self._operations[f"inventory:{item.inventory_id}"] = deepcopy(item)
        return deepcopy(item)

    def list_inventory(self, user_id: str) -> list[InventoryItem]:
        return [deepcopy(v) for k, v in self._operations.items() if k.startswith("inventory:") and v.user_id == user_id]

    def save_meal_record(self, record: MealRecord, operation_key: str) -> MealRecord:
        key = f"meal-record:{record.record_id}"
        existing = self._operations.get(key)
        if existing and existing.version + 1 != record.version:
            raise ToolError("version_conflict")
        self._operations[key] = deepcopy(record)
        self.meal_record_versions.append({"record_id": record.record_id, "version": record.version,
                                          "user_id": record.user_id, "operation_key": operation_key,
                                          "payload": deepcopy(record)})
        return deepcopy(record)

    def get_meal_record(self, record_id: str) -> MealRecord | None:
        return deepcopy(self._operations.get(f"meal-record:{record_id}"))

    def list_meal_records(self, user_id: str, *, include_deleted: bool = False) -> list[MealRecord]:
        return [deepcopy(v) for k, v in self._operations.items()
                if k.startswith("meal-record:") and isinstance(v, MealRecord)
                and v.user_id == user_id and (include_deleted or v.status != "deleted")]

    def list_tasks(self, user_id: str) -> list[Task]:
        return [deepcopy(task) for task in self.tasks.values() if task.user_id == user_id]

    def delete_user_data(self, user_id: str) -> dict[str, int]:
        counts = {"profiles": int(user_id in self.profiles), "tasks": 0, "actions": 0, "meal_records": 0,
                  "plans": 0, "shopping_lists": 0, "inventory_items": 0, "food_observations": 0}
        counts["tasks"] = sum(task.user_id == user_id for task in self.tasks.values())
        counts["actions"] = sum(action.user_id == user_id for action in self.actions.values())
        counts["meal_records"] = sum(isinstance(value, MealRecord) and value.user_id == user_id for value in self._operations.values())
        counts["plans"] = sum(isinstance(value, Plan) and value.user_id == user_id for value in self._operations.values())
        counts["shopping_lists"] = sum(isinstance(value, ShoppingList) and value.user_id == user_id for value in self._operations.values())
        counts["inventory_items"] = sum(isinstance(value, InventoryItem) and value.user_id == user_id for value in self._operations.values())
        counts["food_observations"] = sum(isinstance(value, FoodObservation) and value.user_id == user_id for value in self._operations.values())
        self.profiles.pop(user_id, None)
        self.tasks = {key: value for key, value in self.tasks.items() if value.user_id != user_id}
        self.actions = {key: value for key, value in self.actions.items() if value.user_id != user_id}
        self.events = [event for event in self.events if event.user_id != user_id]
        self.profile_drafts = {key: value for key, value in self.profile_drafts.items() if value.user_id != user_id}
        self.profile_versions = {key: value for key, value in self.profile_versions.items() if key[0] != user_id}
        self.consent_events = [event for event in self.consent_events if event.get("user_id") != user_id]
        self.meal_record_versions = [item for item in self.meal_record_versions if item.get("user_id") != user_id]
        self._operations = {key: value for key, value in self._operations.items()
                            if not (hasattr(value, "user_id") and value.user_id == user_id)
                            and not key.startswith((f"profile:{user_id}:", f"start:{user_id}:"))}
        return counts


def _sqlite_locked(method):
    @wraps(method)
    def locked(self, *args, **kwargs):
        with self._lock:
            return method(self, *args, **kwargs)
    return locked


class SQLiteStore:
    """SQLite is authoritative; no process-local cache of business objects."""

    def __init__(self, path: str = "dietlens.db") -> None:
        self.path = path
        # FastAPI runs synchronous handlers in a worker pool. The connection is
        # shared by the repository, so serialize transactions explicitly while
        # allowing reads and writes from those worker threads.
        self.db = sqlite3.connect(path, isolation_level=None, timeout=10, check_same_thread=False)
        self.db.execute("PRAGMA journal_mode=WAL")
        self.db.execute("PRAGMA foreign_keys=ON")
        self._lock = threading.RLock()
        self._depth = 0
        self._migrate()

    def _migrate(self) -> None:
        # All migrations, including adoption of an old unversioned DB, are atomic.
        with self.transaction():
            self.db.execute("CREATE TABLE IF NOT EXISTS schema_migrations (version TEXT PRIMARY KEY, applied_at TEXT NOT NULL)")
            for path in sorted(Path(__file__).with_name("migrations").glob("*.sql")):
                if self.db.execute("SELECT 1 FROM schema_migrations WHERE version=?", (path.stem,)).fetchone():
                    continue
                for statement in path.read_text().split(";"):
                    if statement.strip():
                        self.db.execute(statement)
                self.db.execute("INSERT INTO schema_migrations VALUES (?, ?)", (path.stem, now()))

    @contextmanager
    def transaction(self):
        self._lock.acquire()
        outer = self._depth == 0
        if outer:
            self.db.execute("BEGIN IMMEDIATE")
        self._depth += 1
        try:
            yield
            if outer:
                self.db.commit()
        except BaseException:
            if outer:
                self.db.rollback()
            raise
        finally:
            self._depth -= 1
            self._lock.release()

    @staticmethod
    def _context(data: dict) -> Context:
        return Context(**data)

    @classmethod
    def _action(cls, data: dict) -> Action:
        data = dict(data)
        data["context"] = cls._context(data["context"])
        data["decision"] = Decision(data["decision"]) if data.get("decision") else None
        data["execution"] = Execution(data["execution"]) if data.get("execution") else None
        data["created_at"] = datetime.fromisoformat(data["created_at"])
        if data.get("cooldown_until"):
            data["cooldown_until"] = datetime.fromisoformat(data["cooldown_until"])
        if data.get("last_reminded_at"):
            data["last_reminded_at"] = datetime.fromisoformat(data["last_reminded_at"])
        return Action(**data)

    _json = staticmethod(dumps)

    @classmethod
    def _task(cls, data: dict) -> Task:
        data = dict(data)
        data["state"] = TaskState(data["state"])
        data["care_state"] = CareState(data.get("care_state", CareState.WELCOME.value))
        data["context"] = cls._context(data["context"]) if data.get("context") else None
        data["candidates"] = [cls._action(a) for a in data.get("candidates", [])]
        return Task(**data)

    @_sqlite_locked
    def put_profile(self, profile: Profile) -> Profile:
        self.db.execute("INSERT INTO profiles(user_id,payload) VALUES (?, ?) ON CONFLICT(user_id) DO UPDATE SET payload=excluded.payload", (profile.user_id, self._json(profile)))
        return deepcopy(profile)

    @_sqlite_locked
    def get_profile(self, user_id: str) -> Profile | None:
        row = self.db.execute("SELECT payload FROM profiles WHERE user_id=?", (user_id,)).fetchone()
        return Profile(**json.loads(row[0])) if row else None

    @_sqlite_locked
    def save_task(self, task: Task) -> Task:
        with self.transaction():
            row = self.db.execute("SELECT version FROM tasks WHERE task_id=?", (task.task_id,)).fetchone()
            if row and row[0] != task.version:
                raise ToolError("version_conflict")
            if row:
                task.version += 1
            task.updated_at = now()
            self.db.execute("INSERT INTO tasks(task_id,payload,user_id,version,created_at,updated_at) VALUES (?,?,?,?,?,?) ON CONFLICT(task_id) DO UPDATE SET payload=excluded.payload,version=excluded.version,updated_at=excluded.updated_at", (task.task_id, self._json(task), task.user_id, task.version, task.created_at, task.updated_at))
        return deepcopy(task)

    @_sqlite_locked
    def get_task(self, task_id: str) -> Task | None:
        row = self.db.execute("SELECT payload,version,created_at,updated_at FROM tasks WHERE task_id=?", (task_id,)).fetchone()
        if not row:
            return None
        data = json.loads(row[0])
        data.update(version=row[1], created_at=row[2], updated_at=row[3])
        return self._task(data)

    @_sqlite_locked
    def save_action(self, action: Action, operation_key: str) -> Action:
        with self.transaction():
            row = self.db.execute("SELECT payload FROM operations WHERE operation_key=?", (operation_key,)).fetchone()
            if row:
                return self._action(json.loads(row[0]))
            self.db.execute("INSERT INTO actions(action_id,payload,user_id) VALUES (?,?,?) ON CONFLICT(action_id) DO UPDATE SET payload=excluded.payload", (action.action_id, self._json(action), action.user_id))
            self.db.execute("INSERT INTO operations(operation_key,payload) VALUES (?,?)", (operation_key, self._json(action)))
        return deepcopy(action)

    @_sqlite_locked
    def get_action(self, action_id: str) -> Action | None:
        row = self.db.execute("SELECT payload FROM actions WHERE action_id=?", (action_id,)).fetchone()
        return self._action(json.loads(row[0])) if row else None

    @_sqlite_locked
    def list_actions(self, user_id: str) -> list[Action]:
        return [self._action(json.loads(row[0])) for row in self.db.execute("SELECT payload FROM actions WHERE user_id=? ORDER BY rowid", (user_id,))]

    @property
    @_sqlite_locked
    def actions(self) -> dict[str, Action]:
        return {row[0]: self._action(json.loads(row[1])) for row in self.db.execute("SELECT action_id,payload FROM actions")}

    @_sqlite_locked
    def append_event(self, event: Event) -> None:
        self.db.execute("INSERT INTO events(payload) VALUES (?)", (self._json(event),))

    @property
    @_sqlite_locked
    def events(self) -> list[Event]:
        result = []
        for row in self.db.execute("SELECT payload FROM events ORDER BY id"):
            data = json.loads(row[0])
            data["timestamp"] = datetime.fromisoformat(data["timestamp"])
            result.append(Event(**data))
        return result

    @_sqlite_locked
    def list_events(self, task_id: str) -> list[Event]:
        return [e for e in self.events if e.task_id == task_id]

    @_sqlite_locked
    def get_receipt(self, operation_key: str) -> dict | None:
        row = self.db.execute("SELECT payload FROM operations WHERE operation_key=?", (operation_key,)).fetchone()
        return json.loads(row[0]) if row else None

    @_sqlite_locked
    def save_receipt(self, operation_key: str, receipt: dict) -> None:
        self.db.execute("INSERT INTO operations(operation_key,payload) VALUES (?,?)", (operation_key, self._json(receipt)))

    @_sqlite_locked
    def save_profile_draft(self, draft: ProfileDraft) -> None:
        self.db.execute("INSERT INTO profile_drafts(task_id,user_id,payload) VALUES (?,?,?)", (draft.task_id, draft.user_id, self._json(draft)))

    @_sqlite_locked
    def get_profile_draft(self, task_id: str) -> ProfileDraft | None:
        row = self.db.execute("SELECT payload FROM profile_drafts WHERE task_id=?", (task_id,)).fetchone()
        if not row:
            return None
        data = json.loads(row[0])
        data["proposed"] = Profile(**data["proposed"])
        return ProfileDraft(**data)

    @_sqlite_locked
    def list_profile_versions(self, user_id: str) -> list[Profile]:
        return [Profile(**json.loads(row[0])) for row in self.db.execute("SELECT payload FROM profile_versions WHERE user_id=? ORDER BY version", (user_id,))]

    @_sqlite_locked
    def put_profile_version(self, profile: Profile, expected_version: int, task_id: str, operation_key: str) -> None:
        with self.transaction():
            previous = self.get_profile(profile.user_id)
            if (previous.version if previous else 0) != expected_version:
                raise ToolError("version_conflict")
            if profile.version != expected_version + 1:
                raise ToolError("invalid_profile_version")
            if previous:
                self.db.execute("INSERT OR IGNORE INTO profile_versions VALUES (?,?,?,?,?,?,?)", (previous.user_id, previous.version, self._json(previous), None, "legacy-profile", now(), now()))
            self.db.execute("INSERT INTO profile_versions VALUES (?,?,?,?,?,?,?)", (profile.user_id, profile.version, self._json(profile), task_id, operation_key, profile.updated_at, profile.updated_at))
            self.put_profile(profile)
            for scope, granted in profile.consents.items():
                if previous is None or previous.consents.get(scope, False) != granted:
                    self.db.execute("INSERT INTO consents VALUES (?,?,?,?,?,?,?,?,?)", (profile.user_id, scope, profile.version, int(granted), "user_confirmation", task_id, operation_key, profile.updated_at, profile.updated_at))

    @_sqlite_locked
    def list_consent_events(self, user_id: str) -> list[dict]:
        columns = ["user_id", "scope", "profile_version", "granted", "source", "task_id", "operation_key", "created_at", "updated_at"]
        return [{**dict(zip(columns, row)), "granted": bool(row[3])} for row in self.db.execute("SELECT * FROM consents WHERE user_id=? ORDER BY profile_version,scope", (user_id,))]

    @_sqlite_locked
    def save_food_observation(self, observation: FoodObservation) -> FoodObservation:
        with self.transaction():
            self.db.execute("INSERT INTO food_observations(observation_id,user_id,task_id,source,source_id,status,payload,retrieved_at,created_at) VALUES (?,?,?,?,?,?,?,?,?)", (observation.observation_id, observation.user_id, observation.task_id, observation.record.get("source", ""), observation.record.get("source_id"), observation.status, self._json(observation), observation.record.get("retrieved_at", observation.created_at), observation.created_at))
        return deepcopy(observation)

    @_sqlite_locked
    def list_food_observations(self, user_id: str) -> list[FoodObservation]:
        result = []
        for row in self.db.execute("SELECT payload FROM food_observations WHERE user_id=? ORDER BY created_at", (user_id,)):
            result.append(FoodObservation(**json.loads(row[0])))
        return result

    @classmethod
    def _plan(cls, data: dict) -> Plan:
        data = dict(data); data["items"] = [PlanItem(**item) for item in data.get("items", [])]
        return Plan(**data)

    @classmethod
    def _shopping(cls, data: dict) -> ShoppingList:
        data = dict(data); data["items"] = [ShoppingListItem(**item) for item in data.get("items", [])]
        return ShoppingList(**data)

    @_sqlite_locked
    def save_plan(self, plan: Plan) -> Plan:
        with self.transaction():
            row = self.db.execute("SELECT version FROM plans WHERE plan_id=?", (plan.plan_id,)).fetchone()
            if row and row[0] != plan.version:
                raise ToolError("version_conflict")
            if row:
                plan.version += 1
            plan.updated_at = now()
            self.db.execute("INSERT INTO plans(plan_id,user_id,version,status,payload,created_at,updated_at) VALUES (?,?,?,?,?,?,?) ON CONFLICT(plan_id) DO UPDATE SET user_id=excluded.user_id,version=excluded.version,status=excluded.status,payload=excluded.payload,updated_at=excluded.updated_at", (plan.plan_id, plan.user_id, plan.version, plan.status, self._json(plan), plan.created_at, plan.updated_at))
        return deepcopy(plan)

    @_sqlite_locked
    def get_plan(self, plan_id: str) -> Plan | None:
        row = self.db.execute("SELECT payload,version,status,created_at,updated_at FROM plans WHERE plan_id=?", (plan_id,)).fetchone()
        if not row: return None
        data = json.loads(row[0]); data.update(version=row[1], status=row[2], created_at=row[3], updated_at=row[4]); return self._plan(data)

    @_sqlite_locked
    def list_plans(self, user_id: str) -> list[Plan]:
        return [self._plan(json.loads(row[0]) | {"version": row[1], "status": row[2], "created_at": row[3], "updated_at": row[4]}) for row in self.db.execute("SELECT payload,version,status,created_at,updated_at FROM plans WHERE user_id=? ORDER BY updated_at", (user_id,))]

    @_sqlite_locked
    def save_shopping_list(self, shopping_list: ShoppingList) -> ShoppingList:
        with self.transaction():
            self.db.execute("INSERT INTO shopping_lists(list_id,user_id,plan_id,plan_version,status,payload,created_at,updated_at) VALUES (?,?,?,?,?,?,?,?) ON CONFLICT(list_id) DO UPDATE SET status=excluded.status,payload=excluded.payload,updated_at=excluded.updated_at", (shopping_list.list_id, shopping_list.user_id, shopping_list.plan_id, shopping_list.plan_version, shopping_list.status, self._json(shopping_list), shopping_list.created_at, shopping_list.updated_at))
        return deepcopy(shopping_list)

    @_sqlite_locked
    def get_shopping_list(self, list_id: str) -> ShoppingList | None:
        row = self.db.execute("SELECT payload,status,created_at,updated_at FROM shopping_lists WHERE list_id=?", (list_id,)).fetchone()
        if not row: return None
        data=json.loads(row[0]); data.update(status=row[1],created_at=row[2],updated_at=row[3]); return self._shopping(data)

    @_sqlite_locked
    def list_shopping_lists(self, plan_id: str) -> list[ShoppingList]:
        return [self.get_shopping_list(row[0]) for row in self.db.execute("SELECT list_id FROM shopping_lists WHERE plan_id=? ORDER BY created_at", (plan_id,))]

    @_sqlite_locked
    def save_inventory_item(self, item: InventoryItem) -> InventoryItem:
        with self.transaction():
            row=self.db.execute("SELECT user_id,version FROM inventory_items WHERE inventory_id=?", (item.inventory_id,)).fetchone()
            if row and row[0] != item.user_id: raise ToolError("user_ownership_required")
            if item.version != (row[1] if row else 1): raise ToolError("version_conflict")
            duplicate=self.db.execute("SELECT inventory_id FROM inventory_items WHERE user_id=? AND ingredient_id=? AND unit=? AND inventory_id<>?", (item.user_id,item.ingredient_id,item.unit,item.inventory_id)).fetchone()
            if duplicate: raise ToolError("inventory_duplicate")
            if row: item.version += 1
            item.updated_at=now()
            self.db.execute("INSERT INTO inventory_items(inventory_id,user_id,ingredient_id,unit,version,payload,created_at,updated_at) VALUES (?,?,?,?,?,?,?,?) ON CONFLICT(inventory_id) DO UPDATE SET user_id=excluded.user_id,ingredient_id=excluded.ingredient_id,unit=excluded.unit,version=excluded.version,payload=excluded.payload,updated_at=excluded.updated_at", (item.inventory_id,item.user_id,item.ingredient_id,item.unit,item.version,self._json(item),item.updated_at,item.updated_at))
        return deepcopy(item)

    @_sqlite_locked
    def list_inventory(self, user_id: str) -> list[InventoryItem]:
        return [InventoryItem(**json.loads(row[0])) for row in self.db.execute("SELECT payload FROM inventory_items WHERE user_id=? ORDER BY updated_at", (user_id,))]

    @_sqlite_locked
    def list_tasks(self, user_id: str) -> list[Task]:
        return [self._task(json.loads(row[0]) | {"version": row[1], "created_at": row[2], "updated_at": row[3]})
                for row in self.db.execute("SELECT payload,version,created_at,updated_at FROM tasks WHERE user_id=? ORDER BY updated_at", (user_id,))]

    @_sqlite_locked
    def delete_user_data(self, user_id: str) -> dict[str, int]:
        tables = ["profiles", "profile_versions", "profile_drafts", "consents", "tasks", "food_observations",
                  "actions", "events", "plans", "shopping_lists", "inventory_items", "meal_records", "meal_record_versions"]
        counts = {}
        with self.transaction():
            for table in tables:
                if table == "events":
                    row = self.db.execute("SELECT count(*) FROM events WHERE json_extract(payload, '$.user_id')=?", (user_id,)).fetchone()
                    self.db.execute("DELETE FROM events WHERE json_extract(payload, '$.user_id')=?", (user_id,))
                elif table in {"profile_versions", "consents", "food_observations", "plans", "shopping_lists", "inventory_items", "meal_records", "meal_record_versions", "profiles"}:
                    row = self.db.execute(f"SELECT count(*) FROM {table} WHERE user_id=?", (user_id,)).fetchone()
                    self.db.execute(f"DELETE FROM {table} WHERE user_id=?", (user_id,))
                else:
                    row = self.db.execute(f"SELECT count(*) FROM {table} WHERE user_id=?", (user_id,)).fetchone()
                    self.db.execute(f"DELETE FROM {table} WHERE user_id=?", (user_id,))
                counts[table] = row[0]
            self.db.execute("DELETE FROM operations WHERE json_extract(payload, '$.user_id')=? OR operation_key LIKE ? OR operation_key LIKE ?", (user_id, f"profile:{user_id}:%", f"start:{user_id}:%"))
        return counts

    @_sqlite_locked
    def save_meal_record(self, record: MealRecord, operation_key: str) -> MealRecord:
        with self.transaction():
            row = self.db.execute("SELECT version FROM meal_records WHERE record_id=?", (record.record_id,)).fetchone()
            if row and row[0] + 1 != record.version:
                raise ToolError("version_conflict")
            self.db.execute("INSERT INTO meal_records(record_id,user_id,version,status,payload,created_at,updated_at) VALUES (?,?,?,?,?,?,?) ON CONFLICT(record_id) DO UPDATE SET user_id=excluded.user_id,version=excluded.version,status=excluded.status,payload=excluded.payload,updated_at=excluded.updated_at",
                            (record.record_id, record.user_id, record.version, record.status, self._json(record), record.created_at, record.updated_at))
            self.db.execute("INSERT INTO meal_record_versions(record_id,version,user_id,operation_key,payload,created_at) VALUES (?,?,?,?,?,?)",
                            (record.record_id, record.version, record.user_id, operation_key, self._json(record), record.updated_at))
        return deepcopy(record)

    @_sqlite_locked
    def get_meal_record(self, record_id: str) -> MealRecord | None:
        row = self.db.execute("SELECT payload FROM meal_records WHERE record_id=?", (record_id,)).fetchone()
        return MealRecord(**json.loads(row[0])) if row else None

    @_sqlite_locked
    def list_meal_records(self, user_id: str, *, include_deleted: bool = False) -> list[MealRecord]:
        query = "SELECT payload FROM meal_records WHERE user_id=?"
        params: tuple[Any, ...] = (user_id,)
        if not include_deleted:
            query += " AND status <> 'deleted'"
        query += " ORDER BY updated_at"
        return [MealRecord(**json.loads(row[0])) for row in self.db.execute(query, params)]

    @_sqlite_locked
    def close(self) -> None:
        self.db.close()
