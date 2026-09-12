# Decision-Space Audit: claude-mem as Precedent for Kivi

This report extracts questions, not recommendations. “Kivi fit” means comparison with `kivi-semantic-memory-position.md`; it is not a proposed answer. Local citations use repository-relative `file:line`. Historical issue links are primary GitHub records. Intent is marked **inferred** wherever code shows behavior but not rationale.

## Scope and read boundary

Read closely: `kivi-semantic-memory-position.md`; architecture and search documents; settings defaults; hook/CLI handlers; SDK prompt/parser; worker session, response, SQLite, Chroma, context, and search paths; core schemas; both server storage schemas; representative tests in every core cluster; relevant git history and linked GitHub issues. Inventoried but did not read assertion-by-assertion: the entire test tree. Skipped unless needed to verify shipped parity: generated/minified bundles, translated docs, image/font assets, UI styling, marketing copy, release notification scripts, and unrelated installer animation. “Every” config and magic-number claim below is therefore every decision-bearing value in the inspected memory runtime, not CSS dimensions, test fixtures, build constants, or telemetry presentation caps.

## Orientation

The mature local core is the worker, `SessionStore`, observer protocol, context compiler, and search subsystem (`docs/architecture-overview.md:17-28`). CLI handlers, HTTP routes, adapters, installers, UI, Docker, and platform-specific packages are delivery surfaces. A newer, separate server core lives in `src/server`, `src/storage`, and `src/core/schemas`; its compatibility boundary is explicit in the retained `server_beta_*` DDL names (`src/storage/postgres/schema.ts:6-10`).

The local data model has sessions, observations, summaries, prompts, pending messages, feedback, tool uses, and sync state (`docs/architecture-overview.md:114-138`). Observations serialize facts/concepts/file lists as JSON text and use FTS5 plus Chroma documents; the response processor performs JSON serialization at `src/services/worker/agents/ResponseProcessor.ts:655-711`. The server model instead normalizes events, jobs, observations, and provenance links (`src/storage/postgres/schema.ts:149-266`).

The main local write path is hook → CLI handler → worker HTTP route → durable pending queue → observer provider → XML parser → transactionally stored observation/summary → Chroma sync → SSE (`docs/architecture-overview.md:44-63`). Context/search returns through SQLite filter paths or Chroma-to-SQLite hydration and context compilation. The server path is event ingest → idempotent event row → generation job → observation plus source row (`src/storage/postgres/schema.ts:169-266`).

The canonical settings surface is `SettingsDefaults` (`src/shared/SettingsDefaultsManager.ts:22-148`) and its defaults (`:151-272`). Tests cover schema repair, queues, parsing, providers, search strategies, context, privacy validation, sync, server routes/storage/auth, adapters/hooks, process management, and UI utilities. They are much stronger on mechanical integrity than on semantic truth, disclosure, human correction, or longitudinal belief change.

# 1. Decision inventory

