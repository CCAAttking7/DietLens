"""校验并导出本项目架构；不改共享模型，不创建业务数据库。"""
from pathlib import Path
import base64
import hashlib
import json
import shutil
import subprocess
import urllib.request
import xml.etree.ElementTree as ET
import zlib
from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / 'docs/design/diagrams/architecture'
SHARED = Path('D:/Projects/software-design-workbench/tools/structurizr')
DOCKER = shutil.which('docker') or 'D:/Tools/Docker/resources/bin/docker.exe'
IMAGE = 'structurizr/structurizr:latest'
MOUNT = f'type=bind,source={SOURCE},target=/workspace'
TARGET = SOURCE / 'rendered'
TARGET.mkdir(exist_ok=True)
DERIVED = SOURCE / 'chinese-puml'
DERIVED.mkdir(exist_ok=True)

def digest(p):
    return hashlib.sha256(p.read_bytes()).hexdigest()

def shared_hashes():
    return {p.name: digest(p) for p in SHARED.glob('workspace.*') if p.is_file()}

before = shared_hashes()
runs = []
def cli(args):
    result = subprocess.run([DOCKER, 'run', '--rm', '--mount', MOUNT, IMAGE, *args],
                            capture_output=True, text=True, encoding='utf-8', errors='replace')
    runs.append({'命令': args, '退出码': result.returncode, '工具输出': result.stdout.strip()})
    if result.returncode:
        raise RuntimeError(result.stderr + result.stdout)

cli(['validate', '-workspace', '/workspace/workspace.dsl'])
for fmt, name in [('plantuml', 'puml'), ('mermaid', 'mermaid'), ('json', 'json')]:
    cli(['export', '-workspace', '/workspace/workspace.dsl', '-format', fmt,
         '-output', '/workspace/exported-' + name])

identity = subprocess.run([DOCKER, 'image', 'inspect', IMAGE, '--format', '{{.Id}}'],
                          capture_output=True, text=True, check=True).stdout.strip()
transform = bytes.maketrans(b'ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789+/',
                          b'0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz-_')
def encode(value):
    compressor = zlib.compressobj(level=9, wbits=-15)
    raw = compressor.compress(value.encode('utf-8')) + compressor.flush()
    return base64.b64encode(raw).translate(transform).rstrip(b'=').decode('ascii')

sources = []
for p in sorted((SOURCE/'exported-puml').glob('structurizr-A*.puml')):
    if p.stem.endswith('-key'):
        continue
    text = p.read_text(encoding='utf-8')
    text = text.replace('@startuml', '@startuml\nskinparam defaultFontName Noto Sans CJK SC', 1)
    out = DERIVED / p.name.removeprefix('structurizr-')
    out.write_text(text, encoding='utf-8')
    sources.append(out)
sources.extend(sorted(SOURCE.glob('S*.puml')))
assert len(sources) == 8
records = []
for p in sources:
    value = p.read_text(encoding='utf-8')
    for fmt in ('svg', 'png'):
        with urllib.request.urlopen(f'http://localhost:8082/{fmt}/{encode(value)}', timeout=60) as response:
            body = response.read()
            assert response.status == 200
        if fmt == 'svg':
            xml = ET.fromstring(body)
            labels = ''.join(xml.itertext())
            assert xml.tag.endswith('svg') and 'Syntax Error' not in labels and 'Error line' not in labels
        else:
            assert body.startswith(b'\x89PNG\r\n\x1a\n')
        out = TARGET/(p.stem+'.'+fmt)
        out.write_bytes(body)
        records.append({'源文件':str(p.relative_to(ROOT)).replace('\\','/'), '源摘要':digest(p),
                        '产物':str(out.relative_to(ROOT)).replace('\\','/'),
                        '产物摘要':digest(out), '响应状态':200, '字节数':len(body)})

workspace = json.loads((SOURCE/'exported-json/workspace.json').read_text(encoding='utf-8'))
views = workspace['views']
assert sum(len(views.get(k, [])) for k in ['systemContextViews','containerViews','componentViews','deploymentViews']) == 5
system = next(s for s in workspace['model']['softwareSystems'] if s['name']=='DietLens饮食工作台')
api = next(c for c in system['containers'] if c['name']=='后端应用')
assert len(api['components']) == 11
after = shared_hashes()
assert before == after

font = ImageFont.truetype('C:/Windows/Fonts/msyh.ttc', 23)
sheet = Image.new('RGB', (1600, 4*620), '#fcfbf7')
draw = ImageDraw.Draw(sheet)
titles = ['系统上下文','运行单元','后端模块','本地演示部署','目标托管部署',
          '行动采纳与反馈','计划准备与实际用餐','原子提交与恢复']
for n, p in enumerate(sources):
    png = TARGET/(p.stem+'.png')
    with Image.open(png) as original:
        im = original.convert('RGB')
        im.thumbnail((770, 555))
        x, y = (n%2)*800, (n//2)*620
        draw.text((x+20,y+10), p.stem.split('-')[0]+' '+titles[n], font=font, fill='#24231f')
        sheet.paste(im,(x+(800-im.width)//2,y+55+(555-im.height)//2))
sheet.save(TARGET/'架构图预览.png')
manifest = {'日期':'2026-11-17','阶段':'P3候选，待确认','工具镜像':IMAGE,'镜像标识':identity,
            '模型源摘要':digest(SOURCE/'workspace.dsl'),'运行记录':runs,'检查视图数':5,
            '后端模块数':11,'时序图数':3,'共享模型摘要之前':before,'共享模型摘要之后':after,
            '共享模型未改变':before==after,'范围':'设计模型校验与渲染，未验证产品性能或执行业务部署',
            '渲染记录':records}
(SOURCE/'build-manifest.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2),encoding='utf-8')
print('架构校验通过：五个C4视图、三个时序图、十一个后端模块；共享模型未改变。')
