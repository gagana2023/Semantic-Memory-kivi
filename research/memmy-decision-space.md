# Memmy Decision Space for Kivi

Baseline: `main` at `62ec3d92` (2026-09-11). This is a map of questions and precedent, not a recommendation. “Kivi” refers to the system described in `kivi-semantic-memory-position.md:1-284`.

## Orientation

### Where the real logic lives

The load-bearing subsystem is `Memory/`, not the desktop application. `Memory/src/service/` owns capture, episode routing, retrieval, evolution, feedback, lifecycle, and background work. `Memory/src/storage/` owns persistence, indexes, conflict behavior, and ordering. `Memory/src/model/` owns LLM and embedding calls. The public façade composes those pieces in `Memory/src/service/memory-service.ts:249-600`.

The following are mostly boundaries around that core:

- HTTP transport and process lifecycle: `Memory/src/server/index.ts:18-143`, `Memory/src/server/http.ts:132-269`.
- CLI and installation: `Memory/src/cli/`.
- Source-specific ingestion and hook installation: `Memory/src/agent-source/`.
- Viewer/UI: `Memory/viewer/` and `App/frontend/`.
- Desktop shell, packaging, release automation, documentation, and examples: `App/shell/`, `scripts/`, `docs/`, and top-level smoke tests.

This distinction matters: adapter limitations are evidence about interoperability, but not necessarily about the semantic-memory model.

### Data model and frozen decisions

The canonical public types separate memories into L1 traces, L2 policies, L3 world models, Skills, and a parallel UserMemory lane (`Memory/src/types.ts:30-42`, `Memory/src/types.ts:193-221`). A general `MemoryRow` stores free-form JSON beside indexed scalar fields (`Memory/src/types.ts:129-162`); UserMemory has a separate typed record with provenance, replacement links, embeddings, and lifecycle state (`Memory/src/types.ts:355-377`).

SQLite schema version 7 freezes this split into `memories`, `user_memories`, vectors, sessions, episodes, raw turns, feedback, recall events, change logs, idempotency keys, capture claims, jobs, retries, processing state, artifacts, and audit logs (`Memory/src/storage/schema.ts:4-5`, `Memory/src/storage/schema.ts:25-132`, `Memory/src/storage/schema.ts:136-238`, `Memory/src/storage/schema.ts:403-613`). JSON is the main serialization format inside relational rows; FTS5 indexes user-memory content and general memory value/tags (`Memory/src/storage/schema.ts:82-121`). Vector rows record model, provider, and dimensionality, with one vector per memory/field (`Memory/src/storage/schema.ts:123-132`).

Protocol contracts are in `Memory/src/contracts/`; bundle serialization/import conflict handling is in `Memory/src/storage/repositories.ts:3993-4104`; the alternate remote backend is selected through `Memory/src/storage/backend.ts` and the PolarDB schema is in `Memory/src/storage/polardb.ts`.

### Main execution path: entry to persistence

1. `main()` loads environment/config, binds only a loopback host, acquires service and SQLite locks, selects the backend, constructs `MemoryService`, and starts HTTP plus agent-source automation (`Memory/src/server/index.ts:18-143`).
2. HTTP authenticates, parses JSON, injects namespace/timezone, and routes session/turn/search operations (`Memory/src/server/http.ts:132-252`, `Memory/src/server/http.ts:482-547`).
3. Session-open establishes identity/scope and may queue a project-environment scan (`Memory/src/service/memory-service.ts:902-926`).
4. Turn-start retrieves memories and returns both ranked hits and rendered injected context (`Memory/src/service/memory-service.ts:1021-1040`).
5. Turn-complete is the write boundary: it commits the route proposal, raw turn, UserMemory and/or L1 trace, change log, and jobs (`Memory/src/service/memory-service.ts:1042-1044`; behavior is tested at `Memory/tests/service/session/turn-capture.test.ts:44-154`).
6. Durable jobs then summarize, embed, score, induce L2 policies, update L3 world models, crystallize skills, and resolve trials; job kinds are enumerated in `Memory/src/types.ts:68-84`, and their persisted retry/dead-letter state is defined in `Memory/src/storage/schema.ts:501-577`.

### Config surface

The complete semantic-memory config type is `MemmyConfig`: domain, role routing, user/timezone, storage, summary LLM, evolution LLM, embedding, agent access, and algorithm (`Memory/src/config/index.ts:60-277`). File config is YAML; merge precedence is defaults, runtime YAML, then environment (`Memory/src/config/index.ts:490-520`). The environment surface is:

- `MEMMY_CONFIG` (`Memory/src/config/index.ts:490-494`).
- Domain/user: `MEMMY_MEMORY_DOMAIN`, `MEMMY_DOMAIN`, `MEMMY_MEMORY_USER_ID`, `MEMMY_USER_ID`, `MEMORY_SERVICE_USER_ID` (`Memory/src/config/index.ts:536-540`).
- Storage: `MEMMY_MEMORY_MODE`, `MEMMY_MEMORY_BACKEND`, `MEMMY_MEMORY_DB`, `MEMORY_SERVICE_DB`, `MEMMY_MEMORY_URL`, `MEMORY_SERVICE_URL`, `MEMMY_MEMORY_TOKEN`, `MEMORY_SERVICE_TOKEN` (`Memory/src/config/index.ts:540-546`).
- Summary model: `MEMMY_SUMMARY_PROVIDER`, `MEMMY_SUMMARY_VENDOR`, `MEMMY_SUMMARY_ENDPOINT`, `MEMMY_SUMMARY_MODEL`, `MEMMY_SUMMARY_API_KEY`, `MEMMY_SUMMARY_TEMPERATURE`, `MEMMY_SUMMARY_MAX_TOKENS`, `MEMMY_SUMMARY_TIMEOUT_MS`, `MEMMY_SUMMARY_MAX_RETRIES` (`Memory/src/config/index.ts:547-557`).
- Evolution model: parallel `MEMMY_EVOLUTION_*` settings plus `MEMMY_EVOLUTION_ENABLE_THINKING` (`Memory/src/config/index.ts:558-569`).
- Embedding: `MEMMY_EMBEDDING_PROVIDER`, `MEMMY_EMBEDDING_ENDPOINT`, `MEMMY_EMBEDDING_MODEL`, `MEMMY_EMBEDDING_API_KEY`, `MEMMY_EMBEDDING_MAX_INPUT_TOKENS`, `MEMMY_EMBEDDING_BATCH_SIZE`, `MEMMY_EMBEDDING_TIMEOUT_MS`, `MEMMY_EMBEDDING_MAX_RETRIES` (`Memory/src/config/index.ts:570-579`).
- Gates/injection: `MEMMY_ENABLE_MEMORY_ADD`, `MEMMY_ENABLE_MEMORY_SEARCH`, `MEMMY_ENABLE_QUERY_REWRITE`, `MEMMY_RETRIEVAL_INJECTION_PROFILE`, `MEMMY_READONLY_INJECTION_PROFILE` (`Memory/src/config/index.ts:580-589`).
- Server-only host/port aliases: `MEMMY_MEMORY_HOST`, `MEMORY_SERVICE_HOST`, `MEMMY_MEMORY_PORT`, `MEMORY_SERVICE_PORT` (`Memory/src/server/index.ts:49-57`).

