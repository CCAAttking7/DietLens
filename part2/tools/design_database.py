"""生成数据库设计SQL、字典及中文ER源；不连接或执行业务数据库。"""
from pathlib import Path
import json
import re

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT/'database'
OUT.mkdir(exist_ok=True)
TABLES = []

def col(name, label, kind='text', nullable=False, default=None, note=''):
    return dict(name=name,label=label,kind=kind,nullable=nullable,default=default,note=note)

def t(name, label, group, cols, pk=('user_id','id'), unique=(), checks=(), retain=False):
    row=dict(name=name,label=label,group=group,columns=[col('user_id','所属用户')]+cols,
             pk=list(pk),unique=[list(x) for x in unique],checks=list(checks),fks=[],indexes=[])
    row['columns'] += [col('created_at','建立时间','time')]
    if retain:
        row['columns'] += [col('retain_until','保留截止','time',note='初次不超过180天；明确续期须留审计依据'),
                           col('renewed_at','续期确认时间','time',True)]
    TABLES.append(row)
    if name!='user_control': fk(row,['user_id'],'user_control',['user_id'])
    return row

def fk(row, columns, target, target_columns=None, late=False):
    row['fks'].append(dict(columns=list(columns),target=target,
                          target_columns=list(target_columns or columns),late=late))

def ref(row, name, target, target_name='id', nullable=False, label='来源标识'):
    row['columns'].insert(-1,col(name,label,nullable=nullable))
    fk(row,['user_id',name],target,['user_id',target_name])

def enum(row, field, values):
    row['checks'].append(field+' IN ('+', '.join("'"+x+"'" for x in values)+')')

def qty(row, prefix, label):
    row['columns'] += [col(prefix+'_state',label+'状态'),col(prefix+'_micros',label+'定点值','amount',True,
                        note='实际值乘1000000；未知必须为空'),col(prefix+'_unit',label+'单位',nullable=True)]
    enum(row,prefix+'_state',['已知','未知'])
    row['checks'].append(f"(({prefix}_state = '已知' AND {prefix}_micros IS NOT NULL AND {prefix}_unit IS NOT NULL) OR ({prefix}_state = '未知' AND {prefix}_micros IS NULL))")

def ident(): return col('id','对象标识')
def rev(): return col('revision','修订号','positive')
def confirm(): return col('confirmed_at','用户确认时间','time')
def pair(row, id_col, rev_col, target, label='来源', nullable=False):
    row['columns'] += [col(id_col,label+'标识',nullable=nullable),col(rev_col,label+'修订号','positive',nullable)]
    fk(row,['user_id',id_col,rev_col],target,['user_id','id','revision'])
    if nullable: row['checks'].append(f'(({id_col} IS NULL AND {rev_col} IS NULL) OR ({id_col} IS NOT NULL AND {rev_col} IS NOT NULL))')

# 所有权、版本与授权。
r=t('user_control','用户处理控制','授权与证据',[
    col('external_subject','托管身份主体',nullable=True,note='只存身份映射，不存口令或访问令牌'),
    col('processing_state','处理状态'),col('authorization_epoch','授权修订标记','positive'),
    col('data_revision','用户数据修订','positive'),col('current_profile_revision','当前档案修订','positive',True),
    col('delete_requested_at','主动删除请求时间','time',True)],pk=('user_id',),unique=[('external_subject',)])
enum(r,'processing_state',['正常','待删除','清理中','清理失败','已清理待备份到期'])
fk(r,['user_id','current_profile_revision'],'profile_revisions',['user_id','revision'],True)
r=t('profile_revisions','档案确认版本','授权与证据',[
    rev(),col('confirmed_fields','已确认字段','json',note='目标、预算、硬约束、软偏好及逐字段来源；固定结构由模块校验'),confirm()],
    pk=('user_id','revision'),retain=True)
r=t('media_assets','临时图片','授权与证据',[ident(),col('storage_key','本机受控文件键',nullable=True),
    col('media_kind','材料用途'),col('content_hash','内容摘要'),col('expires_at','图片过期时间','time'),
    col('processing_state','图片处理状态')],retain=True)
enum(r,'processing_state',['可用','待清理','已清理'])
r['checks'].append("((processing_state = '已清理' AND storage_key IS NULL) OR (processing_state <> '已清理' AND storage_key IS NOT NULL))")
r=t('consent_revisions','用途授权修订','授权与证据',[
    col('purpose','用途'),col('scope_key','范围键',note='全域或对应图片标识'),rev(),
    col('asset_id','外传图片标识',nullable=True),col('allowed','允许使用','bool'),
    col('recipient','接收方',nullable=True),col('authorization_epoch','授权修订标记','positive'),confirm()],
    pk=('user_id','purpose','scope_key','revision'),retain=True)