| Question with defensible alternatives | Repository answer and placement | Assumptions | Kivi difference/push |
|---|---|---|---|
| What events enter memory: all conversation, user statements, or only selected lifecycle events? | Prompts and tool uses enter through hooks; configured tool classes are skipped (`src/shared/SettingsDefaultsManager.ts:157`, `docs/architecture-overview.md:31-40`). Configurable exclusions imply moderate confidence. | Coding work is revealed by tool use; skipped coordination tools are low-value noise. | Kivi ingests dictation, application context, and requests, so the input boundary must distinguish speaker/subject and retention permission; claude-mem does not face that identity problem (`kivi-semantic-memory-position.md:1-8`, `:20-29`). |
| Is memory raw history or model-authored compression? | Model-authored observations and summaries are the primary semantic units (`src/sdk/prompts.ts:24-58`, `:187-223`). Hardcoded protocol, configurable model. | Compression errors cost less than repeated raw context; coding artifacts make claims comparatively verifiable. | Kivi requires source-attributable beliefs and rejects unverifiable characterization, pushing toward evidence links and explicit epistemic state rather than free-standing summaries (`kivi-semantic-memory-position.md:31-55`). |
| What is the observation schema? | Type, title, subtitle, facts, narrative/text, concepts, files, tokens, agent identity and timestamps; parser shape at `src/sdk/parser.ts:19-38`, storage serialization at `src/services/worker/agents/ResponseProcessor.ts:655-711`. Mode makes taxonomy pluggable, fields are hardcoded. | One denormalized document is convenient for rendering, FTS, and embeddings. | Kivi needs separate stated facts, observations, and hypotheses with provenance and lifecycle; one generic observation row pushes against structural disclosure separation. |
| How deterministic must model output be? | Text XML parsed by regex; non-XML is discarded (`src/sdk/parser.ts:66-84`, `src/sdk/prompts.ts:187-223`). A TODO calls it a bridge to tool-use JSON (`src/sdk/parser.ts:5`). Incomplete work, not settled design. | Provider portability mattered more than schema-enforced output; discarded generations are tolerable. | Kivi’s exclusion/provenance guarantees raise failure cost, pushing toward validated structured candidates and auditable rejection records. |
| What is discarded before storage? | Empty observations, skipped summaries, configured tool events, private-tagged content, invalid/non-XML batches, and (in some paths) empty titles (`src/sdk/parser.ts:137-145`, `src/services/worker/agents/ResponseProcessor.ts:376-424`). | Noise omission is more valuable than recall; model skip decisions are acceptable. | Kivi demands a hard sensitive-category and third-party barrier with logged reasons, which this generic skip machinery does not establish (`kivi-semantic-memory-position.md:56-75`). |
| Where is privacy enforced? | A validation component exists and private tags are stripped, but semantic sensitivity is largely prompt/mode driven (`src/services/worker/validation/PrivacyCheckValidator.ts:1`; `src/utils/tag-stripping.ts:1`). **Inference:** no schema-level sensitive-category barrier appears in the inspected write path. | Project/code memory is not principally about a person; explicit tags are adequate user intent. | Kivi’s non-retention of others and sensitive-topic exclusions push to a pre-storage, candidate-level policy decision with proof of drops. |
| What is authoritative storage? | SQLite is structured source of truth; Chroma is a derived semantic index (`docs/architecture-overview.md:114-138`). Chroma can be disabled (`src/shared/SettingsDefaultsManager.ts:206-215`). Configurability shows low confidence in vector availability, high confidence in SQLite. | Single-user local scale; rebuildable embeddings; keyword degradation is acceptable. | Kivi needs provenance and suppression to remain authoritative across reprocessing; derived retrieval indexes fit, but must not become an unobservable second truth. |
| How are facts serialized? | Arrays are JSON strings in SQLite and JSON/JSONB in newer server/sync formats (`src/services/worker/agents/ResponseProcessor.ts:710-711`; `src/storage/postgres/schema.ts:94-125`). | Schemaless evolution and easy transport outweigh relational querying. | Kivi’s entity conflict, evidence count, source attribution, and tier transitions push toward normalized relations or strongly validated documents. |
| What constitutes a duplicate? | Local exact dedupe uses `(memory_session_id, content_hash)` and `ON CONFLICT DO NOTHING` (`src/services/sqlite/SessionStore.ts:2686-2766`); the older documented rule hashes title+narrative with a 30-second window (`docs/architecture-overview.md:100-105`). Server events/jobs use scoped idempotency keys (`src/storage/postgres/schema.ts:176-199`, `:284-302`). | Retries duplicate exact content; semantic near-duplicates are a separate optional concern. | Kivi must decide whether repeated evidence strengthens a belief rather than disappears. Exact dedupe pushes toward retry safety; semantic merging risks erasing evidence count. |
| What happens on contradiction? | No general contradiction or supersession relation exists in the local observation schema; multiple observations coexist. **Inference** from table model and search behavior. | Work history is additive; later chronology is sufficient context. | Kivi explicitly requires supersession with retained history, so this precedent supplies no answer (`kivi-semantic-memory-position.md:203-211`). |
| What happens when a user rejects memory? | Reversible dismiss was added later; current history names a hide-from-surfacing abstraction (`git log`, commits `82945b9a`, `9aac37ba`). Deletion is also exposed in viewer history (`36c7e7ac`). Exact current semantics require deeper UI/repository tracing: **unclear**. | Hiding retrieval is adequate correction for coding observations. | Kivi requires demote-plus-suppress so the same belief cannot regrow, pushing beyond row deletion/hiding (`kivi-semantic-memory-position.md:207-211`). |
| Is ingestion ordered? | Pending rows are claimed per session and parser success clears a batch; pending survives generator restarts (`docs/architecture-overview.md:67-89`). Server batch writes were later serialized (commit `e78e62a5`). | Per-session order matters; cross-session global order does not. | Kivi’s multi-source evidence and contradictions raise the question of event-time versus ingest-time order; repo chronology mainly uses created timestamps. |
| Is processing idempotent? | Enqueue IDs, content hashes, event idempotency keys, scoped job keys, sync origin/revision ledgers, and unique provenance links make replay mostly idempotent (`src/storage/postgres/schema.ts:176-199`, `:240-250`; `src/services/sqlite/SessionStore.ts:547-548`). | At-least-once delivery is expected; exact replay identity is available. | Kivi can reuse the question, but correction/suppression operations need semantic idempotency not shown here. |
| What happens on storage conflict? | Exact conflict returns the existing observation ID; migrations repair duplicates before adding unique indexes (`src/services/sqlite/SessionStore.ts:1875-1917`, `:2722-2766`). | Keeping either identical row is harmless. | For Kivi, identical text from distinct sources is not identical evidence; collapsing may lose provenance. |
| What is retrieved? | Search spans observations, prompts, and summaries; semantic candidates come from Chroma and are hydrated from SQLite, with FTS fallback (`src/services/worker/SearchManager.ts:64-112`, `:905-942`). | All memory kinds are useful to an agent when scoped to project/platform. | Kivi demands structurally separate dictation retrieval that cannot access observations/hypotheses (`kivi-semantic-memory-position.md:174-187`), unlike a shared search manager with filters. |
| How is retrieval ordered? | Chroma relevance order is deliberately preserved (commit `c4a5f1bf`); timeline hydration orders by date descending (`src/services/worker/SearchManager.ts:1094-1121`); context timeline explicitly sorts by epoch (`src/services/context/ObservationCompiler.ts:223-233`). | Relevance for search, recency for navigation, and chronology for context are distinct user intents. | Kivi adds epistemic tier, confidence/evidence, disclosure permission, decay, and contradiction status as ordering dimensions. |
| How is retrieval scoped? | Project plus merged-project alias and optional normalized platform source are filters (`src/services/worker/SearchManager.ts:76-92`). Platform scoping was added after leakage bugs (commit `348d9ee4`; issue #2687). | A project/platform is the primary tenancy boundary. | Kivi’s subject boundary is “the person this is about,” not merely project/platform; third-party content cannot share a store and be filtered later. |
| What is exposed initially? | A compact index of up to 50 observations, 10 sessions, zero full narratives by default, with explicit fetch-by-ID tools (`src/shared/SettingsDefaultsManager.ts:152-186`; `src/services/context/formatters/AgentFormatter.ts:40-45`). Configurable progressive disclosure indicates tuning uncertainty. | Token cost dominates; an agent can fetch details when needed. | Kivi separates knowing from saying and requires a Why trace, so token progressive disclosure is necessary but not equivalent to permission-based disclosure. |
| What happens when semantic search fails? | Fall back to SQLite FTS and continue; sync/search failures log warnings (`src/services/worker/SearchManager.ts:905-942`). | Stale or lexical recall is better than no recall; availability dominates perfect ranking. | Kivi requires visible abstention and search trace; silent fallback can conceal missing evidence or index drift (`kivi-semantic-memory-position.md:189-201`). |
| What happens at low confidence? | No first-class confidence field in the local observation schema; parser accepts structurally valid claims. **Inference.** | Model output quality plus later retrieval relevance is enough. | Kivi has explicit observation/hypothesis tiers, confirmation budgets, expiry, and abstention; the repo offers precedent only for operational confidence, not epistemic confidence. |
| What happens when the observer fails? | Transport errors degrade without blocking the coding session; client bugs can fail loudly after a threshold (`docs/architecture-overview.md:91-98`; `src/shared/SettingsDefaultsManager.ts:195`). Invalid output is classified and eventually poisons/recycles a generation (`src/services/worker/agents/ResponseProcessor.ts:376-424`). | Memory is auxiliary; blocking primary work costs more than memory loss. | Kivi’s memory is a product feature rather than background enhancement; silent non-retention may have a higher user cost and requires legibility. |
| What changes over time? | Sessions complete, observations accumulate, derived indexes/sync revisions advance; observer conversations recycle at a size bound (`src/shared/SettingsDefaultsManager.ts:194`). No general decay or hypothesis expiry. | Historical work remains useful; storage growth can be managed operationally. | Kivi explicitly requires decay, supersession, hypothesis expiry, confirmation, and suppression, all absent as semantic lifecycle primitives. |
| Who owns identity? | Local model distinguishes host content-session ID from observer memory-session ID (`docs/architecture-overview.md:107-112`); newer schema adds team/project/platform/agent identities (`src/storage/postgres/schema.ts:149-185`). | Worker restarts change model conversation identity; content session is stable. | Kivi additionally needs speaker, subject, author/source, and disclosure recipient identities. |

# 2. Magic numbers

“Origin” is traceable only when a comment, issue, plan, or commit says so. Otherwise it is **unclear** and classified as guessed-looking rather than falsely attributed.

| Value | Location / trace | 10× lower | 10× higher | Signal |
|---|---|---|---|---|
| 50 observations | `src/shared/SettingsDefaultsManager.ts:153` | Context omits most history | Large token/noise bill | Configurable; likely guessed/tuned operationally, origin unclear |
| 10 sessions | `src/shared/SettingsDefaultsManager.ts:183` | Weak continuity | Timeline/context bloat | Configurable; origin unclear |
| 0 full observations | `src/shared/SettingsDefaultsManager.ts:181-182` | Already minimum | More direct evidence, sharply more tokens | Deliberate progressive-disclosure default |
| semantic top-k 5 | `src/shared/SettingsDefaultsManager.ts:199-200` | rounds to zero/one useful item | injection noise and cost | Experimental, explicitly configurable; guessed pending evidence |
| 2 concurrent agents | `src/shared/SettingsDefaultsManager.ts:193` | serial backlog | provider/process pressure | Configurable operational compromise; origin unclear |
| 400,000 conversation chars | `src/shared/SettingsDefaultsManager.ts:194` | frequent recycle, lost conversational cache | overflow/latency risk | Traced to #3800; tuned from a failure |
| fail-loud after 3 | `src/shared/SettingsDefaultsManager.ts:195` | transient outage blocks host | prolonged silent loss | Plan-derived, but empirical basis unclear |
| 16,000 chars per prompt field | `src/sdk/prompts.ts:121-140` | truncates tool evidence | ~80k variable chars per observation and context pressure | Comment derives it from ~8k-token target; tuned-looking |
| 60% head / 30% tail | `src/sdk/prompts.ts:138-149` | nearly no retained content | impossible as ratios; would exceed budget | Remaining 10% is truncation marker/headroom; heuristic |
| optimizer target 0.8, timeout 30s | `src/services/worker/field-optimizer.ts:35-42` | destructive compression / premature fallback | fails to get under cap / stalls minute-scale | Defensive heuristic; origin unclear |
| exact duplicate window 30s (documented legacy) | `docs/architecture-overview.md:100-105` | retries outside 3s duplicate | distinct repeated observations within 5m collapse | Historical heuristic; current unique session/hash rule is stronger, so status is compatibility/history-sensitive |
| retry: 2 retries, 30s attempt, 100ms base, 30s cap, jitter <50ms | `src/services/worker/retry.ts:34-64` | fragile transient recovery / faster failure | long stalls, duplicate POST risk | Adapted from open-agent-sdk; defaults deliberately cap non-idempotent POSTs |
| generator restart 1/2/4s, stop after >3 | `docs/architecture-overview.md:80-89` | restart storm | minutes of stalled memory | Explicit bounded exponential policy; empirical origin unclear |
| shutdown wait 30s | `src/services/worker/SessionManager.ts:284-288` | orphan risk | shutdown hangs | Traced to #1099; failure-derived |
| Chroma connect 30s; prewarm 120s; max 600s; reap/exit 1s; reconnect 10s | `src/services/sync/ChromaMcpManager.ts:25-39` | false unavailability / frequent churn | startup and recovery stalls | Mixed: configurable prewarm, hardcoded supervision; likely operational tuning |
| 5,000 pending Chroma mutations | `src/shared/SettingsDefaultsManager.ts:214-215` | burst imports throttle/drop sooner | memory growth/OOM risk | Comment says burst bound; magnitude origin unclear |
| 2,048-char Chroma output tail | `src/services/sync/ChromaMcpManager.ts:38` | diagnostics lost | log/memory growth | Guessed diagnostic cap |
| 256 KiB prompt | `src/services/worker/http/routes/SessionRoutes.ts:44`, `:586-595` | large prompts truncated | abuse/memory pressure | Hard boundary, rationale unclear |
| 256,000-byte sync body; 4,096-byte mutation field; uint64 revisions | `src/services/sync/CanonicalContent.ts:4-7`, `:47` | rejects legitimate records/edits | transport/storage abuse | Protocol limits; likely designed but provenance unclear |
| cloud sync batch 200, max body 4,000,000 bytes, max 500 ops | `src/services/sync/CloudSync.ts:64-69`, `:739-821` | request overhead | timeout/memory/atomic failure blast radius | Tuned-looking transport limits, origin unclear |
| search defaults 3 recent sessions / 5 timeline results | `src/services/worker/SearchManager.ts:968-970`, `:1094` | insufficient context | noisy output/cost | API defaults, origin unclear |
| server search defaults 20 and 10; caps 100 and 50 | `src/server/routes/v1/ServerV1Routes.ts:235-249` | under-recall | response/DB work increases | Separate endpoints imply use-case tuning; rationale unclear |
| 90-day semantic recency window | `src/services/worker/SearchManager.ts:98-99`; commit `dc03b76b` | 9-day amnesia | 900-day stale relevance | Deliberate and later propagated to fallback, but evidence basis unclear |
| rate-limit reset grace 15m; floor 0.85 | `src/services/worker/RateLimitStore.ts:174-185` | premature retries | excessive idle time | Heuristic around provider windows; likely tuned after incidents |
| stdin safety 30s | `src/cli/stdin-reader.ts:36-82` | truncates slow input | hook hangs | Defensive guess |
| worker port 37700 + uid mod 100; server 37877 + uid mod 100 | `src/shared/SettingsDefaultsManager.ts:154`, `:267-270` | fewer collision slots | wider port allocation only, not more isolation | Deliberate multi-account convenience, collision-prone by construction |
| Chroma port 8000, Redis 6379 | `src/shared/SettingsDefaultsManager.ts:208-213`, `:256-260` | not meaningful | not meaningful | Inherited ecosystem defaults, not tuned memory decisions |

No observer temperature is set in the inspected primary path; provider defaults therefore govern it. That absence is itself an unexamined default, not evidence that temperature is irrelevant.

# 3. What the history says

Reversals and rewrites are the highest-value evidence because they show where an earlier plausible answer failed under use.

- **Highest-value reversal — Chroma-primary discovery gained SQLite FTS fallback and supplementation.** Imported/local rows could exist in SQLite yet be invisible to MCP search ([#1615](https://github.com/thedotmack/claude-mem/issues/1615)); watermark drift later left roughly half one user’s rows unindexed ([#2487](https://github.com/thedotmack/claude-mem/issues/2487)). Commits `015cbc88`, `c21e311f`, `6b404e40`, and current fallback at `src/services/worker/SearchManager.ts:905-942` show the answer changed from “vector index defines discoverability” to “vector plus lexical recovery.”
- **Highest-value reversal — schema-version trust became structural self-repair.** Missing queue columns completely stopped persistence ([#2139](https://github.com/thedotmack/claude-mem/issues/2139)); the consolidated diagnosis says version markers were trusted where actual columns/indexes had to be verified ([#2341](https://github.com/thedotmack/claude-mem/issues/2341)). Current migration code probes table structure before repair (`src/services/sqlite/SessionStore.ts:908`, `:1644-1654`, `:1827-1917`).
- **Highest-value reversal — unbounded observer conversation became bounded generations.** Commits `7a7ada5f`, `8f60f8f9`, `d1368653`, and `c26c2914` replaced a long-lived conversation with recyclable generations seeded from stored memory; the present configurable bound is `src/shared/SettingsDefaultsManager.ts:194`.
- **Search ranking was rewritten to preserve semantic order.** Commit `c4a5f1bf` explicitly fixes hydration that destroyed Chroma relevance order. This shows ordering is deliberate now, but was initially an accidental consequence of SQL hydration.
- **Project-only scoping stopped working across hosts.** Platform source was threaded through search after cross-agent memory bleed (commit `348d9ee4`; [#2687](https://github.com/thedotmack/claude-mem/issues/2687)); current filter is `src/services/worker/SearchManager.ts:76-92` and server indexes are `src/storage/postgres/schema.ts:271-297`.
- **Session identity was rewritten from one ID to two, then to composite platform/content identity.** The current two-ID rationale is explicit (`docs/architecture-overview.md:107-112`); migration and later commits repair null/orphan/composite cases. This is backward-compatibility pressure, not merely abstraction taste.
- **Dedup evolved from exact hash toward optional near-duplicate folding.** Git history includes `6b90afa0`/`6b404e40` (“opt-in near-duplicate”) and `25818e5e` (“auto dedup-folding”). The fact that near-duplicate behavior remained opt-in signals low confidence and semantic risk.
- **Queue lifecycle generated recurring bug reports.** The consolidated issue groups stuck active sessions, zombie pending rows, infinite reset loops, poor parallel throughput, and missing cleanup ([#2341](https://github.com/thedotmack/claude-mem/issues/2341)). A separate report records ~29,400 failed rows with memory frozen ([#2718](https://github.com/thedotmack/claude-mem/issues/2718)). This is repeated evidence against assuming “accepted by hook” means “durably remembered.”
- **Provider prose was mistaken for malformed model output.** Weekly-limit messages triggered poison/respawn loops and thousands of repeated calls ([#3037](https://github.com/thedotmack/claude-mem/issues/3037)); later commits `829359a4`, `3bf19145`, and `808ac7d8` introduce error envelopes and quota-aware stopping. Classification is a later repair.
- **Tool advertisement was decoupled from runtime support too late.** Server-only tools were advertised under worker runtime and could hang Codex ([#3064](https://github.com/thedotmack/claude-mem/issues/3064)). This is an integration-contract bug, not a semantic-memory decision.
- **Explicit shortcut:** XML regex parsing is acknowledged as a bridge pending deterministic tool-use JSON (`src/sdk/parser.ts:5`).
- **Explicit deferred work:** live Redis integration tests and semantic-context server independence remain follow-ups (`docs/server-release-readiness.md:161-163`); legacy worker test/typecheck failures were also deferred (`:163`). These make the new server abstraction incomplete evidence.
- **Persisted naming debt:** PostgreSQL retains `server_beta_*` table identifiers until a coordinated DDL phase (`src/storage/postgres/schema.ts:6-10`). This is backward compatibility, not confidence in the name/model.

# 4. Unexamined defaults

| Default with no visible deliberation | Alternative not tried in inspected evidence |
|---|---|
| English FTS stemming (`to_tsvector('english', content)`) (`src/storage/postgres/schema.ts:223-231`) | language-neutral tokenization, per-record language, multilingual embeddings |
| Provider temperature left implicit | explicit deterministic temperature or task-specific sampling |
| Creation time as chronology (`src/services/context/ObservationCompiler.ts:231-233`) | source event time, effective-from time, or bi-temporal history |
| Additive observation history with no contradiction edge | belief graph with supersedes/contradicts relations |
| Project/platform as read boundary | subject/person, organization, conversation, or consent boundary |
| JSON text arrays in local SQLite | normalized evidence/concept/source tables or validated JSON columns |
| Model-written type/title/narrative accepted if structurally nonempty (`src/sdk/parser.ts:137-145`) | per-field confidence, evidence entailment validation, human confirmation gate |
| Exact string/hash duplicate identity | source-aware duplicate evidence, semantic equivalence classes, or temporal reinforcement |
| “Fallback to FTS” is invisible to caller (`src/services/worker/SearchManager.ts:905-942`) | caller-visible degraded-result flag and inspected-index trace |
| All retained observations remain eligible indefinitely | decay, TTL, evidence aging, or explicit archival |
| Silence has no semantic meaning | Kivi explicitly decides silence is not confirmation (`kivi-semantic-memory-position.md:196-201`) |
| Framework/ecosystem ports 8000 and 6379 (`src/shared/SettingsDefaultsManager.ts:208-213`, `:256-260`) | dynamic allocation or socket discovery |

# 5. Questions this repo never faced

Derived directly from Kivi’s position, not inferred as omissions accidentally:

1. Who is the subject of each candidate memory, and how is “the user” distinguished from a quoted correspondent or document author?
2. Can third-party personal material be used transiently while being structurally impossible to retain?
3. Which sensitive categories are prohibited, how are candidates classified, and what auditable reason is stored for a drop without retaining the sensitive content itself?
4. What separates a stated fact, repeated observation, and live hypothesis in storage, query capability, UI, and disclosure policy?
5. Is disclosure permission evaluated before retrieval, after retrieval, or through physically separate retrieval paths—and can the dictation path prove it cannot access inferred tiers?
6. What evidence count promotes an observation; what kinds of evidence are independent rather than repeated copies of one source?
7. What does contradiction mean across names, roles, preferences, schedules, and behavioral observations, and when does new evidence supersede rather than coexist?
8. What clock drives decay: source time, last corroboration, last use, or user confirmation?
9. How does “That’s not me anymore” suppress re-derivation from unchanged transcripts without erasing the audit trail?
10. How does “Forget” differ from correction, demotion, legal deletion, index deletion, backup deletion, and sync tombstoning?
11. What is the weekly confirmation budget, what value function spends it, and how is user interruption cost measured?
12. What exactly appears in a Why panel: candidates considered, withheld memories, scores, policy reasons, model inputs, and source spans?
13. How does an abstention distinguish absent evidence, inaccessible evidence, withheld evidence, index failure, low confidence, and contradictory evidence?
14. Can a user edit a belief without forging its original provenance? Is the correction a new sourced event or mutation of old content?
15. How are permissions calibrated over relationship/time, and are disclosure settings global, contextual, recipient-specific, or topic-specific?
16. What evaluation penalizes a fluent unsupported answer versus an over-cautious abstention, and how asymmetric are those costs?

# 6. What the tests do not cover

These are decisions for which a materially different semantic answer could still pass the inspected suite; the repository supplies precedent, not evidence.

- Whether an observation is true, entailed by its source, or an impermissible characterization. Parser tests distinguish valid shape, not epistemic validity (`src/sdk/parser.ts:66-145`).
- Whether facts, observations, and hypotheses require different tables or disclosure paths; the suite assumes the current generic observation representation.
- Whether exact duplicates should reinforce confidence, merge provenance, or disappear. Current tests protect idempotent rows, not the meaning of repetition (`src/services/sqlite/SessionStore.ts:2686-2766`).
- Whether contradictions should supersede, coexist, trigger confirmation, or abstain. No inspected test models a belief changing over months.
- Whether decay improves accuracy or erases durable preferences. There is no semantic decay mechanism to test.
- Whether third-party content is never retained. Private-tag and privacy-validator tests do not establish speaker/subject classification across ordinary untagged messages.
- Whether a user correction prevents re-derivation after replay. Reversible dismiss/deletion tests, where present, protect storage/UI mechanics rather than Kivi’s suppression invariant.
- Whether disclosure permission changes what the system says while retrieval remains constant. Context tests cover formatting/filtering, not calibrated social disclosure.
- Whether abstention exposes what was searched and why no answer was given. Search tests cover result/fallback mechanics, not the user-facing epistemic trace.
- Whether relevance, recency, evidence strength, epistemic tier, or permission should dominate ranking. Existing tests freeze current Chroma/date ordering but do not compare those objectives.
- Whether FTS fallback must be visible. A test can prove fallback returns rows while still allowing silent degraded confidence.
- Whether 50 observations, 10 sessions, top-5 injection, 90 days, or any model choice optimizes user outcomes. Tests protect boundaries and regression behavior, not empirical calibration.
- Whether server and local schemas encode equivalent semantics. Parity tests primarily cover API/storage contracts; the server readiness document explicitly defers remaining dependencies and baseline failures (`docs/server-release-readiness.md:161-163`).
- Whether queue acceptance should count as memory success. Recurring “healthy worker, frozen observations” reports show health and ingestion tests historically failed to establish end-to-end liveness ([#2687](https://github.com/thedotmack/claude-mem/issues/2687)).

## Complete user-facing config inventory

The canonical contract is contiguous at `src/shared/SettingsDefaultsManager.ts:22-148`; defaults are `:151-272`. Grouped without omitting keys:

- Model/provider/auth: `CLAUDE_MEM_MODEL`, `PROVIDER`, `CLAUDE_AUTH_METHOD`, Gemini key/model/rate-limit flag, OpenRouter key/model/base/site/app (`:23`, `:29-38`, defaults `:152`, `:162-171`).
- Context: observations, read/work/savings displays, full count/field, session count, last summary/message, terminal output, welcome hint (`:24`, `:44-54`, defaults `:153`, `:177-187`).
- Runtime/paths: worker port/host, API timeout, data dir, log level, Python version, Claude path, mode, runtime (`:25-27`, `:39-43`, `:138`; defaults `:154-176`, `:263`).
- Capture: skip tools, transcript enable/config, Codex ingestion, max agents, observer chars, fail-loud threshold, excluded projects, folder Markdown switches/exclusions, semantic injection and limit (`:28`, `:55-67`; defaults `:157`, `:188-200`).
- Tier routing: enable, simple/summary/fast/smart models (`:68-72`; defaults `:201-205`).
- Chroma: enable, mode, host, port, SSL, key, tenant, database, prewarm timeout, mutation cap (`:73-82`; defaults `:206-215`).
- Cloud sync and TV: token, user, hub, device ID/name, WebSocket flag, TV token (`:87-98`; defaults `:217-228`).
- Hosted trial/credentials: email, timestamps/state/plan/fallback, staged key/base/model (`:102-114`; defaults `:231-239`).
- Notifications/awareness: Telegram enable/token/chat/type/concept; Grok awareness enable/agent/type/concept; CCS enable/viewers/types/patch shadows (`:115-130`; defaults `:240-255`).
- Queue/server: queue engine, Redis URL/host/port/mode/prefix, auth mode, canonical server URL/key/project plus legacy beta equivalents (`:131-147`; defaults `:256-272`).

Additional direct environment switches found outside that contract include banner/color/CI behavior (`src/npx-cli/banner.ts:153-216`), cleanup escape hatch (`src/services/infrastructure/CleanupV12_4_3.ts:40-41`), and host/server port probes (`src/npx-cli/cmem-memory-credentials.ts:167-276`). Their separation means the settings interface is not, in fact, the complete runtime configuration authority.

## Sources

Primary sources are the repository files and git history cited inline, plus GitHub issues [#1615](https://github.com/thedotmack/claude-mem/issues/1615), [#2139](https://github.com/thedotmack/claude-mem/issues/2139), [#2341](https://github.com/thedotmack/claude-mem/issues/2341), [#2487](https://github.com/thedotmack/claude-mem/issues/2487), [#2687](https://github.com/thedotmack/claude-mem/issues/2687), [#2718](https://github.com/thedotmack/claude-mem/issues/2718), [#3037](https://github.com/thedotmack/claude-mem/issues/3037), and [#3064](https://github.com/thedotmack/claude-mem/issues/3064).
