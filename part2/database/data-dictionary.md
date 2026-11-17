# 数据字典

版本：R2-P4候选。物理字段使用稳定技术标识，业务名称、含义和约束说明采用中文。

所有时点按UTC存储，业务日期按Asia/Shanghai核对；标识由服务端生成。所有者字段不可由浏览器任意指定。
数量定点值=实际值×1000000；输入超过六位小数时先展示规范化值待核对，不静默截断。所有私有外键含user_id。
空值只表示对应语义中的未知或不适用，具体状态字段控制其含义。子表生命周期随所属聚合，版本内容除清理脱敏外不可原地修改。

## 用户处理控制（user_control）

责任分区：授权与证据。主键：`user_id`。

| 字段 | 中文含义 | PostgreSQL / SQLite | 可空 | 默认值 | 约束与说明 |
|---|---|---|---|---|---|
| `user_id` | 所属用户 | TEXT / TEXT | 否 | 无 | 主键组成；外键组成，详见表后 |
| `external_subject` | 托管身份主体 | TEXT / TEXT | 是 | 无 | 只存身份映射，不存口令或访问令牌 |
| `processing_state` | 处理状态 | TEXT / TEXT | 否 | 无 |  |
| `authorization_epoch` | 授权修订标记 | BIGINT / INTEGER | 否 | 无 | 正整数 |
| `data_revision` | 用户数据修订 | BIGINT / INTEGER | 否 | 无 | 正整数 |
| `current_profile_revision` | 当前档案修订 | BIGINT / INTEGER | 是 | 无 | 外键组成，详见表后；正整数 |
| `delete_requested_at` | 主动删除请求时间 | TIMESTAMPTZ / TEXT | 是 | 无 |  |
| `created_at` | 建立时间 | TIMESTAMPTZ / TEXT | 否 | 无 |  |

关系、约束及索引：

- `user_id,current_profile_revision` → `profile_revisions(user_id,revision)`；提交时检查，不自动删除关联。
- 唯一：`external_subject`。
- 检查：`processing_state IN ('正常', '待删除', '清理中', '清理失败', '已清理待备份到期')`。
- 检查：`authorization_epoch >= 1`。
- 检查：`data_revision >= 1`。
- 检查：`current_profile_revision IS NULL OR (current_profile_revision >= 1)`。
- 查询索引：`user_id,current_profile_revision`。

## 档案确认版本（profile_revisions）

责任分区：授权与证据。主键：`user_id, revision`。

| 字段 | 中文含义 | PostgreSQL / SQLite | 可空 | 默认值 | 约束与说明 |
|---|---|---|---|---|---|
| `user_id` | 所属用户 | TEXT / TEXT | 否 | 无 | 主键组成；外键组成，详见表后 |
| `revision` | 修订号 | BIGINT / INTEGER | 否 | 无 | 主键组成；正整数 |
| `confirmed_fields` | 已确认字段 | JSONB / TEXT | 否 | 无 | 目标、预算、硬约束、软偏好及逐字段来源；固定结构由模块校验 |
| `confirmed_at` | 用户确认时间 | TIMESTAMPTZ / TEXT | 否 | 无 |  |
| `created_at` | 建立时间 | TIMESTAMPTZ / TEXT | 否 | 无 |  |
| `retain_until` | 保留截止 | TIMESTAMPTZ / TEXT | 否 | 无 | 初次不超过180天；明确续期须留审计依据 |
| `renewed_at` | 续期确认时间 | TIMESTAMPTZ / TEXT | 是 | 无 |  |

关系、约束及索引：

- `user_id` → `user_control(user_id)`；提交时检查，不自动删除关联。
- 检查：`revision >= 1`。
- 检查：`retain_until >= created_at`。
- 检查：`((renewed_at IS NULL AND retain_until <= created_at + INTERVAL '180 days') OR (renewed_at IS NOT NULL AND renewed_at >= created_at AND retain_until <= renewed_at + INTERVAL '180 days'))`。
- 查询索引：`retain_until`。

## 临时图片（media_assets）

责任分区：授权与证据。主键：`user_id, id`。

| 字段 | 中文含义 | PostgreSQL / SQLite | 可空 | 默认值 | 约束与说明 |
|---|---|---|---|---|---|
| `user_id` | 所属用户 | TEXT / TEXT | 否 | 无 | 主键组成；外键组成，详见表后 |
| `id` | 对象标识 | TEXT / TEXT | 否 | 无 | 主键组成 |
| `storage_key` | 本机受控文件键 | TEXT / TEXT | 是 | 无 |  |
| `media_kind` | 材料用途 | TEXT / TEXT | 否 | 无 |  |
| `content_hash` | 内容摘要 | TEXT / TEXT | 否 | 无 |  |
| `expires_at` | 图片过期时间 | TIMESTAMPTZ / TEXT | 否 | 无 |  |
| `processing_state` | 图片处理状态 | TEXT / TEXT | 否 | 无 |  |
| `created_at` | 建立时间 | TIMESTAMPTZ / TEXT | 否 | 无 |  |
| `retain_until` | 保留截止 | TIMESTAMPTZ / TEXT | 否 | 无 | 初次不超过180天；明确续期须留审计依据 |
| `renewed_at` | 续期确认时间 | TIMESTAMPTZ / TEXT | 是 | 无 |  |

关系、约束及索引：

- `user_id` → `user_control(user_id)`；提交时检查，不自动删除关联。
- 检查：`processing_state IN ('可用', '待清理', '已清理')`。
- 检查：`((processing_state = '已清理' AND storage_key IS NULL) OR (processing_state <> '已清理' AND storage_key IS NOT NULL))`。
- 检查：`retain_until >= created_at`。
- 检查：`((renewed_at IS NULL AND retain_until <= created_at + INTERVAL '180 days') OR (renewed_at IS NOT NULL AND renewed_at >= created_at AND retain_until <= renewed_at + INTERVAL '180 days'))`。
- 检查：`expires_at >= created_at`。
- 检查：`expires_at <= created_at + INTERVAL '1 days'`。
- 查询索引：`expires_at`。
- 查询索引：`retain_until`。

## 用途授权修订（consent_revisions）

责任分区：授权与证据。主键：`user_id, purpose, scope_key, revision`。

| 字段 | 中文含义 | PostgreSQL / SQLite | 可空 | 默认值 | 约束与说明 |
|---|---|---|---|---|---|
| `user_id` | 所属用户 | TEXT / TEXT | 否 | 无 | 主键组成；外键组成，详见表后 |
| `purpose` | 用途 | TEXT / TEXT | 否 | 无 | 主键组成 |
| `scope_key` | 范围键 | TEXT / TEXT | 否 | 无 | 主键组成；全域或对应图片标识 |
| `revision` | 修订号 | BIGINT / INTEGER | 否 | 无 | 主键组成；正整数 |
| `asset_id` | 外传图片标识 | TEXT / TEXT | 是 | 无 | 外键组成，详见表后 |
| `allowed` | 允许使用 | SMALLINT / INTEGER | 否 | 无 | 0或1 |
| `recipient` | 接收方 | TEXT / TEXT | 是 | 无 |  |
| `authorization_epoch` | 授权修订标记 | BIGINT / INTEGER | 否 | 无 | 正整数 |
| `confirmed_at` | 用户确认时间 | TIMESTAMPTZ / TEXT | 否 | 无 |  |
| `created_at` | 建立时间 | TIMESTAMPTZ / TEXT | 否 | 无 |  |
| `retain_until` | 保留截止 | TIMESTAMPTZ / TEXT | 否 | 无 | 初次不超过180天；明确续期须留审计依据 |
| `renewed_at` | 续期确认时间 | TIMESTAMPTZ / TEXT | 是 | 无 |  |

关系、约束及索引：

- `user_id` → `user_control(user_id)`；提交时检查，不自动删除关联。
- `user_id,asset_id` → `media_assets(user_id,id)`；提交时检查，不自动删除关联。
- 检查：`purpose IN ('历史分析', '图片外传', '提醒')`。
- 检查：`((purpose = '图片外传' AND asset_id IS NOT NULL AND scope_key = asset_id AND recipient IS NOT NULL) OR (purpose <> '图片外传' AND asset_id IS NULL AND scope_key = '全域'))`。
- 检查：`revision >= 1`。
- 检查：`allowed IN (0, 1)`。
- 检查：`authorization_epoch >= 1`。
- 检查：`retain_until >= created_at`。
- 检查：`((renewed_at IS NULL AND retain_until <= created_at + INTERVAL '180 days') OR (renewed_at IS NOT NULL AND renewed_at >= created_at AND retain_until <= renewed_at + INTERVAL '180 days'))`。
- 查询索引：`user_id,asset_id`。
- 查询索引：`retain_until`。

## 临时任务会话（task_sessions）

责任分区：授权与证据。主键：`user_id, id`。

| 字段 | 中文含义 | PostgreSQL / SQLite | 可空 | 默认值 | 约束与说明 |
|---|---|---|---|---|---|
| `user_id` | 所属用户 | TEXT / TEXT | 否 | 无 | 主键组成；外键组成，详见表后 |
| `id` | 对象标识 | TEXT / TEXT | 否 | 无 | 主键组成 |
| `task_kind` | 任务类型 | TEXT / TEXT | 否 | 无 |  |
| `state` | 任务状态 | TEXT / TEXT | 否 | 无 |  |
| `draft_revision` | 草稿修订 | BIGINT / INTEGER | 否 | 无 | 正整数 |
| `draft_payload` | 未确认草稿 | JSONB / TEXT | 否 | 无 |  |
| `authorization_epoch` | 绑定授权修订 | BIGINT / INTEGER | 否 | 无 | 正整数 |
| `expires_at` | 任务过期时间 | TIMESTAMPTZ / TEXT | 否 | 无 |  |
| `created_at` | 建立时间 | TIMESTAMPTZ / TEXT | 否 | 无 |  |

关系、约束及索引：

- `user_id` → `user_control(user_id)`；提交时检查，不自动删除关联。
- 检查：`state IN ('进行中', '已暂停', '已取消', '已完成')`。
- 检查：`draft_revision >= 1`。
- 检查：`authorization_epoch >= 1`。
- 检查：`expires_at >= created_at`。
- 检查：`expires_at <= created_at + INTERVAL '7 days'`。
- 查询索引：`expires_at`。

## 已确认情境（context_snapshots）

责任分区：授权与证据。主键：`user_id, id`。

| 字段 | 中文含义 | PostgreSQL / SQLite | 可空 | 默认值 | 约束与说明 |
|---|---|---|---|---|---|
| `user_id` | 所属用户 | TEXT / TEXT | 否 | 无 | 主键组成；外键组成，详见表后 |
| `id` | 对象标识 | TEXT / TEXT | 否 | 无 | 主键组成 |
| `profile_revision` | 档案修订 | BIGINT / INTEGER | 否 | 无 | 外键组成，详见表后；正整数 |
| `context_key` | 情境指纹 | TEXT / TEXT | 否 | 无 | 相同情境冷却的规范化键，不以新快照标识绕过冷却 |
| `situation` | 已确认情境内容 | JSONB / TEXT | 否 | 无 |  |
| `authorization_epoch` | 当时授权修订 | BIGINT / INTEGER | 否 | 无 | 正整数 |
| `confirmed_at` | 用户确认时间 | TIMESTAMPTZ / TEXT | 否 | 无 |  |
| `created_at` | 建立时间 | TIMESTAMPTZ / TEXT | 否 | 无 |  |
| `retain_until` | 保留截止 | TIMESTAMPTZ / TEXT | 否 | 无 | 初次不超过180天；明确续期须留审计依据 |
| `renewed_at` | 续期确认时间 | TIMESTAMPTZ / TEXT | 是 | 无 |  |

