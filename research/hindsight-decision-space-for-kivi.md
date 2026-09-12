# Hindsight’s Decision Space for Kivi

This report extracts questions embodied in `vectorize-io/hindsight` at commit `11e624325`; it does not recommend answers. “Kivi fit” means comparison with `../kivi-semantic-memory-position.md`, not an endorsement. Intent is labelled **inferred** whenever the code or history does not state it.

## 0. Orientation

### Core versus perimeter

The load-bearing implementation is `hindsight-api-slim/hindsight_api/engine/`. `memory_engine.py` is the application orchestrator; `retain/` performs extraction, entity resolution, linking, embedding and writes; `search/` performs semantic, lexical, graph and temporal retrieval plus fusion/reranking; `consolidation/` turns source facts into observations; `reflect/` is the iterative answer agent. The storage seam is explicit: addressed reads use `StoredMemory`, mutations use `MemoryPatch`, and full retrieval is expressed as `FullRecallRequest` (`engine/memories/base.py:155-218`, `engine/memories/base.py:566-642`).

`api/http.py`, `api/mcp.py`, `mcp_tools.py`, `main.py` and `server.py` are transport/startup glue. `engine/providers/`, `engine/parsers/` and `engine/storage/` are adapters. `hindsight-clients/` is generated client surface; `hindsight-control-plane/` is UI; `hindsight-integrations/`, `cookbook/`, `hindsight-docs/`, Docker and Helm are integrations/examples/packaging. They matter only where they freeze compatibility or reveal a failure.

### Data model

The active relational shape is frozen in SQLAlchemy plus Alembic. A `Document` is keyed by `(id, bank_id)` and can retain original text and a content hash (`models.py:90-108`). A `MemoryUnit` is a sentence-level row containing text, vector, context, four notions of time, one of `world|experience|observation`, JSON metadata and timestamps (`models.py:111-183`). Entities are bank-scoped canonical names with first/last-seen and mention count (`models.py:186-221`); unit/entity joins and ordered entity co-occurrences form the entity graph (`models.py:224-269`). Memory links encode temporal, semantic, entity and causal edges with weights constrained to `[0,1]`; legacy causal names remain readable (`models.py:272-313`).

The engine read model adds proof count, tags, observation scopes, provenance (`source_memory_ids`), consolidation state and optional semantic/causal edges (`engine/memories/base.py:155-195`). The API input accepts text or multimodal blocks, caller metadata/entities/tags, timestamps, observation scoping, named strategies and `replace|append` update semantics (`api/http.py:1071-1216`). Async requests may carry a UUID operation identity whose reuse is deduplicated and whose conflicting reuse returns 409 (`api/http.py:1219-1267`). Recall and reflect serialization are Pydantic models in `api/http.py:372-787` and `api/http.py:1421-1618`; bank transfer is versioned separately in `engine/transfer/schema.py:1-224`.

The migration tree is itself historical evidence: opinion facts were removed (`alembic/versions/g2h3i4j5k6l7_remove_opinion_fact_type.py:1-45`, `i4d5e6f7g8h9_delete_opinions.py:1-44`), mental models were renamed observations (`t5o6p7q8r9s0_rename_mental_models_to_observations.py:1-58`), observation history was split out (`a7b8c9d0e1f2_split_history_into_own_tables.py:1-186`), and a new knowledge architecture was introduced (`p1k2l3m4n5o6_new_knowledge_architecture.py:1-291`).

### Main execution paths

**Retain:** `POST .../memories` validates `RetainRequest`, then calls the engine (`api/http.py:8881-9125`). `MemoryEngine` resolves per-bank configuration and invokes `retain_batch`; the orchestrator screens/redacts, builds or appends document bodies, chunks, extracts facts, resolves entities, embeds, inserts facts and links, and finally stores document bodies (`engine/retain/orchestrator.py:58-289`, `engine/retain/orchestrator.py:1126-1265`, `engine/retain/orchestrator.py:1266-2090`). Document ID means upsert: replace deletes/reprocesses; append concatenates and reprocesses (`api/http.py:1192-1196`).

**Recall:** the request exposes query, budget, fact-type/tag filters, max tokens, score floors, fusion and trace/include controls (`api/http.py:372-479`). The engine analyzes the query, obtains an embedding, retrieves fact types in parallel, fuses candidates, optionally cross-encoder reranks, applies recency/boost scoring and token/result budgets (`engine/search/retrieval.py:793-1056`, `engine/search/fusion.py:30-108`, `engine/search/reranking.py:300-431`).

**Reflect:** a request defaults to low budget and a 4,096-token answer cap, can include provenance/tool traces, and can exclude observations/mental models (`api/http.py:1421-1498`). `run_reflect_agent` iterates LLM tool calls until `done`, a configured iteration/context/wall limit, or an error; structured output is a post-processing path (`engine/reflect/agent.py:436-1332`, `engine/reflect/agent.py:1375-1635`).

### Config surface

The canonical surface is `config.py`: `HindsightConfig` is the sole parser of `HINDSIGHT_API_*` variables (`config.py:152-1091`, `config.py:2669-4981`). Resolution is hierarchical—global environment, tenant extension, bank config—for the names in `_CONFIGURABLE_FIELDS`; infrastructure remains static (`config.py:810-884`, `config_resolver.py:353-604`). The surface includes database/backend/pools; four operation-specific LLM profiles; embeddings and rerankers; extraction/chunking/attachments; entity matching; retrieval arms, score floors, fusion/recency and budgets; consolidation/history/scopes; async workers/retries/timeouts; migrations; MCP/API feature gates; telemetry/audit/traces; file storage/parsers; maintenance; and webhooks (`config.py:152-1909`). Numeric policy is itemized in §2.

### Tests read and skipped

