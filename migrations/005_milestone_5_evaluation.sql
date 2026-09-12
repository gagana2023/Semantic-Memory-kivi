CREATE TABLE IF NOT EXISTS evaluation_runs (
  id TEXT PRIMARY KEY, case_set TEXT NOT NULL, state TEXT NOT NULL,
  manifest_json TEXT NOT NULL, report_json TEXT, report_markdown TEXT,
  error_code TEXT, created_at TEXT NOT NULL, completed_at TEXT
);
CREATE TABLE IF NOT EXISTS evaluation_results (
  id TEXT PRIMARY KEY, run_id TEXT NOT NULL REFERENCES evaluation_runs(id),
  case_id TEXT NOT NULL, criterion TEXT NOT NULL, claim TEXT,
  outcome TEXT NOT NULL, reason TEXT, evidence_json TEXT NOT NULL,
  latency_ms REAL NOT NULL, created_at TEXT NOT NULL,
  UNIQUE(run_id, case_id)
);
CREATE INDEX IF NOT EXISTS idx_evaluation_results_run ON evaluation_results(run_id);
