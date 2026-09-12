import json
from pathlib import Path

import pytest

from kivi.config import Settings
from kivi.review import corpus, reset_database


def test_development_corpus_has_approximately_500_schema_valid_records():
    data = corpus("fixtures/development-500.json")
    assert len(data["records"]) == 500


def test_invalid_and_duplicate_foreign_corpora_fail_loudly(tmp_path):
    invalid = tmp_path / "invalid.json"
    invalid.write_text("{}", encoding="utf-8")
    with pytest.raises(ValueError, match="CORPUS_RECORDS_REQUIRED"):
        corpus(str(invalid))
    duplicate = tmp_path / "duplicate.json"
    record = {"transcript_id":"x", "raw_asr":"x", "formatted_text":"x", "occurred_at":"2026-01-01T00:00:00Z", "metadata":{"source":"dictation"}}
    duplicate.write_text(json.dumps({"records":[record, record]}), encoding="utf-8")
    with pytest.raises(ValueError, match="CORPUS_DUPLICATE_TRANSCRIPT_ID"):
        corpus(str(duplicate))


def test_reset_is_operator_only_and_removes_database_and_generated_reports(tmp_path, monkeypatch):
    database = tmp_path / "review.db"
    database.write_text("state", encoding="utf-8")
    monkeypatch.setattr("kivi.review.ROOT", tmp_path)
    (tmp_path / "evaluation-report.json").write_text("report", encoding="utf-8")
    result = reset_database(Settings(database_path=str(database)))
    assert result["code"] == "RESET_COMPLETED"
    assert not database.exists()
    assert not (tmp_path / "evaluation-report.json").exists()
