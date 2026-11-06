"""Exercise API ownership checks without network or a hosted account."""
import importlib
from types import SimpleNamespace

import pytest

pytest.importorskip('fastapi')
from fastapi import HTTPException
from starlette.requests import Request
from dietlens_mvp import DietLensAgent, Harness, InMemoryStore
from dietlens_mvp.models import Task, Profile
from dietlens_mvp.meal_records import MealRecordService
from dietlens_mvp.planning import PlanningService
from dietlens_mvp.models import PlanItem
from dietlens_mvp.models import InventoryItem


@pytest.fixture
def api_module(monkeypatch, tmp_path):
    monkeypatch.setenv('DIETLENS_ENV_FILE', str(tmp_path / 'missing.env'))
    monkeypatch.setenv('DIETLENS_STORAGE', 'sqlite')
    monkeypatch.setenv('DIETLENS_DB', str(tmp_path / 'api.db'))
    monkeypatch.setenv('DIETLENS_AUTH_MODE', 'demo')
    monkeypatch.setenv('DIETLENS_API_KEY', '')
    module = importlib.import_module('api_server')
    store = InMemoryStore()
    monkeypatch.setattr(module, 'store', store)
    monkeypatch.setattr(module, 'agent', DietLensAgent(Harness(store)))
    monkeypatch.setattr(module, 'meal_records', MealRecordService(store))
    monkeypatch.setattr(module, 'planning', PlanningService(store))
    monkeypatch.setattr(module, 'authenticator', SimpleNamespace(user_id=lambda token: 'owner'))
    return module


def request(token=True):
    return Request({'type': 'http', 'headers': [(b'authorization', b'Bearer synthetic-token')] if token else []})


def test_recent_tasks_requires_login_and_matching_owner(api_module):
    with pytest.raises(HTTPException) as missing:
        api_module.recent_tasks(request(False), 'owner')
    assert missing.value.status_code == 401
    with pytest.raises(HTTPException) as other:
        api_module.recent_tasks(request(), 'someone-else')
    assert other.value.status_code == 403


def test_recent_tasks_only_returns_own_meal_tasks(api_module):
    own = Task(user_id='owner')
    api_module.store.save_task(own)
    api_module.store.save_task(Task(user_id='someone-else'))
    api_module.store.save_task(Task(user_id='owner', task_type='profile_update'))
    assert [item['task_id'] for item in api_module.recent_tasks(request(), 'owner')] == [own.task_id]


def test_resume_task_cannot_read_another_account(api_module):
    other = Task(user_id='someone-else')
    api_module.store.save_task(other)
    with pytest.raises(HTTPException) as caught:
        api_module.authenticated_task(request(), other.task_id)
    assert caught.value.status_code == 403


def test_meal_record_list_requires_login_and_matching_owner(api_module):
    with pytest.raises(HTTPException) as missing:
        api_module.meal_record_list('owner', request(False))
    assert missing.value.status_code == 401
    with pytest.raises(HTTPException) as other:
        api_module.meal_record_list('someone-else', request())
    assert other.value.status_code == 403


def test_meal_record_list_is_recent_owned_active_and_bounded(api_module):
    service = api_module.meal_records
    def save(user, day, name):
        return service.confirm(service.preview(user, meal_date=day, meal_slot='lunch', name=name))
    save('owner', '2026-11-03', 'earlier')
    latest = save('owner', '2026-11-04', 'latest')
    deleted = save('owner', '2026-11-05', 'deleted')
    service.delete(deleted.record_id, expected_version=deleted.version)
    save('someone-else', '2026-11-06', 'private')
    records = api_module.meal_record_list('owner', request(), limit=1)
    assert len(records) == 1
    assert records[0]['record_id'] == latest.record_id
    assert records[0]['version'] == latest.version
    assert len(api_module.meal_record_list('owner', request())) == 2
    with pytest.raises(HTTPException) as invalid:
        api_module.meal_record_list('owner', request(), limit=101)
    assert invalid.value.status_code == 422


def test_quick_log_is_a_resumable_harness_task(api_module):
    api_module.store.put_profile(Profile('owner'))
    body = api_module.MealRecordBody(user_id='owner', meal_date='2026-11-05', meal_slot='lunch', name='番茄面')
    preview = api_module.quick_log_preview(body, request())
    assert preview['task']['task_type'] == 'quick_log'
    assert preview['task']['state'] == 'created'
    assert preview['task']['pending_record']['record_id'] == preview['record']['record_id']
    confirm = api_module.QuickLogConfirmBody(task_id=preview['task']['task_id'], record_id=preview['record']['record_id'], user_id='owner', meal_date='2026-11-05', meal_slot='lunch', name='番茄面')
    result = api_module.quick_log_confirm(confirm, request(), operation_key='quick-log-test')
    assert result['task']['state'] == 'done'
    assert result['task']['linked_objects']['meal_record_id'] == result['record']['record_id']
    assert len(api_module.meal_records.list('owner')) == 1


