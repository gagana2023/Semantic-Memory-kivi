ALTER TABLE memories ADD COLUMN basis TEXT NOT NULL DEFAULT 'stated' CHECK(basis IN ('stated','observed','hypothesis'));
ALTER TABLE memories ADD COLUMN status TEXT NOT NULL DEFAULT 'active' CHECK(status IN ('active','superseded','suppressed'));
ALTER TABLE memories ADD COLUMN pinned INTEGER NOT NULL DEFAULT 0 CHECK(pinned IN (0,1));
CREATE TABLE IF NOT EXISTS permissions (
  singleton INTEGER PRIMARY KEY CHECK(singleton=1), mode TEXT NOT NULL CHECK(mode IN ('anbu','koottu')),
  updated_at TEXT NOT NULL
);
INSERT OR IGNORE INTO permissions(singleton,mode,updated_at) VALUES(1,'anbu',datetime('now'));
CREATE VIRTUAL TABLE IF NOT EXISTS transcript_fts USING fts5(transcript_id UNINDEXED, formatted_text);
CREATE TABLE IF NOT EXISTS internal_events (
  id TEXT PRIMARY KEY, memory_id TEXT NOT NULL REFERENCES memories(id), starts_at TEXT NOT NULL,
  idempotency_key TEXT NOT NULL UNIQUE, status TEXT NOT NULL, created_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS retrieval_candidates (
  trace_id TEXT NOT NULL REFERENCES decision_traces(id), memory_id TEXT NOT NULL REFERENCES memories(id),
  rank INTEGER NOT NULL, disposition TEXT NOT NULL, legs_json TEXT NOT NULL, PRIMARY KEY(trace_id,memory_id)
);
