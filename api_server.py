"""FastAPI boundary for the React client.

The server owns the Harness and is the only component allowed to write business state.
Set SUPABASE_DB_URL to use Postgres/Supabase; otherwise it uses SQLite for local work.
"""
from __future__ import annotations

from dataclasses import asdict
import os
from typing import Any

try:
    from fastapi import FastAPI, HTTPException, Request
    from fastapi.middleware.cors import CORSMiddleware
    from pydantic import BaseModel, Field
except ImportError as exc:  # keeps core CLI installation light
    raise RuntimeError("install dietlens[server] to run api_server.py") from exc

from dietlens_mvp import DietLensAgent, Harness, SQLiteStore, PostgresStore
from dietlens_mvp.config import Settings
from dietlens_mvp.errors import ToolError
from dietlens_mvp.model_provider import StubModelProvider
from dietlens_mvp.models import Decision, Execution, InventoryItem, MealRecord, PlanItem
from dietlens_mvp.meal_records import MealRecordService
from dietlens_mvp.preferences import suggestions
from dietlens_mvp.comprehensive_review import ComprehensiveReviewService
from dietlens_mvp.food import search_result, summarize_record
from dietlens_mvp.sources import FoodSourceRegistry
from dietlens_mvp.portability import DataPortabilityService
from dietlens_mvp.planning import PlanningService
from dietlens_mvp.auth import SupabaseAuthenticator

settings = Settings.from_env(os.getenv("DIETLENS_ENV_FILE", ".env"))
storage_mode = os.getenv("DIETLENS_STORAGE", "auto").lower()
if storage_mode == "sqlite" or not settings.supabase_db_url:
    store = SQLiteStore(settings.database_path)
elif storage_mode == "postgres":
    store = PostgresStore(settings.supabase_db_url)
else:
    try:
        store = PostgresStore(settings.supabase_db_url)
    except Exception:
        # Hosted HTTPS is usable even when this environment cannot keep a raw
        # 5432 tunnel open. Keep the local interaction demo available; cloud
        # mode remains opt-in with DIETLENS_STORAGE=postgres.
        store = SQLiteStore(settings.database_path)
provider = settings.create_provider() if settings.api_key and settings.model_name else StubModelProvider()
agent = DietLensAgent(Harness(store, provider))
planning = PlanningService(store)
meal_records = MealRecordService(store)
comprehensive_review = ComprehensiveReviewService(store)
food_registry = FoodSourceRegistry()
portability = DataPortabilityService(store)
authenticator = SupabaseAuthenticator(settings.supabase_url, settings.supabase_publishable_key) if settings.auth_mode == "supabase" else None
app = FastAPI(title="DietLens API", version="0.3.0")
app.add_middleware(CORSMiddleware, allow_origins=[os.getenv("DIETLENS_WEB_ORIGIN", "http://localhost:5173")], allow_methods=["*"], allow_headers=["*"])


class TaskCreate(BaseModel):
    user_id: str = Field(min_length=1, max_length=128)
    task_type: str = Field(default="micro_action", pattern="^(micro_action|quick_log|plan|explore|reflect)$")


class ProfilePreviewBody(BaseModel):
    user_id: str = Field(min_length=1, max_length=128)
    changes: dict[str, Any] = Field(default_factory=dict)
    expected_version: int = Field(default=0, ge=0)
    consents: dict[str, bool] = Field(default_factory=dict)


class ProfileConfirmBody(BaseModel):
    user_id: str = Field(min_length=1, max_length=128)
    task_id: str = Field(min_length=1, max_length=128)
    operation_key: str = Field(min_length=1, max_length=256)
    expected_version: int = Field(ge=0)


class Message(BaseModel):
    content: str = Field(min_length=1, max_length=4000)


class ContextConfirm(BaseModel):
    meal: str = Field(min_length=1, max_length=80)
    options: list[str] = Field(min_length=1, max_length=20)


class DecisionBody(BaseModel):
    action_index: int = Field(default=0, ge=0, le=20)
    decision: str = Field(default="adopt", pattern="^(adopt|skip)$")


class FeedbackBody(BaseModel):
    execution: str = Field(pattern="^(complete|partial|not_done|unknown)$")
    note: str = Field(default="", max_length=1000)


class FeedbackCorrectionBody(FeedbackBody):
    operation_key: str | None = None
    expected_version: int | None = Field(default=None, ge=1)


