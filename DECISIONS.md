# Implementation decisions

## 2026-09-12 — Release review import boundary

- Chose: an operator-only `python -m kivi import-corpus` command validates the corpus locally, then drives the running server's public `/v1/imports` API and polls it to a terminal state.
- Alternative: direct SQLite seed/import writes or a dashboard-only import procedure.
- Why: it makes the documented review route a real end-to-end path while preserving the API's validation, provenance, jobs, and decision traces; direct database writes would evade the product contract.

## 2026-09-12 — Local model lock procedure

- Chose: generate and verify a machine-local `config/model-locks.json` from `ollama list`; mismatch and missing-model states fail loudly.
- Alternative: trust mutable model tags or commit a digest that cannot be verified on this machine.
- Why: the design requires digest verification, while no local Ollama inventory was available to truthfully commit a digest. The operator-generated lock provides inspectable evidence without fabricating one.

## 2026-09-12 — Evaluation leakage guard

- Chose: record every fixed evaluation case as a durable failure with `EVALUATION_PUBLIC_CONTRACT_PATH_UNAVAILABLE` until an isolated public-contract adapter can execute it without persisting evaluation prompts as transcripts.
- Alternative: invoke `/v1/hey-kivi` directly and remove the resulting transcripts, or report passing fixture outcomes without execution.
- Why: removing them violates durable-source history and leaving them violates AC-FR-32's explicit leakage guard. A truthful visible failure is safer than a fabricated pass.

## 2026-09-12 — Milestone 2 projection repair boundary

- Chose: commit admitted memory lexically with a durable `projections.pending` record when embedding projection is unavailable.
- Alternative: reject an otherwise valid memory until embedding succeeds.
- Why: a projection outage must not fabricate an embedding or lose durable source/provenance; a real projection-repair worker remains required before claiming complete Milestone 2.

## 2026-09-12 — Import validation behavior

- Chose: reject only malformed import records and continue valid records; conflict under an existing transcript ID fails the whole request with `409`.
- Alternative: reject every mixed batch or silently reuse conflicting source content.
- Why: this follows AC-FR-04's no-silent-discard rule and AC-FR-05's content-conflict safety boundary.

## 2026-09-12 — Thin-slice extraction delivery

- Chose: queue extraction in an in-process asyncio task after the dictation transaction commits.
- Alternative: run extraction synchronously before returning.
- Why: the milestone requires the written response and transcript ID before real extraction completes, while SQLite exposes durable job state.

## 2026-09-12 — First entity relation contract

- Chose: one strict `name` / `relation` / `value` JSON entity relation from Ollama.
- Alternative: accept free-form model prose or infer a relation in Python.
- Why: strict model output lets the slice fail loudly rather than fabricate an entity.

## 2026-09-12 — Recall behavior with no lexical hit

- Chose: return an explicit grounded abstention.
- Alternative: synthesize an answer or use a non-FTS fallback.
- Why: Milestone 1 permits exact/FTS retrieval only and requires no fabricated return values.

## 2026-09-12 — Milestone 3 unavailable embedding leg

- Chose: record `EMBEDDING_UNAVAILABLE` in the retrieval trace and continue only with the available lexical/one-hop legs.
- Alternative: synthesize a deterministic vector or claim semantic retrieval completed.
- Why: a missing local embedding projection must produce an inspectable degraded retrieval result, never fabricated semantic evidence. The projection worker remains required before Milestone 3 can be claimed complete.

## 2026-09-12 — Internal schedule idempotency

- Chose: require an absolute UTC timestamp and caller-supplied idempotency key before creating an internal event.
- Alternative: interpret relative time or deduplicate on request wording.
- Why: FR-25 prohibits guessed scheduling; a stable explicit key gives repeat requests exactly one durable state change.

## 2026-09-12 â€” Milestone 4 lifecycle windows

- Chose: suppress unpinned observed memories after 90 days and unpinned hypotheses after 30 days; stated and pinned memories never expire automatically.
- Alternative: retain all memories indefinitely or use an unrecorded adaptive score.
- Why: the acceptance criteria require observable lifecycle behavior but do not set windows. Fixed durable windows are inspectable, deterministic, and cannot silently promote or evict stated/pinned evidence.

## 2026-09-12 â€” Memory action concurrency contract

- Chose: every state-changing memory action requires an expected version and idempotency key; a stale version returns `409` and a repeated key returns its original receipt.
- Alternative: last-write-wins actions or deduplication by action text.
- Why: this makes concurrent control changes explicit and gives retries one durable outcome without fabricating a second state change.
