-- DietLens 第二次作业：数据库候选设计，仅保存，不执行。
-- 类型、约束与删除顺序以数据字典和数据库设计正文为准。

-- 用户处理控制（授权与证据）
CREATE TABLE user_control (
    user_id TEXT NOT NULL,
    external_subject TEXT,
    processing_state TEXT NOT NULL,
    authorization_epoch INTEGER NOT NULL,
    data_revision INTEGER NOT NULL,
    current_profile_revision INTEGER,
    delete_requested_at TEXT,
    created_at TEXT NOT NULL,
    PRIMARY KEY (user_id),
    UNIQUE (external_subject),
    CHECK (processing_state IN ('正常', '待删除', '清理中', '清理失败', '已清理待备份到期')),
    CHECK (typeof(authorization_epoch) = 'integer' AND authorization_epoch >= 1),
    CHECK (typeof(data_revision) = 'integer' AND data_revision >= 1),
    CHECK (current_profile_revision IS NULL OR (typeof(current_profile_revision) = 'integer' AND current_profile_revision >= 1)),
    CHECK (delete_requested_at IS NULL OR (typeof(delete_requested_at) = 'text' AND length(delete_requested_at) = 24 AND strftime('%Y-%m-%dT%H:%M:%fZ', delete_requested_at) IS NOT NULL AND strftime('%Y-%m-%dT%H:%M:%fZ', delete_requested_at) = delete_requested_at)),
    CHECK (typeof(created_at) = 'text' AND length(created_at) = 24 AND strftime('%Y-%m-%dT%H:%M:%fZ', created_at) IS NOT NULL AND strftime('%Y-%m-%dT%H:%M:%fZ', created_at) = created_at),
    FOREIGN KEY (user_id, current_profile_revision) REFERENCES profile_revisions (user_id, revision) ON DELETE NO ACTION DEFERRABLE INITIALLY DEFERRED
);
CREATE INDEX ix_user_control_0 ON user_control (user_id, current_profile_revision);

-- 档案确认版本（授权与证据）
CREATE TABLE profile_revisions (
    user_id TEXT NOT NULL,
    revision INTEGER NOT NULL,
    confirmed_fields TEXT NOT NULL,
    confirmed_at TEXT NOT NULL,
    created_at TEXT NOT NULL,
    retain_until TEXT NOT NULL,
    renewed_at TEXT,
    PRIMARY KEY (user_id, revision),
    CHECK (typeof(revision) = 'integer' AND revision >= 1),
    CHECK (json_valid(confirmed_fields)),
    CHECK (typeof(confirmed_at) = 'text' AND length(confirmed_at) = 24 AND strftime('%Y-%m-%dT%H:%M:%fZ', confirmed_at) IS NOT NULL AND strftime('%Y-%m-%dT%H:%M:%fZ', confirmed_at) = confirmed_at),
    CHECK (typeof(created_at) = 'text' AND length(created_at) = 24 AND strftime('%Y-%m-%dT%H:%M:%fZ', created_at) IS NOT NULL AND strftime('%Y-%m-%dT%H:%M:%fZ', created_at) = created_at),
    CHECK (typeof(retain_until) = 'text' AND length(retain_until) = 24 AND strftime('%Y-%m-%dT%H:%M:%fZ', retain_until) IS NOT NULL AND strftime('%Y-%m-%dT%H:%M:%fZ', retain_until) = retain_until),
    CHECK (renewed_at IS NULL OR (typeof(renewed_at) = 'text' AND length(renewed_at) = 24 AND strftime('%Y-%m-%dT%H:%M:%fZ', renewed_at) IS NOT NULL AND strftime('%Y-%m-%dT%H:%M:%fZ', renewed_at) = renewed_at)),
    CHECK (retain_until >= created_at),
    CHECK (((renewed_at IS NULL AND retain_until <= strftime('%Y-%m-%dT%H:%M:%fZ', created_at, '+180 days')) OR (renewed_at IS NOT NULL AND renewed_at >= created_at AND retain_until <= strftime('%Y-%m-%dT%H:%M:%fZ', renewed_at, '+180 days')))),
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
    expires_at TEXT NOT NULL,
    processing_state TEXT NOT NULL,
    created_at TEXT NOT NULL,
    retain_until TEXT NOT NULL,
    renewed_at TEXT,
    PRIMARY KEY (user_id, id),
    CHECK (processing_state IN ('可用', '待清理', '已清理')),
    CHECK (((processing_state = '已清理' AND storage_key IS NULL) OR (processing_state <> '已清理' AND storage_key IS NOT NULL))),
    CHECK (typeof(expires_at) = 'text' AND length(expires_at) = 24 AND strftime('%Y-%m-%dT%H:%M:%fZ', expires_at) IS NOT NULL AND strftime('%Y-%m-%dT%H:%M:%fZ', expires_at) = expires_at),
    CHECK (typeof(created_at) = 'text' AND length(created_at) = 24 AND strftime('%Y-%m-%dT%H:%M:%fZ', created_at) IS NOT NULL AND strftime('%Y-%m-%dT%H:%M:%fZ', created_at) = created_at),
    CHECK (typeof(retain_until) = 'text' AND length(retain_until) = 24 AND strftime('%Y-%m-%dT%H:%M:%fZ', retain_until) IS NOT NULL AND strftime('%Y-%m-%dT%H:%M:%fZ', retain_until) = retain_until),
    CHECK (renewed_at IS NULL OR (typeof(renewed_at) = 'text' AND length(renewed_at) = 24 AND strftime('%Y-%m-%dT%H:%M:%fZ', renewed_at) IS NOT NULL AND strftime('%Y-%m-%dT%H:%M:%fZ', renewed_at) = renewed_at)),
    CHECK (retain_until >= created_at),
    CHECK (((renewed_at IS NULL AND retain_until <= strftime('%Y-%m-%dT%H:%M:%fZ', created_at, '+180 days')) OR (renewed_at IS NOT NULL AND renewed_at >= created_at AND retain_until <= strftime('%Y-%m-%dT%H:%M:%fZ', renewed_at, '+180 days')))),
    CHECK (expires_at >= created_at),
    CHECK (expires_at <= strftime('%Y-%m-%dT%H:%M:%fZ', created_at, '+1 days')),
    FOREIGN KEY (user_id) REFERENCES user_control (user_id) ON DELETE NO ACTION DEFERRABLE INITIALLY DEFERRED
);
CREATE INDEX ix_media_assets_0 ON media_assets (expires_at);
CREATE INDEX ix_media_assets_1 ON media_assets (retain_until);

-- 用途授权修订（授权与证据）
CREATE TABLE consent_revisions (
    user_id TEXT NOT NULL,
    purpose TEXT NOT NULL,
    scope_key TEXT NOT NULL,
    revision INTEGER NOT NULL,
    asset_id TEXT,
    allowed INTEGER NOT NULL,
    recipient TEXT,
    authorization_epoch INTEGER NOT NULL,
    confirmed_at TEXT NOT NULL,
    created_at TEXT NOT NULL,
    retain_until TEXT NOT NULL,
    renewed_at TEXT,
    PRIMARY KEY (user_id, purpose, scope_key, revision),
    CHECK (purpose IN ('历史分析', '图片外传', '提醒')),
    CHECK (((purpose = '图片外传' AND asset_id IS NOT NULL AND scope_key = asset_id AND recipient IS NOT NULL) OR (purpose <> '图片外传' AND asset_id IS NULL AND scope_key = '全域'))),
    CHECK (typeof(revision) = 'integer' AND revision >= 1),
    CHECK (typeof(allowed) = 'integer' AND allowed IN (0, 1)),
    CHECK (typeof(authorization_epoch) = 'integer' AND authorization_epoch >= 1),
    CHECK (typeof(confirmed_at) = 'text' AND length(confirmed_at) = 24 AND strftime('%Y-%m-%dT%H:%M:%fZ', confirmed_at) IS NOT NULL AND strftime('%Y-%m-%dT%H:%M:%fZ', confirmed_at) = confirmed_at),
    CHECK (typeof(created_at) = 'text' AND length(created_at) = 24 AND strftime('%Y-%m-%dT%H:%M:%fZ', created_at) IS NOT NULL AND strftime('%Y-%m-%dT%H:%M:%fZ', created_at) = created_at),
    CHECK (typeof(retain_until) = 'text' AND length(retain_until) = 24 AND strftime('%Y-%m-%dT%H:%M:%fZ', retain_until) IS NOT NULL AND strftime('%Y-%m-%dT%H:%M:%fZ', retain_until) = retain_until),
    CHECK (renewed_at IS NULL OR (typeof(renewed_at) = 'text' AND length(renewed_at) = 24 AND strftime('%Y-%m-%dT%H:%M:%fZ', renewed_at) IS NOT NULL AND strftime('%Y-%m-%dT%H:%M:%fZ', renewed_at) = renewed_at)),
    CHECK (retain_until >= created_at),
    CHECK (((renewed_at IS NULL AND retain_until <= strftime('%Y-%m-%dT%H:%M:%fZ', created_at, '+180 days')) OR (renewed_at IS NOT NULL AND renewed_at >= created_at AND retain_until <= strftime('%Y-%m-%dT%H:%M:%fZ', renewed_at, '+180 days')))),
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
    draft_revision INTEGER NOT NULL,
    draft_payload TEXT NOT NULL,
    authorization_epoch INTEGER NOT NULL,
    expires_at TEXT NOT NULL,
    created_at TEXT NOT NULL,
    PRIMARY KEY (user_id, id),
    CHECK (state IN ('进行中', '已暂停', '已取消', '已完成')),
    CHECK (typeof(draft_revision) = 'integer' AND draft_revision >= 1),
    CHECK (json_valid(draft_payload)),
    CHECK (typeof(authorization_epoch) = 'integer' AND authorization_epoch >= 1),
    CHECK (typeof(expires_at) = 'text' AND length(expires_at) = 24 AND strftime('%Y-%m-%dT%H:%M:%fZ', expires_at) IS NOT NULL AND strftime('%Y-%m-%dT%H:%M:%fZ', expires_at) = expires_at),
    CHECK (typeof(created_at) = 'text' AND length(created_at) = 24 AND strftime('%Y-%m-%dT%H:%M:%fZ', created_at) IS NOT NULL AND strftime('%Y-%m-%dT%H:%M:%fZ', created_at) = created_at),
    CHECK (expires_at >= created_at),
    CHECK (expires_at <= strftime('%Y-%m-%dT%H:%M:%fZ', created_at, '+7 days')),
    FOREIGN KEY (user_id) REFERENCES user_control (user_id) ON DELETE NO ACTION DEFERRABLE INITIALLY DEFERRED
);
CREATE INDEX ix_task_sessions_0 ON task_sessions (expires_at);