enum(r,'purpose',['历史分析','图片外传','提醒'])
fk(r,['user_id','asset_id'],'media_assets',['user_id','id'])
r['checks'].append("((purpose = '图片外传' AND asset_id IS NOT NULL AND scope_key = asset_id AND recipient IS NOT NULL) OR (purpose <> '图片外传' AND asset_id IS NULL AND scope_key = '全域'))")
r=t('task_sessions','临时任务会话','授权与证据',[ident(),col('task_kind','任务类型'),
    col('state','任务状态'),col('draft_revision','草稿修订','positive'),col('draft_payload','未确认草稿','json'),
    col('authorization_epoch','绑定授权修订','positive'),col('expires_at','任务过期时间','time')])
enum(r,'state',['进行中','已暂停','已取消','已完成'])
r=t('context_snapshots','已确认情境','授权与证据',[ident(),col('profile_revision','档案修订','positive'),
    col('context_key','情境指纹',note='相同情境冷却的规范化键，不以新快照标识绕过冷却'),
    col('situation','已确认情境内容','json'),col('authorization_epoch','当时授权修订','positive'),confirm()],retain=True)
fk(r,['user_id','profile_revision'],'profile_revisions',['user_id','revision'])
r=t('source_references','证据来源','授权与证据',[ident(),col('source_kind','来源类型'),
    col('source_locator','出处或自述说明'),col('specification','商品或菜单规格',nullable=True),
    col('published_at','材料时间','time',True),col('acquired_at','取得时间','time'),
    col('asset_id','原图片标识',nullable=True),col('asset_digest','材料摘要',nullable=True),
    col('verification_note','核对依据',nullable=True)],retain=True)
enum(r,'source_kind',['用户自述','商品标签','菜单','公开资料','本地编码'])
fk(r,['user_id','asset_id'],'media_assets',['user_id','id'])
r=t('food_observations','食品证据版本','授权与证据',[ident(),col('previous_id','上一证据版本',nullable=True),
    col('food_name','食品名称'),col('specification','当前规格',nullable=True),
    col('recipe_coverage','配方覆盖'),col('checked_at','核对时间','time',True)],retain=True)
fk(r,['user_id','previous_id'],'food_observations',['user_id','id'])
enum(r,'recipe_coverage',['完整已核对','仅部分已知','未知'])
qty(r,'basis','营养基准量')
r=t('food_fields','食品逐字段事实','授权与证据',[
    col('observation_id','食品证据标识'),col('field_key','字段键'),col('state','字段状态'),
    col('value_kind','值类型'),col('number_micros','数值定点值','amount',True),
    col('text_value','文字值',nullable=True),col('unit','字段单位',nullable=True),
    col('raw_value','原始候选值',nullable=True),col('checked_at','核对时间','time',True)],
    pk=('user_id','observation_id','field_key'))
fk(r,['user_id','observation_id'],'food_observations',['user_id','id'])
enum(r,'state',['已核对','待核对','未知','冲突']);enum(r,'value_kind',['数值','文字'])
r['checks'].append("((state IN ('未知','冲突') AND number_micros IS NULL AND text_value IS NULL) OR (state IN ('已核对','待核对') AND ((value_kind = '数值' AND number_micros IS NOT NULL AND text_value IS NULL AND unit IS NOT NULL) OR (value_kind = '文字' AND text_value IS NOT NULL AND number_micros IS NULL))))")
r=t('field_sources','字段来源关联','授权与证据',[
    col('observation_id','食品证据标识'),col('field_key','字段键'),col('source_id','来源标识'),
    col('source_role','来源角色')],pk=('user_id','observation_id','field_key','source_id'))
fk(r,['user_id','observation_id','field_key'],'food_fields',['user_id','observation_id','field_key'])
fk(r,['user_id','source_id'],'source_references',['user_id','id'])
enum(r,'source_role',['原始材料','用户核对','冲突材料'])
r=t('constraint_assessments','约束评估','授权与证据',[ident(),col('context_id','情境标识'),
    col('observation_id','食品证据标识',nullable=True),col('rule_version','规则版本'),
    col('outcome','评估结论'),col('reasons','原因与受影响操作','json'),col('evaluated_at','评估时间','time')],retain=True)
fk(r,['user_id','context_id'],'context_snapshots',['user_id','id'])
fk(r,['user_id','observation_id'],'food_observations',['user_id','id'])
enum(r,'outcome',['通过','拦截','待核对'])

# 计划、准备与人工库存。
r=t('ingredients','标准食材','计划与准备',[ident(),col('canonical_name','标准名称'),
    col('catalog_code','外部编码',nullable=True)],retain=True)
r=t('plan_heads','计划身份','计划与准备',[ident(),col('current_revision','当前确认修订','positive'),
    col('row_version','并发版本','positive'),col('state','身份状态')],retain=True)
enum(r,'state',['有效','已删除'])
fk(r,['user_id','id','current_revision'],'plan_revisions',['user_id','id','revision'],True)
r=t('plan_revisions','计划确认版本','计划与准备',[ident(),rev(),col('mode','计划模式'),
    col('start_date','开始日期','date'),col('end_date','结束日期','date'),col('day_count','计划天数','positive'),
    col('context_id','情境标识'),confirm()],pk=('user_id','id','revision'),
    checks=['end_date >= start_date','day_count IN (1, 7)'])
