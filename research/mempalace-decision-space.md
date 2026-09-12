# MemPalace Decision Space for Kivi

This is a map of questions and precedents, not a recommendation. “Kivi fit” means whether the assumptions in this repository match the commitments in `kivi-semantic-memory-position.md`; it does not select an answer.

## Scope and method

The repository was read at commit `f9297a2` on branch `develop`. Evidence came from the core runtime, its storage contracts, schemas, configuration, relevant regression and conformance tests, and local Git history. GitHub issues and pull requests were consulted only as primary historical records. File citations use `path:line`; history citations name the commit or link the issue/PR. Where intent is not explicit, the text says **inference** or **unclear**.

Read closely: `mempalace/config.py`, `miner.py`, `convo_miner.py`, `normalize.py`, `general_extractor.py`, `searcher.py`, `palace.py`, `ids.py`, `entities.py`, `entity_detector.py`, `entity_registry.py`, `knowledge_graph.py`, `layers.py`, `dynamics.py`, `dedup.py`, `dialect.py`, `backends/base.py`, `backends/chroma.py`, `backends/sqlite_exact.py`, the CLI/MCP entry points around mining/search/drawer/KG operations, and tests directly corresponding to those modules. I also inspected schema-bearing `logstream.py`, source-adapter contracts, RFC-related comments, blame for load-bearing constants, and Git history for reversals and regressions.

Read selectively: `cli.py` and `mcp_server.py` are very large orchestration surfaces; their command definitions, dispatch paths, public result envelopes, limits, failure gates, and write paths were read, but not every presentation string. Alternative remote backends were read for their configuration and contract differences, not line by line. `repair.py`, `sync.py`, and daemon/coordination modules were read where they expose consistency assumptions.

Skipped: website/landing visual code, translated message bodies, images/assets, most deployment packaging, benchmark corpora, examples, plugin manifest boilerplate, and integration-specific behavior unrelated to memory semantics. Tests for CSS/docs spelling/manifest shape were inventoried but not treated as evidence about memory decisions.

## Orientation

### Core versus shell

The real logic is concentrated in:

- Project ingestion and representation: `mempalace/miner.py:1408`, `mempalace/miner.py:1500`, `mempalace/miner.py:1860`.
- Conversation ingestion and representation: `mempalace/convo_miner.py:298`, `mempalace/convo_miner.py:628`, `mempalace/convo_miner.py:1009`.
- Retrieval and ordering: `mempalace/searcher.py:166`, `mempalace/searcher.py:334`, `mempalace/searcher.py:1961`.
- Collection lifecycle, locking, and “already mined” semantics: `mempalace/palace.py:214`, `mempalace/palace.py:844`, `mempalace/palace.py:1301`, `mempalace/palace.py:1450`.
- Persistence abstraction and concrete default: `mempalace/backends/base.py:101`, `mempalace/backends/base.py:362`, `mempalace/backends/base.py:600`, `mempalace/backends/chroma.py:206`.
- Temporal entity relationships: `mempalace/knowledge_graph.py:142`, `mempalace/knowledge_graph.py:156`.

`cli.py`, `mcp_server.py`, `service.py`, hook scripts, proxy/transport, and daemon code expose and orchestrate that logic (`mempalace/cli.py:951`, `mempalace/cli.py:1562`, `mempalace/mcp_server.py:2570`, `mempalace/mcp_server.py:3459`). `integrations/`, `examples/`, deployment files, and plugin manifests are adapters or distribution surfaces. This distinction is imperfect: `mcp_server.py` also contains substantial diary mutation policy, so it is glue with embedded domain decisions (`mempalace/mcp_server.py:3186`, `mempalace/mcp_server.py:4288`).

### Data model

The principal record is a **drawer**: a verbatim document plus an ID and flat metadata. Project-mine metadata includes wing, room, hall, source path, chunk index/total, timestamps, content hash, normalization version, entities, and optional authored date (`mempalace/miner.py:1429`, `mempalace/miner.py:1440`, `mempalace/miner.py:1695`). Conversation drawers additionally carry ingest/extract mode and agent/source provenance (`mempalace/convo_miner.py:123`, `mempalace/convo_miner.py:710`, `mempalace/convo_miner.py:723`). Zero-content files can still acquire registry sentinel rows so idempotency has a durable marker (`mempalace/convo_miner.py:215`, `mempalace/convo_miner.py:243`).

The backend contract freezes typed query/get results and a flat filter language (`mempalace/backends/base.py:289`, `mempalace/backends/base.py:326`, `mempalace/backends/base.py:362`). Backend and embedder identity are persisted and checked because vector spaces are not interchangeable (`mempalace/backends/base.py:140`, `mempalace/backends/base.py:192`). Chroma creates cosine HNSW collections with serialized inserts and upstream batch/sync defaults (`mempalace/backends/chroma.py:206`, `mempalace/backends/chroma.py:242`).

The knowledge graph is separate SQLite state. `entities` stores `id`, `name`, `type`, JSON `properties`, and `created_at`; `triples` stores subject/predicate/object, temporal validity, source and confidence (`mempalace/knowledge_graph.py:160`, `mempalace/knowledge_graph.py:168`). Dates are TEXT, so input accepts only canonical full dates or UTC datetimes to preserve lexical ordering (`mempalace/config.py:130`, `mempalace/config.py:167`). Coordination data uses separate SQLite `events`, `artifacts`, and join tables, with JSON metadata and hybrid logical clocks (`mempalace/logstream.py:453`, `mempalace/logstream.py:482`, `mempalace/logstream.py:496`). JSON files hold config, people aliases, hallways, and tunnels (`mempalace/config.py:618`, `mempalace/config.py:621`, `mempalace/config.py:622`, `mempalace/config.py:817`).

### Main execution path

Project path: the console entry point reaches `cli.main`, dispatches `cmd_mine`, resolves mode/config/backend, scans readable files, normalizes/chunks content, and invokes the per-file processor (`pyproject.toml:57`, `mempalace/cli.py:951`, `mempalace/miner.py:443`, `mempalace/miner.py:1500`). The processor checks file type/size and the chunk cap, takes a source lock, rechecks idempotency, purges stale rows, calculates deterministic IDs/metadata, batch-upserts drawers, and creates closet index lines (`mempalace/miner.py:1519`, `mempalace/miner.py:1560`, `mempalace/miner.py:1605`, `mempalace/miner.py:1641`).

Conversation path: `cmd_mine` dispatches to `mine_convos`, format normalization yields exchanges or general extracted memories, unchanged sources are skipped, changed sources are purged and rebuilt under a lock, and complete batches plus a sentinel are upserted (`mempalace/cli.py:1021`, `mempalace/convo_miner.py:875`, `mempalace/convo_miner.py:973`, `mempalace/convo_miner.py:1140`, `mempalace/convo_miner.py:1187`). A partial multi-batch failure triggers cleanup rather than leaving a set that can masquerade as complete (`mempalace/convo_miner.py:758`).

Search path: CLI/MCP calls `search_memories`; the function resolves language and date/filter gates, opens the backend, over-fetches vector candidates, optionally unions lexical candidates, re-ranks with vector similarity plus BM25, applies date/distance scope, enriches closet hits, deduplicates, and truncates into a structured envelope (`mempalace/searcher.py:1961`, `mempalace/searcher.py:2032`, `mempalace/searcher.py:2055`, `mempalace/searcher.py:2180`). When HNSW is judged unsafe, it routes to SQLite/BM25 instead of opening the native vector reader (`mempalace/searcher.py:2002`, `mempalace/searcher.py:1745`).

### Configuration surface

The primary precedence is environment over `~/.mempalace/config.json` over defaults, except explicit path/command arguments and some compatibility-sensitive backend resolution (`mempalace/config.py:1`, `mempalace/config.py:602`, `mempalace/palace.py:387`). The settings are:

| Area | Settings and defaults | Evidence |
|---|---|---|
| Identity/path | `--palace`; `MEMPALACE_PALACE_PATH`; `palace_path`; collection `mempalace_drawers`; backend `chroma` | `mempalace/config.py:226`, `mempalace/config.py:227`, `mempalace/config.py:228`, `mempalace/config.py:804`, `mempalace/config.py:834` |
| Chunking/admission | `chunk_size=800`, `chunk_overlap=100`, `min_chunk_size=50` projects / 30 conversations; `--max-chunks-per-file` or `MEMPALACE_MAX_CHUNKS_PER_FILE=50000`; `--limit`; include ignored/subagents; extract mode | `mempalace/config.py:274`, `mempalace/convo_miner.py:163`, `mempalace/miner.py:205`, `mempalace/cli.py:3273`, `mempalace/cli.py:3290`, `mempalace/cli.py:3315` |
| Search | query, wing, room, exact source file, `[since,before)`, results `5`, max distance `0` (disabled), candidate strategy `vector|union`, language | `mempalace/searcher.py:1961`, `mempalace/searcher.py:1969`, `mempalace/searcher.py:1972`, `mempalace/cli.py:3401`, `mempalace/cli.py:3409` |
| Language/entities | `MEMPALACE_LANG`/`MEMPAL_LANG`; `lang`; `MEMPALACE_ENTITY_LANGUAGES`/`MEMPAL_ENTITY_LANGUAGES`, default `['en']`; topic wings and hall keyword maps | `mempalace/config.py:1114`, `mempalace/config.py:1377`, `mempalace/config.py:1395`, `mempalace/config.py:283`, `mempalace/config.py:293` |
| Embeddings | model (`minilm` compatibility fallback; onboarding may persist `embeddinggemma`), device `auto`, threads half logical CPUs, Gemma batch `32`, OpenAI-compatible URL/model/key | `mempalace/config.py:1146`, `mempalace/config.py:1163`, `mempalace/config.py:1187`, `mempalace/config.py:1218`, `mempalace/config.py:1291` |
| Remote backends | Qdrant URL/key/namespace/timeout; Milvus URI/token/db/namespace/consistency; pgvector DSN/namespace; backend env/flag | `mempalace/config.py:839`, `mempalace/config.py:854`, `mempalace/config.py:896`, `mempalace/config.py:946`, `mempalace/palace.py:392` |
| Graph/backups | topic tunnel minimum `1`; maximum retained backups `10` (`0` keeps all) | `mempalace/config.py:1321`, `mempalace/config.py:1347` |
| Hooks/writes | auto-save, silent save, desktop toast, hook/CLI routing (`direct|prefer|required`), legacy daemon toggle, mine timeout/PID file, verbose mode, project source dir | `mempalace/config.py:981`, `mempalace/config.py:1414`, `mempalace/config.py:1440`, `mempalace/config.py:1520`, `mempalace/hooks_cli.py:298`, `mempalace/hooks_cli.py:304`, `hooks/mempal_save_hook.sh:263` |
| MCP/server | stdio/http, host `127.0.0.1`, port `8765`, TLS cert/key, read-only, HTTP token, allowed hosts, insecure override, max SSE clients, idle hours, startup integrity MB gate, eager warmup, peer-writer/stale-library overrides, write-stall warning/exit, sync interval | `mempalace/mcp_server.py:259`, `mempalace/mcp_server.py:277`, `mempalace/mcp_server.py:282`, `mempalace/mcp_server.py:326`, `mempalace/mcp_server.py:346`, `mempalace/mcp_server.py:406`, `mempalace/mcp_server.py:7000`, `mempalace/mcp_server.py:7134`, `mempalace/mcp_server.py:7400`, `mempalace/mcp_server.py:8000` |
| Replication/transport | forward kill switch, HTTPS timeout, transport `https` (`meshguard` reserved), sync interval | `mempalace/hub_client.py:13`, `mempalace/transport.py:61`, `mempalace/transport.py:154`, `mempalace/mcp_server.py:8000` |
| Maintenance | dry-run/confirmation, repair mode, archive existing, strict truncation guard, max backups | `mempalace/cli.py:3515`, `mempalace/cli.py:3537`, `mempalace/cli.py:3579`, `mempalace/config.py:1347` |

### What tests exercise

The tests distinguish backend isolation, typed result shape, filter semantics, add/upsert/delete, embedder identity, and backend capability behavior (`mempalace/backends/base.py:108`, `tests/test_backend_conformance.py:1`). Mining tests cover scanning, chunking, deterministic IDs, mtime/content-hash idempotency, file caps, locking, stale purge, partial-write cleanup, and normalization regressions (`tests/test_miner.py:1`, `tests/test_convo_miner_unit.py:1`, `tests/test_convo_miner_size_cap.py:1`, `tests/test_miner_fts5_validation.py:1`). Search tests cover hybrid scoring, candidate union, filters, date windows, duplicate result suppression, line IDs, empty/corrupt backend fallbacks, and performance budgets (`tests/test_searcher.py:1`, `tests/test_hybrid_candidate_union.py:1`, `tests/test_search_distinct_closet_results.py:1`, `tests/benchmarks/test_recall_threshold.py:1`). KG tests cover temporal query and legacy date compatibility (`tests/test_knowledge_graph.py:179`). Regression tests explicitly target concurrency, repair safety, HNSW capacity, FTS5 integrity, encoding, schema migration, and MCP error surfaces (`tests/test_palace_locks.py:1`, `tests/test_hnsw_capacity.py:1`, `tests/test_repair.py:1`, `tests/test_mcp_server.py:1`).

They do not constitute evidence for Kivi’s permission tiers, exclusion policy, third-party retention barrier, observation/hypothesis lifecycle, suppression, or disclosure trace; those concepts do not exist in this schema.

## 1. Decision inventory

### 1. What is admitted?

**Question:** Should a memory system ingest every readable project/transcript artifact, only explicit saves, or only extracted durable propositions?

**Repo answer:** project mode admits a broad extension allowlist and skips known directories/filenames; conversation mode recognizes a smaller family of transcript extensions; “general” extraction can select marker-bearing spans rather than all exchanges (`mempalace/miner.py:110`, `mempalace/miner.py:138`, `mempalace/miner.py:181`, `mempalace/convo_miner.py:146`, `mempalace/convo_miner.py:1140`). This is partly configurable/pluggable through include lists and source adapters, but the built-in allow/deny taxonomy is hardcoded (`mempalace/sources/base.py:1`, `mempalace/cli.py:3279`). Placement suggests confidence in broad local capture, with extensibility focused on formats rather than retention policy.

**Assumptions:** local storage is cheap; false-positive retention is less costly than forgetting; files are primarily the user’s own work; extension/path rules approximate consent. Kivi explicitly makes non-retention of others a hard write-path rule (`kivi-semantic-memory-position.md:21`, `kivi-semantic-memory-position.md:47`, `kivi-semantic-memory-position.md:125`). That assumption does not hold: Kivi needs actor/ownership classification before persistence, pushing admission policy earlier than MemPalace’s format scanner.

### 2. Verbatim chunks or semantic beliefs?

**Question:** Is the durable unit a source-faithful passage, a normalized exchange, or a proposition with epistemic state?

**Repo answer:** the durable unit is primarily verbatim drawer text with flat location/provenance metadata; even its mission rejects summarization (`CLAUDE.md:5`, `mempalace/miner.py:1429`, `mempalace/convo_miner.py:723`). The general extractor does classify snippets into memory types, but still emits source text rather than Kivi’s belief schema (`mempalace/general_extractor.py:164`, `mempalace/convo_miner.py:1140`). Hardcoded core principle, while extraction mode is configurable.

**Assumptions:** retrieval of exact source passages is the product; epistemic interpretation happens downstream; source text is safe to retain. Kivi requires independent `type` and `tier`, evidence arrays, confirmation state, and status (`kivi-semantic-memory-position.md:70`, `kivi-semantic-memory-position.md:78`, `kivi-semantic-memory-position.md:99`). The shared verbatim/provenance preference holds, but Kivi’s load-bearing record is a revisable belief linked to sources, not the source chunk itself.

### 3. How large is a unit?

**Question:** Should boundaries follow characters, paragraphs, exchanges, semantic statements, or model token limits?

