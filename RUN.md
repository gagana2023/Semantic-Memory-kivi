# Kivi runbook — Milestones 2 and 3

## Runtimes and install

Requires CPython 3.12 and a local Ollama server. From the repository root:

```powershell
py -3.12 -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

## Model prerequisite — MANUAL

Start Ollama, then verify or pull the local model names used by this milestone:

```powershell
ollama pull qwen3:8b
ollama pull nomic-embed-text
ollama list
```

The Ollama CLI resolves tags; record the displayed digest in review evidence. No model weights are committed.

Create and verify the host-local model lock after pulling models (**MANUAL**; it requires a running local Ollama):

```powershell
$env:PYTHONPATH='src'
python -m kivi write-model-lock
python -m kivi verify-model-lock
```

Both commands fail loudly on a missing model or digest mismatch. No model weights or credentials are committed.

## Environment variables

- `KIVI_DATABASE_PATH` — SQLite path, default `kivi.db`.
- `KIVI_OLLAMA_URL` — Ollama base URL, default `http://127.0.0.1:11434`.
- `KIVI_EXTRACTION_MODEL` — extraction model, default `qwen3:8b`.
- `KIVI_EMBEDDING_MODEL` — declared for local model inventory; unused until semantic recall.

## Migrate, run, inspect

Migrations run automatically at startup:

```powershell
$env:PYTHONPATH='src'
uvicorn kivi.app:app --host 127.0.0.1 --port 8000
```

Open `http://127.0.0.1:8000/`. The three pages are Dictation, Hey Kivi, and Inspect.

`KIVI_REVIEW_URL` is the local server URL used by the corpus-import CLI; its default is `http://127.0.0.1:8000`.

## Five-click smoke path — MANUAL

1. Open Dictation and enter raw ASR plus formatted text stating one entity relation, e.g. “Atlas review note is ready”.
2. Submit and copy the returned transcript/job IDs.
3. Wait until `GET /v1/jobs/{job_id}` says `completed`.
4. Open Hey Kivi, ask “Atlas”, and confirm its citation.
5. Open Inspect, enter the dictation transcript ID, confirm memory provenance and Why trace; restart the process and repeat recall.

Draft and internal schedule requests are available through Hey Kivi; no external calendar is contacted. Full permission/disclosure inspection remains incomplete.

## Tests

```powershell
$env:PYTHONPATH='src'
pytest tests/thin_slice -q --basetemp .pytest-tmp *> test-output.txt
```

`test-output.txt` is the full test output. The tests exercise AC-FR-01 and AC-FR-03, including malformed input, failed extraction, lexical abstention, and persistence after restart. They use a deterministic extractor test double; the application path uses real Ollama.

Milestone 2 adds import/write-path checks (including invalid admission and model-failure cases):

```powershell
$env:PYTHONPATH='src'
pytest tests/thin_slice tests/ingestion -q --basetemp .pytest-tmp *> test-output.txt
```

This is a development check only. It does not satisfy Milestone 2's required 500-record corpus, `tests/memory_write`, or corpus CLI verification; those remain release gaps until implemented.

## Milestone 3 tests

```powershell
$env:PYTHONPATH='src'
pytest tests/thin_slice tests/ingestion tests/retrieval tests/disclosure tests/tools tests/grounding -q --basetemp .pytest-tmp *> test-output.txt
```

The full output is in `test-output.txt`. The currently implemented read-path checks cover grounded recall/abstention, stable pre-permission candidate order, unsupported tool rejection, and internal schedule idempotency. The vector projection worker, raw fallback, one-hop fixture, and full disclosure/Daari negative matrix remain visible implementation gaps, not passing claims.

## Inspection and reset

Use `GET /v1/jobs/{job_id}` for durable job state and `GET /v1/inspect/{transcript_id}` for transcript, memory provenance, and decision traces. These API views are authoritative in this slice.

## Milestone 4 tests

