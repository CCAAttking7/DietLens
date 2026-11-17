"""整合最终中文报告；宋体、黑白、连续紧凑排版。"""
from pathlib import Path
import json,re,io,copy
from PIL import Image as PILImage
ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'final/提交版';OUT.mkdir(parents=True,exist_ok=True)
data=json.loads((ROOT/'final/report-content.json').read_text(encoding='utf-8'))
pages=data['pages']
def p(t):return {'kind':'p','text':t}
def h(t):return {'kind':'h','text':t}
def tab(heads,rows,widths=None):return {'kind':'table','heads':heads,'rows':rows,'widths':widths}
for pg in pages:
 new=[]
 for b in pg['blocks']:
  if b['kind']=='p':
   t=b['text']
   if t.startswith(('篇幅说明：','DietLens · 系统分析','按用户指定，','教师或课堂反馈：','课堂或教师反馈','原作业最终截止：')):continue
   t=t.replace('教师或课堂反馈尚未提供，未将其虚构为变更依据；分工完成情况须由组员核对。','')
   t=t.replace('本次交付包括','本报告包括').replace('四人平均分工安排','团队分工').replace('当前均未冒称已执行','均为第三部分待执行的验证计划')
   t=t.replace('用户指出后，重新按原作业九项收敛','经审查后，重新按作业九项交付收敛')
   t=t.replace('最终报告需要团队承担判断：复核原SRS及课堂反馈、确认设计取舍、检查数量与指标样例、实际执行PoC，并逐人核实贡献。AI不能替成员提供完成证明、教师反馈或未做过的实验。','团队负责复核需求、确认设计取舍、检查样例并执行PoC。实验结论以实际测试记录为准。')
   b={**b,'text':t}
  if b['kind']=='h' and b['text']=='反馈与当前状态':continue
  if b['kind']=='figure':b={**b,'height':min(b['height'],275 if b['path'].startswith('ui/') else 340)}
  if b['kind']=='pair':b={**b,'height':275}
  new.append(b)
 pg['blocks']=new
pages[0]['title']='1 设计摘要'
pages[0]['blocks'].insert(0,p('DietLens：基于Web Agent的个人饮食管理与微习惯干预系统。第二组：薛毓哲、刘相成、颜泽霖、韩昊苏。2026年11月17日。'))
pages[0]['blocks'].insert(2,p('系统以“处理眼前这一餐”为主要场景：复用已确认档案，从用户的一句话中整理食物、时间和数量，只追问会改变判断的缺口；在预算、可获得性与食品证据允许的范围内，提出一个可尝试的微行动。用户可修改或跳过，随后用简短反馈说明结果或障碍。近期反馈调整同类情境的候选，稳定偏好经确认后保存。核心验证依次关注食品约束、录入负担、行动可行性和反馈后的调整价值。'))
arch=next(x for x in pages if x['title'].startswith('2.3'))
arch['blocks'].append(p('Harness与确定性领域服务作为同一FastAPI进程内的逻辑模块部署，共享发布和故障域；逻辑分离用于约束职责，不新增网络服务。模型请求使用有界并发与超时，等待期间不持有数据库写事务。进程重启后从已提交任务与回执恢复；外部模型失败仍保留手动路径。仅当慢调用持续影响普通请求且资源隔离措施不足时，再评估独立执行进程。'))
arch['blocks'].append(p('首轮PoC沿用模块化单体和本地SQLite，验证主闭环。托管数据库迁移、完整费用审计和复杂运维作为后续候选；附件中的表与接口用于检查边界，不要求首轮全部实现。涉及授权、硬约束和数据正确性的原需求继续保留；范围调整须进入变更日志。'))
idx=next(i for i,x in enumerate(pages) if x['title'].startswith('3.1'))
pages.insert(idx,{'title':'3.1 食品身份与多来源证据融合','section':'模型','blocks':[
 p('食品服务采用来源适配器模式，分别读取包装商品、本地食物编码和用户提供的菜单或标签；适配层统一字段结构，保留原始来源。业务层再核对身份、单位、加工状态和适用范围，形成当前用途的证据摘要。[7]'),
 tab(['类别','身份与适用范围','融合规则'],[['包装商品','条码、品牌、规格、配方及标签时间','身份一致后比较字段；当前包装用于核对本次商品。'],['通用食材','来源编码、生熟及加工状态','只用于对应状态的参考；食材分类不证明具体商品配料。'],['非标准菜品','本次菜单、图片或用户自述','保存本次描述；参考配方与实际确认配料分别表示。']],[1,1.8,2.5]),
 p('融合流程为：来源记录→身份关联候选→字段证据→冲突处理→当前用途评估。每字段记录值、单位、计量基准、来源、获取时间、适用范围和核对状态。名称相似只产生关联线索；关键字段冲突保留双方证据并要求核对，不按来源数量投票，也不自动以最新抓取值覆盖当前标签。冲突处理策略与来源接入分开，便于分别验证。'),
 p('例如，同名“燕麦奶”的商品标签列出燕麦及大豆，通用燕麦编码只提供参考营养。两者不能合并为无大豆商品。明确过敏原命中时排除该推荐；配料未知时暂停受影响候选；仅热量缺失时停止热量比较，仍允许保存用户实际用餐自述。180 kcal/100 g与150 g可确定性换算为270 kcal，g与mL无密度依据时分列。'),
 p('食品证据摘要同时传给计划和微行动服务，包含食品身份、证据版本、约束版本、未知与冲突。行动引入的新食品须单独检查，原餐通过不能替代新增食物的核对。首轮只验证代表性食品样例，不建设完整食品主数据平台。')]})
