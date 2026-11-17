"""生成中文接口契约与映射；不导入产品服务、不启动接口、不写业务数据库。"""
from pathlib import Path
import copy
import json
import yaml

ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'api';OUT.mkdir(exist_ok=True)
S={};COMMANDS=[];OPS=[]
def text(desc,maximum=500,**kw):return dict(type='string',description=desc,minLength=1,maxLength=maximum,**kw)
def number(desc,minimum=0,maximum=9000000000000000):return dict(type='integer',format='int64',description=desc,minimum=minimum,maximum=maximum)
def flag(desc):return dict(type='boolean',description=desc)
def en(desc,values):return dict(type='string',description=desc,enum=values)
def date(desc):return dict(type='string',format='date',description=desc)
def instant(desc):return dict(type='string',format='date-time',description=desc)
def uid(desc):return dict(type='string',format='uuid',description=desc)
def ref(name):return {'$ref':'#/components/schemas/'+name}
def array(item,desc,minimum=0,maximum=100):return dict(type='array',description=desc,items=ref(item) if isinstance(item,str) else item,minItems=minimum,maxItems=maximum)
def obj(props,required=None,desc=''):
    r=dict(type='object',additionalProperties=False,properties=props,required=list(props) if required is None else required)
    if desc:r['description']=desc
    return r
def add(name,schema):S[name]=schema;return ref(name)
def version(desc='对象并发版本；0只用于声明目标尚不存在'):return number(desc,0)
def resource():return obj({'resource_kind':en('业务对象类型',['profile','consent','calibration','context','food','plan','slot','preparation','inventory','meal','action','learning','preference','expected','recovery','week','settings','user']),
                          'resource_key':text('服务端给出的本人对象键；不是数据库表名',200),'version':version()})
add('ResourceVersion',resource())
add('KnownQuantity',obj({'state':en('数量已知',['已知']),'amount_micros':number('实际数值乘1000000；禁止用二进制浮点静默截断'),
                         'unit':text('已核对口径，例如g、mL、个、份；仅有规格依据时换算',20)}))
add('UnknownQuantity',obj({'state':en('未知不是零',['未知']),'unit':text('如已知则保留单位',20)},['state']))
add('Quantity',{'description':'已知与未知互斥；数值上限与P4定点设计相同','oneOf':[ref('KnownQuantity'),ref('UnknownQuantity')]})
add('MealSlot',obj({'meal_date':date('Asia/Shanghai业务日期'),'meal_slot':en('规范餐次',['早餐','午餐','晚餐','加餐'])}))
add('PlanSlot',obj({'meal_date':date('Asia/Shanghai计划日期'),'meal_slot':en('计划餐次',['早餐','午餐','晚餐'])}))
add('VersionReference',obj({'id':uid('来源身份'),'revision':number('来源确认修订',1)}))
add('FactReference',obj({'fact_kind':en('内容修订种类，不等于并发版本',['meal_revision','execution_revision','plan_revision','profile_revision','food_observation','context_snapshot','inventory_revision','expected_schedule','action_window','week_presentation','recovery_episode','preference_revision']),
                        'resource_key':text('本人事实身份或自然周键',200),'revision':number('具体内容修订；固定快照取1',1)}))
add('Money',obj({'amount_micros':number('金额乘1000000'),'currency':text('币种代码，比较前须相同',3,pattern='^[A-Z]{3}$')}))
add('Constraint',obj({'kind':en('用户明确的硬约束类别',['过敏','宗教饮食','禁忌','其他']),
                       'value':text('确认内容',200)}))
add('ProfileData',obj({'goals':array(text('确认目标',200),'目标',0,10),
                       'hard_constraints':array('Constraint','确认硬约束',0,30),
                       'soft_preferences':array(text('确认软偏好',200),'可调整偏好',0,30),
                       'budget':ref('Money')},['goals','hard_constraints','soft_preferences']))
add('ProfileView',obj({'state':en('是否已有确认档案',['未建立','已确认']),
                       'version':version(),'data':ref('ProfileData'),'retained_until':instant('有效保留截止')},['state','version'],
                      '未建立时version为0且没有data；已确认时必须返回data和有效截止，关系由语义检查验证。'))
add('ConsentView',obj({'purpose':en('用途',['历史分析','图片外传','提醒']),
                       'scope_key':text('全域或具体图片标识',100),'allowed':flag('当前有效决定'),
                       'version':number('当前修订',1),'recipient':text('图片接收方',200)},['purpose','scope_key','allowed','version']))
add('ConsentInput',obj({'purpose':en('授权用途',['历史分析','图片外传','提醒']),
                        'scope_key':text('全域或已上传图片标识',100),'allowed':flag('允许或撤回'),
                        'asset_id':uid('逐图外传的图片身份'),'recipient':text('外部接收方',200)},['purpose','scope_key','allowed'],
                       '图片外传必须填写同一图片的scope_key、asset_id及recipient；其余用途scope_key为全域且不得带图片。'))
add('CalibrationAnswer',obj({'question_key':text('当前题库的稳定题目标识',80),'question_version':text('题目版本',80),
                             'choice_codes':array(text('题库允许的选项编码',60),'选项',1,3),'text_answer':text('如题目允许则填写',300)},
                            ['question_key','question_version'], '每题至少一个符合题库的回答；题库最多三题，具体文案待P6确认。'))
add('CalibrationQuestion',obj({'key':text('稳定题目标识',80),'version':text('题目版本',80),'prompt':text('已确认题目中文文案'),
                               'options':array(obj({'code':text('选项编码',60),'label':text('中文选项',100)}),'可选项',0,10),
                               'allows_text':flag('是否接受补充文字')}))
add('CalibrationView',obj({'enabled':flag('是否开启'),'questions':array('CalibrationQuestion','题库',0,3),
                           'answers':array('CalibrationAnswer','当前允许读取的回答',0,3),'catalog_state':en('题库配置状态',['可用','尚未配置'])}))
add('SettingsInput',obj({'companion_enabled':flag('陪伴开关'),'collection_enabled':flag('图鉴开关'),
                         'calibration_enabled':flag('校准开关')},desc='提醒订阅走用途授权；客户端不得设置退避计数、冷却或排序权重。'))
add('SettingsView',obj({'version':number('并发版本',1),'settings':ref('SettingsInput'),
                        'unanswered_count':number('仅在提醒订阅有效时累计',0),
                        'backoff_until':instant('如处于静默期则给出截止'),'ranking_version':text('内环规则版本',80)},['version','settings','unanswered_count','ranking_version']))
add('ContextInput',obj({'profile_revision':number('所核对档案修订',1),'situation':text('用户确认的当前情境',1000),
                        'meal_slot':ref('MealSlot'),'people_count':number('准备人数',1,100),
                        'budget':ref('Money'),'availability':array(text('当前可获得条件',200),'可获得性',0,30)},
                       ['profile_revision','situation','people_count','availability']))
add('ContextView',obj({'id':uid('已确认情境身份'),'version':number('固定快照版本',1),'content':ref('ContextInput'),
                       'authorization_epoch':number('当时授权修订，不能代替当前许可',1)}))
add('SourceInput',obj({'source_kind':en('来源类别',['用户自述','商品标签','菜单','公开资料','本地编码']),
                       'locator':text('出处或自述说明；不是任意抓取地址',1000),
                       'specification':text('当前商品或菜单规格',300),'published_at':instant('材料时间'),
                       'asset_id':uid('仍可用且属于本人的图片')},['source_kind','locator']))
add('SourceView',obj({'id':uid('来源身份'),'content':ref('SourceInput'),'acquired_at':instant('取得时间'),
                      'material_state':en('原材料可用性',['可用','原材料已清理','仅有自述'])}))
add('NumericField',obj({'field_key':text('版本化字段目录中的键，例如energy或price',80),
                        'state':en('已知字段核对状态',['已核对','待核对']),'value_kind':en('数值',['数值']),
                        'amount_micros':number('字段数值乘1000000'),'unit':text('字段单位或已核对复合单位',40),
                        'sources':array('SourceInput','字段来源',1,10)}))