```powershell
$env:PYTHONPATH='src'
pytest tests/thin_slice tests/ingestion tests/retrieval tests/disclosure tests/tools tests/grounding tests/actions tests/lifecycle tests/inspection tests/restart -q --basetemp .pytest-tmp *> test-output.txt
```

`test-output.txt` is the complete test output. The focused suites cover action idempotency/version conflicts, correction validation, forgetting, lifecycle suppression, memory detail/provenance/history, Why retrieval candidates, and restart persistence. UI smoke inspection is **MANUAL**: start the server, open Inspect, then confirm all three tier headings and an active-memory row are visible.

Lifecycle windows are 90 days for unpinned observations and 30 days for unpinned hypotheses; stated and pinned memory is never swept.

To reset **after stopping the server**, delete only the configured SQLite database and its SQLite sidecars (for the default path: `kivi.db`, `kivi.db-wal`, `kivi.db-shm`). This is a destructive local reset:

```powershell
Remove-Item -LiteralPath kivi.db,kivi.db-wal,kivi.db-shm -Force -ErrorAction SilentlyContinue
```

## Complete-pipeline evaluation

The evaluator is local and creates no transcript records for evaluation questions. It removes the configured database first, ingests every corpus record through the durable worker, and runs every fixed question through the same Hey Kivi retrieval/disclosure service used by the API:

```powershell
$env:PYTHONPATH='src'
python -m kivi evaluate --corpus fixtures/development-500.json --questions EVAL_QUESTIONS.json --ground-truth GROUND_TRUTH.json
```

The artifacts are `results.json` (the complete audit) and `summary.md` (class pass rates, refusal/fabrication counts, p50/p95 latency, totals, and every failure in full). The command exits non-zero if any case fails. Extraction uses temperature 0 and `KIVI_RANDOM_SEED` (default `7`); lock model digests using the commands above.

Inspect all memory without knowing the database schema:

```powershell
python -m kivi inspect-memory
```

## Milestone 5 tests

```powershell
$env:PYTHONPATH='src'
pytest tests/evaluation -q --basetemp .pytest-tmp *> test-output.txt
```

## Corpus import and clean review — Milestone 6

This is the primary local review path. Start the server using the command above, then in a second PowerShell window import a schema-valid corpus through the public import contract (no dashboard action is required):

```powershell
$env:PYTHONPATH='src'
python -m kivi import-corpus fixtures/development-500.json *> import-output.txt
```

The command waits for a terminal import state, writes full output to `import-output.txt`, and fails loudly on invalid JSON, invalid schema, duplicate transcript IDs, HTTP failure, or timeout. Inspect its returned per-state counts, then use the Dictation and Hey Kivi pages plus `GET /v1/inspect/{transcript_id}`. A translated, unseen one-user corpus follows the same command, replacing the fixture path; it must use the exact `records` schema in `fixtures/development-500.json`.

To reset, stop the server first. Reset is an operator-only CLI action, never an HTTP endpoint. It removes the configured SQLite database, sidecars, and generated evaluation reports; then restart the server and re-import the documented seed corpus:

```powershell
$env:PYTHONPATH='src'
python -m kivi reset
uvicorn kivi.app:app --host 127.0.0.1 --port 8000
python -m kivi import-corpus fixtures/development-500.json *> import-output.txt
```

## Milestone 6 release tests

```powershell
$env:PYTHONPATH='src'
pytest tests/thin_slice tests/ingestion tests/retrieval tests/disclosure tests/tools tests/grounding tests/actions tests/lifecycle tests/inspection tests/restart tests/evaluation tests/release -q --basetemp .pytest-tmp *> test-output.txt
```

The required human UI pass is **MANUAL**: after a clean reset and corpus import, open Dictation, Hey Kivi, and Inspect; submit an ordinary dictation, ask a history-present question and an absent-history question, and confirm that the latter abstains. Run the documented evaluation command and retain its generated JSON/Markdown report, including any failures. Current evaluation is intentionally a visible release failure until its isolated public-contract adapter is implemented; do not treat this manual pass as AC-FR-32 success.
