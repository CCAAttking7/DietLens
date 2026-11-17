"""生成最终报告的精简中文模型，保留完整设计模型作为附件。"""
from pathlib import Path
import base64, hashlib, json, re, urllib.request, zlib
import xml.etree.ElementTree as E

ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'final/figures';OUT.mkdir(parents=True,exist_ok=True)
BASE='''@startuml
skinparam defaultFontName Noto Sans CJK SC
skinparam defaultFontSize 22
skinparam backgroundColor #FCFBF7
skinparam shadowing false
skinparam sequenceArrowFontSize 20
skinparam sequenceParticipantFontSize 22
skinparam maxMessageSize 270
hide footbox
'''
SOURCES={
'F01-domain':'''title 核心领域：未来准备与个人实际分开
left to right direction
class "计划版本" as P {确认范围与模式}
class "计划餐次" as M {日期、餐次、人数}
class "计划食物" as F {准备份量与基准}
class "食材需求" as I {标准食材、量或未知}
class "采购清单" as L {来源版本与独立状态}
class "库存核对" as S {人工数量、单位、修订}
class "个人用餐版本" as A {实际日期、餐次}
class "实际食物" as B {个人份量与出处}
P "1" *-- "1..*" M
M "1" *-- "1..*" F
F "1" *-- "0..*" I
P "1" <-- "0..*" L : 引用确认版本
L ..> I : 汇总可追溯需求
L ..> S : 读取，不扣减
A "1" *-- "1..*" B
B "0..*" --> "0..1" F : 可选预填出处
note bottom of A
同一午餐可有多次用餐；
餐次覆盖按槽位去重。
end note
''',
'F02-action':'''title 微行动：生成、核对、采纳与独立反馈
actor "用户" as U
participant "工作台" as W
participant "编排与规则" as C
participant "外部适配器" as T
database "权威库" as D
U -> W : 说明当前情境
W -> C : 核对档案、用途及约束
C -> T : 有界理解与证据查询
T --> C : 候选与来源；无写权限
C --> W : 具体行动、依据、建议窗口
U -> W : 核对行为及起止，确认采纳
group 短事务：复核当前许可和版本
W -> C : 提交绑定的确认预览
C -> D : 行动、决策、窗口与回执同提交
end
C --> W : 已采纳，仍待反馈
... 实际执行后 ...
U -> W : 确认执行日期及结果
W -> C : 原行动追加反馈修订
C -> D : 切换有效反馈并更新数据修订
C --> W : 采纳与完成分别展示
''',
'F03-plan':'''title 计划到准备，再到个人实际
actor "用户" as U
participant "工作台" as W
participant "计划与准备" as P
participant "实际餐食" as M
database "权威库" as D
U -> W : 选择完整或指定餐次及人数
W -> P : 预览餐次缺口与替换范围
U -> W : 核对并确认计划
W -> P : 提交绑定版本的确认命令
P -> D : 新版本、当前槽位、清单失效同提交
W -> P : 按食材口径读取需求和库存
P --> W : 已知小计与未知差额
U -> W : 单独确认清单或库存调整
W -> P : 提交对应的独立确认
P -> D : 保存对应准备事实
... 实际用餐之后 ...
W -> M : 从计划只读预填名称与出处
M --> W : 个人多食物草案，份量待核对
U -> W : 修改个人份量，确认这一餐
W -> M : 提交个人餐食确认
M -> D : 一次用餐、多食物及回执同提交
note over P,M
已购不扣库；准备量不等摄入；
记餐不自动完成行动。
end note
''',
'F04-recovery':'''title 确认提交与断网恢复
actor "用户" as U
participant "工作台" as W
participant "可信命令" as C
database "权威库" as D
U -> W : 确认具体内容和影响
W -> C : 原预览、版本与操作键
C -> C : 当前身份、授权及归属校验
group 短事务：先锁处理控制
C -> D : 原键查重，核对预期版本
C -> D : 业务、事件、任务及回执同提交
end
C ->x W : 已提交，但响应丢失
W -> C : 按原键查询结果
C -> C : 再核对当前可返回范围
C -> D : 读取原提交回执
D --> C : 原提交标识
C --> W : 显示原结果，禁止复制保存
note over W,D
版本不一致：返回差异并重新核对。
查询不可用：保持待核对，不换新键重做。
end note
''',
'F05-flow':'''title 用户流程：按当前任务进入，明确确认事实
start
:选择食品、计划、记录、微行动或回顾;
:复用已确认档案，核对当前缺口;
if (需要外部图片解析？) then (是)
:逐图确认用途和接收方;
else (否)
:手输或读取允许使用的资料;
endif
:形成候选与结构化预览;
if (有关键未知或冲突？) then (是)
:补充、改选或手动继续;
:重新核对受影响内容;
else (否)
endif
:显示变更范围、来源与独立影响;
if (用户确认？) then (确认)
:提交原预览，显示回执或核对结果;
else (取消)
:退出草案，保留原已确认事实;
endif
stop
''',
'F06-state':'''title 行动决策与执行的两层状态
state "提案" as P
state "已采纳" as A
state "已跳过或被替代" as S
state "待反馈" as W
state "未知" as N
state "有效自述：完成／部分／未完成" as R
[*] --> P
P --> A : 确认行为与窗口
P --> S : 用户决定不采纳
A --> W : 不增加完成数
W --> N : 窗口结束且无有效自述
W --> R : 确认实际日期与结果
N --> R : 同一行动迟到补报
R --> R : 原行动追加修订
R --> N : 撤回且窗口已结束
R --> W : 撤回且窗口未结束
''',
'F07-context':'''title 系统上下文与外部信任边界
actor "成年用户" as U
rectangle "DietLens饮食工作台\n选择、准备、实际自述与微行动" as D
rectangle "外部模型\n只返回理解、候选与表达" as L
rectangle "食品参考来源\n资料有来源、规格与缺口" as F
rectangle "托管身份服务\n验证访问令牌" as I
U --> D : 描述、核对、明确确认
D --> L : 最小必要输入
D --> F : 受控只读查询
D --> I : 核验身份
note bottom of D
当前用途许可及确定性规则控制写入。
外部来源没有业务库写权限。
end note
''',
'F08-logical':'''title 逻辑架构：受控编排的模块化单体
rectangle "网页工作台\n对话入口＋结构化核对" as W
package "一个后端应用" {
rectangle "请求与身份\n当前主体和资源归属" as B
rectangle "命令与任务\n确认绑定、版本、回执和恢复" as C
rectangle "领域模块\n档案授权／食品证据／计划准备\n实际餐食／微行动／回顾" as M
rectangle "工具执行\n白名单、超时、预算" as T
rectangle "期限与数据控制\n导出、清理及派生失效" as R
}
database "唯一权威业务库" as D
W --> B : 认证请求
B --> C : 确认命令
C --> M : 领域用例
C --> T : 事务外外调
M --> D : 统一事务范围
C --> D : 原子提交和回执
R --> D : 有断点清理
B --> M : 授权查询
'''}
TRANS=bytes.maketrans(b'ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789+/',b'0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz-_')
records=[]
for name,body in SOURCES.items():
    body=re.sub(r'(class [^\n]+) \{([^\n{}]+)\}',r'\1 {\n\2\n}',body)
    body=re.sub(r'"[^"]*"',lambda m:m.group().replace('\n',r'\n'),body)
    src=OUT/(name+'.puml');src.write_text(BASE+body+'@enduml\n',encoding='utf-8')
    raw=src.read_text(encoding='utf-8').encode();z=zlib.compressobj(9,zlib.DEFLATED,-15)
    token=base64.b64encode(z.compress(raw)+z.flush()).translate(TRANS).rstrip(b'=').decode()
    for fmt in ['svg','png']:
        data=urllib.request.urlopen('http://localhost:8082/'+fmt+'/'+token,timeout=40).read()
        if fmt=='svg':
            x=E.fromstring(data);assert 'Syntax Error' not in ''.join(x.itertext())
        target=OUT/(name+'.'+fmt);target.write_bytes(data)
        records.append({'源':str(src.relative_to(ROOT)),'产物':str(target.relative_to(ROOT)),
                        '源摘要':hashlib.sha256(src.read_bytes()).hexdigest(),'摘要':hashlib.sha256(data).hexdigest()})
(OUT/'render-record.json').write_text(json.dumps({'说明':'报告精简模型；完整源模型保留作附件','图数':len(SOURCES),'记录':records},ensure_ascii=False,indent=2),encoding='utf-8')
print('已生成八张报告专用中文精简图。')
