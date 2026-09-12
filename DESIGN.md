# Kivi Semantic Memory System Design

This document implements `SPECIFICATION.md`. `FR-nn`, `API-nn`, `TOOL-nn`, and `AC-FR-nn` are requirement references into that file. `C4.x` refers to its constraints. A line marked **ASSUMPTION** fills a gap explicitly left open by the specification; it is not a requirement. A line marked **SCOPE CREEP** identifies optional work that must not enter v1 without a specification change. Proposed paths name the implementation location to create; they do not claim that code already exists.

## 1. OBJECTIVE

Kivi is a local, single-user text application that turns dictations and explicit user actions into durable, typed work memory, then uses that memory for grounded recall, drafting, and an internal schedule. It optimises first for trust: user-authored evidence only, hard exclusions, provenance to the original source, explicit permission boundaries, durable correction, honest abstention, and a complete explanation for every result. It optimises second for a clean-clone review: one application process, one SQLite database, local Ollama models, checked-in migrations and fixtures, and no paid or hosted runtime dependency. Ordinary dictation remains structurally narrower than Hey Kivi, while Anbu, Koottu, and per-request Daari control what retrieved semantic memory may be disclosed. The intended scale is one user and roughly 500 transcripts, not a general multi-tenant memory platform. (Trace: FR-01–FR-33; C4.1–C4.4.)

## 2. TECH STACK

All runtime components are free/open-source and run locally. **ASSUMPTION (user constraint):** “no spend” means zero API, SaaS, licence, or hosted-infrastructure charges; it does not attempt to price the reviewer’s existing computer, electricity, or initial model/package downloads. Evaluation reports those excluded cost categories and records attributable service cost as USD 0.00. (Trace: FR-31–FR-33; C4.3.6; C4.4 cost reporting.)

| Component | Choice | Alternative considered | Why the alternative lost | Trace |
|---|---|---|---|---|
| Runtime | CPython 3.12, version checked in `.python-version` | Node/TypeScript | A browser build chain and separate server/client dependency graphs add review steps without improving the required behavior. | FR-33; C4.1.11–C4.1.14 |
| HTTP application | FastAPI + Uvicorn, one worker process | Django; Flask; multiple Uvicorn workers | Django adds an ORM/admin surface Kivi does not use; Flask requires more hand-written validation; multiple workers violate the singular-writer review arrangement. | API-01–API-18; C4.3.1, C4.3.3 |
| Validation | Pydantic discriminated models with `extra="forbid"` | Ad hoc dictionary validation | The API must reject unknown fields and malformed structured model output with field-level errors. | API contract rules; FR-04, FR-12 |
| User interface | Server-rendered Jinja2 templates, checked-in CSS, and small vanilla-JS modules | React/Vite SPA; desktop shell | A SPA or Electron/Tauri build adds Node, bundling, hydration, and packaging steps. The required three work surfaces and drawers do not need them. | FR-01, FR-26, FR-29, FR-33 |
| Durable store | SQLite in WAL mode through Python's `sqlite3`; explicit repository functions and transactions | PostgreSQL; SQLAlchemy ORM | PostgreSQL adds a service and credentials. An ORM obscures the exact writes and migrations that reviewers need to inspect; the v1 scale does not justify it. | FR-31; C4.3.1, C4.3.3; E2 |
| Migrations | Ordered, idempotent SQL files plus a small stdlib migration runner | Alembic | Alembic is useful with SQLAlchemy but otherwise adds configuration and generated indirection. Plain SQL is the artifact under review. | FR-31, FR-33; C4.1.10–C4.1.12 |
| Lexical search | SQLite FTS5 with `unicode61 remove_diacritics 2` | Elasticsearch/OpenSearch; LIKE scans | A search service is disproportionate; LIKE has poor token matching and no useful rank. FTS5 ships with the chosen SQLite build and is preflight-checked. | FR-02, FR-18–FR-19; C4.3.4 |
| Semantic search | Ollama `/api/embed`; float32 vectors stored in SQLite and cosine-scored in Python over the low hundreds of current memories | Hosted embeddings; a vector database; native SQLite vector extension | Hosted embeddings cost money and send memory off-device. A vector service or native extension adds setup/platform risk. A bounded linear scan is simple and adequate at the declared scale. | FR-18–FR-19, FR-31; C4.3.4; Non-goal 13 |
| Local language model | Ollama `/api/chat` with JSON-schema output for extraction, admission labels, relationship judging, routing, and grounded wording | Hosted LLM API; separate specialist models; handwritten-only NLP | Hosted inference violates the no-spend/local constraint. Several models multiply downloads and failure modes. Rules alone cannot perform the semantic extraction and relation judgments required by the spec. | FR-07–FR-12, FR-17–FR-25, FR-32; C4.3.5 |
| Initial model set | `qwen3:8b` for language/tool tasks and `nomic-embed-text` for embeddings | A larger model; a different model per stage | One moderate model is more likely to run on reviewer hardware and keeps behavior comparable across stages. Larger/specialised sets increase RAM, disk, and setup cost before corpus evidence justifies them. | FR-32–FR-33; C4.4 model/cost measurements |
| Model pinning | `config/models.lock.json` records Ollama tag, manifest digest, quantisation, context length, and prompt-schema version; startup refuses a digest mismatch | Trust mutable tags; commit model weights | Mutable tags break reproducibility. Committing multi-GB weights makes the repository impractical. The documented bootstrap pulls then verifies the digest. | FR-05, FR-31–FR-33; C4.3.5 |
| Ollama client | Direct local HTTP through `httpx`, bound by default to `127.0.0.1:11434` | Ollama Python SDK | The REST contract is small; direct calls expose timeouts, request options, response usage, and errors without another versioned wrapper. | FR-12, FR-29, FR-32 |
| Deferred work | A durable SQLite `jobs` table consumed serially by an in-process async worker | Celery/RQ + Redis; OS cron | A broker creates two extra services and failure domains. Cron cannot provide per-record leases, attempts, or immediate progress. | FR-03, FR-06, FR-12, FR-31 |
| Date handling | RFC 3339 parsing with stdlib `datetime`; a small explicitly tested parser for the supported relative phrases | LLM-only time resolution; Duckling service | Model-only parsing can invent dates; Duckling adds another runtime. Unresolved phrases abstain. | FR-13, FR-25; Open Question 23 |
| Packaging | `venv` + a fully pinned `requirements.lock`; PowerShell and POSIX commands in `RUN.md` | Docker as the primary path; `uv` prerequisite | Docker and `uv` are useful, but either becomes another prerequisite. A standard Python environment is the shortest clean-clone path. A container may be added only as a secondary path. | FR-33; C4.1.11–C4.1.14 |
| Tests/evaluation | `pytest`, FastAPI's in-process client, checked-in corpus/cases, and a CLI runner using the real database and Ollama paths | Notebook evaluation; external observability/eval SaaS; browser automation suite | Notebooks and SaaS are not the shipped path. A browser driver adds a large download; DOM contracts and a documented manual UI pass cover the small server-rendered UI. | FR-32–FR-33 |
| Logs | One-line JSON to stderr/stdout, implemented with stdlib logging | Cloud logging/APM | External observability costs money and is not the decision record; durable inspection belongs in SQLite and the specified endpoints. | FR-29–FR-33; E4 |

**ASSUMPTION (Open Questions 1–14 and 50):** the initial runnable configuration is `N=3` independent transcripts, 180-day observation decay, 60-day hypothesis expiry, top 12 memories/4,000 UTF-8-character context budget, 8 contradiction candidates, 2 confirmation prompts per ISO week in `Asia/Kolkata`, 3 extraction attempts with backoff of 5 and 30 seconds, 16,384 characters per transcript, 1,000 records/20 MiB per import, and no pin count cap. These values live only in `config/defaults.toml`, are copied into every trace/evaluation, and are release candidates to be replaced by corpus-backed values. No pass claim may depend on an unreported default. (Trace: C4.4; Open Questions 1–14.)

The model tags above are likewise **ASSUMPTION**, not a claim that they meet quality targets. Before release, the generated `models.lock.json` must contain observed digests and the full acceptance suite must pass on those exact artifacts. Ollama is a documented prerequisite because it is not vendored. After the initial package and model pulls, all runtime and evaluation operations are local and make no network calls. (Trace: FR-32–FR-33; Open Questions 49–50.)

## 3. ARCHITECTURE

### 3.1 Process and module boundaries

The primary review arrangement is one Uvicorn process and one local Ollama daemon. Uvicorn serves HTML and `/v1`; its lifespan starts exactly one serial job consumer. SQLite is the sole authority. Ollama is stateless computation and never becomes a source of truth. (Trace: FR-31–FR-33; C4.3.1–C4.3.6.)

| Proposed location | Responsibility | May write | Trace |
|---|---|---|---|
| `src/kivi/api/` | Implements exactly API-01–API-18, common errors, idempotency, and localhost/token policy. | Through services only. | API-01–API-18 |
| `src/kivi/web/` | Dictation, Hey Kivi, Memory, Why, transcript, import, and evaluation views in human language. | Calls the public service contracts. | FR-01, FR-26, FR-29–FR-30, FR-33 |
| `src/kivi/domain/contracts.py` | Enums and Pydantic contracts for transcripts, three memory types, three tiers, outcomes, tools, and model schemas. | Nothing. | FR-01, FR-06–FR-08, FR-13–FR-17 |
| `src/kivi/services/ingest.py` | Validates/idempotently stores imports and live turns and creates held durable jobs. | Imports, transcripts, jobs, idempotency. | FR-03–FR-06 |
| `src/kivi/services/extract.py` | Calls Ollama once per transcript for atomic candidates and semantic category labels; rejects malformed/ambiguous output. | Attempts and candidate decisions through the memory writer. | FR-07–FR-12 |
| `src/kivi/services/admission.py` | Executes exclusion, third-party/work-level, type, completeness, and suppression gates in that exact order. | Reason-only decisions; no rejected body. | FR-08–FR-09, FR-12 |
| `src/kivi/services/consolidate.py` | Canonicalises, finds at most `s` candidates, judges same/overlap/contradiction, merges evidence, and resolves precedence. | Memories, versions, provenance, relations. | FR-10–FR-11, FR-14 |
| `src/kivi/services/retrieve.py` | Runs FTS, embedding cosine, and one-hop entity legs once; performs deterministic reciprocal-rank fusion and bounded raw fallback. | Retrieval snapshot/candidates only. | FR-18–FR-19, FR-23 |
| `src/kivi/services/disclose.py` | Applies surface and Anbu/Koottu/Daari rules after the Hey Kivi retrieval snapshot exists. | Candidate dispositions and prompt ledger. | FR-02, FR-19–FR-22 |
| `src/kivi/services/tools.py` | Defines only `recall_search`, `draft_reply`, and `schedule_reschedule`; validates tool results and citations. | Internal schedule only for the schedule tool. | FR-17–FR-25 |
| `src/kivi/services/actions.py` | Atomically confirms, corrects, demotes, forgets, pins, reveals, and changes permission. | Memory state, suppression, audit events, idempotency. | FR-15–FR-16, FR-20, FR-27–FR-28 |
| `src/kivi/services/tracing.py` | Opens/finalises traces and records every candidate disposition, citation, failure, timing, model call, token count, and zero-fee cost method. | Trace tables. | FR-29–FR-30, FR-32 |
| `src/kivi/worker.py` | Claims one leased job at a time in event-time order, retries durably, resumes expired leases, and runs lifecycle/evaluation jobs. | Jobs and service-owned state. | FR-05–FR-06, FR-12, FR-16, FR-32 |
| `src/kivi/storage/` and `migrations/` | Connection policy, `BEGIN IMMEDIATE` write transactions, SQL repositories, schema, views, FTS maintenance, reset, and seed. | All tables, only behind explicit repositories. | FR-31–FR-33; C4.3.3 |
| `src/kivi/evaluation/` | Loads non-ingested test cases, snapshots starting state, runs public contracts, asserts ACs, and writes reports. | Evaluation tables/artifacts. | FR-32–FR-33 |

Public-contract ownership is fixed: `api/imports.py` owns API-01/API-02; `api/dictations.py` API-03; `api/hey_kivi.py` API-04; `api/permission.py` API-05/API-06; `api/memories.py` API-07/API-08/API-09/API-10/API-11/API-12/API-13; `api/inspection.py` API-14/API-15/API-16; and `api/evaluations.py` API-17/API-18. `services/tools.py` exposes exactly TOOL-01, TOOL-02, and TOOL-03 to the router. No other `/v1` route or model-callable schema is registered. (Trace: FR-17, API-01–API-18, TOOL-01–TOOL-03.)

There is deliberately no plug-in framework, event bus, graph database, external vector store, admin dashboard, or second account boundary. Adding any is **SCOPE CREEP** because it serves no v1 requirement. (Trace: Non-goals 4, 8–10, 13, 15; E1, E5.)

### 3.2 Text diagram

```text
                                    local machine
+----------------------+       +-----------------------------------------+
| Browser / CLI        | HTTP  | kivi (one Uvicorn process)              |
| - Dictation          +------>| API + server-rendered UI                |
| - Hey Kivi           |       |                                         |
| - Memory / Why       |       | write services      read services       |
+----------------------+       | validate -> outbox  retrieve -> disclose|
                               |              |       -> 1 of 3 tools    |
                               |              v              |            |
                               |        serial worker         v            |
                               |        extract/admit     trace validator |
                               |        merge/project          |           |
                               +-------------+------------------+----------+
                                             |                  |
                                   SQL txns  v                  v local HTTP
                               +-------------------+      +---------------+
                               | SQLite + FTS5     |      | Ollama        |
                               | truth + audit     |      | qwen3:8b      |
                               | jobs + vectors    |      | nomic embed   |
                               +-------------------+      +---------------+
```

### 3.3 Write path: input to stored memory

