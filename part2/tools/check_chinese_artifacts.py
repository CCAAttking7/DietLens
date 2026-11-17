"""检查已编写成果的中文显示、图稿完整性及引用，保留必要技术标识。"""
from pathlib import Path
import hashlib
import json
import re
import xml.etree.ElementTree as ET
from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
ALLOWED = {'React','TypeScript','FastAPI','HTTP','HTTPS','api','API','SQLite','WAL',
           'Vite','Supabase','Auth','Postgres','DietLens','main','UC','PostgreSQL',
           'Python','Node','js','Windows','Linux'}
svgs = [*(ROOT/'diagrams/rendered').glob('M*.svg'),
        *(ROOT/'docs/design/diagrams/rendered').glob('D*.svg'),*(ROOT/'ui').glob('U*.svg'),
        *(ROOT/'docs/design/diagrams/architecture/rendered').glob('[AS]*.svg'),
        *(ROOT/'docs/design/diagrams/database/rendered').glob('E*.svg'),
        *(ROOT/'final/figures').glob('F*.svg')]
assert len(svgs) == 43
text_count = 0
for path in svgs:
    labels = [''.join(n.itertext()) for n in ET.parse(path).getroot().iter() if n.tag.endswith('text')]
    for label in labels:
        text_count += 1
        for token in re.findall(r'\b[A-Za-z][A-Za-z0-9_]*\b', label):
            assert token in ALLOWED or len(token) == 1 or re.fullmatch(r'[A-Za-z]{1,4}\d[A-Za-z0-9]*',token), (path.name,token,label)
    with Image.open(path.with_suffix('.png')) as im:
        im.verify()

manifest = json.loads((ROOT/'docs/design/diagrams/render-manifest.json').read_text(encoding='utf-8'))
for row in manifest['records']:
    assert hashlib.sha256((ROOT/row['source']).read_bytes()).hexdigest() == row['source_sha256']
    assert (ROOT/row['output']).stat().st_size == row['bytes']

architecture = json.loads((ROOT/'docs/design/diagrams/architecture/build-manifest.json').read_text(encoding='utf-8'))
assert architecture['共享模型未改变']
assert all(r['退出码'] == 0 for r in architecture['运行记录'])
assert architecture['模型源摘要'] == hashlib.sha256((ROOT/'docs/design/diagrams/architecture/workspace.dsl').read_bytes()).hexdigest()
for row in architecture['渲染记录']:
    assert hashlib.sha256((ROOT/row['源文件']).read_bytes()).hexdigest() == row['源摘要']
    assert hashlib.sha256((ROOT/row['产物']).read_bytes()).hexdigest() == row['产物摘要']

database = json.loads((ROOT/'database/validation.json').read_text(encoding='utf-8'))
for row in database['渲染记录']:
    assert hashlib.sha256((ROOT/row['源文件']).read_bytes()).hexdigest() == row['源摘要']
    assert hashlib.sha256((ROOT/row['产物']).read_bytes()).hexdigest() == row['产物摘要']
for name, digest in database['文件摘要'].items():
    assert hashlib.sha256((ROOT/'database'/name).read_bytes()).hexdigest() == digest

api = json.loads((ROOT/'api/validation.json').read_text(encoding='utf-8'))
assert api['规范校验'] == '通过'
for name, digest in api['文件摘要'].items():
    assert hashlib.sha256((ROOT/'api'/name).read_bytes()).hexdigest() == digest
api_tool = json.loads((ROOT/'api/tool-record.json').read_text(encoding='utf-8'))
for name, digest in api_tool['产物摘要'].items():
    assert hashlib.sha256((ROOT/'api'/name).read_bytes()).hexdigest() == digest
with Image.open(ROOT/'api/接口契约编辑器.jpg') as im:
    im.verify()

docs = [p for p in ROOT.rglob('*.md') if not any(part in ['.agents','.specify','.dependencies'] for part in p.relative_to(ROOT).parts)]
links = 0
for path in docs:
    content = path.read_text(encoding='utf-8')
    assert not re.search(r'^#{1,6} .*\b(?:Feature Specification|User Story|Requirements|Assumptions|Success Criteria)\b',content,re.M),path
    assert '提供满足原文字数要求的英文内容' not in content,path
    for target in re.findall(r'\]\(([^)]+)\)',content):
        if re.match(r'^(?:[a-zA-Z][\w+.-]*:|#|/)',target):
            continue
        assert (path.parent/target.split('#')[0]).exists(), (path.name,target)
        links += 1

spec = (ROOT/'specs/001-dietlens-design/spec.md').read_text(encoding='utf-8')
assert len(re.findall(r'^### 用户故事 \d',spec,re.M)) == 6
assert len(re.findall(r'^### FR-\d{3} ',spec,re.M)) == 20
assert len(re.findall(r'^\| NFR-\d{3} ',spec,re.M)) == 26
checklist = (ROOT/'specs/001-dietlens-design/checklists/requirements.md').read_text(encoding='utf-8')
assert len(re.findall(r'^- \[x\]',checklist,re.M)) == 16

report = {'日期':'2026-11-17','范围':'本次编写的文档和图稿；来源材料和工具原文件保留',
          '语言':'中文，必要技术标识保留','检查文档数':len(docs),'检查图稿数':len(svgs),
          '图稿文字节点数':text_count,'中文领域图':4,'中文旧版设计图':10,'中文界面稿':8,'中文架构及交互图':8,'中文数据库图':5,'报告精简图':8,
          '源文件与渲染记录一致':True,'本地链接数':links,'需求编号与六故事完整':True,
          '阶段状态':'按原作业九项要求完成中文提交整合版','接口规范检查':'通过','接口操作数':api['HTTP操作数']}
(ROOT/'docs/design/language-validation.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
print(json.dumps(report,ensure_ascii=False,indent=2))