关系、约束及索引：

- `user_id` → `user_control(user_id)`；提交时检查，不自动删除关联。
- `user_id,profile_revision` → `profile_revisions(user_id,revision)`；提交时检查，不自动删除关联。
- 检查：`profile_revision >= 1`。
- 检查：`authorization_epoch >= 1`。
- 检查：`retain_until >= created_at`。
- 检查：`((renewed_at IS NULL AND retain_until <= created_at + INTERVAL '180 days') OR (renewed_at IS NOT NULL AND renewed_at >= created_at AND retain_until <= renewed_at + INTERVAL '180 days'))`。
- 查询索引：`user_id,profile_revision`。
- 查询索引：`user_id,context_key`。
- 查询索引：`retain_until`。

## 证据来源（source_references）

责任分区：授权与证据。主键：`user_id, id`。

| 字段 | 中文含义 | PostgreSQL / SQLite | 可空 | 默认值 | 约束与说明 |
|---|---|---|---|---|---|
| `user_id` | 所属用户 | TEXT / TEXT | 否 | 无 | 主键组成；外键组成，详见表后 |
| `id` | 对象标识 | TEXT / TEXT | 否 | 无 | 主键组成 |
| `source_kind` | 来源类型 | TEXT / TEXT | 否 | 无 |  |
| `source_locator` | 出处或自述说明 | TEXT / TEXT | 否 | 无 |  |
| `specification` | 商品或菜单规格 | TEXT / TEXT | 是 | 无 |  |
| `published_at` | 材料时间 | TIMESTAMPTZ / TEXT | 是 | 无 |  |
| `acquired_at` | 取得时间 | TIMESTAMPTZ / TEXT | 否 | 无 |  |
| `asset_id` | 原图片标识 | TEXT / TEXT | 是 | 无 | 外键组成，详见表后 |
| `asset_digest` | 材料摘要 | TEXT / TEXT | 是 | 无 |  |
| `verification_note` | 核对依据 | TEXT / TEXT | 是 | 无 |  |
| `created_at` | 建立时间 | TIMESTAMPTZ / TEXT | 否 | 无 |  |
| `retain_until` | 保留截止 | TIMESTAMPTZ / TEXT | 否 | 无 | 初次不超过180天；明确续期须留审计依据 |
| `renewed_at` | 续期确认时间 | TIMESTAMPTZ / TEXT | 是 | 无 |  |

关系、约束及索引：

- `user_id` → `user_control(user_id)`；提交时检查，不自动删除关联。
- `user_id,asset_id` → `media_assets(user_id,id)`；提交时检查，不自动删除关联。
- 检查：`source_kind IN ('用户自述', '商品标签', '菜单', '公开资料', '本地编码')`。
- 检查：`retain_until >= created_at`。
- 检查：`((renewed_at IS NULL AND retain_until <= created_at + INTERVAL '180 days') OR (renewed_at IS NOT NULL AND renewed_at >= created_at AND retain_until <= renewed_at + INTERVAL '180 days'))`。
- 查询索引：`user_id,asset_id`。
- 查询索引：`retain_until`。

## 食品证据版本（food_observations）

责任分区：授权与证据。主键：`user_id, id`。

| 字段 | 中文含义 | PostgreSQL / SQLite | 可空 | 默认值 | 约束与说明 |
|---|---|---|---|---|---|
| `user_id` | 所属用户 | TEXT / TEXT | 否 | 无 | 主键组成；外键组成，详见表后 |
| `id` | 对象标识 | TEXT / TEXT | 否 | 无 | 主键组成 |
| `previous_id` | 上一证据版本 | TEXT / TEXT | 是 | 无 | 外键组成，详见表后 |
| `food_name` | 食品名称 | TEXT / TEXT | 否 | 无 |  |
| `specification` | 当前规格 | TEXT / TEXT | 是 | 无 |  |
| `recipe_coverage` | 配方覆盖 | TEXT / TEXT | 否 | 无 |  |
| `checked_at` | 核对时间 | TIMESTAMPTZ / TEXT | 是 | 无 |  |
| `created_at` | 建立时间 | TIMESTAMPTZ / TEXT | 否 | 无 |  |
| `retain_until` | 保留截止 | TIMESTAMPTZ / TEXT | 否 | 无 | 初次不超过180天；明确续期须留审计依据 |
| `renewed_at` | 续期确认时间 | TIMESTAMPTZ / TEXT | 是 | 无 |  |
| `basis_state` | 营养基准量状态 | TEXT / TEXT | 否 | 无 |  |
| `basis_micros` | 营养基准量定点值 | BIGINT / INTEGER | 是 | 无 | 实际值乘1000000；未知必须为空；0至9000000000000000的整数 |
| `basis_unit` | 营养基准量单位 | TEXT / TEXT | 是 | 无 |  |

关系、约束及索引：

- `user_id` → `user_control(user_id)`；提交时检查，不自动删除关联。
- `user_id,previous_id` → `food_observations(user_id,id)`；提交时检查，不自动删除关联。
- 检查：`recipe_coverage IN ('完整已核对', '仅部分已知', '未知')`。
- 检查：`basis_state IN ('已知', '未知')`。
- 检查：`((basis_state = '已知' AND basis_micros IS NOT NULL AND basis_unit IS NOT NULL) OR (basis_state = '未知' AND basis_micros IS NULL))`。
- 检查：`basis_micros IS NULL OR (basis_micros >= 0 AND basis_micros <= 9000000000000000)`。
- 检查：`retain_until >= created_at`。
- 检查：`((renewed_at IS NULL AND retain_until <= created_at + INTERVAL '180 days') OR (renewed_at IS NOT NULL AND renewed_at >= created_at AND retain_until <= renewed_at + INTERVAL '180 days'))`。
- 检查：`basis_state = '未知' OR basis_micros > 0`。
- 查询索引：`user_id,previous_id`。
- 查询索引：`user_id,food_name`。
- 查询索引：`retain_until`。

## 食品逐字段事实（food_fields）

责任分区：授权与证据。主键：`user_id, observation_id, field_key`。

| 字段 | 中文含义 | PostgreSQL / SQLite | 可空 | 默认值 | 约束与说明 |
|---|---|---|---|---|---|
| `user_id` | 所属用户 | TEXT / TEXT | 否 | 无 | 主键组成；外键组成，详见表后 |
| `observation_id` | 食品证据标识 | TEXT / TEXT | 否 | 无 | 主键组成；外键组成，详见表后 |
| `field_key` | 字段键 | TEXT / TEXT | 否 | 无 | 主键组成 |
| `state` | 字段状态 | TEXT / TEXT | 否 | 无 |  |
| `value_kind` | 值类型 | TEXT / TEXT | 否 | 无 |  |
| `number_micros` | 数值定点值 | BIGINT / INTEGER | 是 | 无 | 0至9000000000000000的整数 |
| `text_value` | 文字值 | TEXT / TEXT | 是 | 无 |  |
| `unit` | 字段单位 | TEXT / TEXT | 是 | 无 |  |
| `raw_value` | 原始候选值 | TEXT / TEXT | 是 | 无 |  |
| `checked_at` | 核对时间 | TIMESTAMPTZ / TEXT | 是 | 无 |  |
| `created_at` | 建立时间 | TIMESTAMPTZ / TEXT | 否 | 无 |  |

关系、约束及索引：

- `user_id` → `user_control(user_id)`；提交时检查，不自动删除关联。
- `user_id,observation_id` → `food_observations(user_id,id)`；提交时检查，不自动删除关联。
- 检查：`state IN ('已核对', '待核对', '未知', '冲突')`。
- 检查：`value_kind IN ('数值', '文字')`。
- 检查：`((state IN ('未知','冲突') AND number_micros IS NULL AND text_value IS NULL) OR (state IN ('已核对','待核对') AND ((value_kind = '数值' AND number_micros IS NOT NULL AND text_value IS NULL AND unit IS NOT NULL) OR (value_kind = '文字' AND text_value IS NOT NULL AND number_micros IS NULL))))`。
- 检查：`number_micros IS NULL OR (number_micros >= 0 AND number_micros <= 9000000000000000)`。

## 字段来源关联（field_sources）

责任分区：授权与证据。主键：`user_id, observation_id, field_key, source_id`。

| 字段 | 中文含义 | PostgreSQL / SQLite | 可空 | 默认值 | 约束与说明 |
|---|---|---|---|---|---|
| `user_id` | 所属用户 | TEXT / TEXT | 否 | 无 | 主键组成；外键组成，详见表后 |
| `observation_id` | 食品证据标识 | TEXT / TEXT | 否 | 无 | 主键组成；外键组成，详见表后 |
| `field_key` | 字段键 | TEXT / TEXT | 否 | 无 | 主键组成；外键组成，详见表后 |
| `source_id` | 来源标识 | TEXT / TEXT | 否 | 无 | 主键组成；外键组成，详见表后 |
| `source_role` | 来源角色 | TEXT / TEXT | 否 | 无 |  |
| `created_at` | 建立时间 | TIMESTAMPTZ / TEXT | 否 | 无 |  |

关系、约束及索引：

- `user_id` → `user_control(user_id)`；提交时检查，不自动删除关联。
- `user_id,observation_id,field_key` → `food_fields(user_id,observation_id,field_key)`；提交时检查，不自动删除关联。
- `user_id,source_id` → `source_references(user_id,id)`；提交时检查，不自动删除关联。
- 检查：`source_role IN ('原始材料', '用户核对', '冲突材料')`。
- 查询索引：`user_id,source_id`。

## 约束评估（constraint_assessments）

责任分区：授权与证据。主键：`user_id, id`。

| 字段 | 中文含义 | PostgreSQL / SQLite | 可空 | 默认值 | 约束与说明 |
|---|---|---|---|---|---|
| `user_id` | 所属用户 | TEXT / TEXT | 否 | 无 | 主键组成；外键组成，详见表后 |
| `id` | 对象标识 | TEXT / TEXT | 否 | 无 | 主键组成 |
| `context_id` | 情境标识 | TEXT / TEXT | 否 | 无 | 外键组成，详见表后 |
| `observation_id` | 食品证据标识 | TEXT / TEXT | 是 | 无 | 外键组成，详见表后 |
| `rule_version` | 规则版本 | TEXT / TEXT | 否 | 无 |  |
| `outcome` | 评估结论 | TEXT / TEXT | 否 | 无 |  |
| `reasons` | 原因与受影响操作 | JSONB / TEXT | 否 | 无 |  |
| `evaluated_at` | 评估时间 | TIMESTAMPTZ / TEXT | 否 | 无 |  |
| `created_at` | 建立时间 | TIMESTAMPTZ / TEXT | 否 | 无 |  |
| `retain_until` | 保留截止 | TIMESTAMPTZ / TEXT | 否 | 无 | 初次不超过180天；明确续期须留审计依据 |
| `renewed_at` | 续期确认时间 | TIMESTAMPTZ / TEXT | 是 | 无 |  |

关系、约束及索引：

- `user_id` → `user_control(user_id)`；提交时检查，不自动删除关联。
- `user_id,context_id` → `context_snapshots(user_id,id)`；提交时检查，不自动删除关联。
- `user_id,observation_id` → `food_observations(user_id,id)`；提交时检查，不自动删除关联。
- 检查：`outcome IN ('通过', '拦截', '待核对')`。
- 检查：`retain_until >= created_at`。
- 检查：`((renewed_at IS NULL AND retain_until <= created_at + INTERVAL '180 days') OR (renewed_at IS NOT NULL AND renewed_at >= created_at AND retain_until <= renewed_at + INTERVAL '180 days'))`。
- 查询索引：`user_id,context_id`。
- 查询索引：`user_id,observation_id`。
- 查询索引：`retain_until`。

