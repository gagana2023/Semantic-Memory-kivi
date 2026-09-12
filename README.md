# Kivi

Kivi is a local, single-user text client for durable work memory. It turns eligible user dictations into typed, inspectable memories and uses them to answer Hey Kivi requests with source provenance. It deliberately does not provide speech recognition, external calendar integration, hosted storage, multiple users, autonomous actions, or a general-purpose assistant.

**Submission map**

| Brief item | Where |
|---|---|
| Product positioning statement and vision | [kivi-semantic-memory-position.md](kivi-semantic-memory-position.md) (§3 is the positioning statement; §1–9 the vision) |
| Design and specification | [DESIGN.md](DESIGN.md), [SPECIFICATION.md](SPECIFICATION.md), [DECISIONS.md](DECISIONS.md) |
| Source code | [src/kivi/](src/kivi/) — API, services, storage, worker, evaluation, CLI, templates |
| Schema and migrations | [migrations/](migrations/) |
| Seed data | [fixtures/development-500.json](fixtures/development-500.json), regenerable with [generate_corpus.py](generate_corpus.py) |
| Corpus and evaluation | [CORPUS.md](CORPUS.md), [PERSONA.md](PERSONA.md), [EVAL_QUESTIONS.json](EVAL_QUESTIONS.json), [GROUND_TRUTH.json](GROUND_TRUTH.json) |
| Generated results | [results.json](results.json), [summary.md](summary.md), [evaluation-sensitivity.md](evaluation-sensitivity.md), [evaluation-after-fixes.md](evaluation-after-fixes.md) |
| Limitations | [LIMITATIONS.md](LIMITATIONS.md) |
| How to run / review | [RUN.md](RUN.md) |

`research/`, `extracted/`, `merged/`, `clusters.json`, `build_merged.py`, `MERGED_INVENTORY.md`, and `RESOLUTIONS.md` are the literature-survey working files behind the design decisions; they are not needed to run or review the system.

## Use cases

Hey Kivi can recall facts and episodes from work history, combine evidence from separate dictations, distinguish current from historical facts, draft grounded text, and create internal schedule entries. Its v1 tool surface is limited to `recall_search`, `draft_reply`, and `schedule_reschedule`; scheduling has no external side effect.

Dictation and Hey Kivi are separate entry points with different memory rights. Ordinary dictation writes the user's text and queues learning, but may use only lexical/entity spelling memory and stated formatting preferences while writing. It cannot silently invoke semantic recall. Hey Kivi may retrieve semantic memory, subject to the active Anbu/Koottu disclosure policy, but an evaluation question is never ingested as memory.

## Architecture

Kivi runs as one FastAPI/Uvicorn process beside a local Ollama daemon. SQLite in WAL mode is the sole authority; FTS5 supplies lexical retrieval, and model output is treated as stateless computation rather than stored truth.

```text
                         local machine

  Dictation / import                         Hey Kivi
         |                                      |
         v                                      v
  validate + persist source              freeze request state
         |                                      |
         v                                      v
  durable ordered job                    retrieve candidates
         |                               FTS + entity links
         v                                      |
  Ollama structured extraction                  v
         |                               support qualification
         v                               + near-miss decisions
  admission gates                              |
         |                                      v
         v                               permission disclosure
  consolidate / version / supersede      Anbu / Koottu / Daari
         |                                      |
         +------------------+-------------------+
                            v
                     SQLite + FTS5
       transcripts | jobs | memories | versions | evidence
       retrieval candidates | decisions | traces | actions
                            |
                            v
                 answer + citations + Why trace
```

The write path first commits the original transcript, then processes it in event-time order. Ollama proposes atomic `entity`, `preference`, or `episode` candidates. Deterministic admission gates reject invalid, prohibited, incomplete, or unsafe candidates before storage. Accepted memories retain versions and source evidence; exact repeats merge provenance rather than inflating the memory count.

The read path retrieves before applying permission. Candidate memories are qualified as support or near misses, then disclosure determines what may be used, withheld, or presented as an observation or question. An answer abstains when the requested fact is not supported. Current implementation gaps are reported below rather than hidden.

Core state consists of source `transcripts`, durable `jobs`, typed `memories`, `memory_versions`, `memory_evidence`, lifecycle/suppression records, FTS projections, and interaction traces. A memory's evidence rows link directly back to the original record IDs. Decision traces link a request to retrieval candidates and disclosure outcomes; the evaluation artifact expands those links with citations, exclusions, timings, model usage, and cost. The `inspect-memory` command exposes memory type, creation time, status, and provenance without requiring schema knowledge.

See [DESIGN.md](DESIGN.md) for the complete contracts, trade-offs, schema design, and failure behavior.

## How to run it

Follow the single supported setup, operation, inspection, evaluation, and reset path in [RUN.md](RUN.md).

## Evaluation

The checked-in development corpus contains 500 user-authored records spanning 5 January through 30 June 2026. Each record includes a stable ID, degraded raw ASR, corrected text, occurrence time, and source metadata. The corpus intentionally mixes sparse planted signal with mundane acknowledgements, corrections, draft operations, reminders, duplicates, name ambiguity, reversals, and an unresolved contradiction. See [CORPUS.md](CORPUS.md) and `GROUND_TRUTH.json`.

The 52 evaluation cases test distributed recovery, superseded facts, demonstrated preferences, episodic reconstruction, grounded refusal, duplicate evidence, and entity disambiguation. The evaluator starts from a clean database, processes every corpus record through the durable ingestion worker, and invokes the production Hey Kivi retrieval/disclosure path without storing evaluation questions as transcripts.

