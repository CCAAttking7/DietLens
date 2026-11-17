"""DietLens 网页端新界面设计稿（晨光餐盘）：生成中文HTML并用Edge渲染为PNG。

用法：python part2/tools/render_ui_v2.py
输出：part2/ui_v2/html/*.html、part2/ui_v2/png/*.png、part2/ui_v2/screens.json
"""
from pathlib import Path
import json, subprocess

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'ui_v2'
HTML = OUT / 'html'
PNG = OUT / 'png'
for d in (HTML, PNG):
    d.mkdir(parents=True, exist_ok=True)
EDGE = r'C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe'

IC = {
 'home': '<path d="M3 11l9-8 9 8v9a1 1 0 0 1-1 1h-5v-6H9v6H4a1 1 0 0 1-1-1z"/>',
 'cal': '<rect x="3" y="5" width="18" height="16" rx="3"/><path d="M3 10h18M8 3v4M16 3v4"/>',
 'box': '<path d="M4 7l8-4 8 4v10l-8 4-8-4z"/><path d="M4 7l8 4 8-4M12 11v10"/>',
 'plus': '<path d="M12 5v14M5 12h14"/>',
 'food': '<circle cx="11" cy="11" r="7"/><path d="M16.5 16.5L21 21"/>',
 'chart': '<path d="M5 20V11M12 20V4M19 20v-7"/>',
 'mic': '<rect x="9" y="3" width="6" height="12" rx="3"/><path d="M5 11a7 7 0 0 0 14 0M12 18v3"/>',
 'send': '<path d="M4 12l16-8-6 16-3-7z"/>',
 'user': '<circle cx="12" cy="8" r="4"/><path d="M4 21c1-5 15-5 16 0"/>',
 'cam': '<path d="M4 8h3l2-3h6l2 3h3a2 2 0 0 1 2 2v8a2 2 0 0 1-2 2H4a2 2 0 0 1-2-2v-8a2 2 0 0 1 2-2z"/><circle cx="12" cy="13" r="3.5"/>',
}
def ic(n): return f'<svg viewBox="0 0 24 24">{IC[n]}</svg>'
def mk(n, style='right:-8px;top:-10px'): return f'<i class="mk" style="{style}">{n}</i>'

def rail(on):
    def n(key, label, icon): return f'<div class="nav {"on" if key==on else ""}">{ic(icon)}{label}</div>'
    return ('<aside class="rail"><div class="brand"><div class="logo emo">🥗</div>DietLens</div><div style="margin-top:20px"></div>'
            + n('today', '今日工作台', 'home') + n('food', '食品核对', 'food') + n('plan', '计划与准备', 'cal')
            + n('inv', '食材库存', 'box') + n('review', '阶段回顾', 'chart') + n('me', '我的数据', 'user')
            + f'<div class="nav add">{ic("plus")}记一餐</div>'
            + '<div style="margin-top:auto;padding:12px;border-radius:14px;background:var(--bg);font-size:12.5px;color:var(--ink2);line-height:1.6">'
              '<b style="color:var(--gd)">当前底线</b><br>花生过敏 · 每餐预算 ¥20</div></aside>')

def desk(inner, on, h=660):
    return ('<!doctype html><html lang="zh-CN"><head><meta charset="utf-8"><link rel="stylesheet" href="../ui.css"></head>'
            '<body><div class="stage" style="width:1440px;height:' + str(h + 80) + 'px">'
            '<div class="desk" style="height:' + str(h) + 'px">' + rail(on) + '<main class="dmain">' + inner + '</main></div></div></body></html>')

def ring(pct, label, val, sub, color='var(--g)'):
    return f'<div class="ringw"><div class="ring" style="width:88px;height:88px;background:conic-gradient({color} 0 {pct}%,#E4EDE5 0)"><b>{val}</b></div><div class="small">{label}<br><span style="font-weight:500">{sub}</span></div></div>'

def stepper(txt):
    return f'<div class="row gap8"><div class="step" style="width:36px;height:36px;font-size:20px;background:var(--gr);color:var(--ink2)">−</div><b style="min-width:58px;text-align:center;font-size:15px">{txt}</b><div class="step" style="width:36px;height:36px;font-size:20px">+</div></div>'

def tl(emo, lab, txt, last=False):
    line = '' if last else '<div style="position:absolute;left:19px;top:40px;bottom:-12px;width:2px;background:#CFE3D4"></div>'
    return f'''<div class="rel row gap12" style="align-items:flex-start;padding-bottom:14px">{line}<div class="step emo" style="width:40px;height:40px;font-size:20px;border-radius:50%;z-index:1">{emo}</div><div><div class="lab">{lab}</div><b style="font-size:15.5px;line-height:1.4">{txt}</b></div></div>'''