## 标准食材（ingredients）

责任分区：计划与准备。主键：`user_id, id`。

| 字段 | 中文含义 | PostgreSQL / SQLite | 可空 | 默认值 | 约束与说明 |
|---|---|---|---|---|---|
| `user_id` | 所属用户 | TEXT / TEXT | 否 | 无 | 主键组成；外键组成，详见表后 |
| `id` | 对象标识 | TEXT / TEXT | 否 | 无 | 主键组成 |
| `canonical_name` | 标准名称 | TEXT / TEXT | 否 | 无 |  |
| `catalog_code` | 外部编码 | TEXT / TEXT | 是 | 无 |  |
| `created_at` | 建立时间 | TIMESTAMPTZ / TEXT | 否 | 无 |  |
| `retain_until` | 保留截止 | TIMESTAMPTZ / TEXT | 否 | 无 | 初次不超过180天；明确续期须留审计依据 |
| `renewed_at` | 续期确认时间 | TIMESTAMPTZ / TEXT | 是 | 无 |  |

关系、约束及索引：

- `user_id` → `user_control(user_id)`；提交时检查，不自动删除关联。
- 检查：`retain_until >= created_at`。
- 检查：`((renewed_at IS NULL AND retain_until <= created_at + INTERVAL '180 days') OR (renewed_at IS NOT NULL AND renewed_at >= created_at AND retain_until <= renewed_at + INTERVAL '180 days'))`。
- 查询索引：`retain_until`。

## 计划身份（plan_heads）

责任分区：计划与准备。主键：`user_id, id`。

| 字段 | 中文含义 | PostgreSQL / SQLite | 可空 | 默认值 | 约束与说明 |
|---|---|---|---|---|---|
| `user_id` | 所属用户 | TEXT / TEXT | 否 | 无 | 主键组成；外键组成，详见表后 |
| `id` | 对象标识 | TEXT / TEXT | 否 | 无 | 主键组成；外键组成，详见表后 |
| `current_revision` | 当前确认修订 | BIGINT / INTEGER | 否 | 无 | 外键组成，详见表后；正整数 |
| `row_version` | 并发版本 | BIGINT / INTEGER | 否 | 无 | 正整数 |
| `state` | 身份状态 | TEXT / TEXT | 否 | 无 |  |
| `created_at` | 建立时间 | TIMESTAMPTZ / TEXT | 否 | 无 |  |
| `retain_until` | 保留截止 | TIMESTAMPTZ / TEXT | 否 | 无 | 初次不超过180天；明确续期须留审计依据 |
| `renewed_at` | 续期确认时间 | TIMESTAMPTZ / TEXT | 是 | 无 |  |

关系、约束及索引：

- `user_id` → `user_control(user_id)`；提交时检查，不自动删除关联。
- `user_id,id,current_revision` → `plan_revisions(user_id,id,revision)`；提交时检查，不自动删除关联。
- 检查：`state IN ('有效', '已删除')`。
- 检查：`current_revision >= 1`。
- 检查：`row_version >= 1`。
- 检查：`retain_until >= created_at`。
- 检查：`((renewed_at IS NULL AND retain_until <= created_at + INTERVAL '180 days') OR (renewed_at IS NOT NULL AND renewed_at >= created_at AND retain_until <= renewed_at + INTERVAL '180 days'))`。
- 查询索引：`user_id,id,current_revision`。
- 查询索引：`retain_until`。

## 计划确认版本（plan_revisions）

责任分区：计划与准备。主键：`user_id, id, revision`。

| 字段 | 中文含义 | PostgreSQL / SQLite | 可空 | 默认值 | 约束与说明 |
|---|---|---|---|---|---|
| `user_id` | 所属用户 | TEXT / TEXT | 否 | 无 | 主键组成；外键组成，详见表后 |
| `id` | 对象标识 | TEXT / TEXT | 否 | 无 | 主键组成；外键组成，详见表后 |
| `revision` | 修订号 | BIGINT / INTEGER | 否 | 无 | 主键组成；正整数 |
| `mode` | 计划模式 | TEXT / TEXT | 否 | 无 |  |
| `start_date` | 开始日期 | DATE / TEXT | 否 | 无 |  |
| `end_date` | 结束日期 | DATE / TEXT | 否 | 无 |  |
| `day_count` | 计划天数 | BIGINT / INTEGER | 否 | 无 | 正整数 |
| `context_id` | 情境标识 | TEXT / TEXT | 否 | 无 | 外键组成，详见表后 |
| `confirmed_at` | 用户确认时间 | TIMESTAMPTZ / TEXT | 否 | 无 |  |
| `created_at` | 建立时间 | TIMESTAMPTZ / TEXT | 否 | 无 |  |

关系、约束及索引：

- `user_id` → `user_control(user_id)`；提交时检查，不自动删除关联。
- `user_id,id` → `plan_heads(user_id,id)`；提交时检查，不自动删除关联。
- `user_id,context_id` → `context_snapshots(user_id,id)`；提交时检查，不自动删除关联。
- 检查：`end_date >= start_date`。
- 检查：`day_count IN (1, 7)`。
- 检查：`mode IN ('完整', '指定')`。
- 检查：`revision >= 1`。
- 检查：`day_count >= 1`。
- 检查：`end_date = start_date + CAST(day_count - 1 AS INTEGER)`。
- 查询索引：`user_id,context_id`。

## 计划餐次（planned_meals）

责任分区：计划与准备。主键：`user_id, id`。

| 字段 | 中文含义 | PostgreSQL / SQLite | 可空 | 默认值 | 约束与说明 |
|---|---|---|---|---|---|
| `user_id` | 所属用户 | TEXT / TEXT | 否 | 无 | 主键组成；外键组成，详见表后 |
| `id` | 对象标识 | TEXT / TEXT | 否 | 无 | 主键组成 |
| `plan_id` | 计划标识 | TEXT / TEXT | 否 | 无 | 外键组成，详见表后 |
| `plan_revision` | 计划修订 | BIGINT / INTEGER | 否 | 无 | 外键组成，详见表后；正整数 |
| `meal_date` | 餐次日期 | DATE / TEXT | 否 | 无 |  |
| `meal_slot` | 规范餐次 | TEXT / TEXT | 否 | 无 |  |
| `people_count` | 准备人数 | BIGINT / INTEGER | 否 | 无 | 正整数 |
| `created_at` | 建立时间 | TIMESTAMPTZ / TEXT | 否 | 无 |  |

关系、约束及索引：

- `user_id` → `user_control(user_id)`；提交时检查，不自动删除关联。
- `user_id,plan_id,plan_revision` → `plan_revisions(user_id,id,revision)`；提交时检查，不自动删除关联。
- 唯一：`user_id,plan_id,plan_revision,meal_date,meal_slot`。
- 唯一：`user_id,id,meal_date,meal_slot`。
- 检查：`meal_slot IN ('早餐', '午餐', '晚餐')`。
- 检查：`plan_revision >= 1`。
- 检查：`people_count >= 1`。

## 计划食物（planned_foods）

责任分区：计划与准备。主键：`user_id, id`。

| 字段 | 中文含义 | PostgreSQL / SQLite | 可空 | 默认值 | 约束与说明 |
|---|---|---|---|---|---|
| `user_id` | 所属用户 | TEXT / TEXT | 否 | 无 | 主键组成；外键组成，详见表后 |
| `id` | 对象标识 | TEXT / TEXT | 否 | 无 | 主键组成 |
| `planned_meal_id` | 计划餐次标识 | TEXT / TEXT | 否 | 无 | 外键组成，详见表后 |
| `food_name` | 食物名称 | TEXT / TEXT | 否 | 无 |  |
| `observation_id` | 食品证据标识 | TEXT / TEXT | 是 | 无 | 外键组成，详见表后 |
| `assessment_id` | 约束评估标识 | TEXT / TEXT | 是 | 无 | 外键组成，详见表后 |
| `quantity_basis` | 数量基准 | TEXT / TEXT | 否 | 无 |  |
| `created_at` | 建立时间 | TIMESTAMPTZ / TEXT | 否 | 无 |  |
| `quantity_state` | 计划份量状态 | TEXT / TEXT | 否 | 无 |  |
| `quantity_micros` | 计划份量定点值 | BIGINT / INTEGER | 是 | 无 | 实际值乘1000000；未知必须为空；0至9000000000000000的整数 |
| `quantity_unit` | 计划份量单位 | TEXT / TEXT | 是 | 无 |  |

关系、约束及索引：

- `user_id` → `user_control(user_id)`；提交时检查，不自动删除关联。
- `user_id,planned_meal_id` → `planned_meals(user_id,id)`；提交时检查，不自动删除关联。
- `user_id,observation_id` → `food_observations(user_id,id)`；提交时检查，不自动删除关联。
- `user_id,assessment_id` → `constraint_assessments(user_id,id)`；提交时检查，不自动删除关联。
- 检查：`quantity_basis IN ('每人', '本餐总量')`。
- 检查：`quantity_state IN ('已知', '未知')`。
- 检查：`((quantity_state = '已知' AND quantity_micros IS NOT NULL AND quantity_unit IS NOT NULL) OR (quantity_state = '未知' AND quantity_micros IS NULL))`。
- 检查：`quantity_micros IS NULL OR (quantity_micros >= 0 AND quantity_micros <= 9000000000000000)`。
- 查询索引：`user_id,planned_meal_id`。
- 查询索引：`user_id,observation_id`。
- 查询索引：`user_id,assessment_id`。

## 食材需求（ingredient_requirements）

责任分区：计划与准备。主键：`user_id, id`。

| 字段 | 中文含义 | PostgreSQL / SQLite | 可空 | 默认值 | 约束与说明 |
|---|---|---|---|---|---|
| `user_id` | 所属用户 | TEXT / TEXT | 否 | 无 | 主键组成；外键组成，详见表后 |
| `id` | 对象标识 | TEXT / TEXT | 否 | 无 | 主键组成 |
| `planned_food_id` | 计划食物标识 | TEXT / TEXT | 否 | 无 | 外键组成，详见表后 |
| `ingredient_id` | 食材标识 | TEXT / TEXT | 否 | 无 | 外键组成，详见表后 |
| `quantity_basis` | 数量基准 | TEXT / TEXT | 否 | 无 |  |
| `source_id` | 配方来源 | TEXT / TEXT | 是 | 无 | 外键组成，详见表后 |
| `created_at` | 建立时间 | TIMESTAMPTZ / TEXT | 否 | 无 |  |
| `quantity_state` | 食材用量状态 | TEXT / TEXT | 否 | 无 |  |
| `quantity_micros` | 食材用量定点值 | BIGINT / INTEGER | 是 | 无 | 实际值乘1000000；未知必须为空；0至9000000000000000的整数 |
| `quantity_unit` | 食材用量单位 | TEXT / TEXT | 是 | 无 |  |

关系、约束及索引：

- `user_id` → `user_control(user_id)`；提交时检查，不自动删除关联。
- `user_id,planned_food_id` → `planned_foods(user_id,id)`；提交时检查，不自动删除关联。
- `user_id,ingredient_id` → `ingredients(user_id,id)`；提交时检查，不自动删除关联。
- `user_id,source_id` → `source_references(user_id,id)`；提交时检查，不自动删除关联。
- 检查：`quantity_basis IN ('每人', '本餐总量')`。
- 检查：`quantity_state IN ('已知', '未知')`。
- 检查：`((quantity_state = '已知' AND quantity_micros IS NOT NULL AND quantity_unit IS NOT NULL) OR (quantity_state = '未知' AND quantity_micros IS NULL))`。
- 检查：`quantity_micros IS NULL OR (quantity_micros >= 0 AND quantity_micros <= 9000000000000000)`。
- 查询索引：`user_id,planned_food_id`。
- 查询索引：`user_id,ingredient_id`。
- 查询索引：`user_id,source_id`。