**Repo answer:** project chunks default to 800 characters with 100 overlap and a 50-character floor; conversations use exchange/paragraph boundaries but target 800 characters and a 30-character floor, falling back to groups of 25 lines after 20 newlines (`mempalace/config.py:274`, `mempalace/convo_miner.py:163`, `mempalace/convo_miner.py:298`, `mempalace/convo_miner.py:334`). Configurable for the three main size parameters; fallback shape is hardcoded. This reveals moderate confidence in the size but high confidence in boundary heuristics.

**Assumptions:** characters correlate sufficiently with embedding quality and retrieval granularity; overlap cost is tolerable; short content is low-value noise. Kivi’s types include atomic relations, preferences, and episodes (`kivi-semantic-memory-position.md:70`). Character chunks can be evidence containers, but cannot alone enforce atomic contradiction, promotion, or suppression; Kivi pushes toward separating evidence segmentation from belief segmentation.

### 4. What is discarded?

**Question:** What content must never be persisted, and should rejection be visible?

**Repo answer:** unreadable/oversized/non-regular files, ignored paths, unsupported formats, too-short chunks, detected transcript noise, NULs, and lone surrogates are skipped or sanitized (`mempalace/miner.py:181`, `mempalace/miner.py:204`, `mempalace/config.py:35`, `mempalace/config.py:47`, `mempalace/normalize.py:1`). Topic defaults explicitly include emotions and family (`mempalace/config.py:283`, `mempalace/config.py:293`). Mostly hardcoded, with path/cap overrides. No durable per-candidate rejection ledger was found: **unclear** whether all skip reasons are externally inspectable.

**Assumptions:** technical integrity/noise are the reasons to discard; semantic sensitivity is not. This directly conflicts with Kivi’s hard exclusions and “read, not kept” evidence (`kivi-semantic-memory-position.md:47`, `kivi-semantic-memory-position.md:123`). The difference pushes Kivi toward typed rejection events before any drawer/backend write.

### 5. How is identity represented?

**Question:** Are people/projects loose strings, canonical entities, or versioned identities with disambiguators?

**Repo answer:** drawers store semicolon-separated entity strings; structural extraction biases precision and keeps up to 24 tokens, while registry logic canonicalizes aliases and optionally enriches candidates (`mempalace/entities.py:3`, `mempalace/entities.py:31`, `mempalace/entities.py:42`, `mempalace/entity_registry.py:273`). The KG has entity IDs/types/properties (`mempalace/knowledge_graph.py:160`). Extraction/registry are partly pluggable by language and maps, but flat drawer metadata is hardcoded.

**Assumptions:** names are adequate retrieval facets; first-seen casing and string canonicalization are acceptable; cross-source identity uncertainty is secondary. Kivi makes entity relations a memory type and requires source-attributable correction (`kivi-semantic-memory-position.md:70`, `kivi-semantic-memory-position.md:23`). The direction is compatible, but Kivi raises disambiguation and ownership (“user” versus third party) into write-path correctness.

### 6. What happens on exact duplicate, near duplicate, or changed source?

**Question:** Reject, merge, append, overwrite by deterministic ID, or preserve every occurrence?

**Repo answer:** deterministic IDs plus `upsert` make replays overwrite equivalent logical chunks; mtime/content hash/schema markers skip unchanged sources; changed sources are purged then fully rebuilt (`mempalace/ids.py:1`, `mempalace/palace.py:1450`, `mempalace/convo_miner.py:657`, `mempalace/convo_miner.py:660`). Near-duplicate cleanup is a separate, dry-run-first operation with distance threshold 0.15 and minimum group size five (`mempalace/dedup.py:39`, `mempalace/dedup.py:98`). Exact behavior is hardcoded; cap and dedup threshold are caller-configurable, but automatic near-dedup is not integrated.

**Assumptions:** source files are the identity boundary; a changed export can be safely reconstructed; duplicates are maintenance noise, not contradictory beliefs. Kivi says evidence occurrences matter and “nothing self-promotes” (`kivi-semantic-memory-position.md:95`), so duplicate evidence cannot simply collapse without preserving provenance/count. Difference pushes Kivi to distinguish duplicate evidence, corroboration, and replacement.

### 7. What happens on contradiction?

**Question:** Keep both passages, replace old state, temporally close it, or ask for confirmation?

**Repo answer:** ordinary drawers coexist and search can retrieve contradictory passages. Source-file re-mine replaces only that source’s rows. The KG offers temporal triples and a supersede operation, but contradiction detection is not automatically connected to drawer ingestion (`mempalace/knowledge_graph.py:168`, `mempalace/knowledge_graph.py:337`, `mempalace/convo_miner.py:660`). Pluggable/manual only at the KG tool surface.

