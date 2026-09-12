# Decision-space extraction: `akitaonrails/ai-memory` against Kivi

## Scope

This maps questions and precedent; it does not recommend answers. Snapshot: `55fcce35` on `main`. “Kivi fit” compares against the separation of retrieval/disclosure, hard third-party non-retention, and source-attributable revision in `kivi-semantic-memory-position.md:21-25`. **Inference** marks analysis rather than an explicit statement; **unclear** marks absent evidence.

Read closely: `AGENTS.md`, architecture/design/history docs, the Kivi position, core page/observation/identity/sanitization types, store migrations/writer/reader/decay, hook router, wiki mutation, consolidation, provider boundary, config, targeted tests, changelog, git history, and linked issues. Sampled: CLI plumbing, auth administration, web UI, workstream adapters, provider-specific HTTP. Skipped: repetitive client hook wrappers, packaging, generated/static assets, most installer tests, Docker/AUR detail, and the standalone importer. Claims concern the memory engine, not every installation surface.

## Orientation

### Core modules

The semantic engine is `ai-memory-core` (domain invariants), `ai-memory-store` (SQLite, ranking, decay, serialized writes), `ai-memory-wiki` (canonical Markdown, atomic mutation, watcher, git), `ai-memory-hooks` (ingress and session finalization), and `ai-memory-consolidate` (rule/LLM compilation) (`AGENTS.md:122-141`, `AGENTS.md:174-195`). `ai-memory-mcp` exposes tools/routes; `ai-memory-cli` composes services; `ai-memory-llm` is a provider boundary. `web`, `workstream`, hook bundles, packaging, evals, and importer are adapters/integrations/validation (`AGENTS.md:176-195`).

### Data model

Git-versioned Markdown is canonical; SQLite is the derived index and operational ledger (`docs/design-decisions.md:32-60`). A page has typed workspace/project/path identity, title/body, tier, open frontmatter JSON, pin, links, author, expiry, entities, timestamps, and `supersedes` (`crates/ai-memory-core/src/page.rs:36-84`, `crates/ai-memory-core/src/page.rs:270-300`). Observations have a closed kind, optional extension event, bounded body, session/project identity, and time (`crates/ai-memory-core/src/observation.rs:18-102`, `crates/ai-memory-core/src/observation.rs:113-155`). Handoffs have state, tenancy, origin/owner, content, and lifecycle (`crates/ai-memory-core/src/handoff.rs:21-188`). SQLite additionally freezes FTS, links/entities, sessions/observations, handoffs, embeddings, feedback, audit, job queues, and workstream state (`docs/ARCHITECTURE.md:141-168`). Frontmatter is YAML on disk and JSON at the typed/store boundary; enums use stable snake/kebab serialization (`crates/ai-memory-core/src/page.rs:21-22`, `crates/ai-memory-core/src/observation.rs:18-19`).

### Execution path

Lifecycle event → bounded hook router → authentication/scope/session resolution → sanitization → single-writer command (`crates/ai-memory-hooks/src/router.rs:51-62`, `crates/ai-memory-hooks/src/router.rs:578`, `crates/ai-memory-hooks/src/router.rs:2358`; `crates/ai-memory-store/src/writer.rs:52`, `crates/ai-memory-store/src/writer.rs:618-627`). One worker owns the write connection (`crates/ai-memory-store/src/writer.rs:2496-2500`). Native keyed delivery commits observation plus ingest key; session-end combines end watermark and auto-handoff, writes a heuristic session page, and may enqueue provider consolidation (`docs/design-decisions.md:98-100`). Wiki file and index changes are coordinated but have no true cross-resource transaction (`docs/design-decisions.md:60-66`).

Query → scope resolution → FTS/vector/entity/link candidates → equal RRF (`k=60`) → bounded authority multiplier → optional 30-candidate LLM rerank → bounded response (`crates/ai-memory-store/src/reader.rs:3968-3982`, `crates/ai-memory-store/src/reader.rs:4158-4241`, `crates/ai-memory-store/src/reader.rs:4290-4307`; `crates/ai-memory-mcp/src/server.rs:624-632`). Hits reinforce access after a one-minute cooldown (`crates/ai-memory-mcp/src/server.rs:4190`). Raw observation FTS appears on compiled-page miss, not as a normal co-equal stream (`docs/ARCHITECTURE.md:76-87`).