The core package contains 546 test/support files. I read or searched the policy-discriminating suites for retain/chunking/document upsert/delta/append, fact extraction, narrator attribution, entity resolution, memory defense, recall/fusion/reranking/temporal search, consolidation/dedup/history/scopes/failure recovery, reflect/structured output, curation, transfers, bank isolation/config, async idempotency and migration shape. Representative evidence includes retain ordering and links (`tests/test_retain.py:19-2381`), delta replacement/deletion (`tests/test_delta_retain.py:59-987`), zero-fact document persistence (`tests/test_document_tracking.py:324-503`), secret blocking/redaction (`tests/test_memory_defense.py:563-934`), scope/cap behavior (`tests/test_consolidation.py:1882-3165`) and scoring (`tests/test_combined_scoring.py:1-740`).

I sampled rather than line-read provider compatibility/retry suites, Oracle-only internals, admin backup, UI tests, generated SDK tests, integration packages, documentation rendering, packaging and deployment tests. I skipped generated clients and lockfiles except where a historical change cited them. Therefore “every” in §2 means every numeric threshold in the core memory-policy/config path, not protocol constants inside every third-party adapter.

## 1. Decision inventory

### D1 — What is allowed to enter memory?

- **Question:** accept arbitrary text/multimodal content and let extraction decide, or require a narrow typed event contract before ingestion?
- **Hindsight answer:** accepts text, image and file blocks plus caller context, entities, metadata, tags and time; the extractor emits factual statements and entities (`api/http.py:788-1070`, `engine/retain/fact_extraction.py:256-300`). It has a pluggable memory-defense screen for secrets, but no first-class policy for Kivi’s sensitive topics or third-party personal content (`extensions/memory_defense.py:1-103`, `extensions/builtin/memory_defense_regex.py:1-222`).
- **Placement:** input shape is configurable/extensible; semantic admissibility is mostly prompt/mission driven. This suggests confidence in a generic ingestion platform, not in a normative personal-memory boundary.
- **Assumptions:** the caller owns the bank and is entitled to retain supplied context; false retention is tolerable enough to curate later. **Kivi fit:** does not hold. Kivi requires structural non-retention and a hard excluded-category check before storage (`../kivi-semantic-memory-position.md:47-50`, `:106-125`), pushing toward a separate gate and a dropped-candidate audit model.

### D2 — What is the atomic remembered object?

- **Question:** preserve transcripts/events as primary records, store extracted atomic facts, or store only synthesized profiles?
- **Hindsight answer:** source documents and chunks remain, but retrieval centers on sentence-level `MemoryUnit` facts (`models.py:90-137`); observations are also memory units distinguished by `fact_type` (`models.py:156-175`).
- **Placement:** schema-hardcoded taxonomy; extraction mode is configurable (`config.py:1492-1500`). High confidence in fact-oriented storage, lower confidence in extraction verbosity.
- **Assumptions:** atomic propositions are reusable across agent tasks and embedding-friendly; source retention cost/privacy is acceptable. **Kivi fit:** partially. Kivi needs typed entity/preference/episode plus an independent epistemic tier (`../kivi-semantic-memory-position.md:66-103`); Hindsight’s `world|experience|observation` combines perspective and derivation, pushing Kivi toward an additional axis rather than reuse unchanged.

### D3 — Is provenance part of the value or optional payload?

- **Question:** must every derived belief carry source identity through every read, or may provenance be reconstructed/omitted for speed?
- **Hindsight answer:** raw facts point to document/chunk; observations carry `source_memory_ids`; recall can suppress source facts when their observation supersedes them (`engine/memories/base.py:163-187`, `api/http.py:397-405`). Reflect provenance and tool output are opt-in response includes (`api/http.py:1393-1418`).
- **Placement:** provenance storage is structural, disclosure configurable. This shows confidence that lineage matters operationally, but treats user-visible explanation as payload cost.
- **Assumptions:** most callers prefer compact results; source IDs are sufficient and source content can be fetched later. **Kivi fit:** storage aligns, default disclosure does not. Kivi makes the Why trace a product guarantee (`../kivi-semantic-memory-position.md:203-229`), pushing toward always-generated trace state even if collapsed in UI.

### D4 — What gets discarded?

- **Question:** discard non-factual text, unsafe secrets, low-information facts, low-score candidates, or nothing unless a user deletes it?
- **Hindsight answer:** extraction can return no facts; degenerate fact text is rejected (`engine/retain/types.py:414-468`); memory defense can redact or block (`engine/retain/orchestrator.py:58-289`); retrieval floors/candidate and token budgets discard candidates (`config.py:1243-1291`, `config.py:1741-1769`). File bytes are deleted after retain by default while source text is retained (`config.py:1544-1555`).
- **Placement:** safety is pluggable/configurable, degenerate rejection hardcoded, ranking loss configurable. **Inferred:** these are operational-quality choices, not a coherent privacy policy.
- **Assumptions:** omitted facts can be re-extracted from stored source; silent ranking loss is acceptable. **Kivi fit:** only if dropped sensitive/third-party candidates and reasons become durable audit events; Kivi explicitly demands that proof (`../kivi-semantic-memory-position.md:47-50`, `:277-287`).

### D5 — What does a duplicate document mean?

- **Question:** reject, append, merge incrementally, or replace prior derived state?
- **Hindsight answer:** same `document_id` defaults to replace; append is explicit (`api/http.py:1192-1196`). Delta retain hashes chunks, preserves unchanged facts, extracts changed chunks and removes facts for deleted chunks (`engine/retain/orchestrator.py:3496-4360`; `tests/test_delta_retain.py:59-987`). Duplicate document IDs in one queued batch are rejected (`engine/memory_engine.py:20682-20701`).
- **Placement:** caller-configurable per item, with hard invariants around append monotonicity (`engine/retain/orchestrator.py:132-180`). This reveals low confidence that one update semantic fits all sources, but high confidence that append must never shrink history.
- **Assumptions:** callers can assign stable document identities and know whether content is a snapshot or tail. **Kivi fit:** transcripts naturally favor append, corrections favor semantic supersession; conflating these pushes toward distinct source-update and belief-update operations.

