CREATE TABLE profile_versions (
    user_id TEXT NOT NULL,
    version INTEGER NOT NULL,
    payload TEXT NOT NULL,
    task_id TEXT,
    operation_key TEXT NOT NULL,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    PRIMARY KEY(user_id, version)
);
INSERT INTO profile_versions(user_id,version,payload,task_id,operation_key,created_at,updated_at)
SELECT user_id, COALESCE(json_extract(payload,'$.version'),1), payload, NULL,
       'migration:legacy-profile', strftime('%Y-%m-%dT%H:%M:%f+00:00','now'),
       strftime('%Y-%m-%dT%H:%M:%f+00:00','now') FROM profiles;
CREATE TABLE profile_drafts (
    task_id TEXT PRIMARY KEY REFERENCES tasks(task_id),
    user_id TEXT NOT NULL,
    payload TEXT NOT NULL
);
CREATE INDEX profile_drafts_user ON profile_drafts(user_id);
CREATE TABLE consents (
    user_id TEXT NOT NULL,
    scope TEXT NOT NULL,
    profile_version INTEGER NOT NULL,
    granted INTEGER NOT NULL CHECK(granted IN (0,1)),
    source TEXT NOT NULL,
    task_id TEXT NOT NULL,
    operation_key TEXT NOT NULL,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    PRIMARY KEY(user_id,scope,profile_version)
);
