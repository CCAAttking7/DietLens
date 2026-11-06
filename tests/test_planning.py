from datetime import date, timedelta
import pytest

from dietlens_mvp import InMemoryStore, SQLiteStore
from dietlens_mvp.errors import ToolError
from dietlens_mvp.models import InventoryItem, PlanItem
from dietlens_mvp.planning import PlanningService


def items(start='2026-11-01', days=1, repeat=False):
    slots=['早餐','午餐','晚餐']
    result=[]
    for day in range(days):
        d=(date.fromisoformat(start)+timedelta(days=day)).isoformat()
        for slot in slots:
            ingredient='rice' if slot != '早餐' else 'oat'
            unit='g'
            result.append(PlanItem(f'{d}-{slot}',d,slot,'米饭' if ingredient=='rice' else '燕麦',ingredient,100,unit))
    return result

@pytest.fixture(params=['memory','sqlite'])
def service(request,tmp_path):
    store=InMemoryStore() if request.param=='memory' else SQLiteStore(str(tmp_path/'plan.db'))
    yield PlanningService(store)
    if isinstance(store,SQLiteStore): store.close()

def test_one_day_plan_three_meals_and_confirm_does_not_create_meal_records(service):
    plan=service.preview('u',start_date='2026-11-01',days=1,servings=1,items=items())
    assert plan.status=='draft'
    assert service.store.list_shopping_lists(plan.plan_id)==[]
    confirmed=service.confirm(plan.plan_id)
    assert confirmed.status=='confirmed'
    assert not hasattr(service.store,'meal_records')

def test_seven_day_plan_has_21_meals(service):
    plan=service.preview('u',start_date='2026-11-01',days=7,servings=2,items=items(days=7))
    assert len(plan.items)==21

def test_invalid_shape_duplicate_and_bad_unit_stop(service):
    with pytest.raises(ToolError,match='meal_count_mismatch'):
        service.preview('u',start_date='2026-11-01',days=1,servings=1,items=[])
    bad=items();bad[1].meal_slot='早餐'
    with pytest.raises(ToolError,match='duplicate_plan_meal'):
        service.preview('u',start_date='2026-11-01',days=1,servings=1,items=bad)
    bad=items();bad[0].unit='毫升'
    with pytest.raises(ToolError,match='invalid_plan_item'):
        service.preview('u',start_date='2026-11-01',days=1,servings=1,items=bad)

def test_shopping_list_groups_same_ingredient_and_unit(service):
    meal_items=items();meal_items[0].quantity=100;meal_items[1].quantity=200;meal_items[2]=PlanItem('x2','2026-11-01','晚餐','酱油','soy',20,'ml')
    plan=service.preview('u',start_date='2026-11-01',days=1,servings=1,items=meal_items)
    service.confirm(plan.plan_id)
    shopping=service.generate_shopping_list(plan.plan_id)
    rice=[i for i in shopping.items if i.ingredient_id=='rice'][0]
    assert rice.quantity==200
    assert rice.unit=='g'
    assert [i for i in shopping.items if i.ingredient_id=='soy'][0].unit=='ml'

def test_g_and_ml_are_separate_and_inventory_is_not_auto_decremented(service):
    plan_items=items();plan_items[0]=PlanItem('a','2026-11-01','早餐','牛奶','milk',250,'ml');plan=service.preview('u',start_date='2026-11-01',days=1,servings=1,items=plan_items);service.confirm(plan.plan_id);shopping=service.generate_shopping_list(plan.plan_id)
    service.inventory_upsert(InventoryItem('inv','u','milk','牛奶',100,'g'))
    service.inventory_upsert(InventoryItem('inv2','u','milk','牛奶',100,'ml'))
    diff=service.inventory_diff(shopping.list_id)
    milk=diff[0]
    assert milk.needed==150
    assert service.store.list_inventory('u')[1].quantity==100

def test_inventory_diff_uses_only_same_unit(service):
    plan=service.preview('u',start_date='2026-11-01',days=1,servings=1,items=items());service.confirm(plan.plan_id);shopping=service.generate_shopping_list(plan.plan_id)
    service.inventory_upsert(InventoryItem('inv','u','rice','米饭',100,'ml'))
    rice=[i for i in service.inventory_diff(shopping.list_id) if i.ingredient_id=='rice'][0]
    assert rice.needed==200

def test_inventory_repeated_edits_use_latest_version_and_keep_identity(service):
    saved=service.inventory_upsert(InventoryItem('inv','u','rice','米饭',100,'g'))
    for quantity in [90,80,70]:
        saved=service.inventory_upsert(InventoryItem('inv','u','rice','米饭',quantity,'g',version=saved.version))
    assert saved.version==4
    assert len(service.store.list_inventory('u'))==1
    with pytest.raises(ToolError,match='version_conflict'):
        service.inventory_upsert(InventoryItem('inv','u','rice','米饭',999,'g',version=1))
    assert service.store.list_inventory('u')[0].quantity==70

