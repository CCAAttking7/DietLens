"""将指定 Markdown 按原文排版，仅将已核对的 Mermaid 源码转成图。"""
from pathlib import Path
import hashlib
import json
import re
import shutil
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / '作业二设计稿准备/作业二设计稿准备/DietLens_Assignment2_精简润色版.md'
MODELS = ROOT / 'final/视觉整合版'
replace_ui = '--ui-v2' in sys.argv
OUT = ROOT / ('final/原文配图整合' if replace_ui else 'final/原文排版检查')
OUT.mkdir(parents=True, exist_ok=True)


def pandoc(text, *args):
    return subprocess.run(['pandoc', *args], input=text, encoding='utf-8',
                          capture_output=True, check=True).stdout


original = SOURCE.read_bytes()
source = original.decode('utf-8-sig')
if replace_ui:
    for old, new in [
        ('已有首页原型展示自然语言和手动输入入口。复合任务的目标界面应分别标明待确认记录与建议候选。',
         '首页设计稿展示自然语言和手动输入入口。复合任务分别标明待确认记录与建议候选。'),
        ('原型中的旧卡片名称保留在图片里，目标界面按此更新。', ''),
        ('六张图片对应当前原型。', '六张图片为网页端目标界面设计稿。'),
    ]:
        assert source.count(old) == 1
        source = source.replace(old, new, 1)
    (OUT / 'DietLens_设计报告排版正文.md').write_text(source, encoding='utf-8')
document = json.loads(pandoc(source, '-f',
    'markdown-smart+tex_math_single_backslash', '-t', 'json'))
images = 0
diagrams = 0
for block in document['blocks']:
    if block['t'] != 'CodeBlock' or 'mermaid' not in block['c'][0][1]:
        continue
    diagrams += 1
    model = MODELS / f'模型{diagrams:02}.mmd'
    assert model.read_text(encoding='utf-8').rstrip('\n') == block['c'][1].rstrip('\n')
    diagram = model.with_suffix('.svg').read_text(encoding='utf-8')
    # Chromium 本地打印可直接读取矢量图，文件名保留中文。
    name = f'图源{diagrams:02}.svg'
    (OUT / name).write_text(diagram, encoding='utf-8')
    block.update(t='RawBlock', c=['html', f'<figure class="model model-{diagrams}"><img src="{name}"></figure>'])

body = pandoc(json.dumps(document, ensure_ascii=False), '-f', 'json', '-t', 'html5',
              '--wrap=none', '--mathml', '--no-highlight')
for first_cell, table_class in [('优先级', 'risks'), ('成员', 'team')]:
    pattern = rf'<table>(?:\s*<colgroup>(?:(?!</colgroup>).)*</colgroup>)?(\s*<thead>\s*<tr>\s*<th>{first_cell}</th>)'
    body, count = re.subn(pattern, rf'<table class="{table_class}">\1', body, flags=re.S)
    assert count == 1
image_dir = OUT / 'images' if replace_ui else SOURCE.parent / 'images'
for image in sorted(image_dir.glob('*.png')):
    relative = f'images/{image.name}'
    if f'src="{relative}"' in body:
        target = OUT / relative
        target.parent.mkdir(exist_ok=True)
        if not replace_ui:
            shutil.copy2(image, target)
        images += 1
assert diagrams == 8 and images == 6

css = '''
@page{size:A4;margin:16mm 17mm 17mm;@bottom-center{content:counter(page);font:9pt SimSun}}
@page:first{@bottom-center{content:none}}
*{box-sizing:border-box}
body{margin:0;background:white;color:black;font:10.5pt/1.55 SimSun,'宋体',serif}
body>h1:first-child{font-size:33pt;margin:64mm 0 0;padding:10mm 0;border-top:1pt solid black;border-bottom:.5pt solid black;break-after:page}
h2,h3,h4{margin:12pt 0 6pt;break-after:avoid;line-height:1.4}
h2{font-size:16pt}h3{font-size:12.5pt}h4{font-size:11.3pt}
p{margin:0 0 6pt;orphans:2;widows:2;overflow-wrap:anywhere}
a{color:inherit;text-decoration:none;overflow-wrap:anywhere}
ol,ul{margin-top:3pt;margin-bottom:7pt;padding-left:2em}
li p{margin-bottom:3pt}
table{width:100%;border-collapse:collapse;font-size:9.4pt;line-height:1.4;margin:6pt 0 9pt;overflow-wrap:anywhere}
thead{display:table-header-group}tr{break-inside:avoid}
th,td{border:.4pt solid #555;padding:3pt 4pt;vertical-align:top}th{text-align:left}
.risks{table-layout:fixed}.risks th:nth-child(1){width:7%}.risks th:nth-child(2){width:18%}
.risks th:nth-child(3){width:15%}.risks th:nth-child(4){width:40%}.risks th:nth-child(5){width:20%}
.team{break-inside:avoid}
figure{margin:7pt 0 9pt;text-align:center;break-inside:avoid}
img{max-width:100%;max-height:174mm;object-fit:contain;print-color-adjust:exact}
figure img[src^="images/"]{max-height:112mm}
figure.model img{max-height:188mm}
figure.model-4 img{max-height:151mm}
figcaption{font-size:9pt;margin-top:3pt}
pre{font:8.3pt/1.38 Consolas,'Microsoft YaHei',monospace;white-space:pre-wrap;overflow-wrap:anywhere;border-left:.6pt solid #777;padding:3pt 0 3pt 7pt;margin:5pt 0 8pt;orphans:3;widows:3}
code{font-family:Consolas,'Microsoft YaHei',monospace;font-size:.94em;overflow-wrap:anywhere}
pre code{font-size:inherit}
math{max-width:100%;font-size:9.5pt}
'''
preview = OUT / '原文排版.html'
preview.write_text(f'<!doctype html><html lang="zh-CN"><meta charset="utf-8"><title>DietLens 系统设计报告</title><style>{css}</style><body>{body}</body></html>', encoding='utf-8')
assert SOURCE.read_bytes() == original
image_label = '新版界面图' if replace_ui else '原稿配图'
print(f'已完成排版：{diagrams} 张模型，{images} 张{image_label}，原稿校验值 {hashlib.sha256(original).hexdigest()}。')