fk(r,['user_id','id'],'plan_heads',['user_id','id']);fk(r,['user_id','context_id'],'context_snapshots',['user_id','id'])
enum(r,'mode',['完整','指定'])
r=t('planned_meals','计划餐次','计划与准备',[ident(),col('plan_id','计划标识'),
    col('plan_revision','计划修订','positive'),col('meal_date','餐次日期','date'),col('meal_slot','规范餐次'),
    col('people_count','准备人数','positive')],unique=[('user_id','plan_id','plan_revision','meal_date','meal_slot'),
                                                    ('user_id','id','meal_date','meal_slot')])
fk(r,['user_id','plan_id','plan_revision'],'plan_revisions',['user_id','id','revision'])
enum(r,'meal_slot',['早餐','午餐','晚餐'])
r=t('planned_foods','计划食物','计划与准备',[ident(),col('planned_meal_id','计划餐次标识'),
    col('food_name','食物名称'),col('observation_id','食品证据标识',nullable=True),
    col('assessment_id','约束评估标识',nullable=True),col('quantity_basis','数量基准')])
fk(r,['user_id','planned_meal_id'],'planned_meals',['user_id','id'])
fk(r,['user_id','observation_id'],'food_observations',['user_id','id'])
fk(r,['user_id','assessment_id'],'constraint_assessments',['user_id','id'])
enum(r,'quantity_basis',['每人','本餐总量']);qty(r,'quantity','计划份量')
r=t('ingredient_requirements','食材需求','计划与准备',[ident(),col('planned_food_id','计划食物标识'),
    col('ingredient_id','食材标识'),col('quantity_basis','数量基准'),col('source_id','配方来源',nullable=True)])
fk(r,['user_id','planned_food_id'],'planned_foods',['user_id','id']);fk(r,['user_id','ingredient_id'],'ingredients',['user_id','id'])
fk(r,['user_id','source_id'],'source_references',['user_id','id']);enum(r,'quantity_basis',['每人','本餐总量']);qty(r,'quantity','食材用量')
r=t('slot_assignments','当前槽位归属','计划与准备',[
    col('meal_date','餐次日期','date'),col('meal_slot','规范餐次'),col('planned_meal_id','当前计划餐次标识'),
    col('row_version','槽位并发版本','positive')],pk=('user_id','meal_date','meal_slot'))
fk(r,['user_id','planned_meal_id','meal_date','meal_slot'],'planned_meals',['user_id','id','meal_date','meal_slot'])
enum(r,'meal_slot',['早餐','午餐','晚餐'])
r=t('inventory_heads','库存身份','计划与准备',[ident(),col('ingredient_id','标准食材标识'),
    col('unit','核对口径单位'),col('current_revision','当前库存修订','positive'),col('row_version','并发版本','positive'),
    col('state','身份状态')],unique=[('user_id','ingredient_id','unit')],retain=True)
fk(r,['user_id','ingredient_id'],'ingredients',['user_id','id']);enum(r,'state',['有效','已删除'])
fk(r,['user_id','id','current_revision'],'inventory_revisions',['user_id','id','revision'],True)
r=t('inventory_revisions','库存核对版本','计划与准备',[ident(),rev(),col('quantity_state','库存量状态'),
    col('quantity_micros','库存定点值','amount',True),col('observed_at','库存核对时间','time'),
    col('reason','变更原因'),confirm()],pk=('user_id','id','revision'))
fk(r,['user_id','id'],'inventory_heads',['user_id','id']);enum(r,'quantity_state',['已知','未知'])
r['checks'].append("((quantity_state = '已知' AND quantity_micros IS NOT NULL) OR (quantity_state = '未知' AND quantity_micros IS NULL))")
r=t('preparation_lists','准备采购清单','计划与准备',[ident(),col('plan_id','来源计划标识'),
    col('plan_revision','来源计划修订','positive'),col('row_version','并发版本','positive'),
    col('state','清单状态'),col('inventory_data_revision','库存核对截点','positive'),confirm()],retain=True)
fk(r,['user_id','plan_id','plan_revision'],'plan_revisions',['user_id','id','revision']);enum(r,'state',['有效','已失效','已取消'])
r['indexes'].append(dict(columns=['user_id','plan_id','plan_revision'],unique=True,where="state = '有效'"))
r=t('preparation_lines','清单条目','计划与准备',[ident(),col('list_id','清单标识'),col('ingredient_id','标准食材标识'),
    col('unit','汇总口径单位'),col('has_unknown_requirement','另有未知需求','bool'),
    col('known_need_micros','已知需求小计','amount'),col('stock_state','库存量状态'),
    col('stock_micros','核对库存定点值','amount',True),col('shortage_state','差额状态'),
    col('shortage_micros','采购差额定点值','amount',True),col('purchased_state','采购自述状态'),
    col('prepared_state','准备自述状态'),col('inventory_id','所用库存身份',nullable=True),
    col('inventory_revision','所用库存修订','positive',True),col('manual_reason','人工调整原因',nullable=True)],
    unique=[('user_id','list_id','ingredient_id','unit')])