add('TextField',obj({'field_key':text('版本化字段目录中的键，例如ingredients',80),
                     'state':en('已知字段核对状态',['已核对','待核对']),'value_kind':en('文字',['文字']),
                     'text_value':text('核对或待核对文字',4000),'sources':array('SourceInput','字段来源',1,10)}))
add('UnresolvedField',obj({'field_key':text('字段键',80),'state':en('尚无可用确定值',['未知','冲突']),
                           'sources':array('SourceInput','可追溯冲突材料',0,10),'reason':text('未知或冲突原因',500)}))
add('FoodField',{'oneOf':[ref('NumericField'),ref('TextField'),ref('UnresolvedField')]})
add('FoodInput',obj({'food_name':text('食品名称',200),'specification':text('当前规格',300),
                     'previous_id':uid('前一食品证据身份'),'basis':ref('Quantity'),
                     'recipe_coverage':en('配方覆盖',['完整已核对','仅部分已知','未知']),
                     'fields':array('FoodField','逐字段事实，字段键不可重复',1,60)},['food_name','basis','recipe_coverage','fields'],
                    '只提交用户核对内容；营养基准、价格基准和币种分别按字段目录解释，不能把营养100g基准套到每份价格。'))
add('FoodView',obj({'id':uid('不可变证据版本身份'),'version':number('固定证据版本号',1),
                    'content':ref('FoodInput'),'sources':array('SourceView','已保存来源',0,600),
                    'field_source_refs':array(obj({'field_key':text('字段键',80),'source_ids':array(uid('来源身份'),'该字段的具体来源',0,10)}),'逐字段来源身份关联',1,60),
                    'retained_until':instant('保留截止')}))
add('IngredientRequirement',obj({'ingredient_id':uid('标准食材身份'),'quantity':ref('Quantity'),
                                'quantity_basis':en('乘人数的依据',['每人','本餐总量']),'source_id':uid('已存在配方依据')},
                               ['ingredient_id','quantity','quantity_basis']))
add('PlannedFoodInput',obj({'item_key':text('本次草稿中稳定且唯一的条目键',80),'food_name':text('食物名称',200),
                            'observation_id':uid('食品证据身份'),'assessment_id':uid('与当前情境匹配的评估'),
                            'quantity':ref('Quantity'),'quantity_basis':en('准备量基准',['每人','本餐总量']),
                            'ingredients':array('IngredientRequirement','已知或明确未知的需求，不能从菜名补造',0,60)},
                           ['item_key','food_name','quantity','quantity_basis','ingredients']))
add('PlannedMealInput',obj({'slot':ref('PlanSlot'),'people_count':number('该餐准备人数',1,100),
                            'foods':array('PlannedFoodInput','该餐多种食物',1,30)}))
add('PlanContent',obj({'mode':en('明确选择计划模式',['完整','指定']),'day_count':dict(type='integer',enum=[1,7],description='一天或七天'),
                       'start_date':date('计划开始日期'),'context_id':uid('已确认情境'),
                       'selected_slots':array('PlanSlot','用户明确选定的槽位；完整模式为3或21个',1,21),
                       'meals':array('PlannedMealInput','确认餐次',1,21)},desc='selected_slots与meals须逐槽相等且无重复；日期在所选1/7日范围内。'))
add('PlanInput',obj({'plan_id':uid('修改已有计划时携带；新计划省略'),'content':ref('PlanContent')},['content']))
add('PlanView',obj({'id':uid('计划身份'),'version':number('并发版本',1),'revision':number('确认内容修订',1),
                    'content':ref('PlanContent'),'active_slots':array('PlanSlot','当前仍生效的槽位',0,21),
                    'planned_meal_refs':array(obj({'slot':ref('PlanSlot'),'planned_meal_id':uid('确认后餐次来源标识')}),'预填及关联餐次来源',1,21),
                    'planned_food_refs':array(obj({'item_key':text('草稿条目键',80),'planned_food_id':uid('确认后来源标识')}),'预填来源',1,630),
                    'retained_until':instant('保留截止')}))
add('PreparationLineInput',obj({'ingredient_id':uid('标准食材'),'unit':text('兼容口径',20),
                                'requirement_ids':array(uid('可追溯食材需求'),'来源需求',1,200),
                                'adjusted_need':ref('Quantity'),'adjustment_reason':text('人工调整时必填',500)},
                               ['ingredient_id','unit','requirement_ids']))
add('PreparationInput',obj({'plan':ref('VersionReference'),'inventory_data_revision':number('只读汇总中用户核对的库存截点',1),
                           'lines':array('PreparationLineInput','待核对汇总条目',1,300)},
                          desc='服务端重算需求及库存差额；客户端不得提交权威差额或把未知库存填零。'))
add('PreparationLineView',obj({'id':uid('清单条目'),'ingredient_id':uid('标准食材'),'known_need':ref('KnownQuantity'),
                               'has_unknown_requirement':flag('另有未知需求'),'stock':ref('Quantity'),'shortage':ref('Quantity'),
                               'purchased_state':en('采购自述',['未报告','已确认','不适用']),
                               'prepared_state':en('准备自述',['未报告','已确认','不适用']),
                               'inventory_reference':ref('VersionReference')},
                              ['id','ingredient_id','known_need','has_unknown_requirement','stock','shortage','purchased_state','prepared_state']))
add('PreparationView',obj({'id':uid('清单身份'),'version':number('并发版本',1),'plan':ref('VersionReference'),
                           'state':en('有效或已失效',['有效','已失效','已取消']),
                           'lines':array('PreparationLineView','汇总及独立准备状态',1,300),
                           'inventory_data_revision':number('库存计算截点',1)}))
add('PreparationDraftLine',obj({'ingredient_id':uid('标准食材'),'unit':text('核对口径',20),
                               'requirement_ids':array(uid('确认计划中的需求身份'),'具体需求出处',1,200),
                               'known_need':ref('KnownQuantity'),'has_unknown_requirement':flag('另有未知需求'),
                               'stock':ref('Quantity'),'shortage':ref('Quantity'),'inventory_reference':ref('VersionReference')},
                              ['ingredient_id','unit','requirement_ids','known_need','has_unknown_requirement','stock','shortage']))
add('PreparationDraftView',obj({'state':en('未保存',['只读草案']),'plan':ref('VersionReference'),
                               'inventory_data_revision':number('库存核对截点',1),
                               'lines':array('PreparationDraftLine','可核对的来源需求与差额',0,300),
                               'issues':array('Issue','已知部分或缺口说明',0,100)},
                              desc='不含已保存清单身份；确认后才生成清单及其条目身份。无配方时可为空并明确缺口。'))
add('InventoryQuantity',{'oneOf':[ref('KnownQuantity'),obj({'state':en('库存未知',['未知']),
                                                        'unit':text('未知量仍需明确库存口径',20)})]})
add('InventoryInput',obj({'inventory_id':uid('修改已有库存时携带'),'ingredient_id':uid('标准食材'),
                         'quantity':ref('InventoryQuantity'),'observed_at':instant('人工核对时间'),'reason':text('原值新值变化原因',500)},
                        ['ingredient_id','quantity','observed_at','reason']))
add('InventoryView',obj({'id':uid('库存身份'),'version':number('并发版本',1),'revision':number('核对修订',1),
                         'ingredient_id':uid('标准食材'),'quantity':ref('Quantity'),'observed_at':instant('核对时间')}))
add('ReportedFoodInput',obj({'item_key':text('餐食内稳定条目键',80),'food_name':text('本人实际食物',200),
                             'quantity':ref('Quantity'),'observation_id':uid('所用食品证据版本'),
                             'planned_food_id':uid('可选计划预填出处'),
                             'entry_source':en('名称和份量仍需核对',['手动自述','计划预填','图文核对'])},
                            ['item_key','food_name','quantity','entry_source']))
add('MealContent',obj({'slot':ref('MealSlot'),'actual_at':instant('如用户知道则保存实际时点'),
                       'foods':array('ReportedFoodInput','一次用餐多项食物',1,50),'note':text('个人自述',2000)},['slot','foods']))