## 当前槽位归属（slot_assignments）

责任分区：计划与准备。主键：`user_id, meal_date, meal_slot`。

| 字段 | 中文含义 | PostgreSQL / SQLite | 可空 | 默认值 | 约束与说明 |
|---|---|---|---|---|---|
| `user_id` | 所属用户 | TEXT / TEXT | 否 | 无 | 主键组成；外键组成，详见表后 |
| `meal_date` | 餐次日期 | DATE / TEXT | 否 | 无 | 主键组成；外键组成，详见表后 |
| `meal_slot` | 规范餐次 | TEXT / TEXT | 否 | 无 | 主键组成；外键组成，详见表后 |
| `planned_meal_id` | 当前计划餐次标识 | TEXT / TEXT | 否 | 无 | 外键组成，详见表后 |
| `row_version` | 槽位并发版本 | BIGINT / INTEGER | 否 | 无 | 正整数 |
| `created_at` | 建立时间 | TIMESTAMPTZ / TEXT | 否 | 无 |  |

关系、约束及索引：

- `user_id` → `user_control(user_id)`；提交时检查，不自动删除关联。
- `user_id,planned_meal_id,meal_date,meal_slot` → `planned_meals(user_id,id,meal_date,meal_slot)`；提交时检查，不自动删除关联。
- 检查：`meal_slot IN ('早餐', '午餐', '晚餐')`。
- 检查：`row_version >= 1`。
- 查询索引：`user_id,planned_meal_id,meal_date,meal_slot`。

## 库存身份（inventory_heads）

责任分区：计划与准备。主键：`user_id, id`。

| 字段 | 中文含义 | PostgreSQL / SQLite | 可空 | 默认值 | 约束与说明 |
|---|---|---|---|---|---|
| `user_id` | 所属用户 | TEXT / TEXT | 否 | 无 | 主键组成；外键组成，详见表后 |
| `id` | 对象标识 | TEXT / TEXT | 否 | 无 | 主键组成；外键组成，详见表后 |
| `ingredient_id` | 标准食材标识 | TEXT / TEXT | 否 | 无 | 外键组成，详见表后 |
| `unit` | 核对口径单位 | TEXT / TEXT | 否 | 无 |  |
| `current_revision` | 当前库存修订 | BIGINT / INTEGER | 否 | 无 | 外键组成，详见表后；正整数 |
| `row_version` | 并发版本 | BIGINT / INTEGER | 否 | 无 | 正整数 |
| `state` | 身份状态 | TEXT / TEXT | 否 | 无 |  |
| `created_at` | 建立时间 | TIMESTAMPTZ / TEXT | 否 | 无 |  |
| `retain_until` | 保留截止 | TIMESTAMPTZ / TEXT | 否 | 无 | 初次不超过180天；明确续期须留审计依据 |
| `renewed_at` | 续期确认时间 | TIMESTAMPTZ / TEXT | 是 | 无 |  |

关系、约束及索引：

- `user_id` → `user_control(user_id)`；提交时检查，不自动删除关联。
- `user_id,ingredient_id` → `ingredients(user_id,id)`；提交时检查，不自动删除关联。
- `user_id,id,current_revision` → `inventory_revisions(user_id,id,revision)`；提交时检查，不自动删除关联。
- 唯一：`user_id,ingredient_id,unit`。
- 检查：`state IN ('有效', '已删除')`。
- 检查：`current_revision >= 1`。
- 检查：`row_version >= 1`。
- 检查：`retain_until >= created_at`。
- 检查：`((renewed_at IS NULL AND retain_until <= created_at + INTERVAL '180 days') OR (renewed_at IS NOT NULL AND renewed_at >= created_at AND retain_until <= renewed_at + INTERVAL '180 days'))`。
- 查询索引：`user_id,id,current_revision`。
- 查询索引：`retain_until`。

## 库存核对版本（inventory_revisions）

责任分区：计划与准备。主键：`user_id, id, revision`。

| 字段 | 中文含义 | PostgreSQL / SQLite | 可空 | 默认值 | 约束与说明 |
|---|---|---|---|---|---|
| `user_id` | 所属用户 | TEXT / TEXT | 否 | 无 | 主键组成；外键组成，详见表后 |
| `id` | 对象标识 | TEXT / TEXT | 否 | 无 | 主键组成；外键组成，详见表后 |
| `revision` | 修订号 | BIGINT / INTEGER | 否 | 无 | 主键组成；正整数 |
| `quantity_state` | 库存量状态 | TEXT / TEXT | 否 | 无 |  |
| `quantity_micros` | 库存定点值 | BIGINT / INTEGER | 是 | 无 | 0至9000000000000000的整数 |
| `observed_at` | 库存核对时间 | TIMESTAMPTZ / TEXT | 否 | 无 |  |
| `reason` | 变更原因 | TEXT / TEXT | 否 | 无 |  |
| `confirmed_at` | 用户确认时间 | TIMESTAMPTZ / TEXT | 否 | 无 |  |
| `created_at` | 建立时间 | TIMESTAMPTZ / TEXT | 否 | 无 |  |

关系、约束及索引：

- `user_id` → `user_control(user_id)`；提交时检查，不自动删除关联。
- `user_id,id` → `inventory_heads(user_id,id)`；提交时检查，不自动删除关联。
- 检查：`quantity_state IN ('已知', '未知')`。
- 检查：`((quantity_state = '已知' AND quantity_micros IS NOT NULL) OR (quantity_state = '未知' AND quantity_micros IS NULL))`。
- 检查：`revision >= 1`。
- 检查：`quantity_micros IS NULL OR (quantity_micros >= 0 AND quantity_micros <= 9000000000000000)`。

## 准备采购清单（preparation_lists）

责任分区：计划与准备。主键：`user_id, id`。

| 字段 | 中文含义 | PostgreSQL / SQLite | 可空 | 默认值 | 约束与说明 |
|---|---|---|---|---|---|
| `user_id` | 所属用户 | TEXT / TEXT | 否 | 无 | 主键组成；外键组成，详见表后 |
| `id` | 对象标识 | TEXT / TEXT | 否 | 无 | 主键组成 |
| `plan_id` | 来源计划标识 | TEXT / TEXT | 否 | 无 | 外键组成，详见表后 |
| `plan_revision` | 来源计划修订 | BIGINT / INTEGER | 否 | 无 | 外键组成，详见表后；正整数 |
| `row_version` | 并发版本 | BIGINT / INTEGER | 否 | 无 | 正整数 |
| `state` | 清单状态 | TEXT / TEXT | 否 | 无 |  |
| `inventory_data_revision` | 库存核对截点 | BIGINT / INTEGER | 否 | 无 | 正整数 |
| `confirmed_at` | 用户确认时间 | TIMESTAMPTZ / TEXT | 否 | 无 |  |
| `created_at` | 建立时间 | TIMESTAMPTZ / TEXT | 否 | 无 |  |
| `retain_until` | 保留截止 | TIMESTAMPTZ / TEXT | 否 | 无 | 初次不超过180天；明确续期须留审计依据 |
| `renewed_at` | 续期确认时间 | TIMESTAMPTZ / TEXT | 是 | 无 |  |

关系、约束及索引：

- `user_id` → `user_control(user_id)`；提交时检查，不自动删除关联。
- `user_id,plan_id,plan_revision` → `plan_revisions(user_id,id,revision)`；提交时检查，不自动删除关联。
- 检查：`state IN ('有效', '已失效', '已取消')`。
- 检查：`plan_revision >= 1`。
- 检查：`row_version >= 1`。
- 检查：`inventory_data_revision >= 1`。
- 检查：`retain_until >= created_at`。
- 检查：`((renewed_at IS NULL AND retain_until <= created_at + INTERVAL '180 days') OR (renewed_at IS NOT NULL AND renewed_at >= created_at AND retain_until <= renewed_at + INTERVAL '180 days'))`。
- 唯一索引：`user_id,plan_id,plan_revision`；条件`state = '有效'`。
- 查询索引：`user_id,plan_id,plan_revision`。
- 查询索引：`retain_until`。

## 清单条目（preparation_lines）

责任分区：计划与准备。主键：`user_id, id`。

| 字段 | 中文含义 | PostgreSQL / SQLite | 可空 | 默认值 | 约束与说明 |
|---|---|---|---|---|---|
| `user_id` | 所属用户 | TEXT / TEXT | 否 | 无 | 主键组成；外键组成，详见表后 |
| `id` | 对象标识 | TEXT / TEXT | 否 | 无 | 主键组成 |
| `list_id` | 清单标识 | TEXT / TEXT | 否 | 无 | 外键组成，详见表后 |
| `ingredient_id` | 标准食材标识 | TEXT / TEXT | 否 | 无 | 外键组成，详见表后 |
| `unit` | 汇总口径单位 | TEXT / TEXT | 否 | 无 |  |
| `has_unknown_requirement` | 另有未知需求 | SMALLINT / INTEGER | 否 | 无 | 0或1 |
| `known_need_micros` | 已知需求小计 | BIGINT / INTEGER | 否 | 无 | 0至9000000000000000的整数 |
| `stock_state` | 库存量状态 | TEXT / TEXT | 否 | 无 |  |
| `stock_micros` | 核对库存定点值 | BIGINT / INTEGER | 是 | 无 | 0至9000000000000000的整数 |
| `shortage_state` | 差额状态 | TEXT / TEXT | 否 | 无 |  |
| `shortage_micros` | 采购差额定点值 | BIGINT / INTEGER | 是 | 无 | 0至9000000000000000的整数 |
| `purchased_state` | 采购自述状态 | TEXT / TEXT | 否 | 无 |  |
| `prepared_state` | 准备自述状态 | TEXT / TEXT | 否 | 无 |  |
| `inventory_id` | 所用库存身份 | TEXT / TEXT | 是 | 无 | 外键组成，详见表后 |
| `inventory_revision` | 所用库存修订 | BIGINT / INTEGER | 是 | 无 | 外键组成，详见表后；正整数 |
| `manual_reason` | 人工调整原因 | TEXT / TEXT | 是 | 无 |  |
| `created_at` | 建立时间 | TIMESTAMPTZ / TEXT | 否 | 无 |  |

关系、约束及索引：

- `user_id` → `user_control(user_id)`；提交时检查，不自动删除关联。
- `user_id,list_id` → `preparation_lists(user_id,id)`；提交时检查，不自动删除关联。
- `user_id,ingredient_id` → `ingredients(user_id,id)`；提交时检查，不自动删除关联。
- `user_id,inventory_id,inventory_revision` → `inventory_revisions(user_id,id,revision)`；提交时检查，不自动删除关联。
- 唯一：`user_id,list_id,ingredient_id,unit`。
- 检查：`((inventory_id IS NULL AND inventory_revision IS NULL) OR (inventory_id IS NOT NULL AND inventory_revision IS NOT NULL))`。
- 检查：`((stock_state = '已知' AND stock_micros IS NOT NULL) OR (stock_state = '未知' AND stock_micros IS NULL))`。
- 检查：`((shortage_state = '已知' AND shortage_micros IS NOT NULL AND stock_state = '已知' AND has_unknown_requirement = 0) OR (shortage_state = '未知' AND shortage_micros IS NULL))`。
- 检查：`stock_state IN ('已知', '未知')`。
- 检查：`shortage_state IN ('已知', '未知')`。
- 检查：`purchased_state IN ('未报告', '已确认', '不适用')`。
- 检查：`prepared_state IN ('未报告', '已确认', '不适用')`。
- 检查：`has_unknown_requirement IN (0, 1)`。
- 检查：`known_need_micros >= 0 AND known_need_micros <= 9000000000000000`。
- 检查：`stock_micros IS NULL OR (stock_micros >= 0 AND stock_micros <= 9000000000000000)`。
- 检查：`shortage_micros IS NULL OR (shortage_micros >= 0 AND shortage_micros <= 9000000000000000)`。
- 检查：`inventory_revision IS NULL OR (inventory_revision >= 1)`。
- 查询索引：`user_id,ingredient_id`。
- 查询索引：`user_id,inventory_id,inventory_revision`。

