"""将本次编写的文档和图稿显示文字统一为中文，保留技术标识及工具原文件。"""
from pathlib import Path
import re

ROOT = Path(__file__).resolve().parents[1]

NAMES = {
 'UserProfile':'用户档案','ProfileRevision':'档案版本','ConsentRecord':'用途授权',
 'DietaryTask':'饮食任务','ContextSnapshot':'情境快照','FoodObservation':'食品观察',
 'VerifiedField':'核对字段','SourceReference':'来源引用','DietPlan':'饮食计划',
 'PlanRevision':'计划版本','PlannedMeal':'计划餐次','PlannedFood':'计划食物',
 'IngredientRequirement':'食材需求','Ingredient':'标准食材','PreparationList':'准备采购清单',
 'PreparationLine':'清单条目','InventoryObservation':'库存核对','SlotAssignment':'餐次归属',
 'MealRecord':'实际餐食记录','ReportedFood':'实际食物条目','MicroAction':'微行动',
 'ActionDecision':'行动决策','ActionWindow':'行动窗口','ExecutionRevision':'执行修订',
 'PreferenceSuggestion':'偏好候选','PreferenceRule':'稳定偏好规则','ContextClue':'情境线索',
 'RecoveryEpisode':'恢复周期','ExpectedMealSchedule':'预期餐次安排',
 'WeekPresentation':'连续周呈现','PeriodSummary':'期间回顾',
}
TEXT = {
 'D01 - Confirmed context and evidence (R2-P2 proposal)':'D01 · 已确认情境与食品证据（第二轮领域候选版）',
 'D02 - Preparation and personal meal facts (R2-P2)':'D02 · 未来准备与个人实际餐食（第二轮领域候选版）',
 'D03 - Micro-action, reports and learning (R2-P2)':'D03 · 微行动、执行自述与反馈调整（第二轮领域候选版）',
 'D04 - Decision and execution are distinct (R2-P2)':'D04 · 行动决策与执行状态分离（第二轮领域候选版）',
 'userId':'用户身份','currentRevision':'当前版本','proposeChange()':'提出变更()',
 'confirmChange()':'确认变更()','version':'版本','confirmedAt':'确认时间',
 'goals / constraints / preferences':'目标 / 硬约束 / 软偏好',
 'purpose / scope / revision':'用途 / 范围 / 修订','effectiveAt / revokedAt':'生效时间 / 撤回时间',
 'allow() / revoke()':'允许() / 撤回()','taskId / taskType':'任务身份 / 类型',
 'progress / resumePoint':'进度 / 恢复位置','pause() / resume()':'暂停() / 恢复()',
 'contextId / revision':'情境身份 / 修订','mealSlot / servingCount':'餐次槽位 / 准备人数',
 'profileReference':'档案版本引用','confirmContext()':'确认情境()',
 'observationId / evidenceRevision':'观察身份 / 证据版本','productOrMenuSpec':'当前商品或菜单规格',
 'verifyField()':'核对字段()','original / verifiedValue / unit':'原始值 / 核对值 / 单位',
 'candidateOrVerifiedOrUnknown':'候选 / 已核对 / 未知','source / objectSpec':'来源 / 对象规格',
 'materialDate / retrievedAt':'资料日期 / 获取时间','confirmed versions':'确认版本',
 'purpose permissions':'分项用途授权','current context':'当前情境','version used':'所用版本',
 'evidence used':'所用证据','provenance':'来源依据','current permission on resume':'恢复时检查当前授权',
 'A snapshot records the conditions used.':'快照保留当时采用的条件。',
 'It never replaces current consent.':'新处理仍须检查当前授权。',
 'planId / owner':'计划身份 / 所属用户','confirmRevision()':'确认新版本()',
 'revision / dateRange':'修订 / 日期范围','mode / selectedSlots / status':'模式 / 选定槽位 / 状态',
 'plannedMealId / mealSlot':'计划餐次身份 / 槽位','servingCount':'准备人数',
 'plannedFoodId / foodSpec':'计划食物身份 / 规格','evidenceReference':'证据版本引用',
 'quantityOrUnknown / unit':'已知或未知数量 / 单位','perPersonOrTotal / provenance':'每人或全餐总量 / 依据',
 'ingredientId / standardName':'食材身份 / 标准名称','listId / planVersion':'清单身份 / 计划版本',
 'stockBasis / status':'库存核对依据 / 状态','preview() / confirm()':'预览() / 确认()',
 'lineId / compatibleBasis':'条目身份 / 兼容口径','demand / gap / unknowns':'需求 / 差额 / 未知',
 'purchasedReport / preparedReport':'自述已购 / 自述已准备','inventoryId / revision':'库存身份 / 修订',
 'adjust() / remove()':'调整() / 删除()','owner / date / mealSlot':'用户 / 日期 / 餐次槽位',
 'activePlanMealReference':'当前有效计划餐次引用','mealRecordId / revision':'用餐记录身份 / 修订',
 'date / slot / eatenAt / status':'日期 / 餐次 / 用餐时间 / 状态',
 'confirm() / correct() / delete()':'确认() / 修正() / 删除()',
 'foodEntryId / foodSpec':'食物条目身份 / 规格','personalQuantityOrUnknown / unit':'个人已知或未知份量 / 单位',
 'origin / evidenceType':'输入出处 / 自述证据类型','exact source revision':'来源计划的明确版本',
 'trace source demand':'追溯原需求','read confirmed stock':'读取已核对库存',
 'current effective slot':'当前槽位归属','optional versioned reference':'可选的版本引用',
 'Q2 confirmed: one eating occasion contains food entries.':'已确认：一次个人用餐包含多条食物。',
 'Several occasions may occupy the same date/meal slot.':'同一日期与餐次可有多次实际用餐。',
 'Coverage counts that slot only once.':'覆盖度对该餐次槽位仅计一次。',
 'Unknown demand or stock keeps the full gap unknown.':'需求或库存未知时，完整差额保持未知。',
 'Marking purchased/prepared does not change stock.':'勾选已购或已准备不自动改变库存。',
 'actionId / contextReference':'行动身份 / 情境引用','cue / behavior / effort / rationale':'线索 / 行为 / 努力量 / 依据',
 'dimension / proposalRevision':'动作维度 / 提案版本','confirmedWindowRevision':'已确认窗口版本',
 'adopt() / skip() / replace()':'采纳() / 跳过() / 换一个()',
 'actionReference / decision':'行动引用 / 决策','adoptedProposalRevision / decidedAt':'所采纳提案版本 / 决策时间',
 'context / startAt / endAt / zone':'场景 / 开始时间 / 结束时间 / 时区','confirmedRevision':'确认版本',
 'actionReference / reportRevision':'行动引用 / 自述修订','status / executionDate / reportedAt':'执行状态 / 执行日期 / 报告时间',
 'correctReport()':'修正执行自述()','suggestionId / evidenceScope':'候选身份 / 证据范围',
 'reason / proposedDirection':'原因 / 候选调整方向','ruleId / revision / confirmedAt':'规则身份 / 修订 / 确认时间',
 'conditions / direction / status':'条件 / 方向 / 状态','confirm() / disable() / delete()':'确认() / 停用() / 删除()',
 'clueId / evidenceScope':'线索身份 / 证据范围','hypothesis / uncertainty / userResponse':'假设 / 不确定性 / 用户核对',
 'episodeId / confirmedDeparture':'周期身份 / 已确认偏离','confirmedReturn / excludedPeriods':'已确认回归 / 排除时段',
 'owner / week / revision':'用户 / 自然周 / 修订','confirmedExpectedSlots':'已确认预期餐次槽位',
 'owner / week / evidenceBasis':'用户 / 自然周 / 证据依据','completedOrFrozenOrUnknown':'完成周 / 冻结周 / 未知周',
 'period / zone / updatedAt':'期间 / 时区 / 更新时间','sources / numerator / denominator':'来源 / 分子 / 分母',
 'unknownCoverage':'未知与覆盖范围','proposed then confirmed at adoption':'提案后在采纳时确认',
 'only when adopted':'仅已采纳时成立','permitted evidence':'授权范围内的证据',
 'explicit user confirmation':'用户明确确认','user confirms endpoints':'用户确认起止点',
 'latest effective report':'最新有效执行自述','slot denominator':'预期餐次分母',
 'display without changing facts':'仅作呈现，不修改事实',
 'Same action identity for late feedback/corrections.':'迟到反馈与修正沿用同一行动身份。',
 'Execution date assigns the completion week.':'完成数按执行日期归周。',
 'Window end assigns the feedback cohort.':'反馈队列按窗口结束时间归周。',
 r'confirm adoption\nbehavior + constraints + window':r'确认采纳\n行为、约束及行动窗口',
 'user skips':'用户跳过',r'edit or replace\nrevalidate new proposal':r'修改或更换\n重新校验新提案',
 'window ended AND no effective report':'窗口已结束且无有效执行自述',
 'confirmed self-report':'用户确认执行自述','late confirmed self-report':'用户迟到确认执行自述',
 r'correct same action\nappend report revision':r'修正同一行动\n追加自述版本',
 r'withdraw effective report\n[window ended]':r'撤回有效执行自述\n[窗口已结束]',
 r'withdraw effective report\n[window still open]':r'撤回有效执行自述\n[窗口尚未结束]',
 'confirmed deletion':'用户确认删除','Skipped has no execution state.':'跳过没有执行状态。',
 'Reported = complete / partial / not_done; latest revision only.':'有效执行自述：完成、部分完成或未完成，取最新有效版本。',
 'Late feedback never extends a window.':'迟到反馈不自动延长窗口。',
 'Excluded facts cannot resume processing.':'已删除事实不得恢复后继续处理。',
}