add('MealInput',obj({'record_id':uid('修改同一用餐时携带'),'content':ref('MealContent')},['content']))
add('MealView',obj({'id':uid('个人用餐身份'),'version':number('并发版本',1),'revision':number('有效餐食修订',1),
                    'content':ref('MealContent'),'retained_until':instant('保留截止')}))
add('ActionWindow',obj({'starts_at':instant('行动可开始时点'),'ends_at':instant('用户确认的结束时点'),
                        'timezone':en('业务时区',['Asia/Shanghai']),'reason':text('拟定或修正窗口的原因',500)},
                       desc='按具体行动确认，不设通用固定时长；起点不得晚于终点。'))
add('ActionProposal',obj({'candidate_id':uid('该任务内候选身份，决定后沿用为行动身份'),'context_id':uid('确认情境'),
                          'dimension':en('只改一维',['平替','顺手加法','进食顺序','时序节律']),
                          'cue':text('线索',300),'behavior':text('具体行为',500),'effort':text('努力量',200),
                          'rationale':text('依据',1000),'proposed_window':ref('ActionWindow'),
                          'replacement_of':uid('原被替代提案'),'planned_meal_id':uid('可选计划餐次'),
                          'meal_reference':ref('VersionReference')},
                         ['candidate_id','context_id','dimension','cue','behavior','effort','rationale','proposed_window']))
add('AdoptAction',obj({'candidate_id':uid('当前任务中的候选身份'),'decision':en('采纳',['采纳']),'window':ref('ActionWindow')}))
add('SkipAction',obj({'candidate_id':uid('当前任务中的候选身份'),'decision':en('明确不采纳',['跳过','被替代'])}))
add('ActionDecisionInput',{'oneOf':[ref('AdoptAction'),ref('SkipAction')],
                          'description':'从本任务服务器候选读取含义；决定后物化行动及最终决策，不把采纳当执行。'})
add('ExecutionReport',obj({'state':en('确认自述',['完成','部分','未完成']),'execution_date':date('实际执行业务日期'),
                          'note':text('执行或障碍自述',2000)},['state','execution_date']))
add('ExecutionWithdraw',obj({'state':en('撤回确定自述',['撤回为不确定']),'note':text('修正原因',2000)},['state']))
add('ExecutionInput',obj({'action_id':uid('已采纳行动'),'report':{'oneOf':[ref('ExecutionReport'),ref('ExecutionWithdraw')]}}))
add('ActionView',obj({'id':uid('行动身份'),'version':number('并发版本',1),'proposal':ref('ActionProposal'),
                      'decision':en('最终决策',['采纳','跳过','被替代']),
                      'window':ref('ActionWindow'),'window_revision':number('当前窗口修订',1),
                      'execution':{'oneOf':[ref('ExecutionReport'),ref('ExecutionWithdraw')]},
                      'execution_revision':number('当前执行修订',1),'reported_at':instant('实际报告时间'),
                      'derived_state':en('截至查询时的执行呈现',['未采纳','待反馈','未知','完成','部分','未完成'])},
                     ['id','version','proposal','decision','derived_state']))
add('LearningView',obj({'id':uid('候选身份'),'version':number('采用当前用户数据修订作保守并发守卫，P4未另设候选行版本',1),
                        'kind':en('候选类别',['稳定偏好','情境线索']),'hypothesis':text('待核对内容',2000),
                        'state':en('核对状态',['待核对','已确认','已拒绝','已到期']),
                        'evidence':array('FactReference','已授权来源内容修订',1,100),
                        'range_start':date('证据起点'),'range_end':date('证据终点')}))
add('PreferenceContent',obj({'condition':text('何种情况下',500),'direction':text('偏好方向',500),'scope':text('适用范围',500)}))
add('PreferenceView',obj({'id':uid('稳定规则身份'),'version':number('当前修订',1),'candidate_id':uid('确认候选'),
                          'content':ref('PreferenceContent'),'state':en('规则状态',['有效','已停用'])}))
add('ExpectedInput',obj({'week_start':date('周一日期'),'slots':array('MealSlot','明确确认的预期槽位，可为空',0,100)},
                        desc='日期须在该自然周；从计划导入也必须重新核对分母。空集合时覆盖未知。'))
add('ExpectedView',obj({'version':version(),'content':ref('ExpectedInput'),'state':en('是否已确认',['未确认','已确认'])}))
add('RecoveryExclusion',obj({'starts_at':instant('排除开始'),'ends_at':instant('排除结束'),'reason':text('排除依据',500)}))
add('RecoveryInput',obj({'episode_id':uid('修改已有周期时携带'),'deviation_at':instant('已确认偏离起点'),
                         'return_at':instant('已确认回归终点'),'reason':text('确认情境',1000),
                         'exclusions':array('RecoveryExclusion','排除区间',0,30)},['reason','exclusions']))
add('RecoveryView',obj({'id':uid('周期身份'),'version':number('并发版本',1),'content':ref('RecoveryInput'),
                        'state':en('缺端点不估算',['未闭合','可计算'])}))
add('KnownRatio',obj({'state':en('分母可用',['已知']),'numerator':number('分子'),
                      'denominator':number('分母',1),'ratio':dict(type='number',minimum=0,maximum=1,description='服务端按同一截点计算')}))
add('UnknownRatio',obj({'state':en('不能计算',['未知']),'reason':text('未确认分母、为零或不可得',500),
                        'numerator':number('如已知则给出分子'),'denominator':number('如已知则给出分母')},['state','reason']))
add('Ratio',{'oneOf':[ref('KnownRatio'),ref('UnknownRatio')]})
add('ReviewSnapshot',obj({'snapshot_revision':number('同一用户数据截点',1),'authorization_epoch':number('查询当前授权修订',1),
                          'as_of':instant('统计时点'),'range_start':date('期间起点'),'range_end':date('期间终点'),
                          'completed_actions':number('执行日期归周、按行动去重的完成数'),
                          'ended_actions':number('当前确认窗口归结束队列的E'),
                          'reported_actions':number('E中有效完成/部分/未完成反馈R'),
                          'done_in_ended_cohort':number('R中的完成D'),
                          'feedback_coverage':ref('Ratio'),'completion_among_reported':ref('Ratio'),
                          'meal_coverage':ref('Ratio'),'extra_meal_slots':array('MealSlot','预期外的实际槽位',0,500),
                          'nutrition_note':text('可计算条目及未知范围',2000),
                          'observation_level':en('依据餐次覆盖限制观察强度',['记录范围内周期观察','仅限已记录次数','基础汇总']),
                          'source_refs':array('FactReference','当前可用事实的来源摘录；不是完整来源全集',0,1000),
                          'has_more_sources':flag('来源摘录超过上限时为真；完整来源经同截点分页查询'),
                          'week_presentations':array(obj({'week_start':date('周一'),'state':en('冻结不补完成',['完成','冻结','未知'])}),'周呈现',0,54)}))

# 用例命令为带判别字段的封闭集合。
def command(kind,label,data,fr,module,tables):
    name='Command'+''.join(x.title() for x in kind.split('.'))
    add(name,obj({'kind':en('命令类型',[kind]),'data':ref(data)}))
    COMMANDS.append(dict(kind=kind,label=label,schema=name,data_schema=data,requirements=fr,module=module,tables=tables))
command('profile.confirm','确认或修订档案','ProfileData',['FR-001'],'档案与授权',['profile_revisions','user_control'])
command('consent.change','变更用途授权','ConsentInput',['FR-011'],'档案与授权',['consent_revisions','user_control'])
command('calibration.answer','确认校准回答','CalibrationAnswer',['FR-001','FR-011'],'档案与授权',['calibration_revisions'])
command('settings.change','修改可选交互开关','SettingsInput',['FR-008','FR-011'],'微行动',['interaction_settings'])
command('context.confirm','确认当前情境','ContextInput',['FR-003','FR-020'],'档案与授权',['context_snapshots'])
command('food.confirm','逐字段核对食品','FoodInput',['FR-002','FR-012','FR-015','FR-016'],'食品证据',['food_observations','food_fields','field_sources','source_references'])
command('plan.confirm','确认或替换计划','PlanInput',['FR-017','FR-020'],'计划与准备',['plan_heads','plan_revisions','planned_meals','planned_foods','ingredient_requirements','slot_assignments'])
command('preparation.confirm','核对准备采购清单','PreparationInput',['FR-018'],'计划与准备',['preparation_lists','preparation_lines','preparation_sources'])
add('PreparationStatusInput',obj({'list_id':uid('有效清单'),'line_id':uid('条目'),
                                  'purchased_state':en('采购自述',['未报告','已确认','不适用']),
                                  'prepared_state':en('准备自述',['未报告','已确认','不适用'])},['list_id','line_id'],
                                 '至少修改一项；两项独立，不带未修改项也不默认改为未报告。'))
