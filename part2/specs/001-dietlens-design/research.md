# 架构选型研究记录

日期：2026-11-17；状态：P3决策证据。正文结论见[系统架构](../../docs/design/04-system-architecture.md)。

## 事务与并发

SQLite的WAL模式允许读写并行，但仍只有一个写者；长读事务会影响检查点，WAL要求同一主机上的共享内存机制。使用本机文件、短写事务、有界忙等待。[官方WAL说明](https://www.sqlite.org/wal.html)

SQLite事务可能因锁竞争失败，事务开始和提交失败需要明确处理。提交成功后的响应丢失应通过持久回执恢复，不能重做一份业务写入；后半句是本项目设计推导。[官方事务说明](https://www.sqlite.org/lang_transaction.html)

PostgreSQL默认读已提交隔离为每条语句提供快照，不能直接保证跨对象业务不变量。条件版本更新、受影响行数检查及共同行锁属于本项目的并发策略；若改用可串行化事务，还需完整重试策略。[官方隔离说明](https://www.postgresql.org/docs/current/transaction-iso.html)

行锁会阻塞竞争写入，锁顺序影响死锁。本项目推导：撤回、删除和业务写入都先锁定用户处理控制，再按固定顺序锁定对象，提交前检查当前权限；外部调用放在锁外。权限撤回无法收回已经发往外部的内容，因此还要在发送边界检查并最小化输入。[官方锁说明](https://www.postgresql.org/docs/current/explicit-locking.html)

## 一致提交与恢复

业务事实、任务状态、审计和幂等回执同库提交。以用户和操作标识唯一、请求摘要一致为重复识别条件；只读回执查询仍需当前身份与资源授权。该组合是为满足本项目需求的设计，不是数据库默认提供的业务能力。暂不引入跨库消息与独立事件投影。

## 模型与数据权威

模型不决定硬约束、执行事实或统计分母。模型及食品查询可替换；写入由结构化核对和版本绑定控制。来源失效、授权变化或超时后返回的候选须丢弃或重新核对。这里依据已确认需求和领域模型，不依赖某家服务的即时价格或型号。

## 建模工具与实际使用

已安装Structurizr命令提供validate与export；模型在项目独立挂载目录解析，导出PlantUML、Mermaid和JSON，不载入共享示例工作区。[官方命令说明](https://docs.structurizr.com/cli)、[导出说明](https://docs.structurizr.com/export)、[DSL语法](https://docs.structurizr.com/dsl/language)

图稿再由本地PlantUML服务渲染，记录源摘要和响应状态。[官方编码说明](https://plantuml.com/text-encoding)、[时序图说明](https://plantuml.com/sequence-diagram)

模型验证结论见图目录的构建记录；事务和容量推导必须在后续PoC中验证。所有选型当前为P3候选，未实施业务改造。
