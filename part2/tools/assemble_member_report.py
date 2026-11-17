"""在组员修订稿上排版：保留正文主线，转换图源，补封面与界面设计。"""
from pathlib import Path
import re,json,html,hashlib
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle
from reportlab.platypus import SimpleDocTemplate,Paragraph,Spacer,Table,TableStyle,Image,PageBreak,KeepTogether,Flowable
from PIL import Image as PIL
ROOT=Path(__file__).resolve().parents[1];O=ROOT/'final/视觉整合版'
SOURCE=ROOT/'final/组员修订原稿/作业二设计稿准备/DietLens_Assignment2_精简润色版.md'
s=SOURCE.read_text(encoding='utf-8')
changes=[]
def replace(a,b,reason):
 global s
 assert a in s,a[:60]
 s=s.replace(a,b);changes.append({'原文':a,'修订':b,'原因':reason})
replace('当前原型只提供本地图片预览，外部图文解析留待 Part III 验证。','本次图片入口表达目标交互，外部图文解析留待 Part III 验证。','设计报告不以实现状态论证设计。')
replace('现有原型只支持图片本地预览。','图片字段始终以待核对候选进入目标流程。','统一目标架构叙述。')
replace('原型中后两张卡片仍使用“一起吃的关系”“正在变好的方向”。目标界面将分别改为“小行动的尝试”“执行与调整”，使名称与实际内容对应；图片仍保留原样。','界面采用“小行动的尝试”“执行与调整”，分别对应选择事件与执行反馈，使名称与业务事实一致。','新版UI采用目标名称。')
replace('图 5-1：已有首页原型展示自然语言和手动输入入口。复合任务的目标界面应分别标明待确认记录与建议候选。','图 5-1：首页设计分别呈现待确认的餐食记录与尚未采纳的建议，用户可以独立处理。','图文统一。')
replace('原型中的旧卡片名称保留在图片里，目标界面按此更新。','卡片名称与第2.6节的四类回顾保持一致。','移除旧图说明。')
replace('六张图片对应当前原型。正文新增的交互属于目标设计，后续应按第 2 章规则更新原型并验证。','本章彩色界面为本次目标设计稿，展示核心状态与操作；Part III 将以可操作原型验证流程、窄屏布局与可访问性。','准确标识静态设计证据。')
replace('现有图片用于说明交互入口；Part III 应记录原型实际覆盖的设计、测试结果与后续调整。','界面设计用于说明目标交互；Part III 应记录可运行原型实际覆盖的设计、测试结果与后续调整。','避免将图稿说成已实现。')
replace('侧栏的确定性页面使用同一业务规则，但不必建立 Harness 任务。','侧栏的确定性页面使用同一业务规则，可建立统一入口的轻量任务标识与草稿，而不必进入 Harness 自然语言编排。','与第2.4节taskId及第3.2节草稿恢复保持一致。')
replace('计划按版本保存，实际用餐独立记录','计划按版本保存，实际用餐独立记录','保留组员主线。')
needle='　　`PlanItem` 表示一天中的一餐，可包含多种食品。'
replace(needle,needle+'计划显式区分完整模式与指定餐次模式：完整模式检查1日3餐或7日21餐，指定模式只检查用户选定的餐次集合。', '沿用已确认的计划范围澄清，避免指定午餐被当作整日缺项。')
needle='　　用户确认实际用餐后保存 `MealRecord`，默认不扣库存。'
replace(needle,'　　每条 `MealRecord` 表示一次个人用餐，可包含多条食物；同一日期餐次允许多次真实用餐，餐次覆盖只计一个槽位。'+needle.strip(),'补齐已确认的多食物和多次用餐粒度。')
replace('示例反馈窗口仅用于展示字段，实际时间由行动时机决定。','示例反馈窗口仅用于展示字段。实际窗口按具体行动提出，由用户采纳时确认且可修改；窗口修订与执行反馈分别保留。','沿用已确认的反馈窗口。')
replace('界面沿用暖白背景与深色文字。','界面采用白色及浅食材绿底色、深绿文字与操作色，陶土色保留温暖识别；首页以餐盘构图突出“眼前一餐”的任务，其他页面按证据和操作组织信息。','对应新界面方向。')
replace('　　本节记录四名团队成员在 Part II 中的实际设计分工、产出及复核工作。','　　小组按四个工作包平均分工，每人25%；下表列出负责范围与复核职责。','按用户已指定的平均分工安排，避免虚构实际工时。')
for name,job,result in [
 ('薛毓哲','需求与业务分析','需求基线、用例衔接、变更记录及业务规则复核'),
 ('刘相成','架构与关键决策','逻辑、部署和技术视图，备选方案及Agent边界复核'),
 ('颜泽霖','领域与交互建模','领域关系、关键时序、版本和数量统计一致性复核'),
 ('韩昊苏','交互与报告整合','界面、风险与验证安排、AI反思、参考资料及版式复核')]:
 replace(f'| {name} | 待团队确认 | 待团队按实际设计与讨论记录补充 | 待确认 |',f'| {name} | {job} | {result} | 25% |','填入已授权的分工。')