-- 已确认情境（授权与证据）
CREATE TABLE context_snapshots (
    user_id TEXT NOT NULL,
    id TEXT NOT NULL,
    profile_revision INTEGER NOT NULL,
    context_key TEXT NOT NULL,
    situation TEXT NOT NULL,
    authorization_epoch INTEGER NOT NULL,
    confirmed_at TEXT NOT NULL,
    created_at TEXT NOT NULL,
    retain_until TEXT NOT NULL,
    renewed_at TEXT,
    PRIMARY KEY (user_id, id),
    CHECK (typeof(profile_revision) = 'integer' AND profile_revision >= 1),
    CHECK (json_valid(situation)),
    CHECK (typeof(authorization_epoch) = 'integer' AND authorization_epoch >= 1),
    CHECK (typeof(confirmed_at) = 'text' AND length(confirmed_at) = 24 AND strftime('%Y-%m-%dT%H:%M:%fZ', confirmed_at) IS NOT NULL AND strftime('%Y-%m-%dT%H:%M:%fZ', confirmed_at) = confirmed_at),
    CHECK (typeof(created_at) = 'text' AND length(created_at) = 24 AND strftime('%Y-%m-%dT%H:%M:%fZ', created_at) IS NOT NULL AND strftime('%Y-%m-%dT%H:%M:%fZ', created_at) = created_at),
    CHECK (typeof(retain_until) = 'text' AND length(retain_until) = 24 AND strftime('%Y-%m-%dT%H:%M:%fZ', retain_until) IS NOT NULL AND strftime('%Y-%m-%dT%H:%M:%fZ', retain_until) = retain_until),
    CHECK (renewed_at IS NULL OR (typeof(renewed_at) = 'text' AND length(renewed_at) = 24 AND strftime('%Y-%m-%dT%H:%M:%fZ', renewed_at) IS NOT NULL AND strftime('%Y-%m-%dT%H:%M:%fZ', renewed_at) = renewed_at)),
    CHECK (retain_until >= created_at),
    CHECK (((renewed_at IS NULL AND retain_until <= strftime('%Y-%m-%dT%H:%M:%fZ', created_at, '+180 days')) OR (renewed_at IS NOT NULL AND renewed_at >= created_at AND retain_until <= strftime('%Y-%m-%dT%H:%M:%fZ', renewed_at, '+180 days')))),
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
    published_at TEXT,
    acquired_at TEXT NOT NULL,
    asset_id TEXT,
    asset_digest TEXT,
    verification_note TEXT,
    created_at TEXT NOT NULL,
    retain_until TEXT NOT NULL,
    renewed_at TEXT,
    PRIMARY KEY (user_id, id),
    CHECK (source_kind IN ('用户自述', '商品标签', '菜单', '公开资料', '本地编码')),
    CHECK (published_at IS NULL OR (typeof(published_at) = 'text' AND length(published_at) = 24 AND strftime('%Y-%m-%dT%H:%M:%fZ', published_at) IS NOT NULL AND strftime('%Y-%m-%dT%H:%M:%fZ', published_at) = published_at)),
    CHECK (typeof(acquired_at) = 'text' AND length(acquired_at) = 24 AND strftime('%Y-%m-%dT%H:%M:%fZ', acquired_at) IS NOT NULL AND strftime('%Y-%m-%dT%H:%M:%fZ', acquired_at) = acquired_at),
    CHECK (typeof(created_at) = 'text' AND length(created_at) = 24 AND strftime('%Y-%m-%dT%H:%M:%fZ', created_at) IS NOT NULL AND strftime('%Y-%m-%dT%H:%M:%fZ', created_at) = created_at),
    CHECK (typeof(retain_until) = 'text' AND length(retain_until) = 24 AND strftime('%Y-%m-%dT%H:%M:%fZ', retain_until) IS NOT NULL AND strftime('%Y-%m-%dT%H:%M:%fZ', retain_until) = retain_until),
    CHECK (renewed_at IS NULL OR (typeof(renewed_at) = 'text' AND length(renewed_at) = 24 AND strftime('%Y-%m-%dT%H:%M:%fZ', renewed_at) IS NOT NULL AND strftime('%Y-%m-%dT%H:%M:%fZ', renewed_at) = renewed_at)),
    CHECK (retain_until >= created_at),
    CHECK (((renewed_at IS NULL AND retain_until <= strftime('%Y-%m-%dT%H:%M:%fZ', created_at, '+180 days')) OR (renewed_at IS NOT NULL AND renewed_at >= created_at AND retain_until <= strftime('%Y-%m-%dT%H:%M:%fZ', renewed_at, '+180 days')))),
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
    checked_at TEXT,
    created_at TEXT NOT NULL,
    retain_until TEXT NOT NULL,
    renewed_at TEXT,
    basis_state TEXT NOT NULL,
    basis_micros INTEGER,
    basis_unit TEXT,
    PRIMARY KEY (user_id, id),
    CHECK (recipe_coverage IN ('完整已核对', '仅部分已知', '未知')),
    CHECK (basis_state IN ('已知', '未知')),
    CHECK (((basis_state = '已知' AND basis_micros IS NOT NULL AND basis_unit IS NOT NULL) OR (basis_state = '未知' AND basis_micros IS NULL))),
    CHECK (checked_at IS NULL OR (typeof(checked_at) = 'text' AND length(checked_at) = 24 AND strftime('%Y-%m-%dT%H:%M:%fZ', checked_at) IS NOT NULL AND strftime('%Y-%m-%dT%H:%M:%fZ', checked_at) = checked_at)),
    CHECK (typeof(created_at) = 'text' AND length(created_at) = 24 AND strftime('%Y-%m-%dT%H:%M:%fZ', created_at) IS NOT NULL AND strftime('%Y-%m-%dT%H:%M:%fZ', created_at) = created_at),
    CHECK (typeof(retain_until) = 'text' AND length(retain_until) = 24 AND strftime('%Y-%m-%dT%H:%M:%fZ', retain_until) IS NOT NULL AND strftime('%Y-%m-%dT%H:%M:%fZ', retain_until) = retain_until),
    CHECK (renewed_at IS NULL OR (typeof(renewed_at) = 'text' AND length(renewed_at) = 24 AND strftime('%Y-%m-%dT%H:%M:%fZ', renewed_at) IS NOT NULL AND strftime('%Y-%m-%dT%H:%M:%fZ', renewed_at) = renewed_at)),
    CHECK (basis_micros IS NULL OR (typeof(basis_micros) = 'integer' AND basis_micros >= 0 AND basis_micros <= 9000000000000000)),
    CHECK (retain_until >= created_at),
    CHECK (((renewed_at IS NULL AND retain_until <= strftime('%Y-%m-%dT%H:%M:%fZ', created_at, '+180 days')) OR (renewed_at IS NOT NULL AND renewed_at >= created_at AND retain_until <= strftime('%Y-%m-%dT%H:%M:%fZ', renewed_at, '+180 days')))),
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
    number_micros INTEGER,
    text_value TEXT,
    unit TEXT,
    raw_value TEXT,
    checked_at TEXT,
    created_at TEXT NOT NULL,
    PRIMARY KEY (user_id, observation_id, field_key),
    CHECK (state IN ('已核对', '待核对', '未知', '冲突')),
    CHECK (value_kind IN ('数值', '文字')),
    CHECK (((state IN ('未知','冲突') AND number_micros IS NULL AND text_value IS NULL) OR (state IN ('已核对','待核对') AND ((value_kind = '数值' AND number_micros IS NOT NULL AND text_value IS NULL AND unit IS NOT NULL) OR (value_kind = '文字' AND text_value IS NOT NULL AND number_micros IS NULL))))),
    CHECK (number_micros IS NULL OR (typeof(number_micros) = 'integer' AND number_micros >= 0 AND number_micros <= 9000000000000000)),
    CHECK (checked_at IS NULL OR (typeof(checked_at) = 'text' AND length(checked_at) = 24 AND strftime('%Y-%m-%dT%H:%M:%fZ', checked_at) IS NOT NULL AND strftime('%Y-%m-%dT%H:%M:%fZ', checked_at) = checked_at)),
    CHECK (typeof(created_at) = 'text' AND length(created_at) = 24 AND strftime('%Y-%m-%dT%H:%M:%fZ', created_at) IS NOT NULL AND strftime('%Y-%m-%dT%H:%M:%fZ', created_at) = created_at),
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
    created_at TEXT NOT NULL,
    PRIMARY KEY (user_id, observation_id, field_key, source_id),
    CHECK (source_role IN ('原始材料', '用户核对', '冲突材料')),
    CHECK (typeof(created_at) = 'text' AND length(created_at) = 24 AND strftime('%Y-%m-%dT%H:%M:%fZ', created_at) IS NOT NULL AND strftime('%Y-%m-%dT%H:%M:%fZ', created_at) = created_at),
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
    reasons TEXT NOT NULL,
    evaluated_at TEXT NOT NULL,
    created_at TEXT NOT NULL,
    retain_until TEXT NOT NULL,
    renewed_at TEXT,
    PRIMARY KEY (user_id, id),
    CHECK (outcome IN ('通过', '拦截', '待核对')),
    CHECK (json_valid(reasons)),
    CHECK (typeof(evaluated_at) = 'text' AND length(evaluated_at) = 24 AND strftime('%Y-%m-%dT%H:%M:%fZ', evaluated_at) IS NOT NULL AND strftime('%Y-%m-%dT%H:%M:%fZ', evaluated_at) = evaluated_at),
    CHECK (typeof(created_at) = 'text' AND length(created_at) = 24 AND strftime('%Y-%m-%dT%H:%M:%fZ', created_at) IS NOT NULL AND strftime('%Y-%m-%dT%H:%M:%fZ', created_at) = created_at),
    CHECK (typeof(retain_until) = 'text' AND length(retain_until) = 24 AND strftime('%Y-%m-%dT%H:%M:%fZ', retain_until) IS NOT NULL AND strftime('%Y-%m-%dT%H:%M:%fZ', retain_until) = retain_until),
    CHECK (renewed_at IS NULL OR (typeof(renewed_at) = 'text' AND length(renewed_at) = 24 AND strftime('%Y-%m-%dT%H:%M:%fZ', renewed_at) IS NOT NULL AND strftime('%Y-%m-%dT%H:%M:%fZ', renewed_at) = renewed_at)),
    CHECK (retain_until >= created_at),
    CHECK (((renewed_at IS NULL AND retain_until <= strftime('%Y-%m-%dT%H:%M:%fZ', created_at, '+180 days')) OR (renewed_at IS NOT NULL AND renewed_at >= created_at AND retain_until <= strftime('%Y-%m-%dT%H:%M:%fZ', renewed_at, '+180 days')))),
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
    created_at TEXT NOT NULL,
    retain_until TEXT NOT NULL,
    renewed_at TEXT,
    PRIMARY KEY (user_id, id),
    CHECK (typeof(created_at) = 'text' AND length(created_at) = 24 AND strftime('%Y-%m-%dT%H:%M:%fZ', created_at) IS NOT NULL AND strftime('%Y-%m-%dT%H:%M:%fZ', created_at) = created_at),
    CHECK (typeof(retain_until) = 'text' AND length(retain_until) = 24 AND strftime('%Y-%m-%dT%H:%M:%fZ', retain_until) IS NOT NULL AND strftime('%Y-%m-%dT%H:%M:%fZ', retain_until) = retain_until),
    CHECK (renewed_at IS NULL OR (typeof(renewed_at) = 'text' AND length(renewed_at) = 24 AND strftime('%Y-%m-%dT%H:%M:%fZ', renewed_at) IS NOT NULL AND strftime('%Y-%m-%dT%H:%M:%fZ', renewed_at) = renewed_at)),
    CHECK (retain_until >= created_at),
    CHECK (((renewed_at IS NULL AND retain_until <= strftime('%Y-%m-%dT%H:%M:%fZ', created_at, '+180 days')) OR (renewed_at IS NOT NULL AND renewed_at >= created_at AND retain_until <= strftime('%Y-%m-%dT%H:%M:%fZ', renewed_at, '+180 days')))),
    FOREIGN KEY (user_id) REFERENCES user_control (user_id) ON DELETE NO ACTION DEFERRABLE INITIALLY DEFERRED
);
CREATE INDEX ix_ingredients_0 ON ingredients (retain_until);

