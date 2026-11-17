"""生成中文静态界面设计稿的SVG和PNG，未运行产品。"""
from pathlib import Path
from html import escape
from PIL import Image, ImageDraw, ImageFont

OUT = Path(__file__).resolve().parents[1] / 'ui'
OUT.mkdir(exist_ok=True)
FONT = 'C:/Windows/Fonts/msyh.ttc'
BOLD = 'C:/Windows/Fonts/msyhbd.ttc'
BG, INK, MUTED, LINE, BRAND = '#f7f6f2', '#24231f', '#6f6b63', '#dfdbd2', '#b24e32'

class Frame:
    def __init__(self, name, title, subtitle, active, width=1100, height=820):
        self.name,self.w,self.h=name,width,height
        self.im=Image.new('RGB',(width,height),BG);self.d=ImageDraw.Draw(self.im)
        self.svg=[f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}">']
        self.rect(0,0,width,height,BG)
        if width>500:
            self.rect(0,0,172,height,'#ffffff',radius=0)
            self.text(22,30,'DietLens',25,True,BRAND)
            self.text(22,72,'好好吃饭，慢慢改变',12,color=MUTED)
            for i,s in enumerate(['今日饮食','饮食计划','食品资料','食材库存','餐食记录','阶段回顾','设置']):
                y=143+i*61
                if s==active:self.rect(12,y-10,158,y+36,'#f3e1d9')
                self.text(25,y,s,17,s==active,BRAND if s==active else MUTED)
            self.text(206,28,'第二次作业 / 目标设计稿',12,color=MUTED)
            self.text(206,66,title,29,True)
            self.text(206,111,subtitle,16,color=MUTED)
            self.text(206,784,'目标设计稿 · 示例数据 · 非实际运行截图',13,color=MUTED)
        else:
            self.text(20,20,'DietLens   /   餐食记录',18,True,BRAND)
            self.text(20,65,title,25,True)
            self.text(20,106,subtitle,14,color=MUTED)

    def rect(self,x1,y1,x2,y2,fill='#ffffff',stroke=None,radius=12):
        self.d.rounded_rectangle((x1,y1,x2,y2),radius,fill,outline=stroke)
        self.svg.append(f'<rect x="{x1}" y="{y1}" width="{x2-x1}" height="{y2-y1}" rx="{radius}" fill="{fill}" stroke="{stroke or fill}"/>')

    def text(self,x,y,text,size=17,bold=False,color=INK):
        font=ImageFont.truetype(BOLD if bold else FONT,size)
        box=self.d.textbbox((x,y),text,font=font,anchor='lt')
        assert box[2] <= self.w-8 and box[3] <= self.h-8,(self.name,text,box)
        self.d.text((x,y),text,font=font,fill=color,anchor='lt')
        self.svg.append(f'<text x="{x}" y="{y}" font-family="Microsoft YaHei,sans-serif" font-size="{size}" font-weight="{700 if bold else 400}" fill="{color}" dominant-baseline="text-before-edge">{escape(text)}</text>')

    def card(self,y,title,lines,height=190):
        self.rect(206,y,1060,y+height,stroke=LINE)
        self.text(230,y+22,title,20,True)
        for i,line in enumerate(lines):self.text(230,y+65+i*34,line,17,color=MUTED)

    def button(self,x,y,label,primary=True,width=190):
        self.rect(x,y,x+width,y+46,BRAND if primary else '#f1eee8')
        self.text(x+18,y+13,label,16,True,'#ffffff' if primary else INK)

    def save(self):
        self.svg.append('</svg>')
        (OUT/(self.name+'.svg')).write_text('\n'.join(self.svg),encoding='utf-8')
        self.im.save(OUT/(self.name+'.png'))

f=Frame('U01-food','先核对这一餐','当前任务：比较午餐选项 · 只核对影响选择的信息','食品资料')
f.card(158,'你的饮食边界',['花生过敏：已确认    ·    预算：每人每餐 30 元'],115)
f.rect(206,294,1060,580,'#fff7e6',LINE)
f.text(230,318,'番茄鸡蛋面    /    需要核对',22,True,'#9a6b1d')
for i,t in enumerate(['来源：用户提供的菜单文字 · 本次输入','已知：餐名、标价 18 元','待核对：酱料配料、花生及交叉接触标注','先补充关键配料，再继续这项餐食推荐。']):f.text(230,369+i*40,t,18)
f.button(230,610,'补充配料信息');f.button(445,610,'改选另一餐',False)
f.text(230,695,'也可以手输标签；图片为可选输入，外传前单独确认。',16,color=MUTED)
f.save()