### D6 — Are repeated facts deduplicated or accumulated as evidence?

- **Question:** collapse repeats into one fact, preserve every mention, or maintain one belief plus evidence count?
- **Hindsight answer:** facts remain source-linked; semantic linking and later consolidation perform dedup/synthesis. `proof_count` exists in the read/write seam and can increment relatively (`engine/memories/base.py:171-217`), while observations name multiple source memories (`engine/memories/base.py:184-187`). Consolidation uses a 0.97 embedding threshold before model-level dedup (`config.py:1593`).
- **Placement:** the mechanism is mixed: schema/seam for evidence, configurable heuristic for observation dedup, LLM-pluggable reconciliation. Confidence is highest in preserving sources, lower in defining equivalence.
- **Assumptions:** duplicates are semantically near and consolidation can repair misses. **Kivi fit:** evidence accumulation matches observed-tier semantics, but Kivi forbids automatic promotion regardless of count (`../kivi-semantic-memory-position.md:95-103`), pushing against treating proof count as truth tier.

### D7 — What happens on contradiction?

- **Question:** keep both facts, overwrite the old fact, mark temporal validity, or create a superseding derived belief with history?
- **Hindsight answer:** raw source facts coexist; consolidation creates/updates/deletes observations and retains observation history when enabled (`engine/consolidation/consolidator.py:1170-1620`, `config.py:1562-1583`). Re-retaining a document invalidates stale derived observations and requeues consolidation (`engine/retain/fact_storage.py:250-392`).
- **Placement:** LLM-pluggable reconciliation plus configurable history. This indicates uncertainty about contradiction semantics but confidence that derived state must be regenerable.
- **Assumptions:** contradiction can be resolved during asynchronous synthesis; temporary coexistence is acceptable. **Kivi fit:** Kivi requires explicit supersession, visible history, and “not me anymore” suppression (`../kivi-semantic-memory-position.md:232-248`). Hindsight has history/retraction machinery but no user-semantic suppression against re-derivation; the gap pushes toward a separate correction ledger.

### D8 — How are entities identified and conflicts resolved?

- **Question:** exact identity, fuzzy string identity, embedding identity, caller-owned IDs, or model adjudication?
- **Hindsight answer:** entities are canonical bank-scoped names; default lookup is trigram, with 0.15 candidate threshold, 0.5 in-batch merge and 0.3 stored-entity merge thresholds (`models.py:186-221`, `config.py:1532-1537`, `config.py:1663-1681`). Callers may supply entities and control resolution (`api/http.py:788-845`).
- **Placement:** heuristic thresholds are configurable; entity resolver is a core module. This signals known domain sensitivity and limited confidence in universal cutoffs.
- **Assumptions:** name similarity is a useful proxy and false merges are repairable. **Kivi fit:** names/projects matter unusually much for dictation (`../kivi-semantic-memory-position.md:181-199`); false merges can corrupt spelling and disclosure, pushing toward caller-visible identity/provenance and perhaps stricter defaults—direction only, not a recommendation.

### D9 — Which retrieval strategies compete?

- **Question:** dense-only, lexical-only, structured/graph-only, temporal-only, or hybrid?
- **Hindsight answer:** four parallel arms—semantic, BM25, graph, temporal—are enabled by default, fused then reranked (`config.py:1750-1753`, `engine/search/retrieval.py:793-1056`). Empty lexical queries fall back to semantic-only; Oracle text-search errors also fall back rather than fail recall (`engine/search/retrieval.py:233-334`).
- **Placement:** arms and thresholds configurable, graph retriever pluggable (`engine/search/retrieval.py:80-120`). This reflects low confidence that one retrieval family dominates all data shapes.
- **Assumptions:** extra latency/connections are worth recall robustness. **Kivi fit:** Hey Kivi can benefit; regular dictation explicitly must have a separate entity/lexical-only path (`../kivi-semantic-memory-position.md:181-199`). Hindsight’s fact-type filters are not structural table isolation.

### D10 — How are retrieval results ordered?

- **Question:** raw similarity, weighted sum, reciprocal-rank fusion, round-robin coverage, recency, or learned reranking?
- **Hindsight answer:** ordinary recall uses RRF (`1/(60+rank)`) and optional cross-encoder reranking; recency and strategy boosts affect combined scoring (`engine/search/fusion.py:30-108`, `engine/search/reranking.py:300-431`). Consolidation dedup can request interleaving because RRF could hide the semantic rank-1 “twin” and create duplicates (`engine/search/fusion.py:113-129`).
- **Placement:** fusion mode is caller/config selectable, reranker provider pluggable, RRF constant hardcoded. The special interleave path is strong evidence the default ordering is task-dependent.
- **Assumptions:** general recall rewards multi-arm agreement; dedup rewards coverage of each arm’s best hit. **Kivi fit:** Kivi has at least two distinct objectives—accurate lexical recall and epistemically governed disclosure—pushing away from one global ranking objective.

### D11 — Should retrieved observations hide their source facts?

- **Question:** show both evidence and synthesis, show synthesis only, or let the caller decide?
- **Hindsight answer:** `exclude_observation_sources=true` removes facts cited by returned observations and backfills freed slots to avoid duplicate content (`api/http.py:397-405`).
- **Placement:** request configurable. This exposes uncertainty: compactness versus auditability is delegated to caller.
- **Assumptions:** source facts are redundant for answer generation. **Kivi fit:** evidence is not redundant because tier and provenance are user-facing epistemics; Kivi likely experiences pressure toward retaining evidence in trace while hiding it from answer prose (`../kivi-semantic-memory-position.md:155-176`, `:227-229`).