-- 计划身份（计划与准备）
CREATE TABLE plan_heads (
    user_id TEXT NOT NULL,
    id TEXT NOT NULL,
    current_revision INTEGER NOT NULL,
    row_version INTEGER NOT NULL,
    state TEXT NOT NULL,
    created_at TEXT NOT NULL,
    retain_until TEXT NOT NULL,
    renewed_at TEXT,
    PRIMARY KEY (user_id, id),
    CHECK (state IN ('有效', '已删除')),
    CHECK (typeof(current_revision) = 'integer' AND current_revision >= 1),
    CHECK (typeof(row_version) = 'integer' AND row_version >= 1),
    CHECK (typeof(created_at) = 'text' AND length(created_at) = 24 AND strftime('%Y-%m-%dT%H:%M:%fZ', created_at) IS NOT NULL AND strftime('%Y-%m-%dT%H:%M:%fZ', created_at) = created_at),
    CHECK (typeof(retain_until) = 'text' AND length(retain_until) = 24 AND strftime('%Y-%m-%dT%H:%M:%fZ', retain_until) IS NOT NULL AND strftime('%Y-%m-%dT%H:%M:%fZ', retain_until) = retain_until),
    CHECK (renewed_at IS NULL OR (typeof(renewed_at) = 'text' AND length(renewed_at) = 24 AND strftime('%Y-%m-%dT%H:%M:%fZ', renewed_at) IS NOT NULL AND strftime('%Y-%m-%dT%H:%M:%fZ', renewed_at) = renewed_at)),
    CHECK (retain_until >= created_at),
    CHECK (((renewed_at IS NULL AND retain_until <= strftime('%Y-%m-%dT%H:%M:%fZ', created_at, '+180 days')) OR (renewed_at IS NOT NULL AND renewed_at >= created_at AND retain_until <= strftime('%Y-%m-%dT%H:%M:%fZ', renewed_at, '+180 days')))),
    FOREIGN KEY (user_id) REFERENCES user_control (user_id) ON DELETE NO ACTION DEFERRABLE INITIALLY DEFERRED,
    FOREIGN KEY (user_id, id, current_revision) REFERENCES plan_revisions (user_id, id, revision) ON DELETE NO ACTION DEFERRABLE INITIALLY DEFERRED
);
CREATE INDEX ix_plan_heads_0 ON plan_heads (user_id, id, current_revision);
CREATE INDEX ix_plan_heads_1 ON plan_heads (retain_until);

-- 计划确认版本（计划与准备）
CREATE TABLE plan_revisions (
    user_id TEXT NOT NULL,
    id TEXT NOT NULL,
    revision INTEGER NOT NULL,
    mode TEXT NOT NULL,
    start_date TEXT NOT NULL,
    end_date TEXT NOT NULL,
    day_count INTEGER NOT NULL,
    context_id TEXT NOT NULL,
    confirmed_at TEXT NOT NULL,
    created_at TEXT NOT NULL,
    PRIMARY KEY (user_id, id, revision),
    CHECK (end_date >= start_date),
    CHECK (day_count IN (1, 7)),
    CHECK (mode IN ('完整', '指定')),
    CHECK (typeof(revision) = 'integer' AND revision >= 1),
    CHECK (typeof(start_date) = 'text' AND length(start_date) = 10 AND date(start_date, '+0 days') IS NOT NULL AND date(start_date, '+0 days') = start_date),
    CHECK (typeof(end_date) = 'text' AND length(end_date) = 10 AND date(end_date, '+0 days') IS NOT NULL AND date(end_date, '+0 days') = end_date),
    CHECK (typeof(day_count) = 'integer' AND day_count >= 1),
    CHECK (typeof(confirmed_at) = 'text' AND length(confirmed_at) = 24 AND strftime('%Y-%m-%dT%H:%M:%fZ', confirmed_at) IS NOT NULL AND strftime('%Y-%m-%dT%H:%M:%fZ', confirmed_at) = confirmed_at),
    CHECK (typeof(created_at) = 'text' AND length(created_at) = 24 AND strftime('%Y-%m-%dT%H:%M:%fZ', created_at) IS NOT NULL AND strftime('%Y-%m-%dT%H:%M:%fZ', created_at) = created_at),
    CHECK (end_date = date(start_date, '+' || (day_count - 1) || ' days')),
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
    plan_revision INTEGER NOT NULL,
    meal_date TEXT NOT NULL,
    meal_slot TEXT NOT NULL,
    people_count INTEGER NOT NULL,
    created_at TEXT NOT NULL,
    PRIMARY KEY (user_id, id),
    UNIQUE (user_id, plan_id, plan_revision, meal_date, meal_slot),
    UNIQUE (user_id, id, meal_date, meal_slot),
    CHECK (meal_slot IN ('早餐', '午餐', '晚餐')),
    CHECK (typeof(plan_revision) = 'integer' AND plan_revision >= 1),
    CHECK (typeof(meal_date) = 'text' AND length(meal_date) = 10 AND date(meal_date, '+0 days') IS NOT NULL AND date(meal_date, '+0 days') = meal_date),
    CHECK (typeof(people_count) = 'integer' AND people_count >= 1),
    CHECK (typeof(created_at) = 'text' AND length(created_at) = 24 AND strftime('%Y-%m-%dT%H:%M:%fZ', created_at) IS NOT NULL AND strftime('%Y-%m-%dT%H:%M:%fZ', created_at) = created_at),
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
    created_at TEXT NOT NULL,
    quantity_state TEXT NOT NULL,
    quantity_micros INTEGER,
    quantity_unit TEXT,
    PRIMARY KEY (user_id, id),
    CHECK (quantity_basis IN ('每人', '本餐总量')),
    CHECK (quantity_state IN ('已知', '未知')),
    CHECK (((quantity_state = '已知' AND quantity_micros IS NOT NULL AND quantity_unit IS NOT NULL) OR (quantity_state = '未知' AND quantity_micros IS NULL))),
    CHECK (typeof(created_at) = 'text' AND length(created_at) = 24 AND strftime('%Y-%m-%dT%H:%M:%fZ', created_at) IS NOT NULL AND strftime('%Y-%m-%dT%H:%M:%fZ', created_at) = created_at),
    CHECK (quantity_micros IS NULL OR (typeof(quantity_micros) = 'integer' AND quantity_micros >= 0 AND quantity_micros <= 9000000000000000)),
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
    created_at TEXT NOT NULL,
    quantity_state TEXT NOT NULL,
    quantity_micros INTEGER,
    quantity_unit TEXT,
    PRIMARY KEY (user_id, id),
    CHECK (quantity_basis IN ('每人', '本餐总量')),
    CHECK (quantity_state IN ('已知', '未知')),
    CHECK (((quantity_state = '已知' AND quantity_micros IS NOT NULL AND quantity_unit IS NOT NULL) OR (quantity_state = '未知' AND quantity_micros IS NULL))),
    CHECK (typeof(created_at) = 'text' AND length(created_at) = 24 AND strftime('%Y-%m-%dT%H:%M:%fZ', created_at) IS NOT NULL AND strftime('%Y-%m-%dT%H:%M:%fZ', created_at) = created_at),
    CHECK (quantity_micros IS NULL OR (typeof(quantity_micros) = 'integer' AND quantity_micros >= 0 AND quantity_micros <= 9000000000000000)),
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
    meal_date TEXT NOT NULL,
    meal_slot TEXT NOT NULL,
    planned_meal_id TEXT NOT NULL,
    row_version INTEGER NOT NULL,
    created_at TEXT NOT NULL,
    PRIMARY KEY (user_id, meal_date, meal_slot),
    CHECK (meal_slot IN ('早餐', '午餐', '晚餐')),
    CHECK (typeof(meal_date) = 'text' AND length(meal_date) = 10 AND date(meal_date, '+0 days') IS NOT NULL AND date(meal_date, '+0 days') = meal_date),
    CHECK (typeof(row_version) = 'integer' AND row_version >= 1),
    CHECK (typeof(created_at) = 'text' AND length(created_at) = 24 AND strftime('%Y-%m-%dT%H:%M:%fZ', created_at) IS NOT NULL AND strftime('%Y-%m-%dT%H:%M:%fZ', created_at) = created_at),
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
    current_revision INTEGER NOT NULL,
    row_version INTEGER NOT NULL,
    state TEXT NOT NULL,
    created_at TEXT NOT NULL,
    retain_until TEXT NOT NULL,
    renewed_at TEXT,
    PRIMARY KEY (user_id, id),
    UNIQUE (user_id, ingredient_id, unit),
    CHECK (state IN ('有效', '已删除')),
    CHECK (typeof(current_revision) = 'integer' AND current_revision >= 1),
    CHECK (typeof(row_version) = 'integer' AND row_version >= 1),
    CHECK (typeof(created_at) = 'text' AND length(created_at) = 24 AND strftime('%Y-%m-%dT%H:%M:%fZ', created_at) IS NOT NULL AND strftime('%Y-%m-%dT%H:%M:%fZ', created_at) = created_at),
    CHECK (typeof(retain_until) = 'text' AND length(retain_until) = 24 AND strftime('%Y-%m-%dT%H:%M:%fZ', retain_until) IS NOT NULL AND strftime('%Y-%m-%dT%H:%M:%fZ', retain_until) = retain_until),
    CHECK (renewed_at IS NULL OR (typeof(renewed_at) = 'text' AND length(renewed_at) = 24 AND strftime('%Y-%m-%dT%H:%M:%fZ', renewed_at) IS NOT NULL AND strftime('%Y-%m-%dT%H:%M:%fZ', renewed_at) = renewed_at)),
    CHECK (retain_until >= created_at),
    CHECK (((renewed_at IS NULL AND retain_until <= strftime('%Y-%m-%dT%H:%M:%fZ', created_at, '+180 days')) OR (renewed_at IS NOT NULL AND renewed_at >= created_at AND retain_until <= strftime('%Y-%m-%dT%H:%M:%fZ', renewed_at, '+180 days')))),
    FOREIGN KEY (user_id) REFERENCES user_control (user_id) ON DELETE NO ACTION DEFERRABLE INITIALLY DEFERRED,
    FOREIGN KEY (user_id, ingredient_id) REFERENCES ingredients (user_id, id) ON DELETE NO ACTION DEFERRABLE INITIALLY DEFERRED,
    FOREIGN KEY (user_id, id, current_revision) REFERENCES inventory_revisions (user_id, id, revision) ON DELETE NO ACTION DEFERRABLE INITIALLY DEFERRED
);
CREATE INDEX ix_inventory_heads_0 ON inventory_heads (user_id, id, current_revision);
CREATE INDEX ix_inventory_heads_1 ON inventory_heads (retain_until);

