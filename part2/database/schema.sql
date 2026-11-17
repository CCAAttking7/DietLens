-- DietLens 第二次作业：数据库候选设计，仅保存，不执行。
-- 类型、约束与删除顺序以数据字典和数据库设计正文为准。

-- 用户处理控制（授权与证据）
CREATE TABLE user_control (
    user_id TEXT NOT NULL,
    external_subject TEXT,
    processing_state TEXT NOT NULL,
    authorization_epoch BIGINT NOT NULL,
    data_revision BIGINT NOT NULL,
    current_profile_revision BIGINT,
    delete_requested_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ NOT NULL,
    PRIMARY KEY (user_id),
    UNIQUE (external_subject),
    CHECK (processing_state IN ('正常', '待删除', '清理中', '清理失败', '已清理待备份到期')),
    CHECK (authorization_epoch >= 1),
    CHECK (data_revision >= 1),
    CHECK (current_profile_revision IS NULL OR (current_profile_revision >= 1))
);
CREATE INDEX ix_user_control_0 ON user_control (user_id, current_profile_revision);

-- 档案确认版本（授权与证据）
CREATE TABLE profile_revisions (
    user_id TEXT NOT NULL,
    revision BIGINT NOT NULL,
    confirmed_fields JSONB NOT NULL,
    confirmed_at TIMESTAMPTZ NOT NULL,
    created_at TIMESTAMPTZ NOT NULL,
    retain_until TIMESTAMPTZ NOT NULL,
    renewed_at TIMESTAMPTZ,
    PRIMARY KEY (user_id, revision),
    CHECK (revision >= 1),
    CHECK (retain_until >= created_at),
    CHECK (((renewed_at IS NULL AND retain_until <= created_at + INTERVAL '180 days') OR (renewed_at IS NOT NULL AND renewed_at >= created_at AND retain_until <= renewed_at + INTERVAL '180 days'))),
    FOREIGN KEY (user_id) REFERENCES user_control (user_id) ON DELETE NO ACTION DEFERRABLE INITIALLY DEFERRED
);
CREATE INDEX ix_profile_revisions_0 ON profile_revisions (retain_until);

-- 临时图片（授权与证据）
CREATE TABLE media_assets (
    user_id TEXT NOT NULL,
    id TEXT NOT NULL,
    storage_key TEXT,
    media_kind TEXT NOT NULL,
    content_hash TEXT NOT NULL,
    expires_at TIMESTAMPTZ NOT NULL,
    processing_state TEXT NOT NULL,
    created_at TIMESTAMPTZ NOT NULL,
    retain_until TIMESTAMPTZ NOT NULL,
    renewed_at TIMESTAMPTZ,
    PRIMARY KEY (user_id, id),
    CHECK (processing_state IN ('可用', '待清理', '已清理')),
    CHECK (((processing_state = '已清理' AND storage_key IS NULL) OR (processing_state <> '已清理' AND storage_key IS NOT NULL))),
    CHECK (retain_until >= created_at),
    CHECK (((renewed_at IS NULL AND retain_until <= created_at + INTERVAL '180 days') OR (renewed_at IS NOT NULL AND renewed_at >= created_at AND retain_until <= renewed_at + INTERVAL '180 days'))),
    CHECK (expires_at >= created_at),
    CHECK (expires_at <= created_at + INTERVAL '1 days'),
    FOREIGN KEY (user_id) REFERENCES user_control (user_id) ON DELETE NO ACTION DEFERRABLE INITIALLY DEFERRED
);
CREATE INDEX ix_media_assets_0 ON media_assets (expires_at);
CREATE INDEX ix_media_assets_1 ON media_assets (retain_until);

-- 用途授权修订（授权与证据）
CREATE TABLE consent_revisions (
    user_id TEXT NOT NULL,
    purpose TEXT NOT NULL,
    scope_key TEXT NOT NULL,
    revision BIGINT NOT NULL,
    asset_id TEXT,
    allowed SMALLINT NOT NULL,
    recipient TEXT,
    authorization_epoch BIGINT NOT NULL,
    confirmed_at TIMESTAMPTZ NOT NULL,
    created_at TIMESTAMPTZ NOT NULL,
    retain_until TIMESTAMPTZ NOT NULL,
    renewed_at TIMESTAMPTZ,
    PRIMARY KEY (user_id, purpose, scope_key, revision),
    CHECK (purpose IN ('历史分析', '图片外传', '提醒')),
    CHECK (((purpose = '图片外传' AND asset_id IS NOT NULL AND scope_key = asset_id AND recipient IS NOT NULL) OR (purpose <> '图片外传' AND asset_id IS NULL AND scope_key = '全域'))),
    CHECK (revision >= 1),
    CHECK (allowed IN (0, 1)),
    CHECK (authorization_epoch >= 1),
    CHECK (retain_until >= created_at),
    CHECK (((renewed_at IS NULL AND retain_until <= created_at + INTERVAL '180 days') OR (renewed_at IS NOT NULL AND renewed_at >= created_at AND retain_until <= renewed_at + INTERVAL '180 days'))),
    FOREIGN KEY (user_id) REFERENCES user_control (user_id) ON DELETE NO ACTION DEFERRABLE INITIALLY DEFERRED,
    FOREIGN KEY (user_id, asset_id) REFERENCES media_assets (user_id, id) ON DELETE NO ACTION DEFERRABLE INITIALLY DEFERRED
);
CREATE INDEX ix_consent_revisions_0 ON consent_revisions (user_id, asset_id);
CREATE INDEX ix_consent_revisions_1 ON consent_revisions (retain_until);

-- 临时任务会话（授权与证据）
CREATE TABLE task_sessions (
    user_id TEXT NOT NULL,
    id TEXT NOT NULL,
    task_kind TEXT NOT NULL,
    state TEXT NOT NULL,
    draft_revision BIGINT NOT NULL,
    draft_payload JSONB NOT NULL,
    authorization_epoch BIGINT NOT NULL,
    expires_at TIMESTAMPTZ NOT NULL,
    created_at TIMESTAMPTZ NOT NULL,
    PRIMARY KEY (user_id, id),
    CHECK (state IN ('进行中', '已暂停', '已取消', '已完成')),
    CHECK (draft_revision >= 1),
    CHECK (authorization_epoch >= 1),
    CHECK (expires_at >= created_at),
    CHECK (expires_at <= created_at + INTERVAL '7 days'),
    FOREIGN KEY (user_id) REFERENCES user_control (user_id) ON DELETE NO ACTION DEFERRABLE INITIALLY DEFERRED
);
CREATE INDEX ix_task_sessions_0 ON task_sessions (expires_at);

-- 已确认情境（授权与证据）
CREATE TABLE context_snapshots (
    user_id TEXT NOT NULL,
    id TEXT NOT NULL,
    profile_revision BIGINT NOT NULL,
    context_key TEXT NOT NULL,
    situation JSONB NOT NULL,
    authorization_epoch BIGINT NOT NULL,
    confirmed_at TIMESTAMPTZ NOT NULL,
    created_at TIMESTAMPTZ NOT NULL,
    retain_until TIMESTAMPTZ NOT NULL,
    renewed_at TIMESTAMPTZ,
    PRIMARY KEY (user_id, id),
    CHECK (profile_revision >= 1),
    CHECK (authorization_epoch >= 1),
    CHECK (retain_until >= created_at),
    CHECK (((renewed_at IS NULL AND retain_until <= created_at + INTERVAL '180 days') OR (renewed_at IS NOT NULL AND renewed_at >= created_at AND retain_until <= renewed_at + INTERVAL '180 days'))),
    FOREIGN KEY (user_id) REFERENCES user_control (user_id) ON DELETE NO ACTION DEFERRABLE INITIALLY DEFERRED,
    FOREIGN KEY (user_id, profile_revision) REFERENCES profile_revisions (user_id, revision) ON DELETE NO ACTION DEFERRABLE INITIALLY DEFERRED
);
CREATE INDEX ix_context_snapshots_0 ON context_snapshots (user_id, profile_revision);
CREATE INDEX ix_context_snapshots_1 ON context_snapshots (user_id, context_key);
CREATE INDEX ix_context_snapshots_2 ON context_snapshots (retain_until);

