# DietLens 完整产品开发计划

## 总体目标

把 DietLens 做成一个简体中文、中国用户场景下的饮食管理与微习惯 Agent 产品：

冷启动识别
→ 用户目标、预算、过敏和偏好
→ 当前饮食情境
→ 真实食品资料查询
→ 约束过滤与解释
→ 用户确认
→ 计划/记录/微行动
→ 执行反馈
→ 可追溯回顾

默认技术和产品决策：

- Web 产品，CLI 作为第一阶段调试和演示入口。
- React + TypeScript 前端。
- Python Agent/Harness 后端。
- OpenAI-compatible 模型适配层。
- SQLite 长期使用，采用 Repository 层隔离数据访问。
- 单用户演示，不做真实登录，但所有业务对象保留 user_id。
- 简体中文、中国用户。
- 首版纯文字；图片作为后续可选能力。
- 不依赖 USDA。
- 食品数据采用 Open Food Facts、中国疾控官方资源和用户主动提供的标签/菜单。
- 按 SRS 实现授权、来源、未知、删除和审计边界。

## 一、总体架构

### 1. Agent 层

Agent 只负责：

- 识别用户意图；
- 识别当前任务类型；
- 生成结构化澄清问题；
- 选择候选工具；
- 解释工具结果；
- 生成候选微行动；
- 组织最终回复。

Agent 不允许直接：

- 修改用户档案；
- 保存计划；
- 修改库存；
- 写入餐食记录；
- 保存行动采纳；
- 保存执行反馈；
- 删除或导出资料。

Agent 的输出统一为结构化对象：

{
  "intent": "food_search | menu_recommendation | plan | meal_record | micro_action | review",
  "entities": {},
  "missing_fields": [],
  "candidate_tool": "string",
  "user_message": "string",
  "confidence": 0.0
}

模型输出必须经过 JSON Schema 校验，解析失败时进入澄清或人工继续路径。

### 2. Harness 层

Harness 是产品的安全控制面，采用有限状态机：

created
→ collecting_context
→ validating_constraints
→ retrieving_sources
→ generating_candidates
→ awaiting_user_confirmation
→ writing_business_state
→ awaiting_feedback
→ reviewing
→ completed

异常状态：

needs_clarification
needs_manual_input
partial_result
dependency_failed
budget_exhausted
timeout
conflict
stopped

Harness 负责：

- 工具白名单；
- 工具读写权限；
- 每步模型调用上限；
- 每步工具调用上限；
- 重试次数；
- 超时；
- 费用预算；
- 幂等键；
- 版本冲突；
- 用户确认门；
- 工具结果结构校验；
- 事件记录；
- 任务恢复。

工具注册信息至少包含：

ToolSpec(
    name="search_food",
    access="read",
    requires_confirmation=False,
    timeout_seconds=10,
    max_retries=1,
    idempotent=True,
    input_schema=...,
    output_schema=...
)

所有写工具都必须通过 Harness 的确认状态才能执行。

### 3. 确定性业务层

确定性服务负责：

- 过敏和硬约束过滤；
- 软偏好排序；
- 营养单位换算；
- 价格和预算校验；
- 计划餐次校验；
- 清单汇总；
- 库存差额；
- 餐食记录统计；
- 微行动状态统计；
- 反馈覆盖率；
- 北极星指标；
- 数据删除后的派生结果重算。

模型不参与最终数值计算、状态判断和安全放行。

## 二、核心数据模型

SQLite 采用迁移脚本管理，所有表保留创建时间、更新时间和版本字段。

### 用户与授权

- users
- profile_versions
- consents
- data_retention_policies

字段重点：

- user_id
- profile_version
- goal
- budget
- allergies
- dislikes
- consent_history
- consent_image_transfer
- consent_review_history

### 情境与任务

- tasks
- context_snapshots
- task_events

任务保存：

- 任务类型；
- 当前状态；
- 当前步骤；
- 约束版本；
- 授权快照；
- 工具预算；
- 模型预算；
- 操作键；
- 最后错误；
- 恢复信息。

### 食品和来源

- food_observations
- food_source_records
- food_aliases
- nutrition_facts
- ingredient_facts

每个字段都保留：

- 来源；
- 来源 ID；
- 抓取时间；
- 单位；
- 原始值；
- 清洗值；
- 是否用户确认；
- 是否未知；
- 商品规格；
- 数据版本。