def choice(emo, name, desc, sel=False):
    cls = 'choice sel' if sel else 'choice'
    dot = '<div style="flex:none;width:26px;height:26px;border-radius:50%;background:var(--g);color:#fff;display:grid;place-items:center;font-weight:800">✓</div>' if sel else '<div style="flex:none;width:26px;height:26px;border-radius:50%;border:2px solid #BFCDC3"></div>'
    return f'<div class="{cls}"><div class="emo" style="font-size:28px;width:36px;text-align:center">{emo}</div><div style="flex:1"><b style="font-size:16px">{name}</b><div class="small">{desc}</div></div>{dot}</div>'

def setrow(emo, name, desc, on):
    return f'<div class="st" style="align-items:center"><div class="emo" style="font-size:24px;width:34px;text-align:center">{emo}</div><div style="flex:1"><b>{name}</b><div class="small">{desc}</div></div><div class="sw {"on" if on else ""}"></div></div>'

S = {}
SIZES = {}

# ---------- W01 今日工作台 ----------
SIZES['W01-today'] = (1440, 740)
S['W01-today'] = (desk(f'''
<div class="row sp"><div><div class="sub">11月18日 · 周三</div><h1>先处理这一餐</h1></div><div class="row gap12"><span class="chip g" style="height:34px;font-size:13.5px">档案：少糖目标 · 花生过敏已确认</span><div class="avatar">我</div></div></div>
<div class="grid2" style="margin-top:18px">
 <div>
  <div class="hero rel"><div class="plate emo">🍜</div><div class="lab" style="color:rgba(255,255,255,.8);position:relative;z-index:2">今天午餐 · 2 人准备</div><h2 style="font-size:28px;margin-top:4px;position:relative;z-index:2">番茄鸡蛋面</h2>
   <div class="row gap8" style="margin-top:10px;position:relative;z-index:2"><span class="chip w">计划已确认</span><span class="chip w">需购 2 项 · 1 项未知</span></div>
   <div class="ask rel"><span class="t">午餐吃了牛肉面，帮我想想今晚怎么安排</span><span class="round" style="background:#EEF2EE;color:var(--ink2)">{ic("cam")}</span><span class="round" style="background:#EEF2EE;color:var(--ink2)">{ic("mic")}</span><span class="round" style="background:var(--g);color:#fff">{ic("send")}</span>{mk(1,'right:-6px;top:-12px')}</div>
   <div class="small" style="color:rgba(255,255,255,.92);margin-top:10px;position:relative;z-index:2">✓ 已拆分为两项独立草稿：1) 待核对午餐记录（份量待确认）　2) 晚餐微行动候选（尚未采纳）</div></div>
  <div class="card rel" style="margin-top:16px;border-left:6px solid var(--co)"><div class="row sp"><div><span class="lab" style="color:#A82F10">今日微行动 · 努力量：低</span><h2 style="margin-top:4px">拿饮料时，换成白水</h2><div class="small" style="margin-top:2px">保留主餐，只改一个小动作 · 11:00–14:00 可尝试 · 依据：减少含糖饮品</div></div>
   <div class="row gap8"><div class="btn c1">采纳这个行动</div><div class="btn s1">换一个</div><div class="btn g1">跳过</div></div></div>{mk(2)}</div>
 </div>
 <div>
  <div class="card rel"><b style="font-size:17px">本周小进展</b><div class="row sp" style="margin-top:12px">{ring(100,'完成','3 个','按执行日期')}{ring(80,'反馈覆盖','80%','4 / 5 个已结束')}</div>{mk(3)}</div>
  <div class="card"><b style="font-size:17px">还有 3 件小事</b>
   <div class="st"><div class="si a">!</div><div><b>核对酱料配料</b><div class="small">补充后恢复受影响推荐</div></div></div>
   <div class="st"><div class="si n">?</div><div><b>核对面条库存</b><div class="small">完成后得出需购差额</div></div></div>
   <div class="st"><div class="si g">✓</div><div><b>确认午餐实际份量</b><div class="small">保存后计入个人记录</div></div></div></div>
 </div>
</div>''', 'today', 660),
 '网页端·今日工作台',
 '首页聚焦“眼前这一餐”，将自然语言复合意图拆分为独立可确认的草稿，并把主微行动与本周待办同屏呈现。',
 [('1', '一句话复合入口', '支持文字、语音和可选图片；系统把复合意图拆成“餐食记录草稿”和“晚餐微行动候选”，两项独立确认、互不捆绑。'),
  ('2', '主微行动卡片', '只展示一个主候选，“采纳”为唯一实心主按钮，“换一个”“跳过”弱化并排，避免视觉干扰。'),
  ('3', '本周进展与待办', '右侧固定展示本周完成数、反馈覆盖率与待核对小事，点击即可跳转对应工作台。')])

