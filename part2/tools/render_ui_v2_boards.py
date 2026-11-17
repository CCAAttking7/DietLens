"""生成网页端设计系统板、信息架构板、界面总览板，并计算关键配色的WCAG对比度。
用法：python part2/tools/render_ui_v2_boards.py   （需先运行 render_ui_v2.py）
"""
from pathlib import Path
import json, sys
sys.path.insert(0, str(Path(__file__).resolve().parent))
import render_ui_v2 as R

OUT = R.OUT
HTML, PNG = R.HTML, R.PNG

def lum(h):
    h = h.lstrip('#'); r, g, b = [int(h[i:i + 2], 16) / 255 for i in (0, 2, 4)]
    f = lambda c: c / 12.92 if c <= .03928 else ((c + .055) / 1.055) ** 2.4
    return .2126 * f(r) + .7152 * f(g) + .0722 * f(b)
def cr(a, b):
    la, lb = lum(a), lum(b)
    if la < lb: la, lb = lb, la
    return (la + .05) / (lb + .05)

PAIRS = [
 ('主按钮文字（浅端）', '#FFFFFF', '#118650', '主按钮渐变最浅端上的白字'),
 ('主按钮文字（深端）', '#FFFFFF', '#0F7D47', '森林绿底上的白字'),
 ('微行动按钮文字', '#FFFFFF', '#D4401B', '陶橙渐变最浅端上的白字'),
 ('首页主卡文字', '#FFFFFF', '#118650', '主卡渐变最浅端上的白字'),
 ('正文', '#10251C', '#FFFFFF', '深墨绿字，白卡片'),
 ('次要正文', '#41564A', '#F3F8F2', '次要说明，页面底色'),
 ('辅助说明', '#5A6D61', '#F3F8F2', '最浅一级说明文字，页面底色'),
 ('已知状态', '#073D27', '#DDF3E4', '深绿字，浅绿标签'),
 ('待核对状态', '#8A5300', '#FFF0CF', '琥珀字，浅黄标签'),
 ('冲突状态', '#B3261E', '#FFE1DE', '红字，浅红标签'),
 ('智能建议', '#4B3FC9', '#ECEAFF', '紫字，浅紫标签'),
 ('微行动标签', '#A82F10', '#FFE9E1', '陶橙深字，浅橙标签'),
]
rows = [(n, f, b, d, round(cr(f, b), 2)) for n, f, b, d in PAIRS]
(OUT / 'contrast.json').write_text(json.dumps([{'项目': n, '前景': f, '背景': b, '说明': d, '对比度': c} for n, f, b, d, c in rows], ensure_ascii=False, indent=1), encoding='utf-8')
for r in rows: print(r)

HEAD = '<!doctype html><html lang="zh-CN"><head><meta charset="utf-8"><link rel="stylesheet" href="../ui.css"><style>body{{width:{w}px;height:{h}px}}.board{{width:{w}px;height:{h}px;padding:42px 50px;background:linear-gradient(155deg,#E8F5EB 0%,#FAF6EA 55%,#FFEDE3 100%)}}.bt{{font-size:34px;font-weight:800;color:var(--gd)}}.bs{{font-size:16px;color:var(--ink2);margin-top:6px}}.pn{{background:#fff;border-radius:22px;padding:22px;box-shadow:var(--sh)}}.pn h3{{font-size:17px;margin-bottom:12px;color:var(--gd)}}.sw1{{display:flex;align-items:center;gap:12px;margin-bottom:9px}}.chipx{{width:52px;height:40px;border-radius:12px;flex:none;box-shadow:inset 0 0 0 1px rgba(0,0,0,.06)}}</style></head><body><div class="board">'

def swatch(name, hexv, use):
    return f'<div class="sw1"><div class="chipx" style="background:{hexv}"></div><div><b style="font-size:14.5px">{name} <span style="font-weight:500;color:var(--mute)">{hexv}</span></b><div class="small">{use}</div></div></div>'

