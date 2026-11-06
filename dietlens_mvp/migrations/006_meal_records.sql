CREATE TABLE meal_records (
    record_id TEXT PRIMARY KEY,
    user_id TEXT NOT NULL,
    version INTEGER NOT NULL,
    status TEXT NOT NULL CHECK(status IN ('active','deleted')),
    payload TEXT NOT NULL,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);
CREATE INDEX meal_records_user ON meal_records(user_id, updated_at);
CREATE TABLE meal_record_versions (
    record_id TEXT NOT NULL,
    version INTEGER NOT NULL,
    user_id TEXT NOT NULL,
    operation_key TEXT NOT NULL,
    payload TEXT NOT NULL,
    created_at TEXT NOT NULL,
    PRIMARY KEY(record_id, version)
);
CREATE INDEX meal_record_versions_user ON meal_record_versions(user_id, created_at);