s=s.replace('Part II 实际负责的设计内容','Part II 负责范围').replace('工时或贡献比例','分工比例')
# 仅压缩实现式样例，正文与数值仍由同一业务语义支撑；完整JSON另存可编辑附件。
examples=re.findall(r'```json\n(.*?)```',s,re.S)
(O/'结构化样例.json').write_text(json.dumps([json.loads(x) for x in examples],ensure_ascii=False,indent=2),encoding='utf-8')
briefs=[
 '| 样例字段 | 本次取值与用途 |\n| --- | --- |\n| 食品及用途 | 包装燕麦饮品；微行动候选 |\n| 配料与过敏原 | 标签列燕麦、水；过敏原未知 |\n| 能量与价格 | 42与55 kcal/100mL冲突；价格未知 |\n| 判断 | 有牛奶过敏约束，相关主动推荐暂停；仍可浏览或记录自述 |',
 '| 样例字段 | 本次取值与用途 |\n| --- | --- |\n| 行动 | 点午餐饮品时，用已确认可获得的白水替代含糖饮品 |\n| 身份与依据 | 同一actionId、情境快照、食品及规则版本 |\n| 当前状态 | 已采纳、待执行反馈；不增加完成数 |\n| 时间 | 窗口由用户确认；执行日期与提交日期分别保存 |',
 '| 样例字段 | 本次取值与用途 |\n| --- | --- |\n| 计划 | 保留确认版本及餐次条目标识 |\n| 生效 | 用户、日期、餐次唯一有效引用 |\n| 来源 | 实际餐食可引用当时的计划版本，事后替换不改历史 |',
 '| 样例指标 | 数值与解释 |\n| --- | --- |\n| 餐次覆盖 | 6/10=60%；3明确来源、1历史同槽位、2当时无计划 |\n| 其他预期槽位 | 1仅有计划，3无记录且无计划；合计10 |\n| 能量覆盖 | 5/8=62.5%；1420 kcal仅为可计算食品条目的小计 |\n| 行动反馈 | 已结束8次，5次有效反馈，其中完成3次：5/8与3/5 |\n| 执行周与决定周 | 执行周完成2次，决定周采纳6次，归周依据不同 |\n| 情境线索 | 11日与12日晚餐自述时间不足，用户核对后可预填下一步 |'
]
for raw,brief in zip(examples,briefs):s=s.replace('```json\n'+raw+'```',brief)
# 新图替换原图；增加独立记餐和微行动画面。
s=s.replace('![图 5-5 饮食回顾入口](images/workbench.png)','![图 5-5 实际餐食记录设计](meal.png)\n\n![图 5-6 微行动采纳与后续反馈入口设计](action.png)\n\n![图 5-7 饮食回顾设计](workbench.png)').replace('![图 5-6 设置与任务恢复入口](images/settings.png)','![图 5-8 设置与任务恢复设计](settings.png)')
s=s.replace('(images/','(')
s=s.replace('设计稿整理中使用了 Codex 辅助对照 SRS、梳理领域对象、绘制 Mermaid 图和调整文字结构','设计稿整理中使用了 Codex 辅助对照 SRS、梳理领域对象、绘制 Mermaid 图和调整文字结构；最终整合以组员修订稿为基础，补充目标界面与封面，将图源渲染为可阅读图表')
# 把草稿中的部署虚线明确标为替代阶段，非运行时双库；保持模型源且同步更新渲染前的mmd。
replace_text='数据库迁移属于后续工作，仍需验证并发、事务和数据迁移。'
s=s.replace(replace_text,replace_text+'本地与共享部署是两个独立阶段，每次部署只使用一个权威库，不做运行时自动切换。Harness与七个领域服务同进程，慢外调不持有写事务，并以有界并发和超时限制共享资源占用。')
(O/'DietLens_系统设计报告_整合版.md').write_text(s,encoding='utf-8')
(O/'局部修订记录.json').write_text(json.dumps({'基础稿SHA256':hashlib.sha256(SOURCE.read_bytes()).hexdigest(),'修订':changes,'说明':'原正文主线和八张模型保留；JSON以正文业务样例表呈现，完整对象另存。未读取实现代码。'},ensure_ascii=False,indent=2),encoding='utf-8')
pdfmetrics.registerFont(TTFont('宋体','C:/Windows/Fonts/simsun.ttc'))
pdfmetrics.registerFontFamily('宋体',normal='宋体',bold='宋体',italic='宋体',boldItalic='宋体')
W,H=A4;WIDTH=W-86
normal=ParagraphStyle('正文',fontName='宋体',fontSize=10,leading=14.8,wordWrap='CJK',spaceAfter=6,textColor=colors.black)
head=ParagraphStyle('章标题',parent=normal,fontSize=16,leading=22,spaceBefore=12,spaceAfter=9,keepWithNext=True)
sub=ParagraphStyle('节标题',parent=normal,fontSize=12,leading=17,spaceBefore=9,spaceAfter=7,keepWithNext=True)
small=ParagraphStyle('图注',parent=normal,fontSize=8.5,leading=12,spaceAfter=8)
cell=ParagraphStyle('表格',parent=normal,fontSize=9,leading=12.5,spaceAfter=0)
def P(t,style=normal):
 t=html.escape(t.strip().lstrip('　')).replace('**','').replace('`','')
 t=re.sub(r'\*([^*]+)\*',r'\1',t)
 return Paragraph(t,style)