-- 库存核对版本（计划与准备）
CREATE TABLE inventory_revisions (
    user_id TEXT NOT NULL,
    id TEXT NOT NULL,
    revision INTEGER NOT NULL,
    quantity_state TEXT NOT NULL,
    quantity_micros INTEGER,
    observed_at TEXT NOT NULL,
    reason TEXT NOT NULL,
    confirmed_at TEXT NOT NULL,
    created_at TEXT NOT NULL,
    PRIMARY KEY (user_id, id, revision),
    CHECK (quantity_state IN ('已知', '未知')),
    CHECK (((quantity_state = '已知' AND quantity_micros IS NOT NULL) OR (quantity_state = '未知' AND quantity_micros IS NULL))),
    CHECK (typeof(revision) = 'integer' AND revision >= 1),
    CHECK (quantity_micros IS NULL OR (typeof(quantity_micros) = 'integer' AND quantity_micros >= 0 AND quantity_micros <= 9000000000000000)),
    CHECK (typeof(observed_at) = 'text' AND length(observed_at) = 24 AND strftime('%Y-%m-%dT%H:%M:%fZ', observed_at) IS NOT NULL AND strftime('%Y-%m-%dT%H:%M:%fZ', observed_at) = observed_at),
    CHECK (typeof(confirmed_at) = 'text' AND length(confirmed_at) = 24 AND strftime('%Y-%m-%dT%H:%M:%fZ', confirmed_at) IS NOT NULL AND strftime('%Y-%m-%dT%H:%M:%fZ', confirmed_at) = confirmed_at),
    CHECK (typeof(created_at) = 'text' AND length(created_at) = 24 AND strftime('%Y-%m-%dT%H:%M:%fZ', created_at) IS NOT NULL AND strftime('%Y-%m-%dT%H:%M:%fZ', created_at) = created_at),
    FOREIGN KEY (user_id) REFERENCES user_control (user_id) ON DELETE NO ACTION DEFERRABLE INITIALLY DEFERRED,
    FOREIGN KEY (user_id, id) REFERENCES inventory_heads (user_id, id) ON DELETE NO ACTION DEFERRABLE INITIALLY DEFERRED
);

-- 准备采购清单（计划与准备）
CREATE TABLE preparation_lists (
    user_id TEXT NOT NULL,
    id TEXT NOT NULL,
    plan_id TEXT NOT NULL,
    plan_revision INTEGER NOT NULL,
    row_version INTEGER NOT NULL,
    state TEXT NOT NULL,
    inventory_data_revision INTEGER NOT NULL,
    confirmed_at TEXT NOT NULL,
    created_at TEXT NOT NULL,
    retain_until TEXT NOT NULL,
    renewed_at TEXT,
    PRIMARY KEY (user_id, id),
    CHECK (state IN ('有效', '已失效', '已取消')),
    CHECK (typeof(plan_revision) = 'integer' AND plan_revision >= 1),
    CHECK (typeof(row_version) = 'integer' AND row_version >= 1),
    CHECK (typeof(inventory_data_revision) = 'integer' AND inventory_data_revision >= 1),
    CHECK (typeof(confirmed_at) = 'text' AND length(confirmed_at) = 24 AND strftime('%Y-%m-%dT%H:%M:%fZ', confirmed_at) IS NOT NULL AND strftime('%Y-%m-%dT%H:%M:%fZ', confirmed_at) = confirmed_at),
    CHECK (typeof(created_at) = 'text' AND length(created_at) = 24 AND strftime('%Y-%m-%dT%H:%M:%fZ', created_at) IS NOT NULL AND strftime('%Y-%m-%dT%H:%M:%fZ', created_at) = created_at),
    CHECK (typeof(retain_until) = 'text' AND length(retain_until) = 24 AND strftime('%Y-%m-%dT%H:%M:%fZ', retain_until) IS NOT NULL AND strftime('%Y-%m-%dT%H:%M:%fZ', retain_until) = retain_until),
    CHECK (renewed_at IS NULL OR (typeof(renewed_at) = 'text' AND length(renewed_at) = 24 AND strftime('%Y-%m-%dT%H:%M:%fZ', renewed_at) IS NOT NULL AND strftime('%Y-%m-%dT%H:%M:%fZ', renewed_at) = renewed_at)),
    CHECK (retain_until >= created_at),
    CHECK (((renewed_at IS NULL AND retain_until <= strftime('%Y-%m-%dT%H:%M:%fZ', created_at, '+180 days')) OR (renewed_at IS NOT NULL AND renewed_at >= created_at AND retain_until <= strftime('%Y-%m-%dT%H:%M:%fZ', renewed_at, '+180 days')))),
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
    has_unknown_requirement INTEGER NOT NULL,
    known_need_micros INTEGER NOT NULL,
    stock_state TEXT NOT NULL,
    stock_micros INTEGER,
    shortage_state TEXT NOT NULL,
    shortage_micros INTEGER,
    purchased_state TEXT NOT NULL,
    prepared_state TEXT NOT NULL,
    inventory_id TEXT,
    inventory_revision INTEGER,
    manual_reason TEXT,
    created_at TEXT NOT NULL,
    PRIMARY KEY (user_id, id),
    UNIQUE (user_id, list_id, ingredient_id, unit),
    CHECK (((inventory_id IS NULL AND inventory_revision IS NULL) OR (inventory_id IS NOT NULL AND inventory_revision IS NOT NULL))),
    CHECK (((stock_state = '已知' AND stock_micros IS NOT NULL) OR (stock_state = '未知' AND stock_micros IS NULL))),
    CHECK (((shortage_state = '已知' AND shortage_micros IS NOT NULL AND stock_state = '已知' AND has_unknown_requirement = 0) OR (shortage_state = '未知' AND shortage_micros IS NULL))),
    CHECK (stock_state IN ('已知', '未知')),
    CHECK (shortage_state IN ('已知', '未知')),
    CHECK (purchased_state IN ('未报告', '已确认', '不适用')),
    CHECK (prepared_state IN ('未报告', '已确认', '不适用')),
    CHECK (typeof(has_unknown_requirement) = 'integer' AND has_unknown_requirement IN (0, 1)),
    CHECK (typeof(known_need_micros) = 'integer' AND known_need_micros >= 0 AND known_need_micros <= 9000000000000000),
    CHECK (stock_micros IS NULL OR (typeof(stock_micros) = 'integer' AND stock_micros >= 0 AND stock_micros <= 9000000000000000)),
    CHECK (shortage_micros IS NULL OR (typeof(shortage_micros) = 'integer' AND shortage_micros >= 0 AND shortage_micros <= 9000000000000000)),
    CHECK (inventory_revision IS NULL OR (typeof(inventory_revision) = 'integer' AND inventory_revision >= 1)),
    CHECK (typeof(created_at) = 'text' AND length(created_at) = 24 AND strftime('%Y-%m-%dT%H:%M:%fZ', created_at) IS NOT NULL AND strftime('%Y-%m-%dT%H:%M:%fZ', created_at) = created_at),
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
    created_at TEXT NOT NULL,
    PRIMARY KEY (user_id, line_id, requirement_id),
    CHECK (typeof(created_at) = 'text' AND length(created_at) = 24 AND strftime('%Y-%m-%dT%H:%M:%fZ', created_at) IS NOT NULL AND strftime('%Y-%m-%dT%H:%M:%fZ', created_at) = created_at),
    FOREIGN KEY (user_id) REFERENCES user_control (user_id) ON DELETE NO ACTION DEFERRABLE INITIALLY DEFERRED,
    FOREIGN KEY (user_id, line_id) REFERENCES preparation_lines (user_id, id) ON DELETE NO ACTION DEFERRABLE INITIALLY DEFERRED,
    FOREIGN KEY (user_id, requirement_id) REFERENCES ingredient_requirements (user_id, id) ON DELETE NO ACTION DEFERRABLE INITIALLY DEFERRED
);
CREATE INDEX ix_preparation_sources_0 ON preparation_sources (user_id, requirement_id);

-- 个人用餐身份（实际与回顾）
CREATE TABLE meal_heads (
    user_id TEXT NOT NULL,
    id TEXT NOT NULL,
    current_revision INTEGER NOT NULL,
    row_version INTEGER NOT NULL,
    state TEXT NOT NULL,
    created_at TEXT NOT NULL,
    retain_until TEXT NOT NULL,
    renewed_at TEXT,
    PRIMARY KEY (user_id, id),
    CHECK (state IN ('有效', '已删除')),
    CHECK (typeof(current_revision) = 'integer' AND current_revision >= 1),
    CHECK (typeof(row_version) = 'integer' AND row_version >= 1),
    CHECK (typeof(created_at) = 'text' AND length(created_at) = 24 AND strftime('%Y-%m-%dT%H:%M:%fZ', created_at) IS NOT NULL AND strftime('%Y-%m-%dT%H:%M:%fZ', created_at) = created_at),
    CHECK (typeof(retain_until) = 'text' AND length(retain_until) = 24 AND strftime('%Y-%m-%dT%H:%M:%fZ', retain_until) IS NOT NULL AND strftime('%Y-%m-%dT%H:%M:%fZ', retain_until) = retain_until),
    CHECK (renewed_at IS NULL OR (typeof(renewed_at) = 'text' AND length(renewed_at) = 24 AND strftime('%Y-%m-%dT%H:%M:%fZ', renewed_at) IS NOT NULL AND strftime('%Y-%m-%dT%H:%M:%fZ', renewed_at) = renewed_at)),
    CHECK (retain_until >= created_at),
    CHECK (((renewed_at IS NULL AND retain_until <= strftime('%Y-%m-%dT%H:%M:%fZ', created_at, '+180 days')) OR (renewed_at IS NOT NULL AND renewed_at >= created_at AND retain_until <= strftime('%Y-%m-%dT%H:%M:%fZ', renewed_at, '+180 days')))),
    FOREIGN KEY (user_id) REFERENCES user_control (user_id) ON DELETE NO ACTION DEFERRABLE INITIALLY DEFERRED,
    FOREIGN KEY (user_id, id, current_revision) REFERENCES meal_revisions (user_id, id, revision) ON DELETE NO ACTION DEFERRABLE INITIALLY DEFERRED
);
CREATE INDEX ix_meal_heads_0 ON meal_heads (user_id, id, current_revision);
CREATE INDEX ix_meal_heads_1 ON meal_heads (retain_until);

-- 个人用餐版本（实际与回顾）
CREATE TABLE meal_revisions (
    user_id TEXT NOT NULL,
    id TEXT NOT NULL,
    revision INTEGER NOT NULL,
    meal_date TEXT NOT NULL,
    meal_slot TEXT NOT NULL,
    actual_at TEXT,
    note TEXT,
    confirmed_at TEXT NOT NULL,
    created_at TEXT NOT NULL,
    PRIMARY KEY (user_id, id, revision),
    CHECK (meal_slot IN ('早餐', '午餐', '晚餐', '加餐')),
    CHECK (typeof(revision) = 'integer' AND revision >= 1),
    CHECK (typeof(meal_date) = 'text' AND length(meal_date) = 10 AND date(meal_date, '+0 days') IS NOT NULL AND date(meal_date, '+0 days') = meal_date),
    CHECK (actual_at IS NULL OR (typeof(actual_at) = 'text' AND length(actual_at) = 24 AND strftime('%Y-%m-%dT%H:%M:%fZ', actual_at) IS NOT NULL AND strftime('%Y-%m-%dT%H:%M:%fZ', actual_at) = actual_at)),
    CHECK (typeof(confirmed_at) = 'text' AND length(confirmed_at) = 24 AND strftime('%Y-%m-%dT%H:%M:%fZ', confirmed_at) IS NOT NULL AND strftime('%Y-%m-%dT%H:%M:%fZ', confirmed_at) = confirmed_at),
    CHECK (typeof(created_at) = 'text' AND length(created_at) = 24 AND strftime('%Y-%m-%dT%H:%M:%fZ', created_at) IS NOT NULL AND strftime('%Y-%m-%dT%H:%M:%fZ', created_at) = created_at),
    FOREIGN KEY (user_id) REFERENCES user_control (user_id) ON DELETE NO ACTION DEFERRABLE INITIALLY DEFERRED,
    FOREIGN KEY (user_id, id) REFERENCES meal_heads (user_id, id) ON DELETE NO ACTION DEFERRABLE INITIALLY DEFERRED
);
CREATE INDEX ix_meal_revisions_0 ON meal_revisions (user_id, meal_date, meal_slot);

