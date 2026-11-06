# 按任务选择模型

Harness 根据代码确定的任务类型选择模型，模型不能通过自己的输出改变路由。不同任务可以使用不同 Model ID。未配置独立模型的任务沿用 `DIETLENS_MODEL`。

| 配置 | 任务 | 当前接入状态 |
| --- | --- | --- |
| `DIETLENS_MODEL_CONTEXT` | 饮食情境解析、微行动前的字段提取 | 已接 CLI，真实 MiniMax 闭环验证 |
| `DIETLENS_MODEL_FOOD` | 食品查询、菜单字段解析 | 路由已预留，食品解析切片后接入 |
| `DIETLENS_MODEL_PLAN` | 日周计划相关模型步骤 | 路由已预留，阶段 3 接入 |
| `DIETLENS_MODEL_REVIEW` | 综合回顾解释相关模型步骤 | 路由已预留；当前回顾由确定性代码生成 |

例如当前已验证的本地配置：

```dotenv
DIETLENS_MODEL=DeepSeek-V4.1-Flash
DIETLENS_MODEL_JSON_MODE=false
DIETLENS_MODEL_CONTEXT=MiniMax-M3.1-Flash
DIETLENS_MODEL_CONTEXT_JSON_MODE=true
```

`*_JSON_MODE` 可针对每条路由覆盖全局 `DIETLENS_MODEL_JSON_MODE`，留空继承。其他任务可以分别设置用户套餐中真实可用的 Model ID；不依据模型名称推定质量或延迟。计划和回顾的路由配置不代表相应业务模块已经实现，也不把当前情境解析提示词当作完整计划生成器。

当前各路由共用平台 Base URL、Key、超时和应用内 DNS 覆盖。跨服务商的独立凭据、每模型费用配置、复杂度自动分类和能力探测后续扩展。

每个步骤只调用选定模型，不同时请求多个模型，也不会因失败自动切到另一个收费模型。输出必须通过 Schema，失败进入明确的手动路径。审计保存本次实际模型名及 token 用量，未返回的用量保留未知。所有业务计算、约束检查、版本冲突与确认写入仍由 Harness 和确定性工具完成。

语音、OCR、向量与重排需要各自的请求协议、输入输出和权限边界，将按后续业务接入专用适配器，不走文本 Chat Completions 路由。

## 真实验证

2026-10-31，MiniMax 普通文本模式返回了不符合 Schema 的输出，被系统拒绝且没有写行动；开启 JSON mode 后，同一合成情境提取成功。成功请求报告输入 494 token、输出 85 token。

任务 `4664bb44-4aa5-4f49-88d5-014d2499c0f1` 保存在 `data/synthetic_route.db`，使用用户此前确认的合成午餐情境和 unknown 反馈：采纳 1，完成 0，反馈覆盖 0。数据库重启后重复反馈与回顾结果一致。DeepSeek 的既有实测见 `docs/model-integration.md`。这些是功能联调结果，不是模型性能基准。