-- 证据来源（授权与证据）
CREATE TABLE source_references (
    user_id TEXT NOT NULL,
    id TEXT NOT NULL,
    source_kind TEXT NOT NULL,
    source_locator TEXT NOT NULL,
    specification TEXT,
    published_at TIMESTAMPTZ,
    acquired_at TIMESTAMPTZ NOT NULL,
    asset_id TEXT,
    asset_digest TEXT,
    verification_note TEXT,
    created_at TIMESTAMPTZ NOT NULL,
    retain_until TIMESTAMPTZ NOT NULL,
    renewed_at TIMESTAMPTZ,
    PRIMARY KEY (user_id, id),
    CHECK (source_kind IN ('用户自述', '商品标签', '菜单', '公开资料', '本地编码')),
    CHECK (retain_until >= created_at),
    CHECK (((renewed_at IS NULL AND retain_until <= created_at + INTERVAL '180 days') OR (renewed_at IS NOT NULL AND renewed_at >= created_at AND retain_until <= renewed_at + INTERVAL '180 days'))),
    FOREIGN KEY (user_id) REFERENCES user_control (user_id) ON DELETE NO ACTION DEFERRABLE INITIALLY DEFERRED,
    FOREIGN KEY (user_id, asset_id) REFERENCES media_assets (user_id, id) ON DELETE NO ACTION DEFERRABLE INITIALLY DEFERRED
);
CREATE INDEX ix_source_references_0 ON source_references (user_id, asset_id);
CREATE INDEX ix_source_references_1 ON source_references (retain_until);

-- 食品证据版本（授权与证据）
CREATE TABLE food_observations (
    user_id TEXT NOT NULL,
    id TEXT NOT NULL,
    previous_id TEXT,
    food_name TEXT NOT NULL,
    specification TEXT,
    recipe_coverage TEXT NOT NULL,
    checked_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ NOT NULL,
    retain_until TIMESTAMPTZ NOT NULL,
    renewed_at TIMESTAMPTZ,
    basis_state TEXT NOT NULL,
    basis_micros BIGINT,
    basis_unit TEXT,
    PRIMARY KEY (user_id, id),
    CHECK (recipe_coverage IN ('完整已核对', '仅部分已知', '未知')),
    CHECK (basis_state IN ('已知', '未知')),
    CHECK (((basis_state = '已知' AND basis_micros IS NOT NULL AND basis_unit IS NOT NULL) OR (basis_state = '未知' AND basis_micros IS NULL))),
    CHECK (basis_micros IS NULL OR (basis_micros >= 0 AND basis_micros <= 9000000000000000)),
    CHECK (retain_until >= created_at),
    CHECK (((renewed_at IS NULL AND retain_until <= created_at + INTERVAL '180 days') OR (renewed_at IS NOT NULL AND renewed_at >= created_at AND retain_until <= renewed_at + INTERVAL '180 days'))),
    CHECK (basis_state = '未知' OR basis_micros > 0),
    FOREIGN KEY (user_id) REFERENCES user_control (user_id) ON DELETE NO ACTION DEFERRABLE INITIALLY DEFERRED,
    FOREIGN KEY (user_id, previous_id) REFERENCES food_observations (user_id, id) ON DELETE NO ACTION DEFERRABLE INITIALLY DEFERRED
);
CREATE INDEX ix_food_observations_0 ON food_observations (user_id, previous_id);
CREATE INDEX ix_food_observations_1 ON food_observations (user_id, food_name);
CREATE INDEX ix_food_observations_2 ON food_observations (retain_until);

-- 食品逐字段事实（授权与证据）
CREATE TABLE food_fields (
    user_id TEXT NOT NULL,
    observation_id TEXT NOT NULL,
    field_key TEXT NOT NULL,
    state TEXT NOT NULL,
    value_kind TEXT NOT NULL,
    number_micros BIGINT,
    text_value TEXT,
    unit TEXT,
    raw_value TEXT,
    checked_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ NOT NULL,
    PRIMARY KEY (user_id, observation_id, field_key),
    CHECK (state IN ('已核对', '待核对', '未知', '冲突')),
    CHECK (value_kind IN ('数值', '文字')),
    CHECK (((state IN ('未知','冲突') AND number_micros IS NULL AND text_value IS NULL) OR (state IN ('已核对','待核对') AND ((value_kind = '数值' AND number_micros IS NOT NULL AND text_value IS NULL AND unit IS NOT NULL) OR (value_kind = '文字' AND text_value IS NOT NULL AND number_micros IS NULL))))),
    CHECK (number_micros IS NULL OR (number_micros >= 0 AND number_micros <= 9000000000000000)),
    FOREIGN KEY (user_id) REFERENCES user_control (user_id) ON DELETE NO ACTION DEFERRABLE INITIALLY DEFERRED,
    FOREIGN KEY (user_id, observation_id) REFERENCES food_observations (user_id, id) ON DELETE NO ACTION DEFERRABLE INITIALLY DEFERRED
);

-- 字段来源关联（授权与证据）
CREATE TABLE field_sources (
    user_id TEXT NOT NULL,
    observation_id TEXT NOT NULL,
    field_key TEXT NOT NULL,
    source_id TEXT NOT NULL,
    source_role TEXT NOT NULL,
    created_at TIMESTAMPTZ NOT NULL,
    PRIMARY KEY (user_id, observation_id, field_key, source_id),
    CHECK (source_role IN ('原始材料', '用户核对', '冲突材料')),
    FOREIGN KEY (user_id) REFERENCES user_control (user_id) ON DELETE NO ACTION DEFERRABLE INITIALLY DEFERRED,
    FOREIGN KEY (user_id, observation_id, field_key) REFERENCES food_fields (user_id, observation_id, field_key) ON DELETE NO ACTION DEFERRABLE INITIALLY DEFERRED,
    FOREIGN KEY (user_id, source_id) REFERENCES source_references (user_id, id) ON DELETE NO ACTION DEFERRABLE INITIALLY DEFERRED
);
CREATE INDEX ix_field_sources_0 ON field_sources (user_id, source_id);

-- 约束评估（授权与证据）
CREATE TABLE constraint_assessments (
    user_id TEXT NOT NULL,
    id TEXT NOT NULL,
    context_id TEXT NOT NULL,
    observation_id TEXT,
    rule_version TEXT NOT NULL,
    outcome TEXT NOT NULL,
    reasons JSONB NOT NULL,
    evaluated_at TIMESTAMPTZ NOT NULL,
    created_at TIMESTAMPTZ NOT NULL,
    retain_until TIMESTAMPTZ NOT NULL,
    renewed_at TIMESTAMPTZ,
    PRIMARY KEY (user_id, id),
    CHECK (outcome IN ('通过', '拦截', '待核对')),
    CHECK (retain_until >= created_at),
    CHECK (((renewed_at IS NULL AND retain_until <= created_at + INTERVAL '180 days') OR (renewed_at IS NOT NULL AND renewed_at >= created_at AND retain_until <= renewed_at + INTERVAL '180 days'))),
    FOREIGN KEY (user_id) REFERENCES user_control (user_id) ON DELETE NO ACTION DEFERRABLE INITIALLY DEFERRED,
    FOREIGN KEY (user_id, context_id) REFERENCES context_snapshots (user_id, id) ON DELETE NO ACTION DEFERRABLE INITIALLY DEFERRED,
    FOREIGN KEY (user_id, observation_id) REFERENCES food_observations (user_id, id) ON DELETE NO ACTION DEFERRABLE INITIALLY DEFERRED
);
CREATE INDEX ix_constraint_assessments_0 ON constraint_assessments (user_id, context_id);
CREATE INDEX ix_constraint_assessments_1 ON constraint_assessments (user_id, observation_id);
CREATE INDEX ix_constraint_assessments_2 ON constraint_assessments (retain_until);

-- 标准食材（计划与准备）
CREATE TABLE ingredients (
    user_id TEXT NOT NULL,
    id TEXT NOT NULL,
    canonical_name TEXT NOT NULL,
    catalog_code TEXT,
    created_at TIMESTAMPTZ NOT NULL,
    retain_until TIMESTAMPTZ NOT NULL,
    renewed_at TIMESTAMPTZ,
    PRIMARY KEY (user_id, id),
    CHECK (retain_until >= created_at),
    CHECK (((renewed_at IS NULL AND retain_until <= created_at + INTERVAL '180 days') OR (renewed_at IS NOT NULL AND renewed_at >= created_at AND retain_until <= renewed_at + INTERVAL '180 days'))),
    FOREIGN KEY (user_id) REFERENCES user_control (user_id) ON DELETE NO ACTION DEFERRABLE INITIALLY DEFERRED
);
CREATE INDEX ix_ingredients_0 ON ingredients (retain_until);