f=Frame('U02-plan','为明天准备两人午餐','2026-11-18 午餐 · 指定餐次 · 计划 P/v1 已确认','饮食计划')
f.card(157,'番茄鸡蛋面',['人数：2 人    ·    下方为采购清单预览，尚未保存'],112)
f.rect(206,290,1060,592,stroke=LINE)
xs=[230,424,607,814]
for x,t in zip(xs,['食材','总需求','已核对库存','需购差额']):f.text(x,312,t,17,True)
for y,vals in [(364,['番茄','300 g','100 g','200 g']),(421,['鸡蛋','2 个','1 个','1 个']),(478,['面条','200 g','未核对','待核对'])]:
    for x,t in zip(xs,vals):f.text(x,y,t,19,color='#9a6b1d' if t in ['未核对','待核对'] else INK)
f.text(230,546,'番茄：150 g / 人 × 2 人；面条：全餐总量 200 g。',16,color=MUTED)
f.button(230,620,'先核对面条库存');f.button(445,620,'保存含未知项清单',False,220)
f.text(230,697,'确认清单后分别标记已购 / 已准备；库存调整另行确认。',16,color=MUTED)
f.save()

f=Frame('U03-record','一餐，记录多种实际食物','2026-11-18 午餐 · 由计划预填后核对 · 尚未保存','餐食记录')
f.card(158,'只记录我个人实际吃的',['两人备餐量不作为个人摄入；同餐可添加多条食物。'],112)
f.rect(206,290,1060,562,stroke=LINE)
for x,t in [(230,'食物'),(545,'我的实际份量'),(850,'来源')]: f.text(x,311,t,17,True)
for y,vals in [(363,['番茄鸡蛋面','1 份','计划预填后核对']),(420,['无糖茶','300 mL','用户手输']),(477,['苹果','未知','用户手输'])]:
    for x,t in zip([230,545,850],vals):f.text(x,y,t,17)
f.text(230,525,'＋ 添加食物     ·     修改或移除条目后重新核对整份餐食。',16,color=MUTED)
f.button(230,591,'预览这一餐');f.button(445,591,'取消，不保存',False)
f.card(663,'确认边界',['核对预览后再保存；不扣库存，也不自动完成微行动。'],95)
f.save()

f=Frame('U04-feedback','这次小行动，进行得怎样？','已采纳 · 待反馈 · 行动 A01 · 可暂不反馈','今日饮食')
f.card(158,'拿饮料时，换成白水',['窗口：11-18 11:00 至 14:00（已确认，可显式修改）','实际执行日期：2026-11-18；报告时间另行记录'],161)
f.rect(206,342,1060,572,stroke=LINE)
f.text(230,364,'选择本次执行情况',21,True)
for x,label in [(230,'○ 完成'),(430,'● 部分完成'),(630,'○ 未完成')]:
    f.rect(x,411,x+178,463,'#f3e1d9' if x==430 else '#f7f6f2',LINE)
    f.text(x+16,429,label,18)
f.text(230,508,'备注（选填）：换成了小杯，仍喝了一些含糖饮料。',17,color=MUTED)
f.button(230,605,'确认这次反馈');f.button(445,605,'暂不反馈',False)
f.text(230,695,'未反馈在窗口结束后保持未知；稍后可以补充或修改。',16,color=MUTED)
f.save()

f=Frame('U05-review','把这一周看清楚','2026-11-16 至 11-22 · 亚洲 / 上海 · 更新于 11-23 09:00','阶段回顾')
for x,value,label,note in [(206,'3 个','自述完成微行动','按执行日归周，行动去重'),(498,'80%','反馈覆盖率','4 / 5 个已结束窗口行动'),(790,'75%','已反馈者完成比例','3 / 4 个有效反馈行动')]:
    f.rect(x,158,x+270,335,stroke=LINE)
    f.text(x+20,179,label,17,True);f.text(x+20,217,value,34,True,BRAND);f.text(x+20,286,note,14,color=MUTED)