def system_board():
    w, h = 1640, 920
    c = HEAD.format(w=w, h=h)
    c += '<div class="bt">晨光餐盘 · 网页端视觉与交互规范</div><div class="bs">明亮的食材绿、温暖的陶橙与清晰的状态色；一页只有一个实心主按钮；状态用图标、文字、颜色三重表达。</div>'
    c += '<div style="display:grid;grid-template-columns:1fr 1fr 1fr;gap:20px;margin-top:24px">'
    c += '<div class="pn"><h3>色彩角色</h3>' + swatch('森林绿', '#0F7D47', '主操作、已知、成功') + swatch('陶橙', '#D4401B', '微行动、记餐入口（品牌记忆色）') + swatch('琥珀', '#8A5300', '待核对、处理中（配浅黄底）') + swatch('绛红', '#B3261E', '冲突、删除（配浅红底）') + swatch('薰衣草紫', '#4B3FC9', '智能建议、提案') + swatch('米绿底', '#F3F8F2', '页面背景，卡片用纯白') + swatch('深墨绿', '#10251C', '正文与标题') + '</div>'
    c += '<div class="pn"><h3>字体与尺寸（网页端）</h3><div style="font-size:28px;font-weight:800">页面标题 30 / 800</div><div style="font-size:20px;font-weight:800;margin-top:8px">卡片标题 20 / 800</div><div style="font-size:16px;font-weight:700;margin-top:8px">行标题与按钮 15 / 700</div><div style="font-size:14.5px;margin-top:8px;color:var(--ink2)">正文说明 14.5 / 400，行高 1.6</div><div style="font-size:13px;margin-top:8px;color:var(--mute)">辅助说明 13 / 400，仅用于补充信息</div>'
    c += '<h3 style="margin-top:18px">布局与交互尺寸</h3><div class="small" style="line-height:2">桌面工作台 1360 px，左侧固定导航栏 236 px<br>卡片圆角 20 px · 按钮圆角 14 px · 标签圆角 14 px<br>按钮高 40–46 px，步进器 36 px 视觉、整行 ≥ 48 px<br>字体：微软雅黑 UI，系统回退无衬线</div></div>'
    c += '<div class="pn"><h3>按钮层级</h3><div class="btn p1 full" style="margin-bottom:10px">主操作 · 每页仅一个</div><div class="btn c1 full" style="margin-bottom:10px">微行动 · 采纳</div><div class="row gap8"><div class="btn s1 sm" style="flex:1">次要</div><div class="btn g1 sm" style="flex:1">弱化 / 取消</div></div>'
    c += '<h3 style="margin-top:18px">状态标签</h3><div class="row gap8" style="flex-wrap:wrap"><span class="chip g">✓ 已知</span><span class="chip a">! 待核对</span><span class="chip r">✕ 冲突</span><span class="chip n">? 未知</span><span class="chip v">✨ 建议</span><span class="chip co">需购 200g</span></div></div>'
    c += '</div>'
    c += '<div style="display:grid;grid-template-columns:1.15fr 1fr 1fr;gap:20px;margin-top:18px">'
    c += '<div class="pn"><h3>状态行（图标 + 文字 + 来源）</h3><div class="st"><div class="si g">✓</div><div><b>名称、标价 ¥18</b><div class="small">已知 · 本次菜单文字输入</div></div></div><div class="st"><div class="si a">!</div><div><b>酱料配料</b><div class="small">待核对 · 菜单未列出，不由系统猜补</div></div></div><div class="st"><div class="si r">✕</div><div><b>配料与档案冲突</b><div class="small">冲突 · 命中花生，相关推荐已排除</div></div></div><div class="st"><div class="si n">?</div><div><b>热量</b><div class="small">未知 · 不按 0 处理</div></div></div></div>'
    c += '<div class="pn"><h3>输入与选择</h3><div class="seg" style="margin-bottom:14px"><span>完整日周</span><span class="on">指定餐次</span></div><div class="row sp"><b>步进器</b><div class="row gap8"><div class="step" style="width:36px;height:36px;background:var(--gr);color:var(--ink2)">−</div><b>1 份</b><div class="step" style="width:36px;height:36px">+</div></div></div><div class="row sp" style="margin-top:14px"><b>开关</b><div class="sw on"></div></div><div class="row sp" style="margin-top:14px"><b>环形指标</b><div class="ring" style="width:62px;height:62px;background:conic-gradient(var(--g) 0 80%,#E4EDE5 0)"><b style="font-size:14.5px">80%</b></div></div></div>'
    c += '<div class="pn"><h3>网页端设计原则</h3><div class="p" style="line-height:1.9">① 眼前这一餐优先，一页一个主动作<br>② 左主工作区 + 右影响预览，确认不盲按<br>③ 未知就说未知，不填零、不猜补<br>④ 采纳、执行、记录分别确认<br>⑤ 取消与恢复入口始终可见<br>⑥ 状态用图标、颜色、文字三重表达</div></div>'
    c += '</div></div></body></html>'
    return c, (w, h)

def flow_board():
    w, h = 1640, 720
    def node(t, s='', cls='g'):
        return f'<div class="chip {cls}" style="height:auto;padding:10px 16px;border-radius:14px;font-size:15px;flex-direction:column;align-items:flex-start;gap:2px;min-width:210px"><b>{t}</b><span style="font-weight:500;font-size:12.5px">{s}</span></div>'
    arrow = '<div style="font-size:24px;color:var(--mute);padding:0 6px">→</div>'
    def lane(title, items, color):
        return f'<div class="pn" style="margin-top:12px;padding:14px 22px"><div class="row"><div style="width:170px;font-weight:800;color:{color};font-size:16.5px">{title}</div><div class="row" style="flex-wrap:nowrap">' + arrow.join(items) + '</div></div></div>'
    c = HEAD.format(w=w, h=h)
    c += '<div class="bt">网页端信息架构与核心流程</div><div class="bs">左侧常驻导航对应六类工作台加“记一餐”主入口；所有写入类流程共用“说 → 核 → 确认 → 回执”四步，取消与恢复始终可见。</div>'
    c += lane('今日工作台', [node('今日工作台', '一句话复合意图入口'), node('微行动采纳', '确认行动窗口', 'co'), node('执行反馈', '完成 / 部分 / 未完成', 'co'), node('回顾洞察', '核对后带入', 'v')], 'var(--g)')
    c += lane('食品核对', [node('识别 / 比较 / 菜单', '三合一工作台'), node('补充配料', '手输或逐图授权拍标签', 'a'), node('恢复推荐', '未知项解除', 'g')], 'var(--g)')
    c += lane('计划与库存', [node('计划与备餐清单', '人数换算，未知不补零'), node('食材库存', '分批次有效期与只读估算', 'a'), node('调整前预览', '展示原值与新值', 'g')], 'var(--g)')
    c += lane('记一餐', [node('个人实际记餐', '一餐多种食物'), node('预览这一餐', '核对个人份量', 'a'), node('确认保存', '一次提交'), node('网络中断？', '先核对保存结果', 'r')], 'var(--co)')
    c += lane('回顾与数据', [node('阶段回顾', '三口径与明细追溯'), node('调整提案', '用户核对后生效', 'v'), node('我的数据', '分用途开关'), node('导出 / 删除', '三段真实进度', 'a')], 'var(--vi)')
    c += '</div></body></html>'
    return c, (w, h)