### D12 — Is permission applied at retrieval or disclosure?

- **Question:** prevent lower-permission paths from loading data, retrieve all then redact, or use both depending on surface?
- **Hindsight answer:** tag and fact-type filters operate during retrieval (`api/http.py:424-479`); reflect directives are separately scoped and can be globally applied (`api/http.py:1462-1494`). There is no Kivi-like stated/observed/hypothesized disclosure tier.
- **Placement:** caller-controlled filters, not a first-class policy engine. **Kivi fit:** differs in both directions: Kivi wants retrieval-all/disclosure gating for Hey Kivi, but structural non-access to observations for dictation (`../kivi-semantic-memory-position.md:155-176`, `:181-199`). That means Hindsight supplies mechanisms, not the governing abstraction.

### D13 — What is exposed to the caller?

- **Question:** facts only, scores and arm traces, raw chunks, attachments, provenance, or a synthesized answer?
- **Hindsight answer:** recall can include entities, chunks, source facts, attachments and trace; reflect returns answer text, optional structured output, optional based-on facts and optional tool/LLM traces (`api/http.py:333-787`, `api/http.py:1393-1618`). Trace construction is skipped when not requested for performance (`engine/memory_engine.py:1425-1447`).
- **Placement:** highly configurable response expansion. The system prioritizes generic API cost control over mandatory legibility.
- **Assumptions:** callers build their own trust UI. **Kivi fit:** Kivi makes withheld/used/source state part of the product contract (`../kivi-semantic-memory-position.md:176-178`, `:227-229`), pushing optional Hindsight diagnostics into required domain output.

### D14 — What happens on low confidence or no answer?

- **Question:** abstain with evidence, return low-score candidates, ask for clarification, or let the LLM synthesize anyway?
- **Hindsight answer:** retrieval has score floors and may return empty; reflect defines `ReflectNoAnswerError`, but the iterative agent normally forces a final response at budget limits (`engine/reflect/agent.py:74-121`, `engine/reflect/agent.py:493-1332`). The API returns operational errors rather than a domain-specific “searched but absent” object (`api/http.py:1597-1658`).
- **Placement:** thresholds configurable; abstention semantics incomplete/unclear. **Kivi fit:** does not satisfy Kivi’s explicit actionable abstention and search trace requirement (`../kivi-semantic-memory-position.md:203-216`). Pressure is toward a first-class negative-result schema, not merely an empty list or generation exception.

### D15 — What changes over time?

- **Question:** immutable facts, mutable facts, decaying relevance, versioned observations, or expiring hypotheses?
- **Hindsight answer:** source facts may be edited/invalidated/deleted; recency ranking uses linear 365-day or exponential 90-day-half-life decay (`config.py:1279-1283`); observations and mental models can keep up to 50 history entries (`config.py:1562-1583`). There is no hypothesis tier or automatic semantic expiry.
- **Placement:** decay and history configurable; no schema-level belief lifecycle. **Kivi fit:** Kivi requires observations to lose standing, hypotheses to expire, and confirmed corrections to suppress regeneration (`../kivi-semantic-memory-position.md:232-248`). Hindsight’s recency score is retrieval relevance, not epistemic status.

### D16 — What is idempotent and what must be ordered?

- **Question:** identify retries by payload, document identity, operation identity, sequence cursor, or transaction boundary?
- **Hindsight answer:** async retain supports client operation UUID idempotency (`api/http.py:1249-1255`); document updates depend on stable IDs and ordered chunk indexes; scans are positional, not snapshot-consistent (`engine/memories/base.py:241-248`). Store sessions defer completion events until commit, and outbox failure after commit is logged rather than turning a successful retain into failure (`engine/memory_engine.py:2860-2935`).
- **Placement:** operation identity is caller-visible/config-free; ordering invariants are hardcoded. Confidence is high because replay mistakes destroy or duplicate knowledge.
- **Assumptions:** callers can persist UUIDs across ambiguous failures; one document’s append order is known. **Kivi fit:** transcript replay provides sequence/order, but confirmation, demotion and suppression events also need durable identities—questions Hindsight’s generic retain operation does not settle.

### D17 — What happens when extraction or consolidation fails?

- **Question:** fail the whole batch, keep good partial outputs, bisect/retry, dead-letter, or silently skip?
- **Hindsight answer:** extraction failure policy is configurable (`config.py:1799-1802`). Consolidation validates whole model responses fail-closed, bisects failed batches, marks permanently failed source rows and exposes recovery (`engine/consolidation/consolidator.py:744-1055`, `api/http.py:8384-8406`).
- **Placement:** operational retry budgets configurable, schema validation hardcoded. This reveals high confidence that malformed destructive instructions must not partially apply.
- **Assumptions:** delayed observations are cheaper than corrupt ones; raw facts remain available. **Kivi fit:** mostly holds, but Kivi additionally needs visible “candidate dropped” reasons and failure traces to prove privacy boundaries.

### D18 — Who owns customization?

- **Question:** fork prompts/code, configure a bank mission, install a tenant extension, or provide a storage/retrieval plugin?
- **Hindsight answer:** retention mission, custom extraction instructions, named strategies, observation mission/scopes, LLM strategies and a memories extension are all seams (`config.py:1495-1500`, `config.py:1610-1614`, `engine/memories/base.py:681-1100`).
- **Placement:** deliberately pluggable. **Kivi fit:** useful for mechanics, dangerous for guarantees: Kivi’s exclusions, tier grammar and surface separation cannot be optional bank configuration without weakening the position document.