1. **Accept synchronously.** The endpoint parses strict JSON, validates RFC 3339 time/size/metadata, checks transcript ID plus SHA-256 content fingerprint, and rejects conflicting reuse. Batch records are sorted by `(occurred_at, transcript_id)` for scheduling; invalid items receive content-free per-index errors while valid items continue. (Trace: FR-04–FR-05; API-01, API-03–API-04.)
2. **Commit the source before responding.** One `BEGIN IMMEDIATE` transaction writes the user-authored `transcripts` row, its `import_records` link if any, an idempotency record, and a `jobs` row in `held` state. A dictation response applies only canonical entity aliases and stated formatting rules, records those allowed uses, and returns the supplied formatted text after deterministic corrections. A Hey Kivi turn is excluded from its own retrieval snapshot. (Trace: FR-01–FR-03, FR-05, FR-07; AC-FR-02.)
3. **Release after the response boundary.** A response-finaliser changes `held` to `queued` only after the handler has yielded the response. On process restart, recovery queues held jobs whose source request reached a terminal persisted result; a held record without a terminal result remains inspectable and is not guessed complete. This is the application-observable meaning of “after the response”; TCP delivery cannot be proven by the server. (Trace: FR-03, FR-06, FR-12.)
4. **Claim in event-time order, deferred.** The single worker claims the oldest available extraction job by `(transcripts.occurred_at, jobs.created_at, jobs.job_id)`, gives it a lease, and moves both job and transcript to `processing`. Expired leases become `retrying` on startup. (Trace: FR-05–FR-06, FR-12; C4.3.3.)
5. **Extract one transcript.** `qwen3:8b` receives only the eligible user-authored text, allowed lexical entity aliases, the three type schemas, the closed relation vocabulary, and the exclusion taxonomy. It returns an array of atomic candidates with direct/observed/hypothesis basis and a semantic category. Temperature is zero, a fixed seed/options set is supplied, and JSON schema is enforced. Raw application context, assistant turns, and tool results are not in this prompt. (Trace: FR-07–FR-09, FR-12, FR-14; C4.3.5.)
6. **Apply gates deterministically.** For each candidate, code evaluates category exclusion, third-party/work-level eligibility, type, completeness, then active suppression. An `uncertain` classifier value fails closed. Dropped bodies and raw model output are never persisted; only index, reason, count, safe model metadata, and `read_not_kept` survive. Good candidates from a partially failed array remain valid. (Trace: FR-08–FR-09, FR-12, FR-30.)
7. **Canonicalise and compare.** Code builds the typed semantic key and its SHA-256. Exact keys are handled without a model. Otherwise FTS/embedding/entity lookup proposes at most `s` current memories; a single structured Ollama comparison per candidate labels each pair `same_fact`, `overlap`, `contradiction`, or `unrelated`. Any judge failure takes the safe `new/separate` direction. (Trace: FR-10–FR-11; C4.3.4; Open Question 5.)
8. **Commit one candidate atomically.** A transaction either creates a typed memory/version/provenance/entity link, adds one new transcript source and version to an existing memory, records overlap, or records/resolves a contradiction. The same transcript cannot be evidence twice. Below-stated conflicts use tier then event time; stated conflicts stay unresolved; explicit corrections create a stated replacement and suppression together or neither. Every mutation increments `runtime_state.memory_generation`. (Trace: FR-10–FR-14, FR-27–FR-28, FR-31.)
9. **Project and finish.** The worker obtains the local embedding before finalising the candidate when possible. If projection fails after a valid memory commit, the memory is lexical-only, the transcript becomes `partially_processed`, and a durable projection retry is queued. The final transcript outcome is exactly one of the five specified classes; attempts, model usage, elapsed time, and USD 0.00 service cost are stored. (Trace: FR-06, FR-12, FR-29–FR-32.)

Tier assignment is explicit. A direct user assertion becomes stated. A model-proposed recurring work behavior enters as an observed `candidate`; independent matching transcripts add evidence and status becomes active at `N`, without changing tier. Once such an observation is active, one bounded consolidation call may propose a work-level question. The question passes the complete admission pipeline again, is stored as hypothesised, copies the supporting transcript provenance with `derived_evidence`, and is never acted on. **ASSUMPTION (Open Question 3):** a hypothesis is “re-raised” only when a new distinct transcript adds provenance to its parent observation; retrieval alone does not refresh it. This creates no narrative/profile artifact. (Trace: FR-07–FR-08, FR-10, FR-14–FR-16; Non-goals 5–8.)

Direct Confirm/Correct/Demote/Forget/Pin actions do not wait for this worker. They use one synchronous transaction because a returned success must immediately govern retrieval and negative updates must not be separable from their suppression. (Trace: FR-27–FR-28.)

### 3.4 Read path: user request to answer

1. **Freeze the request.** `POST /v1/hey-kivi/requests` synchronously stores the user-authored turn as held, opens an `interaction_traces` row, reads the persistent permission, computes whether the text is an explicit Daari invitation, and records the current `memory_generation`. It never accepts a hidden Daari flag. (Trace: FR-01, FR-19–FR-22, FR-29; API-04.)
2. **Apply effective lifecycle without waiting for maintenance.** The query excludes an unpinned observation/hypothesis whose configured window has elapsed even if the deferred sweep never ran. Stated and pinned rows remain eligible. A later sweep only materialises the same status and audit event. (Trace: FR-16.)
3. **Retrieve once.** The service runs FTS5, one local query embedding/cosine scan, and one-hop entity expansion against the same generation. It combines ranks with fixed reciprocal-rank fusion, then orders ties by relevance, pinned, tier, evidence, recency, and stable memory ID. There is no LLM reranker. All candidates and leg failures are written before disclosure. (Trace: FR-18–FR-19, FR-23; C4.3.4.)
4. **Apply disclosure separately.** Dictation never reaches this service. Hey Kivi considers all types/tiers, then marks each candidate used, withheld, near miss, historical-only, or budget-dropped. Anbu can use stated only and emits one content-free notice if an observation was withheld. Koottu may present but never apply an observation. Daari may expose at most one relevant allowed hypothesis as a question for this request. (Trace: FR-02, FR-19–FR-22.)
5. **Select at most one tool.** The model sees the fixed three JSON schemas. Code rejects any other name. Invalid/no selection returns unsupported or abstained; there is no tool loop or second attempt. (Trace: FR-17; C4.4 call limits.)
6. **Execute and validate.** Recall reads the frozen snapshot and may run exactly one labelled FTS raw-transcript fallback on a compiled-memory miss. Drafting uses instruction, supplied context, and permitted memories without sending. Scheduling writes only an internal event and requires a grounded event plus resolved absolute time. A postcondition checker requires every factual claim to cite a permitted current memory or labelled raw source; otherwise the whole result abstains. (Trace: FR-18, FR-23–FR-25.)
7. **Commit before returning.** Answer/abstention/unsupported state, candidate dispositions, tool input/result, citations, failures, timings, model usage, and cost method are committed with the idempotency response. If this commit fails, the endpoint returns `503` and a mutating tool transaction is rolled back. After the response boundary, the held user-turn extraction job is released. (Trace: FR-23, FR-25, FR-29, FR-31; API contract rules.)

### 3.5 Synchronous, deferred, and permanent non-completion

| Work | Timing | If it never runs | Trace |
|---|---|---|---|
| Validation, source/idempotency commit, dictation lexical formatting | Synchronous | Request fails; no claimed success. | FR-03–FR-05 |
| Hey Kivi retrieval, permission, one tool, grounding validation, trace commit | Synchronous | Returns a traced abstention if computation fails; `503` only if state/trace cannot commit. | FR-17–FR-25, FR-29 |
| Correction/demotion/forget suppression transaction; pin/permission; schedule mutation | Synchronous | Original state remains and action reports failure. | FR-25, FR-27–FR-28 |
| Extraction, admission, consolidation, projection | Deferred after response | Transcript remains raw-searchable and labelled `not processed by memory yet`; job state/lease/error remains visible. It is never marked processed. | FR-03, FR-06, FR-12, FR-30 |
| Retry | Deferred at 5 s and 30 s | Third failed attempt sets transcript/job `quarantined`; import becomes terminal `completed_with_quarantine`. | FR-06, FR-12 |
| Lifecycle materialisation | Deferred daily and at startup | Read-time eligibility still enforces decay/expiry; only the audit row/status update lags. | FR-16 |
| Evaluation | Deferred serial job | Evaluation stays non-terminal with visible job state; it cannot fabricate a report. | FR-32–FR-33 |

## 4. DATA MODEL

### 4.1 Conventions and invariants

SQLite `STRICT` tables are used. Times are non-null RFC 3339 strings normalised to UTC (`...Z`), while the original offset remains in source JSON where supplied. Booleans are `INTEGER NOT NULL CHECK(value IN (0,1))`. JSON is `TEXT NOT NULL CHECK(json_valid(value))`; `{}` or `[]` is used instead of SQL null when “present but empty” is meaningful. IDs are ULID-shaped opaque text generated in application code. Foreign keys are enabled on every connection. (Trace: API contract-wide rules; FR-13; C4.3.3.)

`ON DELETE` is `RESTRICT` unless shown. The writer uses `BEGIN IMMEDIATE`, performs all dependent rows, validates the aggregate, and commits once. Cross-row rules—an active memory has provenance, evidence count equals distinct evidence sources, and a trace citation resolves—are asserted in the same repository transaction and by `PRAGMA foreign_key_check` plus invariant tests. (Trace: FR-10, FR-13, FR-27–FR-31.)

Column roles are explicit. Columns that exist only for later inspection/audit and are never read to decide a future answer are: migration name/hash/time; audit request/detail/content-free/creation fields; import usage/cost/timestamps; import-record supplied ID/error/creation fields; all `extraction_attempts` and `candidate_decisions` fields; all historical `memory_versions` fields; relation reason/model/timestamps/event; tombstone fields except ID resolution; entity creation/update times; embedding tag/dimensions/content hash/creation time; completed trace/snapshot ranks, timing, usage, cost, and model-call rows; prompt selection explanation; state manifests; and evaluation result/metric fields. Some inspection fields also enforce integrity at write time (hashes, source IDs, model digest, citation rows) but do not change later semantic ranking. Current `memories`, active `memory_relations`, `suppressions`, `runtime_state`, FTS/vector values, entity links, job state, permission, and internal events are behavioral. (Trace: FR-13, FR-19, FR-29–FR-32.)

The discriminated `semantic_json` payload is closed:

- `entity`: `{subject, relation, object}` where relation is one of `works-at`, `client-contact-for`, `works-on`, `owns`, `part-of`.
- `preference`: `{subject:"user", scope, preference, polarity:"prefer"|"avoid"}`.
- `episode`: `{title, starts_at, ends_at, participants:[entity_id...], time_precision}`; `starts_at` is required and `ends_at` may be null only in JSON to mean an instant/unknown end.

Hypothesised content must end in `?`; semantic payload describes the subject of the question, not a claimed truth. The application rejects fields outside each schema. **ASSUMPTION:** the five relation values are treated as final for v1; unsupported relations are dropped with `UNSUPPORTED_RELATION`, not flattened into prose. (Trace: FR-07, FR-13–FR-14; Open Questions 19–20, 48.)

### 4.2 Core, ingestion, and work queue

#### `schema_migrations`

Why it exists: proves exactly which checked-in schema transformations a clone has applied. (Trace: FR-31, FR-33.)

```text
version             INTEGER  PK NOT NULL
name                TEXT        NOT NULL UNIQUE
sha256              TEXT        NOT NULL CHECK(length(sha256)=64)
applied_at          TEXT        NOT NULL
```

#### `runtime_state`

Why it exists: stores the one-user permission and the generation used to freeze a consistent retrieval view. (Trace: FR-19–FR-22, FR-31.)

```text
singleton_id        INTEGER  PK NOT NULL DEFAULT 1 CHECK(singleton_id=1)
state_id            TEXT        NOT NULL UNIQUE
memory_generation   INTEGER     NOT NULL DEFAULT 0 CHECK(memory_generation>=0)
permission          TEXT        NOT NULL DEFAULT 'anbu' CHECK(permission IN ('anbu','koottu'))
permission_changed_at TEXT      NOT NULL
created_at          TEXT        NOT NULL
updated_at          TEXT        NOT NULL
```

Indexes: the primary key and unique `state_id` indexes only; there is one row.

#### `idempotency_records`

Why it exists: prevents replayed actions and tools from repeating writes and preserves the original response. (Trace: FR-05, FR-25, FR-27–FR-28; contract-wide idempotency.)

```text
scope               TEXT        NOT NULL
idempotency_key     TEXT        NOT NULL
request_sha256      TEXT        NOT NULL CHECK(length(request_sha256)=64)
state               TEXT        NOT NULL CHECK(state IN ('in_progress','completed','failed'))
http_status         INTEGER     NULL
response_json       TEXT        NULL CHECK(response_json IS NULL OR json_valid(response_json))
created_at          TEXT        NOT NULL
completed_at        TEXT        NULL
PRIMARY KEY (scope, idempotency_key)
CHECK ((state='completed') = (http_status IS NOT NULL AND response_json IS NOT NULL))
```

Index: `idx_idempotency_created(created_at)` for reset/reporting.

#### `audit_events`

Why it exists: is the timestamped receipt for user, system, and operator state changes, including confirmations and lifecycle changes. It stores no forgotten or rejected content. (Trace: FR-14–FR-16, FR-27–FR-28, OP-01.)

```text
event_id            TEXT     PK NOT NULL
kind                TEXT        NOT NULL CHECK(kind IN
                    ('permission_changed','confirmed','corrected','demoted','forgotten',
                     'pinned','unpinned','observation_revealed','decayed','expired',
                     'transcript_replayed','reset'))
actor               TEXT        NOT NULL CHECK(actor IN ('user','system','operator'))
target_kind         TEXT        NOT NULL CHECK(target_kind IN
                    ('memory','permission','trace','transcript','import','system'))
target_id           TEXT        NULL
request_id          TEXT        NULL
idempotency_key     TEXT        NULL
details_json        TEXT        NOT NULL DEFAULT '{}' CHECK(json_valid(details_json))
content_free        INTEGER     NOT NULL CHECK(content_free IN (0,1))
occurred_at         TEXT        NOT NULL
created_at          TEXT        NOT NULL
```