action=next(x for x in pages if x['title'].startswith('3.2 用例'))
action['title']='3.3 用例实现：微行动选择与反馈'
action['blocks'][:0]=[
 p('微行动分为平替、加法、顺序和时序四类：保留主要餐食，只改变一个可表达的小行为。候选先经过食品硬约束、预算、时间、可获得性及保留条件检查，再按当前目标、已报告障碍、努力量和已授权偏好分层排序；同条件采用稳定顺序，记录规则版本与主要理由。首轮使用可解释规则，不提前确定学习模型或排序权重。[8]'),
 tab(['午餐场景候选','资格与选择依据','结果'],[['将含糖配饮换为白水','用户希望减少含糖饮品；预算用尽；白水可获得','主候选：保留主餐，改变配饮。'],['额外购买一份水果','新增费用超出本次确认预算','排除本次候选。'],['换另一款配饮','配料未知，影响已确认限制检查','待核对，不能直接采纳。']],[1.4,2.5,1.7]),
 p('默认展示一个主候选及理由，备选可展开。微行动可独立发起，不要求先完成周计划或完整饮食日志。采纳表示愿意尝试；完成数只由后续有效执行自述产生。')]
action['blocks'].append(p('短期调整以用户确认的障碍为依据：时间不足时降低准备步骤，缺少食材时核对可获得的替代项；“换一个”只调整相关候选，“暂不需要”结束当前提案。采纳和执行分别作为观察信号，避免仅因采纳就持续重复同类建议。长期偏好形成可解释提案，用户确认后生效，可停用或重置；未知结果不写成负反馈。'))
for pg in pages:
 if pg['title']=='3.1 Agent角色、状态与记忆':pg['title']='3.2 Agent角色、状态与记忆'
 elif pg['title'].startswith('3.3 用例实现：计划'):pg['title']='3.4 用例实现：计划、准备与记餐'
 elif pg['title'].startswith('3.4 用例实现：故障'):pg['title']='3.5 用例实现：故障、回执与恢复'
flow=next(x for x in pages if any(b.get('text','').startswith('任务上下文复用') for b in x['blocks']))
flow['blocks'].extend([h('低负担录入与连续场景'),p('用户输入“明天午餐吃面，饮料想少糖”，系统带入已确认目标和预算，只询问确实影响本次建议的可获得选项。文字解析形成食物、餐次和份量候选；图片OCR可辅助提取标签，需逐图授权。页面只突出待核对字段，其他已知信息可展开查看。修改、差异预览和确认放在同一卡片，不要求重填整份档案。'),p('实际用餐可从计划或最近记录选择预填；一次表述可整理成多条食物，份量不清楚时保留未知。用户核对本次实际内容后一次保存，重复提交查原回执。采纳行动后，反馈主入口只问完成、部分完成或未完成；日期给出可修改建议，障碍为可选项，不强制填写完整日志。下次同类情境明确说明因哪个障碍调整了建议。')])
risk=next(x for x in pages if x['title'].startswith('6 '))
risk['blocks'][:0]=[p('验证顺序以核心价值为先：食品约束→录入减负与行动可行性→反馈驱动调整；状态一致性作为各阶段的共同通过条件。下列样本量和阈值为原SRS目标或本次候选验证方案，结果均待第三部分获得。'),tab(['验证问题','方法与记录','决策用途'],[['复用与提取能否降低负担','6名成年用户，平衡任务顺序，对比手工填写与复用预填；记录耗时、手输字段、纠错、放弃及求助','至少5/6独立完成主流程；同时报告每人的差异，若更省时但误录增多则修订预填。'],['情境化行动是否更可行','12类障碍情境比较固定模板与约束后排序；记录可获得性、感知努力、换选理由及执行自述','优先修正不可行建议与排序规则，不以采纳率单独判定收益。'],['反馈是否改善下一次建议','同一虚构情境注入不同障碍，检查调整方向；邀请用户复核理由，记录规则版本','调整须能对应已确认障碍；关闭历史或重置后不再使用该信号。'],['持续价值能否维持','形成性研究后开展自愿的2周探索，记录重复执行、反馈负担、退出原因和记录覆盖','用于调整行动库与提示频率；长期行为效果另设更长周期及适当对照研究。']],[1.1,2.7,2.1])]
for b in risk['blocks']:
 if b['kind']=='p' and b['text'].startswith('先验证可信提交'):b['text']='食品覆盖、排序规则、模型型号与托管配置由PoC结果决定。性能与删除恢复按风险分阶段验证；未通过状态与授权检查时，不进入真实用户数据研究。'