fk(r,['user_id','list_id'],'preparation_lists',['user_id','id']);fk(r,['user_id','ingredient_id'],'ingredients',['user_id','id'])
fk(r,['user_id','inventory_id','inventory_revision'],'inventory_revisions',['user_id','id','revision'])
r['checks'] += ['((inventory_id IS NULL AND inventory_revision IS NULL) OR (inventory_id IS NOT NULL AND inventory_revision IS NOT NULL))',
    "((stock_state = '已知' AND stock_micros IS NOT NULL) OR (stock_state = '未知' AND stock_micros IS NULL))",
    "((shortage_state = '已知' AND shortage_micros IS NOT NULL AND stock_state = '已知' AND has_unknown_requirement = 0) OR (shortage_state = '未知' AND shortage_micros IS NULL))"]
for f in ['stock_state','shortage_state']:enum(r,f,['已知','未知'])
for f in ['purchased_state','prepared_state']:enum(r,f,['未报告','已确认','不适用'])
r=t('preparation_sources','清单需求来源','计划与准备',[col('line_id','清单条目标识'),col('requirement_id','食材需求标识')],
    pk=('user_id','line_id','requirement_id'))
fk(r,['user_id','line_id'],'preparation_lines',['user_id','id']);fk(r,['user_id','requirement_id'],'ingredient_requirements',['user_id','id'])

# 一次个人用餐，多食物条目。
r=t('meal_heads','个人用餐身份','实际与回顾',[ident(),col('current_revision','当前餐食修订','positive'),
    col('row_version','并发版本','positive'),col('state','身份状态')],retain=True)
enum(r,'state',['有效','已删除']);fk(r,['user_id','id','current_revision'],'meal_revisions',['user_id','id','revision'],True)
r=t('meal_revisions','个人用餐版本','实际与回顾',[ident(),rev(),col('meal_date','业务用餐日期','date'),
    col('meal_slot','规范餐次'),col('actual_at','实际时点','time',True),col('note','用户自述',nullable=True),confirm()],pk=('user_id','id','revision'))
fk(r,['user_id','id'],'meal_heads',['user_id','id']);enum(r,'meal_slot',['早餐','午餐','晚餐','加餐'])
r=t('reported_foods','个人实际食物','实际与回顾',[col('record_id','用餐身份'),col('record_revision','用餐修订','positive'),
    col('item_id','条目标识'),col('food_name','实际食物名称'),col('observation_id','食品证据标识',nullable=True),
    col('planned_food_id','计划食物出处',nullable=True),col('entry_source','录入来源')],
    pk=('user_id','record_id','record_revision','item_id'))
fk(r,['user_id','record_id','record_revision'],'meal_revisions',['user_id','id','revision'])
fk(r,['user_id','observation_id'],'food_observations',['user_id','id']);fk(r,['user_id','planned_food_id'],'planned_foods',['user_id','id'])
enum(r,'entry_source',['手动自述','计划预填','图文核对']);qty(r,'quantity','个人实际份量')

# 行动含义、决策、窗口、执行互相独立。
r=t('micro_actions','微行动提案','行动与学习',[ident(),col('context_id','情境标识'),col('dimension','行动维度'),
    col('cue','行动线索'),col('behavior','具体行为'),col('effort','努力量'),col('rationale','行动依据'),
    col('replacement_of','被替代提案标识',nullable=True),col('planned_meal_id','关联计划餐次',nullable=True),
    col('current_window_revision','当前窗口修订','positive',True),col('current_execution_revision','当前执行修订','positive',True),
    col('row_version','并发版本','positive'),col('state','身份状态')],retain=True)
pair(r,'record_id','record_revision','meal_revisions','关联实际用餐',True)
fk(r,['user_id','context_id'],'context_snapshots',['user_id','id']);fk(r,['user_id','replacement_of'],'micro_actions',['user_id','id'])
fk(r,['user_id','planned_meal_id'],'planned_meals',['user_id','id'])
fk(r,['user_id','id','current_window_revision'],'action_windows',['user_id','action_id','revision'],True)
fk(r,['user_id','id','current_execution_revision'],'execution_revisions',['user_id','action_id','revision'],True)
enum(r,'dimension',['平替','顺手加法','进食顺序','时序节律']);enum(r,'state',['有效','已删除'])
r=t('action_decisions','行动最终决策','行动与学习',[col('action_id','行动标识'),col('decision','用户决策'),confirm()],pk=('user_id','action_id'))
fk(r,['user_id','action_id'],'micro_actions',['user_id','id']);enum(r,'decision',['采纳','跳过','被替代'])
r=t('action_windows','行动窗口修订','行动与学习',[col('action_id','行动标识'),rev(),
    col('starts_at','窗口开始','time'),col('ends_at','窗口结束','time'),col('timezone','业务时区',default="'Asia/Shanghai'"),
    col('reason','确认或修正原因'),confirm()],pk=('user_id','action_id','revision'),checks=['ends_at >= starts_at',"timezone = 'Asia/Shanghai'"])
