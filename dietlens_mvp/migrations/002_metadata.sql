ALTER TABLE tasks ADD COLUMN user_id TEXT;
ALTER TABLE tasks ADD COLUMN version INTEGER NOT NULL DEFAULT 1;
ALTER TABLE tasks ADD COLUMN created_at TEXT;
ALTER TABLE tasks ADD COLUMN updated_at TEXT;
UPDATE tasks SET user_id=json_extract(payload, '$.user_id'),
    created_at=strftime('%Y-%m-%dT%H:%M:%f+00:00', 'now'),
    updated_at=strftime('%Y-%m-%dT%H:%M:%f+00:00', 'now');
CREATE INDEX tasks_user ON tasks(user_id);
ALTER TABLE actions ADD COLUMN user_id TEXT;
UPDATE actions SET user_id=json_extract(payload, '$.user_id');
CREATE INDEX actions_user ON actions(user_id);