-- 计划身份（计划与准备）
CREATE TABLE plan_heads (
    user_id TEXT NOT NULL,
    id TEXT NOT NULL,
    current_revision BIGINT NOT NULL,
    row_version BIGINT NOT NULL,
    state TEXT NOT NULL,
    created_at TIMESTAMPTZ NOT NULL,
    retain_until TIMESTAMPTZ NOT NULL,
    renewed_at TIMESTAMPTZ,
    PRIMARY KEY (user_id, id),
    CHECK (state IN ('有效', '已删除')),
    CHECK (current_revision >= 1),
    CHECK (row_version >= 1),
    CHECK (retain_until >= created_at),
    CHECK (((renewed_at IS NULL AND retain_until <= created_at + INTERVAL '180 days') OR (renewed_at IS NOT NULL AND renewed_at >= created_at AND retain_until <= renewed_at + INTERVAL '180 days'))),
    FOREIGN KEY (user_id) REFERENCES user_control (user_id) ON DELETE NO ACTION DEFERRABLE INITIALLY DEFERRED
);
CREATE INDEX ix_plan_heads_0 ON plan_heads (user_id, id, current_revision);
CREATE INDEX ix_plan_heads_1 ON plan_heads (retain_until);

-- 计划确认版本（计划与准备）
CREATE TABLE plan_revisions (
    user_id TEXT NOT NULL,
    id TEXT NOT NULL,
    revision BIGINT NOT NULL,
    mode TEXT NOT NULL,
    start_date DATE NOT NULL,
    end_date DATE NOT NULL,
    day_count BIGINT NOT NULL,
    context_id TEXT NOT NULL,
    confirmed_at TIMESTAMPTZ NOT NULL,
    created_at TIMESTAMPTZ NOT NULL,
    PRIMARY KEY (user_id, id, revision),
    CHECK (end_date >= start_date),
    CHECK (day_count IN (1, 7)),
    CHECK (mode IN ('完整', '指定')),
    CHECK (revision >= 1),
    CHECK (day_count >= 1),
    CHECK (end_date = start_date + CAST(day_count - 1 AS INTEGER)),
    FOREIGN KEY (user_id) REFERENCES user_control (user_id) ON DELETE NO ACTION DEFERRABLE INITIALLY DEFERRED,
    FOREIGN KEY (user_id, id) REFERENCES plan_heads (user_id, id) ON DELETE NO ACTION DEFERRABLE INITIALLY DEFERRED,
    FOREIGN KEY (user_id, context_id) REFERENCES context_snapshots (user_id, id) ON DELETE NO ACTION DEFERRABLE INITIALLY DEFERRED
);
CREATE INDEX ix_plan_revisions_0 ON plan_revisions (user_id, context_id);

-- 计划餐次（计划与准备）
CREATE TABLE planned_meals (
    user_id TEXT NOT NULL,
    id TEXT NOT NULL,
    plan_id TEXT NOT NULL,
    plan_revision BIGINT NOT NULL,
    meal_date DATE NOT NULL,
    meal_slot TEXT NOT NULL,
    people_count BIGINT NOT NULL,
    created_at TIMESTAMPTZ NOT NULL,
    PRIMARY KEY (user_id, id),
    UNIQUE (user_id, plan_id, plan_revision, meal_date, meal_slot),
    UNIQUE (user_id, id, meal_date, meal_slot),
    CHECK (meal_slot IN ('早餐', '午餐', '晚餐')),
    CHECK (plan_revision >= 1),
    CHECK (people_count >= 1),
    FOREIGN KEY (user_id) REFERENCES user_control (user_id) ON DELETE NO ACTION DEFERRABLE INITIALLY DEFERRED,
    FOREIGN KEY (user_id, plan_id, plan_revision) REFERENCES plan_revisions (user_id, id, revision) ON DELETE NO ACTION DEFERRABLE INITIALLY DEFERRED
);

-- 计划食物（计划与准备）
CREATE TABLE planned_foods (
    user_id TEXT NOT NULL,
    id TEXT NOT NULL,
    planned_meal_id TEXT NOT NULL,
    food_name TEXT NOT NULL,
    observation_id TEXT,
    assessment_id TEXT,
    quantity_basis TEXT NOT NULL,
    created_at TIMESTAMPTZ NOT NULL,
    quantity_state TEXT NOT NULL,
    quantity_micros BIGINT,
    quantity_unit TEXT,
    PRIMARY KEY (user_id, id),
    CHECK (quantity_basis IN ('每人', '本餐总量')),
    CHECK (quantity_state IN ('已知', '未知')),
    CHECK (((quantity_state = '已知' AND quantity_micros IS NOT NULL AND quantity_unit IS NOT NULL) OR (quantity_state = '未知' AND quantity_micros IS NULL))),
    CHECK (quantity_micros IS NULL OR (quantity_micros >= 0 AND quantity_micros <= 9000000000000000)),
    FOREIGN KEY (user_id) REFERENCES user_control (user_id) ON DELETE NO ACTION DEFERRABLE INITIALLY DEFERRED,
    FOREIGN KEY (user_id, planned_meal_id) REFERENCES planned_meals (user_id, id) ON DELETE NO ACTION DEFERRABLE INITIALLY DEFERRED,
    FOREIGN KEY (user_id, observation_id) REFERENCES food_observations (user_id, id) ON DELETE NO ACTION DEFERRABLE INITIALLY DEFERRED,
    FOREIGN KEY (user_id, assessment_id) REFERENCES constraint_assessments (user_id, id) ON DELETE NO ACTION DEFERRABLE INITIALLY DEFERRED
);
CREATE INDEX ix_planned_foods_0 ON planned_foods (user_id, planned_meal_id);
CREATE INDEX ix_planned_foods_1 ON planned_foods (user_id, observation_id);
CREATE INDEX ix_planned_foods_2 ON planned_foods (user_id, assessment_id);

-- 食材需求（计划与准备）
CREATE TABLE ingredient_requirements (
    user_id TEXT NOT NULL,
    id TEXT NOT NULL,
    planned_food_id TEXT NOT NULL,
    ingredient_id TEXT NOT NULL,
    quantity_basis TEXT NOT NULL,
    source_id TEXT,
    created_at TIMESTAMPTZ NOT NULL,
    quantity_state TEXT NOT NULL,
    quantity_micros BIGINT,
    quantity_unit TEXT,
    PRIMARY KEY (user_id, id),
    CHECK (quantity_basis IN ('每人', '本餐总量')),
    CHECK (quantity_state IN ('已知', '未知')),
    CHECK (((quantity_state = '已知' AND quantity_micros IS NOT NULL AND quantity_unit IS NOT NULL) OR (quantity_state = '未知' AND quantity_micros IS NULL))),
    CHECK (quantity_micros IS NULL OR (quantity_micros >= 0 AND quantity_micros <= 9000000000000000)),
    FOREIGN KEY (user_id) REFERENCES user_control (user_id) ON DELETE NO ACTION DEFERRABLE INITIALLY DEFERRED,
    FOREIGN KEY (user_id, planned_food_id) REFERENCES planned_foods (user_id, id) ON DELETE NO ACTION DEFERRABLE INITIALLY DEFERRED,
    FOREIGN KEY (user_id, ingredient_id) REFERENCES ingredients (user_id, id) ON DELETE NO ACTION DEFERRABLE INITIALLY DEFERRED,
    FOREIGN KEY (user_id, source_id) REFERENCES source_references (user_id, id) ON DELETE NO ACTION DEFERRABLE INITIALLY DEFERRED
);
CREATE INDEX ix_ingredient_requirements_0 ON ingredient_requirements (user_id, planned_food_id);
CREATE INDEX ix_ingredient_requirements_1 ON ingredient_requirements (user_id, ingredient_id);
CREATE INDEX ix_ingredient_requirements_2 ON ingredient_requirements (user_id, source_id);

-- 当前槽位归属（计划与准备）
CREATE TABLE slot_assignments (
    user_id TEXT NOT NULL,
    meal_date DATE NOT NULL,
    meal_slot TEXT NOT NULL,
    planned_meal_id TEXT NOT NULL,
    row_version BIGINT NOT NULL,
    created_at TIMESTAMPTZ NOT NULL,
    PRIMARY KEY (user_id, meal_date, meal_slot),
    CHECK (meal_slot IN ('早餐', '午餐', '晚餐')),
    CHECK (row_version >= 1),
    FOREIGN KEY (user_id) REFERENCES user_control (user_id) ON DELETE NO ACTION DEFERRABLE INITIALLY DEFERRED,
    FOREIGN KEY (user_id, planned_meal_id, meal_date, meal_slot) REFERENCES planned_meals (user_id, id, meal_date, meal_slot) ON DELETE NO ACTION DEFERRABLE INITIALLY DEFERRED
);
CREATE INDEX ix_slot_assignments_0 ON slot_assignments (user_id, planned_meal_id, meal_date, meal_slot);

