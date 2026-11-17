# R2 领域图

本目录的D01–D04是目标领域模型，已沿用为后续阶段基线。图中中文对象名与[词表](../../../GLOSSARY.md)及[正文](../03-domain-model.md)对应；源文件仅在内部别名保留技术标识。未将当前代码类或物理表当作目标领域。

| 源文件 | 业务主题 | 导出 |
|---|---|---|
| [D01](D01-context-evidence.puml) | 档案、用途授权、当前情境和食品证据 | [SVG](rendered/D01-context-evidence.svg)、[PNG](rendered/D01-context-evidence.png) |
| [D02](D02-meals-preparation.puml) | 未来计划、准备食材、库存与个人实际自述 | [SVG](rendered/D02-meals-preparation.svg)、[PNG](rendered/D02-meals-preparation.png) |
| [D03](D03-actions-learning.puml) | 微行动、窗口、执行修订、偏好及回顾 | [SVG](rendered/D03-actions-learning.svg)、[PNG](rendered/D03-actions-learning.png) |
| [D04](D04-action-lifecycle.puml) | 行动决策与执行生命周期 | [SVG](rendered/D04-action-lifecycle.svg)、[PNG](rendered/D04-action-lifecycle.png) |

重建：仓库根目录运行 `python part2/tools/render_domain_models.py`。脚本只将本目录虚构设计内容送到 `http://localhost:8082` 的PlantUML服务，保存PUML源、SVG/PNG及[渲染记录](render-manifest.json)，不更改共享工作区。

语法依据：[PlantUML类图](https://plantuml.com/class-diagram)、[文本编码](https://plantuml.com/text-encoding)。采用标准关系、多重性与状态迁移，组合关系不代表物理删除级联。HTTP成功后另外检查SVG结构、错误文本和PNG签名；业务语义依靠正文与场景走查。P3架构和时序见architecture目录；P4物理ER见database目录，二者不替代领域模型。