Every YAML algorithm field is enumerated at `Memory/src/config/index.ts:113-259` and normalized at `Memory/src/config/index.ts:1024-1210`. Some apparent choices are not real: `capture.batchMode` has only `windowed` (`Memory/src/config/index.ts:56`), and session `followUpMode` is forced to `merge_follow_ups` during normalization (`Memory/src/config/index.ts:1174-1176`).

### What the tests exercise, and what was read

There are 814 `describe`/`it`/`test` declarations under `Memory/tests`. The review read all production files named above, the full config/type/schema surfaces, key capture/retrieval/evolution/user-memory/lifecycle implementations, the test titles and relevant bodies for configuration, schema, turn capture, UserMemory, retrieval, injection, deduplication, policy induction, L3, and lifecycle. Representative coverage is visible at `Memory/tests/service/session/turn-capture.test.ts:20-940`, `Memory/tests/service/user-memory/user-memory.test.ts:18-1270`, `Memory/tests/service/retrieval/query-and-filter.test.ts:47-1192`, and `Memory/tests/service/lifecycle/memory-lifecycle.test.ts:24-633`.

Skipped in depth: most UI component bodies, desktop shell/platform packaging, release/Yunxiao automation, documentation translations, and most source-adapter parsing bodies. Their file inventories and relevant TODO/legacy references were searched, but they were not treated as semantic precedent. Tests were inspected, not executed; this report describes asserted behavior, not a fresh green run.

## 1. Decision inventory

### What enters the system?

**Question:** Should memory be written at turn start, incrementally during execution, or only after a completed turn?

**Repo answer:** turn-start records recall/audit only; durable turn content is committed at turn-complete (`Memory/src/service/memory-service.ts:1021-1044`; `Memory/tests/service/session/turn-capture.test.ts:44-154`). Cancelled or structurally incomplete completions write nothing, while explicit failed turns are retained (`Memory/tests/service/session/turn-capture.test.ts:216-299`). This is hardcoded protocol behavior, indicating high confidence. It assumes completion events are reliably emitted and the loss cost of interrupted work is lower than the pollution cost of partial state. Kivi’s dictation path may not provide the same transactional boundary; the difference pushes the question toward explicit capture events or a recoverable draft state. This applicability judgment is inferred from `kivi-semantic-memory-position.md:181-199`.

**Question:** Should a single interaction become one memory or be split into chunks?

**Repo answer:** one source turn becomes one memory, with oversize content clipped rather than split (`AgentSourceCore/src/index.ts`; current regression test at `Memory/tests/agent-source-runtime.test.ts:25-43`). This is hardcoded. It assumes turn identity is more valuable than full payload retention. For Kivi, where one dictation can contain several independent entity/preference/episode candidates (`kivi-semantic-memory-position.md:66-103`), the assumption does not automatically hold; the difference pushes toward separating source-event identity from extracted-memory cardinality.

**Question:** Should UserMemory capture be coupled to episodic/L1 capture?

**Repo answer:** no. The two branches are judged independently, and the same turn may produce neither, either, or both (`Memory/tests/service/user-memory/user-memory.test.ts:233-481`, `Memory/tests/service/user-memory/user-memory.test.ts:1101-1194`). This is core logic with model and heuristic pluggability. It assumes different downstream uses warrant different admission criteria. That aligns with Kivi’s independent type/tier axes, but Memmy’s split is “user fact/preference/directive vs agent trace,” not Kivi’s “entity/preference/episode × stated/observed/hypothesised” (`kivi-semantic-memory-position.md:66-103`).

**Question:** Should questions, transient commands, dynamic current facts, and assistant guesses become durable user beliefs?

**Repo answer:** no. Regex gates reject question-like and dynamic current data (`Memory/src/service/user-memory/user-memory.ts:4-24`, `Memory/src/service/user-memory/user-memory.ts:34-38`), while tests explicitly reject assistant guesses and recall-only restatements (`Memory/tests/service/user-memory/user-memory.test.ts:172-232`, `Memory/tests/service/user-memory/user-memory.test.ts:511-574`). The categories are partly hardcoded and partly model-decided, revealing medium confidence in the category boundary but low confidence in pure regex sufficiency. Kivi agrees on guesses/hypotheses not becoming facts, but needs hypotheses stored as questions (`kivi-semantic-memory-position.md:91-103`); Memmy discards that lane instead.

**Question:** Should tool calls/results/reasoning be stored alongside conversational text?

**Repo answer:** raw turns can store user text, assistant text, reasoning summary, tool calls/results, artifacts, source memories, usage, and outcome (`Memory/src/types.ts:336-353`). Tool payloads are sanitized/truncated during capture (`Memory/src/config/index.ts:345-372`; `Memory/tests/service/session/turn-capture.test.ts:456-630`). L3 deliberately omits reasoning evidence (`Memory/tests/service/evolution/l3-world-model.test.ts:168-244`). This is configurable for size, hardcoded for L3 exclusion. It assumes agent-operational learning benefits from tool traces. Kivi’s third-party-content rule is stricter and source-subject aware (`kivi-semantic-memory-position.md:106-127`); Memmy’s sanitation is not evidence of that boundary.

### How is it represented and stored?

**Question:** One universal memory table or domain-specific tables?

**Repo answer:** hybrid. L1/L2/L3/Skill share `memories`, while UserMemory is separate (`Memory/src/storage/schema.ts:25-132`). This is schema-hardcoded and therefore expensive to reverse. It assumes user facts need different lifecycle/search semantics, but policies/world models/skills can tolerate JSON polymorphism. Kivi’s epistemic tier is load-bearing and user-visible (`kivi-semantic-memory-position.md:66-103`, `kivi-semantic-memory-position.md:232-251`); Memmy has no first-class stated/observed/hypothesised column, pushing the question toward whether Kivi can safely encode tier only in JSON.

**Question:** Structured facts or prose blobs?

