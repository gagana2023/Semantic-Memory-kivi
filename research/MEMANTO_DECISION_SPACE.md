# Memanto decision-space audit for Kivi

> Purpose: recover the questions embodied by this repository, not document its features or recommend answers. Repository state audited: `a368c79` (2026-09-10). Kivi comparison source: `kivi-semantic-memory-position.md`. “Inference” marks conclusions not stated by the authors. Line references are to this checkout.

## Orientation (reported before analysis)

### Where the real logic lives

The load-bearing memory logic is in five services:

- `memanto/app/services/memory_write_service.py`: timestamp ownership, single/batch writes, same-ID updates, lifecycle transitions, hard deletion (`:76-600`).
- `memanto/app/services/memory_read_service.py`: semantic, temporal and recent retrieval; type unions; post-filtering; deduplication; formatting; grounded answer generation (`:63-1058`).
- `memanto/app/services/conversation_memory_extraction_service.py`: LLM extraction, prompt contract, validation, truncation and within-response duplicate removal (`:18-190`).
- `memanto/app/services/memory_policy_service.py` plus `policy_presets.py`: explicit sweep-based expiry/purge semantics and preset windows (`memory_policy_service.py:1-9,237-274,352-503`; `policy_presets.py:21-115`).
- `memanto/app/services/daily_analysis_service.py` and `memanto/app/clients/agent_conflict.py`: retrospective summaries and LLM/agent-based conflict discovery (`daily_analysis_service.py:128-234,271-415`; `agent_conflict.py:315-470`).

`memanto/app/core.py` and `memanto/app/models/__init__.py` freeze the record and API contracts (`core.py:85-194`; `models/__init__.py:32-205,226-312`). `memanto/app/routes/memory.py` is mostly HTTP orchestration, session scoping, error translation and post-commit activity/summary logging (`:377-410,410-773,775-1109,1247-1669`). `memanto/cli/client/direct_client.py` is nominally a client but contains substantive conflict-resolution mutations (`:1568-1753`), so it is not pure glue.

Glue/adapters: FastAPI assembly and auth in `memanto/app/main.py` and `memanto/app/routes/auth_deps.py`; cloud/on-prem client normalization in `memanto/app/clients/{moorcheh,onprem,backend}.py`; CLI commands under `memanto/cli/commands`; generated/client SDK code under `sdks`; product integrations under `integrations`; demonstrations and benchmarks under `examples`. The large single-file dashboard `memanto/app/ui/static/index.html` is presentation plus UI-side orchestration, not the authoritative memory semantics.

### Data model and serialization

There is no relational schema or migration chain. Durable semantic memory is a Moorcheh document. The canonical in-process record is `MemoryRecord`: UUID id; optional one-of-13 type; title (100 chars); content (10,000); agent and actor IDs; bounded writer source and optional source reference; confidence `[0,1]` defaulting to `0.8`; `active|expired`; at most 20 tags of at most 64 chars; six-way provenance; created/updated times; and paired expiry timestamp/reason (`core.py:18-61,85-131`; `constants.py:3-18,28-47`).

Serialization is deliberately denormalized. Search text becomes `[TYPE] title\n\ncontent`, optionally followed by `Tags: ...`; filterable metadata is flat, tags become one comma-separated string, and timestamps become ISO strings (`core.py:133-178`). This format has already caused a backwards-compatible newline repair (`core.py:94-108`). Read formatting accepts nested or flat backend shapes and legacy missing fields (`memory_read_service.py:936-1058`).

Local persistence uses:

- agent/session JSON files and Markdown session summaries under `~/.memanto` or its on-prem subdirectory (`config.py:200-218`; `session_service.py:102-176,614-850`);
- YAML policy files (`memory_policy_service.py:276-338`);
- JSON conflict reports (`config.py:214-229`; `daily_analysis_service.py:236-415`);
- Markdown/OKF export formats (`memory_export_service.py:1-298`; `okf_export_service.py:1-420`).

The API request/response model admits up to 100 memories per batch, 200 conversation turns, and 100 answer contexts (`models/__init__.py:78-130,177-196`). Conflict resolution is represented as an indexed action over a dated report, not as an atomic version graph (`models/__init__.py:137-174`).

### Main execution paths, entry point to persistence

**Explicit write.** `python -m memanto` enters the Typer CLI (`memanto/__main__.py:1-6`; `cli/main.py:1-70`), or FastAPI enters through `app/main.py:67-155`. HTTP `POST /{agent_id}/remember` authenticates a session, requires the session’s agent to match the path, optionally rule-parses the type, derives a title from the first 50 characters, constructs `MemoryRecord`, and dispatches `MemoryWriteService.store_memory` off the event loop (`routes/memory.py:377-466`). The service owns timestamps, ensures the per-agent Moorcheh namespace, serializes the record, and calls `documents.upload`; activity and local Markdown summary logging happen after storage and are best-effort (`memory_write_service.py:96-166`; `routes/memory.py:466-495`; `session_service.py:758-788`). Persistence of the memory itself is therefore remote Moorcheh cloud or the on-prem compatible backend, not the local session file (`clients/moorcheh.py:33-143`; `clients/onprem.py:52-145`).

**Conversation write.** `POST /remember/extract` validates up to 200 chat messages, invokes `answer.generate` in raw-LLM mode (`namespace=""`, `top_k=1`, temperature zero), parses the first usable JSON array, normalizes/truncates/deduplicates candidates, stamps them as source `system` and provenance `inferred`, then batch-uploads unless `dry_run` (`conversation_memory_extraction_service.py:29-78,98-190`; `routes/memory.py:661-773`). The backend sees no candidate-level exclusion audit.

**Recall.** `POST /recall` resolves the limit, verifies types/status/session, then `search_memories` creates Moorcheh filter tokens, fans one query per requested type in parallel, widens the pool to 100 when client-side filters may discard items, merges by score, deduplicates by ID, applies temporal/status/confidence filters, and slices offset/limit (`routes/memory.py:924-993`; `memory_read_service.py:114-315`). All-status recall is the default, so expired records remain visible unless callers narrow it (`memory_read_service.py:835-857`).

**Grounded answer.** `POST /answer` passes question, context limit, temperature, optional model and kiosk-only threshold directly to Moorcheh `answer.generate`; the response exposes only answer text plus backend sources (`routes/memory.py:995-1109`; `memory_read_service.py:860-893`).

**Conflict/lifecycle.** Conflict reports are generated retrospectively from session summaries and stored memory (`daily_analysis_service.py:271-415`). Resolution is a later, report-indexed CLI/client operation: delete old/new/both, expire selected records, keep both as a no-op, or delete both then insert a manual replacement (`direct_client.py:1568-1753`). Expiry policies do nothing until an explicit sweep; purge is a separate explicit destructive pass (`memory_policy_service.py:1-9,352-503`).

### Configuration surface