**Assumptions:** the caller interprets source/time context; contradictions across sources are acceptable. A still-open issue explicitly reports stale contradictory memory entering live context ([issue #224](https://github.com/MemPalace/mempalace/issues/224)). Kivi requires supersession with auditable history (`kivi-semantic-memory-position.md:240`), so this assumption fails and pushes contradiction handling into the belief store.

### 8. What is the source of truth?

**Question:** Are source files, SQLite records, or vector-index state authoritative after failure?

**Repo answer:** source files drive incremental ingest, but Chroma’s SQLite metadata/documents are treated as recoverable truth when the HNSW index diverges; exact backends make the SQL record directly searchable (`mempalace/palace.py:1450`, `mempalace/backends/chroma.py:904`, `mempalace/backends/sqlite_exact.py:1`, `mempalace/repair.py:611`). Backend is pluggable, but the default’s dual state creates hardcoded repair logic.

**Assumptions:** source files remain available or SQLite retains enough to rebuild; vector indexes are derived. Kivi requires source transcript IDs and reversible beliefs (`kivi-semantic-memory-position.md:99`), so the source/evidence log should remain authoritative; this precedent supports that direction but does not answer suppression and confirmation events.

### 9. How are concurrent writes handled?

**Question:** Permit multi-writer optimistic updates, serialize per source, serialize the palace, or route all writes through one owner?

**Repo answer:** per-source and palace locks guard mining; backend capabilities declare whether a single writer is required; daemon/hub routing centralizes writes where configured (`mempalace/palace.py:844`, `mempalace/palace.py:1301`, `mempalace/palace.py:431`, `mempalace/config.py:1440`). Routing is configurable, but Chroma’s single-writer reality is structural.

**Assumptions:** contention is occasional, blocking/defer is cheaper than corruption, and local processes share lock semantics. Kivi has no stated multi-agent/write-concurrency model. If replay and live writes overlap, this becomes a first-order question; MemPalace history shows per-file locking alone was insufficient ([issue #1202](https://github.com/MemPalace/mempalace/issues/1202)).

### 10. How is retrieval gathered?

**Question:** Vector-first, lexical-first, structured-first, or union all candidate sources before ranking?

**Repo answer:** default is vector candidates, over-fetched and hybrid re-ranked; optional `union` adds backend lexical candidates; filters scope wing/room/source and dates are post-filtered (`mempalace/searcher.py:1961`, `mempalace/searcher.py:2006`, `mempalace/searcher.py:2012`). Candidate strategy is configurable at the API, backend lexical capability is pluggable, but vector remains compatibility default. Placement reveals uncertainty: union is opt-in until cost is characterized (`mempalace/searcher.py:2016`).

**Assumptions:** embeddings usually contain the relevant item; a small rerank pool is enough; structured belief type/tier are absent. Kivi explicitly leaves retrieval mechanics open (`kivi-semantic-memory-position.md:267`). MemPalace supplies precedent, not a Kivi-specific answer.

### 11. How are results ordered?

**Question:** Semantic closeness, lexical match, recency, confidence, epistemic tier, or user permission?

**Repo answer:** score is `0.6 * vector_similarity + 0.4 * normalized_BM25`; exact score ties prefer newer `authored_at`; result distinctness uses source/chunk identity and closet enrichment (`mempalace/searcher.py:334`, `mempalace/searcher.py:369`, `mempalace/searcher.py:375`, `mempalace/searcher.py:1457`). Hardcoded weights and tie-break, configurable result count/distance.

**Assumptions:** relevance is mostly semantic/lexical; recency matters only on ties; confidence/tier do not exist. Kivi’s dial governs disclosure after full retrieval (`kivi-semantic-memory-position.md:155`), so Kivi needs ordering signals this repository never models. Whether tier affects retrieval rank or only disclosure remains an open Kivi question.

### 12. What is exposed to callers?

**Question:** Return text only, ranked evidence with provenance, or a disclosure decision and trace?

**Repo answer:** the programmatic envelope includes documents, metadata, distance and diagnostic fields; backend results have typed IDs/documents/metadata/distances/embeddings (`mempalace/searcher.py:1641`, `mempalace/backends/base.py:289`). MCP adds errors/hints and drawer IDs that can be round-tripped (`mempalace/searcher.py:1613`, `mempalace/searcher.py:1961`). This public shape is deliberate and compatibility-constrained; dict-style access remains as a migration shim (`mempalace/backends/base.py:265`).

**Assumptions:** exposing retrieval evidence is enough; the caller decides what to say. Kivi requires used/withheld/reason/source tracing and abstention traces (`kivi-semantic-memory-position.md:225`, `kivi-semantic-memory-position.md:228`). MemPalace provides evidence plumbing but no disclosure-policy result.

### 13. What happens on low confidence?

**Question:** Filter, lower-rank, warn, abstain, or ask the user?

**Repo answer:** `max_distance=0` means no threshold by default; callers may set a distance cutoff, and operational uncertainty returns diagnostic envelopes or lexical fallback (`mempalace/searcher.py:1969`, `mempalace/searcher.py:1998`, `mempalace/searcher.py:1613`, `mempalace/searcher.py:1745`). Configurable threshold, but abstention semantics are outside the system.

**Assumptions:** recall loss is worse than irrelevant retrieval; caller can interpret weak results. Kivi forbids plausible gap-filling and requires actionable abstention (`kivi-semantic-memory-position.md:205`). Difference pushes Kivi to represent epistemic absence separately from backend failure and low similarity.

### 14. What happens on storage or index failure?

**Question:** Fail closed, return partial lexical evidence, self-repair, quarantine, or continue degraded?

**Repo answer:** invalid/mismatched backend and embedder states fail loudly; unsafe HNSW can be quarantined or bypassed with SQLite/BM25; failed stale purge aborts instead of writing mixed schema rows (`mempalace/backends/base.py:192`, `mempalace/backends/chroma.py:455`, `mempalace/searcher.py:1745`, `mempalace/convo_miner.py:665`). The degradation path is hardcoded around default-backend failure modes.

**Assumptions:** lexical partial service is preferable to total outage, provided diagnostics are visible; silent mixed state is worse than delayed ingestion. Kivi’s failure cost includes incorrect disclosure and irreversible sensitive retention, which this repository never faces. The same fallback policy cannot be assumed for policy-check failure.

### 15. What changes over time?

**Question:** Do memories decay, get reinforced, supersede, expire, or remain forever?

**Repo answer:** drawer text persists until explicit deletion/re-mine/sync. Hallway/tunnel connection strength decays to a nonzero floor, potentiates on co-access, and gains stability after spaced access (`mempalace/dynamics.py:41`, `mempalace/dynamics.py:59`, `mempalace/dynamics.py:63`). KG triples have validity ranges and supersession (`mempalace/knowledge_graph.py:168`, `mempalace/knowledge_graph.py:337`). Mixed: hardcoded dynamics, manual temporal graph.

**Assumptions:** forgetting content violates the product promise; only navigation salience should decay. Kivi explicitly requires observations to decay, hypotheses to expire, and contradictions to supersede (`kivi-semantic-memory-position.md:239`, `kivi-semantic-memory-position.md:242`). The premise differs: Kivi’s belief status changes while evidence remains auditable.

### 16. What is idempotent and ordered?

**Question:** Is replay keyed by path, content, logical event, or sequence; and does order mean ingest time or authored time?

**Repo answer:** mine idempotency uses source path plus metadata completeness, schema version, mtime/content hash, extract mode, deterministic chunk identity, and complete `chunk_total` sets (`mempalace/palace.py:1450`, `mempalace/palace.py:1573`, `mempalace/convo_miner.py:693`). Search dates use `filed_at` ingest time, while tie-breaking can use `authored_at` (`mempalace/searcher.py:1987`, `mempalace/searcher.py:375`). Coordination replication adds origin sequence and HLC ordering (`mempalace/logstream.py:469`, `mempalace/logstream.py:504`).

**Assumptions:** a source can be rebuilt as a unit; mtime is a useful fast signal; authored and ingested time can coexist without a single temporal model. Kivi needs confirmation, correction, suppression, and promotion events to be replay-idempotent. Those event identities/orderings are not answered here.

### 17. Is privacy local deployment or semantic minimization?

**Question:** Is “data does not leave the device” sufficient, or must some locally seen data never become durable?

**Repo answer:** privacy is local-first transport/provider choice; core content is broadly retained, while external LLM use is opt-in (`CLAUDE.md:17`, `mempalace/config.py:1291`, `mempalace/llm_client.py:281`). Hardcoded architectural principle plus pluggable providers.

**Assumptions:** local persistence resolves the principal privacy risk. Kivi says local handling is not sufficient: third-party and sensitive content may enter context but not storage (`kivi-semantic-memory-position.md:22`, `kivi-semantic-memory-position.md:47`). This is a categorical mismatch, not a parameter difference.

## 2. Magic numbers

“10× down/up” describes directional failure, not a benchmark result unless explicitly cited. “Tuned” means code/history gives a target or incident; “guessed” means no local rationale, test calibration, or issue was found.

| Number | Decision frozen | Traceability | 10× lower / 10× higher | Assessment |
|---|---|---|---|---|
| 128 chars | maximum wing/room/KG value | validation comment only (`mempalace/config.py:32`, `mempalace/config.py:88`) | 13 rejects ordinary names/context; 1,280 expands metadata/path abuse surface | guessed |
| 100,000 chars | MCP drawer content limit | no issue found (`mempalace/config.py:215`) | 10k rejects long saves; 1m increases request/storage/embedding exposure | guessed |
| 800 / 100 / 50 chars | project chunk, overlap, minimum | introduced together in `b1d75b30`; no corpus rationale found (`mempalace/config.py:274`) | 80/10/5 fragments context and explodes rows; 8k/1k/500 blurs facts and drops short memories | guessed/compatibility-stabilized |
| 30 chars | conversation minimum | earliest history; config deliberately preserves difference (`mempalace/convo_miner.py:163`, `mempalace/config.py:1548`) | 3 retains noise; 300 drops concise exchanges | deliberate compatibility, original value unclear |
| 25 lines / 20 newlines | conversation fallback grouping/trigger | `3cac26fc`; comments name purpose (`mempalace/convo_miner.py:165`) | 2/2 fragments logs; 250/200 creates huge fallback chunks | heuristic, weakly tuned |
| 1,000 rows | drawer upsert batch | `fbd09047` (`mempalace/miner.py:203`, `mempalace/convo_miner.py:167`) | 100 more calls/flush pressure; 10k memory spikes and larger partial failures | incident-shaped, exact value unclear |
| 500 MB | maximum file | comments only (`mempalace/miner.py:204`) | 50 MB rejects long exports; 5 GB risks memory/runtime stalls | safety guess |
| 50,000 chunks/file | admission cap | raised from 500 after issues #1296/#1455; rationale documents two orders of magnitude (`mempalace/miner.py:205`, `mempalace/miner.py:218`) | 5k rejects books/large corpora; 500k weakens allocation safety | tuned from incidents |
| 5,000 chars / 25 entities | entity scan window/metadata cap | no rationale beyond comments (`mempalace/miner.py:782`) | 500 misses late entities / 2 loses facets; 50k costs more / 250 bloats flat metadata | guessed |
| 24 entities, 2–64 chars | structural entity limits | precision-oriented comments, no empirical source (`mempalace/entities.py:31`, `mempalace/entities.py:42`) | 2 entities loses recall; 240 adds noise; 6-char max rejects identifiers; 640 admits giant tokens | deliberate heuristic |
| BM25 `k1=1.5`, `b=.75` | term saturation/length normalization | conventional range cited in code, introduced `32d7f437` (`mempalace/searcher.py:166`, `mempalace/searcher.py:182`) | `.15/.075` nearly removes TF/length effects; `15/7.5` makes pathological normalization | borrowed standard, not repo-tuned |
| `.6/.4` | vector/BM25 blend | introduced `32d7f437`; no evaluation note (`mempalace/searcher.py:334`) | `.06/.04` together only rescales ordering, but changing one alone makes the other dominate; `6/4` also only rescales | guessed ratio; only relative values matter |
| 3× / 15× / cap 500 | normal/date-window overfetch | commit `5036e3c`; comment explains post-filter starvation (`mempalace/searcher.py:1250`) | `.3×/1.5×/50` cannot fill results; `30×/150×/5000` increases query/hydration cost | deliberately incident-tuned |
| 4× | closet enrichment pool | commit `ad78f63`; tied to distinct-passage fix (`mempalace/searcher.py:1270`) | below 1× underfills; 40× increases reads/rerank cost | tuned, evidence limited |
| 10,000 chars | maximum source hydration | same change as closet enrichment (`mempalace/searcher.py:1271`) | 1k truncates context; 100k increases latency/memory | heuristic |
| `n_results=5` | public search default | repeated CLI/API default (`mempalace/searcher.py:1969`, `mempalace/cli.py:3409`) | integer floor makes 0 unusable; 50 increases context/noise/cost | product guess |
| distance `0` disabled; “useful” `.3–1.0` | relevance cutoff | API docs only (`mempalace/searcher.py:1998`) | threshold near .03 rejects paraphrases; near 3 admits all cosine results | explicitly caller-tunable, default favors recall |
| neighbor radius `1` | adjacent chunk expansion | no rationale found (`mempalace/searcher.py:450`) | 0 loses split context; 10 drags unrelated nearby content | guessed |
| dedup distance `.15`, group min 5 | near-duplicate cleanup | introduced `71e8f2d`; no issue rationale found (`mempalace/dedup.py:39`) | `.015` only near-identical; `1.5` merges unrelated cosine items; min 1 makes every source eligible; 50 misses small repeated sets | guessed and risky |
| HNSW batch 100 / sync 1,000 / threads 1 | index persistence/write serialization | reset to upstream defaults in `72bbb0a`; history reversed earlier large custom thresholds (`mempalace/backends/chroma.py:200`, `mempalace/backends/chroma.py:206`, `mempalace/backends/chroma.py:227`) | 10/100 flushes frequently; 1k/10k widens unflushed tail and batch memory | deliberate reversal; upstream-derived |
| link:data ratio 10 | corrupt HNSW heuristic | no derivation found (`mempalace/backends/chroma.py:55`) | 1 causes false positives; 100 misses severe bloat | guessed guard |
| 1,024 bytes | meaningful HNSW data floor | comment only (`mempalace/backends/chroma.py:258`) | 102 risks interpreting headers; 10k ignores small broken indexes | guessed guard |
| 2,000 rows / 10% / 300 s | HNSW divergence tolerance/grace | separate incident commits; issue #1816 challenged the tolerance (`mempalace/backends/chroma.py:713`) | 200/1%/30s causes more fallback; 20k/100%/3000s allows stale/unsafe vector reads much longer | incident-tuned but contested |
| cache 32 entries / 10 s | HNSW capacity cache | no rationale found (`mempalace/backends/chroma.py:815`, `mempalace/backends/chroma.py:823`) | 3/1s more probing; 320/100s stale safety verdicts and memory | guessed |
| stale quarantine 300 s | HNSW directory age | no derivation found (`mempalace/backends/chroma.py:455`) | 30s may quarantine active writes; 3000s delays recovery | guessed safety interval |
| 384 dimensions / 2,048 tokens / batch 32 | EmbeddingGemma truncation/window/batch | model constraint plus issue-driven batch configurability (`mempalace/embedding.py:270`, `mempalace/embedding.py:271`, `mempalace/embedding.py:283`, `mempalace/config.py:1218`) | 38 dims/205 tokens damages semantic signal; 3,840 dims impossible for model / 20k exceeds model; batch 3 slower / 320 OOM-prone | model-derived except batch, which is incident-tuned |
| API batch 64 / timeout 120 s | remote embedding request | no local derivation found (`mempalace/embedding.py:588`) | 6/12s more calls/timeouts; 640/1200s larger failures and long hangs | guessed |
| LLM refine 25 candidates / 3 context lines / 240 chars | local classifier prompt budget | comment says tuned for 4B local models (`mempalace/llm_refine.py:31`) | 2/0/24 starves context and adds calls; 250/30/2400 overflows small-model context/latency | claimed tuned; benchmark not found |
| strength floor `.05`, max `5`, increments `.05/.1`, spaced interval 1 h | hallway/tunnel decay/reinforcement | all introduced in `a2ba1ccb`; comments state behavioral targets (`mempalace/dynamics.py:41`) | lower floor approximates forgetting; higher floor prevents useful fading; 10× max/increments changes dominance in a few accesses; .1h/10h changes what counts as spaced | deliberately modeled, empirical basis unclear |
| closet 1,500 chars / extract window 5,000 | compact pointer grouping/entity scan | comments only (`mempalace/palace.py:566`) | 150/500 creates many lines and misses entities; 15k/50k creates unwieldy index entries/cost | guessed |
| stale lock reap 3,600 s | orphan lock eligibility | default only (`mempalace/palace.py:1030`) | 6 min risks active long mines; 10 h prolongs blockage | guessed safety compromise |
| 10 backups | retention | explicit disk-growth rationale, configurable (`mempalace/config.py:1347`) | 1 reduces rollback history; 100 consumes large disk | operationally reasoned, not workload-tuned |
| tunnel topic minimum 1 | graph edge creation | config docs explain alternative (`mempalace/config.py:1321`) | cannot go 10× down meaningfully; 10 shared topics produces sparse graph | explicit product default, guessed |
| Chroma extraction 10,000 | repair truncation suspicion | inherited Chroma default (`mempalace/repair.py:611`) | 1k aborts more legitimate cases; 100k can silently truncate larger palaces if dependency changes | framework-inherited guard |
| HTTP host/port `127.0.0.1:8765` | local service exposure | CLI defaults (`mempalace/cli.py:3634`, `mempalace/cli.py:3637`) | port arithmetic has no semantic 10× interpretation; broader host changes threat boundary | conventional/local-first default |
| sync 15 s | replica sync interval | env fallback only (`mempalace/mcp_server.py:8000`) | 1.5s more network/lock load; 150s staler replicas | guessed |
| event list 50; wait 60 s; watch 300 s | coordination paging/polling | CLI defaults (`mempalace/cli.py:3779`, `mempalace/cli.py:3786`, `mempalace/cli.py:3869`) | lower misses/busy-polls; higher increases latency/payload/blocked calls | guessed operational defaults |

No generation temperature was found in the core memory path. That absence is itself a decision: built-in extraction is deterministic-marker based unless optional LLM refinement is invoked (`mempalace/general_extractor.py:164`, `mempalace/llm_refine.py:31`).

## 3. What the history says

### High-value reversals and rewrites

These are the highest-value signals because they expose answers that stopped working under real load.

1. **HNSW write tuning was reversed.** An incident proposed very large batch/sync thresholds after catastrophic index bloat ([issue #344](https://github.com/MemPalace/mempalace/issues/344)); later commit `72bbb0a` explicitly restored Chroma’s own `100/1000` defaults because the assumed Python persistence path did not apply to the Rust bindings (`mempalace/backends/chroma.py:200`, `mempalace/backends/chroma.py:206`). This is a direct reversal: “tune the index aggressively” became “inherit upstream defaults and serialize writes.”

2. **Seen-source idempotency became completeness-aware replacement.** Duplicate conversation exports produced nearly all drawers again ([issue #2044](https://github.com/MemPalace/mempalace/issues/2044)); PR/merge `31bc2f8` and later `759b8f1` added deduped logical identities, `chunk_total`, and cleanup after partial batches (`mempalace/convo_miner.py:693`, `mempalace/convo_miner.py:758`). The original “source seen” answer stopped working once exports were mutable and multi-batch.

3. **Read/write-anywhere Chroma usage became guarded single-writer routing.** Concurrent stop hooks and MCP clients repeatedly corrupted indexes ([issue #1202](https://github.com/MemPalace/mempalace/issues/1202), [issue #1581](https://github.com/MemPalace/mempalace/issues/1581)). Locks, peer-writer refusal, stale-lock reaping, and hub/daemon routing accumulated later (`mempalace/palace.py:1030`, `mempalace/palace.py:1301`, `mempalace/mcp_server.py:424`). This is not an original abstraction; it is evidence the default backend’s concurrency model was discovered operationally.

4. **“Status/count is harmless” became preflight-before-open.** Native HNSW reads could segfault even on `count()`, so commit `8b5e372` audited count sites and search gained an SQLite-only fallback (`mempalace/searcher.py:692`, `mempalace/searcher.py:2002`). Issue #1816 reports daily divergence and challenges the `max(2000, 10%)` tolerance ([issue #1816](https://github.com/MemPalace/mempalace/issues/1816)). The safety boundary moved above the backend API.

5. **Repair-as-rebuild became repair-as-forensics/fail-closed.** Repeated repairs corrupted FTS5 ([issue #1517](https://github.com/MemPalace/mempalace/issues/1517)); corrupt HNSW could make repair itself crash or report success for an unloadable segment ([issue #1589](https://github.com/MemPalace/mempalace/issues/1589)). Current code has quick checks, truncation guards, direct-SQL extraction, quarantine, archive, and dry-run paths (`mempalace/repair.py:611`, `mempalace/backends/chroma.py:455`). The abstraction “backend can repair itself” proved incomplete.

6. **Vector-only candidate gathering became optionally unioned lexical+vector retrieval.** PR merge `a6725e9` is unrelated, but `98e6dfc`/PR #1964 and `af7bca7` exposed candidate union after missed lexical matches; the code still defaults to vector because cost is uncharacterized (`mempalace/searcher.py:2006`, `mempalace/searcher.py:2016`). This is an abstraction added after vector-first precedent stopped achieving recall in some data shapes.

7. **Global hallway/tunnel files became palace-scoped.** The config comment states that hardcoded `~/.mempalace/hallways.json` caused multiple palaces to silently share state (`mempalace/config.py:822`). Tests preserve warnings rather than auto-migrating ambiguous legacy files (`tests/test_palace_graph_tunnels.py:552`). This distinguishes a corrected accident from deliberate global sharing.

8. **Untyped backend dictionaries became typed contracts with compatibility shims.** RFC 001 introduced `QueryResult`, `GetResult`, capabilities, palace isolation, and embedder identity, but dict access remains for old callers (`mempalace/backends/base.py:108`, `mempalace/backends/base.py:265`). This later abstraction implies the original Chroma-shaped interface no longer worked across backends.

### Recurring bug families

- **Index divergence/corruption:** #344, #823, #1202, #1266, #1581, #1589, #1599, and #1816 describe bloat, stale vector state, concurrent-writer corruption, broken metadata, FTS5 corruption, and native crashes. Current guards are responses, not proof the class is eliminated (`mempalace/backends/chroma.py:713`, `mempalace/backends/chroma.py:904`).
- **Duplicate/stale drawers:** #2044, commits `3a97996`, `3da1d79`, `759b8f1`, and `f92095e` repeatedly adjust purge, logical IDs, partial batches, and derived closets (`mempalace/convo_miner.py:660`, `mempalace/mcp_server.py:3238`).
- **Compatibility-shaped correctness:** legacy missing `extract_mode`, old drawer IDs, old date forms, stale hub capabilities, and old result dictionaries have dedicated branches/tests (`mempalace/palace.py:1427`, `mempalace/config.py:204`, `mempalace/backends/base.py:265`). This is backwards compatibility, not evidence those shapes are preferred.
- **Encoding/input integrity:** NUL and lone-surrogate defenses were added after datastore corruption/crashes, explicitly citing #1235 (`mempalace/config.py:35`, `mempalace/config.py:47`).

### TODOs and admitted shortcuts

- Typed backend result dict access is explicitly transitional and scheduled for removal (`mempalace/backends/base.py:265`).
- Inner-product distance mapping is explicitly provisional because no in-tree backend exercises it (`mempalace/searcher.py:238`).
- `meshguard` transport is reserved but unimplemented; selecting it fails loudly (`mempalace/transport.py:154`, `mempalace/transport.py:166`).
- The config initializer intentionally preserves inconsistent setter behavior for backwards compatibility, including failure behavior inherited from `develop` (`mempalace/config.py:1137`, `mempalace/config.py:1253`).
- LLM refinement says 25 candidates is tuned for 4B local models, but no benchmark or issue trail was found for the exact value (`mempalace/llm_refine.py:31`).
- Search applies date constraints after retrieval because Chroma rejects string range operands, then widens a capped pool; the response admits possible truncation (`mempalace/searcher.py:1253`, `mempalace/searcher.py:1262`). This is an explicit datastore workaround.
- Missing embedder dimension `0` is treated as “unknown,” allowing compatibility checks to proceed without full model load (`mempalace/backends/base.py:146`, `mempalace/backends/base.py:213`). This is a deliberate uncertainty escape hatch.

## 4. Unexamined defaults

These choices show no nearby comment, configuration, discriminating test, or explored alternative. “Nobody tried” means no evidence was found, not proof no one ever considered it.

| Default | Alternative not evidenced | Classification and Kivi relevance |
|---|---|---|
| Cosine distance for every historical/in-tree backend (`mempalace/searcher.py:258`) | learned sparse+dense fusion, dot product with calibrated scores, per-type metrics | framework inheritance; Kivi’s type/tier may have different retrieval geometry |
| Lowercased `\w{2,}` tokens (`mempalace/searcher.py:50`, `mempalace/searcher.py:94`) | language-specific segmentation, character n-grams, exact identifiers | implementation default; weak for scripts without whitespace and one-character symbols |
| Flat semicolon-separated entities metadata (`mempalace/entities.py:10`, `mempalace/entities.py:69`) | typed arrays/edge table with ownership and evidence | accidental storage convenience; incompatible with Kivi’s actor boundary |
| First-seen surface form survives case-insensitive dedup (`mempalace/entities.py:45`) | canonical later correction or source-authoritative spelling | deterministic default; Kivi needs correction semantics |
| Missing authored dates sort oldest in score ties (`mempalace/searcher.py:375`) | missing-last, ingest-time fallback, explicit uncertainty | unexamined ranking default |
| BM25 normalized by maximum, not min-max despite prose saying min-max (`mempalace/searcher.py:349`, `mempalace/searcher.py:366`) | subtract minimum then scale; calibrated score fusion | likely implementation/documentation mismatch; tests may lock ordering without validating the claim |
| `max_distance=0` disables all relevance filtering (`mempalace/searcher.py:1969`) | abstain below calibrated confidence | deliberate recall bias, but no Kivi evidence |
| Newer wins only exact score ties (`mempalace/searcher.py:375`) | explicit recency decay or temporal intent model | unexamined compromise |
| Changed files are purge-and-rebuild units (`mempalace/convo_miner.py:660`) | event-level diff with tombstones | incident-hardened but source-centric; Kivi needs durable correction/suppression events |
| Emotional/family topic wings ship by default (`mempalace/config.py:283`) | no sensitive taxonomy, or excluded-by-default policy | deliberate MemPalace worldview; directly opposite Kivi’s boundary |
| English entity detection default (`mempalace/config.py:1114`) | language detection or language-neutral extraction only | compatibility default; can systematically alter who/what gets recognized |
| Local path and collection name are global user defaults (`mempalace/config.py:226`) | per-application/per-person store | convenience default; Kivi’s person boundary needs explicit tenancy |
| Optional API key can be stored in JSON config (`mempalace/config.py:1311`) | credential store/env-only secret | inherited config convenience; not deliberated here |
| Unknown embedding model falls back to MiniLM (`mempalace/config.py:1247`) | fail closed | backwards-compatible convenience; can silently change representation |
| Broad source capture treats format/path as the consent proxy (`mempalace/miner.py:138`) | per-speaker/per-field retention labels | core philosophical default; Kivi cannot inherit it |

## 5. Questions this repo never faced

Derived directly from Kivi’s position; these are absent from MemPalace’s persisted schema and tests.

1. What representation proves that third-party content was available to generation but structurally unreachable by persistence? Kivi demands separate paths (`kivi-semantic-memory-position.md:22`, `kivi-semantic-memory-position.md:125`).
2. Who is the subject and who is the speaker of each candidate, and what happens when either is uncertain?
3. Can a work-level fact about a third party be retained without copying the third party’s personal statement, and how is that derivation attributed?
4. What deterministic exclusion classifier enforces health, emotion, relationship, faith, politics, finance, competence, and character boundaries before storage (`kivi-semantic-memory-position.md:47`)?
5. What is logged about a dropped candidate without the rejection log itself retaining the forbidden content?
6. How are `type` and `tier` orthogonal in schema, and which operations are valid for every cell (`kivi-semantic-memory-position.md:70`, `kivi-semantic-memory-position.md:78`)?
7. What exact event counts as user confirmation, especially during ordinary conversational agreement?
8. How is silence represented so it cannot accidentally promote a hypothesis (`kivi-semantic-memory-position.md:223`)?
9. How are hypotheses stored grammatically as questions and prevented from being consumed as facts?
10. How does “nothing self-promotes” coexist with evidence accumulation and confidence scoring (`kivi-semantic-memory-position.md:95`)?
11. What suppression record prevents a removed/demoted belief from being re-derived from unchanged transcripts (`kivi-semantic-memory-position.md:241`)?
12. Does suppression target a normalized proposition, evidence set, extraction rule, or semantic neighborhood?
13. How are corrections and supersessions replayed when transcripts are reprocessed out of order?
14. What decays: evidence weight, observation visibility, confidence, or the record itself; and what remains auditable?
15. What event refreshes `last_confirmed_at`, and can observation alone refresh it?
16. How are weekly confirmation prompts budgeted by value without inferring sensitive psychological importance?
17. How can Anbu retrieve everything yet prove observations/hypotheses were withheld from generation (`kivi-semantic-memory-position.md:155`)?
18. What data boundary makes dictation structurally unable to load observation/hypothesis tables (`kivi-semantic-memory-position.md:199`)?
19. Is Daari’s one-request permission an execution capability, a query scope, or a nonpersistent token, and how is it prevented from leaking to later requests?
20. What is an abstention threshold when structured facts, evidence freshness, contradiction, and semantic retrieval each have different uncertainty?
21. What trace is safe to show when a withheld memory is itself sensitive?
22. Who may edit a memory about another person, and whose correction is authoritative?
23. When a project fact and personal preference conflict, which type owns the action?
24. How is “durable enough to avoid re-explanation” evaluated without learning a psychological profile (`kivi-semantic-memory-position.md:59`)?
25. How are absence claims evaluated—“nothing from Arun”—when ingestion coverage itself may be incomplete?
26. What does deletion mean across belief rows, evidence transcripts, embeddings, indexes, backups, logs, and replicas?
27. Can provenance remain after “Forget,” or does auditability conflict with erasure?
28. How are permission-mode changes themselves audited without turning UI behavior into sensitive memory?
29. How are observed patterns tested for counterexamples, not just repeated positive instances?
30. What corpus labels distinguish “not retained because third-party” from “not extracted,” “excluded sensitive,” “duplicate,” and “low confidence” (`kivi-semantic-memory-position.md:265`)?

## 6. What the tests do not cover

These are decisions for which a materially different answer could still pass the current suite.

- **Retention ethics:** replacing broad capture with a sensitive/third-party exclusion wall—or retaining everything—would not violate a test for Kivi’s promised categories because no such tests exist. Existing tests focus on format/noise/integrity (`tests/test_normalize.py:1452`, `tests/test_non_regular_file_guards.py:1`).
- **Epistemic tiers:** stated/observed/hypothesized, promotion by confirmation, and non-promotion by repetition are absent. The current metadata can change without any suite assertion about these semantics.
- **Disclosure versus retrieval:** no test retrieves all tiers and proves one is withheld by a permission mode while leaving an auditable trace. Kivi explicitly requires this (`kivi-semantic-memory-position.md:155`, `kivi-semantic-memory-position.md:283`).
- **Dictation isolation:** no schema-level test proves ordinary dictation cannot access observations/hypotheses (`kivi-semantic-memory-position.md:199`, `kivi-semantic-memory-position.md:287`).
- **Suppression after correction:** deletion and source purge are tested, but “do not re-derive this belief from the same evidence” is not. A different suppression design—or none—passes.
- **Contradiction semantics:** temporal KG tests distinguish date interval behavior, not automatic contradiction discovery, confidence arbitration, or belief supersession across drawer sources (`tests/test_knowledge_graph.py:179`).
- **Abstention quality:** empty/error envelopes are tested, but not whether the system distinguishes absent evidence from incomplete ingestion or low-confidence retrieval and explains what it searched.
- **Score calibration:** ordering tests can validate relative results while `.6/.4`, `k1`, `b`, pool multipliers, and distance thresholds remain uncalibrated to truth. Different values that preserve fixtures would pass (`mempalace/searcher.py:334`).
- **Semantic chunk boundaries:** tests verify deterministic/bounded chunks, not whether a preference, episode, or contradiction stays atomic. Many chunk-size answers would pass.
- **Near-duplicate meaning:** dedup tests can assert a threshold operation, but do not distinguish duplicate statement from independent corroboration or repeated evidence. Kivi’s `evidence_count` makes that distinction load-bearing (`kivi-semantic-memory-position.md:99`).
- **Actor ownership:** entity tests identify names/tokens, not whether content belongs to the user or a third party.
- **Sensitive leakage through metadata:** sanitization tests cover malformed characters/NULs; they do not assert excluded content is absent from embeddings, entity metadata, logs, rejection reasons, backups, or closets.
- **Time semantics:** date tests cover parsing and `[since,before)` filtering, not observation decay, hypothesis expiry, confirmation freshness, or out-of-order correction events.
- **Erasure closure:** individual backend deletes and sync behavior are tested, but there is no end-to-end proof that forget removes every derivative, backup, index entry, graph edge, and replica.
- **Fallback truthfulness:** vector-to-BM25 degradation is tested operationally; no test asks whether an answer generated from degraded retrieval must disclose reduced coverage.
- **Longitudinal user change:** the suite has no corpus where an old behavior stops, a new one begins, and the system must avoid presenting the old pattern as identity.
- **Permission prompt budget:** Kivi leaves the cap open and MemPalace has no analogous cost model, so any number—including unlimited—has no precedent or evidence (`kivi-semantic-memory-position.md:267`).

## Closing boundary

MemPalace is strongest evidence for questions about verbatim evidence, provenance-bearing retrieval, incremental replay, backend failure, and the hazards of mutable sources plus derived indexes. It is weakest as evidence for Kivi’s defining questions: semantic minimization, actor ownership, epistemic tiering, confirmation, suppression, contradiction, disclosure permissions, and abstention. On those points the repository offers adjacent machinery, not a tested answer.

## Appendix: complete runtime environment-variable inventory

This appendix separates actual operator inputs from shell-local variables such as `MEMPAL_PYTHON_BIN` and parse markers. It is the complete set found in the Python runtime and supported hook scripts within the reviewed scope.

- **Palace/backend:** `MEMPALACE_PALACE_PATH`, legacy `MEMPAL_PALACE_PATH`, `MEMPALACE_BACKEND`, and process-stamped `MEMPALACE_BACKEND_EXPLICIT` (`mempalace/config.py:808`, `mempalace/config.py:842`, `mempalace/palace.py:65`).
- **Qdrant:** `MEMPALACE_QDRANT_URL`, `_API_KEY`, `_NAMESPACE`, `_TIMEOUT` (`mempalace/config.py:859`, `mempalace/config.py:869`, `mempalace/config.py:878`, `mempalace/config.py:887`).
- **Milvus:** `MEMPALACE_MILVUS_URI`, `_TOKEN`, `_DB_NAME`, `_NAMESPACE`, `_CONSISTENCY_LEVEL` (`mempalace/config.py:903`, `mempalace/config.py:912`, `mempalace/config.py:921`, `mempalace/config.py:930`, `mempalace/config.py:939`).
- **pgvector:** `MEMPALACE_PGVECTOR_DSN`, `_NAMESPACE`; tests additionally use `MEMPALACE_PGVECTOR_LIVE_URL` to opt into a live server (`mempalace/config.py:951`, `mempalace/config.py:963`, `mempalace/backends/pgvector.py:22`).
- **Embedding:** `MEMPALACE_EMBEDDING_MODEL`, `_DEVICE`, `_THREADS`, `_EMBEDDINGGEMMA_BATCH_SIZE`, `_API_URL`, `_API_MODEL`, `_API_KEY`; optional LLM providers also read `OPENAI_API_KEY` and `ANTHROPIC_API_KEY` (`mempalace/config.py:1157`, `mempalace/config.py:1181`, `mempalace/config.py:1206`, `mempalace/config.py:1233`, `mempalace/config.py:1299`, `mempalace/config.py:1308`, `mempalace/config.py:1318`, `mempalace/llm_client.py:298`, `mempalace/llm_client.py:384`).
- **Language/entity graph:** `MEMPALACE_LANG`, legacy `MEMPAL_LANG`, `MEMPALACE_ENTITY_LANGUAGES`, legacy `MEMPAL_ENTITY_LANGUAGES`, `MEMPALACE_TOPIC_TUNNEL_MIN_COUNT` (`mempalace/config.py:1380`, `mempalace/config.py:1121`, `mempalace/config.py:1331`).
- **Mining/source:** `MEMPALACE_MAX_CHUNKS_PER_FILE`, `MEMPALACE_MINE_PID_FILE`, `MEMPALACE_MINE_TIMEOUT_HOURS`, `MEMPALACE_SOURCE_DIR`, `MEMPALACE_PROJECT_FILES`, and hook source `MEMPAL_DIR` (`mempalace/miner.py:248`, `mempalace/hooks_cli.py:298`, `mempalace/hooks_cli.py:304`, `mempalace/split_mega_files.py:33`, `mempalace/cli.py:50`, `mempalace/hooks_cli.py:269`).
- **Hook behavior/routing:** `MEMPALACE_HOOKS_AUTO_SAVE`, `MEMPALACE_HOOK_WRITE_ROUTING`, `MEMPALACE_CLI_WRITE_ROUTING`, `MEMPALACE_WRITE_ROUTING`, legacy `MEMPALACE_HOOKS_DAEMON`, `MEMPALACE_PYTHON`/`MEMPAL_PYTHON`, `MEMPAL_DISABLE_HOOK`, `MEMPAL_VERBOSE`, `MEMPAL_SAVE_INTERVAL`, `MEMPAL_STATE_DIR`, and `MEMPAL_STATE_TTL_DAYS` (`mempalace/config.py:987`, `mempalace/config.py:1442`, `mempalace/config.py:1462`, `mempalace/config.py:1470`, `mempalace/hooks_cli.py:79`, `hooks/mempal_save_hook.sh:279`, `hooks/cursor/lib/common.sh:19`, `hooks/cursor/lib/common.sh:352`). Harness-specific log/silent variables are `MEMPAL_CURSOR_LOG`, `MEMPAL_CURSOR_SILENT`, and `MEMPAL_AGY_LOG` (`hooks/cursor/lib/common.sh:37`, `hooks/cursor/mempal_save_hook_cursor.sh:34`, `hooks/antigravity/lib/common.sh:48`).
- **Daemon:** `MEMPALACE_DAEMON_STATE_ROOT`, `_LOCK_BACKOFF_SECONDS`, `_RETENTION_DAYS` (`mempalace/daemon.py:40`, `mempalace/daemon.py:70`, `mempalace/daemon.py:87`).
- **MCP lifecycle/safety:** `MEMPALACE_LOG_FILE`, `MEMPALACE_MCP_READ_ONLY`, `_IDLE_HOURS`, `_ALLOW_PEER_WRITER`, `_ALLOW_STALE_LIBRARY`, `_WRITE_STALL_WARN_SECS`, `_WRITE_STALL_EXIT_SECS`, `MEMPALACE_STARTUP_INTEGRITY_MAX_MB`, and `MEMPALACE_EAGER_WARMUP` (`mempalace/mcp_server.py:196`, `mempalace/mcp_server.py:329`, `mempalace/mcp_server.py:349`, `mempalace/mcp_server.py:424`, `mempalace/mcp_server.py:608`, `mempalace/mcp_server.py:7134`, `mempalace/mcp_server.py:7136`, `mempalace/mcp_server.py:408`, `mempalace/mcp_server.py:7059`).
- **MCP HTTP:** `MEMPALACE_MCP_HTTP_TOKEN`, `_HTTP_ALLOW_INSECURE_NO_TOKEN`, `_TLS_CERT`, `_TLS_KEY`, `_EXTRA_ALLOWED_HOSTS`, and `MEMPALACE_SSE_MAX_CLIENTS` (`mempalace/mcp_server.py:8192`, `mempalace/mcp_server.py:7411`, `mempalace/mcp_server.py:7422`, `mempalace/mcp_server.py:7424`, `mempalace/mcp_server.py:7450`, `mempalace/mcp_server.py:7400`).
- **Hub/sync/transport:** `MEMPALACE_HUB_FORWARD`, `MEMPALACE_SYNC_INTERVAL`, `MEMPALACE_SYNC_HTTP_TIMEOUT`, and `MEMPALACE_TRANSPORT` (`mempalace/hub_client.py:13`, `mempalace/mcp_server.py:8000`, `mempalace/transport.py:64`, `mempalace/transport.py:161`).
- **Retention:** `MEMPALACE_MAX_BACKUPS` (`mempalace/config.py:1366`).
- **Hermes adapter only:** `MEMPALACE_IDENTITY_PATH` and `MEMPALACE_WING` (`mempalace/integrations/hermes/__init__.py:1178`).

Config-file keys mirror most of the above and additionally include `collection_name`, `people_map`, `topic_wings`, `hall_keywords`, `chunk_size`, `chunk_overlap`, `min_chunk_size`, `hooks.auto_save`, `hooks.silent_save`, `hooks.desktop_toast`, `write_routing.{default,hooks,cli}`, `embedding_*`, `lang`, `entity_languages`, `topic_tunnel_min_count`, and `max_backups` (`mempalace/config.py:621`, `mempalace/config.py:970`, `mempalace/config.py:981`, `mempalace/config.py:994`, `mempalace/config.py:1077`, `mempalace/config.py:1414`, `mempalace/config.py:1456`).

## Sources

1. MemPalace repository at local commit `f9297a2`; file-and-line citations throughout.
2. MemPalace, “[HNSW index bloat](https://github.com/MemPalace/mempalace/issues/344),” issue #344.
3. MemPalace, “[Automatic deduplication on add_drawer](https://github.com/MemPalace/mempalace/issues/464),” issue #464.
4. MemPalace, “[HNSW persistence vs add_drawer](https://github.com/MemPalace/mempalace/issues/823),” issue #823.
5. MemPalace, “[Concurrent stop-hook mining](https://github.com/MemPalace/mempalace/issues/1202),” issue #1202.
6. MemPalace, “[HNSW pickle corruption](https://github.com/MemPalace/mempalace/issues/1266),” issue #1266.
7. MemPalace, “[FTS5 corruption after repair](https://github.com/MemPalace/mempalace/issues/1517),” issue #1517.
8. MemPalace, “[Concurrent Chroma clients corrupt HNSW](https://github.com/MemPalace/mempalace/issues/1581),” issue #1581.
9. MemPalace, “[Repair produces unloadable HNSW](https://github.com/MemPalace/mempalace/issues/1589),” issue #1589.
10. MemPalace, “[Recurring FTS5 corruption](https://github.com/MemPalace/mempalace/issues/1599),” issue #1599.
11. MemPalace, “[Daily HNSW re-divergence](https://github.com/MemPalace/mempalace/issues/1816),” issue #1816.
12. MemPalace, “[Duplicate conversation drawers](https://github.com/MemPalace/mempalace/issues/2044),” issue #2044.
13. MemPalace, “[Stale contradictory drawer retrieval](https://github.com/MemPalace/mempalace/issues/224),” issue #224.