**Repo answer:** both, but the semantic payload is mainly prose (`memory_value`/`content`) with tags and free-form JSON; indexed columns carry scope/lifecycle (`Memory/src/storage/schema.ts:25-47`, `Memory/src/storage/schema.ts:82-100`). This is schema-hardcoded with pluggable JSON shape. It assumes embedding/LLM interpretation can recover semantics from prose. Kivi requires editable entities/relations, evidence counts, tier, and provenance (`kivi-semantic-memory-position.md:96-103`), so its shape pushes toward more schema-visible epistemics than this precedent.

**Question:** Local-first storage or remote service?

**Repo answer:** local SQLite is default, with a remote OpenMem REST backend available (`Memory/src/config/index.ts:290-295`, `Memory/src/config/index.ts:45-49`). This is configurable/pluggable, revealing low confidence that one deployment model fits all users. It assumes local latency/privacy are valuable while cloud parity matters. This broadly matches Kivi’s trust position, but the source document does not decide deployment (`kivi-semantic-memory-position.md:267-274`), so fit is unclear.

**Question:** How is provenance represented?

**Repo answer:** source turn IDs, source-memory IDs, recall members/routes, policy links, batch evidence, change logs, and audit logs are all persisted (`Memory/src/types.ts:193-221`, `Memory/src/storage/schema.ts:358-371`, `Memory/src/storage/schema.ts:403-479`, `Memory/src/storage/schema.ts:599-613`). This is hardcoded and extensively tested. It assumes provenance storage cost is justified by debugging and governance. Kivi explicitly requires transcript-level provenance and an explanation surface (`kivi-semantic-memory-position.md:203-251`), so the assumption holds, but Memmy’s provenance does not encode “read, not kept” candidate counts.

### What is discarded?

**Question:** Drop uninteresting turns entirely, or retain raw observation while declining semantic promotion?

**Repo answer:** chitchat remains as raw observation but produces no L1 memory (`Memory/tests/service/session/turn-capture.test.ts:768-887`). Redacted/deleted raw turns are excluded from L3 evidence (`Memory/src/service/evolution/l3-world-model-pipeline.ts:167-179`). This is hardcoded. It assumes raw retention is acceptable even when semantic value is nil. Kivi’s rule says third-party personal content must not enter the write path at all (`kivi-semantic-memory-position.md:106-127`); that is a direct mismatch pushing the boundary earlier than Memmy’s raw store.

**Question:** Truncate oversize content or preserve it through chunking/external artifacts?

**Repo answer:** truncate at several boundaries: capture text/tool budgets (`Memory/src/config/index.ts:345-372`), imported tool payload at 20,000 chars (`Memory/src/service/import/memory-import-pipeline.ts:21-24`, `Memory/src/service/import/memory-import-pipeline.ts:260`), injected snippets at 640 chars (`Memory/src/service/retrieval/retrieval-service.ts:530-533`). This is partly configurable, partly hardcoded. It assumes the head/summary retains enough signal and bounded requests beat perfect recall. Kivi promises attributable claims; truncation may sever the decisive evidence, pushing toward an explicit evidence-preservation question.

### Duplicate, conflict, and contradiction

**Question:** What defines an idempotent duplicate?

**Repo answer:** public request idempotency combines adapter/request identity with a stable request hash and conflicts if the key is reused with a different body (`Memory/src/service/session/session-turn-service.ts:493-518`, `Memory/src/service/session/session-turn-service.ts:1222-1240`). Cross-ingestion memory capture uses `(user_id, source, qa_hash)` as a unique claim (`Memory/src/storage/schema.ts:472-480`). Exact UserMemory repeats use normalized punctuation/case/space-stripped text hashes (`Memory/src/service/user-memory/user-memory.ts:40-49`; `Memory/tests/service/user-memory/user-memory.test.ts:575-641`). These are hardcoded, indicating high confidence in event-level idempotency but limited semantic dedup confidence. Kivi needs “same claim from new evidence” to increment evidence, not merely suppress a duplicate (`kivi-semantic-memory-position.md:96-103`), so the distinction pushes toward separate claim identity and evidence-event identity.

**Question:** What happens when a user corrects a belief?

**Repo answer:** an explicit correction creates/upserts a replacement, rejects unchanged normalized content, and archives the target with bidirectional replacement links (`Memory/src/service/session/session-turn-service.ts:2590-2631`; `Memory/src/storage/repositories.ts:1478-1489`). This is hardcoded and tested (`Memory/tests/service/user-memory/user-memory.test.ts:699-788`, `Memory/tests/service/user-memory/user-memory.test.ts:954-996`). It assumes the caller identifies the exact target. Kivi wants natural inline correction and suppression against re-derivation (`kivi-semantic-memory-position.md:217-229`, `kivi-semantic-memory-position.md:232-251`); Memmy supplies supersession but no general suppression/tombstone semantics, so it only partially holds.

**Question:** If the user states a new current fact, is it a correction?

**Repo answer:** not automatically; both remain active unless the caller sends an explicit correction target (`Memory/tests/service/user-memory/user-memory.test.ts:997-1072`). This is deliberate, test-backed behavior. It assumes “new state” may be additive rather than contradictory. Kivi says contradictions supersede (`kivi-semantic-memory-position.md:238-245`), so this is a direct divergent precedent.

**Question:** How should bundle-import conflicts resolve?

**Repo answer:** `skip` by default, with `replace` and `error` alternatives (`Memory/src/storage/repositories.ts:4005-4075`). This is configurable at operation time, showing acknowledged uncertainty. It assumes primary-key equality is the conflict boundary. Kivi’s semantic contradictions are not primary-key conflicts, so this precedent does not answer them.

### Retrieval and ordering

**Question:** One retrieval channel or parallel lanes?

**Repo answer:** parallel UserMemory, L1, and agent-memory lanes, later merged; same-source-turn L1 and UserMemory hits collapse into one representative with maximum score and combined provenance (`Memory/src/service/retrieval/retrieval-service.ts:285-367`). This is hardcoded architecture with configurable limits. It assumes lane-specific recall protects high-value classes from crowding. Kivi requires structurally distinct dictation and Hey Kivi retrieval (`kivi-semantic-memory-position.md:181-199`); Memmy’s lanes are content-class lanes, not permission lanes.

**Question:** Relevance only, or relevance plus diversity and prior value?