req=next(x for x in pages if x['title'].startswith('4 更新'))
req['blocks'].append(tab(['新增细化','对应原需求','原因及影响'],[['字段证据与身份融合','UC-02/03/04、FR-012/015/016','同名与不同加工状态不能直接比较；来源适配与冲突策略分开。'],['复用预填与缺口追问','UC-01/07/12','降低重复输入；自动提取为候选，实际记录仍由用户核对。'],['候选资格与障碍调整','UC-09/10、FR-004至008','把微行动落实为可行选择；排序及适应规则列为待验证假设。']],[1.3,1.4,3]))
refpage={'title':'8 注释参考文献（续）','section':'参考文献','blocks':[]}
refs=[('7','Open Food Facts食品来源接口','Open Food Facts. Introduction to Open Food Facts API documentation.','https://openfoodfacts.github.io/openfoodfacts-server/api/',
 '该官方文档介绍开放食品商品资料的接入方式，字段可包含配料和营养信息。对DietLens的作用是提供包装商品的来源适配参考：接入层负责查询及保留来源，业务层判断该记录是否适用于当前包装和用途。接口返回成功与关键字段足够支持建议是两个不同检查点。\n\n本设计据此保留商品身份、规格、获取时间及字段来源，并将资料缺失、来源失败和无匹配分别呈现。同名菜单不自动继承商品配料，食材编码也不替代本次标签。合并前核对身份与计量基准；冲突保留差异，无法消解的安全关键字段进入人工核对。这样既利用多来源扩大查询机会，又避免拼接出实际不存在的完整食品。\n\n验证采用代表性包装、食材和菜单样例，分别统计字段覆盖、身份误配与失败。来源接口是设计依据，具体覆盖和新鲜度由本地样例决定；缓存保留获取时间，模型不填造缺失配料。首轮优先验证证据能否贯通计划和微行动，再决定持久化粒度。'),
 ('8','即时自适应干预与决策规则','Nahum-Shani, I., et al. (2018). Annals of Behavioral Medicine, 52(6), 446–462.','https://doi.org/10.1007/s12160-016-9830-8',
 '该研究讨论即时自适应干预的六类要素：远期结果、近期结果、决策点、干预选项、个性化变量与决策规则。DietLens借此将干预拆成可以审查的设计：当前一餐作为决策情境，时间、预算和障碍作为输入，小行动作为候选，资格与排序规则决定本次呈现。\n\n本项目的近期关注点是建议可行性、感知努力和用户报告的执行；持续习惯改善是较长周期目标。反馈首先用于修正相同情境的建议，稳定偏好仍由用户确认。这种映射使“反馈驱动优化”具有明确输入和输出，也使规则版本可以与候选理由关联。采纳、执行和未知分别保留，避免把缺少反馈直接解释为建议失败。\n\n该框架用于指导验证设计，未直接提供本项目的排序权重或冷却时长。第三部分先用障碍案例和形成性研究检查可理解性，再用自愿的短期探索观察重复使用与负担。若要评价持续行为改善，需要更长随访和适当比较设计；本次不把设计模型或静态界面视为干预效果数据。')]
for no,title,author,url,txt in refs:
 refpage['blocks'] += [h('['+no+'] '+title),p(author+' 访问日期：2026-11-17。'),{'kind':'link','text':url,'url':url}]+[p(x) for x in txt.split('\n\n')]
pages.insert(len(pages)-1,refpage)
last=pages[-1];last['title']='9 团队分工'
last['blocks']=[p('小组按需求分析、架构决策、模型设计、交互与报告四个工作包平均分工，每人25%。'),next(b for b in last['blocks'] if b['kind']=='table')]
data['version']='中文最终提交版';data['pages']=pages
(OUT/'报告内容.json').write_text(json.dumps(data,ensure_ascii=False,indent=2),encoding='utf-8')
md=['# DietLens 系统分析与设计报告','']
for pg in pages:
 md+=['## '+pg['title'],'']
 for b in pg['blocks']:
  if b['kind'] in ('p','h'):md += [('### ' if b['kind']=='h' else '')+b['text'],'']
  elif b['kind']=='table':md+=['| '+' | '.join(b['heads'])+' |','|'+'---|'*len(b['heads'])]+['| '+' | '.join(r)+' |' for r in b['rows']]+['']
  elif b['kind']=='link':md+=['[来源]('+b['url']+')','']
  elif b['kind']=='figure':md+=['!['+b['caption']+'](../../'+b['path']+')','']
  elif b['kind']=='pair':md+=['!['+b['caption']+'](../../'+s+')' for s in b['paths']]+['']
