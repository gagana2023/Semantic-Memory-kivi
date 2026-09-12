# Kivi — RUN.md

## Primary review method

**A completely local application.** One FastAPI/Uvicorn process, one SQLite database file, and a local Ollama daemon on the same machine. Nothing is hosted, containerised, or networked beyond `127.0.0.1`. No API key or credential is required.

Everything below is the single supported path. Commands are given for **bash** (Linux/macOS) and **PowerShell** (Windows); use one column consistently. Run every command from the repository root.

---

## 1. Required runtimes and versions

| Runtime | Version | Purpose |
|---|---|---|
| CPython | 3.12.x (tested 3.12.10) | application, worker, CLI, tests |
| Ollama | 0.6 or newer | local extraction model |
| SQLite | bundled with CPython (needs FTS5, which the official builds include) | storage |

Models used (pulled in step 3, not committed):

- `qwen2.5:7b-instruct` — extraction model. **The checked-in `results.json` / `summary.md` were produced with this model**; use it to reproduce them.
- `nomic-embed-text` — declared embedding model. It is verified by the model lock but the embedding retrieval leg is not active in this build (see README "Limitations"); retrieval is FTS5/entity based.

The design document names `qwen3:8b` as the intended extraction model. It is *not* the primary path because the checked-in results were not produced with it; to try it, pull it and set `KIVI_EXTRACTION_MODEL=qwen3:8b`.

## 2. Environment variables

All variables are optional; the defaults are shown. `.env.example` lists the same set. Copy it to `.env` and export the values yourself (the application does not read `.env` files), or set them inline as shown in the later steps.

| Variable | Default | Meaning |
|---|---|---|
| `PYTHONPATH` | — | **must be `src`** for every `python -m kivi …`, `uvicorn …`, and `pytest` command |
| `KIVI_DATABASE_PATH` | `kivi.db` | SQLite file path (WAL sidecars `-wal`/`-shm` sit beside it) |
| `KIVI_OLLAMA_URL` | `http://127.0.0.1:11434` | Ollama base URL |
| `KIVI_EXTRACTION_MODEL` | `qwen3:8b` | Ollama model used for extraction. **Set to `qwen2.5:7b-instruct` for the primary path.** |
| `KIVI_EMBEDDING_MODEL` | `nomic-embed-text` | declared embedding model (lock-verified; leg inactive) |
| `KIVI_REVIEW_URL` | `http://127.0.0.1:8000` | server URL used by the `import-corpus` CLI |
| `KIVI_RANDOM_SEED` | `7` | seed passed to Ollama for deterministic extraction |

No LLM API key exists or is needed.

## 3. Install dependencies

bash:

```bash
python3.12 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

ollama pull qwen2.5:7b-instruct
ollama pull nomic-embed-text
ollama list
```

PowerShell:

```powershell
py -3.12 -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt

ollama pull qwen2.5:7b-instruct
ollama pull nomic-embed-text
ollama list
```

Optional model lock (records the installed digests to `config/model-locks.json`, which is git-ignored and host-local; both commands fail loudly on a missing model or digest mismatch):

```bash
export PYTHONPATH=src KIVI_EXTRACTION_MODEL=qwen2.5:7b-instruct
python -m kivi write-model-lock
python -m kivi verify-model-lock
```

```powershell
$env:PYTHONPATH='src'; $env:KIVI_EXTRACTION_MODEL='qwen2.5:7b-instruct'
python -m kivi write-model-lock
python -m kivi verify-model-lock
```

## 4. Create, migrate, and seed the database

There is no separate create/migrate command: the server creates the SQLite file and applies `migrations/001…005` idempotently at startup. Seeding is an import through the public import contract and requires the server to be running, so:

1. Start the server (step 5).
2. In a second terminal, import the checked-in seed corpus:

bash:

```bash
export PYTHONPATH=src
python -m kivi import-corpus fixtures/development-500.json 2>&1 | tee import-output.txt
```

PowerShell:

```powershell
$env:PYTHONPATH='src'
python -m kivi import-corpus fixtures/development-500.json *> import-output.txt
Get-Content import-output.txt
```

The command blocks until the import reaches a terminal state (default timeout 300 s; raise with `--timeout-seconds 900` on a slow GPU/CPU — 500 records take roughly 3–10 minutes), prints one JSON object with per-record states, and exits non-zero on invalid JSON, invalid schema, duplicate transcript IDs, HTTP failure, or timeout. A successful seed shows `"counts": {"processed": 500, "quarantined": 0, …}`. Any `quarantined` record carries an `error_code`; `OLLAMA_EXTRACTION_FAILED` means the configured extraction model is not installed or Ollama is not running.

## 5. Start every required process

Two processes: the Ollama daemon and the Kivi server. The durable job worker runs inside the Kivi server process; nothing else is needed.

bash:

```bash
ollama serve   # skip if Ollama is already running as a service

export PYTHONPATH=src KIVI_EXTRACTION_MODEL=qwen2.5:7b-instruct
uvicorn kivi.app:app --host 127.0.0.1 --port 8000
```

PowerShell:

```powershell
ollama serve   # skip if Ollama is already running as a service

$env:PYTHONPATH='src'; $env:KIVI_EXTRACTION_MODEL='qwen2.5:7b-instruct'
uvicorn kivi.app:app --host 127.0.0.1 --port 8000
```

Every later terminal that runs `python -m kivi …` needs the same two environment variables set.

## 6. Interface to open