-- 个人实际食物（实际与回顾）
CREATE TABLE reported_foods (
    user_id TEXT NOT NULL,
    record_id TEXT NOT NULL,
    record_revision INTEGER NOT NULL,
    item_id TEXT NOT NULL,
    food_name TEXT NOT NULL,
    observation_id TEXT,
    planned_food_id TEXT,
    entry_source TEXT NOT NULL,
    created_at TEXT NOT NULL,
    quantity_state TEXT NOT NULL,
    quantity_micros INTEGER,
    quantity_unit TEXT,
    PRIMARY KEY (user_id, record_id, record_revision, item_id),
    CHECK (entry_source IN ('手动自述', '计划预填', '图文核对')),
    CHECK (quantity_state IN ('已知', '未知')),
    CHECK (((quantity_state = '已知' AND quantity_micros IS NOT NULL AND quantity_unit IS NOT NULL) OR (quantity_state = '未知' AND quantity_micros IS NULL))),
    CHECK (typeof(record_revision) = 'integer' AND record_revision >= 1),
    CHECK (typeof(created_at) = 'text' AND length(created_at) = 24 AND strftime('%Y-%m-%dT%H:%M:%fZ', created_at) IS NOT NULL AND strftime('%Y-%m-%dT%H:%M:%fZ', created_at) = created_at),
    CHECK (quantity_micros IS NULL OR (typeof(quantity_micros) = 'integer' AND quantity_micros >= 0 AND quantity_micros <= 9000000000000000)),
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
    current_window_revision INTEGER,
    current_execution_revision INTEGER,
    row_version INTEGER NOT NULL,
    state TEXT NOT NULL,
    created_at TEXT NOT NULL,
    retain_until TEXT NOT NULL,
    renewed_at TEXT,
    record_id TEXT,
    record_revision INTEGER,
    PRIMARY KEY (user_id, id),
    CHECK (((record_id IS NULL AND record_revision IS NULL) OR (record_id IS NOT NULL AND record_revision IS NOT NULL))),
    CHECK (dimension IN ('平替', '顺手加法', '进食顺序', '时序节律')),
    CHECK (state IN ('有效', '已删除')),
    CHECK (current_window_revision IS NULL OR (typeof(current_window_revision) = 'integer' AND current_window_revision >= 1)),
    CHECK (current_execution_revision IS NULL OR (typeof(current_execution_revision) = 'integer' AND current_execution_revision >= 1)),
    CHECK (typeof(row_version) = 'integer' AND row_version >= 1),
    CHECK (typeof(created_at) = 'text' AND length(created_at) = 24 AND strftime('%Y-%m-%dT%H:%M:%fZ', created_at) IS NOT NULL AND strftime('%Y-%m-%dT%H:%M:%fZ', created_at) = created_at),
    CHECK (typeof(retain_until) = 'text' AND length(retain_until) = 24 AND strftime('%Y-%m-%dT%H:%M:%fZ', retain_until) IS NOT NULL AND strftime('%Y-%m-%dT%H:%M:%fZ', retain_until) = retain_until),
    CHECK (renewed_at IS NULL OR (typeof(renewed_at) = 'text' AND length(renewed_at) = 24 AND strftime('%Y-%m-%dT%H:%M:%fZ', renewed_at) IS NOT NULL AND strftime('%Y-%m-%dT%H:%M:%fZ', renewed_at) = renewed_at)),
    CHECK (record_revision IS NULL OR (typeof(record_revision) = 'integer' AND record_revision >= 1)),
    CHECK (retain_until >= created_at),
    CHECK (((renewed_at IS NULL AND retain_until <= strftime('%Y-%m-%dT%H:%M:%fZ', created_at, '+180 days')) OR (renewed_at IS NOT NULL AND renewed_at >= created_at AND retain_until <= strftime('%Y-%m-%dT%H:%M:%fZ', renewed_at, '+180 days')))),
    FOREIGN KEY (user_id) REFERENCES user_control (user_id) ON DELETE NO ACTION DEFERRABLE INITIALLY DEFERRED,
    FOREIGN KEY (user_id, record_id, record_revision) REFERENCES meal_revisions (user_id, id, revision) ON DELETE NO ACTION DEFERRABLE INITIALLY DEFERRED,
    FOREIGN KEY (user_id, context_id) REFERENCES context_snapshots (user_id, id) ON DELETE NO ACTION DEFERRABLE INITIALLY DEFERRED,
    FOREIGN KEY (user_id, replacement_of) REFERENCES micro_actions (user_id, id) ON DELETE NO ACTION DEFERRABLE INITIALLY DEFERRED,
    FOREIGN KEY (user_id, planned_meal_id) REFERENCES planned_meals (user_id, id) ON DELETE NO ACTION DEFERRABLE INITIALLY DEFERRED,
    FOREIGN KEY (user_id, id, current_window_revision) REFERENCES action_windows (user_id, action_id, revision) ON DELETE NO ACTION DEFERRABLE INITIALLY DEFERRED,
    FOREIGN KEY (user_id, id, current_execution_revision) REFERENCES execution_revisions (user_id, action_id, revision) ON DELETE NO ACTION DEFERRABLE INITIALLY DEFERRED
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
    confirmed_at TEXT NOT NULL,
    created_at TEXT NOT NULL,
    PRIMARY KEY (user_id, action_id),
    CHECK (decision IN ('采纳', '跳过', '被替代')),
    CHECK (typeof(confirmed_at) = 'text' AND length(confirmed_at) = 24 AND strftime('%Y-%m-%dT%H:%M:%fZ', confirmed_at) IS NOT NULL AND strftime('%Y-%m-%dT%H:%M:%fZ', confirmed_at) = confirmed_at),
    CHECK (typeof(created_at) = 'text' AND length(created_at) = 24 AND strftime('%Y-%m-%dT%H:%M:%fZ', created_at) IS NOT NULL AND strftime('%Y-%m-%dT%H:%M:%fZ', created_at) = created_at),
    FOREIGN KEY (user_id) REFERENCES user_control (user_id) ON DELETE NO ACTION DEFERRABLE INITIALLY DEFERRED,
    FOREIGN KEY (user_id, action_id) REFERENCES micro_actions (user_id, id) ON DELETE NO ACTION DEFERRABLE INITIALLY DEFERRED
);

-- 行动窗口修订（行动与学习）
CREATE TABLE action_windows (
    user_id TEXT NOT NULL,
    action_id TEXT NOT NULL,
    revision INTEGER NOT NULL,
    starts_at TEXT NOT NULL,
    ends_at TEXT NOT NULL,
    timezone TEXT NOT NULL DEFAULT 'Asia/Shanghai',
    reason TEXT NOT NULL,
    confirmed_at TEXT NOT NULL,
    created_at TEXT NOT NULL,
    PRIMARY KEY (user_id, action_id, revision),
    CHECK (ends_at >= starts_at),
    CHECK (timezone = 'Asia/Shanghai'),
    CHECK (typeof(revision) = 'integer' AND revision >= 1),
    CHECK (typeof(starts_at) = 'text' AND length(starts_at) = 24 AND strftime('%Y-%m-%dT%H:%M:%fZ', starts_at) IS NOT NULL AND strftime('%Y-%m-%dT%H:%M:%fZ', starts_at) = starts_at),
    CHECK (typeof(ends_at) = 'text' AND length(ends_at) = 24 AND strftime('%Y-%m-%dT%H:%M:%fZ', ends_at) IS NOT NULL AND strftime('%Y-%m-%dT%H:%M:%fZ', ends_at) = ends_at),
    CHECK (typeof(confirmed_at) = 'text' AND length(confirmed_at) = 24 AND strftime('%Y-%m-%dT%H:%M:%fZ', confirmed_at) IS NOT NULL AND strftime('%Y-%m-%dT%H:%M:%fZ', confirmed_at) = confirmed_at),
    CHECK (typeof(created_at) = 'text' AND length(created_at) = 24 AND strftime('%Y-%m-%dT%H:%M:%fZ', created_at) IS NOT NULL AND strftime('%Y-%m-%dT%H:%M:%fZ', created_at) = created_at),
    FOREIGN KEY (user_id) REFERENCES user_control (user_id) ON DELETE NO ACTION DEFERRABLE INITIALLY DEFERRED,
    FOREIGN KEY (user_id, action_id) REFERENCES action_decisions (user_id, action_id) ON DELETE NO ACTION DEFERRABLE INITIALLY DEFERRED
);
CREATE INDEX ix_action_windows_0 ON action_windows (user_id, ends_at);

-- 执行自述修订（行动与学习）
CREATE TABLE execution_revisions (
    user_id TEXT NOT NULL,
    action_id TEXT NOT NULL,
    revision INTEGER NOT NULL,
    execution_state TEXT NOT NULL,
    execution_date TEXT,
    reported_at TEXT NOT NULL,
    note TEXT,
    confirmed_at TEXT NOT NULL,
    created_at TEXT NOT NULL,
    PRIMARY KEY (user_id, action_id, revision),
    CHECK (execution_state IN ('完成', '部分', '未完成', '撤回为不确定')),
    CHECK (((execution_state = '撤回为不确定' AND execution_date IS NULL) OR (execution_state <> '撤回为不确定' AND execution_date IS NOT NULL))),
    CHECK (typeof(revision) = 'integer' AND revision >= 1),
    CHECK (execution_date IS NULL OR (typeof(execution_date) = 'text' AND length(execution_date) = 10 AND date(execution_date, '+0 days') IS NOT NULL AND date(execution_date, '+0 days') = execution_date)),
    CHECK (typeof(reported_at) = 'text' AND length(reported_at) = 24 AND strftime('%Y-%m-%dT%H:%M:%fZ', reported_at) IS NOT NULL AND strftime('%Y-%m-%dT%H:%M:%fZ', reported_at) = reported_at),
    CHECK (typeof(confirmed_at) = 'text' AND length(confirmed_at) = 24 AND strftime('%Y-%m-%dT%H:%M:%fZ', confirmed_at) IS NOT NULL AND strftime('%Y-%m-%dT%H:%M:%fZ', confirmed_at) = confirmed_at),
    CHECK (typeof(created_at) = 'text' AND length(created_at) = 24 AND strftime('%Y-%m-%dT%H:%M:%fZ', created_at) IS NOT NULL AND strftime('%Y-%m-%dT%H:%M:%fZ', created_at) = created_at),
    FOREIGN KEY (user_id) REFERENCES user_control (user_id) ON DELETE NO ACTION DEFERRABLE INITIALLY DEFERRED,
    FOREIGN KEY (user_id, action_id) REFERENCES action_decisions (user_id, action_id) ON DELETE NO ACTION DEFERRABLE INITIALLY DEFERRED
);
CREATE INDEX ix_execution_revisions_0 ON execution_revisions (user_id, execution_date, execution_state);

