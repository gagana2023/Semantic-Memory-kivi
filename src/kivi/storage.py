import json
import sqlite3
from pathlib import Path
from .config import Settings

def connect(settings: Settings) -> sqlite3.Connection:
    db = sqlite3.connect(settings.database_path, check_same_thread=False)
    db.row_factory = sqlite3.Row; db.execute("PRAGMA journal_mode=WAL"); db.execute("PRAGMA foreign_keys=ON")
    return db

def migrate(settings: Settings) -> None:
    db = connect(settings)
    try:
        db.execute("CREATE TABLE IF NOT EXISTS schema_migrations (version TEXT PRIMARY KEY, applied_at TEXT NOT NULL)")
        migrations = sorted((Path(__file__).resolve().parents[2] / "migrations").glob("*.sql"))
        for migration in migrations:
            version = migration.name
            if not db.execute("SELECT 1 FROM schema_migrations WHERE version=?", (version,)).fetchone():
                db.executescript(migration.read_text(encoding="utf-8"))
                db.execute("INSERT INTO schema_migrations VALUES (?, datetime('now'))", (version,))
                db.commit()
    finally: db.close()

def trace(db, ident, transcript_id, memory_id, stage, outcome, detail, stamp):
    db.execute("INSERT INTO decision_traces VALUES (?, ?, ?, ?, ?, ?, ?)", (ident, transcript_id, memory_id, stage, outcome, json.dumps(detail, sort_keys=True), stamp))