Indexes: `idx_audit_target(target_kind,target_id,occurred_at)` and `idx_audit_kind_time(kind,occurred_at)`. `UNIQUE(kind,idempotency_key)` applies when the key is non-null. Application validation limits `details_json` to IDs, before/after status, reason codes, and receipts.

#### `imports`

Why it exists: gives each corpus submission durable progress, completion, usage, and cost accounting. (Trace: FR-04–FR-06, API-01–API-02.)

```text
import_id           TEXT     PK NOT NULL
state               TEXT        NOT NULL CHECK(state IN
                    ('queued','processing','processed','partially_processed','retrying','quarantined',
                     'completed','completed_with_quarantine','failed'))
request_sha256      TEXT        NOT NULL CHECK(length(request_sha256)=64)
submitted_count     INTEGER     NOT NULL CHECK(submitted_count>=0)
accepted_count      INTEGER     NOT NULL CHECK(accepted_count>=0)
rejected_count      INTEGER     NOT NULL CHECK(rejected_count>=0)
created_at          TEXT        NOT NULL
started_at          TEXT        NULL
completed_at        TEXT        NULL
model_calls         INTEGER     NOT NULL DEFAULT 0 CHECK(model_calls>=0)
input_tokens        INTEGER     NOT NULL DEFAULT 0 CHECK(input_tokens>=0)
output_tokens       INTEGER     NOT NULL DEFAULT 0 CHECK(output_tokens>=0)
service_cost_microusd INTEGER   NOT NULL DEFAULT 0 CHECK(service_cost_microusd>=0)
CHECK(submitted_count=accepted_count+rejected_count)
```

Indexes: `idx_imports_state_created(state,created_at)`.

#### `transcripts`

Why it exists: is the immutable user-authored source and bounded raw-fallback corpus. (Trace: FR-03–FR-07, FR-13, FR-18, FR-30.)

```text
transcript_id       TEXT     PK NOT NULL
surface             TEXT        NOT NULL CHECK(surface IN ('dictation','hey_kivi'))
raw_asr             TEXT        NOT NULL CHECK(length(trim(raw_asr))>0)
formatted_text      TEXT        NOT NULL CHECK(length(trim(formatted_text))>0)
occurred_at         TEXT        NOT NULL
metadata_json       TEXT        NOT NULL CHECK(json_valid(metadata_json))
content_sha256      TEXT        NOT NULL CHECK(length(content_sha256)=64)
received_at         TEXT        NOT NULL
processing_state    TEXT        NOT NULL CHECK(processing_state IN
                    ('queued','processing','processed','partially_processed','retrying','quarantined'))
extraction_outcome  TEXT        NULL CHECK(extraction_outcome IS NULL OR extraction_outcome IN
                    ('nothing_found','candidates_stored','all_dropped','partially_processed','failed_quarantined'))
attempt_count       INTEGER     NOT NULL DEFAULT 0 CHECK(attempt_count>=0)
read_not_kept_count INTEGER     NOT NULL DEFAULT 0 CHECK(read_not_kept_count>=0)
processed_at        TEXT        NULL
last_error_code     TEXT        NULL
CHECK((processing_state IN ('processed','partially_processed','quarantined')) =
      (extraction_outcome IS NOT NULL))
```

Indexes: unique primary ID; `idx_transcripts_event(occurred_at,transcript_id)` for ordering; `idx_transcripts_processing(processing_state,occurred_at)`; `idx_transcripts_sha(content_sha256)`. `raw_asr`, `formatted_text`, and `metadata_json` are inspection/provenance fields; only FTS and explicit provenance views read them at runtime. A Hey Kivi user turn stores its literal `text` in both text columns because there is no ASR transform. Application/tool/assistant context is not put in this table.

#### `import_records`

Why it exists: maps ordered batch positions—including rejected positions—to their import without retaining invalid bodies. (Trace: FR-04–FR-06, FR-30.)

```text
import_id           TEXT        NOT NULL REFERENCES imports(import_id) ON DELETE CASCADE
ordinal             INTEGER     NOT NULL CHECK(ordinal>=0)
supplied_transcript_id TEXT     NULL
transcript_id       TEXT        NULL REFERENCES transcripts(transcript_id)
acceptance          TEXT        NOT NULL CHECK(acceptance IN ('accepted','replayed','rejected','conflict'))
error_code          TEXT        NULL
error_field         TEXT        NULL
created_at          TEXT        NOT NULL
PRIMARY KEY(import_id,ordinal)
CHECK((acceptance IN ('accepted','replayed')) = (transcript_id IS NOT NULL))
CHECK((acceptance IN ('rejected','conflict')) = (error_code IS NOT NULL))
```

Indexes: `idx_import_records_transcript(transcript_id)` and `idx_import_records_acceptance(import_id,acceptance)`. `supplied_transcript_id`, error code, and field are inspection-only.

#### `jobs`

Why it exists: makes extraction, projection repair, lifecycle materialisation, and evaluation resumable without Redis. (Trace: FR-03, FR-06, FR-12, FR-16, FR-32.)

```text
job_id              TEXT     PK NOT NULL
kind                TEXT        NOT NULL CHECK(kind IN ('extract','project','lifecycle','evaluate'))
transcript_id       TEXT        NULL REFERENCES transcripts(transcript_id) ON DELETE CASCADE
memory_id           TEXT        NULL REFERENCES memories(memory_id) ON DELETE CASCADE
evaluation_id       TEXT        NULL REFERENCES evaluation_runs(evaluation_id) ON DELETE CASCADE
state               TEXT        NOT NULL CHECK(state IN
                    ('held','queued','processing','retrying','completed','quarantined','failed'))
attempt_count       INTEGER     NOT NULL DEFAULT 0 CHECK(attempt_count>=0)
max_attempts        INTEGER     NOT NULL CHECK(max_attempts>0)
not_before_at       TEXT        NOT NULL
lease_owner         TEXT        NULL
lease_until         TEXT        NULL
last_error_code     TEXT        NULL
payload_json        TEXT        NOT NULL DEFAULT '{}' CHECK(json_valid(payload_json))
created_at          TEXT        NOT NULL
updated_at          TEXT        NOT NULL
CHECK((state='processing') = (lease_owner IS NOT NULL AND lease_until IS NOT NULL))
```

Indexes: `idx_jobs_claim(state,not_before_at,created_at,job_id)`, `idx_jobs_transcript(transcript_id)`, `idx_jobs_memory(memory_id)`, and `idx_jobs_evaluation(evaluation_id)`. SQLite permits foreign keys to tables introduced by later migrations. Target-shape checks remain application-enforced: extract has a transcript, project a memory, evaluate an evaluation, and lifecycle no target.

#### `extraction_attempts`

Why it exists: preserves every attempt and safe failure stage needed to distinguish retry, partial success, and quarantine. (Trace: FR-06, FR-12, FR-30.)

```text
attempt_id          TEXT     PK NOT NULL
job_id              TEXT        NOT NULL REFERENCES jobs(job_id) ON DELETE CASCADE
transcript_id       TEXT        NOT NULL REFERENCES transcripts(transcript_id) ON DELETE CASCADE
attempt_no          INTEGER     NOT NULL CHECK(attempt_no>0)
outcome             TEXT        NOT NULL CHECK(outcome IN ('running','succeeded','partial','failed'))
failure_stage       TEXT        NULL CHECK(failure_stage IS NULL OR failure_stage IN
                    ('ollama_unavailable','extract','parse','admission','embedding','relation','commit'))
error_code          TEXT        NULL
safe_detail_json    TEXT        NOT NULL DEFAULT '{}' CHECK(json_valid(safe_detail_json))
started_at          TEXT        NOT NULL
completed_at        TEXT        NULL
UNIQUE(job_id,attempt_no)
```

Indexes: `idx_attempts_transcript(transcript_id,attempt_no)`. `safe_detail_json` is inspection-only and must not contain transcript, candidate, prompt, or model-output bodies.

#### `candidate_decisions`

Why it exists: records what happened to every extracted candidate without retaining the body of a rejected candidate. (Trace: FR-08–FR-12, FR-30.)

```text
decision_id         TEXT     PK NOT NULL
attempt_id          TEXT        NOT NULL REFERENCES extraction_attempts(attempt_id) ON DELETE CASCADE
transcript_id       TEXT        NOT NULL REFERENCES transcripts(transcript_id) ON DELETE CASCADE
candidate_index     INTEGER     NOT NULL CHECK(candidate_index>=0)
decision            TEXT        NOT NULL CHECK(decision IN
                    ('created','duplicate_transcript','same_fact_new_evidence','separate_overlapping_fact',
                     'superseded','unresolved_contradiction','dropped'))
memory_id           TEXT        NULL
related_memory_id   TEXT        NULL
reason_code         TEXT        NULL
read_not_kept       INTEGER     NOT NULL DEFAULT 0 CHECK(read_not_kept IN (0,1))
safe_detail_json    TEXT        NOT NULL DEFAULT '{}' CHECK(json_valid(safe_detail_json))
created_at          TEXT        NOT NULL
UNIQUE(attempt_id,candidate_index)
CHECK((decision='dropped') = (reason_code IS NOT NULL))
```

Indexes: `idx_candidate_transcript(transcript_id,candidate_index)`, `idx_candidate_memory(memory_id)`, and `idx_candidate_reason(reason_code)`. `safe_detail_json`, ranks, and reason are for inspection; the schema intentionally has no candidate-content column.

### 4.3 Memory, provenance, contradiction, and deletion

#### `memories`

Why it exists: is the current, queryable projection of one independently correctable semantic belief. (Trace: FR-07, FR-13–FR-16, FR-26.)

```text
memory_id           TEXT     PK NOT NULL
type                TEXT        NOT NULL CHECK(type IN ('entity','preference','episode'))
current_version     INTEGER     NOT NULL CHECK(current_version>0)
content             TEXT        NOT NULL CHECK(length(trim(content))>0)
semantic_json       TEXT        NOT NULL CHECK(json_valid(semantic_json))
semantic_key_sha256 TEXT        NOT NULL CHECK(length(semantic_key_sha256)=64)
tier                TEXT        NOT NULL CHECK(tier IN ('stated','observed','hypothesised'))
status              TEXT        NOT NULL CHECK(status IN
                    ('candidate','active','superseded','demoted','decayed','expired'))
pinned              INTEGER     NOT NULL DEFAULT 0 CHECK(pinned IN (0,1))
evidence_count      INTEGER     NOT NULL CHECK(evidence_count>=0)
first_seen_at       TEXT        NOT NULL
last_seen_at        TEXT        NOT NULL
last_confirmed_at   TEXT        NULL
projection_state    TEXT        NOT NULL CHECK(projection_state IN ('pending','ready','failed'))
created_at          TEXT        NOT NULL
updated_at          TEXT        NOT NULL
CHECK(first_seen_at<=last_seen_at)
CHECK(tier<>'hypothesised' OR substr(rtrim(content),-1)='?')
CHECK(last_confirmed_at IS NULL OR tier='stated')
CHECK(NOT pinned OR status NOT IN ('decayed','expired'))
```

Indexes: `idx_memories_surface(status,tier,pinned,last_seen_at,memory_id)`; `idx_memories_semantic_key(semantic_key_sha256,status)`; `idx_memories_projection(projection_state,status)`; `idx_memories_type_status(type,status)`. `evidence_count` and times are transactionally maintained query projections whose authoritative rows are provenance/events; all other columns affect runtime behavior.

`candidate` is below the observation threshold and is never exposed. Reaching `N` changes status to `active` but not tier, so it is not the forbidden automatic epistemic promotion. `superseded`, `demoted`, `decayed`, and `expired` are history/lifecycle states and cannot govern a current answer. An active memory participating in an unresolved contradiction is also excluded from factual use by the retrieval view. (Trace: FR-10–FR-16.)

#### `memory_versions`

Why it exists: preserves immutable before/after snapshots for evidence merges, confirmation, pinning, lifecycle, and supersession. (Trace: FR-11, FR-13, FR-27–FR-28.)

```text
memory_id           TEXT        NOT NULL REFERENCES memories(memory_id) ON DELETE CASCADE
version             INTEGER     NOT NULL CHECK(version>0)
content             TEXT        NOT NULL
semantic_json       TEXT        NOT NULL CHECK(json_valid(semantic_json))
semantic_key_sha256 TEXT        NOT NULL CHECK(length(semantic_key_sha256)=64)
tier                TEXT        NOT NULL CHECK(tier IN ('stated','observed','hypothesised'))
status              TEXT        NOT NULL CHECK(status IN
                    ('candidate','active','superseded','demoted','decayed','expired'))
pinned              INTEGER     NOT NULL CHECK(pinned IN (0,1))
evidence_count      INTEGER     NOT NULL CHECK(evidence_count>=0)
first_seen_at       TEXT        NOT NULL
last_seen_at        TEXT        NOT NULL
last_confirmed_at   TEXT        NULL
change_kind         TEXT        NOT NULL CHECK(change_kind IN
                    ('created','evidence_added','confirmed','pinned','unpinned','superseded',
                     'demoted','decayed','expired','projection_repaired'))
event_id            TEXT        NULL REFERENCES audit_events(event_id)
attempt_id          TEXT        NULL REFERENCES extraction_attempts(attempt_id)
changed_at          TEXT        NOT NULL
PRIMARY KEY(memory_id,version)
```

Indexes: `idx_memory_versions_changed(memory_id,changed_at)` and `idx_memory_versions_event(event_id)`. All version columns are for inspection except where copied to `memories`; runtime reads the current projection only. Repository code asserts the `memories` row exactly equals the version named by `current_version`.

#### `memory_provenance`

Why it exists: links every memory to the actual user transcript or explicit user action that supports it and prevents double-counting. (Trace: FR-07, FR-10, FR-13, FR-29–FR-30.)