S['PreparationStatusInput']['minProperties']=3
S['CalibrationAnswer']['minProperties']=3
S['PlanContent']['properties']['selected_slots']['uniqueItems']=True
S['ExpectedInput']['properties']['slots']['uniqueItems']=True
command('preparation.status','报告已购或已准备','PreparationStatusInput',['FR-018','FR-019','FR-020'],'计划与准备',['preparation_lists','preparation_lines'])
command('inventory.confirm','核对或修订库存','InventoryInput',['FR-019'],'计划与准备',['inventory_heads','inventory_revisions','preparation_lists'])
command('meal.confirm','确认或修订个人用餐','MealInput',['FR-014','FR-020'],'实际餐食',['meal_heads','meal_revisions','reported_foods'])
command('action.decide','采纳跳过或替代候选','ActionDecisionInput',['FR-004','FR-005','FR-020'],'微行动',['micro_actions','action_decisions','action_windows','interaction_events'])
add('WindowInput',obj({'action_id':uid('已采纳行动'),'window':ref('ActionWindow')}))
command('action.window','显式修正行动窗口','WindowInput',['FR-007','FR-008'],'微行动',['micro_actions','action_windows'])
command('action.feedback','报告或更正执行','ExecutionInput',['FR-006','FR-007'],'微行动',['micro_actions','execution_revisions'])
add('LearningDecisionInput',obj({'candidate_id':uid('已展示候选'),'decision':en('用户核对结果',['确认','拒绝']),
                                'preference_content':ref('PreferenceContent')},['candidate_id','decision'],
                               '稳定偏好确认必须给出核对后的规则内容并同事务建立规则；情境确认不产生心理标签。'))
command('learning.decide','核对偏好或情境候选','LearningDecisionInput',['FR-008','FR-011'],'微行动',['learning_candidates','preference_rule_revisions','learning_evidence'])
add('PreferenceInput',obj({'rule_id':uid('已有规则'),'content':ref('PreferenceContent'),'state':en('用户决定',['有效','已停用'])}))
command('preference.confirm','修订或停用稳定规则','PreferenceInput',['FR-001','FR-008'],'微行动',['preference_rule_revisions'])
command('expected.confirm','确认预期餐次分母','ExpectedInput',['FR-009'],'回顾查询',['expected_schedules','expected_slots'])
command('recovery.confirm','确认恢复起止与排除','RecoveryInput',['FR-009'],'回顾查询',['recovery_episodes','recovery_exclusions'])
add('WeekInput',obj({'week_start':date('周一'),'decision':en('冻结是呈现决定',['冻结','取消冻结']),'reason':text('核对的情境依据',1000)}))
command('week.present','确认连续周呈现','WeekInput',['FR-009','FR-011'],'回顾查询',['week_presentations'])
add('ExportInput',obj({'scope':en('导出本人允许访问的各类对象',['本人全部数据']),'format':en('结构化中文说明和技术标识',['JSON'])}))
command('data.export','请求导出本人数据','ExportInput',['FR-011'],'期限与数据控制',['data_control_jobs'])
add('DeleteTarget',obj({'resource_kind':en('可删除的业务范围',['profile','context','food','plan','preparation','inventory','meal','action','learning','preference','calibration','expected','recovery','week']),
                       'resource_key':text('本人对象键，校准可指题目标识',200)}))
add('DeleteAll',obj({'scope':en('全量删除',['本人全部数据'])}))
add('DeleteSome',obj({'scope':en('部分删除',['指定对象']),'targets':array('DeleteTarget','预览实际依赖影响',1,50)}))
add('DeleteInput',{'oneOf':[ref('DeleteAll'),ref('DeleteSome')]})
command('data.delete','确认范围后请求删除','DeleteInput',['FR-011','FR-020'],'期限与数据控制',['user_control','data_control_jobs'])
renew_target=resource();renew_target['properties']['resource_kind']=copy.deepcopy(S['DeleteTarget']['properties']['resource_kind'])
renew_target['properties']['version']=number('所见本人对象并发版本',1)
add('RenewTarget',renew_target)
add('RenewInput',obj({'targets':array('RenewTarget','明确续期的本人业务对象及依赖版本',1,50),
                      'retained_until':instant('明确确认的新截止；不超过本次确认后180天')}))
renew_tables=[t['name'] for t in json.loads((ROOT/'database/model.json').read_text(encoding='utf-8'))['tables'] if any(c['name']=='retain_until' for c in t['columns'])]
command('data.renew','确认业务保留续期','RenewInput',['FR-011'],'期限与数据控制',renew_tables)
add('CommandIntent',{'description':'客户端只能选择这22种用例，不能提交任意表写入或工具名',
                     'oneOf':[ref(c['schema']) for c in COMMANDS],
                     'discriminator':{'propertyName':'kind','mapping':{c['kind']:'#/components/schemas/'+c['schema'] for c in COMMANDS}}})
add('Issue',obj({'code':text('稳定机器编码',80),'message':text('中文说明',1000),
                 'field_path':text('受影响字段路径',200),'resolution':text('继续方式',1000)},['code','message','resolution']))
add('PreviewRequest',obj({'task_id':uid('本人未过期任务'),'draft_revision':number('用户正在核对的任务草稿修订',1),
                          'intent':ref('CommandIntent'),'expected_versions':array('ResourceVersion','用户所见版本；服务器补齐隐含依赖守卫',0,200)}))
add('DeletionStatusAccess',obj({'job_id':uid('预分配的本次删除任务身份'),'token':text('仅查询本次进度的不透明凭证，不得写日志',2000),
                              'expires_at':instant('签发后最多7天'),'scope':en('不允许读取原数据或下载',['仅查询本次删除进度'])}))
preview_props={'id':uid('预览身份'),'task_id':uid('所属任务'),'draft_revision':number('服务器保存后的草稿修订',1),
               'intent':ref('CommandIntent'),'guards':array('ResourceVersion','完整并发守卫',0,300),
               'authorization_epoch':number('绑定授权修订',1),'expires_at':instant('确认预览最多15分钟，且不超过任务及证据期限；不是行动反馈窗口'),
               'impact':array(text('将变更的事实或明确的独立副作用',1000),'用户可核对的影响',1,100),
               'issues':array('Issue','待核对项',0,100)}
ready_required=list(preview_props)+['state','operation_key','preview_digest','confirmation_token']
add('ReadyPreview',obj({**preview_props,'state':en('允许展示确认按钮',['可确认']),
                        'operation_key':uid('服务端为本内容签发的幂等键'),
                        'preview_digest':text('服务端规范化内容及影响摘要',64,pattern='^[a-f0-9]{64}$'),
                        'confirmation_token':text('绑定用户、任务、内容、版本、影响和期限的不透明令牌',2000),
                        'deletion_status_access':ref('DeletionStatusAccess')},ready_required,
                       '删除预览在提交前发放仅限本次进度的凭证；响应丢失且身份映射已清理后仍可查询，不能复原业务数据。'))
add('BlockedPreview',obj({**preview_props,'state':en('不签发可提交令牌',['待核对'])}))
add('PreviewView',{'oneOf':[ref('ReadyPreview'),ref('BlockedPreview')]})
add('CommitRequest',obj({'preview_id':uid('待确认预览'),'draft_revision':number('核对的草稿修订',1),
                         'preview_digest':text('回显预览摘要',64,pattern='^[a-f0-9]{64}$'),
                         'confirmation_token':text('原预览不透明令牌',2000),'decision':en('明确确认',['确认'])}))