-- 提醒与回应历史（行动与学习）
CREATE TABLE reminder_events (
    user_id TEXT NOT NULL,
    id TEXT NOT NULL,
    action_id TEXT NOT NULL,
    scheduled_at TEXT NOT NULL,
    sent_at TEXT,
    responded_at TEXT,
    outcome TEXT NOT NULL,
    authorization_epoch INTEGER NOT NULL,
    created_at TEXT NOT NULL,
    retain_until TEXT NOT NULL,
    renewed_at TEXT,
    PRIMARY KEY (user_id, id),
    CHECK (outcome IN ('待发送', '已发送', '已取消', '失败')),
    CHECK (typeof(scheduled_at) = 'text' AND length(scheduled_at) = 24 AND strftime('%Y-%m-%dT%H:%M:%fZ', scheduled_at) IS NOT NULL AND strftime('%Y-%m-%dT%H:%M:%fZ', scheduled_at) = scheduled_at),
    CHECK (sent_at IS NULL OR (typeof(sent_at) = 'text' AND length(sent_at) = 24 AND strftime('%Y-%m-%dT%H:%M:%fZ', sent_at) IS NOT NULL AND strftime('%Y-%m-%dT%H:%M:%fZ', sent_at) = sent_at)),
    CHECK (responded_at IS NULL OR (typeof(responded_at) = 'text' AND length(responded_at) = 24 AND strftime('%Y-%m-%dT%H:%M:%fZ', responded_at) IS NOT NULL AND strftime('%Y-%m-%dT%H:%M:%fZ', responded_at) = responded_at)),
    CHECK (typeof(authorization_epoch) = 'integer' AND authorization_epoch >= 1),
    CHECK (typeof(created_at) = 'text' AND length(created_at) = 24 AND strftime('%Y-%m-%dT%H:%M:%fZ', created_at) IS NOT NULL AND strftime('%Y-%m-%dT%H:%M:%fZ', created_at) = created_at),
    CHECK (typeof(retain_until) = 'text' AND length(retain_until) = 24 AND strftime('%Y-%m-%dT%H:%M:%fZ', retain_until) IS NOT NULL AND strftime('%Y-%m-%dT%H:%M:%fZ', retain_until) = retain_until),
    CHECK (renewed_at IS NULL OR (typeof(renewed_at) = 'text' AND length(renewed_at) = 24 AND strftime('%Y-%m-%dT%H:%M:%fZ', renewed_at) IS NOT NULL AND strftime('%Y-%m-%dT%H:%M:%fZ', renewed_at) = renewed_at)),
    CHECK (retain_until >= created_at),
    CHECK (((renewed_at IS NULL AND retain_until <= strftime('%Y-%m-%dT%H:%M:%fZ', created_at, '+180 days')) OR (renewed_at IS NOT NULL AND renewed_at >= created_at AND retain_until <= strftime('%Y-%m-%dT%H:%M:%fZ', renewed_at, '+180 days')))),
    FOREIGN KEY (user_id) REFERENCES user_control (user_id) ON DELETE NO ACTION DEFERRABLE INITIALLY DEFERRED,
    FOREIGN KEY (user_id, action_id) REFERENCES action_decisions (user_id, action_id) ON DELETE NO ACTION DEFERRABLE INITIALLY DEFERRED
);
CREATE INDEX ix_reminder_events_0 ON reminder_events (user_id, action_id);
CREATE INDEX ix_reminder_events_1 ON reminder_events (user_id, scheduled_at);
CREATE INDEX ix_reminder_events_2 ON reminder_events (retain_until);

-- 交互与提醒状态（行动与学习）
CREATE TABLE interaction_settings (
    user_id TEXT NOT NULL,
    row_version INTEGER NOT NULL,
    unanswered_count INTEGER NOT NULL,
    backoff_until TEXT,
    companion_enabled INTEGER NOT NULL,
    collection_enabled INTEGER NOT NULL,
    calibration_enabled INTEGER NOT NULL,
    ranking_version TEXT NOT NULL,
    ranking_parameters TEXT NOT NULL,
    created_at TEXT NOT NULL,
    retain_until TEXT NOT NULL,
    renewed_at TEXT,
    PRIMARY KEY (user_id),
    CHECK (typeof(row_version) = 'integer' AND row_version >= 1),
    CHECK (typeof(unanswered_count) = 'integer' AND unanswered_count >= 0),
    CHECK (backoff_until IS NULL OR (typeof(backoff_until) = 'text' AND length(backoff_until) = 24 AND strftime('%Y-%m-%dT%H:%M:%fZ', backoff_until) IS NOT NULL AND strftime('%Y-%m-%dT%H:%M:%fZ', backoff_until) = backoff_until)),
    CHECK (typeof(companion_enabled) = 'integer' AND companion_enabled IN (0, 1)),
    CHECK (typeof(collection_enabled) = 'integer' AND collection_enabled IN (0, 1)),
    CHECK (typeof(calibration_enabled) = 'integer' AND calibration_enabled IN (0, 1)),
    CHECK (json_valid(ranking_parameters)),
    CHECK (typeof(created_at) = 'text' AND length(created_at) = 24 AND strftime('%Y-%m-%dT%H:%M:%fZ', created_at) IS NOT NULL AND strftime('%Y-%m-%dT%H:%M:%fZ', created_at) = created_at),
    CHECK (typeof(retain_until) = 'text' AND length(retain_until) = 24 AND strftime('%Y-%m-%dT%H:%M:%fZ', retain_until) IS NOT NULL AND strftime('%Y-%m-%dT%H:%M:%fZ', retain_until) = retain_until),
    CHECK (renewed_at IS NULL OR (typeof(renewed_at) = 'text' AND length(renewed_at) = 24 AND strftime('%Y-%m-%dT%H:%M:%fZ', renewed_at) IS NOT NULL AND strftime('%Y-%m-%dT%H:%M:%fZ', renewed_at) = renewed_at)),
    CHECK (retain_until >= created_at),
    CHECK (((renewed_at IS NULL AND retain_until <= strftime('%Y-%m-%dT%H:%M:%fZ', created_at, '+180 days')) OR (renewed_at IS NOT NULL AND renewed_at >= created_at AND retain_until <= strftime('%Y-%m-%dT%H:%M:%fZ', renewed_at, '+180 days')))),
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
    explanation TEXT NOT NULL,
    cooldown_until TEXT,
    created_at TEXT NOT NULL,
    retain_until TEXT NOT NULL,
    renewed_at TEXT,
    PRIMARY KEY (user_id, id),
    CHECK (event_kind IN ('采纳', '换一个', '暂不需要', '规则调整')),
    CHECK (json_valid(explanation)),
    CHECK (cooldown_until IS NULL OR (typeof(cooldown_until) = 'text' AND length(cooldown_until) = 24 AND strftime('%Y-%m-%dT%H:%M:%fZ', cooldown_until) IS NOT NULL AND strftime('%Y-%m-%dT%H:%M:%fZ', cooldown_until) = cooldown_until)),
    CHECK (typeof(created_at) = 'text' AND length(created_at) = 24 AND strftime('%Y-%m-%dT%H:%M:%fZ', created_at) IS NOT NULL AND strftime('%Y-%m-%dT%H:%M:%fZ', created_at) = created_at),
    CHECK (typeof(retain_until) = 'text' AND length(retain_until) = 24 AND strftime('%Y-%m-%dT%H:%M:%fZ', retain_until) IS NOT NULL AND strftime('%Y-%m-%dT%H:%M:%fZ', retain_until) = retain_until),
    CHECK (renewed_at IS NULL OR (typeof(renewed_at) = 'text' AND length(renewed_at) = 24 AND strftime('%Y-%m-%dT%H:%M:%fZ', renewed_at) IS NOT NULL AND strftime('%Y-%m-%dT%H:%M:%fZ', renewed_at) = renewed_at)),
    CHECK (retain_until >= created_at),
    CHECK (((renewed_at IS NULL AND retain_until <= strftime('%Y-%m-%dT%H:%M:%fZ', created_at, '+180 days')) OR (renewed_at IS NOT NULL AND renewed_at >= created_at AND retain_until <= strftime('%Y-%m-%dT%H:%M:%fZ', renewed_at, '+180 days')))),
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
    hypothesis TEXT NOT NULL,
    state TEXT NOT NULL,
    authorization_epoch INTEGER NOT NULL,
    range_start TEXT NOT NULL,
    range_end TEXT NOT NULL,
    confirmed_at TEXT,
    created_at TEXT NOT NULL,
    retain_until TEXT NOT NULL,
    renewed_at TEXT,
    PRIMARY KEY (user_id, id),
    CHECK (candidate_kind IN ('稳定偏好', '情境线索')),
    CHECK (state IN ('待核对', '已确认', '已拒绝', '已到期')),
    CHECK (range_end >= range_start),
    CHECK (json_valid(hypothesis)),
    CHECK (typeof(authorization_epoch) = 'integer' AND authorization_epoch >= 1),
    CHECK (typeof(range_start) = 'text' AND length(range_start) = 10 AND date(range_start, '+0 days') IS NOT NULL AND date(range_start, '+0 days') = range_start),
    CHECK (typeof(range_end) = 'text' AND length(range_end) = 10 AND date(range_end, '+0 days') IS NOT NULL AND date(range_end, '+0 days') = range_end),
    CHECK (confirmed_at IS NULL OR (typeof(confirmed_at) = 'text' AND length(confirmed_at) = 24 AND strftime('%Y-%m-%dT%H:%M:%fZ', confirmed_at) IS NOT NULL AND strftime('%Y-%m-%dT%H:%M:%fZ', confirmed_at) = confirmed_at)),
    CHECK (typeof(created_at) = 'text' AND length(created_at) = 24 AND strftime('%Y-%m-%dT%H:%M:%fZ', created_at) IS NOT NULL AND strftime('%Y-%m-%dT%H:%M:%fZ', created_at) = created_at),
    CHECK (typeof(retain_until) = 'text' AND length(retain_until) = 24 AND strftime('%Y-%m-%dT%H:%M:%fZ', retain_until) IS NOT NULL AND strftime('%Y-%m-%dT%H:%M:%fZ', retain_until) = retain_until),
    CHECK (renewed_at IS NULL OR (typeof(renewed_at) = 'text' AND length(renewed_at) = 24 AND strftime('%Y-%m-%dT%H:%M:%fZ', renewed_at) IS NOT NULL AND strftime('%Y-%m-%dT%H:%M:%fZ', renewed_at) = renewed_at)),
    CHECK (retain_until >= created_at),
    CHECK (((renewed_at IS NULL AND retain_until <= strftime('%Y-%m-%dT%H:%M:%fZ', created_at, '+180 days')) OR (renewed_at IS NOT NULL AND renewed_at >= created_at AND retain_until <= strftime('%Y-%m-%dT%H:%M:%fZ', renewed_at, '+180 days')))),
    FOREIGN KEY (user_id) REFERENCES user_control (user_id) ON DELETE NO ACTION DEFERRABLE INITIALLY DEFERRED
);
CREATE INDEX ix_learning_candidates_0 ON learning_candidates (retain_until);