Keep the Kivi server terminal from step 5 running, then open [http://127.0.0.1:8000/](http://127.0.0.1:8000/) in a browser. The top navigation exposes three server-rendered, normal-user surfaces:

- `/` Dictate — writes the person's words without semantic recall, then learns eligible work facts afterward
- `/hey` Hey Kivi — grounded recall, drafting, internal scheduling, Anbu/Koottu control, and a plain-language Why drawer
- `/memory` Memory — the three human memory tiers, source notes, history, pinning, correction, demotion, and forgetting

`/inspect` remains an alias for `/memory` so old review links still work. The JSON API under `/v1/` is the authoritative view; the surfaces call it.

## 7. Primary interactions to try

After seeding (step 4). Bodies are strict — unknown fields are rejected with field-level errors.

**a. Dictation (write path).** Submit, then poll the job.

```bash
curl -s -X POST http://127.0.0.1:8000/v1/dictations -H 'content-type: application/json' \
  -d '{"raw_asr":"the atlas review note is ready","formatted_text":"The Atlas review note is ready."}'
# → 202 {"transcript_id": "...", "job_id": "..."}
curl -s http://127.0.0.1:8000/v1/jobs/<job_id>          # until "status": "completed"
curl -s http://127.0.0.1:8000/v1/inspect/<transcript_id> # transcript, memories, admission decisions
```

**b. Hey Kivi recall (history present).**

```bash
curl -s -X POST http://127.0.0.1:8000/v1/hey-kivi -H 'content-type: application/json' \
  -d '{"text":"Who is the Atlas technical lead?"}'
```

The answer carries `citations` (memory IDs + source transcript IDs) and a `trace_id`. Follow it:

```bash
curl -s http://127.0.0.1:8000/v1/why/<trace_id>   # retrieval candidates, support/near-miss decisions, disclosure
```

**c. Hey Kivi abstention (history absent).** Ask something the corpus never states; expect `"status": "abstained"`, `"reason": "NO_GROUNDED_MATCH"`, and empty `citations` — not a plausible guess.

```bash
curl -s -X POST http://127.0.0.1:8000/v1/hey-kivi -H 'content-type: application/json' \
  -d '{"text":"What is the office wifi password?"}'
```

(A question that shares an entity name with stored memory — "What is the Atlas budget?" — may instead return the Atlas facts it does have. This is the known "unanswerable" weakness reported in README: 8/11 correct refusals, 3 fabrications.)

**d. Draft and internal schedule.** Same endpoint; the tool is chosen by keyword (`draft`/`reply`/`write ` → `draft_reply`; `schedule`/`reschedule`/`move to` → `schedule_reschedule`; otherwise `recall_search`) and reported in `selected_tool`. No external calendar or mail is contacted. A schedule request needs an RFC 3339 UTC time in the text, an `idempotency_key`, and a retrieved `episode` memory; otherwise it abstains with `MISSING_TIME_OR_GROUNDED_EVENT`.

```bash
curl -s -X POST http://127.0.0.1:8000/v1/hey-kivi -H 'content-type: application/json' \
  -d '{"text":"Draft a reply to Arun confirming the Atlas review slot."}'
curl -s -X POST http://127.0.0.1:8000/v1/hey-kivi -H 'content-type: application/json' \
  -d '{"text":"Reschedule the pricing legal review to 2026-06-10T14:00:00Z.","idempotency_key":"sched-1"}'
# → "status":"completed", "event_id":"evt_…", "external_side_effects":"none"; repeating with the same key returns the same event_id
```

**e. Permission dial.** `anbu` (default) discloses stated memory only; `koottu` may also surface observations. Candidate ranking does not change between them.

```bash
curl -s http://127.0.0.1:8000/v1/permissions
curl -s -X PUT http://127.0.0.1:8000/v1/permissions -H 'content-type: application/json' -d '{"mode":"koottu"}'
```

**f. User control over a memory.** List, read, then act. `GET /v1/memories` returns `{"groups": {"stated": [...], "observed": [...], "hypothesis": [...]}}`; each memory carries a `version` (starting at 0). `expected_version` must equal the current version (optimistic concurrency; a stale value is rejected) and `idempotency_key` makes repeats safe. Actions: `confirm`, `correct` (needs `value`), `demote`, `forget`, `pin`, `unpin`. Each returns a `receipt_id` and the new `version`.

```bash
curl -s http://127.0.0.1:8000/v1/memories
curl -s http://127.0.0.1:8000/v1/memories/<memory_id>   # memory, provenance transcripts, versions, action history
curl -s -X POST http://127.0.0.1:8000/v1/memories/<memory_id>/actions -H 'content-type: application/json' \
  -d '{"action":"correct","expected_version":0,"idempotency_key":"fix-1","value":"since 2 March 2026"}'
curl -s -X POST http://127.0.0.1:8000/v1/memories/<memory_id>/actions -H 'content-type: application/json' \
  -d '{"action":"forget","expected_version":1,"idempotency_key":"forget-1"}'
```

After `forget` the memory's status is `suppressed`: `GET /v1/memories/<memory_id>` returns `MEMORY_NOT_FOUND`, it no longer appears in recall, and only the action receipt and suppression row remain (`memory_actions`, `suppressions` tables; `python -m kivi inspect-memory` no longer lists it).

**g. Restart persistence.** Stop the server (Ctrl+C), start it again (step 5), and repeat (b): the same citations return.

The same flows are available in the UI: Dictation page (a), Hey Kivi page (b–e), Inspect page (f, plus the three tier headings and active-memory rows).

## 8. Run the candidate evaluation

The evaluator is offline from the server: it **deletes the configured database**, re-ingests the whole corpus through the durable worker, runs all 52 questions through the production Hey Kivi service without storing them as transcripts, and writes `results.json` and `summary.md`. Stop the server first, or point the evaluator at a different `KIVI_DATABASE_PATH`.

bash:

```bash
export PYTHONPATH=src KIVI_EXTRACTION_MODEL=qwen2.5:7b-instruct KIVI_DATABASE_PATH=eval.db
python -m kivi evaluate --corpus fixtures/development-500.json --questions EVAL_QUESTIONS.json \
  --ground-truth GROUND_TRUTH.json --output-dir eval-out 2>&1 | tee evaluation-output.txt
```

PowerShell:

```powershell
$env:PYTHONPATH='src'; $env:KIVI_EXTRACTION_MODEL='qwen2.5:7b-instruct'; $env:KIVI_DATABASE_PATH='eval.db'
python -m kivi evaluate --corpus fixtures/development-500.json --questions EVAL_QUESTIONS.json `
  --ground-truth GROUND_TRUTH.json --output-dir eval-out *> evaluation-output.txt
Get-Content evaluation-output.txt
```

`--output-dir` defaults to `.`; the command above writes to `eval-out/` so the committed `results.json` / `summary.md` (the submitted results) are not overwritten. The process exits non-zero whenever any case fails — **it is expected to exit non-zero**: the submitted result is 24/52. Extraction runs at temperature 0 with `KIVI_RANDOM_SEED`; model output is still not guaranteed bit-identical across hardware, so small differences from the committed numbers are possible and are reported, not hidden.

Unit/integration tests (no Ollama needed; deterministic extractor double):

```bash
export PYTHONPATH=src
pytest tests -q 2>&1 | tee test-output.txt
```

```powershell
$env:PYTHONPATH='src'
pytest tests -q *> test-output.txt
```

## 9. Import another corpus

### 9.1 Where to put it

Place the translated corpus anywhere readable; the recommended location is `fixtures/<name>.json` beside the seed corpus (e.g. `fixtures/reviewer-corpus.json`). The import command takes the path explicitly, so no other file has to be edited and no directory is scanned. One file may hold up to 1,000 records; split a larger corpus into `fixtures/<name>-1.json`, `fixtures/<name>-2.json`, … and import them in order.

If the foreign corpus should replace the seed rather than sit alongside it, run the reset (step 11) first; otherwise both corpora coexist in one database and `transcript_id` values must not collide with the seed's `meera_2026_NNNN` IDs.

### 9.2 Record format

A corpus is a JSON object with a single `records` array, exactly the schema of `fixtures/development-500.json`:

```json
{
  "records": [
    {
      "transcript_id": "reviewer_0001",
      "raw_asr": "degraded speech-recognition text",
      "formatted_text": "the user's corrected dictation text",
      "occurred_at": "2026-01-05T09:12:00+05:30",
      "metadata": {"source": "dictation", "application": "mail", "language": "en-IN", "channel": "inbox"}
    }
  ]
}
```

| Field | Rule |
|---|---|
| `records` | 1–1000 entries per file |
| `transcript_id` | non-empty; unique across the whole database — a duplicate fails the entire import loudly before anything is written |
| `raw_asr` | non-empty; the pre-correction text (may equal `formatted_text` if no ASR variant exists) |
| `formatted_text` | non-empty; the user's authored text — the **only** memory evidence |
| `occurred_at` | RFC 3339 timestamp with offset (`+05:30` in the seed; `Z` accepted); records are processed in this order |
| `metadata` | JSON object with a **required non-empty `source`** string (the seed uses `"dictation"`); other keys are optional — the seed uses `application` (e.g. `slack`, `mail`, `docs`), `language` (`en-IN`), and `channel`. Stored for provenance only; never used as memory evidence. `{}` is rejected with `CORPUS_RECORD_INVALID` |

Any other field, at any level, is rejected with a field-level error.

### 9.3 Import it

With the server running (step 5):

bash:

```bash
export PYTHONPATH=src
python -m kivi import-corpus fixtures/reviewer-corpus.json --timeout-seconds 900 2>&1 | tee import-output.txt
```

PowerShell:

```powershell
$env:PYTHONPATH='src'
python -m kivi import-corpus fixtures/reviewer-corpus.json --timeout-seconds 900 *> import-output.txt
Get-Content import-output.txt
```

Then use the interactions in step 7 against the new records, and `python -m kivi inspect-memory` to see what was admitted.

### 9.4 Evaluate against it (optional)

The evaluator needs a questions file. Put it beside the corpus, e.g. `fixtures/reviewer-questions.json`, with this shape:

```json
{
  "schema_version": "1.0",
  "tiers": {
    "tier_1": {
      "questions": [
        {
          "id": "q_role",
          "question": "What is Meera's role?",
          "answerability": "answerable",
          "capability": "distributed evidence synthesis",
          "expected_answer": "Meera is Product Lead at Ternary Studio.",
          "required_provenance": ["reviewer_0002"]
        },
        {
          "id": "q_absent",
          "question": "What is the office wifi password?",
          "answerability": "unanswerable",
          "capability": "absent-history abstention",
          "expected_behavior": "abstain",
          "required_provenance": []
        }
      ]
    },
    "tier_2": {"questions": []}
  }
}
```

- `answerability`: `answerable` or `unanswerable`.
- `capability`: free text; it decides the report class — contains `preference` → demonstrated-preferences; `supersession` / `current-truth` / `historical` / `reversal` → superseded-facts; `episode` / `reconstruction` / `time/app` → episodic-retrieval; anything else → distributed-recovery. `unanswerable` always classes as unanswerable.
- `expected_answer`: the answer text scored by token overlap (answerable cases).
- `required_provenance`: `transcript_id`s that must all appear in the answer's citations.
- `tier_2`: leave `"questions": []`. The tier-2 templates in `EVAL_QUESTIONS.json` are bound by ID to the seed corpus's tier-1 cases and only apply to it.

`--ground-truth` is required on the command line but is only recorded in the report configuration; it does not affect scoring. Pass `GROUND_TRUTH.json` unchanged or a file of the same shape.

Stop the server, then:

```bash
export PYTHONPATH=src KIVI_EXTRACTION_MODEL=qwen2.5:7b-instruct KIVI_DATABASE_PATH=eval.db
python -m kivi evaluate --corpus fixtures/reviewer-corpus.json --questions fixtures/reviewer-questions.json   --ground-truth GROUND_TRUTH.json --output-dir eval-out-reviewer 2>&1 | tee evaluation-output.txt
```

The evaluator deletes and rebuilds `KIVI_DATABASE_PATH` from the given corpus, so it never sees the seed unless you pass the seed file.

## 10. Where to inspect results and memory state

- **Evaluation results:** `results.json` (complete audit: per-case expected/actual, retrieved memories, exclusions, provenance, timings, token usage, database growth samples) and `summary.md` (class pass rates, refusals/fabrications, latency, every failure in full). A fresh run writes the same two files into `--output-dir`. `evaluation-sensitivity.md` and `evaluation-after-fixes.md` hold the break-test runs.
- **Memory state without schema knowledge:**

  ```bash
  export PYTHONPATH=src
  python -m kivi inspect-memory
  ```

  prints every active memory with type, name/relation/value, basis, status, supersession status, pinned flag, creation time, and provenance transcript IDs.
- **Per-object views:** `GET /v1/inspect/{transcript_id}`, `GET /v1/memories`, `GET /v1/memories/{memory_id}`, `GET /v1/why/{trace_id}`, `GET /v1/jobs/{job_id}`, `GET /v1/imports/{import_id}`, and the Inspect page.
- **Raw database:** `kivi.db` (or `KIVI_DATABASE_PATH`) is plain SQLite; `sqlite3 kivi.db .tables` works. Tables of interest: `transcripts`, `jobs`, `memories`, `memory_versions`, `memory_evidence`, `admission_decisions`, `retrieval_candidates`, `decision_traces`, `memory_actions`, `suppressions`, `memory_tombstones`, `imports`, `import_records`.
- **Logs:** one JSON line per event on the server's stdout; allowlisted metadata only.

## 11. Reset the system

Reset is an operator CLI action only; there is no HTTP reset endpoint. Stop the server first.

bash:

```bash
export PYTHONPATH=src
python -m kivi reset
```

PowerShell:

```powershell
$env:PYTHONPATH='src'
python -m kivi reset
```

It deletes the configured SQLite database and its `-wal`/`-shm` sidecars plus the generated `import-output.txt`, `evaluation-output.txt`, and any `evaluation-report.*` files in the repository root. It does **not** touch the committed `results.json` / `summary.md`, `eval-out/`, or `config/model-locks.json`. Then restart the server (step 5) and re-seed (step 4).

If you used a non-default `KIVI_DATABASE_PATH` (e.g. `eval.db`), set the same value before running `reset`.