class PlanItemBody(BaseModel):
    item_id: str = Field(min_length=1, max_length=128)
    meal_date: str
    meal_slot: str
    name: str
    ingredient_id: str
    ingredient_name: str = ""
    quantity: float = Field(ge=0)
    unit: str
    servings: int = Field(default=1, ge=1, le=20)


class PlanBody(BaseModel):
    user_id: str = Field(min_length=1, max_length=128)
    start_date: str
    days: int = Field(ge=1, le=7)
    servings: int = Field(ge=1, le=20)
    items: list[PlanItemBody] = Field(min_length=1, max_length=21)


class InventoryBody(BaseModel):
    inventory_id: str
    user_id: str
    ingredient_id: str
    name: str
    quantity: float = Field(ge=0)
    unit: str
    version: int = Field(default=1, ge=1)


class PortabilityBody(BaseModel):
    user_id: str = Field(min_length=1, max_length=128)
    confirmed: bool = False


class MealRecordBody(BaseModel):
    record_id: str | None = None
    user_id: str = Field(min_length=1, max_length=128)
    meal_date: str
    meal_slot: str
    name: str
    ingredient_id: str = ""
    quantity: float | None = Field(default=None, ge=0)
    unit: str | None = None
    eaten_at: str | None = None
    source: str = "user_self_report"
    plan_id: str | None = None
    plan_item_id: str | None = None


class MealRecordConfirmBody(MealRecordBody):
    record_id: str = Field(min_length=1, max_length=128)


class QuickLogConfirmBody(MealRecordConfirmBody):
    task_id: str = Field(min_length=1, max_length=128)


class MealRecordPatch(BaseModel):
    expected_version: int = Field(ge=1)
    operation_key: str | None = None
    changes: dict[str, Any] = Field(default_factory=dict)



def error(exc: ToolError) -> HTTPException:
    status = 403 if exc.code == "user_ownership_required" else 409 if exc.code in {"version_conflict", "operation_conflict", "profile_changed", "inventory_duplicate"} else 400
    return HTTPException(status_code=status, detail={"code": exc.code})


def authenticated_user(request: Request, claimed_user_id: str) -> str:
    """Return the caller identity, enforcing body/query/path ownership in Auth mode."""
    if authenticator is None:
        return claimed_user_id
    token = request.headers.get("Authorization", "")
    if not token.lower().startswith("bearer "):
        raise HTTPException(status_code=401, detail={"code": "authentication_required"})
    try:
        identity = authenticator.user_id(token[7:].strip())
    except ToolError as exc:
        raise error(exc)
    if identity != claimed_user_id:
        raise HTTPException(status_code=403, detail={"code": "user_ownership_required"})
    return identity


def authenticated_task(request: Request, task_id: str):
    task = agent.harness._task(task_id)
    authenticated_user(request, task.user_id)
    return task


def task_json(task):
    return asdict(task)


@app.get("/api/status")
def public_status():
    return {"auth_mode": settings.auth_mode}


@app.get("/health")
def health():
    return {"ok": True, "storage": "supabase" if isinstance(store, PostgresStore) else "sqlite"}


@app.get("/api/tasks")
def recent_tasks(request: Request, user_id: str):
    user_id = authenticated_user(request, user_id)
    # The task inbox is intentionally cross-flow: quick logs, plans, food
    # questions and micro-actions can all be paused and resumed from one place.
    tasks = [task for task in store.list_tasks(user_id) if task.task_type != "profile_update"]
    return [task_json(task) for task in sorted(tasks, key=lambda task: task.updated_at, reverse=True)[:20]]


@app.post("/api/tasks")
def create_task(body: TaskCreate, request: Request):
    try:
        user_id = authenticated_user(request, body.user_id)
        return task_json(agent.harness.create_task(user_id, body.task_type))
    except ToolError as exc:
        raise error(exc)


@app.post("/api/profile/preview")
def profile_preview(body: ProfilePreviewBody, request: Request):
    try:
        user_id = authenticated_user(request, body.user_id)
        return asdict(agent.preview_profile(user_id, body.changes,
                                            expected_version=body.expected_version,
                                            consents=body.consents))
    except ToolError as exc:
        raise error(exc)


@app.post("/api/profile/confirm")
def profile_confirm(body: ProfileConfirmBody, request: Request):
    try:
        user_id = authenticated_user(request, body.user_id)
        authenticated_task(request, body.task_id)
        return asdict(agent.confirm_profile(user_id, body.task_id,
                                            operation_key=body.operation_key,
                                            expected_version=body.expected_version))
    except ToolError as exc:
        raise error(exc)


