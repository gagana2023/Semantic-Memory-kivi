# Memvid Decision-Space Analysis for Kivi

This report extracts the questions and assumptions embedded in Memvid rather than treating its current implementation as a recommendation. “Fit” means fit with the product constraints in [`kivi-semantic-memory-position.md`](./kivi-semantic-memory-position.md), not an architectural recommendation.

## Orientation

### Scope read

I read:

- The complete Kivi position document.
- Public API exports and lifecycle behavior in [`src/lib.rs`](./src/lib.rs#L74).
- Ingestion, mutation, WAL staging, commit, update, delete, deduplication, and indexing paths in [`src/memvid/mutation.rs`](./src/memvid/mutation.rs#L3305).
- Creation, opening, recovery, and index rehydration in [`src/memvid/lifecycle.rs`](./src/memvid/lifecycle.rs#L134).
- Search and ask paths, including lexical fallback, vector fusion, temporal heuristics, ACLs, and correction promotion.
- Memory-card extraction, storage, versioning, schema validation, and enrichment tracking.
- Binary-format constants, manifests, TOC compatibility decoders, footer, and WAL code.
- All test filenames and test declarations: 91 integration tests and 406 unit tests by source inspection.
- Local Git history and blame for major constants, selected patches, and relevant GitHub issues.

I skipped detailed implementation of PDF/XLSX layout algorithms except their limits and public behavior; CLIP/Whisper tensor and audio internals; cipher internals; translated READMEs; Docker and installer recipes; and examples. I could not run the test suite because `cargo` is not installed. Test conclusions are therefore source-level coverage analysis, not runtime verification.

### Core versus surrounding code

The storage engine is centered on:

- `Memvid` lifecycle and state: [`src/memvid/lifecycle.rs:44`](./src/memvid/lifecycle.rs#L44)
- Mutation, WAL staging, commit, update, and delete: [`src/memvid/mutation.rs:412`](./src/memvid/mutation.rs#L412)
- Frame access: [`src/memvid/frame.rs:163`](./src/memvid/frame.rs#L163)
- Search orchestration: [`src/memvid/search/mod.rs:45`](./src/memvid/search/mod.rs#L45)
- Tantivy lexical indexing: [`src/search/tantivy/engine.rs:76`](./src/search/tantivy/engine.rs#L76)
- Vector indexes: [`src/vec.rs:30`](./src/vec.rs#L30)
- Persistent structures: [`src/types/manifest.rs:735`](./src/types/manifest.rs#L735), [`src/toc.rs:14`](./src/toc.rs#L14), and [`src/io/wal.rs:43`](./src/io/wal.rs#L43)

The semantic-memory subsystem is narrower:

- Card model: [`src/types/memory_card.rs:166`](./src/types/memory_card.rs#L166)
- Memory track and indices: [`src/types/memories_track.rs:252`](./src/types/memories_track.rs#L252)
- Rules extraction: [`src/enrich/rules.rs:1`](./src/enrich/rules.rs#L1)
- Pluggable enrichment interface: [`src/enrich/engine.rs:93`](./src/enrich/engine.rs#L93)
- Extraction orchestration and within-frame deduplication: [`src/triplet/extractor.rs:76`](./src/triplet/extractor.rs#L76)
- Memory lookup and schema control: [`src/memvid/memory.rs:42`](./src/memvid/memory.rs#L42)

Readers, API embedding providers, model loaders, replay, audit, Docker, examples, and language bindings are adapters or optional integrations. `ask.rs` is retrieval orchestration; answer synthesis is outside the core contract [`src/types/ask.rs:142`](./src/types/ask.rs#L142).

### Data model and serialization

Memvid has two distinct semantic units:

1. `Frame`: source content with timestamp, payload offsets, checksum, URI, metadata, search text, hierarchy, status, supersession links, and enrichment state [`src/types/frame.rs:166`](./src/types/frame.rs#L166).
2. `MemoryCard`: extracted entity-slot-value data with kind, polarity, two time axes, provenance, engine identity, confidence, and version relation [`src/types/memory_card.rs:175`](./src/types/memory_card.rs#L175).

The `.mv2` container uses a fixed header, embedded WAL, payload/index segments, bincode-encoded TOC, and commit footer. The header records WAL and footer offsets [`src/types/manifest.rs:745`](./src/types/manifest.rs#L745). TOC serialization is fixed-width little-endian bincode [`src/toc.rs:14`](./src/toc.rs#L14). Memory cards instead use JSON under a versioned track header, compressed with zstd level 3 [`src/types/memories_track.rs:492`](./src/types/memories_track.rs#L492).

There are no database migrations. Format evolution uses explicit legacy TOC decoders [`src/toc.rs:21`](./src/toc.rs#L21).

### Main execution path

The normal write path is:

`Memvid::create/open` → `put_bytes_with_options` → `put_internal` → optional BLAKE3 deduplication → reader/extraction → chunk/frame construction → optional tags, dates, triplets, and instant Tantivy indexing → WAL append → `commit` → materialize WAL records and indexes → serialize TOC/footer → persist header → optional `sync_all`.

Anchors: [`src/memvid/lifecycle.rs:137`](./src/memvid/lifecycle.rs#L137), [`src/memvid/mutation.rs:3109`](./src/memvid/mutation.rs#L3109), [`src/memvid/mutation.rs:3305`](./src/memvid/mutation.rs#L3305), [`src/memvid/mutation.rs:572`](./src/memvid/mutation.rs#L572), [`src/memvid/mutation.rs:755`](./src/memvid/mutation.rs#L755), and [`src/memvid/mutation.rs:2879`](./src/memvid/mutation.rs#L2879).

Reopening validates or recovers the TOC, reloads available indexes and tracks, then replays the WAL [`src/memvid/lifecycle.rs:321`](./src/memvid/lifecycle.rs#L321).

### Configuration surface

- Ingest: timestamp, track, kind, URI, title, metadata, search text, tags, labels, embeddings, auto-tagging, date/triplet extraction, hierarchy, raw retention, source path, deduplication, instant indexing, and extraction budget [`src/types/options.rs:19`](./src/types/options.rs#L19).
- Batch ingest: compression, checkpointing, fsync, embeddings, tagging, dates, raw retention, enrichment, and WAL preallocation [`src/types/options.rs:301`](./src/types/options.rs#L301).
- Search: query, top-k, snippet size, URI/scope, cursor, temporal and replay bounds, sketch bypass, and ACLs [`src/types/search.rs:39`](./src/types/search.rs#L39).
- Ask: search settings plus lexical/semantic/hybrid mode, context-only, and adaptive retrieval [`src/types/ask.rs:45`](./src/types/ask.rs#L45).
- Adaptive cutoff: result bounds, normalization, and absolute/relative/cliff/elbow/combined strategies [`src/types/adaptive.rs:37`](./src/types/adaptive.rs#L37).
- Locking: timeout, heartbeat, stale grace, forced takeover, and command label [`src/memvid/lifecycle.rs:109`](./src/memvid/lifecycle.rs#L109).
- Parallel build: segment size, threads, compression, memory cap, queue depth, and vector compression [`src/memvid/builder.rs:32`](./src/memvid/builder.rs#L32).
- Cargo features: lexical, vector, document extractors, temporal tracks, parallel segments, logic mesh, Whisper, replay, encryption, API embeddings, SIMD, and GPU backends [`Cargo.toml:99`](./Cargo.toml#L99).
- Environment: configurable API-key variable [`src/api_embed.rs:92`](./src/api_embed.rs#L92); `MEMVID_MODELS_DIR`, `MEMVID_CLIP_MODEL`, `MEMVID_WHISPER_MODEL`, `MEMVID_OFFLINE`, `MEMVID_LOCK_REGISTRY_DIR`, and `MEMVID_MAX_INDEX_PAYLOAD` [`src/clip.rs:511`](./src/clip.rs#L511), [`src/whisper.rs:144`](./src/whisper.rs#L144), [`src/registry.rs:163`](./src/registry.rs#L163), [`src/memvid/search/api.rs:940`](./src/memvid/search/api.rs#L940).

## 1. Decision inventory

### What may enter memory?

Memvid accepts arbitrary bytes/documents and models extracted memories as facts, preferences, events, profiles, relationships, goals, or custom kinds [`src/types/memory_card.rs:15`](./src/types/memory_card.rs#L15). The taxonomy is hardcoded, although `Other` provides an escape hatch. This assumes broad archival memory. Kivi instead limits durable semantic memory to user-about, work-level material, so the pressure is toward a policy boundary before Memvid's general write API.

### Is source content retained?

Single-document writes retain raw content by default; batch writes default to `no_raw=true` [`src/types/options.rs:80`](./src/types/options.rs#L80), [`src/types/options.rs:362`](./src/types/options.rs#L362). The configurable split reveals workload-dependent confidence rather than one settled answer. Kivi separately needs inspectable provenance and non-retention of third-party material, which this binary raw/no-raw choice does not express.

### Is personal or third-party information excluded?

No. Built-in schemas include spouse, age, birthday, education, hobbies, and pets [`src/types/schema.rs:338`](./src/types/schema.rs#L338). Rules tests expect retention of a third party's pet and brother [`src/enrich/rules.rs:1223`](./src/enrich/rules.rs#L1223). This is deliberate behavior and directly conflicts with Kivi's exclusion and “read, not kept” constraints.

### How is knowledge represented?

Knowledge is an atomic entity-slot-string triple; complex values may be JSON embedded inside the string [`src/types/memory_card.rs:183`](./src/types/memory_card.rs#L183). This hardcoded model assumes facts can be flattened to slots. Kivi additionally needs epistemic tier, evidence count and sources, confirmation status, and suppression state.

### Is confidence the same as authority?

Confidence is an optional `f32`, clamped to 0–1 [`src/types/memory_card.rs:231`](./src/types/memory_card.rs#L231), [`src/types/memory_card.rs:464`](./src/types/memory_card.rs#L464). There is no stated/observed/hypothesised distinction. Memvid therefore records extraction probability but not source authority or disclosure permission.

### What counts as a duplicate?

At document level, deduplication is exact BLAKE3 payload equality and opt-in [`src/types/options.rs:58`](./src/types/options.rs#L58). Within one extraction, duplicate means the same `entity:slot`; the highest-confidence candidate wins, with ties preserving the earlier candidate [`src/triplet/extractor.rs:162`](./src/triplet/extractor.rs#L162). This assumes single-valued slots. Kivi needs repeated occurrences to become evidence rather than disappear.

### What happens on contradiction?

The caller labels cards as `Updates` or `Retracts`; Memvid does not infer contradiction. Supersession requires the same version key and a strictly later event/document timestamp [`src/types/memory_card.rs:246`](./src/types/memory_card.rs#L246). This assumes upstream code correctly identifies both version relations and time. Equal or absent timestamps remain ambiguous.

### What is current truth?

“Current” is the most recent non-retraction ordered by event date, document date, then creation time [`src/types/memories_track.rs:363`](./src/types/memories_track.rs#L363), [`src/types/memory_card.rs:274`](./src/types/memory_card.rs#L274). This hardcodes recency as the resolver. Kivi also needs confirmation authority and tier to matter.

### Is deletion historical or physical?

Frames are marked `Deleted`; updates retain supersession links [`src/types/common.rs:101`](./src/types/common.rs#L101), [`src/types/frame.rs:214`](./src/types/frame.rs#L214). Cards can be retracted, while `clear_memories` destroys the entire memory track [`src/memvid/memory.rs:333`](./src/memvid/memory.rs#L333). Kivi raises separate questions about physical erasure, audit history, suppression, and derived-data removal.

### What makes enrichment idempotent?

Idempotence is keyed by `(frame_id, engine_kind, engine_version)` [`src/types/memories_track.rs:165`](./src/types/memories_track.rs#L165). A new version becomes eligible to run again. This assumes a version uniquely identifies deterministic behavior and does not protect against same-version prompt/model drift.

### What happens on schema conflict?

Strict mode rejects an entire card batch; default non-strict mode logs warnings and stores the cards anyway [`src/memvid/memory.rs:101`](./src/memvid/memory.rs#L101). The default values availability and extensibility over semantic integrity. Kivi requires policy violations to become explicit, durable dropped-candidate outcomes.

### How is retrieval selected and ordered?

`ask` defaults to hybrid retrieval [`src/types/ask.rs:13`](./src/types/ask.rs#L13). Ranking combines BM25/vector order, optional reciprocal-rank fusion, query-class expansion, temporal promotion, and unconditional promotion of correction URIs [`src/memvid/ask.rs:45`](./src/memvid/ask.rs#L45), [`src/memvid/ask.rs:1380`](./src/memvid/ask.rs#L1380), [`src/memvid/ask.rs:1434`](./src/memvid/ask.rs#L1434). These are mainly hardcoded heuristics. Kivi requires separate ranking/filtering dimensions for authority, disclosure permission, evidence, and status.

### What is exposed to the caller?

Callers receive ranked snippets, ranges, scores, metadata, context fragments, citations, and timings [`src/types/search.rs:77`](./src/types/search.rs#L77), [`src/types/ask.rs:86`](./src/types/ask.rs#L86). These are useful provenance primitives but do not represent Kivi's retrieved/used/withheld/dropped trace.

### What happens with no hits or partial extraction?

`ask` broadens lexical terms and may fall back to timeline retrieval [`src/memvid/ask.rs:129`](./src/memvid/ask.rs#L129). Instant indexing permits a 350 ms extraction budget and makes a frame searchable before enrichment completes [`src/types/options.rs:62`](./src/types/options.rs#L62), [`src/types/common.rs:127`](./src/types/common.rs#L127). Memvid assumes approximate context and reduced recall are acceptable. Kivi makes abstention and pre-storage policy enforcement load-bearing.

### What ordering and concurrency model applies?

Frame IDs are dense monotonic indexes and each writable file has one exclusive writer [`src/types/common.rs:7`](./src/types/common.rs#L7), [`src/memvid/lifecycle.rs:135`](./src/memvid/lifecycle.rs#L135). This assumes local single-writer ownership. GitHub issue [#218](https://github.com/memvid/memvid/issues/218) shows that the assumption blocks multi-agent workloads.

### Is commit explicit?

Commit is public and explicit, but `Drop` attempts an implicit commit and discards its error [`src/lib.rs:441`](./src/lib.rs#L441). This hardcodes best-effort convenience. Silent loss of corrections or suppression events would have a higher trust cost in Kivi than ordinary document ingestion.

## 2. Magic numbers

Pure byte-layout offsets, enum tags, cryptographic key/tag sizes, and model-required tensor dimensions are protocol constants, not tunable product decisions, and are excluded here.

| Value | Location and origin | If 10× lower / higher | Assessment |
|---|---|---|---|
| Extraction budget 350 ms | [`src/extract_budgeted.rs:21`](./src/extract_budgeted.rs#L21) | 35 ms frequently yields skim-only content; 3.5 s defeats sub-second ingestion | Locally tuned or guessed; no linked corpus |
| Recency `2×/20`, aggregation `3×/30`, analytical `5×/50` | [`src/memvid/ask.rs:45`](./src/memvid/ask.rs#L45) | Lower misses distributed evidence; higher raises latency and noise | Guessed heuristics |
| RRF `k=60` | [`src/memvid/ask.rs:19`](./src/memvid/ask.rs#L19) | 6 makes top ranks dominant; 600 flattens rank differences | Conventional inherited default |
| Correction boost `2.0` | [`src/memvid/ask.rs:1447`](./src/memvid/ask.rs#L1447) | 0.2 weakens it; 20 overwhelms relevance | Guessed and partly vestigial because corrections are reordered first |
| Adaptive max/min `100/1`; ratios `0.5/0.4/0.3` | [`src/types/adaptive.rs:65`](./src/types/adaptive.rs#L65), [`src/types/adaptive.rs:191`](./src/types/adaptive.rs#L191) | Lower favors truncation/return-all; higher increases cost or becomes invalid | Comments say “reasonable”; guessed but configurable |
| Reranker `50→10`, recall `100→20`, precision `20→5`, floor `0.3` | [`src/types/reranker.rs:87`](./src/types/reranker.rs#L87) | Fewer candidates lose recall; more cost latency; floor 3 rejects all normalized scores | Unvalidated presets |
| HNSW at 1,000 vectors | [`src/vec.rs:23`](./src/vec.rs#L23) | 100 adds early index overhead; 10,000 prolongs linear scans | Benchmark-adjacent, exact value unexplained |
| HNSW distance scale 100,000 | [`src/vec.rs:24`](./src/vec.rs#L24) | Lower loses precision; higher reduces safe range | Deliberate and explained |
| PQ at 100 vectors | [`src/memvid/segments.rs:29`](./src/memvid/segments.rs#L29) | 10 gives weak training; 1,000 delays compression | Algorithm-informed, not demonstrated |
| Lexical sections 900/1,400 chars, max 2,048 | [`src/lex.rs:20`](./src/lex.rs#L20) | Smaller loses context; larger dilutes matches and increases index size | Guessed |
| Search text 32,768; preview 120 bytes | [`src/lib.rs:339`](./src/lib.rs#L339) | Lower loses context; higher raises storage/index costs | Unexplained |
| Max frame 256 MiB; indexes 512 MiB | [`src/lib.rs:340`](./src/lib.rs#L340) | Lower rejects large data; higher expands allocation/DoS exposure | Index increased from 64 MiB; exact rationale unclear |
| WAL 64 KiB/1/4/16/64 MiB; checkpoint 75% or 1,000 transactions | [`src/constants.rs:23`](./src/constants.rs#L23) | Smaller churns copies/fsync; larger increases recovery and unsynced work | Initial PRD-era defaults, not measured here |
| WAL shift buffer 8 MiB | [`src/memvid/mutation.rs:77`](./src/memvid/mutation.rs#L77) | Lower increases iterations; higher transient memory | Operational guess |
| Lock 250 ms; heartbeat 2 s; stale grace 10 s | [`src/memvid/lifecycle.rs:40`](./src/memvid/lifecycle.rs#L40) | Lower causes false failures/takeovers; higher delays recovery | Guessed local-file defaults |
| Lock retry 200 × 50 ms | [`src/lock.rs:130`](./src/lock.rs#L130) | About 1 s fails under brief contention; 100 s appears hung | Commented, not evidence-backed |
| Parallel segment 2,048 tokens/4 pages; 4 GiB; queue 64 | [`src/memvid/builder.rs:23`](./src/memvid/builder.rs#L23) | Lower raises overhead; higher reduces parallelism and raises memory/context size | Unexplained |
| Worker count CPU−1, minimum 1 | [`src/memvid/builder.rs:82`](./src/memvid/builder.rs#L82) | Assumes one core should remain free | Framework-style default |
| zstd level 3 | [`src/types/options.rs:365`](./src/types/options.rs#L365), [`src/types/memories_track.rs:503`](./src/types/memories_track.rs#L503) | Lower favors speed; 10× is outside normal useful range | Conventional default |
| Extraction cache 100; embedding cache 1,000 | [`src/extract.rs:60`](./src/extract.rs#L60), [`src/text_embed.rs:147`](./src/text_embed.rs#L147) | Lower repeats work; higher retains more RAM | LRU was added later; capacities look guessed |
| Model unload 300 s | [`src/text_embed.rs:143`](./src/text_embed.rs#L143), [`src/clip.rs:119`](./src/clip.rs#L119) | 30 s reloads frequently; 3,000 s holds memory | Guessed compromise |
| NER 512 tokens, confidence 0.5 | [`src/analysis/ner.rs:42`](./src/analysis/ner.rs#L42) | Length is model-bound; 0.05 admits noise; 5.0 admits nothing | Length inherited; confidence guessed |
| Temporal confidence 950/900/700 | [`src/analysis/temporal.rs:9`](./src/analysis/temporal.rs#L9) | Lower compresses distinctions; higher exceeds implied scale | Hand-assigned, not calibrated |
| Sketch Hamming 10/64 | [`src/types/sketch_track.rs:70`](./src/types/sketch_track.rs#L70) | 1 is strict; 100 admits everything | Guessed |
| Frame bounds 10,000 children; 1,024 tags/labels/dates; 4,096 metadata | [`src/types/frame.rs:233`](./src/types/frame.rs#L233) | Lower rejects metadata-heavy sources; higher enlarges corrupt allocations | Untraced security ceilings |
| TOC 1M segments, 10M frames, 1M catalog entries | [`src/types/manifest.rs:13`](./src/types/manifest.rs#L13) | Lower caps scale; higher increases decode/DoS exposure | Untraced safety ceilings |
| PDF 4,096 pages, 64–128 MiB, 10 s | [`src/reader/pdf.rs:23`](./src/reader/pdf.rs#L23), [`src/extract.rs:463`](./src/extract.rs#L463) | Lower rejects books; higher monopolizes CPU/RAM | Safety guesses |
| XLSX 1,200-char chunks, max 500 | [`src/reader/xlsx_chunker.rs:18`](./src/reader/xlsx_chunker.rs#L18) | Lower fragments rows; higher loses locality; 50 drops sheets; 5,000 expands index | Tested operationally, not optimized |
| CLIP min 64 px, aspect 10, variance 0.01 | [`src/clip.rs:110`](./src/clip.rs#L110) | Lower admits junk; higher rejects legitimate narrow/low-color images | Semantic filter guesses |
| Replay 10 MiB hard, 1 MiB warning, 512 preview | [`src/replay/types.rs:17`](./src/replay/types.rs#L17), [`src/replay/types.rs:73`](./src/replay/types.rs#L73) | Lower loses tool calls; higher bloats sessions | Safety guesses |
| Doctor scan 100 MB | [`src/memvid/doctor.rs:1604`](./src/memvid/doctor.rs#L1604) | 10 MB misses old footer; 1 GB makes repair expensive | Guessed recovery bound |

No generation temperature is selected by the core. Replay only records caller-supplied optional temperature and top-k [`src/replay/types.rs:418`](./src/replay/types.rs#L418).

## 3. What the history says

### Reversals and later abstractions

The highest-value reversal is the complete v2 rewrite: Python and QR/video encoding were replaced by Rust and a binary single-file format [`CHANGELOG.md:28`](./CHANGELOG.md#L28). The original representational metaphor stopped serving performance, safety, and storage goals.

- Multi-word lexical parsing changed to implicit AND after a precision failure. Commit `f129a94` added a benchmark and regression test [`tests/test_implicit_and.rs:16`](./tests/test_implicit_and.rs#L16).
- Vector search gained HNSW above 1,000 vectors in `1cbfcac`, implying linear-only search stopped scaling [`src/vec.rs:23`](./src/vec.rs#L23).
- Extraction caching gained bounded LRU eviction in `0bb56a0`, implying the original cache lifecycle stopped working operationally [`src/extract.rs:60`](./src/extract.rs#L60).
- Embedding compatibility moved from dimensions toward strict model identity in `80a2544`; same-dimensional models were recognized as non-interchangeable [`src/types/embedding_identity.rs:6`](./src/types/embedding_identity.rs#L6).
- Persisted search capability changed from wrapper/runtime flags to on-disk detection after [issue #194](https://github.com/memvid/memvid/issues/194); current detection is at [`src/memvid/lifecycle.rs:409`](./src/memvid/lifecycle.rs#L409).
- Search changed from failing on stale frame IDs to returning partial results in `a79dfdd`, changing inconsistency policy from fail-closed to skip-invalid.

### Recurring bug classes

- Persistence/index-state disagreement caused semantic failure and silent hybrid degradation: [issue #194](https://github.com/memvid/memvid/issues/194).
- Stale frame references required fixes across multiple search and timeline paths, suggesting frame/index atomicity was not uniformly maintained.
- Repeated small commits corrupted WAL/payload state after region growth; the fix refreshed cached payload offsets. Regression: [`tests/mutation.rs:461`](./tests/mutation.rs#L461); report: [issue #230](https://github.com/memvid/memvid/issues/230).
- Tantivy temporary directories leaked once per put until resource drop ordering changed: [issue #215](https://github.com/memvid/memvid/issues/215).
- Low-memory reopen hangs remain reported in [issue #225](https://github.com/memvid/memvid/issues/225).
- Single-writer ownership is an adoption constraint for multi-agent workloads: [issue #218](https://github.com/memvid/memvid/issues/218).

### Admitted shortcuts and incomplete work

- Mutation code says it should eventually split into ingestion, chunking, and WAL modules [`src/memvid/mutation.rs:1`](./src/memvid/mutation.rs#L1).
- LLM extraction is exposed but produces zero cards [`src/triplet/extractor.rs:120`](./src/triplet/extractor.rs#L120).
- Entity-reference validation currently checks only non-emptiness [`src/types/schema.rs:64`](./src/types/schema.rs#L64).
- Schema inference leaves entity domains unrestricted “for now” [`src/memvid/memory.rs:475`](./src/memvid/memory.rs#L475).
- Batch embeddings, auto-tagging, and date extraction are marked unimplemented [`src/types/options.rs:330`](./src/types/options.rs#L330).
- Some WAL sequencing uses `frame_id + WAL_START_SEQUENCE` as an approximation [`src/memvid/mutation.rs:3771`](./src/memvid/mutation.rs#L3771).
- A legacy compressed-vector case returns `None` rather than decoding [`src/vec.rs:296`](./src/vec.rs#L296).

## 4. Unexamined defaults

- Memory kind defaults to `Fact`; unknown strings silently become `Other` [`src/types/memory_card.rs:51`](./src/types/memory_card.rs#L51). Untried alternative: reject unknown kinds.
- Version relation defaults to `Sets` [`src/types/memory_card.rs:72`](./src/types/memory_card.rs#L72). Alternative: require explicit prior-state semantics.
- Missing event/document timestamps fall back to creation time [`src/types/memory_card.rs:274`](./src/types/memory_card.rs#L274). Alternative: preserve unknown ordering.
- Equal-confidence same-slot candidates keep the first encountered [`src/triplet/extractor.rs:176`](./src/triplet/extractor.rs#L176). Alternative: preserve ambiguity.
- Entity/slot identity is a lowercased concatenated string [`src/types/memories_track.rs:54`](./src/types/memories_track.rs#L54). Alternatives include stable IDs, aliases, locale-aware normalization, and escaped structural keys.
- Unknown predicates are accepted by default [`src/types/schema.rs:439`](./src/types/schema.rs#L439). Alternative: quarantine them.
- `DateTime` accepts any string containing `T` or `-` [`src/types/schema.rs:56`](./src/types/schema.rs#L56). Alternative: real timestamp parsing.
- Ask always disables sketch filtering because accuracy is preferred [`src/memvid/ask.rs:103`](./src/memvid/ask.rs#L103). Alternative: query-adaptive sketch use.
- No-result retrieval broadens or falls back to timeline rather than returning a typed abstention [`src/memvid/ask.rs:129`](./src/memvid/ask.rs#L129).
- Non-strict schema failures exist only in tracing output, not stored status [`src/memvid/memory.rs:138`](./src/memvid/memory.rs#L138).
- Drop-time commit errors are ignored [`src/lib.rs:441`](./src/lib.rs#L441).
- Lexical indexing defaults on when compiled, while per-put embeddings default off [`src/memvid/lifecycle.rs:194`](./src/memvid/lifecycle.rs#L194), [`src/types/options.rs:93`](./src/types/options.rs#L93).

## 5. Questions this repository never faced

Derived from Kivi's position document:

- How is a candidate proven to concern the user rather than a quoted or addressed third party?
- How can third-party context be available to generation but structurally absent from durable writes?
- Can a rejection log prove the boundary without itself retaining prohibited information?
- Is “stated” attached to a proposition, its source utterance, or a later confirmation event?
- How are occurrence count and independent-source count distinguished?
- How does repeated observation accumulate evidence without self-promotion?
- How does confirmation change epistemic tier while retaining earlier history?
- How is a hypothesis stored as a question so downstream code cannot treat it as a fact?
- Where is disclosure authorization enforced so prompts and adapters cannot bypass it?
- How is dictation structurally prevented from reading observations or hypotheses?
- What does “forget” mean across source frames, cards, WAL, indexes, replay, recovery artifacts, and backups?
- How does “that's not me anymore” suppress re-derivation across engine versions and reprocessing?
- Does correction outrank observation because it is newer or because it has greater authority?
- How do observations decay without rewriting history?
- What exactly expires for an unconfirmed hypothesis: visibility, row, evidence, or all three?
- How is the confirmation-prompt budget allocated, replenished, persisted, and audited?
- How does the Why panel distinguish retrieved, withheld, used, rejected, superseded, and unavailable evidence?
- What makes an abstention demonstrably correct rather than just empty lexical retrieval?
- How are sensitive-category false negatives evaluated when failure cost is privacy harm?
- Can enrichment ever precede the hard exclusion check under progressive/instant indexing?
- Can one transcript create lexical/entity residue for dictation while remaining barred from semantic-card storage?
- What happens when a user edits a source transcript after derived memories were confirmed?
- Who may view provenance that contains third-party material even if the derived card is work-level?
- Are mode settings and per-request Daari invitations replayable audit events?

Memvid did not face these questions because it treats memory chiefly as portable retrieval infrastructure; Kivi treats retention and disclosure as moral and epistemic permissions.

## 6. What the tests do not cover

The repository has strong source-level test coverage for lifecycle, corruption detection/recovery, single-file invariants, update/delete status, URI uniqueness, embedding identity, lexical precision, search limits/scopes/snippets, timeline ordering, encryption, replay integrity, and XLSX ingestion.

A materially different answer would still pass the suite for these decisions:

- Whether profiles, goals, family, spouse, age, and pets should be retained. Existing rules tests only lock in examples, including third-party family/pet retention [`src/enrich/rules.rs:1223`](./src/enrich/rules.rs#L1223).
- Whether model confidence differs from source authority or confirmation.
- Whether memories need stated/observed/hypothesised tiers.
- Whether excluded candidates and “read, not kept” outcomes are recorded.
- Whether duplicate observations increment evidence rather than disappear; the card-dedup test expects one winner [`src/triplet/extractor.rs:260`](./src/triplet/extractor.rs#L260).
- How equal timestamps, missing timestamps, and equal-confidence contradictions are handled.
- Whether retraction suppresses later re-extraction from the same source.
- Whether logical forgetting physically erases WAL, indexes, replay, and recovery artifacts.
- Whether non-strict validation failures are observable to callers.
- Whether 350 ms, RRF 60, adaptive thresholds, correction boost, HNSW 1,000, or query expansion factors are corpus-calibrated.
- Whether broad fallback is preferable to abstention.
- Why a result was withheld, used, or ignored.
- Whether dictation and interactive requests have structurally separate retrieval rights.
- Decay, hypothesis expiry, confirmation budgets, demotion, pinning, and suppression.
- Concurrent writers; the architecture excludes the scenario before semantic behavior is exercised.
- Visibility of `Drop`-time commit failures.
- Engine-version idempotence under nondeterministic output or same-version model drift.
- Semantic interoperability of permissive unknown predicates.
- Systematic `limit−1`, `limit`, and `limit+1` tests for format deserialization ceilings.

## Bottom line

Memvid supplies useful provenance, temporal, append/recovery, and retrieval primitives. Almost every load-bearing Kivi choice—subject boundary, retention eligibility, epistemic tier, disclosure permission, correction authority, suppression, decay, and abstention—sits above or outside the decisions this repository actually tested. Its implementation is therefore precedent for storage mechanics, not evidence for Kivi's semantic-memory policy.