# ---------- W02 食品核对 ----------
SIZES['W02-food'] = (1440, 740)
S['W02-food'] = (desk(f'''
<div class="row sp"><div><div class="sub">食品核对 · 番茄鸡蛋面（非标准菜品）</div><h1>酱料配料还需确认</h1></div>
 <div class="seg rel"><span class="on">识别与核对</span><span>比较食品</span><span>选择菜单</span>{mk(1,'right:-6px;top:-12px')}</div></div>
<div class="grid2" style="margin-top:18px;grid-template-columns:1.45fr 1fr">
 <div class="card rel">
  <div class="row sp" style="margin-bottom:8px"><b style="font-size:17px">逐字段证据核对</b><span class="small">来源 · 用户提供菜单原文</span></div>
  <div class="st"><div class="si g">✓</div><div style="flex:1"><b>食品名称与标价（¥18）</b><div class="small">已知 · 本次菜单文字输入，满足每餐预算 ¥20</div></div><span class="chip g">已知</span></div>
  <div class="st"><div class="si a">!</div><div style="flex:1"><b>酱料配料与调味成分</b><div class="small">待核对 · 菜单未列出具体配料，系统不按常见做法猜补</div></div><span class="chip a">待核对</span></div>
  <div class="st"><div class="si a">!</div><div style="flex:1"><b>花生交叉接触说明</b><div class="small">待核对 · 与已确认“花生过敏”约束相关</div></div><span class="chip a">待核对</span></div>
  <div class="st"><div class="si n">?</div><div style="flex:1"><b>能量与营养素</b><div class="small">未知 · 缺少可靠份量与成分依据，不按 0 计算</div></div><span class="chip n">未知</span></div>
  {mk(2)}
 </div>
 <div>
  <div class="card rel" style="background:var(--ams);box-shadow:none"><div class="row gap12" style="align-items:flex-start"><div class="emo" style="font-size:26px">⏸️</div><div><b style="color:#5E3A00;font-size:16px">当前影响：主动推荐已暂停</b><div class="p" style="color:#5E3A00;margin-top:4px">由于你的档案包含“花生过敏”，在酱料配料未核实前，此菜品不能进入主动推荐；但你仍可继续浏览或如实记录实际用餐。</div></div></div>{mk(3)}</div>
  <div class="card rel">
   <b style="font-size:17px">补充证据或更换候选</b>
   <div class="small" style="margin:6px 0 14px">拍标签或菜单图片需逐张单独确认接收方、用途和保存期限；拒绝外传仍可手动填写。</div>
   <div class="btn p1 full">手输配料信息</div>
   <div class="row gap8" style="margin-top:10px"><div class="btn s1 full" style="flex:1">拍标签（逐图授权）</div><div class="btn g1 full" style="flex:1">改选另一款</div></div>
  </div>
 </div>
</div>''', 'food', 660),
 '网页端·食品核对',
 '把“安全限制、价格、营养”三类判断拆成逐字段证据行，明确区分“不能推荐”与“可以记录”。',
 [('1', '三合一工作台', '顶部一键切换“识别与核对”“比较食品”“选择菜单”，共享同一份食品证据与来源记录。'),
  ('2', '四态证据流', '已知 ✓、待核对 !、冲突 ✕、未知 ?，状态同时用图标、颜色和文字表达，不依赖单一颜色。'),
  ('3', '受影响范围说明', '明确提示仅“主动推荐”受影响而暂停，不阻断浏览或如实记录；手输路径与逐图授权拍照并列。')])