-- 库存身份（计划与准备）
CREATE TABLE inventory_heads (
    user_id TEXT NOT NULL,
    id TEXT NOT NULL,
    ingredient_id TEXT NOT NULL,
    unit TEXT NOT NULL,
    current_revision BIGINT NOT NULL,
    row_version BIGINT NOT NULL,
    state TEXT NOT NULL,
    created_at TIMESTAMPTZ NOT NULL,
    retain_until TIMESTAMPTZ NOT NULL,
    renewed_at TIMESTAMPTZ,
    PRIMARY KEY (user_id, id),
    UNIQUE (user_id, ingredient_id, unit),
    CHECK (state IN ('有效', '已删除')),
    CHECK (current_revision >= 1),
    CHECK (row_version >= 1),
    CHECK (retain_until >= created_at),
    CHECK (((renewed_at IS NULL AND retain_until <= created_at + INTERVAL '180 days') OR (renewed_at IS NOT NULL AND renewed_at >= created_at AND retain_until <= renewed_at + INTERVAL '180 days'))),
    FOREIGN KEY (user_id) REFERENCES user_control (user_id) ON DELETE NO ACTION DEFERRABLE INITIALLY DEFERRED,
    FOREIGN KEY (user_id, ingredient_id) REFERENCES ingredients (user_id, id) ON DELETE NO ACTION DEFERRABLE INITIALLY DEFERRED
);
CREATE INDEX ix_inventory_heads_0 ON inventory_heads (user_id, id, current_revision);
CREATE INDEX ix_inventory_heads_1 ON inventory_heads (retain_until);

-- 库存核对版本（计划与准备）
CREATE TABLE inventory_revisions (
    user_id TEXT NOT NULL,
    id TEXT NOT NULL,
    revision BIGINT NOT NULL,
    quantity_state TEXT NOT NULL,
    quantity_micros BIGINT,
    observed_at TIMESTAMPTZ NOT NULL,
    reason TEXT NOT NULL,
    confirmed_at TIMESTAMPTZ NOT NULL,
    created_at TIMESTAMPTZ NOT NULL,
    PRIMARY KEY (user_id, id, revision),
    CHECK (quantity_state IN ('已知', '未知')),
    CHECK (((quantity_state = '已知' AND quantity_micros IS NOT NULL) OR (quantity_state = '未知' AND quantity_micros IS NULL))),
    CHECK (revision >= 1),
    CHECK (quantity_micros IS NULL OR (quantity_micros >= 0 AND quantity_micros <= 9000000000000000)),
    FOREIGN KEY (user_id) REFERENCES user_control (user_id) ON DELETE NO ACTION DEFERRABLE INITIALLY DEFERRED,
    FOREIGN KEY (user_id, id) REFERENCES inventory_heads (user_id, id) ON DELETE NO ACTION DEFERRABLE INITIALLY DEFERRED
);

-- 准备采购清单（计划与准备）
CREATE TABLE preparation_lists (
    user_id TEXT NOT NULL,
    id TEXT NOT NULL,
    plan_id TEXT NOT NULL,
    plan_revision BIGINT NOT NULL,
    row_version BIGINT NOT NULL,
    state TEXT NOT NULL,
    inventory_data_revision BIGINT NOT NULL,
    confirmed_at TIMESTAMPTZ NOT NULL,
    created_at TIMESTAMPTZ NOT NULL,
    retain_until TIMESTAMPTZ NOT NULL,
    renewed_at TIMESTAMPTZ,
    PRIMARY KEY (user_id, id),
    CHECK (state IN ('有效', '已失效', '已取消')),
    CHECK (plan_revision >= 1),
    CHECK (row_version >= 1),
    CHECK (inventory_data_revision >= 1),
    CHECK (retain_until >= created_at),
    CHECK (((renewed_at IS NULL AND retain_until <= created_at + INTERVAL '180 days') OR (renewed_at IS NOT NULL AND renewed_at >= created_at AND retain_until <= renewed_at + INTERVAL '180 days'))),
    FOREIGN KEY (user_id) REFERENCES user_control (user_id) ON DELETE NO ACTION DEFERRABLE INITIALLY DEFERRED,
    FOREIGN KEY (user_id, plan_id, plan_revision) REFERENCES plan_revisions (user_id, id, revision) ON DELETE NO ACTION DEFERRABLE INITIALLY DEFERRED
);
CREATE UNIQUE INDEX ix_preparation_lists_0 ON preparation_lists (user_id, plan_id, plan_revision) WHERE state = '有效';
CREATE INDEX ix_preparation_lists_1 ON preparation_lists (user_id, plan_id, plan_revision);
CREATE INDEX ix_preparation_lists_2 ON preparation_lists (retain_until);

-- 清单条目（计划与准备）
CREATE TABLE preparation_lines (
    user_id TEXT NOT NULL,
    id TEXT NOT NULL,
    list_id TEXT NOT NULL,
    ingredient_id TEXT NOT NULL,
    unit TEXT NOT NULL,
    has_unknown_requirement SMALLINT NOT NULL,
    known_need_micros BIGINT NOT NULL,
    stock_state TEXT NOT NULL,
    stock_micros BIGINT,
    shortage_state TEXT NOT NULL,
    shortage_micros BIGINT,
    purchased_state TEXT NOT NULL,
    prepared_state TEXT NOT NULL,
    inventory_id TEXT,
    inventory_revision BIGINT,
    manual_reason TEXT,
    created_at TIMESTAMPTZ NOT NULL,
    PRIMARY KEY (user_id, id),
    UNIQUE (user_id, list_id, ingredient_id, unit),
    CHECK (((inventory_id IS NULL AND inventory_revision IS NULL) OR (inventory_id IS NOT NULL AND inventory_revision IS NOT NULL))),
    CHECK (((stock_state = '已知' AND stock_micros IS NOT NULL) OR (stock_state = '未知' AND stock_micros IS NULL))),
    CHECK (((shortage_state = '已知' AND shortage_micros IS NOT NULL AND stock_state = '已知' AND has_unknown_requirement = 0) OR (shortage_state = '未知' AND shortage_micros IS NULL))),
    CHECK (stock_state IN ('已知', '未知')),
    CHECK (shortage_state IN ('已知', '未知')),
    CHECK (purchased_state IN ('未报告', '已确认', '不适用')),
    CHECK (prepared_state IN ('未报告', '已确认', '不适用')),
    CHECK (has_unknown_requirement IN (0, 1)),
    CHECK (known_need_micros >= 0 AND known_need_micros <= 9000000000000000),
    CHECK (stock_micros IS NULL OR (stock_micros >= 0 AND stock_micros <= 9000000000000000)),
    CHECK (shortage_micros IS NULL OR (shortage_micros >= 0 AND shortage_micros <= 9000000000000000)),
    CHECK (inventory_revision IS NULL OR (inventory_revision >= 1)),
    FOREIGN KEY (user_id) REFERENCES user_control (user_id) ON DELETE NO ACTION DEFERRABLE INITIALLY DEFERRED,
    FOREIGN KEY (user_id, list_id) REFERENCES preparation_lists (user_id, id) ON DELETE NO ACTION DEFERRABLE INITIALLY DEFERRED,
    FOREIGN KEY (user_id, ingredient_id) REFERENCES ingredients (user_id, id) ON DELETE NO ACTION DEFERRABLE INITIALLY DEFERRED,
    FOREIGN KEY (user_id, inventory_id, inventory_revision) REFERENCES inventory_revisions (user_id, id, revision) ON DELETE NO ACTION DEFERRABLE INITIALLY DEFERRED
);
CREATE INDEX ix_preparation_lines_0 ON preparation_lines (user_id, ingredient_id);
CREATE INDEX ix_preparation_lines_1 ON preparation_lines (user_id, inventory_id, inventory_revision);

-- 清单需求来源（计划与准备）
CREATE TABLE preparation_sources (
    user_id TEXT NOT NULL,
    line_id TEXT NOT NULL,
    requirement_id TEXT NOT NULL,
    created_at TIMESTAMPTZ NOT NULL,
    PRIMARY KEY (user_id, line_id, requirement_id),
    FOREIGN KEY (user_id) REFERENCES user_control (user_id) ON DELETE NO ACTION DEFERRABLE INITIALLY DEFERRED,
    FOREIGN KEY (user_id, line_id) REFERENCES preparation_lines (user_id, id) ON DELETE NO ACTION DEFERRABLE INITIALLY DEFERRED,
    FOREIGN KEY (user_id, requirement_id) REFERENCES ingredient_requirements (user_id, id) ON DELETE NO ACTION DEFERRABLE INITIALLY DEFERRED
);
CREATE INDEX ix_preparation_sources_0 ON preparation_sources (user_id, requirement_id);

