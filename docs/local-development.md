# 本地运行

要求 Python 3.11+。首次安装：

```bash
python3 -m venv .venv
.venv/bin/python -m pip install -e '.[test]'
```

不联网演示与测试：

```bash
.venv/bin/python demo.py
.venv/bin/python -m pytest -q
```

CLI 默认持久化至当前目录 `dietlens.db`。`DIETLENS_DB` 和 `DIETLENS_LOG_LEVEL` 从环境变量读取。CLI 默认加载项目根目录 `.env`，也可通过 `--env-file` 指定；已有环境变量优先，`.env.example` 是配置示例。

```bash
.venv/bin/python cli.py --db /tmp/dietlens.db
.venv/bin/python cli.py --db /tmp/dietlens.db --resume TASK_ID
```

首次运行时跳过食品搜索，可通过手动餐食输入离线完成。CLI 会打印任务 ID；暂不反馈时退出，后续用同一数据库和任务 ID 继续。`--refresh-china` 和食品搜索需要网络。

数据库启动时自动按文件名执行 `dietlens_mvp/migrations/*.sql`，并记录于 `schema_migrations`。迁移按追加文件维护，不修改已应用的迁移。旧 MVP 的五张表会原地保留。档案版本、草稿和授权审计已由 003 迁移引入；计划与实际餐食表随对应阶段引入。

业务故障使用 `ToolError.code`，如 `operation_conflict`、`version_conflict`、`confirmation_required`。客户端重试应复用同一操作键和参数；重试已提交的相同请求不检查过时预期版本。同一任务的默认采纳、反馈操作键分别固定；反馈修正将在阶段 5 引入单独版本命令。

此版本是单用户演示，无账号认证。任务恢复通过本地任务 ID 完成，不应直接暴露为公网服务。

档案初始化现在需要预览后明确确认；过敏输入“无”表示明确没有，留空保留未知。已有档案默认复用。单独管理档案与授权：

```bash
.venv/bin/python cli.py --profile
```

历史回顾授权默认关闭，撤回后阻止读取历史和旧回顾缓存。详细交互见 `docs/profile-workflow.md`；按任务配置不同文本模型见 `docs/model-routing.md`。

食品查询会为每个来源使用短期有界缓存，失败来源不会阻断其他来源。查询结果可写入 `food_observations`，其中状态只表示资料安全门结果，不表示已推荐或实际吃过。若档案中的过敏字段留空，CLI 不会自动采用来源候选；输入“无”并确认后才表示明确没有已知过敏。来源字段缺失、冲突以及未知价格/营养会原样显示。

计划、购物清单和库存服务目前可直接通过 Python API 使用：计划先调用 `/api/plans/preview`，确认后调用 `/api/plans/{plan_id}/confirm`，再调用 `/api/plans/{plan_id}/shopping-list`；库存通过 `/api/inventory` 写入，差额通过 `/api/shopping-lists/{list_id}/inventory-diff` 读取。计划接受 1 日或 7 日，可填写其中一餐或多餐；空白餐次保持未计划。不同日期范围的计划分别保留，相同范围的新版本替代旧版；部分重叠的范围会拒绝确认，避免丢失其他日期的安排。库存差额按相同食材与单位计算，不自动扣库存。

实际餐食记录遵循“预填不落库、确认才写入”：`/api/meal-records/preview` 可接收计划条目或手动输入，`/api/meal-records/confirm` 才创建记录；修改使用版本号，删除保留历史版本但从当前回顾中排除。`/api/reviews?user_id=...` 返回计划覆盖、实际记录数和份量未知数。模型情境解析通过 `/api/tasks/{task_id}/messages` 完成，用户需先核对模型提取结果，再推进状态。

反馈修正使用 `/api/tasks/{task_id}/feedback/correct`；提醒状态和发送分别使用 `/api/tasks/{task_id}/reminder` 的 GET/POST，只有档案明确授予 `reminders` 时才可用。提醒不会自动改变档案偏好。

重复反馈产生的长期偏好信号通过 `/api/preferences/suggestions?user_id=...` 读取；它只返回证据和待确认文案。要写入档案，仍必须走档案 preview/confirm 两步。

综合工作台回顾使用 `/api/reviews?user_id=...&period=day|week|month`，可选 `anchor_date=YYYY-MM-DD`。回顾默认使用确定性模板，即使模型不可用也会返回计划/实际分离、未知项和下一步。

数据可携带边界使用 `POST /api/export` 导出当前用户的档案、任务、事件、行动、食品观察、计划、库存和实际餐食记录；使用 `POST /api/delete` 删除当前用户的业务数据，请求体必须包含 `{"user_id":"...","confirmed":true}`，缺少显式确认会返回 `delete_confirmation_required`。Web 设置页的“导出数据”和“删除全部数据”对应这两个接口，删除前还会在浏览器端再次确认。

Web 首页现在提供陪伴一餐、日计划、食品资料、库存、回顾工作台和设置入口。日计划的写入顺序是预览→确认→采购清单；计划取消不会创建实际餐食记录。运行 `npm run dev` 后可直接在浏览器操作。

## Web 与 API

本地 Web 位于 `web/`，使用 React + TypeScript + Vite；API 边界位于 `api_server.py`。默认 API 使用 SQLite，配置 `SUPABASE_DB_URL` 后改用 Supabase Postgres Repository：

```bash
.venv/bin/python -m pip install -e '.[server,cloud]'
.venv/bin/uvicorn api_server:app --reload --port 8000
cd web && npm install && npm run dev
```

浏览器的 `web/.env` 只放 `VITE_SUPABASE_URL` 与 publishable key；Python `.env` 才能放 `SUPABASE_DB_URL` 和服务端配置。启用真实登录时，在根目录 `.env` 设置 `DIETLENS_AUTH_MODE=supabase`、`SUPABASE_URL` 和同一项目的 `SUPABASE_PUBLISHABLE_KEY`。API 会验证 Bearer token，并拒绝请求体/查询参数中的其他 `user_id`；未启用时才保留演示用 `user_id`。

API 的存储模式可用 `DIETLENS_STORAGE=sqlite` 或 `DIETLENS_STORAGE=postgres` 明确指定；默认 `auto` 会优先尝试 Postgres，原生 5432 连接失败时回退到本地 SQLite，保证 HTML 交互演示不被网络代理中断。`/health` 会返回实际使用的存储。

## 生产 Web 加载检查

开发服务器不会体现生产分包行为。检查按需加载时，保持本地 API 运行，在 `web/` 构建并启动预览：

```bash
npm run build
npm run preview -- --host 127.0.0.1 --port 5175 --strictPort
```

在项目根目录另开终端运行 `node scripts/check_loading_web.cjs`。需安装 Playwright 和 Chromium，或通过 `PLAYWRIGHT_MODULE`、`CHROMIUM_PATH` 指向现有安装；`DIETLENS_PREVIEW_URL` 可覆盖默认 `http://127.0.0.1:5175/`。脚本使用浏览器接口 fixture，模拟工具和登录模块下载失败，不发送真实登录邮件。生产预览只用于本机验证。
