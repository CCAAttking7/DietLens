# 接口与用例映射

版本：R2-P5候选；接口路径以`/api/v2`为前缀。业务变更走预览与统一提交，表列为主要责任而非客户端可直接写入范围。

| 操作标识 | 方法与路径 | 中文用途 | 需求 | 模块 | 主要表 |
|---|---|---|---|---|---|
| `createTask` | `POST /tasks` | 创建临时任务 | FR-002,FR-010 | 命令与任务 | task_sessions |
| `listTasks` | `GET /tasks` | 列出可恢复任务 | FR-010 | 命令与任务 | task_sessions |
| `getTask` | `GET /tasks/{task_id}` | 读取或恢复任务 | FR-010,FR-013 | 命令与任务 | task_sessions |
| `changeTaskState` | `PATCH /tasks/{task_id}` | 暂停恢复或取消临时任务 | FR-010,FR-013 | 命令与任务 | task_sessions |
| `continueTask` | `POST /tasks/{task_id}/messages` | 提交对话并获取下一步 | FR-001,FR-002,FR-010,FR-013 | 命令与任务 | task_sessions |
| `getProfile` | `GET /profile` | 读取本人确认档案 | FR-001 | 档案与授权 | user_control,profile_revisions |
| `getConsents` | `GET /consents` | 读取当前用途授权 | FR-011 | 档案与授权 | consent_revisions |
| `getCalibration` | `GET /calibration` | 读取校准题库和回答 | FR-001,FR-011 | 档案与授权 | calibration_revisions,interaction_settings |
| `getSettings` | `GET /interaction-settings` | 读取可选交互与退避状态 | FR-008,FR-011 | 微行动 | interaction_settings |
| `getContext` | `GET /contexts/{context_id}` | 读取已确认情境 | FR-003,FR-020 | 档案与授权 | context_snapshots |
| `uploadMedia` | `POST /media` | 上传本地核对图片 | FR-002,FR-012 | 食品证据 | media_assets,task_sessions |
| `getMediaStatus` | `GET /media/{asset_id}` | 读取图片有效性 | FR-011,FR-012 | 食品证据 | media_assets |
| `readMediaContent` | `GET /media/{asset_id}/content` | 在有效期内核对本人原图 | FR-010,FR-011,FR-012 | 食品证据 | media_assets,user_control |
| `searchFoodFacts` | `GET /foods` | 检索已核对食品证据 | FR-002,FR-015 | 食品证据 | food_observations,food_fields,source_references |
| `getFoodFact` | `GET /foods/{observation_id}` | 读取指定食品证据版本 | FR-002,FR-012,FR-015 | 食品证据 | food_observations,food_fields,field_sources |
| `getSource` | `GET /sources/{source_id}` | 读取当前可用来源 | FR-012,FR-015 | 食品证据 | source_references,media_assets |
| `listIngredients` | `GET /ingredients` | 读取标准食材目录 | FR-018,FR-019 | 计划与准备 | ingredients |
| `resolveIngredients` | `POST /ingredients/resolve` | 核对已有食材或形成临时匹配 | FR-018,FR-019 | 计划与准备 | task_sessions,ingredients |
| `parseFood` | `POST /analyses/food` | 解析标签菜单或餐食图片 | FR-002,FR-003,FR-012,FR-013 | 外部工具执行 | task_sessions,constraint_assessments |
| `compareFoods` | `POST /analyses/comparisons` | 比较同口径营养 | FR-015,FR-013 | 外部工具执行 | task_sessions,constraint_assessments |
| `recommendMenu` | `POST /analyses/menus` | 筛选现实菜单 | FR-003,FR-016,FR-013 | 外部工具执行 | task_sessions,constraint_assessments |
| `proposePlan` | `POST /analyses/plans` | 形成分步日周计划草案 | FR-003,FR-017,FR-013 | 外部工具执行 | task_sessions,constraint_assessments |
| `proposeAction` | `POST /analyses/actions` | 形成完整微行动候选 | FR-003,FR-004,FR-008,FR-013 | 外部工具执行 | task_sessions,constraint_assessments |
| `explainReview` | `POST /analyses/review-text` | 表述已计算的期间回顾 | FR-009,FR-013 | 外部工具执行 | task_sessions,constraint_assessments |
| `listPlans` | `GET /plans` | 读取计划及当前范围 | FR-017 | 计划与准备 | plan_heads,plan_revisions,slot_assignments |
| `getPlan` | `GET /plans/{plan_id}` | 读取指定计划版本 | FR-017,FR-020 | 计划与准备 | plan_heads,plan_revisions,planned_meals,planned_foods |
| `getPreparationDraft` | `GET /plans/{plan_id}/preparation-preview` | 只读汇总需求与库存差额 | FR-018,FR-019 | 计划与准备 | ingredient_requirements,inventory_revisions,preparation_lists |
| `getPreparation` | `GET /preparations/{list_id}` | 读取准备清单及独立状态 | FR-018,FR-020 | 计划与准备 | preparation_lists,preparation_lines |
| `listInventory` | `GET /inventory` | 读取人工核对库存 | FR-019 | 计划与准备 | inventory_heads,inventory_revisions |
| `listMealRecords` | `GET /meal-records` | 读取本人实际用餐 | FR-014 | 实际餐食 | meal_heads,meal_revisions,reported_foods |
| `getMealRecord` | `GET /meal-records/{record_id}` | 读取实际用餐及多食物 | FR-014,FR-020 | 实际餐食 | meal_heads,meal_revisions,reported_foods |
| `prefillMeal` | `GET /plans/{plan_id}/meal-prefill` | 只读预填个人餐食草稿 | FR-014,FR-020 | 实际餐食 | planned_foods,plan_revisions |
| `listActions` | `GET /actions` | 读取本人行动与有效反馈 | FR-005,FR-006,FR-007 | 微行动 | micro_actions,action_decisions,action_windows,execution_revisions |
| `getAction` | `GET /actions/{action_id}` | 读取行动窗口及执行修订 | FR-006,FR-007 | 微行动 | micro_actions,action_windows,execution_revisions |
| `listLearningCandidates` | `GET /learning-candidates` | 读取待核对偏好与情境线索 | FR-008,FR-011 | 微行动 | learning_candidates,learning_evidence |
| `listPreferences` | `GET /preferences` | 读取本人稳定偏好规则 | FR-001,FR-008 | 微行动 | preference_rule_revisions |
| `getExpectedMeals` | `GET /expected-meals/{week_start}` | 读取已确认预期餐次分母 | FR-009 | 回顾查询 | expected_schedules,expected_slots |
| `listRecoveryEpisodes` | `GET /recovery-episodes` | 读取确认恢复周期 | FR-009 | 回顾查询 | recovery_episodes,recovery_exclusions |
| `getPeriodReview` | `GET /reviews` | 按一致截点计算期间回顾 | FR-009,FR-011 | 回顾查询 | user_control,meal_revisions,execution_revisions,action_windows,expected_slots,week_presentations,recovery_episodes |
| `previewCommand` | `POST /command-previews` | 预览业务变更及依赖影响 | FR-001,FR-003,FR-005,FR-010,FR-011,FR-014,FR-017,FR-018,FR-019,FR-020 | 命令与任务 | task_sessions,user_control |
| `commitCommand` | `POST /commands` | 明确确认并原子提交预览 | FR-001,FR-002,FR-003,FR-004,FR-005,FR-006,FR-007,FR-008,FR-009,FR-010,FR-011,FR-012,FR-013,FR-014,FR-015,FR-016,FR-017,FR-018,FR-019,FR-020 | 命令与任务 | command_receipts,audit_events,user_control |
| `getCommandReceipt` | `GET /command-receipts/{operation_key}` | 按原键查提交结果 | FR-010,FR-013 | 命令与任务 | command_receipts,user_control |
| `getDataJob` | `GET /data-jobs/{job_id}` | 查询导出删除的真实进度 | FR-011 | 期限与数据控制 | data_control_jobs,user_control |
| `downloadExport` | `GET /data-jobs/{job_id}/download` | 认证后下载本人导出文件 | FR-011 | 期限与数据控制 | data_control_jobs |
| `getHealth` | `GET /health` | 读取最小运行状态 |  | 请求与身份 |  |