fk(r,['user_id','action_id'],'action_decisions',['user_id','action_id'])
r=t('execution_revisions','执行自述修订','行动与学习',[col('action_id','行动标识'),rev(),
    col('execution_state','有效自述状态'),col('execution_date','实际执行日期','date',True),
    col('reported_at','报告时间','time'),col('note','执行自述备注',nullable=True),confirm()],pk=('user_id','action_id','revision'))
fk(r,['user_id','action_id'],'action_decisions',['user_id','action_id'])
enum(r,'execution_state',['完成','部分','未完成','撤回为不确定'])
r['checks'].append("((execution_state = '撤回为不确定' AND execution_date IS NULL) OR (execution_state <> '撤回为不确定' AND execution_date IS NOT NULL))")
r=t('reminder_events','提醒与回应历史','行动与学习',[ident(),col('action_id','行动标识'),
    col('scheduled_at','计划提醒时间','time'),col('sent_at','实际提醒时间','time',True),
    col('responded_at','回应时间','time',True),col('outcome','发送结果'),col('authorization_epoch','发送授权修订','positive')],retain=True)
fk(r,['user_id','action_id'],'action_decisions',['user_id','action_id']);enum(r,'outcome',['待发送','已发送','已取消','失败'])
r=t('interaction_settings','交互与提醒状态','行动与学习',[
    col('row_version','并发版本','positive'),col('unanswered_count','连续未响应数','nonnegative'),
    col('backoff_until','静默截止','time',True),col('companion_enabled','陪伴开启','bool'),
    col('collection_enabled','图鉴开启','bool'),col('calibration_enabled','校准开启','bool'),
    col('ranking_version','内环规则版本'),col('ranking_parameters','内环参数及原因','json')],pk=('user_id',),retain=True)
r=t('interaction_events','内环决策记录','行动与学习',[ident(),col('context_id','情境标识'),
    col('action_id','行动标识',nullable=True),col('event_kind','交互类型'),col('rule_version','排序规则版本'),
    col('explanation','依据及参数','json'),col('cooldown_until','情境冷却截止','time',True)],retain=True)
fk(r,['user_id','context_id'],'context_snapshots',['user_id','id']);fk(r,['user_id','action_id'],'micro_actions',['user_id','id'])
enum(r,'event_kind',['采纳','换一个','暂不需要','规则调整'])
r=t('learning_candidates','偏好与情境候选','行动与学习',[ident(),col('candidate_kind','候选类型'),
    col('hypothesis','待核对内容','json'),col('state','核对状态'),col('authorization_epoch','来源授权修订','positive'),
    col('range_start','证据开始日期','date'),col('range_end','证据结束日期','date'),col('confirmed_at','核对时间','time',True)],retain=True)
enum(r,'candidate_kind',['稳定偏好','情境线索']);enum(r,'state',['待核对','已确认','已拒绝','已到期'])
r['checks'].append('range_end >= range_start')
r=t('learning_evidence','学习证据引用','行动与学习',[ident(),col('candidate_id','候选标识'),
    col('action_id','来源行动',nullable=True),col('execution_revision','来源执行修订','positive',True),
    col('record_id','来源用餐',nullable=True),col('record_revision','来源用餐修订','positive',True)])
fk(r,['user_id','candidate_id'],'learning_candidates',['user_id','id'])
fk(r,['user_id','action_id','execution_revision'],'execution_revisions',['user_id','action_id','revision'])
fk(r,['user_id','record_id','record_revision'],'meal_revisions',['user_id','id','revision'])
r['checks'].append('((action_id IS NOT NULL AND execution_revision IS NOT NULL AND record_id IS NULL AND record_revision IS NULL) OR (action_id IS NULL AND execution_revision IS NULL AND record_id IS NOT NULL AND record_revision IS NOT NULL))')
r=t('preference_rule_revisions','稳定偏好修订','行动与学习',[ident(),rev(),col('candidate_id','已确认候选'),
    col('rule_content','条件方向与适用范围','json'),col('state','规则状态'),confirm()],pk=('user_id','id','revision'),retain=True)
fk(r,['user_id','candidate_id'],'learning_candidates',['user_id','id']);enum(r,'state',['有效','已停用','已删除'])
r=t('calibration_revisions','校准回答修订','行动与学习',[col('question_key','题目标识'),col('question_version','题目版本'),
    rev(),col('answer','确认回答','json',True),col('state','回答状态'),confirm()],pk=('user_id','question_key','revision'),retain=True)
enum(r,'state',['已确认','已删除'])
r['checks'].append("((state = '已确认' AND answer IS NOT NULL) OR (state = '已删除' AND answer IS NULL))")