```text
provenance_id       TEXT     PK NOT NULL
memory_id           TEXT        NOT NULL REFERENCES memories(memory_id) ON DELETE CASCADE
source_kind         TEXT        NOT NULL CHECK(source_kind IN ('transcript','user_action'))
transcript_id       TEXT        NULL REFERENCES transcripts(transcript_id)
event_id            TEXT        NULL REFERENCES audit_events(event_id)
role                TEXT        NOT NULL CHECK(role IN
                    ('direct_evidence','distributed_evidence','derived_evidence','confirmation','correction'))
counts_as_evidence  INTEGER     NOT NULL CHECK(counts_as_evidence IN (0,1))
added_in_version    INTEGER     NOT NULL CHECK(added_in_version>0)
source_occurred_at  TEXT        NOT NULL
created_at          TEXT        NOT NULL
CHECK((source_kind='transcript' AND transcript_id IS NOT NULL AND event_id IS NULL) OR
      (source_kind='user_action' AND event_id IS NOT NULL AND transcript_id IS NULL))
```

Indexes: partial unique `uq_memory_transcript_source(memory_id,transcript_id) WHERE transcript_id IS NOT NULL`; partial unique `uq_memory_event_source(memory_id,event_id) WHERE event_id IS NOT NULL`; `idx_provenance_transcript(transcript_id,memory_id)`; `idx_provenance_event(event_id)`. Only distinct transcript rows with `counts_as_evidence=1` contribute to `memories.evidence_count`; confirmation/correction actions establish authority but do not pretend to be independent observed evidence.

#### `memory_relations`

Why it exists: stores positive sameness/overlap decisions, supersession lineage, and unresolved or resolved contradictions instead of overwriting history. (Trace: FR-10–FR-11, FR-27.)

```text
relation_id         TEXT     PK NOT NULL
left_memory_id      TEXT        NOT NULL REFERENCES memories(memory_id) ON DELETE CASCADE
right_memory_id     TEXT        NOT NULL REFERENCES memories(memory_id) ON DELETE CASCADE
kind                TEXT        NOT NULL CHECK(kind IN ('overlaps','contradicts','supersedes'))
status              TEXT        NOT NULL CHECK(status IN ('informational','unresolved','resolved'))
winner_memory_id    TEXT        NULL REFERENCES memories(memory_id)
decision_rule       TEXT        NOT NULL CHECK(decision_rule IN
                    ('model_overlap','tier_then_event_time','stated_requires_user','explicit_correction'))
reason_code         TEXT        NOT NULL
judge_model_call_id TEXT        NULL REFERENCES model_calls(model_call_id)
created_at          TEXT        NOT NULL
resolved_at         TEXT        NULL
resolution_event_id TEXT        NULL REFERENCES audit_events(event_id)
CHECK(left_memory_id<>right_memory_id)
CHECK((status='resolved')=(winner_memory_id IS NOT NULL AND resolved_at IS NOT NULL))
```

Indexes: unique `uq_memory_relation_pair(kind,left_memory_id,right_memory_id)` after application canonicalises smaller/larger IDs for symmetric kinds; `idx_relation_left(left_memory_id,status)`; `idx_relation_right(right_memory_id,status)`; `idx_relation_unresolved(kind,status)`. `reason_code` and model-call link are inspection fields; `kind/status/winner` control current-truth eligibility.

#### `suppressions`

Why it exists: makes correction, demotion, and forgetting survive source replay without retaining the rejected belief as a readable memory. (Trace: FR-27–FR-28.)

```text
suppression_id      TEXT     PK NOT NULL
semantic_key_sha256 TEXT        NOT NULL CHECK(length(semantic_key_sha256)=64)
memory_type         TEXT        NOT NULL CHECK(memory_type IN ('entity','preference','episode'))
reason              TEXT        NOT NULL CHECK(reason IN ('corrected','not_me_anymore','forgotten'))
source_event_id     TEXT        NOT NULL REFERENCES audit_events(event_id)
original_memory_id  TEXT        NOT NULL
replacement_memory_id TEXT      NULL
active              INTEGER     NOT NULL DEFAULT 1 CHECK(active IN (0,1))
created_at          TEXT        NOT NULL
revoked_at          TEXT        NULL
CHECK((active=1)=(revoked_at IS NULL))
```

Indexes: unique `uq_active_suppression(memory_type,semantic_key_sha256) WHERE active=1`; `idx_suppression_event(source_event_id)`; `idx_suppression_original(original_memory_id)`. The match is **ASSUMPTION (Open Question 18):** exact canonical semantic-key equality. Canonical entity IDs, relation/predicate, normalised object, and explicit validity time feed the hash; wording does not. A genuinely new object/time is therefore not blocked. This is testable but cannot guarantee every paraphrase; see Risks and Spec Conflicts.

#### `memory_tombstones`

Why it exists: lets old traces resolve a forgotten opaque ID to “forgotten” without preserving its content or history. (Trace: FR-28–FR-29.)

```text
memory_id           TEXT     PK NOT NULL
suppression_id      TEXT        NOT NULL REFERENCES suppressions(suppression_id)
forget_event_id     TEXT        NOT NULL REFERENCES audit_events(event_id)
forgotten_at        TEXT        NOT NULL
```

Indexes: primary key only. Every field is inspection-only. The table is deliberately content-free and is not returned from `/v1/memories`; it is resolved only while rendering an older trace.

#### `entities`

Why it exists: provides canonical spelling and the nodes used for bounded one-hop retrieval. (Trace: FR-02, FR-09, FR-18–FR-19.)

```text
entity_id           TEXT     PK NOT NULL
canonical_name      TEXT        NOT NULL
kind                TEXT        NOT NULL CHECK(kind IN ('person','organisation','project','other_work'))
normalised_name     TEXT        NOT NULL
created_at          TEXT        NOT NULL
updated_at          TEXT        NOT NULL
UNIQUE(kind,normalised_name)
```

Indexes: `idx_entities_name(normalised_name)`. `other_work` cannot be used for a third-party characterisation; admission owns that rule.

#### `entity_aliases`

Why it exists: supports ASR spelling correction and exact entity expansion without semantic-memory access on the dictation path. (Trace: FR-02, AC-FR-02.)

```text
entity_id           TEXT        NOT NULL REFERENCES entities(entity_id) ON DELETE CASCADE
normalised_alias    TEXT        NOT NULL
display_alias       TEXT        NOT NULL
source_memory_id    TEXT        NOT NULL REFERENCES memories(memory_id) ON DELETE CASCADE
created_at          TEXT        NOT NULL
PRIMARY KEY(entity_id,normalised_alias)
```

Indexes: unique `idx_alias_lookup(normalised_alias,entity_id)`. `display_alias` is for inspection/UI; lookup uses the normalised value.

#### `memory_entities`

Why it exists: connects a memory to explicit entities for one-hop expansion without introducing a graph database. (Trace: FR-18–FR-19; C4.3.4.)

```text
memory_id           TEXT        NOT NULL REFERENCES memories(memory_id) ON DELETE CASCADE
entity_id           TEXT        NOT NULL REFERENCES entities(entity_id) ON DELETE CASCADE
role                TEXT        NOT NULL CHECK(role IN ('subject','object','participant','scope'))
PRIMARY KEY(memory_id,entity_id,role)
```

Indexes: `idx_memory_entities_entity(entity_id,memory_id)`.

#### `memory_embeddings`

Why it exists: stores a recomputable semantic-search projection separately from memory truth. (Trace: FR-18–FR-19, FR-31; C4.3.4.)

```text
memory_id           TEXT        NOT NULL REFERENCES memories(memory_id) ON DELETE CASCADE
memory_version      INTEGER     NOT NULL
model_tag           TEXT        NOT NULL
model_digest        TEXT        NOT NULL
dimensions          INTEGER     NOT NULL CHECK(dimensions>0)
vector_f32le        BLOB        NOT NULL
content_sha256      TEXT        NOT NULL CHECK(length(content_sha256)=64)
created_at          TEXT        NOT NULL
PRIMARY KEY(memory_id,memory_version,model_digest)
CHECK(length(vector_f32le)=dimensions*4)
```

Indexes: `idx_embeddings_model(model_digest,memory_id)`. The vector and digest exist for runtime retrieval; tag, dimensions, content hash, and created time also support inspection/rebuild. A mismatch between the current version/hash and this row sets `projection_state=pending` and cannot silently use a stale vector.

#### FTS virtual tables

Why they exist: implement exact/lexical memory retrieval, the bounded raw fallback, and entity-spelling lookup with no service dependency. (Trace: FR-02, FR-18–FR-19.)

```sql
CREATE VIRTUAL TABLE memory_fts USING fts5(
  memory_id UNINDEXED, memory_version UNINDEXED, content,
  tokenize='unicode61 remove_diacritics 2'
);
CREATE VIRTUAL TABLE transcript_fts USING fts5(
  transcript_id UNINDEXED, processing_state UNINDEXED, raw_asr, formatted_text,
  tokenize='unicode61 remove_diacritics 2'
);
```

Repository code updates these tables in the same transaction as the source row and verifies one current FTS row per non-forgotten memory/transcript. FTS rank is only one input; it is never treated as confidence. `transcript_fts` is queried once only after a compiled-memory miss, and hits retain their processing label. (Trace: FR-18, FR-23.)

### 4.4 Retrieval and decision trace

#### `interaction_traces`

Why it exists: is the durable decision record for every dictation/Hey Kivi terminal result and the backing artifact for the Why view. (Trace: FR-01, FR-23, FR-29, FR-31.)

```text
trace_id            TEXT     PK NOT NULL
request_id          TEXT        NOT NULL UNIQUE
surface             TEXT        NOT NULL CHECK(surface IN ('dictation','hey_kivi'))
user_transcript_id  TEXT        NULL REFERENCES transcripts(transcript_id)
idempotency_scope   TEXT        NULL
idempotency_key     TEXT        NULL
request_text        TEXT        NOT NULL
application_context_json TEXT   NOT NULL DEFAULT '[]' CHECK(json_valid(application_context_json))
turn_history_json   TEXT        NOT NULL DEFAULT '[]' CHECK(json_valid(turn_history_json))
permission          TEXT        NULL CHECK(permission IS NULL OR permission IN ('anbu','koottu'))
daari_invited       INTEGER     NOT NULL DEFAULT 0 CHECK(daari_invited IN (0,1))
available_tools_json TEXT       NOT NULL CHECK(json_valid(available_tools_json))
selected_tool       TEXT        NULL CHECK(selected_tool IS NULL OR selected_tool IN
                    ('recall_search','draft_reply','schedule_reschedule'))
router_reason_code  TEXT        NULL
search_description_json TEXT    NOT NULL DEFAULT '{}' CHECK(json_valid(search_description_json))
retrieval_snapshot_id TEXT      NULL UNIQUE
tool_input_json     TEXT        NULL CHECK(tool_input_json IS NULL OR json_valid(tool_input_json))
tool_result_json    TEXT        NULL CHECK(tool_result_json IS NULL OR json_valid(tool_result_json))
outcome             TEXT        NOT NULL CHECK(outcome IN ('in_progress','written','completed','abstained','unsupported','failed'))
answer_text         TEXT        NULL
abstention_code     TEXT        NULL
failure_json        TEXT        NOT NULL DEFAULT '[]' CHECK(json_valid(failure_json))
degradation_json    TEXT        NOT NULL DEFAULT '[]' CHECK(json_valid(degradation_json))
retrieval_ms        INTEGER     NULL CHECK(retrieval_ms IS NULL OR retrieval_ms>=0)
tool_ms             INTEGER     NULL CHECK(tool_ms IS NULL OR tool_ms>=0)
generation_ms       INTEGER     NULL CHECK(generation_ms IS NULL OR generation_ms>=0)
end_to_end_ms       INTEGER     NULL CHECK(end_to_end_ms IS NULL OR end_to_end_ms>=0)
model_calls         INTEGER     NOT NULL DEFAULT 0 CHECK(model_calls>=0)
input_tokens        INTEGER     NOT NULL DEFAULT 0 CHECK(input_tokens>=0)
output_tokens       INTEGER     NOT NULL DEFAULT 0 CHECK(output_tokens>=0)
service_cost_microusd INTEGER   NOT NULL DEFAULT 0 CHECK(service_cost_microusd>=0)
cost_method         TEXT        NOT NULL DEFAULT 'local_no_usage_fee'
redaction_state     TEXT        NOT NULL DEFAULT 'none' CHECK(redaction_state IN ('none','forgotten_memory'))
started_at          TEXT        NOT NULL
completed_at        TEXT        NULL
CHECK(outcome='in_progress' OR completed_at IS NOT NULL)
CHECK(surface='hey_kivi' OR selected_tool IS NULL)
```

Indexes: `idx_traces_completed(completed_at,trace_id)`, `idx_traces_transcript(user_transcript_id)`, `idx_traces_outcome(outcome,completed_at)`, and unique `(idempotency_scope,idempotency_key)` when non-null. Request/context/history are needed to reproduce a decision and inspect it; ranks, timing, usage, cost, failure, and router reason are inspection rather than answer behavior. `available_tools_json` is application-asserted to the exact sorted three-item set for Hey Kivi and `[]` for dictation.

#### `retrieval_snapshots`

Why it exists: freezes the pre-permission search and configuration so Anbu/Koottu comparisons do not rewrite history. (Trace: FR-19, FR-29, AC-FR-19.)

```text
snapshot_id         TEXT     PK NOT NULL
trace_id            TEXT        NOT NULL UNIQUE REFERENCES interaction_traces(trace_id) ON DELETE CASCADE
memory_generation   INTEGER     NOT NULL CHECK(memory_generation>=0)
query_text          TEXT        NOT NULL
query_embedding_model TEXT      NOT NULL
query_embedding_digest TEXT     NOT NULL
lexical_state       TEXT        NOT NULL CHECK(lexical_state IN ('ok','failed'))
semantic_state      TEXT        NOT NULL CHECK(semantic_state IN ('ok','degraded','failed'))
entity_state        TEXT        NOT NULL CHECK(entity_state IN ('ok','degraded','failed'))
raw_fallback_state  TEXT        NOT NULL CHECK(raw_fallback_state IN ('not_run','ok','failed'))
config_json         TEXT        NOT NULL CHECK(json_valid(config_json))
started_at          TEXT        NOT NULL
completed_at        TEXT        NOT NULL
```

Indexes: `idx_snapshot_generation(memory_generation,started_at)`. Except for generation and leg states, these fields are inspection/reproducibility data.

#### `retrieval_candidates`

