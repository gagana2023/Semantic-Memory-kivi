ALTER TABLE transcripts ADD COLUMN occurred_at TEXT;
ALTER TABLE transcripts ADD COLUMN metadata_json TEXT NOT NULL DEFAULT '{}';
ALTER TABLE transcripts ADD COLUMN outcome TEXT;
ALTER TABLE jobs ADD COLUMN attempts INTEGER NOT NULL DEFAULT 0;
ALTER TABLE jobs ADD COLUMN lease_until TEXT;
ALTER TABLE jobs ADD COLUMN import_id TEXT;
CREATE TABLE IF NOT EXISTS imports (
  id TEXT PRIMARY KEY, state TEXT NOT NULL, submitted INTEGER NOT NULL,
  accepted INTEGER NOT NULL, rejected INTEGER NOT NULL, created_at TEXT NOT NULL,
  started_at TEXT, completed_at TEXT
);
CREATE TABLE IF NOT EXISTS import_records (
  import_id TEXT NOT NULL REFERENCES imports(id), transcript_id TEXT,
  record_index INTEGER NOT NULL, state TEXT NOT NULL, error_code TEXT,
  PRIMARY KEY(import_id, record_index)
);
CREATE TABLE IF NOT EXISTS memory_evidence (
  memory_id TEXT NOT NULL REFERENCES memories(id), transcript_id TEXT NOT NULL REFERENCES transcripts(id),
  PRIMARY KEY(memory_id, transcript_id)
);
CREATE TABLE IF NOT EXISTS admission_decisions (
  id TEXT PRIMARY KEY, transcript_id TEXT NOT NULL REFERENCES transcripts(id), candidate_index INTEGER NOT NULL,
  gate TEXT NOT NULL, outcome TEXT NOT NULL, reason_code TEXT, created_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS entity_links (
  memory_id TEXT NOT NULL REFERENCES memories(id), entity_name TEXT NOT NULL,
  PRIMARY KEY(memory_id, entity_name)
);
CREATE TABLE IF NOT EXISTS projections (
  memory_id TEXT PRIMARY KEY REFERENCES memories(id), vector_json TEXT, state TEXT NOT NULL, error_code TEXT
);