-- 个人用餐身份（实际与回顾）
CREATE TABLE meal_heads (
    user_id TEXT NOT NULL,
    id TEXT NOT NULL,
    current_revision BIGINT NOT NULL,
    row_version BIGINT NOT NULL,
    state TEXT NOT NULL,
    created_at TIMESTAMPTZ NOT NULL,
    retain_until TIMESTAMPTZ NOT NULL,
    renewed_at TIMESTAMPTZ,
    PRIMARY KEY (user_id, id),
    CHECK (state IN ('有效', '已删除')),
    CHECK (current_revision >= 1),
    CHECK (row_version >= 1),
    CHECK (retain_until >= created_at),
    CHECK (((renewed_at IS NULL AND retain_until <= created_at + INTERVAL '180 days') OR (renewed_at IS NOT NULL AND renewed_at >= created_at AND retain_until <= renewed_at + INTERVAL '180 days'))),
    FOREIGN KEY (user_id) REFERENCES user_control (user_id) ON DELETE NO ACTION DEFERRABLE INITIALLY DEFERRED
);
CREATE INDEX ix_meal_heads_0 ON meal_heads (user_id, id, current_revision);
CREATE INDEX ix_meal_heads_1 ON meal_heads (retain_until);

-- 个人用餐版本（实际与回顾）
CREATE TABLE meal_revisions (
    user_id TEXT NOT NULL,
    id TEXT NOT NULL,
    revision BIGINT NOT NULL,
    meal_date DATE NOT NULL,
    meal_slot TEXT NOT NULL,
    actual_at TIMESTAMPTZ,
    note TEXT,
    confirmed_at TIMESTAMPTZ NOT NULL,
    created_at TIMESTAMPTZ NOT NULL,
    PRIMARY KEY (user_id, id, revision),
    CHECK (meal_slot IN ('早餐', '午餐', '晚餐', '加餐')),
    CHECK (revision >= 1),
    FOREIGN KEY (user_id) REFERENCES user_control (user_id) ON DELETE NO ACTION DEFERRABLE INITIALLY DEFERRED,
    FOREIGN KEY (user_id, id) REFERENCES meal_heads (user_id, id) ON DELETE NO ACTION DEFERRABLE INITIALLY DEFERRED
);
CREATE INDEX ix_meal_revisions_0 ON meal_revisions (user_id, meal_date, meal_slot);

-- 个人实际食物（实际与回顾）
CREATE TABLE reported_foods (
    user_id TEXT NOT NULL,
    record_id TEXT NOT NULL,
    record_revision BIGINT NOT NULL,
    item_id TEXT NOT NULL,
    food_name TEXT NOT NULL,
    observation_id TEXT,
    planned_food_id TEXT,
    entry_source TEXT NOT NULL,
    created_at TIMESTAMPTZ NOT NULL,
    quantity_state TEXT NOT NULL,
    quantity_micros BIGINT,
    quantity_unit TEXT,
    PRIMARY KEY (user_id, record_id, record_revision, item_id),
    CHECK (entry_source IN ('手动自述', '计划预填', '图文核对')),
    CHECK (quantity_state IN ('已知', '未知')),
    CHECK (((quantity_state = '已知' AND quantity_micros IS NOT NULL AND quantity_unit IS NOT NULL) OR (quantity_state = '未知' AND quantity_micros IS NULL))),
    CHECK (record_revision >= 1),
    CHECK (quantity_micros IS NULL OR (quantity_micros >= 0 AND quantity_micros <= 9000000000000000)),
    FOREIGN KEY (user_id) REFERENCES user_control (user_id) ON DELETE NO ACTION DEFERRABLE INITIALLY DEFERRED,
    FOREIGN KEY (user_id, record_id, record_revision) REFERENCES meal_revisions (user_id, id, revision) ON DELETE NO ACTION DEFERRABLE INITIALLY DEFERRED,
    FOREIGN KEY (user_id, observation_id) REFERENCES food_observations (user_id, id) ON DELETE NO ACTION DEFERRABLE INITIALLY DEFERRED,
    FOREIGN KEY (user_id, planned_food_id) REFERENCES planned_foods (user_id, id) ON DELETE NO ACTION DEFERRABLE INITIALLY DEFERRED
);
CREATE INDEX ix_reported_foods_0 ON reported_foods (user_id, observation_id);
CREATE INDEX ix_reported_foods_1 ON reported_foods (user_id, planned_food_id);

-- 微行动提案（行动与学习）
CREATE TABLE micro_actions (
    user_id TEXT NOT NULL,
    id TEXT NOT NULL,
    context_id TEXT NOT NULL,
    dimension TEXT NOT NULL,
    cue TEXT NOT NULL,
    behavior TEXT NOT NULL,
    effort TEXT NOT NULL,
    rationale TEXT NOT NULL,
    replacement_of TEXT,
    planned_meal_id TEXT,
    current_window_revision BIGINT,
    current_execution_revision BIGINT,
    row_version BIGINT NOT NULL,
    state TEXT NOT NULL,
    created_at TIMESTAMPTZ NOT NULL,
    retain_until TIMESTAMPTZ NOT NULL,
    renewed_at TIMESTAMPTZ,
    record_id TEXT,
    record_revision BIGINT,
    PRIMARY KEY (user_id, id),
    CHECK (((record_id IS NULL AND record_revision IS NULL) OR (record_id IS NOT NULL AND record_revision IS NOT NULL))),
    CHECK (dimension IN ('平替', '顺手加法', '进食顺序', '时序节律')),
    CHECK (state IN ('有效', '已删除')),
    CHECK (current_window_revision IS NULL OR (current_window_revision >= 1)),
    CHECK (current_execution_revision IS NULL OR (current_execution_revision >= 1)),
    CHECK (row_version >= 1),
    CHECK (record_revision IS NULL OR (record_revision >= 1)),
    CHECK (retain_until >= created_at),
    CHECK (((renewed_at IS NULL AND retain_until <= created_at + INTERVAL '180 days') OR (renewed_at IS NOT NULL AND renewed_at >= created_at AND retain_until <= renewed_at + INTERVAL '180 days'))),
    FOREIGN KEY (user_id) REFERENCES user_control (user_id) ON DELETE NO ACTION DEFERRABLE INITIALLY DEFERRED,
    FOREIGN KEY (user_id, record_id, record_revision) REFERENCES meal_revisions (user_id, id, revision) ON DELETE NO ACTION DEFERRABLE INITIALLY DEFERRED,
    FOREIGN KEY (user_id, context_id) REFERENCES context_snapshots (user_id, id) ON DELETE NO ACTION DEFERRABLE INITIALLY DEFERRED,
    FOREIGN KEY (user_id, replacement_of) REFERENCES micro_actions (user_id, id) ON DELETE NO ACTION DEFERRABLE INITIALLY DEFERRED,
    FOREIGN KEY (user_id, planned_meal_id) REFERENCES planned_meals (user_id, id) ON DELETE NO ACTION DEFERRABLE INITIALLY DEFERRED
);
CREATE INDEX ix_micro_actions_0 ON micro_actions (user_id, record_id, record_revision);
CREATE INDEX ix_micro_actions_1 ON micro_actions (user_id, context_id);
CREATE INDEX ix_micro_actions_2 ON micro_actions (user_id, replacement_of);
CREATE INDEX ix_micro_actions_3 ON micro_actions (user_id, planned_meal_id);
CREATE INDEX ix_micro_actions_4 ON micro_actions (user_id, id, current_window_revision);
CREATE INDEX ix_micro_actions_5 ON micro_actions (user_id, id, current_execution_revision);
CREATE INDEX ix_micro_actions_6 ON micro_actions (retain_until);

-- 行动最终决策（行动与学习）
CREATE TABLE action_decisions (
    user_id TEXT NOT NULL,
    action_id TEXT NOT NULL,
    decision TEXT NOT NULL,
    confirmed_at TIMESTAMPTZ NOT NULL,
    created_at TIMESTAMPTZ NOT NULL,
    PRIMARY KEY (user_id, action_id),
    CHECK (decision IN ('采纳', '跳过', '被替代')),
    FOREIGN KEY (user_id) REFERENCES user_control (user_id) ON DELETE NO ACTION DEFERRABLE INITIALLY DEFERRED,
    FOREIGN KEY (user_id, action_id) REFERENCES micro_actions (user_id, id) ON DELETE NO ACTION DEFERRABLE INITIALLY DEFERRED
);

