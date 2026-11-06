CREATE TABLE food_observations (
    observation_id TEXT PRIMARY KEY,
    user_id TEXT NOT NULL,
    task_id TEXT,
    source TEXT NOT NULL,
    source_id TEXT,
    status TEXT NOT NULL CHECK(status IN ('safe','blocked','needs_confirmation')),
    payload TEXT NOT NULL,
    retrieved_at TEXT NOT NULL,
    created_at TEXT NOT NULL
);
CREATE INDEX food_observations_user ON food_observations(user_id, created_at);
CREATE INDEX food_observations_source ON food_observations(source, source_id);