@app.get("/api/tasks/{task_id}")
def get_task(task_id: str, request: Request):
    try:
        task = authenticated_task(request, task_id)
        return task_json(task)
    except ToolError as exc:
        raise error(exc)


@app.get("/api/profile/{user_id}")
def get_profile(user_id: str, request: Request):
    user_id = authenticated_user(request, user_id)
    profile = store.get_profile(user_id)
    if profile is None:
        raise HTTPException(status_code=404, detail={"code": "profile_not_found"})
    return asdict(profile)


@app.post("/api/tasks/{task_id}/messages")
def message(task_id: str, body: Message, request: Request):
    try:
        authenticated_task(request, task_id)
        result = agent.harness.interpret(task_id, [{"role": "user", "content": body.content}])
        return {"intent": result, "task": task_json(agent.harness._task(task_id))}
    except ToolError as exc:
        raise error(exc)


@app.post("/api/tasks/{task_id}/context")
def confirm_context(task_id: str, body: ContextConfirm, request: Request):
    try:
        authenticated_task(request, task_id)
        return task_json(agent.harness.context(task_id, body.meal, body.options))
    except ToolError as exc:
        raise error(exc)


@app.post("/api/tasks/{task_id}/confirm")
def confirm(task_id: str, body: DecisionBody, request: Request):
    try:
        authenticated_task(request, task_id)
        return task_json(agent.harness.decide(task_id, Decision(body.decision), body.action_index))
    except ToolError as exc:
        raise error(exc)


@app.post("/api/tasks/{task_id}/feedback")
def feedback(task_id: str, body: FeedbackBody, request: Request):
    try:
        authenticated_task(request, task_id)
        return task_json(agent.harness.feedback(task_id, Execution(body.execution), note=body.note))
    except ToolError as exc:
        raise error(exc)


@app.post("/api/tasks/{task_id}/feedback/correct")
def correct_feedback(task_id: str, body: FeedbackCorrectionBody, request: Request):
    try:
        authenticated_task(request, task_id)
        return task_json(agent.harness.correct_feedback(task_id, Execution(body.execution), note=body.note,
                                                        operation_key=body.operation_key,
                                                        expected_version=body.expected_version))
    except ToolError as exc:
        raise error(exc)


@app.get("/api/tasks/{task_id}/reminder")
def reminder_status(task_id: str, request: Request):
    try:
        authenticated_task(request, task_id)
        return agent.harness.reminder_status(task_id)
    except ToolError as exc:
        raise error(exc)


@app.post("/api/tasks/{task_id}/reminder")
def remind(task_id: str, request: Request, operation_key: str | None = None):
    try:
        authenticated_task(request, task_id)
        return task_json(agent.harness.remind(task_id, operation_key=operation_key))
    except ToolError as exc:
        raise error(exc)


@app.get("/api/tasks/{task_id}/events")
def events(task_id: str, request: Request):
    try:
        task = authenticated_task(request, task_id)
        return [asdict(event) for event in store.list_events(task.task_id)]
    except ToolError as exc:
        raise error(exc)


@app.get("/api/tasks/{task_id}/review")
def review(task_id: str, request: Request):
    try:
        authenticated_task(request, task_id)
        return agent.review(task_id)
    except ToolError as exc:
        raise error(exc)


@app.get("/api/plans")
def plan_list(user_id: str, request: Request, limit: int = 30):
    user_id = authenticated_user(request, user_id)
    if not 1 <= limit <= 100:
        raise HTTPException(status_code=422, detail={"code": "invalid_plan_limit"})
    plans = [plan for plan in planning.store.list_plans(user_id) if plan.status in {"confirmed", "superseded"}]
    plans.sort(key=lambda plan: (plan.start_date, plan.updated_at, plan.plan_id), reverse=True)
    return [asdict(plan) for plan in plans[:limit]]


@app.get("/api/plans/{plan_id}")
def plan_read(plan_id: str, request: Request):
    try:
        plan = planning.store.get_plan(plan_id)
        if plan is None:
            raise ToolError("plan_not_found")
        authenticated_user(request, plan.user_id)
        return asdict(plan)
    except ToolError as exc:
        raise error(exc)