-- 行动窗口修订（行动与学习）
CREATE TABLE action_windows (
    user_id TEXT NOT NULL,
    action_id TEXT NOT NULL,
    revision BIGINT NOT NULL,
    starts_at TIMESTAMPTZ NOT NULL,
    ends_at TIMESTAMPTZ NOT NULL,
    timezone TEXT NOT NULL DEFAULT 'Asia/Shanghai',
    reason TEXT NOT NULL,
    confirmed_at TIMESTAMPTZ NOT NULL,
    created_at TIMESTAMPTZ NOT NULL,
    PRIMARY KEY (user_id, action_id, revision),
    CHECK (ends_at >= starts_at),
    CHECK (timezone = 'Asia/Shanghai'),
    CHECK (revision >= 1),
    FOREIGN KEY (user_id) REFERENCES user_control (user_id) ON DELETE NO ACTION DEFERRABLE INITIALLY DEFERRED,
    FOREIGN KEY (user_id, action_id) REFERENCES action_decisions (user_id, action_id) ON DELETE NO ACTION DEFERRABLE INITIALLY DEFERRED
);
CREATE INDEX ix_action_windows_0 ON action_windows (user_id, ends_at);

-- 执行自述修订（行动与学习）
CREATE TABLE execution_revisions (
    user_id TEXT NOT NULL,
    action_id TEXT NOT NULL,
    revision BIGINT NOT NULL,
    execution_state TEXT NOT NULL,
    execution_date DATE,
    reported_at TIMESTAMPTZ NOT NULL,
    note TEXT,
    confirmed_at TIMESTAMPTZ NOT NULL,
    created_at TIMESTAMPTZ NOT NULL,
    PRIMARY KEY (user_id, action_id, revision),
    CHECK (execution_state IN ('完成', '部分', '未完成', '撤回为不确定')),
    CHECK (((execution_state = '撤回为不确定' AND execution_date IS NULL) OR (execution_state <> '撤回为不确定' AND execution_date IS NOT NULL))),
    CHECK (revision >= 1),
    FOREIGN KEY (user_id) REFERENCES user_control (user_id) ON DELETE NO ACTION DEFERRABLE INITIALLY DEFERRED,
    FOREIGN KEY (user_id, action_id) REFERENCES action_decisions (user_id, action_id) ON DELETE NO ACTION DEFERRABLE INITIALLY DEFERRED
);
CREATE INDEX ix_execution_revisions_0 ON execution_revisions (user_id, execution_date, execution_state);

-- 提醒与回应历史（行动与学习）
CREATE TABLE reminder_events (
    user_id TEXT NOT NULL,
    id TEXT NOT NULL,
    action_id TEXT NOT NULL,
    scheduled_at TIMESTAMPTZ NOT NULL,
    sent_at TIMESTAMPTZ,
    responded_at TIMESTAMPTZ,
    outcome TEXT NOT NULL,
    authorization_epoch BIGINT NOT NULL,
    created_at TIMESTAMPTZ NOT NULL,
    retain_until TIMESTAMPTZ NOT NULL,
    renewed_at TIMESTAMPTZ,
    PRIMARY KEY (user_id, id),
    CHECK (outcome IN ('待发送', '已发送', '已取消', '失败')),
    CHECK (authorization_epoch >= 1),
    CHECK (retain_until >= created_at),
    CHECK (((renewed_at IS NULL AND retain_until <= created_at + INTERVAL '180 days') OR (renewed_at IS NOT NULL AND renewed_at >= created_at AND retain_until <= renewed_at + INTERVAL '180 days'))),
    FOREIGN KEY (user_id) REFERENCES user_control (user_id) ON DELETE NO ACTION DEFERRABLE INITIALLY DEFERRED,
    FOREIGN KEY (user_id, action_id) REFERENCES action_decisions (user_id, action_id) ON DELETE NO ACTION DEFERRABLE INITIALLY DEFERRED
);
CREATE INDEX ix_reminder_events_0 ON reminder_events (user_id, action_id);
CREATE INDEX ix_reminder_events_1 ON reminder_events (user_id, scheduled_at);
CREATE INDEX ix_reminder_events_2 ON reminder_events (retain_until);

-- 交互与提醒状态（行动与学习）
CREATE TABLE interaction_settings (
    user_id TEXT NOT NULL,
    row_version BIGINT NOT NULL,
    unanswered_count BIGINT NOT NULL,
    backoff_until TIMESTAMPTZ,
    companion_enabled SMALLINT NOT NULL,
    collection_enabled SMALLINT NOT NULL,
    calibration_enabled SMALLINT NOT NULL,
    ranking_version TEXT NOT NULL,
    ranking_parameters JSONB NOT NULL,
    created_at TIMESTAMPTZ NOT NULL,
    retain_until TIMESTAMPTZ NOT NULL,
    renewed_at TIMESTAMPTZ,
    PRIMARY KEY (user_id),
    CHECK (row_version >= 1),
    CHECK (unanswered_count >= 0),
    CHECK (companion_enabled IN (0, 1)),
    CHECK (collection_enabled IN (0, 1)),
    CHECK (calibration_enabled IN (0, 1)),
    CHECK (retain_until >= created_at),
    CHECK (((renewed_at IS NULL AND retain_until <= created_at + INTERVAL '180 days') OR (renewed_at IS NOT NULL AND renewed_at >= created_at AND retain_until <= renewed_at + INTERVAL '180 days'))),
    FOREIGN KEY (user_id) REFERENCES user_control (user_id) ON DELETE NO ACTION DEFERRABLE INITIALLY DEFERRED
);
CREATE INDEX ix_interaction_settings_0 ON interaction_settings (retain_until);

-- 内环决策记录（行动与学习）
CREATE TABLE interaction_events (
    user_id TEXT NOT NULL,
    id TEXT NOT NULL,
    context_id TEXT NOT NULL,
    action_id TEXT,
    event_kind TEXT NOT NULL,
    rule_version TEXT NOT NULL,
    explanation JSONB NOT NULL,
    cooldown_until TIMESTAMPTZ,
    created_at TIMESTAMPTZ NOT NULL,
    retain_until TIMESTAMPTZ NOT NULL,
    renewed_at TIMESTAMPTZ,
    PRIMARY KEY (user_id, id),
    CHECK (event_kind IN ('采纳', '换一个', '暂不需要', '规则调整')),
    CHECK (retain_until >= created_at),
    CHECK (((renewed_at IS NULL AND retain_until <= created_at + INTERVAL '180 days') OR (renewed_at IS NOT NULL AND renewed_at >= created_at AND retain_until <= renewed_at + INTERVAL '180 days'))),
    FOREIGN KEY (user_id) REFERENCES user_control (user_id) ON DELETE NO ACTION DEFERRABLE INITIALLY DEFERRED,
    FOREIGN KEY (user_id, context_id) REFERENCES context_snapshots (user_id, id) ON DELETE NO ACTION DEFERRABLE INITIALLY DEFERRED,
    FOREIGN KEY (user_id, action_id) REFERENCES micro_actions (user_id, id) ON DELETE NO ACTION DEFERRABLE INITIALLY DEFERRED
);
CREATE INDEX ix_interaction_events_0 ON interaction_events (user_id, context_id);
CREATE INDEX ix_interaction_events_1 ON interaction_events (user_id, action_id);
CREATE INDEX ix_interaction_events_2 ON interaction_events (user_id, context_id, cooldown_until);
CREATE INDEX ix_interaction_events_3 ON interaction_events (retain_until);

-- 偏好与情境候选（行动与学习）
CREATE TABLE learning_candidates (
    user_id TEXT NOT NULL,
    id TEXT NOT NULL,
    candidate_kind TEXT NOT NULL,
    hypothesis JSONB NOT NULL,
    state TEXT NOT NULL,
    authorization_epoch BIGINT NOT NULL,
    range_start DATE NOT NULL,
    range_end DATE NOT NULL,
    confirmed_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ NOT NULL,
    retain_until TIMESTAMPTZ NOT NULL,
    renewed_at TIMESTAMPTZ,
    PRIMARY KEY (user_id, id),
    CHECK (candidate_kind IN ('稳定偏好', '情境线索')),
    CHECK (state IN ('待核对', '已确认', '已拒绝', '已到期')),
    CHECK (range_end >= range_start),
    CHECK (authorization_epoch >= 1),
    CHECK (retain_until >= created_at),
    CHECK (((renewed_at IS NULL AND retain_until <= created_at + INTERVAL '180 days') OR (renewed_at IS NOT NULL AND renewed_at >= created_at AND retain_until <= renewed_at + INTERVAL '180 days'))),
    FOREIGN KEY (user_id) REFERENCES user_control (user_id) ON DELETE NO ACTION DEFERRABLE INITIALLY DEFERRED
);
CREATE INDEX ix_learning_candidates_0 ON learning_candidates (retain_until);

