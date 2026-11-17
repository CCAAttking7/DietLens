"""使用本地PlantUML服务渲染中文领域图并保存检查记录。"""
from pathlib import Path
import base64
import hashlib
import json
import urllib.request
import xml.etree.ElementTree as ET
import zlib

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / 'docs/design/diagrams'
TARGET = SOURCE / 'rendered'
TARGET.mkdir(exist_ok=True)
ENDPOINT = 'http://localhost:8082'
TRANS = bytes.maketrans(b'ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789+/',
                       b'0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz-_')

def encode(text):
    compressor = zlib.compressobj(level=9, wbits=-15)
    data = compressor.compress(text.encode('utf-8')) + compressor.flush()
    return base64.b64encode(data).translate(TRANS).rstrip(b'=').decode('ascii')

records = []
for source in sorted(SOURCE.glob('D*.puml')):
    text = source.read_text(encoding='utf-8')
    token = encode(text)
    for fmt in ('svg', 'png'):
        with urllib.request.urlopen(f'{ENDPOINT}/{fmt}/{token}', timeout=30) as response:
            body = response.read()
            mime = response.headers.get('Content-Type', '')
            status = response.status
        if fmt == 'svg':
            xml = ET.fromstring(body)
            labels = ''.join(xml.itertext())
            if 'Syntax Error' in labels or 'Error line' in labels:
                raise ValueError(f'PlantUML returned an error diagram: {source.name}')
            assert xml.tag.endswith('svg'), source.name
        else:
            assert body.startswith(b'\x89PNG\r\n\x1a\n'), source.name
        output = TARGET / (source.stem + '.' + fmt)
        output.write_bytes(body)
        records.append({'source':str(source.relative_to(ROOT)).replace('\\','/'),
                        'source_sha256':hashlib.sha256(source.read_bytes()).hexdigest(),
                        'rendered_text_sha256':hashlib.sha256(text.encode('utf-8')).hexdigest(),
                        'output':str(output.relative_to(ROOT)).replace('\\','/'),
                        'format':fmt,'http_status':status,'content_type':mime,'bytes':len(body)})

manifest = {'tool':'本地 PlantUML 服务','endpoint':ENDPOINT,'date':'2026-11-17',
            'operation':'渲染中文领域候选模型，未修改共享工作区',
            'syntax_references':['https://plantuml.com/class-diagram','https://plantuml.com/text-encoding'],
            'records':records}
(SOURCE/'render-manifest.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2),encoding='utf-8')
print(f'本地 PlantUML 已渲染 {len(records)//2} 张中文领域图，SVG及PNG文件检查通过。')