**Repo answer:** configurable cosine/priority weighting, MMR diversity, RRF, layer-specific thresholds, and skill eta blending (`Memory/src/config/index.ts:457-485`). MMR explicitly penalizes textual overlap except between UserMemory hits (`Memory/src/service/retrieval/retrieval-service.ts:370-406`). This is configurable, showing tuning uncertainty. It assumes relevance proxies and past utility correlate with present usefulness. Kivi’s dial governs disclosure rather than retrieval (`kivi-semantic-memory-position.md:154-178`), so ranking must be separated from permission in a way this repo does not model.

**Question:** Should exact temporal queries use semantic ranking?

**Repo answer:** extracted time ranges bypass ordinary score ordering, select up to 20 recent L1 traces, then present them chronologically (`Memory/src/service/retrieval/retrieval-service.ts:448-484`, `Memory/tests/service/retrieval/query-and-filter.test.ts:367-449`). This is hardcoded. It assumes temporal completeness within a cap matters more than semantic score. Kivi’s episodic questions make this precedent relevant, but its absence/abstention promise raises the unanswered question of whether “20” can support claims of completeness.

**Question:** Should low-confidence results be withheld?

**Repo answer:** thresholds and an optional LLM filter can drop results, including all candidates; filter failure falls back to a capped raw list (`Memory/tests/service/retrieval/query-and-filter.test.ts:584-780`). Thresholds are configurable, fallback policy hardcoded. It assumes omission is preferable to irrelevant injection, but provider failure should degrade to heuristic output rather than no memory. Kivi says never fill gaps with plausible guesses and expose what was searched (`kivi-semantic-memory-position.md:203-230`); Memmy exposes recall audit structures but does not implement Kivi’s user-facing abstention contract.

**Question:** Is the caller’s context budget authoritative?

**Repo answer:** the API accepts `contextBudget` (`Memory/src/types.ts:327-334`, `Memory/src/types.ts:418-428`), but `buildInjectedContext` explicitly discards it with `void budget`, returns no budget drops, and injects every rendered section (`Memory/src/service/retrieval/retrieval-service.ts:544-628`). This is an implementation accident or incomplete work, not a defensible settled design. For Kivi, whose Why panel promises retrieved/withheld/used distinctions (`kivi-semantic-memory-position.md:223-230`), this pushes toward treating the budget and drop trace as an unresolved correctness question.

### Exposure, failure, and change over time

**Question:** Expose only answer text or also evidence and decision traces?

**Repo answer:** search returns hits, injected sections/Markdown, source IDs, drop reasons, latency tiers, status, and a recall-event audit row (`Memory/src/service/memory-service.ts:1091-1114`, `Memory/src/storage/schema.ts:403-427`). This is hardcoded contract. It assumes developers/callers can interpret the trace. Kivi wants the same evidence legible to normal users (`kivi-semantic-memory-position.md:217-230`), so the data precedent holds but presentation precedent does not.

**Question:** Fail synchronously, retry durably, or degrade?

**Repo answer:** semantic post-processing is asynchronous and durable. Jobs move through queued/leased/succeeded/failed/dead-letter; embedding has a separate retry queue and processing can become `ready_text_only` (`Memory/src/types.ts:42-84`, `Memory/src/storage/schema.ts:501-577`). Error classification maps configuration/corruption/input errors to settings/no-retry and network/rate/5xx failures to retry (`Memory/src/service/worker/job-handlers.ts:520-553`). This is hardcoded state machinery with configurable model retries. It assumes raw capture must survive model outages and eventual enrichment is acceptable. Kivi’s latency targets are explicitly undecided (`kivi-semantic-memory-position.md:267-274`), so applicability is unclear.

**Question:** Do memories decay, archive, or remain until deleted?

**Repo answer:** L2 candidates have TTL, values decay with a configurable half-life, policies/skills archive below gain/eta thresholds, and L3 fields may archive/reactivate (`Memory/src/config/index.ts:374-451`; `Memory/tests/service/evolution/l3-world-model.test.ts:285-323`). UserMemory does not automatically decay (`Memory/src/types.ts:355-377`). This is mixed configurable/hardcoded behavior. Kivi explicitly requires observations to decay and hypotheses to expire, while stated memories persist until corrected (`kivi-semantic-memory-position.md:232-251`); Memmy’s decay axis is utility/layer rather than epistemic tier.

**Question:** What ordering is assumed?

**Repo answer:** turn and evidence ordering use timestamps plus stable IDs; L3 uses immutable scope sequence numbers and unique `(scope_key, scope_seq)` jobs (`Memory/src/storage/schema.ts:501-531`); same-session routing proposals are computed at start and committed at completion with stale-proposal handling (`Memory/src/service/session/session-turn-service.ts:2793-2961`). This is hardcoded. It assumes per-scope total ordering can be serialized through SQLite/jobs. Kivi’s multi-surface dictation/Hey Kivi environment may create concurrent evidence, raising a stronger causal-order question than this repo faced.

## 2. Magic numbers

Unless noted, blame traces the original defaults to the initial Memory commit `e1b5717f`; no comment, issue, or benchmark rationale was found. That makes them look guessed or inherited, not tuned. “÷10/×10” describes the likely qualitative break, not a recommendation.

### Model, embedding, and service limits

| Value | Meaning and source | Provenance | ÷10 | ×10 | Read |
|---|---|---|---|---|---|
| 1,000 | account evolution thinking budget (`Memory/src/config/index.ts:279`) | initial commit; no rationale | weaker structured reasoning | higher latency/cost | guessed |
| 512 | summary max tokens (`Memory/src/config/index.ts:281`, `:305`) | added in reliability commit `419cc1a2` | truncation/invalid summaries | verbosity/cost | tuned-looking, rationale unclear |
| 180 s | summary timeout (`Memory/src/config/index.ts:306`) | changed in `0edd5b4d` model-index hardening | more timeout failures | long stalls | reactive tuning |
| 3 / 1 | summary retries / malformed retries (`Memory/src/config/index.ts:307-308`) | initial | brittle | repeated cost/latency | guessed |
| 4,096 / 180 s / 2 / 1 | evolution output, timeout, retries, malformed retries (`Memory/src/config/index.ts:318-321`) | 4,096 added in `419cc1a2`; others initial | clipped transformations | excessive latency/cost | mixed |
| 32 / 60 s / 2 | embedding batch, timeout, retries (`Memory/src/config/index.ts:329-331`) | initial | throughput collapse | memory/provider pressure | guessed |
| 5 s / 250 ms | worker startup fallback/post-health delay (`Memory/src/server/http.ts:128-135`) | no explanatory comment | races/startup churn | visibly stale processing | guessed |
| 3,000 ms | query-vector timeout (`Memory/src/service/retrieval/retrieval-service.ts:98`) | `3563a0e5`; no rationale | vector lane often absent | turn-start stalls | guessed |