-- 学习证据引用（行动与学习）
CREATE TABLE learning_evidence (
    user_id TEXT NOT NULL,
    id TEXT NOT NULL,
    candidate_id TEXT NOT NULL,
    action_id TEXT,
    execution_revision BIGINT,
    record_id TEXT,
    record_revision BIGINT,
    created_at TIMESTAMPTZ NOT NULL,
    PRIMARY KEY (user_id, id),
    CHECK (((action_id IS NOT NULL AND execution_revision IS NOT NULL AND record_id IS NULL AND record_revision IS NULL) OR (action_id IS NULL AND execution_revision IS NULL AND record_id IS NOT NULL AND record_revision IS NOT NULL))),
    CHECK (execution_revision IS NULL OR (execution_revision >= 1)),
    CHECK (record_revision IS NULL OR (record_revision >= 1)),
    FOREIGN KEY (user_id) REFERENCES user_control (user_id) ON DELETE NO ACTION DEFERRABLE INITIALLY DEFERRED,
    FOREIGN KEY (user_id, candidate_id) REFERENCES learning_candidates (user_id, id) ON DELETE NO ACTION DEFERRABLE INITIALLY DEFERRED,
    FOREIGN KEY (user_id, action_id, execution_revision) REFERENCES execution_revisions (user_id, action_id, revision) ON DELETE NO ACTION DEFERRABLE INITIALLY DEFERRED,
    FOREIGN KEY (user_id, record_id, record_revision) REFERENCES meal_revisions (user_id, id, revision) ON DELETE NO ACTION DEFERRABLE INITIALLY DEFERRED
);
CREATE INDEX ix_learning_evidence_0 ON learning_evidence (user_id, candidate_id);
CREATE INDEX ix_learning_evidence_1 ON learning_evidence (user_id, action_id, execution_revision);
CREATE INDEX ix_learning_evidence_2 ON learning_evidence (user_id, record_id, record_revision);

-- 稳定偏好修订（行动与学习）
CREATE TABLE preference_rule_revisions (
    user_id TEXT NOT NULL,
    id TEXT NOT NULL,
    revision BIGINT NOT NULL,
    candidate_id TEXT NOT NULL,
    rule_content JSONB NOT NULL,
    state TEXT NOT NULL,
    confirmed_at TIMESTAMPTZ NOT NULL,
    created_at TIMESTAMPTZ NOT NULL,
    retain_until TIMESTAMPTZ NOT NULL,
    renewed_at TIMESTAMPTZ,
    PRIMARY KEY (user_id, id, revision),
    CHECK (state IN ('有效', '已停用', '已删除')),
    CHECK (revision >= 1),
    CHECK (retain_until >= created_at),
    CHECK (((renewed_at IS NULL AND retain_until <= created_at + INTERVAL '180 days') OR (renewed_at IS NOT NULL AND renewed_at >= created_at AND retain_until <= renewed_at + INTERVAL '180 days'))),
    FOREIGN KEY (user_id) REFERENCES user_control (user_id) ON DELETE NO ACTION DEFERRABLE INITIALLY DEFERRED,
    FOREIGN KEY (user_id, candidate_id) REFERENCES learning_candidates (user_id, id) ON DELETE NO ACTION DEFERRABLE INITIALLY DEFERRED
);
CREATE INDEX ix_preference_rule_revisions_0 ON preference_rule_revisions (user_id, candidate_id);
CREATE INDEX ix_preference_rule_revisions_1 ON preference_rule_revisions (retain_until);

-- 校准回答修订（行动与学习）
CREATE TABLE calibration_revisions (
    user_id TEXT NOT NULL,
    question_key TEXT NOT NULL,
    question_version TEXT NOT NULL,
    revision BIGINT NOT NULL,
    answer JSONB,
    state TEXT NOT NULL,
    confirmed_at TIMESTAMPTZ NOT NULL,
    created_at TIMESTAMPTZ NOT NULL,
    retain_until TIMESTAMPTZ NOT NULL,
    renewed_at TIMESTAMPTZ,
    PRIMARY KEY (user_id, question_key, revision),
    CHECK (state IN ('已确认', '已删除')),
    CHECK (((state = '已确认' AND answer IS NOT NULL) OR (state = '已删除' AND answer IS NULL))),
    CHECK (revision >= 1),
    CHECK (retain_until >= created_at),
    CHECK (((renewed_at IS NULL AND retain_until <= created_at + INTERVAL '180 days') OR (renewed_at IS NOT NULL AND renewed_at >= created_at AND retain_until <= renewed_at + INTERVAL '180 days'))),
    FOREIGN KEY (user_id) REFERENCES user_control (user_id) ON DELETE NO ACTION DEFERRABLE INITIALLY DEFERRED
);
CREATE INDEX ix_calibration_revisions_0 ON calibration_revisions (retain_until);

-- 预期餐次版本（实际与回顾）
CREATE TABLE expected_schedules (
    user_id TEXT NOT NULL,
    week_start DATE NOT NULL,
    revision BIGINT NOT NULL,
    confirmed_at TIMESTAMPTZ NOT NULL,
    created_at TIMESTAMPTZ NOT NULL,
    retain_until TIMESTAMPTZ NOT NULL,
    renewed_at TIMESTAMPTZ,
    PRIMARY KEY (user_id, week_start, revision),
    CHECK (revision >= 1),
    CHECK (retain_until >= created_at),
    CHECK (((renewed_at IS NULL AND retain_until <= created_at + INTERVAL '180 days') OR (renewed_at IS NOT NULL AND renewed_at >= created_at AND retain_until <= renewed_at + INTERVAL '180 days'))),
    CHECK (EXTRACT(ISODOW FROM week_start) = 1),
    FOREIGN KEY (user_id) REFERENCES user_control (user_id) ON DELETE NO ACTION DEFERRABLE INITIALLY DEFERRED
);
CREATE INDEX ix_expected_schedules_0 ON expected_schedules (retain_until);

-- 预期餐次槽位（实际与回顾）
CREATE TABLE expected_slots (
    user_id TEXT NOT NULL,
    week_start DATE NOT NULL,
    schedule_revision BIGINT NOT NULL,
    meal_date DATE NOT NULL,
    meal_slot TEXT NOT NULL,
    created_at TIMESTAMPTZ NOT NULL,
    PRIMARY KEY (user_id, week_start, schedule_revision, meal_date, meal_slot),
    CHECK (meal_slot IN ('早餐', '午餐', '晚餐', '加餐')),
    CHECK (schedule_revision >= 1),
    CHECK (EXTRACT(ISODOW FROM week_start) = 1),
    CHECK (meal_date >= week_start AND meal_date <= week_start + 6),
    FOREIGN KEY (user_id) REFERENCES user_control (user_id) ON DELETE NO ACTION DEFERRABLE INITIALLY DEFERRED,
    FOREIGN KEY (user_id, week_start, schedule_revision) REFERENCES expected_schedules (user_id, week_start, revision) ON DELETE NO ACTION DEFERRABLE INITIALLY DEFERRED
);

-- 恢复周期确认（实际与回顾）
CREATE TABLE recovery_episodes (
    user_id TEXT NOT NULL,
    id TEXT NOT NULL,
    row_version BIGINT NOT NULL,
    deviation_at TIMESTAMPTZ,
    return_at TIMESTAMPTZ,
    reason TEXT NOT NULL,
    confirmed_at TIMESTAMPTZ NOT NULL,
    created_at TIMESTAMPTZ NOT NULL,
    retain_until TIMESTAMPTZ NOT NULL,
    renewed_at TIMESTAMPTZ,
    PRIMARY KEY (user_id, id),
    CHECK (return_at IS NULL OR (deviation_at IS NOT NULL AND return_at >= deviation_at)),
    CHECK (row_version >= 1),
    CHECK (retain_until >= created_at),
    CHECK (((renewed_at IS NULL AND retain_until <= created_at + INTERVAL '180 days') OR (renewed_at IS NOT NULL AND renewed_at >= created_at AND retain_until <= renewed_at + INTERVAL '180 days'))),
    FOREIGN KEY (user_id) REFERENCES user_control (user_id) ON DELETE NO ACTION DEFERRABLE INITIALLY DEFERRED
);
CREATE INDEX ix_recovery_episodes_0 ON recovery_episodes (retain_until);