def overview_board():
    order = ['W01-today', 'W02-food', 'W03-plan', 'W04-inventory', 'W05-record',
             'W06-action', 'W07-feedback', 'W08-review', 'W09-recovery', 'W10-privacy']
    names = {'W01-today': 'W01 今日工作台', 'W02-food': 'W02 食品核对', 'W03-plan': 'W03 计划与备餐清单',
             'W04-inventory': 'W04 食材库存', 'W05-record': 'W05 个人实际记餐', 'W06-action': 'W06 微行动采纳',
             'W07-feedback': 'W07 执行反馈', 'W08-review': 'W08 阶段回顾', 'W09-recovery': 'W09 中断恢复', 'W10-privacy': 'W10 个人数据控制'}
    w, h = 1640, 1180
    c = HEAD.format(w=w, h=h)
    c += '<div class="bt">DietLens 网页端新界面总览 · 晨光餐盘</div><div class="bs">10 个网页端核心界面共用同一套设计系统与常驻侧栏结构（虚构示例数据，设计稿）。</div>'
    c += '<div style="display:grid;grid-template-columns:repeat(2,740px);gap:20px 36px;margin-top:22px;justify-content:center">'
    for n in order:
        c += (f'<div style="display:flex;flex-direction:column;align-items:center">'
              f'<img src="{n}.png" style="width:740px;height:auto;border-radius:12px;box-shadow:0 6px 18px rgba(16,37,28,.12)">'
              f'<div style="margin-top:6px;font-size:15px;font-weight:800;color:var(--gd)">{names[n]}</div></div>')
    c += '</div></div></body></html>'
    # 5 rows * (740 * 740/1440 ≈ 380 + 30) ≈ 2050 + 180 = 2230
    return c, (1640, 2240)

def cover_board():
    picks = [('W01-today', '今日工作台'), ('W02-food', '食品核对'), ('W03-plan', '计划与清单'),
             ('W05-record', '个人记餐'), ('W06-action', '微行动采纳'), ('W08-review', '阶段回顾')]
    w, h = 1560, 1340
    c = ('<!doctype html><html lang="zh-CN"><head><meta charset="utf-8"><link rel="stylesheet" href="../ui.css">'
         '<style>body{width:1560px;height:1340px;background:transparent}</style></head><body>'
         '<div style="display:grid;grid-template-columns:repeat(2,750px);gap:24px 36px;justify-content:center;padding:12px">')
    for n, label in picks:
        c += (f'<div style="text-align:center"><img src="{n}.png" style="width:750px;border-radius:14px;box-shadow:0 10px 26px rgba(16,37,28,.16)">'
              f'<div style="margin-top:8px;font-size:18px;font-weight:800;color:var(--gd)">{label}</div></div>')
    c += '</div></body></html>'
    return c, (w, h)

if __name__ == '__main__':
    for name, fn in (('B01-design-system', system_board), ('B02-flow', flow_board), ('B03-overview', overview_board), ('B04-cover', cover_board)):
        html, size = fn()
        (HTML / f'{name}.html').write_text(html, encoding='utf-8')
        # B03/B04 reference pngs in ../png/, so write html into PNG dir or fix relative path
        if name in ('B03-overview', 'B04-cover'):
            (PNG / f'{name}.html').write_text(html.replace('../ui.css', '../ui.css'), encoding='utf-8')
            url = (PNG / f'{name}.html').resolve().as_uri()
            import subprocess
            subprocess.run([R.EDGE, '--headless', '--disable-gpu', '--hide-scrollbars', '--force-device-scale-factor=2',
                            f'--window-size={size[0]},{size[1]}', '--default-background-color=00000000',
                            f'--screenshot={PNG / (name + ".png")}', url], check=True, capture_output=True, timeout=120)
            (PNG / f'{name}.html').unlink(missing_ok=True)
        else:
            R.shot(f'{name}.html', size, PNG / f'{name}.png')
        print('已渲染', name)
