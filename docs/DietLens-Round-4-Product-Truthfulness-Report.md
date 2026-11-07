# DietLens Round 4 — Product Truthfulness & Core Value Report

## Executive summary

本轮围绕“用户能否相信系统正在说什么”做了小范围产品逻辑修复。重点是把过敏的未知、明确没有和已记录区分开，避免不完整食品来源被标为安全；同时收紧推荐、回顾和购物清单的产品承诺，使其与当前 deterministic 实现一致。

## 已修复的问题

### 过敏安全语义（P0）

- `Profile.allergy_status` 持久化为 `unknown`、`none` 或 `specified`。
- onboarding 提供“暂不说明 / 没有已知过敏 / 有过敏信息”三种明确选择。
- 旧档案缺失状态时，空列表仍按未知处理；非空且已有用户确认的旧列表保留为 `specified`。
- 未知过敏不会生成餐食候选；食品记录缺少配料或过敏原来源字段时返回 `needs_confirmation`。
- 微行动仍只按用户提供的餐名做文本匹配，界面和 rationale 明确提示餐厅菜品实际配料需要用户核对。

### 推荐真实性

- 软偏好只影响候选排序，不变成安全排除条件。
- 添加食物的建议改为“如果手边有…”，不假设用户已有食材。
- 删除了首页对时间、地点的未实现个性化暗示；当前说明聚焦于用户提供的餐次、选项和已确认边界。
- 已完成行动只产生需要用户确认的偏好线索，不宣称系统自动学习。

### 回顾体验

- Lens 标签改为“已安排餐次、实际记录餐次、已选择的小行动、已反馈行动的完成比例”。
- 计划卡片不再声称预算、时间或库存决定指标。
- 移除重复的指标网格，保留单一 overview、时间线、未知项和下一步。
- “Agent 看到的线索”改为“从这段记录中整理出的线索”。重复阻碍只有在同一餐食/选项上下文重复时才会报告；跨情境只显示中性反馈事实。
- 明确显示当前没有足够可核验营养数据，不从餐名计算热量或宏量营养素。

### 计划与购物

- 计划界面明确为单日编辑器。
- 空的主要食材字段不会回退为餐名，也不会产生伪造的食材购物项。
- 购物面板改称“主要食材库存差额”，说明只覆盖明确输入、同名、相同单位，不自动换算，也不是完整菜谱清单。

## Claim-to-capability matrix

| 产品信息 | 收集位置 | 是否到达生成器/服务 | 当前影响 | 可验证证据 |
|---|---|---|---|---|
| 目标 | Profile onboarding | 目前保存，未用于排序 | 仅用于上下文展示 | `Profile.goal` 与 API profile |
| 预算 | Profile onboarding | 到达 Food 搜索预算过滤 | 仅对有价格来源的食品做过滤 | `search_result` |
| 过敏 | Profile onboarding | 到达安全门 | unknown 停止候选；none/specified 进入评估 | `test_round4_truthfulness.py` |
| 绝对忌口 | Profile onboarding | 到达微行动文本过滤 | 硬约束排除匹配餐名 | `filter_options` |
| 不喜欢 | Profile onboarding | 到达 action ranking | 只降排序，不阻断 | `test_soft_dislike_changes_order_without_becoming_safety_exclusion` |
| 时间/地点 | 当前未收集 | 不到达生成器 | 不应宣称个性化 | 首页 copy |
| 今日精力 | 当前未收集 | 不到达生成器 | 不应宣称精力适配 | 首页 copy |
| 历史反馈 | Action history | 到达 cooldown/dimension/review | 影响冷却与回顾；不自动写长期偏好 | `tools.py`, `preferences.py` |

## 回归状态

本轮新增 5 个后端真值测试，覆盖三态档案、旧空列表、食品来源缺失、软偏好排序、空主要食材购物和跨情境阻碍；与既有测试合计 232 个 Python 测试通过。浏览器 QA 的移动导航、首页 CTA、设置恢复、删除忙碌态和 35 个页面/视口渲染检查均通过。认证 Supabase 流程仍因没有安全 fixture 保持 BLOCKED。

## 剩余限制

- 微行动不是成分级过敏验证，无法证明任意餐厅菜品的隐藏配料。
- 当前前端只提供单日计划；后端 7 日能力不是已完成的多日编辑体验。
- 方向 B 所需的成分、份量和营养来源链尚未实现。
- 远程 GitHub Actions 状态需以推送后的实际工作流结果为准，不能由本地通过替代。

## Round 4.1 closure

本轮进一步修复了来源空字段的可信度判断、计划食材数量与实际摄入数量的串用、过敏未知停止状态、行动实际选项关联和 Review 计划覆盖率。新增字段保持旧 JSON 可读；无法从旧行动中确认选项时不再猜测。具体证据见 `docs/DietLens-Round-4.1-Data-Truth-and-Experience-Closure.md`。
