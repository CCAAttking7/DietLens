"""对数据库设计做静态核对和ER渲染；禁止执行SQL或连接数据库。"""
from pathlib import Path
import hashlib
import html
import json
import shutil
import subprocess
import sys
import xml.etree.ElementTree as ET
from collections import Counter
from PIL import Image, ImageDraw, ImageFont

ROOT=Path(__file__).resolve().parents[1]
DB=ROOT/'database'
sys.path.insert(0,str(ROOT/'tools/.dependencies'))
from pglast import parse_sql
import pglast
import sqlglot
from sqlglot import expressions as exp

tables=json.loads((DB/'model.json').read_text(encoding='utf-8'))['tables']
by_name={x['name']:x for x in tables}
assert len(by_name)==len(tables)==45
for row in tables:
    columns={c['name']:c for c in row['columns']}
    assert len(columns)==len(row['columns'])
    assert len({c['label'] for c in row['columns']})==len(columns)
    assert set(row['pk'])<=columns.keys()
    assert all(not columns[c]['nullable'] for c in row['pk'])
    for f in row['fks']:
        parent=by_name[f['target']];pc={c['name']:c for c in parent['columns']}
        assert set(f['columns'])<=columns.keys() and set(f['target_columns'])<=pc.keys()
        assert f['columns'][0]=='user_id' and f['target_columns'][0]=='user_id'
        assert f['target_columns'] in [parent['pk']]+parent['unique']
        assert len(f['columns'])==len(f['target_columns'])
        assert all(columns[a]['kind']==pc[b]['kind'] for a,b in zip(f['columns'],f['target_columns']))
        supported=[row['pk']]+row['unique']+[x['columns'] for x in row['indexes'] if not x.get('where')]
        assert any(x[:len(f['columns'])]==f['columns'] for x in supported)

parsers=[]
for name in ['schema.sql','schema.diagram.sql','drawdb-export-reference.sql']:
    ast=parse_sql((DB/name).read_text(encoding='utf-8'))
    count=sum(type(stmt.stmt).__name__=='CreateStmt' for stmt in ast)
    assert count==45,(name,count)
    parsers.append({'文件':name,'解析器':'pglast '+pglast.__version__,'语句数':len(ast),'建表声明数':count,'结论':'语法解析通过；未执行'})
ast=sqlglot.parse((DB/'schema.sqlite.sql').read_text(encoding='utf-8'),read='sqlite',error_level='raise')
assert not any(isinstance(s,exp.Command) for s in ast), '存在未解析的通用命令'
assert sum(isinstance(s,exp.Create) and s.kind=='TABLE' for s in ast)==45
parsers.append({'文件':'schema.sqlite.sql','解析器':'SQLGlot '+sqlglot.__version__,
                '语句数':len(ast),'建表声明数':45,'结论':'静态语法解析通过；不是SQLite引擎验收'})

# 将工具导出的复合关系与源模型逐列比对。
draw=json.loads((DB/'drawdb-model.json').read_text(encoding='utf-8'))
assert len(draw['tables'])==45
dt={t['id']:t for t in draw['tables']}
expected=Counter()
for row in tables:
    labels={c['name']:c['label'] for c in row['columns']}
    match=next(t for t in draw['tables'] if t['name']==row['label'])
    assert Counter(f['name'] for f in match['fields'])==Counter(labels.values())
    assert {f['name'] for f in match['fields'] if f['primary']}=={labels[n] for n in row['pk']}
    for fk in row['fks']:
        parent=by_name[fk['target']];pc={c['name']:c['label'] for c in parent['columns']}
        expected[(row['label'],tuple(labels[n] for n in fk['columns']),parent['label'],tuple(pc[n] for n in fk['target_columns']))]+=1
actual=Counter()
for r in draw['relationships']:
    start,end=dt[r['startTableId']],dt[r['endTableId']]
    sf={f['id']:f['name'] for f in start['fields']};ef={f['id']:f['name'] for f in end['fields']}
    fields=r.get('fields') or [r]
    actual[(start['name'],tuple(sf[f['startFieldId']] for f in fields),end['name'],tuple(ef[f['endFieldId']] for f in fields))]+=1
assert actual==expected

