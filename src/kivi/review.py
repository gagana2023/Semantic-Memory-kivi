"""Operator-only release-review helpers; none of these functions expose HTTP reset."""
import json
import subprocess
import time
from pathlib import Path

import httpx

ROOT = Path(__file__).resolve().parents[2]


def corpus(path: str) -> dict:
    source = Path(path)
    if not source.is_file():
        raise ValueError("CORPUS_NOT_FOUND")
    try:
        value = json.loads(source.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise ValueError("CORPUS_INVALID_JSON") from exc
    records = value.get("records") if isinstance(value, dict) else None
    if not isinstance(records, list) or not records:
        raise ValueError("CORPUS_RECORDS_REQUIRED")
    ids = set()
    required = {"transcript_id", "raw_asr", "formatted_text", "occurred_at", "metadata"}
    for record in records:
        if not isinstance(record, dict) or set(record) != required or not all(isinstance(record[k], str) and record[k] for k in required - {"metadata"}) or not isinstance(record["metadata"], dict) or not record["metadata"].get("source"):
            raise ValueError("CORPUS_RECORD_INVALID")
        if record["transcript_id"] in ids:
            raise ValueError("CORPUS_DUPLICATE_TRANSCRIPT_ID")
        ids.add(record["transcript_id"])
    return value


def import_corpus(settings, path: str, timeout_seconds: int = 300) -> dict:
    payload = corpus(path)
    with httpx.Client(base_url=settings.review_url, timeout=15) as client:
        response = client.post("/v1/imports", json=payload)
        response.raise_for_status()
        started = response.json()
        deadline = time.monotonic() + timeout_seconds
        while time.monotonic() < deadline:
            status = client.get(started["status_url"])
            status.raise_for_status()
            result = status.json()
            if result["complete"]:
                return result
            time.sleep(0.25)
    raise RuntimeError("IMPORT_COMPLETION_TIMEOUT")


def reset_database(settings) -> dict:
    removed = []
    database = Path(settings.database_path)
    for path in (database, Path(str(database) + "-wal"), Path(str(database) + "-shm")):
        if path.exists():
            path.unlink()
            removed.append(str(path))
    for name in ("import-output.txt", "evaluation-output.txt", "evaluation-report.json", "evaluation-report.md"):
        path = ROOT / name
        if path.exists():
            path.unlink()
            removed.append(name)
    return {"code": "RESET_COMPLETED", "removed": removed}


def ollama_models() -> dict:
    result = subprocess.run(["ollama", "list"], check=True, capture_output=True, text=True)
    lines = [line.split() for line in result.stdout.splitlines()[1:] if line.strip()]
    return {line[0]: line[2] for line in lines if len(line) >= 3}


def write_model_lock(settings) -> dict:
    installed = ollama_models()
    wanted = (settings.extraction_model, settings.embedding_model)
    missing = [model for model in wanted if model not in installed]
    if missing:
        raise RuntimeError("MODEL_NOT_INSTALLED:" + ",".join(missing))
    lock = {"models": {model: installed[model] for model in wanted}}
    path = ROOT / "config" / "model-locks.json"
    path.parent.mkdir(exist_ok=True)
    path.write_text(json.dumps(lock, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return lock


def verify_model_lock(settings) -> dict:
    path = ROOT / "config" / "model-locks.json"
    if not path.is_file():
        raise RuntimeError("MODEL_LOCK_NOT_FOUND")
    locked = json.loads(path.read_text(encoding="utf-8")).get("models")
    if not isinstance(locked, dict):
        raise RuntimeError("MODEL_LOCK_INVALID")
    installed = ollama_models()
    mismatches = {model: {"expected": digest, "actual": installed.get(model)} for model, digest in locked.items() if installed.get(model) != digest}
    if mismatches:
        raise RuntimeError("MODEL_DIGEST_MISMATCH:" + json.dumps(mismatches, sort_keys=True))
    return {"models": locked, "verified": True}