# ---------- W03 计划与准备 ----------
SIZES['W03-plan'] = (1440, 700)
S['W03-plan'] = (desk(f'''
<div class="row sp"><div><div class="sub">11月18日 · 午餐 · 2 人准备</div><h1>备餐清单与计划预览</h1></div><div class="seg rel"><span>完整日周</span><span class="on">指定餐次</span>{mk(1,'right:-6px;top:-12px')}</div></div>
<div class="grid2" style="margin-top:18px;grid-template-columns:1.65fr 1fr">
 <div class="card rel" style="padding:10px 18px"><table><tr><th>食材</th><th>人数换算</th><th>总需求</th><th>可用库存</th><th>需购差额</th></tr>
  <tr><td><span class="emo" style="font-size:22px">🍅</span> <b>番茄</b></td><td>每人 150g × 2 人</td><td>300g</td><td>100g</td><td><span class="chip co">需购 200g</span></td></tr>
  <tr><td><span class="emo" style="font-size:22px">🥚</span> <b>鸡蛋</b></td><td>每人 1 个 × 2 人</td><td>2 个</td><td>1 个</td><td><span class="chip co">需购 1 个</span></td></tr>
  <tr style="background:#FBFDFB"><td><span class="emo" style="font-size:22px">🍜</span> <b>面条</b></td><td>全餐 200g（不乘人数）</td><td>200g</td><td><span class="chip n">未核对</span></td><td><span class="chip n">差额未知</span></td></tr></table>
  <div class="row gap8" style="padding:12px 10px 6px"><span class="chip co">2 项需购</span><span class="chip n">1 项未知</span><span class="chip g">✓ 0 项已购</span></div>
  {mk(2,'right:-8px;top:-10px')}</div>
 <div>
  <div class="card rel"><b style="font-size:17px">确认前预览</b>
   <div class="st"><div class="si g">1</div><div><b>生效槽位</b><div class="small">仅替换 11-18 午餐，其余日期与餐次保留</div></div></div>
   <div class="st"><div class="si g">2</div><div><b>将生成清单 v1</b><div class="small">计划确认与清单确认分开；旧已购不自动迁移</div></div></div>
   <div class="st"><div class="si a">!</div><div><b>1 项未知（面条）</b><div class="small">未知库存不填零，不生成确定需购量</div></div></div>
   <div class="btn p1 full" style="margin-top:8px">先核对面条库存</div>
   <div class="btn g1 full sm" style="margin-top:8px">保存含未知项的清单</div>{mk(3)}</div>
 </div>
</div>''', 'plan', 620),
 '网页端·计划与备餐清单',
 '在表格中直观展示“每人 × 人数”与“全餐总量”两种换算方式，右侧固定展示确认影响范围与未知项规则。',
 [('1', '计划模式切换', '支持“完整日周（检查 3/21 餐）”与“指定餐次”，按当前选择明确校验范围。'),
  ('2', '换算与未知透明', '“人数换算”单独成列；面条库存未核对时保持“差额未知”，绝不按 0 抵扣。'),
  ('3', '确认影响预览', '右侧清晰列出生效槽位、清单版本与未知提示，主按钮优先引导核对未知库存。')])

# ---------- W04 食材库存 ----------
SIZES['W04-inventory'] = (1440, 720)
S['W04-inventory'] = (desk(f'''
<div class="row sp"><div><div class="sub">食材库存 · 共享余量与有效期批次</div><h1>手边有什么，一眼看清</h1></div><div class="btn p1">＋ 新增或核对库存</div></div>
<div class="grid2" style="margin-top:18px;grid-template-columns:1.55fr 1fr">
 <div class="card rel" style="padding:10px 18px"><table><tr><th>食材与批次</th><th>当前余量</th><th>有效期</th><th>核对状态</th></tr>
  <tr><td><b>鸡肉 · 批次 A</b></td><td>100 g</td><td>11月18日</td><td><span class="chip g">✓ 优先用于近日期</span></td></tr>
  <tr><td><b>鸡肉 · 批次 B</b></td><td>200 g</td><td>11月25日</td><td><span class="chip g">✓ 已核对</span></td></tr>
  <tr><td><b>鸡蛋</b></td><td>2 个</td><td>未填写</td><td><span class="chip a">! 未来可用性待核对</span></td></tr>
  <tr><td><b>青菜</b></td><td>少量（定性）</td><td>未填写</td><td><span class="chip n">? 数值差额未知</span></td></tr></table>
  {mk(1,'right:-8px;top:-10px')}</div>
 <div>
  <div class="card rel" style="background:var(--gs);box-shadow:none"><b style="color:var(--gd);font-size:16px">跨计划只读估算预览</b>
   <div class="p" style="margin-top:6px">18日午餐需鸡肉 200 g、20日需 100 g；按近效期优先分配，当前批次可覆盖。</div>
   <div class="small" style="margin-top:6px">仅实时估算参考缺口，不预占或自动扣减真实库存。</div>{mk(2)}</div>
  <div class="card rel"><b style="font-size:17px">入库 / 扣减前预览</b>
   <div class="row sp" style="margin:12px 0;padding:12px;background:var(--bg);border-radius:12px"><div><div class="small">鸡肉 · 批次 A</div><b>100 g → 0 g</b></div><span class="chip g">核对通过</span></div>
   <div class="small">入库、用量或删除均须单独确认；数量未知、单位不可比或超出余量时禁止扣减。</div>
   <div class="row gap8" style="margin-top:12px"><div class="btn s1 sm" style="flex:1">确认本次调整</div><div class="btn g1 sm" style="flex:1">取消</div></div>{mk(3)}</div>
 </div>
</div>''', 'inv', 640),
 '网页端·食材库存',
 '同食材不同有效期分批次管理，定性余量（少量）与未填有效期分别标注，跨计划只做只读估算而不隐式扣库。',
 [('1', '分批与定性状态', '同一食材按有效期分列；未填有效期不强制补齐，标“未来可用性待核对”；定性“少量”不冒充精确克数。'),
  ('2', '跨计划只读估算', '从核对时点起按未来餐次顺序估算消耗，近效期批次优先抵扣，不修改真实库存。'),
  ('3', '调整前预览原新值', '任何入库或扣减均先展示原值与新值并由用户单独确认，禁止负库存。')])