# 回顾的确认输入；指标本身不长期落表。
r=t('expected_schedules','预期餐次版本','实际与回顾',[col('week_start','自然周起始','date'),rev(),confirm()],
    pk=('user_id','week_start','revision'),retain=True)
r=t('expected_slots','预期餐次槽位','实际与回顾',[col('week_start','自然周起始','date'),
    col('schedule_revision','预期餐次修订','positive'),col('meal_date','餐次日期','date'),col('meal_slot','规范餐次')],
    pk=('user_id','week_start','schedule_revision','meal_date','meal_slot'))
fk(r,['user_id','week_start','schedule_revision'],'expected_schedules',['user_id','week_start','revision'])
enum(r,'meal_slot',['早餐','午餐','晚餐','加餐'])
r=t('recovery_episodes','恢复周期确认','实际与回顾',[ident(),col('row_version','并发版本','positive'),
    col('deviation_at','确认偏离起点','time',True),col('return_at','确认回归终点','time',True),
    col('reason','用户确认情境'),confirm()],checks=['return_at IS NULL OR (deviation_at IS NOT NULL AND return_at >= deviation_at)'],retain=True)
r=t('recovery_exclusions','恢复排除时段','实际与回顾',[ident(),col('episode_id','恢复周期标识'),
    col('starts_at','排除开始','time'),col('ends_at','排除结束','time'),col('reason','排除原因'),confirm()],checks=['ends_at >= starts_at'])
fk(r,['user_id','episode_id'],'recovery_episodes',['user_id','id'])
r=t('week_presentations','连续周呈现修订','实际与回顾',[col('week_start','自然周起始','date'),rev(),
    col('override_kind','呈现决定'),col('reason','用户确认依据'),confirm()],pk=('user_id','week_start','revision'),retain=True)
enum(r,'override_kind',['冻结','取消冻结'])

# 原子提交、最小化事件与可恢复数据控制。
r=t('command_receipts','持久提交回执','命令与数据控制',[col('operation_key','操作标识'),
    col('request_hash','规范化请求摘要'),col('commit_id','唯一提交标识'),col('task_id','来源任务标识',nullable=True,
         note='任务过期后可清除此引用，不代表回执失效'),col('authorization_epoch','提交授权修订','positive'),
    col('data_revision','提交数据修订','positive'),col('result_refs','结果标识与版本','json',note='只保留必要标识，恢复时重新授权读取'),
    col('issued_at','操作令牌签发时间','time'),col('expires_at','回执过期时间','time')],pk=('user_id','operation_key'),
    unique=[('user_id','commit_id')])
fk(r,['user_id','task_id'],'task_sessions',['user_id','id'])
r=t('audit_events','最小化业务事件','命令与数据控制',[col('id','事件标识'),col('commit_id','提交标识'),
    col('event_kind','事件类型'),col('object_kind','对象类型'),col('object_id','对象标识'),
    col('object_revision','对象修订','positive',True),col('reason_code','原因编码',nullable=True)],retain=True)
fk(r,['user_id','commit_id'],'command_receipts',['user_id','commit_id'])
r=t('data_control_jobs','导出删除清理任务','命令与数据控制',[ident(),col('job_kind','处理类型'),
    col('state','处理进度'),col('scope_manifest','范围与断点','json'),col('requested_at','请求时间','time'),
    col('deadline_at','目标截止','time'),col('completed_at','完成时间','time',True),
    col('artifact_key','临时导出文件键',nullable=True),col('artifact_expires_at','导出文件过期','time',True),
    col('failure_code','失败原因编码',nullable=True)])
enum(r,'job_kind',['导出','主动删除','期限清理']);enum(r,'state',['待处理','处理中','已完成','失败'])

TYPE_PG={'text':'TEXT','positive':'BIGINT','nonnegative':'BIGINT','bool':'SMALLINT','amount':'BIGINT','time':'TIMESTAMPTZ','date':'DATE','json':'JSONB'}
TYPE_SQLITE={**TYPE_PG,'positive':'INTEGER','nonnegative':'INTEGER','bool':'INTEGER','amount':'INTEGER','time':'TEXT','date':'TEXT','json':'TEXT'}

# 每一外键均生成支持索引；已有主键/唯一索引前缀能支持时不重复。
for row in TABLES:
    supported=[row['pk']]+row['unique']+[x['columns'] for x in row['indexes'] if not x.get('where')]
    for relation in row['fks']:
        fields=relation['columns']
        if not any(x[:len(fields)]==fields for x in supported):
            row['indexes'].append(dict(columns=fields,unique=False));supported.append(fields)

extra_indexes={
 'meal_revisions':[['user_id','meal_date','meal_slot']],
 'action_windows':[['user_id','ends_at']],
 'execution_revisions':[['user_id','execution_date','execution_state']],
 'food_observations':[['user_id','food_name']],
 'context_snapshots':[['user_id','context_key']],
 'interaction_events':[['user_id','context_id','cooldown_until']],
 'reminder_events':[['user_id','scheduled_at']],
 'task_sessions':[['expires_at']], 'media_assets':[['expires_at']],
 'command_receipts':[['expires_at']], 'data_control_jobs':[['state','deadline_at']]}