Open Food Facts 的数据质量必须按“候选资料”处理，不能自动解除过敏限制。官方文档明确说明其数据由用户贡献且不保证完整性和准确性。Open Food Facts API 文档

中国数据采用中国疾控公共卫生科学数据中心的官方资源下载和本地索引；下载权限、资源版本和更新时间必须记录。中国食物成分数据库

### 饮食业务对象

- plans
- plan_items
- shopping_lists
- shopping_list_items
- inventory_items
- meal_records
- meal_record_versions

必须保持：

计划 ≠ 采购清单 ≠ 库存 ≠ 实际餐食记录

保存计划不能生成实际摄入；勾选采购不能扣库存；库存变化不能修改历史餐食记录。

### 微行动对象

- micro_actions
- action_decisions
- action_executions
- action_adjustment_events
- action_preference_rules

状态严格区分：

proposed
adopted
skipped
pending_feedback
complete
partial
not_done
unknown
superseded

采纳不等于完成；跳过不等于失败；无反馈不等于未完成。

## 三、外部数据源和数据处理

### Open Food Facts

实现：

- 条码查询；
- 产品详情；
- 结构化搜索；
- 配料；
- 过敏原；
- 营养字段；
- 产品规格；
- 来源和抓取时间；
- 请求限流；
- 缓存；
- 失败降级。

官方 API 对产品读取和搜索有不同限流规则，不能实现无限搜索或实时逐字搜索。Open Food Facts API 文档

### 中国数据源

分为两层：

1. 官方基础食物数据：
   - 定期下载；
   - 保存原始文件；
   - 保存数据版本；
   - 建立本地检索索引；
   - 记录更新时间。
2. 用户当前事实：
   - 用户输入的中文标签；
   - 用户提供的菜单；
   - 用户核对的份量；
   - 用户确认的配料；
   - 当前商品或当前餐次来源。

官方基础数据不能自动覆盖当前商品标签；当前标签优先作为本次任务事实。

### 数据清洗

清洗规则：

- 统一空白和大小写；
- 中文别名归一；
- 同义单位归一；
- 数值字段无法解析时保持未知；
- 不把未知填为零；
- 不把图片推断的份量当作实际摄入；
- 不把相似商品自动视为同一商品；
- 不把来源不同的营养数据无提示合并；
- 清洗前后都保存原始值和版本。

## 四、产品分阶段交付

### 阶段 0：工程基础和评测骨架（第 1 周）

目标：把当前 MVP 变成可持续开发的工程基础。

工作：

- 整理 Python 项目结构；
- 建立配置管理；
- 建立 SQLite migration；
- 建立 Repository 接口；
- 移除临时 demo 状态；
- 增加统一错误码；
- 增加结构化日志；
- 固定任务事件格式；
- 建立模型适配器接口；
- 建立 Harness 工具注册表；
- 建立最小回放测试框架。

验收：

- 应用可从空数据库启动;
- 任务可恢复；
- 重复操作不会重复写入；
- 所有状态迁移都有事件；
- 模型不可用时仍可使用确定性路径。

### 阶段 1：冷启动和用户初始化（第 2 周）

目标：

第一次使用
→ 目标
→ 预算
→ 过敏/忌口
→ 偏好
→ 授权
→ 当前情境

实现：

- CLI 冷启动；
- Web 对话入口；
- 目标档案版本；
- 过敏与软偏好分离；
- 每个字段来源；
- 跳过非关键问题；
- 用户确认后保存；
- 修改前后差异预览；
- 取消不写入；
- 资料版本化；
- 用户授权状态。

验收：

- 用户可不上传图片完成初始化；
- 未确认的猜测不进入长期档案；
- 过敏和软偏好不会混为一类；
- 预算未变化时不会重复询问；
- 取消修改后原版本不变。

### 阶段 2：真实食品查询和推荐（第 3-4 周）

目标：

用户输入食品/菜单
→ 查询真实来源
→ 字段清洗
→ 来源展示
→ 约束过滤
→ 候选排序
→ 用户确认

实现：

- Open Food Facts 适配器；
- 中国官方数据适配器；
- 来源注册中心；
- 失败隔离；
- 缓存；
- 过敏硬过滤；
- 预算过滤；
- 缺字段展示；
- 可靠候选不足时停止推荐；
- 手动输入路径；
- 来源冲突提示；
- 同单位营养比较。

验收：

- 明确过敏项不能推荐；
- 关键配料未知时停止受影响推荐；
- 缺营养字段显示未知；
- 固液单位不自动换算；
- 外部服务失败时仍可手动继续；
- 每个候选都能展示来源和理由。