# ---------- W05 个人实际记餐 ----------
SIZES['W05-record'] = (1440, 720)
S['W05-record'] = (desk(f'''
<div class="row sp"><div><div class="sub">实际餐食记录 · 11月18日 午餐 · 个人实际</div><h1>吃过什么，如实记下来</h1></div><span class="chip g" style="height:34px;font-size:13.5px">3 种食物 · 只算 1 次午餐槽位</span></div>
<div class="grid2" style="margin-top:18px;grid-template-columns:1.55fr 1fr">
 <div>
  <div class="card rel">
   <div class="st" style="align-items:center"><div class="step emo">🍜</div><div style="flex:1"><b>番茄鸡蛋面</b><div style="margin-top:3px"><span class="chip n">计划预填 · 份量待核对</span></div></div>{stepper('1 份')}</div>
   <div class="st" style="align-items:center"><div class="step emo">🍵</div><div style="flex:1"><b>无糖茶</b><div style="margin-top:3px"><span class="chip g">✓ 用户手输</span></div></div>{stepper('300 mL')}</div>
   <div class="st" style="align-items:center"><div class="step emo">🍎</div><div style="flex:1"><b>苹果</b><div style="margin-top:3px"><span class="chip a">份量未知 · 可保留</span></div></div><div class="btn s1 sm">补充份量</div></div>
   <div style="margin-top:12px;padding:12px;border:1.5px dashed #9BB0A3;border-radius:14px;text-align:center;color:var(--g);font-weight:800">＋ 添加同餐其他食物</div>
   {mk(1)}
  </div>
 </div>
 <div>
  <div class="card rel"><b style="font-size:17px">核对后再成为记录</b>
   <div class="st"><div class="si g">1</div><div><b>个人份量独立核对</b><div class="small">计划只预填名称与出处，多人准备量不代表个人摄入</div></div></div>
   <div class="st"><div class="si g">2</div><div><b>不自动扣减库存</b><div class="small">也不将采纳的微行动自动标为已完成</div></div></div>
   <div class="st"><div class="si n">?</div><div><b>未知份量不按 0 计算</b><div class="small">保留未知状态，保存后仍可修订整份餐食</div></div></div>
   <div class="btn p1 full" style="margin-top:10px">预览并确认这一餐</div>
   <div class="btn g1 full sm" style="margin-top:8px">取消草稿，不保存</div>{mk(2)}</div>
 </div>
</div>''', 'today', 640),
 '网页端·个人实际记餐',
 '一餐包含多种食物时统一在一个草稿内调整，步进器降低份量修改成本，未知份量无需强填即可保存。',
 [('1', '同餐多食物与步进器', '三种食物同属一次午餐，覆盖率只计 1 个槽位；步进器让常见份量一键微调，计划预填项明确标注待核对。'),
  ('2', '确认边界提示', '保存前明示“不自动扣库存、不代写微行动完成、未知不按零计”，取消草稿绝不写入记录。')])

# ---------- W06 微行动采纳与窗口 ----------
SIZES['W06-action'] = (1440, 720)
S['W06-action'] = (desk(f'''
<div class="row sp"><div><div class="sub">今日微行动 · 平替类 · 可修改、可跳过</div><h1>先确认一个小行动</h1></div><span class="chip co" style="height:34px;font-size:13.5px">努力量：低 · 仅改变饮品</span></div>
<div class="grid2" style="margin-top:18px;grid-template-columns:1.35fr 1fr">
 <div class="card rel" style="padding-bottom:10px">
  <h2 style="margin-bottom:16px">拿饮料时，换成白水</h2>
  {tl('📍','触发线索','明天午餐点饮品或拿饮料时')}
  {tl('💧','具体行为','本次饮品选择已确认可获得的白水，主餐保持不变')}
  {tl('🎯','推荐依据','符合你已确认的“减少含糖饮品”目标',True)}
  <div class="row gap8" style="margin-top:6px"><span class="chip g">✓ 不碰过敏底线</span><span class="chip g">✓ 不增加餐费</span><span class="chip g">✓ 随处可得</span></div>
  {mk(1)}
 </div>
 <div>
  <div class="card rel"><div class="row sp"><b style="font-size:17px">这次行动什么时候结束？</b><span class="chip v">建议窗口</span></div>
   <div class="row gap8" style="margin:14px 0"><div style="flex:1;background:var(--bg);border-radius:14px;padding:12px 14px"><div class="small">开始时间</div><b style="font-size:16px">11-18 11:00</b></div><span style="color:var(--mute);font-weight:800">→</span><div style="flex:1;background:var(--bg);border-radius:14px;padding:12px 14px"><div class="small">结束时间</div><b style="font-size:16px">11-18 14:00</b></div></div>
   <div class="small">窗口按本次午餐场景提出，开始和结束时间都可修改，不套用统一 24 小时。</div>
   <div class="btn c1 full" style="margin-top:16px">采纳这个行动</div>
   <div class="row gap8" style="margin-top:10px"><div class="btn s1 sm" style="flex:1">换一个</div><div class="btn g1 sm" style="flex:1">跳过</div></div>
   <div class="small" style="text-align:center;margin-top:8px">采纳只表示愿意一试，进入“待反馈”，不计为完成。</div>{mk(2)}</div>
 </div>
</div>''', 'today', 640),
 '网页端·微行动采纳与窗口',
 '左侧用时间线讲清“什么时候做、做什么、为什么推荐”，右侧由用户确认或修改行动窗口后再决定采纳、换一个或跳过。',
 [('1', '时间线与资格核对', '线索、行为、依据三步清晰呈现，底部三个绿色标签证明已通过安全、预算和可获得性核对。'),
  ('2', '可修改行动窗口', '起止时间并排可改；采纳按钮下方明确写出“采纳不等于完成”。')])