for p in (ROOT/'docs/design/diagrams').glob('D*.puml'):
    text=p.read_text(encoding='utf-8')
    for old,new in sorted(TEXT.items(),key=lambda item:len(item[0]),reverse=True):
        # Only visible attributes/notes/labels, never aliases in relationships.
        text=text.replace(old,new)
    for alias,label in NAMES.items():
        text=re.sub(rf'^class {alias} (<<[^>]+>>)',f'class "{label}" as {alias} \\1',text,flags=re.M)
    for old,new in [('aggregate','聚合'),('entity','实体'),('value','值对象'),('derived','派生结果')]:
        text=text.replace(f'<<{old}>>',f'<<{new}>>')
    if 'skinparam defaultFontName' not in text:
        text=text.replace('skinparam shadowing false','skinparam shadowing false\nskinparam defaultFontName Noto Sans CJK SC')
    states={'Decision':'行动决策','Execution':'执行状态','Proposed':'待决定提案',
            'Adopted':'已采纳','Skipped':'已跳过','Superseded':'已被替代',
            'PendingFeedback':'待反馈','Unknown':'执行未知','Reported':'已有有效执行自述','Excluded':'已删除退出处理'}
    if p.name.startswith('D04'):
        for alias,label in states.items():
            text=re.sub(rf'^(\s*)state {alias}(\s*\{{)?\s*$',
                        lambda m:f'{m[1]}state "{label}" as {alias}'+(' {' if m[2] else ''),text,flags=re.M)
        # Declare nodes that previously only appeared in transitions.
        for alias in ['Proposed','Adopted','Skipped','Superseded']:
            if f'as {alias}' not in text:
                text=text.replace('state "行动决策" as Decision {',
                                  f'state "行动决策" as Decision {{\n state "{states[alias]}" as {alias}')
    p.write_text(text,encoding='utf-8')

