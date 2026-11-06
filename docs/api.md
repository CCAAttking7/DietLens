# DietLens API 边界

本地服务默认监听 `http://localhost:8000`，浏览器只调用 FastAPI，不直接写 SQLite 或 Supabase 表。设置 `DIETLENS_AUTH_MODE=supabase` 后，所有带用户归属的接口都要求 `Authorization: Bearer <Supabase access token>`，并以 Auth 返回的用户 ID 校验请求中的 `user_id`。

## 核心流程

| 方法 | 路径 | 用途 |
| --- | --- | --- |
| `GET` | `/health` | 查看当前实际存储后端 |
| `POST` | `/api/profile/preview` | 生成档案差异草稿 |
| `POST` | `/api/profile/confirm` | 用户确认后保存档案 |
| `POST` | `/api/tasks` | 创建陪伴任务 |
| `POST` | `/api/tasks/{task_id}/messages` | 解析用户描述，返回待核对意图 |
| `POST` | `/api/tasks/{task_id}/context` | 用户确认餐次和选项 |
| `POST` | `/api/tasks/{task_id}/confirm` | 用户采纳候选行动 |
| `POST` | `/api/tasks/{task_id}/feedback` | 提交执行反馈 |
| `GET` | `/api/tasks/{task_id}/review` | 查看单次回顾 |
| `GET` | `/api/reviews?user_id=...&period=day\|week\|month` | 查看综合回顾 |

## 资料与饮食对象

| 方法 | 路径 | 用途 |
| --- | --- | --- |
| `GET` | `/api/foods/search?user_id=...&q=...` | 只读查询食品来源和安全门结果 |
| `POST` | `/api/plans/preview` | 生成计划草稿 |
| `POST` | `/api/plans/{plan_id}/confirm` | 确认计划 |
| `POST` | `/api/plans/{plan_id}/cancel` | 取消计划草稿 |
| `POST` | `/api/plans/{plan_id}/shopping-list` | 生成采购清单 |
| `GET/POST` | `/api/inventory` | 查看或手动调整库存 |
| `POST` | `/api/meal-records/preview` | 生成实际餐食记录草稿 |
| `POST` | `/api/meal-records/confirm` | 用户确认后保存实际餐食 |

## 数据控制

`POST /api/export` 的请求体为 `{"user_id":"..."}`，返回结构化 JSON，包括档案、版本、授权事件、任务、事件、行动、食品观察、计划、采购清单、库存和实际餐食记录。

`POST /api/delete` 的请求体必须为 `{"user_id":"...","confirmed":true}`。缺少 `confirmed: true` 时服务返回 `delete_confirmation_required`；删除成功后当前用户的业务对象不再可导出。Web 设置页会在请求前再次要求浏览器确认。

所有写入仍由 Harness 或对应确定性服务执行。模型只负责结构化理解和表达，不能绕过用户确认门，也不能直接修改档案、计划、库存或实际餐食记录。
