# 设计复核与后续验证指南

## 查看当前成果

先读[架构正文](../../docs/design/04-system-architecture.md)，再对照[领域反例](../../docs/design/domain-scenario-review.md)。架构图源与构建记录位于docs/design/diagrams/architecture；PlantUML、Mermaid和JSON均由同一DSL导出，三张时序图单独维护。

## 重建模型

在D:/DietLens执行：

```powershell
python part2/tools/build_architecture.py
python part2/tools/check_chinese_artifacts.py
```

前提：本机Docker可运行已安装Structurizr镜像，PlantUML服务位于localhost:8082。脚本只挂载part2中的架构目录，记录共享示例工作区摘要前后值；不会向共享模型导入本项目。生成的是设计图与检查文件，不启动产品、不创建业务数据库。

## 后续PoC的断言

| 场景 | 应验证结果 |
|---|---|
| 同键并发与响应丢失 | 一份业务提交、一份回执；恢复后返回同一提交 |
| 不同键同版本并发 | 仅合法版本提交，另一请求返回冲突并重新核对 |
| 写入中撤回/删除 | 按同一处理控制顺序线性化，之后不产生新的未授权处理 |
| 慢模型/资料源 | 超时后不持有写锁；迟到候选不自动提交 |
| 同餐多记录/多人准备 | 覆盖槽位去重；准备量不充当个人摄入 |
| 跨周迟报/修改窗口 | 执行周按日期；结束队列重算；未知不补零 |
| SQLite/Pg锁竞争 | 有界等待、失败回滚、不改用另一库 |
| 来源删除与回顾失效 | 删除传播与重算可恢复，响应不引用已撤回证据 |

这些是后续验收方案，目前仅执行模型解析、导出、渲染、中文显示及引用检查。性能数值与容量上限要通过PoC测量，不在本阶段填造结果。