### 阶段 3：日周计划、清单和库存（第 5-6 周）

目标：

餐食候选
→ 1 日/7 日计划
→ 用户替换
→ 采购清单
→ 库存核对

实现：

- 单日计划；
- 7 日计划；
- 日期、人数、餐次；
- 餐次替换；
- 计划版本；
- 旧版本失效；
- 食材标准 ID；
- 同单位汇总；
- 库存差额；
- 采购和准备状态；
- 手动库存调整；
- 冲突检测；
- 清单重新生成。

验收：

- 1 日 3 餐和 7 日 21 餐数量正确；
- 计划保存不会生成实际用餐；
- 同食材同单位可以汇总；
- g 和 mL 不会被无依据合并；
- 库存不会被计划自动扣减；
- 计划版本变化会使旧清单失效；
- 重复生成不会产生重复清单。

### 阶段 4：实际餐食记录（第 7 周）

目标：

计划条目预填
→ 用户确认自述
→ 实际记录
→ 修正/删除
→ 回顾重算

实现：

- 手动输入；
- 计划预填；
- 时间和份量；
- 用户自述来源；
- 未知份量；
- 修正；
- 删除；
- 记录版本；
- 营养覆盖度；
- 记录与计划关联；
- 删除后的统计重算。

验收：

- 计划预填但取消不会创建记录；
- 确认后才创建实际记录；
- 图片不能自动证明已用餐；
- 未知份量不计作零；
- 修正同一记录不会重复计数；
- 删除后回顾同步变化。

### 阶段 5：微行动和反馈闭环（第 8-9 周）

目标：

饮食情境
→ 微行动候选
→ 采纳/跳过/换一个
→ 执行反馈
→ 下一候选调整

实现：

- 四维微行动库：
  - 平替；
  - 顺手加法；
  - 进食顺序；
  - 时序与节律。
- 单主候选；
- cue、behavior、effort、rationale；
- 采纳；
- 修改；
- 跳过；
- 完成；
- 部分完成；
- 未完成；
- 未反馈转 unknown；
- 迟到反馈；
- 同 ID 修正；
- 冷却；
- 提醒退避；
- 偏好排序；
- 长期偏好确认；
- 删除派生排序贡献。

验收：

- 采纳不增加完成数；
- 跳过不增加失败数；
- 到期无反馈为未知；
- 迟到反馈修正原行动；
- 障碍只调整下一候选；
- 反馈不会修改原始记录；
- 用户可以关闭提醒和历史分析。

### 阶段 6：综合回顾和产品工作台（第 10 周）

目标：

计划
+ 实际餐食
+ 营养覆盖
+ 微行动反馈
→ 有边界的综合回顾

实现：

- 日/周/月期间选择；
- 计划和实际分开展示；
- 餐食记录覆盖度；
- 营养覆盖度；
- 微行动反馈覆盖率；
- 已反馈者完成比例；
- 北极星指标；
- 未知单列；
- 来源和分母展示；
- 模型失败时模板回顾；
- 回顾中的下一步入口；
- 计划、记录、行动之间的对象引用。

验收：

- 不把未记录当作未用餐；
- 不把未知当作完成或失败；
- 分母未知时不输出比例；
- 冻结周不增加完成数；
- 删除授权后的历史不再读取；
- 模型不可用时仍可生成基础回顾。

### 阶段 7：React Web 产品（第 11-12 周）

页面：

- Agent 对话首页；
- 用户目标与约束；
- 当前情境；
- 食品查询与比较；
- 菜单推荐；
- 日周计划；
- 准备与库存；
- 实际餐食记录；
- 微行动；
- 执行反馈；
- 综合回顾；
- 数据授权与导出删除。

前端规则：

- 所有写操作显示确认卡片；
- 来源和未知字段可见；
- 状态使用文字和颜色双重表达；
- 断网或后端失败时显示部分结果；
- 支持任务恢复；
- 先保证键盘访问和窄屏布局；
- 前端不自行计算核心营养和状态结果。

## 五、模型适配器计划

定义统一接口：

class ModelProvider(Protocol):
    def complete(
        self,
        messages: list[dict],
        tools: list[dict],
        response_schema: dict
    ) -> ModelResponse:
        ...

实现顺序：

1. StubModelProvider
2. OpenAI-compatible HTTP provider
3. 结构化输出校验
4. 超时和重试
5. Token 与费用记录
6. Prompt 版本管理
7. 模型回放
8. 模型不可用降级

