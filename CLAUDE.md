# Kivi — session guide

## Product boundary

Kivi is a local, single-user text client that turns eligible user dictations and explicit user actions into durable typed work memory, then uses it for grounded recall, drafts, and an internal schedule. It prioritises trust: user-authored evidence, hard exclusions, provenance, explicit permissions, correction, abstention, and complete explanations.

It deliberately is not speech recognition, a general assistant, a multi-user platform, a hosted service, an external calendar client, a profile/summary engine, a plugin system, an event bus, a graph database, an external vector store, an admin dashboard, or a second account boundary. Do not add tools beyond recall, draft, and internal scheduling.

## Stack and layout

- CPython 3.12; FastAPI + Uvicorn (one process/worker); Pydantic strict/discriminated contracts.
- Server-rendered Jinja2, checked-in CSS, small vanilla JS; no Node build chain or SPA.
- SQLite WAL through `sqlite3`, explicit repositories and `BEGIN IMMEDIATE`; ordered idempotent SQL migrations, not an ORM/Alembic.
- SQLite FTS5 for lexical search; local Ollama (`qwen3:8b`, `nomic-embed-text:latest`) via `httpx`; vectors in SQLite, cosine scored in Python.
- Durable SQLite jobs consumed serially in-process; `pytest` plus checked-in corpus/cases; one-line JSON logging via stdlib logging.
- Intended layout: `src/kivi/api/`, `web/`, `domain/contracts.py`, `services/`, `storage/`, `evaluation/`, `worker.py`; `migrations/`, `config/`, `fixtures/`, `tests/`.

## Decisions that constrain implementation

- Local, no-cost, single-user system — reject hosted APIs/SaaS and multi-tenancy.
- One Uvicorn process and one serial durable worker — reject multi-worker deployment, Celery/RQ/Redis, and cron.
- SQLite is the sole authority; Ollama is stateless computation — reject PostgreSQL and a separate vector database.
- Strict Pydantic contracts with forbidden unknown fields — reject ad-hoc dictionaries.
- Server-rendered UI — reject React/Vite, Electron, and Tauri.
- Plain idempotent SQL migrations — reject Alembic/ORM indirection.
- FTS5 plus bounded local vector scan — reject Elasticsearch/OpenSearch, LIKE scans, and native vector extensions.
- Direct Ollama REST with pinned model digests — reject SDK wrappers, mutable tags, and committed model weights.
- Local `qwen3:8b` plus `nomic-embed-text:latest` — reject hosted inference and per-stage model sprawl.
- Only user dictations, user-authored Hey Kivi turns, and explicit actions are memory evidence — reject app context, Kivi output, and tool results as evidence.
- Memory types are only entity, preference, and time-bearing episode — reject summaries and untyped fallback memory.
- Admission gates run exclusion, third-party/work eligibility, typability, completeness, suppression — reject user overrides and fail-open ambiguity.
- Dictation is structurally lexical/stated-formatting only; Hey Kivi retrieves semantic memory — reject a wording-based mode switch.
- Retrieve before permission, with deterministic ranking — reject permission-dependent ranking or LLM reranking.
- Anbu defaults to stated only; Koottu may surface observations; Daari is one-request, one-question hypothesis — reject persistent Daari or acting on unconfirmed memory.
- Exactly `recall_search`, `draft_reply`, `schedule_reschedule` — reject tool loops, external actions, and extra tools.
- Ground every factual Hey Kivi claim in current permitted memory or labelled raw fallback — reject plausible unsupported answers.
- Explicit correction writes replacement and suppression atomically; forget leaves disclosed residue only — reject partial control changes or silent regrowth.
- All source persistence, jobs, traces, actions, and evaluation state are durable and inspectable — reject demo-only/canned behavior.
- Logs are JSON allowlist records; rejected bodies/raw model output are never stored — reject cloud logging and sensitive diagnostics.

## Conventions

- Errors: strict validation; field-level errors; ambiguous/unsupported/model failures fail closed, are reason-coded, retried durably where specified, then quarantined. Never fabricate success.
- Logging: one JSON line through stdlib logging; allowlisted metadata only; no excluded/rejected content or raw model output.
- Naming: Python modules are lowercase snake_case; public API ownership and routes stay exactly as specified; opaque ULID-shaped IDs; RFC 3339 UTC `Z` timestamps.
- Tests: pytest, in-process FastAPI client, production services/real SQLite/Ollama paths; assert deterministic state, provenance, idempotency, safe abstention, and no leakage. No browser automation as the primary test path.

## Milestones

| Milestone | Status |
|---|---|
| 1. Local thin slice | Complete |
| 2. Complete write path and corpus import | Complete |
| 3. Read path, permission, three tools | Complete |
| 4. User control, lifecycle, inspection | Complete |
| 5. Reproducible full-pipeline evaluation | Complete |
| 6. Clean-clone and foreign-corpus release gate | Complete |

## Standing rules

No design decision is made during implementation. If a choice comes up that `DESIGN.md` does not cover, stop and ask.

Update `RUN.md` in the same change as any setup step it describes. Never defer that documentation.