### Config surface

One immutable config is loaded defaults → TOML → `AI_MEMORY_*` → CLI (`crates/ai-memory-cli/src/config.rs:1-7`, `crates/ai-memory-cli/src/config.rs:986-1016`). Complete semantic surface: paths/bind/logging; LLM provider/model/URL/strict schema/timeout/reasoning/headers/fallbacks; consolidate-on-end; assistant capture; MCP schema compatibility; reranker; embedding provider/model/dimension/URL; decay/raw retention; maintenance; slots; consolidation budgets; auto-improvement scheduling/eval/approval/bounds; sanitizer; auth; auto-scope; mid-session routing; hook rate/burst; hosts/CORS; admission webhooks (`crates/ai-memory-cli/src/config.rs:152-392`). Environment-only credentials/routing are at `crates/ai-memory-cli/src/config.rs:395-463`; defaults at `crates/ai-memory-cli/src/config.rs:691-733`, `crates/ai-memory-cli/src/config.rs:753-915`, and `crates/ai-memory-cli/src/config.rs:956-982`.

### Tests read

Repository count: 200 of 267 Rust files contain tests (**measured inference**). Dense tests cover sanitization, hook parsing/replay/finalization, store transactions/scope/supersession, FTS/hybrid ranking, decay properties, wiki admission/atomicity, provider dialects, auto-improvement, MCP schemas/routes, lifecycle operations, and installers. Examples: search regressions (`crates/ai-memory-store/src/lib.rs:2187-2465`), decay (`crates/ai-memory-store/src/decay.rs:156-275`), hook integration (`crates/ai-memory-hooks/src/router.rs:3594-12581`), MCP temporal/scope/raw/limit behavior (`crates/ai-memory-mcp/src/server.rs:6496-8763`, `crates/ai-memory-mcp/src/server.rs:11196-11240`). LongMemEval is separate; hit@5 moved 0.617→0.823 across retrieval changes (`docs/benchmarks/README.md:16-22`). Skipped areas are listed under Scope and are not evidence for semantic claims.

## 1. Decision inventory

### What enters

**Question:** Automatically retain bounded lifecycle projections, or require explicit semantic admission? **Repo:** automatic capture; manual writes only for explicitly durable knowledge; path exclusions can drop recognized tool events pre-spool (`docs/design-decisions.md:104-129`). **Placement:** capture is architectural, exclusions configurable—high confidence in broad capture, lower at file boundaries. **Assumes:** codebase traffic is project-owned and secret stripping/size bounds form an adequate trust boundary. **Kivi:** weak; Kivi requires subject/category exclusion before storage (`kivi-semantic-memory-position.md:47`, `kivi-semantic-memory-position.md:106-125`), pushing from path privacy toward semantic/identity admission.

**Question:** Retain assistant output? **Repo:** double opt-in and capped (`crates/ai-memory-cli/src/config.rs:258-265`; `crates/ai-memory-hooks/src/assistant_capture.rs:33-38`). **Placement:** configurable, signaling uncertainty. **Assumes:** assistant text is derivative/contaminating. **Kivi:** directionally aligned, but speaker role does not solve user-versus-third-party subject.

**Question:** Should rejection be invisible or leave a non-content audit? **Repo:** excluded capture disappears before spool/log/storage (`AGENTS.md:463-467`). **Placement:** hard boundary. **Assumes:** trace minimization beats proving absence. **Kivi:** conflict; Kivi wants “read, not kept” counts/reasons without content (`kivi-semantic-memory-position.md:123-125`).

### Representation/storage