f.card(357,'餐食与计划',['已记录：7 / 10 个用户确认的预期餐次槽位（70%）','已确认计划：5 餐；与实际记录分开展示','营养覆盖：未知，缺少可核验营养资料'],181)
f.card(560,'11-18 午餐    /    已明确关联',['计划：番茄鸡蛋面；实际自述：番茄鸡蛋面，份量未知'],109)
f.button(230,699,'查看统计依据');f.button(445,699,'记录一餐',False)
f.save()

f=Frame('U06-recovery','先核对保存结果','快速记餐 · 网络在确认后中断 · 填写内容已保留','餐食记录')
f.rect(206,158,1060,299,'#fff7e6',LINE)
f.text(230,185,'正在核对是否保存',23,True,'#9a6b1d')
f.text(230,238,'暂时没有收到服务器回执，核对后会显示原记录。',18)
f.card(322,'你刚才确认的内容',['2026-11-18 午餐 · 番茄鸡蛋面 · 份量未知','原确认请求会被复用，保持同一份记录。'],160)
f.button(230,519,'核对保存结果');f.button(445,519,'保留草稿，稍后继续',False,230)
f.card(602,'如果发现资料已经变化',['展示变化字段，重新核对并预览，再确认保存。','模型或查询失败可手输；数据库不可用时保留草稿。'],139)
f.save()

f=Frame('U03M-record-mobile','记录这一餐','11-18 午餐 · 个人实际 · 尚未保存', '餐食记录',390,820)
f.rect(20,150,370,450,stroke=LINE)
for y,t,size in [(173,'番茄鸡蛋面',21),(211,'我的份量：1 份',16),(270,'无糖茶：300 mL',19),(330,'苹果：份量未知',19),(397,'＋ 添加食物',17)]:f.text(38,y,t,size)
f.rect(20,475,370,612,stroke=LINE)
f.text(38,496,'逐条核对，再保存这一餐',19,True)
f.text(38,540,'计划只作来源，不代表实际吃过。',15,color=MUTED)
f.text(38,576,'行动执行情况另行反馈。',15,color=MUTED)
f.button(20,661,'预览这一餐',True,350)
f.text(20,744,'取消不保存 · 示例设计稿',14,color=MUTED)
f.save()

f=Frame('U07-adoption','先确认一个小行动','候选方案 · 不计完成 · 可修改、换一个或跳过','今日饮食')
f.card(158,'拿饮料时，换成白水',['线索：明天午餐拿饮料时；行为：本次饮品选择白水','努力量：低，只改饮品；依据：你确认的减少含糖饮料目标'],157)
f.card(336,'这次行动，什么时候结束？',['建议窗口：2026-11-18 11:00 至 14:00（亚洲 / 上海）','可以修改开始和结束时间；没有统一24小时反馈窗口。'],160)
f.button(230,531,'修改窗口',False);f.button(445,531,'换一个',False);f.button(660,531,'跳过',False)
f.button(230,613,'预览并确认采纳',True,220)
f.text(230,701,'采纳后进入待反馈；窗口到期未反馈为未知，支持迟到补报。',16,color=MUTED)
f.save()

paths=sorted(OUT.glob('U*.png'))
sheet=Image.new('RGB',(1650,480*((len(paths)+2)//3)),'#e7e5df')
for i,p in enumerate(paths):
    im=Image.open(p);im.thumbnail((530,425));x=(i%3)*550;y=(i//3)*480
    sheet.paste(im,(x+(550-im.width)//2,y+10))
    ImageDraw.Draw(sheet).text((x+12,y+447),{'U01-food':'U01 配料核对','U02-plan':'U02 两人计划与准备','U03-record':'U03 个人实际记餐','U03M-record-mobile':'U03M 移动端记餐','U04-feedback':'U04 行动执行反馈','U05-review':'U05 周回顾','U06-recovery':'U06 中断恢复','U07-adoption':'U07 行动采纳与窗口'}.get(p.stem,p.stem),font=ImageFont.truetype(FONT,18),fill=INK)
sheet.save(OUT/'review_contact_sheet.png')
print('已生成八张中文界面设计稿；文字边界检查通过。')
