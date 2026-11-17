# 领域反例与需求覆盖审查

版本 R2-P2 · 2026-11-17。以下为设计走查，不是已执行的产品测试。Q2餐食结构、Q3窗口规则采用本轮用户回答；其余新增机制随本轮用户“继续”沿用进入P3。

## 业务反例

| 案例 | 情境与预期 | 关联规则 |
|---|---|---|
| DS-01 | 午餐面条、饮料、水果属于一份MealRecord、三条ReportedFood；餐次只计一个槽位 | Q2、INV-13 |
| DS-02 | 同日午餐分两次真实用餐，可两份记录；仍仅覆盖该午餐槽位一次 | Q2、INV-13 |
| DS-03 | 删除一条饮料只修订原餐食；删掉最后食物须明确删除整份记录或返回空草稿，不写“零摄入” | INV-02/06 |
| DS-04 | 面条份量未知、饮料量已知；只能计算有营养来源且口径可靠的饮料部分，面条仍未知 | INV-06 |
| DS-05 | 两人番茄每人150g产生300g准备需求，当前用户个人实际量仍待核对 | INV-05 |
| DS-06 | 外卖限制证据可用但无原料克数：可安排该食物，清单配方覆盖未知，不伪造番茄量；若关键过敏证据未知则仍拦截 | INV-03/06 |
| DS-07 | 面条需求200g、库存未核对：完整差额未知；确认零库存后才为200g | INV-06 |
| DS-08 | 两餐鸡肉各150g、库存200g为需购100g；已购勾选不自动将库存变300g | INV-07 |
| DS-09 | 同日期计划午餐和晚餐，只替换午餐：差异确认后午餐归新计划版本，晚餐仍保留，旧确认内容不可变 | INV-08、槽位归属提案 |
| DS-10 | 旧清单鸡肉已购，新版需求增加：保留旧自述作核对材料，不把“已购”直接复制为新版全部已购 | 清单状态守卫 |
| DS-11 | 只安排明日午餐可在指定模式确认；完整日模式缺早餐/晚餐保持草稿 | 已确认Q1 |
| DS-12 | 用户采纳换白水后保存了面条记录：行动仍待反馈，不增加完成数 | INV-09 |
| DS-13 | 窗口周日结束，周二报告周日执行完成：执行周完成数+1，原结束队列的反馈分子+1 | INV-10/12 |
| DS-14 | 窗口下周才结束，本周提前反馈完成：本周可计执行日北极星，尚不进入本周结束队列 | INV-12 |
| DS-15 | 已报告部分完成，撤回为不确定：窗口未结束回待反馈，已结束为未知；不生成新行动 | 执行状态守卫 |
| DS-16 | 主动确认将窗口结束从本周改到下周：同一行动保留窗口修订历史，更新两个结束队列，实际执行日期不自动改动 | Q3、窗口修正提案 |
| DS-17 | 提醒两次未响应：进入提示退避；是否未知由确认窗口决定，不写未完成 | INV-11 |
| DS-18 | 用户更改过敏档案后补报旧行动：允许真实自述修正；新食物推荐按当前条件重查 | INV-04与历史事实边界 |
| DS-19 | 关闭历史后，旧情境快照仍存在：不得因此继续用旧历史排序；可用当前确认情境生成候选 | INV-15 |
| DS-20 | 同一行动完成被修正为部分：原执行周完成数减1，反馈率分子仍包含该有效反馈，不计第二次行动 | INV-10/12 |
| DS-21 | 冻结某周连续显示：该周不增加完成事实，未确认的偏离原因不成为长期标签 | INV-14 |
| DS-22 | 回顾仅有1条记录但用户未确认预期餐次：覆盖度未知，不按计划3餐给出33% | INV-13 |
| DS-23 | 同一原确认请求重复到达：同身份返回原结果；意图改变须新确认而非复用键覆盖 | INV-16 |
| DS-24 | 删除后从旧任务或已导出回执路径恢复：不得重新向当前处理暴露已删除业务资料 | INV-15、删除守卫 |

## 功能需求→领域责任

| 引用 | 主要对象/行为 | 场景或守卫 |
|---|---|---|
| FR-001 | UserProfile、ProfileRevision、CalibrationResponse、PreferenceRule | 确认版本、跳过校准 |
| FR-002 | DietaryTask、FoodObservation、MealRecord | 多入口独立；计划仅预填 |
| FR-003 | ContextSnapshot、VerifiedField、ConstraintAssessment | DS-06/18 |
| FR-004 | MicroAction、ActionWindow | 提案单维、完整内容 |
| FR-005 | ActionDecision | DS-12；采纳/跳过/替代守卫 |
| FR-006 | ExecutionRevision、SourceReference | DS-12/20 |
| FR-007 | ExecutionRevision、ActionWindow | DS-13/15/20 |
| FR-008 | PreferenceSuggestion/Rule、ContextClue、ReminderHistory | DS-17/19/21 |
| FR-009 | PeriodSummary、ExpectedMealSchedule、RecoveryEpisode、WeekPresentation | DS-13/14/20/21/22 |
| FR-010 | DietaryTask、VersionedReference | DS-23/24 |
| FR-011 | ConsentRecord、个人对象及派生证据范围 | DS-19/24 |
| FR-012 | FoodObservation、VerifiedField、SourceReference | DS-06；逐字段候选/核对 |
| FR-013 | DietaryTask进度、确认快照与原因 | 中断守卫；恢复不虚报 |
| FR-014 | MealRecord、ReportedFood | DS-01/02/03/04 |
| FR-015 | ReportedPortion、Quantity、SourceReference | DS-04；单位兼容 |
| FR-016 | FoodObservation、ConstraintAssessment | DS-06/18 |
| FR-017 | DietPlan、PlanRevision、PlannedMeal、SlotAssignment | DS-09/11 |
| FR-018 | PlannedFood、IngredientRequirement、PreparationList/Line | DS-05/06/08/10 |
| FR-019 | Ingredient、InventoryObservation、PurchaseGap | DS-07/08 |
| FR-020 | VersionedReference及各聚合独立状态 | DS-05/09/12/24 |

## 需要后续阶段处理的事项

实体身份在P4映射为主外键、唯一性和保留策略；跨聚合一致写入在P3/P5设计；长期偏好参数、线索阈值和提醒反馈疲劳按确认规则及验证数据细化，不用现有代码阈值替换原SRS。

P2目前不决定SQL、接口URL、队列、微服务或托管平台。上述场景后续作为数据约束、接口响应及UI流程的共同验收输入。