Why it exists: records every item returned by any retrieval leg and exactly why it was used, withheld, ignored, or dropped by budget. (Trace: FR-18–FR-23, FR-29.)

```text
snapshot_id         TEXT        NOT NULL REFERENCES retrieval_snapshots(snapshot_id) ON DELETE CASCADE
candidate_no        INTEGER     NOT NULL CHECK(candidate_no>=0)
kind                TEXT        NOT NULL CHECK(kind IN ('memory','raw_transcript'))
memory_ref          TEXT        NULL
memory_version      INTEGER     NULL
transcript_id       TEXT        NULL REFERENCES transcripts(transcript_id)
lexical_rank        INTEGER     NULL CHECK(lexical_rank IS NULL OR lexical_rank>0)
semantic_rank       INTEGER     NULL CHECK(semantic_rank IS NULL OR semantic_rank>0)
entity_hops         INTEGER     NULL CHECK(entity_hops IS NULL OR entity_hops IN (0,1))
fused_score         REAL        NULL
pre_permission_rank INTEGER     NULL CHECK(pre_permission_rank IS NULL OR pre_permission_rank>0)
pinned_at_read      INTEGER     NULL CHECK(pinned_at_read IS NULL OR pinned_at_read IN (0,1))
tier_at_read        TEXT        NULL CHECK(tier_at_read IS NULL OR tier_at_read IN
                    ('stated','observed','hypothesised'))
evidence_at_read    INTEGER     NULL CHECK(evidence_at_read IS NULL OR evidence_at_read>=0)
last_seen_at_read   TEXT        NULL
processing_state_at_read TEXT   NULL
decision            TEXT        NOT NULL CHECK(decision IN
                    ('retrieved','used','withheld','near_miss','budget_dropped','historical_evidence','unusable_leg_failure'))
reason_code         TEXT        NOT NULL
required_permission TEXT        NULL CHECK(required_permission IS NULL OR required_permission IN ('koottu','daari_invitation'))
use_role            TEXT        NULL CHECK(use_role IS NULL OR use_role IN ('fact','style','entity','observation','question','historical'))
PRIMARY KEY(snapshot_id,candidate_no)
CHECK((kind='memory' AND memory_ref IS NOT NULL AND transcript_id IS NULL) OR
      (kind='raw_transcript' AND memory_ref IS NULL AND transcript_id IS NOT NULL))
```

Indexes: `idx_candidates_memory(memory_ref,snapshot_id)`, `idx_candidates_transcript(transcript_id,snapshot_id)`, `idx_candidates_decision(snapshot_id,decision,pre_permission_rank)`. All score/rank snapshots are inspection-only after the request; `decision`, permission, and use role are also consumed by answer validation. `memory_ref` intentionally resolves to either `memories` or `memory_tombstones`, which SQLite cannot express as one foreign key; trace rendering must resolve exactly one.

#### `trace_citations`

Why it exists: makes each returned factual claim traverse to a memory/version and dated source in one step. (Trace: FR-18, FR-23–FR-25, FR-29.)

```text
trace_id            TEXT        NOT NULL REFERENCES interaction_traces(trace_id) ON DELETE CASCADE
citation_no         INTEGER     NOT NULL CHECK(citation_no>=0)
claim_label         TEXT        NOT NULL
memory_ref          TEXT        NULL
memory_version      INTEGER     NULL
transcript_id       TEXT        NOT NULL REFERENCES transcripts(transcript_id)
source_role         TEXT        NOT NULL CHECK(source_role IN ('memory_evidence','raw_fallback'))
PRIMARY KEY(trace_id,citation_no)
CHECK((source_role='raw_fallback' AND memory_ref IS NULL AND memory_version IS NULL) OR
      (source_role='memory_evidence' AND memory_ref IS NOT NULL AND memory_version IS NOT NULL))
```

Indexes: `idx_citations_memory(memory_ref,trace_id)` and `idx_citations_transcript(transcript_id,trace_id)`. `claim_label` is a short answer-span description for inspection, not free-form reasoning.

#### `model_calls`

Why it exists: attributes local model identity, inputs by hash, usage, latency, outcome, and zero-fee cost to imports, traces, relation judgments, and evaluations. (Trace: FR-12, FR-29, FR-32.)

```text
model_call_id       TEXT     PK NOT NULL
owner_kind          TEXT        NOT NULL CHECK(owner_kind IN ('trace','job','attempt','relation','evaluation'))
owner_id            TEXT        NOT NULL
stage               TEXT        NOT NULL CHECK(stage IN
                    ('extract','admission','relation','query_embedding','memory_embedding','route','generate','judge'))
model_tag           TEXT        NOT NULL
model_digest        TEXT        NOT NULL
options_json        TEXT        NOT NULL CHECK(json_valid(options_json))
schema_version      TEXT        NOT NULL
prompt_sha256       TEXT        NOT NULL CHECK(length(prompt_sha256)=64)
response_sha256     TEXT        NULL CHECK(response_sha256 IS NULL OR length(response_sha256)=64)
outcome             TEXT        NOT NULL CHECK(outcome IN ('ok','timeout','invalid','error'))
error_code          TEXT        NULL
input_tokens        INTEGER     NULL CHECK(input_tokens IS NULL OR input_tokens>=0)
output_tokens       INTEGER     NULL CHECK(output_tokens IS NULL OR output_tokens>=0)
duration_ms         INTEGER     NOT NULL CHECK(duration_ms>=0)
service_cost_microusd INTEGER   NOT NULL DEFAULT 0 CHECK(service_cost_microusd=0)
started_at          TEXT        NOT NULL
completed_at        TEXT        NOT NULL
```

Indexes: `idx_model_calls_owner(owner_kind,owner_id,stage)`, `idx_model_calls_model(model_digest,stage)`, and `idx_model_calls_outcome(outcome,started_at)`. Prompt/output bodies are deliberately absent; hashes, options, schema, and metrics are inspection-only. Accepted structured facts live in memory/candidate-decision tables, while malformed or excluded model text is discarded. **ASSUMPTION (Open Question 35):** privacy wins over retaining raw malformed model output.

#### `confirmation_prompts`

Why it exists: enforces the visible weekly attention budget and proves that silence did not confirm anything. (Trace: FR-15.)

```text
prompt_id           TEXT     PK NOT NULL
trace_id            TEXT        NOT NULL REFERENCES interaction_traces(trace_id) ON DELETE CASCADE
memory_ref          TEXT        NOT NULL
week_key            TEXT        NOT NULL
selection_rank      INTEGER     NOT NULL CHECK(selection_rank>0)
selection_json      TEXT        NOT NULL CHECK(json_valid(selection_json))
shown_at            TEXT        NOT NULL
response_event_id   TEXT        NULL REFERENCES audit_events(event_id)
responded_at        TEXT        NULL
CHECK((response_event_id IS NULL)=(responded_at IS NULL))
UNIQUE(trace_id,memory_ref)
```

Indexes: `idx_prompt_budget(week_key,shown_at)` and `idx_prompt_memory(memory_ref,shown_at)`. Selection factors are inspection-only. **ASSUMPTION (Open Question 7):** unresolved stated conflict outranks observation; ties use retrieval rank, evidence count descending, last-seen descending, then memory ID.

### 4.5 Internal schedule and evaluation

#### `internal_events`

Why it exists: is the real but explicitly non-calendar state mutated by `schedule_reschedule`. (Trace: FR-25, FR-31.)

```text
event_id            TEXT     PK NOT NULL
current_version     INTEGER     NOT NULL CHECK(current_version>0)
title               TEXT        NOT NULL CHECK(length(trim(title))>0)
scheduled_for       TEXT        NOT NULL
status              TEXT        NOT NULL CHECK(status IN ('scheduled','cancelled'))
created_at          TEXT        NOT NULL
updated_at          TEXT        NOT NULL
```

Indexes: `idx_internal_events_time(status,scheduled_for,event_id)` and `idx_internal_events_title(title,status)`.

#### `internal_event_versions`

Why it exists: proves the prior and new value of every internal create/reschedule operation. (Trace: FR-25, AC-FR-25.)

```text
event_id            TEXT        NOT NULL REFERENCES internal_events(event_id) ON DELETE CASCADE
version             INTEGER     NOT NULL CHECK(version>0)
title               TEXT        NOT NULL
scheduled_for       TEXT        NOT NULL
status              TEXT        NOT NULL CHECK(status IN ('scheduled','cancelled'))
trace_id            TEXT        NOT NULL REFERENCES interaction_traces(trace_id)
idempotency_key     TEXT        NOT NULL
changed_at          TEXT        NOT NULL
PRIMARY KEY(event_id,version)
UNIQUE(idempotency_key)
```

Indexes: `idx_event_versions_trace(trace_id)`.

#### `state_snapshots`

Why it exists: captures the exact logical starting state used by each evaluation case. (Trace: FR-32, API-17–API-18.)

```text
snapshot_id         TEXT     PK NOT NULL
reason              TEXT        NOT NULL CHECK(reason IN ('evaluation_start','case_start','manual_inspection'))
state_id            TEXT        NOT NULL
memory_generation   INTEGER     NOT NULL CHECK(memory_generation>=0)
model_lock_sha256   TEXT        NOT NULL CHECK(length(model_lock_sha256)=64)
config_sha256       TEXT        NOT NULL CHECK(length(config_sha256)=64)
manifest_json       TEXT        NOT NULL CHECK(json_valid(manifest_json))
manifest_sha256     TEXT        NOT NULL CHECK(length(manifest_sha256)=64)
created_at          TEXT        NOT NULL
```

Indexes: `idx_state_snapshots_state(state_id,created_at)`. The manifest contains sorted memory IDs/versions/status/tier/pin/source IDs, active suppression hashes, permission, and internal event IDs/versions. It is inspection/evaluation data, not a restore mechanism.

#### `evaluation_runs`

Why it exists: tracks durable whole-pipeline evaluation progress, conditions, aggregate results, and report location. (Trace: FR-32–FR-33.)

```text
evaluation_id       TEXT     PK NOT NULL
corpus_import_id    TEXT        NOT NULL REFERENCES imports(import_id)
case_set_id         TEXT        NOT NULL
state               TEXT        NOT NULL CHECK(state IN ('queued','running','completed','failed','invalid'))
starting_snapshot_id TEXT       NOT NULL REFERENCES state_snapshots(snapshot_id)
case_count          INTEGER     NOT NULL CHECK(case_count>=0)
passed_count        INTEGER     NOT NULL DEFAULT 0 CHECK(passed_count>=0)
failed_count        INTEGER     NOT NULL DEFAULT 0 CHECK(failed_count>=0)
abstained_count     INTEGER     NOT NULL DEFAULT 0 CHECK(abstained_count>=0)
conditions_json     TEXT        NOT NULL CHECK(json_valid(conditions_json))
summary_json        TEXT        NULL CHECK(summary_json IS NULL OR json_valid(summary_json))
report_path         TEXT        NULL
created_at          TEXT        NOT NULL
started_at          TEXT        NULL
completed_at        TEXT        NULL
```

Indexes: `idx_evaluations_state(state,created_at)` and `idx_evaluations_import(corpus_import_id,created_at)`. Counts, conditions, summary, and report path are inspection-only.

#### `evaluation_cases`

Why it exists: retains each non-ingested evaluation input, starting state, behavior, oracle result, and failure evidence. (Trace: FR-32; AC-FR-32.)

```text
evaluation_id       TEXT        NOT NULL REFERENCES evaluation_runs(evaluation_id) ON DELETE CASCADE
case_id             TEXT        NOT NULL
ordinal             INTEGER     NOT NULL CHECK(ordinal>=0)
input_json          TEXT        NOT NULL CHECK(json_valid(input_json))
input_sha256        TEXT        NOT NULL CHECK(length(input_sha256)=64)
starting_snapshot_id TEXT       NOT NULL REFERENCES state_snapshots(snapshot_id)
trace_id            TEXT        NULL REFERENCES interaction_traces(trace_id)
result              TEXT        NOT NULL CHECK(result IN ('queued','running','passed','failed','error'))
expected_json       TEXT        NOT NULL CHECK(json_valid(expected_json))
assertions_json     TEXT        NULL CHECK(assertions_json IS NULL OR json_valid(assertions_json))
failure_json        TEXT        NULL CHECK(failure_json IS NULL OR json_valid(failure_json))
started_at          TEXT        NULL
completed_at        TEXT        NULL
PRIMARY KEY(evaluation_id,case_id)
UNIQUE(evaluation_id,ordinal)
```

Indexes: `idx_eval_cases_result(evaluation_id,result,ordinal)` and `idx_eval_cases_trace(trace_id)`. `input_json` lives only here, is tagged `evaluation`, and is forbidden by application invariant from creating a `transcripts` row.

#### `evaluation_metrics`

Why it exists: stores measurements as typed observations rather than hiding them in a prose report. (Trace: FR-32; API-18.)

```text
metric_id           TEXT     PK NOT NULL
evaluation_id       TEXT        NOT NULL REFERENCES evaluation_runs(evaluation_id) ON DELETE CASCADE
case_id             TEXT        NULL
name                TEXT        NOT NULL
unit                TEXT        NOT NULL CHECK(unit IN ('ms','bytes','count','tokens','microusd','ratio'))
value_integer       INTEGER     NULL
value_real          REAL        NULL
stage               TEXT        NULL
method               TEXT       NOT NULL
created_at          TEXT        NOT NULL
CHECK((value_integer IS NULL)<>(value_real IS NULL))
```

Indexes: `idx_eval_metrics_name(evaluation_id,name,case_id)`; unique expression index `uq_eval_metric(evaluation_id,coalesce(case_id,''),name,coalesce(stage,''))`. `method` states measured/derived and, for money, `local_no_usage_fee`; every column is evaluation/inspection only.

### 4.6 Views and deletion behavior

Migration `007_views.sql` creates four read-only views:

