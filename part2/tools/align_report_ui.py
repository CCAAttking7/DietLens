"""从 UI v2 生成与指定原稿第 5 章一致的六张展示图源。"""
from pathlib import Path
import runpy
import shutil

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'final/原文配图整合'
HTML = OUT / '界面图源/html'
HTML.mkdir(parents=True, exist_ok=True)
shutil.copy2(ROOT / 'ui_v2/ui.css', HTML.parent / 'ui.css')
ui = runpy.run_path(str(ROOT / 'tools/render_ui_v2.py'))
screens, desk, ring = ui['S'], ui['desk'], ui['ring']


def revise(name, changes):
    page = screens[name][0]
    for old, new in changes:
        assert old in page, (name, old)
        page = page.replace(old, new, 1)
    return page


today = revise('W01-today', [
    (f'<span class="round" style="background:#EEF2EE;color:var(--ink2)">{ui["ic"]("mic")}</span>',
     '<span class="small" style="white-space:nowrap">手动填写</span>'),
    ('✓ 已拆分为两项独立草稿：1) 待核对午餐记录（份量待确认）　2) 晚餐微行动候选（尚未采纳）',
     '午餐记录草稿 · 份量待核对　｜　晚餐微行动候选 · 尚未采纳'),
    ('今日微行动 · 努力量：低', '晚餐微行动候选 · 尚未采纳'),
    ('11:00–14:00 可尝试', '晚餐时段 · 窗口待确认'),
    ('采纳这个行动', '核对行动与窗口'),
    ('本周小进展', '上周小进展 · 11月9日–15日'),
    (ring(100, '完成', '3 个', '按执行日期'), ring(100, '完成', '2 次', '按执行日期')),
    (ring(80, '反馈覆盖', '80%', '4 / 5 个已结束'), ring(62.5, '反馈覆盖', '62.5%', '5 / 8 个已结束')),
])
food = revise('W02-food', [
    ('识别与核对','识别食品'),
    ('已知 · 本次菜单文字输入，满足每餐预算 ¥20', '已知 · 菜单标价。完整餐次总费用仍待核对'),
])
plan = revise('W03-plan', [
    ('<div class="grid2" style="margin-top:18px;grid-template-columns:1.65fr 1fr">',
     '<div class="row gap8" style="margin-top:12px"><span class="chip g">当前有效餐次：11月18日午餐 · 计划 v2</span><span class="chip n">计划 v3 · 待确认</span><span class="chip n">单计划清单</span><span class="chip n">跨计划只读汇总</span></div><div class="grid2" style="margin-top:15px;grid-template-columns:1.65fr 1fr">'),
    ('<span class="chip g">✓ 0 项已购</span>', '<span class="chip g">采购进度 · 0 项已购</span>'),
    ('<i class="mk" style="right:-8px;top:-10px">2</i></div>', '<div class="row gap8" style="padding:8px 10px"><span class="chip n">新增／改量／移除</span><span class="chip n">核对清单差异</span></div></div>'),
    ('仅替换 11-18 午餐，其余日期与餐次保留', '逐项核对重叠；本次仅替换 11月18日午餐'),
    ('将生成清单 v1', '计划与清单分别确认'),
    ('计划确认与清单确认分开；旧已购不自动迁移', '计划确认后核对清单差异与手工调整'),
    ('先核对面条库存', '复核食品与预算后确认计划'),
    ('保存含未知项的清单', '仅保存为备选'),
])
inventory = revise('W04-inventory', [
    ('数量未知、单位不可比或超出余量时禁止扣减。', '余量可标为充足、少量或用完；数量未知、单位不可比或超量时禁止扣减。'),
])
review = desk(f'''
<div class="row sp"><div><div class="sub">11月9日 – 11月15日 · 亚洲/上海</div><h1>这一周，看清楚了</h1></div>
<div class="btn g1 sm">修改预期餐次（当前 10）</div></div>
<div class="grid2eq" style="margin-top:16px">
 <div class="card"><h3>手边的余地</h3><div class="p" style="margin-top:8px">青菜余量未核对，采购差额未知。</div><div class="btn s1 sm" style="margin-top:10px">查看计划与库存依据</div></div>
 <div class="card"><h3>日常的节奏</h3><div class="p" style="margin-top:8px">已记录餐次 6 / 10（60%）</div><div class="bar" style="margin:8px 0"><i style="width:60%"></i></div><div class="small">能量可计算 5 / 8 项；已知小计 1420 kcal</div></div>
 <div class="card"><h3>小行动的尝试</h3><div class="p" style="margin-top:8px">本周采纳 6 次 · 更换 2 次 · 修改 1 次</div><div class="small">按决定日期统计，可查看原始选择记录。</div><div class="btn g1 sm" style="margin-top:10px">查看选择明细</div></div>
 <div class="card"><h3>执行与调整</h3><div class="row sp" style="margin-top:10px">{ring(100,'执行日归周','2 次','自述已完成')}{ring(62.5,'反馈覆盖','62.5%','5 / 8 个已结束')}{ring(60,'已反馈者完成','60%','3 / 5 个有效反馈','#D4401B')}</div><div class="small" style="margin-top:7px">窗口已结束但无有效反馈：3 项未知 · 查看来源／补报</div></div>
</div>
<div class="card row sp gap12" style="margin-top:14px;background:var(--vis);box-shadow:none">
 <div><h3>两次晚餐都提到时间困难</h3><div class="small">来源：11月11日、12日晚餐及关联行动。下次是否减少准备步骤？</div></div>
 <div class="row gap8"><div class="btn p1 sm">核对并带入</div><div class="btn g1 sm">否认</div><div class="btn g1 sm">仅本次</div></div>
</div>''', 'review', 640)
settings = desk(f'''
<div class="row sp"><div><div class="sub">设置与个人数据</div><h1>设置与任务恢复</h1></div><div class="avatar">我</div></div>
<div class="grid2eq" style="margin-top:18px">
 <div><div class="card"><h3>情境校准与提醒</h3>
  <div class="st"><div><b>可选情境校准 · 最多三题</b><div class="small">可以逐题跳过。只保存确认过的回答，可单独修改或删除。</div></div></div>
  <div class="btn s1 sm">管理校准回答</div>
  <div class="st" style="margin-top:12px"><div><b>主动订阅提醒 · 当前未订阅</b><div class="small">两次未响应后进入退避，可重新设置。</div></div></div>
  <div class="row gap8"><div class="btn g1 sm">管理订阅</div><div class="btn g1 sm">重置退避</div></div>
 </div></div>
 <div><div class="card"><h3>继续上次的任务</h3><div class="st"><div class="si a">!</div><div><b>晚餐微行动 · 情境待核对</b><div class="small">恢复时检查最新条件、授权和对象版本。</div></div></div><div class="btn p1 sm">继续核对</div></div>
 <div class="card"><h3>授权与数据管理</h3><div class="p" style="margin:8px 0">历史分析按用途授权。图片外传逐张确认。</div><div class="row gap8"><div class="btn s1 sm">管理授权</div><div class="btn g1 sm">导出数据</div><div class="btn g1 sm">删除数据</div></div></div></div>
</div>''', 'me', 600)

for name, page in {'care': today, 'food': food, 'plan': plan, 'inventory': inventory,
                   'workbench': review, 'settings': settings}.items():
    page = page.replace('我的数据</div>', '设置</div>')
    page = page.replace('</head>', '<style>.mk{display:none}</style></head>')
    (HTML / f'{name}.html').write_text(page, encoding='utf-8')