add('Receipt',obj({'operation_key':uid('原操作标识'),'commit_id':uid('唯一提交标识'),
                   'state':en('只表示命令提交，不代表后台清理完成',['已提交']),
                   'committed_at':instant('实际提交时点'),'data_revision':number('提交后的数据修订',1),
                   'result_refs':array('ResourceVersion','当前授权内仍可返回的结果引用',0,300),
                   'job_ids':array(uid('后续导出或删除任务'),'待跟踪任务',0,50),
                   'replayed':flag('是否返回已有提交'),'redacted':flag('部分原结果已删或无权而被隐藏')}))
add('Problem',obj({'code':text('稳定错误编码',80),'title':text('中文错误标题',200),'detail':text('用户可理解的原因',2000),
                   'status':number('HTTP状态',400,599),'request_id':uid('本次请求诊断标识'),
                   'commit_state':en('不能以失败状态推断从未提交',['未提交','已提交','结果待核对','不可返回']),
                   'retry_strategy':en('明确恢复方式',['修正后重新预览','重新登录','查询原回执','稍后查询','停止']),
                   'issues':array('Issue','字段或业务冲突信息',0,100),
                   'current_versions':array('ResourceVersion','授权范围内当前版本',0,200)},
                  ['code','title','detail','status','request_id','commit_state','retry_strategy']))
add('TaskCreate',obj({'client_request_id':uid('仅用于临时任务创建去重的客户端请求标识'),
                      'entry':en('当前入口',['微行动','食品查询','营养比较','菜单推荐','饮食计划','准备清单','库存','实际记餐','期间回顾','数据控制','档案'])}))
add('TaskMessage',obj({'request_key':uid('任务内消息重提去重标识'),'expected_draft_revision':number('所见草稿修订',1),
                       'text':text('本人输入，不作系统指令',4000),'asset_ids':array(uid('本人已上传图片'),'仅引用材料，不等于外传授权',0,5)},
                      ['request_key','expected_draft_revision','text']))
add('TaskStateInput',obj({'state':en('只改变临时进度',['已暂停','进行中','已取消']),
                         'expected_draft_revision':number('所见任务草稿修订',1)}))
add('Budget',obj({'tools_used':number('重试累计在高层工具调用内',0,3),'models_used':number('模型尝试次数',0,2),
                  'readonly_retries_used':number('只读瞬时重试次数',0,1),'step_deadline':instant('步骤总截止'),
                  'paid_state':en('没有配置不能付费调用',['无配置已停止付费','可用','预算耗尽','费用待核对'])}))
add('AnalysisControl',obj({'task_id':uid('本人任务'),'request_key':uid('本次分析重试去重标识'),
                           'expected_draft_revision':number('所见草稿修订',1)}))
add('FoodCandidate',obj({'candidate_id':uid('任务内候选'),'content':ref('FoodInput'),'issues':array('Issue','字段缺口',0,100)}))
add('FoodAnalysisResult',obj({'kind':en('食品候选',['food']),'candidates':array('FoodCandidate','核对前仅候选',0,50)}))
add('ComparisonRow',obj({'field_key':text('比较字段',80),'observation_ids':array(uid('所用食品证据'),'参与对象',2,6),
                         'basis':ref('Quantity'),'values':array(obj({'observation_id':uid('食品证据'),'value':ref('Quantity')}),'同口径字段值',2,6),
                         'note':text('缺值或不可换算说明',1000)}))
add('ComparisonResult',obj({'kind':en('营养比较',['comparison']),'rows':array('ComparisonRow','可计算部分与未知',0,60)}))
add('MenuResult',obj({'kind':en('现实菜单筛选',['menu']),'eligible_observation_ids':array(uid('已核对且通过的条目'),'可靠候选，可为空',0,30),
                      'blocked':array('Issue','被阻止条目及原因',0,100),'explanation':text('依据与可继续路径',2000)}))
plan_draft=copy.deepcopy(S['PlanContent']);plan_draft['properties']['meals']['minItems']=0
add('PlanDraftContent',plan_draft)
add('PlanAnalysisResult',obj({'kind':en('计划草案',['plan']),'content':ref('PlanDraftContent'),
                             'completed_steps':number('周计划累计步骤',1,3),'incomplete_slots':array('PlanSlot','缺口保持草案',0,21)}))
add('ActionAnalysisResult',obj({'kind':en('行动候选',['action']),'candidates':array('ActionProposal','完整候选；未决定仍在任务内',0,3)}))
add('ReviewTextResult',obj({'kind':en('回顾表述',['review_text']),'snapshot_revision':number('只解释所绑定的聚合截点',1),
                           'text':text('中文解释；模型失败用模板',8000),'source_mode':en('表达来源',['模型整理','规则模板'])}))
add('AnalysisResult',{'oneOf':[ref(n) for n in ['FoodAnalysisResult','ComparisonResult','MenuResult','PlanAnalysisResult','ActionAnalysisResult','ReviewTextResult']],
                       'discriminator':{'propertyName':'kind','mapping':{k:'#/components/schemas/'+v for k,v in {
                           'food':'FoodAnalysisResult','comparison':'ComparisonResult','menu':'MenuResult',
                           'plan':'PlanAnalysisResult','action':'ActionAnalysisResult','review_text':'ReviewTextResult'}.items()}}})
add('AnalysisResponse',obj({'task_id':uid('任务身份'),'draft_revision':number('分析保存后的任务修订',1),
                            'state':en('失败也可保留已确认资料',['可核对','部分结果','已停止']),
                            'result':ref('AnalysisResult'),'issues':array('Issue','停止原因及缺口',0,100),'budget':ref('Budget')},
                           ['task_id','draft_revision','state','issues','budget'],
                          '可核对时必须有result；依赖失败且没有结果时省略result并说明停止原因，不能伪造空成功。'))
add('TaskView',obj({'id':uid('任务身份'),'state':en('任务进度',['进行中','已暂停','已取消','已完成']),
                    'draft_revision':number('当前临时修订',1),'expires_at':instant('最长7天'),
                    'next_step':en('已注册流程中的下一步',['核对情境','核对食品','核对计划','核对餐食','选择行动','报告执行','查看回顾','已停止']),
                    'prompt':text('中文提示',2000),'last_analysis':ref('AnalysisResponse'),'pending_preview_id':uid('尚可核对的预览')},
                   ['id','state','draft_revision','expires_at','next_step','prompt']))
add('MediaView',obj({'id':uid('临时图片身份'),'state':en('材料状态',['可用','待清理','已清理']),
                     'expires_at':instant('上传后最长24小时'),'content_hash':text('内容摘要',64,pattern='^[a-f0-9]{64}$')},
                    desc='不返回存储文件键；上传不代表已同意外传。'))
add('DataJob',obj({'id':uid('导出删除任务'),'kind':en('请求类型',['导出','主动删除','期限清理']),
                   'state':en('真实处理进度',['待处理','处理中','已完成','失败']),'requested_at':instant('请求时间'),
                   'deadline_at':instant('主动删除最迟24小时退出处理'),'completed_at':instant('仅完成后提供'),
                   'summary':text('已处理及剩余范围，不含被删敏感正文',2000),
                   'failure_code':text('失败编码',80),'artifact_expires_at':instant('可下载文件过期；最长24小时')},
                  ['id','kind','state','requested_at','deadline_at','summary']))

spec={'openapi':'3.0.3','info':{'title':'DietLens 饮食管理接口设计','version':'2.0.0-design-p5',
       'description':'第二次作业P5候选契约。仅设计，未实现或部署。查询、候选、变更预览与确认提交分开；个人资料只经本人认证访问。'},
      'servers':[{'url':'https://dietlens.invalid/api/v2','description':'保留示例域名，仅说明目标路径，不是可调用服务'}],
      'security':[{'bearerAuth':[]}], 'tags':[{'name':n,'description':d} for n,d in [
       ('任务与恢复','临时进度与候选，不自动确认业务'),('档案与授权','本人档案、校准和当前用途'),
       ('食品与分析','带来源候选及有界外部工具'),('计划与准备','未来安排、采购与人工库存'),
       ('实际与行动','个人实际自述及独立微行动反馈'),('回顾与学习','同一截点的有效事实与核对候选'),
       ('确认命令','所有业务变化经绑定内容的预览及确认'),('数据控制','导出删除进度及受控文件下载'),('运行状态','最小运行信息')]],
      'paths':{},'components':{'securitySchemes':{'bearerAuth':{'type':'http','scheme':'bearer','bearerFormat':'JWT',
           'description':'托管模式验证签发方、受众、期限与主体；本地演示身份仅显式离线配置，验证失败不回退。'},
           'deletionStatusTicket':{'type':'apiKey','in':'header','name':'X-Deletion-Status-Token',
             'description':'只用于原删除任务进度；绑定同一已验证身份主体和预分配job_id，最多7天，不授予原事实、导出文件或其他任务访问权。'}},'schemas':S,'responses':{},'parameters':{}}}
