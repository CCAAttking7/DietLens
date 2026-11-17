"""仅去除已选报告的封面版本标识，并整理与该报告对应的提交材料。"""
from pathlib import Path
import re,json,hashlib,zipfile,shutil
import pymupdf
ROOT=Path(__file__).resolve().parents[1]
SRC=ROOT/'DietLens_系统设计报告_UI重设计版.pdf'
DEST=ROOT/'DietLens_系统设计报告_最终提交版.pdf'
OUT=ROOT/'final/最终提交';OUT.mkdir(exist_ok=True)
doc=pymupdf.open(SRC);page=doc[0];hits=page.search_for('网页端界面重设计版')
assert len(hits)==1
rect=hits[0]
for sep in page.search_for('｜'):
 if abs(sep.y0-rect.y0)<3 and 0<=rect.x0-sep.x1<18:rect=rect|sep
page.add_redact_annot(rect,fill=False,cross_out=False)
page.apply_redactions(images=0,graphics=0,text=0)
doc.save(DEST,garbage=4,deflate=True);doc.close()
original=pymupdf.open(SRC);final=pymupdf.open(DEST)
assert len(original)==len(final)==33
assert '网页端界面重设计版' not in final[0].get_text()
assert '基于Web Agent的个人饮食管理与微习惯干预系统' in final[0].get_text()
for i in range(1,len(original)):
 assert original[i].get_text()==final[i].get_text(),i
 assert original[i].get_pixmap().samples==final[i].get_pixmap().samples,i
final[0].get_pixmap(matrix=pymupdf.Matrix(1.5,1.5)).save(OUT/'最终封面.png')
original.close();final.close()
# 保留现有相对目录，使正文、网页和配套图片在解压后仍可打开。
base=OUT/'可编辑材料/part2'
source_dir=ROOT/'final/UI重设计版'
dest_dir=base/'final/UI重设计版';dest_dir.mkdir(parents=True,exist_ok=True)
md=(source_dir/'DietLens_系统设计报告_UI重设计版.md').read_text(encoding='utf-8')
html=(source_dir/'DietLens_系统设计报告_UI重设计版.html').read_text(encoding='utf-8')
html=html.replace('　｜　网页端界面重设计版','').replace('（网页端界面重设计版）','')
assert '网页端界面重设计版</div>' not in html
(dest_dir/'DietLens_系统设计报告_最终版.md').write_text(md,encoding='utf-8')
(dest_dir/'DietLens_系统设计报告_最终版.html').write_text(html,encoding='utf-8')
paths=re.findall(r'src=["\x27]([^"\x27]+)',html)+re.findall(r'!\[[^\]]*\]\(([^)]+)\)',md)
for ref in set(paths):
 if re.match(r'^(https?:|data:)',ref):continue
 src=(source_dir/ref).resolve();assert src.is_file(),str(src)
 rel=src.relative_to(ROOT);dst=base/rel;dst.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(src,dst)
 # 模型图的编辑来源随相同路径保留。
 for ext in ['.svg','.puml','.dsl']:
  edit=src.with_suffix(ext)
  if edit.is_file():shutil.copy2(edit,dst.with_suffix(ext))
shutil.copytree(ROOT/'ui_v2',base/'ui_v2',dirs_exist_ok=True)
readme='''# DietLens 第二次作业最终提交材料

主文件：DietLens_系统设计报告_最终提交版.pdf，共33页。

本次以用户选定的UI重设计版为最终依据，仅删除封面副标题末尾的版本标识，正文及其余页面保持原样。

“可编辑材料/part2/final/UI重设计版”含对应Markdown与HTML正文；“可编辑材料/part2/ui_v2”含网页端界面源稿、设计系统、流程、PNG及对比度记录。其余图表按正文引用的相对目录保留。解压整个压缩包后再打开HTML，以便正确加载图片。

提交时以主PDF为阅读入口。压缩包不包含其他旧版报告、对比审阅、缓存或工具依赖。
'''
(OUT/'阅读说明.md').write_text(readme,encoding='utf-8')
record={'原报告':SRC.name,'最终报告':DEST.name,'页数':33,'修改范围':'仅移除封面版本标识及其分隔符','正文验证':'第2至33页文字及逐页渲染像素与原报告完全一致','最终PDF摘要':hashlib.sha256(DEST.read_bytes()).hexdigest(),'相对图片引用':len(set(paths))}
(OUT/'交付检查.json').write_text(json.dumps(record,ensure_ascii=False,indent=2),encoding='utf-8')
zpath=ROOT/'DietLens_第二次作业_最终提交材料.zip'
with zipfile.ZipFile(zpath,'w',zipfile.ZIP_DEFLATED) as z:
 z.write(DEST,DEST.name)
 for f in OUT.rglob('*'):
  if f.is_file() and f.name!='最终封面.png':z.write(f,f.relative_to(OUT).as_posix())
with zipfile.ZipFile(zpath) as z:assert z.testzip() is None;record['压缩包文件数']=len(z.namelist())
(ROOT/'提交说明.md').write_text('# 最终提交入口\n\n[最终报告](DietLens_系统设计报告_最终提交版.pdf)\n\n[最终提交压缩包](DietLens_第二次作业_最终提交材料.zip)\n\n以用户选定的UI重设计版为准，仅去除封面版本标识；此前报告留作历史，不放入提交压缩包。\n',encoding='utf-8')
with (ROOT/'WORKLOG.md').open('a',encoding='utf-8') as f:f.write('\n\n## 最终版本锁定\n\n按用户指定，以UI重设计版为最终报告，仅去除封面版本标识。保留33页及全部正文，逐页像素核对第2至33页完全一致。最终压缩包包含主PDF、对应正文与图稿，剔除旧版和中间产物。\n')
print(json.dumps(record,ensure_ascii=False))