## 2. Magic numbers

“Trace” labels: **stated** means a comment/history gives a reason; **compat** means explicitly retained behavior; **inferred/guessed** means no rationale was found. Moving an order of magnitude is a counterfactual, not a recommendation.

| Number / default | Location | Trace | 10× lower | 10× higher |
|---|---|---|---|---|
| temperatures verify `0.0`, retain `0.1`, reflect `0.9`, consolidate `0.0` | `config.py:241-244` | operation intent stated; tuning provenance unclear | retain becomes deterministic; reflect loses exploration | retain/consolidation become unstable; 0.9 cannot meaningfully become 9 on normal APIs |
| LLM retries `3`, backoff `1..60s`, timeout `120s`, connect `10s`; reflect call `30s` | `config.py:1110-1139` | guessed | transient failures surface sooner | very long tail latency and retry cost |
| embedding max input `8192` tokens | `config.py:1422` | **compat**, model-context legacy (`tests/test_embeddings_max_input_tokens.py:1-22`) | truncates source severely | provider rejection/context overflow |
| embedding batches ONNX/TEI `32`, OpenAI/Gemini `100`; concurrency `8` | `config.py:1173-1213` | provider-shaped; exact tuning unclear | more calls, lower memory | rate-limit/RAM spikes |
| embedding retry `4`, `0.5..4s`, 15s budget | `config.py:1198-1201` | bounded-retry design | brittle remote calls | request latency hides outages |
| reranker retries `3`, `0.5..4s`, 10s budget; remote timeout `30–60s` | `config.py:1206-1242` | bounded-retry history; values unclear | more partial/unreranked responses | recall stalls under provider failure |
| embedding dimensions `384`, Gemini `768`, ZeroEntropy `1280` | `config.py:1210-1214`, `:1351-1358` | model/provider contracts | quality/capacity loss or invalid schema | storage/index cost or provider mismatch |
| reranker candidates `300`; low/mid/high overrides `0` | `config.py:1243-1247` | legacy/global fallback | relevant tail lost before rerank | latency and memory inflate |
| semantic floor `0.3`; graph seed `0.3`; temporal `0.1`; semantic-link `0.7` | `config.py:1248-1251` | no derivation found: **guessed/tuned unclear** | noisy candidates/edges | sparse recall/disconnected graph |
| BM25 floor `0.0`, max query terms `16` | `config.py:1255-1267` | no derivation found | max terms ≈2 loses intent | ≈160 terms increases SQL/search cost and query drift |
| recency linear window `365d`, exponential half-life `90d` | `config.py:1279-1283` | no derivation found | recent-only memory | old preferences dominate much longer |
| RRF `k=60` | `engine/search/fusion.py:30-37` | conventional default; repo-specific validation unclear | top ranks dominate | arms become nearly uniform; rank discrimination shrinks |
| graph seed count `10` | `engine/search/types.py:14-18` | unclear | graph coverage collapses | graph DB work expands |
| recall concurrency `32`, DB connections/op `4`, query `500` tokens, entity expansion `200`, timeout `10s` | `config.py:1463-1468` | I/O bounds; exact tuning unclear | throughput/recall coverage falls | pool exhaustion, graph latency, prompt-like queries |
| bank info cache `30s/2048`; stats `60s/1024` | `config.py:1486-1489` | capacity/latency trade-off, guessed | DB churn | stale UI/config and memory growth |
| retain completion cap `64,000` tokens; chunk `3,000` chars | `config.py:1492-1495` | no corpus derivation found | truncated extraction / too many calls | provider limits, cross-topic facts, large failure unit |
| attachment `20MB`, `50/item`, image cost `1,500 chars`, `8/chunk` | `config.py:1507-1523` | operational guesses | rejects ordinary scans/multi-image docs | memory, VLM cost and payload abuse |
| retain RAM budget `128MB`; async split `10,000` tokens | `config.py:1530-1531` | comment ties split to ≈40KB; tuning unclear | excessive streaming/calls | OOM and huge retry units |
| entity lookup batch `100`, candidates `200`; similarity `0.15/0.5/0.3` | `config.py:1532-1537`, `:1663-1681` | no benchmark cited | more DB calls, stricter merge if thresholds ×10 (often impossible) | large queries; thresholds ÷10 yield false merges |
| batch poll `60s` | `config.py:1541` | guessed | provider polling load | completion visibility delayed |
| file batch `100MB`, `10 files` | `config.py:1551-1552` | guessed | rejects practical uploads | worker memory/time amplification |
| history caps `50` each | `config.py:1581-1582` | guessed | weak audit trail | storage/read cost, long personal history |
| consolidation attempts `3`, load batch `50`, LLM batch `8`, parallelism derived, recall `512` tokens | `config.py:1583-1607` | comments describe purpose; values unclear | more calls and missed context | large failure domains, model confusion/cost |
| consolidation dedup `0.97` | `config.py:1593` | no source found: likely tuned/guessed | false merges | almost no pre-LLM dedup (threshold >1 impossible) |
| max observations/scope `-1` | `config.py:1611-1614` | explicit unlimited sentinel | N/A | a finite large cap changes only scale failure |
| DB pool `5..100`; command `60s`, acquire `30s`, statement `600s` | `config.py:1627-1631` | infrastructure defaults, provenance unclear | timeout churn/low throughput | hung work consumes pool for minutes/hours |
| model init `300s` | `config.py:1682` | comment: first downloads | cold start fails | unhealthy startup hidden for 50 minutes |
| worker poll `500ms`, retries `3`, retry delay `60s`, slots `10` | `config.py:1687-1691` | guessed | DB polling/rapid retry pressure | queue latency and slow recovery; slots 100 raise contention |
| operation cleanup batch `1,000`; retention `0d` | `config.py:1696-1697` | `0` semantics require runtime reading; intent unclear | N/A | 10k-delete transactions lock longer |
| retain DB concurrency `4`, subbatch `1`, store writes `16` | `config.py:1698-1707` | comments tie `4` to HNSW I/O | slower ingestion | DB/index contention and OOM |
| retain wall `3,600s`; consolidation `7,200s` | `config.py:1715-1722` | comments give 1h/2h; derivation unclear | large jobs fail | stuck jobs occupy capacity for 10–20h |
| reflect iterations `10`, context `100,000`, wall `300s`, source facts `-1` | `config.py:1725-1732` | forced-answer mechanics stated; values guessed | shallow answers/early synthesis | runaway tool loops, cost and latency |
| recall fact budget `2,048`, chunk budget `1,000` tokens | `config.py:1741-1743` | guessed | evidence loss | prompt cost/context crowding |
| fixed recall low/mid/high `100/300/1000`; adaptive `2.5%/7.5%/25%`, floor `20`, cap `2,000` | `config.py:1760-1769` | fixed explicitly preserves legacy behavior (`config.py:1756`, `:3142`) | misses long tail | large candidate/rerank cost; high adaptive can approach whole bank |
| loop stall/acquire warning `1,000ms`, watchdog poll `250ms` | `config.py:1788-1791` | observability guesses | noisy alerts/thread wakeups | misses user-visible stalls |
| LLM trace retention `1d`, max `50,000 chars` | `config.py:1804-1807` | guessed | weak incident/audit evidence | privacy/storage exposure grows |
| reconcile/mental-model ticks `300s`; retention sweep `3,600s`; cleanup/index interval `900s`; jitter `60s` | `config.py:1813-1879` | maintenance/load spreading comments; exact values unclear | database churn | stale derived state/deletions/indexes |
| link weight partial-index floor `0.1` | `models.py:307-312` | no rationale found | larger index | useful weak links excluded |
| default bank disposition `3/3/3` | `models.py:317-325` | midpoint default; deliberate origin unclear | invalid below scale | invalid above scale |