target=ROOT/'docs/design/diagrams/database'
rendered=target/'rendered'
rendered.mkdir(parents=True,exist_ok=True)
dot=shutil.which('dot') or 'C:/Program Files/Graphviz/bin/dot.exe'
groups=list(dict.fromkeys(t['group'] for t in tables))
records=[]
for number,group in enumerate(groups,1):
    selected=[t for t in tables if t['group']==group];names={t['name'] for t in selected}
    lines=['digraph G {','graph [rankdir=TB, bgcolor="#fcfbf7", nodesep=0.5, ranksep=0.7, pad=0.35, fontname="Microsoft YaHei"];',
           'node [shape=plain, fontname="Microsoft YaHei"];','edge [fontname="Microsoft YaHei", fontsize=11, color="#678374"];',
           f'label="E0{number} {group}：物理表关系\n各表均含所属用户；箭头由外键指向目标键，可空与唯一性见字典"; labelloc=t; fontsize=19;']
    for row in selected:
        key=set(row['pk'])|{n for f in row['fks'] for n in f['columns']}
        shown=[c for c in row['columns'] if c['name']!='user_id' and (c['name'] in key or c['name'] not in ['created_at','retain_until','renewed_at'])]
        body=''
        for c in shown:
            suffix=('主键 ' if c['name'] in row['pk'] else '')+('外键 ' if any(c['name'] in f['columns'] for f in row['fks']) else '')+('可空' if c['nullable'] else '')
            body+=f'<TR><TD ALIGN="LEFT">{html.escape(c["label"])}</TD><TD ALIGN="LEFT"><FONT COLOR="#657269">{suffix or "&#160;"}</FONT></TD></TR>'
        label='<TABLE BORDER="0" CELLBORDER="1" CELLSPACING="0" CELLPADDING="6"><TR><TD COLSPAN="2" BGCOLOR="#dce9df"><B>'+row['label']+'</B></TD></TR>'+body+'</TABLE>'
        lines.append(row['name']+' [label=<'+label+'>];')
    for row in selected:
        for f in row['fks']:
            if f['target'] in names:
                nullable=any(next(c for c in row['columns'] if c['name']==n)['nullable'] for n in f['columns'])
                label='可空引用' if nullable else '引用'
                if f['late']:label='当前版本引用'
                lines.append(row['name']+' -> '+f['target']+' [label="'+label+'", arrowhead=vee];')
    lines.append('}')
    source=target/f'E0{number}.dot';source.write_text('\n'.join(lines),encoding='utf-8')
    for fmt in ['svg','png']:
        output=rendered/f'E0{number}.{fmt}'
        subprocess.run([dot,'-T'+fmt,str(source),'-o',str(output)],capture_output=True,check=True)
        if fmt=='svg':assert ET.parse(output).getroot().tag.endswith('svg')
        else:
            with Image.open(output) as im:im.verify()
        records.append({'源文件':str(source.relative_to(ROOT)).replace('\\','/'),'源摘要':hashlib.sha256(source.read_bytes()).hexdigest(),
                        '产物':str(output.relative_to(ROOT)).replace('\\','/'),'产物摘要':hashlib.sha256(output.read_bytes()).hexdigest()})

sheet=Image.new('RGB',(1800,3*660),'#fcfbf7');d=ImageDraw.Draw(sheet);font=ImageFont.truetype('C:/Windows/Fonts/msyh.ttc',25)
for n,group in enumerate(groups):
    with Image.open(rendered/f'E0{n+1}.png') as src:
        im=src.convert('RGB');im.thumbnail((870,590));x=(n%2)*900;y=(n//2)*660
        d.text((x+20,y+12),f'E0{n+1} '+group,font=font,fill='#24231f');sheet.paste(im,(x+(900-im.width)//2,y+60+(590-im.height)//2))
sheet.save(rendered/'数据库图预览.png')
report={'日期':'2026-11-17','阶段':'P4数据库设计候选，待确认','设计表数':len(tables),
        '字段数':sum(len(t['columns']) for t in tables),'外键数':sum(len(t['fks']) for t in tables),
        '外键目标与类型及索引静态检查':'通过','所有私有外键包含用户归属':True,
        '工具导出表字段主键及复合关系与源模型一致':True,'工具提示':'存在身份与当前版本指针引起的循环依赖；以显式延迟外键及同事务写入处理，不声称工具问题为零',
        '解析记录':parsers,'中文分区ER图数':5,'渲染记录':records,
        '文件摘要':{p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in DB.iterdir() if p.is_file() and p.suffix in ['.sql','.json'] and p.name!='validation.json'},
        '未执行内容':'未连接或创建业务数据库，未执行SQL、迁移、产品验收或容量测量'}
(DB/'validation.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
print(f'数据库设计静态核对通过：{len(tables)}张表、{report["字段数"]}个字段、{report["外键数"]}个外键、5张中文ER图；未执行SQL。')
