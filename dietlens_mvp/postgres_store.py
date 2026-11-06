"""Supabase Postgres repository.

This adapter uses the database connection string, not a browser key. It keeps the
same repository contract as SQLite so Harness remains the authority for writes.
"""
from __future__ import annotations

from contextlib import contextmanager
from copy import deepcopy
from datetime import datetime, timezone
import json
from typing import Any
import os

from .errors import ToolError
from .models import Action, CareState, Context, Decision, Event, Execution, FoodObservation, InventoryItem, MealRecord, Plan, PlanItem, Profile, ProfileDraft, ShoppingList, ShoppingListItem, Task, TaskState
from .serialization import dumps
from .proxy_tunnel import ProxyTunnel


def _require_psycopg():
    try:
        import psycopg
    except ImportError as exc:
        raise RuntimeError("install dietlens[cloud] to use PostgresStore") from exc
    return psycopg


class PostgresStore:
    """Postgres/Supabase implementation of the Repository protocol."""

    def __init__(self, dsn: str, *, connect_timeout: int = 10) -> None:
        if not dsn or any(c in dsn for c in "\r\n"):
            raise ToolError("invalid_database_config")
        psycopg = _require_psycopg()
        self.path = "supabase"
        self._tunnel = None
        params = psycopg.conninfo.conninfo_to_dict(dsn)
        target_host = params.get("host", "")
        target_port = int(params.get("port") or 5432)
        # The environment proxy can reach the hosted API and accepts CONNECT for
        # Postgres; use it only when a direct socket cannot be assumed.
        if target_host not in {"localhost", "127.0.0.1", "::1"} and (os.getenv("HTTPS_PROXY") or os.getenv("https_proxy")):
            self._tunnel = ProxyTunnel(target_host, target_port)
            self._tunnel.__enter__()
            params["hostaddr"] = "127.0.0.1"
            params["port"] = str(self._tunnel.port)
            params.setdefault("sslmode", "require")
            # Keep host for server-name/certificate identity where libpq supports it.
            dsn = psycopg.conninfo.make_conninfo(**params)
        self.db = psycopg.connect(dsn, connect_timeout=connect_timeout, autocommit=False)
        self._depth = 0

    @staticmethod
    def _json(value: Any) -> Any:
        # psycopg needs an explicit JSONB wrapper for Python dict/list values.
        from psycopg.types.json import Jsonb
        return Jsonb(json.loads(dumps(value)))

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

    @classmethod
    def _task(cls, data: dict) -> Task:
        data = dict(data)
        data["state"] = TaskState(data["state"])
        data["care_state"] = CareState(data.get("care_state", CareState.WELCOME.value))
        data["context"] = cls._context(data["context"]) if data.get("context") else None
        data["candidates"] = [cls._action(a) for a in data.get("candidates", [])]
        return Task(**data)

    @contextmanager
    def transaction(self):
        outer = self._depth == 0
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

    def _one(self, sql: str, params=()):
        with self.db.cursor() as cursor:
            cursor.execute(sql, params)
            return cursor.fetchone()

    def put_profile(self, profile: Profile) -> Profile:
        self.db.execute("""insert into profiles(user_id,version,payload,created_at,updated_at)
            values (%s,%s,%s,%s,%s) on conflict(user_id) do update set version=excluded.version,payload=excluded.payload,updated_at=now()""",
            (profile.user_id, profile.version, self._json(profile), profile.created_at, profile.updated_at))
        self.db.commit()
        return deepcopy(profile)

    def get_profile(self, user_id: str) -> Profile | None:
        row = self._one("select payload from profiles where user_id=%s", (user_id,))
        return Profile(**row[0]) if row else None

    def save_task(self, task: Task) -> Task:
        with self.transaction():
            row = self._one("select version from tasks where task_id=%s for update", (task.task_id,))
            if row and row[0] != task.version:
                raise ToolError("version_conflict")
            if row:
                task.version += 1
            self.db.execute("""insert into tasks(task_id,user_id,task_type,state,version,payload,created_at,updated_at)
                values (%s,%s,%s,%s,%s,%s,%s,%s)
                on conflict(task_id) do update set user_id=excluded.user_id,task_type=excluded.task_type,state=excluded.state,version=excluded.version,payload=excluded.payload,updated_at=now()""",
                (task.task_id, task.user_id, task.task_type, task.state.value, task.version, self._json(task), task.created_at, task.updated_at))
        return deepcopy(task)

    def get_task(self, task_id: str) -> Task | None:
        row = self._one("select payload,version,created_at,updated_at from tasks where task_id=%s", (task_id,))
        if not row:
            return None
        data = dict(row[0]); data.update(version=row[1], created_at=row[2].isoformat() if hasattr(row[2], "isoformat") else row[2], updated_at=row[3].isoformat() if hasattr(row[3], "isoformat") else row[3])
        return self._task(data)

    def save_action(self, action: Action, operation_key: str) -> Action:
        with self.transaction():
            row = self._one("select payload from operations where operation_key=%s for update", (operation_key,))
            if row:
                return self._action(row[0])
            payload = self._json(action)
            self.db.execute("insert into actions(action_id,user_id,task_id,payload) values (%s,%s,%s,%s) on conflict(action_id) do update set payload=excluded.payload", (action.action_id, action.user_id, None, payload))
            self.db.execute("insert into operations(operation_key,user_id,request_hash,payload) values (%s,%s,%s,%s)", (operation_key, action.user_id, operation_key, payload))
        return deepcopy(action)

    def get_action(self, action_id: str) -> Action | None:
        row = self._one("select payload from actions where action_id=%s", (action_id,))
        return self._action(row[0]) if row else None

    def list_actions(self, user_id: str) -> list[Action]:
        with self.db.cursor() as cursor:
            cursor.execute("select payload from actions where user_id=%s order by created_at", (user_id,))
            return [self._action(row[0]) for row in cursor.fetchall()]

    @property
    def actions(self) -> dict[str, Action]:
        with self.db.cursor() as cursor:
            cursor.execute("select action_id,payload from actions")
            return {row[0]: self._action(row[1]) for row in cursor.fetchall()}

    def append_event(self, event: Event) -> None:
        self.db.execute("insert into events(task_id,user_id,event_type,payload,operation_key,created_at) values (%s,%s,%s,%s,%s,%s)", (event.task_id, event.user_id, event.event_type, self._json(event.payload), event.operation_key, event.timestamp))

    @property
    def events(self) -> list[Event]:
        with self.db.cursor() as cursor:
            cursor.execute("select task_id,user_id,event_type,payload,operation_key,created_at from events order by id")
            return [Event(row[2], row[0], row[1], row[3], row[4], row[5]) for row in cursor.fetchall()]

    def list_events(self, task_id: str) -> list[Event]:
        return [event for event in self.events if event.task_id == task_id]

    def get_receipt(self, operation_key: str) -> dict | None:
        row = self._one("select payload from operations where operation_key=%s", (operation_key,))
        return row[0] if row else None

    def save_receipt(self, operation_key: str, receipt: dict[str, Any]) -> None:
        user_id = receipt.get("user_id", "system")
        self.db.execute("insert into operations(operation_key,user_id,request_hash,payload) values (%s,%s,%s,%s) on conflict(operation_key) do nothing", (operation_key, user_id, operation_key, self._json(receipt)))

    def save_profile_draft(self, draft: ProfileDraft) -> None:
        self.db.execute("insert into profile_drafts(task_id,user_id,expected_version,payload,changes) values (%s,%s,%s,%s,%s)", (draft.task_id, draft.user_id, draft.expected_version, self._json(draft.proposed), self._json(draft.changes)))

    def get_profile_draft(self, task_id: str) -> ProfileDraft | None:
        row = self._one("select task_id,user_id,expected_version,payload,changes from profile_drafts where task_id=%s", (task_id,))
        if not row:
            return None
        return ProfileDraft(row[0], row[1], row[2], Profile(**row[3]), row[4])

    def list_profile_versions(self, user_id: str) -> list[Profile]:
        with self.db.cursor() as cursor:
            cursor.execute("select payload from profile_versions where user_id=%s order by version", (user_id,))
            return [Profile(**row[0]) for row in cursor.fetchall()]

    def put_profile_version(self, profile: Profile, expected_version: int, task_id: str, operation_key: str) -> None:
        # Direct Postgres transactions preserve the Harness event/task atomic boundary.
        with self.transaction():
            row = self._one("select version,payload from profiles where user_id=%s for update", (profile.user_id,))
            current = row[0] if row else 0
            if current != expected_version or profile.version != expected_version + 1:
                raise ToolError("version_conflict")
            if row:
                self.db.execute("insert into profile_versions(user_id,version,payload,task_id,operation_key) values (%s,%s,%s,%s,%s) on conflict do nothing", (profile.user_id, current, row[1], None, "legacy-profile"))
            self.db.execute("insert into profile_versions(user_id,version,payload,task_id,operation_key) values (%s,%s,%s,%s,%s)", (profile.user_id, profile.version, self._json(profile), task_id, operation_key))
            self.db.execute("""insert into profiles(user_id,version,payload,created_at,updated_at) values (%s,%s,%s,%s,%s)
                on conflict(user_id) do update set version=excluded.version,payload=excluded.payload,updated_at=now()""", (profile.user_id, profile.version, self._json(profile), profile.created_at, profile.updated_at))
            previous = Profile(**row[1]) if row else None
            for scope, granted in profile.consents.items():
                if previous is None or previous.consents.get(scope) != granted:
                    self.db.execute("insert into consents(user_id,scope,profile_version,granted,source,task_id,operation_key) values (%s,%s,%s,%s,%s,%s,%s)", (profile.user_id, scope, profile.version, granted, "user_confirmation", task_id, operation_key))

    def list_consent_events(self, user_id: str) -> list[dict]:
        with self.db.cursor() as cursor:
            cursor.execute("select user_id,scope,profile_version,granted,source,task_id,operation_key,created_at,updated_at from consents where user_id=%s order by profile_version,scope", (user_id,))
            columns = ["user_id", "scope", "profile_version", "granted", "source", "task_id", "operation_key", "created_at", "updated_at"]
            return [dict(zip(columns, row)) for row in cursor.fetchall()]

    def save_food_observation(self, observation: FoodObservation) -> FoodObservation:
        self.db.execute("insert into food_observations(observation_id,user_id,task_id,source,source_id,status,payload,retrieved_at,created_at) values (%s,%s,%s,%s,%s,%s,%s,%s,%s)", (observation.observation_id, observation.user_id, observation.task_id, observation.record.get("source", ""), observation.record.get("source_id"), observation.status, self._json(observation), observation.record.get("retrieved_at", observation.created_at), observation.created_at))
        self.db.commit()
        return deepcopy(observation)

    def list_food_observations(self, user_id: str) -> list[FoodObservation]:
        with self.db.cursor() as cursor:
            cursor.execute("select payload from food_observations where user_id=%s order by created_at", (user_id,))
            return [FoodObservation(**row[0]) for row in cursor.fetchall()]

    @classmethod
    def _plan(cls, data: dict) -> Plan:
        data=dict(data); data["items"]=[PlanItem(**item) for item in data.get("items", [])]; return Plan(**data)

    @classmethod
    def _shopping(cls, data: dict) -> ShoppingList:
        data=dict(data); data["items"]=[ShoppingListItem(**item) for item in data.get("items", [])]; return ShoppingList(**data)

    def save_plan(self, plan: Plan) -> Plan:
        with self.transaction():
            row=self._one("select version from plans where plan_id=%s for update",(plan.plan_id,))
            if row and row[0] != plan.version: raise ToolError("version_conflict")
            if row: plan.version += 1
            self.db.execute("insert into plans(plan_id,user_id,version,status,payload,created_at,updated_at) values (%s,%s,%s,%s,%s,%s,%s) on conflict(plan_id) do update set version=excluded.version,status=excluded.status,payload=excluded.payload,updated_at=now()",(plan.plan_id,plan.user_id,plan.version,plan.status,self._json(plan),plan.created_at,plan.updated_at))
        return deepcopy(plan)

    def get_plan(self, plan_id: str) -> Plan | None:
        row=self._one("select payload,version,status,created_at,updated_at from plans where plan_id=%s",(plan_id,))
        if not row:return None
        data=dict(row[0]);data.update(version=row[1],status=row[2],created_at=row[3].isoformat() if hasattr(row[3],'isoformat') else row[3],updated_at=row[4].isoformat() if hasattr(row[4],'isoformat') else row[4]);return self._plan(data)

    def list_plans(self, user_id: str) -> list[Plan]:
        with self.db.cursor() as c:
            c.execute("select payload,version,status,created_at,updated_at from plans where user_id=%s order by updated_at",(user_id,)); rows=c.fetchall()
        result=[]
        for row in rows:
            data=dict(row[0]);data.update(version=row[1],status=row[2],created_at=row[3].isoformat() if hasattr(row[3],'isoformat') else row[3],updated_at=row[4].isoformat() if hasattr(row[4],'isoformat') else row[4]);result.append(self._plan(data))
        return result

    def save_shopping_list(self, shopping_list: ShoppingList) -> ShoppingList:
        with self.transaction():
            self.db.execute("insert into shopping_lists(list_id,user_id,plan_id,plan_version,status,payload,created_at,updated_at) values (%s,%s,%s,%s,%s,%s,%s,%s) on conflict(list_id) do update set status=excluded.status,payload=excluded.payload,updated_at=now()",(shopping_list.list_id,shopping_list.user_id,shopping_list.plan_id,shopping_list.plan_version,shopping_list.status,self._json(shopping_list),shopping_list.created_at,shopping_list.updated_at))
        return deepcopy(shopping_list)

    def get_shopping_list(self, list_id: str) -> ShoppingList | None:
        row=self._one("select payload,status,created_at,updated_at from shopping_lists where list_id=%s",(list_id,))
        if not row:return None
        data=dict(row[0]);data.update(status=row[1],created_at=row[2].isoformat() if hasattr(row[2],'isoformat') else row[2],updated_at=row[3].isoformat() if hasattr(row[3],'isoformat') else row[3]);return self._shopping(data)

    def list_shopping_lists(self, plan_id: str) -> list[ShoppingList]:
        with self.db.cursor() as c:
            c.execute("select list_id from shopping_lists where plan_id=%s order by created_at",(plan_id,)); ids=[row[0] for row in c.fetchall()]
        return [self.get_shopping_list(item_id) for item_id in ids]

    def save_inventory_item(self, item: InventoryItem) -> InventoryItem:
        with self.transaction():
            row=self._one("select user_id,version from inventory_items where inventory_id=%s for update",(item.inventory_id,))
            if row and row[0] != item.user_id:raise ToolError("user_ownership_required")
            if item.version != (row[1] if row else 1):raise ToolError("version_conflict")
            duplicate=self._one("select inventory_id from inventory_items where user_id=%s and ingredient_id=%s and unit=%s and inventory_id<>%s",(item.user_id,item.ingredient_id,item.unit,item.inventory_id))
            if duplicate:raise ToolError("inventory_duplicate")
            if row:item.version += 1
            item.updated_at=datetime.now(timezone.utc).isoformat()
            cursor=self.db.execute("insert into inventory_items(inventory_id,user_id,ingredient_id,unit,version,payload,created_at,updated_at) values (%s,%s,%s,%s,%s,%s,%s,%s) on conflict(inventory_id) do update set ingredient_id=excluded.ingredient_id,unit=excluded.unit,version=excluded.version,payload=excluded.payload,updated_at=now() where inventory_items.user_id=excluded.user_id and inventory_items.version=excluded.version-1",(item.inventory_id,item.user_id,item.ingredient_id,item.unit,item.version,self._json(item),item.updated_at,item.updated_at))
            if cursor.rowcount != 1:raise ToolError("version_conflict")
        return deepcopy(item)

    def list_inventory(self, user_id: str) -> list[InventoryItem]:
        with self.db.cursor() as c:
            c.execute("select payload from inventory_items where user_id=%s order by updated_at",(user_id,));return [InventoryItem(**row[0]) for row in c.fetchall()]

    def list_tasks(self, user_id: str) -> list[Task]:
        with self.db.cursor() as c:
            c.execute("select payload,version,created_at,updated_at from tasks where user_id=%s order by updated_at", (user_id,)); rows=c.fetchall()
        result=[]
        for row in rows:
            data=dict(row[0]); data.update(version=row[1], created_at=row[2].isoformat() if hasattr(row[2],'isoformat') else row[2], updated_at=row[3].isoformat() if hasattr(row[3],'isoformat') else row[3]); result.append(self._task(data))
        return result

    def delete_user_data(self, user_id: str) -> dict[str, int]:
        tables = ["profiles", "profile_versions", "profile_drafts", "consents", "tasks", "food_observations", "actions", "events", "plans", "shopping_lists", "inventory_items", "meal_records", "meal_record_versions"]
        counts={}
        with self.transaction():
            for table in tables:
                row=self._one(f"select count(*) from {table} where user_id=%s", (user_id,)); counts[table]=row[0]
                self.db.execute(f"delete from {table} where user_id=%s", (user_id,))
            self.db.execute("delete from operations where user_id=%s", (user_id,))
        return counts

    def save_meal_record(self, record: MealRecord, operation_key: str) -> MealRecord:
        with self.transaction():
            row = self._one("select version from meal_records where record_id=%s for update", (record.record_id,))
            if row and row[0] + 1 != record.version:
                raise ToolError("version_conflict")
            self.db.execute("insert into meal_records(record_id,user_id,version,status,payload,created_at,updated_at) values (%s,%s,%s,%s,%s,%s,%s) on conflict(record_id) do update set user_id=excluded.user_id,version=excluded.version,status=excluded.status,payload=excluded.payload,updated_at=excluded.updated_at",
                            (record.record_id, record.user_id, record.version, record.status, self._json(record), record.created_at, record.updated_at))
            self.db.execute("insert into meal_record_versions(record_id,version,user_id,operation_key,payload,created_at) values (%s,%s,%s,%s,%s,%s)",
                            (record.record_id, record.version, record.user_id, operation_key, self._json(record), record.updated_at))
        return deepcopy(record)

    def get_meal_record(self, record_id: str) -> MealRecord | None:
        row = self._one("select payload from meal_records where record_id=%s", (record_id,))
        return MealRecord(**row[0]) if row else None

    def list_meal_records(self, user_id: str, *, include_deleted: bool = False) -> list[MealRecord]:
        sql = "select payload from meal_records where user_id=%s"
        if not include_deleted:
            sql += " and status <> 'deleted'"
        sql += " order by (payload->>'meal_date'), updated_at"
        with self.db.cursor() as c:
            c.execute(sql, (user_id,))
            return [MealRecord(**row[0]) for row in c.fetchall()]

    def close(self) -> None:
        self.db.close()
        if self._tunnel:
            self._tunnel.__exit__(None, None, None)