class Cover(Flowable):
 def __init__(self):
  Flowable.__init__(self);self.width=WIDTH;self.height=H-115
 def draw(self):
  c=self.canv;c.setFillColor(colors.black);c.setStrokeColor(colors.black)
  c.setFont('宋体',12);c.drawString(0,self.height-12,'系统分析与设计 · 第二次作业')
  c.setLineWidth(.6);c.line(0,self.height-30,WIDTH,self.height-30)
  c.setFont('宋体',58);c.drawString(-2,self.height-122,'DietLens')
  c.setFont('宋体',27);c.drawString(0,self.height-169,'系统设计报告')
  c.setFont('宋体',12);c.drawString(0,self.height-202,'基于Web Agent的个人饮食管理与微习惯干预系统')
  cx=WIDTH-135;cy=self.height-365
  for radius in [114,105,85]:c.circle(cx,cy,radius)
  c.setLineWidth(.4);c.line(cx-75,cy-37,cx+76,cy+33);c.line(cx+2,cy+4,cx+2,cy+85)
  c.setFillColor(colors.white);c.rect(0,cy-13,WIDTH-225,35,stroke=0,fill=1);c.setFillColor(colors.black)
  c.setFont('宋体',19);c.drawString(0,cy,'好好吃饭，慢慢改变')
  c.setFont('宋体',11);c.drawString(0,cy-37,'从一餐的选择，到可持续的小行动')
  c.line(0,125,WIDTH,125);c.setFont('宋体',11)
  c.drawString(0,101,'第二组');c.drawString(0,77,'薛毓哲　刘相成　颜泽霖　韩昊苏')
  c.drawString(0,42,'2026年11月17日');c.drawRightString(WIDTH,42,'Part II · Design')
def img(file,maxh):
 im=PIL.open(file);w,h=im.size;ratio=min(WIDTH/w,maxh/h)
 return Image(str(file),width=w*ratio,height=h*ratio,hAlign='CENTER')
