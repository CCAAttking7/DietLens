"""规范、示例与追踪静态校验；不调用目标业务接口。"""
from pathlib import Path
import copy
import hashlib
import importlib.metadata
import json
import re
import sys
import yaml

ROOT=Path(__file__).resolve().parents[1];API=ROOT/'api'
sys.path.insert(0,str(ROOT/'tools/.dependencies'))
from openapi_spec_validator import validate_spec
from openapi_schema_validator import OAS30Validator
from referencing import Registry, Resource
from referencing.jsonschema import DRAFT4

spec=yaml.safe_load((API/'openapi.yaml').read_text(encoding='utf-8'))
assert spec==json.loads((API/'openapi.json').read_text(encoding='utf-8'))
validate_spec(spec)
schemas=spec['components']['schemas']
registry=Registry().with_resource('urn:dietlens:openapi',Resource(contents=spec,specification=DRAFT4))
def errors(name,value):
    return list(OAS30Validator({'$ref':'urn:dietlens:openapi#/components/schemas/'+name},
                              registry=registry,format_checker=OAS30Validator.FORMAT_CHECKER).iter_errors(value))

records=[]
def case(label,name,value,expected=True):
    found=errors(name,value);actual=not found
    assert actual==expected,(label,[e.message for e in found][:3])
    records.append({'场景':label,'结构':name,'期望':'接受' if expected else '拒绝','静态结果':'符合',
                    '说明':'只核对契约数据形状，不是服务实现测试'})

examples=json.loads((API/'examples.json').read_text(encoding='utf-8'))
preview=examples['多食物记餐预览'];commit=examples['确认提交']
case('一次午餐三条食物','PreviewRequest',preview)
case('明确确认只引用原预览','CommitRequest',commit)
case('未知数量保留单位','Quantity',{'state':'未知','unit':'个'})
case('已知零库存数量','InventoryQuantity',{'state':'已知','amount_micros':0,'unit':'g'})
case('未知数量不能带零','Quantity',{'state':'未知','amount_micros':0,'unit':'g'},False)
case('已知量必须有单位','Quantity',{'state':'已知','amount_micros':1000000},False)
case('数量负数拒绝','Quantity',{'state':'已知','amount_micros':-1,'unit':'g'},False)
case('数量不能为小数定点整数','Quantity',{'state':'已知','amount_micros':1.5,'unit':'g'},False)
case('数量超过安全整数范围','Quantity',{'state':'已知','amount_micros':9000000000000001,'unit':'g'},False)
case('未知库存仍须口径','InventoryQuantity',{'state':'未知'},False)
case('实际餐食不得空食物','MealContent',{'slot':{'meal_date':'2026-11-18','meal_slot':'午餐'},'foods':[]},False)
bad=copy.deepcopy(preview);bad['user_id']='其他人的身份'
case('客户端不能自报用户','PreviewRequest',bad,False)
bad=copy.deepcopy(commit);bad['intent']=preview['intent']
case('确认不能夹带修改后的业务内容','CommitRequest',bad,False)
bad=copy.deepcopy(commit);bad['decision']='取消'
case('取消不走提交入口','CommitRequest',bad,False)
bad=copy.deepcopy(commit);bad['draft_revision']=0
case('确认草稿版本不能为零','CommitRequest',bad,False)
bad=copy.deepcopy(preview);bad['intent']['kind']='任意数据库写入'
case('未注册命令拒绝','PreviewRequest',bad,False)
case('不确定自述不携执行日期','ExecutionWithdraw',{'state':'撤回为不确定'})
case('完成必须有执行日期','ExecutionReport',{'state':'完成'},False)
case('撤回自述不能伪造执行日期','ExecutionWithdraw',{'state':'撤回为不确定','execution_date':'2026-11-18'},False)
case('比例零分母用未知','Ratio',{'state':'未知','reason':'没有已结束行动','denominator':0})
case('已知比例不能零分母','Ratio',{'state':'已知','numerator':0,'denominator':0,'ratio':0},False)
case('采购状态至少明确改一项','PreparationStatusInput',{'list_id':commit['preview_id'],'line_id':commit['preview_id']},False)
case('采购和准备可独立改动','PreparationStatusInput',{'list_id':commit['preview_id'],'line_id':commit['preview_id'],'purchased_state':'已确认'})
case('采纳必须核对窗口','ActionDecisionInput',{'candidate_id':commit['preview_id'],'decision':'采纳'},False)
case('跳过不能夹带采纳窗口','ActionDecisionInput',{'candidate_id':commit['preview_id'],'decision':'跳过','window':{}},False)
case('校准不能只交题目而无回答','CalibrationAnswer',{'question_key':'待配置题目键','question_version':'题目版本'},False)
case('校准空选项不是回答','CalibrationAnswer',{'question_key':'待配置题目键','question_version':'题目版本','choice_codes':[]},False)
case('范围删除必须列对象','DeleteInput',{'scope':'指定对象','targets':[]},False)
case('全量删除不能夹带选择性目标','DeleteInput',{'scope':'本人全部数据','targets':[]},False)

