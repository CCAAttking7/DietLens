"""从共同正文内容生成可检索的中文PDF，不运行产品或数据库。"""
from pathlib import Path
import html,json
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.lib import colors
from reportlab.lib.enums import TA_LEFT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle
from reportlab.platypus import SimpleDocTemplate,Paragraph,Spacer,Table,TableStyle,Image,PageBreak,KeepTogether
from PIL import Image as PILImage

ROOT=Path(__file__).resolve().parents[1]
FINAL=ROOT/'final'
data=json.loads((FINAL/'report-content.json').read_text(encoding='utf-8'))
pdfmetrics.registerFont(TTFont('中文正文','C:/Windows/Fonts/msyh.ttc'))
pdfmetrics.registerFont(TTFont('中文标题','C:/Windows/Fonts/msyhbd.ttc'))
ink=colors.HexColor('#24231f');accent=colors.HexColor('#486958')
normal=ParagraphStyle('正文',fontName='中文正文',fontSize=10.1,leading=17,wordWrap='CJK',textColor=ink,spaceAfter=10)
heading=ParagraphStyle('页标题',parent=normal,fontName='中文标题',fontSize=18,leading=25,textColor=accent,spaceAfter=18)
sub=ParagraphStyle('小标题',parent=normal,fontName='中文标题',fontSize=12,leading=18,spaceBefore=5,spaceAfter=9)
cell=ParagraphStyle('表格',parent=normal,fontSize=9.3,leading=14,spaceAfter=0)
cap=ParagraphStyle('图注',parent=normal,fontSize=8.6,leading=13,textColor=colors.HexColor('#657269'),spaceAfter=10)
linkstyle=ParagraphStyle('来源',parent=cap,fontSize=8,leading=12,splitLongWords=True)
W,H=A4;WIDTH=W-88
def par(text,style=normal):return Paragraph(html.escape(text).replace('\n','<br/>'),style)
def image(path,maxheight,width=WIDTH):
    p=ROOT/path
    with PILImage.open(p) as im:w,h=im.size
    ratio=min(width/w,maxheight/h)
    result=Image(str(p),width=w*ratio,height=h*ratio)
    result.hAlign='CENTER'
    return result
story=[]
for n,pg in enumerate(data['pages']):
    if n:story.append(PageBreak())
    story.append(par(pg['title'],heading))
    for b in pg['blocks']:
        kind=b['kind']
        if kind=='p':story.append(par(b['text']))
        elif kind=='h':story.append(par(b['text'],sub))
        elif kind=='link':story.append(Paragraph('<link href="'+html.escape(b['url'],quote=True)+'" color="#486958">'+html.escape(b['text'])+'</link>',linkstyle))
        elif kind=='figure':story.append(KeepTogether([image(b['path'],b['height']),Spacer(1,7),par(b['caption'],cap)]))
        elif kind=='pair':
            imgs=[image(p,b['height'],(WIDTH-20)/2) for p in b['paths']]
            pair=Table([imgs],colWidths=[WIDTH/2]*2,hAlign='CENTER')
            pair.setStyle(TableStyle([('VALIGN',(0,0),(-1,-1),'TOP'),('LEFTPADDING',(0,0),(-1,-1),0),('RIGHTPADDING',(0,0),(-1,-1),0)]))
            story += [pair,Spacer(1,7),par(b['caption'],cap)]
        elif kind=='table':
            weights=b.get('widths') or [1]*len(b['heads']);total=sum(weights)
            cells=[[par(t,cell) for t in row] for row in [b['heads']]+b['rows']]
            t=Table(cells,colWidths=[WIDTH*x/total for x in weights],repeatRows=1,hAlign='LEFT')
            t.setStyle(TableStyle([('BACKGROUND',(0,0),(-1,0),colors.HexColor('#dce9df')),
                ('ROWBACKGROUNDS',(0,1),(-1,-1),[colors.white,colors.HexColor('#f8f9f6')]),
                ('GRID',(0,0),(-1,-1),.35,colors.HexColor('#cdd6ce')),('VALIGN',(0,0),(-1,-1),'TOP'),
                ('LEFTPADDING',(0,0),(-1,-1),7),('RIGHTPADDING',(0,0),(-1,-1),7),
                ('TOPPADDING',(0,0),(-1,-1),6),('BOTTOMPADDING',(0,0),(-1,-1),6)]))
            story.extend([t,Spacer(1,12)])
def footer(canvas,doc):
    canvas.saveState()
    canvas.setStrokeColor(colors.HexColor('#d9dfd8'));canvas.line(44,H-35,W-44,H-35)
    canvas.setFont('中文正文',8);canvas.setFillColor(colors.HexColor('#657269'))
    canvas.drawString(44,H-26,'DietLens｜系统分析与设计第二次作业｜中文整合版')
    canvas.drawRightString(W-44,25,'第 '+str(doc.page)+' 页')
    canvas.drawString(44,25,'2026-11-17 · 设计产物与验证计划')
    canvas.restoreState()
path=ROOT/'DietLens_Assignment2_Design.pdf'
doc=SimpleDocTemplate(str(path),pagesize=A4,rightMargin=44,leftMargin=44,topMargin=53,bottomMargin=47,
    title=data['title'],author='DietLens项目组',subject='第二次作业九项设计交付；中文版本')
doc.build(story,onFirstPage=footer,onLaterPages=footer)
print('已生成中文设计报告：'+str(path))