## 清单需求来源（preparation_sources）

责任分区：计划与准备。主键：`user_id, line_id, requirement_id`。

| 字段 | 中文含义 | PostgreSQL / SQLite | 可空 | 默认值 | 约束与说明 |
|---|---|---|---|---|---|
| `user_id` | 所属用户 | TEXT / TEXT | 否 | 无 | 主键组成；外键组成，详见表后 |
| `line_id` | 清单条目标识 | TEXT / TEXT | 否 | 无 | 主键组成；外键组成，详见表后 |
| `requirement_id` | 食材需求标识 | TEXT / TEXT | 否 | 无 | 主键组成；外键组成，详见表后 |
| `created_at` | 建立时间 | TIMESTAMPTZ / TEXT | 否 | 无 |  |

关系、约束及索引：

- `user_id` → `user_control(user_id)`；提交时检查，不自动删除关联。
- `user_id,line_id` → `preparation_lines(user_id,id)`；提交时检查，不自动删除关联。
- `user_id,requirement_id` → `ingredient_requirements(user_id,id)`；提交时检查，不自动删除关联。
- 查询索引：`user_id,requirement_id`。

## 个人用餐身份（meal_heads）

责任分区：实际与回顾。主键：`user_id, id`。

| 字段 | 中文含义 | PostgreSQL / SQLite | 可空 | 默认值 | 约束与说明 |
|---|---|---|---|---|---|
| `user_id` | 所属用户 | TEXT / TEXT | 否 | 无 | 主键组成；外键组成，详见表后 |
| `id` | 对象标识 | TEXT / TEXT | 否 | 无 | 主键组成；外键组成，详见表后 |
| `current_revision` | 当前餐食修订 | BIGINT / INTEGER | 否 | 无 | 外键组成，详见表后；正整数 |
| `row_version` | 并发版本 | BIGINT / INTEGER | 否 | 无 | 正整数 |
| `state` | 身份状态 | TEXT / TEXT | 否 | 无 |  |
| `created_at` | 建立时间 | TIMESTAMPTZ / TEXT | 否 | 无 |  |
| `retain_until` | 保留截止 | TIMESTAMPTZ / TEXT | 否 | 无 | 初次不超过180天；明确续期须留审计依据 |
| `renewed_at` | 续期确认时间 | TIMESTAMPTZ / TEXT | 是 | 无 |  |

关系、约束及索引：

- `user_id` → `user_control(user_id)`；提交时检查，不自动删除关联。
- `user_id,id,current_revision` → `meal_revisions(user_id,id,revision)`；提交时检查，不自动删除关联。
- 检查：`state IN ('有效', '已删除')`。
- 检查：`current_revision >= 1`。
- 检查：`row_version >= 1`。
- 检查：`retain_until >= created_at`。
- 检查：`((renewed_at IS NULL AND retain_until <= created_at + INTERVAL '180 days') OR (renewed_at IS NOT NULL AND renewed_at >= created_at AND retain_until <= renewed_at + INTERVAL '180 days'))`。
- 查询索引：`user_id,id,current_revision`。
- 查询索引：`retain_until`。

## 个人用餐版本（meal_revisions）

责任分区：实际与回顾。主键：`user_id, id, revision`。

| 字段 | 中文含义 | PostgreSQL / SQLite | 可空 | 默认值 | 约束与说明 |
|---|---|---|---|---|---|
| `user_id` | 所属用户 | TEXT / TEXT | 否 | 无 | 主键组成；外键组成，详见表后 |
| `id` | 对象标识 | TEXT / TEXT | 否 | 无 | 主键组成；外键组成，详见表后 |
| `revision` | 修订号 | BIGINT / INTEGER | 否 | 无 | 主键组成；正整数 |
| `meal_date` | 业务用餐日期 | DATE / TEXT | 否 | 无 |  |
| `meal_slot` | 规范餐次 | TEXT / TEXT | 否 | 无 |  |
| `actual_at` | 实际时点 | TIMESTAMPTZ / TEXT | 是 | 无 |  |
| `note` | 用户自述 | TEXT / TEXT | 是 | 无 |  |
| `confirmed_at` | 用户确认时间 | TIMESTAMPTZ / TEXT | 否 | 无 |  |
| `created_at` | 建立时间 | TIMESTAMPTZ / TEXT | 否 | 无 |  |

关系、约束及索引：

- `user_id` → `user_control(user_id)`；提交时检查，不自动删除关联。
- `user_id,id` → `meal_heads(user_id,id)`；提交时检查，不自动删除关联。
- 检查：`meal_slot IN ('早餐', '午餐', '晚餐', '加餐')`。
- 检查：`revision >= 1`。
- 查询索引：`user_id,meal_date,meal_slot`。

## 个人实际食物（reported_foods）

责任分区：实际与回顾。主键：`user_id, record_id, record_revision, item_id`。

| 字段 | 中文含义 | PostgreSQL / SQLite | 可空 | 默认值 | 约束与说明 |
|---|---|---|---|---|---|
| `user_id` | 所属用户 | TEXT / TEXT | 否 | 无 | 主键组成；外键组成，详见表后 |
| `record_id` | 用餐身份 | TEXT / TEXT | 否 | 无 | 主键组成；外键组成，详见表后 |
| `record_revision` | 用餐修订 | BIGINT / INTEGER | 否 | 无 | 主键组成；外键组成，详见表后；正整数 |
| `item_id` | 条目标识 | TEXT / TEXT | 否 | 无 | 主键组成 |
| `food_name` | 实际食物名称 | TEXT / TEXT | 否 | 无 |  |
| `observation_id` | 食品证据标识 | TEXT / TEXT | 是 | 无 | 外键组成，详见表后 |
| `planned_food_id` | 计划食物出处 | TEXT / TEXT | 是 | 无 | 外键组成，详见表后 |
| `entry_source` | 录入来源 | TEXT / TEXT | 否 | 无 |  |
| `created_at` | 建立时间 | TIMESTAMPTZ / TEXT | 否 | 无 |  |
| `quantity_state` | 个人实际份量状态 | TEXT / TEXT | 否 | 无 |  |
| `quantity_micros` | 个人实际份量定点值 | BIGINT / INTEGER | 是 | 无 | 实际值乘1000000；未知必须为空；0至9000000000000000的整数 |
| `quantity_unit` | 个人实际份量单位 | TEXT / TEXT | 是 | 无 |  |

关系、约束及索引：

- `user_id` → `user_control(user_id)`；提交时检查，不自动删除关联。
- `user_id,record_id,record_revision` → `meal_revisions(user_id,id,revision)`；提交时检查，不自动删除关联。
- `user_id,observation_id` → `food_observations(user_id,id)`；提交时检查，不自动删除关联。
- `user_id,planned_food_id` → `planned_foods(user_id,id)`；提交时检查，不自动删除关联。
- 检查：`entry_source IN ('手动自述', '计划预填', '图文核对')`。
- 检查：`quantity_state IN ('已知', '未知')`。
- 检查：`((quantity_state = '已知' AND quantity_micros IS NOT NULL AND quantity_unit IS NOT NULL) OR (quantity_state = '未知' AND quantity_micros IS NULL))`。
- 检查：`record_revision >= 1`。
- 检查：`quantity_micros IS NULL OR (quantity_micros >= 0 AND quantity_micros <= 9000000000000000)`。
- 查询索引：`user_id,observation_id`。
- 查询索引：`user_id,planned_food_id`。

## 微行动提案（micro_actions）

责任分区：行动与学习。主键：`user_id, id`。

| 字段 | 中文含义 | PostgreSQL / SQLite | 可空 | 默认值 | 约束与说明 |
|---|---|---|---|---|---|
| `user_id` | 所属用户 | TEXT / TEXT | 否 | 无 | 主键组成；外键组成，详见表后 |
| `id` | 对象标识 | TEXT / TEXT | 否 | 无 | 主键组成；外键组成，详见表后 |
| `context_id` | 情境标识 | TEXT / TEXT | 否 | 无 | 外键组成，详见表后 |
| `dimension` | 行动维度 | TEXT / TEXT | 否 | 无 |  |
| `cue` | 行动线索 | TEXT / TEXT | 否 | 无 |  |
| `behavior` | 具体行为 | TEXT / TEXT | 否 | 无 |  |
| `effort` | 努力量 | TEXT / TEXT | 否 | 无 |  |
| `rationale` | 行动依据 | TEXT / TEXT | 否 | 无 |  |
| `replacement_of` | 被替代提案标识 | TEXT / TEXT | 是 | 无 | 外键组成，详见表后 |
| `planned_meal_id` | 关联计划餐次 | TEXT / TEXT | 是 | 无 | 外键组成，详见表后 |
| `current_window_revision` | 当前窗口修订 | BIGINT / INTEGER | 是 | 无 | 外键组成，详见表后；正整数 |
| `current_execution_revision` | 当前执行修订 | BIGINT / INTEGER | 是 | 无 | 外键组成，详见表后；正整数 |
| `row_version` | 并发版本 | BIGINT / INTEGER | 否 | 无 | 正整数 |
| `state` | 身份状态 | TEXT / TEXT | 否 | 无 |  |
| `created_at` | 建立时间 | TIMESTAMPTZ / TEXT | 否 | 无 |  |
| `retain_until` | 保留截止 | TIMESTAMPTZ / TEXT | 否 | 无 | 初次不超过180天；明确续期须留审计依据 |
| `renewed_at` | 续期确认时间 | TIMESTAMPTZ / TEXT | 是 | 无 |  |
| `record_id` | 关联实际用餐标识 | TEXT / TEXT | 是 | 无 | 外键组成，详见表后 |
| `record_revision` | 关联实际用餐修订号 | BIGINT / INTEGER | 是 | 无 | 外键组成，详见表后；正整数 |

关系、约束及索引：

- `user_id` → `user_control(user_id)`；提交时检查，不自动删除关联。
- `user_id,record_id,record_revision` → `meal_revisions(user_id,id,revision)`；提交时检查，不自动删除关联。
- `user_id,context_id` → `context_snapshots(user_id,id)`；提交时检查，不自动删除关联。
- `user_id,replacement_of` → `micro_actions(user_id,id)`；提交时检查，不自动删除关联。
- `user_id,planned_meal_id` → `planned_meals(user_id,id)`；提交时检查，不自动删除关联。
- `user_id,id,current_window_revision` → `action_windows(user_id,action_id,revision)`；提交时检查，不自动删除关联。
- `user_id,id,current_execution_revision` → `execution_revisions(user_id,action_id,revision)`；提交时检查，不自动删除关联。
- 检查：`((record_id IS NULL AND record_revision IS NULL) OR (record_id IS NOT NULL AND record_revision IS NOT NULL))`。
- 检查：`dimension IN ('平替', '顺手加法', '进食顺序', '时序节律')`。
- 检查：`state IN ('有效', '已删除')`。
- 检查：`current_window_revision IS NULL OR (current_window_revision >= 1)`。
- 检查：`current_execution_revision IS NULL OR (current_execution_revision >= 1)`。
- 检查：`row_version >= 1`。
- 检查：`record_revision IS NULL OR (record_revision >= 1)`。
- 检查：`retain_until >= created_at`。
- 检查：`((renewed_at IS NULL AND retain_until <= created_at + INTERVAL '180 days') OR (renewed_at IS NOT NULL AND renewed_at >= created_at AND retain_until <= renewed_at + INTERVAL '180 days'))`。
- 查询索引：`user_id,record_id,record_revision`。
- 查询索引：`user_id,context_id`。
- 查询索引：`user_id,replacement_of`。
- 查询索引：`user_id,planned_meal_id`。
- 查询索引：`user_id,id,current_window_revision`。
- 查询索引：`user_id,id,current_execution_revision`。
- 查询索引：`retain_until`。