**Question:** Legible files or transactional DB as truth? **Repo:** Markdown-in-git primary, SQLite derived (`docs/design-decisions.md:32-60`). **Placement:** hard architecture, highest confidence. **Assumes:** hundreds/low-thousands of pages and human portability outweigh cross-resource atomicity (`docs/design-decisions.md:68-86`). **Kivi:** legibility/reversibility fit; transactional erasure and per-person controls do not.

**Question:** Normalized claim/evidence records or flexible documents? **Repo:** typed page envelope with mostly open frontmatter (`crates/ai-memory-core/src/page.rs:36-84`). **Placement:** envelope hardcoded, semantics convention-pluggable. **Assumes:** agents produce coherent pages and variable knowledge shapes. **Kivi:** partial; Kivi explicitly freezes `type`, `tier`, content, evidence count, source transcript IDs, first/last time, status (`kivi-semantic-memory-position.md:99`), pushing toward normalized provenance/status.

**Question:** Separate stores per memory kind or one polymorphic table? **Repo:** one page table with tier plus observations (`docs/design-decisions.md:131-142`). **Placement:** schema-hardcoded for migration simplicity. **Assumes:** tiers differ in ranking/retention, not security. **Kivi:** risky because inference/disclosure permissions may differ by kind; its axes are independent (`kivi-semantic-memory-position.md:66-99`).

**Question:** Strings or typed entities? **Repo:** lowercase names leniently merged from `entities` and `tags`, max 10×64 chars (`crates/ai-memory-core/src/page.rs:77-91`, `crates/ai-memory-core/src/page.rs:154-177`). **Placement:** hard bounds, shallow ontology. **Assumes:** ambiguity is tolerable within projects. **Kivi:** poor for people; untyped names cannot enforce non-retention and may conflate identities (`kivi-semantic-memory-position.md:74`).

### Discarding/change

**Question:** When is deletion irreversible? **Repo:** TTL hard-deletes even pinned pages; low-retention episodic pages tombstone then purge ancestry after 180 days; raw observations persist unless positive retention is configured (`docs/ARCHITECTURE.md:88-111`; `crates/ai-memory-cli/src/config.rs:66-85`). **Placement:** formula configurable, TTL semantics hardcoded, raw prune opt-in. **Assumes:** storage cheap and reconsolidation/forensics valuable. **Kivi:** conflict for third-party material and corrections that must block regrowth (`kivi-semantic-memory-position.md:239-241`).

**Question:** Should access determine survival? **Repo:** salience×age decay plus logarithmic recent-access reinforcement and optional reader breadth (`crates/ai-memory-store/src/decay.rs:1-7`, `crates/ai-memory-store/src/decay.rs:94-119`). **Placement:** configurable coefficients, hard formula. **Assumes:** retrieval correlates with value. **Kivi:** uncertain; frequent retrieval can reinforce a sensitive/wrong belief, pushing toward separate usefulness, truth, and disclosure signals.

**Question:** Can correction prevent re-derivation? **Repo:** edit/delete/supersede/pin/feedback/TTL exist; no source-level suppression was found (**inference**) (`crates/ai-memory-core/src/page.rs:270-328`; `crates/ai-memory-store/src/decay.rs:132-153`). **Kivi:** direct gap; it explicitly demands durable suppression (`kivi-semantic-memory-position.md:232-241`).

### Conflict/duplicate/order

**Question:** Overwrite, fork, merge, or supersede conflicting writes? **Repo:** same-path writes supersede; per-path serialization preserves the losing version (`AGENTS.md:388-390`; `CHANGELOG.md:389`). **Placement:** invariant and lock, very high confidence. **Assumes:** path equals knowledge identity. **Kivi:** history fits revisability, but semantically equivalent claims at different paths remain unresolved.

**Question:** Resolve contradictions or surface them? **Repo:** typed `contradicts` edges and lint; unknown relations remain plain links (`crates/ai-memory-core/src/page.rs:203-228`; `docs/design-decisions.md:154-162`). **Placement:** vocabulary hardcoded, detection provider-pluggable. **Assumes:** surfacing is safer than choosing. **Kivi:** useful but incomplete; unresolved conflict must affect response/abstention, not only maintenance (`kivi-semantic-memory-position.md:203-227`).

