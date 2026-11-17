# DietLens 数据库设计产物

状态：R2-P4候选，待确认。只保存设计SQL；没有业务库、迁移执行或真实用户数据。

权威阅读入口为[数据库设计正文](../docs/design/05-database-design.md)和[逐字段字典](data-dictionary.md)。完整DDL见[schema.sql](schema.sql)及[SQLite设计](schema.sqlite.sql)。字段和关系从[共同结构源](model.json)生成；修改通过part2/tools/design_database.py维护后重建，防止两种方言和字典漂移。

## 可编辑模型与图稿

- [中文drawDB模型](drawdb-model.json)：在本地drawDB打开JSON即可编辑。
- [中文导入投影](schema.diagram.sql)：只展示结构，不包含完整检查和延迟语义。
- [工具导出SQL留证](drawdb-export-reference.sql)：从实际画布导出，表字段及复合关系已核对；不作为正式迁移。
- [中文分区图预览](../docs/design/diagrams/database/rendered/数据库图预览.png)：五个分区涵盖全部表；单图SVG可在正文放大。
- [建模画布截图](drawdb-设计画布.jpg)：导入后的中文名称、表数和关系数留证。
- [静态检查结果](validation.json)、[语义走查](scenario-review.md)、[工具使用记录](tool-record.json)。

建模工具内新建了本项目独立画布，未覆盖旧图。循环依赖提示来自当前版本指针及身份/版本反向关系；完整设计用延迟外键并要求同事务完成，未将工具提示隐藏或声称零问题。

## 重建与检查

在D:/DietLens执行：

```powershell
python -m pip install --target part2/tools/.dependencies -r part2/tools/requirements-design.txt
python part2/tools/design_database.py
python part2/tools/review_database.py
python part2/tools/check_chinese_artifacts.py
```

需要现有Graphviz与Pillow；脚本只解析文本、比较模型及生成图稿，不使用数据库驱动，不执行SQL。drawDB部分通过本地网页实际导入/导出，结构变化后需重新导出对应JSON及SQL副本，否则往返比对会失败。

SQLite每个未来连接须启用外键，WAL和写事务模式另由连接初始化配置；本文件不运行相关命令。引擎约束、并发和删除恢复验收留P7计划及后续另行授权的实施。
