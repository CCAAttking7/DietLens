# DietLens Agent 工作台

DietLens 是一个由 Harness 编排的饮食陪伴工作台。它把长期目标、当前餐次、快速记录、未来计划、食品资料和阶段回顾放在同一套可恢复任务模型中：

```text
理解目标 → 看清现状 → 比较路径 → 用户确认 → 执行或记录 → 回顾调整
```

当前主要任务类型包括：

- `quick_log`：快速记录已经发生的餐食，支持预览、确认、恢复、再记一次和版本化修改；
- `micro_action`：从当前餐事情境生成低负担行动，用户确认后再反馈；
- `plan`：安排未来餐次，独立生成购物清单，不伪造实际摄入；
- `explore`：按来源查询食品资料，缺失字段保持未知；
- `reflect`：回看计划、实际餐食和行动反馈，形成下一步建议。

工作台还提供跨入口恢复：未完成的小行动会在首页提示继续；快速记录和计划保留各自的待确认任务；回顾时间线区分“已明确关联、同餐次待核对、计划外、待记录”，并可将计划餐次一键预填到实际记录。

核心微行动闭环仍然是：

`用户档案/过敏约束 → 当前餐事情境 → 安全候选 → 用户采纳/跳过 → 执行自述 → 回顾`

实现重点来自 SRS 的 FR-003、FR-005、FR-006、FR-007、FR-010、FR-013、FR-020 和 NFR-010/NFR-015：

- `Harness` 是有限状态控制面，负责状态迁移、工具调用上限、失败停止和事件记录。
- `tools.py` 是确定性业务层，负责约束过滤、候选生成、决策/反馈写入和回顾统计。
- `DietLensAgent` 只负责意图和对外 API；它不能绕过 Harness 直接改权威状态。
- 所有写入带 operation key，重复请求返回已有结果；计划/实际记录/行动决策/执行结果使用不同对象边界。
- 候选包含 cue、behavior、effort、rationale；过敏命中时不产生受影响候选。
- 事件轨迹对用户只展示确认、选择、提醒、反馈和修正等可理解步骤，模型内部调用不会伪装成用户行为。
- `SQLiteStore` 提供真实数据库持久化；默认 WAL 和参数化 SQL，表按 profiles/tasks/actions/events/operations 分离。
- `cleaning.py` 只做可解释标准化和去重；未知字段仍保持未知，不把缺失值填成 0，也不做医学推断。

## 运行

```bash
python3 demo.py
```

终端冷启动：

```bash
python3 cli.py --refresh-china
```

数据源适配器：`OpenFoodFactsSource` 使用官方 API v3/v2，`ChinaCDCFoodCompositionSource` 从中国疾控公共卫生科学数据中心下载官方食物编码资源并建立本地索引。它们统一输出带来源、来源 ID、抓取时间和原始响应的 `FoodRecord`，未知营养字段保留为 `None`。USDA 不属于当前运行依赖。

使用 SQLite：

```python
from dietlens_mvp import DietLensAgent, Harness, SQLiteStore
agent = DietLensAgent(Harness(SQLiteStore("dietlens.db")))
```

测试依赖未预装时，可安装 pytest 后运行：

```bash
python3 -m pytest -q
```

## 当前边界

模型只负责理解、整理和表达；安全判断、数值计算、任务状态、授权和业务写入由确定性服务与 Harness 控制。食品资料不完整时不会自动晋级为安全，份量未知不会按零计算，计划也不会自动变成实际餐食记录。

完整的任务编排模型、恢复协议和用户体验原则见 [docs/product-logic.md](docs/product-logic.md)。开发阶段验收记录见 [docs/development.md](docs/development.md)。