MD = {
 '# Feature Specification:':'# 功能需求规格：','**Feature Branch**':'**版本分支**',
 '**Created**':'**编写日期**','**Status**':'**状态**','**Input**':'**输入依据**',
 '## User Scenarios & Testing':'## 用户故事与验收','### User Story ':'### 用户故事 ',
 '(Priority:':'（优先级：','**Why this priority**':'**优先级依据**',
 '**Independent Test**':'**独立验证方式**','**Acceptance Scenarios**':'**验收场景**',
 '**Given**':'**给定**','**When**':'**当**','**Then**':'**则**',
 '### Edge Cases':'### 边界与异常','## Requirements':'## 需求',
 '### Functional Requirements':'### 功能需求','### Non-Functional Requirements':'### 非功能需求',
 '### Key Entities':'### 主要业务对象','## Success Criteria':'## 成功标准',
 '### Measurable Outcomes':'### 可量化结果','## Assumptions':'## 依据与假设',
 '## Clarifications':'## 澄清与确认记录','_Avoid_:':'_避免混用_：',
 '| Clear |':'| 已明确 |','| Deferred |':'| 留后续阶段 |','| Outstanding |':'| 待补充 |',
 'Local Files':'本地文件','Design Summary':'设计摘要','Architecture and Key Decisions':'架构与关键决策',
 'Design Models':'设计模型','Updated Requirements':'需求更新','UI and UX Design':'界面与用户体验设计',
 'Open Issues and Risks':'开放问题与风险','AI Tools Reflection':'人工智能工具反思',
 'Annotated References':'注释参考文献','Team member contributions':'成员贡献',
 'Given/When/Then':'给定／当／则','NEEDS CLARIFICATION标记':'待澄清标记',
 'TBD':'待定',
}
for p in ROOT.rglob('*.md'):
    if any(x in p.relative_to(ROOT).parts for x in ['.agents','.specify']):continue
    text=p.read_text(encoding='utf-8')
    for old,new in MD.items():text=text.replace(old,new)
    text=re.sub(r'（优先级： (P\d)\)',r'（优先级：\1）',text)
    p.write_text(text,encoding='utf-8')