for row in TABLES:
    for fields in extra_indexes.get(row['name'],[]):row['indexes'].append(dict(columns=fields,unique=False))
    if any(c['name']=='retain_until' for c in row['columns']):row['indexes'].append(dict(columns=['retain_until'],unique=False))

def column_checks(row, sqlite=False):
    result=[]
    for c in row['columns']:
        n,k=c['name'],c['kind']
        if k in ['positive','nonnegative','bool','amount']:
            check = f'{n} >= 1' if k=='positive' else f'{n} >= 0'
            if k=='bool':check=f'{n} IN (0, 1)'
            if k=='amount':check+=f' AND {n} <= 9000000000000000'
            if sqlite:check=f"typeof({n}) = 'integer' AND "+check
            if c['nullable']:check=f'{n} IS NULL OR ({check})'
            result.append(check)
        if k=='json' and sqlite:
            result.append((f'{n} IS NULL OR ' if c['nullable'] else '')+f'json_valid({n})')
        if sqlite and k in ['time','date']:
            check=(f"typeof({n}) = 'text' AND length({n}) = 24 AND strftime('%Y-%m-%dT%H:%M:%fZ', {n}) IS NOT NULL AND strftime('%Y-%m-%dT%H:%M:%fZ', {n}) = {n}" if k=='time'
                   else f"typeof({n}) = 'text' AND length({n}) = 10 AND date({n}, '+0 days') IS NOT NULL AND date({n}, '+0 days') = {n}")
            result.append((f'{n} IS NULL OR ('+check+')') if c['nullable'] else check)
    names={c['name'] for c in row['columns']}
    def plus(field, days):
        return f"strftime('%Y-%m-%dT%H:%M:%fZ', {field}, '+{days} days')" if sqlite else f"{field} + INTERVAL '{days} days'"
    if 'retain_until' in names:
        result.append('retain_until >= created_at')
        result.append(f"((renewed_at IS NULL AND retain_until <= {plus('created_at',180)}) OR (renewed_at IS NOT NULL AND renewed_at >= created_at AND retain_until <= {plus('renewed_at',180)}))")
    ttl={'media_assets':1,'task_sessions':7,'command_receipts':180}.get(row['name'])
    if ttl:
        result += ['expires_at >= created_at',f"expires_at <= {plus('created_at',ttl)}"]
    if row['name']=='plan_revisions':
        result.append("end_date = date(start_date, '+' || (day_count - 1) || ' days')" if sqlite else 'end_date = start_date + CAST(day_count - 1 AS INTEGER)')
    if row['name'] in ['expected_schedules','expected_slots','week_presentations']:
        result.append("strftime('%w', week_start) = '1'" if sqlite else 'EXTRACT(ISODOW FROM week_start) = 1')
    if row['name']=='expected_slots':
        result.append("meal_date >= week_start AND meal_date <= date(week_start, '+6 days')" if sqlite else 'meal_date >= week_start AND meal_date <= week_start + 6')
    if row['name']=='food_observations':result.append("basis_state = '未知' OR basis_micros > 0")
    if row['name']=='data_control_jobs':
        result += ['deadline_at >= requested_at',"state <> '已完成' OR completed_at IS NOT NULL"]
        result.append(f"job_kind <> '主动删除' OR deadline_at <= {plus('requested_at',1)}")
    return result

def render(dialect):
    sqlite=dialect=='sqlite'; types=TYPE_SQLITE if sqlite else TYPE_PG
    lines=['-- DietLens 第二次作业：数据库候选设计，仅保存，不执行。',
           '-- 类型、约束与删除顺序以数据字典和数据库设计正文为准。']
    late=[]
    for row in TABLES:
        name=row['name'];lines+=['',f'-- {row["label"]}（{row["group"]}）',f'CREATE TABLE {name} (']
        parts=[]
        for c in row['columns']:
            s=f'    {c["name"]} {types[c["kind"]]}'
            if not c['nullable']:s+=' NOT NULL'
            if c['default'] is not None:s+=' DEFAULT '+c['default']
            parts.append(s)
        parts.append('    PRIMARY KEY ('+', '.join(row['pk'])+')')
        for u in row['unique']:parts.append('    UNIQUE ('+', '.join(u)+')')
        for check in row['checks']+column_checks(row,sqlite):parts.append('    CHECK ('+check+')')
        for i,f in enumerate(row['fks']):
            clause='FOREIGN KEY ('+', '.join(f['columns'])+') REFERENCES '+f['target']+' ('+', '.join(f['target_columns'])+') ON DELETE NO ACTION DEFERRABLE INITIALLY DEFERRED'
            if f['late'] and not sqlite:late.append(f'ALTER TABLE {name} ADD CONSTRAINT fk_{name}_{i} '+clause+';')
            else:parts.append('    '+clause)
        lines.append(',\n'.join(parts)+'\n);')
        for i,idx in enumerate(row['indexes']):
            lines.append('CREATE '+('UNIQUE ' if idx.get('unique') else '')+f'INDEX ix_{name}_{i} ON {name} ('+', '.join(idx['columns'])+')'+(' WHERE '+idx['where'] if idx.get('where') else '')+';')
    lines+=['','-- 循环的当前版本引用在所有表声明后补充。']+late if late else []
    return '\n'.join(lines)+'\n'