- `v_memory_current`: current non-forgotten memory plus source count, unresolved-conflict count, computed lifecycle eligibility, and projection health. It backs API-07/API-08. (Trace: FR-13, FR-16, FR-26.)
- `v_import_status`: record counts joined to transcript/job state and `complete`, where queued/processing/retrying/held are all zero. It backs API-02. (Trace: FR-06.)
- `v_trace_decision`: trace plus ordered candidate dispositions, citations, tool selection/result code, failures, and model-call totals. It backs API-15 and contains no rejected candidate body. (Trace: FR-29.)
- `v_transcript_inspection`: source, attempt/outcome, candidate decision counts, safe drops, linked memory IDs, and trace IDs. It backs API-14. (Trace: FR-30.)

Forget is a single transaction: insert content-free audit event; insert suppression; insert tombstone; mark affected historical trace references `redaction_state='forgotten_memory'`; remove the memory FTS row; delete the `memories` row, cascading versions/provenance/embedding/entity links/relations; and commit the idempotent content-free receipt. Source transcripts remain. Trace structure, ranks, IDs, timings, and reason codes remain, but derived answer/tool text that contains the forgotten memory is replaced by an explicit redaction marker. If any step fails, all roll back. (Trace: FR-28–FR-31; the unavoidable tradeoff is in Spec Conflicts.)

Demote and Correct do not delete history. Both atomically write a suppression. Demote appends a `demoted` version. Correct creates a new stated memory sourced to the correction action, appends a `superseded` version to the old memory, links them with `supersedes`, and immediately updates FTS/entity/projection state; the old source transcripts remain linked only to the old history. (Trace: FR-11, FR-27–FR-28.)

### 4.7 Migration sequence

1. `001_core.sql`: strict-mode preflight, `schema_migrations`, `runtime_state`, `idempotency_records`, `audit_events`; seed the singleton state. Runnable check: migrate twice and compare schema/hash. (Trace: FR-31, FR-33.)
2. `002_ingestion.sql`: `imports`, `transcripts`, `import_records`, `jobs`, `extraction_attempts`, `candidate_decisions`. Runnable check: accept/replay/conflict records and restart a leased job. (Trace: FR-03–FR-06, FR-12.)
3. `003_memory.sql`: `memories`, `memory_versions`, `memory_provenance`, `memory_relations`, `suppressions`, `memory_tombstones`. Runnable check: provenance and atomic correction/suppression invariants. (Trace: FR-10–FR-16, FR-27–FR-28.)
4. `004_retrieval.sql`: entities/aliases/links, embeddings, both FTS tables, and integrity triggers. Runnable check: exact, semantic, and one-hop candidates plus raw fallback. (Trace: FR-02, FR-18–FR-19.)
5. `005_tracing.sql`: interaction traces, retrieval snapshots/candidates, citations, model calls, confirmation ledger. Runnable check: completed/abstained/unsupported trace completeness. (Trace: FR-15, FR-20–FR-23, FR-29–FR-30.)
6. `006_tools_eval.sql`: internal events/versions, state snapshots, evaluation runs/cases/metrics. Runnable check: idempotent reschedule and one persisted evaluation case. (Trace: FR-25, FR-32.)
7. `007_views.sql`: the four inspection views and indexes shown above. Runnable check: compare endpoint JSON with direct view rows. (Trace: FR-06, FR-13, FR-26, FR-29–FR-30.)
8. `008_seed_manifest.sql`: seed-version record only; the documented seed command imports checked-in JSON through API-01 rather than inserting semantic state directly. Runnable check: reset/seed produces the declared state manifest hash. (Trace: FR-31–FR-33.)

Migrations are forward-only in review. Reset is not a down migration: `python -m kivi reset-system --confirmation RESET --restore-seed` deletes rows in an explicit foreign-key-safe order inside the named database, reruns integrity checks, increments `state_id`, and optionally imports seed data through public contracts. It never exposes reset over HTTP. (Trace: OP-01, FR-33.)

## 5. DESIGN DECISIONS

This is the implementation interview record. Assumption-backed parameters remain visibly different from resolved requirements.

| # | Decision | Rationale | Rejected alternative and why it lost | Realised in | Trace |
|---:|---|---|---|---|---|
| 1 | One local user, one app process, one SQLite authority. | It is the review and product boundary; it makes state and failures reproducible from a clone. | Multi-user services, tenant IDs, distributed locks, and remote databases solve excluded problems and add setup. | `api/`, `storage/connection.py`; `runtime_state`; all APIs omit user ID. | FR-31–FR-33; C4.3.1; E1–E2 |
| 2 | Dictation and Hey Kivi are separate handlers and service dependency graphs. | The same words must have different memory rights by entry action, not inferred tone. | One endpoint plus a mode classifier could silently switch rights and fails AC-FR-01. | `api/dictations.py`, `api/hey_kivi.py`; `interaction_traces.surface`. | FR-01–FR-03 |
| 3 | Dictation can import only entity aliases and stated formatting preferences; it cannot call semantic retrieval. | “Structurally unable” is stronger and easier to inspect than post-filtering. | Calling general retrieval then filtering would expose observed/episode IDs to the path and violate AC-FR-02. | `services/dictation.py` imports only `LexiconRepository` and `StatedFormatRepository`; dependency test forbids `RetrieveService`. | FR-02; AC-FR-02 |
| 4 | Input is pushed, source-first, idempotent by transcript ID+content, then processed after response. | It matches the reviewer corpus, preserves provenance even on model failure, and keeps semantic work off the interaction path. | Watched folders/pull ingestion are undeclared ambient access; synchronous extraction adds latency and loses the required pending state. | `ingest.py`; `imports`, `transcripts`, `jobs`, `import_records`. | FR-03–FR-06 |
| 5 | Event time determines processing and contradiction recency; arrival time is only audit data. | Reverse-order imports must produce the same current truth. | Arrival order makes replay/network timing change state. | Worker claim query; `transcripts.occurred_at`; `consolidate.py::precedence_key`. | FR-05, FR-11 |
| 6 | Only user transcript text and explicit user actions may be provenance. | Model/tool/application output is not evidence about the user. | Learning from accepted drafts or tool results is convenient but mistakes Kivi’s output or silence for user authority. | Extraction prompt builder; `memory_provenance.source_kind`; source-eligibility tests. | FR-07, FR-09 |
| 7 | Admission is a fail-closed, code-owned state machine in the specified order. | A model can classify semantics, but only code decides whether a row may be inserted; uncertainty produces no memory. | A prompt-only safety instruction is not enforceable or inspectable; storing then filtering is too late. | `admission.py`; Pydantic enums; `candidate_decisions` without a body column. | FR-08–FR-09, FR-12 |
| 8 | One memory is one typed, complete semantic atom with a human sentence and closed typed JSON. | It is independently correctable and gives deterministic keys without hiding content in a profile. | Narrative summaries/blobs make tier, source, correction, and suppression apply to an ambiguous fragment. | `domain/memory.py`; `memories`, `memory_versions`; type-specific schemas. | FR-07, FR-13; Non-goals 5, 8 |
| 9 | Tier is categorical (`stated`, `observed`, `hypothesised`); similarity scores never become belief confidence. | Tier represents user-authorised use, while retrieval scores represent query fit. | A scalar confidence conflates truth, relevance, and permission and is hard to explain. | Tier enum; `memories.tier`; disclosure policy. | FR-14, FR-19 |
| 10 | Repeated evidence activates an observed candidate at `N` but never changes its tier to stated. | The system may detect a pattern without gaining permission to enforce it. | Evidence-count promotion would make repetition impersonate confirmation. | `consolidate.py::add_evidence`; `candidate`→`active` status; confirmation endpoint is the only tier promotion. | FR-10, FR-14 |
| 11 | Exact transcript replay is a no-op; a distinct source for the same semantic key adds evidence once; uncertain overlap stays separate. | This preserves distributed evidence while preferring a visible duplicate over a destructive false merge. | Always create inflates duplicates; similarity-only merge destroys independent correction boundaries. | Transcript fingerprint; provenance unique index; `memory_relations`; relation judge. | FR-05, FR-10 |
| 12 | Below-stated contradictions resolve by tier then event time; any conflict touching stated remains unresolved until explicit correction. | User statements carry authority and must not be silently displaced by inference. | Latest-wins for all tiers is simple but breaks the stated contract; keeping every conflict unresolved makes current answers unnecessarily weak. | `consolidate.py::resolve_conflict`; `memory_relations`; `v_memory_current`. | FR-11 |
| 13 | Corrections create a new stated memory and supersession edge; demote/forget/correct atomically create a semantic-key suppression. | Append-only lineage explains change, while the negative update prevents source replay from regrowing the old belief. | In-place overwrite loses history; row deletion alone is known to regress. | `actions.py`; `memory_versions`, `memory_relations`, `suppressions`, `audit_events`. | FR-11, FR-27–FR-28 |
| 14 | Forget deletes readable memory/history but keeps raw sources, a content-free tombstone, and a hash suppression; affected derived trace text is redacted. | This is the smallest mechanism that preserves provenance policy, non-regrowth, and resolvable old IDs. | True erasure of every copy defeats suppression/provenance; retaining readable history makes “Forget” false. The residual conflict is explicit in Section 10. | Forget transaction; `memory_tombstones`; `suppressions`; `interaction_traces.redaction_state`. | FR-28–FR-30 |
| 15 | Lifecycle eligibility is computed on every read; the sweep only materialises it. | Missing deferred maintenance must never cause stale observations/hypotheses to surface. | Sweep-only enforcement makes behavior depend on whether a background task happened. | `v_memory_current`; `lifecycle.py`; version/audit rows. | FR-16 |
| 16 | Retrieval uses one FTS leg, one embedding leg, and one-hop entities, with code-owned reciprocal-rank fusion and explicit tie breaks. | It meets the hybrid requirement at this scale while keeping every factor inspectable. | LLM reranking hides order; semantic-only misses names; lexical-only misses paraphrases; a graph/vector service adds operations. | `retrieve.py`; FTS tables, embeddings, entity links, retrieval-candidate rank columns. | FR-18–FR-19; C4.3.4 |
| 17 | Superseded memories are eligible only for an explicit change/history intent; candidates/decayed/expired/demoted are not current facts. | History can explain change without contaminating current truth. | Globally excluding superseded loses required change evidence; globally including it produces stale factual answers. | `retrieve.py::status_scope`; `retrieval_candidates.use_role`. | FR-11, FR-16, FR-19 |
| 18 | A compiled-memory miss gets exactly one labelled FTS search over transcripts; pending hits remain labelled raw. | It makes not-yet-processed and missed extraction discoverable without turning raw history into semantic memory. | Searching raw on every request bypasses memory contracts and budgets; never searching it loses required history recall. | `retrieve.py::raw_fallback`; `transcript_fts`; trace leg state. | FR-06, FR-18; Non-goal 12 |
| 19 | Retrieval completes before Anbu/Koottu/Daari disclosure. | The trace can show what was known versus what could be said; permission changes disclosure, not relevance. | Permission-filtered retrieval hides withheld evidence and fails same-state comparison. | `retrieve.py` then `disclose.py`; retrieval snapshot/candidate dispositions. | FR-19–FR-22 |
| 20 | Anbu is persistent default, Koottu is explicit persistent state, and Daari is a one-request intent with false positives failing closed. | This directly encodes the three promises and prevents tone from granting inference permission. | Persistent Daari or tone inference turns an invitation into ambient authority. | `runtime_state.permission`; `disclose.py`; Daari phrase classifier/test corpus. | FR-20–FR-22 |
| 21 | The only model-callable tools are the exact three specified; one route, one tool, at most one answer-generation attempt. | A narrow bounded action surface is reviewable and prevents apparent external action. | Dynamic tools, agents, retries, and reflection broaden scope and hide failure cost. | `tools.py` frozen enum and schemas; router validator; trace available-tools assertion. | FR-17, FR-24–FR-25; C4.4 |
| 22 | Every factual output claim must cite permitted evidence; any missing, ambiguous, contradictory, partial-leg, timeout, or invalid citation causes whole-result abstention. | False refusal is safer and visible; a plausible unsupported answer is a severity-one failure. | Best-effort completion or use of a surviving retrieval leg can sound correct while having no defensible provenance. | `grounding.py`; `trace_citations`; abstention codes. | FR-18, FR-23–FR-25 |
| 23 | A mutating tool and its terminal trace commit in one transaction. | The system cannot claim a schedule change whose state or explanation was lost. | Commit tool state before trace risks an unexplained action; trace first risks claiming an action that rolled back. | `tools.py::schedule_reschedule`; storage unit-of-work. | FR-25, FR-29, FR-31 |
| 24 | Durable deferred work is a serial SQLite lease queue inside the app process. | It survives restarts, shows progress, preserves event order, and avoids a broker. | Fire-and-forget tasks disappear on crash; Redis/Celery adds services and configuration. | `worker.py`; `jobs`, `extraction_attempts`. | FR-05–FR-06, FR-12, FR-31 |
| 25 | Local Ollama is the only inference provider; exact post-pull digests/options/schema versions are recorded. | It satisfies the user’s zero-service-spend constraint and keeps private memory local during runtime. | Hosted models incur usage fees and transmit content; mutable unrecorded tags make results uninterpretable. | `ollama_client.py`; `models.lock.json`; `model_calls`. | FR-31–FR-33; C4.3.5–C4.3.6 |
| 26 | Raw prompts/model outputs are not retained; accepted semantic results and hashes are. | Raw malformed output can copy prohibited content, while hashes and typed decisions are enough to account for calls. | Full raw traces aid debugging but create an unbounded sensitive duplicate store. | `model_calls`; logging redactor; no raw-output column. | FR-08, FR-29–FR-30; Open Question 35 |
| 27 | User and engineer inspection share persisted facts but render at different detail levels. | The Why panel stays legible while API review evidence exposes ranks/timing/model usage; neither relies on ephemeral logs. | A developer console violates the position; putting scores in normal-user prose makes the feature unintelligible. | `/why/...` view; API-14/API-15; `v_trace_decision`, `v_transcript_inspection`. | FR-26, FR-29–FR-30; E4 |
| 28 | Evaluation cases are stored outside transcripts and call the same services as the UI/API. | Questions cannot leak into memory, and the measured path is the shipped path. | A notebook, mock retriever, or ingestion of questions makes results non-representative or leaks answers. | `evaluation/`; `evaluation_cases`; leakage invariant. | FR-32 |
| 29 | Reset is a named local CLI operation with literal confirmation, never HTTP/model-callable. | Reviewers need reproducibility without exposing destructive capability to product requests. | A reset endpoint is easy to automate but violates the operator-only boundary. | `cli/reset.py`; OP-01; reset audit. | FR-33 |
| 30 | The default listener and Ollama URL are loopback-only; any non-loopback Kivi bind requires one configured bearer token on every API route. | This preserves the spec's simple local path without accidentally exposing private transcripts unauthenticated. | Always unauthenticated is unsafe when misbound; always authenticated adds credentials to the primary local review for no benefit. | `api/security.py` startup guard/middleware; `RUN.md` environment table. | API contract authentication; C4.3.6 |