The code also contains provider IDs, ports (`8888`, `8889`), model batch sizes, cache capacities and infrastructure timeouts; they are config surface but not semantic-memory policy. All are centralized in `config.py:1102-1909`, which is the authoritative exhaustive list.

## 3. What the history says

### Highest-value reversals

1. **RRF was not universal.** Interleaved fusion was added specifically because RRF rewarded agreement across arms and could push semantic rank #1 below the consolidation budget, causing duplicate observations (`engine/search/fusion.py:113-129`). This is a genuine answer reversal: “one fusion rule” became “fusion depends on task.”
2. **Authored mental-model page content was reverted.** History contains paired commits `306b8ab`/`65b4e32` (“Revert the authored-page-content path”), after later work made pages projected views over consolidated memory. The exact rationale is **unclear** from the current files; the reversal itself is explicit in git history.
3. **Free-threaded Python plus multi-loop serving was removed.** Load testing did not justify maintenance cost, so 1,819 lines and public extension hooks were removed; real thread-safety fixes remained. This is explicit in [PR #4234](https://github.com/vectorize-io/hindsight/pull/4234) and commit `6f441b0ae`.
4. **Bank profile/background APIs became config, then were retired.** The old endpoints now return 410; an LLM-merge background command was removed rather than silently changed to overwrite semantics. Commit `163fbb0ed`; compatibility stubs remain at `api/http.py:7696-7790`.
5. **Causal taxonomy narrowed.** New retain writes only `caused_by`, while `causes|enables|prevents` survive solely for old rows/transfers (`models.py:295-301`, `engine/causal_links.py:8-16`). This is backwards compatibility, not continuing endorsement of four causal relations.

### Recurring bug shapes

- **Replacement/replay is not semantically idempotent.** Issue [#3989](https://github.com/vectorize-io/hindsight/issues/3989) measured a growing transcript whose extracted facts fell from 197 to 131 after re-extraction. The server-side append bug then truncated stored source and caused facts to disappear on the next append; the fix added a hard monotonicity invariant (commit `fda969777`; `engine/retain/orchestrator.py:132-180`).
- **Identity flattening leaked across isolation boundaries.** `(bank_id, document_id, index)` was underscore-concatenated, allowing cross-bank chunk-ID collisions and overwrite. The fix escaped components and made bank ID mandatory on deletes; legacy IDs remain readable (commit `179938a65`; `engine/chunk_ids.py:1-116`; `tests/test_chunk_id_legacy_documents.py:1-190`).
- **Derived-state invalidation repeatedly lagged source edits.** History includes “unsay facts a page cites that no longer exist” (#3475/#3618), “invalidate observations when a re-retain changes scoping” (#4019), and attachment/source integrity fixes. Current invalidation state is explicit on memory rows and in curation APIs (`api/http.py:2160-2180`, `:2580-2630`).
- **Consolidation’s destructive output failed silently.** A missing `deletes[].observation_id` caused whole responses—including valid creates/updates—to be discarded; bisection cleared stuck-row gauges, making the broken delete path look healthy. The answer stayed fail-closed, but prompt schema, alias tolerance and metrics were added. This is reported in [issue #4152](https://github.com/vectorize-io/hindsight/issues/4152) and commit `05c775c41`.
- **Temporal assumptions caused whole-recall failures.** A far-future timestamp overflowed exponential recency before clamping; the fix clamps first (commit `1ca8c4d60`; `engine/search/reranking.py:235-255`). “Last weekend” semantics and dateparser thread safety also recur in recent history.
- **Commit/event ordering was wrong.** `retain.completed` could publish before the store commit. It is now deferred, and a later outbox failure cannot reclassify committed storage as failed because that invites duplicates (commit `511c86e10`; `tests/test_retain_outbox_session.py:1-124`).
- **Schema evolution broke availability.** A history table used `VARCHAR(64)` while bank IDs elsewhere were unbounded text; a 78-character bank ID aborted startup migration. The migration and a forward repair were added (commit `621ab7e66`; `alembic/versions/a7b8c9d0e1f2_split_history_into_own_tables.py:55-90`).

### Shortcuts and admitted incompleteness

- A scan cursor is explicitly a position rather than snapshot, so concurrent writes may shift pages (`engine/memories/base.py:241-248`). Deliberate trade-off.
- Unknown graph retriever names silently fall back to link expansion (`engine/search/retrieval.py:103-109`). Deliberate availability bias, but configuration mistakes can go unnoticed.
- Oracle text-search failures fall back to semantic-only recall (`engine/search/retrieval.py:330-369`). Deliberate degradation.
- Config permission-check failure can fail open “for backward compatibility” (`config_resolver.py:552-573`). Compatibility concession, not fresh design.
- `event_date` remains non-null only for backwards compatibility while newer occurred/mentioned fields carry semantics (`models.py:124-131`).
- Several legacy causal values, auth modes, input shapes and response fields remain accepted (`models.py:295-301`, `api/mcp.py:44-48`, `api/http.py:73-83`, `engine/search/trace.py:161-168`). These are compatibility load, not evidence for Kivi’s greenfield model.

### Later abstractions that expose failed original assumptions

- The memories extension grew from storage operations to full-recall ownership, graph retrieval and store-owned retain (`engine/memories/base.py:681-1100`): persistence could not remain “just a database adapter.”
- Operation-specific LLM profiles/strategies were added on top of one global provider (`config.py:227-238`, `:380-441`): extraction, reflection and consolidation did not share one optimal model/cost/temperature.
- Observation scopes (`per_tag|combined|all_combinations|shared|explicit`) were added (`api/http.py:1174-1186`): one bank-wide consolidation namespace caused cross-context duplicate or leakage pressure.
- History moved from embedded arrays to dedicated tables (`alembic/versions/a7b8c9d0e1f2_split_history_into_own_tables.py:45-186`): mutable JSON history stopped scaling or querying adequately (**inferred**; migration states mechanics, not rationale).
- Async `operation_id`, serialization keys, bank-deduped queues and per-bank claim fairness accumulated (`api/http.py:1249-1255`, `engine/memory_engine.py:20332-20554`): naive “enqueue once” semantics did not survive retries and concurrent workers.

## 4. Unexamined defaults

These have no comment, test that compares an alternative, or traceable rationale in the inspected scope. They may still have been discussed elsewhere; intent is **unclear**.

- **Sentence-level facts:** alternative not tried in evidence here: event-shaped records with typed participants/actions and fact fragments as indexes (`models.py:111-137`).
- **One vector per memory unit:** alternative: field-specific or multi-vector representations for entity, episode and preference (`models.py:121-123`).
- **Cosine HNSW as model-level default:** alternative: exact search until scale warrants ANN, or learned sparse+dense indexing (`models.py:177-182`). Later per-bank index work partially revisits this.
- **Canonical entity name as identity anchor:** alternative: caller-owned immutable entity IDs with names as aliases (`models.py:186-221`).
- **Unbounded document/source text retention by default:** alternative: source TTL, encrypted source vault, or provenance hashes with user-owned originals (`config.py:1554-1555`).
- **Observations and auto-consolidation on by default:** alternative: opt-in after evidence or explicit confirmation (`config.py:1562-1564`). This matters sharply for Kivi because “observed” must never self-promote (`../kivi-semantic-memory-position.md:95-100`).
- **No observation cap (`-1`):** alternative: bounded working set with archive/decay (`config.py:1611`).
- **Low reflect budget and 4,096 output tokens:** alternative: query-dependent budget/abstention (`api/http.py:1445-1455`).
- **`tags_match=any` includes untagged/global state:** alternative: strict exclusion of untagged memories unless requested (`api/http.py:1468-1479`).
- **Silently fall back for unknown graph retriever:** alternative: startup/config failure (`engine/search/retrieval.py:103-109`).
- **Drop source facts when an observation supersedes them:** alternative: return synthesis and evidence in separate channels (`api/http.py:397-405`).
- **History cap 50:** alternative: time-based or storage-budget retention (`config.py:1581-1582`).
- **Midpoint disposition 3/3/3:** alternative: no disposition until user sets it, or per-request permission (`models.py:317-325`). Kivi explicitly chooses the latter for Daari (`../kivi-semantic-memory-position.md:159-161`).

## 5. Questions this repo never faced

Derived from Kivi’s commitments, not found as first-class questions in Hindsight:

1. How can the write path prove that third-party personal content was used transiently but never became a candidate storage object (`../kivi-semantic-memory-position.md:106-125`)?
2. What representation makes “hypothesis as a question, never a claim” impossible to misuse downstream (`../kivi-semantic-memory-position.md:90-95`)?
3. How is explicit user confirmation represented so observation frequency can never masquerade as permission (`../kivi-semantic-memory-position.md:95-103`)?
4. How can one retrieval run preserve all knowledge while a separate disclosure policy withholds tiers and records what it withheld (`../kivi-semantic-memory-position.md:155-176`)?
5. How can ordinary dictation be structurally incapable—not merely configured not—to load observations/hypotheses (`../kivi-semantic-memory-position.md:181-199`)?
6. What is the durable negative state created by “That’s not me anymore” so the same source corpus cannot regenerate the rejected characterization (`../kivi-semantic-memory-position.md:239-242`)?
7. How are exclusions evaluated on candidate semantics without retaining the excluded candidate itself, while preserving an auditable reason/count (`../kivi-semantic-memory-position.md:47-50`)?
8. What confidence threshold justifies asking for confirmation when prompts consume a weekly user-attention budget, not just tokens/latency (`../kivi-semantic-memory-position.md:218-223`)?
9. What exactly decays: retrieval score, epistemic standing, permission to disclose, or the stored observation itself (`../kivi-semantic-memory-position.md:239-242`)?
10. What negative retrieval evidence must be exposed so “I don’t have it” is verifiable rather than fluent (`../kivi-semantic-memory-position.md:203-216`)?
11. How are work-level facts about another person separated from personal facts about that person when both appear in one sentence or imply each other (`../kivi-semantic-memory-position.md:106-125`)?
12. Can user edits change content without laundering an observed/hypothesized tier into stated truth, and how is that edit event attributed (`../kivi-semantic-memory-position.md:99-103`, `:232-248`)?
13. Does “Forget” erase source text, derived memory, embeddings, history, traces and backups, or create suppression while some audit residue remains (`../kivi-semantic-memory-position.md:244-248`)?
14. How is Daari’s one-request permission cryptographically/transactionally prevented from persisting into the next answer or being written back (`../kivi-semantic-memory-position.md:159-161`)?

## 6. What the tests do not cover

These are decisions for which the inspected tests would still largely pass under a materially different answer.

- **Normative retention boundary:** memory-defense tests prove regex secret detection/redaction/blocking, not health/mood/relationships/politics/character judgments or third-party consent (`tests/test_memory_defense.py:227-401`, `:563-934`). A system retaining Priya’s mother’s illness would pass.
- **Independent type and tier:** tests assert `world|experience|observation`, not `entity|preference|episode × stated|observed|hypothesized` (`tests/test_retain.py:19-2381`). Flattening epistemic tier still passes.
- **Explicit promotion only:** consolidation tests prove automatic observation creation/update/delete and scoping (`tests/test_consolidation.py:1882-3165`); none require user confirmation before an observation is acted on. The opposite policy would need new tests.
- **Non-regrowth after correction:** invalidation/reconsolidation is tested, but no test models a user suppression tombstone that blocks the same pattern from the same transcripts. Kivi’s claim 6 therefore has no precedent (`../kivi-semantic-memory-position.md:281-287`).
- **Disclosure separate from retrieval:** recall fact/tag filtering and reflect includes are tested, but no test proves all tiers were retrieved, one was withheld by permission, and that withholding was traced. Kivi’s claim 4 remains uncovered (`../kivi-semantic-memory-position.md:283-285`).
- **Structural dictation isolation:** Hindsight has a generic recall path with filters; no test proves a dictation code path lacks physical/logical access to observation storage. Kivi’s claim 7 remains uncovered (`../kivi-semantic-memory-position.md:287`).
- **Actionable abstention:** empty retrieval and reflect errors are exercised, but no black-box test distinguishes “searched these scopes and found only these near misses” from generic no-answer behavior. A plausible generated guess may pass unrelated response tests.
- **Ranking values:** tests usually verify order on constructed examples and formula mechanics; they do not establish that 0.3 similarity, 0.7 link threshold, 60 RRF constant, 365-day window or low/mid/high budgets optimize user outcomes (`tests/test_combined_scoring.py:1-740`, `tests/test_interleave_fusion.py:1-260`, `tests/test_fusion_cap.py:1-180`). These are precedent, not evidence.
- **Cross-model extraction stability:** real-LLM judge tests check selected interpretation criteria, but replacement can still produce fewer facts from a longer transcript—as issue #3989 demonstrated. Delta tests establish mechanical preservation, not semantic equivalence across model/version/prompt changes (`tests/test_delta_retain.py:59-987`).
- **Entity false-merge cost:** resolver tests cover named cases and thresholds, but do not test downstream privacy/disclosure damage from merging two real people with similar names (`tests/test_entity_resolver.py:1-1200`, `tests/test_entity_resolution_eval.py:1-500`).
- **History semantics:** tests cover recording/capping/transfer, not whether 50 versions are sufficient, whether history should decay, or whether a user who forgets a memory expects history deletion.
- **Concurrent scan meaning:** the code declares cursor scans non-snapshot (`engine/memories/base.py:241-248`); tests can validate pagination mechanics without distinguishing eventual-complete browsing from a consistent audit export.
- **Fallback transparency:** semantic-only fallback preserves recall availability on text-search failure (`engine/search/retrieval.py:330-369`), but tests do not establish whether callers/users should be told one retrieval arm failed. Kivi’s legibility principle makes that difference observable.

## Bottom line of the map

Hindsight offers strong precedents for fact extraction with provenance, hybrid retrieval, derived observations, configurable storage/retrieval seams, replay safety and failure recovery. Its most valuable evidence is where those answers broke: task-independent fusion, replace-as-retry, flattened identities, asynchronous commit ordering, implicit invalidation and malformed destructive model output.

It offers little evidence for Kivi’s defining decisions: normative non-retention, independent epistemic tiers, disclosure permissions, explicit promotion, suppression against re-derivation, user-facing abstention and structural separation of dictation from reflective memory. On those points Hindsight is a mechanism catalogue, not an answered precedent.

## External history sources

1. vectorize-io/hindsight, [Issue #3989: failed retain and non-idempotent re-extraction](https://github.com/vectorize-io/hindsight/issues/3989), September 2026.
2. vectorize-io/hindsight, [Issue #4152: malformed consolidation deletes and invisible failure](https://github.com/vectorize-io/hindsight/issues/4152), September 2026.
3. vectorize-io/hindsight, [PR #4234: remove free-threaded Python and multi-loop serving](https://github.com/vectorize-io/hindsight/pull/4234), September 2026.