slot={'meal_date':'2026-11-18','meal_slot':'午餐'}
food={'item_key':'面','food_name':'面条','quantity':{'state':'未知','unit':'份'},'quantity_basis':'每人','ingredients':[]}
plan={'mode':'指定','day_count':1,'start_date':'2026-11-18','context_id':commit['preview_id'],
      'selected_slots':[slot],'meals':[{'slot':slot,'people_count':2,'foods':[food]}]}
case('指定一餐可独立表达','PlanContent',plan)
bad=copy.deepcopy(plan);bad['selected_slots']=[slot,slot]
case('选定槽位不得重复','PlanContent',bad,False)
bad=copy.deepcopy(plan);bad['day_count']=2
case('仅一日或七日模式','PlanContent',bad,False)
stopped={'task_id':preview['task_id'],'draft_revision':2,'state':'已停止',
         'issues':[{'code':'SOURCE_UNAVAILABLE','message':'来源暂不可用','resolution':'改用手动核对'}],
         'budget':{'tools_used':1,'models_used':0,'readonly_retries_used':0,'step_deadline':'2026-11-17T08:00:15Z','paid_state':'无配置已停止付费'}}
case('依赖失败可无结果且明确停止','AnalysisResponse',stopped)
for kind,result in [('food',{'kind':'food','candidates':[]}),('comparison',{'kind':'comparison','rows':[]}),
                    ('menu',{'kind':'menu','eligible_observation_ids':[],'blocked':[],'explanation':'没有可靠候选'}),
                    ('action',{'kind':'action','candidates':[]}),
                    ('review_text',{'kind':'review_text','snapshot_revision':1,'text':'当前记录不足，保留基础汇总','source_mode':'规则模板'})]:
    case('分析判别类型可解析：'+kind,'AnalysisResult',result)
draft=copy.deepcopy(plan);draft['meals']=[]
case('空计划阶段可保留缺口草案','AnalysisResult',{'kind':'plan','content':draft,'completed_steps':1,'incomplete_slots':[slot]})
case('食品冲突不能装作确定数值','FoodField',{'field_key':'ingredients','state':'冲突','value_kind':'数值','amount_micros':0,'unit':'g','sources':[]},False)

# 路径、鉴权、编号和物理表映射核对。
mapping=json.loads((API/'operation-map.json').read_text(encoding='utf-8'))
db={t['name'] for t in json.loads((ROOT/'database/model.json').read_text(encoding='utf-8'))['tables']}
opids=[];coverage=set()
for path,methods in spec['paths'].items():
    for method,op in methods.items():
        assert method in ['get','post','patch']
        opids.append(op['operationId'])
        assert set(op['x-tables'])<=db,(path,op['x-tables'])
        if path=='/health':assert op['security']==[]
        elif path=='/data-jobs/{job_id}':
            assert op['security']==[{'bearerAuth':[]},{'bearerAuth':[],'deletionStatusTicket':[]}]
        else:assert op.get('security',spec['security'])==[{'bearerAuth':[]}]
        assert 'description' in op and 'summary' in op
        assert all(n in {p['name'] for p in op['parameters'] if p['in']=='path' and p['required']} for n in re.findall(r'{([^}]+)}',path))
        if path not in ['/commands','/command-previews']:coverage.update(op['x-requirements'])
        for status,res in op['responses'].items():
            if '$ref' not in res:assert res['headers']['Cache-Control']['schema']['enum']==['no-store']