# ---------- W07 执行反馈 ----------
SIZES['W07-feedback'] = (1440, 720)
S['W07-feedback'] = (desk(f'''
<div class="row sp"><div><div class="sub">执行反馈 · 行动 A01（窗口：11-18 11:00–14:00）</div><h1>这次进行得怎样？</h1></div><span class="chip a" style="height:34px;font-size:13.5px">● 待执行反馈</span></div>
<div class="grid2" style="margin-top:18px;grid-template-columns:1.35fr 1fr">
 <div class="card rel">
  <b style="font-size:17px;display:block;margin-bottom:12px">选择本次执行结果（互斥三选一）</b>
  {choice('✅','完成','按计划换成了白水')}
  {choice('🌗','部分完成','换了小杯，仍喝了一些含糖饮料',True)}
  {choice('⏭️','未完成','这次没有尝试')}
  {mk(1)}
 </div>
 <div>
  <div class="card rel">
   <div class="row sp"><div><div class="small">实际执行日期（默认带入，可修改）</div><b style="font-size:18px">2026-11-18</b></div><div class="btn s1 sm">修改日期</div></div>
   <div style="margin-top:14px"><div class="lab" style="margin-bottom:8px">遇到的障碍（可选）</div>
    <div class="row gap8" style="flex-wrap:wrap"><span class="chip n">来不及</span><span class="chip n">没买到</span><span class="chip g">✓ 口味不习惯</span><span class="chip n">其他</span></div></div>
   <div style="margin-top:14px;background:var(--bg);border-radius:12px;padding:10px 14px"><div class="small">备注（可选）</div><div style="font-size:14.5px;margin-top:2px">换了小杯，仍喝了一些含糖饮料</div></div>
   <div class="btn p1 full" style="margin-top:16px">确认这次反馈</div>
   <div class="btn g1 full sm" style="margin-top:8px">暂不反馈（窗口结束后记为未知）</div>{mk(2)}</div>
 </div>
</div>''', 'today', 640),
 '网页端·执行反馈',
 '互斥三选一卡片配默认带入的执行日期与可选障碍标签，让用户在 30 秒内、至多 3 次主要操作完成反馈。',
 [('1', '互斥大卡片', '完成、部分完成、未完成互斥单选，用边框、底色和勾选图标三重区分；迟到补报沿原行动更新有效版本。'),
  ('2', '可选障碍与暂不反馈', '障碍标签与备注均可选填，用于改进下次同类建议；“暂不反馈”在窗口结束后记为未知，不代写未完成。')])

