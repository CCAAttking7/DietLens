# 数据模型入口

领域规则不重复定义。权威模型见[领域正文](../../docs/design/03-domain-model.md)、[术语表](../../GLOSSARY.md)及[反例审查](../../docs/design/domain-scenario-review.md)。

架构关注的持久化边界为档案与授权、食品证据、计划与准备、个人实际餐食、行动与执行、任务和回执。回顾是基于有效版本的派生查询。跨模块写入由同一事务协调。

P4物理映射候选见[数据库设计](../../docs/design/05-database-design.md)及[数据字典](../../database/data-dictionary.md)。保存了PostgreSQL及SQLite设计SQL，尚未创建业务表、执行迁移或连接业务数据库。