### Capture and reflection budgets

All are configurable at `Memory/src/config/index.ts:344-372` and normalized at `Memory/src/config/index.ts:1038-1066`.

| Values | Question frozen by the values | ÷10 | ×10 | Read |
|---|---|---|---|---|
| 4,000 text / 2,000 tool chars | How much raw step context is enough? | loses decisive detail | prompt/storage inflation | guessed |
| threshold 12 steps | When is an episode “large”? | batching common, context fragmented | oversized single-pass prompts | guessed |
| 3 downstream steps | How far can future outcome explain an action? | weak credit assignment | contamination by later tasks | guessed |
| 800 task / 1,200 downstream / 400 per-step / 600 outcome chars | How much causal context reaches reflection? | shallow/incomplete | cost and distractors | guessed |
| windows 6 overlap 1; degraded 3 overlap 1 | How much local continuity does batch reflection need? | context loss | cost/duplicate judgments | guessed |
| retries 1 primary / 2 degraded | How much model instability is tolerated? | transient loss | repeated latency/cost | guessed |
| 600 state / 300 thinking / 600 action / 120 tool input / 160 output / 160 error / 240 outcome / 300 reflection chars | Which evidence classes deserve prompt space? | key evidence clipped | large prompts/noise | guessed |
| 20,000 imported tool chars | Wire-size protection (`Memory/src/service/import/memory-import-pipeline.ts:21-24`) | severe import loss | request/memory bloat | guessed |

### Reward, feedback, lifecycle

All are configurable at `Memory/src/config/index.ts:374-451`.

| Values | Encoded decision | ÷10 | ×10 | Read |
|---|---|---|---|---|
| gamma .9, lambda .5, delta .1, softmax tau .5 | reward smoothing/credit mixture | unstable or near-zero carryover | invalid ranges or frozen history | guessed |
| 30-day half-life | how fast usefulness ages | rapid forgetting | stale utility dominates | guessed |
| implicit threshold .2; feedback window 30 s | when behavior counts as feedback | noisy signals | missed feedback | guessed |
| 2,000 summary chars; concurrency 2 | grading context/parallel cost | weak evidence/slow throughput | prompt cost/provider pressure | guessed |
| min exchanges 1; content 40; tool-heavy .7; assistant chars 80 | when an episode is gradable | trivial noise accepted | short valid work excluded | guessed |
| failure threshold 3 in window 5; cooldown 60 s | when repeated failure triggers repair | single glitches overfit | persistent failures ignored | guessed |
| value delta .5; low value .01 | update magnitude/archive boundary | imperceptible updates | violent oscillation | guessed |
| feedback trace 500 chars; evidence 4 | repair evidence breadth | loses cause | prompt dilution | guessed |
| failure score -.15; implicit confidence cap .65 | negative-experience admission/assertiveness | over-admit / weak cap | nearly nothing admitted / invalid confidence | guessed |
| anti-patterns 3, preferences 3, source IDs 20 | negative packet breadth | under-informs | noisy prompt | guessed |
| L2 activation 3 episodes | evidence needed to become active (`Memory/src/config/index.ts:412`) | near-single-shot promotion | slow learning | changed later in `7fca0df7`; tuned-looking |
| L2 similarity .65, trace value .005, gain .02, archive -.05 | association/promotion/retirement | broad false merges | almost no matches/invalid scales | guessed |
| L2 TTL 30 days, trace 3,000 chars, EMA .4 | candidate patience/evidence/update speed | churn/weak evidence/volatile score | stale candidates/high cost/frozen score | guessed |
| L3 policies 1, support 1, similarity .3, evidence 1 | minimum abstraction evidence | effectively unchanged at minimum | little abstraction | guessed, permissive |
| L3 policy 800 / trace 500 chars; cooldown 0 days | abstraction prompt and cadence | thin profiles | cost; or ten-day staleness | guessed |
| L3 confidence delta .05, retrieval min .2 | confidence motion/visibility | noisy micro-updates/over-recall | frozen confidence/under-recall | guessed |
| skill eta .1, support 1, gain .02, trials 1, cooldown 0 | crystallization/retrieval evidence | almost immediate promotion | slow/no learning | guessed, permissive |
| skill evidence 6, trace 500 chars, eta delta .1, archive eta .1, repair min .5 | skill evidence and lifecycle | weak/noisy | costly/rare | guessed |
| success .5, failure -.15, max failure ratio .4 | trial outcome boundaries | false outcomes | few outcomes/invalid ratio | guessed |

### Retrieval and presentation

All config defaults are at `Memory/src/config/index.ts:457-485`.

| Values | Encoded decision | ÷10 | ×10 | Read |
|---|---|---|---|---|
| top-k L1/L2/L3 = 3/5/2 | per-layer prompt share | layers disappear | prompt overload | guessed |
| pool factor 4 | reranking headroom | little diversity | excess DB/vector work | guessed |
| cosine .6 / priority .4 | present relevance vs past value | priority dominates | invalid unnormalized mix | guessed |
| MMR lambda .7 | relevance vs diversity (`Memory/src/service/retrieval/retrieval-service.ts:370-394`) | novelty dominates | redundancy dominates | guessed |
| RRF 60 | rank fusion smoothing | top ranks dominate | ranks flatten | likely conventional inherited default; no repo rationale |
| relative floor .2; trace sim .25; goal sim .45 | admission similarity | noise | empty recall | guessed |
| min recall .12 | global relevance floor (`Memory/src/config/index.ts:467`) | over-recall | near-empty recall | explicitly lowered in commit `f39b00bc`; tuned reactively |
| keyword top-k 20 | lexical candidate breadth | misses synonyms/exact facts | DB/rerank cost | guessed |
| skill blend .15; smart seed .7 | skill utility and seeding balance | semantic score dominates / sparse seeds | eta dominates / little exploration | guessed |
| skill summary 200; filter candidate 500 chars | reranker/injection evidence | ambiguity | cost/noise | guessed |
| filter keep 8, fallback 6, min candidates 2 | LLM filtering economics | starves recall | crowded prompt; more calls | guessed |
| 60 s extract, 30 s filter/rewrite, rewrite count 3, retries 1, rewrite RRF 8, per-query keep 3 | query-expansion latency and breadth (`Memory/src/service/retrieval/retrieval-service.ts:90-104`) | frequent fallback/narrow recall | turn latency/excess duplicates | guessed |
| temporal cap 20 | maximum time-filtered history (`Memory/src/service/retrieval/retrieval-service.ts:106`) | false absence | prompt bloat | guessed |
| snippet 640, skill 200, recent exclusion 8 | injection detail and same-session suppression (`Memory/src/service/retrieval/retrieval-service.ts:530-533`) | loses evidence / duplicate reminders | prompt bloat / delayed useful recall | 8 added later in `89b777af`; others initial |
| token estimate = chars/4 | model-agnostic budget approximation (`Memory/src/service/retrieval/retrieval-service.ts:517`) | understates budgets if divided | overstates if multiplied | inherited heuristic |
| lane over-recall = 1.5× | diversity headroom (`Memory/src/service/retrieval/retrieval-service.ts:409-411`) | no rerank choice | excess work | guessed |
| episode merge gap 2 h | follow-up continuity (`Memory/src/config/index.ts:453-455`) | fragments work | merges unrelated work | guessed |
| feedback classifier confidence .6 | implicit feedback admission (`Memory/src/service/session/session-turn-service.ts:3014-3038`) | noisy corrections | feedback ignored | hardcoded/guessed |
| log retention 10,000 | operational history (`Memory/src/storage/repositories.ts:92-93`) | weak audit/debug history | storage growth | guessed |
| L3 source cap 256 | maximum retained evidence IDs (`Memory/tests/service/evolution/l3-world-model.test.ts:324-456`) | provenance loss | large rows/responses | tuned-looking, rationale unclear |

