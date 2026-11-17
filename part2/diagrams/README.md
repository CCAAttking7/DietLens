# 设计模型索引

十张模型均提供可编辑 DOT 源文件、`rendered/` 中的 SVG 矢量图和 PNG。M01A 为当前 main 5ecd03f 的结构；其余为目标设计，其中 M02 分组展示当前本地与目标托管部署。

| 模型 | 内容 |
|---|---|
| M01A-current | 当前逻辑架构 |
| M01B-target | 目标逻辑架构及统一命令策略 |
| M02-deployment | 本地与托管部署节点和连接 |
| M03-domain | 领域对象、关键属性与引用关系 |
| M04-action | 微行动生成、确认及反馈协作 |
| M05-plan-record | 计划、准备、实际餐食及取消分支 |
| M06-recovery | 原子提交、回滚、响应丢失及恢复 |
| M07A-task | 通用任务交互进度 |
| M07B-execution | 行动决策与执行状态分层 |
| M08-user-flow | 独立入口、跨业务用户流程及恢复分支 |

领域图箭头表示有标签的引用或关系，非 UML 继承。M04–M06 采用编号协作流程和活动式分支表达交互，非带生命线的 UML 时序图。每个流程的调用与状态细节见 `../04_domain_and_interactions.md`。

在仓库根目录执行 `python part2/tools/render_design_models.py` 可重建全部源图和导出文件，依赖 Python 与 Graphviz dot。M08 与七张界面稿已完成，见 `../06_ui_ux_design.md`。