## 行动最终决策（action_decisions）

责任分区：行动与学习。主键：`user_id, action_id`。

| 字段 | 中文含义 | PostgreSQL / SQLite | 可空 | 默认值 | 约束与说明 |
|---|---|---|---|---|---|
| `user_id` | 所属用户 | TEXT / TEXT | 否 | 无 | 主键组成；外键组成，详见表后 |
| `action_id` | 行动标识 | TEXT / TEXT | 否 | 无 | 主键组成；外键组成，详见表后 |
| `decision` | 用户决策 | TEXT / TEXT | 否 | 无 |  |
| `confirmed_at` | 用户确认时间 | TIMESTAMPTZ / TEXT | 否 | 无 |  |
| `created_at` | 建立时间 | TIMESTAMPTZ / TEXT | 否 | 无 |  |

关系、约束及索引：

- `user_id` → `user_control(user_id)`；提交时检查，不自动删除关联。
- `user_id,action_id` → `micro_actions(user_id,id)`；提交时检查，不自动删除关联。
- 检查：`decision IN ('采纳', '跳过', '被替代')`。

## 行动窗口修订（action_windows）

责任分区：行动与学习。主键：`user_id, action_id, revision`。

| 字段 | 中文含义 | PostgreSQL / SQLite | 可空 | 默认值 | 约束与说明 |
|---|---|---|---|---|---|
| `user_id` | 所属用户 | TEXT / TEXT | 否 | 无 | 主键组成；外键组成，详见表后 |
| `action_id` | 行动标识 | TEXT / TEXT | 否 | 无 | 主键组成；外键组成，详见表后 |
| `revision` | 修订号 | BIGINT / INTEGER | 否 | 无 | 主键组成；正整数 |
| `starts_at` | 窗口开始 | TIMESTAMPTZ / TEXT | 否 | 无 |  |
| `ends_at` | 窗口结束 | TIMESTAMPTZ / TEXT | 否 | 无 |  |
| `timezone` | 业务时区 | TEXT / TEXT | 否 | 'Asia/Shanghai' |  |
| `reason` | 确认或修正原因 | TEXT / TEXT | 否 | 无 |  |
| `confirmed_at` | 用户确认时间 | TIMESTAMPTZ / TEXT | 否 | 无 |  |
| `created_at` | 建立时间 | TIMESTAMPTZ / TEXT | 否 | 无 |  |

关系、约束及索引：

- `user_id` → `user_control(user_id)`；提交时检查，不自动删除关联。
- `user_id,action_id` → `action_decisions(user_id,action_id)`；提交时检查，不自动删除关联。
- 检查：`ends_at >= starts_at`。
- 检查：`timezone = 'Asia/Shanghai'`。
- 检查：`revision >= 1`。
- 查询索引：`user_id,ends_at`。

## 执行自述修订（execution_revisions）

责任分区：行动与学习。主键：`user_id, action_id, revision`。

| 字段 | 中文含义 | PostgreSQL / SQLite | 可空 | 默认值 | 约束与说明 |
|---|---|---|---|---|---|
| `user_id` | 所属用户 | TEXT / TEXT | 否 | 无 | 主键组成；外键组成，详见表后 |
| `action_id` | 行动标识 | TEXT / TEXT | 否 | 无 | 主键组成；外键组成，详见表后 |
| `revision` | 修订号 | BIGINT / INTEGER | 否 | 无 | 主键组成；正整数 |
| `execution_state` | 有效自述状态 | TEXT / TEXT | 否 | 无 |  |
| `execution_date` | 实际执行日期 | DATE / TEXT | 是 | 无 |  |
| `reported_at` | 报告时间 | TIMESTAMPTZ / TEXT | 否 | 无 |  |
| `note` | 执行自述备注 | TEXT / TEXT | 是 | 无 |  |
| `confirmed_at` | 用户确认时间 | TIMESTAMPTZ / TEXT | 否 | 无 |  |
| `created_at` | 建立时间 | TIMESTAMPTZ / TEXT | 否 | 无 |  |

关系、约束及索引：

- `user_id` → `user_control(user_id)`；提交时检查，不自动删除关联。
- `user_id,action_id` → `action_decisions(user_id,action_id)`；提交时检查，不自动删除关联。
- 检查：`execution_state IN ('完成', '部分', '未完成', '撤回为不确定')`。
- 检查：`((execution_state = '撤回为不确定' AND execution_date IS NULL) OR (execution_state <> '撤回为不确定' AND execution_date IS NOT NULL))`。
- 检查：`revision >= 1`。
- 查询索引：`user_id,execution_date,execution_state`。

## 提醒与回应历史（reminder_events）

责任分区：行动与学习。主键：`user_id, id`。

| 字段 | 中文含义 | PostgreSQL / SQLite | 可空 | 默认值 | 约束与说明 |
|---|---|---|---|---|---|
| `user_id` | 所属用户 | TEXT / TEXT | 否 | 无 | 主键组成；外键组成，详见表后 |
| `id` | 对象标识 | TEXT / TEXT | 否 | 无 | 主键组成 |
| `action_id` | 行动标识 | TEXT / TEXT | 否 | 无 | 外键组成，详见表后 |
| `scheduled_at` | 计划提醒时间 | TIMESTAMPTZ / TEXT | 否 | 无 |  |
| `sent_at` | 实际提醒时间 | TIMESTAMPTZ / TEXT | 是 | 无 |  |
| `responded_at` | 回应时间 | TIMESTAMPTZ / TEXT | 是 | 无 |  |
| `outcome` | 发送结果 | TEXT / TEXT | 否 | 无 |  |
| `authorization_epoch` | 发送授权修订 | BIGINT / INTEGER | 否 | 无 | 正整数 |
| `created_at` | 建立时间 | TIMESTAMPTZ / TEXT | 否 | 无 |  |
| `retain_until` | 保留截止 | TIMESTAMPTZ / TEXT | 否 | 无 | 初次不超过180天；明确续期须留审计依据 |
| `renewed_at` | 续期确认时间 | TIMESTAMPTZ / TEXT | 是 | 无 |  |

关系、约束及索引：

- `user_id` → `user_control(user_id)`；提交时检查，不自动删除关联。
- `user_id,action_id` → `action_decisions(user_id,action_id)`；提交时检查，不自动删除关联。
- 检查：`outcome IN ('待发送', '已发送', '已取消', '失败')`。
- 检查：`authorization_epoch >= 1`。
- 检查：`retain_until >= created_at`。
- 检查：`((renewed_at IS NULL AND retain_until <= created_at + INTERVAL '180 days') OR (renewed_at IS NOT NULL AND renewed_at >= created_at AND retain_until <= renewed_at + INTERVAL '180 days'))`。
- 查询索引：`user_id,action_id`。
- 查询索引：`user_id,scheduled_at`。
- 查询索引：`retain_until`。

## 交互与提醒状态（interaction_settings）

责任分区：行动与学习。主键：`user_id`。

| 字段 | 中文含义 | PostgreSQL / SQLite | 可空 | 默认值 | 约束与说明 |
|---|---|---|---|---|---|
| `user_id` | 所属用户 | TEXT / TEXT | 否 | 无 | 主键组成；外键组成，详见表后 |
| `row_version` | 并发版本 | BIGINT / INTEGER | 否 | 无 | 正整数 |
| `unanswered_count` | 连续未响应数 | BIGINT / INTEGER | 否 | 无 | 非负整数 |
| `backoff_until` | 静默截止 | TIMESTAMPTZ / TEXT | 是 | 无 |  |
| `companion_enabled` | 陪伴开启 | SMALLINT / INTEGER | 否 | 无 | 0或1 |
| `collection_enabled` | 图鉴开启 | SMALLINT / INTEGER | 否 | 无 | 0或1 |
| `calibration_enabled` | 校准开启 | SMALLINT / INTEGER | 否 | 无 | 0或1 |
| `ranking_version` | 内环规则版本 | TEXT / TEXT | 否 | 无 |  |
| `ranking_parameters` | 内环参数及原因 | JSONB / TEXT | 否 | 无 |  |
| `created_at` | 建立时间 | TIMESTAMPTZ / TEXT | 否 | 无 |  |
| `retain_until` | 保留截止 | TIMESTAMPTZ / TEXT | 否 | 无 | 初次不超过180天；明确续期须留审计依据 |
| `renewed_at` | 续期确认时间 | TIMESTAMPTZ / TEXT | 是 | 无 |  |

关系、约束及索引：

- `user_id` → `user_control(user_id)`；提交时检查，不自动删除关联。
- 检查：`row_version >= 1`。
- 检查：`unanswered_count >= 0`。
- 检查：`companion_enabled IN (0, 1)`。
- 检查：`collection_enabled IN (0, 1)`。
- 检查：`calibration_enabled IN (0, 1)`。
- 检查：`retain_until >= created_at`。
- 检查：`((renewed_at IS NULL AND retain_until <= created_at + INTERVAL '180 days') OR (renewed_at IS NOT NULL AND renewed_at >= created_at AND retain_until <= renewed_at + INTERVAL '180 days'))`。
- 查询索引：`retain_until`。

## 内环决策记录（interaction_events）

责任分区：行动与学习。主键：`user_id, id`。

| 字段 | 中文含义 | PostgreSQL / SQLite | 可空 | 默认值 | 约束与说明 |
|---|---|---|---|---|---|
| `user_id` | 所属用户 | TEXT / TEXT | 否 | 无 | 主键组成；外键组成，详见表后 |
| `id` | 对象标识 | TEXT / TEXT | 否 | 无 | 主键组成 |
| `context_id` | 情境标识 | TEXT / TEXT | 否 | 无 | 外键组成，详见表后 |
| `action_id` | 行动标识 | TEXT / TEXT | 是 | 无 | 外键组成，详见表后 |
| `event_kind` | 交互类型 | TEXT / TEXT | 否 | 无 |  |
| `rule_version` | 排序规则版本 | TEXT / TEXT | 否 | 无 |  |
| `explanation` | 依据及参数 | JSONB / TEXT | 否 | 无 |  |
| `cooldown_until` | 情境冷却截止 | TIMESTAMPTZ / TEXT | 是 | 无 |  |
| `created_at` | 建立时间 | TIMESTAMPTZ / TEXT | 否 | 无 |  |
| `retain_until` | 保留截止 | TIMESTAMPTZ / TEXT | 否 | 无 | 初次不超过180天；明确续期须留审计依据 |
| `renewed_at` | 续期确认时间 | TIMESTAMPTZ / TEXT | 是 | 无 |  |

关系、约束及索引：

- `user_id` → `user_control(user_id)`；提交时检查，不自动删除关联。
- `user_id,context_id` → `context_snapshots(user_id,id)`；提交时检查，不自动删除关联。
- `user_id,action_id` → `micro_actions(user_id,id)`；提交时检查，不自动删除关联。
- 检查：`event_kind IN ('采纳', '换一个', '暂不需要', '规则调整')`。
- 检查：`retain_until >= created_at`。
- 检查：`((renewed_at IS NULL AND retain_until <= created_at + INTERVAL '180 days') OR (renewed_at IS NOT NULL AND renewed_at >= created_at AND retain_until <= renewed_at + INTERVAL '180 days'))`。
- 查询索引：`user_id,context_id`。
- 查询索引：`user_id,action_id`。
- 查询索引：`user_id,context_id,cooldown_until`。
- 查询索引：`retain_until`。

