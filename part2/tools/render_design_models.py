"""重建可编辑的中文设计图及其SVG和PNG导出。"""
from pathlib import Path
import json
import subprocess

BASE = Path(__file__).resolve().parents[1] / 'diagrams'
OUT = BASE / 'rendered'
OUT.mkdir(parents=True, exist_ok=True)
ZH_LABELS = json.loads((BASE / 'labels-zh.json').read_text(encoding='utf-8'))

def q(value):
    for original, translated in sorted(ZH_LABELS.items(), key=lambda item: len(item[0]), reverse=True):
        value = value.replace(original, translated)
    return json.dumps(value, ensure_ascii=False)

def graph(name, title, nodes, edges, direction='TB', clusters=None):
    lines = ['digraph G {',
        f'graph [rankdir={direction}, bgcolor="#fcfbf7", pad="0.3", nodesep="0.35", ranksep="0.55", fontname="Microsoft YaHei", fontsize=18, labelloc=t, label={q(title)}];',
        'node [shape=box, style="rounded,filled", fillcolor="#edf3ed", color="#486958", fontname="Microsoft YaHei", fontsize=12, margin="0.18,0.12"];',
        'edge [color="#627468", fontname="Microsoft YaHei", fontsize=10, arrowsize=0.7];']
    for key, label in nodes.items():
        lines.append(f'{key} [label={q(label)}];')
    for index, (label, ids) in enumerate(clusters or []):
        lines.append(f'subgraph cluster_{index} {{ label={q(label)}; color="#b3b9b1"; ' + ';'.join(ids) + '; }')
    for source, target, label in edges:
        lines.append(f'{source} -> {target} [label={q(label)}];')
    lines.append('}')
    path = BASE / (name + '.dot')
    path.write_text('\n'.join(lines), encoding='utf-8')
    for fmt in ['svg', 'png']:
        subprocess.run(['dot', f'-T{fmt}', '-Gdpi=125', str(path), '-o', str(OUT / (name + '.' + fmt))], check=True)

graph('M01A-current', 'M01A · 当前逻辑架构 / main 5ecd03f', {
    'u':'成年用户', 'w':'React + TypeScript\n对话与业务页面', 'a':'FastAPI\n认证 / 归属 / 输入校验',
    'h':'Agent / Harness\n完整微行动状态控制\n计划、快速记餐关联任务',
    'b':'独立领域服务\n档案 / 计划 / 库存\n餐食 / 食品 / 回顾',
    'd':'Repository\nSQLite 本地演示', 'm':'可选模型\n结构化理解', 'f':'食品参考源\n外部查询 / 本地编码索引'
}, [('u','w','输入 / 核对 / 确认'),('w','a','HTTP /api'),('a','h','微行动 / 关联任务'),('a','b','业务端点'),('h','d','状态 / 决策 / 反馈'),('b','d','业务对象'),('h','m','有界调用'),('b','f','只读资料检索')])

graph('M01B-target', 'M01B · 目标逻辑架构 / 单体内职责', {
    'w':'Web 工作台\n候选 / 差异 / 确认 / 恢复', 'a':'API 身份边界\n请求主体 / 对象归属',
    'c':'命令协调器 + Harness\n确认 / 授权 / 版本 / 幂等\n事务 / 调用预算 / 恢复',
    'p':'档案与授权', 'f':'食品与菜单评估\n证据 / 单位 / 硬约束', 'l':'计划 / 清单 / 库存',
    'r':'实际餐食记录', 'x':'微行动与反馈', 'v':'回顾查询\n期间 / 分母 / 有效版本',
    'd':'Repository / 唯一权威库\n业务 + 任务 + 事件 + 回执', 'm':'模型适配器\n结构化候选 / 表达', 's':'食品来源适配器'
}, [('w','a','请求'),('a','c','确认写命令'),('a','v','授权查询'),('c','p',''),('c','f',''),('c','l',''),('c','r',''),('c','x',''),('p','d',''),('f','d',''),('l','d',''),('r','d',''),('x','d',''),('v','d','只读聚合'),('c','m','事务外调用'),('f','s','检索')])

graph('M02-deployment', 'M02 · 当前本地与目标托管部署（两种配置）', {
    'b':'本地浏览器', 'v':'Vite :5173', 'a':'FastAPI :8000', 'd':'SQLite 文件 / WAL',
    'cb':'用户浏览器\n访问令牌', 'web':'静态站点 / HTTPS 入口', 'api':'反向代理 + API 实例\n服务端密钥 / 命令事务',
    'auth':'Supabase Auth', 'pg':'唯一 Postgres 数据库\n备份到期 / 期限清理',
    'ext':'外部模型与食品参考源\n只出站 / 授权 / 超时'
}, [('b','v','页面'),('b','a','HTTP /api'),('a','d','本机访问'),('cb','web','HTTPS'),('web','api','/api 转发'),('cb','auth','登录'),('api','auth','令牌身份核验'),('api','pg','数据库加密连接'),('a','ext','可选出站'),('api','ext','HTTPS / 按需')], clusters=[('当前 · 本机演示', ['b','v','a','d']),('目标 · 托管运行', ['cb','web','api','auth','pg'])])

