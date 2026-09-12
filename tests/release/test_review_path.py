import json
from pathlib import Path

import pytest

from kivi.config import Settings
from kivi.review import corpus, import_corpus, ollama_models, reset_database, verify_model_lock, write_model_lock


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


def test_ollama_models_uses_model_id_not_size(monkeypatch):
    class Result:
        stdout = (
            "NAME                       ID              SIZE      MODIFIED\n"
            "qwen2.5:7b-instruct        845dbda0ea48    4.7 GB    2 days ago\n"
            "nomic-embed-text:latest    0a109f422b47    274 MB    2 days ago\n"
        )

    monkeypatch.setattr("kivi.review.subprocess.run", lambda *args, **kwargs: Result())
    assert ollama_models() == {
        "qwen2.5:7b-instruct": "845dbda0ea48",
        "nomic-embed-text:latest": "0a109f422b47",
    }


def test_model_lock_resolves_implicit_latest_tag(tmp_path, monkeypatch):
    installed = {
        "qwen2.5:7b-instruct": "845dbda0ea48",
        "nomic-embed-text:latest": "0a109f422b47",
    }
    settings = Settings(
        extraction_model="qwen2.5:7b-instruct",
        embedding_model="nomic-embed-text",
    )
    monkeypatch.setattr("kivi.review.ROOT", tmp_path)
    monkeypatch.setattr("kivi.review.ollama_models", lambda: installed)

    lock = write_model_lock(settings)

    assert lock == {"models": installed}
    assert verify_model_lock(settings) == {"models": installed, "verified": True}


def test_import_corpus_fails_loudly_on_terminal_rejections(tmp_path, monkeypatch):
    source = tmp_path / "corpus.json"
    record = {"transcript_id":"x", "raw_asr":"x", "formatted_text":"x", "occurred_at":"2026-01-01T00:00:00Z", "metadata":{"source":"dictation"}}
    source.write_text(json.dumps({"records":[record]}), encoding="utf-8")

    class Response:
        def __init__(self, body): self.body = body
        def raise_for_status(self): pass
        def json(self): return self.body
    class Client:
        def __enter__(self): return self
        def __exit__(self, *args): pass
        def post(self, *args, **kwargs): return Response({"status_url":"/status"})
        def get(self, *args, **kwargs): return Response({"complete":True,"counts":{"submitted":1,"accepted":0,"replayed":0,"rejected":1,"processed":0,"quarantined":0}})

    monkeypatch.setattr("kivi.review.httpx.Client", lambda **kwargs: Client())
    with pytest.raises(RuntimeError, match="IMPORT_COMPLETED_WITH_FAILURES"):
        import_corpus(Settings(), str(source))
