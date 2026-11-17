# 接口数据形状正反例

这些是按OpenAPI结构验证的虚构数据，不是服务实现验收。跨字段计算、真实授权、版本竞争与恢复另按正文验证。

| 场景 | 结构 | 期望 | 静态结果 |
|---|---|---|---|
| 一次午餐三条食物 | `PreviewRequest` | 接受 | 符合 |
| 明确确认只引用原预览 | `CommitRequest` | 接受 | 符合 |
| 未知数量保留单位 | `Quantity` | 接受 | 符合 |
| 已知零库存数量 | `InventoryQuantity` | 接受 | 符合 |
| 未知数量不能带零 | `Quantity` | 拒绝 | 符合 |
| 已知量必须有单位 | `Quantity` | 拒绝 | 符合 |
| 数量负数拒绝 | `Quantity` | 拒绝 | 符合 |
| 数量不能为小数定点整数 | `Quantity` | 拒绝 | 符合 |
| 数量超过安全整数范围 | `Quantity` | 拒绝 | 符合 |
| 未知库存仍须口径 | `InventoryQuantity` | 拒绝 | 符合 |
| 实际餐食不得空食物 | `MealContent` | 拒绝 | 符合 |
| 客户端不能自报用户 | `PreviewRequest` | 拒绝 | 符合 |
| 确认不能夹带修改后的业务内容 | `CommitRequest` | 拒绝 | 符合 |
| 取消不走提交入口 | `CommitRequest` | 拒绝 | 符合 |
| 确认草稿版本不能为零 | `CommitRequest` | 拒绝 | 符合 |
| 未注册命令拒绝 | `PreviewRequest` | 拒绝 | 符合 |
| 不确定自述不携执行日期 | `ExecutionWithdraw` | 接受 | 符合 |
| 完成必须有执行日期 | `ExecutionReport` | 拒绝 | 符合 |
| 撤回自述不能伪造执行日期 | `ExecutionWithdraw` | 拒绝 | 符合 |
| 比例零分母用未知 | `Ratio` | 接受 | 符合 |
| 已知比例不能零分母 | `Ratio` | 拒绝 | 符合 |
| 采购状态至少明确改一项 | `PreparationStatusInput` | 拒绝 | 符合 |
| 采购和准备可独立改动 | `PreparationStatusInput` | 接受 | 符合 |
| 采纳必须核对窗口 | `ActionDecisionInput` | 拒绝 | 符合 |
| 跳过不能夹带采纳窗口 | `ActionDecisionInput` | 拒绝 | 符合 |
| 校准不能只交题目而无回答 | `CalibrationAnswer` | 拒绝 | 符合 |
| 校准空选项不是回答 | `CalibrationAnswer` | 拒绝 | 符合 |
| 范围删除必须列对象 | `DeleteInput` | 拒绝 | 符合 |
| 全量删除不能夹带选择性目标 | `DeleteInput` | 拒绝 | 符合 |
| 指定一餐可独立表达 | `PlanContent` | 接受 | 符合 |
| 选定槽位不得重复 | `PlanContent` | 拒绝 | 符合 |
| 仅一日或七日模式 | `PlanContent` | 拒绝 | 符合 |
| 依赖失败可无结果且明确停止 | `AnalysisResponse` | 接受 | 符合 |
| 分析判别类型可解析：food | `AnalysisResult` | 接受 | 符合 |
| 分析判别类型可解析：comparison | `AnalysisResult` | 接受 | 符合 |
| 分析判别类型可解析：menu | `AnalysisResult` | 接受 | 符合 |
| 分析判别类型可解析：action | `AnalysisResult` | 接受 | 符合 |
| 分析判别类型可解析：review_text | `AnalysisResult` | 接受 | 符合 |
| 空计划阶段可保留缺口草案 | `AnalysisResult` | 接受 | 符合 |
| 食品冲突不能装作确定数值 | `FoodField` | 拒绝 | 符合 |
