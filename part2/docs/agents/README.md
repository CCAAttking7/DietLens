# 本地文件 设计上下文

当前设计目标根目录：`D:/DietLens/part2`。使用本地文件记录上下文，不接入外部任务服务。

## 路径

- 设计阶段与确认：`../design/README.md`。
- 原需求：`../../../DietLens_SRS.pdf`（相对此文件；作业一只读）。
- 权威需求：`../../specs/001-dietlens-design/spec.md`；设计阶段入口 `../design/02-requirements.md` 只引用。其他设计正文在 `../design/` 按阶段确认。
- 旧稿：part2 顶层 01–07、diagrams 和 ui，保留为参考。
- 术语表：`../../GLOSSARY.md`；领域入口 `../../domain-model.md`，权威正文 `../design/03-domain-model.md`。
- API 及数据设计：计划放 `../../api/`、`../../database/`，当前尚未创建。

此文件是本地路径与范围说明，不宣称已配置任何外部平台或已执行专业工具集成。专业 Skill 后续按实际阶段读取；每一事实只在对应权威正文定义，其余采用引用。

Spec Kit已在本目标根目录初始化，版本1.4.1；官方前置检查确认REPO_ROOT为D:/DietLens/part2。不得把返回的特征名当作实际Git分支；当前Git仍为main。
