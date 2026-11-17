# 旧稿审查与工具使用计划

日期 2026-11-17；审查范围为 part2 上一轮设计及新工作台能力。属于设计完整性审查，不是运行或生产验收。

## 1. 旧稿保留与改进清单

| 发现 | 依据 | 改进产物 |
|---|---|---|
| 需求编号和用例已覆盖 | 01_requirements_and_traceability.md | 保留编号，区分确认的需求与 CHG 提案，建立唯一权威正文 |
| 术语分散于段落和图 | 04_domain_and_interactions.md | 领域术语表，明确餐次、餐食条目、食材、行动窗口等概念 |
| 域图缺少完整身份、基数及业务行为 | M03-domain.dot 和属性表 | 实体/值对象/聚合、不变量、反例；另做物理映射 |
| 协作流程不是标准时序 | M04–M06 及 diagrams/README.md 的明确说明 | PlantUML 生命线、同步返回、分支、事务和失败路径 |
| 架构图尚无 C4 分层模型 | M01A/B、M02 | Structurizr DSL 的 Context/Container/Component/Deployment |
| 数据关系没有字段及约束落地 | 原稿无设计 SQL、索引字典 | 只设计 SQL 与 ER，唯一键、外键、空值、版本、删除范围明确 |
| 命令信封没有可校验接口规范 | 04 章恢复协议为文字 | OpenAPI、错误模型、幂等/确认/版本契约及规范检查 |
| 状态图尚未给出完整守卫表 | M07A/B | 触发、角色、前置版本、授权、结果、失败及恢复；明确修正是否新任务 |
| UI 只有静态示意 | ui/README.md 明确不可点击 | 确认方向后补可编辑交互原型，覆盖反馈、未知、冲突与取消 |
| ADR 表混合业务规则和架构取舍 | 03_architecture_and_decisions.md | 仅高成本、存在真实取舍的决策成独立 ADR，其余归业务规则 |
| 验证方案已有基础，任务链未落地 | 07_risks_and_validation.md | 依赖任务、PoC 与需求/领域/API/界面逐项追踪 |
| 参考文献和最终报告尚未完成 | 既有 README/WORKLOG | 官方原始来源核查、工具反思、摘要和最终版式检查 |

## 2. 工具可用性检查

本轮使用只读命令和 HTTP GET 检查；没有向共享工具导入模型、创建账号或更改项目。

| 能力 | 本轮结果 | 实际检查范围 | 后续用途 |
|---|---|---|---|
| software-design | 已读取 | 个人级 SKILL.md | 阶段、确认与成果协调 |
| domain-modeling | 已读取 | SKILL.md 及术语格式 | 术语和领域不变量 |
| Spec Kit | 命令帮助可用 | 加载工作台当前进程环境后 specify --help 成功 | P1 按需初始化 part2 的正式规格；先核对 init 帮助与已有文件 |
| drawDB :4300 | HTTP 200 | 入口可访问 | 设计 SQL 导入与 ER；不连业务库 |
| Structurizr :8080 | HTTP 200 | 重定向 /workspace/1 可访问 | DSL 架构视图；先检查已有 workspace |
| Swagger Editor :8081 | HTTP 200 | 页面入口可访问 | OpenAPI 编辑；另以校验器验证 |
| PlantUML :8082 | HTTP 200 | 默认示例页面可访问 | 真正的时序/状态源图及导出 |
| Penpot :9001 | HTTP 200 | 页面入口可访问 | 交互原型；登录、创建、导出权限未测 |
| Graphviz / Python / Node | 命令可发现 | 本机路径发现；前轮已有生成记录 | 保留旧稿、辅助图和校验 |
| uipro / redocly / mmdc | 包装入口存在 | 工作台 global-bin 文件可见，未执行校验命令 | P5/P6 按实际命令帮助验证后使用 |

以上 HTTP 检查只证明入口可达；渲染、编辑、导出和规范验证需要使用时分别留证。未发现专门的共享工具连接器，后续按已安装工具的文件接口/本地命令及必要浏览器操作使用，不把页面打开当作成果完成。

## 3. 配置与数据保护

检查时 DietLens 根目录与 part2 均未发现现有 `.specify/`、`specs/` 或 `docs/agents/` 配置；本轮仅创建 part2 内的 本地文件 说明，不初始化 Spec Kit 或拷贝工作台示例。工作台自身的 `.specify/` 与 `examples/` 不属于 DietLens 成果。

保持服务原状；未启动/停止、删除容器或操作 volumes。后续 Structurizr 和 Penpot 的现有内容先检查、保留/备份，再加载当前项目的独立模型。
