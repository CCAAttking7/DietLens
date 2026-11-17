# DietLens 中文接口设计

状态：R2-P5候选，待确认。这里只保存契约、示例和检查记录，没有实现或部署接口。

## 阅读与使用

- [接口设计正文](../docs/design/06-api-design.md)：确认提交、恢复、权限、删除、分页与兼容性。
- [OpenAPI YAML](openapi.yaml)及[等价JSON](openapi.json)：同一契约的两种格式。
- [操作与命令映射](operation-map.md)：45个HTTP操作、23种确认命令的需求及物理表责任。
- [错误恢复目录](error-catalog.md)、[虚构中文示例](examples.json)及[40个数据形状正反例](contract-review.md)。
- [规范校验记录](validation.json)、[工具使用记录](tool-record.json)、[编辑器导出](swagger-editor-export.json)及[编辑器截图](接口契约编辑器.jpg)。

本地Swagger Editor位于http://localhost:8081。先保留当前模型，再导入本目录契约。本轮已保存[原有工具示例备份](reference/编辑器原有示例备份.yaml)；它是工具来源，保留原文，不属于本项目中文业务文稿。契约中的dietlens.invalid仅作设计占位，不能当作已运行服务。

## 重建与静态检查

在D:/DietLens执行：

```powershell
python -m pip install --target part2/tools/.dependencies -r part2/tools/requirements-api.txt
python part2/tools/design_api.py
python part2/tools/review_api.py
python part2/tools/check_chinese_artifacts.py
```

契约由design_api.py维护，生成YAML、JSON及操作映射。改动后需重新载入编辑器并导出对应副本，避免留证指向旧版本。检查脚本不导入api_server.py、不访问业务端点、不创建数据库；库的规范检查与结构正反例不替代未来的服务验收。

## 进入下一阶段

本阶段确认后，P6先讨论中文用户流程、信息结构与视觉方向，再制作可编辑交互原型。当前不生成业务代码、迁移、客户端SDK或PPT。
