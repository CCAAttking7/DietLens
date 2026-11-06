# Supabase + Figma 接入教程

你不需要先准备 Figma 文件。我先做了一个可运行的 React 设计骨架，等你创建项目后再把 Supabase 和真实视觉稿接上。

## 第一步：创建 Supabase 项目

1. 打开 <https://supabase.com/dashboard>，注册或登录。
2. New project，项目名填 `dietlens`，设置数据库密码并选择离你用户近的区域。
3. 等项目状态变为可用后，进入 **Project Settings → API** 或项目 **Connect** 面板。
4. 复制 Project URL。它形如 `https://你的项目编号.supabase.co`。
5. 创建或复制 **Publishable key**（旧项目可能显示 `anon` key）。只把它放到浏览器 `.env` 的 `VITE_SUPABASE_PUBLISHABLE_KEY`。
6. 创建或复制 **Secret key**（旧项目可能显示 `service_role` key）。只放到 Python 服务端 `.env` 的 `SUPABASE_SECRET_KEY`，不要放进 `web/`，不要提交到 Git，不要发给聊天机器人。

Supabase 当前同时支持新 publishable/secret key 和旧 anon/service_role key；新项目优先使用新名称。Publishable key 只能在 RLS 下访问允许的数据，secret key 会绕过 RLS，只能留在服务端。参见 [Supabase API keys](https://supabase.com/docs/guides/getting-started/api-keys)。

## 第二步：把数据库迁移到 Supabase

本机安装 Supabase CLI 后，在项目根目录执行：

```bash
supabase login
supabase link --project-ref 你的项目编号
supabase db push
```

迁移文件在 `supabase/migrations/0001_dietlens_core.sql`。它包含档案版本、草稿、授权、任务、食品观察、行动、事件和幂等操作表，开启 RLS，并提供档案确认的原子数据库函数。计划、购物清单和库存表在 `supabase/migrations/005_planning.sql`，实际餐食记录在 `supabase/migrations/006_meal_records.sql`。Supabase CLI 会把迁移文件保存并推送到托管项目；参见 [Supabase CLI](https://supabase.com/features/cli)。

如果你使用 SQL Editor 而不是 CLI：先确认核心迁移已经执行，再依次点 **New snippet** 执行 `005_planning.sql` 和 `006_meal_records.sql`。看到 `Success. No rows returned` 即表示 DDL 执行成功；之后可在 Table Editor 看到计划、库存和实际餐食记录表。

计划迁移成功后，再新建一个 **New snippet**，执行 `006_meal_records.sql`。成功后可在 Table Editor 看到 `meal_records` 和 `meal_record_versions`；计划预填不会自动写入这两张表，只有用户确认实际吃过才写入。

在迁移前先打开文件检查表结构。当前项目仍可使用 SQLite 本地测试；Supabase 迁移是第二个持久化目标，不会自动覆盖本地数据库。

## 第三步：配置本地环境

根目录 `.env`（Python 服务端）：

```dotenv
SUPABASE_URL=https://你的项目编号.supabase.co
SUPABASE_SECRET_KEY=只在服务端使用
SUPABASE_DB_URL=Connect 面板中的 Postgres connection string
DIETLENS_DB=dietlens.db
```

`web/.env`（浏览器）：

```dotenv
VITE_SUPABASE_URL=https://你的项目编号.supabase.co
VITE_SUPABASE_PUBLISHABLE_KEY=只读公开 key
VITE_DIETLENS_API_URL=http://localhost:8000
```

浏览器不直接持有 secret key。前端调用 Python Harness API，Python 再根据当前用户身份和版本执行确认写入。这样模型不能绕过 Harness 直接写 Supabase。

## 第四步：开始 Figma 设计

如果你没有 Figma 文件，最省事的做法是现在新建一个空白 Figma Design 文件，名称设为 `DietLens`；不需要先画页面。后续按下面顺序建立：

1. `Foundations`：颜色、字号、间距、圆角、阴影和状态颜色。
2. `Components`：按钮、状态徽章、来源卡片、未知字段提示、确认卡、候选行动卡。
3. `Screens`：Agent 首页、档案与授权、食品查询、候选确认、反馈、回顾。
4. 每个写入界面保留确认卡；状态同时用文字和颜色；未知、来源和失败原因直接可见。

当前 `web/src/styles/tokens.css` 是没有 Figma 依赖的临时设计令牌，`web/src/App.tsx` 是首个首页骨架。你创建 Figma 后，把文件链接发给我；如果无法使用 Figma API，只要提供截图或 Dev Mode 的间距/颜色/字体数值，我也能按同一组件契约实现。

## 第五步：本地运行

```bash
cd web
npm install
npm run dev
```

当前页面可以离线打开，Supabase 未配置时只显示设计骨架；API 交互等 Python FastAPI 路由接入后启用。生产构建已经通过：

```bash
npm run build
```

## 当前边界

Supabase SQL 迁移和前端骨架已经提交到仓库，核心、计划和实际餐食迁移已连接到你的托管项目。Python `PostgresStore` 已补入仓库，安装 `dietlens[cloud]` 后使用 `SUPABASE_DB_URL` 可复用 Harness 的事务接口；Auth 登录会话和部署仍按后续切片接入。

## 当前项目状态

Project URL 已配置，SQL Editor 的 **New snippet** 已成功运行核心、计划和实际餐食迁移；九张业务表的 REST 查询均返回 200。当前项目还没有业务数据。

计划迁移已经运行。可执行 `scripts/check_supabase.py` 或在 Table Editor 检查三张计划表；当前本地 SQLite 计划闭环已由测试覆盖。

实际餐食迁移已经运行。`scripts/check_supabase.py` 会同时检查两张记录表；当前没有业务数据。

本机网络对 Supabase 的 HTTPS API 可用，但对 Postgres 5432 直连超时。若要让 Python `PostgresStore` 直接工作，请在 Connect 面板尝试 Session Pooler connection string；如果当前网络仍阻断原生 Postgres，则保留 SQLite 本地 API，并把服务端 Supabase 写入改为使用 secret key + RPC。secret key 不要放进 `web/.env`。