(OUT/'schema.sql').write_text(render('postgres'),encoding='utf-8')
(OUT/'schema.sqlite.sql').write_text(render('sqlite'),encoding='utf-8')
(OUT/'model.json').write_text(json.dumps({'版本':'R2-P4候选','说明':'生成设计产物的结构元数据，不含真实用户数据','tables':TABLES},ensure_ascii=False,indent=2),encoding='utf-8')

lines=['# 数据字典','', '版本：R2-P4候选。物理字段使用稳定技术标识，业务名称、含义和约束说明采用中文。',
       '', '所有时点按UTC存储，业务日期按Asia/Shanghai核对；标识由服务端生成。所有者字段不可由浏览器任意指定。',
       '数量定点值=实际值×1000000；输入超过六位小数时先展示规范化值待核对，不静默截断。所有私有外键含user_id。',
       '空值只表示对应语义中的未知或不适用，具体状态字段控制其含义。子表生命周期随所属聚合，版本内容除清理脱敏外不可原地修改。','']
for row in TABLES:
    lines += [f'## {row["label"]}（{row["name"]}）','',f'责任分区：{row["group"]}。主键：`'+', '.join(row['pk'])+'`。','',
              '| 字段 | 中文含义 | PostgreSQL / SQLite | 可空 | 默认值 | 约束与说明 |','|---|---|---|---|---|---|']
    for c in row['columns']:
        tags=[]
        if c['name'] in row['pk']:tags.append('主键组成')
        if any(c['name'] in f['columns'] for f in row['fks']):tags.append('外键组成，详见表后')
        tags += [c['note']] if c['note'] else []
        if c['kind']=='positive':tags.append('正整数')
        if c['kind']=='nonnegative':tags.append('非负整数')
        if c['kind']=='bool':tags.append('0或1')
        if c['kind']=='amount':tags.append('0至9000000000000000的整数')
        lines.append(f'| `{c["name"]}` | {c["label"]} | {TYPE_PG[c["kind"]]} / {TYPE_SQLITE[c["kind"]]} | '+('是' if c['nullable'] else '否')+' | '+(c['default'] or '无')+' | '+'；'.join(tags)+' |')
    lines+=['','关系、约束及索引：','']
    for f in row['fks']:lines.append('- `'+','.join(f['columns'])+'` → `'+f['target']+'('+','.join(f['target_columns'])+')`；提交时检查，不自动删除关联。')
    for u in row['unique']:lines.append('- 唯一：`'+','.join(u)+'`。')
    for check in row['checks']+column_checks(row):lines.append('- 检查：`'+check+'`。')
    for idx in row['indexes']:lines.append('- '+('唯一' if idx.get('unique') else '查询')+'索引：`'+','.join(idx['columns'])+'`'+('；条件`'+idx['where']+'`' if idx.get('where') else '')+'。')
    lines+=['']
(OUT/'data-dictionary.md').write_text('\n'.join(lines),encoding='utf-8')

# drawDB中文展示投影只承载表、键和关系；完整检查约束仍以schema.sql为准。
name_map={r['name']:r['label'] for r in TABLES}
projection=['-- 中文ER展示投影，只用于drawDB导入；不是迁移脚本。']
for row in TABLES:
    cols=[f'  "{c["label"]}" {TYPE_PG[c["kind"]]}'+(' NOT NULL' if not c['nullable'] else '') for c in row['columns']]
    labels={c['name']:c['label'] for c in row['columns']}
    cols.append('  PRIMARY KEY ('+', '.join('"'+labels[n]+'"' for n in row['pk'])+')')
    for u in row['unique']:cols.append('  UNIQUE ('+', '.join('"'+labels[n]+'"' for n in u)+')')
    projection.append('CREATE TABLE "'+row['label']+'" (\n'+',\n'.join(cols)+'\n);')
for row in TABLES:
    labels={c['name']:c['label'] for c in row['columns']}
    for f in row['fks']:
        target=next(x for x in TABLES if x['name']==f['target']);tl={c['name']:c['label'] for c in target['columns']}
        projection.append('ALTER TABLE "'+row['label']+'" ADD FOREIGN KEY ('+', '.join('"'+labels[n]+'"' for n in f['columns'])+') REFERENCES "'+target['label']+'" ('+', '.join('"'+tl[n]+'"' for n in f['target_columns'])+');')
(OUT/'schema.diagram.sql').write_text('\n\n'.join(projection)+'\n',encoding='utf-8')

print(f'已生成{len(TABLES)}张表的双方言设计SQL、中文展示投影及逐字段数据字典。')