-- 学习证据引用（行动与学习）
CREATE TABLE learning_evidence (
    user_id TEXT NOT NULL,
    id TEXT NOT NULL,
    candidate_id TEXT NOT NULL,
    action_id TEXT,
    execution_revision INTEGER,
    record_id TEXT,
    record_revision INTEGER,
    created_at TEXT NOT NULL,
    PRIMARY KEY (user_id, id),
    CHECK (((action_id IS NOT NULL AND execution_revision IS NOT NULL AND record_id IS NULL AND record_revision IS NULL) OR (action_id IS NULL AND execution_revision IS NULL AND record_id IS NOT NULL AND record_revision IS NOT NULL))),
    CHECK (execution_revision IS NULL OR (typeof(execution_revision) = 'integer' AND execution_revision >= 1)),
    CHECK (record_revision IS NULL OR (typeof(record_revision) = 'integer' AND record_revision >= 1)),
    CHECK (typeof(created_at) = 'text' AND length(created_at) = 24 AND strftime('%Y-%m-%dT%H:%M:%fZ', created_at) IS NOT NULL AND strftime('%Y-%m-%dT%H:%M:%fZ', created_at) = created_at),
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
    revision INTEGER NOT NULL,
    candidate_id TEXT NOT NULL,
    rule_content TEXT NOT NULL,
    state TEXT NOT NULL,
    confirmed_at TEXT NOT NULL,
    created_at TEXT NOT NULL,
    retain_until TEXT NOT NULL,
    renewed_at TEXT,
    PRIMARY KEY (user_id, id, revision),
    CHECK (state IN ('有效', '已停用', '已删除')),
    CHECK (typeof(revision) = 'integer' AND revision >= 1),
    CHECK (json_valid(rule_content)),
    CHECK (typeof(confirmed_at) = 'text' AND length(confirmed_at) = 24 AND strftime('%Y-%m-%dT%H:%M:%fZ', confirmed_at) IS NOT NULL AND strftime('%Y-%m-%dT%H:%M:%fZ', confirmed_at) = confirmed_at),
    CHECK (typeof(created_at) = 'text' AND length(created_at) = 24 AND strftime('%Y-%m-%dT%H:%M:%fZ', created_at) IS NOT NULL AND strftime('%Y-%m-%dT%H:%M:%fZ', created_at) = created_at),
    CHECK (typeof(retain_until) = 'text' AND length(retain_until) = 24 AND strftime('%Y-%m-%dT%H:%M:%fZ', retain_until) IS NOT NULL AND strftime('%Y-%m-%dT%H:%M:%fZ', retain_until) = retain_until),
    CHECK (renewed_at IS NULL OR (typeof(renewed_at) = 'text' AND length(renewed_at) = 24 AND strftime('%Y-%m-%dT%H:%M:%fZ', renewed_at) IS NOT NULL AND strftime('%Y-%m-%dT%H:%M:%fZ', renewed_at) = renewed_at)),
    CHECK (retain_until >= created_at),
    CHECK (((renewed_at IS NULL AND retain_until <= strftime('%Y-%m-%dT%H:%M:%fZ', created_at, '+180 days')) OR (renewed_at IS NOT NULL AND renewed_at >= created_at AND retain_until <= strftime('%Y-%m-%dT%H:%M:%fZ', renewed_at, '+180 days')))),
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
    revision INTEGER NOT NULL,
    answer TEXT,
    state TEXT NOT NULL,
    confirmed_at TEXT NOT NULL,
    created_at TEXT NOT NULL,
    retain_until TEXT NOT NULL,
    renewed_at TEXT,
    PRIMARY KEY (user_id, question_key, revision),
    CHECK (state IN ('已确认', '已删除')),
    CHECK (((state = '已确认' AND answer IS NOT NULL) OR (state = '已删除' AND answer IS NULL))),
    CHECK (typeof(revision) = 'integer' AND revision >= 1),
    CHECK (answer IS NULL OR json_valid(answer)),
    CHECK (typeof(confirmed_at) = 'text' AND length(confirmed_at) = 24 AND strftime('%Y-%m-%dT%H:%M:%fZ', confirmed_at) IS NOT NULL AND strftime('%Y-%m-%dT%H:%M:%fZ', confirmed_at) = confirmed_at),
    CHECK (typeof(created_at) = 'text' AND length(created_at) = 24 AND strftime('%Y-%m-%dT%H:%M:%fZ', created_at) IS NOT NULL AND strftime('%Y-%m-%dT%H:%M:%fZ', created_at) = created_at),
    CHECK (typeof(retain_until) = 'text' AND length(retain_until) = 24 AND strftime('%Y-%m-%dT%H:%M:%fZ', retain_until) IS NOT NULL AND strftime('%Y-%m-%dT%H:%M:%fZ', retain_until) = retain_until),
    CHECK (renewed_at IS NULL OR (typeof(renewed_at) = 'text' AND length(renewed_at) = 24 AND strftime('%Y-%m-%dT%H:%M:%fZ', renewed_at) IS NOT NULL AND strftime('%Y-%m-%dT%H:%M:%fZ', renewed_at) = renewed_at)),
    CHECK (retain_until >= created_at),
    CHECK (((renewed_at IS NULL AND retain_until <= strftime('%Y-%m-%dT%H:%M:%fZ', created_at, '+180 days')) OR (renewed_at IS NOT NULL AND renewed_at >= created_at AND retain_until <= strftime('%Y-%m-%dT%H:%M:%fZ', renewed_at, '+180 days')))),
    FOREIGN KEY (user_id) REFERENCES user_control (user_id) ON DELETE NO ACTION DEFERRABLE INITIALLY DEFERRED
);
CREATE INDEX ix_calibration_revisions_0 ON calibration_revisions (retain_until);

-- 预期餐次版本（实际与回顾）
CREATE TABLE expected_schedules (
    user_id TEXT NOT NULL,
    week_start TEXT NOT NULL,
    revision INTEGER NOT NULL,
    confirmed_at TEXT NOT NULL,
    created_at TEXT NOT NULL,
    retain_until TEXT NOT NULL,
    renewed_at TEXT,
    PRIMARY KEY (user_id, week_start, revision),
    CHECK (typeof(week_start) = 'text' AND length(week_start) = 10 AND date(week_start, '+0 days') IS NOT NULL AND date(week_start, '+0 days') = week_start),
    CHECK (typeof(revision) = 'integer' AND revision >= 1),
    CHECK (typeof(confirmed_at) = 'text' AND length(confirmed_at) = 24 AND strftime('%Y-%m-%dT%H:%M:%fZ', confirmed_at) IS NOT NULL AND strftime('%Y-%m-%dT%H:%M:%fZ', confirmed_at) = confirmed_at),
    CHECK (typeof(created_at) = 'text' AND length(created_at) = 24 AND strftime('%Y-%m-%dT%H:%M:%fZ', created_at) IS NOT NULL AND strftime('%Y-%m-%dT%H:%M:%fZ', created_at) = created_at),
    CHECK (typeof(retain_until) = 'text' AND length(retain_until) = 24 AND strftime('%Y-%m-%dT%H:%M:%fZ', retain_until) IS NOT NULL AND strftime('%Y-%m-%dT%H:%M:%fZ', retain_until) = retain_until),
    CHECK (renewed_at IS NULL OR (typeof(renewed_at) = 'text' AND length(renewed_at) = 24 AND strftime('%Y-%m-%dT%H:%M:%fZ', renewed_at) IS NOT NULL AND strftime('%Y-%m-%dT%H:%M:%fZ', renewed_at) = renewed_at)),
    CHECK (retain_until >= created_at),
    CHECK (((renewed_at IS NULL AND retain_until <= strftime('%Y-%m-%dT%H:%M:%fZ', created_at, '+180 days')) OR (renewed_at IS NOT NULL AND renewed_at >= created_at AND retain_until <= strftime('%Y-%m-%dT%H:%M:%fZ', renewed_at, '+180 days')))),
    CHECK (strftime('%w', week_start) = '1'),
    FOREIGN KEY (user_id) REFERENCES user_control (user_id) ON DELETE NO ACTION DEFERRABLE INITIALLY DEFERRED
);
CREATE INDEX ix_expected_schedules_0 ON expected_schedules (retain_until);

-- 预期餐次槽位（实际与回顾）
CREATE TABLE expected_slots (
    user_id TEXT NOT NULL,
    week_start TEXT NOT NULL,
    schedule_revision INTEGER NOT NULL,
    meal_date TEXT NOT NULL,
    meal_slot TEXT NOT NULL,
    created_at TEXT NOT NULL,
    PRIMARY KEY (user_id, week_start, schedule_revision, meal_date, meal_slot),
    CHECK (meal_slot IN ('早餐', '午餐', '晚餐', '加餐')),
    CHECK (typeof(week_start) = 'text' AND length(week_start) = 10 AND date(week_start, '+0 days') IS NOT NULL AND date(week_start, '+0 days') = week_start),
    CHECK (typeof(schedule_revision) = 'integer' AND schedule_revision >= 1),
    CHECK (typeof(meal_date) = 'text' AND length(meal_date) = 10 AND date(meal_date, '+0 days') IS NOT NULL AND date(meal_date, '+0 days') = meal_date),
    CHECK (typeof(created_at) = 'text' AND length(created_at) = 24 AND strftime('%Y-%m-%dT%H:%M:%fZ', created_at) IS NOT NULL AND strftime('%Y-%m-%dT%H:%M:%fZ', created_at) = created_at),
    CHECK (strftime('%w', week_start) = '1'),
    CHECK (meal_date >= week_start AND meal_date <= date(week_start, '+6 days')),
    FOREIGN KEY (user_id) REFERENCES user_control (user_id) ON DELETE NO ACTION DEFERRABLE INITIALLY DEFERRED,
    FOREIGN KEY (user_id, week_start, schedule_revision) REFERENCES expected_schedules (user_id, week_start, revision) ON DELETE NO ACTION DEFERRABLE INITIALLY DEFERRED
);

-- 恢复周期确认（实际与回顾）
CREATE TABLE recovery_episodes (
    user_id TEXT NOT NULL,
    id TEXT NOT NULL,
    row_version INTEGER NOT NULL,
    deviation_at TEXT,
    return_at TEXT,
    reason TEXT NOT NULL,
    confirmed_at TEXT NOT NULL,
    created_at TEXT NOT NULL,
    retain_until TEXT NOT NULL,
    renewed_at TEXT,
    PRIMARY KEY (user_id, id),
    CHECK (return_at IS NULL OR (deviation_at IS NOT NULL AND return_at >= deviation_at)),
    CHECK (typeof(row_version) = 'integer' AND row_version >= 1),
    CHECK (deviation_at IS NULL OR (typeof(deviation_at) = 'text' AND length(deviation_at) = 24 AND strftime('%Y-%m-%dT%H:%M:%fZ', deviation_at) IS NOT NULL AND strftime('%Y-%m-%dT%H:%M:%fZ', deviation_at) = deviation_at)),
    CHECK (return_at IS NULL OR (typeof(return_at) = 'text' AND length(return_at) = 24 AND strftime('%Y-%m-%dT%H:%M:%fZ', return_at) IS NOT NULL AND strftime('%Y-%m-%dT%H:%M:%fZ', return_at) = return_at)),
    CHECK (typeof(confirmed_at) = 'text' AND length(confirmed_at) = 24 AND strftime('%Y-%m-%dT%H:%M:%fZ', confirmed_at) IS NOT NULL AND strftime('%Y-%m-%dT%H:%M:%fZ', confirmed_at) = confirmed_at),
    CHECK (typeof(created_at) = 'text' AND length(created_at) = 24 AND strftime('%Y-%m-%dT%H:%M:%fZ', created_at) IS NOT NULL AND strftime('%Y-%m-%dT%H:%M:%fZ', created_at) = created_at),
    CHECK (typeof(retain_until) = 'text' AND length(retain_until) = 24 AND strftime('%Y-%m-%dT%H:%M:%fZ', retain_until) IS NOT NULL AND strftime('%Y-%m-%dT%H:%M:%fZ', retain_until) = retain_until),
    CHECK (renewed_at IS NULL OR (typeof(renewed_at) = 'text' AND length(renewed_at) = 24 AND strftime('%Y-%m-%dT%H:%M:%fZ', renewed_at) IS NOT NULL AND strftime('%Y-%m-%dT%H:%M:%fZ', renewed_at) = renewed_at)),
    CHECK (retain_until >= created_at),
    CHECK (((renewed_at IS NULL AND retain_until <= strftime('%Y-%m-%dT%H:%M:%fZ', created_at, '+180 days')) OR (renewed_at IS NOT NULL AND renewed_at >= created_at AND retain_until <= strftime('%Y-%m-%dT%H:%M:%fZ', renewed_at, '+180 days')))),
    FOREIGN KEY (user_id) REFERENCES user_control (user_id) ON DELETE NO ACTION DEFERRABLE INITIALLY DEFERRED
);
CREATE INDEX ix_recovery_episodes_0 ON recovery_episodes (retain_until);