## 偏好与情境候选（learning_candidates）

责任分区：行动与学习。主键：`user_id, id`。

| 字段 | 中文含义 | PostgreSQL / SQLite | 可空 | 默认值 | 约束与说明 |
|---|---|---|---|---|---|
| `user_id` | 所属用户 | TEXT / TEXT | 否 | 无 | 主键组成；外键组成，详见表后 |
| `id` | 对象标识 | TEXT / TEXT | 否 | 无 | 主键组成 |
| `candidate_kind` | 候选类型 | TEXT / TEXT | 否 | 无 |  |
| `hypothesis` | 待核对内容 | JSONB / TEXT | 否 | 无 |  |
| `state` | 核对状态 | TEXT / TEXT | 否 | 无 |  |
| `authorization_epoch` | 来源授权修订 | BIGINT / INTEGER | 否 | 无 | 正整数 |
| `range_start` | 证据开始日期 | DATE / TEXT | 否 | 无 |  |
| `range_end` | 证据结束日期 | DATE / TEXT | 否 | 无 |  |
| `confirmed_at` | 核对时间 | TIMESTAMPTZ / TEXT | 是 | 无 |  |
| `created_at` | 建立时间 | TIMESTAMPTZ / TEXT | 否 | 无 |  |
| `retain_until` | 保留截止 | TIMESTAMPTZ / TEXT | 否 | 无 | 初次不超过180天；明确续期须留审计依据 |
| `renewed_at` | 续期确认时间 | TIMESTAMPTZ / TEXT | 是 | 无 |  |

关系、约束及索引：

- `user_id` → `user_control(user_id)`；提交时检查，不自动删除关联。
- 检查：`candidate_kind IN ('稳定偏好', '情境线索')`。
- 检查：`state IN ('待核对', '已确认', '已拒绝', '已到期')`。
- 检查：`range_end >= range_start`。
- 检查：`authorization_epoch >= 1`。
- 检查：`retain_until >= created_at`。
- 检查：`((renewed_at IS NULL AND retain_until <= created_at + INTERVAL '180 days') OR (renewed_at IS NOT NULL AND renewed_at >= created_at AND retain_until <= renewed_at + INTERVAL '180 days'))`。
- 查询索引：`retain_until`。

## 学习证据引用（learning_evidence）

责任分区：行动与学习。主键：`user_id, id`。

| 字段 | 中文含义 | PostgreSQL / SQLite | 可空 | 默认值 | 约束与说明 |
|---|---|---|---|---|---|
| `user_id` | 所属用户 | TEXT / TEXT | 否 | 无 | 主键组成；外键组成，详见表后 |
| `id` | 对象标识 | TEXT / TEXT | 否 | 无 | 主键组成 |
| `candidate_id` | 候选标识 | TEXT / TEXT | 否 | 无 | 外键组成，详见表后 |
| `action_id` | 来源行动 | TEXT / TEXT | 是 | 无 | 外键组成，详见表后 |
| `execution_revision` | 来源执行修订 | BIGINT / INTEGER | 是 | 无 | 外键组成，详见表后；正整数 |
| `record_id` | 来源用餐 | TEXT / TEXT | 是 | 无 | 外键组成，详见表后 |
| `record_revision` | 来源用餐修订 | BIGINT / INTEGER | 是 | 无 | 外键组成，详见表后；正整数 |
| `created_at` | 建立时间 | TIMESTAMPTZ / TEXT | 否 | 无 |  |

关系、约束及索引：

- `user_id` → `user_control(user_id)`；提交时检查，不自动删除关联。
- `user_id,candidate_id` → `learning_candidates(user_id,id)`；提交时检查，不自动删除关联。
- `user_id,action_id,execution_revision` → `execution_revisions(user_id,action_id,revision)`；提交时检查，不自动删除关联。
- `user_id,record_id,record_revision` → `meal_revisions(user_id,id,revision)`；提交时检查，不自动删除关联。
- 检查：`((action_id IS NOT NULL AND execution_revision IS NOT NULL AND record_id IS NULL AND record_revision IS NULL) OR (action_id IS NULL AND execution_revision IS NULL AND record_id IS NOT NULL AND record_revision IS NOT NULL))`。
- 检查：`execution_revision IS NULL OR (execution_revision >= 1)`。
- 检查：`record_revision IS NULL OR (record_revision >= 1)`。
- 查询索引：`user_id,candidate_id`。
- 查询索引：`user_id,action_id,execution_revision`。
- 查询索引：`user_id,record_id,record_revision`。

## 稳定偏好修订（preference_rule_revisions）

责任分区：行动与学习。主键：`user_id, id, revision`。

| 字段 | 中文含义 | PostgreSQL / SQLite | 可空 | 默认值 | 约束与说明 |
|---|---|---|---|---|---|
| `user_id` | 所属用户 | TEXT / TEXT | 否 | 无 | 主键组成；外键组成，详见表后 |
| `id` | 对象标识 | TEXT / TEXT | 否 | 无 | 主键组成 |
| `revision` | 修订号 | BIGINT / INTEGER | 否 | 无 | 主键组成；正整数 |
| `candidate_id` | 已确认候选 | TEXT / TEXT | 否 | 无 | 外键组成，详见表后 |
| `rule_content` | 条件方向与适用范围 | JSONB / TEXT | 否 | 无 |  |
| `state` | 规则状态 | TEXT / TEXT | 否 | 无 |  |
| `confirmed_at` | 用户确认时间 | TIMESTAMPTZ / TEXT | 否 | 无 |  |
| `created_at` | 建立时间 | TIMESTAMPTZ / TEXT | 否 | 无 |  |
| `retain_until` | 保留截止 | TIMESTAMPTZ / TEXT | 否 | 无 | 初次不超过180天；明确续期须留审计依据 |
| `renewed_at` | 续期确认时间 | TIMESTAMPTZ / TEXT | 是 | 无 |  |

关系、约束及索引：

- `user_id` → `user_control(user_id)`；提交时检查，不自动删除关联。
- `user_id,candidate_id` → `learning_candidates(user_id,id)`；提交时检查，不自动删除关联。
- 检查：`state IN ('有效', '已停用', '已删除')`。
- 检查：`revision >= 1`。
- 检查：`retain_until >= created_at`。
- 检查：`((renewed_at IS NULL AND retain_until <= created_at + INTERVAL '180 days') OR (renewed_at IS NOT NULL AND renewed_at >= created_at AND retain_until <= renewed_at + INTERVAL '180 days'))`。
- 查询索引：`user_id,candidate_id`。
- 查询索引：`retain_until`。

## 校准回答修订（calibration_revisions）

责任分区：行动与学习。主键：`user_id, question_key, revision`。

| 字段 | 中文含义 | PostgreSQL / SQLite | 可空 | 默认值 | 约束与说明 |
|---|---|---|---|---|---|
| `user_id` | 所属用户 | TEXT / TEXT | 否 | 无 | 主键组成；外键组成，详见表后 |
| `question_key` | 题目标识 | TEXT / TEXT | 否 | 无 | 主键组成 |
| `question_version` | 题目版本 | TEXT / TEXT | 否 | 无 |  |
| `revision` | 修订号 | BIGINT / INTEGER | 否 | 无 | 主键组成；正整数 |
| `answer` | 确认回答 | JSONB / TEXT | 是 | 无 |  |
| `state` | 回答状态 | TEXT / TEXT | 否 | 无 |  |
| `confirmed_at` | 用户确认时间 | TIMESTAMPTZ / TEXT | 否 | 无 |  |
| `created_at` | 建立时间 | TIMESTAMPTZ / TEXT | 否 | 无 |  |
| `retain_until` | 保留截止 | TIMESTAMPTZ / TEXT | 否 | 无 | 初次不超过180天；明确续期须留审计依据 |
| `renewed_at` | 续期确认时间 | TIMESTAMPTZ / TEXT | 是 | 无 |  |

关系、约束及索引：

- `user_id` → `user_control(user_id)`；提交时检查，不自动删除关联。
- 检查：`state IN ('已确认', '已删除')`。
- 检查：`((state = '已确认' AND answer IS NOT NULL) OR (state = '已删除' AND answer IS NULL))`。
- 检查：`revision >= 1`。
- 检查：`retain_until >= created_at`。
- 检查：`((renewed_at IS NULL AND retain_until <= created_at + INTERVAL '180 days') OR (renewed_at IS NOT NULL AND renewed_at >= created_at AND retain_until <= renewed_at + INTERVAL '180 days'))`。
- 查询索引：`retain_until`。

## 预期餐次版本（expected_schedules）

责任分区：实际与回顾。主键：`user_id, week_start, revision`。

| 字段 | 中文含义 | PostgreSQL / SQLite | 可空 | 默认值 | 约束与说明 |
|---|---|---|---|---|---|
| `user_id` | 所属用户 | TEXT / TEXT | 否 | 无 | 主键组成；外键组成，详见表后 |
| `week_start` | 自然周起始 | DATE / TEXT | 否 | 无 | 主键组成 |
| `revision` | 修订号 | BIGINT / INTEGER | 否 | 无 | 主键组成；正整数 |
| `confirmed_at` | 用户确认时间 | TIMESTAMPTZ / TEXT | 否 | 无 |  |
| `created_at` | 建立时间 | TIMESTAMPTZ / TEXT | 否 | 无 |  |
| `retain_until` | 保留截止 | TIMESTAMPTZ / TEXT | 否 | 无 | 初次不超过180天；明确续期须留审计依据 |
| `renewed_at` | 续期确认时间 | TIMESTAMPTZ / TEXT | 是 | 无 |  |

关系、约束及索引：

- `user_id` → `user_control(user_id)`；提交时检查，不自动删除关联。
- 检查：`revision >= 1`。
- 检查：`retain_until >= created_at`。
- 检查：`((renewed_at IS NULL AND retain_until <= created_at + INTERVAL '180 days') OR (renewed_at IS NOT NULL AND renewed_at >= created_at AND retain_until <= renewed_at + INTERVAL '180 days'))`。
- 检查：`EXTRACT(ISODOW FROM week_start) = 1`。
- 查询索引：`retain_until`。

## 预期餐次槽位（expected_slots）

责任分区：实际与回顾。主键：`user_id, week_start, schedule_revision, meal_date, meal_slot`。

| 字段 | 中文含义 | PostgreSQL / SQLite | 可空 | 默认值 | 约束与说明 |
|---|---|---|---|---|---|
| `user_id` | 所属用户 | TEXT / TEXT | 否 | 无 | 主键组成；外键组成，详见表后 |
| `week_start` | 自然周起始 | DATE / TEXT | 否 | 无 | 主键组成；外键组成，详见表后 |
| `schedule_revision` | 预期餐次修订 | BIGINT / INTEGER | 否 | 无 | 主键组成；外键组成，详见表后；正整数 |
| `meal_date` | 餐次日期 | DATE / TEXT | 否 | 无 | 主键组成 |
| `meal_slot` | 规范餐次 | TEXT / TEXT | 否 | 无 | 主键组成 |
| `created_at` | 建立时间 | TIMESTAMPTZ / TEXT | 否 | 无 |  |

关系、约束及索引：