graph('M03-domain', 'M03 · 目标领域结构（属性详见正文）', {
    'p':'ProfileVersion\nuser_id / version / constraints', 'c':'Consent\nuser_id / purpose / revision',
    't':'Task\nstate / version / resume_point', 's':'ContextSnapshot\nprofile_version / evidence_revision',
    'f':'FoodObservation\nsource / fields / unknowns', 'pl':'Plan\nplan_id / version / status / persons',
    'pm':'PlanMeal\ndate / slot / selected', 'il':'IngredientLine\nquantity? / unit / basis',
    'sh':'ShoppingList\nplan_version / inventory_revision', 'i':'InventoryItem\nquantity? / unit / confirmed_at',
    'r':'MealRecord\nversion / self_report / quantity?\noptional plan reference',
    'a':'Action\ncue / behavior / effort / rationale', 'de':'Decision\nadopt / skip / replace',
    'ex':'ExecutionRevision\nexecution_date / reported_at / status',
    'o':'OperationReceipt\nuser_id + key / hash / result', 'e':'Event\nactor / entity / version / time'
}, [('p','s','1 version / 0..* snapshots'),('c','s','revision used'),('t','s','1 / 0..1 current snapshot'),('s','f','0..* evidence refs'),('t','pl','0..1 plan link'),('pl','pm','1 / 1..*'),('pm','il','1 / 1..*'),('pl','sh','1 / 0..* versioned lists'),('i','sh','read version / compute gap'),('pm','r','1 / 0..* optional links'),('s','a','1 / 0..* proposals'),('a','de','1 / 0..* decision history'),('a','ex','1 / 0..* execution revisions'),('r','a','0..1 optional meal ref'),('t','o','1 / 0..* commands'),('o','e','1 / 1..* committed events')], direction='TB')

graph('M04-action', 'M04 · 目标微行动协作 / UC-09、10、12', {
    'n1':'1 用户 → Web\n说明当前餐次和可选项', 'n2':'2 API / Harness → 档案与证据\n身份、授权、版本；可选模型提取',
    'n3':'3 食品评估 → Web\n缺配料/预算：只核对关键缺失\n明确冲突：阻止受影响候选',
    'n4':'4 确定性规则 → Web\n校验餐食及新增食物；生成一个主行动\ncue / behavior / effort / rationale',
    'n5':'5 用户 → 命令协调器\n采纳 / 跳过 / 修改 / 换一个',
    'n6':'6 协调器 → Repository\n当前授权和版本复核\n事务保存决策 + 任务 + 事件 + 回执',
    'n7':'7 用户 → 反馈服务\n完成 / 部分 / 未完成；可保持未知',
    'n8':'8 反馈服务 → Repository / 回顾\n同 action_id 追加执行修订\n更新执行所属周统计'
}, [('n1','n2',''),('n2','n3',''),('n3','n4','所需事实已核对'),('n4','n5',''),('n5','n4','修改/更换：重查，最多两次'),('n5','n6','采纳/跳过'),('n6','n7','仅采纳进入待反馈'),('n7','n8','明确执行自述')])

graph('M05-plan-record', 'M05 · 目标计划、准备与实际记录 / UC-05、06、07、14', {
    'n1':'用户 / 计划服务\n日期、人数、餐次、配料、预算\n全餐或指定餐次；草案预览',
    'n2':'用户确认 → 原子命令\n保存计划版本 P/v1；完成计划任务',
    'n3':'清单服务\n按人数和数量基准汇总食材\n核对库存；未知差额待确认',
    'n4':'用户确认清单\n保存 L 引用 P/v1\n已购、已准备分别记录',
    'n5':'次日用户 → 记录服务\n从计划预填名称和引用\n个人实际数量待核对',
    'n6':'用户修改并确认 → 原子命令\n保存实际餐食 R / 自述证据\n未知份量保持 null',
    'n7':'回顾服务\n读取有效版本 / 显式关联\n计划、实际、行动分别汇总',
    'n8':'替换计划 P/v2\n旧清单 stale；差异预览后重建\n历史 R 和待反馈行动保持独立',
    'cancel':'取消预填\n不创建实际记录'
}, [('n1','n2',''),('n2','n3','独立准备入口'),('n3','n4',''),('n2','n5','到用餐时 / 可独立记餐'),('n5','n6',''),('n5','cancel','取消'),('n6','n7',''),('n4','n8','计划变更'),('n8','n3','重建预览')])