Server settings and defaults are frozen in `Settings`: backend and Moorcheh URL/provider/timeout; host, port, debug; CORS origins/credentials; signing secret; session duration/extension/renew/recreate settings; inert legacy default TTL; answer model, temperature, context limit and threshold; summary model; recall limit; schedule time; auto-parse; and UI mode (`config.py:129-193`). The exact variables are `MOORCHEH_API_KEY`, `MEMANTO_BACKEND`, `MOORCHEH_ONPREM_URL`, `MOORCHEH_ONPREM_EMBEDDING_PROVIDER`, `MOORCHEH_ONPREM_TIMEOUT`, `HOST`, `PORT`, `DEBUG`, `ALLOWED_ORIGINS`, `CORS_ALLOW_CREDENTIALS`, `MEMANTO_SECRET_KEY`, `SESSION_DEFAULT_DURATION_HOURS`, `SESSION_AUTO_EXTEND`, `SESSION_EXTEND_THRESHOLD_MINUTES`, `SESSION_AUTO_RENEW_ENABLED`, `SESSION_AUTO_RENEW_INTERVAL_HOURS`, `SESSION_AUTO_RECREATE_ENABLED`, `DEFAULT_TTL_SECONDS`, `ANSWER_MODEL`, `ANSWER_TEMPERATURE`, `ANSWER_LIMIT`, `ANSWER_THRESHOLD`, `SUMMARY_MODEL`, `RECALL_LIMIT`, `MEMANTO_SCHEDULE_TIME`, `AUTO_PARSE_ENABLED`, and `MEMANTO_UI_MODE` (`config.py:133-189`). `MOORCHEH_BASE_URL` and `MEMANTO_CLIENT` are read outside `Settings` (`cli/client/direct_client.py:80`; `utils/client_identity.py:189-199`).

Config precedence is mixed: project `.env`, then `~/.memanto/.env` with override; selected YAML keys are copied into process environment; exported session toggles win through `setdefault`; and on-prem state JSON supplies URL/provider (`config.py:19-96`). YAML exposes answer model/temperature/limit, summary model, smart parse, session auto-renew/recreate and backend, but not every `Settings` field (`config.py:25-77`). Integration-specific variables include `MEMANTO_AGENT_ID`; Langfuse API/public/secret key and host; Mem0, Letta and Supermemory keys; and `HERMES_HOME` (`cli/config/manager.py:145-228`; `integrations/mcp/memanto_mcp/config.py:13-45`; `integrations/langfuse/langfuse_memanto/config.py:21-57`; `integrations/hermes-agents/hermes_memanto/provider.py:127,643-651`).

Per-request settings are memory type, title, confidence, tags, writer source and provenance; extraction dry-run/max/model; recall types/tags/source/tool/status/limit/offset/temporal bounds/min-confidence; answer limit/threshold/temperature/model/kiosk mode; conflict action; and policy contents/preset/sweep/purge (`models/__init__.py:32-196`; `routes/memory.py:924-1669`).

### Tests read, exercised, and skipped

I read every root test filename and the tests targeting memory format, parsing, extraction, write/update, confidence, multi-type recall, temporal recall, pagination, lifecycle policy, conflict client, sessions, API/auth, config overlay, export/OKF and post-commit resilience. I sampled CLI, migration, Langfuse and UI-auth tests where they reveal a design boundary. Relevant evidence is cited below. I did not line-read every assertion in the 2,800-line `test_unit.py`, every migration-provider case, generated TypeScript SDK tests, integration-package tests, benchmark fixtures/results, or browser HTML/JS behavior; those are adapter/product verification rather than the Kivi memory-core decision space.

Test collection was attempted. It did not complete in this environment: `moorcheh_sdk` is missing; ambient `DEBUG=release` violates the boolean settings model; and the pytest asyncio plugin/config is absent. This is an environment result, not a repository failure. Static collection reached 295 tests in 20 modules before errors. No claim below depends on a passing local suite.

The tests substantially exercise schema bounds and legacy normalization (`test_unit.py:762-891`; `test_memory_format.py:1-310`), rule/fuzzy parsing (`test_memory_parsing.py:1-253`), extraction normalization (`test_conversation_memory_extraction.py:1-168`), write/update preservation and lifecycle state (`test_unit.py:1200-1700`), client-side confidence and temporal filtering (`test_memory_read_confidence.py:1-95`; `test_memory_read_temporal_recall.py:1-310`), multi-type union ordering (`test_memory_read_multi_type.py:1-192`), policies (`test_memory_policy.py:1-465`), conflict-agent transport/cancellation (`test_agent_conflict_client.py:1-430`), and session/auth failure paths (`test_tool_sessions.py:1-494`; `test_api.py:1-940`). They mostly mock Moorcheh. Retrieval relevance, extraction truthfulness and disclosure effects are therefore not tested end-to-end.

## 1. Decision inventory

Each item is a question with multiple defensible answers. “Placement” records whether the answer is hardcoded, configurable or pluggable and what that suggests about confidence.

### D1 — What unit owns isolation: person, agent, project, tenant, or source?