**Question:** How are delivery duplicates handled? **Repo:** stable scoped keys, atomic observation+key commit, downstream completion marker, bounded overlapping-key gate; downstream effects remain at-least-once until completion (`docs/ARCHITECTURE.md:31-48`). **Placement:** protocol/schema, high confidence. **Assumes:** crashes and retries are normal; duplicate effect is cheaper than silent loss. **Kivi:** strong infrastructure precedent, conditional on suppression also being idempotent.

**Question:** Wall clock or generation ordering? **Repo:** resumed end uses observation-count generation, not time (`docs/design-decisions.md:99`). **Placement:** hardcoded after a bug. **Assumes:** IDs resume and clocks/delivery are unreliable. **Kivi:** supports transcript offsets/generations over timestamp-only last-write-wins.

### Retrieval/order/exposure/failure

**Question:** Which retrievers compete? **Repo:** FTS, cosine, lexical entity, link-neighbor (`crates/ai-memory-store/src/reader.rs:3968-3982`). **Placement:** built-ins; vector/reranker pluggable. **Assumes:** heterogeneous rank improves recall cheaply. **Kivi:** useful recall precedent, but no independent disclosure pass despite Kivi’s explicit separation (`kivi-semantic-memory-position.md:155`).

**Question:** How combine streams? **Repo:** equal RRF, `k=60`, then authority (`crates/ai-memory-store/src/reader.rs:4158-4241`). **Placement:** hardcoded, likely inherited convention. **Assumes:** ranks compare better than scores and streams deserve equal influence. **Kivi:** unclear; evidence/source quality and permissions are missing dimensions.

**Question:** Should durable knowledge outrank episodes? **Repo:** bounded 0.55–1.50 multiplier; rules/decisions/procedures/gotchas rise, sessions/episodic/historical/test evidence fall but remain visible (`crates/ai-memory-store/src/reader.rs:214-267`). **Placement:** hardcoded policy. **Assumes:** kind proxies authority. **Kivi:** wrong dimension—a memory may be relevant/true yet forbidden to disclose.

**Question:** What on compiled-memory miss? **Repo:** bounded raw-observation FTS; any page hit suppresses raw fallback (`docs/ARCHITECTURE.md:76-87`). **Placement:** hardcoded. **Assumes:** compiled pages preferred, raw logs rescue recall. **Kivi:** risky; transcripts are provenance and may contain material that must never persist/surface (`kivi-semantic-memory-position.md:106-125`).

**Question:** Can an LLM reorder results? **Repo:** opt-in, max 30, one call, four concurrent; every invalid/failing/saturated attempt preserves deterministic order (`crates/ai-memory-mcp/src/server.rs:624-632`; `crates/ai-memory-cli/src/config.rs:291-298`). **Placement:** pluggable/fail-open, signaling uncertainty. **Kivi:** acceptable for relevance, unacceptable as disclosure authority because policy failure must not fail open.

**Question:** What does caller see? **Repo:** bounded hits/descriptors and optional rank provenance; raw evidence via fallback/dedicated pagination (`docs/design-decisions.md:204-226`). **Placement:** public compatibility-sensitive schema. **Assumes:** caller is an agent. **Kivi:** insufficient for a normal-user Why panel showing retrieved/withheld/used/source (`kivi-semantic-memory-position.md:227`).

**Question:** What does low confidence do? **Repo:** auto-improvement rejects below configurable .75; ordinary retrieval has no confidence abstention; stale/wrong feedback lowers salience and creates lint (`crates/ai-memory-consolidate/src/auto_improve.rs:71-79`; `crates/ai-memory-store/src/decay.rs:137-153`). **Placement:** write threshold configurable, read behavior hardcoded. **Assumes:** uncertainty matters at write time. **Kivi:** conflict; uncertainty is a visible response state (`kivi-semantic-memory-position.md:203-227`).

## 2. Magic numbers

