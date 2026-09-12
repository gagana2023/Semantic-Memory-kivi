CREATE TABLE IF NOT EXISTS memory_versions (
  id TEXT PRIMARY KEY, memory_id TEXT NOT NULL REFERENCES memories(id), version INTEGER NOT NULL,
  kind TEXT NOT NULL, name TEXT NOT NULL, relation TEXT NOT NULL, value TEXT NOT NULL,
  basis TEXT NOT NULL, status TEXT NOT NULL, action TEXT NOT NULL, created_at TEXT NOT NULL,
  UNIQUE(memory_id, version)
);
CREATE TABLE IF NOT EXISTS memory_actions (
  id TEXT PRIMARY KEY, memory_id TEXT NOT NULL REFERENCES memories(id), action TEXT NOT NULL,
  idempotency_key TEXT NOT NULL UNIQUE, expected_version INTEGER NOT NULL,
  detail_json TEXT NOT NULL, created_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS suppressions (
  id TEXT PRIMARY KEY, memory_id TEXT NOT NULL REFERENCES memories(id), reason TEXT NOT NULL,
  created_at TEXT NOT NULL, UNIQUE(memory_id)
);
CREATE TABLE IF NOT EXISTS memory_tombstones (
  memory_id TEXT PRIMARY KEY, forgotten_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS confirmation_prompts (
  id TEXT PRIMARY KEY, memory_id TEXT NOT NULL REFERENCES memories(id), trace_id TEXT,
  week_start TEXT NOT NULL, created_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS prompt_ledger (
  week_start TEXT PRIMARY KEY, used INTEGER NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_memories_lifecycle ON memories(status,basis,pinned,created_at);