### Results

| Class | Before fixes | After fixes | Change |
|---|---:|---:|---:|
| Distributed recovery | 10/22 (45.5%) | 15/22 (68.2%) | +5 |
| Superseded facts | 0/8 (0.0%) | 0/8 (0.0%) | 0 |
| Demonstrated preferences | 0/8 (0.0%) | 0/8 (0.0%) | 0 |
| Episodic retrieval | 0/3 (0.0%) | 1/3 (33.3%) | +1 |
| Unanswerable | 1/11 (9.1%) | 8/11 (72.7%) | +7 |
| **Overall** | **11/52 (21.2%)** | **24/52 (46.2%)** | **+13** |

No class regressed in this round. The unanswerable result comprises eight correct refusals and three fabrications.

The weak classes are findings about specific mechanisms:

- **Superseded facts: 0/8.** The run created no superseded memory. Old and new statements were often omitted during extraction or emitted with incompatible semantic keys, so consolidation could not establish a current-versus-stale relationship. The evaluator requires persisted supersession evidence and does not award text-only passes.
- **Demonstrated preferences: 0/8.** No evidence-backed observed pattern was consolidated across independent records. Text-only extraction also lacks the application/channel scope needed by several expected patterns, and default Anbu does not disclose observed content.
- **Episodic retrieval: 1/3.** Required event fragments were omitted at ingestion in the remaining cases, so later retrieval could not reconstruct the complete episode with required provenance.
- **Unanswerable: 8/11.** Requested-facet support validation removed most weak near matches, improving correct refusals from one to eight. Three cases still accepted unrelated evidence and returned factual content instead of abstaining.

Measured retrieval latency was **7.621 ms p50 / 8.990 ms p95**. End-to-end question latency was **22.096 ms p50 / 28.256 ms p95**. These measurements cover local retrieval and answer assembly after ingestion; extraction model time is accounted for separately in the complete run.

The run made **500** calls to `qwen2.5:7b-instruct`, with **75,091 input tokens** and **9,740 output tokens**. Local model and service cost was **USD 0.00**. The design names `qwen3:8b`, but that model was unavailable on the evaluation host, so this run is diagnostic rather than evidence for the designed model lock.

Database growth was sampled 21 times during ingestion. The SQLite main file grew from **614,400 bytes after record 1** to **892,928 bytes after record 500**, an increase of **278,528 bytes (45.3%)**. The final sampled state contained 500 transcripts, 500 jobs, 81 compiled memories, 114 memory-evidence links, and 116 admission decisions. Per-sample rows and bytes by table are retained in the result artifact.

Every aggregate above is traceable to [results.json](results.json). All failed cases, expected and actual answers, retrieved memories, exclusions, and provenance are printed in [summary.md](summary.md).

## Break tests

Three faults were introduced independently against copies of the same post-fix memory state, measured, and removed:

| Fault | Observed class movement |
|---|---|
| Remove the `entity` memory type from retrieval | Distributed recovery fell **15/22 to 0/22**; episodic retrieval fell **1/3 to 0/3**. Unanswerable improved 8/11 to 9/11 because one false-positive entity match disappeared. |
| Disable supersession | Superseded facts remained **0/8**. This break is not detectable because the baseline already contains no superseded memories. |
| Stop abstaining on empty retrieval | Unanswerable fell **8/11 to 0/11**; the other class totals did not move. |

The first and third breaks demonstrate that the evaluator can lose class-level passes when their mechanisms are removed. The no-movement supersession break is a failed sensitivity precondition, not positive evidence: there is no working supersession baseline to break. Full mutation results are in [evaluation-after-fixes.md](evaluation-after-fixes.md).

## Limitations

The current build does not establish supersession reliably, does not consolidate demonstrated preferences, leaves two episodic cases incomplete, and fabricates in three unanswerable cases. Its semantic embedding leg is unavailable in the measured path, so retrieval is primarily lexical/entity-based. The run also used an installed model different from the design's intended locked model.

Some failures follow deliberate design boundaries rather than implementation bugs: application metadata is excluded from semantic extraction; Anbu withholds observed preferences; and flat mandatory provenance can reject an answer supported by an alternative sufficient source set. The mechanism, rationale, remediation cost, and conditions that would justify each change are documented in [LIMITATIONS.md](LIMITATIONS.md).

## AI use

Part One — the product positioning and vision in [kivi-semantic-memory-position.md](kivi-semantic-memory-position.md) — was written by me without generative AI.

Generative AI (Claude, through Claude Code) was used, under the design decisions I made and recorded in [DESIGN.md](DESIGN.md) and [DECISIONS.md](DECISIONS.md), for:

- **Literature survey scaffolding** — extracting decision spaces from memory-system papers into `extracted/` and merging them in `merged/` for me to resolve.
- **Implementation** — the Python source, migrations, templates, and tests, with the rule that no design decision is made during implementation (see `CLAUDE.md`).
- **Corpus generation** — `generate_corpus.py` and the 500-record development corpus, from the persona and planted-signal plan I specified in [PERSONA.md](PERSONA.md) and [CORPUS.md](CORPUS.md).
- **Evaluation construction** — the 52 questions and ground truth, and the evaluator/report code.
- **Documentation drafting** — README, RUN.md, and LIMITATIONS.md, which I reviewed against the running system.

All evaluation numbers come from running the checked-in code locally; none were produced or edited by a model.