## 6. FUNCTIONAL FLOW

### 6.1 Ordinary dictation becomes usable memory without blocking the response

Input: at 09:00 on 11 September, the user submits raw ASR `send the atlus recap to prea raghavan` and formatted text `Send the Atlus recap to Prea Raghavan.` through `/v1/dictations`.

1. The endpoint validates the source and hashes the normalised record. It finds `Atlus`→`Atlas` and `Prea Raghavan`→`Priya Raghavan` in `entity_aliases`; no general retrieval service is callable. One transaction inserts `transcripts(tr_...; surface=dictation; processing_state=queued)`, a held extraction `jobs` row, the dictation `interaction_traces` row, and its idempotency result. (Trace: FR-01–FR-05.)
2. The response is `Send the Atlas recap to Priya Raghavan.`, with two allowed entity memory uses and `semantic_processing: queued`. A relevant observed “risk paragraph” preference and an episode in `memories` are never selected or recorded in this dictation trace. (Trace: FR-02–FR-03; AC-FR-02.)
3. After response finalisation, the job becomes queued. The worker calls Ollama with only the user text and allowed lexicon. Suppose it extracts the entity/project relation `Priya Raghavan client-contact-for Atlas`. Admission accepts limited work identity, canonicalisation produces a semantic key, and no suppression or duplicate exists. (Trace: FR-06–FR-09.)
4. One transaction creates `memories`, version 1, transcript `memory_provenance`, `entities`/`memory_entities`, a `candidate_decisions.created` row, the FTS row, and the local embedding. The transcript ends `processed/candidates_stored`; the import/status view becomes terminal for this record. (Trace: FR-10, FR-12–FR-13, FR-30.)
5. If Ollama is unavailable, steps 1–2 are unchanged. Attempts appear in `extraction_attempts`; after the cap the transcript is `quarantined/failed_quarantined`, and `transcript_fts` can still return it as raw and unprocessed. Nothing is silently called memory. (Trace: FR-06, FR-12, FR-18.)

Data touched: `entity_aliases`, `transcripts`, `jobs`, `interaction_traces`, then deferred `extraction_attempts`, `candidate_decisions`, `memories`, `memory_versions`, `memory_provenance`, `entities`, `memory_entities`, `memory_embeddings`, and both relevant FTS tables.

### 6.2 Distributed facts answer a recall request; permission changes only disclosure

Starting history contains three stated memories sourced to separate transcripts: `Atlas part-of Acme redesign`, `Arun owns Atlas backend`, and episode `Atlas review starts Thursday 15:00`. It also contains an active observed memory supported by four sources: `The user usually sends the recap immediately after the review.` Permission is Anbu.

1. The user asks, “Who owns the backend on the Acme redesign, and when is its review?” The request transaction creates the held user transcript and `interaction_traces`, fixes `memory_generation=42`, and opens `retrieval_snapshots`. (Trace: FR-18–FR-19.)
2. FTS ranks Atlas/Acme terms, the embedding leg finds paraphrases, and the entity leg joins the three facts through Atlas. `retrieval_candidates` stores the same pre-permission order for all four memories with ranks, pin/tier/evidence/recency, and healthy-leg states. (Trace: FR-18–FR-19.)
3. Anbu marks the three stated memories `used` and the observation `withheld/ANBU_OBSERVATION`; the answer says Arun owns the backend and the review is Thursday at 15:00. `trace_citations` contains each supporting memory/version and every source transcript. The UI shows only `Kivi noticed something here` for the observation. (Trace: FR-20, FR-23.)
4. Opening that affordance writes `audit_events.observation_revealed`; API-16 returns the one observation with evidence dates. `runtime_state.permission` remains Anbu and no tier/version changes. (Trace: FR-20.)
5. If the user explicitly switches to Koottu and repeats the request against unchanged memory state, retrieval produces the same IDs/order. Disclosure may offer the recap observation separately with four sources, but the recalled facts and requested answer do not silently apply it. The two trace rows differ only at the permission/disposition stage. (Trace: FR-19–FR-21; AC-FR-19.)

Data touched: `runtime_state`, `transcripts`, `jobs`, `interaction_traces`, `retrieval_snapshots`, `memory_fts`, `memory_embeddings`, `memory_entities`, `retrieval_candidates`, `trace_citations`, `model_calls`; on reveal, `audit_events`; after each response, the held turn is queued.

### 6.3 Missing evidence produces an actionable abstention, not a plausible answer

The history mentions Arun’s Atlas backend work and a database migration with Priya, but contains no statement connecting Arun to an auth migration. The user asks, “What did Arun say about the auth migration?”

1. The three retrieval legs run successfully. The Arun memory is a high entity match but lacks the requested topic; the database-migration memory is semantically nearby but concerns Priya. Both are stored as `near_miss` in `retrieval_candidates`, not as support. (Trace: FR-18, FR-23.)
2. Because no compiled memory jointly entails `{speaker=Arun, topic=auth migration, requested=say}`, recall performs its one raw FTS fallback. It finds the Priya database transcript only; that row is also a near miss and is explicitly `kind=raw_transcript`. (Trace: FR-18.)
3. The support validator requires the named person/topic relation and has zero supporting citations. This—not a vague model confidence—is the exact abstention trigger. `recall_search` returns `NOT_FOUND`; answer generation is restricted to a missing-history explanation and cannot attribute a view to Arun. (Trace: FR-23; AC-FR-18 negative.)
4. The endpoint returns HTTP 200, `outcome=abstained`, the searched concepts, both genuine near misses, and a trace ID. `v_trace_decision` shows healthy retrieval legs, empty `used`, no withheld items, fallback executed once, tool selection, zero citations, timings, local model digest/usage, and USD 0.00 service cost. (Trace: FR-23, FR-29.)

If either the lexical or semantic leg fails, the abstention code is instead `PARTIAL_RETRIEVAL`; results from the surviving leg are marked `unusable_leg_failure`. If a stated contradiction is found, the code is `STATED_CONTRADICTION`. If generation times out, the code is `GENERATION_FAILED`. In all cases, the system commits the full trace and returns no factual answer. (Trace: FR-11, FR-23; AC-FR-23.)

## 7. OBSERVABILITY AND INSPECTION

The durable database is the explanation source; JSON logs only help diagnose process failure before a trace can be committed. (Trace: FR-29–FR-32; E4.)

### 7.1 Inspecting one result

The response links to `GET /v1/traces/{trace_id}` and the server-rendered `/why/{trace_id}` page. API-15 reads `v_trace_decision` plus the following rows:

| Question | Concrete artifact | What it proves |
|---|---|---|
| What request and permission were active? | `interaction_traces.request_text`, `application_context_json`, `turn_history_json`, `permission`, `daari_invited` | The input contract and disclosure state. |
| What was searched? | `interaction_traces.search_description_json`; `retrieval_snapshots.query_text`, config, generation, and leg states | Query, bounds, thresholds, and whether all legs completed. |
| What memory was retrieved and in what order? | Ordered `retrieval_candidates` with `kind=memory`, per-leg ranks, fusion score, tie-break snapshots | The complete pre-permission candidate set. |
| What was ignored, and why? | `retrieval_candidates.decision/reason_code` values `near_miss`, `budget_dropped`, `historical_evidence`, or `unusable_leg_failure` | Relevance/budget/failure non-use is distinct from permission. |
| What was withheld? | `decision=withheld` plus `required_permission` | Anbu or Daari prevented disclosure after retrieval. |
| What actually affected output? | `decision=used`, `use_role`, and `trace_citations` | Each fact/style/observation has a memory version and dated source. |
| What tool decision occurred? | `available_tools_json`, `selected_tool`, `router_reason_code`, `tool_input_json`, `tool_result_json` | All three candidates, selected/none, exact result, and no fourth tool. |
| Why did it abstain or degrade? | `abstention_code`, `failure_json`, `degradation_json`, retrieval leg states | Missing, ambiguous, conflict, partial retrieval, model, or state failure. |
| How much did it take? | Trace timing/usage/cost totals and child `model_calls` rows | Retrieval/end-to-end time, exact model digest/options, tokens, and zero-fee method. |
| Did an old source contribute? | `trace_citations.transcript_id` → API-14 | One additional action reaches the dated original transcript. |

The human Why page translates those fields without scores: “used,” “found but not an answer,” “not shown in Anbu,” “left out by the context limit,” and “search incomplete.” A collapsed “Review details” block may show ranks, model digests, timings, tokens, and configuration; this is the same artifact, not a separate developer console. Rejected content is absent because neither `candidate_decisions` nor `model_calls` has a column for it. (Trace: FR-29; Open Question 34.)

### 7.2 Inspecting one source or memory

- `GET /v1/transcripts/{id}/inspection`, backed by `v_transcript_inspection`, shows raw/formatted input, metadata, state, every attempt, the single terminal outcome, created/merged/superseded IDs, reason/count-only drops, read-not-kept count, usage/cost, and linked traces. (Trace: FR-30.)
- `GET /v1/memories/{id}`, backed by `v_memory_current`, `memory_versions`, `memory_provenance`, and `memory_relations`, shows the current record, dated sources, evidence count, lifecycle, pin, action availability, lineage, and unresolved conflicts. Forgotten IDs return not found on the memory API; old traces render their `memory_tombstones` state without content. (Trace: FR-13, FR-26–FR-29.)
- `GET /v1/imports/{id}`, backed by `v_import_status`, lists every accepted/replayed/rejected record and every non-terminal/quarantined state. `complete` is computed, not trusted from a progress percentage. (Trace: FR-04–FR-06.)
- `GET /v1/evaluations/{id}` joins evaluation cases/metrics, trace links, and state snapshots; the checked-in generated report is a serialisation of these rows, not a separately authored summary. (Trace: FR-32.)

### 7.3 Operational log

Every process line is JSON with this fixed envelope:

```json
{"ts":"2026-09-11T10:26:00.824Z","level":"INFO","event":"request.completed","request_id":"req_...","trace_id":"trace_...","job_id":null,"stage":"hey_kivi","duration_ms":824,"outcome":"abstained","error_code":"NOT_IN_HISTORY"}
```

Allowed identifiers are request/trace/job/import/evaluation/transcript IDs. Logs may contain counts, durations, states, and safe error codes; they must not contain request bodies, transcript text, memory content, prompts, model output, application context, auth tokens, or environment values. `RUN.md` names stderr as the log location and the API/database views as the authoritative inspection locations. (Trace: FR-08, FR-29–FR-33; C4.1.12–C4.1.13.)

## 8. DEVELOPMENT PLAN

Each milestone is merged only with its named executable check and a clean database. “Stubbed” means a visible, non-canned limitation; no stub may claim a memory, action, or pass that did not occur. All commands are ultimately collected verbatim in `RUN.md`. (Trace: FR-31–FR-33; C4.1.2, C4.1.14.)

### Milestone 1 — Local thin slice through the full path

At the end: a clean clone can create a venv, install the locked Python dependencies, verify/pull the two Ollama models, migrate SQLite, start the one process, open the three-page shell, submit a dictation, receive its response before a real Ollama extraction, observe the durable job complete, see one stated entity memory with transcript provenance, ask a Hey Kivi recall question, inspect its citation/Why trace, restart, and repeat the recall from persisted state.

Stubbed: one entity relation only; exact/FTS retrieval only; Anbu only; `recall_search` only; no merge, exclusions beyond a minimal deny fixture, semantic leg, raw fallback, lifecycle, actions, import batch, or full evaluation. The UI labels unfinished actions unavailable; it does not fake them.

Verification: `pytest tests/thin_slice -q` plus the documented five-click smoke path. This fully satisfies AC-FR-01 and AC-FR-03. It also exercises the happy path needed by later criteria but does not claim them early. (Trace: FR-01, FR-03, FR-31.)

### Milestone 2 — Complete write path and corpus import

At the end: API-01/API-02 import a 500-record fixture; event-time ordering, identical replay, content conflict, durable leases/retries/quarantine, all five extraction outcomes, all three memory types, ordered admission gates, reason-only drops, third-party identity limits, exact/semantic duplicate judging, distributed evidence, below-stated and stated contradiction behavior, entity linkage, embeddings, and projection repair are implemented. Import status and transcript inspection are usable in UI and API.

Stubbed: Hey Kivi still has recall only and Anbu only; raw fallback and final multi-leg abstention are not complete; memory actions/lifecycle/evaluation runner are unavailable.

Verification: `pytest tests/ingestion tests/memory_write -q` and `python -m kivi import-corpus fixtures/development-500.json`; generated import evidence must satisfy AC-FR-04, AC-FR-05, AC-FR-06, AC-FR-07, AC-FR-08, AC-FR-10, AC-FR-11, and AC-FR-12. No criterion is waived for local-model variance; failures remain visible. (Trace: FR-04–FR-14, FR-30.)

### Milestone 3 — Complete read path, permission, and three tools

At the end: dictation’s structural memory restriction is enforced by dependency tests; FTS+embedding+one-hop retrieval, deterministic fusion/order, all candidate dispositions, one raw fallback, Anbu/Koottu, one-request Daari, fixed three-tool routing, grounded recall, draft, internal schedule/reschedule, citation validation, and all abstention modes are implemented. The same application context can inform a draft but cannot reach extraction.

Stubbed: Confirm/Correct/Demote/Forget/Pin and automatic lifecycle changes remain unavailable; confirmation prompt budget is not spent; the Why view is functional but not yet final visual polish.