@app.post("/api/plans/preview")
def plan_preview(body: PlanBody, request: Request):
    try:
        user_id = authenticated_user(request, body.user_id)
        items=[PlanItem(**item.model_dump()) for item in body.items]
        plan = planning.preview(user_id,start_date=body.start_date,days=body.days,servings=body.servings,items=items)
        task = agent.harness.create_task(user_id, "plan")
        plan.task_id = task.task_id
        planning.store.save_plan(plan)
        agent.harness.plan_previewed(task.task_id, plan.plan_id)
        return asdict(plan)
    except ToolError as exc: raise error(exc)


@app.post("/api/plans/{plan_id}/confirm")
def plan_confirm(plan_id: str, request: Request):
    try:
        plan = planning.store.get_plan(plan_id)
        if plan is None:
            raise ToolError("plan_not_found")
        authenticated_user(request, plan.user_id)
        saved = planning.confirm(plan_id)
        if saved.task_id:
            agent.harness.plan_confirmed(saved.task_id, saved.plan_id, f"plan-task:{saved.task_id}:confirm")
        return asdict(saved)
    except ToolError as exc: raise error(exc)


@app.post("/api/plans/{plan_id}/cancel")
def plan_cancel(plan_id: str, request: Request):
    try:
        plan = planning.store.get_plan(plan_id)
        if plan is None:
            raise ToolError("plan_not_found")
        authenticated_user(request, plan.user_id)
        saved = planning.cancel(plan_id)
        if saved.task_id:
            agent.harness.plan_cancelled(saved.task_id, saved.plan_id, f"plan-task:{saved.task_id}:cancel")
        return asdict(saved)
    except ToolError as exc: raise error(exc)


@app.post("/api/plans/{plan_id}/shopping-list")
def plan_shopping(plan_id: str, request: Request):
    try:
        plan = planning.store.get_plan(plan_id)
        if plan is None:
            raise ToolError("plan_not_found")
        authenticated_user(request, plan.user_id)
        return asdict(planning.generate_shopping_list(plan_id))
    except ToolError as exc: raise error(exc)


@app.post("/api/inventory")
def inventory(body: InventoryBody, request: Request):
    try:
        data = body.model_dump()
        data["user_id"] = authenticated_user(request, data["user_id"])
        return asdict(planning.inventory_upsert(InventoryItem(**data)))
    except ToolError as exc: raise error(exc)


@app.get("/api/inventory")
def inventory_list(user_id: str, request: Request):
    user_id = authenticated_user(request, user_id)
    return [asdict(item) for item in planning.store.list_inventory(user_id)]


@app.get("/api/shopping-lists/{list_id}/inventory-diff")
def inventory_diff(list_id: str, request: Request):
    try:
        shopping_list = planning.store.get_shopping_list(list_id)
        if shopping_list is None:
            raise ToolError("shopping_list_not_found")
        authenticated_user(request, shopping_list.user_id)
        return [asdict(item) for item in planning.inventory_diff(list_id)]
    except ToolError as exc: raise error(exc)


@app.get("/api/meal-records")
def meal_record_list(user_id: str, request: Request, limit: int = 20):
    user_id = authenticated_user(request, user_id)
    if not 1 <= limit <= 100:
        raise HTTPException(status_code=422, detail={"code": "invalid_record_limit"})
    records = meal_records.list(user_id)
    records.sort(key=lambda record: (record.meal_date, record.updated_at, record.record_id), reverse=True)
    return [asdict(record) for record in records[:limit]]


@app.post("/api/meal-records/preview")
def meal_record_preview(body: MealRecordBody, request: Request):
    try:
        user_id = authenticated_user(request, body.user_id)
        return asdict(meal_records.preview(user_id, **{key: value for key, value in body.model_dump().items() if key != "user_id"}))
    except ToolError as exc: raise error(exc)


@app.post("/api/quick-log/preview")
def quick_log_preview(body: MealRecordBody, request: Request):
    """Create a resumable quick-log task and keep the intake as a draft."""
    try:
        user_id = authenticated_user(request, body.user_id)
        data = body.model_dump()
        data["user_id"] = user_id
        record = meal_records.preview(user_id, **{key: value for key, value in data.items() if key != "user_id"})
        task = agent.harness.create_task(user_id, "quick_log")
        task = agent.harness.quick_log_preview(task.task_id, asdict(record))
        return {"task": task_json(task), "record": asdict(record)}
    except ToolError as exc: raise error(exc)