def test_inventory_id_cannot_take_another_users_record(service):
    service.inventory_upsert(InventoryItem('private-id','other','rice','私有米饭',100,'g'))
    with pytest.raises(ToolError,match='user_ownership_required'):
        service.inventory_upsert(InventoryItem('private-id','u','rice','米饭',999,'g'))
    assert service.store.list_inventory('other')[0].quantity==100
    assert service.store.list_inventory('u')==[]

def test_inventory_duplicate_does_not_replace_existing_record(service):
    service.inventory_upsert(InventoryItem('first','u','rice','米饭',100,'g'))
    with pytest.raises(ToolError,match='inventory_duplicate'):
        service.inventory_upsert(InventoryItem('second','u','rice','米饭',999,'g'))
    assert service.store.list_inventory('u')[0].inventory_id=='first'

def test_repeated_shopping_generation_is_idempotent(service):
    plan=service.preview('u',start_date='2026-11-01',days=1,servings=1,items=items());service.confirm(plan.plan_id)
    first=service.generate_shopping_list(plan.plan_id);again=service.generate_shopping_list(plan.plan_id)
    assert first==again and len(service.store.list_shopping_lists(plan.plan_id))==1

def test_new_confirmed_plan_stales_old_list(service):
    first=service.preview('u',start_date='2026-11-01',days=1,servings=1,items=items());service.confirm(first.plan_id);old=service.generate_shopping_list(first.plan_id)
    second_items=items();second_items[0].quantity=999
    second=service.preview('u',start_date='2026-11-01',days=1,servings=1,items=second_items);service.confirm(second.plan_id)
    assert service.store.get_plan(first.plan_id).status=='superseded'
    assert service.store.get_shopping_list(old.list_id).status=='stale'

def test_different_dates_keep_both_plans_and_shopping_active(service):
    first=service.preview('u',start_date='2026-11-01',days=1,servings=1,items=items())
    service.confirm(first.plan_id)
    shopping=service.generate_shopping_list(first.plan_id)
    second=service.preview('u',start_date='2026-11-02',days=1,servings=1,items=items(start='2026-11-02'))
    service.confirm(second.plan_id)
    assert service.store.get_plan(first.plan_id).status=='confirmed'
    assert service.store.get_shopping_list(shopping.list_id).status=='active'
    assert len([plan for plan in service.store.list_plans('u') if plan.status=='confirmed'])==2

def test_partial_date_overlap_is_rejected_without_losing_existing_plan(service):
    week=service.preview('u',start_date='2026-11-01',days=7,servings=1,items=items(days=7))
    service.confirm(week.plan_id)
    shopping=service.generate_shopping_list(week.plan_id)
    day=service.preview('u',start_date='2026-11-02',days=1,servings=1,items=items(start='2026-11-02'))
    with pytest.raises(ToolError,match='overlapping_plan_range'):
        service.confirm(day.plan_id)
    assert service.store.get_plan(week.plan_id).status=='confirmed'
    assert service.store.get_plan(day.plan_id).status=='draft'
    assert service.store.get_shopping_list(shopping.list_id).status=='active'

def test_confirm_retry_does_not_create_another_version(service):
    plan=service.preview('u',start_date='2026-11-01',days=1,servings=1,items=items())
    saved=service.confirm(plan.plan_id)
    assert service.confirm(plan.plan_id)==saved

def test_shopping_displays_ingredient_name_instead_of_meal_name(service):
    meal=PlanItem('lunch','2026-11-01','午餐','鸡肉饭','chicken',200,'g',ingredient_name='鸡肉')
    plan=service.preview('u',start_date='2026-11-01',days=1,servings=1,items=[meal])
    service.confirm(plan.plan_id)
    assert service.generate_shopping_list(plan.plan_id).items[0].name=='鸡肉'

def test_cancel_does_not_create_plan_or_list_after_draft(service):
    plan=service.preview('u',start_date='2026-11-01',days=1,servings=1,items=items());service.cancel(plan.plan_id)
    with pytest.raises(ToolError,match='plan_not_confirmed'): service.generate_shopping_list(plan.plan_id)


def test_single_meal_plan_only_adds_its_ingredients_to_shopping(service):
    lunch = items()[1:2]
    plan = service.preview('u', start_date='2026-11-01', days=1, servings=1, items=lunch)
    assert len(plan.items) == 1
    service.confirm(plan.plan_id)
    shopping = service.generate_shopping_list(plan.plan_id)
    assert len(shopping.items) == 1
    assert shopping.items[0].ingredient_id == lunch[0].ingredient_id
    assert shopping.items[0].quantity == lunch[0].quantity