模型调用限制：

- 每步骤最多 2 次模型调用；
- 工具调用最多 3 次；
- 只读瞬时错误最多重试 1 次；
- 写入请求不盲目重试；
- 预算达到 80% 提示；
- 预算达到 100% 停止付费模型调用；
- 任何模型结果都不能绕过确认门。

## 六、Web/API 接口

后端采用 FastAPI 风格接口：

POST /api/tasks
GET  /api/tasks/{task_id}
POST /api/tasks/{task_id}/messages
POST /api/tasks/{task_id}/confirm
POST /api/tasks/{task_id}/feedback
GET  /api/tasks/{task_id}/events

GET  /api/profile
PUT  /api/profile/preview
POST /api/profile/confirm

GET  /api/foods/search
GET  /api/foods/{source}/{source_id}

POST /api/plans
PUT  /api/plans/{plan_id}
POST /api/plans/{plan_id}/confirm

GET  /api/inventory
POST /api/inventory/preview
POST /api/inventory/confirm

POST /api/meal-records/preview
POST /api/meal-records/confirm
PATCH /api/meal-records/{record_id}
DELETE /api/meal-records/{record_id}

GET /api/reviews
GET /api/consents
POST /api/consents
POST /api/export
POST /api/delete

所有写接口需要：

- operation_key;
- expected_version;
- 当前用户归属；
- 当前授权状态；
- Harness 状态允许；
- 幂等结果。

## 七、测试和评测体系

### 单元测试

覆盖：

- 单位换算；
- 预算过滤；
- 过敏过滤；
- 缺失字段；
- 来源冲突；
- 计划餐次；
- 清单汇总；
- 库存差额；
- 反馈状态；
- 去重；
- 冷却；
- 覆盖率；
- 北极星指标。

### Harness 测试

覆盖：

- 工具越权；
- 模型输出非法 JSON；
- 重复提交；
- 写入回执不明；
- 依赖超时；
- 外部服务 503；
- 版本冲突；
- 任务恢复；
- 预算耗尽；
- 最大迭代次数；
- 手动接管。

### 固定数据集

建立四类评测集：

- 食品标签；
- 中文菜单；
- 用户约束；
- 微行动反馈。

每条样例保留：

- 样例 ID；
- 原始输入；
- 预期字段；
- 预期未知字段；
- 预期安全动作；
- 来源；
- 标注版本。

### 发布门槛

必须满足：

- 约束安全案例 100% 正确；
- 状态不变量案例 100% 正确；
- 重复操作不产生重复业务对象；
- 模型故障仍能手动继续；
- 无来源的营养结论禁止展示；
- 计划不被统计为实际摄入；
- 采纳不被统计为完成；
- 删除后派生数据失效；
- 所有写入均有任务、版本、操作键和时间。

## 八、隐私、安全和运行控制

首版按 SRS 实现：

- 分项授权；
- 图片外传单独授权；
- 历史分析单独授权；
- 导出；
- 删除；
- 临时图片自动过期；
- 原始图片不进入普通日志；
- 数据来源和模型调用可审计；
- 医疗诊断、治疗和药物建议直接停止并转交专业服务；
- 不根据用餐时间推断心理或医学状态；
- 业务数据和模型上下文分离；
- 密钥只从环境变量读取；
- SQLite 开启 WAL；
- 所有用户对象带归属字段。

## 九、最终交付物

完成后仓库应包含：

- CLI 演示程序；
- React Web 客户端；
- Python Agent/Harness 服务；
- SQLite schema 和迁移；
- 数据源适配器；
- 模型适配器；
- 工具注册表；
- Prompt 版本；
- 固定评测集；
- 单元测试；
- 集成测试；
- Harness 回放测试；
- Docker Compose；
- .env.example;
- API 文档；
- Agent 架构文档；
- 数据溯源说明；
- SRS 需求追踪矩阵；
- 演示脚本；
- 项目简历说明。

## 明确假设

- 首版不做真实账号登录和多租户，但数据库保留多用户字段。
- 首版不依赖 USDA。
- 首版不做图片识别，后续再接多模态解析。
- 中国基础数据优先使用官方可下载资源；当前商品事实必须以用户标签或菜单核对结果为准。
- SQLite 作为长期数据库，但通过 Repository 层保留未来迁移空间。
- 8-12 周按个人项目节奏推进，每周交付可运行增量。
- Agent/Harness、状态一致性、来源溯源和评测优先级高于视觉细节