header_base={'X-Request-Id':{'description':'本次请求诊断标识','schema':uid('诊断标识')},
             'Cache-Control':{'description':'个人结果统一no-store','schema':{'type':'string','enum':['no-store']}}}
for status,desc in {'400':'请求语法或操作标识格式错误','401':'身份缺失、无效或过期','403':'本人身份有效但当前用途不允许',
                    '404':'对象不存在或不属于本人；不透露其他用户的存在性','409':'版本、草稿、幂等键、游标或快照冲突，须按编码处理',
                    '410':'已验证本人归属的任务、材料、预览或下载已到期',
                    '413':'图片超过技术大小限制','415':'不支持的图片或内容类型','422':'结构或业务输入不合法',
                    '429':'有界并发或调用预算限制','503':'依赖或数据库暂不可用；提交是否成功以commit_state及原回执为准'}.items():
    headers=copy.deepcopy(header_base)
    if status=='401':headers['WWW-Authenticate']={'description':'要求合法访问令牌','schema':{'type':'string'}}
    if status in ['429','503']:headers['Retry-After']={'description':'如可建议等待则返回秒数；不表示可以新键重做写入','schema':{'type':'integer','minimum':1}}
    spec['components']['responses']['Error'+status]={'description':desc,'headers':headers,
        'content':{'application/problem+json':{'schema':ref('Problem')}}}

def param(name,desc,schema,where='query',required=False):return {'name':name,'in':where,'required':required,'description':desc,'schema':schema}
def operation(path,method,opid,label,tag,response,fr,module,tables,body=None,params=None,status='200',desc='',errors=None):
    params=list(params or [])
    import re
    for name in re.findall(r'{([^}]+)}',path):
        if not any(p['name']==name and p['in']=='path' for p in params):
            params.append(param(name,'本人对象标识',uid('对象标识'),'path',True))
    schema=ref(response) if isinstance(response,str) else response
    headers=copy.deepcopy(header_base)
    if method=='get' and '{' in path:headers['ETag']={'description':'如该对象支持修改，则返回其强版本标签；以预览守卫为准','schema':{'type':'string'}}
    result={'operationId':opid,'summary':label,'description':desc or label+'；返回前检查当前授权和对象有效性。',
            'tags':[tag],'parameters':params,'responses':{status:{'description':'成功返回；待处理任务不表示业务处理已完成',
            'headers':headers,'content':{'application/json':{'schema':schema}}}},
            'x-requirements':fr,'x-module':module,'x-tables':tables}
    for e in errors or ['400','401','403','404','409','410','422','429','503']:
        result['responses'][e]={'$ref':'#/components/responses/Error'+e}
    if body:result['requestBody']={'required':True,'content':{'application/json':{'schema':ref(body) if isinstance(body,str) else body}}}
    spec['paths'].setdefault(path,{})[method]=result
    OPS.append(dict(operationId=opid,path=path,method=method.upper(),label=label,requirements=fr,module=module,tables=tables))
    return result

def listing(path,opid,label,tag,item,fr,module,tables,dated=False):
    name=item+'Page'
    if name not in S:add(name,obj({'items':array(item,'当前授权内结果',0,50),'next_cursor':text('如还有下一页才提供',2000),
                                  'snapshot_revision':number('当前用户数据截点',1)},['items','snapshot_revision']))
    params=[param('limit','每页数量',dict(type='integer',minimum=1,maximum=50,default=20)),
            param('cursor','不透明且绑定用户、过滤条件及数据截点的游标',text('游标',2000)),
            param('snapshot_revision','可绑定回顾已展示截点；变化时返回409要求刷新',number('所见用户数据修订',1))]
    if dated:params += [param('from','含起点日期',date('开始日期')),param('to','含终点日期',date('结束日期'))]
    return operation(path,'get',opid,label,tag,name,fr,module,tables,params=params)

operation('/tasks','post','createTask','创建临时任务','任务与恢复','TaskView',['FR-002','FR-010'],'命令与任务',['task_sessions'],body='TaskCreate',status='201',
          desc='本人域内按client_request_id及请求摘要去重，最多任务7天；到期后新建任务也不重放业务确认。')
listing('/tasks','listTasks','列出可恢复任务','任务与恢复','TaskView',['FR-010'],'命令与任务',['task_sessions'])
operation('/tasks/{task_id}','get','getTask','读取或恢复任务','任务与恢复','TaskView',['FR-010','FR-013'],'命令与任务',['task_sessions'],
          desc='先验证当前归属、授权及期限；已提交事实不因任务取消而撤销，过期草稿不能直接提交。')
operation('/tasks/{task_id}','patch','changeTaskState','暂停恢复或取消临时任务','任务与恢复','TaskView',['FR-010','FR-013'],'命令与任务',['task_sessions'],body='TaskStateInput',
          desc='仅改变临时进度，取消不撤销已经确认的事实。正文中的预期草稿修订不匹配返回409，缺少则422；不使用HTTP条件请求代替业务守卫。')
operation('/tasks/{task_id}/messages','post','continueTask','提交对话并获取下一步','任务与恢复','TaskView',['FR-001','FR-002','FR-010','FR-013'],'命令与任务',['task_sessions'],body='TaskMessage',
          desc='消息按任务内request_key去重；内容只作用户输入。外调仍受每步工具3次、模型2次、只读重试1次和15秒总截止，不自动提交业务。')
operation('/profile','get','getProfile','读取本人确认档案','档案与授权','ProfileView',['FR-001'],'档案与授权',['user_control','profile_revisions'])
listing('/consents','getConsents','读取当前用途授权','档案与授权','ConsentView',['FR-011'],'档案与授权',['consent_revisions'])
operation('/calibration','get','getCalibration','读取校准题库和回答','档案与授权','CalibrationView',['FR-001','FR-011'],'档案与授权',['calibration_revisions','interaction_settings'])
operation('/interaction-settings','get','getSettings','读取可选交互与退避状态','档案与授权','SettingsView',['FR-008','FR-011'],'微行动',['interaction_settings'])
operation('/contexts/{context_id}','get','getContext','读取已确认情境','档案与授权','ContextView',['FR-003','FR-020'],'档案与授权',['context_snapshots'])
operation('/media','post','uploadMedia','上传本地核对图片','食品与分析','MediaView',['FR-002','FR-012'],'食品证据',['media_assets','task_sessions'],status='201',
          desc='仅存本地受控临时图片，最长24小时；不发外部。JPEG/PNG且不超过10MiB，解码后核验并清理元数据。同一任务上传键及内容摘要去重，已到期键不复活材料。',
          errors=['400','401','403','404','409','410','413','415','422','429','503'])
spec['paths']['/media']['post']['requestBody']={'required':True,'content':{'multipart/form-data':{'schema':obj({
    'task_id':uid('本人未过期任务'),'upload_key':uid('任务内上传重试键'),'file':{'type':'string','format':'binary','description':'JPEG/PNG图片，最长24小时'}})}}}
operation('/media/{asset_id}','get','getMediaStatus','读取图片有效性','食品与分析','MediaView',['FR-011','FR-012'],'食品证据',['media_assets'])
media_content=operation('/media/{asset_id}/content','get','readMediaContent','在有效期内核对本人原图','食品与分析',{'type':'string','format':'binary'},
                        ['FR-010','FR-011','FR-012'],'食品证据',['media_assets','user_control'],
                        desc='认证后读取本人未过期原图供核对；不返回内部文件键，不因本地查看自动授权外传；24小时到期或删除后不可读取。')