The most important non-number is that the caller’s numeric `contextBudget` currently has no effect (`Memory/src/service/retrieval/retrieval-service.ts:544-599`). Any apparent tuning of that value is illusory.

## 3. What the history says

### Reversals and rewrites

**Highest-value reversal:** oversized agent turns were once split at blank lines; this produced hundreds of near-empty fragments and 19,413 memories from 1,000 selected turns. Commit [`0da2e36d`](https://github.com/MemTensor/memmy-agent/commit/0da2e36d1f180104a1d6ca4c08915a2a58aeeffc) explicitly restored “one turn == one memory,” clipped oversize UTF-8 payloads, and preserved legacy idempotency keys. The current test protects stable legacy keys (`Memory/tests/agent-source-runtime.test.ts:25-43`). This is the clearest evidence that chunking by textual layout was not merely suboptimal; it failed operationally.

Turn persistence itself moved from start/incremental behavior to completion in [`023c40b1`](https://github.com/MemTensor/memmy-agent/commit/023c40b1775c385ce08cc096a1535edcdad07c0b), then episode routing was rewritten so proposals are made at turn start but committed at completion in [`66429665`](https://github.com/MemTensor/memmy-agent/commit/664296656cb89beeb20abeee9c78da264b72b5ff). Current tests encode the resulting boundary (`Memory/tests/service/session/turn-capture.test.ts:44-299`). This signals recurring ambiguity around when a turn becomes durable and how interrupted/concurrent turns behave.

UserMemory and L1 admission were later decoupled in [`d2136643`](https://github.com/MemTensor/memmy-agent/commit/d213664345acd34d4473028f9c13e5efd2391f2b). The test matrix now insists that either branch can accept while the other rejects (`Memory/tests/service/user-memory/user-memory.test.ts:233-481`). That later abstraction implies the original single admission answer stopped working.

L3 was substantially rewritten into a project-scoped, protocol-versioned world model in [`1d7b8cd4`](https://github.com/MemTensor/memmy-agent/commit/1d7b8cd42a4169f5de5b6e841b495f1d2151172a), then changed to refresh before each turn in [`fcc5b8eb`](https://github.com/MemTensor/memmy-agent/commit/fcc5b8eb3090c861ba0af1e339eab7b9e7a1c626), and changed again to omit reasoning evidence in [`affab319`](https://github.com/MemTensor/memmy-agent/commit/affab3195d0b97844f690eb1d9a36b5a64241745). Current ownership and evidence constraints live at `Memory/src/storage/schema.ts:65-80`, `Memory/src/storage/schema.ts:225-238`, and `Memory/tests/service/evolution/l3-world-model.test.ts:168-244`. These are high-value reversals: scope, freshness, and admissible evidence were all unstable.

Retrieval layers became caller-configurable only later in [`b6a62159`](https://github.com/MemTensor/memmy-agent/commit/b6a62159dd530289ff93c716ce4805f6481b510a), while minimum recall was reactively lowered to 0.12 in [`f39b00bc`](https://github.com/MemTensor/memmy-agent/commit/f39b00bc585209cfa9d93c5cbff7c04a414ba3e2). This is evidence that the original global retrieval answer caused missed recall; the commit message states the change, but not a benchmark or issue rationale.

Live correction and grounding required a later cross-cutting fix in [`88fa2a93`](https://github.com/MemTensor/memmy-agent/commit/88fa2a937f8ba059ef08d5ad4bc25706a20c4629). Current explicit replacement behavior is at `Memory/src/service/session/session-turn-service.ts:2590-2631`. This implies correction was not initially a first-class lifecycle.

Legacy raw-turn duplication required a dedicated migration repair in [`17f929bc`](https://github.com/MemTensor/memmy-agent/commit/17f929bc62d979541f5cbea226da9a13cd142521); later scanner boundary fixes in [`32545a03`](https://github.com/MemTensor/memmy-agent/commit/32545a034de9bfd1abbbed89594ac1f413fe3d9d) and [`0da2e36d`](https://github.com/MemTensor/memmy-agent/commit/0da2e36d1f180104a1d6ca4c08915a2a58aeeffc) show ingestion identity/boundaries were a recurring bug family. Current capture claims freeze the cross-path dedup answer (`Memory/src/storage/schema.ts:472-480`).

### Recurring bug themes

- Processing recovery and diagnostic fidelity recur in commits [`56b6fec8`](https://github.com/MemTensor/memmy-agent/commit/56b6fec8c3e787a60220f300877d16ffd9049a0d) and [`419cc1a2`](https://github.com/MemTensor/memmy-agent/commit/419cc1a23b1c68762ef2efa919ef3073f9708e66). The explicit processing/retry model now occupies `Memory/src/storage/schema.ts:501-577`.
- Source-boundary and duplicate problems recur across `17f929bc`, `32545a03`, `0da2e36d`, and `c9b58487`; current tests distinguish hook-vs-scan ownership and changed assistant answers (`Memory/tests/service/import/memory-capture-dedup.test.ts:16-139`).
- Retrieval precision/recall recurs in `8d35e70a` (negative-memory precision), `06b1e066` (filtering/skill timing), `f39b00bc` (lower threshold), `b394e9e8` (short-term JSON noise), and `88fa2a93` (grounding/corrections). Current ranking has many configurable knobs (`Memory/src/config/index.ts:457-485`), which itself is evidence of unsettled confidence.

The public GitHub issue list is sparse and mostly packaging as of the baseline; for example, the open issues concern missing native runtime libraries/model-cache paths rather than semantic behavior ([repository issues](https://github.com/MemTensor/memmy-agent/issues)). Therefore “recurring” above is inferred from repeated fix commits and regression tests, not from multiple closed public issue reports. Where no issue/PR body exposed a reason, intent is **unclear**.

### TODOs, shortcuts, compatibility seams

No substantive `TODO` or `FIXME` was found in the core semantic paths. The more revealing admissions are executable:

- `void budget` leaves context budgeting incomplete (`Memory/src/service/retrieval/retrieval-service.ts:588-599`).
- `followUpMode` is typed as a choice but normalized to one answer (`Memory/src/config/index.ts:226-229`, `Memory/src/config/index.ts:1174-1176`).
- Legacy target fallback remains in policy induction (`Memory/src/service/evolution/policy-induction.ts:446-450`).
- Cursor encoding is externally owned specifically to retain sync compatibility (`Memory/src/service/read-model/skill.ts:130`).
- Database migration recognizes versions 2–7 and refuses unknown/newer schemas rather than guessing (`Memory/src/storage/schema.ts:616-630`).
- L3 legacy jobs are dead-lettered and old v7 abstractions archived during migration (`Memory/src/storage/schema.ts:725-747` in the current file; intent is explicit in the update values).

These are backwards-compatibility or incomplete-work constraints, not evidence that the underlying semantic choice is preferred.

## 4. Unexamined defaults

**Exact-text normalization defines equality.** NFKC + lowercase + deletion of all punctuation, symbols, and whitespace determines UserMemory equality (`Memory/src/service/user-memory/user-memory.ts:40-49`). No comment considers locale-specific case, numbers with punctuation, or meaning-bearing symbols. An untried alternative is structured canonicalization plus semantic/entity keys.

**Visibility defaults private but is an open string.** SQLite defaults `private`, while the type allows arbitrary strings (`Memory/src/storage/schema.ts:33-43`, `Memory/src/types.ts:137-154`). No test here establishes access semantics for unknown visibility values. An untried alternative is a closed enum enforced in storage.

**FTS tokenization is SQLite `unicode61`.** Both FTS tables inherit this tokenizer (`Memory/src/storage/schema.ts:108-121`). No deliberation appears for CJK word segmentation, stemming, or domain tokenization. Alternatives include trigram, language-specific segmentation, or provider-side lexical indexes.

**Token estimation is characters divided by four.** This is model/language agnostic (`Memory/src/service/retrieval/retrieval-service.ts:517`). No test distinguishes English from CJK budget accuracy. An alternative is provider tokenizer accounting—though the current budget is ignored anyway (`Memory/src/service/retrieval/retrieval-service.ts:588-599`).

**Local embeddings default to MiniLM and are not normalized.** `Xenova/all-MiniLM-L6-v2`, cache on, normalize off (`Memory/src/config/index.ts:323-334`). No code comment compares models or normalization choices. Alternatives include a multilingual model, normalized cosine-ready vectors, or no default embedding until selected.

**Temperature zero everywhere.** Summary and evolution default to deterministic sampling (`Memory/src/config/index.ts:297-321`). No test evaluates whether diversity improves hypothesis/policy discovery. An alternative is task-specific temperature rather than a global zero.

**Local server means anonymous access.** With no storage token, the server enables anonymous requests, relying on loopback binding (`Memory/src/server/index.ts:95-111`). No semantic test considers hostile local processes. An alternative is mandatory per-install token even on loopback.

**Same-turn merge takes maximum score and prefers L1 as representative.** (`Memory/src/service/retrieval/retrieval-service.ts:338-357`). No test distinguishes max from mean/independent display for contradictory lane content. An alternative is keep both claims visible with shared provenance.

**UserMemory items do not decay.** Their lifecycle has only active/archived/deleted and no expiry (`Memory/src/types.ts:355-377`). No default alternative is encoded for temporal facts. Kivi explicitly raises observed/hypothesis expiration (`kivi-semantic-memory-position.md:232-251`).

**A new current state is additive unless explicitly targeted as correction.** (`Memory/tests/service/user-memory/user-memory.test.ts:997-1072`). The untried alternative is contradiction detection with supersession or uncertainty sets.

**Framework defaults leak into semantics.** SQLite transaction/order semantics, FTS BM25 ranking, JSON string persistence, HTTP 200 success envelopes, and Node timers are used without comparison (`Memory/src/storage/schema.ts:18-23`, `Memory/src/server/http.ts:214-252`). Alternative storage/transport semantics were implemented only at backend level, not evaluated for behavioral equivalence.

## 5. Questions this repo never faced

These follow from Kivi’s stated constraints, not from hidden intent.

1. **How is the speaker/subject of every candidate established before persistence?** Memmy scopes by user/source/session but does not encode “this fact is about a third party and may be read but never kept” (`Memory/src/types.ts:86-105`, versus `kivi-semantic-memory-position.md:106-127`).
2. **Can excluded content be proven absent while still showing a count/reason?** Memmy logs retrieval drops, not extraction candidates dropped for privacy (`Memory/src/storage/schema.ts:403-424`; Kivi requirement at `kivi-semantic-memory-position.md:120-127`).
3. **How can a tier be enforced so a hypothesis cannot accidentally be consumed as a fact?** Memmy lifecycle/status is not epistemic tier (`Memory/src/types.ts:30-50`; Kivi at `kivi-semantic-memory-position.md:66-103`).
4. **How is explicit confirmation represented as an event, and can silence ever promote?** Memmy has feedback and corrections but no general stated/observed/hypothesised promotion protocol (`Memory/src/storage/schema.ts:238-267`; Kivi at `kivi-semantic-memory-position.md:96-103`, `:217-230`).
5. **How are confirmation prompts budgeted per user/week and selected by value?** No corresponding config/state exists in `Memory/src/config/index.ts:113-259`; Kivi requires a capped prompt budget (`kivi-semantic-memory-position.md:217-222`).
6. **How does “That’s not me anymore” suppress re-derivation from old transcripts?** Memmy supports archive/delete/supersession, but no extraction suppression record is present in the schema (`Memory/src/storage/schema.ts:82-107`; Kivi at `kivi-semantic-memory-position.md:238-245`).
7. **Can dictation be structurally denied access to observation/hypothesis stores?** Memmy supports caller-selected layers, but not distinct epistemic stores/permissions (`Memory/src/types.ts:327-334`, `Memory/src/types.ts:418-428`; Kivi at `kivi-semantic-memory-position.md:181-199`).
8. **How is disclosure permission applied after retrieval while leaving an auditable withheld trace?** Memmy filters/ranks before injection and records drops, but has no Anbu/Koottu/Daari permission model (`Memory/src/service/retrieval/retrieval-service.ts:1907-1925`; Kivi at `kivi-semantic-memory-position.md:129-178`).
9. **What does a trustworthy absence answer require?** A top-k search cannot by itself establish absence; Kivi promises to say what was searched and distinguish absent, insufficient, and irreconcilable evidence (`kivi-semantic-memory-position.md:203-230`). Memmy’s recall audit stores candidates/hits but not coverage guarantees (`Memory/src/storage/schema.ts:403-424`).
10. **How do evidence count and confidence interact without self-promotion?** Memmy uses support/gain/confidence to activate policies (`Memory/src/config/index.ts:409-433`), while Kivi says twenty observations still do not become stated (`kivi-semantic-memory-position.md:91-103`).
11. **What is the retention policy for original transcripts after derived memories exist?** Memmy retains raw turns unless redacted/deleted (`Memory/src/storage/schema.ts:201-238`); Kivi’s provenance promise and third-party deletion rule create tension (`kivi-semantic-memory-position.md:106-127`, `:232-251`).
12. **How are shared entities distinguished from claims about those entities?** Memmy stores prose/tags rather than a first-class entity/relation graph (`Memory/src/types.ts:129-162`); Kivi names entities/relations as a primary type (`kivi-semantic-memory-position.md:72-78`).
13. **Does “Forget” remove derived consequences and cached outputs, or only the selected row?** Memmy recomputes some dependent policy/L3/skill state after L1 deletion (`Memory/tests/service/lifecycle/memory-lifecycle.test.ts:135-238`), but Kivi’s suppression rule also governs future re-extraction (`kivi-semantic-memory-position.md:238-245`).
14. **How is per-request Daari invitation recognized without inferring broad permission from tone?** Memmy has no equivalent permission escalation (`Memory/src/types.ts:34-41`; Kivi at `kivi-semantic-memory-position.md:161-178`).

## 6. What the tests do not cover

These are decisions for which a materially different implementation could still satisfy the reviewed suite.

- **Actual context-budget enforcement.** Tests assert injected packet shape and ranked/drop behavior, but the implementation ignores the supplied budget (`Memory/src/service/retrieval/retrieval-service.ts:544-628`; relevant test list at `Memory/tests/service/retrieval/injected-context.test.ts:221-861`). A correct cap, no cap, or several allocation policies could pass tests that do not assert total tokens against the request.
- **Why the numeric defaults are correct.** Config tests assert that defaults load (`Memory/tests/config.test.ts:54-92`, `:245-260`); they do not compare task quality across threshold/top-k/temperature values. These tests preserve compatibility, not evidence.
- **Third-party privacy at the write boundary.** Capture tests cover empty/chitchat/sanitized protocol data (`Memory/tests/service/session/turn-capture.test.ts:655-887`) but do not distinguish user facts from private facts about another person. Memmy offers no precedent on Kivi’s central exclusion rule.
- **Epistemic tiers and permissioned disclosure.** No type encodes Kivi’s tier or Anbu/Koottu/Daari mode (`Memory/src/types.ts:30-50`). Therefore every retrieval test could pass while observations are silently asserted as facts.
- **Semantic contradiction detection.** Tests require explicit targeted correction and deliberately allow two current states (`Memory/tests/service/user-memory/user-memory.test.ts:954-1072`). Any automatic contradiction policy is outside the evidence base.
- **Suppression after delete/demotion.** Lifecycle tests ensure dependency recomputation and old L3 work cannot recreate a deleted scope (`Memory/tests/service/lifecycle/memory-lifecycle.test.ts:135-238`, `:571-633`), but not that old transcripts cannot re-extract a rejected personal belief.
- **Multilingual equality and retrieval quality.** Regexes contain Chinese/English patterns and FTS uses `unicode61` (`Memory/src/service/user-memory/user-memory.ts:4-20`, `Memory/src/storage/schema.ts:108-121`), but reviewed tests do not establish equivalent recall, contradiction, or token-budget behavior across languages.
- **Embedding-model swaps.** Schema stores model/provider/dimension and rejects incompatible dimensions (`Memory/src/storage/schema.ts:123-132`, `Memory/src/storage/sqlite-vec-store.ts:167-182`), but no test shows semantic ranking remains comparable during partial re-embedding or between models.
- **Concurrent completion for the same session/turn.** Idempotency conflicts are tested structurally, and SQLite uniqueness prevents some duplicates (`Memory/src/storage/schema.ts:464-480`), but the reviewed tests do not establish behavior under genuinely parallel processes between read/check/write. The design is precedent, not concurrency evidence.
- **Abstention truthfulness.** Retrieval tests show candidates may all be dropped (`Memory/tests/service/retrieval/query-and-filter.test.ts:715-780`), but no end-to-end test verifies the caller tells the user what was searched or refrains from filling the gap. Kivi’s promise remains unevaluated (`kivi-semantic-memory-position.md:203-230`).
- **Provenance completeness after truncation.** Tests preserve IDs and cap lists (`Memory/tests/service/evolution/l3-world-model.test.ts:324-456`), but do not prove the retained excerpt still supports the generated claim after capture/snippet truncation (`Memory/src/config/index.ts:345-372`, `Memory/src/service/retrieval/retrieval-service.ts:530-533`).
- **Utility decay versus identity change.** Tests exercise policy/skill lifecycle, not whether a stale personal observation stops being surfaced on the right human timescale (`Memory/src/config/index.ts:374-451`).
- **Fresh-session behavioral restraint.** Injection tests verify packet contents, not whether the consuming agent treats cross-session memory only as background. That reader-side choice is outside `MemoryService`; a different agent response policy would leave the suite green (`Memory/src/types.ts:224-236`).

## Sources and limits

Primary evidence is the checked-out repository at commit `62ec3d92`, with line citations throughout, plus its Git history and linked GitHub commits. Public issues/PR search was checked, but issue visibility was not rich enough to attribute most semantic changes to a stated issue rationale. Where commit messages and tests showed behavior but not motivation, this report says “unclear” or labels the interpretation as inference.

The scope of “every magic number” is the core semantic-memory execution path: config, capture, retrieval, lifecycle, model calls, worker behavior, and persistence. UI dimensions, CSS constants, installer retry loops, packaging sizes, and release automation numbers were excluded because they do not constrain Kivi’s semantic-memory decision space.