-- 恢复排除时段（实际与回顾）
CREATE TABLE recovery_exclusions (
    user_id TEXT NOT NULL,
    id TEXT NOT NULL,
    episode_id TEXT NOT NULL,
    starts_at TEXT NOT NULL,
    ends_at TEXT NOT NULL,
    reason TEXT NOT NULL,
    confirmed_at TEXT NOT NULL,
    created_at TEXT NOT NULL,
    PRIMARY KEY (user_id, id),
    CHECK (ends_at >= starts_at),
    CHECK (typeof(starts_at) = 'text' AND length(starts_at) = 24 AND strftime('%Y-%m-%dT%H:%M:%fZ', starts_at) IS NOT NULL AND strftime('%Y-%m-%dT%H:%M:%fZ', starts_at) = starts_at),
    CHECK (typeof(ends_at) = 'text' AND length(ends_at) = 24 AND strftime('%Y-%m-%dT%H:%M:%fZ', ends_at) IS NOT NULL AND strftime('%Y-%m-%dT%H:%M:%fZ', ends_at) = ends_at),
    CHECK (typeof(confirmed_at) = 'text' AND length(confirmed_at) = 24 AND strftime('%Y-%m-%dT%H:%M:%fZ', confirmed_at) IS NOT NULL AND strftime('%Y-%m-%dT%H:%M:%fZ', confirmed_at) = confirmed_at),
    CHECK (typeof(created_at) = 'text' AND length(created_at) = 24 AND strftime('%Y-%m-%dT%H:%M:%fZ', created_at) IS NOT NULL AND strftime('%Y-%m-%dT%H:%M:%fZ', created_at) = created_at),
    FOREIGN KEY (user_id) REFERENCES user_control (user_id) ON DELETE NO ACTION DEFERRABLE INITIALLY DEFERRED,
    FOREIGN KEY (user_id, episode_id) REFERENCES recovery_episodes (user_id, id) ON DELETE NO ACTION DEFERRABLE INITIALLY DEFERRED
);
CREATE INDEX ix_recovery_exclusions_0 ON recovery_exclusions (user_id, episode_id);

-- 连续周呈现修订（实际与回顾）
CREATE TABLE week_presentations (
    user_id TEXT NOT NULL,
    week_start TEXT NOT NULL,
    revision INTEGER NOT NULL,
    override_kind TEXT NOT NULL,
    reason TEXT NOT NULL,
    confirmed_at TEXT NOT NULL,
    created_at TEXT NOT NULL,
    retain_until TEXT NOT NULL,
    renewed_at TEXT,
    PRIMARY KEY (user_id, week_start, revision),
    CHECK (override_kind IN ('冻结', '取消冻结')),
    CHECK (typeof(week_start) = 'text' AND length(week_start) = 10 AND date(week_start, '+0 days') IS NOT NULL AND date(week_start, '+0 days') = week_start),
    CHECK (typeof(revision) = 'integer' AND revision >= 1),
    CHECK (typeof(confirmed_at) = 'text' AND length(confirmed_at) = 24 AND strftime('%Y-%m-%dT%H:%M:%fZ', confirmed_at) IS NOT NULL AND strftime('%Y-%m-%dT%H:%M:%fZ', confirmed_at) = confirmed_at),
    CHECK (typeof(created_at) = 'text' AND length(created_at) = 24 AND strftime('%Y-%m-%dT%H:%M:%fZ', created_at) IS NOT NULL AND strftime('%Y-%m-%dT%H:%M:%fZ', created_at) = created_at),
    CHECK (typeof(retain_until) = 'text' AND length(retain_until) = 24 AND strftime('%Y-%m-%dT%H:%M:%fZ', retain_until) IS NOT NULL AND strftime('%Y-%m-%dT%H:%M:%fZ', retain_until) = retain_until),
    CHECK (renewed_at IS NULL OR (typeof(renewed_at) = 'text' AND length(renewed_at) = 24 AND strftime('%Y-%m-%dT%H:%M:%fZ', renewed_at) IS NOT NULL AND strftime('%Y-%m-%dT%H:%M:%fZ', renewed_at) = renewed_at)),
    CHECK (retain_until >= created_at),
    CHECK (((renewed_at IS NULL AND retain_until <= strftime('%Y-%m-%dT%H:%M:%fZ', created_at, '+180 days')) OR (renewed_at IS NOT NULL AND renewed_at >= created_at AND retain_until <= strftime('%Y-%m-%dT%H:%M:%fZ', renewed_at, '+180 days')))),
    CHECK (strftime('%w', week_start) = '1'),
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
    authorization_epoch INTEGER NOT NULL,
    data_revision INTEGER NOT NULL,
    result_refs TEXT NOT NULL,
    issued_at TEXT NOT NULL,
    expires_at TEXT NOT NULL,
    created_at TEXT NOT NULL,
    PRIMARY KEY (user_id, operation_key),
    UNIQUE (user_id, commit_id),
    CHECK (typeof(authorization_epoch) = 'integer' AND authorization_epoch >= 1),
    CHECK (typeof(data_revision) = 'integer' AND data_revision >= 1),
    CHECK (json_valid(result_refs)),
    CHECK (typeof(issued_at) = 'text' AND length(issued_at) = 24 AND strftime('%Y-%m-%dT%H:%M:%fZ', issued_at) IS NOT NULL AND strftime('%Y-%m-%dT%H:%M:%fZ', issued_at) = issued_at),
    CHECK (typeof(expires_at) = 'text' AND length(expires_at) = 24 AND strftime('%Y-%m-%dT%H:%M:%fZ', expires_at) IS NOT NULL AND strftime('%Y-%m-%dT%H:%M:%fZ', expires_at) = expires_at),
    CHECK (typeof(created_at) = 'text' AND length(created_at) = 24 AND strftime('%Y-%m-%dT%H:%M:%fZ', created_at) IS NOT NULL AND strftime('%Y-%m-%dT%H:%M:%fZ', created_at) = created_at),
    CHECK (expires_at >= created_at),
    CHECK (expires_at <= strftime('%Y-%m-%dT%H:%M:%fZ', created_at, '+180 days')),
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
    object_revision INTEGER,
    reason_code TEXT,
    created_at TEXT NOT NULL,
    retain_until TEXT NOT NULL,
    renewed_at TEXT,
    PRIMARY KEY (user_id, id),
    CHECK (object_revision IS NULL OR (typeof(object_revision) = 'integer' AND object_revision >= 1)),
    CHECK (typeof(created_at) = 'text' AND length(created_at) = 24 AND strftime('%Y-%m-%dT%H:%M:%fZ', created_at) IS NOT NULL AND strftime('%Y-%m-%dT%H:%M:%fZ', created_at) = created_at),
    CHECK (typeof(retain_until) = 'text' AND length(retain_until) = 24 AND strftime('%Y-%m-%dT%H:%M:%fZ', retain_until) IS NOT NULL AND strftime('%Y-%m-%dT%H:%M:%fZ', retain_until) = retain_until),
    CHECK (renewed_at IS NULL OR (typeof(renewed_at) = 'text' AND length(renewed_at) = 24 AND strftime('%Y-%m-%dT%H:%M:%fZ', renewed_at) IS NOT NULL AND strftime('%Y-%m-%dT%H:%M:%fZ', renewed_at) = renewed_at)),
    CHECK (retain_until >= created_at),
    CHECK (((renewed_at IS NULL AND retain_until <= strftime('%Y-%m-%dT%H:%M:%fZ', created_at, '+180 days')) OR (renewed_at IS NOT NULL AND renewed_at >= created_at AND retain_until <= strftime('%Y-%m-%dT%H:%M:%fZ', renewed_at, '+180 days')))),
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
    scope_manifest TEXT NOT NULL,
    requested_at TEXT NOT NULL,
    deadline_at TEXT NOT NULL,
    completed_at TEXT,
    artifact_key TEXT,
    artifact_expires_at TEXT,
    failure_code TEXT,
    created_at TEXT NOT NULL,
    PRIMARY KEY (user_id, id),
    CHECK (job_kind IN ('导出', '主动删除', '期限清理')),
    CHECK (state IN ('待处理', '处理中', '已完成', '失败')),
    CHECK (json_valid(scope_manifest)),
    CHECK (typeof(requested_at) = 'text' AND length(requested_at) = 24 AND strftime('%Y-%m-%dT%H:%M:%fZ', requested_at) IS NOT NULL AND strftime('%Y-%m-%dT%H:%M:%fZ', requested_at) = requested_at),
    CHECK (typeof(deadline_at) = 'text' AND length(deadline_at) = 24 AND strftime('%Y-%m-%dT%H:%M:%fZ', deadline_at) IS NOT NULL AND strftime('%Y-%m-%dT%H:%M:%fZ', deadline_at) = deadline_at),
    CHECK (completed_at IS NULL OR (typeof(completed_at) = 'text' AND length(completed_at) = 24 AND strftime('%Y-%m-%dT%H:%M:%fZ', completed_at) IS NOT NULL AND strftime('%Y-%m-%dT%H:%M:%fZ', completed_at) = completed_at)),
    CHECK (artifact_expires_at IS NULL OR (typeof(artifact_expires_at) = 'text' AND length(artifact_expires_at) = 24 AND strftime('%Y-%m-%dT%H:%M:%fZ', artifact_expires_at) IS NOT NULL AND strftime('%Y-%m-%dT%H:%M:%fZ', artifact_expires_at) = artifact_expires_at)),
    CHECK (typeof(created_at) = 'text' AND length(created_at) = 24 AND strftime('%Y-%m-%dT%H:%M:%fZ', created_at) IS NOT NULL AND strftime('%Y-%m-%dT%H:%M:%fZ', created_at) = created_at),
    CHECK (deadline_at >= requested_at),
    CHECK (state <> '已完成' OR completed_at IS NOT NULL),
    CHECK (job_kind <> '主动删除' OR deadline_at <= strftime('%Y-%m-%dT%H:%M:%fZ', requested_at, '+1 days')),
    FOREIGN KEY (user_id) REFERENCES user_control (user_id) ON DELETE NO ACTION DEFERRABLE INITIALLY DEFERRED
);
CREATE INDEX ix_data_control_jobs_0 ON data_control_jobs (state, deadline_at);