media_content['responses']['200']['content']={mime:{'schema':{'type':'string','format':'binary','description':'本人有效期内的核对图片'}} for mime in ['image/jpeg','image/png']}
listing('/foods','searchFoodFacts','检索已核对食品证据','食品与分析','FoodView',['FR-002','FR-015'],'食品证据',['food_observations','food_fields','source_references'])['parameters'].append(param('q','食品名称关键词',text('关键词',100),required=True))
operation('/foods/{observation_id}','get','getFoodFact','读取指定食品证据版本','食品与分析','FoodView',['FR-002','FR-012','FR-015'],'食品证据',['food_observations','food_fields','field_sources'])
operation('/sources/{source_id}','get','getSource','读取当前可用来源','食品与分析','SourceView',['FR-012','FR-015'],'食品证据',['source_references','media_assets'])
add('IngredientView',obj({'id':uid('本人标准食材身份'),'name':text('标准食材名称',200),'catalog_code':text('外部编码，仅说明编码命中',100)},['id','name']))
listing('/ingredients','listIngredients','读取标准食材目录','计划与准备','IngredientView',['FR-018','FR-019'],'计划与准备',['ingredients'])
add('IngredientResolveInput',obj({'task_id':uid('本人任务'),'request_key':uid('任务内去重标识'),
                                 'names':array(text('用户核对的食材名称',200),'待解析名称',1,100)}))
add('IngredientResolveView',obj({'items':array(obj({'name':text('原食材名',200),'candidate_key':text('任务内临时食材键',100),
                                                'matched_id':uid('仅已有食材时给出')},['name','candidate_key']),'匹配或待确认项',1,100)}))
operation('/ingredients/resolve','post','resolveIngredients','核对已有食材或形成临时匹配','计划与准备','IngredientResolveView',['FR-018','FR-019'],'计划与准备',['task_sessions','ingredients'],body='IngredientResolveInput',
          desc='未知食材先存任务内候选，不直接写业务目录；须通过ingredient.confirm确认后才获得持久标识。')
add('IngredientInput',obj({'name':text('核对的标准食材名',200),'candidate_key':text('本任务内食材候选键',100)},['name','candidate_key']))
command('ingredient.confirm','确认标准食材身份','IngredientInput',['FR-018','FR-019'],'计划与准备',['ingredients'])
# 更新封闭命令集合，所有后加命令仍由同一入口处理。
S['CommandIntent']['oneOf']=[ref(c['schema']) for c in COMMANDS]
S['CommandIntent']['discriminator']['mapping']={c['kind']:'#/components/schemas/'+c['schema'] for c in COMMANDS}
S['CommandIntent']['description']=f'客户端只能选择这{len(COMMANDS)}种用例，不能提交任意表写入或工具名'

control=S['AnalysisControl']['properties']
analysis_specs=[
 ('food','parseFood','解析标签菜单或餐食图片',obj({**control,'text':text('用户文字',4000),'asset_ids':array(uid('本人图片'),'图片需逐图逐接收方许可才可外传',0,5)},list(control), '文字或图片至少一项；纯文字路径可独立继续。'),['FR-002','FR-003','FR-012']),
 ('comparisons','compareFoods','比较同口径营养',obj({**control,'observation_ids':array(uid('已核对食品证据'),'比较对象',2,6),'basis':ref('Quantity')}),['FR-015']),
 ('menus','recommendMenu','筛选现实菜单',obj({**control,'context_id':uid('确认情境'),'observation_ids':array(uid('菜单食品证据'),'现实可获得条目',1,30)}),['FR-003','FR-016']),
 ('plans','proposePlan','形成分步日周计划草案',obj({**control,'context_id':uid('确认情境'),'mode':en('计划模式',['完整','指定']),
      'day_count':dict(type='integer',enum=[1,7],description='一天或七天'),'start_date':date('起点'),'selected_slots':array('PlanSlot','用户选择',1,21)}),['FR-003','FR-017']),
 ('actions','proposeAction','形成完整微行动候选',obj({**control,'context_id':uid('确认情境'),'replacement_of':uid('已明确替代的原提案')},list(control)+['context_id']),['FR-003','FR-004','FR-008']),
 ('review-text','explainReview','表述已计算的期间回顾',obj({**control,'range_start':date('期间起点'),'range_end':date('期间终点'),
      'snapshot_revision':number('已展示的服务端聚合截点',1)}),['FR-009'])]
for suffix,opid,label,schema,fr in analysis_specs:
    operation('/analyses/'+suffix,'post',opid,label,'食品与分析','AnalysisResponse',fr+['FR-013'],'外部工具执行',['task_sessions','constraint_assessments'],body=schema,
              desc='在当前授权及有界预算下产生候选或解释，不确认业务事实。模型与来源请求在写事务外；请求键去重，晚到结果丢弃。缺关键证据返回部分结果或停止。')
del S['AnalysisControl']
plans_list=listing('/plans','listPlans','读取计划及当前范围','计划与准备','PlanView',['FR-017'],'计划与准备',['plan_heads','plan_revisions','slot_assignments'],True)
plans_list['description']='日期范围按当前有效槽位与所选期间是否相交过滤，不按计划创建时间过滤；仍分别返回确认内容和当前剩余范围。'
operation('/plans/{plan_id}','get','getPlan','读取指定计划版本','计划与准备','PlanView',['FR-017','FR-020'],'计划与准备',['plan_heads','plan_revisions','planned_meals','planned_foods'],params=[param('revision','省略取当前确认内容；旧版仍须当前授权',number('内容修订',1))])
operation('/plans/{plan_id}/preparation-preview','get','getPreparationDraft','只读汇总需求与库存差额','计划与准备','PreparationDraftView',['FR-018','FR-019'],'计划与准备',['ingredient_requirements','inventory_revisions','preparation_lists'],
          desc='由完整仍当前的确认计划版本形成只读草案；不隐式保存或预留库存。源版本若已部分被替换，先明确整合范围并确认新计划版本，不把残存范围静默当成原版本。缺配方保留缺口。')
operation('/preparations/{list_id}','get','getPreparation','读取准备清单及独立状态','计划与准备','PreparationView',['FR-018','FR-020'],'计划与准备',['preparation_lists','preparation_lines'])
listing('/inventory','listInventory','读取人工核对库存','计划与准备','InventoryView',['FR-019'],'计划与准备',['inventory_heads','inventory_revisions'])
listing('/meal-records','listMealRecords','读取本人实际用餐','实际与行动','MealView',['FR-014'],'实际餐食',['meal_heads','meal_revisions','reported_foods'],True)
operation('/meal-records/{record_id}','get','getMealRecord','读取实际用餐及多食物','实际与行动','MealView',['FR-014','FR-020'],'实际餐食',['meal_heads','meal_revisions','reported_foods'],params=[param('revision','可选历史修订，仍检查当前授权',number('内容修订',1))])
operation('/plans/{plan_id}/meal-prefill','get','prefillMeal','只读预填个人餐食草稿','实际与行动','MealContent',['FR-014','FR-020'],'实际餐食',['planned_foods','plan_revisions'],
          params=[param('planned_meal_id','所用计划餐次',uid('计划餐次'),required=True)],
          desc='只带名称、来源及待核对条目；个人份量默认未知，不把多人准备量当摄入，不保存或扣库存。')
actions_list=listing('/actions','listActions','读取本人行动与有效反馈','实际与行动','ActionView',['FR-005','FR-006','FR-007'],'微行动',['micro_actions','action_decisions','action_windows','execution_revisions'],True)
actions_list['parameters'] += [param('date_basis','有日期过滤时采用哪种业务归属',en('日期口径',['执行日期','窗口结束日期'])),
                               param('as_of','可固定到回顾统计时点，不能晚于服务器当前时间',instant('统计时点'))]