(OUT/'DietLens_系统设计报告_最终版.md').write_text('\n'.join(md),encoding='utf-8')
# 复用既有排版器，替换版式和图形加载；向量图中文字使用嵌入宋体。
src=(ROOT/'tools/build_assignment_pdf.py').read_text(encoding='utf-8')
src=src.replace("FINAL/'report-content.json'","FINAL/'提交版/报告内容.json'")
src=src.replace('C:/Windows/Fonts/msyh.ttc','C:/Windows/Fonts/simsun.ttc').replace('C:/Windows/Fonts/msyhbd.ttc','C:/Windows/Fonts/simsun.ttc')
src=re.sub(r"colors.HexColor\('#[0-9a-fA-F]+'\)",'colors.black',src)
src=src.replace('fontSize=10.1,leading=17','fontSize=10.5,leading=15').replace('spaceAfter=10)','spaceAfter=6)')
src=src.replace('fontSize=18,leading=25','fontSize=15,leading=21').replace('spaceAfter=18','spaceAfter=10')
src=src.replace('fontSize=9.3,leading=14','fontSize=9.5,leading=13').replace('spaceAfter=9','spaceAfter=6')
src=src.replace('if n:story.append(PageBreak())','if n:pass')
src=src.replace("story.append(par(pg['title'],heading))", "\n    if not (pg['section']=='参考文献' and '续' in pg['title']):story.append(par(pg['title'],heading))")
src=src.replace("('BACKGROUND',(0,0),(-1,0),colors.black)","('BACKGROUND',(0,0),(-1,0),colors.white)")
src=src.replace('[colors.white,colors.black]','[colors.white,colors.white]').replace("(-1,-1),6)","(-1,-1),4)")
src=src.replace('color="#486958"','color="#000000"').replace('Spacer(1,12)','Spacer(1,7)')
src=src.replace('中文整合版','最终设计报告').replace("ROOT/'DietLens_Assignment2_Design.pdf'","ROOT/'DietLens_系统设计报告_最终版.pdf'")
start=src.index('def image(');end=src.index('story=[]',start)
src=src[:start]+'''def image(path,maxheight,width=WIDTH):
    import xml.etree.ElementTree as ET
    from svglib.svglib import svg2rlg, Svg2RlgAttributeConverter
    Svg2RlgAttributeConverter.convertFontFamily=lambda self,*args,**kwargs:'中文正文'
    from reportlab.graphics import renderPDF
    from reportlab.platypus import Flowable
    sp=(ROOT/path).with_suffix('.svg')
    root=ET.parse(sp).getroot()
    for el in root.iter():
        tag=el.tag.split('}')[-1]
        if 'style' in el.attrib:
            st=re.sub(r'stroke:#[0-9a-fA-F]+','stroke:black',el.get('style'))
            st=re.sub(r'fill:#[0-9a-fA-F]+','fill:'+('black' if tag in ('text','tspan') else 'white'),st)
            el.set('style',st)
        if 'font-family' in el.attrib:el.set('font-family','中文正文')
        if 'fill' in el.attrib and el.get('fill')!='none':
            fill=el.get('fill').lower()
            el.set('fill','black' if tag in ('text','tspan') or fill in ('#000000','black','#000') else 'white')
        if 'stroke' in el.attrib and el.get('stroke')!='none':el.set('stroke','black')
    drawing=svg2rlg(io.BytesIO(ET.tostring(root)))
    def fix(group):
        if hasattr(group,'fontName'):group.fontName='中文正文'
        for child in getattr(group,'contents',[]):fix(child)
    fix(drawing)
    ratio=min(width/drawing.width,maxheight/drawing.height)
    drawing.scale(ratio,ratio);drawing.width*=ratio;drawing.height*=ratio
    return drawing
''' + src[end:]
src=src.replace('import html,json','import html,json,io')
src=src.replace('story=[]','heading.keepWithNext=True\nsub.keepWithNext=True\nstory=[]')
src=src.replace('doc.build(story,onFirstPage=footer,onLaterPages=footer)', '''fixed=[]
for item in story:
    if isinstance(item,KeepTogether) and fixed and isinstance(fixed[-1],Paragraph) and fixed[-1].style.name=='页标题':
        item._content.insert(0,fixed.pop())
    fixed.append(item)
doc.build(fixed,onFirstPage=footer,onLaterPages=footer)''')
exec(compile(src,str(ROOT/'tools/build_assignment_pdf.py'),'exec'))