graph('M06-recovery', 'M06 · 目标原子命令与中断恢复 / UC-11', {
    'n1':'API：验证身份、归属、最新授权\n同用户域查 operation_key / request_hash',
    'n2':'已有回执：同摘要返回原结果\n不同摘要返回 operation_conflict',
    'n3':'新命令：事务开始\n唯一键 + 草稿确认 + 预期版本检查',
    'n4':'写业务对象 + 任务进度\n写事件 + 原结果回执',
    'n5':'COMMIT\n四类写入一并生效',
    'n6':'向 Web 返回对象及版本',
    'n7':'响应丢失：保留原键和请求\n用户恢复 / 查询回执',
    'fail':'任何事务内异常 → ROLLBACK\n冲突提示重载；不盲目重试写入'
}, [('n1','n2','已存在'),('n1','n3','不存在'),('n3','n4','检查通过'),('n3','fail','拒绝/错误'),('n4','fail','任一步失败'),('n4','n5','全部成功'),('n5','n6','响应正常'),('n5','n7','提交后断网'),('n7','n1','原键恢复；重新验权')])

graph('M07A-task', 'M07A · 目标任务状态 / 进度不代表业务执行完成', {
    'cr':'created', 'co':'collecting\n情境 / 草稿 / 检索', 'aw':'awaiting_confirmation',
    'af':'awaiting_feedback', 'done':'completed', 'cancel':'cancelled', 'stop':'stopped\nreason + resume_point'
}, [('cr','co','开始'),('co','aw','写入预览可确认'),('co','done','只读任务完成'),('aw','done','计划/记餐确认；行动跳过'),('aw','af','微行动采纳'),('aw','co','编辑/重新核对'),('af','done','反馈或窗口到期置未知'),('co','cancel','用户取消'),('aw','cancel','取消草稿'),('co','stop','依赖/预算/冲突'),('aw','stop','提交校验失败'),('stop','co','用户恢复 + 复核'),('done','co','独立修正命令关联原对象')])

graph('M07B-execution', 'M07B · 目标行动决策与执行（两层语义）', {
    'pr':'proposed', 'ad':'adopted', 'sk':'skipped\n无执行状态', 'su':'superseded\n重新校验新提案',
    'pe':'pending_feedback', 'un':'unknown', 're':'有效执行修订\ncomplete / partial / not_done',
    'hi':'同 action_id 的修订历史\nexecution_date / reported_at / revision'
}, [('pr','ad','采纳'),('pr','sk','跳过'),('pr','su','修改/换一个'),('ad','pe','决策已存，尚无执行自述'),('pe','un','窗口到期无反馈'),('pe','re','用户反馈'),('un','re','迟到反馈'),('re','re','明确修正：追加版本'),('re','un','改为未知：追加版本'),('re','hi','保存历史'),('un','hi','保存历史')], clusters=[('决策', ['pr','ad','sk','su']),('执行：仅采纳后成立', ['pe','un','re','hi'])])

graph('M08-user-flow', 'M08 · 目标用户流程 / 各入口可独立使用', {
    'entry':'选择当前需要\n查食品 / 做计划 / 记餐 / 微行动 / 回顾',
    'food':'输入菜单或标签\n核对来源和关键配料',
    'check':'配料未知或冲突\n补充 / 换选项；阻止受影响推荐',
    'plan':'日期、人数、指定餐次\n计划预览 → 确认计划',
    'shop':'按人数汇总多食材\n库存核对 → 确认清单',
    'record':'手输或计划预填\n个人实际情况 → 记录预览',
    'saved':'确认保存实际餐食\n取消则不创建记录',
    'action':'情境核对 → 单步行动\n采纳 / 跳过 / 修改',
    'feedback':'仅采纳后待反馈\n完成 / 部分 / 未完成 / 未知',
    'review':'授权后查看期间回顾\n计划 / 实际 / 行动分别汇总',
    'recovery':'任一提交回执不明\n保留草稿 → 原键核对结果'
}, [('entry','food','查资料'),('entry','plan','安排未来'),('entry','record','记录已吃'),('entry','action','试一个小改变'),('entry','review','看历史'),('food','check','受影响事实不足'),('check','food','用户补充'),('food','plan','已核对餐食可引用'),('plan','shop','准备入口'),('plan','record','到用餐时可预填'),('record','saved','用户确认'),('action','feedback','采纳'),('saved','review','按有效记录汇总'),('feedback','review','按有效反馈汇总'),('saved','recovery','未收到回执'),('recovery','saved','查明已提交：显示原记录')])

print('已生成十张中文设计图的SVG与PNG：', OUT)