def test_quick_log_rejects_confirmation_that_changes_the_preview(api_module):
    api_module.store.put_profile(Profile('owner'))
    preview = api_module.quick_log_preview(api_module.MealRecordBody(user_id='owner', meal_date='2026-11-05', meal_slot='lunch', name='番茄面'), request())
    changed = api_module.QuickLogConfirmBody(task_id=preview['task']['task_id'], record_id=preview['record']['record_id'], user_id='owner', meal_date='2026-11-05', meal_slot='lunch', name='临时改成炒饭')
    with pytest.raises(Exception) as caught:
        api_module.quick_log_confirm(changed, request(), operation_key='quick-log-changed')
    assert getattr(caught.value, 'detail', {}).get('code') == 'quick_log_draft_changed'
    assert api_module.meal_records.list('owner') == []


def test_plan_preview_and_confirm_are_linked_to_a_resumable_task(api_module):
    api_module.store.put_profile(Profile('owner'))
    body = api_module.PlanBody(user_id='owner', start_date='2026-11-05', days=1, servings=1, items=[api_module.PlanItemBody(item_id='lunch', meal_date='2026-11-05', meal_slot='lunch', name='番茄面', ingredient_id='番茄', quantity=1, unit='份')])
    preview = api_module.plan_preview(body, request())
    assert preview['task_id']
    assert api_module.agent.harness._task(preview['task_id']).task_type == 'plan'
    saved = api_module.plan_confirm(preview['plan_id'], request())
    assert saved['status'] == 'confirmed'
    assert api_module.agent.harness._task(preview['task_id']).state.value == 'done'


def test_plan_reads_require_login_and_matching_owner(api_module):
    with pytest.raises(HTTPException) as missing:
        api_module.plan_list('owner', request(False))
    assert missing.value.status_code == 401
    with pytest.raises(HTTPException) as other:
        api_module.plan_list('someone-else', request())
    assert other.value.status_code == 403
    plan=api_module.planning.preview('someone-else',start_date='2026-11-04',days=1,servings=1,
                                   items=[PlanItem('l','2026-11-04','lunch','private','rice',1,'份')])
    with pytest.raises(HTTPException) as read:
        api_module.plan_read(plan.plan_id, request())
    assert read.value.status_code == 403


def test_saved_plans_exclude_drafts_and_other_users_but_keep_old_versions(api_module):
    def create(user,day):
        return api_module.planning.preview(user,start_date=day,days=1,servings=1,
                                          items=[PlanItem('l',day,'lunch','meal','rice',1,'份')])
    first=create('owner','2026-11-04');api_module.planning.confirm(first.plan_id)
    second=create('owner','2026-11-04');api_module.planning.confirm(second.plan_id)
    create('owner','2026-11-05')
    private=create('someone-else','2026-11-06');api_module.planning.confirm(private.plan_id)
    plans=api_module.plan_list('owner',request())
    assert {plan['plan_id'] for plan in plans}=={first.plan_id,second.plan_id}
    assert {plan['status'] for plan in plans}=={'confirmed','superseded'}
    assert len(api_module.plan_list('owner',request(),limit=1))==1
    with pytest.raises(HTTPException) as invalid:
        api_module.plan_list('owner',request(),limit=101)
    assert invalid.value.status_code==422


def test_inventory_boundary_preserves_version_and_rejects_foreign_id(api_module):
    api_module.planning.inventory_upsert(InventoryItem('foreign','someone-else','rice','private',100,'g'))
    with pytest.raises(HTTPException) as other:
        api_module.inventory(api_module.InventoryBody(inventory_id='foreign',user_id='owner',ingredient_id='rice',name='meal',quantity=1,unit='g'),request())
    assert other.value.status_code==403
    saved=api_module.inventory(api_module.InventoryBody(inventory_id='own',user_id='owner',ingredient_id='rice',name='meal',quantity=100,unit='g'),request())
    for quantity in [90,80]:
        saved=api_module.inventory(api_module.InventoryBody(inventory_id='own',user_id='owner',ingredient_id='rice',name='meal',quantity=quantity,unit='g',version=saved['version']),request())
    assert saved['version']==3 and saved['quantity']==80


@pytest.mark.parametrize('query',['', '  ', 'x'*121])
def test_food_query_rejected_before_external_request(api_module,query,monkeypatch):
    def forbidden(*args,**kwargs):
        raise AssertionError('invalid query must not contact sources')
    monkeypatch.setattr(api_module,'search_result',forbidden)
    with pytest.raises(HTTPException) as invalid:
        api_module.foods_search('owner',request(),query)
    assert invalid.value.status_code==400