- **Repo answer:** one Moorcheh namespace per `agent_id`, `memanto_agent_{agent_id}`; ordinary recall searches only that namespace (`core.py:80-82`; `memory_read_service.py:895-905`). Actor and writer are metadata, not isolation boundaries (`core.py:110-120`).
- **Placement:** hardcoded naming and routing. This reads as a high-confidence architectural invariant, although open issue [#542](https://github.com/moorcheh-ai/memanto/issues/542) says single-agent scoping blocks cross-agent recall.
- **Assumptions:** users organize memory around agents/projects; namespace count is affordable; cross-project leakage is costlier than cross-project recall friction.
- **Kivi pressure:** Kivi’s subject is one person across surfaces, while third parties must not be retained (`kivi-semantic-memory-position.md:15-29,126-158`). The difference pushes the question from project isolation toward subject/consent isolation and separate retrieval capabilities. This is comparison, not a recommendation.

### D2 — What is allowed onto the write path?

- **Repo answer:** explicit arbitrary nonblank memories, accepted file types, or LLM-extracted “durable” facts/preferences/decisions/instructions/goals/commitments/errors/observations/relationships/context/events/artifacts/learnings. Extraction prompt excludes secrets and transient chatter, but there is no code-enforced sensitive-topic or third-party filter (`models/__init__.py:24-55,112-134`; `conversation_memory_extraction_service.py:117-133`; `routes/memory.py:775-878`).
- **Placement:** categories are hardcoded; auto-parsing and extraction model/max are configurable; privacy exclusions exist only as prompt text. That indicates confidence in the 13-category ontology, lower confidence in classification, and no encoded confidence about subject eligibility.
- **Assumptions:** agent work context is broadly retainable; callers control what they submit; prompt compliance is sufficient for secrets.
- **Kivi pressure:** these assumptions do not hold. Kivi commits to a structural third-party barrier and a hard sensitive-domain candidate check with drop reasons (`kivi-semantic-memory-position.md:61-78,132-158`). Difference pushes toward candidate-level policy decisions before persistence.

### D3 — Should ingestion be verbatim, extracted, or both?

- **Repo answer:** both. Explicit `remember` has zero extraction latency, file upload delegates parsing/embedding to Moorcheh, and optional conversation extraction spends an LLM call (`routes/memory.py:410-495,661-878`; `conversation_memory_extraction_service.py:29-78`).
- **Placement:** pluggable entry paths; auto type parsing is configurable (`config.py:185-186`). This signals deliberate flexibility and a product claim that direct writes should be instantly searchable.
- **Assumptions:** callers can articulate atomic durable memories; latency-sensitive writes outweigh mandatory normalization; heterogeneous records can coexist.
- **Kivi pressure:** Kivi inputs are transcripts plus application context, with derived residue and provenance required (`kivi-semantic-memory-position.md:126-158`). The difference increases pressure on extraction/audit semantics and reduces the relevance of a wholly caller-authored write primitive.

### D4 — What ontology should a memory inhabit?

- **Repo answer:** one optional type among 13; missing/invalid extracted type falls back to deterministic parsing or effectively `fact` at serialization (`constants.py:3-18`; `core.py:140-152`; `conversation_memory_extraction_service.py:154-160`; `routes/memory.py:442-455`).
- **Placement:** hardcoded closed enumeration, with configurable auto-parse on/off. This suggests confidence that categories are stable and mutually sufficient, less confidence in how type is assigned.
- **Assumptions:** one label per memory is adequate; entity structure and relations can remain prose; epistemic origin is orthogonal metadata.
- **Kivi pressure:** Kivi separates type (`entity/preference/episode`) from tier (`stated/observed/hypothesised`) and needs relations/evidence arrays (`kivi-semantic-memory-position.md:85-122`). Memanto’s `provenance` resembles but does not enforce tier permissions. Difference pushes toward testing whether type and epistemic authority must be independently structural.

### D5 — Is memory a structured assertion or a searchable card?

- **Repo answer:** searchable card text plus flat metadata; title/content/tags are folded into a single embedded string (`core.py:133-178`).
- **Placement:** hardcoded serialization imposed by backend filtering. High confidence or backend lock-in is unclear.
- **Assumptions:** semantic similarity over prose is primary; flat filters suffice; relations, predicates, negation and evidence can remain implicit.
- **Kivi pressure:** Kivi needs attributable beliefs, relations, questions that cannot be accidentally asserted, and per-source evidence (`kivi-semantic-memory-position.md:103-122,224-247`). Difference pushes toward a richer assertion/evidence boundary; direction only.

### D6 — Who owns timestamps and ordering?

- **Repo answer:** server stamps current UTC, except imported provenance may preserve valid imported timestamps; updated records preserve creation and refresh update time (`memory_write_service.py:96-113,330-504`). Temporal queries use created/updated/expired timestamps and sort/dedup by newest known version (`memory_read_service.py:317-519,650-700`).
- **Placement:** hardcoded with a backwards-compatibility exception for imports. This looks deliberate about temporal integrity but adaptive about legacy data.
- **Assumptions:** server arrival time approximates fact/event time; clock ordering is usable; imports deserve historical placement.
- **Kivi pressure:** episode time, transcript time, observation time and confirmation time differ (`kivi-semantic-memory-position.md:85-122`). Memanto does not model that distinction, pushing Kivi’s question toward multiple temporal axes.

### D7 — What is confidence, and who is permitted to set it?

- **Repo answer:** any caller or extractor supplies a scalar `[0,1]`, default `0.8`; recall may filter numerically, while unknown legacy confidence fails open (`core.py:115`; `models/__init__.py:43`; `conversation_memory_extraction_service.py:165-169`; `memory_read_service.py:815-832`).
- **Placement:** configurable per record/request, but semantics are hardcoded nowhere. This reveals low confidence about calibration and high confidence that a scalar is useful.
- **Assumptions:** confidence values from humans/models/sources are comparable; `0.8` is a sensible missing value; unknown is safer to include than exclude.
- **Kivi pressure:** Kivi’s authority is categorical and confirmation-based, and nothing self-promotes (`kivi-semantic-memory-position.md:91-118`). Difference pushes away from treating one score as both evidence strength and permission.

### D8 — How are duplicates defined and resolved?

- **Repo answer:** extraction removes exact normalized `(type, lowercased whitespace-collapsed content)` duplicates within one model response (`conversation_memory_extraction_service.py:141-186`). Recall defensively deduplicates identical IDs, keeping the newest timestamped version (`memory_read_service.py:244-279,650-700`). Semantic duplicates across IDs survive until conflict analysis, where duplicate/compatible items are currently omitted from normalized contradictions (`daily_analysis_service.py:271-310`).
- **Placement:** hardcoded local heuristics; backend upload with the same ID is an upsert (`memory_write_service.py:460-495`). Confidence is high for identity semantics, low/unclear for semantic duplication.
- **Assumptions:** callers usually provide fresh UUIDs; duplicates are tolerable; exact text dedup catches common extraction repetition.
- **Kivi pressure:** repeated evidence should increment evidence count rather than silently form duplicate memories (`kivi-semantic-memory-position.md:112-118,142-154`). Difference pushes toward separating repeated support from duplicate assertion identity.

### D9 — What happens when evidence contradicts an existing memory?

- **Repo answer:** ordinary writes do not synchronously check or suppress contradictions. A later conflict-analysis job proposes conflicts; a user/action then keeps, deletes, expires, or manually replaces records (`daily_analysis_service.py:271-415`; `models/__init__.py:137-174`; `direct_client.py:1568-1753`).
- **Placement:** conflict detection is pluggable/backend-agent-driven and resolution action is caller-selectable. The decoupling suggests low confidence in automated resolution and acceptance of temporary coexistence.
- **Assumptions:** deferred cleanup is acceptable; a report index is stable enough; users/operators can adjudicate; destructive deletion is sometimes appropriate.
- **Kivi pressure:** Kivi says contradictions supersede immediately and history remains auditable (`kivi-semantic-memory-position.md:259-276`). Memanto removed trust/version-link fields (`constants.py:86-95`), while public issue [#541](https://github.com/moorcheh-ai/memanto/issues/541) still asks for inspectable supersession. Difference pushes toward deciding whether contradiction is a write transaction, a review workflow, or both.

### D10 — Should corrections mutate in place, append a version, or suppress re-derivation?

- **Repo answer:** edit is same-ID upsert; hard delete removes; expire preserves but can restore. There is no version chain and no suppression tombstone (`memory_write_service.py:330-600`; `constants.py:86-95`).
- **Placement:** hardcoded lifecycle. Versioning is absent/incomplete rather than clearly rejected: issue #541 remains open and removed fields are explicitly guarded against resurrection (`constants.py:86-95`).
- **Assumptions:** latest row is enough for edit history; expired state captures retirement; extractor reprocessing/regrowth is outside the model.
- **Kivi pressure:** does not hold: “not me anymore” and “forget” must prevent re-derivation from old transcripts (`kivi-semantic-memory-position.md:263-276`). Difference strongly increases the value of a durable negative/suppression event.

### D11 — What should expiry mean?

- **Repo answer:** expiry is reversible state, stamped with when/why; nothing expires automatically until a sweep; purge is separate and defaults to never (`core.py:126-131,184-194`; `memory_policy_service.py:1-9,352-503`). Legacy no-status records are active (`memory_read_service.py:835-857`).
- **Placement:** custom policy is configurable/pluggable, with hardcoded presets. This shows confidence in lifecycle semantics but treats windows as tunable.
- **Assumptions:** scheduled/explicit maintenance exists; stale records may remain searchable; lifecycle observability matters more than invisible TTL.
- **Kivi pressure:** broadly aligned on revisability, but Kivi distinguishes observation decay, hypothesis expiry and suppression (`kivi-semantic-memory-position.md:259-276`). Difference pushes toward type/tier-specific semantic transitions rather than one generic expired state.

### D12 — What gets discarded, and is discard observable?

- **Repo answer:** blank/invalid extraction items, excess messages/content/memories, invalid types (type becomes `None`), overlong memory tails (ellipsis), within-response duplicates, secrets/transient chatter if the model obeys, malformed confidence (reset to `0.8`), and malformed JSON arrays (try another array, then fail) (`conversation_memory_extraction_service.py:63-78,80-115,117-190`). Only returned candidates and aggregate errors are exposed; per-candidate drop reasons are not.
- **Placement:** mostly hardcoded normalization, with prompt-level semantic exclusions. This suggests operational robustness is deliberate; auditability of rejection is unexamined.
- **Assumptions:** silent normalization is acceptable; truncation does not change meaning; model output is expendable.
- **Kivi pressure:** Kivi explicitly commits to a dropped-candidate log and “read, not kept” evidence (`kivi-semantic-memory-position.md:67-78,151-158`). Difference pushes toward discard as a first-class outcome.

### D13 — What is retrieved and how is it ordered?

- **Repo answer:** one similarity query per selected type, merged by backend score descending; candidate pool up to 100; exact metadata filters plus client-side temporal/confidence/status filters; final offset/limit slicing (`memory_read_service.py:114-315`). Recent and changed-since paths sort by timestamps instead (`memory_read_service.py:419-580`).
- **Placement:** result limit and answer threshold are configurable; 100-pool/backend max and score merge are hardcoded. This reveals confidence in a single comparable score, with a patched hedge against post-filter starvation.
- **Assumptions:** per-type scores are comparable; 100 candidates cover filtered recall; one-stage retrieval needs no reranker; one agent namespace is enough.
- **Kivi pressure:** Kivi requires retrieval independent of disclosure and a structurally restricted dictation path (`kivi-semantic-memory-position.md:183-223`). Memanto has no disclosure stage or capability-separated store. Difference pushes toward separating candidate relevance, epistemic eligibility and use/disclosure order.

### D14 — Should expired/low-confidence records fail open or fail closed?

- **Repo answer:** recall defaults to all statuses; legacy missing status is active; unknown confidence survives a minimum-confidence filter; malformed expiry timestamp in historical recall fails open (`memory_read_service.py:281-293,372-398,815-857`).
- **Placement:** hardcoded backwards-compatible safety bias. This is deliberate compatibility, not accident.
- **Assumptions:** omission is worse than stale/uncertain inclusion; callers/UI will label status; legacy records are valuable.
- **Kivi pressure:** low-authority content may not be disclosed under Anbu and hypotheses may never be asserted (`kivi-semantic-memory-position.md:166-211`). Difference reverses the failure cost for disclosure even if retrieval remains fail-open.

### D15 — What should a caller see?

- **Repo answer:** remember returns identifiers/status/type/provenance/confidence; recall returns normalized memory cards including score/source/provenance/status; answer returns generated text and backend sources (`models/__init__.py:226-312`; `routes/memory.py:466-495,965-1109`). No used/withheld distinction or source-transcript evidence chain exists.
- **Placement:** hardcoded API contract, SDK-generated. This indicates confidence in memory records as the explainability unit.
- **Assumptions:** backend “sources” are enough provenance; callers can interpret scores; withheld items are not a concept.
- **Kivi pressure:** Kivi commits to a Why panel showing retrieved, withheld, used and transcript source, including for abstentions (`kivi-semantic-memory-position.md:236-247`). Difference expands response state beyond answer plus citations.

### D16 — What happens on failure after the memory commit?

- **Repo answer:** activity/Markdown session summary logging is best-effort and may fail without rolling back the committed memory (`session_service.py:758-788,852-874`; `routes/memory.py:466-495`). Same-ID update uploads before losing the original, relying on backend upsert atomicity (`memory_write_service.py:460-504`). Batch results count per-item validation/upload failures (`memory_write_service.py:169-318`).
- **Placement:** hardcoded consistency boundary. This is deliberate prioritization of semantic persistence over auxiliary audit completeness.
- **Assumptions:** missing local audit entries are tolerable; backend upsert is atomic/idempotent; retries can use the same ID.
- **Kivi pressure:** Kivi’s trust claims depend on complete extraction/drop/source traces (`kivi-semantic-memory-position.md:61-78,236-247`). Difference raises the failure cost of audit-write loss.

### D17 — What does the system do when confidence/retrieval is insufficient?

- **Repo answer:** no application-level abstention policy. `answer.generate` receives optional kiosk threshold; the backend decides answer behavior. Search can return zero rows; malformed backend responses become operation errors (`models/__init__.py:177-196`; `memory_read_service.py:187-241,860-893`).
- **Placement:** threshold configurable, behavior delegated. This reveals uncertainty/outsourcing of the abstention contract.
- **Assumptions:** grounded-answer backend handles insufficiency; caller does not require a structured search trace.
- **Kivi pressure:** does not hold. Kivi defines abstention language and inspectable searched alternatives (`kivi-semantic-memory-position.md:224-247`). Difference pushes abstention into product semantics rather than backend generation behavior.

### D18 — Is observation frequency allowed to become authority?

- **Repo answer:** no automatic promotion mechanism exists, but neither is there an enforced tier boundary. `observed`, `inferred`, `validated`, `corrected` are peer provenance labels and updates can preserve/alter provenance through allowed service fields (`constants.py:39-73`; `memory_write_service.py:330-457`).
- **Placement:** metadata is hardcoded, permission semantics absent. Intent is unclear.
- **Assumptions:** provenance is descriptive rather than capability-bearing; agents/callers use it responsibly.
- **Kivi pressure:** Kivi explicitly prohibits self-promotion and requires confirmation events (`kivi-semantic-memory-position.md:103-118`). Difference pushes provenance from display metadata toward enforced authorization state.

### D19 — Which operations are idempotent, and what ordering is assumed?

- **Repo answer:** same-ID upload/update is treated as idempotent upsert (`memory_write_service.py:460-495`); UUID-default writes are not idempotent under retry (`core.py:89`). Session summary appends are serialized only within the process (`session_service.py:829-850`). Conflict resolution assumes the dated report and its list index still identify the intended pair (`models/__init__.py:137-174`; `direct_client.py:1568-1645`). Temporal duplicate resolution selects the newest known timestamp (`memory_read_service.py:650-700`).
- **Placement:** mixed hardcoded mechanics; no caller idempotency key. Confidence in backend upsert is explicit; distributed ordering is unaddressed.
- **Assumptions:** one process usually writes local summaries; clients can retain IDs; report contents do not reorder between display and action.
- **Kivi pressure:** transcript replay and suppression require deterministic reprocessing (`kivi-semantic-memory-position.md:263-276,306-314`). Difference raises questions about source-derived identity and event ordering.

### D20 — Who may write on behalf of whom?

- **Repo answer:** session token scopes agent namespace, while `source` is an open but syntax-bounded writer label and `actor_id` is set from the session (`core.py:27-43,110-120`; `routes/memory.py:377-466`). Source is caller-declared; client identity can be inferred from headers/environment (`utils/client_identity.py:130-207`).
- **Placement:** pluggable labels within hardcoded syntax constraints. This reflects confidence in attribution visibility, not cryptographic writer identity.
- **Assumptions:** authenticated agent scope is the principal security boundary; source spoofing is low-cost.
- **Kivi pressure:** source transcript and person-about-whom are trust-critical (`kivi-semantic-memory-position.md:15-29,251-276`). Difference pushes toward separating writer, subject, speaker and evidence origin.

## 2. Magic numbers

“Origin” is from comment/history where traceable; otherwise **unclear**. “÷10 / ×10” describes pressure, not a recommendation. UI pixel values, HTTP status codes, calendar conversion constants, test fixture values and generated SDK literals are excluded because they are not behavioral thresholds in the memory system.

| Number | Decision frozen | Location | Origin / tuned vs guessed | If ~10× lower | If ~10× higher |
|---|---|---|---|---|---|
| 64 | writer/expiry-token/tag length | `core.py:18-20,32-41,50-60` | Moorcheh filter-token syntax is stated; length origin unclear; likely conservative guess | rejects integration names/tags | larger metadata/filter abuse surface |
| 20 | tags per memory | `core.py:21`; `models/__init__.py:44` | unclear; guessed | multi-facet records lose labels | long embedded tag tails and noisy filters |
| 512 | source reference length | `core.py:23-25` | unclear; guessed | long URIs/trace IDs fail | larger metadata payloads |
| 100 / 10,000 | title/content chars | `core.py:91-92`; `models/__init__.py:35-42` | title format bug explains single-line normalization, not sizes; guessed | lossy titles and unusably small memories | embedding dilution, cost/context and oversized records |
| 0.8 | default confidence | `core.py:115`; `models/__init__.py:43`; `conversation_memory_extraction_service.py:165-169` | no comment/blame rationale found; guessed | defaults are filtered/devalued | nearly every unknown appears authoritative (bounded at 1) |
| 100 | batch documents | `models/__init__.py:81-85`; `memory_write_service.py:169-190` | service says Moorcheh request limit; inherited backend constraint | more calls/latency | backend rejects or request size spikes |
| 200 turns | extraction conversation limit | `models/__init__.py:115-119`; `conversation_memory_extraction_service.py:21-23` | unclear; guessed safety cap | longer conversations are partly invisible | prompt cost/context failures |
| 120,000 chars | total extraction text | `conversation_memory_extraction_service.py:21-24,98-115` | unclear; guessed character proxy for tokens | drops most long sessions | model context/cost failures |
| 20 default / 100 max | memories per extraction | `models/__init__.py:125-129`; `conversation_memory_extraction_service.py:21-22,34-42` | unclear; guessed | misses distributed durable facts | over-extraction/noise/write cost |
| 1 top-k / 0 temperature | raw extraction LLM call | `conversation_memory_extraction_service.py:44-51` | top-k is API requirement workaround; deterministic extraction intent inferred; deliberate | top-k cannot go meaningfully lower; temperature fixed | retrieval is irrelevant with empty namespace; temp increase makes repeated extraction unstable |
| 80 / 100 | derived extracted title slice/cap | `conversation_memory_extraction_service.py:162-164` | unclear; guessed | opaque titles | clashes with schema cap unless schema also changes |
| 50 | explicit-write derived title | `routes/memory.py:446-455` | unclear; guessed and inconsistent with extractor’s 80 | poorer scanability | approaches 100-char schema max |
| 47+`...` / 50 | manual conflict replacement title | `direct_client.py:1732-1734` | preserves a 50-char display target; unclear | poorer scanability | eventually violates 100-char cap |
| 100 | Moorcheh max top-k and post-filter pool | `memory_read_service.py:54-60,171-185` | backend cap stated. History reversed 100→30→100 (`48978fb`, `1a8dd58`); high-value reversal, evidence of operational tuning | filtered recall starves; earlier 30 did | impossible without backend/API change; more latency/results |
| 10 | default recall results | `config.py:179-180`; `memory_read_service.py:114-122` | unclear; guessed UX/context cap | misses relevant memories | more caller tokens/noise |
| 15 | answer context memories | `config.py:170-174` | unclear; guessed | poorer answer coverage | higher prompt cost/distraction |
| 0.01 | answer relevance threshold | `config.py:173-174` | unclear; very permissive, likely guessed | effectively zero filtering | at 0.1 may drop weak but useful matches |
| 0.7 | answer temperature | `config.py:170-174` | conventional inherited LLM default; no repo rationale | more deterministic/possibly terse | capped request range is 2; high variance/hallucination risk |
| 100 | max answer/recall request limit | `models/__init__.py:181-192`; `routes/memory.py:387-409` | aligns backend top-k; deliberate constraint | less context/recall | backend cannot supply it in one call |
| 2,048 / 1,800 tokens | embedding context/query budget | `daily_analysis_service.py:31-35` | explicit backend-model context with headroom; deliberate | poor day coverage | exceeds target embedding context |
| 10 | evenly sampled summary chunks | `daily_analysis_service.py:75-103` | unclear; guessed coverage heuristic | loses temporal breadth | tiny disconnected fragments |
| 50 | daily summary retrieval top-k | `daily_analysis_service.py:187-198` | unclear; guessed | misses stored context | reaches backend cap at 100, more latency/noise |
| 300s / 3s | conflict-agent timeout/poll | `clients/agent_conflict.py:15-16` | cold/long agent runs inferred; no exact rationale | premature failure / more aggressive polling if interval lower | five-minute→50-minute stalls / sluggish cancellation if interval higher |
| 300s | on-prem HTTP timeout | `config.py:139-141` | comment: Ollama first-call cold starts exceed SDK’s 30s; deliberate | cold start failures recur | failures hang ~50 minutes |
| 3d, 14d, 30d, 60d, 90d, 180d, 365d | lifecycle preset windows | `policy_presets.py:29-113` | prose gives qualitative decay order only; exact values unclear, likely guessed starting points | durable work disappears quickly; 3d becomes hours | stale context persists months/years |
| 0.5 | “low-confidence” preset cutoff | `policy_presets.py:67-72,103-109` | unclear; guessed midpoint | only extreme uncertainty expires | most inferred/imported memories expire |
| 6h / 30m / 15m | session duration, extension threshold, warning | `config.py:108-117,156-165` | unclear; conventional work-session guess | token churn/interruptions | stale authorization persists days |
| 3,600s | `DEFAULT_TTL_SECONDS` | `config.py:167-168` | legacy/inert: TTL behavior was removed (`f2ed9c7`, `4c56e6a`) | no active effect found | no active effect found; its presence risks accidental resurrection |
| 23:55 | daily schedule | `config.py:182-183` | likely end-of-day convention; timezone semantics elsewhere; unclear | not magnitude-scalable | not magnitude-scalable; changing time shifts what “day” sees |
| 300s / 30d | live activity window/retention | `activity_service.py:45-47` | unclear; UI operational defaults | connections flicker / little history | stale “live” state / larger logs |
| 30 days | UI activity query maximum | `ui/routes/ui_router.py:63` | aligns activity retention; deliberate | limits inspection | backend has no older retained activity |
| 8 | tokenizer LRU cache | `daily_analysis_service.py:38` | unclear; guessed model variety | repeated tokenizer setup | small memory increase only |
| 88 | fuzzy classifier cutoff | `memory_parsing_service.py:34-39` | tests distinguish typos/false positives; likely tuned against small handcrafted cases (`test_memory_parsing.py:212-253`) | many false type matches | fuzzy fallback almost never fires |
| 3 | minimum deterministic rule score | `memory_parsing_service.py:34` | rule weights/tests imply handcrafted tuning; no corpus trace found | weak keywords dominate | nearly everything falls back to fact |
| 500 / 7d / 60s / 200 pages / 1,000 observations / 100 scores / 200 traces | Langfuse migration/export bounds | `cli/analyze/langfuse_export.py:34-56` | API/operational guard mix; origins unclear | incomplete migrations | API load, long runs, memory use |
| $0.15/$1.00 per 1M, 2.5× | ingestion cost estimator | `cli/analyze/ingestion_cost.py:10-14` | explicitly defaults, pricing origin not cited; temporally fragile guess | under/over-estimation depending move | same; these are accounting assumptions, not memory semantics |

## 3. What the history says

### Reversals and rewrites

These are the highest-value signals because the repository tried more than one defensible answer.

1. **TTL → status lifecycle → accidental TTL reintroduction removal.** Commit `8a8a605` replaces TTL with active/expired lifecycle; `4c56e6a` and `f2ed9c7` remove reintroduced/inert TTL fields. Current code says expiry is sweep-driven and reversible (`memory_policy_service.py:1-9`; `core.py:126-131`). The surviving `DEFAULT_TTL_SECONDS` is incomplete cleanup (`config.py:167-168`). Stated commit reason: distinguish reversible expiry from destructive purge; exact original PR discussion was not recoverable from the public page. This is an explicit high-value reversal.

2. **Rich status/trust metadata removed, then a smaller lifecycle returned.** `b89420e` removed `provisional/active/deleted/superseded`; `3f9a9af` reverted enough to keep active; later `8a8a605` introduced `active|expired`. Current code actively strips old supersession/validation/contradiction fields (`constants.py:86-95`; `memory_write_service.py:56-73,394-399`). This implies the original richer answer was operationally dead/incomplete, not that versioning ceased to matter: public issue [#541](https://github.com/moorcheh-ai/memanto/issues/541) still requests it.

3. **Conflict resolution behavior was implemented then reverted.** `0698169` is `Revert "...fix/conflict-resolution-behavior"`; current resolution remains a later report-indexed mutation in `DirectClient` (`direct_client.py:1568-1753`). Stated reason beyond the commit subject is unclear. This is a high-value reversal, but intent must remain **unclear**.

4. **Retrieval top-k 100 → 30 → 100.** `48978fb` reduced the cap; `1a8dd58` raised it. Current comments anchor 100 to the backend cap and widen post-filter queries to it (`memory_read_service.py:54-60,171-185`). Nearby history `121dcef` states post-retrieval filters were starving results. This is a high-value reversal driven by correctness/recall pressure rather than product taste.

5. **Current-state recall removed; temporal primitives rewritten.** `df3fa47` removed “current state recall”; `d69ae51` and `8d75a6c` standardized as-of/changed-since/recent. The current surface exposes those three temporal questions (`routes/memory.py:1247-1394`). This implies a broad semantic abstraction was replaced by explicit query semantics.

6. **Scope concept removed in favor of `agent_id`.** `6b3a5ff` states this simplification; current namespace construction is solely agent based (`core.py:80-82`). Open cross-agent issue #542 demonstrates the simpler answer stopped covering multi-agent search.

7. **Synchronous contradiction handling gave way to batch prefetch and later agent-based analysis.** History includes `fe64d5b` (write-time resolution), `e377a05` (batch prefetch), and recent `e264349`/`a368c79` (agent conflict analysis/contradict-memory). Current ordinary store has no contradiction transaction (`memory_write_service.py:115-318`); analysis is separate (`daily_analysis_service.py:271-415`). This is a rewrite across latency/cost/control boundaries; exact causal rationale is **unclear** from code.

### Recurring bug clusters

- **Temporal and backwards-compatible recall:** malformed/null/epoch timestamps, date-only end-of-day, since-expired as-of records, duplicate version choice (`memory_read_service.py:35-51,317-419,650-700`). History: `d645545`, `db923f5`, `d6bb706`, `79f9675`, `cd259a0`, `0b40867`. Recurrence shows time semantics are load-bearing and heterogeneous storage shapes are normal.
- **Filter starvation/pagination:** numeric confidence filtering, temporal filters after top-k, repeated pagination tokens (`memory_read_service.py:171-185,582-678,815-832`). History: `52b31cf`, `121dcef`, `e6765cf`, `8bffa8b`.
- **Serialization/metadata preservation:** falsey values, tags, provenance, extra imported metadata, title newline corruption (`core.py:94-108`; `memory_write_service.py:23-73,330-504`; `memory_read_service.py:936-1058`). History: `270563b`, `07d7101`, `e25bc56`, `be113d9`, `e6d7874`.
- **Session/token lifecycle and concurrency:** auto-regeneration, summary append races, stale active markers (`session_service.py:829-953`; `auth_deps.py:225-350`). History: `22505b0`, `b3cc625`, `0c9e816`; tests at `test_session_summary_concurrency.py:1-131`, `test_tool_sessions.py:1-494`.
- **Conflict jobs exceeding context or running too long:** open issue [#1329](https://github.com/moorcheh-ai/memanto/issues/1329) says active-day conflict queries can exceed embedding context; recent commits add truncation, streaming, polling and cancellation. Current fixed budgets and cancellation hooks are at `daily_analysis_service.py:31-103` and `agent_conflict.py:15-38,315-470`.

### TODOs, shortcuts and admitted incompleteness

- Session summaries report a placeholder memory count: `# TODO: Get actual memory count from backend` (`session_service.py:526`). This is incomplete work, not design.
- Missing/invalid config files warn and continue (`config.py:27-96`); auxiliary post-commit summaries are explicitly best-effort (`session_service.py:758-788,852-874`). These are deliberate degraded-mode choices.
- Unknown/malformed legacy fields frequently fail open (`memory_read_service.py:372-398,815-857`). Comments identify backwards compatibility, not idealized semantics.
- Windows active-session markers fall back from symlink to a plain file (`session_service.py:876-894`). This is platform adaptation.
- Extraction exclusions are prompt-only (`conversation_memory_extraction_service.py:117-133`). There is no comment admitting the privacy shortcut, so classify it as an unexamined gap rather than deliberate privacy design.

### Abstractions added later

- Backend abstraction (`cloud|on-prem`) and normalized model selection (`clients/backend.py:18-78`) came after a cloud-only design; public [on-prem announcement](https://github.com/moorcheh-ai/memanto/discussions/744) states data-residency demand drove it.
- Policy service/presets (`memory_policy_service.py:276-503`; `policy_presets.py:29-115`) came after TTL removal, implying per-record timer semantics did not express reversible lifecycle/retention.
- Conversation extraction service (`conversation_memory_extraction_service.py:18-190`) adds an LLM path beside direct ingestion, implying caller-authored atomic memories were insufficient for chat imports.
- Client identity/activity service (`utils/client_identity.py:70-207`; `services/activity_service.py:45-388`) came with live connections, implying generic `source=agent` did not provide adequate observability.
- Temporal recall variants and legacy normalizers (`memory_read_service.py:317-700,936-1058`) accumulated after initial retrieval, implying “similarity search plus metadata” was not enough for historical truth.

## 4. Unexamined defaults

These have no nearby rationale, alternative implementation or behavior-distinguishing test found.

| Question not visibly deliberated | Default | Alternative not tried in this repo | Evidence |
|---|---|---|---|
| Should a memory have one type? | exactly one optional label | multi-label or entity/relation schema | `core.py:89-92`; `constants.py:3-18` |
| Should missing type mean fact? | serialization falls back to `fact` | reject, preserve unknown, or infer at read | `core.py:140-152` |
| Should confidence be scalar/comparable? | caller/model scalar, default `0.8` | categorical authority or source-calibrated distributions | `core.py:115`; `models/__init__.py:43` |
| Should the writer’s label be trusted? | caller-declared bounded string | authenticated writer principal | `core.py:27-43`; `models/__init__.py:45-51` |
| Should content and metadata both influence embedding? | title/content/tags embedded together | field-specific embeddings or structured ranking | `core.py:142-169` |
| Should retrieval score order cross types? | merge per-type searches by raw score | quotas, calibrated per-type scores, reranking | `memory_read_service.py:147-279` |
| Should expiry be visible by default? | `status=all` | active-only default with history opt-in | `memory_read_service.py:114-122,835-857` |
| Should unknown confidence be included? | fail open | exclude/label/route for review | `memory_read_service.py:815-832` |
| Should extraction truncation preserve the beginning? | stop after prefix of conversation; truncate candidate tail | recency window, sampled coverage, summarization | `conversation_memory_extraction_service.py:98-115,148-153` |
| Should exact text identify duplicate extraction? | lowercased whitespace-normalized content + type | semantic identity, predicate/entity key, evidence merge | `conversation_memory_extraction_service.py:141-186` |
| Should observations be ordinary content? | peer memory type plus peer provenance | separate evidence aggregate with surfacing threshold | `constants.py:3-18,39-47` |
| Should silence affect hypotheses? | no hypothesis confirmation state exists | explicit non-event semantics/expiry | `constants.py:39-47`; `core.py:85-131` |
| Should conflict resolution address report index? | integer index + date | conflict UUID/version/optimistic lock | `models/__init__.py:137-174` |
| Should manual replacement delete both parents? | yes | preserve linked supersession history | `direct_client.py:1705-1753` |
| Should a generated answer expose only sources? | answer + backend source list | retrieved/used/withheld/abstention trace | `models/__init__.py:308-312`; `memory_read_service.py:860-893` |
| Should policies require a sweep? | yes | read-time decay, background scheduler, write-time expiry | `memory_policy_service.py:1-9,352-503` |

## 5. Questions this repo never faced

Derived from Kivi’s positioning; absence was checked against the core schema/routes/services. These are questions, not proposed answers.

1. How does the write path prove that content about a non-user was read for the current task but never persisted? Memanto has writer/actor, not subject/consent (`core.py:110-120` versus `kivi-semantic-memory-position.md:126-158`).
2. What is the enforcement boundary between allowed work facts about another person and forbidden personal facts/characterizations about them (`kivi-semantic-memory-position.md:132-158`)?
3. How are sensitive categories detected after extraction but before storage, and how is every rejection reason audited without retaining the sensitive payload itself (`kivi-semantic-memory-position.md:61-78`)?
4. Can a stored question be made structurally impossible to consume as a fact, rather than distinguished by prompt wording (`kivi-semantic-memory-position.md:103-109`)?
5. What event, actor and evidence transform `observed` or `hypothesised` into `stated`, and how is promotion prevented without explicit confirmation (`kivi-semantic-memory-position.md:110-118`)?
6. Does the permission dial gate retrieval, ranking, tool use, prompt inclusion, generated text, or final disclosure—and how can withholding be proven (`kivi-semantic-memory-position.md:183-211`)?
7. How can regular dictation be structurally incapable of reading observation/hypothesis data even if an injection or implementation bug requests it (`kivi-semantic-memory-position.md:213-223`)?
8. What is the smallest trace that lets a normal person distinguish retrieved, used and withheld memories without becoming a system administrator (`kivi-semantic-memory-position.md:236-247`)?
9. What does a useful abstention return: missing answer, search domain, near misses, provenance, and a next action (`kivi-semantic-memory-position.md:224-247`)?
10. How is a correction represented so old transcripts remain auditable but cannot regenerate the rejected belief (`kivi-semantic-memory-position.md:263-276`)?
11. Do observations decay because of elapsed time, contrary evidence, lack of re-observation, changing context, or an explicit user action (`kivi-semantic-memory-position.md:259-276`)?
12. How are confirmation prompts budgeted by user cost/value, and what state records that a prompt was offered, ignored, accepted or rejected (`kivi-semantic-memory-position.md:232-239`)?
13. How does the system distinguish event time, utterance time, extraction time, first-seen time and last-confirmed time (`kivi-semantic-memory-position.md:112-118`)?
14. How is evidence count defined when multiple transcripts paraphrase the same claim, and when does repetition by one source cease to be independent evidence (`kivi-semantic-memory-position.md:112-118`)?
15. What does “Forget” mean when source transcripts, derived memories, caches, exports, traces and suppression tombstones all exist (`kivi-semantic-memory-position.md:251-276`)?
16. How can Kivi preserve an auditable supersession chain while satisfying a request to remove content (`kivi-semantic-memory-position.md:251-276`)?
17. How are per-request Daari invitations recognized without silently inferring a persistent permission from tone (`kivi-semantic-memory-position.md:193-202`)?
18. Does model-generated reasoning from a Daari request become transient output, a hypothesis candidate, or prohibited writeback (`kivi-semantic-memory-position.md:193-202`)?
19. What evaluation distinguishes “removes re-explanation” from “delivers an insight,” since both may look relevant to a semantic retriever (`kivi-semantic-memory-position.md:80-84`)?
20. How is provenance shown when one belief is synthesized from distributed evidence rather than copied from one memory card (`kivi-semantic-memory-position.md:303-314`)?

## 6. What the tests do not cover

These are decisions for which a materially different implementation could still satisfy the current suite. Therefore the repository supplies precedent, not evidence.

- **Retrieval quality.** Unit tests mock ranked Moorcheh results and verify merging/filtering; they do not show that a real query retrieves the right Kivi fact, near miss or absence (`test_memory_read_multi_type.py:1-192`; `test_memory_read_confidence.py:1-95`). A different embedding/ranker could pass.
- **Cross-type score comparability.** Tests verify the code sorts supplied numeric scores, not that scores from independent type queries share calibration (`memory_read_service.py:244-279`; `test_memory_read_multi_type.py:95-192`).
- **Extraction truth and privacy.** Tests feed canned JSON and validate normalization; they do not run a model over third-party personal material, excluded sensitive topics, prompt injection or distributed evidence (`test_conversation_memory_extraction.py:1-168`; `conversation_memory_extraction_service.py:117-190`). A model that retains forbidden Kivi content could pass.
- **Confidence calibration.** Bounds/default/filter arithmetic are tested, but no outcome distinguishes a well-calibrated `0.8` from a guessed one (`test_memory_read_confidence.py:1-95`; `test_unit.py:762-891`).
- **Epistemic permissions.** No test asks whether inferred/observed content may be asserted, used, withheld or promoted because the implementation has no such capability boundary (`constants.py:39-47`; `core.py:119-120`).
- **Non-retention of others.** No subject field or negative persistence assertion exists (`core.py:110-120`; extraction tests at `test_conversation_memory_extraction.py:1-168`).
- **Suppression after correction.** Edit/expire/delete mechanics are tested, but no replay test proves the same derived memory cannot regrow; no suppression model exists (`memory_write_service.py:330-600`; `test_memory_policy.py:1-465`).
- **Atomic contradiction resolution.** Conflict client tests exercise action calls/transport, not concurrent writes between report generation and index-based resolution (`models/__init__.py:137-174`; `test_agent_conflict_client.py:1-430`).
- **Semantic duplicate handling.** Exact candidate dedup is testable; paraphrases across batches/IDs can coexist without failing (`conversation_memory_extraction_service.py:141-186`).
- **Actual backend idempotency.** Mocks accept same-ID upload; no failure injection proves Moorcheh upsert atomicity across network ambiguity (`memory_write_service.py:460-504`; root tests mock the SDK in `tests/conftest.py:1-170`).
- **Distributed ordering.** Local locks are in-process; tests cover threads in one process, not multiple servers or network filesystems (`session_service.py:829-850`; `test_session_summary_concurrency.py:1-131`).
- **Trace completeness after partial failure.** Tests correctly permit summary logging to fail after commit (`test_postcommit_summary_resilience.py:1-153`), but none evaluates whether an end user can detect the missing audit event.
- **Expired-memory disclosure cost.** Tests establish that `status=all` returns expired/legacy records; they do not compare user harm from stale inclusion against omission (`test_as_of_expired_recall.py:1-160`; `memory_read_service.py:835-857`).
- **Policy window fitness.** Tests verify parsing and boundary arithmetic, not whether 3/7/14/30/60/90/180/365 days match behavioral drift (`test_memory_policy.py:1-465`; `policy_presets.py:29-113`).
- **Answer abstention.** API tests check parameter forwarding and response shape, not whether absent evidence produces a transparent abstention rather than a fluent guess (`test_api.py:540-640`; `memory_read_service.py:860-893`).
- **Provenance accuracy.** Tests ensure values survive round trips/updates, not that `explicit_statement`, `inferred`, `observed`, `corrected` or `validated` were assigned truthfully (`test_unit.py:1200-1700`; `constants.py:39-47`).
- **Source authenticity.** Validation tests block filter syntax injection but do not prove the caller is the claimed writer (`test_unit.py:780-860`; `core.py:27-43`).
- **Historical truth under edits.** As-of tests cover created/expired timestamps and duplicate IDs, but same-ID upsert destroys prior content, so no test can recover “what this record said before edit” (`memory_write_service.py:330-504`; `test_memory_read_as_of.py:1-150`).
- **Kivi’s seven committed demonstrations.** None of the suite distinguishes: excluded candidate logged; third-party content used but not kept; multi-transcript evidence assembly; same retrieval with mode-dependent withholding; reasoned abstention; correction that prevents regrowth; or structural denial of observation access on dictation (`kivi-semantic-memory-position.md:303-314`).

## Closing boundary

The strongest transferable precedent in Memanto is not a particular threshold. It is the evidence that temporal semantics, metadata preservation, conflict handling, session lifecycle and post-filter retrieval repeatedly required rewrites (`memory_read_service.py:317-700`; `memory_write_service.py:330-600`; `session_service.py:829-953`). The strongest non-transferable assumption is that an authenticated agent/project namespace may treat durable work context as ordinary retainable memory (`core.py:80-120`; `conversation_memory_extraction_service.py:117-133`). Kivi’s positioning makes permission, subject, disclosure, suppression and legibility part of correctness, while this repository mostly treats provenance, confidence and lifecycle as searchable metadata (`kivi-semantic-memory-position.md:15-29,251-276`; `core.py:110-178`). That is the edge of the precedent; beyond it, the questions in §5 have no answer here.