p=ROOT/'README.md';text=p.read_text(encoding='utf-8')
text=text.replace('正文采用中文，需求与模型保留稳定英文编号。约 500 words 的设计摘要和每条 200–300 words 的参考文献注释将提供满足原文字数要求的英文内容。',
                  '全部交付材料采用中文，包括摘要、参考注释、图表与界面；需求编号及必要技术标识保留。原要求的摘要约500 words、参考注释每条200–300 words作为字数依据单列，中文篇幅口径在最终提交说明中注明，不自行把英文单词数等同汉字数。')
text=text.replace('英文约 500 words，内容与正文一致','中文版；内容与正文一致，提交说明注明篇幅口径').replace('每条英文注释 200–300 words；核查链接和适用范围','中文注释；核查链接和适用范围，注明篇幅口径')
p.write_text(text,encoding='utf-8')
p=ROOT/'docs/design/01-project-overview.md';text=p.read_text(encoding='utf-8').replace('中文设计和交流；摘要与参考注释的英文 word 数沿用原作业字数处理方案，最终注明','全部成果使用中文；编号、接口路径与技术专名保留；原作业字数要求与中文篇幅口径在提交说明中分别注明');p.write_text(text,encoding='utf-8')
p=ROOT/'docs/design/diagrams/README.md';text=p.read_text(encoding='utf-8').replace('英文概念名与中文','图中中文对象名与').replace('对应；未将当前代码类或物理表当作目标领域。','对应；源文件仅在内部别名保留技术标识。未将当前代码类或物理表当作目标领域。');p.write_text(text,encoding='utf-8')

# Update UI source so regeneration cannot bring the English banner back.
p=ROOT/'tools/render_ui_mockups.py';text=p.read_text(encoding='utf-8').replace('ASSIGNMENT 2 / TARGET DESIGN','第二次作业 / 目标设计稿').replace("paths=sorted(OUT.glob('*.png'))","paths=sorted(OUT.glob('U*.png'))")
text=text.replace('ImageDraw.Draw(sheet).text((x+12,y+447),p.stem,',"ImageDraw.Draw(sheet).text((x+12,y+447),{'U01-food':'U01 配料核对','U02-plan':'U02 两人计划与准备','U03-record':'U03 个人实际记餐','U03M-record-mobile':'U03M 移动端记餐','U04-feedback':'U04 行动执行反馈','U05-review':'U05 周回顾','U06-recovery':'U06 中断恢复'}.get(p.stem,p.stem),")
p.write_text(text,encoding='utf-8')
print('已更新文档、领域图源及界面生成文字，待重新渲染和检查。')