# ---------- W08 阶段回顾 ----------
SIZES['W08-review'] = (1440, 720)
S['W08-review'] = (desk(f'''
<div class="row sp"><div><div class="sub">11月16日 – 11月22日 · 本周回顾（亚洲/上海）</div><h1>这一周，看清楚了</h1></div><div class="btn g1 sm">修改预期餐次（当前 10）</div></div>
<div class="grid3" style="margin-top:18px">
 <div class="card rel row sp">{ring(100,'完成行动','3 个','按执行日期')}<div class="small" style="width:140px">按用户自述实际执行日期归周，采纳不计入。</div>{mk(1)}</div>
 <div class="card row sp">{ring(80,'反馈覆盖','80%','4 / 5 个已结束')}<div class="small" style="width:140px">本周结束窗口共 5 个，已有效反馈 4 个。</div></div>
 <div class="card row sp">{ring(75,'已反馈者完成','75%','3 / 4 个反馈','#D4401B')}<div class="small" style="width:140px">仅在已反馈队列中计算，未知不作失败。</div></div>
</div>
<div class="grid2" style="margin-top:16px;grid-template-columns:1.35fr 1fr">
 <div class="card rel"><b style="font-size:17px">本周结束队列（5 个行动，可追溯来源）</b>
  <div class="st"><div class="si g">✓</div><div style="flex:1"><b>周一 · 午餐拿饮料时换成白水</b></div><span class="chip g">完成</span></div>
  <div class="st"><div class="si g">✓</div><div style="flex:1"><b>周二 · 餐前先喝一杯水</b></div><span class="chip g">完成</span></div>
  <div class="st"><div class="si g">✓</div><div style="flex:1"><b>周二 · 晚餐先吃蔬菜</b></div><span class="chip g">完成</span></div>
  <div class="st"><div class="si a">◐</div><div style="flex:1"><b>周三 · 午餐拿饮料时换成白水</b></div><span class="chip a">部分完成</span></div>
  <div class="st"><div class="si n">?</div><div style="flex:1"><b>周三 · 晚餐减少一口主食</b></div><span class="chip n">未反馈 · 未知</span></div>{mk(2)}</div>
 <div>
  <div class="card"><div class="row sp"><b>餐次覆盖</b><span><b style="font-size:22px">7</b><span class="small"> / 10 个预期槽位</span></span></div><div class="bar" style="margin:10px 0 12px"><i style="width:70%"></i></div><div class="row sp"><span class="small">营养可计算覆盖</span><span class="chip n">未知 · 缺少可核对资料</span></div></div>
  <div class="card rel" style="background:var(--vis);box-shadow:none"><b style="color:#2D2688;font-size:16px">✨ 两次反馈提到“口味不习惯”</b><div class="p" style="color:#2D2688;margin-top:4px">来源：11-16、11-17 行动反馈。下次建议换成无糖茶，是否核对并带入？</div><div class="row gap8" style="margin-top:12px"><div class="btn p1 sm" style="flex:1.4">核对并带入</div><div class="btn g1 sm" style="flex:1">暂不处理</div></div>{mk(3)}</div>
 </div>
</div>''', 'review', 640),
 '网页端·阶段回顾',
 '用三个独立环形指标分开统计口径，下方列表可追溯到具体行动与未知项，调整提案由用户核对后才带入下一次任务。',
 [('1', '三口径分离', '完成行动按执行日归周，反馈覆盖和已反馈者完成比例基于结束窗口队列，分母与口径固定展示。'),
  ('2', '明细可追溯', '结束队列逐条列出，未反馈项保持“未知”而非失败，可随时点击补充迟到反馈。'),
  ('3', '待核对线索', '所有观察先展示来源记录与时间范围，只有用户确认后才预填到下一次建议中。')])

# ---------- W09 中断恢复 ----------
SIZES['W09-recovery'] = (1440, 680)
S['W09-recovery'] = (desk(f'''
<div class="row sp"><div><div class="sub">实际餐食记录 · 网络中断恢复</div><h1>先核对保存结果</h1></div><span class="chip a" style="height:34px;font-size:13.5px">● 待核对回执</span></div>
<div class="card rel" style="margin-top:16px;background:linear-gradient(135deg,#FFF3D6,#FFE9C2);box-shadow:none"><div class="row gap16"><div class="emo" style="font-size:34px">📡</div><div><b style="font-size:17px;color:#5E3A00">提交后暂时没有收到服务器回执</b><div class="p" style="color:#5E3A00;margin-top:2px">你刚才填写的内容已保留在本地草稿中。系统将按原操作键查证结果：若已保存则显示原记录，绝不会再创建第二份。</div></div></div>{mk(1)}</div>
<div class="grid2eq" style="margin-top:16px">
 <div class="card rel"><b style="font-size:17px">你刚才确认的内容（已保留）</b>
  <div style="margin-top:14px;padding:14px;background:var(--bg);border-radius:14px">
   <div class="small">11月18日 · 午餐</div>
   <b style="font-size:16px;display:block;margin-top:4px;line-height:1.6">番茄鸡蛋面 1 份 · 无糖茶 300 mL · 苹果（份量未知）</b>
  </div>
  <div class="small" style="margin-top:12px">若发现来源资料或档案在断网期间发生变化，系统会先展示差异供你重新核对，再决定是否提交。</div>{mk(2)}</div>
 <div class="card rel"><b style="font-size:17px">核对进度</b>
  <div style="margin-top:14px">
   <div class="row gap12"><div class="si g">✓</div><div><b>1. 提交请求已发出</b><div class="small">携带唯一操作键与预期修订号</div></div></div>
   <div style="height:18px;margin-left:14px;border-left:2px solid #CFE3D4"></div>
   <div class="row gap12"><div class="si a">●</div><div><b>2. 正在按原键核对保存结果</b><div class="small">查询不可用时保持待核对，不另建新键</div></div></div>
   <div style="height:18px;margin-left:14px;border-left:2px dashed #CFE3D4"></div>
   <div class="row gap12"><div class="si n">○</div><div><b style="color:var(--mute)">3. 显示最终确认记录</b></div></div>
  </div>
  <div class="row gap8" style="margin-top:20px"><div class="btn p1" style="flex:1.5">核对保存结果</div><div class="btn g1" style="flex:1">保留草稿，稍后继续</div></div>{mk(3)}</div>
</div>''', 'today', 600),
 '网页端·中断恢复',
 '断网或响应丢失后不要求重填，先给出“不重复保存”的承诺、完整回显原内容，并用三步进度条引导唯一查证动作。',
 [('1', '温和提示与承诺', '明确说明内容已保留且不会重复创建记录，消除用户反复点击提交的焦虑。'),
  ('2', '原内容回显', '保留完整餐食草稿；若期间对象版本变化，先展示差异供重新核对。'),
  ('3', '三步核对进度', '按原操作键查证回执状态，主按钮直接触发查证，也可先保留草稿稍后恢复。')])