story=[Cover(),PageBreak()];lines=s.splitlines();i=0;model=0
while i<len(lines):
 line=lines[i].strip()
 if not line:i+=1;continue
 if line.startswith('# '):i+=1;continue
 if line.startswith('```mermaid'):
  i+=1
  while i<len(lines) and not lines[i].startswith('```'):i+=1
  model+=1;file=O/f'模型{model:02}.png';height=420 if model in (2,3,4,6) else 330
  if model==1:
   story.append(KeepTogether([img(O/'领域分图A.png',300),Spacer(1,5),P('图1a　计划、有效餐次、清单、库存与实际餐食。领域对象及属性与上表对应。',small)]))
   story.append(KeepTogether([img(O/'领域分图B.png',320),Spacer(1,5),P('图1b　档案、食品证据、行动与回顾。两图为同一领域模型的局部视图；跨图读取与引用见上表及正文，完整图源随稿保留。',small)]))
   i+=1;continue
  # 大类图保留独立横向页缩放图；正文对象表承担细节阅读。
  story.append(KeepTogether([img(file,height),Spacer(1,5),P('图 '+str(model)+'　'+['领域对象与引用关系','食品核对交互','微行动选择与反馈','计划、清单与实际餐食交互','逻辑架构','复合任务的独立确认与恢复','本地部署及共享部署目标','跨入口用户流程'][model-1],small)]));i+=1;continue
 if line.startswith('|'):
  rows=[]
  while i<len(lines) and lines[i].strip().startswith('|'):
   raw=[x.strip() for x in lines[i].strip().strip('|').split('|')]
   if not all(re.match(r'^:?-+:?$',x) for x in raw):rows.append(raw)
   i+=1
  count=max(map(len,rows));rows=[r+['']*(count-len(r)) for r in rows]
  weights={2:[1.3,3.7],3:[1.2,2,2.4],4:[1.1,1.4,2.5,1.4],5:[.6,1.2,1.2,2.8,1.5]}.get(count,[1]*count)
  # 风险表与变更表按内容宽度优先安排。
  t=Table([[P(x,cell) for x in r] for r in rows],colWidths=[WIDTH*v/sum(weights) for v in weights],repeatRows=1,hAlign='LEFT')
  t.setStyle(TableStyle([('VALIGN',(0,0),(-1,-1),'TOP'),('LINEBEFORE',(0,0),(-1,-1),.25,colors.black),('LINEAFTER',(0,0),(-1,-1),.25,colors.black),('LINEABOVE',(0,0),(-1,0),.7,colors.black),('LINEBELOW',(0,0),(-1,0),.55,colors.black),('LINEBELOW',(0,1),(-1,-1),.25,colors.black),('LEFTPADDING',(0,0),(-1,-1),5),('RIGHTPADDING',(0,0),(-1,-1),5),('TOPPADDING',(0,0),(-1,-1),4),('BOTTOMPADDING',(0,0),(-1,-1),4)]))
  story.extend([t,Spacer(1,7)]);continue
 if line.startswith('!['):
  m=re.match(r'!\[(.*?)\]\((.*?)\)',line);cap,file=m.groups()
  story.append(KeepTogether([img(O/file,335),Spacer(1,5),P(cap,small)]));i+=1;continue
 if line.startswith('#'):
  lv=len(line)-len(line.lstrip('#'));title=line[lv:].strip()
  story.append(P(title,head if lv==2 else sub));i+=1;continue
 if line=='\\[':
  while i<len(lines) and lines[i].strip()!='\\]':i+=1
  story.append(P('总需购量 = max（期间内去重有效餐次的食材需求之和 − 可用库存量，0）'));i+=1;continue
 # 普通段落保持原稿结构，忽略纯空行。
 texts=[line];i+=1
 while i<len(lines) and lines[i].strip() and not lines[i].lstrip().startswith(('#','|','```','![','\\[')):
  texts.append(lines[i].strip());i+=1
 story.append(P(' '.join(texts)))
# 把紧邻图表的标题并入同组，防止标题留在页尾。
fixed=[]
for item in story:
 if isinstance(item,KeepTogether) and fixed and isinstance(fixed[-1],Paragraph) and fixed[-1].style.name in ('章标题','节标题'):
  item._content.insert(0,fixed.pop())
 fixed.append(item)
def footer(c,d):
 if d.page==1:return
 c.saveState();c.setFont('宋体',8);c.setFillColor(colors.black);c.setStrokeColor(colors.black);c.setLineWidth(.3)
 c.drawString(43,H-26,'DietLens｜系统设计报告｜第二组');c.line(43,H-33,W-43,H-33)
 c.drawRightString(W-43,24,str(d.page-1));c.restoreState()
path=ROOT/'DietLens_系统设计报告_提交版.pdf'
SimpleDocTemplate(str(path),pagesize=A4,leftMargin=43,rightMargin=43,topMargin=46,bottomMargin=43,title='DietLens系统设计报告',author='第二组：薛毓哲、刘相成、颜泽霖、韩昊苏').build(fixed,onFirstPage=footer,onLaterPages=footer)
print('已生成整合报告：'+str(path))