Verification: `pytest tests/retrieval tests/disclosure tests/tools tests/grounding -q`; it fully satisfies AC-FR-02, AC-FR-09, and AC-FR-17 through AC-FR-25. The Anbu/Koottu fixture asserts byte-identical pre-permission candidate IDs/order. (Trace: FR-02, FR-09, FR-17–FR-25.)

### Milestone 4 — User control, lifecycle, and complete inspection

At the end: the three human memory groups, detail/history/provenance pages, confirmation prompts and budget ledger, Confirm/Correct/inline correction/Demote/Forget/Pin, suppression, content-free tombstones, read-time and swept lifecycle, reveal action, complete Why/transcript views, trace redaction on forget, and restart recovery are implemented. All state-changing operations are concurrency/version/idempotency tested.

Stubbed: the development evaluation is still a targeted pytest suite rather than the public evaluation API/report; reset can create an empty DB but seed restoration is completed next.

Verification: `pytest tests/actions tests/lifecycle tests/inspection tests/restart -q` plus UI smoke fixtures for each tier/outcome; it fully satisfies AC-FR-13 through AC-FR-16 and AC-FR-26 through AC-FR-31. (Trace: FR-13–FR-16, FR-26–FR-31.)

### Milestone 5 — Reproducible full-pipeline evaluation

At the end: API-17/API-18, the durable evaluation worker, state manifests, leakage guard, fixed cases for all seven position claims and every acceptance criterion, sensitivity runs for assumed thresholds, latency/storage/model/cost metrics, and generated Markdown+JSON reports exist. Cases call production services; evaluation inputs never create transcripts. Failures and abstentions remain in both DB and report.

Stubbed: only the checked-in development corpus/case set has been dry-run; reviewer-machine and translated foreign-corpus variation remains a release check.

Verification: from reset, `python -m kivi evaluate --case-set development --wait` must produce a report whose completeness checks pass and whose service/API cost is USD 0.00; it fully satisfies AC-FR-32 and reruns AC-FR-01 through AC-FR-31 through the public contracts. (Trace: FR-32.)

### Milestone 6 — Clean-clone and foreign-corpus release gate

At the end: `README.md`, complete `RUN.md`, `.env.example` with only local host/path settings, model bootstrap/digest verification, seed/reset, the approximately-500 record development corpus, generated results, model/config locks, and Windows/POSIX commands are present. A clean environment runs the exact primary path without dashboard work. A schema-valid unseen translated corpus is reset/imported/processed/inspected/queried/evaluated, and the resulting limitations are reported rather than tuned away.

Stubbed: nothing required by the specification. Docker, hosted deployment, live integrations, extra tools, multi-user support, and richer navigation remain explicitly out of scope.

Verification: a clean-clone scripted dry run plus a human UI pass fully satisfies AC-FR-33 and reruns all AC-FR-01–AC-FR-32. The release fails on a model-digest mismatch, undeclared network connection, non-zero paid-service cost, missing metric, invented absent-history answer, unresolved migration error, or undocumented step. (Trace: FR-31–FR-33; C4.1.10–C4.1.14.)

Acceptance coverage is therefore complete and non-overlapping at first completion: M1 = 01,03; M2 = 04–08,10–12; M3 = 02,09,17–25; M4 = 13–16,26–31; M5 = 32; M6 = 33. M5 and M6 rerun earlier criteria as regression rather than redefining them.

## 9. RISKS

| Risk | Likely failure | Earliest point it is known | Test/response | Trace |
|---|---|---|---|---|
| The local 8B model is not reliable enough for strict extraction/admission. | Missed facts, invalid JSON, or prohibited content misclassified. | M1’s first 20 adversarial records; decisively by M2’s five-outcome/exclusion fixtures. | Measure per-stage failures; fail closed; try a different free local model only by updating the lock and rerunning all evaluation. | FR-08, FR-12, FR-32 |
| Reviewer hardware cannot run `qwen3:8b` within practical memory/time. | Ollama eviction/timeouts; 500 records take hours. | M1 startup benchmark and M2 50-record then 500-record timing. | Publish RAM/disk/runtime conditions and measured rate. A smaller model is acceptable only after full re-evaluation; no hidden hosted fallback. | FR-12, FR-32–FR-33 |
| Ollama is absent or FTS5 is missing. | Primary path cannot start. The current design-time workspace did not have the `ollama` command installed. | First two preflight commands in M1. | `doctor` checks Python/SQLite FTS5/Ollama/model digests and gives exact remediation before migration. | FR-33 |
| Ollama tags move or model artifacts disappear. | Clean clones cannot reproduce the evaluated model. | Model bootstrap/digest check in M1 and every CI/release run. | Verify recorded manifest digest and fail loudly. Updating a digest creates a new evaluation artifact; weights are not silently substituted. | FR-31–FR-33 |
| Temperature zero is still not bit-deterministic across Ollama/GPU versions. | A reset rerun may yield a different but valid candidate relation. | M2 repeated clean-reset test on the release machine; M6 cross-machine dry run. | Pin Ollama version, digest, quantisation, seed/options and schema; report semantic/state diffs. Do not promise bit identity (Section 10). | FR-05, FR-32 |
| Hybrid retrieval misses a fact derivable across several transcripts. | False abstention on a present-history question. | M3 distributed-fact fixtures, then M5 case set and M6 foreign corpus. | Log each leg/rank, test query paraphrases, and tune only the disclosed RRF/top-k/broadening config. Never compensate by guessing. | FR-18–FR-23 |
| Reciprocal-rank scores do not provide calibrated confidence. | Threshold behaves differently by query shape. | M3 weak-near-match suite and M5 sensitivity report. | Base support on typed entailment/citation checks plus a disclosed threshold; measure false refusal. | FR-23; Open Question 47 |
| Canonical-key suppression is too narrow. | Rephrased old belief regrows after correction/forget. | M2 paraphrase replay tests and M4 full-source reprocessing. | Test multilingual/paraphrase fixtures; preserve safe `NEW` behavior only for merge, not suppression. A broader suppression needs an owner rule (Section 10). | FR-27–FR-28; Open Question 18 |
| Canonical-key suppression is too broad. | A legitimate later changed fact is silently blocked. | M4 temporal-change fixtures. | Include typed object and explicit validity time in the key; show `SUPPRESSED_BY_USER_ACTION` reason; do not broaden to subject-wide matching. | FR-11, FR-28; Open Questions 18,22 |
| Structural exclusion of application context makes pronouns/deictic dictation unlearnable. | “Move it to Tuesday” produces an ambiguous drop even when the current message makes “it” obvious. | M2 worked-example fixture. | Preserve current-task drafting but drop the memory; report the limitation rather than admit context as evidence. | FR-07, FR-09; Spec Conflict 5 |
| Excluded content leaks through logs, trace JSON, raw model output, or raw fallback. | The safety claim is false even though the memory table is clean. | M2 canary-string database/log scan; rerun in M3 raw fallback and M5 evaluation. | No rejected-body columns, no raw model outputs, structured log allowlist, answer-category validator, and automated whole-state canary scan. Raw source retention remains a declared conflict. | FR-08–FR-09, FR-29–FR-30 |
| Citation validator is too permissive. | Fluent answer cites a nearby but non-entailing memory. | M3 person/topic/date swap tests. | Require subject/predicate/object coverage and source existence; severity-one failure in evaluation. | FR-18, FR-23, FR-32 |
| SQLite write contention blocks interactive actions behind import work. | Correct/forget/schedule latency spikes or returns busy. | M2 concurrent import+action stress test. | Serial worker uses short transactions and does model calls outside transactions; bounded busy timeout; user action wins the next write slot. | FR-27–FR-31; C4.3.3 |
| A crash occurs between HTTP response and held-job release. | A user turn remains held indefinitely. | M1 kill-at-boundary fault test. | Startup recovery reconciles terminal traces to held jobs; raw source remains visible throughout. | FR-03, FR-06, FR-12 |
| Trace/source retention grows or conflicts with later forgetting. | Database growth and privacy exposure exceed expectations. | M4 forget/trace test and M5 bytes-per-transcript metric. | Redact derived trace text on forget, retain structural audit, report growth. No retention deletion is invented while the spec leaves it open. | FR-28–FR-32; Open Question 33 |
| Relative date parser differs from user intent. | Wrong internal scheduled time. | M3 timezone/DST/“next Tuesday” matrix. | Use occurred-at anchor and configured IANA zone; if one absolute result is not deterministic, return `MISSING_TIME/AMBIGUOUS` and write nothing. | FR-25; Open Question 23 |
| Evaluation accidentally teaches the system its questions. | Inflated recall scores and leaked sources. | M5 invariant before the first case. | Evaluation inputs have no transcript creation path; fingerprint scan marks the run invalid. | FR-32 |

## 10. SPEC CONFLICTS

These are not alternative designs. They are places where the design cannot make every sentence simultaneously true. The implementation follows the stated tradeoff and the evaluation must disclose it.

### 10.1 Raw provenance versus “not kept”

FR-09 says third-party personal material is read but not kept, while FR-03/FR-13/FR-30 and C4.3.7 require the complete raw/formatted transcript to persist and open from provenance. A transcript may itself contain the hospital/family material that admission correctly excludes from memory. No schema can both retain that original and not retain it.

Tradeoff: retain the local source transcript as provenance, exclude it from semantic memory, do not copy rejected spans into decisions/logs/model-call records, and phrase the product promise as “not retained as memory.” Raw fallback may use a source only for an allowed work-level answer and never turn excluded material into a belief. True system-wide non-retention would require redacted provenance or transcript deletion semantics, neither authorised by the spec. (Related: specification Open Questions 24–28; Resolutions B1–B3.)

### 10.2 Forget versus suppression, sources, and complete old traces

FR-28 requires readable belief/history removal but also a durable suppression and retained source transcripts. FR-29 requires every historical result to keep its request, tool result, answer, and citations. Those artifacts can repeat the forgotten content. A useful suppression must also retain at least a fingerprint of what was forgotten. Literal erasure and non-regrowth/complete historical inspection cannot coexist.

Tradeoff: delete memory content/history, retain raw sources and a non-reversible semantic-key hash, keep a content-free ID tombstone, and redact affected derived answer/tool text while retaining trace structure. This makes future behavior safe and the residue explicit, but an old trace is no longer a byte-complete copy of its original result. If legal/cryptographic erasure is intended, the spec must add transcript/trace deletion and accept that exact replay suppression may weaken. (Related: Open Questions 26,31,33; Resolutions B2, B5.)

### 10.3 Explicit correction as source versus transcript-only provenance

FR-07 permits an explicit Confirm/Correct event to create or change memory. API-09/API-10 carry user-authored correction text but no transcript ID. FR-13 simultaneously says an active memory cannot lack a source and its observable source IDs resolve to dated transcripts. Reusing the old transcript as proof of the corrected claim would be false provenance; inventing a synthetic ASR transcript would also misdescribe the event.

Tradeoff: `memory_provenance` supports a dated `user_action` source, and the UI labels it “Corrected by you” rather than “Transcript.” Extracted memories still require transcript provenance. If `source_transcript_ids` must literally be non-empty for action-only replacements, the API must be revised to create/name a first-class action source record or corrections must be submitted as dictations. (Related: FR-13 observable result; API-10.)

### 10.4 Universal recall guarantee versus bounded retrieval and mandatory abstention

FR-18 says “any reasonable question” present or derivable in supported history must be answered. FR-19/C4.4 bound retrieval to one pass/top-k, FR-23 requires abstention below a threshold or on partial failure, and the memory ontology intentionally drops unsupported types/content. No finite retriever/model can guarantee recall for every reasonable natural-language derivation, especially on an unseen translated corpus, while also guaranteeing no invention.

Tradeoff: prioritise FR-23’s safety rule, implement all three retrieval legs plus one bounded raw fallback, and treat false abstentions as measured failures. Acceptance can be demonstrated on declared cases and the foreign corpus, but the universal quantifier cannot be proven. Satisfying it literally would require unbounded full-corpus reasoning or guessing, both prohibited. (Related: Open Questions 4,8,47–48.)

### 10.5 Structural write boundary versus context-dependent dictation

FR-07/FR-09 require application context to be ineligible for the write path. The source position’s worked example expects “move it to the following Tuesday” to become a standalone Atlas episode, although “it” and the prior date exist only in third-party context. Using that context to fill the memory means it did influence memory construction; refusing it means the promised example cannot be learned.

Tradeoff: this design drops the candidate as `AMBIGUOUS_REFERENCE` unless the user-authored text or an already-allowed entity memory resolves it. The context still informs the immediate draft. A safe derived context digest could recover more memories, but it is an unapproved new evidence path and therefore scope creep. (Related: Open Question 46; Resolutions B6.)

### 10.6 Deterministic report versus local-model nondeterminism

FR-32 asks for a deterministic report, and FR-05 asks replay to produce the same memory state. Idempotent replay is deterministic because it returns the stored result, but a reset and fresh Ollama run may not be bit-identical across CPU/GPU kernels or Ollama versions even with a fixed model digest, seed, and temperature zero.

Tradeoff: pin and record Ollama version, model digest/quantisation, options, prompt schema, config, inputs, and state manifests; sort every code-owned decision; compare semantic state and acceptance results rather than raw generated wording. The report format and provenance are deterministic, but fresh model wording/verdicts are only reproducible under the documented environment, not mathematically guaranteed. Requiring bit identity would need a fixed execution image/hardware backend or a non-model extractor, neither supplied by the spec. (Related: Open Question 50.)

### 10.7 The specification still contains release-blocking open values

Section 7 of the specification says its open questions must not be filled with convenient defaults, yet a runnable system requires thresholds, windows, retry/input limits, prompt budget, relation/time rules, model IDs, retention policy, and hardware expectations. Calling the specification “settled” does not supply those values.

Tradeoff: every necessary provisional value is marked **ASSUMPTION**, centralised in versioned config, copied into traces/evaluation, and subjected to sensitivity tests. The system can be built and interrogated, but release claims depending on those values remain conditional until the owner adopts them or the corpus evidence justifies them. This design does not silently convert assumptions into requirements. (Related: all Specification Open Questions, especially 1–14 and 47–51.)