## 统一确认入口的命令类型

每种类型的完整输入在OpenAPI的CommandIntent中定义，不能把任意表名或工具名当命令。

| 命令标识 | 用户确认的变化 | 输入结构 | 需求 | 责任模块 | 主要业务表 |
|---|---|---|---|---|---|
| `profile.confirm` | 确认或修订档案 | `ProfileData` | FR-001 | 档案与授权 | profile_revisions,user_control |
| `consent.change` | 变更用途授权 | `ConsentInput` | FR-011 | 档案与授权 | consent_revisions,user_control |
| `calibration.answer` | 确认校准回答 | `CalibrationAnswer` | FR-001,FR-011 | 档案与授权 | calibration_revisions |
| `settings.change` | 修改可选交互开关 | `SettingsInput` | FR-008,FR-011 | 微行动 | interaction_settings |
| `context.confirm` | 确认当前情境 | `ContextInput` | FR-003,FR-020 | 档案与授权 | context_snapshots |
| `food.confirm` | 逐字段核对食品 | `FoodInput` | FR-002,FR-012,FR-015,FR-016 | 食品证据 | food_observations,food_fields,field_sources,source_references |
| `plan.confirm` | 确认或替换计划 | `PlanInput` | FR-017,FR-020 | 计划与准备 | plan_heads,plan_revisions,planned_meals,planned_foods,ingredient_requirements,slot_assignments |
| `preparation.confirm` | 核对准备采购清单 | `PreparationInput` | FR-018 | 计划与准备 | preparation_lists,preparation_lines,preparation_sources |
| `preparation.status` | 报告已购或已准备 | `PreparationStatusInput` | FR-018,FR-019,FR-020 | 计划与准备 | preparation_lists,preparation_lines |
| `inventory.confirm` | 核对或修订库存 | `InventoryInput` | FR-019 | 计划与准备 | inventory_heads,inventory_revisions,preparation_lists |
| `meal.confirm` | 确认或修订个人用餐 | `MealInput` | FR-014,FR-020 | 实际餐食 | meal_heads,meal_revisions,reported_foods |
| `action.decide` | 采纳跳过或替代候选 | `ActionDecisionInput` | FR-004,FR-005,FR-020 | 微行动 | micro_actions,action_decisions,action_windows,interaction_events |
| `action.window` | 显式修正行动窗口 | `WindowInput` | FR-007,FR-008 | 微行动 | micro_actions,action_windows |
| `action.feedback` | 报告或更正执行 | `ExecutionInput` | FR-006,FR-007 | 微行动 | micro_actions,execution_revisions |
| `learning.decide` | 核对偏好或情境候选 | `LearningDecisionInput` | FR-008,FR-011 | 微行动 | learning_candidates,preference_rule_revisions,learning_evidence |
| `preference.confirm` | 修订或停用稳定规则 | `PreferenceInput` | FR-001,FR-008 | 微行动 | preference_rule_revisions |
| `expected.confirm` | 确认预期餐次分母 | `ExpectedInput` | FR-009 | 回顾查询 | expected_schedules,expected_slots |
| `recovery.confirm` | 确认恢复起止与排除 | `RecoveryInput` | FR-009 | 回顾查询 | recovery_episodes,recovery_exclusions |
| `week.present` | 确认连续周呈现 | `WeekInput` | FR-009,FR-011 | 回顾查询 | week_presentations |
| `data.export` | 请求导出本人数据 | `ExportInput` | FR-011 | 期限与数据控制 | data_control_jobs |
| `data.delete` | 确认范围后请求删除 | `DeleteInput` | FR-011,FR-020 | 期限与数据控制 | user_control,data_control_jobs |
| `data.renew` | 确认业务保留续期 | `RenewInput` | FR-011 | 期限与数据控制 | profile_revisions,media_assets,consent_revisions,context_snapshots,source_references,food_observations,constraint_assessments,ingredients,plan_heads,inventory_heads,preparation_lists,meal_heads,micro_actions,reminder_events,interaction_settings,interaction_events,learning_candidates,preference_rule_revisions,calibration_revisions,expected_schedules,recovery_episodes,week_presentations,audit_events |
| `ingredient.confirm` | 确认标准食材身份 | `IngredientInput` | FR-018,FR-019 | 计划与准备 | ingredients |