- `user_id` → `user_control(user_id)`；提交时检查，不自动删除关联。
- `user_id,week_start,schedule_revision` → `expected_schedules(user_id,week_start,revision)`；提交时检查，不自动删除关联。
- 检查：`meal_slot IN ('早餐', '午餐', '晚餐', '加餐')`。
- 检查：`schedule_revision >= 1`。
- 检查：`EXTRACT(ISODOW FROM week_start) = 1`。
- 检查：`meal_date >= week_start AND meal_date <= week_start + 6`。

## 恢复周期确认（recovery_episodes）

责任分区：实际与回顾。主键：`user_id, id`。

| 字段 | 中文含义 | PostgreSQL / SQLite | 可空 | 默认值 | 约束与说明 |
|---|---|---|---|---|---|
| `user_id` | 所属用户 | TEXT / TEXT | 否 | 无 | 主键组成；外键组成，详见表后 |
| `id` | 对象标识 | TEXT / TEXT | 否 | 无 | 主键组成 |
| `row_version` | 并发版本 | BIGINT / INTEGER | 否 | 无 | 正整数 |
| `deviation_at` | 确认偏离起点 | TIMESTAMPTZ / TEXT | 是 | 无 |  |
| `return_at` | 确认回归终点 | TIMESTAMPTZ / TEXT | 是 | 无 |  |
| `reason` | 用户确认情境 | TEXT / TEXT | 否 | 无 |  |
| `confirmed_at` | 用户确认时间 | TIMESTAMPTZ / TEXT | 否 | 无 |  |
| `created_at` | 建立时间 | TIMESTAMPTZ / TEXT | 否 | 无 |  |
| `retain_until` | 保留截止 | TIMESTAMPTZ / TEXT | 否 | 无 | 初次不超过180天；明确续期须留审计依据 |
| `renewed_at` | 续期确认时间 | TIMESTAMPTZ / TEXT | 是 | 无 |  |

关系、约束及索引：

- `user_id` → `user_control(user_id)`；提交时检查，不自动删除关联。
- 检查：`return_at IS NULL OR (deviation_at IS NOT NULL AND return_at >= deviation_at)`。
- 检查：`row_version >= 1`。
- 检查：`retain_until >= created_at`。
- 检查：`((renewed_at IS NULL AND retain_until <= created_at + INTERVAL '180 days') OR (renewed_at IS NOT NULL AND renewed_at >= created_at AND retain_until <= renewed_at + INTERVAL '180 days'))`。
- 查询索引：`retain_until`。

## 恢复排除时段（recovery_exclusions）

责任分区：实际与回顾。主键：`user_id, id`。

| 字段 | 中文含义 | PostgreSQL / SQLite | 可空 | 默认值 | 约束与说明 |
|---|---|---|---|---|---|
| `user_id` | 所属用户 | TEXT / TEXT | 否 | 无 | 主键组成；外键组成，详见表后 |
| `id` | 对象标识 | TEXT / TEXT | 否 | 无 | 主键组成 |
| `episode_id` | 恢复周期标识 | TEXT / TEXT | 否 | 无 | 外键组成，详见表后 |
| `starts_at` | 排除开始 | TIMESTAMPTZ / TEXT | 否 | 无 |  |
| `ends_at` | 排除结束 | TIMESTAMPTZ / TEXT | 否 | 无 |  |
| `reason` | 排除原因 | TEXT / TEXT | 否 | 无 |  |
| `confirmed_at` | 用户确认时间 | TIMESTAMPTZ / TEXT | 否 | 无 |  |
| `created_at` | 建立时间 | TIMESTAMPTZ / TEXT | 否 | 无 |  |

关系、约束及索引：

- `user_id` → `user_control(user_id)`；提交时检查，不自动删除关联。
- `user_id,episode_id` → `recovery_episodes(user_id,id)`；提交时检查，不自动删除关联。
- 检查：`ends_at >= starts_at`。
- 查询索引：`user_id,episode_id`。

## 连续周呈现修订（week_presentations）

责任分区：实际与回顾。主键：`user_id, week_start, revision`。

| 字段 | 中文含义 | PostgreSQL / SQLite | 可空 | 默认值 | 约束与说明 |
|---|---|---|---|---|---|
| `user_id` | 所属用户 | TEXT / TEXT | 否 | 无 | 主键组成；外键组成，详见表后 |
| `week_start` | 自然周起始 | DATE / TEXT | 否 | 无 | 主键组成 |
| `revision` | 修订号 | BIGINT / INTEGER | 否 | 无 | 主键组成；正整数 |
| `override_kind` | 呈现决定 | TEXT / TEXT | 否 | 无 |  |
| `reason` | 用户确认依据 | TEXT / TEXT | 否 | 无 |  |
| `confirmed_at` | 用户确认时间 | TIMESTAMPTZ / TEXT | 否 | 无 |  |
| `created_at` | 建立时间 | TIMESTAMPTZ / TEXT | 否 | 无 |  |
| `retain_until` | 保留截止 | TIMESTAMPTZ / TEXT | 否 | 无 | 初次不超过180天；明确续期须留审计依据 |
| `renewed_at` | 续期确认时间 | TIMESTAMPTZ / TEXT | 是 | 无 |  |

关系、约束及索引：

- `user_id` → `user_control(user_id)`；提交时检查，不自动删除关联。
- 检查：`override_kind IN ('冻结', '取消冻结')`。
- 检查：`revision >= 1`。
- 检查：`retain_until >= created_at`。
- 检查：`((renewed_at IS NULL AND retain_until <= created_at + INTERVAL '180 days') OR (renewed_at IS NOT NULL AND renewed_at >= created_at AND retain_until <= renewed_at + INTERVAL '180 days'))`。
- 检查：`EXTRACT(ISODOW FROM week_start) = 1`。
- 查询索引：`retain_until`。

## 持久提交回执（command_receipts）

责任分区：命令与数据控制。主键：`user_id, operation_key`。

| 字段 | 中文含义 | PostgreSQL / SQLite | 可空 | 默认值 | 约束与说明 |
|---|---|---|---|---|---|
| `user_id` | 所属用户 | TEXT / TEXT | 否 | 无 | 主键组成；外键组成，详见表后 |
| `operation_key` | 操作标识 | TEXT / TEXT | 否 | 无 | 主键组成 |
| `request_hash` | 规范化请求摘要 | TEXT / TEXT | 否 | 无 |  |
| `commit_id` | 唯一提交标识 | TEXT / TEXT | 否 | 无 |  |
| `task_id` | 来源任务标识 | TEXT / TEXT | 是 | 无 | 外键组成，详见表后；任务过期后可清除此引用，不代表回执失效 |
| `authorization_epoch` | 提交授权修订 | BIGINT / INTEGER | 否 | 无 | 正整数 |
| `data_revision` | 提交数据修订 | BIGINT / INTEGER | 否 | 无 | 正整数 |
| `result_refs` | 结果标识与版本 | JSONB / TEXT | 否 | 无 | 只保留必要标识，恢复时重新授权读取 |
| `issued_at` | 操作令牌签发时间 | TIMESTAMPTZ / TEXT | 否 | 无 |  |
| `expires_at` | 回执过期时间 | TIMESTAMPTZ / TEXT | 否 | 无 |  |
| `created_at` | 建立时间 | TIMESTAMPTZ / TEXT | 否 | 无 |  |

关系、约束及索引：

- `user_id` → `user_control(user_id)`；提交时检查，不自动删除关联。
- `user_id,task_id` → `task_sessions(user_id,id)`；提交时检查，不自动删除关联。
- 唯一：`user_id,commit_id`。
- 检查：`authorization_epoch >= 1`。
- 检查：`data_revision >= 1`。
- 检查：`expires_at >= created_at`。
- 检查：`expires_at <= created_at + INTERVAL '180 days'`。
- 查询索引：`user_id,task_id`。
- 查询索引：`expires_at`。

## 最小化业务事件（audit_events）

责任分区：命令与数据控制。主键：`user_id, id`。

| 字段 | 中文含义 | PostgreSQL / SQLite | 可空 | 默认值 | 约束与说明 |
|---|---|---|---|---|---|
| `user_id` | 所属用户 | TEXT / TEXT | 否 | 无 | 主键组成；外键组成，详见表后 |
| `id` | 事件标识 | TEXT / TEXT | 否 | 无 | 主键组成 |
| `commit_id` | 提交标识 | TEXT / TEXT | 否 | 无 | 外键组成，详见表后 |
| `event_kind` | 事件类型 | TEXT / TEXT | 否 | 无 |  |
| `object_kind` | 对象类型 | TEXT / TEXT | 否 | 无 |  |
| `object_id` | 对象标识 | TEXT / TEXT | 否 | 无 |  |
| `object_revision` | 对象修订 | BIGINT / INTEGER | 是 | 无 | 正整数 |
| `reason_code` | 原因编码 | TEXT / TEXT | 是 | 无 |  |
| `created_at` | 建立时间 | TIMESTAMPTZ / TEXT | 否 | 无 |  |
| `retain_until` | 保留截止 | TIMESTAMPTZ / TEXT | 否 | 无 | 初次不超过180天；明确续期须留审计依据 |
| `renewed_at` | 续期确认时间 | TIMESTAMPTZ / TEXT | 是 | 无 |  |

关系、约束及索引：

- `user_id` → `user_control(user_id)`；提交时检查，不自动删除关联。
- `user_id,commit_id` → `command_receipts(user_id,commit_id)`；提交时检查，不自动删除关联。
- 检查：`object_revision IS NULL OR (object_revision >= 1)`。
- 检查：`retain_until >= created_at`。
- 检查：`((renewed_at IS NULL AND retain_until <= created_at + INTERVAL '180 days') OR (renewed_at IS NOT NULL AND renewed_at >= created_at AND retain_until <= renewed_at + INTERVAL '180 days'))`。
- 查询索引：`user_id,commit_id`。
- 查询索引：`retain_until`。

## 导出删除清理任务（data_control_jobs）

责任分区：命令与数据控制。主键：`user_id, id`。

| 字段 | 中文含义 | PostgreSQL / SQLite | 可空 | 默认值 | 约束与说明 |
|---|---|---|---|---|---|
| `user_id` | 所属用户 | TEXT / TEXT | 否 | 无 | 主键组成；外键组成，详见表后 |
| `id` | 对象标识 | TEXT / TEXT | 否 | 无 | 主键组成 |
| `job_kind` | 处理类型 | TEXT / TEXT | 否 | 无 |  |
| `state` | 处理进度 | TEXT / TEXT | 否 | 无 |  |
| `scope_manifest` | 范围与断点 | JSONB / TEXT | 否 | 无 |  |
| `requested_at` | 请求时间 | TIMESTAMPTZ / TEXT | 否 | 无 |  |
| `deadline_at` | 目标截止 | TIMESTAMPTZ / TEXT | 否 | 无 |  |
| `completed_at` | 完成时间 | TIMESTAMPTZ / TEXT | 是 | 无 |  |
| `artifact_key` | 临时导出文件键 | TEXT / TEXT | 是 | 无 |  |
| `artifact_expires_at` | 导出文件过期 | TIMESTAMPTZ / TEXT | 是 | 无 |  |
| `failure_code` | 失败原因编码 | TEXT / TEXT | 是 | 无 |  |
| `created_at` | 建立时间 | TIMESTAMPTZ / TEXT | 否 | 无 |  |

关系、约束及索引：

- `user_id` → `user_control(user_id)`；提交时检查，不自动删除关联。
- 检查：`job_kind IN ('导出', '主动删除', '期限清理')`。
- 检查：`state IN ('待处理', '处理中', '已完成', '失败')`。
- 检查：`deadline_at >= requested_at`。
- 检查：`state <> '已完成' OR completed_at IS NOT NULL`。
- 检查：`job_kind <> '主动删除' OR deadline_at <= requested_at + INTERVAL '1 days'`。
- 查询索引：`state,deadline_at`。