for c in mapping['commands']:
    assert set(c['tables'])<=db
    coverage.update(c['requirements'])
assert len(opids)==len(set(opids))==45
assert len(mapping['commands'])==23
assert coverage=={f'FR-{i:03}' for i in range(1,21)}
assert set(spec['paths'])=={o['path'] for o in mapping['operations']}
assert set(opids)=={o['operationId'] for o in mapping['operations']}
assert spec['components']['securitySchemes']['deletionStatusTicket']['in']=='header'
assert spec['components']['securitySchemes']['deletionStatusTicket']['name']=='X-Deletion-Status-Token'
assert not errors('DeletionStatusAccess',{'job_id':commit['preview_id'],'token':'虚构的只读进度凭证',
                 'expires_at':'2026-11-24T08:00:00Z','scope':'仅查询本次删除进度'})
if (API/'swagger-editor-export.json').exists():
    assert json.loads((API/'swagger-editor-export.json').read_text(encoding='utf-8'))==spec,'编辑器导出与最新契约不一致，须重新载入导出'

def walk(node):
    if isinstance(node,dict):
        if '$ref' in node:
            r=node['$ref'];assert r.startswith('#/'),r
            cur=spec
            for piece in r[2:].split('/'):cur=cur[piece.replace('~1','/').replace('~0','~')]
        for k,v in node.items():
            if k in ['summary','description','title'] and isinstance(v,str):assert re.search(r'[\u3400-\u9fff]',v),(k,v)
            walk(v)
    elif isinstance(node,list):
        for v in node:walk(v)
walk(spec)

# 所有内嵌请求示例也经对应结构校验。
embedded=0
for methods in spec['paths'].values():
    for op in methods.values():
        for media in op.get('requestBody',{}).get('content',{}).values():
            values=([media['example']] if 'example' in media else [])+[v['value'] for v in media.get('examples',{}).values()]
            for value in values:
                target=media['schema']['$ref'].split('/')[-1]
                assert not errors(target,value)
                embedded+=1

report={'日期':'2026-11-17','阶段':'P5接口设计候选，待确认','OpenAPI版本':spec['openapi'],
        '规范校验':'通过','规范校验器':'openapi-spec-validator '+importlib.metadata.version('openapi-spec-validator'),
        '结构校验器':'openapi-schema-validator '+importlib.metadata.version('openapi-schema-validator'),
        'HTTP操作数':len(opids),'确认命令数':len(mapping['commands']),'结构数':len(schemas),
        '契约正反例数':len(records),'内嵌请求示例数':embedded,'功能需求覆盖数':len(coverage),
        '检查':['全部引用可解析且为本地引用','操作标识唯一','路径参数齐备','本人认证边界及no-store声明',
                '操作和命令的物理表映射存在','不靠统一提交的兜底编号补足20FR覆盖','中文标题摘要说明','YAML与JSON一致'],
        '正反例记录':records,
        '文件摘要':{p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in API.iterdir() if p.is_file() and p.suffix in ['.yaml','.json'] and p.name!='validation.json'},
        '未执行':'没有导入或启动产品API；未发业务请求、未创建数据库；事务、授权及网络恢复仍须后续服务验收'}
(API/'validation.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
lines=['# 接口数据形状正反例','','这些是按OpenAPI结构验证的虚构数据，不是服务实现验收。跨字段计算、真实授权、版本竞争与恢复另按正文验证。','',
       '| 场景 | 结构 | 期望 | 静态结果 |','|---|---|---|---|']
for row in records:lines.append('| '+row['场景']+' | `'+row['结构']+'` | '+row['期望']+' | '+row['静态结果']+' |')
(API/'contract-review.md').write_text('\n'.join(lines)+'\n',encoding='utf-8')
print(f'接口规范与静态契约核对通过：{len(opids)}个操作、23种命令、{len(records)}个正反例、20项功能需求；未调用业务API。')
