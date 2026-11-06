CREATE TABLE plans (
    plan_id TEXT PRIMARY KEY,
    user_id TEXT NOT NULL,
    version INTEGER NOT NULL,
    status TEXT NOT NULL CHECK(status IN ('draft','confirmed','superseded','cancelled')),
    payload TEXT NOT NULL,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);
CREATE INDEX plans_user ON plans(user_id, updated_at);
CREATE TABLE shopping_lists (
    list_id TEXT PRIMARY KEY,
    user_id TEXT NOT NULL,
    plan_id TEXT NOT NULL,
    plan_version INTEGER NOT NULL,
    status TEXT NOT NULL CHECK(status IN ('active','stale','cancelled')),
    payload TEXT NOT NULL,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    UNIQUE(plan_id, plan_version)
);
CREATE TABLE inventory_items (
    inventory_id TEXT PRIMARY KEY,
    user_id TEXT NOT NULL,
    ingredient_id TEXT NOT NULL,
    unit TEXT NOT NULL,
    version INTEGER NOT NULL,
    payload TEXT NOT NULL,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    UNIQUE(user_id, ingredient_id, unit)
);
