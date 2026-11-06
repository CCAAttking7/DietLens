-- Compatible with the original MVP's unversioned SQLite database.
CREATE TABLE IF NOT EXISTS profiles (user_id TEXT PRIMARY KEY, payload TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS tasks (task_id TEXT PRIMARY KEY, payload TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS actions (action_id TEXT PRIMARY KEY, payload TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS events (id INTEGER PRIMARY KEY AUTOINCREMENT, payload TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS operations (operation_key TEXT PRIMARY KEY, payload TEXT NOT NULL);