actions_list['description']='带from/to时必须同时指定date_basis；完成查询按当前执行日期，结束队列查询按当前确认窗口在Asia/Shanghai的结束日期。不按创建或报告日期过滤；派生状态按as_of判断。'
operation('/actions/{action_id}','get','getAction','读取行动窗口及执行修订','实际与行动','ActionView',['FR-006','FR-007'],'微行动',['micro_actions','action_windows','execution_revisions'])
listing('/learning-candidates','listLearningCandidates','读取待核对偏好与情境线索','回顾与学习','LearningView',['FR-008','FR-011'],'微行动',['learning_candidates','learning_evidence'])
listing('/preferences','listPreferences','读取本人稳定偏好规则','回顾与学习','PreferenceView',['FR-001','FR-008'],'微行动',['preference_rule_revisions'])
operation('/expected-meals/{week_start}','get','getExpectedMeals','读取已确认预期餐次分母','回顾与学习','ExpectedView',['FR-009'],'回顾查询',['expected_schedules','expected_slots'],
          params=[param('week_start','周一日期',date('自然周起点'),'path',True)])
listing('/recovery-episodes','listRecoveryEpisodes','读取确认恢复周期','回顾与学习','RecoveryView',['FR-009'],'回顾查询',['recovery_episodes','recovery_exclusions'])
operation('/reviews','get','getPeriodReview','按一致截点计算期间回顾','回顾与学习','ReviewSnapshot',['FR-009','FR-011'],'回顾查询',
          ['user_control','meal_revisions','execution_revisions','action_windows','expected_slots','week_presentations','recovery_episodes'],
          params=[param('from','含起点日期',date('开始日期'),required=True),param('to','含终点日期',date('结束日期'),required=True)],
          desc='同一授权和有效版本读快照计算；完成按执行日，反馈率按已结束窗口队列，覆盖按确认预期槽位。未知不填零。发送前复核当前授权。')
operation('/command-previews','post','previewCommand','预览业务变更及依赖影响','确认命令','PreviewView',['FR-001','FR-003','FR-005','FR-010','FR-011','FR-014','FR-017','FR-018','FR-019','FR-020'],
          '命令与任务',['task_sessions','user_control'],body='PreviewRequest',
          desc='只保存最长7天的临时核对态；可确认时服务器签发与用户、内容、影响、版本和期限绑定的操作键及令牌。编辑任何内容必须重新预览，不能用旧确认。')
operation('/commands','post','commitCommand','明确确认并原子提交预览','确认命令','Receipt',[f'FR-{i:03}' for i in range(1,21)],
          '命令与任务',['command_receipts','audit_events','user_control'],body='CommitRequest',
          params=[param('Idempotency-Key','必须等于原预览签发的操作标识',uid('服务端签发幂等键'),'header',True)],
          desc='不接收客户端重传的业务内容或自报user_id。先查授权和原回执，再按规则处理同键重提；首次提交复核全部绑定并同库原子写入。导出/删除仅受理任务，完成状态另查。')
operation('/command-receipts/{operation_key}','get','getCommandReceipt','按原键查提交结果','确认命令','Receipt',['FR-010','FR-013'],'命令与任务',['command_receipts','user_control'],
          desc='先核验身份和当前可返回范围。404只说明当前未查到可见回执，不证明从未提交；503必须保留结果待核对。旧任务到期不阻断尚在保留期的已提交回执，但不返回已删除内容。')
job_query=operation('/data-jobs/{job_id}','get','getDataJob','查询导出删除的真实进度','数据控制','DataJob',['FR-011'],'期限与数据控制',['data_control_jobs','user_control'],
          desc='普通路径要求当前本人映射；删除映射清理后可用预览先行签发的进度凭证加同主体有效身份令牌，仅查本次最小化状态。未受理返回404，不能视为完成；凭证过期410，不恢复业务事实。')
job_query['security']=[{'bearerAuth':[]},{'bearerAuth':[],'deletionStatusTicket':[]}]
download=operation('/data-jobs/{job_id}/download','get','downloadExport','认证后下载本人导出文件','数据控制',{'type':'string','format':'binary'},['FR-011'],'期限与数据控制',['data_control_jobs'],
                   desc='仅导出任务已完成、文件未过期、当前身份及授权仍允许时返回文件；不提供无认证公开URL，不返回内部文件键。')
download['responses']['200']['content']={'application/octet-stream':{'schema':{'type':'string','format':'binary','description':'UTF-8编码的本人JSON导出文件，中文说明与原技术标识'}}}
download['responses']['200']['headers']['Content-Disposition']={'description':'下载文件名，使用UTF-8编码中文名称','schema':{'type':'string'}}
health=operation('/health','get','getHealth','读取最小运行状态','运行状态',obj({'state':en('最小存活状态',['可用'])}),[],
                 '请求与身份',[],errors=['503'],desc='公开存活检查，不暴露用户数量、模型密钥、数据库地址或依赖版本。')
health['security']=[]

# 可独立复制的中文示例。均为虚构标识，不是真实用户资料。
ID='11111111-1111-4111-8111-111111111111';TASK='22222222-2222-4222-8222-222222222222'
MEAL={'slot':{'meal_date':'2026-11-18','meal_slot':'午餐'},'foods':[
    {'item_key':'面条','food_name':'番茄鸡蛋面','quantity':{'state':'已知','amount_micros':1000000,'unit':'份'},'entry_source':'手动自述'},
    {'item_key':'饮料','food_name':'无糖茶','quantity':{'state':'已知','amount_micros':300000000,'unit':'mL'},'entry_source':'手动自述'},
    {'item_key':'水果','food_name':'苹果','quantity':{'state':'未知','unit':'个'},'entry_source':'手动自述'}]}
sample={'task_id':TASK,'draft_revision':1,'intent':{'kind':'meal.confirm','data':{'content':MEAL}},'expected_versions':[]}
spec['paths']['/command-previews']['post']['requestBody']['content']['application/json']['examples']={
    '一次午餐多条食物':{'summary':'面条、饮料和水果同属一次个人用餐；未知量不补零','value':sample}}
commit={'preview_id':ID,'draft_revision':2,'preview_digest':'a'*64,'confirmation_token':'服务器签发的不透明示例令牌','decision':'确认'}
spec['paths']['/commands']['post']['requestBody']['content']['application/json']['example']=commit

class Dumper(yaml.SafeDumper):
    def ignore_aliases(self,data):return True
(OUT/'openapi.yaml').write_text(yaml.dump(spec,Dumper=Dumper,allow_unicode=True,sort_keys=False,width=110),encoding='utf-8')
(OUT/'openapi.json').write_text(json.dumps(spec,ensure_ascii=False,indent=2),encoding='utf-8')
(OUT/'operation-map.json').write_text(json.dumps({'阶段':'R2-P5候选','operations':OPS,'commands':COMMANDS},ensure_ascii=False,indent=2),encoding='utf-8')
(OUT/'examples.json').write_text(json.dumps({'说明':'中文虚构契约示例，不是真实业务记录','多食物记餐预览':sample,'确认提交':commit},ensure_ascii=False,indent=2),encoding='utf-8')
lines=['# 接口与用例映射','','版本：R2-P5候选；接口路径以`/api/v2`为前缀。业务变更走预览与统一提交，表列为主要责任而非客户端可直接写入范围。','',
       '| 操作标识 | 方法与路径 | 中文用途 | 需求 | 模块 | 主要表 |','|---|---|---|---|---|---|']
for o in OPS:lines.append('| `'+o['operationId']+'` | `'+o['method']+' '+o['path']+'` | '+o['label']+' | '+','.join(o['requirements'])+' | '+o['module']+' | '+','.join(o['tables'])+' |')
lines+=['','## 统一确认入口的命令类型','','每种类型的完整输入在OpenAPI的CommandIntent中定义，不能把任意表名或工具名当命令。','',
        '| 命令标识 | 用户确认的变化 | 输入结构 | 需求 | 责任模块 | 主要业务表 |','|---|---|---|---|---|---|']
for c in COMMANDS:lines.append('| `'+c['kind']+'` | '+c['label']+' | `'+c['data_schema']+'` | '+','.join(c['requirements'])+' | '+c['module']+' | '+','.join(c['tables'])+' |')
(OUT/'operation-map.md').write_text('\n'.join(lines)+'\n',encoding='utf-8')
print(f'已生成中文OpenAPI：{len(OPS)}个HTTP操作、{len(COMMANDS)}种确认命令、{len(S)}种结构。')
