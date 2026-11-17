"""为已生成的领域图和旧版设计图制作中文检查拼图。"""
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parents[1]
FONT = ImageFont.truetype('C:/Windows/Fonts/msyh.ttc', 19)
DOMAIN = {
 'D01-context-evidence':'D01 已确认情境与食品证据',
 'D02-meals-preparation':'D02 未来准备与个人实际餐食',
 'D03-actions-learning':'D03 微行动与反馈调整',
 'D04-action-lifecycle':'D04 行动决策与执行生命周期',
}
LEGACY = {
 'M01A-current':'M01A 当前逻辑架构','M01B-target':'M01B 目标逻辑架构',
 'M02-deployment':'M02 部署架构','M03-domain':'M03 领域结构',
 'M04-action':'M04 微行动协作','M05-plan-record':'M05 计划与实际记录',
 'M06-recovery':'M06 命令与恢复','M07A-task':'M07A 任务状态',
 'M07B-execution':'M07B 决策与执行','M08-user-flow':'M08 用户流程',
}

def sheet(folder, labels, output):
    canvas=Image.new('RGB',(1900,1000*((len(labels)+1)//2)),'#ebe9e3')
    for i,(stem,caption) in enumerate(labels.items()):
        im=Image.open(folder/(stem+'.png')).convert('RGB')
        im.thumbnail((920,920))
        x=(i%2)*950;y=(i//2)*1000
        canvas.paste(im,(x+(950-im.width)//2,y+15))
        ImageDraw.Draw(canvas).text((x+15,y+960),caption,font=FONT,fill='#24231f')
    canvas.save(output)

sheet(ROOT/'docs/design/diagrams/rendered', DOMAIN,
      ROOT/'docs/design/diagrams/rendered/domain-review-contact-sheet.png')
sheet(ROOT/'diagrams/rendered', LEGACY, ROOT/'diagrams/model_review_contact_sheet.png')
print('已重建两份中文设计图检查拼图。')