# ---------- W10 个人数据控制 ----------
SIZES['W10-privacy'] = (1440, 680)
S['W10-privacy'] = (desk(f'''
<div class="row sp"><div><div class="sub">我的数据 · 按用途分别授权</div><h1>我的数据，我来决定</h1></div><div class="avatar">我</div></div>
<div class="grid2eq" style="margin-top:18px">
 <div class="card rel" style="padding:10px 20px">
  {setrow('📊','历史分析与排序','用于回顾与排序，可随时关闭；关闭后旧快照不再使用',True)}
  {setrow('🖼️','逐图外传授权','每张图片上传前单独确认用途、接收方与期限；拒绝后仍可手输',False)}
  {setrow('🔔','主动订阅提醒','仅在订阅后发送；连续两次未响应自动退避，不影响主动请求',True)}
  {mk(1)}
 </div>
 <div>
  <div class="card rel">
   <div class="row sp"><b style="font-size:17px">全量删除进度</b><span class="chip a">● 处理中</span></div>
   <div class="row" style="margin:16px 0 6px;align-items:center"><div class="si g" style="width:28px;height:28px;font-size:13px">✓</div><div style="flex:1;height:3px;background:var(--g)"></div><div class="si a" style="width:28px;height:28px;font-size:13px">●</div><div style="flex:1;height:3px;background:repeating-linear-gradient(90deg,#B8C9BD 0 6px,transparent 6px 10px)"></div><div class="si n" style="width:28px;height:28px;font-size:13px">○</div></div>
   <div class="row sp small" style="font-weight:700"><span>已受理</span><span>处理中</span><span>清理完成</span></div>
   <div class="small" style="margin-top:8px">“已受理”不等于清理完成；短期凭证仅用于查询本次进度，不恢复原数据。</div>
   <div class="row gap8" style="margin-top:12px"><div class="btn s1 sm" style="flex:1">导出我的数据</div><div class="btn g1 sm" style="flex:1;color:var(--rd);border-color:#F0B9B5">删除全部数据</div></div>{mk(2)}</div>
  <div class="card"><b style="font-size:16px">数据保留期限</b>
   <div class="row sp small" style="margin-top:8px"><span>临时图片</span><b>不超过 24 小时</b></div>
   <div class="row sp small" style="margin-top:4px"><span>任务临时草稿</span><b>不超过 7 天</b></div>
   <div class="row sp small" style="margin-top:4px"><span>业务记录</span><b>原则上 180 天（支持明确续期）</b></div></div>
 </div>
</div>''', 'me', 600),
 '网页端·个人数据控制',
 '把用途授权做成互不干扰的独立开关，导出与全量删除提供三段真实进度与明确的数据保留期限。',
 [('1', '分用途独立开关', '历史分析、逐图外传和提醒各自控制，关闭附加功能绝不阻断核心饮食管理任务。'),
  ('2', '三段删除进度与期限', '已受理 → 处理中 → 清理完成三段状态清晰可查，明确展示 24 小时、7 天、180 天保存期限。')])

def shot(html_name, size, out):
    url = (HTML / html_name).resolve().as_uri()
    subprocess.run([EDGE, '--headless', '--disable-gpu', '--hide-scrollbars', '--force-device-scale-factor=2',
                    f'--window-size={size[0]},{size[1]}', '--default-background-color=00000000',
                    f'--screenshot={out}', url], check=True, capture_output=True, timeout=120)

if __name__ == '__main__':
    meta = {}
    for name, (html, title, intent, notes) in S.items():
        (HTML / f'{name}.html').write_text(html, encoding='utf-8')
        shot(f'{name}.html', SIZES[name], PNG / f'{name}.png')
        meta[name] = {'title': title, 'intent': intent, 'notes': notes}
        print('已渲染', name)
    (OUT / 'screens.json').write_text(json.dumps(meta, ensure_ascii=False, indent=1), encoding='utf-8')