Scope: every threshold/limit/window/timeout/top-k/temperature/ratio found in the closely read semantic runtime. Excluded: auth/password, HTTP error-display, installer/UI/packaging, and test-fixture numbers.

For compactness in this table only, `core/`, `store/`, `hooks/`, `wiki/`, `consolidate/`, `mcp/`, `llm/`, and `cli/` expand respectively to `crates/ai-memory-core/`, `crates/ai-memory-store/`, `crates/ai-memory-hooks/`, `crates/ai-memory-wiki/`, `crates/ai-memory-consolidate/`, `crates/ai-memory-mcp/`, `crates/ai-memory-llm/`, and `crates/ai-memory-cli/`. Every entry remains a repository-relative `file:line` citation.

| Number | Location/provenance | 10× lower / 10× higher | Tuned? |
|---|---|---|---|
| Observation 16 KiB; tool/notification 2 KB | `core/src/sanitize.rs:46`; `hooks/src/payload.rs:12-20` | Loses decisions / expands leakage, DB, prompt cost | Defensive guess |
| Assistant 64 KiB input→2 KB excerpt | `hooks/src/assistant_capture.rs:33-38` | Misses tail / parsing and contamination grow | Defensive guess |
| 10 entities, 64 chars | `core/src/page.rs:86-91` | One/6 chars kills recall / 100/640 admits noise | Deliberate bounds, not benchmarked |
| RRF `k=60` | `store/src/reader.rs:3982,4158-4159` | 6 makes top ranks dominate / 600 flattens differences | Canonical inherited default |
| Authority window max(20,4×limit)+300 | `store/src/reader.rs:196-198,295` | Prevents rescue / raises SQL+hydration work | Regression-tuned |
| Authority 0.55–1.50 plus kind/tier/tag increments | `store/src/reader.rs:214-267` | Suppresses evidence / metadata swamps relevance | Hand-tuned |
| Query entities 12 tokens, ≥3 chars | `store/src/reader.rs:413-414` | Misses multi-entity / admits noise | Guess |
| Rerank 3× overfetch, 30 candidates, 4 in flight | `mcp/src/server.rs:624-632` | Cannot promote enough / token and provider load | Cost/safety tuned |
| Rerank 1000/200/600 B query/title/snippet | `llm/src/reranker.rs:74-78` | Loses disambiguation / raises cost+injection surface | Guess |
| Access cooldown 60 s | `mcp/src/server.rs:4190` | Query loops inflate / legitimate repeats undercount | Operational guess |
| Decay λ=.02, σ=.6, μ=.04, salience=1, cold=.20, purge=180 d | `store/src/decay.rs:35-44` | Near-permanent/weak access/18d recovery / days-scale forgetting/access dominance/1800d deletion | Formula adapted; coefficients guessed; λ comment derives ~35d half-life (`store/src/decay.rs:18-20`) |
| Salience .25–2, step .25 | `store/src/decay.rs:122-153` | Immediate eviction/tiny correction / quasi-pin/one-shot swings | Deliberate policy |
| Raw prune batch 5,000 | `consolidate/src/sweep.rs:138` | Transaction overhead / longer write locks | Operational guess |
| Maintenance daily; embedding backfill 0 | `cli/src/config.rs:975-982` | More churn / stale state; backfill remains explicit | Round default |
| Consolidation 100k input, 32k output; floors 6k/1k | `consolidate/src/consolidator.rs:1046-1078` | Starves evidence/output / exceeds contexts/cost | Sized for stated 200k context (`cli/src/config.rs:318-320`) |
| Projection 256×3000 chars; prior body 20k | `consolidate/src/consolidator.rs:1087-1092` | Loses distributed evidence / blows context | Budget guess, tests bound |
| Sampling 16 buckets; title/source 500/128; body prefix 4000 | `consolidate/src/projection.rs:7-10,426-445` | Recency bias/truncation / overhead and context | Algorithmic guess |
| Auto-improve .75, 8 observations, 120 s | `consolidate/src/auto_improve.rs:71-75` | Incidental noise / misses short meaningful sessions (confidence 7.5 invalid) | Guess |
| Auto-improve 24k input, 5 proposals | `consolidate/src/auto_improve.rs:77-79` | Evidence starvation / cost and proposal flood | Safety/cost guess |
| Patch 8 pages×8k, 5 edits×4k, 12k changed, 8 edits/run | `consolidate/src/auto_improve.rs:30-40` | Blocks meaningful edits / broad autonomous rewrites | Explicit blast radius |
| Rejection context 50/180d/12k chars | `consolidate/src/auto_improve.rs:42-44,62` | Repeats rejected ideas / anchors and crowds prompt | Guess |
| Scheduler 3600 s, 1 session/project, 600 s age; experience 0 else 10 | `cli/src/config.rs:866-875` | Churn/races / delayed learning; 1 lacks pattern / 100 costs context | Conservative rounds |
| LLM timeout 300 s | `llm/src/lib.rs:39`; rationale `cli/src/config.rs:190-198` | Kills cold models / ties resources 50 min | Operationally informed |
| Consolidation attempts 5; fallback cooldown 30 s | `store/src/session_consolidation.rs:11`; `llm/src/fallback.rs:28` | Transient loss/thrash / costly retries/healthy provider unused | Conventional |
| Atomic persistence 5 attempts, 10 ms base | `wiki/src/atomic.rs:19-20` | Exposes transient races / can stall | Platform-informed |
| Watch reconcile 30 s, debounce 300 ms, degrade after 5 | `wiki/src/watcher.rs:35-38,150` | IO/duplicates / minutes of stale index | Operational guess |
| Ingest 1024 in flight; maps 4096; batch 256 | `hooks/src/router.rs:51-80` | Sheds bursts / memory+DB contention | Capacity guess |
| Ingest-key TTL 30 d | `store/src/ops.rs:1392` | Late replay duplicates / dedupe state grows | Replay-window guess |
| Brief 4k, min1.5k,max20k; 24 core+10 recent | `hooks/src/router.rs:1523-1541` | Context disappears / startup prompt swells | Product-budget guess |
| Handoff 3k/1.5k/512; 20 items; 4–6k lists | `mcp/src/server.rs:36-41` | Loses actionable state / overwhelms next prompt | Prompt-budget guess |
| Rerank temperature .2 | `mcp/src/server.rs:4456` | .02 more deterministic / 2 unstable | Conventional, no tuning evidence |