@app.post("/api/quick-log/confirm")
def quick_log_confirm(body: QuickLogConfirmBody, request: Request, operation_key: str | None = None):
    try:
        task = authenticated_task(request, body.task_id)
        if task.task_type != "quick_log":
            raise ToolError("task_type_mismatch")
        data = body.model_dump()
        data.pop("task_id", None)
        data["user_id"] = authenticated_user(request, data["user_id"])
        pending = task.pending_record or {}
        compare_fields = ("user_id", "meal_date", "meal_slot", "name", "ingredient_id", "quantity", "unit", "eaten_at", "source", "plan_id", "plan_item_id")
        if any(pending.get(field) != data.get(field) for field in compare_fields):
            raise ToolError("quick_log_draft_changed")
        key = operation_key or f"quick-log:{body.task_id}:{body.record_id}"
        record = meal_records.confirm(MealRecord(**data), operation_key=key)
        completed = agent.harness.quick_log_confirmed(body.task_id, asdict(record), key + ":task")
        return {"task": task_json(completed), "record": asdict(record)}
    except ToolError as exc: raise error(exc)


@app.post("/api/meal-records/confirm")
def meal_record_confirm(body: MealRecordConfirmBody, request: Request, operation_key: str | None = None):
    try:
        data = body.model_dump()
        data["user_id"] = authenticated_user(request, data["user_id"])
        return asdict(meal_records.confirm(MealRecord(**data), operation_key=operation_key))
    except ToolError as exc: raise error(exc)


@app.patch("/api/meal-records/{record_id}")
def meal_record_update(record_id: str, body: MealRecordPatch, request: Request):
    try:
        current = meal_records.store.get_meal_record(record_id)
        if current is None:
            raise ToolError("meal_record_not_found")
        authenticated_user(request, current.user_id)
        return asdict(meal_records.update(record_id, expected_version=body.expected_version,
                                          operation_key=body.operation_key, **body.changes))
    except ToolError as exc: raise error(exc)


@app.delete("/api/meal-records/{record_id}")
def meal_record_delete(record_id: str, expected_version: int, request: Request, operation_key: str | None = None):
    try:
        current = meal_records.store.get_meal_record(record_id)
        if current is None:
            raise ToolError("meal_record_not_found")
        authenticated_user(request, current.user_id)
        return asdict(meal_records.delete(record_id, expected_version=expected_version, operation_key=operation_key))
    except ToolError as exc: raise error(exc)


@app.get("/api/reviews")
def meal_review(user_id: str, request: Request, period: str = "week", anchor_date: str | None = None):
    try:
        user_id = authenticated_user(request, user_id)
        return comprehensive_review.generate(user_id, period=period, anchor_date=anchor_date)
    except ToolError as exc:
        raise error(exc)
    except ValueError:
        raise HTTPException(status_code=400, detail={"code": "invalid_review_range"})


@app.get("/api/foods/search")
def foods_search(user_id: str, request: Request, q: str, limit: int = 5):
    limit = max(1, min(limit, 10))
    user_id = authenticated_user(request, user_id)
    q = q.strip()
    if not 1 <= len(q) <= 120:
        raise HTTPException(status_code=400, detail={"code": "invalid_food_query"})
    profile = store.get_profile(user_id)
    constraints = []
    confirmed = False
    budget = None
    if profile:
        constraints = [*profile.allergies, *profile.hard_avoids]
        confirmed = "allergies" in profile.confirmed_fields
        budget = profile.budget
    result = search_result(food_registry, q, constraints, budget=budget, limit=limit, constraints_confirmed=confirmed)
    return {"query": result["query"],
            "records": [summarize_record(record) for record in result["records"]],
            "assessments": [{"record": summarize_record(item.record), "status": item.status,
                             "reasons": list(item.reasons), "unknown_fields": list(item.unknown_fields)}
                            for item in result["assessments"]],
            "failures": result["failures"], "conflicts": [asdict(item) for item in result["conflicts"]]}


@app.get("/api/preferences/suggestions")
def preference_suggestions(user_id: str, request: Request):
    user_id = authenticated_user(request, user_id)
    return suggestions(store, user_id)


@app.post("/api/export")
def export_data(body: PortabilityBody, request: Request):
    try:
        return portability.export(authenticated_user(request, body.user_id))
    except ToolError as exc:
        raise error(exc)


@app.post("/api/delete")
def delete_data(body: PortabilityBody, request: Request):
    try:
        return {"deleted": portability.delete(authenticated_user(request, body.user_id), confirmed=body.confirmed)}
    except ToolError as exc:
        raise error(exc)