-- 恢复排除时段（实际与回顾）
CREATE TABLE recovery_exclusions (
    user_id TEXT NOT NULL,
    id TEXT NOT NULL,
    episode_id TEXT NOT NULL,
    starts_at TIMESTAMPTZ NOT NULL,
    ends_at TIMESTAMPTZ NOT NULL,
    reason TEXT NOT NULL,
    confirmed_at TIMESTAMPTZ NOT NULL,
    created_at TIMESTAMPTZ NOT NULL,
    PRIMARY KEY (user_id, id),
    CHECK (ends_at >= starts_at),
    FOREIGN KEY (user_id) REFERENCES user_control (user_id) ON DELETE NO ACTION DEFERRABLE INITIALLY DEFERRED,
    FOREIGN KEY (user_id, episode_id) REFERENCES recovery_episodes (user_id, id) ON DELETE NO ACTION DEFERRABLE INITIALLY DEFERRED
);
CREATE INDEX ix_recovery_exclusions_0 ON recovery_exclusions (user_id, episode_id);

-- 连续周呈现修订（实际与回顾）
CREATE TABLE week_presentations (
    user_id TEXT NOT NULL,
    week_start DATE NOT NULL,
    revision BIGINT NOT NULL,
    override_kind TEXT NOT NULL,
    reason TEXT NOT NULL,
    confirmed_at TIMESTAMPTZ NOT NULL,
    created_at TIMESTAMPTZ NOT NULL,
    retain_until TIMESTAMPTZ NOT NULL,
    renewed_at TIMESTAMPTZ,
    PRIMARY KEY (user_id, week_start, revision),
    CHECK (override_kind IN ('冻结', '取消冻结')),
    CHECK (revision >= 1),
    CHECK (retain_until >= created_at),
    CHECK (((renewed_at IS NULL AND retain_until <= created_at + INTERVAL '180 days') OR (renewed_at IS NOT NULL AND renewed_at >= created_at AND retain_until <= renewed_at + INTERVAL '180 days'))),
    CHECK (EXTRACT(ISODOW FROM week_start) = 1),
    FOREIGN KEY (user_id) REFERENCES user_control (user_id) ON DELETE NO ACTION DEFERRABLE INITIALLY DEFERRED
);
CREATE INDEX ix_week_presentations_0 ON week_presentations (retain_until);

-- 持久提交回执（命令与数据控制）
CREATE TABLE command_receipts (
    user_id TEXT NOT NULL,
    operation_key TEXT NOT NULL,
    request_hash TEXT NOT NULL,
    commit_id TEXT NOT NULL,
    task_id TEXT,
    authorization_epoch BIGINT NOT NULL,
    data_revision BIGINT NOT NULL,
    result_refs JSONB NOT NULL,
    issued_at TIMESTAMPTZ NOT NULL,
    expires_at TIMESTAMPTZ NOT NULL,
    created_at TIMESTAMPTZ NOT NULL,
    PRIMARY KEY (user_id, operation_key),
    UNIQUE (user_id, commit_id),
    CHECK (authorization_epoch >= 1),
    CHECK (data_revision >= 1),
    CHECK (expires_at >= created_at),
    CHECK (expires_at <= created_at + INTERVAL '180 days'),
    FOREIGN KEY (user_id) REFERENCES user_control (user_id) ON DELETE NO ACTION DEFERRABLE INITIALLY DEFERRED,
    FOREIGN KEY (user_id, task_id) REFERENCES task_sessions (user_id, id) ON DELETE NO ACTION DEFERRABLE INITIALLY DEFERRED
);
CREATE INDEX ix_command_receipts_0 ON command_receipts (user_id, task_id);
CREATE INDEX ix_command_receipts_1 ON command_receipts (expires_at);

-- 最小化业务事件（命令与数据控制）
CREATE TABLE audit_events (
    user_id TEXT NOT NULL,
    id TEXT NOT NULL,
    commit_id TEXT NOT NULL,
    event_kind TEXT NOT NULL,
    object_kind TEXT NOT NULL,
    object_id TEXT NOT NULL,
    object_revision BIGINT,
    reason_code TEXT,
    created_at TIMESTAMPTZ NOT NULL,
    retain_until TIMESTAMPTZ NOT NULL,
    renewed_at TIMESTAMPTZ,
    PRIMARY KEY (user_id, id),
    CHECK (object_revision IS NULL OR (object_revision >= 1)),
    CHECK (retain_until >= created_at),
    CHECK (((renewed_at IS NULL AND retain_until <= created_at + INTERVAL '180 days') OR (renewed_at IS NOT NULL AND renewed_at >= created_at AND retain_until <= renewed_at + INTERVAL '180 days'))),
    FOREIGN KEY (user_id) REFERENCES user_control (user_id) ON DELETE NO ACTION DEFERRABLE INITIALLY DEFERRED,
    FOREIGN KEY (user_id, commit_id) REFERENCES command_receipts (user_id, commit_id) ON DELETE NO ACTION DEFERRABLE INITIALLY DEFERRED
);
CREATE INDEX ix_audit_events_0 ON audit_events (user_id, commit_id);
CREATE INDEX ix_audit_events_1 ON audit_events (retain_until);

-- 导出删除清理任务（命令与数据控制）
CREATE TABLE data_control_jobs (
    user_id TEXT NOT NULL,
    id TEXT NOT NULL,
    job_kind TEXT NOT NULL,
    state TEXT NOT NULL,
    scope_manifest JSONB NOT NULL,
    requested_at TIMESTAMPTZ NOT NULL,
    deadline_at TIMESTAMPTZ NOT NULL,
    completed_at TIMESTAMPTZ,
    artifact_key TEXT,
    artifact_expires_at TIMESTAMPTZ,
    failure_code TEXT,
    created_at TIMESTAMPTZ NOT NULL,
    PRIMARY KEY (user_id, id),
    CHECK (job_kind IN ('导出', '主动删除', '期限清理')),
    CHECK (state IN ('待处理', '处理中', '已完成', '失败')),
    CHECK (deadline_at >= requested_at),
    CHECK (state <> '已完成' OR completed_at IS NOT NULL),
    CHECK (job_kind <> '主动删除' OR deadline_at <= requested_at + INTERVAL '1 days'),
    FOREIGN KEY (user_id) REFERENCES user_control (user_id) ON DELETE NO ACTION DEFERRABLE INITIALLY DEFERRED
);
CREATE INDEX ix_data_control_jobs_0 ON data_control_jobs (state, deadline_at);

-- 循环的当前版本引用在所有表声明后补充。
ALTER TABLE user_control ADD CONSTRAINT fk_user_control_0 FOREIGN KEY (user_id, current_profile_revision) REFERENCES profile_revisions (user_id, revision) ON DELETE NO ACTION DEFERRABLE INITIALLY DEFERRED;
ALTER TABLE plan_heads ADD CONSTRAINT fk_plan_heads_1 FOREIGN KEY (user_id, id, current_revision) REFERENCES plan_revisions (user_id, id, revision) ON DELETE NO ACTION DEFERRABLE INITIALLY DEFERRED;
ALTER TABLE inventory_heads ADD CONSTRAINT fk_inventory_heads_2 FOREIGN KEY (user_id, id, current_revision) REFERENCES inventory_revisions (user_id, id, revision) ON DELETE NO ACTION DEFERRABLE INITIALLY DEFERRED;
ALTER TABLE meal_heads ADD CONSTRAINT fk_meal_heads_1 FOREIGN KEY (user_id, id, current_revision) REFERENCES meal_revisions (user_id, id, revision) ON DELETE NO ACTION DEFERRABLE INITIALLY DEFERRED;
ALTER TABLE micro_actions ADD CONSTRAINT fk_micro_actions_5 FOREIGN KEY (user_id, id, current_window_revision) REFERENCES action_windows (user_id, action_id, revision) ON DELETE NO ACTION DEFERRABLE INITIALLY DEFERRED;
ALTER TABLE micro_actions ADD CONSTRAINT fk_micro_actions_6 FOREIGN KEY (user_id, id, current_execution_revision) REFERENCES execution_revisions (user_id, action_id, revision) ON DELETE NO ACTION DEFERRABLE INITIALLY DEFERRED;