## 3. What history says

Reversals are the highest-value signal.

1. **Embedding default reversed twice:** prototype local → v1 off → v2 local default after measured recall improvement/no-egress support (`docs/design-decisions.md:92`; `docs/benchmarks/README.md:16-33`; `CHANGELOG.md:685-740`). Genuine reversal.
2. **Session-end idempotency rewrote “already ended, ignore” into observation generations.** Resumed work was stranded in raw rows; now `ended_observation_count` gates re-entry (`docs/design-decisions.md:99`; [issue #152](https://github.com/akitaonrails/ai-memory/issues/152)). High-value reversal about order/idempotency.
3. **Auto handoffs changed from passive accumulation/specificity-first selection to lifecycle supersession/expiry while preserving manual batons** (`docs/design-decisions.md:194`; [issue #293](https://github.com/akitaonrails/ai-memory/issues/293)). Genuine reversal.
4. **Retrieval repeatedly grew new abstractions:** FTS → stopword handling → entity stream → authority → vectors → optional rerank (`CHANGELOG.md:829-831`, `CHANGELOG.md:2705`, `docs/benchmarks/README.md:16-22`). It is benchmark-responsive precedent, not settled truth.
5. **Concurrency moved from implicit races to same-path serialization with preserved supersession** after purge resurrection/divergence (`CHANGELOG.md:389`; `AGENTS.md:388-390`). Later abstraction implies original dual-store answer failed concurrently.
6. **Whole-prompt bounds replaced sectional bounds** after consolidation/briefing bugs (git `64aee229`; `CHANGELOG.md:45`). Recurring bug family: local caps did not cap the envelope.
7. **Typed relations were reshaped for strict providers and later preserved through batch fan-out** (`CHANGELOG.md:91`; git `bab47adb`, `d5c0e375`). Compatibility/incomplete plumbing, not a semantic reversal.
8. **Raw observations gained a dedicated session read surface** after compiled hits made fallback evidence unreachable (`docs/design-decisions.md:222`; [issue #401](https://github.com/akitaonrails/ai-memory/issues/401)). Provenance access was added later.
9. **Migration archive ordering was corrected** after documentation overstated rollback (git `e672f3b9`, `681b1a86`). Incomplete safety work, not semantic design.
10. **Generated token pepper accidentally triggered multi-user behavior**; mode now follows actual user state (`docs/users.md:46`; [issue #191](https://github.com/akitaonrails/ai-memory/issues/191)). An accidental implementation default.

Recurring bugs cluster around hook cancellation/tail loss, duplicate/resumed session ends, stale handoffs, cwd/session/operator scope, file-watcher/dual-store races, whole-prompt bounding, FTS edge cases, provider schema dialects, and destructive file/DB divergence (`CHANGELOG.md:389`, `CHANGELOG.md:1320-1350`, `CHANGELOG.md:2543`).

Core TODO/FIXME markers are scarce. Explicit shortcuts live in design docs: brute-force packed vectors defer `sqlite-vec` (`docs/design-decisions.md:79`); FTS assumes hundreds/low-thousands pages (`docs/design-decisions.md:86`); local embeddings were once future work (`docs/design-decisions.md:92`); RBAC was excluded (`docs/design-decisions.md:260-275`). Absence of TODOs is not completeness; repairs are recorded in issues/changelog instead.

## 4. Unexamined defaults

- Equal-weight RRF: no config/test compares unequal weights (`store/src/reader.rs:4158-4241`). Untried: learned/per-query weights.
- Path equals claim identity (`core/src/page.rs:270-300`). Untried: stable entity-predicate claim IDs.
- Tags double as entities (`core/src/page.rs:154-177`). Untried: separate typed entity references/aliases.
- Hit means usefulness after cooldown (`mcp/src/server.rs:4190`). Untried: reinforce only evidence actually used/accepted.
- No required subject-of-memory field (`core/src/page.rs:270-300`). Untried: typed user/third-party subject identity at admission.
- No disclosure-decision object; explanation describes ranks, not retrieved/withheld/used (`store/src/reader.rs:482-549`). Untried: auditable second policy pass.
- English stopword behavior improved an English benchmark, with no language router in the cited path (**inference**) (`docs/benchmarks/README.md:22`). Untried: language-specific analyzers.
- First H1/frontmatter title supplies descriptor identity (`core/src/page.rs:43-45`). Untried: immutable claim label separate from display title.
- Confidence belongs to proposals, not required stored beliefs (`core/src/page.rs:36-84`; `consolidate/src/auto_improve.rs:71-79`). Untried: evidence-derived belief confidence.
- Raw source is assumed acceptable once sanitized and is retained by default (`cli/src/config.rs:66-85`; `docs/ARCHITECTURE.md:76-87`). Untried: safe-span extraction then raw deletion.

## 5. Questions this repo never faced

1. How is the person a fact concerns resolved before storage across pronouns, quotes, forwarded text, and names (`kivi-semantic-memory-position.md:21-25`)?
2. What minimal audit proves “read, not kept” without reconstructable rejected content (`kivi-semantic-memory-position.md:123-125`)?
3. How are retrieval and disclosure separate state machines, and does policy failure fail closed (`kivi-semantic-memory-position.md:155-176`)?
4. Is permission attached to a memory, relationship, task, conversation, or global mode (`kivi-semantic-memory-position.md:129-176`)?
5. How is a work fact involving a colleague separated from a personal claim about them when co-located in one sentence (`kivi-semantic-memory-position.md:106-125`)?
6. What durable negative artifact implements “not me anymore”; what does it suppress and for how long (`kivi-semantic-memory-position.md:232-241`)?
7. What happens to a multi-source belief when one transcript/span is deleted or reclassified (`kivi-semantic-memory-position.md:99,236-247`)?
8. How are contradiction and temporal change distinguished (`kivi-semantic-memory-position.md:17,265`)?
9. Does abstention express factual uncertainty, permission uncertainty, insufficient evidence, conflict, or missing provenance (`kivi-semantic-memory-position.md:203-227`)?
10. Can a Why panel reveal a withheld memory exists without itself disclosing it (`kivi-semantic-memory-position.md:227`)?
11. Who controls memories about minors, shared accounts, jointly owned projects? **Unclear** in both repo and Kivi document.
12. Can replay retain a transcript for other purposes while deterministically preventing corrected-belief regrowth (`kivi-semantic-memory-position.md:239-241`)?
13. Does evidence count mean transcripts, independent spans, time-separated confirmations, or duplicates (`kivi-semantic-memory-position.md:99`)?
14. How does “source one tap away” reveal the exact span without adjacent third-party leakage (`kivi-semantic-memory-position.md:227,236-247`)?
15. Which controls are distinct: edit, demote, delete belief, delete source, export, suppress derivation, erase derivatives (`kivi-semantic-memory-position.md:232-249`)?

## 6. What tests do not cover

- Semantic third-party admission: sanitizer tests cover secrets/size, not subject (`core/src/sanitize.rs:46`; Kivi `kivi-semantic-memory-position.md:47-48`).
- Disclosure correctness: ranking tests assert relevance/scope, but no permission filter exists (`store/src/lib.rs:2187-2465`; Kivi `kivi-semantic-memory-position.md:155-176`).
- Transcript-span provenance: page tests can pass without it (`core/src/page.rs:36-84`; Kivi `kivi-semantic-memory-position.md:236-247`).
- Correction suppression: feedback tests pin salience, not non-regrowth (`store/src/decay.rs:239-275`; Kivi `kivi-semantic-memory-position.md:239-241`).
- Eval measures hit/recall, not inappropriate recall, withholding, contradiction calibration, or abstention (`docs/benchmarks/README.md:16-22`).
- RRF/authority/top-k values have bound/regression tests, not comparative evidence (`store/src/reader.rs:4158-4241`, `store/src/reader.rs:8647-8654`).
- Decay tests prove monotonic properties, not user-correct 80/180-day policy (`store/src/decay.rs:161-275`; `cli/src/config.rs:308-312`).
- Same-path supersession does not test semantic duplicates across paths (`store/src/lib.rs:2187`; `core/src/page.rs:292`).
- Transport idempotency does not test the same utterance arriving under different IDs (`docs/ARCHITECTURE.md:31-48`).
- Project/operator isolation does not identify people mentioned in content (`AGENTS.md:382-397`; Kivi `kivi-semantic-memory-position.md:21-25`).
- Structured-output tests validate shape/provider dialect, not psychological characterization or allowed ontology (`docs/design-decisions.md:97-101`; Kivi `kivi-semantic-memory-position.md:29-48`).
- Raw-retention tests protect last-copy/batch mechanics, not whether retaining raw consumer text is permissible (`docs/ARCHITECTURE.md:96-111`).
- Reranker failure preserves local order; no analogous fail-closed disclosure test exists (`cli/src/config.rs:291-298`).

The suite provides evidence for mechanics—atomicity, replay, scope, bounds, and compatibility. On Kivi’s defining questions—subject admission, calibrated disclosure, person-legible provenance, and correction suppression—the repository supplies ingredients and precedent, not evidence.

## External primary records

[Issue #152](https://github.com/akitaonrails/ai-memory/issues/152), [#293](https://github.com/akitaonrails/ai-memory/issues/293), [#401](https://github.com/akitaonrails/ai-memory/issues/401), and [#191](https://github.com/akitaonrails/ai-memory/issues/191). All other evidence is cited to the local repository snapshot and supplied Kivi position.
