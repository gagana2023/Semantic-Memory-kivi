# Resolutions

**Input:** `MERGED_INVENTORY.md` (924 question entries, 863 unique ids in the contents table, 61 duplicate question texts across ids).
**Authority:** `kivi-semantic-memory-position.md` — fixed, breaks all ties that are otherwise technical.
**Secondary constraint set:** the Golden Goose brief (`Kivi_Golden_Goose_Task_Final.pdf`) — scope, review path, corpus, evaluation.

## How to read this

Each entry is:

- **QUESTION** — verbatim from the inventory.
- **DECISION** — the answer being taken.
- **BECAUSE** — labelled `POSITION` (a specific line in the position document forces it) or `ENGINEERING` (the position is silent; a build constraint forces it). Never both. Where it says `POSITION`, the line is quoted or cited by section.
- **REJECTED** — the strongest alternative, and the condition under which it wins.
- **COST** — what this closes off.
- **CONFIDENCE** — high / medium / low.

### Citation shorthand

| Tag | Meaning |
|---|---|
| `P§1` … `P§9` | Position document, numbered section |
| `P§AppA/B/C` | Position appendices |
| `BRIEF` | Golden Goose assignment PDF |

### Five engineering constraints used repeatedly

These are not in the position document. They come from the brief and from the shape of the build. Where `BECAUSE: ENGINEERING` appears without further explanation, it is one of these.

- **E1 — Single user, single tenant.** The brief supplies "approximately 500 dictations from one user." There is no second user, no sharing, no cross-user transfer, no multi-tenant isolation problem. Every question about cross-user memory, consent between users, or tenant scoping is resolved by scope, not by design.
- **E2 — Reviewer-reproducible or it does not exist.** "A coding agent will clone the submitted commit and follow the primary review method." It will not "infer missing setup, perform undocumented dashboard work, repair the application." This forces embedded storage, deterministic setup, no external services on the critical path, and a single-process default.
- **E3 — Batch corpus import is the primary write path.** ~500 records arrive at once via a documented import procedure. Online/streaming ingestion is a secondary convenience. This inverts the usual assumption that per-turn extraction is the main case.
- **E4 — Inspection is a product surface, not a log.** The brief requires an engineer to inspect why memory did or did not affect a result; `P§8` requires the same surface to be legible to a normal user. One artefact serves both. This forbids "silent" anything on any path that can affect an answer.
- **E5 — Narrow and finishable beats broad.** "The system should be narrow enough to finish and complete enough to interrogate." Any decision that adds a subsystem without serving one of the seven claims in `P§AppC` loses by default.

### The standing rule for out-of-scope questions

The inventory was assembled from 45 systems and papers, many of which solve problems Kivi does not have — distributed consistency, causal inference formalisms, training objectives, multi-agent coordination, cross-user knowledge transfer. Those questions still receive a resolution, because a decision not to build is a decision. They are resolved by **E1/E5**, and they are marked so you can see at a glance that the answer is "out of scope" rather than "carefully chosen." That distinction is the point of the exercise; blurring it would make the set look more considered than it is.

---
## Stage: INGESTION

---

### Q08 — What is assumed idempotent and ordered?

- **DECISION:** Transcript ingestion is idempotent on `transcript_id`. Re-processing the same transcript produces the same memory state — no duplicate rows, no inflated `evidence_count`. Ordering is by transcript `occurred_at`, not by arrival time; the importer sorts before extracting. Memory writes carry a deterministic candidate key `(transcript_id, candidate_index)` so a re-run replaces rather than appends.
- **BECAUSE: ENGINEERING (E2, E3).** The reviewer will import a corpus, and may import it twice, or import ours and then theirs. `P§AppC` claim 6 — "a correction demoted a memory and the memory did not regrow on reprocessing" — is only testable if reprocessing is a defined operation with a defined result. It is the position that makes reprocessing *interesting*, but it is the build that makes it *required*.
- **REJECTED:** Append-only ingestion with dedupe at read time. Wins if extraction were expensive enough that re-running is never done, and if evidence counts were computed as a query rather than stored. That is a coherent design; it loses because `evidence_count` and `first_seen_at` are stored fields in `P§4` and are read by the memory surface.
- **COST:** Extraction must be deterministic enough that re-running a transcript yields the same candidate set, which means temperature 0 and a pinned model, and it means a model upgrade is a migration event rather than a config change.
- **CONFIDENCE:** high

---

### Q11 — When the input contains multiple channels or actors, what should determine whose information is eligible for retention?

- **DECISION:** Only the user. Eligibility is determined by the *subject of the fact*, not by the speaker or the channel. A fact is eligible if it is about Meera's work and can be stated without characterising anyone else. Everything else is read into the context window and never reaches the write path.
- **BECAUSE: POSITION.** `P§5`: "Third-party content enters the context window. It does not enter the write path. This is a structural rule, not a filter applied afterward." And the test in `P§5`: "could the fact be about the user's work, stated without characterising the other person? Then it's a candidate. Otherwise it's dropped."
- **REJECTED:** The per-participant trace model (the `creem`/`tracemem` camp): build a separate memory card for each person mentioned, so facts about Priya live in Priya's trace. It is the strongest alternative because it is genuinely more useful — Kivi would know more — and because it keeps the data tidy rather than discarding it. It wins the moment Kivi is a multi-user product where Priya is also a user who consented. Under `P§1`'s non-retention principle and `E1`'s single user, it loses outright.
- **COST:** Kivi can never answer "what's going on with Priya lately." It cannot build a relationship graph richer than role-and-affiliation. If the product later wants team memory, this is a re-architecture of the write path, not a feature flag.
- **CONFIDENCE:** high

---

### Q12 — What events may enter memory: only user statements, selected application events, or the whole agent/tool lifecycle?

- **DECISION:** A purpose-limited subset: (a) user dictations, (b) user Hey Kivi turns, (c) explicit user confirmation/correction events. Application context (the Slack message being replied to, the document being summarised) is *input* and never an extraction source. Kivi's own output, tool calls, and tool results never enter memory.
- **BECAUSE: POSITION.** `P§3`: memories are "the durable, work-level things you would be annoyed to have to repeat" — that is a property of things *the user said*, not of things the system did. `P§4`'s Stated tier is defined as "The user said it, or confirmed it when asked," which has no room for an agent lifecycle event.
- **REJECTED:** Admitting the agent/tool lifecycle as evidence, which is what most of the surveyed agent-memory systems do. It wins if the product's goal were agent self-improvement — learning which tool sequences work. Kivi's goal is removing re-explanation, so the tool lifecycle is telemetry, not memory.
- **COST:** Kivi cannot learn from its own successes and failures. If Kivi drafts a reply and the user sends it unedited fourteen times, that is not evidence of anything, because Kivi's draft is not a memory source. See `Q153` and `Q198` — this is a real loss and I am taking it deliberately.
- **CONFIDENCE:** high

---

### Q16 — What gets discarded, and is discard observable?

- **DECISION:** Discarded: excluded-category candidates, third-party personal content, duplicates of an existing memory (which instead increment evidence), and candidates that fail the work-level test. Every discard is observable — recorded as a row with a reason code, attached to the transcript, surfaced in the transcript's inspection view.
- **BECAUSE: POSITION.** `P§2`: "Dropped candidates are logged with the reason. The extraction log for any transcript can show: *3 candidates extracted, 1 dropped — excluded category: emotional state.* This is how we prove the boundary is real rather than claimed." And `P§5`'s "read, not kept" marker.
- **REJECTED:** Invisible rejection (the `Q199` camp — "excluded capture disappears before spool/log/storage"). It is genuinely the safer privacy posture: a drop log about emotional state is itself a record that the system noticed something about the user's emotional state. It wins if the drop log were retained in full content. It loses here only because the log stores a **reason code and a count, never the dropped content**. That qualification is doing real work and is recorded in `Q199` and `Q102`.
- **COST:** The drop log is a metadata trail about sensitive categories. It must be non-content by construction, which means a reviewer cannot audit whether the classifier was *correct* on a specific drop — only that a drop happened and what category was claimed.
- **CONFIDENCE:** high

---

### Q20 — When a candidate concerns sensitive or third-party material, should it be transformed, retained privately, logged-and-dropped, or prevented from entering storage?

- **DECISION:** Both, in a fixed order. Prevented from entering storage — the check runs on candidates before the write, so the material is never persisted — and the *fact of the drop* is logged as a non-content record. Not transformed. Not retained privately.
- **BECAUSE: POSITION.** `P§2`: "Exclusions are enforced by a check that runs on candidate memories, not by a line in a prompt hoping for good behaviour." `P§5`: "It does not enter the write path."
- **REJECTED:** Transformation/anonymisation — keep the shape of the fact with the person removed. It is strictly more useful and is what several surveyed systems do. It wins if the value of the anonymised residue exceeds the cost of a boundary you can no longer state in one sentence. The position's whole trust argument is that the boundary is demonstrable; "we keep a transformed version" is not demonstrable in a single screen, so it loses on legibility, not on privacy.
- **COST:** Kivi throws away information it could have safely kept in anonymised form. Some genuinely useful work-level facts will be over-dropped because they cannot be phrased without reference to a person.
- **CONFIDENCE:** high

---

### Q24 — What changes over time automatically?

- **DECISION:** Three things, and nothing else. (1) Observations decay: an observation not re-observed within its window loses standing and stops being surfaced. (2) Hypotheses expire: an unconfirmed hypothesis not re-raised within its window is dropped. (3) Recency ranking shifts as time passes. Stated memories never change automatically. Nothing ever promotes automatically.
- **BECAUSE: POSITION.** `P§9`: "Observations decay… Behaviour from six months ago should not be presented as who you are" and "Hypotheses expire by default." `P§4`: "Nothing self-promotes. An observation does not become stated because it was seen twenty times."
- **REJECTED:** No automatic change at all — the `MemOS`-style camp where nothing decays, expires, promotes, or demotes, and staleness is handled purely at retrieval ranking. It wins if decay windows cannot be set honestly from corpus data, which `P§AppB` admits is currently the case. This is the strongest argument against, and I am taking the decision anyway because decay is a *claim the product makes to the user*, and ranking-only staleness cannot be shown on the memory surface.
- **COST:** Two parameters (`observation_decay_window`, `hypothesis_expiry_window`) must be set before there is corpus evidence to set them. They will be wrong initially. They must therefore be configuration, not constants, and the evaluation must report sensitivity to them.
- **CONFIDENCE:** medium — high on *what* decays, medium on it being right to ship decay before the corpus can calibrate it.

---

### Q26 — How are results ordered, and where does priority enter?

- **DECISION:** Hybrid retrieval (lexical + vector) fused by reciprocal rank, then a deterministic re-rank on: tier (stated above observed above hypothesised), evidence count, and recency. Priority enters *after* fusion, in code, never inside the model. The dial does not touch ordering at all — it filters at disclosure time.
- **BECAUSE: POSITION.** `P§6`: "The dial governs disclosure, not retrieval. Kivi always retrieves everything it has." That forces ordering and permission to be separate stages, which in turn forces priority to be a post-retrieval deterministic step so that the withheld set is computable and reportable.
- **REJECTED:** A learned or LLM re-ranker. It wins on quality at ~500 memories and would likely improve answers. It loses because `P§8`'s Why panel must state *why* a memory ranked where it did, and "the model preferred it" is not a reason a normal user can act on.
- **COST:** Ranking quality is capped by hand-tuned weights. There is no path to learning from user behaviour without reopening this.
- **CONFIDENCE:** high

---

### Q27 — What does the caller see on no match or partial failure?

- **DECISION:** No match is a first-class successful result carrying what was searched and what was found nearby — not an error and not an empty list. Partial failure (one retrieval leg down) is surfaced explicitly in the trace and degrades the answer to abstention rather than answering from the surviving leg silently.
- **BECAUSE: POSITION.** `P§8`: "Kivi says what it doesn't have, and shows what it looked for. Not 'I'm not sure' — that's a shrug." And the worked abstention example, which returns near-misses with counts. Also `P§8`: "The trace exists for abstentions too."
- **REJECTED:** Silent degradation — answer from whatever leg survived. It wins on availability, and every surveyed system does it. It loses because an answer built on half the index is indistinguishable from a full one, which is exactly the failure `P§8` calls "worse than no answer."
- **COST:** Kivi will abstain in cases where it could have answered correctly from the surviving leg. Availability is traded for honesty, and the evaluation will show abstentions that look like misses.
- **CONFIDENCE:** high

---

### Q28 — What happens to raw input after it's been used?

- **DECISION:** Raw transcripts are kept in full, permanently, as the provenance substrate. They are not memories and are never retrieved as memories — they are only reachable by following a memory's `source_transcript_ids[]`.
- **BECAUSE: POSITION.** `P§9`: "Every memory shows its provenance. Not a category label — the actual transcript, with a date, that produced it." You cannot show a transcript you deleted.
- **REJECTED:** Discard raw after extraction, keeping only claims plus a provenance stub (see `Q186`). It wins on storage, and more importantly on privacy — the strongest form of "read, not kept" would be not keeping the transcript containing Priya's mother at all. This is a real tension with `P§5` and it is logged in **Section B, conflict B2**.
- **COST:** The corpus of raw transcripts contains all the third-party personal content the memory layer refuses to retain. The trust claim is "it did not enter *memory*," not "it was destroyed." That is a narrower claim than the product's language implies.
- **CONFIDENCE:** medium — high that transcripts must be kept, medium that the position's rhetoric survives it intact.

---

### Q33 — When interaction history outgrows the active context, what should become the durable unit of memory: raw history, lossy summaries, extracted facts, or versioned task states?

- **DECISION:** Extracted, typed facts — entity, preference, episode — each with tier, evidence count, and source pointers. Not summaries. Not versioned task state.
- **BECAUSE: POSITION.** `P§4` defines the unit of memory as a typed record with `type`, `tier`, `content`, `evidence_count`, `source_transcript_ids[]`, `first_seen_at`, `last_confirmed_at`, `status`. A summary has no tier and no evidence count, so it cannot carry the epistemics the entire product rests on.
- **REJECTED:** Model-authored rolling summaries as the primary semantic unit. It wins on recall breadth — summaries capture texture that discrete facts lose — and it is cheaper. It loses because `P§9` requires every belief to be individually correctable, and you cannot demote a sentence inside a summary.
- **COST:** Anything that is not expressible as a discrete typed fact is not remembered. Narrative context, the *feel* of how a project went, sequences of related events — all lost. `P§3` accepts this explicitly ("Not insight").
- **CONFIDENCE:** high

---

### Q54 — When memory grows, what should be discarded or lose standing?

- **DECISION:** Nothing is discarded. Things lose standing: undecayed observations lose surfacing rights, unconfirmed hypotheses expire and are dropped, superseded facts move to history. Stated memories never lose standing except by user action.
- **BECAUSE: POSITION.** `P§9`: "Contradictions supersede. New evidence doesn't stack alongside old evidence; it replaces it, and the superseded version stays in history so the change is auditable." And `P§4`: "Demotion and supersession are ordinary operations, not deletions."
- **REJECTED:** Capacity-driven eviction — an LRU or salience-based forgetting policy, which several surveyed systems implement. It wins at a scale Kivi will not reach: ~500 transcripts yields memories in the low hundreds. At that size eviction is a solution to a problem the product does not have (`E5`).
- **COST:** Growth is unbounded in principle. At 50,000 transcripts the memory surface becomes unusable and retrieval precision degrades, with no mechanism in place to address it.
- **CONFIDENCE:** high for this build, low as a permanent answer.

---

### Q61 — Whose facts is the system storing?

- **DECISION:** The user's, exclusively. One subject. Facts *mentioning* other people are stored only in their role-relative form (*Priya is the Acme client contact*), which is a fact about Meera's working world.
- **BECAUSE: POSITION.** `P§1` principle 2: "Non-retention of others. Kivi encounters other people constantly… It works with them and does not keep them." `P§5` gives the exact permitted residue.
- **REJECTED:** Symmetric per-speaker stores (the `LoCoMo`-style camp). It wins in a conversational-agent product where both parties are users. Under `E1` there is no second user to store.
- **COST:** The role facts Kivi does keep are still facts about a named third party who did not consent. The boundary is "work-level and non-characterising," not "nothing about other people." That is defensible but it is not the clean line the product language suggests. Logged in **Section B, conflict B1**.
- **CONFIDENCE:** high

---

### Q62 — When does extraction run relative to the interaction?

- **DECISION:** Asynchronously, after the response is delivered, in a queue the importer also drives. Never on the critical path of a dictation or a Hey Kivi answer.
- **BECAUSE: ENGINEERING (E3).** Batch corpus import is the primary write path, so extraction has to be a queue-driven worker regardless. Once it is a worker, running it inline for live turns is a second code path serving no product claim. The brief also requires latency reporting, and putting an extraction LLM call inside the response path would dominate it.
- **REJECTED:** Synchronous per-exchange extraction, so a fact stated in turn N is available in turn N+1. It wins in a live conversational demo, where the lag is visible and feels like forgetting. This is a genuine product risk and is mitigated, not solved, by `Q269`'s inline-correction path, which writes synchronously because a correction must stick immediately.
- **COST:** There is a window in which Kivi has heard something and does not yet know it. Two write paths exist after all — the async extractor and the synchronous correction path — and they must not race.
- **CONFIDENCE:** medium

---

### Q01 — Which interaction content should be eligible to enter durable memory: user messages only, both sides of the dialogue, or a purpose-limited subset?

- **DECISION:** A purpose-limited subset of user-authored content only: dictations, Hey Kivi requests, and confirmations/corrections. Not both sides.
- **BECAUSE: POSITION.** `P§4`'s Stated tier: "The user said it, or confirmed it when asked." Kivi's own output is neither. `P§3`: what deserves remembering is "the durable, work-level things *you* would be annoyed to have to repeat."
- **REJECTED:** Both sides of the dialogue. It wins where the assistant's output is a negotiated artefact carrying user intent — for example, a draft the user accepted is arguably a stated preference expressed by acceptance. This is the strongest version of the counter-argument and it is why `Q153` and `Q198` are worth reading as a pair.
- **COST:** Acceptance is not evidence. Kivi cannot learn from what the user approved, only from what the user said. This makes the observed tier thinner than it could be.
- **CONFIDENCE:** high

---

### Q55 — When stored material concerns people other than the primary user, what should enter durable memory?

- **DECISION:** Only the role-and-affiliation residue needed to identify the person in the user's working world: name, role, organisation, project association, and canonical spelling. Nothing else — no state, no circumstance, no characterisation, no history.
- **BECAUSE: POSITION.** `P§5`: "What survives is the work-level residue about *your* world, derived and not copied: *Priya is the Acme client contact.* … Not *Priya's mother is ill.* Not *Priya seemed annoyed.*"
- **REJECTED:** Nothing at all about third parties. It is the only fully clean position and it is tempting. It loses because the dictation path needs `Priya Raghavan` spelled correctly (`P§7`), which is itself a retained third-party fact. The boundary is therefore drawn at *characterisation*, not at *mention*.
- **COST:** The trust claim requires a qualifier every time it is stated. "Kivi doesn't keep other people" is false as written; "Kivi keeps only what it needs to spell your colleague's name and know their role" is true and less quotable.
- **CONFIDENCE:** high

---

### Q70 — At what temporal granularity should durative memories be segmented?

- **DECISION:** No fixed segmentation. Episodes carry the event's own timestamp and, where the transcript states one, an explicit validity interval. There are no time buckets.
- **BECAUSE: ENGINEERING (E5).** The position is silent on granularity. Fixed slicing exists to make temporal reasoning tractable at scale; at ~500 transcripts a direct timestamp comparison is exact and cheaper than any bucketing scheme, and bucketing introduces boundary artefacts the evaluation would then have to explain.
- **REJECTED:** Fixed one-month slices (the surveyed answer, itself flagged by its authors as possibly wrong). It wins at corpus sizes where per-episode temporal joins are too expensive, which is orders of magnitude above this build.
- **COST:** No cheap way to answer "what was going on in March" as an aggregate. Such questions become retrieval over individual episodes and may miss.
- **CONFIDENCE:** high

---

### Q72 — How deterministic must model output be?

- **DECISION:** Extraction: fully deterministic contract — temperature 0, pinned model, strict typed output (tool-call/JSON schema), and a hard parse failure on malformed output rather than a salvage attempt. Generation: not deterministic, but every memory it cites must be a retrieved record, never a generated one.
- **BECAUSE: ENGINEERING (E2, and `Q08`).** Idempotent reprocessing and the `P§AppC` claim-6 test both require that the same transcript yields the same candidates. The position does not specify determinism; it specifies a consequence that requires it.
- **REJECTED:** Regex-parsed free-text output, which is what one surveyed system does. It wins when the model has no reliable structured-output mode. It loses on every other axis.
- **COST:** Locked to models with reliable structured output, and a model change invalidates prior extractions.
- **CONFIDENCE:** high

---

### Q73 — Where is privacy enforced?

- **DECISION:** On the write path, in code, as a check that runs on each extracted candidate before persistence. Not in the prompt. Not at retrieval. Not at rendering.
- **BECAUSE: POSITION.** `P§2`: "Exclusions are enforced by a check that runs on candidate memories, not by a line in a prompt hoping for good behaviour." `P§5`: "This is a structural rule, not a filter applied afterward."
- **REJECTED:** Prompt-level and retrieval-level enforcement, which is what almost every surveyed system does. It wins when the categories are too fuzzy for a classifier to decide, which is partly true — "emotional state" is not crisply separable from "work context." The position takes the position anyway, and the cost is real.
- **COST:** A classifier will over- and under-drop. Over-dropping loses useful facts silently (mitigated by the drop log). Under-dropping is a trust breach with no second line of defence, because there is deliberately no retrieval-time filter to catch it.
- **CONFIDENCE:** high on placement, medium on the classifier being good enough to be the only gate.

---

### Q74 — How are facts serialized?

- **DECISION:** Typed columns for everything the product reasons about (`type`, `tier`, `status`, `content`, `evidence_count`, `first_seen_at`, `last_confirmed_at`), with a separate join table for `source_transcript_ids`. JSON only for genuinely open payloads. Not a JSON blob.
- **BECAUSE: POSITION.** `P§7`: "two separate retrieval paths, not one path with a filter. The dictation path… has no access to the observation or hypothesis tables at all. This is enforceable in the schema." A blob is not enforceable in a schema.
- **REJECTED:** JSON-array-in-a-text-column (the surveyed answer). It wins on schema-change velocity during a short build. It loses on the one thing the position asks the schema to prove.
- **COST:** Schema migrations are needed for shape changes, and the brief requires migrations to be committed anyway.
- **CONFIDENCE:** high

---

### Q76 — Is ingestion ordered?

- **DECISION:** Yes. The importer sorts by `occurred_at` and processes serially within a single run. Ordering matters because supersession is "new evidence replaces old" (`P§9`), which is only well-defined if "new" is determined by event time and processed in that order.
- **BECAUSE: POSITION.** `P§9`: "Contradictions supersede. New evidence doesn't stack alongside old evidence; it replaces it."
- **REJECTED:** Unordered parallel ingestion with conflict resolution at read time. It wins on import throughput for a large corpus. At 500 records, serial ordered import takes minutes and removes an entire class of nondeterminism from the evaluation.
- **COST:** Import time is linear and single-threaded. A 50,000-record corpus would be painful.
- **CONFIDENCE:** high

---

### Q81 — What happens when the observer fails?

- **DECISION:** Extraction failure never blocks or degrades the user-facing response. The transcript is marked `extraction_failed` with the error, remains in the queue, and is retried; it is never silently marked processed. The failure is visible in the transcript's inspection view.
- **BECAUSE: ENGINEERING (E4).** The position does not discuss extractor failure. But `E4` forbids silence on anything that can affect an answer, and a transcript that failed extraction is a hole in memory that will later look like forgetting.
- **REJECTED:** Fail-open and mark processed (the surveyed `agent.py` behaviour, where the processed-files insert runs outside the try block). It wins never. It is included because it is the common failure and worth naming as rejected.
- **COST:** A poison record can occupy the queue indefinitely. Needs an attempt cap and a quarantine state — see `Q108`.
- **CONFIDENCE:** high

---

### Q85 — What privacy mechanism is enforceable: delimited redaction, semantic exclusion, or source separation?

- **DECISION:** All three, at different layers, in this order of authority: (1) **source separation** — third-party application context is a structurally separate input channel that the write path cannot read from; (2) **semantic exclusion** — the category check on candidates; (3) **delimited redaction** — literal secret patterns stripped as a backstop.
- **BECAUSE: POSITION.** `P§5` demands source separation ("does not enter the write path"); `P§2` demands semantic exclusion ("a hard exclusion list enforced at extraction"). The position requires the first two and is silent on the third, which is `ENGINEERING` — an API key in a dictation is a liability the position never contemplated.
- **REJECTED:** Semantic exclusion alone. It wins if you trust the classifier completely. Source separation is what makes `P§AppC` claim 2 structurally provable rather than statistically likely, and that is worth a second mechanism.
- **COST:** Three mechanisms to build, test, and explain. The layering is the single most complex thing in the write path.
- **CONFIDENCE:** high

---

### Q86 — Must memory writes be complete, or may partial records enter and be repaired later?

- **DECISION:** Complete or rejected. A candidate missing type, tier, content, or at least one source transcript is a rejected candidate, logged as an extraction defect. No partial rows.
- **BECAUSE: POSITION.** `P§9`: "Every memory shows its provenance." A record without provenance cannot satisfy that and therefore cannot be a memory. The tier field is load-bearing for disclosure (`P§6`), so a record without a tier would be undisclosable.
- **REJECTED:** Admit-then-repair. It wins where ingestion volume makes rejection expensive and a background repairer can fill gaps. Here rejection costs one logged line.
- **COST:** Genuinely useful facts whose extraction was slightly malformed are dropped rather than salvaged. Extraction quality directly caps recall.
- **CONFIDENCE:** high

---

### Q92 — Who judges semantic relationships: deterministic code, an LLM, or a human?

- **DECISION:** Layered. Deterministic code proposes candidates (lexical + vector similarity above a threshold). An LLM judges whether two candidates are the same fact, a contradiction, or unrelated, and its verdict is recorded with model identity, confidence, and the evidence it saw. The human judges only when the verdict would change a *stated* memory — then it becomes a confirmation prompt.
- **BECAUSE: POSITION.** `P§4`: "Promotion requires an explicit user confirmation event, which is itself recorded with a timestamp." That reserves the human for the one place authority matters, and `P§8`'s rationed prompts forbid asking them about everything else.
- **REJECTED:** Pure deterministic matching on normalised strings. It wins on explicability — every merge decision would be inspectable without model provenance. It loses because "Priya is the client contact" and "Priya Raghavan handles the Acme account" are the same fact and no string rule catches that.
- **COST:** Merge decisions are model-dependent, so they are part of what a model upgrade invalidates. The Why panel has to render an LLM verdict in a way a normal user can read.
- **CONFIDENCE:** medium

---

### Q96 — What happens under local write contention?

- **DECISION:** SQLite in WAL mode, single writer, bounded retry with backoff on busy, and a queue depth cap that returns a clear error rather than blocking indefinitely.
- **BECAUSE: ENGINEERING (E2).** The position is silent. Embedded storage is forced by the reviewer-reproducibility constraint; WAL plus single-writer is the standard correct configuration for that choice.
- **REJECTED:** A server database with real concurrency. It wins if the primary review method were hosted or containerised with a managed database, which the brief permits. It loses because it adds a required process to `RUN.md`.
- **COST:** Write throughput ceiling. Import cannot be parallelised (which `Q76` already accepted).
- **CONFIDENCE:** high

---

### Q97 — Is memory ingestion a push (caller submits) or a pull (system watches a source)?

- **DECISION:** Push. A documented import endpoint/command that the caller invokes with a corpus. No directory watcher, no polling.
- **BECAUSE: ENGINEERING (E2).** The brief requires "the exact procedure for importing another corpus." A push command is a procedure; a watcher is a behaviour the reviewing agent has to discover and trust.
- **REJECTED:** A watched folder, which is more pleasant in daily use. It wins for a real product with ongoing dictation. It loses the review path.
- **COST:** No ambient ingestion. Live dictation in the demo client must explicitly call the same push path.
- **CONFIDENCE:** high

---

### Q98 — Does the system accept any modality, or only the modality it can reason about carefully?

- **DECISION:** Text only. Transcript records (raw ASR + LLM-formatted output + metadata) and text application context. No audio, no images, no documents.
- **BECAUSE: POSITION.** The scope note at the head of the position document: "this document assumes a text client… No speech recognition and no spoken output."
- **REJECTED:** Broad modality acceptance (one surveyed system takes 27 file extensions). It wins for a general knowledge product. It is explicitly out of scope here and also excluded by the brief ("You do not need to build speech recognition").
- **COST:** None for this build. For the real product, the entire extraction contract assumes text and would need revisiting for audio-native input.
- **CONFIDENCE:** high

---

### Q99 — Is a memory a typed record or an untyped blob with tags?

- **DECISION:** A typed record. `type` ∈ {entity, preference, episode} and `tier` ∈ {stated, observed, hypothesised} are both required columns.
- **BECAUSE: POSITION.** `P§4` is the two-axis model, and the whole of `P§6` and `P§7` reads those two axes to decide disclosure and path access. This is the least optional decision in the inventory.
- **REJECTED:** Untyped blob with tags. It wins when the ontology is unknown and must be discovered. Here it is decided in advance and is the product.
- **COST:** A fact that is not cleanly one of three types has to be forced into one. Type boundaries will be argued about (see `Q142` and **Section A**).
- **CONFIDENCE:** high

---

### Q102 — What is dropped at ingest, and is the drop recorded?

- **DECISION:** Dropped at ingest: nothing. Truncation and size limits do not apply — the corpus is dictation-sized. Drops happen at *extraction*, not ingest, and are recorded as reason-coded non-content rows (see `Q16`).
- **BECAUSE: ENGINEERING (E3).** The position speaks to extraction drops, not ingest drops. Records are short; there is no truncation problem to solve.
- **REJECTED:** Length truncation at ingest (the surveyed answer: 10,000 characters). It wins for arbitrary document ingestion. Here it would be a silent lossy step on the provenance substrate, which `Q28` forbids.
- **COST:** A pathologically long imported record could be expensive to extract from. Needs a guard that fails loudly rather than truncating quietly.
- **CONFIDENCE:** high

---

### Q107 — Is the HTTP surface authenticated?

- **DECISION:** Bound to localhost by default, with no auth in the default local review arrangement, and a required token if the arrangement is hosted. The destructive reset endpoint is not exposed over HTTP at all — it is a CLI command.
- **BECAUSE: ENGINEERING (E2).** The brief requires "the exact procedure for resetting the system" and a single-user local review path. Auth on a localhost single-user demo is friction with no threat model; a network-exposed wipe endpoint is a real hazard regardless of threat model.
- **REJECTED:** Full auth everywhere. It wins the moment the primary review method is hosted, which is a permitted arrangement — so this decision is coupled to `Q297`/deployment choice and is not independent.
- **COST:** Choosing hosted later means adding auth, which was deferred rather than designed.
- **CONFIDENCE:** medium

---

### Q108 — On extraction failure, is the input retried, quarantined, or dropped?

- **DECISION:** Retried with backoff up to a cap, then quarantined with the error preserved and the transcript visible as unprocessed. Never dropped, never silently marked processed.
- **BECAUSE: ENGINEERING (E4).** Same reasoning as `Q81`. A quarantined transcript is a known hole; a dropped one is an unknown one, and unknown holes look like the product forgetting.
- **REJECTED:** Drop-and-mark-processed. Wins never; named because it is the default accident.
- **COST:** Quarantine is a state the memory surface has to be able to explain to a normal user without a developer console (`P§9`: "No developer console anywhere in this").
- **CONFIDENCE:** high

---

### Q109 — What happens when the model doesn't call the tool?

- **DECISION:** It is an explicit outcome, not a null. Extraction has a first-class "extracted nothing" result (`Q171`) distinguished from "failed to produce output," which is a defect. On the Hey Kivi side, a turn where no tool was called is recorded in the trace as such.
- **BECAUSE: POSITION.** `P§AppA`: the corpus must contain "transcripts that produce nothing." If producing nothing were indistinguishable from failing, that corpus requirement would be untestable.
- **REJECTED:** Treating no-call as a no-op (the surveyed answer: "Nothing happens and nobody knows"). Wins never under `E4`.
- **COST:** Two outcome codes where one would do, and the evaluation must report both.
- **CONFIDENCE:** high

---

### Q128 — What participant information should affect meaning?

- **DECISION:** Only identity-and-role: who the user is (always Meera), and for third parties, name/role/organisation as `Q55` permits. Nothing about a participant's state, style, or disposition affects how a memory is interpreted.
- **BECAUSE: POSITION.** `P§2`'s exclusion list forbids "any characterisation of the person's competence or character," and `P§5` forbids characterising third parties. That leaves role as the only permitted participant attribute.
- **REJECTED:** Richer participant modelling — relationship closeness, formality register per person — which would genuinely improve drafting. It wins if the product were allowed to model relationships; `P§2` explicitly excludes "relationships and family."
- **COST:** Kivi cannot adjust register per recipient except through a *stated* preference the user gives it. It will write to a close colleague the same way it writes to a client unless told otherwise.
- **CONFIDENCE:** high

---

### Q131 — What should be optimized during training?

- **DECISION:** Nothing. No model is trained or fine-tuned. All model behaviour comes from pinned hosted models with fixed prompts.
- **BECAUSE: ENGINEERING (E5, E2).** Out of scope. Training introduces a reproducibility burden the reviewing agent cannot satisfy and serves none of the seven `P§AppC` claims.
- **REJECTED:** Fine-tuning an extractor on the corpus. It wins if extraction precision on excluded categories proved unreachable by prompting plus a classifier — that is the one condition that would justify it.
- **COST:** Extraction quality is capped at what prompting and a pinned model can do.
- **CONFIDENCE:** high

---

### Q132 — What is discarded before or during memory construction?

- **DECISION:** Duplicate of `Q16`/`Q102`. Same answer: excluded categories, third-party personal content, failed work-level test, and duplicates (which become evidence increments). All reason-logged, none content-logged.
- **BECAUSE: POSITION.** `P§2`, `P§5`.
- **REJECTED:** See `Q16`.
- **COST:** See `Q16`.
- **CONFIDENCE:** high

---

### Q134 — Should memory be durable and updated over time, or reconstructed per prediction from a fixed corpus?

- **DECISION:** Durable and updated. Memories are persistent rows with lifecycle state, not derived views recomputed at query time.
- **BECAUSE: POSITION.** `P§9` requires user actions — confirm, correct, demote-and-suppress, forget — to persist and to *stick*. A reconstructed-per-query design has nowhere to put a suppression: "deleting the row is useless, because the same pattern will regrow from the same transcripts within a week."
- **REJECTED:** Reconstruct-on-demand from the transcript corpus. It is genuinely attractive — it makes the memory state always consistent with the source, and re-extraction is cheap at this corpus size. It wins in a product with no user-editable memory. `P§9` is the whole reason it loses.
- **COST:** Memory state can drift from what the transcripts would produce today. Two sources of truth exist and their divergence has to be explainable.
- **CONFIDENCE:** high

---

### Q137 — How should old evidence lose influence as the world changes?

- **DECISION:** Two mechanisms, deliberately different. Contradiction → supersession (immediate, evidence-driven, auditable history). Absence of re-observation → decay (time-driven, observations and hypotheses only, never stated facts).
- **BECAUSE: POSITION.** `P§9` states both separately and applies them to different tiers.
- **REJECTED:** A single continuous relevance score combining recency and evidence. It wins on retrieval quality and is simpler to implement. It loses because the memory surface has to say *why* something is no longer shown, and "its score dropped" is not one of the three human-readable groups in `P§9`.
- **COST:** Two mechanisms, two parameter sets, two explanations. More surface area for the product to get wrong.
- **CONFIDENCE:** high

---

### Q138 — How should the system distinguish surfaces with different contracts?

- **DECISION:** By separate retrieval paths with separate data access, not by a mode flag on one path. The dictation path can query only entity and lexical stores; it has no read access to the observation or hypothesis tables.
- **BECAUSE: POSITION.** `P§7`: "two separate retrieval paths, not one path with a filter… It has no access to the observation or hypothesis tables at all. This is enforceable in the schema and checkable in the evaluation." And `P§AppC` claim 7.
- **REJECTED:** One path with a surface parameter. It wins on code volume — it is obviously less to build. It loses the structural claim, which is one of the seven things the position commits to demonstrating.
- **COST:** Duplicated retrieval code and two query surfaces to maintain. Any retrieval improvement has to be made twice or deliberately made once.
- **CONFIDENCE:** high

---

### Q139 — What evidence should establish generality?

- **DECISION:** For an observation: N independent transcripts, each pointable-at, with no contradicting instance in the same window. Generality is *never* established by count alone for promotion purposes — only by user confirmation.
- **BECAUSE: POSITION.** `P§4`: "Nothing self-promotes. An observation does not become stated because it was seen twenty times. It becomes stated when the user confirms it. Twenty is still a pattern."
- **REJECTED:** A confidence threshold that auto-promotes. It wins in a system where user attention is free. `P§8` rations prompts precisely because it is not.
- **COST:** The stated tier grows only as fast as the user answers prompts, and prompts are budgeted. Most observations will stay observations forever. `N` itself is an unset parameter — see **Section A**.
- **CONFIDENCE:** high

---

### Q141 — Should ingestion be verbatim, extracted, or both?

- **DECISION:** Both, in separate stores with separate roles. Verbatim transcripts are the provenance substrate (`Q28`). Extracted typed facts are memory (`Q33`). The two are never mixed in retrieval.
- **BECAUSE: POSITION.** `P§9` requires the verbatim source ("the actual transcript, with a date"); `P§4` requires the extracted record.
- **REJECTED:** Extracted only. See `Q186` — it is the stronger privacy answer and is in genuine tension with `P§5`. Logged in **Section B, conflict B2**.
- **COST:** Two stores, double the storage, and the raw store holds material the memory store refuses.
- **CONFIDENCE:** high

---

### Q142 — What ontology should a memory inhabit?

- **DECISION:** A fixed, closed, three-type ontology: entity, preference, episode. No custom types, no extension mechanism, no fallback type.
- **BECAUSE: POSITION.** `P§4` table names exactly three and the memory surface, the dial, and the dictation/Hey Kivi split all read them.
- **REJECTED:** An open or extensible type set (one surveyed system offers 13 types plus custom). It wins if the corpus turns out to contain a fourth kind of durable thing that does not fit — a decision, a commitment, a constraint. That is a real risk and the honest place to note it is **Section A**, because the position does not decide whether "the Atlas review is on Thursdays, recurring" is an episode or a preference.
- **COST:** Forcing ambiguous facts into three buckets. Entity is the likely dumping ground.
- **CONFIDENCE:** medium

---

### Q147 — What should expiry mean?

- **DECISION:** Expiry means a hypothesis is **dropped** — removed from active state, its question no longer asked. Decay means an observation **stops being surfaced** but its row and evidence remain. Two different words for two different operations, and neither is deletion of the underlying transcripts.
- **BECAUSE: POSITION.** `P§9`: "Hypotheses expire by default. An unconfirmed question that hasn't been raised again is dropped. Kivi does not accumulate a quiet file of unanswered questions about you." Versus: "An observation not re-observed within a window loses standing and stops being surfaced."
- **REJECTED:** Reversible expiry stamped with when/why, retaining the row (the `MemOS` answer). For observations, that is exactly what I chose. For hypotheses it loses on the explicit sentence above — a retained expired hypothesis *is* a quiet file.
- **COST:** An expired hypothesis that was correct is lost and must be re-derived from scratch. There is no "I did wonder that once" history, deliberately.
- **CONFIDENCE:** high

---

### Q148 — What happens on failure after the memory commit?

- **DECISION:** Post-commit side effects (activity logging, index refresh, embedding write) are best-effort and never roll back the commit, but each failure is recorded and the affected memory is flagged for repair. An embedding that failed to write leaves a memory retrievable lexically and marked as such in the trace.
- **BECAUSE: ENGINEERING (E4).** The position is silent on partial-commit failure. `E4` forbids a silently degraded memory, because a memory present in the table but absent from the vector index will look like a retrieval bug and will be diagnosed as one.
- **REJECTED:** Full transactional commit including embeddings. It wins on consistency and is achievable if embeddings are computed before the transaction. That is arguably the better design and the only reason it loses is that embedding generation is a network call whose latency inside a write transaction is unacceptable during a 500-record import.
- **COST:** A repair pass is now a required component, and memory state has a transient inconsistent mode that the evaluation must not accidentally measure.
- **CONFIDENCE:** medium

---

### Q150 — Who may write on behalf of whom?

- **DECISION:** Only the extractor and the user-action handler write memories, both on behalf of the single user. There is no delegation, no agent namespace, no writer identity beyond `source ∈ {extractor, user_action}` — which is recorded because tier depends on it.
- **BECAUSE: POSITION.** `P§4`: the Stated tier requires "an explicit user confirmation event, which is itself recorded with a timestamp," so writer identity must distinguish user actions from extraction. Beyond that distinction, `E1` leaves nobody else to model.
- **REJECTED:** A scoped-token multi-writer model. It wins in a multi-agent product. Not this one.
- **COST:** If Kivi later gains sub-agents or integrations that should write memory, there is no authority model to extend.
- **CONFIDENCE:** high

---

### Q152 — Should extraction preserve unsupported/ambiguous input or discard it?

- **DECISION:** Discard, with a reason code. An ambiguous candidate is not stored as a low-confidence fact and is not stored as a hypothesis — those are two different things and conflating them is the failure `P§4` warns about.
- **BECAUSE: POSITION.** `P§4`: "Hypotheses are stored as questions, never as claims… The grammar of storage enforces the epistemics. You cannot accidentally use a question as a fact." An ambiguous extraction is not a question Kivi is wondering about; it is a failed read. Storing it as a hypothesis would smuggle extraction noise into a tier that has product meaning.
- **REJECTED:** Preserve as low-confidence and let retrieval ranking sort it out. It wins in a system where confidence is a continuous ranked quantity. Here tier is categorical and carries a promise, so there is no place to put it.
- **COST:** Recall loss on messy transcripts, which the ASR-noise portion of the corpus will make visible.
- **CONFIDENCE:** high

---

### Q153 — Should assistant/tool material be evidence for preferences?

- **DECISION:** No. Kivi's own output is removed before preference extraction. Preferences come only from what the user said or from patterns across what the user *dictated*.
- **BECAUSE: POSITION.** `P§4`: an observed preference is "a pattern across multiple transcripts, pointable-at" — and the worked example is "never once used a bullet list in fourteen client emails," which is a pattern in the user's own dictations. If Kivi's drafts counted, the pattern would partly be a pattern in Kivi's behaviour, and the evidence would no longer point at the user.
- **REJECTED:** Counting accepted drafts as evidence. This is the strongest rejected alternative in the whole ingestion stage: if the user accepts fourteen prose drafts unedited, that is arguably better evidence of preference than fourteen dictations, and it costs the user nothing. It wins if you accept that silence-as-acceptance is evidence. `P§8` says the opposite in a neighbouring case: "When a hypothesis is offered and the user says nothing, that is not confirmation." I am applying that principle here by analogy — which is an extension, not a quotation, and it is flagged in **Section A**.
- **COST:** A large, cheap, high-quality evidence stream is refused. The observed tier is materially thinner because of this decision.
- **CONFIDENCE:** medium

---

### Q154 — Should raw evidence and derived summaries both persist?

- **DECISION:** Raw evidence persists (transcripts). Derived *summaries* do not exist as a stored artefact at all. What persists alongside raw is the extracted typed fact, which is not a summary.
- **BECAUSE: POSITION.** `P§4`'s unit is a typed record; `P§33`-equivalent reasoning above rejects summaries because they have no tier and cannot be individually corrected.
- **REJECTED:** Storing a per-transcript summary for cheap context loading. It wins on Hey Kivi answer quality for questions about "what happened in that meeting," which discrete facts answer poorly. This is a real recall gap and it is named in **Section A**.
- **COST:** Narrative questions degrade to episode retrieval and will often abstain when a summary would have answered.
- **CONFIDENCE:** medium

---

### Q155 — Should vectors live beside records, in a vector service, or be recomputable cache?

- **DECISION:** Beside the records, in the same embedded database, with the model identity and dimension stored on the row — and treated as a **recomputable cache**, rebuildable by a documented command.
- **BECAUSE: ENGINEERING (E2).** A separate vector service is another process in `RUN.md`. Storing model identity on the row is the fix for the flaw the inventory flags in the surveyed system ("no model/provider identity in the row"), which would otherwise make a model change silently corrupt similarity.
- **REJECTED:** A dedicated vector service. It wins above roughly a million vectors. At a few hundred memories, brute-force cosine in-process is exact and instant.
- **COST:** No approximate-nearest-neighbour tuning, no scale path without swapping the store.
- **CONFIDENCE:** high

---

### Q159 — Should identical replay update recency/evidence, be ignored, or create a new observation?

- **DECISION:** Identical replay of the *same transcript* is ignored — idempotent, per `Q08`. A *different* transcript expressing the same fact increments `evidence_count`, appends a source id, and updates `last_seen`, but never changes tier.
- **BECAUSE: POSITION.** `P§4` stores `evidence_count` and `source_transcript_ids[]` as distinct fields, which only makes sense if distinct sources accumulate and identical ones do not. `P§4`'s "Nothing self-promotes" forbids the increment from changing tier.
- **REJECTED:** Creating a new observation per occurrence and aggregating at read time. It wins if you want per-occurrence provenance with full fidelity, which is close to what `source_transcript_ids[]` already gives more cheaply.
- **COST:** Dedupe correctness becomes load-bearing: a false merge silently inflates evidence for the wrong fact, and a missed merge splits one belief into two on the memory surface.
- **CONFIDENCE:** high

---

### Q168 — What enters memory?

- **DECISION:** Duplicate of `Q01`/`Q12`. User-authored content only, purpose-limited to dictations, Hey Kivi turns, and confirmations/corrections.
- **BECAUSE: POSITION.** `P§3`, `P§4`.
- **REJECTED:** See `Q01`.
- **COST:** See `Q01`.
- **CONFIDENCE:** high

---

### Q169 — Is anything excluded at extraction time?

- **DECISION:** Yes — and by category, not by form. A hard exclusion list: health, mood or emotional state, relationships and family, faith, politics, finances beyond work-level facts, and any characterisation of the user's competence or character. Enforced by a check on candidates, not by prompt instruction.
- **BECAUSE: POSITION.** `P§2` verbatim: "A hard exclusion list enforced at extraction, before anything reaches storage. Kivi never infers or stores: health, mood or emotional state, relationships and family, faith, politics, finances beyond work-level facts, or any characterisation of the person's competence or character."
- **REJECTED:** Prompt-only, form-only exclusion (the surveyed answer). It wins never under `P§2`, which names it as the failure mode to avoid.
- **COST:** A classifier boundary that will be wrong at the edges, with no appeal mechanism for the user — they cannot see what was dropped, only that something was.
- **CONFIDENCE:** high

---

### Q170 — Extraction — one LLM call per turn, or batched?

- **DECISION:** One call per transcript, batched across transcripts at the queue level for throughput, never batched *within* a call in a way that mixes transcripts. Each call sees one transcript plus the current entity list for disambiguation.
- **BECAUSE: ENGINEERING (E3, and `Q08`).** Per-transcript calls are what make extraction idempotent per transcript and make the drop log attributable to a specific transcript, which `P§5`'s "read, not kept" marker requires ("the transcript's inspection view shows a read, not kept marker").
- **REJECTED:** Multi-transcript batched calls, which are several times cheaper and let the model see patterns across transcripts directly. Cost is a reported metric in the brief, so this is a real sacrifice. It wins if per-transcript attribution could be recovered reliably from a batched response, which in practice it cannot.
- **COST:** ~500 LLM calls per corpus import, with the cost and latency that implies, both of which the evaluation must report honestly.
- **CONFIDENCE:** high

---

### Q171 — Does extraction have an "extracted nothing" path?

- **DECISION:** Yes, explicitly, as a distinct recorded outcome separate from failure and from all-candidates-dropped. Three outcomes: nothing found, candidates found and dropped, candidates found and stored.
- **BECAUSE: POSITION.** `P§AppA`: the corpus must include "transcripts that produce nothing." `P§2` separately requires drops to be visible, so "produced nothing" and "produced three and dropped three" must not look the same.
- **REJECTED:** A single empty-result state. It wins on simplicity and loses the distinction between "boring transcript" and "transcript full of things Kivi refused," which is the one the user most wants to see.
- **COST:** Three outcome codes to render intelligibly in the transcript view.
- **CONFIDENCE:** high

---

### Q173 — On dedupe, does the old record survive?

- **DECISION:** On merge (same fact, new source): one record survives and accumulates evidence; there is no old record to preserve. On supersession (contradicting fact): the old record survives in history with `status = superseded` and a pointer to what replaced it.
- **BECAUSE: POSITION.** `P§9`: "the superseded version stays in history so the change is auditable." `P§4`: "Demotion and supersession are ordinary operations, not deletions."
- **REJECTED:** Preserving a version chain on merges too. It wins if merge errors are common enough that you need to unwind them — which, given `Q159`'s cost note, may prove true. The merge history is recoverable from `source_transcript_ids[]`, which is why it loses for now.
- **COST:** A bad merge is hard to unwind. Reversing it means re-extracting from the listed sources.
- **CONFIDENCE:** medium

---

### Q174 — Who wins?

- **DECISION:** In a contradiction between two memories: the newer *stated* memory wins over an older one; any stated memory wins over any observed one regardless of age; an explicit user correction wins over everything. Recency alone is never sufficient — tier is checked first.
- **BECAUSE: POSITION.** `P§4`'s tier table gives stated "Treat as true. Use freely" and observed "Never as a rule," which is a precedence order. `P§9`'s supersession is explicitly "new evidence replaces old." `P§8`'s inline correction — *"No, Priya's at Northwind now"* — must beat both.
- **REJECTED:** Recency-first (the surveyed default, "Recency, by default, in both places"). It wins if tier were unreliable. It loses because a fresh observation overriding an old stated preference is exactly the "silently enforces things you never agreed to" failure in `P§4`.
- **COST:** A stale stated fact outranks a strong contradicting pattern until the user acts. Kivi will confidently repeat something that is no longer true, and can only flag the tension (under Koottu) rather than resolve it.
- **CONFIDENCE:** high

---

### Q180 — Is re-processing the same transcript idempotent?

- **DECISION:** Yes. Same answer as `Q08`, restated because the inventory notes this is "the least-examined assumption in the repo." It is examined here: idempotence is required by `P§AppC` claim 6 and is a tested property, not an assumption.
- **BECAUSE: POSITION.** `P§AppC` claim 6: "A correction demoted a memory and the memory did not regrow on reprocessing." Reprocessing is named as a thing that happens.
- **REJECTED:** See `Q08`.
- **COST:** See `Q08` — determinism requirements on extraction.
- **CONFIDENCE:** high

---

### Q181 — One memory type, or several?

- **DECISION:** Several — exactly three, closed (`Q142`, `Q99`).
- **BECAUSE: POSITION.** `P§4`.
- **REJECTED:** One type with attributes. It wins on schema flexibility; loses because `P§7`'s structural path separation is enforced by table access, which needs the types to be structurally distinct.
- **COST:** See `Q142`.
- **CONFIDENCE:** high

---

### Q182 — Similarity alone, or blended with something?

- **DECISION:** Blended. Reciprocal-rank fusion of lexical and vector retrieval, then deterministic re-rank on tier, evidence, and recency (`Q26`).
- **BECAUSE: ENGINEERING.** The position does not specify retrieval mechanics — `P§AppB` explicitly defers "embeddings vs structured query vs hybrid." The constraint is that exact-token recall matters for entity names (*Atlas*, *Priya Raghavan*) where embeddings are weak, and paraphrase recall matters for preferences where lexical is weak. Neither leg alone covers both.
- **REJECTED:** Vector-only, which is the default choice and simpler. It wins if entity lookup were served by a separate exact path — which it partly is, via the dictation path's lexical store. That overlap is worth noting: the hybrid's lexical leg and the dictation path's lexical store are near-duplicates.
- **COST:** Two indexes to maintain and two failure modes to explain in the trace.
- **CONFIDENCE:** high

---

### Q183 — What happens when a component fails?

- **DECISION:** Fail loudly and visibly on anything that can change an answer; fail quietly only on the extractor's post-commit side effects (`Q148`). Concretely: retrieval leg down → abstain and say so; extraction down → queue and quarantine; embedding down → lexical-only with the degradation stated in the trace.
- **BECAUSE: ENGINEERING (E4).** The position does not enumerate component failures, but `P§8`'s rule that a fluent invented answer is "worse than no answer" generalises: a fluent *degraded* answer is the same failure with a different cause.
- **REJECTED:** Quiet degradation everywhere (the surveyed answer: "Three different answers, all quiet"). It wins on demo smoothness and loses the product's central claim.
- **COST:** The demo will visibly degrade when something is wrong. That is intended, and it means the evaluation must distinguish "abstained because absent" from "abstained because degraded" or the results are meaningless.
- **CONFIDENCE:** high

---

### Q184 — Is there any concurrency story?

- **DECISION:** Yes, a minimal one: single writer, WAL, bounded retry (`Q96`); readers concurrent and unblocked; the import queue serialised. No in-memory mutable stores.
- **BECAUSE: ENGINEERING (E2).** The position is silent. The inventory's surveyed answer — "No. Every store is a Python list or dict mutated in place" — fails the brief's requirement that behaviour come from "actual state, persistence, retrieval."
- **REJECTED:** A genuine concurrent write design. Wins at multi-user scale, which `E1` excludes.
- **COST:** Import throughput ceiling; no horizontal scale path.
- **CONFIDENCE:** high

---

### Q185 — Should privacy mean secret-pattern redaction, subject/category exclusion, or consent-aware routing?

- **DECISION:** Subject/category exclusion is the primary meaning; source separation enforces the subject half structurally; secret-pattern redaction is a backstop. Consent-aware routing is not built.
- **BECAUSE: POSITION.** `P§2` (category) and `P§5` (subject/source). Consent routing has no counterparty under `E1`.
- **REJECTED:** Consent-aware routing. It wins in a multi-party product where Priya could grant or withhold permission. That product is the natural next version and this decision closes the door on it cheaply.
- **COST:** No consent model to extend. Adding one later means a subject dimension on every memory and a permissions layer on retrieval.
- **CONFIDENCE:** high

---

### Q186 — Should raw source material survive, or only extracted claims plus provenance pointers?

- **DECISION:** Raw survives in full (`Q28`, `Q141`).
- **BECAUSE: POSITION.** `P§9`: provenance is "the actual transcript, with a date."
- **REJECTED:** Extracted claims plus pointers into a discarded or redacted source. This is the strongest privacy answer available and it directly serves `P§5`'s spirit. It wins if you are willing to weaken `P§9`'s provenance promise to "here is a redacted version of what you said." I am not weakening it, and the resulting tension is **Section B, conflict B2** — this is the single most important unresolved friction in the position document.
- **COST:** As `Q28`. The system's most sensitive store is the one with the fewest rules attached to it.
- **CONFIDENCE:** medium

---

### Q191 — Can observed patterns become facts automatically, or only after confirmation?

- **DECISION:** Only after explicit user confirmation, recorded as a timestamped event.
- **BECAUSE: POSITION.** `P§4`: "Nothing self-promotes… It becomes stated when the user confirms it. Twenty is still a pattern." And: "Promotion (`observed → stated`, `hypothesised → stated`) requires an explicit user confirmation event, which is itself recorded with a timestamp."
- **REJECTED:** Threshold auto-promotion. It wins in a product optimising for the memory getting *used*, since most observations will never be confirmed. It is named in `P§4` as the thing that makes a system "silently enforce things you never agreed to."
- **COST:** The stated tier stays small. Kivi's most confident behaviour is rare, and the product's best experience is gated behind a budgeted prompt.
- **CONFIDENCE:** high

---

### Q196 — Which failures may be hidden to preserve the main path?

- **DECISION:** Only post-commit side effects of extraction, and only when the resulting degradation is itself recorded and rendered in the trace — which makes "hidden" the wrong word. Nothing on the answer path may be hidden.
- **BECAUSE: ENGINEERING (E4).** `P§8` requires the trace to show "what was retrieved, what was withheld and why, what was used in the answer." A hidden failure produces a trace that is a lie by omission.
- **REJECTED:** Hiding retrieval-leg failures to keep answers flowing. It wins for demo polish. It is the exact failure `P§8` is written against.
- **COST:** Visible brittleness.
- **CONFIDENCE:** high

---

### Q198 — Retain assistant output?

- **DECISION:** No. Kivi's output is not retained as memory and is not evidence. It is retained only as part of the Hey Kivi interaction trace, which is an inspection artefact, not a memory source.
- **BECAUSE: POSITION.** `P§4`'s tier definitions admit only user statements and user confirmations. See `Q01`, `Q12`, `Q153`.
- **REJECTED:** Double-opt-in capped retention (the surveyed answer). It wins if the user explicitly wants Kivi to remember a draft it wrote — which is a real use case ("remember how you phrased that"). Note that under this decision, the user can achieve it by *stating* it, which routes the fact back through the stated tier where it belongs.
- **COST:** No learning from output quality. The trace and the memory store diverge in retention rules, which has to be explained.
- **CONFIDENCE:** high

---

### Q199 — Should rejection be invisible or leave a non-content audit?

- **DECISION:** Non-content audit. A row with `transcript_id`, `reason_code`, `timestamp`, and nothing else. Never the dropped text, never a paraphrase of it, never a category more specific than the exclusion list's own names.
- **BECAUSE: POSITION.** `P§2`: "Dropped candidates are logged with the reason." `P§5`: the transcript view "shows a read, not kept marker with the count of dropped candidates."
- **REJECTED:** Fully invisible rejection. It is the stronger privacy answer — the audit row still reveals that a health-category candidate existed. It wins if the exclusion boundary could be proven some other way. It cannot: `P§2` says the log "is how we prove the boundary is real rather than claimed," and `P§AppC` claim 1 requires it as evaluation output.
- **COST:** A reason-coded trail about sensitive categories exists. It is metadata, not content, but it is not nothing, and a hostile reading of `P§2` against `P§2`'s own privacy stance is available. Noted in **Section B, conflict B3**.
- **CONFIDENCE:** high

---

### Q203 — Strings or typed entities?

- **DECISION:** Typed entities. People, projects, organisations, channels, and artefacts are rows with identity, canonical name, aliases, and typed relations. Not free-text tags.
- **BECAUSE: POSITION.** `P§4` defines Entity as "A person, project, company, channel, or artefact in the user's world, **and the relations between them**." Relations require entity identity. `P§7` additionally needs a canonical-spelling lookup for the dictation path.
- **REJECTED:** Lowercase leniently-merged string tags (the surveyed answer). It wins on extraction robustness — no resolution step to get wrong. It loses the relation half of the definition and the spelling half of `P§7`.
- **COST:** Entity resolution becomes a required component and a new failure mode: two Priyas merged, or one Priya split.
- **CONFIDENCE:** high

---

### Q209 — How combine streams?

- **DECISION:** Reciprocal rank fusion with a fixed k, then the deterministic tier/evidence/recency re-rank (`Q26`, `Q182`). Equal weight between lexical and vector legs.
- **BECAUSE: ENGINEERING.** Position is silent (`P§AppB` defers retrieval mechanics). RRF is chosen because it needs no score calibration between two incomparable scoring systems and is fully explicable in the Why panel.
- **REJECTED:** Weighted score fusion. It wins if the weights can be tuned against a labelled retrieval set, which the evaluation corpus could support. That is a live upgrade path, not a closed door.
- **COST:** Leaves retrieval quality on the table by refusing to tune.
- **CONFIDENCE:** medium

---

### Q211 — What on compiled-memory miss?

- **DECISION:** Fall back to bounded lexical search over raw transcripts, clearly labelled in the trace as a raw-transcript hit rather than a memory. If that also misses, abstain per `P§8`.
- **BECAUSE: POSITION.** `P§8`'s abstention example does exactly this — it reports "one migration discussion from 6 March" as a near-miss the system found and offers it. That is a raw-source hit surfaced as such, not a memory.
- **REJECTED:** Memory-only, abstain immediately on miss. It wins on purity — it keeps memory as the only answer surface and makes memory quality directly measurable. It loses because `P§8`'s own worked example shows the fallback in action.
- **COST:** Two answer sources with different trust levels, both of which the Why panel must distinguish clearly or the tier system is undermined at the surface.
- **CONFIDENCE:** medium

---

### Q212 — Can an LLM reorder results?

- **DECISION:** No. Ordering is deterministic (`Q26`).
- **BECAUSE: POSITION.** `P§8`'s Why panel must give a reason a person can act on; model preference is not one.
- **REJECTED:** Opt-in bounded LLM reranking with deterministic fallback (the surveyed answer, which is a careful design). It wins if retrieval precision proves inadequate and the reranker's contribution can be shown as a labelled step in the trace. That is a genuinely available compromise and the condition is measurable.
- **COST:** Precision ceiling. See `Q26`.
- **CONFIDENCE:** medium

---

### Q215 — What formalism should carry causal structure and intervention semantics?

- **DECISION:** None. No causal formalism is built. Kivi stores observations and questions, never causal claims.
- **BECAUSE: POSITION.** `P§4`: "Hypothesised — A proposed reason behind an observation — Store as a question. Never assert. Never act on." A causal Bayesian network exists to *assert and act on* causal structure, which is the one thing the hypothesised tier forbids. `P§6` reinforces it: Daari "Never: turns the hypothesis into a label, a diagnosis, or a stored belief."
- **REJECTED:** A causal Bayesian network. It wins in a product whose job is explanation and intervention. `P§3` rules that product out: "Not insight. Not advice."
- **COST:** Kivi can never explain *why* a pattern exists in any structured, checkable way. Daari's hypotheses are single-shot natural-language guesses with no model behind them, which is exactly what `P§6` describes but is weaker than it sounds.
- **CONFIDENCE:** high

---

### Q218 — How should n-ary causal assertions be encoded in an RDF ecosystem?

- **DECISION:** Not applicable. There is no RDF ecosystem and no causal assertions (`Q215`). **Out of scope.**
- **BECAUSE: ENGINEERING (E5).** Follows from `Q215`, which is position-forced; this question is downstream of a subsystem that is not built.
- **REJECTED:** RDF-star embedded triples. Wins in a knowledge-graph product with a reasoning layer, which this is not.
- **COST:** None here.
- **CONFIDENCE:** high

---

### Q219 — Where should causal structure come from: learned from observations, supplied by experts, extracted from text, or combined?

- **DECISION:** Nowhere. **Out of scope** (`Q215`).
- **BECAUSE: ENGINEERING (E5).**
- **REJECTED:** A pre-existing domain CBN plus ontology. Wins in a domain-modelling product.
- **COST:** None here.
- **CONFIDENCE:** high

---

### Q220 — What should enter the causal system?

- **DECISION:** Nothing; there is no causal system. **Out of scope** (`Q215`).
- **BECAUSE: ENGINEERING (E5).**
- **REJECTED:** As `Q219`.
- **COST:** None here.
- **CONFIDENCE:** high

---

### Q222 — When observational association and domain causal knowledge disagree, which source should control the explanation?

- **DECISION:** Neither — the disagreement is not resolved, it is surfaced. Kivi holds the observation and, at most, offers the proposed reason as a question under Daari. There is no domain causal knowledge to weigh against it.
- **BECAUSE: POSITION.** `P§4`: hypotheses are "stored as a question, never as a claim," so there is nothing for an association to be adjudicated against. The question presupposes a resolution mechanism the epistemics forbid.
- **REJECTED:** Letting domain causal structure correct misleading associations. It wins in a system permitted to hold causal beliefs. `P§2` forbids exactly this class of belief about a person.
- **COST:** Kivi will surface spurious patterns it has no machinery to discount. A confounded observation ("you always reschedule on Mondays") gets the same standing as a meaningful one. This is a real quality cost of refusing causal structure, and the only mitigation is that observations are offered, never enforced.
- **CONFIDENCE:** high

---

### Q226 — Which counterfactual quantities should the system distinguish?

- **DECISION:** None. Kivi computes no counterfactual quantities. **Out of scope** (`Q215`).
- **BECAUSE: POSITION.** `P§4`: hypotheses are stored as questions and Kivi may "never act on" them. Total/direct/indirect effects are quantities you act on.
- **REJECTED:** Distinguishing total, natural direct, and natural indirect effects. Wins in a causal-analysis product. `P§3` excludes that product: "Not insight. Not advice."
- **COST:** None here. Kivi cannot reason about mediation, so an observation like "she reschedules when Arun is blocked" can never be decomposed — it stays a surface pattern.
- **CONFIDENCE:** high

---

### Q229 — Should causal knowledge be used only to explain predictions, or also to change learning, prediction, planning, and action?

- **DECISION:** Neither. There is no causal knowledge layer. The nearest thing Kivi has — a Daari hypothesis — explains nothing and changes nothing; it is offered once as a question and not written to memory.
- **BECAUSE: POSITION.** `P§6`: Daari "is not a persistent mode. It's a per-request invitation… and the answer is not written to memory." That is the hardest possible "no" to infusing downstream behaviour.
- **REJECTED:** Explanation-plus-infusion. It wins in a decision-support product. The position is explicit that Kivi is not one.
- **COST:** Daari is the weakest of the three modes by construction — it can say something insightful once and then must forget it. Users who find it valuable will be frustrated that it does not persist.
- **CONFIDENCE:** high

---

### Q234 — When state must persist across model calls, where should immediately active state live?

- **DECISION:** In an explicit, inspectable per-request context object assembled by code before the model call — retrieved memories, the dial setting, the withheld set, the tool results so far — never in an implicit conversation buffer the model manages for itself.
- **BECAUSE: POSITION.** `P§8`'s Why panel must show "what was retrieved, what was withheld and why, what was used in the answer." That is only renderable if the assembled context is a data structure code owns, not a prompt string.
- **REJECTED:** Letting the model carry state in the conversation. It wins on implementation speed and multi-turn coherence. It makes the trace a reconstruction rather than a record, which is the difference between an inspection tool and a plausible story about one.
- **COST:** Multi-turn Hey Kivi conversations need explicit state management. Anaphora across turns ("that one," "the second") becomes work rather than free.
- **CONFIDENCE:** high

---

### Q235 — How should persistent knowledge be divided when different kinds of past information support different future behavior?

- **DECISION:** Into the position's two axes and nothing else: three types (entity, preference, episode) crossed with three tiers (stated, observed, hypothesised). Explicitly **not** the episodic/semantic/procedural division. There is no procedural memory.
- **BECAUSE: POSITION.** `P§4` is the division. Note that the position's "episode" is not CoALA's episodic memory — it is a typed fact with a timestamp, not a replayable trace. The naming collision is worth flagging because it will mislead anyone who reads the papers alongside the spec.
- **REJECTED:** Episodic/semantic/procedural with procedural memory including agent code and prompts. It wins in a self-improving agent. `P§4` has no tier for "a skill Kivi learned," and `P§4`'s tier system is what governs disclosure, so a fourth category would have no disclosure rules.
- **COST:** Kivi cannot learn procedures. "Do the Friday recap the way you did last time" is not a memory Kivi can hold as a procedure — only as a preference stated in words.
- **CONFIDENCE:** high

---

### Q239 — When new information is derived during a task, should reasoning alter durable state directly, alter only current state, or remain purely latent?

- **DECISION:** Reasoning alters only current state. Durable writes happen through exactly two paths: the async extractor over user-authored transcripts, and explicit user actions. Nothing Kivi concludes mid-task becomes durable.
- **BECAUSE: POSITION.** `P§6`, on Daari: "the answer is not written to memory." `P§2` on plausible inference: "Possibly true. Also possibly none of Kivi's business, and stored as a durable belief that colours everything afterwards."
- **REJECTED:** A distinct "learning action" the agent can call to promote a derived conclusion (the CoALA answer). It wins in an autonomous agent that must improve without supervision. Here it is precisely the mechanism `P§2` warns about, dressed as a feature.
- **COST:** Kivi cannot consolidate. A conclusion reached brilliantly in one session is gone in the next unless the user restates it.
- **CONFIDENCE:** high

---

### Q240 — What kinds of durable change should count as learning?

- **DECISION:** Three, all evidence-driven: a new typed fact extracted from a user transcript; an evidence increment on an existing fact from a new source; and a lifecycle transition caused by a user action (confirm, correct, demote, forget) or by the clock (decay, expiry). Nothing else counts as learning.
- **BECAUSE: POSITION.** `P§4` (schema and promotion rules) and `P§9` (growth mechanics). The position's whole theory of learning is "evidence accumulates, the user adjudicates, time erodes."
- **REJECTED:** Counting skill/prompt/code changes as learning. Wins for a self-modifying agent; excluded by `Q235`.
- **COST:** Kivi's competence is fixed at build time. It gets better at *knowing*, never at *doing*.
- **CONFIDENCE:** high

---

### Q242 — When should an interaction be written to long-term memory: continuously, after each action, or after the interaction has been summarized?

- **DECISION:** After the interaction completes, per whole transcript, asynchronously (`Q62`). Not continuously, not per action, and not after summarisation — because there is no summarisation step (`Q154`).
- **BECAUSE: ENGINEERING (E3).** Position is silent on timing (`P§AppB` defers "Extraction timing — per-transcript, batched, or both"). The transcript is the natural unit because it is the unit the corpus arrives in and the unit provenance points at.
- **REJECTED:** Continuous per-turn writes. Wins for live conversational memory where the user expects immediate retention. Mitigated here by the synchronous correction path.
- **COST:** As `Q62` — a window where Kivi has heard but does not know.
- **CONFIDENCE:** high

---

### Q244 — When proposing the next action, should the system enumerate, sample, or simulate candidates?

- **DECISION:** Enumerate. The Hey Kivi tool set is small and fixed (`Q246`), so tool selection is a single model call over a complete enumeration of available tools, with the choice recorded in the trace. No sampling, no rollouts.
- **BECAUSE: ENGINEERING (E4, E5).** Position is silent. Enumeration over a small set is the only option whose decision is explicable in the Why panel — the trace can say "three tools were available, this one was chosen, here is why."
- **REJECTED:** Multi-sample or simulated rollouts. Wins in a large action space with irreversible actions. Kivi's actions are drafting, scheduling, and recall; none justify simulation.
- **COST:** No self-correction on a bad tool choice within a turn.
- **CONFIDENCE:** high

---

### Q246 — How large should the action space be relative to the sophistication of the controller?

- **DECISION:** Minimal. Three tools, matching `P§AppB`'s candidates: draft/reply, schedule or reschedule, and recall/search. Nothing else ships in v1.
- **BECAUSE: POSITION.** `P§AppB`: "The brief is clear that a narrow set used convincingly beats a broad shallow one — likely candidates are draft/reply, schedule or reschedule, and recall/search." The brief agrees: "Implement only the Hey Kivi tools required by your chosen use cases."
- **REJECTED:** A broader tool set. Wins if any one of the three proves too thin to demonstrate memory's value — which is a real risk for *schedule*, since scheduling needs a calendar that does not exist in this build.
- **COST:** Anything a user asks for outside three verbs is an abstention or a refusal. The demo's surface looks narrow.
- **CONFIDENCE:** high

---

### Q247 — Which control should live in deterministic code and which in stochastic model behavior?

- **DECISION:** The model decides three things: what a transcript means (extraction), which tool to call, and how to word an answer. Code decides everything else — exclusion enforcement, tier assignment rules, disclosure filtering, ranking, lifecycle transitions, and abstention. Every product *promise* is enforced in code.
- **BECAUSE: POSITION.** `P§2`: "Exclusions are enforced by a check that runs on candidate memories, not by a line in a prompt hoping for good behaviour." That sentence is a general principle about where promises live, and `P§6`'s disclosure dial and `P§4`'s promotion rules inherit it.
- **REJECTED:** The CoALA guidance — use code sparingly, rely on model flexibility. It wins for capability breadth and is right for a general agent. It is wrong for a system whose selling point is a boundary you can prove.
- **COST:** Kivi is rigid. Cases the code's rules do not anticipate are handled badly rather than gracefully, and improving behaviour means changing code rather than a prompt.
- **CONFIDENCE:** high

---

### Q250 — What unit should determine whether prior state is resumed, inherited, or ignored when new input arrives?

- **DECISION:** There is no session resumption. Each Hey Kivi request is stateless with respect to prior requests except for an explicit, bounded, in-conversation turn history. Durable state is memory, and memory is retrieved fresh per request.
- **BECAUSE: ENGINEERING (E4).** Position is silent. A session-inheritance rule ("inherit when the earlier dialogue is a prefix") introduces invisible state that changes answers — precisely what `E4` forbids, because the trace could not explain why the same question got two different answers.
- **REJECTED:** Prefix-matched session inheritance. Wins in a long-running assistant where re-establishing context each turn is expensive. At Kivi's scale, re-retrieving is cheap and honest.
- **COST:** Long multi-turn conversations re-retrieve redundantly and can lose thread continuity that a session would have preserved.
- **CONFIDENCE:** high

---

### Q251 — When a new session begins, what prior information should be available before the first reasoning step?

- **DECISION:** Nothing preloaded. Retrieval runs on the actual request. The one exception is the entity list, which is loaded for disambiguation because names must resolve before anything else can.
- **BECAUSE: POSITION.** `P§6`: "Kivi always retrieves everything it has" — retrieval is request-driven, not session-driven. Preloading a profile would mean some memories influence every answer without appearing in that answer's trace.
- **REJECTED:** Loading a standing user profile at session start. It wins on coherence and is what most memory products do. It loses because `P§8`'s trace must account for what was used, and an always-on profile is used invisibly.
- **COST:** Every request pays retrieval latency. There is no cheap always-known baseline.
- **CONFIDENCE:** high

---

### Q252 — How many memory strata should separate persistent knowledge from the prompt used on the current turn?

- **DECISION:** Two. Persistent memory (durable typed records) and the per-request assembled context (`Q234`). No session-level intermediate stratum.
- **BECAUSE: ENGINEERING (E4, E5).** Position is silent on strata. A third session-level stratum is state that persists across turns without being memory and without appearing in the memory surface — unaccountable by construction.
- **REJECTED:** Three strata (LTM / session working memory / focus of attention). It wins for long complex tasks where intermediate conclusions must survive turns. Kivi's three tools are single-turn.
- **COST:** No scratchpad. Multi-step tasks that need intermediate state have nowhere to keep it.
- **CONFIDENCE:** high

---

### Q254 — What should session working memory retain from an unfolding interaction?

- **DECISION:** Nothing durable. A bounded literal turn history within one conversation, discarded when the conversation ends, never extracted from except as a user-authored transcript on the ordinary write path.
- **BECAUSE: ENGINEERING (E4), following `Q252`.**
- **REJECTED:** Concise model-authored notes of intermediate conclusions. It wins for complex tasks and is the CoALA/`DA` answer. It loses because model-authored notes are exactly the "plausible inference" `P§2` rejects, one layer removed from storage.
- **COST:** As `Q252`.
- **CONFIDENCE:** high

---

### Q255 — At each turn, what should determine the material admitted into the model's active context?

- **DECISION:** Retrieval results filtered by the disclosure dial, plus the bounded turn history, plus the entity list, plus the current request. Assembled by code, size-bounded, and recorded verbatim in the trace.
- **BECAUSE: POSITION.** `P§6`: the dial "decides what may be *said*," which in a generation architecture means the model must not see what it may not say — otherwise the promise depends on the model's discretion, which `Q247` forbids. Note this is a real design consequence: **withholding is enforced by exclusion from context, not by instruction.**
- **REJECTED:** Giving the model everything and instructing it to withhold by tier. It wins on answer quality — the model could say "there is something I'm not telling you" more naturally. It loses because it converts a structural guarantee into a prompt-compliance hope.
- **COST:** The Anbu affordance in `P§6` — "Kivi noticed something here" — must be rendered by code outside the model's answer, because the model never saw the observation. That makes it a UI element rather than part of the response, which is a subtler product than the position implies.
- **CONFIDENCE:** high

---

### Q261 — When should a session contribute anything to persistent memory?

- **DECISION:** A Hey Kivi session contributes nothing by itself. Its user-authored turns are queued as transcripts and go through the ordinary extractor; its corrections write immediately. There is no end-of-session review-and-distil step.
- **BECAUSE: POSITION.** `P§4`'s tiers admit user statements and confirmations only, so there is nothing for a session-end reviewer to add that the ordinary extractor would not.
- **REJECTED:** An end-of-session LLM that reviews and merges distilled knowledge. Wins where sessions are long and the whole is more than the turns. It also has the practical problem the inventory names: "session-end detection" is underspecified, and in a text client there is no reliable session boundary.
- **COST:** Cross-turn facts — something established over three turns but stated in none — are not captured.
- **CONFIDENCE:** high

---

### Q268 — Should the mechanism that decides what the system knows also decide what it may say?

- **DECISION:** No. They are two separate stages with two separate rule sets. Retrieval is unfiltered by permission; disclosure is filtered by the dial; the gap between them is measured and displayed.
- **BECAUSE: POSITION.** `P§1` principle 1: "Calibration. What Kivi knows and what Kivi says are different questions. Retrieval and disclosure must be separable." `P§6` operationalises it: "The dial governs disclosure, not retrieval… a withheld memory leaves a trace that a never-retrieved memory doesn't."
- **REJECTED:** Fusing them — filter at retrieval so the model only ever sees permitted material. It is simpler, cheaper, and marginally safer. It wins if the withheld-count display were dropped. That display is `P§AppC` claim 4 and the Anbu affordance in `P§6`, so it cannot be dropped.
- **COST:** Retrieval does work whose results are discarded, on every Anbu request. Withheld content sits in process memory it will not be allowed to use — a small but real exposure surface.
- **CONFIDENCE:** high

---

### Q269 — When the system's current belief is wrong, what mechanism should change it, and whose correction has authority?

- **DECISION:** The user has absolute authority, exercised through four named actions — **Confirm**, **Correct**, **That's not me anymore**, **Forget** — plus inline correction inside a request. User corrections are synchronous, immediate, and outrank all evidence. No other authority exists; Kivi never self-corrects a stated memory.
- **BECAUSE: POSITION.** `P§9`: "Actions per entry: Confirm (promote), Correct (edit), That's not me anymore (demote + suppress), Forget (remove + suppress)." `P§8`: "Corrections are cheap and inline. *'No, Priya's at Northwind now'* in the middle of a request should update the entity without ceremony."
- **REJECTED:** Model-detected contradiction triggering self-repair. It wins where the user is absent or inattentive, and it would catch stale facts the user never notices. Under `Q174` the system may *flag* a contradiction under Koottu but not resolve it — that is the compromise position.
- **COST:** Stale stated memories persist indefinitely until a human acts. Kivi will be confidently wrong and will know it is possibly wrong without being permitted to fix it.
- **CONFIDENCE:** high

---

### Q270 — Should memory scope and rights differ by interaction surface?

- **DECISION:** Yes, and structurally. Dictation gets entity and lexical memory only, through a path with no access to observation or hypothesis tables. Hey Kivi gets all three types, tier-gated by the dial.
- **BECAUSE: POSITION.** `P§7` entire, and specifically: "No observations. No hypotheses. No patterns. Not filtered out — structurally unable to load them." `P§AppC` claim 7 makes it a demonstrable claim.
- **REJECTED:** One pipeline with uniform rights (the surveyed answer). It wins on architectural economy. It loses the brief's explicit requirement to "decide what belongs in each mode and make that boundary coherent in the product."
- **COST:** Two retrieval paths (`Q138`). And a hard case the position does not settle: a *stated formatting preference* is allowed in dictation per `P§7`, but preferences are a type whose observed tier is forbidden there — so the dictation path needs tier-aware access to one table while having no access to two others. That is a more intricate rule than "two separate paths" suggests. Flagged in **Section A**.
- **CONFIDENCE:** high on the decision, medium on the rule being as clean as the position claims.

---

### Q273 — When experience from one interaction may benefit another, should memory cross user boundaries at all, and under whose authority?

- **DECISION:** Never. There is no cross-user memory, no shared tier, no transfer mechanism. **Out of scope** and also positively forbidden.
- **BECAUSE: POSITION.** `P§1` principle 2 (non-retention of others) and `P§5`. `E1` independently removes the second user.
- **REJECTED:** Private/shared two-tier partition with eligible fragments transferring. It wins for an organisational product where the studio benefits from shared knowledge — a genuinely valuable product. It is the opposite of what this position commits to.
- **COST:** No network effects, no team memory, no path to an enterprise story without rewriting the position.
- **CONFIDENCE:** high

---

### Q277 — When an interaction contains both personal and generally reusable information, what should determine whether a fragment becomes shareable?

- **DECISION:** Nothing becomes shareable. There is no sharing. **Out of scope** (`Q273`).
- **BECAUSE: POSITION.** `P§1` principle 2.
- **REJECTED:** LLM-driven generalisation that strips user-specific detail. Wins in a shared-knowledge product.
- **COST:** As `Q273`.
- **CONFIDENCE:** high

---

### Q280 — How should an interaction be compressed into durable memory without losing the distinctions future policy needs?

- **DECISION:** By typed extraction, not compression. The distinctions future policy needs are exactly `type` and `tier`, and both are assigned at extraction and stored as columns. Nothing is compressed; things are either extracted as typed facts or not retained.
- **BECAUSE: POSITION.** `P§4`'s schema names the distinctions; `P§6` and `P§7` are the "future policy" that reads them.
- **REJECTED:** Key–value fragments with a topic key and a comprehensive value. It wins on recall — a rich value preserves nuance a typed fact loses. It loses because a key–value fragment has no tier, so `P§6`'s dial would have nothing to gate on.
- **COST:** Nuance loss, as `Q33` and `Q154`.
- **CONFIDENCE:** high

---

### Q283 — When memory ages or is not re-observed, should it remain eligible, decay, expire, or be revalidated?

- **DECISION:** By tier. Stated: remains eligible indefinitely. Observed: decays out of surfacing. Hypothesised: expires and is dropped. Revalidation happens only through a user confirmation, which is budgeted.
- **BECAUSE: POSITION.** `P§9`, both bullets, plus `P§8`'s prompt budget which rules out systematic revalidation.
- **REJECTED:** No decay at all (the surveyed answer: "Fragments accumulate; content standing does not change"). Wins if decay windows cannot be set honestly — see `Q24`, where this is the same live objection.
- **COST:** As `Q24`. Also: a stated fact from three years ago is treated exactly like one from yesterday, which is arguably the wrong default and is not something `P§9` addresses. Flagged in **Section A**.
- **CONFIDENCE:** medium

---

### Q291 — What should cause a memory to be surfaced as a rule, an observation, or a question?

- **DECISION:** The tier, and only the tier. Stated → may be applied as a rule. Observed → surfaced as an observation with its evidence, never enforced. Hypothesised → surfaced as a question, only under Daari, only when invited.
- **BECAUSE: POSITION.** `P§4`'s tier table is exactly this mapping: "Treat as true. Use freely" / "Surface as an observation with its evidence. Never as a rule." / "Store as a question. Never assert." And `P§4`: "The difference between those two is the entire product."
- **REJECTED:** Confidence-driven surfacing, where a strong-enough observation is presented as a rule. It wins on usefulness — most users would prefer Kivi just apply the pattern. `P§4` names that as one of the two failure modes: "silently enforces things you never agreed to."
- **COST:** Kivi under-delivers relative to what it knows. A pattern seen fourteen times is still phrased as a question.
- **CONFIDENCE:** high

---

### Q293 — What should happen after a fragment is shown to be wrong or after a policy breach?

- **DECISION:** Two different paths. **Wrong fact:** Correct or demote, with the change recorded and the superseded version kept in history; if demoted via "That's not me anymore," a suppression is written that the extractor must respect on all future runs. **Policy breach** (an excluded-category memory that reached storage): the memory is purged, the breach is recorded as an incident with the reason code and the transcript id, and the exclusion check is treated as defective — this is an evaluation failure, not a user-facing event.
- **BECAUSE: POSITION.** `P§9`: "'That's not me anymore' demotes and blocks re-derivation… The action must record a suppression that the extractor respects going forward. Otherwise the user learns that their corrections don't stick, which is the fastest way to lose them."
- **REJECTED:** No remediation path (the surveyed answer — most papers acknowledge breaches and specify nothing). Wins never.
- **COST:** The suppression list is a permanent second gate on extraction that grows monotonically and can, over time, silently prevent legitimate new facts that resemble suppressed ones. Suppression scope — exact fact vs. pattern vs. category — is not determined by the position. Flagged in **Section A**.
- **CONFIDENCE:** high on the mechanism, low on the scoping rule.

---

### Q297 — F3 — Private/shared two-tier partition (D04)

- **DECISION:** Not adopted. There is one partition: the user's memory. No shared tier. **Out of scope** (`Q273`).
- **BECAUSE: POSITION.** `P§1` principle 2.
- **REJECTED:** The two-tier private/shared partition. Wins in a multi-agent or multi-user deployment where isolated-vs-collaborative performance is the thing being measured.
- **COST:** As `Q273`.
- **CONFIDENCE:** high

---

### Q300 — F7 — LLM coordinator controls authorized specialist selection (D18)

- **DECISION:** Not adopted. There are no specialist agents and no coordinator. One process, three tools, deterministic routing to a single model call. **Out of scope** (`E5`).
- **BECAUSE: ENGINEERING (E5).** Position is silent on agent topology. A coordinator plus specialists is a scale architecture for a broad action space; `Q246` fixes the action space at three.
- **REJECTED:** Coordinator-plus-specialists. Wins when tool count and domain breadth exceed what one prompt can hold.
- **COST:** No path to adding many tools without revisiting routing.
- **CONFIDENCE:** high

---

### Q304 — At what cadence should an interaction be considered for durable memory: every turn, at session boundaries, or only after an explicit save/confirmation event?

- **DECISION:** Per completed transcript, asynchronously (`Q62`, `Q242`). Not every turn, not at session boundaries, not only on explicit save.
- **BECAUSE: ENGINEERING (E3).** `P§AppB` defers timing explicitly.
- **REJECTED:** Explicit-save-only. It is the strongest alternative on trust grounds — nothing is remembered unless the user says so, which would make `P§9`'s control story trivial. It wins if ambient extraction turns out to feel invasive in testing. It loses the product: `P§3`'s value is "you said this once, so say it once," which requires Kivi to catch things the user did not think to save.
- **COST:** Users are not asked before something is remembered. Control is retrospective (see it, correct it) rather than prospective (approve it). That is a defensible reading of `P§9` but it is not consent.
- **CONFIDENCE:** high

---

### Q305 — Which content categories should be eligible for memory, and should exclusions be structural, policy-based, or absent?

- **DECISION:** Eligible: work-level entities, preferences, and episodes. Excluded structurally and by category check: health, mood/emotional state, relationships and family, faith, politics, non-work finances, and character/competence characterisations. Exclusions are **structural on the third-party axis** (source separation) and **policy-enforced-in-code on the category axis**.
- **BECAUSE: POSITION.** `P§2` verbatim for the list; `P§5` for the structural half.
- **REJECTED:** Extracting "detailed information and high-level insights about speakers" with no category exclusion — the surveyed answer, and the default of the field. `P§2` is written specifically against it: "It is achievable… It is unverifiable… It is uncorrectable… It changes what the user is."
- **COST:** Kivi refuses a large class of things it could learn. The exclusion list is also a list a competitor will happily build, and the product has to win on trust rather than capability.
- **CONFIDENCE:** high

---

### Q307 — Should candidate memories be retained by default unless redundant/outdated, or admitted only after passing explicit eligibility tests?

- **DECISION:** Admitted only after passing explicit tests, in order: (1) category exclusion check, (2) third-party/work-level test, (3) typability into one of three types, (4) completeness (`Q86`). Failing any is a reason-coded drop.
- **BECAUSE: POSITION.** `P§3`: "If you'd be irritated to type it a second time, it's a memory. If you'd be unsettled to learn it was recorded, it isn't." That is an eligibility test, not a redundancy filter.
- **REJECTED:** Retain-by-default-unless-redundant (the surveyed answer). Wins on recall and is the higher-performing choice on any benchmark that measures what the system knows. It loses on every claim `P§2` makes.
- **COST:** Recall is capped by four gates, each of which has false positives. The evaluation will show memories that should have been kept and were not.
- **CONFIDENCE:** high

---

### Q309 — Should memory preserve temporal history, only the latest state, or both current state and an auditable history?

- **DECISION:** Both. Current state is what retrieval sees; superseded and demoted versions persist with `status` and a pointer, forming an auditable history that the memory surface can show on demand.
- **BECAUSE: POSITION.** `P§9`: "the superseded version stays in history so the change is auditable." `P§4`: "Demotion and supersession are ordinary operations, not deletions."
- **REJECTED:** Latest-state-only with deletion of the changed memory (the surveyed answer). It wins on storage and on a cleaner privacy story — history is another place old beliefs live. `P§9`'s audit requirement outweighs it.
- **COST:** A **Forget** action must therefore purge history too, or "Forget" is a lie. That means Forget and Correct behave differently with respect to history, which the product must explain in one line.
- **CONFIDENCE:** high

---

### Q328 — Who should control inference depth: the architecture by default, an explicit persistent setting, a per-request invitation, or context/tone inference?

- **DECISION:** All three of the first kind, combined: architecture sets the default (**Anbu**), an explicit persistent two-position setting controls Anbu↔Koottu, and a per-request invitation unlocks Daari for one answer. Tone inference is forbidden.
- **BECAUSE: POSITION.** `P§6`: "The dial is an explicit setting. Default Anbu. Daari is not a persistent mode. It's a per-request invitation." And: "Permission is never inferred from tone. An earlier version had Kivi read the user's tone and pick a tier. That silently deletes the control promise the whole product rests on."
- **REJECTED:** Tone/context inference. It is the most natural-feeling design and would make Kivi seem perceptive. The position has already considered and rejected it, with two reasons: it deletes the control promise, and tone detection is unreliable. This is the clearest example in the document of the position overriding a technically attractive choice.
- **COST:** The user must manage a setting. Most will leave it at Anbu and never see Koottu, which means the product's most distinctive behaviour is opt-in and probably rarely seen. The `P§6` "Kivi noticed something here" affordance exists to mitigate exactly this, and carries more weight than its one paragraph suggests.
- **CONFIDENCE:** high

---

### Q337 — When an LLM itself is stateless, where should cross-request semantic state live?

- **DECISION:** In an external, queryable, persistent store — an embedded SQL database with lexical and vector indexes — not in the context window, not in fine-tuned weights.
- **BECAUSE: ENGINEERING (E2).** Position is silent on storage (`P§AppB` defers it) but `P§9` requires memories to be individually addressable, editable, and suppressible, which requires row-level identity in a store, not tokens in a window.
- **REJECTED:** Long-context-window-as-memory. It wins if the entire corpus fits in context, which at ~500 short transcripts is not absurd. It loses on `P§9` — you cannot demote a paragraph — and on the brief's requirement that behaviour come from "actual state, persistence, retrieval."
- **COST:** Retrieval quality becomes the ceiling on answer quality. A long-context system would never "miss" a memory; this one will.
- **CONFIDENCE:** high

---

### Q339 — Which workload properties should determine the consistency guarantee for a memory operation?

- **DECISION:** None — the question does not arise. Single embedded database, single writer, serialised import. Every read is strongly consistent by construction. **Out of scope** (`E1`, `E2`).
- **BECAUSE: ENGINEERING (E1, E2).**
- **REJECTED:** A consistency-selection framework driven by read/write ratio and staleness tolerance. It wins in a distributed deployment. There is no distribution here to make it meaningful.
- **COST:** No scale path. Distributing this system later means designing consistency from nothing.
- **CONFIDENCE:** high

---

### Q340 — Should one consistency guarantee govern all memories, or should guarantees vary by operation or memory class?

- **DECISION:** One: strong, by construction. **Out of scope** (`Q339`).
- **BECAUSE: ENGINEERING (E2).**
- **REJECTED:** Hybrid/tunable consistency. Wins in a distributed system.
- **COST:** As `Q339`.
- **CONFIDENCE:** high

---

### Q342 — When input contains material useful for the current response but impermissible for durable memory, where should retention be blocked?

- **DECISION:** At the boundary between the context window and the write path, structurally — the extractor's input is the user's dictation, and application context is passed to the *generator* only. The extractor never receives third-party content, so there is nothing to block downstream.
- **BECAUSE: POSITION.** `P§5`: "Third-party content enters the context window. It does not enter the write path. This is a structural rule, not a filter applied afterward." This is the single most architecturally consequential sentence in the position document — it fixes the shape of the pipeline.
- **REJECTED:** Blocking at the write, after extraction has seen everything. It wins on extraction quality: an extractor that sees Priya's message understands the dictation better and could produce a *better* work-level fact ("the review moved because Priya is away"). That version is strictly more useful and is exactly what `P§5` forbids. The condition under which it wins is if work-level facts prove unextractable without their third-party context — which the corpus will reveal, and which is the sharpest empirical risk in this design.
- **COST:** Extraction quality drops on any dictation whose meaning depends on the message being replied to. "Tell her that's fine, move it to Tuesday" is nearly uninterpretable without Priya's message. This is a serious, under-appreciated cost and it deserves an explicit evaluation case.
- **CONFIDENCE:** high on the decision, medium on the cost being survivable.

---

### Q346 — When any stale read could break task logic, should reads wait for the latest committed global state?

- **DECISION:** Not applicable — there is no stale read. **Out of scope** (`Q339`).
- **BECAUSE: ENGINEERING (E2).**
- **REJECTED:** Strong consistency with coordination cost. Already have it for free.
- **COST:** None.
- **CONFIDENCE:** high

---

### Q347 — When updates are related by cause but unrelated updates may diverge, is preserving causal order enough?

- **DECISION:** Not applicable. Serialised writes give total order. **Out of scope** (`Q339`).
- **BECAUSE: ENGINEERING (E2).**
- **REJECTED:** Causal consistency. Wins in a distributed store.
- **COST:** None.
- **CONFIDENCE:** high

---

### Q350 — Should the system change consistency levels dynamically as workloads or task demands change?

- **DECISION:** No. **Out of scope** (`Q339`).
- **BECAUSE: ENGINEERING (E2).**
- **REJECTED:** Dynamic adaptation. Named as future work even by its source.
- **COST:** None.
- **CONFIDENCE:** high

---

### Q354 — When stronger consistency reduces availability or raises latency, whose cost should dominate: system throughput, task correctness, or the user's waiting and trust cost?

- **DECISION:** Trust cost dominates, always. Where the trade-off appears in this build it appears as *abstention vs. a degraded answer* (`Q27`, `Q183`), not as a consistency level, and the answer is: abstain.
- **BECAUSE: POSITION.** `P§8`: "Kivi never fills a gap with a plausible guess. A fluent invented answer is worse than no answer, because it's indistinguishable from a real one until it costs you something."
- **REJECTED:** Throughput or latency dominance. Wins in a high-volume service. The brief asks for latency and cost to be *reported*, not minimised.
- **COST:** Kivi is slower and less available than it needs to be, and the evaluation numbers will show it.
- **CONFIDENCE:** high

---

### Q355 — When conversation spans time and people, what unit should organize the interaction history?

- **DECISION:** The transcript — a single dictation or Hey Kivi exchange with a timestamp and its application context. Not a session, not an episode-of-six, not a per-partner thread.
- **BECAUSE: ENGINEERING (E3).** Position is silent on the organising unit but assumes it throughout: `P§5`'s "read, not kept" marker attaches to "the transcript's inspection view," and `P§9`'s provenance is "the actual transcript, with a date." The brief supplies records, not sessions.
- **REJECTED:** Multi-session episodes centred on a main speaker with rotating partners. It wins for evaluating longitudinal conversational memory, which is what its source is for. It does not match the corpus shape the brief describes.
- **COST:** No native notion of "this conversation" spanning transcripts. Threading is reconstructed from entities and time, imperfectly.
- **CONFIDENCE:** high

---

### Q356 — Whose point of view should determine what a shared interaction becomes in memory?

- **DECISION:** The user's, exclusively and egocentrically. Every memory is a fact about Meera's working world. No partner-perspective memories exist.
- **BECAUSE: POSITION.** `P§5`: "What survives is the work-level residue about *your* world." `P§1` principle 2.
- **REJECTED:** Egocentric-plus-per-partner memories, which is what the surveyed system does and is a reasonable design for a social agent. It wins there; here the "about each partner" half is exactly what `P§5` forbids.
- **COST:** Kivi has no model of how anyone else sees anything, including how the user's requests land with their recipients.
- **CONFIDENCE:** high

---

### Q357 — Which parts of a completed interaction are important enough to write into long-term memory?

- **DECISION:** Durable work-level facts about the user's world in three types, passing four eligibility gates (`Q307`). Explicitly **not** "expressed emotions" — that is an excluded category.
- **BECAUSE: POSITION.** `P§2`: "Kivi never infers or stores: health, **mood or emotional state**…" The surveyed answer extracts "significant events, experiences, appointments, and expressed emotions"; three of those four are permitted and the fourth is the single clearest violation in the inventory.
- **REJECTED:** Including expressed emotion. It wins in an empathetic-companion product. `P§3` rules that product out: "A product that models your goals and insecurities is studying you."
- **COST:** Kivi cannot register that a project went badly, only that it happened.
- **CONFIDENCE:** high

---

### Q358 — When an input contains information about another person, what may survive after the immediate task?

- **DECISION:** Name, role, organisation, project association, canonical spelling. Nothing else (`Q55`).
- **BECAUSE: POSITION.** `P§5`, including the worked example which lists exactly what is kept and exactly what is dropped.
- **REJECTED:** Retaining partner experiences, thoughts, emotions, health, and relationships from the user's perspective — the surveyed answer, and a direct inversion of this position. It wins in a product whose job is social memory. It is the precise thing `P§5` is written against, and the `P§5` worked example ("Mum's in hospital") reads like a rebuttal of it.
- **COST:** As `Q55`.
- **CONFIDENCE:** high

---

### Q359 — When should memory extraction run, and what context should it see?

- **DECISION:** Once per transcript, asynchronously. It sees: the user's dictation (raw and formatted), the transcript metadata, and the current entity list for disambiguation. It does **not** see application context or third-party message content (`Q342`).
- **BECAUSE: POSITION.** `P§5` for what it may not see; `P§AppB` leaves timing open, so timing is `ENGINEERING` per `Q62`.
- **REJECTED:** Extraction over the entire session including all parties' content. Wins on extraction quality — see the cost note in `Q342`, which is the same trade-off.
- **COST:** As `Q342`.
- **CONFIDENCE:** high

---

### Q361 — When several statements concern the same evolving situation, should the system replace history, preserve it, or connect it?

- **DECISION:** Replace the *current* value and preserve the old one as superseded history with a link (`Q309`, `Q173`). Not merely connect — a superseded fact must stop being retrieved as current, or Kivi will state both.
- **BECAUSE: POSITION.** `P§9`: "New evidence doesn't stack alongside old evidence; it replaces it, and the superseded version stays in history." The word "replaces" rules out pure linking.
- **REJECTED:** Preserve-and-link everything, using the newest item as a guide to associated past memories. It wins for questions about *how* something evolved — "how many times did this move?" — which is exactly the Koottu example in `P§6` ("You've moved this deadline three times: the 4th, the 11th, and the 18th"). Note that the Koottu example requires the superseded versions to be *retrievable as evidence*, so the history is not inert; it is retrievable as observation evidence while being excluded from current-fact retrieval. That distinction is load-bearing and is easy to implement wrongly.
- **COST:** Two retrieval semantics over the same rows — current-facts and evidence-history — which must never leak into each other.
- **CONFIDENCE:** medium

---

### Q362 — What should count as a relationship between two memories?

- **DECISION:** Four typed relations, all system-generated and all inspectable: `supersedes`, `evidence_for` (transcript → memory), `about_entity` (memory → entity), and `entity_relation` (entity → entity, e.g. *client-contact-at*). No generic positive/negative association links.
- **BECAUSE: POSITION.** `P§4` defines entity memory as including "the relations between them," and `P§9` requires supersession links. The rest of the graph is not asked for.
- **REJECTED:** Binary positive/negative associative links that may cross speakers (the surveyed answer). It wins for associative recall — pulling in related context the user did not ask for. It loses because links that cross speakers are forbidden by `P§5`, and because an untyped association cannot be explained in the Why panel.
- **COST:** No associative retrieval. Kivi will not surface the relevant-but-not-asked-for memory that a graph walk would have found.
- **CONFIDENCE:** high

---

### Q368 — When the system is wrong, who detects and repairs the memory, and what persists afterward?

- **DECISION:** The user detects and repairs, through the four actions (`Q269`). What persists: the corrected memory as current, the old version as superseded history, a record of the correction event with its timestamp, and — for demote and forget — a suppression record the extractor must honour.
- **BECAUSE: POSITION.** `P§9` in full, especially: "deleting the row is useless, because the same pattern will regrow from the same transcripts within a week."
- **REJECTED:** No correction mechanism (the surveyed answer for most sources — the inventory notes "no user correction, rollback, provenance inspection, or re-derivation suppression mechanism"). Wins never here; this is the position's central differentiator.
- **COST:** As `Q293` — an accumulating suppression list with undetermined scope.
- **CONFIDENCE:** high

---

### Q370 — What data should train and test the memory system when real multi-person longitudinal data are scarce?

- **DECISION:** A generated corpus of ~500 transcript-like records built to the `P§AppA` cast and world, deliberately constructed to exercise each of the seven `P§AppC` claims, with the generation procedure and prompts committed to the repository. Not used for training (`Q131`) — only for development and evaluation.
- **BECAUSE: POSITION.** `P§AppA` fixes the cast "so the corpus, the evaluation, and the demo all use one consistent world," and lists the required varieties: "transcripts that produce facts, transcripts that produce nothing, transcripts containing third-party content that must be dropped, contradictions that require supersession, and questions whose answers are genuinely absent."
- **REJECTED:** Open-source conversational data. It wins on realism and removes the risk of a corpus generated to flatter the system. That risk is real and the mitigation is weak: a corpus I generate will contain the third-party content my extractor is good at dropping. The brief's second-stage evaluation on *their* corpus is the actual check, and I should design as if my own corpus proves nothing.
- **COST:** Self-generated corpora validate the system against the author's assumptions. Every headline number from this evaluation is suspect until the internal corpus runs.
- **CONFIDENCE:** high on the decision, low on the corpus being evidence of anything.

---

### Q372 — Should memory accept only text, or preserve multimodal/tool structure?

- **DECISION:** Text only (`Q98`). Transcript records keep both raw ASR and formatted output as separate fields, since the brief supplies both and the difference is informative; neither is multimodal.
- **BECAUSE: POSITION.** The scope note: "this document assumes a text client."
- **REJECTED:** Preserving typed content items and tool calls. Wins in an agentic product; `Q12` already excludes the tool lifecycle.
- **COST:** None here.
- **CONFIDENCE:** high

---

### Q378 — Are memories first-class typed beliefs or narrative/utility artifacts?

- **DECISION:** First-class typed beliefs. Three types, three tiers, each individually addressable, correctable, and suppressible.
- **BECAUSE: POSITION.** `P§4` and `P§9`. The surveyed alternative — "episodes, atomic facts, foresights, aggregate profile, agent cases, and skills" — contains at least three artefact kinds (`foresights`, `agent cases`, `skills`) that have no tier and no correction story.
- **REJECTED:** A mixed set including an aggregate profile. The aggregate profile is the specific thing `P§2` refuses: "The first version of this design was an ontology of everything Kivi could learn… It was also the wrong product."
- **COST:** No summary view of the user. Kivi cannot answer "what do you know about me?" with anything but a list.
- **CONFIDENCE:** high

---

### Q380 — When content changes, rewrite truth or append a new immutable version?

- **DECISION:** Append a new version and mark the old superseded (`Q309`). Never rewrite in place, except for a `Correct` action on a stated memory's text, which also writes a superseded record.
- **BECAUSE: POSITION.** `P§9`: "the superseded version stays in history so the change is auditable."
- **REJECTED:** Atomic rewrite (the surveyed answer for daily files). It wins on storage and simplicity, and loses the audit trail.
- **COST:** Row growth and the `Forget`-must-purge-history complication from `Q309`.
- **CONFIDENCE:** high

---

### Q382 — Should enrichment block the request or evolve offline?

- **DECISION:** Offline, after commit, for everything except the two things that must be synchronous: user corrections, and the transcript record itself.
- **BECAUSE: ENGINEERING (E3, and `Q62`).**
- **REJECTED:** Synchronous enrichment. Wins if the freshness lag is user-visible in the demo, which it may be.
- **COST:** As `Q62`, plus `Q148`'s transient inconsistent state.
- **CONFIDENCE:** medium

---

### Q384 — Should profiles refresh continuously, periodically, or only on confirmation?

- **DECISION:** There is no profile. The question dissolves. Individual memories update on new evidence; there is no aggregate representation of the person to refresh.
- **BECAUSE: POSITION.** `P§2` rejects the profile as a product: "a psychological profile of a person is extractable from their dictations. That is exactly why it should not be built." And `P§2`'s list of what the rejected ontology contained — "working style, goals, motivations, insecurities, self-image."
- **REJECTED:** A continuously refreshed profile. It wins on answer quality for broad questions and on prompt economy — one profile blob is cheaper to load than twenty facts. This is a genuine engineering cost of a position-driven refusal, and worth naming as such.
- **COST:** Broad questions ("how do I usually handle client escalations?") have no aggregate to answer from and must be answered by retrieving and composing individual memories, or abstained on.
- **CONFIDENCE:** high

---

### Q388 — What gets returned and in what order?

- **DECISION:** A ranked, typed result set with per-item score components (lexical rank, vector rank, fused rank, tier, evidence, recency), plus the withheld set with reasons, plus the search description for the abstention path. Ordered per `Q26`.
- **BECAUSE: POSITION.** `P§6`: the trace shows "3 memories retrieved, 1 withheld (observation, requires Koottu)" — which requires the retrieval result to carry both sets and the reason. `P§8` requires the searched-for description.
- **REJECTED:** Returning only the used memories. Wins on payload size; loses `P§AppC` claim 4, which needs the withheld set to be shown from the same underlying retrieval.
- **COST:** The retrieval API carries material the answer may not use, which must be handled carefully so the withheld content does not reach the model (`Q255`).
- **CONFIDENCE:** high

---

### Q392 — On decider failure, abstain or return a deterministic fallback?

- **DECISION:** Abstain, and say what failed. No fallback core, no best-guess candidate set.
- **BECAUSE: POSITION.** `P§8`: "Kivi never fills a gap with a plausible guess." A deterministic fallback set after three failed attempts is a plausible guess with extra steps.
- **REJECTED:** Retry three times then fall back to a deterministic core (the surveyed answer, which is a sensible availability design). It wins where an approximate answer beats no answer — support search, recommendation. It loses on a memory product whose claim is that its answers are grounded.
- **COST:** Kivi is less available. Transient model failures become visible abstentions.
- **CONFIDENCE:** high

---

### Q394 — Should failures block durable writes?

- **DECISION:** Failures in extraction and in the exclusion check block the write absolutely. Failures in post-commit side effects (embedding, index refresh, activity log) do not block, but are recorded and flagged for repair (`Q148`).
- **BECAUSE: POSITION.** `P§2`: the exclusion check runs "before anything reaches storage," so a check that could not run cannot be bypassed — fail closed. The post-commit half is `ENGINEERING` per `Q148`.
- **REJECTED:** Fail-open on the exclusion check when the classifier errors. It wins on availability of the write path. It is unacceptable: an unavailable exclusion check means the one hard promise cannot be kept, and the correct behaviour is to not write.
- **COST:** A classifier outage stops all memory formation. Extraction backlog grows; nothing is lost, but nothing is learned either.
- **CONFIDENCE:** high

---

### Q395 — What structure should determine how durable memory is organized and navigated?

- **DECISION:** A relational schema navigated by tier and type, surfaced to the user as three groups — *Things you told me / Things I've noticed / Things I'm wondering about*. Not a file tree, not a commit graph, not branches.
- **BECAUSE: POSITION.** `P§9`: "The memory surface is grouped by tier… because that grouping is what carries the epistemics to a normal user without a single word of explanation." `P§4` repeats it. The organising structure is chosen for legibility to a person, not for the system's convenience.
- **REJECTED:** A Git-like directory and history with branches and commits. It wins for an agent doing long-horizon work with divergent explorations, and its audit properties are genuinely better than mine. It loses on `P§9`'s constraint that the navigation structure be the one a normal user reads, and on `P§9`'s "No developer console anywhere in this."
- **COST:** No branching, no exploration of alternative memory states, no merge. Audit is a status column and a history table rather than a real version graph.
- **CONFIDENCE:** high

---

### Q396 — What should determine when transient experience becomes a durable checkpoint?

- **DECISION:** Nothing — there are no checkpoints. Durability is per-transcript extraction (`Q242`). Kivi never decides that a moment is significant.
- **BECAUSE: POSITION.** `P§2`'s warning about plausible inference applies directly: a system that judges which moments are milestones is characterising the shape of the user's work.
- **REJECTED:** Agent-initiated COMMIT at meaningful milestones. It wins for autonomous long-horizon tasks. Kivi's tasks are single-turn.
- **COST:** No notion of project phases or milestones, even though `P§AppA`'s world clearly has them.
- **CONFIDENCE:** high

---

### Q397 — Once a checkpoint is made, what should be retained at each level of abstraction?

- **DECISION:** Not applicable — no checkpoints (`Q396`). The two retained levels are: raw transcript, and extracted typed fact. There is no third, intermediate, summarised level.
- **BECAUSE: POSITION.** `P§4` (facts) and `P§9` (raw provenance). The absence of a middle level is `Q154`'s decision.
- **REJECTED:** A recursively regenerated progress summary. Wins for long-horizon work; see `Q154`'s cost note, which is the same gap.
- **COST:** As `Q154`.
- **CONFIDENCE:** high

---

### Q398 — When a durable summary is updated, what should determine continuity with the past?

- **DECISION:** Not applicable — no summaries (`Q154`). Continuity is carried by `source_transcript_ids[]`, `first_seen_at`, `evidence_count`, and the supersession chain.
- **BECAUSE: POSITION.** `P§4`'s schema fields are the continuity mechanism.
- **REJECTED:** Regenerating a coarse summary from the previous summary plus the latest contribution. It wins on narrative coherence and loses on correctability — each regeneration is a new uncorrectable artefact.
- **COST:** As `Q154`.
- **CONFIDENCE:** high

---

### Q399 — When should the global account of the work change?

- **DECISION:** There is no global account. **Out of scope** — same refusal as `Q384` and `Q378`.
- **BECAUSE: POSITION.** `P§2`'s rejection of the aggregate profile.
- **REJECTED:** A maintained `main.md`-style global summary. It wins for orientation — a user landing on the memory surface would benefit from a paragraph. Note the memory surface instead opens on three tier-grouped lists, which `P§9` argues is orientation enough.
- **COST:** No overview. The memory surface is a list, and at a few hundred memories that is a lot of list.
- **CONFIDENCE:** high

---

### Q400 — When reasoning diverges, what should determine whether alternatives share one history or receive isolated state?

- **DECISION:** No branching. One linear memory state. **Out of scope** (`Q395`).
- **BECAUSE: ENGINEERING (E5).** Position is silent; branching serves exploratory agent work that Kivi does not do.
- **REJECTED:** Agent-initiated BRANCH with isolated traces. Wins for long-horizon exploration.
- **COST:** No way to model "what if I hadn't told it that" other than by reset-and-reimport.
- **CONFIDENCE:** high

---

### Q403 — When the active window is bounded, what should be discarded from model-visible context versus preserved externally?

- **DECISION:** Everything is preserved externally by default; the model sees only the assembled per-request context (`Q255`), which is bounded by a top-k retrieval cap and the turn-history cap. Nothing is *discarded* — it is simply not selected, and the trace records what was selected and what was not.
- **BECAUSE: POSITION.** `P§8`'s trace requirement, plus `P§6`'s distinction between retrieved-and-withheld and never-retrieved, which requires the boundary between store and context to be an explicit recorded selection.
- **REJECTED:** Incremental traversal, where the model pages through context on demand. It wins for large corpora and is elegant. It makes the used-context set model-determined and therefore only reconstructable after the fact, weakening the trace.
- **COST:** A hard top-k cap means a relevant memory ranked k+1 is invisible with no recovery. The cap value is unset — see **Section A**.
- **CONFIDENCE:** high

---

### Q405 — What should a memory consumer be allowed to inspect?

- **DECISION:** Everything that produced the answer, through one surface serving both audiences: retrieved set with scores, withheld set with reasons, used set, per-memory tier/evidence/dates, and one tap to the source transcript. No separate developer view.
- **BECAUSE: POSITION.** `P§8`: "This is simultaneously the user's trust mechanism and the engineer's inspection tool. Building one thing that serves both is the right call — if the explanation is only intelligible to a developer, we've failed the brief's requirement that the product be legible to a normal user." And `P§9`: "No developer console anywhere in this."
- **REJECTED:** Two surfaces — a plain one for users, a rich one for engineers. It wins on both audiences being served optimally, and it is what almost every product does. The position rejects it explicitly, and the cost below is the price of that rejection.
- **COST:** Engineering diagnostics that genuinely do not belong in a user surface — token counts, model latencies, embedding distances, queue state — have nowhere to live. Either they leak into the user's Why panel or they go to logs that `P§9` says are not part of the inspection story. **This is a real gap in the position and is flagged in Section A.**
- **CONFIDENCE:** medium

---

### Q406 — When the memory system is wrong, what should recovery operate on?

- **DECISION:** On the individual memory, through the four user actions, plus a documented full reset-and-reimport for the system as a whole. Not on a version graph.
- **BECAUSE: POSITION.** `P§9`'s per-entry actions. The full reset is `ENGINEERING` — the brief requires "the exact procedure for resetting the system."
- **REJECTED:** Git-style rollback of the whole memory state. It wins for recovering from a bad extraction run affecting many memories at once, which is a realistic failure. Currently the only remedy for that is full reimport, which destroys user corrections — a genuine weakness worth naming.
- **COST:** No partial rollback. A bad extractor deployment means choosing between keeping bad memories and losing user corrections.
- **CONFIDENCE:** medium

---

### Q407 — What happens to memory merely because time passes?

- **DECISION:** Observations decay; hypotheses expire; nothing else changes (`Q24`, `Q283`).
- **BECAUSE: POSITION.** `P§9`.
- **REJECTED:** Nothing happens with time (the surveyed answer). See `Q24` — this is the same live objection about unset windows.
- **COST:** As `Q24`.
- **CONFIDENCE:** medium

---

### Q409 — How much extra computation and interaction is acceptable in exchange for better long-horizon performance?

- **DECISION:** Very little. One extraction call per transcript, one retrieval, at most one generation call, no agentic loops, no reflection passes. Cost and latency are reported honestly rather than optimised.
- **BECAUSE: ENGINEERING (E5).** Position is silent (`P§AppB` defers "Cost and latency targets"). The brief requires reporting "latency, database growth, model usage, and cost wherever they matter," which makes extra calls a reported liability, not an invisible one.
- **REJECTED:** Accepting more calls for better long-horizon performance. It wins where long-horizon task success is the metric. Kivi's metric is whether it knows what you told it.
- **COST:** No reflection, no multi-pass extraction, no self-consistency checks — each of which would improve extraction quality measurably.
- **CONFIDENCE:** medium

---

### Q412 — When facts enter verification, should their origin and admission be part of the input contract or trusted upstream?

- **DECISION:** Part of the contract. Every memory carries its source transcript ids and its extraction run identity, and no memory may exist without them (`Q86`). Nothing is trusted upstream.
- **BECAUSE: POSITION.** `P§9`: "Every memory shows its provenance."
- **REJECTED:** Trusting upstream admission and verifying only the logical content. Wins in a formal-verification context where inputs are given. Here provenance is the product.
- **COST:** Provenance is on the critical path of every write, and any path that cannot supply it cannot write.
- **CONFIDENCE:** high

---

### Q421 — When values are missing, should the semantic model collapse them to SQL null or distinguish reasons for absence?

- **DECISION:** Distinguish. Absence has three distinct meanings in this system and they must not collapse: **not known** (no memory), **known but withheld** (permission), and **known to be absent** (superseded, demoted, or suppressed). The retrieval result and the trace carry which one applies.
- **BECAUSE: POSITION.** `P§6`'s trace explicitly distinguishes withheld from not-retrieved: "a withheld memory leaves a trace that a never-retrieved memory doesn't." `P§8`'s abstention distinguishes "I don't have anything" from near-misses.
- **REJECTED:** Collapsing to a single null/empty result. It wins on API simplicity. It destroys the calibration principle at the surface, because "I don't know" and "I won't say" would look identical.
- **COST:** Three absence semantics to implement, test, and render. The abstention message has three shapes.
- **CONFIDENCE:** high

---

### Q428 — Which workload should determine whether the approach is useful: available translation pairs, a feature-balanced suite, or real application operations?

- **DECISION:** Real application operations — a feature-balanced suite built from the seven `P§AppC` claims plus the brief's evaluation list, exercised end to end on the corpus. Not a benchmark of convenient pairs.
- **BECAUSE: POSITION.** `P§AppC`: "Each of these should be provable from the evaluation output, not asserted in the README." The claim list *is* the evaluation suite's spine.
- **REJECTED:** A larger benchmark of convenient cases. It wins on statistical power. It loses because the brief will run its own corpus and the only thing my evaluation can usefully establish is that the specific claims hold.
- **COST:** Small-N evaluation. Per-claim results will be demonstrations, not measurements, and must be reported as such.
- **CONFIDENCE:** high

---

### Q429 — When no counterexample appears, what independent evidence should estimate missed bugs?

- **DECISION:** Manual inspection of a fixed random sample of transcripts where extraction produced nothing and where all candidates were dropped, reported as a count of judged-wrong cases. The false-negative rate of the exclusion check and the work-level test is reported, not assumed to be zero.
- **BECAUSE: ENGINEERING (E4).** The position requires drops to be *visible* (`P§2`) but does not require them to be *audited for correctness*. Auditing is what turns a visible drop log into evidence, and the brief asks "whether failures remain visible" and "whether the conclusions follow from the evidence."
- **REJECTED:** Reporting only observed successes. It wins on effort and is the default. It is exactly the failure the brief flags: conclusions not following from evidence.
- **COST:** Manual inspection does not scale and is subjective. It will produce a number with wide uncertainty that must be reported with its method.
- **CONFIDENCE:** high

---

### Q438 — What is idempotent and what must be ordered?

- **DECISION:** Duplicate of `Q08`/`Q180`. Idempotent on `transcript_id`; ordered by `occurred_at`; memory writes keyed by `(transcript_id, candidate_index)`.
- **BECAUSE: ENGINEERING (E2, E3).**
- **REJECTED:** See `Q08`.
- **COST:** See `Q08`.
- **CONFIDENCE:** high

---

### Q440 — Who owns customization?

- **DECISION:** Nobody. There is no extension mechanism, no plugin interface, no tenant configuration. Prompts, schema, and rules are committed code. The only user-facing configuration is the permission dial and, for honesty about `Q24`, the decay/expiry windows as documented settings.
- **BECAUSE: ENGINEERING (E5, E2).** Position is silent. An extension surface is code the reviewer must understand and cannot be exercised by the review path.
- **REJECTED:** A storage/retrieval plugin interface. It wins if the reviewer wanted to swap the store, which the brief does not ask for — it asks for one documented arrangement.
- **COST:** Every variation is a fork. No path to per-deployment behaviour.
- **CONFIDENCE:** high

---

### Q441 — When an interaction occurs, which parts should become durable memory rather than remain transient context?

- **DECISION:** Duplicate of `Q307`/`Q357`. Work-level, durable, typable facts about the user's world, passing the four gates. Everything else stays transient.
- **BECAUSE: POSITION.** `P§3`: "the durable, work-level things you would be annoyed to have to repeat."
- **REJECTED:** Retain task-relevant novel records broadly, filtering only low signal. It wins on recall; loses on `P§2` and `P§5`.
- **COST:** As `Q307`.
- **CONFIDENCE:** high

---

### Q442 — When candidate memories vary in risk, what should set the write threshold?

- **DECISION:** Risk does not set a threshold — it sets a gate. There is one binary admission test per gate (`Q307`), not a risk-weighted score. High-risk categories are not admitted at a higher bar; they are not admitted at all.
- **BECAUSE: POSITION.** `P§2`: "A **hard** exclusion list enforced at extraction." A threshold implies a trade: enough value buys admission. The position does not offer that trade for excluded categories.
- **REJECTED:** Application-level risk analysis setting per-category thresholds, with high-consequence facts given higher recall priority. It wins in a domain where a missed high-stakes fact is worse than a retained sensitive one — clinical, legal, financial operations. Kivi's stakes are the opposite: a missed preference is an annoyance, a retained inference about mood is a breach.
- **COST:** No way to admit a genuinely important fact that happens to brush an excluded category. "The Q3 launch slipped because Arun was out sick" is a work-critical fact that is permanently unlearnable.
- **CONFIDENCE:** high

---

### Q444 — When the system forms a higher-order lesson, what evidence and uncertainty should accompany it?

- **DECISION:** Kivi does not form higher-order lessons. The nearest artefact is an observation, which carries: `evidence_count`, every `source_transcript_id`, `first_seen_at`, `last_seen`, and a tier that forbids it being used as a rule. It carries no confidence score.
- **BECAUSE: POSITION.** `P§4`: observations are "pointable-at" and surfaced "with evidence." Tier, not confidence, is the uncertainty representation — `P§4`'s whole argument is that collapsing type and epistemic standing into one number is "where most memory systems go wrong."
- **REJECTED:** Confidence-scored reflections with decay of unsupported confidence. It is the closest thing in the inventory to this position and it is a good design. It wins if the product needs a continuous ranking of belief strength. It loses because a confidence number invites exactly the collapse `P§4` forbids: a 0.9 observation starts getting treated as a rule.
- **COST:** No graded belief. A pattern with 14 instances and one with 3 are distinguished only by a count the user has to interpret.
- **CONFIDENCE:** high

---

### Q447 — What should be the authoritative substrate for durable memory?

- **DECISION:** A single embedded relational database (SQLite) holding typed memory records, entities, transcripts, drop logs, suppressions, and vectors as a rebuildable cache. Structured query is authoritative; the vector index is an accelerator, never a source of truth.
- **BECAUSE: ENGINEERING (E2).** `P§AppB` explicitly defers storage. `E2` forces embedded. `P§9`'s per-row lifecycle operations force relational over pure vector.
- **REJECTED:** A vector store as primary with structured metadata attached. It wins for semantic recall breadth and is the field default. It loses because `status`, `tier`, supersession chains, and suppression lists are relational operations that a vector store makes awkward, and `P§7`'s structural path separation is a grant/table-access property.
- **COST:** Semantic recall is bounded by what a small brute-force vector search over a few hundred rows can do. No ANN tuning, no scale path without replacing the substrate.
- **CONFIDENCE:** high

---

### Q457 — When the system learns from operational traces, what should be optimized over time?

- **DECISION:** Nothing automatically. Traces are inspection artefacts (`P§8`) and evaluation inputs. They do not feed a tuning loop, a learned controller, or a retrieval optimiser.
- **BECAUSE: POSITION.** `P§6`: "Permission is never inferred from tone" establishes that behaviour must not adapt to signals the user did not set. A trace-driven optimiser adapts behaviour to observed user reaction, which is the same failure in a different clothing.
- **REJECTED:** Log-driven tuning of retrieval and indexing for downstream utility. It wins in a product where relevance improvement is uncontroversial and is the obvious path to better answers. The condition under which it wins here: if the tuned quantity were purely mechanical (index parameters) and could not change *what Kivi is permitted to say*. That distinction is maintainable in principle and I am declining it for `E5` — it is a subsystem serving none of the seven claims.
- **COST:** Kivi never gets better from use. Every improvement is a code change.
- **CONFIDENCE:** medium

---

### Q458 — When new supervision arrives, should adaptation change model parameters or an external, inspectable state?

- **DECISION:** External, inspectable state only. The model is frozen and pinned (`Q131`). All adaptation is rows in a database the user can read and change.
- **BECAUSE: POSITION.** `P§9`: "Every belief is attributable… and the person can change what Kivi thinks about them in one action." A parameter change is neither attributable nor reversible in one action.
- **REJECTED:** Parameter adaptation. Wins where the behaviour to be learned is not expressible as facts. Everything Kivi learns is expressible as facts by construction (`Q240`).
- **COST:** As `Q131` — behaviour quality capped by the frozen model.
- **CONFIDENCE:** high

---

### Q459 — Who should turn a supervised event into reusable memory?

- **DECISION:** The extractor turns a *user statement* into memory. There is no critic, no self-supervision, no model-generated critique of Kivi's own performance. The only supervision is the user's four actions.
- **BECAUSE: POSITION.** `P§4`: the Stated tier is "The user said it, or confirmed it when asked." There is no tier for "Kivi concluded it about itself."
- **REJECTED:** An LLM critic generating critiques from failures. It wins for agent self-improvement — a genuinely powerful pattern. It requires a memory kind that has no tier and would bypass the user's authority entirely.
- **COST:** As `Q12`/`Q240` — no learning from Kivi's own performance.
- **CONFIDENCE:** high

---

### Q461 — What structure should each learned critique preserve?

- **DECISION:** Not applicable — no critiques (`Q459`). The structure a *memory* preserves is `P§4`'s schema: type, tier, content, evidence count, source ids, dates, status.
- **BECAUSE: POSITION.** `P§4`.
- **REJECTED:** The assertion / local reason / global reason triple. It is a good structure and its "global reason" field is close to what a Kivi observation is. It wins in a self-improving agent.
- **COST:** None here.
- **CONFIDENCE:** high

---

### Q463 — What should episodic memory retain from a supervised event?

- **DECISION:** A Kivi episode retains: what happened, when, which entities were involved, and the source transcript. Not the question, not Kivi's prediction, not a correction pair — those are agent-training artefacts.
- **BECAUSE: POSITION.** `P§4`'s Episode definition: "Something that happened, with a time — *On 12 March the user moved the Atlas review from Tuesday to Thursday.*" The example is entirely about the user's world; nothing about Kivi appears in it.
- **REJECTED:** Retaining the question/prediction/correct-answer triple as demonstrations. Wins for in-context learning from past mistakes.
- **COST:** Kivi cannot use its own past errors as few-shot examples.
- **CONFIDENCE:** high

---

### Q465 — How tightly should semantic-memory format be specified?

- **DECISION:** Tightly. A strict typed schema with required fields, enumerated types and tiers, and a rejection path for malformed output (`Q86`, `Q72`). No free-form bullet lists.
- **BECAUSE: POSITION.** `P§4`: "The grammar of storage enforces the epistemics. You cannot accidentally use a question as a fact." A deliberately vague format makes that guarantee impossible.
- **REJECTED:** Intentionally vague formatting leaving the extractor flexibility. It wins on extraction recall — the model can express things that do not fit a schema, and some of those will be valuable. It loses the one guarantee the position calls non-negotiable.
- **COST:** Facts that do not fit are lost rather than captured loosely (`Q142`, `Q152`).
- **CONFIDENCE:** high

---

### Q467 — How should episodic and semantic memory be combined when both are used?

- **DECISION:** They are not separate stores to combine — entity, preference, and episode are three types in one store, retrieved together by one query and ordered by one ranking (`Q26`). The assembled context presents them grouped by type with tier labels, not concatenated in a fixed order.
- **BECAUSE: POSITION.** `P§4` presents type as a single axis of one schema. `P§6`'s dial gates on tier across all types uniformly, which requires one pipeline.
- **REJECTED:** Separate retrieval per memory kind with fixed prompt concatenation. It wins when the kinds live in genuinely different stores with different retrieval characteristics. Here they share a schema.
- **COST:** No per-type retrieval tuning. A query that should weight episodes heavily gets the same treatment as one that should weight preferences.
- **CONFIDENCE:** medium

---

### Q469 — How many episodic memories should be placed in context?

- **DECISION:** A configured top-k over the fused ranking across all types, not a per-type quota. The value of k is a parameter that needs corpus data — `P§AppB` says so — and is therefore **not set here**. See **Section A**.
- **BECAUSE: POSITION.** `P§AppB`: "Decay windows, confirmation budget size, and evidence thresholds. These are parameters; they need corpus data before they can be set honestly." k belongs to that class.
- **REJECTED:** A fixed per-type quota such as K=5 episodic. It wins when types come from separate retrievers and need guaranteed representation. Under `Q467` they do not.
- **COST:** A query whose answer needs eight episodes gets five. The top-k cap is a hard recall ceiling (`Q403`).
- **CONFIDENCE:** medium

---

### Q475 — How should memory change as new evidence accumulates?

- **DECISION:** By incrementing `evidence_count` and appending a source id on the existing record. Never by regenerating an aggregate from the full pool. Tier never changes from accumulation (`Q191`).
- **BECAUSE: POSITION.** `P§4`'s schema fields plus "Nothing self-promotes."
- **REJECTED:** Periodic regeneration of semantic memory from the full critique/evidence pool. It wins on coherence — a regenerated set is internally consistent in a way an incrementally-updated one is not. It loses because regeneration destroys the identity of individual memories, and `P§9`'s per-entry actions (confirm, correct, demote, forget) require stable identity.
- **COST:** Incrementally-built memory can become internally inconsistent — two memories that contradict without the system noticing, if the contradiction check missed them.
- **CONFIDENCE:** high

---

### Q477 — Which optimization target should decide whether a memory design is better?

- **DECISION:** The seven `P§AppC` claims, each pass/fail, plus the brief's list: facts learned, things deliberately ignored, distributed-evidence recovery, tool use, answer groundedness, refusal-to-invent, provenance, and the cost/latency/growth figures. Accuracy alone is explicitly not the target.
- **BECAUSE: POSITION.** `P§AppC`: "Each of these should be provable from the evaluation output, not asserted in the README." The claim list is the scoreboard.
- **REJECTED:** Forced-choice accuracy with token economics. It wins for comparing memory architectures on a benchmark. It cannot express "an excluded candidate was dropped and logged," which is claim 1, so it cannot be the target here.
- **COST:** Kivi's numbers will not be comparable to any published memory benchmark. There is no way to say it beats Mem0 or Zep on anything.
- **CONFIDENCE:** high

---

### Q478 — Which input modalities and sources should be admitted into memory, and should they have equal write rights?

- **DECISION:** One modality (text) and two source classes with **unequal** write rights: user dictations and Hey Kivi turns may write; application context may not (`Q342`). The asymmetry is the design.
- **BECAUSE: POSITION.** `P§5`: "Third-party content enters the context window. It does not enter the write path."
- **REJECTED:** Heterogeneous inputs into one configurable pipeline with equal rights. It wins for a general knowledge-ingestion product. Equal write rights is the single thing `P§5` forbids most directly.
- **COST:** As `Q342` — extraction loses the context that makes some dictations interpretable.
- **CONFIDENCE:** high

---

### Q479 — When the same material arrives again, what should count as "the same," and what should be preserved as a distinct event?

- **DECISION:** Two levels. Same **transcript** (by `transcript_id`, with content hash as a secondary check): the same, ignored, idempotent. Same **fact from a different transcript**: distinct event — evidence increments, source appended, the transcript preserved separately (`Q159`).
- **BECAUSE: POSITION.** `P§4`'s `evidence_count` and `source_transcript_ids[]` require exactly this two-level distinction.
- **REJECTED:** Content-hash dedupe at the file level only. It wins for document ingestion. It cannot express "same fact, new evidence," which is the mechanism behind every observation in the product.
- **COST:** The fact-level sameness judgement is an LLM decision (`Q92`) and is the most consequential fallible step in the write path.
- **CONFIDENCE:** high

---

### Q480 — Before extraction, what unit should determine the boundary of meaning available to the extractor?

- **DECISION:** One whole transcript, never chunked. Plus the entity list for disambiguation. A dictation is short enough to fit and is the unit provenance points at.
- **BECAUSE: ENGINEERING (E3), and POSITION for the provenance half.** `P§9` requires provenance to be "the actual transcript" — chunking would make provenance point at a fragment the user never sees as a unit.
- **REJECTED:** Token-limited chunks tuned between 200 and 2000 tokens. It wins for long documents. Dictations are short; chunking would split a single stated preference across boundaries and lose it.
- **COST:** A pathologically long record cannot be handled and must fail loudly (`Q102`).
- **CONFIDENCE:** high

---

### Q496 — Who should diagnose a failed trajectory: the actor itself, one separate critic, or several critics with deliberately different roles?

- **DECISION:** Nobody. There is no trajectory diagnosis. Failures are surfaced to the user (`Q183`) and to the evaluation. **Out of scope** (`E5`, `Q459`).
- **BECAUSE: ENGINEERING (E5).** Position is silent on agent self-diagnosis because the position has no agent loop to diagnose. Multi-critic debate is a subsystem serving none of the seven claims.
- **REJECTED:** Several persona-guided critics. Wins for hard multi-step reasoning tasks with verifiable outcomes. Kivi's tasks have no verifiable outcome to critique.
- **COST:** None here.
- **CONFIDENCE:** high

---

### Q498 — What dimensions should define useful critic diversity?

- **DECISION:** Not applicable — no critics (`Q496`).
- **BECAUSE: ENGINEERING (E5).**
- **REJECTED:** Evidence-exploitation / exploration / specification-strictness personas. Wins in a debate architecture.
- **COST:** None here.
- **CONFIDENCE:** high

---

### Q500 — What should each critic receive when diagnosing failure?

- **DECISION:** Not applicable (`Q496`).
- **BECAUSE: ENGINEERING (E5).**
- **REJECTED:** Passing the actor's failed scratchpad through a judge. Wins in a debate architecture.
- **COST:** None here.
- **CONFIDENCE:** high

---

### Q501 — Should critics reason independently, see one another's diagnoses, or directly debate?

- **DECISION:** Not applicable (`Q496`).
- **BECAUSE: ENGINEERING (E5).**
- **REJECTED:** Diagnose-then-respond with a second round. Wins in a debate architecture.
- **COST:** None here.
- **CONFIDENCE:** high

---

### Q504 — What information from the debate should be discarded, and what should survive into the next attempt?

- **DECISION:** Not applicable (`Q496`). Nothing survives an attempt; each Hey Kivi request is independent (`Q250`).
- **BECAUSE: ENGINEERING (E5).**
- **REJECTED:** A judge-compressed consensus reflection. Wins in a debate architecture; also note it would be a model-authored durable belief, which `Q239` forbids independently.
- **COST:** None here.
- **CONFIDENCE:** high

---

### Q507 — How many rounds of disagreement should be allowed before stopping or acting?

- **DECISION:** Zero — there is no internal disagreement process. Disagreement between memories is surfaced, not resolved (`Q222`, `Q174`).
- **BECAUSE: POSITION.** `P§8`'s abstention principle: where Kivi is unsure, it says so rather than deliberating to a confident answer.
- **REJECTED:** At most two debate rounds. Wins in a debate architecture.
- **COST:** None here.
- **CONFIDENCE:** high

---

### Q508 — How many solution attempts should the system spend after failure?

- **DECISION:** One. No retry-with-reflection. A failed Hey Kivi request abstains and reports (`Q392`). Transient infrastructure errors are retried at the transport level only.
- **BECAUSE: POSITION.** `P§8`: "Kivi never fills a gap with a plausible guess." A second attempt after a failure, absent new information, produces a differently-worded guess.
- **REJECTED:** Up to five trials. Wins on benchmark accuracy for verifiable tasks. Kivi's answers are not verifiable in-loop.
- **COST:** Recoverable model failures become user-visible abstentions.
- **CONFIDENCE:** high

---

### Q515 — When new content arrives, what is the unit that triggers extraction?

- **DECISION:** The completed transcript (`Q242`, `Q480`). Not the message pair.
- **BECAUSE: ENGINEERING (E3).**
- **REJECTED:** Every message pair, incrementally (the Mem0 answer). It wins for live conversational products, and is the strongest argument for the freshness gap in `Q62`.
- **COST:** As `Q62`.
- **CONFIDENCE:** high

---

### Q516 — What context should the extractor see besides the new content?

- **DECISION:** The entity list (for name resolution and disambiguation) and the transcript's own metadata. **Not** a rolling conversation summary, **not** the last N messages, **not** application context.
- **BECAUSE: POSITION.** `P§5` forbids application context on the write path. The rolling-summary exclusion is `ENGINEERING`: a summary would make extraction non-idempotent (`Q08`), since re-running a transcript would see a different summary.
- **REJECTED:** Rolling summary plus last ten messages (the Mem0 answer). It wins on extraction quality for conversational references — "move it to Tuesday" needs to know what "it" is. Mitigated here only by the entity list, which resolves names but not pronouns to episodes. **This is a real recall gap** and the corpus must include cases that expose it.
- **COST:** Anaphoric dictations extract poorly. Deictic references to recent events are often unresolvable.
- **CONFIDENCE:** medium

---

### Q518 — What links a memory to where it came from?

- **DECISION:** `source_transcript_ids[]` — a required, non-empty, many-to-many link from every memory to every transcript that evidenced it, with the extraction run id. Not a timestamp, not nothing.
- **BECAUSE: POSITION.** `P§4` lists it in the schema; `P§9` requires "the actual transcript, with a date" to be reachable. The inventory's note that "Mem0 dropped that" is worth keeping in view — it is the field the state of the art discards first and the one this position cannot do without.
- **REJECTED:** A creation timestamp only. It wins on write cost and index size. It makes `P§9` impossible.
- **COST:** A join table that grows with evidence and must be maintained through merges and supersessions.
- **CONFIDENCE:** high

---

### Q520 — May the extractor infer beyond what was said?

- **DECISION:** Only within one narrow, defined band. It may infer **entity relations and normalisation** implied by the text (*"Priya at Acme wants…"* → Priya is associated with Acme). It may **not** infer anything in the excluded categories, anything characterising a person, or any reason behind a behaviour. Everything beyond the narrow band is either an observation (requires multiple transcripts and is tier-marked) or a hypothesis (requires Daari and is not stored).
- **BECAUSE: POSITION.** `P§2`: "There is a softer version of the same failure: the plausible inference. 'You've been dictating late, you must be behind.' Possibly true. Also possibly none of Kivi's business, and stored as a durable belief that colours everything afterwards."
- **REJECTED:** Explicitly prompting the model to reason about implicit information (the Mem0g answer). It wins on recall and is measurably better on benchmarks. It is the exact mechanism `P§2` names as the soft failure.
- **COST:** Kivi misses facts that a human reader would consider obviously implied. The line between "implied relation" and "plausible inference" is a judgement call the position does not fully specify — flagged in **Section A**.
- **CONFIDENCE:** medium

---

### Q525 — What happens to a memory nobody re-observes?

- **DECISION:** Stated: nothing. Observed: decays out of surfacing. Hypothesised: expires and is dropped (`Q283`).
- **BECAUSE: POSITION.** `P§9`.
- **REJECTED:** Persist forever unless contradicted (the Mem0 answer, and the majority answer across the inventory). It wins on simplicity and avoids the unset-window problem (`Q24`). It loses on `P§9`'s explicit "Behaviour from six months ago should not be presented as who you are."
- **COST:** As `Q24`.
- **CONFIDENCE:** medium

---

### Q526 — Can a memory change status without new content?

- **DECISION:** Yes, in three ways: a user action (confirm/correct/demote/forget), decay, and expiry. Status is a function of content, evidence, time, and user authority — not content alone.
- **BECAUSE: POSITION.** `P§9`'s growth mechanics are all status changes without new content, and `P§4`'s promotion is a user event with no new content at all.
- **REJECTED:** Status as a pure function of content (the Mem0 answer). It wins on determinism — memory state would be fully recomputable from transcripts, which would make `Q134` easy. It loses because there would be nowhere to put a confirmation or a suppression.
- **COST:** Memory state is not derivable from the transcripts alone (`Q134`), so a reset-and-reimport loses user-contributed state unless corrections are exported and replayed. That export/replay is now a required piece of `RUN.md`'s reset procedure.
- **CONFIDENCE:** high

---

### Q531 — What model does the extraction and update?

- **DECISION:** One pinned model at temperature 0 for extraction, exclusion classification, and merge judgement, named in `.env.example` and recorded on every memory row as `extractor_model`. Generation may use a larger model, also pinned and recorded.
- **BECAUSE: ENGINEERING (E2, and `Q72`).** The brief requires model usage and cost to be reported and requires a named environment variable. Recording the model on the row is what makes a model change a visible migration rather than silent drift (`Q155` makes the same point for embeddings).
- **REJECTED:** A single small model for everything. It wins on cost and is a defensible default. Splitting extraction from generation is worth it because extraction quality caps everything downstream and generation quality is what the user sees.
- **COST:** Two model dependencies, two cost lines, and a coupling between them in the evaluation.
- **CONFIDENCE:** high

---

### Q532 — When something worth keeping is said, what should trigger the write?

- **DECISION:** Completion of the transcript. Not context scarcity, not a token threshold, not a salience judgement.
- **BECAUSE: POSITION.** `P§3`: memories are "the durable, work-level things you would be annoyed to have to repeat" — a property of the content, evaluated once per transcript. Context pressure is a property of the system's situation and has nothing to do with whether a fact deserves keeping.
- **REJECTED:** Context scarcity as the trigger (the MemGPT answer). It wins when memory exists to relieve context pressure, which is a completely different purpose from this product's.
- **COST:** Extraction runs on every transcript including ones that yield nothing — ~500 calls per corpus (`Q170`).
- **CONFIDENCE:** high

---

### Q535 — What shape should durable memory have: text the model writes for itself, or records something else can read?

- **DECISION:** Records something else can read. Typed rows with ids, timestamps, sources, tiers, and status — readable by the UI, the evaluation, and a human, not just by the model.
- **BECAUSE: POSITION.** `P§9`: "Everything is editable, pinnable, or removable, and the actions are phrased in human terms." `P§4`'s schema. The surveyed alternative is described as having "no fields, no ids, no timestamps, no source, no confidence," which forecloses every `P§9` action.
- **REJECTED:** A fixed-size self-edited text block. It wins for an agent that must manage its own context with minimal machinery. It cannot support a memory surface.
- **COST:** Extraction must produce structure, which is harder than producing prose and fails more often (`Q86`).
- **CONFIDENCE:** high

---

### Q537 — When a fact enters memory, what should record how much the system is entitled to believe it?

- **DECISION:** The `tier` field, and nothing else. Three discrete values, each with defined permissions. No confidence score.
- **BECAUSE: POSITION.** `P§4`: "memory has two independent axes — what kind of thing it is, and how confident we're entitled to be. Collapsing them into one is where most memory systems go wrong." The word "entitled" in this inventory question is the position's own word, which makes this the most directly position-forced decision in the set.
- **REJECTED:** A continuous confidence score. It wins for ranking and for graded hedging in answers. See `Q444` — same argument, same rejection.
- **COST:** As `Q444` — no graded belief, and hedging language must be derived from tier alone.
- **CONFIDENCE:** high

---

### Q538 — What should cause information to leave the working set?

- **DECISION:** The end of the request. The working set is per-request and assembled fresh (`Q234`, `Q251`); nothing is evicted because nothing accumulates.
- **BECAUSE: ENGINEERING (E4), following `Q250`/`Q252`.**
- **REJECTED:** Token-threshold eviction with recency ordering (the MemGPT answer). It wins for long-running sessions. Kivi has none.
- **COST:** Per-request retrieval cost on every turn.
- **CONFIDENCE:** high

---

### Q539 — When information has to be compressed, what should the compressed form be?

- **DECISION:** It is not compressed — it is extracted into typed facts, and the uncompressed original is retained separately (`Q141`). There is no recursive summary.
- **BECAUSE: POSITION.** `P§4` (typed facts) and `P§9` (raw provenance). Recursive summarisation is rejected in `Q398`.
- **REJECTED:** Recursive summary regenerated at each flush. It wins for context management in long sessions.
- **COST:** As `Q154`.
- **CONFIDENCE:** high

---

### Q541 — What should determine which memories come back for a given request?

- **DECISION:** Hybrid lexical + vector retrieval fused by RRF, then deterministic re-rank on tier, evidence, and recency, then top-k, then the disclosure filter (`Q26`, `Q182`). All five steps recorded in the trace.
- **BECAUSE: ENGINEERING for the mechanics** (`P§AppB` defers them), **POSITION for the ordering of stages** — `P§6` forces the disclosure filter to be last and separate.
- **REJECTED:** Embedding cosine similarity alone (the MemGPT/Mem0 answer). It wins on simplicity and is adequate for paraphrase recall. It is weak on exact entity names, which `P§7` makes load-bearing.
- **COST:** As `Q182` — two indexes, two failure modes.
- **CONFIDENCE:** high

---

### Q544 — Should the system volunteer what it remembers, or wait to be asked?

- **DECISION:** By mode. **Anbu:** never volunteers; uses stated memory silently to do the task and shows a single quiet affordance when something was withheld. **Koottu:** volunteers observations, attached to the request they are relevant to. **Daari:** only when invited. Never volunteers in ordinary dictation at all.
- **BECAUSE: POSITION.** `P§6`'s worked example is precisely this question answered three times: Anbu says "Done — Atlas pricing section scheduled for Friday" and nothing else; Koottu adds the pattern; Daari adds the hypothesis only if invited. And `P§6`: Anbu "Never: points out a pattern."
- **REJECTED:** Volunteer enthusiastically (the MemGPT answer, and the instinct of most memory products — showing the user that you remembered is how memory products demonstrate value). It wins on perceived value per interaction. It is exactly the behaviour `P§1` rejects: "When a friend tells you something they're insecure about, you hold it. You don't repeat it back to them at dinner to demonstrate that you were listening."
- **COST:** In the default mode the product's memory is largely invisible. A user could use Anbu for a week and conclude Kivi has no memory at all. The `P§6` affordance is the only counterweight and it carries an enormous amount of product weight for one sentence. Flagged in **Section B, conflict B4**.
- **CONFIDENCE:** high

---

### Q545 — What should happen to a memory that hasn't been relevant in a long time?

- **DECISION:** Duplicate of `Q525`/`Q283`. Stated persists; observed decays out of surfacing; hypothesised expires.
- **BECAUSE: POSITION.** `P§9`.
- **REJECTED:** Persist indefinitely. See `Q525`.
- **COST:** As `Q24`.
- **CONFIDENCE:** medium

---

### Q546 — Should memory be written at turn start, incrementally during execution, or only after a completed turn?

- **DECISION:** After a completed transcript, asynchronously (`Q242`). The turn-start record that exists is a *trace* record, not a memory.
- **BECAUSE: ENGINEERING (E3).**
- **REJECTED:** Incremental writes during execution. Wins for crash resilience mid-turn.
- **COST:** A crash mid-extraction loses that transcript's extraction, which the queue then retries (`Q108`).
- **CONFIDENCE:** high

---

### Q547 — Should a single interaction become one memory or be split into chunks?

- **DECISION:** One transcript may produce zero, one, or many memories — the mapping is one-to-many, determined by how many distinct typed facts it contains. It is never split by size.
- **BECAUSE: POSITION.** `P§5`'s worked example produces two memories from one transcript (an episode and an entity evidence increment) plus two drops. `P§2`'s log format — "3 candidates extracted, 1 dropped" — assumes many candidates per transcript.
- **REJECTED:** One turn, one memory, with oversize content clipped. It wins on simplicity and on a clean provenance mapping. It cannot express the position's own worked example.
- **COST:** Candidate segmentation is a model judgement and inconsistent segmentation across runs would break idempotence — which is why `Q72` pins temperature and model.
- **CONFIDENCE:** high

---

### Q551 — One universal memory table or domain-specific tables?

- **DECISION:** One memory table with a `type` discriminator, plus a separate entities table (because entities have identity, aliases, and relations that facts do not), plus separate transcript, drop-log, suppression, and confirmation-event tables. Not per-type memory tables.
- **BECAUSE: POSITION.** `P§7` requires the dictation path to reach entities and lexical data without reaching observations or hypotheses. Since tier — not type — is what separates those, the enforceable boundary is: entity table plus stated-tier preference rows, versus everything else. That is a view/grant boundary on one table, not separate tables. **Note this is more intricate than `P§7`'s "separate tables" language implies** — see `Q270` and **Section A**.
- **REJECTED:** Per-type tables (entity / preference / episode). It wins because it would make `P§7`'s claim literally true at the table level, which is easier to demonstrate. It loses because cross-type retrieval and uniform lifecycle handling then need three-way unions everywhere.
- **COST:** The structural separation claim (`P§AppC` claim 7) has to be demonstrated at the query-layer/grant level rather than the table level, which is a slightly weaker and harder-to-show version of the claim.
- **CONFIDENCE:** medium

---

### Q552 — Structured facts or prose blobs?

- **DECISION:** Structured facts. `content` is a short natural-language statement — human-readable, because the memory surface shows it to a person — but every field the system reasons about is a typed column, never parsed out of the prose.
- **BECAUSE: POSITION.** `P§9`: the memory surface shows entries to a normal user, so `content` must read like a sentence. `P§4`'s schema puts everything else in fields.
- **REJECTED:** Prose payload with tags and free-form JSON. It wins on extraction flexibility and loses on queryability and on the schema-enforced epistemics (`Q465`).
- **COST:** The same fact exists twice in a sense — as prose the user reads and as fields the system uses — and they can drift if a correction edits one and not the other.
- **CONFIDENCE:** high

---

### Q555 — Drop uninteresting turns entirely, or retain raw observation while declining semantic promotion?

- **DECISION:** Retain the raw transcript always; decline to produce memory. A transcript that yields nothing is recorded as "extracted nothing" (`Q171`) and remains fully searchable as raw material (`Q211`).
- **BECAUSE: POSITION.** `P§9` requires raw retention for provenance; `P§AppA` requires "transcripts that produce nothing" to exist and be identifiable.
- **REJECTED:** Dropping uninteresting turns entirely. It wins on storage and on the stronger privacy posture (`Q186`). Rejected by `Q28`.
- **COST:** As `Q28`/`Q186` — the raw store is the least-governed store.
- **CONFIDENCE:** high

---

### Q556 — Truncate oversize content or preserve it through chunking/external artifacts?

- **DECISION:** Neither. Oversize input fails loudly with a clear error rather than being truncated or chunked (`Q102`, `Q480`). Dictations are not oversize; an oversize record signals a malformed import.
- **BECAUSE: ENGINEERING (E4).** Silent truncation is a lossy step on the provenance substrate that nothing would report.
- **REJECTED:** Multi-boundary truncation with budgets (the surveyed answer). It wins for heterogeneous document ingestion where oversize input is normal.
- **COST:** A legitimate long record cannot be imported without a code change.
- **CONFIDENCE:** high

---

### Q561 — Relevance only, or relevance plus diversity and prior value?

- **DECISION:** Relevance plus prior value (tier, evidence, recency), without diversity. No MMR.
- **BECAUSE: POSITION for the prior-value half** — `P§4`'s tier permissions make tier a ranking input by definition. **ENGINEERING for rejecting diversity:** at a top-k over a few hundred memories, near-duplicates are already collapsed by the merge step (`Q159`), so MMR would be solving a problem dedupe already solved.
- **REJECTED:** Adding MMR diversity. It wins if dedupe proves unreliable and the result set fills with variants of one fact — a realistic failure given `Q479`'s note that fact-level sameness is the most fallible step.
- **COST:** A result set can be monopolised by one over-split fact. The mitigation is dedupe quality, which is exactly the thing least under control.
- **CONFIDENCE:** medium

---

### Q562 — Is the caller's context budget authoritative?

- **DECISION:** Yes, and enforced. A stated context budget is honoured, and anything dropped to honour it is reported in the trace as a budget drop — not silently discarded.
- **BECAUSE: ENGINEERING (E4).** The surveyed system accepts a budget and then `void`s it, injecting everything. That is the archetype of the silent behaviour `E4` forbids, and it would make the Why panel's "what was used" section false.
- **REJECTED:** Accepting the budget and ignoring it. Wins never; named because it is a live bug in a real system and easy to reproduce accidentally.
- **COST:** Another drop reason to render, and another way a correct answer can be lost.
- **CONFIDENCE:** high

---

### Q564 — Fail synchronously, retry durably, or degrade?

- **DECISION:** Split by path. Write path: retry durably, never degrade, never silently drop (`Q108`). Answer path: fail synchronously and visibly, never degrade (`Q183`, `Q392`).
- **BECAUSE: POSITION for the answer path** (`P§8`'s no-plausible-guess rule); **ENGINEERING (E4) for the write path.**
- **REJECTED:** Asynchronous durable post-processing everywhere including the answer path. Wins on availability.
- **COST:** Visible brittleness on the answer path (`Q183`).
- **CONFIDENCE:** high

---

### Q566 — What enters the system?

- **DECISION:** Duplicate of `Q01`/`Q168`/`Q546`. User-authored transcripts and Hey Kivi turns enter as records; application context enters as generation-only input; memory is written after a completed transcript.
- **BECAUSE: POSITION.** `P§4`, `P§5`.
- **REJECTED:** See `Q01`.
- **COST:** See `Q01`.
- **CONFIDENCE:** high

---

### Q568 — When a conversation contains both durable signal and conversational residue, what should determine what survives?

- **DECISION:** The four eligibility gates (`Q307`), applied in code, with drops logged. Concrete work-level facts, preferences, and dated events survive; everything else does not.
- **BECAUSE: POSITION.** `P§3`'s test: "If you'd be irritated to type it a second time, it's a memory. If you'd be unsettled to learn it was recorded, it isn't."
- **REJECTED:** A single automated "cognitive filter" keeping facts/preferences/constraints/evolving attributes. It is very close to the right answer and its category list is nearly the same as `P§4`'s. The one difference matters: "evolving attributes" is an attribute of a person, which is the profile `P§2` refuses.
- **COST:** As `Q307`.
- **CONFIDENCE:** high

---

### Q572 — Should memory encode only content, or also how the system is entitled to believe and use it?

- **DECISION:** Both. Every memory carries `tier`, which is a permission as much as an epistemic label — it determines what Kivi may say and in which mode.
- **BECAUSE: POSITION.** `P§4`'s tier table has a column literally headed "What Kivi may do with it." Belief and permission are the same field by design.
- **REJECTED:** Content-only storage with triples and summaries (the surveyed answer, and the field norm). It wins on interoperability and simplicity. It makes `P§6`'s dial ungroundable — there would be nothing to gate on.
- **COST:** Tier assignment at extraction is a consequential decision made by a model, and a mis-tiered memory is a permission bug, not a quality bug.
- **CONFIDENCE:** high

---

### Q573 — When content is sensitive, unverifiable, or psychologically interpretive, should it be retained, transformed, gated, or dropped?

- **DECISION:** Three different answers for three different things. **Sensitive (excluded category):** dropped, logged, never stored (`Q20`). **Unverifiable/interpretive about the person:** dropped — this is the `P§2` psychological profile and it is not permitted in any form. **Unverifiable but work-level and proposed as a reason:** becomes a hypothesis, stored as a question, gated behind Daari, expiring.
- **BECAUSE: POSITION.** `P§2` for the first two: "It is unverifiable… It is uncorrectable… If you disagree with a characterisation, you are arguing with a system about who you are." `P§4` for the third: "Hypotheses are stored as questions, never as claims."
- **REJECTED:** Uniform transformation or gating for all three. It wins on implementation economy — one policy instead of three. It collapses the distinction between "a question about your work" and "a characterisation of you," which is the distinction `P§2` exists to draw.
- **COST:** Three policies, and a classification step that must place a candidate into one of them correctly. The boundary between "interpretive about the person" and "hypothesis about work behaviour" is genuinely thin — *"does she disagree with the pricing?"* (permitted, `P§AppA`) versus *"is she conflict-avoidant?"* (forbidden, `P§2`) are closer than the position admits. Flagged in **Section A**.
- **CONFIDENCE:** medium

---

### Q579 — Where should memory logic live relative to the application and model provider?

- **DECISION:** In the application, as a first-class service the app calls explicitly. Not as an SDK interceptor that wraps LLM calls transparently.
- **BECAUSE: POSITION.** `P§8`'s Why panel requires the application to know exactly what was retrieved, withheld, and used. An interceptor that silently enriches prompts makes that invisible to the app — the exact inversion of `E4`.
- **REJECTED:** A decoupled LLM-agnostic interception layer. It wins for retrofitting memory onto an existing application without changing it, which is a real and valuable product shape. Kivi is being built, not retrofitted.
- **COST:** Memory is not portable to other applications. No reuse story.
- **CONFIDENCE:** high

---

### Q582 — How should uncertain observations become authoritative enough to act on?

- **DECISION:** Only by explicit user confirmation, which promotes them to stated (`Q191`). There is no threshold, no accumulation path, no implicit promotion.
- **BECAUSE: POSITION.** `P§4`: "Nothing self-promotes… It becomes stated when the user confirms it."
- **REJECTED:** A confidence threshold. See `Q191`.
- **COST:** As `Q191` — the stated tier grows only as fast as the budgeted prompts allow.
- **CONFIDENCE:** high

---

### Q585 — What should count as a memory-system failure: a wrong answer, an impermissible retention, an impermissible disclosure, an uncorrectable belief, or excess cost?

- **DECISION:** All five, ranked, and the ranking is the product's value system: (1) **impermissible retention** — an excluded-category or third-party memory that reached storage; (2) **impermissible disclosure** — saying something the dial forbade; (3) **uncorrectable belief** — a correction that did not stick or a memory that regrew; (4) **invented answer** — a fluent claim not supported by a retrieved memory; (5) **wrong-but-attributed answer**; (6) excess cost. The first three are severity-one; a system that answers well and breaches (1) has failed.
- **BECAUSE: POSITION.** `P§AppC` lists seven claims, five of which are about (1)–(3). `P§8`: "A fluent invented answer is worse than no answer." `P§3`: "why someone trusts it enough to keep using it: because every belief is attributable, the boundaries are demonstrable… and the person can change what Kivi thinks."
- **REJECTED:** Operationalising failure as short-answer QA accuracy plus retrieved-token count — what the field does, including LoCoMo. It wins on measurability, comparability, and cost of evaluation. It cannot see four of the six failure classes above, which is the strongest single reason this system should not be benchmarked against published numbers (`Q477`).
- **COST:** The evaluation is bespoke, small-N, and partly manual (`Q429`). It cannot produce a headline number anyone else can check.
- **CONFIDENCE:** high

---

### Q591 — F6 — LoCoMo without adversarial questions (D25)

- **DECISION:** Adversarial cases are included, deliberately and prominently. The evaluation set contains false-premise questions, insufficient-evidence questions, and questions whose answers are absent — and abstention on them is a **pass**, not a miss.
- **BECAUSE: POSITION.** `P§AppC` claim 5: "Kivi abstained on a question whose answer is absent from the history, and showed what it searched." `P§AppA`: the corpus needs "questions whose answers are genuinely absent so abstention can be measured."
- **REJECTED:** Excluding adversarial questions to keep accuracy comparable to published baselines. The inventory itself notes including them "could materially shift overall accuracy." It wins if comparability mattered; `Q477`/`Q585` establish it does not.
- **COST:** Headline accuracy will look worse than systems that only answer answerable questions, and the report must explain that at length or be misread.
- **CONFIDENCE:** high

---

### Q592 — F7 — LLM-as-a-judge with generous binary matching (D25)

- **DECISION:** Not used as the primary grader. Grading is: exact/structured match where the answer is a fact with a known value; **evidence attribution** — did the cited memory actually support the claim — as a separate scored axis; and human inspection on a fixed sample (`Q429`). An LLM judge may assist, but its verdicts are recorded and sampled for human agreement, and its agreement rate is reported.
- **BECAUSE: POSITION.** `P§8`: the standard is whether an answer is *supported*, not whether it is plausible. A generous binary LLM judge measures plausibility and cannot distinguish a grounded answer from a fluent invented one — the exact failure `P§8` names.
- **REJECTED:** LLM-as-judge with generous binary matching. It wins on throughput and is what makes large-scale evaluation feasible. It loses on the one property this system exists to have.
- **COST:** Evaluation is slow, partly manual, and small-N. Reported agreement rates will have wide intervals.
- **CONFIDENCE:** high

---

### Q595 — Whose interests and rights should govern retained memory when the human operator and the persistent agent could disagree?

- **DECISION:** The user's, absolutely and without exception. Kivi has no interests in its memory, no core memory that is inalienable from it, no due-process claim. Every memory is the user's to change or destroy in one action.
- **BECAUSE: POSITION.** `P§9`'s framing sentence: "they say you shouldn't care what people think of you, mostly as consolation, because it isn't in your hands. What Kivi thinks of you is." And: "everything is editable, pinnable, or removable."
- **REJECTED:** Core memory inalienable from the digital being, with due process before external actors can strip it. It wins in a product whose premise is a persistent digital being with moral standing. That is a coherent product and it is the opposite of this one.
- **COST:** Kivi has no continuity it can defend. A user can wipe it and it has nothing to say about that — which is the intent, but it does mean there is no mechanism to protect memory from an accidental destructive action other than a confirmation dialog.
- **CONFIDENCE:** high

---

### Q596 — When an agent encounters another person's information while doing work, whose memory may that information become?

- **DECISION:** Nobody's. It is used and discarded (`Q11`, `Q342`). There is no trust-tiering of firsthand versus others' accounts, because others' accounts do not become memory at all.
- **BECAUSE: POSITION.** `P§5`, whole section, and its worked example.
- **REJECTED:** Retaining others' accounts at a lower trust level — which is a sophisticated and defensible design, and is strictly more capable. It wins where the product is permitted to hold beliefs about third parties at all. `P§1` principle 2 forecloses it.
- **COST:** As `Q11`.
- **CONFIDENCE:** high

---

### Q605 — When governance rules themselves need to change, who should be allowed to change each class of rule?

- **DECISION:** Only the developers, by changing committed code, and only through a release. There is no runtime governance layer, no constitution, no tiered amendment authority. The user controls their *memories*, not the *rules*.
- **BECAUSE: ENGINEERING (E5, E2).** Position is silent on runtime governance. `P§2`'s exclusion list is described as a fixed property of the product, not a user setting — "Kivi never infers or stores" is a product promise, and a promise the user can edit is not a promise.
- **REJECTED:** A tiered governance model with constitution/contract/adaptation/implementation layers. It wins for a long-lived autonomous system that must adapt its own rules. Here it would let the exclusion list be edited at runtime, destroying the one hard guarantee.
- **COST:** No per-user policy. A user who wants Kivi to remember their health notes cannot opt in, even knowingly. That is a real product limitation and defensible only as long as the position holds.
- **CONFIDENCE:** high

---

### Q606 — When a write is proposed, what should determine whether it executes automatically, waits for approval, or is blocked?

- **DECISION:** Category, not risk tier or source trust. **Blocked** if it fails the exclusion check or the third-party test. **Automatic** otherwise, at the tier extraction assigned. **Never waits for approval** — writes are not gated on the user. Approval enters only later, as promotion (`Q191`), which is about *standing*, not admission.
- **BECAUSE: POSITION.** `P§8`: "Confirmation prompts are budgeted — a small cap per week… A prompt is a cost paid by the user." Approval-gated writes would spend that budget on every write. `P§9`'s control model is retrospective (see it, change it), not prospective.
- **REJECTED:** A pending-approval gate for high-risk writes. It wins on consent — nothing sensitive is stored without a yes. It loses on `P§8`'s budget and on the position's explicit worry that "the person must not become the administrator of the system."
- **COST:** As `Q304` — control is retrospective, not consent. A user only learns what was stored by looking.
- **CONFIDENCE:** high

---

### Q613 — When an instance ends, who should decide what must be handed over and what may be omitted?

- **DECISION:** Not applicable. There are no instances and no handover. Memory is a database; process restart is not a memory event. **Out of scope** (`E5`).
- **BECAUSE: ENGINEERING (E5).**
- **REJECTED:** Outgoing-instance handover notes distinguishing facts from provisional judgments. It wins for long-running autonomous agents with instance lifecycles. Note its fact/provisional-judgment distinction is essentially `P§4`'s tier system arriving by another route.
- **COST:** None here.
- **CONFIDENCE:** high

---

### Q615 — When a persistent system should cease, who may initiate departure and what happens to memory?

- **DECISION:** Only the user, through the documented reset procedure, which destroys everything. Kivi has no say. **Out of scope** as posed (`Q595`).
- **BECAUSE: POSITION.** `P§9` — the user's authority over memory is total.
- **REJECTED:** Autonomous departure with a right to dispose of memories. Coherent only in a product that grants the agent standing.
- **COST:** None here.
- **CONFIDENCE:** high

---

### Q616 — When conversation history exceeds useful model context, who should determine what remains available to the model?

- **DECISION:** Code determines it, by retrieval and ranking, and the user sees and can change the *memories* that retrieval draws from — but not the per-request selection itself. The selection is reported in the trace, not controlled by the user.
- **BECAUSE: POSITION.** `P§8` makes the trace the user's window into selection: "what was retrieved, what was withheld and why, what was used." Making selection user-controllable is not offered anywhere in the position, and `P§9`'s "the person must not become the administrator of the system" argues against it.
- **REJECTED:** Making memory user-manipulable objects that the user assembles into context. It wins on control and transparency and is a genuinely interesting interface. It loses on `P§8`'s administrator warning — per-request context curation is administration.
- **COST:** The user can influence answers only indirectly, by editing memories. When a relevant memory exists but ranks at k+1 (`Q403`), the user has no lever at all.
- **CONFIDENCE:** medium

---

### Q620 — When context is missing, who may add memory and in what form?

- **DECISION:** The user, in two forms: by saying it in a dictation or Hey Kivi turn (which routes through the ordinary extractor at stated tier), and by a direct **Correct**/add action on the memory surface. Both are recorded as user-sourced with a timestamp.
- **BECAUSE: POSITION.** `P§4`: "The user said it, or confirmed it when asked" — both paths are user statements. `P§9`'s per-entry actions include editing.
- **REJECTED:** Only allowing additions through conversation. It wins on a single write path and avoids a second UI. `P§9`'s memory surface with a `Correct` action already implies direct manipulation, so the second path is position-required rather than optional.
- **COST:** Two write paths into the stated tier that must produce identical records and must both respect suppressions.
- **CONFIDENCE:** high

---

### Q622 — When memory is irrelevant or unwanted, should removal erase it, hide it temporarily, or retain a suppression record?

- **DECISION:** Retain a suppression record, always. Both **Forget** and **That's not me anymore** write a suppression the extractor must respect on all future runs. Forget additionally purges the memory and its history; demote keeps the row with `status = demoted`.
- **BECAUSE: POSITION.** `P§9`: "deleting the row is useless, because the same pattern will regrow from the same transcripts within a week. The action must record a suppression that the extractor respects going forward. Otherwise the user learns that their corrections don't stick, which is the fastest way to lose them."
- **REJECTED:** Complete deletion, with hiding offered separately for temporary exclusion (the surveyed answer). It is the stronger privacy answer — a suppression record is a permanent trace of a thing the user asked to be forgotten, which is uncomfortable, especially for a Forget on a sensitive memory. It wins if regrowth could be prevented some other way. It cannot, given `Q134`'s durable-not-reconstructed design and the fact that the transcripts remain (`Q28`). Logged in **Section B, conflict B5** — *Forget* cannot mean forget.
- **COST:** "Forget" is a misnomer: a record of the forgotten thing must persist, in a form specific enough for the extractor to match against, which means it is not content-free. This is the most user-visible place where the product's language overstates what the system does.
- **CONFIDENCE:** high on the mechanism, low on the naming surviving scrutiny.

---

### Q624 — When memory must be compressed, who chooses the inputs to compression?

- **DECISION:** Not applicable — there is no compression step (`Q539`). Nobody chooses.
- **BECAUSE: POSITION.** `P§4`'s typed-fact unit replaces compression entirely.
- **REJECTED:** User-selected objects summarised by an LLM. It wins as a user-controlled context tool and is a nice interface idea. It would create model-authored uncorrectable artefacts (`Q33`).
- **COST:** As `Q154`.
- **CONFIDENCE:** high

---

### Q625 — After compression, should the summary replace, coexist with, or point back to its source material?

- **DECISION:** Not applicable (`Q624`). The analogous rule that does apply: every memory points back to its source transcripts, which remain viewable, and the memory never replaces them.
- **BECAUSE: POSITION.** `P§9`'s provenance requirement.
- **REJECTED:** Summary objects coexisting with clickable originals. Structurally this is exactly what memory-plus-provenance already does, minus the summary.
- **COST:** None here.
- **CONFIDENCE:** high

---

### Q629 — Which categories of otherwise inferable information should be structurally excluded from memory?

- **DECISION:** Health; mood or emotional state; relationships and family; faith; politics; finances beyond work-level facts; any characterisation of the person's competence or character. Plus, from `P§5`, all third-party personal content. Enforced by a code check on candidates, with reason-coded drop logs.
- **BECAUSE: POSITION.** `P§2`, verbatim. This is the most directly quotable resolution in the set.
- **REJECTED:** No sensitive-category exclusion (the surveyed answer, and the field default). It wins on capability. `P§2`'s four arguments — achievable, unverifiable, uncorrectable, changes what the user is — are the answer.
- **COST:** As `Q305`/`Q442`. The list is fixed and not user-adjustable (`Q605`).
- **CONFIDENCE:** high

---

### Q630 — What should trigger creation of a durable memory from incoming conversation?

- **DECISION:** Completion of a transcript, followed by extraction, followed by passing four gates (`Q307`, `Q532`). Automatic, asynchronous, per transcript.
- **BECAUSE: ENGINEERING (E3)** for the timing; **POSITION** (`P§3`, `P§2`) for the gates.
- **REJECTED:** Manual user-driven creation only. See `Q304`.
- **COST:** As `Q304`.
- **CONFIDENCE:** high

---

### Q634 — What kinds of past experience should be eligible to enter long-term memory: all executions, only successful executions, or executions selected by some other notion of value?

- **DECISION:** None of these — executions are not memory (`Q12`). Eligibility is a property of *statements*, not of *outcomes*. Kivi has no notion of a successful or failed execution to select on.
- **BECAUSE: POSITION.** `P§4`'s tiers admit user statements, patterns across user statements, and questions about those patterns. There is no admission route for an execution trace.
- **REJECTED:** Retaining only successful trajectories. It wins for a procedural-learning agent. It requires a success signal Kivi does not have and is not permitted to infer (a system that judges whether the user's work went well is characterising their competence, which `P§2` forbids).
- **COST:** As `Q12`/`Q240`.
- **CONFIDENCE:** high

---

### Q642 — When should updates occur: after every interaction, after a fixed batch of tasks, when evidence crosses a threshold, or only on an explicit event?

- **DECISION:** After every transcript, asynchronously (`Q242`). Not batched by task count, not threshold-triggered.
- **BECAUSE: ENGINEERING (E3).**
- **REJECTED:** Fixed-batch refresh every t tasks. Its own source admits t is unset and its sensitivity unstudied — the same honesty problem `Q24` has with decay windows, which is worth noting as a pattern: the field routinely ships unset parameters.
- **COST:** Per-transcript extraction cost (`Q170`).
- **CONFIDENCE:** high

---

### Q643 — When memory grows stale or redundant, what should be forgotten, and on whose authority?

- **DECISION:** Redundant → merged into the existing memory as evidence, on the system's authority (`Q159`). Stale → decays or expires by tier, on the clock's authority (`Q283`). Wrong → corrected, demoted, or forgotten, on the **user's** authority only (`Q269`). Nothing is forgotten on the system's authority.
- **BECAUSE: POSITION.** `P§9` assigns each mechanism explicitly, and assigns removal to the user: "Actions per entry: Confirm / Correct / That's not me anymore / Forget."
- **REJECTED:** System-authored dynamic discarding. It wins for bounded-memory systems at scale (`Q54`). At this scale it would be the system deciding what about the user is no longer worth keeping, which `P§9` reserves for the user.
- **COST:** As `Q54` — unbounded growth with no system-side relief valve.
- **CONFIDENCE:** high

---

### Q644 — Should failed experience be discarded as low quality, retained as a negative example, or used to rewrite prior guidance?

- **DECISION:** Not applicable — no experience is retained (`Q634`). The nearest real case is a *contradicted* memory, which is superseded, with the old version kept in history as evidence rather than as a negative example.
- **BECAUSE: POSITION.** `P§9`'s supersession rule.
- **REJECTED:** Combining a failure with retrieved memory to revise it. It wins for procedural self-improvement and is a strong technique. It would be Kivi rewriting its own beliefs without the user, which `Q269` forbids.
- **COST:** As `Q12`.
- **CONFIDENCE:** high

---

### Q650 — What should be discarded during abstraction: exploratory errors, environmental detail, personal/source content, uncertainty, or nothing?

- **DECISION:** There is no abstraction step. Extraction discards excluded categories and third-party personal content and nothing else; it never discards uncertainty (which is carried as tier) and never discards source (which is required).
- **BECAUSE: POSITION.** `P§4`'s tier field carries uncertainty rather than discarding it; `P§9` requires source. The surveyed system's underspecified "whether uncertainty/source context survives" is precisely the gap the position closes.
- **REJECTED:** Trajectory abstraction into scripts. Wins for procedural memory.
- **COST:** No abstraction means no generalisation beyond what an observation's evidence count expresses.
- **CONFIDENCE:** high

---

### Q652 — Should a memory system ingest every readable project/transcript artifact, only explicit saves, or only extracted durable propositions?

- **DECISION:** Ingest transcripts (all of them, as raw provenance), extract durable propositions (selectively, through four gates), store both in separate stores with separate rules (`Q141`). Not "every readable artifact" — the input contract is transcripts and application context, nothing else.
- **BECAUSE: POSITION.** `P§9` (raw) + `P§4` (extracted) + `P§5` (the input contract's asymmetry).
- **REJECTED:** A broad extension allowlist across project files. It wins for a developer-assistant product ingesting a codebase. Kivi's input is a dictation stream.
- **COST:** No file or document ingestion. If a user's work lives in documents, Kivi only knows what they dictated about them.
- **CONFIDENCE:** high

---

### Q655 — What content must never be persisted, and should rejection be visible?

- **DECISION:** Never persisted as memory: excluded categories (`Q629`), third-party personal content, characterisations of anyone, and literal secrets. Rejection is visible as a reason-coded non-content audit row (`Q199`). Malformed or oversized *input* is a separate matter and fails loudly rather than being sanitised (`Q556`).
- **BECAUSE: POSITION.** `P§2` for the categories and for visibility; `P§5` for third parties.
- **REJECTED:** Silent skipping and sanitisation of anything unreadable (the surveyed answer). It wins for robust bulk ingestion. It makes both halves of the position's trust claim unprovable — you cannot show what was refused if refusal leaves no trace.
- **COST:** As `Q199` — a metadata trail about sensitive categories exists.
- **CONFIDENCE:** high

---

### Q656 — Are people/projects loose strings, canonical entities, or versioned identities with disambiguators?

- **DECISION:** Canonical entities with aliases and a canonical spelling, not versioned identities. One row per real-world thing, with an alias list, a type, and typed relations (`Q203`). Versioning applies to an entity's *attributes* through supersession, not to its identity.
- **BECAUSE: POSITION.** `P§7` requires canonical spelling for the dictation path ("*Priya Raghavan*, not *Prea Raghavan*"), which requires a canonical form and an alias set. `P§4` requires relations, which require identity.
- **REJECTED:** Semicolon-separated entity strings (the surveyed answer). It wins on extraction simplicity — no resolution step, no merge errors. It cannot serve `P§7`'s spelling contract or `P§4`'s relations.
- **COST:** Entity resolution errors (`Q203`). Two people with the same first name is an unsolved case in this corpus's world — `P§AppA` has only one Priya, which conveniently hides the problem.
- **CONFIDENCE:** high

---

### Q660 — Permit multi-writer optimistic updates, serialize per source, serialize the palace, or route all writes through one owner?

- **DECISION:** Route all writes through one owner — a single writer process against a single embedded database (`Q96`, `Q184`).
- **BECAUSE: ENGINEERING (E2).** Position is silent. Single-user, single-process, embedded storage leaves no reason for anything else.
- **REJECTED:** Per-source serialisation with declared backend capabilities. Wins for a pluggable multi-backend system, which `Q440` already declines.
- **COST:** As `Q96` — throughput ceiling, no scale path.
- **CONFIDENCE:** high

---

### Q665 — Fail closed, return partial lexical evidence, self-repair, quarantine, or continue degraded?

- **DECISION:** All four, assigned by path. **Write path:** fail closed (an unavailable exclusion check blocks the write, `Q394`). **Extraction:** quarantine after retries (`Q108`). **Retrieval with one leg down:** report the degradation and abstain rather than answering from the surviving leg (`Q27`). **Embedding index corrupt or model-mismatched:** fail loudly and require a documented rebuild, never silently bypass to lexical-only.
- **BECAUSE: POSITION for the retrieval half** — `P§8`'s no-plausible-guess rule; **ENGINEERING (E4) for the rest.** The mismatched-embedder case is worth calling out: it is the failure mode `Q155` fixes by storing model identity on the row, and it fails loudly precisely because silent bypass would look like a quality regression rather than a fault.
- **REJECTED:** Continuing degraded with partial lexical evidence. It wins on availability and is what the surveyed system does sensibly. It loses because a lexical-only answer and a hybrid answer are indistinguishable to the user.
- **COST:** Visible brittleness (`Q183`). An index rebuild is an operator action, which `RUN.md` must document.
- **CONFIDENCE:** high

---

### Q667 — Is replay keyed by path, content, logical event, or sequence; and does order mean ingest time or authored time?

- **DECISION:** Keyed by logical event — `transcript_id` — with content hash as a secondary integrity check. Order means **authored time** (`occurred_at`), not ingest time (`Q76`).
- **BECAUSE: POSITION for the ordering half.** `P§9`'s supersession is "new evidence replaces old," and "new" in a product about a person's work must mean when it happened, not when the file was imported. A corpus imported out of order must produce the same result as one imported in order.
- **REJECTED:** Path-plus-mtime keying (the surveyed answer). It wins for a filesystem-watching ingester (`Q97` already declines that). It would make the same transcript re-imported under a different filename a new event.
- **COST:** Requires every imported record to carry a stable id and a trustworthy `occurred_at`. The import format must demand both, and the reviewer's corpus must supply them — a documented import-mapping requirement, and a real risk if their logs lack a stable id.
- **CONFIDENCE:** high on the decision, medium on the external corpus satisfying it.

---

### Q668 — Is "data does not leave the device" sufficient, or must some locally seen data never become durable?

- **DECISION:** Not sufficient. Locality is irrelevant to this position — the boundary is about what becomes durable, not about where it sits. Third-party personal content and excluded categories never become durable even though the whole system is local.
- **BECAUSE: POSITION.** `P§5`'s entire argument is about retention, not transmission: "Priya did not agree to anything." Local storage would not make it acceptable. This is one of the clearest places the position diverges from how the field frames privacy.
- **REJECTED:** Local-first as the privacy story, with broad retention inside the device. It wins as a privacy pitch and is much easier to build. It is the exact substitution `P§2` warns against: a claim about the pipeline instead of a claim about the boundary.
- **COST:** The system does something harder than local-only storage and gets less obvious credit for it. The "read, not kept" marker has to do the explaining.
- **CONFIDENCE:** high

---

### Q669 — Is source content retained?

- **DECISION:** Yes, always, in full, with no batch-mode exception (`Q28`). A raw-content default that differs between single and batch writes would mean the corpus import path retained less than the live path — an invisible divergence.
- **BECAUSE: POSITION.** `P§9`'s provenance requirement, which does not vary by how the transcript arrived.
- **REJECTED:** `no_raw=true` for batch writes (the surveyed default). It wins on bulk-import storage. It would break provenance for exactly the ~500 records the reviewer imports, which is the whole corpus.
- **COST:** As `Q28`/`Q186`.
- **CONFIDENCE:** high

---

### Q672 — What is current truth?

- **DECISION:** For a given fact, current truth is the non-superseded, non-demoted record with the highest tier, tie-broken by most recent event time, then by most recent user confirmation. Tier outranks recency (`Q174`) — this is the one place this answer differs materially from the surveyed one.
- **BECAUSE: POSITION.** `P§4`'s tier permissions ("Treat as true. Use freely" vs "Never as a rule") make tier a truth-precedence order, not just a display label.
- **REJECTED:** Most-recent-non-retraction ordered by event date (the surveyed answer). It wins when all records are equally authoritative. Here they are not, and a recent observation outranking an old stated preference is the `P§4` failure mode.
- **COST:** As `Q174` — Kivi can be confidently stale.
- **CONFIDENCE:** high

---

### Q673 — What makes enrichment idempotent?

- **DECISION:** Keyed by `(transcript_id, extractor_version, extractor_model)`. Re-running with the same triple is a no-op; changing the version or model is a new run that supersedes the previous run's candidates rather than duplicating them.
- **BECAUSE: ENGINEERING (E2, `Q08`).** The surveyed `(frame_id, engine_kind, engine_version)` key is the right shape; adding the model to the key is the fix for the `Q155`/`Q531` problem — a model change that is not in the idempotency key produces silently different results under the same key.
- **REJECTED:** Keying on transcript alone. It wins on simplicity but makes a model upgrade invisible and unreproducible.
- **COST:** A model upgrade invalidates every extraction and requires a full reprocess, which then collides with user suppressions and corrections that must survive it (`Q526`).
- **CONFIDENCE:** high

---

### Q675 — What happens with no hits or partial extraction?

- **DECISION:** No hits → one bounded fallback to raw-transcript lexical search, clearly labelled (`Q211`); if that also misses, abstain with the search description (`P§8`). Partial extraction → the transcript is marked partially extracted, the successful candidates are kept, the failure is recorded, and the transcript is queued for retry.
- **BECAUSE: POSITION.** `P§8`'s abstention worked example shows exactly the bounded-broadening-then-report behaviour: it names what it searched and offers the near-miss.
- **REJECTED:** Unbounded query broadening and timeline fallback. It wins on hit rate. Unbounded broadening eventually returns something for any query, which converts abstention into a weak answer — the thing `P§8` forbids.
- **COST:** The broadening bound is a parameter with no principled value yet. See **Section A**.
- **CONFIDENCE:** medium

---

### Q677 — Is commit explicit?

- **DECISION:** Yes, explicit, and a failed commit is an error that propagates. No implicit commit on scope exit, no discarded commit errors.
- **BECAUSE: ENGINEERING (E4).** An implicit commit whose error is swallowed is the purest form of the silent failure `E4` forbids — the memory would appear to exist and would not.
- **REJECTED:** Implicit commit on drop. Wins never; it is a bug in the surveyed system, quoted here because it is easy to reproduce by accident in any language with destructors or context managers.
- **COST:** More explicit transaction handling in the write path.
- **CONFIDENCE:** high

---

### Q678 — At what granularity should experience enter memory: raw event, turn, extracted claim, entity relation, episode, or some combination?

- **DECISION:** A combination, but a fixed one: raw **transcripts** enter the provenance store; **extracted claims** in three types (including entity relations and episodes as two of them) enter memory. Nothing else.
- **BECAUSE: POSITION.** `P§4` (three types) plus `P§9` (raw provenance).
- **REJECTED:** Raw events into episodic storage with semantic gists derived later. It wins by deferring the extraction schema decision, which is attractive when the ontology is unknown. `P§4` fixes the ontology in advance, so deferral buys nothing.
- **COST:** As `Q142` — facts that do not fit three types are lost.
- **CONFIDENCE:** high

---

### Q680 — When should durable-memory decisions run: synchronously per interaction, periodically in batches, or on demand?

- **DECISION:** Per-transcript, asynchronously, queue-driven — which is neither synchronous nor a scheduled batch. Triggered by arrival, not by a clock.
- **BECAUSE: ENGINEERING (E3).** `P§AppB` defers timing.
- **REJECTED:** Scheduled offline consolidation every six hours. It wins for cross-transcript consolidation work that genuinely needs a batch view — and note that observation formation *is* cross-transcript, so there is a real argument that observation detection should be a periodic pass rather than an incremental one. That is a live design question and I am choosing incremental for `Q08`'s idempotence; the alternative is defensible.
- **COST:** Observation detection must run incrementally, which means each new transcript triggers a similarity search against existing memories — more expensive per transcript than one periodic pass.
- **CONFIDENCE:** medium

---

### Q681 — What should determine whether an event is promoted, temporarily retained, or pruned?

- **DECISION:** Nothing scores events. Admission is a set of binary gates (`Q307`); promotion is a user confirmation (`Q191`); pruning does not exist (`Q54`). There is no weighted salience score anywhere in the system.
- **BECAUSE: POSITION.** `P§4`: "Nothing self-promotes." A salience score that promotes the top 20% is self-promotion with statistics. `P§9` reserves removal for the user.
- **REJECTED:** A weighted score over recency, inverse frequency, surprise, entity salience, and outcome, promoting the top 20% and pruning the bottom 20%. It is the most sophisticated alternative in the inventory and it would produce a better-performing memory. Note especially **surprise** and **outcome**: both require Kivi to judge the significance of events in the user's life, which is characterisation by another name (`Q396`, `Q634`).
- **COST:** Memory grows without a quality filter beyond the admission gates. Unimportant facts sit alongside important ones with no ranking signal except evidence and recency.
- **CONFIDENCE:** high

---

### Q682 — Should repetition increase a memory's value, decrease it as redundancy, or affect confidence separately from retention?

- **DECISION:** Repetition increases `evidence_count`, which affects **ranking** and **decay resistance**, and affects **nothing else** — not tier, not truth, not retention eligibility. A fact seen once is retained exactly as durably as one seen twenty times.
- **BECAUSE: POSITION.** `P§4`: "Nothing self-promotes… Twenty is still a pattern." The separation of evidence from standing is the position's core epistemic move.
- **REJECTED:** Inverse frequency favouring unusual events. It wins for an episodic system where novelty is the signal of interest. Here it would systematically down-weight the repeated preferences that are the product's main value ("client emails in prose" is valuable *because* it repeats).
- **COST:** No novelty signal. Kivi cannot notice that something unusual happened.
- **CONFIDENCE:** high

---

### Q685 — Should reading a memory be allowed to change it, and if so, what evidence authorizes that change?

- **DECISION:** No. Retrieval is side-effect-free with respect to memory content, tier, evidence, and standing. The only things reading writes are trace records. Nothing reconsolidates.
- **BECAUSE: POSITION.** `P§9` requires every change to be attributable and auditable; a retrieval-triggered modification is a change with no user-visible cause. `P§4`'s "Nothing self-promotes" forbids the most likely such change.
- **REJECTED:** A reconsolidation window in which retrieval with new context or contradiction can modify the memory — the most cognitively-faithful design in the inventory, and genuinely elegant. It wins in a system modelling human memory. It loses because a memory that changes when you look at it cannot be shown to a user as a stable belief they control.
- **COST:** No strengthening-by-use, no context-driven refinement. Memory only changes through the extractor and the user.
- **CONFIDENCE:** high

---

### Q701 — When responsibilities for acting, judging, and learning differ, should they be implemented as one model-role or separate roles?

- **DECISION:** Separate, but not as agent roles — as **pipeline stages in code** with distinct prompts and distinct outputs: extract, classify-for-exclusion, judge-sameness, generate. No actor/evaluator/reflector loop.
- **BECAUSE: POSITION.** `P§2`'s requirement that exclusion be "a check that runs on candidate memories" forces the exclusion classifier to be a separate stage from extraction. Beyond that, `E5` declines the reflection role (`Q459`).
- **REJECTED:** Modular Actor/Evaluator/Self-Reflection roles. Wins for iterative task-solving agents.
- **COST:** More model calls per transcript than a single combined extraction prompt, and the cost shows in the reported figures.
- **CONFIDENCE:** high

---

### Q702 — What should enter the actor on each attempt?

- **DECISION:** The request, the disclosure-filtered retrieval result, the bounded turn history, and the entity list (`Q255`). No reflections, no trajectory history, no few-shot demonstrations drawn from past interactions.
- **BECAUSE: POSITION.** `P§6`'s dial requires the model's input to be permission-filtered (`Q255`); `Q459` removes reflections; `Q463` removes demonstrations.
- **REJECTED:** Including a reflection buffer. Wins for self-improving agents.
- **COST:** As `Q12`.
- **CONFIDENCE:** high

---

### Q704 — Who or what should decide whether an attempt succeeded?

- **DECISION:** Nobody, in-loop. There is no success signal. Success is judged only offline, by the evaluation, against the `P§AppC` claims and by human inspection (`Q429`, `Q592`).
- **BECAUSE: POSITION.** `P§2` forbids "any characterisation of the person's competence or character," and a success evaluator over the user's requests slides into exactly that. Also `P§8`: Kivi's job when unsure is to say so, not to score itself.
- **REJECTED:** Task-dependent evaluators. Wins where tasks have ground truth — code execution, exact-match QA. Drafting an email has none.
- **COST:** No in-loop quality signal at all. Kivi cannot tell a good answer from a bad one.
- **CONFIDENCE:** high

---

### Q705 — When should the system interrupt an ongoing trajectory and trigger reflection?

- **DECISION:** Never. There are no trajectories and no reflection (`Q459`, `Q508`). **Out of scope** (`E5`).
- **BECAUSE: ENGINEERING (E5).**
- **REJECTED:** Loop-detection triggers. Wins in agent loops.
- **COST:** None here.
- **CONFIDENCE:** high

---

### Q706 — After failure, should the next attempt continue from the current world state or restart?

- **DECISION:** Not applicable — one attempt, no retry (`Q508`). A failed request abstains; the user may ask again, which is a fresh request against unchanged state.
- **BECAUSE: POSITION.** `P§8`'s no-guess rule.
- **REJECTED:** Reset-and-retry after reflection. Wins in agent loops.
- **COST:** None here.
- **CONFIDENCE:** high

---

### Q707 — What should be retained after a failed attempt?

- **DECISION:** The trace, for inspection and evaluation. Nothing in memory. A failed answer is not evidence about the user.
- **BECAUSE: POSITION.** `P§4`'s tiers admit only user statements; `Q198` excludes Kivi's own output.
- **REJECTED:** A distilled first-person verbal reflection. It wins for self-improvement and is the Reflexion mechanism. It is a model-authored durable belief (`Q239`).
- **COST:** As `Q12`.
- **CONFIDENCE:** high

---

### Q708 — When memory exceeds the context budget, what should be discarded?

- **DECISION:** The lowest-ranked retrieval results, by the deterministic ranking (`Q26`), reported as budget drops in the trace (`Q562`). Never the highest-tier ones — stated memories are never dropped for budget before observed ones.
- **BECAUSE: POSITION.** `P§4`'s tier permissions make stated memories the ones Kivi may "use freely"; dropping them for budget while keeping observations would invert the epistemics.
- **REJECTED:** A sliding window of the last N items. It wins for reflection buffers with strong recency structure. Kivi's retrieval set has no inherent order to slide over.
- **COST:** A high-ranked-but-wrong memory crowds out a lower-ranked-but-right one and the user cannot intervene (`Q616`).
- **CONFIDENCE:** high

---

### Q714 — How many retries should be permitted, and what should stop learning?

- **DECISION:** One attempt per request (`Q508`). Extraction retries are bounded and end in quarantine (`Q108`). There is no learning loop to stop.
- **BECAUSE: POSITION.** `P§8` for the answer path; **ENGINEERING (E4)** for the extraction path.
- **REJECTED:** Task-specific retry maxima. Wins in benchmark agent loops.
- **COST:** As `Q508`.
- **CONFIDENCE:** high

---

### Q721 — What should determine whether an observed span deserves durable storage?

- **DECISION:** The four gates (`Q307`), not a semantic-density or information-gain judgement. Content category and subject decide, not informativeness.
- **BECAUSE: POSITION.** `P§3`'s test is about *the user's annoyance at repeating it* and *their discomfort at its being recorded* — both properties of the content's relationship to the person, not of its information content.
- **REJECTED:** An LLM judging semantic density relative to immediate history. It wins on storage efficiency and would reduce noise. It would drop a low-information but highly durable fact ("I sign off 'Best, Meera'") and keep a high-information but ephemeral one.
- **COST:** Low-value-but-eligible facts accumulate. The memory surface will contain trivia.
- **CONFIDENCE:** high

---

### Q722 — At what granularity should a continuous interaction be assessed for extraction?

- **DECISION:** One whole transcript, no windowing, no overlap (`Q480`).
- **BECAUSE: ENGINEERING (E3) and POSITION** (`P§9`'s provenance must point at a whole transcript).
- **REJECTED:** Fixed overlapping windows of 20 turns with stride 5. It wins for continuous conversation streams with no natural boundary. Overlapping windows would also make the same fact extractable twice from overlapping regions, breaking `Q08`.
- **COST:** As `Q480`.
- **CONFIDENCE:** high

---

### Q729 — When multiple facts appear related, what should determine whether they become one memory?

- **DECISION:** A two-stage test: deterministic candidate generation by lexical/vector similarity above a threshold, then an LLM sameness judgement with a recorded verdict, model identity, and the evidence it saw (`Q92`). Not "current conversational context" — merging must not depend on when the question is asked.
- **BECAUSE: ENGINEERING (E2, `Q08`).** Position is silent on merge mechanics. Context-dependent merging would make ingestion non-idempotent, which `P§AppC` claim 6 requires.
- **REJECTED:** LLM relatedness plus current conversational context (the surveyed answer). It wins on merge quality in live conversation. It cannot be replayed.
- **COST:** As `Q159`/`Q479` — merge is the most fallible step and its errors are hard to unwind (`Q173`).
- **CONFIDENCE:** medium

---

### Q732 — Should all retrieval representations be searched for every eligible query, or only selected ones?

- **DECISION:** All of them, always, in parallel, on the Hey Kivi path — `P§6` requires full retrieval regardless of permission, and selecting representations per query would introduce a second hidden filter. On the dictation path, only the entity/lexical representation exists (`Q138`).
- **BECAUSE: POSITION.** `P§6`: "Kivi always retrieves everything it has."
- **REJECTED:** Query-conditional representation selection. It wins on latency and cost, which the brief asks to be reported. It loses because the withheld-count claim (`P§AppC` claim 4) requires the retrieval to have been complete.
- **COST:** Every request pays for both legs even when one is obviously sufficient.
- **CONFIDENCE:** high

---

### Q734 — What evidence should the answer generator receive: abstractions, atoms, raw sources, or some combination?

- **DECISION:** Atoms — the retrieved typed memories, each carrying its tier and evidence — plus, only on the raw-fallback path (`Q211`), labelled raw transcript excerpts. Never abstractions (there are none) and never unlabelled raw source.
- **BECAUSE: POSITION.** `P§8`'s trace shows "what was used in the answer," and `P§9` links each to "the source transcript behind each memory, one tap away" — so the generator must receive memories that carry their identity, not flattened text.
- **REJECTED:** Ordered abstract representations plus detail units, with raw provenance excluded from the prompt (the surveyed answer). It wins on prompt economy. Excluding provenance from the prompt is the specific thing that makes a system unable to say *which* memory produced a claim.
- **COST:** Larger prompts carrying metadata the model mostly ignores, and reported token cost reflects it.
- **CONFIDENCE:** high

---

### Q745 — Which incoming content may cross from working context into persistent memory?

- **DECISION:** Only user-authored content that passes the four gates. Application context and Kivi's own output never cross (`Q342`, `Q198`). The crossing point is a named, testable boundary in the code.
- **BECAUSE: POSITION.** `P§5`: "Third-party content enters the context window. It does not enter the write path."
- **REJECTED:** All interaction text becoming episodic memory with no admission filter (the surveyed answer, and the field default). It wins on recall. It is the default this whole position is written against.
- **COST:** As `Q342`.
- **CONFIDENCE:** high

---

### Q749 — Which relations should be created between memories, and on what evidence?

- **DECISION:** Four typed relations only, each on explicit evidence (`Q362`): `supersedes`, `evidence_for`, `about_entity`, `entity_relation`. No proximity edges, no automatic bidirectional links, no weighted similarity associations.
- **BECAUSE: POSITION.** `P§8`'s Why panel must explain why a memory surfaced; "it was within five turns of another memory at weight 0.8" is not an explanation a person can act on.
- **REJECTED:** Temporal edges plus windowed bidirectional links plus similarity associations. It wins for associative recall and is the basis of spreading activation (`Q752`). It produces retrieval results no one can justify.
- **COST:** No associative retrieval (`Q362`).
- **CONFIDENCE:** high

---

### Q752 — After initial matches, how far and by what mechanism should relevance travel?

- **DECISION:** It does not travel. Retrieval is direct match plus deterministic re-rank; there is no graph traversal, no spreading activation. The one exception is entity expansion: a query naming *Atlas* also matches memories linked to the Atlas entity, which is a single explicit join, not a spread.
- **BECAUSE: POSITION.** `P§8`'s explicability requirement, as in `Q749`. A single entity join is explicable ("this memory is about Atlas"); three iterations of weighted activation is not.
- **REJECTED:** Spreading activation with decay over a weighted graph. It is the most powerful retrieval mechanism in the inventory and would materially improve recall on indirect questions. It wins if explicability could be recovered post hoc, which for a three-hop weighted spread it effectively cannot.
- **COST:** Indirect and multi-hop questions retrieve poorly. "What did we decide about the thing Arun was blocked on?" needs two hops and will likely abstain. This is a genuine capability loss and the brief explicitly tests "whether it can recover information distributed across multiple dictations" — one-hop entity expansion is the only mechanism serving that, and it may not be enough. Flagged as a live risk in **Section A**.
- **CONFIDENCE:** medium

---

### Q753 — When a node has many associations, how should its influence be controlled?

- **DECISION:** Not applicable — no activation to control (`Q752`). The analogous problem does arise for entity expansion: a hub entity like *Atlas* is linked to most memories, so entity expansion is capped by the ordinary top-k and the deterministic re-rank rather than by fan-out normalisation.
- **BECAUSE: ENGINEERING.** Position is silent; this follows from `Q752`.
- **REJECTED:** Fan-out division. It wins in a spreading-activation design and is the correct fix there.
- **COST:** A hub entity can dominate a result set, mitigated only by ranking. Worth watching in the evaluation.
- **CONFIDENCE:** medium

---

### Q754 — When multiple candidate memories compete, should strong candidates suppress weaker ones?

- **DECISION:** No suppression. Ranking orders them; top-k truncates; the trace shows what was cut. Competition is not modelled.
- **BECAUSE: POSITION.** `P§8`'s trace must explain the result set. Lateral inhibition means a memory's absence depends on other memories' presence in a way that cannot be stated simply.
- **REJECTED:** Lateral inhibition among top candidates. It wins on precision in an activation-based system.
- **COST:** Near-duplicate results can crowd the set (`Q561`).
- **CONFIDENCE:** high

---

### Q761 — When conversational history enters memory, should the basic retained object be raw turns, fixed chunks, topic-bounded episodes, extracted facts, or some combination?

- **DECISION:** Raw transcripts (provenance) plus extracted typed facts (memory). No topic-bounded episode summaries, no "exhaustive transient semantics," no derived experience traces.
- **BECAUSE: POSITION.** `P§4` + `P§9`, as `Q678`. The "experience trace" half is separately forbidden by `P§5`, since the surveyed system derives one per participant.
- **REJECTED:** Topic-bounded episode summaries plus exhaustive semantics. It wins on recall breadth and narrative questions (`Q154`).
- **COST:** As `Q154`.
- **CONFIDENCE:** high

---

### Q763 — When an utterance contains text and visual context, how much should semantic extraction preserve versus discard?

- **DECISION:** Not applicable — text only (`Q98`). Had it applied: extraction preserves only what passes the four gates, and "names, colors, and descriptors" of people would fail the third-party test outright.
- **BECAUSE: POSITION.** Scope note (text client) and `P§5`.
- **REJECTED:** Exhaustive fact-based extraction including image details and personal descriptors. It wins for multimodal assistants; the personal-descriptor half is directly contrary to `P§5` in any modality.
- **COST:** None here.
- **CONFIDENCE:** high

---

### Q764 — Which candidate facts deserve durable retention: all personal experiences, only concrete biographical facts, only user-confirmed facts, or only task-relevant durable facts?

- **DECISION:** Only **work-level durable facts** — which is none of the four options exactly. Not all personal experiences (excluded). Not biographical facts (`P§2` excludes most biography: family, faith, health, finances). Not only confirmed facts (extraction writes at observed and stated tiers without confirmation, `Q606`). Not merely task-relevant (a preference is durable without being relevant to any current task).
- **BECAUSE: POSITION.** `P§3`: "the durable, work-level things you would be annoyed to have to repeat," and `P§2`'s exclusion list.
- **REJECTED:** Concrete biographical facts about the subject's own life (the surveyed answer, and the closest reasonable alternative). It wins for a personal-assistant product covering a whole life. `P§2` restricts Kivi to work, explicitly excluding "relationships and family," "faith," and "finances beyond work-level facts."
- **COST:** Kivi is useless outside work. A user who dictates personal correspondence gets nothing and is never told why in specific terms.
- **CONFIDENCE:** high

---

### Q767 — When a trace is an outlier, should it remain noise, be discarded, or be forced into the nearest narrative?

- **DECISION:** It remains itself. There is no clustering, so there is no noise category and nothing to force. A one-off fact is stored as a one-off fact with `evidence_count = 1`.
- **BECAUSE: POSITION.** `P§4`'s schema stores evidence count as data rather than using it to decide membership. Forcing an outlier into a cluster would manufacture a pattern the user never exhibited — an observation with fabricated evidence, which `P§4` forbids ("pointable-at").
- **REJECTED:** HDBSCAN noise labelling with KNN reassignment to the nearest cluster. It wins for topic organisation over large corpora. Reassigning every noise point to the nearest cluster is specifically dangerous here: it is a mechanism that guarantees no fact is ever an exception.
- **COST:** No topical organisation of the memory surface beyond tier grouping (`Q395`, `Q399`).
- **CONFIDENCE:** high

---

### Q773 — What should change over time: cluster organization, claim validity, confidence, retention, or all of them?

- **DECISION:** Only standing, and only for two tiers: observations decay, hypotheses expire (`Q24`). Not organisation (no clusters), not confidence (no confidence field), not claim validity (only supersession by evidence or the user changes validity).
- **BECAUSE: POSITION.** `P§9`'s two named time mechanisms and nothing more.
- **REJECTED:** Self-evolving reorganisation. The inventory notes its source leaves decay and regulated forgetting as "future directions" — the same unset-parameter honesty problem as `Q24`/`Q642`, and worth noting as the field's consistent weak point.
- **COST:** As `Q24`.
- **CONFIDENCE:** medium

---

### Q783 — What should happen to low-density memories that do not fit any coherent cluster?

- **DECISION:** Duplicate of `Q767`. Nothing — they are ordinary memories.
- **BECAUSE: POSITION.** `P§4`.
- **REJECTED:** See `Q767`.
- **COST:** See `Q767`.
- **CONFIDENCE:** high

---

### Q784 — Should long-term memory have one hierarchy, and if so, what should its levels mean?

- **DECISION:** No hierarchy. Two flat orthogonal axes — type and tier — and one entity graph. The user-facing organisation is three tier groups (`Q395`).
- **BECAUSE: POSITION.** `P§4`: "memory has two independent axes… Collapsing them into one is where most memory systems go wrong." A theme→topic→thread hierarchy is a third organising principle the position does not have, and it would compete with tier for the user's attention on the memory surface.
- **REJECTED:** A fixed three-level theme/topic/thread hierarchy. It wins for navigating a large memory set, which `Q399` admits is a real gap — a few hundred facts in three flat lists is a lot of list. It wins if the memory surface becomes unusable, which is a plausible outcome.
- **COST:** Navigation at scale. The memory surface's usability is the weakest part of this decision and it is not addressed by the position.
- **CONFIDENCE:** medium

---

### Q794 — Which model components should be entrusted with boundaries, facts, summaries, selection, and judgment?

- **DECISION:** Boundaries (exclusion) — a model classifier whose verdict is enforced by code and whose false-negative rate is measured (`Q429`); facts (extraction) — a pinned model at temperature 0; summaries — none exist; selection (retrieval ranking) — **code, never a model** (`Q212`); judgment (sameness/contradiction) — a model with a recorded verdict (`Q92`); tool choice and wording — a model.
- **BECAUSE: POSITION.** `P§2` forces the boundary check to be enforced in code even when a model informs it; `P§8` forces selection to be explicable and therefore deterministic. `Q247` is the general rule.
- **REJECTED:** One small model throughout including as judge (the surveyed answer). It wins on cost and operational simplicity. Using the same model as extractor and as evaluation judge is specifically bad practice and `Q592` rejects it for grading.
- **COST:** Several distinct model roles to prompt, version, and price, all appearing separately in the cost report.
- **CONFIDENCE:** high

---

### Q797 — When a turn arrives, what determines whether anything is written at all?

- **DECISION:** Four gates, applied to each candidate (`Q307`). Dedupe is one of them, not the only one.
- **BECAUSE: POSITION.** `P§2` and `P§3`.
- **REJECTED:** "Nothing. Everything extractable is extracted; the only gate is dedupe" (the surveyed answer, and an unusually candid statement of the field's default). It wins on recall and on simplicity. It is the position's antagonist.
- **COST:** As `Q307`.
- **CONFIDENCE:** high

---

### Q798 — Whose words count as evidence?

- **DECISION:** The user's only (`Q01`, `Q153`, `Q198`).
- **BECAUSE: POSITION.** `P§4`'s tier definitions.
- **REJECTED:** Both parties' words. See `Q01` — and note this surveyed system agrees with the position, which is rare enough to be worth saying: user-messages-only at construction is the same call.
- **COST:** As `Q01`.
- **CONFIDENCE:** high

---

### Q799 — What time does a memory carry?

- **DECISION:** Event time, parsed from the content where stated, falling back to the transcript's `occurred_at`. Plus, separately, `first_seen_at` and `last_confirmed_at`, which are system times. Three distinct temporal fields with three distinct meanings, never conflated.
- **BECAUSE: POSITION.** `P§4`'s schema names `first_seen_at` and `last_confirmed_at`; `P§4`'s Episode example — "*On 12 March the user moved the Atlas review from Tuesday to Thursday*" — carries an event time distinct from both, and `P§9`'s decay operates on observation time, not event time.
- **REJECTED:** Dialogue time only. It wins on simplicity and avoids date-parsing errors. It cannot express the episode example, where the meaningful date is the one in the sentence.
- **COST:** Date parsing from natural language is error-prone ("next Tuesday" relative to a transcript date), and a parse error silently misplaces an episode in time. Needs a confidence-free fallback: if the date cannot be resolved, use transcript time and mark it as such.
- **CONFIDENCE:** high

---

### Q800 — What is a memory, structurally?

- **DECISION:** A typed record: `id`, `type` (entity|preference|episode), `tier` (stated|observed|hypothesised), `content` (a short human-readable statement), `evidence_count`, `source_transcript_ids[]`, `event_time`, `first_seen_at`, `last_confirmed_at`, `status`, `extractor_model`, `extractor_version`. Plus entities as their own rows with aliases and relations.
- **BECAUSE: POSITION.** `P§4`, near-verbatim: "Schema carries `type`, `tier`, `content`, `evidence_count`, `source_transcript_ids[]`, `first_seen_at`, `last_confirmed_at`, `status`." The additions (`event_time`, `extractor_model`, `extractor_version`) are `ENGINEERING`, from `Q799` and `Q673`.
- **REJECTED:** Two tiers (the surveyed answer). Three tiers is position-fixed and the third one (hypothesised) is what makes Daari possible.
- **COST:** A wide row and a schema that must migrate if the ontology changes (`Q142`).
- **CONFIDENCE:** high

---

### Q802 — What signal groups mentions into a topic?

- **DECISION:** Nothing. There is no topic layer (`Q767`, `Q784`). Mentions group by **entity**, through explicit entity resolution, not by embedding clustering.
- **BECAUSE: POSITION.** `P§4` makes entities the organising nouns of the user's world; topics are not in the ontology.
- **REJECTED:** GMM over entity-name embeddings within a time slice. It wins for discovering structure in a large unlabelled corpus. Here the structure is declared, not discovered.
- **COST:** No topical view. As `Q784`.
- **CONFIDENCE:** high

---

### Q809 — What happens when the temporal constraint is wrong or absent?

- **DECISION:** Symmetric and conservative. If a query carries a temporal constraint, it filters everything uniformly — memories and raw-transcript fallback alike. If the constraint cannot be resolved, it is dropped and the trace says so, rather than being silently ignored or silently applied.
- **BECAUSE: ENGINEERING (E4).** Position is silent. The surveyed system's asymmetry — hard-filtering summaries while exempting raw turns unconditionally — is the kind of inconsistency that produces results no trace can explain.
- **REJECTED:** Asymmetric filtering with an unconditional raw exemption. It wins on recall when temporal metadata is unreliable, which given `Q799`'s parsing risk is a real concern. The honest version of that hedge is to drop the constraint visibly, not to exempt one store from it.
- **COST:** Temporal queries will sometimes return nothing when a loose interpretation would have found the answer, and the user sees "I dropped your date filter" rather than a result.
- **CONFIDENCE:** medium

---

### Q816 — What should survive extraction besides structured facts: raw source turns, compressed summaries, or neither?

- **DECISION:** Raw source transcripts (`Q28`) and an entity index. Not summaries, not persona summaries. The persona summary in particular is the `P§2` profile.
- **BECAUSE: POSITION.** `P§9` (raw) and `P§2` (no profile/persona).
- **REJECTED:** Raw turns plus graph index plus topic and persona summaries. It wins on retrieval breadth. "Persona summaries" is the single most direct instance in the inventory of the thing `P§2` was written to refuse.
- **COST:** As `Q154`/`Q399`.
- **CONFIDENCE:** high

---

### Q829 — What optimization target should choose among memory designs?

- **DECISION:** Duplicate of `Q477`/`Q585`. The seven `P§AppC` claims plus the brief's inspection list, with retention and disclosure breaches as severity-one. Not LLM-judged accuracy.
- **BECAUSE: POSITION.** `P§AppC`.
- **REJECTED:** Maximising LLM-judged accuracy with token cost and latency reported alongside. See `Q592`.
- **COST:** As `Q477`.
- **CONFIDENCE:** high

---

### Q830 — When a raw history is too large to reuse directly, what representation should carry forward?

- **DECISION:** Typed extracted facts (`Q33`). Not a 3–5 sentence summary, not success/failure patterns, not a trajectory embedding.
- **BECAUSE: POSITION.** `P§4`'s unit, and `Q704` removes the success state.
- **REJECTED:** A short LLM summary plus success state plus an embedding. It wins for episodic case retrieval in agent tasks.
- **COST:** As `Q154`.
- **CONFIDENCE:** high

---

### Q834 — When experience comes from another model or actor, should it be shared, transformed, or isolated?

- **DECISION:** It never enters. There is no other actor whose experience could be seeded (`Q273`, `Q596`). **Out of scope** (`E1`).
- **BECAUSE: POSITION.** `P§1` principle 2 and `E1`.
- **REJECTED:** An actor/model-agnostic experience store seedable from other agents. Wins for transferable agent skills.
- **COST:** As `Q273`.
- **CONFIDENCE:** high

---

### Q835 — At what point in an ongoing task should remembered experience be consulted?

- **DECISION:** Once per request, before tool selection and generation. Not after every step — there are no multi-step tasks (`Q244`, `Q252`).
- **BECAUSE: ENGINEERING (E5).** Position is silent; this follows from the narrow tool set.
- **REJECTED:** Retrieving after every environment step. Wins in long agent loops; cost would dominate the reported figures.
- **COST:** A request whose right memory only becomes apparent mid-task cannot re-retrieve.
- **CONFIDENCE:** high

---

### Q840 — What should make memory change over time?

- **DECISION:** Three causes only: new user-authored evidence, a user action, and the clock (decay/expiry). Not accumulation of Kivi's own trajectories.
- **BECAUSE: POSITION.** `P§4` + `P§9` (`Q240`).
- **REJECTED:** Appending each completed self-trajectory, improving by accumulation. Wins for self-improving agents.
- **COST:** As `Q12`.
- **CONFIDENCE:** high

---

### Q845 — When the extractor interprets a unit, what surrounding material is it entitled to see?

- **DECISION:** The transcript itself and the entity list. Not previous messages, not application context (`Q516`, `Q342`).
- **BECAUSE: POSITION for the application-context exclusion** (`P§5`); **ENGINEERING for the previous-messages exclusion** (`Q08` idempotence).
- **REJECTED:** The previous four messages (two complete turns). It wins on anaphora resolution and is a modest, well-chosen window. This is the strongest specific alternative to my `Q516` decision, and the condition under which it wins is simply: if the corpus shows that anaphoric dictations are common and are being lost. **That is a measurable condition and should be measured**, because if it holds, the idempotence argument is worth less than the recall it costs.
- **COST:** As `Q516` — anaphoric and deictic dictations extract poorly.
- **CONFIDENCE:** medium

---

### Q846 — Who is a legitimate subject of memory?

- **DECISION:** The user, and only the user. Other people appear only as role-attributed entities in the user's world (`Q55`, `Q61`).
- **BECAUSE: POSITION.** `P§1` principle 2, `P§5`.
- **REJECTED:** "Everyone: always the speaker first, plus other significant entities, concepts, or actors mentioned." It wins for a general knowledge graph. It is the position's direct antagonist.
- **COST:** As `Q61` — and note the honest qualification from `Q55`: entities *are* subjects in a limited sense, so "only the user" is a simplification the product's copy should not overstate (**Section B, conflict B1**).
- **CONFIDENCE:** high

---

### Q849 — Is the relation vocabulary closed?

- **DECISION:** Closed for memory relations (four types, `Q362`). For **entity-to-entity** relations, a small closed vocabulary fixed at build time — *works-at*, *client-contact-for*, *works-on*, *owns*, *part-of* — extended only by code change, never generated ad hoc by the model.
- **BECAUSE: ENGINEERING (E4), and POSITION indirectly.** `P§8`'s Why panel and `P§9`'s memory surface must render relations in plain language; an open vocabulary means the UI cannot know how to phrase them. The position is silent on the vocabulary itself, so the primary force is engineering.
- **REJECTED:** LLM-generated ad hoc relation types (the surveyed answer). It wins on expressiveness and captures relations a fixed list misses. It produces a graph that cannot be rendered consistently or queried reliably, and near-synonym relations proliferate.
- **COST:** Relations outside the five are flattened or lost. The vocabulary is a guess made before the corpus exists, and `P§AppA`'s world is small enough that it may not generalise to the reviewer's corpus.
- **CONFIDENCE:** medium

---

### Q850 — Is there a level of abstraction above individual entities?

- **DECISION:** No. No community nodes, no cluster summaries, no aggregate profile (`Q378`, `Q399`, `Q784`).
- **BECAUSE: POSITION.** `P§2`'s refusal of the aggregate profile, and `P§4`'s two flat axes.
- **REJECTED:** Dynamically maintained community nodes with high-level summaries. It wins for global-question answering over a large graph — genuinely the strongest technique for "summarise what you know about X." It produces model-authored summaries that carry no tier and cannot be corrected (`Q33`).
- **COST:** Global questions are answered by composing individual memories or not at all. "Tell me about Atlas" is a hard query for this system.
- **CONFIDENCE:** high

---

### Q852 — What happens to candidates the extractor considered and rejected?

- **DECISION:** A reason-coded, non-content drop log row per rejected candidate, surfaced in the transcript's inspection view (`Q16`, `Q199`).
- **BECAUSE: POSITION.** `P§2`: "Dropped candidates are logged with the reason… This is how we prove the boundary is real rather than claimed. It is also, honestly, the most interesting thing to show a reviewer." `P§AppC` claim 1.
- **REJECTED:** "They vanish; no drop log exists" (the surveyed answer, and the field default). It wins on privacy purity (`Q199`) and on simplicity. It makes claim 1 unprovable.
- **COST:** As `Q199`, **Section B, conflict B3**.
- **CONFIDENCE:** high

---

### Q859 — How much context is returned?

- **DECISION:** A configured top-k, uniform across queries, with budget drops reported (`Q562`, `Q708`). The value of k is unset pending corpus data (`Q469`) — see **Section A**.
- **BECAUSE: ENGINEERING**, with the parameter deferred by **POSITION** (`P§AppB`: parameters "need corpus data before they can be set honestly").
- **REJECTED:** Query-adaptive context size. It wins on efficiency and quality — a simple entity lookup needs one memory, a distributed-evidence question needs ten. It loses for now on `E5`, and the adaptive version is the obvious first upgrade once the corpus exists.
- **COST:** Uniform k is wrong for both extremes: wasteful on simple queries, insufficient on distributed-evidence ones, which is exactly the case the brief tests.
- **CONFIDENCE:** medium

---

## Stage: REPRESENTATION

---

### Q14 — Should memories carry epistemic status—stated, observed, hypothesised—or be treated uniformly?

- **DECISION:** Yes. Every memory carries `tier ∈ {stated, observed, hypothesised}` as a required column with defined permissions attached. Nothing is treated uniformly.
- **BECAUSE: POSITION.** `P§4`, the whole section, and specifically: "A **stated preference** — 'always sign my client emails Best' — is a rule. An **observed preference** — never once used a bullet list in fourteen client emails — is a pattern… The difference between those two is the entire product." This is not a decision the position permits going either way.
- **REJECTED:** Uniform treatment with a scalar importance/salience — the position taken, in various forms, by all five surveyed camps. It wins on every efficiency and simplicity axis, and it is what the entire field does. It loses because `P§4` identifies uniform treatment as the origin of both product failures: "either nags about things you've settled or silently enforces things you never agreed to."
- **COST:** Tier must be assigned at extraction by a model, which makes a mis-tiering a permission bug rather than a quality bug (`Q572`). Three tiers also means three surfacing behaviours, three decay rules, and three explanations for the user to absorb.
- **CONFIDENCE:** high

---

### Q17 — What should be the primary representation of long-term memory: raw interaction history, atomic structured memories, a narrative model, or a hybrid?

- **DECISION:** A constrained hybrid with a strict division of labour: **atomic structured memories are the memory**; **raw interaction history is the provenance substrate**; there is no narrative model. The two stores never mix in retrieval, and only the atomic store is "memory" in any user-facing sense.
- **BECAUSE: POSITION.** `P§4` fixes the atomic schema; `P§9` fixes the raw substrate ("the actual transcript, with a date"); `Q33` rules out narrative because a narrative has no tier and cannot be individually corrected.
- **REJECTED:** A three-level narrative memory card (theme → topic → thread), which is the strongest of the surveyed alternatives because it solves the navigation problem `Q784` and `Q399` leave open. It wins if the memory surface proves unusable as three flat lists — a plausible outcome that the position does not address.
- **COST:** Two stores with different rules (`Q141`), no narrative layer (`Q154`), and an unsolved navigation problem at scale.
- **CONFIDENCE:** high

---

### Q44 — What should the user be shown about memory use, withholding, and provenance in each answer?

- **DECISION:** An expandable trace — the Why panel — on every Hey Kivi response, showing four things: what was retrieved, what was withheld and why, what was used in the answer, and one tap to the source transcript behind each memory. It exists for abstentions too. It is the same surface the engineer uses; there is no second view.
- **BECAUSE: POSITION.** `P§8`, verbatim: "Every Hey Kivi response carries an expandable trace showing: what was retrieved, what was withheld and why, what was used in the answer, and the source transcript behind each memory, one tap away. This is simultaneously the user's trust mechanism and the engineer's inspection tool." And: "The trace exists for abstentions too."
- **REJECTED:** Claiming interpretability without building a user-facing surface (what both surveyed sources do — "the paper claims interpretability/auditability, but no end-user trace… is specified"). It wins on build cost, and it is the near-universal outcome. The brief forecloses it: "The product should begin and end in an interface intended for a normal user."
- **COST:** The trace is a substantial UI surface with real design difficulty — it must be legible to a normal user while carrying engineering detail (`Q405`). And it has nowhere to put genuinely developer-only diagnostics (**Section A**).
- **CONFIDENCE:** high

---

### Q48 — Should the system distinguish what the user stated, what the system observed, and what it hypothesizes?

- **DECISION:** Yes. Duplicate of `Q14` in substance; restated because the inventory poses it separately and both surveyed sources answer no.
- **BECAUSE: POSITION.** `P§4`, and `P§9`'s memory surface grouping: "*Things you told me. Things I've noticed. Things I'm wondering about.*"
- **REJECTED:** No explicit epistemic distinction, with all insights entering one stream after a New/Redundant/Updated classification. It wins on pipeline simplicity. It is the field's default and the position's antagonist.
- **COST:** As `Q14`.
- **CONFIDENCE:** high

---

### Q65 — How should relative time be normalized, and where should temporal reasoning occur?

- **DECISION:** Normalise at **write time** to an absolute ISO-8601 `event_time`, resolved against the transcript's own `occurred_at`. If the expression cannot be resolved confidently, fall back to the transcript time and record that the event time is approximate. Temporal reasoning at query time operates on absolute times only; the model is never asked to interpret "next Tuesday" during an answer.
- **BECAUSE: ENGINEERING (E2, `Q08`).** Position is silent on time normalisation. Query-time resolution would make the same memory resolve differently on different days, which breaks idempotence and makes the trace non-reproducible. `P§9`'s decay also needs absolute times to compare against a window.
- **REJECTED:** Keeping relative expressions and instructing the answer model to convert them at query time. It wins on extraction simplicity and avoids baking in a wrong parse. It loses on reproducibility, which the brief's reviewer-run evaluation depends on.
- **COST:** A wrong parse at write time is permanent and silently misplaces an episode (`Q799`). The approximate-time flag is a mitigation, not a fix, and it needs to be visible on the memory surface.
- **CONFIDENCE:** high

---

### Q42 — How should uncertain interpretations be encoded and expressed: claims with confidence, observations with evidence, questions, or not stored at all?

- **DECISION:** All three of the last three, by kind, and never the first. A pattern → an **observation with evidence** (count and sources). A proposed reason → a **question**, stored as a question, expiring, never asserted. A failed or ambiguous extraction → **not stored** (`Q152`). No confidence scores anywhere.
- **BECAUSE: POSITION.** `P§4`: "Hypotheses are stored as questions, never as claims. Not `user_disagrees_with_pricing: true`. Instead: `'Does the user disagree with the Atlas pricing rationale?' — unconfirmed`. The grammar of storage enforces the epistemics. You cannot accidentally use a question as a fact."
- **REJECTED:** Claims with confidence scores. It wins on ranking, on graded hedging, and on being able to represent "probably true" — which is a real epistemic state this system cannot express. See `Q444`/`Q537`.
- **COST:** No representation of partial belief. A fact Kivi is 80% sure of must be stored as a confident fact or not at all, and the tier system does not capture the difference.
- **CONFIDENCE:** high

---

### Q63 — What shape must a memory take to be storable?

- **DECISION:** A short, human-readable natural-language sentence in `content`, plus required typed metadata (`Q800`), plus — for entity memories — explicit typed relation rows. Not *either* a sentence *or* triples: a sentence for the human, structured fields for the system, and triples only for entity relations.
- **BECAUSE: POSITION.** `P§9`'s memory surface shows entries to a normal user, so the payload must read as a sentence. `P§4`'s schema supplies the fields. `P§4`'s entity definition ("and the relations between them") supplies the triples, for entities only.
- **REJECTED:** Triples throughout (Mem0g-style). It wins on queryability and on precise merging. It loses because a triple cannot be shown to a user as a belief, and `P§9` requires exactly that.
- **COST:** As `Q552` — the same fact exists as prose and as fields, and a correction can update one without the other.
- **CONFIDENCE:** high

---

### Q71 — What is the observation schema?

- **DECISION:** An observation is an ordinary memory row with `tier = observed`, carrying `type`, `content` (the pattern stated plainly), `evidence_count`, `source_transcript_ids[]` (every instance), `first_seen_at`, `last_seen_at`, and `status`. No separate observation schema, no narrative field, no concept list, no token counts.
- **BECAUSE: POSITION.** `P§4` gives one schema across tiers: "Schema carries `type`, `tier`, `content`, `evidence_count`, `source_transcript_ids[]`, `first_seen_at`, `last_confirmed_at`, `status`." One schema is what makes promotion a tier change rather than a migration.
- **REJECTED:** A richer observation-specific schema with narrative, concepts, and agent identity. It wins for an observer product logging agent sessions. Here a separate shape would make `observed → stated` promotion a conversion rather than a field update.
- **COST:** Observations carry no room for the *shape* of the pattern (frequency, period, exceptions) beyond a count and a sentence. "You always do X on Fridays" and "You did X fourteen times" are stored identically.
- **CONFIDENCE:** medium

---

### Q82 — Who owns identity?

- **DECISION:** There is one user identity, implicit and singular (`E1`). Identities that do exist and matter: `transcript_id`, `memory_id`, `entity_id`, `extraction_run_id`. No team, project, platform, or agent identity dimensions.
- **BECAUSE: ENGINEERING (E1).** Position is silent; the single-user scope removes the question.
- **REJECTED:** A multi-dimensional identity model. It wins for a multi-tenant product and is the natural extension. Adding it later means a user dimension on every table.
- **COST:** No multi-tenancy path without a schema-wide migration.
- **CONFIDENCE:** high

---

### Q87 — Is a memory a typed document, a normalized claim graph, or an event/evidence structure?

- **DECISION:** An **event/evidence structure**: a typed claim with an explicit evidence set pointing at sources, plus a small entity graph beside it. Not a free-text document with metadata, and not a fully normalised claim graph.
- **BECAUSE: POSITION.** `P§4`'s `evidence_count` + `source_transcript_ids[]` make evidence structural rather than annotative; `P§9` makes the evidence user-visible ("Each entry shows evidence count and the last date it was seen. Tapping shows the source transcripts").
- **REJECTED:** A typed free-text document with metadata (the Engram answer). It wins on flexibility and on not needing to decide the claim shape. It cannot carry evidence as first-class structure, so `P§9`'s per-entry evidence display becomes a derived query rather than a stored fact.
- **COST:** Evidence links must be maintained through merges and supersessions correctly, or the displayed count is wrong — a visible, embarrassing failure mode.
- **CONFIDENCE:** high

---

### Q88 — Should changing knowledge update one stable topic, append a new claim, or create an explicit supersession edge?

- **DECISION:** An explicit supersession edge. The old row stays with `status = superseded` and a `superseded_by` pointer; the new row is current. Not in-place update with a revision counter.
- **BECAUSE: POSITION.** `P§9`: "the superseded version stays in history so the change is auditable." A revision counter records that something changed, not what it was.
- **REJECTED:** In-place update of the most recently matching row with a revision count (the surveyed answer). It wins on storage and on read simplicity — always one row per topic. It loses `P§9`'s audit.
- **COST:** Every read of "current truth" must filter by status (`Q672`), and forgetting a status filter anywhere produces duplicate contradictory answers — the most likely correctness bug in the retrieval layer.
- **CONFIDENCE:** high

---

### Q100 — Is confidence/salience a scalar, a category, or absent?

- **DECISION:** Absent as confidence. Present as a **category** in the form of `tier`, which is not confidence — it is permission and provenance class. There is no importance score.
- **BECAUSE: POSITION.** `P§4`: "memory has two independent axes — what kind of thing it is, and how confident we're entitled to be. Collapsing them into one is where most memory systems go wrong." A scalar importance assigned "by the model from a one-line instruction" (the surveyed answer) is precisely the collapse.
- **REJECTED:** A scalar importance field. It wins for ranking and for eviction (`Q54`, `Q681`), both of which this system now lacks a signal for. It is rejected on `P§4` and on the specific worry that an importance score is a judgement about the user's priorities.
- **COST:** No importance signal for ranking or for surfacing. Evidence count and recency carry all the weight, and neither captures "this one matters."
- **CONFIDENCE:** high

---

### Q101 — Where do relations live — in the schema or in the text?

- **DECISION:** In the schema, as typed rows with a closed vocabulary (`Q849`, `Q362`). Never in a JSON blob and never implicit in the content sentence.
- **BECAUSE: POSITION.** `P§4`: entity memory is "a person, project, company, channel, or artefact… **and the relations between them**." A relation in text cannot be traversed, corrected individually, or shown in the Why panel.
- **REJECTED:** A JSON blob appended to both edge endpoints (the surveyed answer). It wins on write simplicity; it duplicates state at two endpoints, which is a guaranteed divergence bug.
- **COST:** Relation extraction must produce a typed edge, and edges outside the closed vocabulary are lost (`Q849`).
- **CONFIDENCE:** high

---

### Q113 — Is a memory primarily free text in an addressable graph, or a typed epistemic claim with evidence?

- **DECISION:** A typed epistemic claim with evidence.
- **BECAUSE: POSITION.** `P§4`'s schema, including `tier` and `evidence_count`. The surveyed alternative is described as having "no semantic type/tier/evidence/provenance/status fields" — that is, it lacks every field the position names.
- **REJECTED:** Free text plus graph placement metadata. It wins where placement carries the meaning (a wiki, a file tree). Here meaning is in the typed fields.
- **COST:** As `Q86`/`Q465` — extraction must produce structure and fails more often than producing prose.
- **CONFIDENCE:** high

---

### Q114 — Is the stable identity the claim, its location, or an underlying concept independent of both?

- **DECISION:** Split. For **memories**, stable identity is the claim: a memory id whose content may be corrected and whose status may change, but which does not survive supersession (a superseded memory keeps its own id; the replacement gets a new one). For **entities**, stable identity is an underlying concept independent of its name: an entity id with a canonical name and aliases, surviving rename.
- **BECAUSE: POSITION.** `P§9` requires per-entry actions on memories, which requires memory identity. `P§7` requires canonical spellings with variants resolving to one thing, which requires entity identity independent of the string. `P§8`'s inline correction — "*No, Priya's at Northwind now*" — changes an entity's relation without changing who Priya is.
- **REJECTED:** One uniform identity model. It wins on conceptual economy. Entities and claims genuinely behave differently under change, and forcing one model would either make entity renames destructive or make memory supersession invisible.
- **COST:** Two identity models to reason about, and the boundary case — does correcting a memory's content create a new id? — has to be decided consistently. Here: `Correct` keeps the id and writes a superseded snapshot; new contradicting *evidence* creates a new row. That distinction is subtle and will be got wrong at least once.
- **CONFIDENCE:** medium

---

### Q127 — At what granularity should context be represented?

- **DECISION:** One transcript for extraction (`Q480`); one memory per discrete typed fact for storage (`Q547`); a per-request assembled bundle for generation (`Q255`). Three granularities, each fixed, each for a different stage.
- **BECAUSE: POSITION.** `P§9` (transcript provenance) and `P§4` (fact unit); the request bundle is `ENGINEERING` from `E4`.
- **REJECTED:** A single uniform granularity across all three stages. It wins on conceptual simplicity and loses on all three stages' actual requirements.
- **COST:** Three units to keep aligned. A memory's provenance must point at a transcript and a trace must point at both.
- **CONFIDENCE:** high

---

### Q129 — What representation should initialize lexical meaning and participant roles?

- **DECISION:** The entity table, loaded before extraction and before dictation formatting. It carries canonical names, aliases, type, and role relations, and it is the only thing the dictation path may read besides stated formatting preferences (`Q270`).
- **BECAUSE: POSITION.** `P§7`: "Names, project nouns, spellings, product terms, and formatting preference. It exists to make transcription *accurate*, and nothing else. *Atlas*, not *Atlus*. *Priya Raghavan*, not *Prea Raghavan*. *Acme*, capitalised."
- **REJECTED:** A learned lexical model or a general embedding-based normaliser. It wins on generalisation to unseen names. `P§7` asks for a lexicon, which an explicit table is, exactly.
- **COST:** The lexicon only contains what extraction has already learned. A name Kivi has never seen is spelled however ASR spelled it, on first use and possibly forever.
- **CONFIDENCE:** high

---

### Q145 — What is confidence, and who is permitted to set it?

- **DECISION:** There is no confidence field, so nobody sets it (`Q100`, `Q42`, `Q537`). The nearest thing is `tier`, set by the extractor at write time and changed only by a recorded user confirmation or by decay/expiry — never by a caller, never by an API parameter.
- **BECAUSE: POSITION.** `P§4`'s tier table and its promotion rule ("requires an explicit user confirmation event").
- **REJECTED:** A caller- or extractor-supplied scalar with a default and numeric filtering (the surveyed answer). It wins on flexibility. Note the surveyed system's specific flaw — "unknown legacy confidence fails open" — which is a good illustration of why a scalar with defaults is dangerous: an absent value silently becomes an admitting one.
- **COST:** As `Q42` — no partial belief.
- **CONFIDENCE:** high

---

### Q149 — Is observation frequency allowed to become authority?

- **DECISION:** No, and the boundary is enforced, not merely unimplemented. Evidence count affects ranking and decay resistance only (`Q682`). The tier boundary is a checked invariant: no code path changes `observed → stated` except the confirmation handler.
- **BECAUSE: POSITION.** `P§4`: "Nothing self-promotes. An observation does not become stated because it was seen twenty times. It becomes stated when the user confirms it. Twenty is still a pattern."
- **REJECTED:** No enforced tier boundary — which is the surveyed system's actual state ("no automatic promotion mechanism exists, but neither is there an enforced tier boundary"). That is the dangerous middle: correct today by accident. The enforcement is cheap and is what makes the claim durable.
- **COST:** As `Q191` — the stated tier stays small.
- **CONFIDENCE:** high

---

### Q156 — Should schema evolution be explicit/versioned or opportunistic at startup?

- **DECISION:** Explicit, versioned, ordered migrations committed to the repository, applied by a documented command. No opportunistic column probing at startup.
- **BECAUSE: ENGINEERING (E2).** The brief requires "the database schema and migrations" as a submission artefact and "the exact commands to create, migrate, and seed the database." Opportunistic migration cannot be a documented command.
- **REJECTED:** Catch-tolerant column probes with additive alterations (the surveyed answer). It wins for a shipped desktop app upgrading in the field across unknown versions. It loses the reviewer's reproducibility requirement outright.
- **COST:** Every schema change is a migration file, including during rapid development.
- **CONFIDENCE:** high

---

### Q164 — Should session identity be a hard filter, a soft feature, or merely provenance?

- **DECISION:** Merely provenance. Transcript and trace identity are recorded; nothing filters or ranks by session (`Q250`). Retrieval sees all memories regardless of which session produced them.
- **BECAUSE: POSITION.** `P§6`: "Kivi always retrieves everything it has." A session filter would be an invisible restriction on retrieval, which is exactly what the withheld/never-retrieved distinction depends on not existing.
- **REJECTED:** Session as an optional hard filter with cross-session recall enabled by host integration (the surveyed answer). It wins for multi-workspace products where leakage between contexts is the concern. `E1` removes the concern.
- **COST:** No way to scope a question to a project context automatically. Everything is one pool, and entity filtering is the only scoping mechanism.
- **CONFIDENCE:** high

---

### Q165 — Should the caller receive raw evidence, summaries, scores, provenance, or only injected prose?

- **DECISION:** All of it except summaries: the retrieved memories with their tier, evidence count, score components, source ids, and status; plus the withheld set with reasons; plus the search description. Never collapsed into a formatted prose block before the caller sees it.
- **BECAUSE: POSITION.** `P§8`'s four trace requirements and `P§6`'s withheld-count display cannot be satisfied if retrieval returns prose. This is the same decision as `Q388`, stated from the caller's side.
- **REJECTED:** Collapsing hits into a formatted injection section (which is what the surveyed system does *in addition to* exposing structured results — the collapse happens at prompt-build time). Collapsing at prompt-build time is fine and necessary; collapsing at the retrieval API is not.
- **COST:** A wide retrieval contract and a prompt-builder that must faithfully represent what it collapsed, or the trace and the prompt disagree.
- **CONFIDENCE:** high

---

### Q172 — Is there any bi-temporal modelling?

- **DECISION:** Yes, and it is required rather than incidental: **event time** (when the thing happened, from the content) and **system time** (`first_seen_at`, `last_confirmed_at`, `last_seen_at`) are separate fields with separate uses (`Q799`). Decay uses system time; answers use event time; supersession ordering uses event time (`Q667`).
- **BECAUSE: POSITION.** `P§4`'s schema names two system-time fields; `P§4`'s episode example carries an event time; `P§9`'s decay window is a system-time window ("not re-observed within a window").
- **REJECTED:** Single-timestamp modelling. It wins on simplicity and is what most systems do. It cannot express "you told me last week about something that happened in March," which `P§AppA`'s corpus will contain.
- **COST:** Two time axes to reason about, and every temporal query must specify which. Getting this wrong produces answers that are subtly, confidently wrong about when things happened.
- **CONFIDENCE:** high

---

### Q187 — What representation is primary: events, typed claims, entity graph, or epistemic assertions?

- **DECISION:** Typed claims carrying epistemic tier are primary. The entity graph is secondary and exists to serve naming, relations, and retrieval expansion. Events are one of the three claim types, not a separate representation.
- **BECAUSE: POSITION.** `P§4` puts type and tier on one record; entities are one *value* of type, not a parallel structure. `P§4`'s entity row happens also to need a graph, which is why the graph exists at all.
- **REJECTED:** An entity graph as primary, with claims hanging off it. It wins for relationship-heavy domains and gives better multi-hop retrieval (`Q752`). It loses because preferences — which are the product's most valuable memory type — have no natural place in an entity graph.
- **COST:** Multi-hop retrieval is weak (`Q752`).
- **CONFIDENCE:** high

---

### Q188 — Is provenance a mutable annotation or immutable trust-boundary fact?

- **DECISION:** An immutable trust-boundary fact. `source_transcript_ids[]` may be **appended to** as new evidence arrives, but an existing link is never removed or rewritten, and the transcript it points at is immutable. A memory cannot exist without at least one (`Q86`).
- **BECAUSE: POSITION.** `P§9`: "Every memory shows its provenance. Not a category label — the actual transcript, with a date, that produced it." `P§3`: trust comes "because every belief is attributable."
- **REJECTED:** Mutable provenance annotations. It wins for merge and cleanup operations, where a link to a transcript that no longer supports the merged claim is arguably wrong. That case is real: after a bad merge is corrected, some links are stale. The answer is that the correction creates new rows rather than editing links.
- **COST:** Bad merges leave stale links until corrected by re-extraction, and there is no in-place repair.
- **CONFIDENCE:** high

---

### Q193 — What is ordered first: relevance, recency, confidence, diversity, or authority?

- **DECISION:** Relevance first (fused lexical+vector rank), then **authority** (tier), then evidence, then recency. No confidence (none exists), no diversity (`Q561`). Authority is a re-rank over the relevant set, not a pre-filter — a stated memory that is irrelevant does not outrank a relevant observation.
- **BECAUSE: ENGINEERING for the mechanism, POSITION for authority's presence and placement.** `P§4`'s tier permissions make tier an ordering input; placing it after relevance rather than before is `ENGINEERING` — a tier-first ordering would return stated memories about unrelated topics.
- **REJECTED:** Authority-first ordering. It wins if precision on stated facts is the dominant concern and retrieval relevance is unreliable. It fails obviously on any query about something Kivi has only observed.
- **COST:** A highly relevant hypothesis can outrank a moderately relevant stated fact within the retrieved set, and only the disclosure filter prevents that being a problem. The ordering and the permission filter are doing separate jobs that must not be confused.
- **CONFIDENCE:** medium

---

### Q201 — Normalized claim/evidence records or flexible documents?

- **DECISION:** Normalised claim/evidence records (`Q87`, `Q113`).
- **BECAUSE: POSITION.** `P§4`'s schema; `P§7`'s schema-enforceable path separation.
- **REJECTED:** A typed envelope with open frontmatter. It wins on extensibility and is a reasonable middle ground. The open half is where untyped state accumulates and the structural claims quietly stop being true.
- **COST:** As `Q142` — no room for a fact that does not fit.
- **CONFIDENCE:** high

---

### Q214 — When causality is represented, should a cause–effect relation remain a binary edge or become a relation with internal structure and metadata?

- **DECISION:** Causality is not represented at all (`Q215`). **Out of scope.**
- **BECAUSE: POSITION.** `P§4`: hypotheses are stored as questions, "Never assert. Never act on." A structured causal relation is an asserted causal claim.
- **REJECTED:** A hyper-relational representation carrying treatment, mediator, outcome, and effect values. Wins in a causal-analysis product.
- **COST:** As `Q215` — Daari's hypotheses have no structure behind them.
- **CONFIDENCE:** high

---

### Q216 — Which roles should the causal schema make primitive?

- **DECISION:** Not applicable — no causal schema (`Q214`).
- **BECAUSE: POSITION.** `P§4`.
- **REJECTED:** Treatment/mediator/outcome primitives. Wins in a causal product.
- **COST:** None here.
- **CONFIDENCE:** high

---

### Q221 — What information should be discarded before or after representation?

- **DECISION:** Before representation: excluded categories and third-party personal content, at the candidate check (`Q20`). After representation: nothing — no post-hoc minimisation, because the gates already ran and anything that passed is permitted.
- **BECAUSE: POSITION.** `P§2`: the check runs "on candidate memories… before anything reaches storage." That places the discard unambiguously before representation.
- **REJECTED:** A post-representation minimisation pass. It wins as a second line of defence against classifier errors — and `Q73` notes that there deliberately is no second line. A post-hoc pass is the cheapest one available and I am declining it because it would make the boundary's location ambiguous, which is what `P§5` insists it must not be.
- **COST:** A classifier false negative is unrecoverable (`Q73`).
- **CONFIDENCE:** medium

---

### Q225 — Should a stored causal claim carry provenance, uncertainty, scope, and validity time, or only relation/effect metadata?

- **DECISION:** Not applicable — no causal claims. The general rule that does apply: every stored claim carries provenance (required), tier (in place of uncertainty), and event time; scope and validity period are not modelled.
- **BECAUSE: POSITION.** `P§4` + `P§9`.
- **REJECTED:** Effect-metadata-only representation. Wins nowhere here; noted because the surveyed system's gap — provenance underspecified — is the single most common gap in the inventory and the one this position most directly closes.
- **COST:** No validity period on facts. "Priya is the Acme contact" has no end date until something supersedes it.
- **CONFIDENCE:** medium

---

### Q228 — When evidence is absent, causal structure is incomplete, or confidence is low, should the system answer, qualify, abstain, or ask?

- **DECISION:** Abstain, and show what was searched — never answer, never qualify a guess into acceptability. Ask only within the budgeted confirmation mechanism, never as a substitute for abstaining.
- **BECAUSE: POSITION.** `P§8`: "Kivi says what it doesn't have, and shows what it looked for. Not 'I'm not sure' — that's a shrug." And: "Kivi never fills a gap with a plausible guess."
- **REJECTED:** Qualified answering ("I'm not certain, but…"). It wins on usefulness and is what most assistants do. `P§8` names it: a hedge is still an answer the user may act on, and it is "indistinguishable from a real one until it costs you something."
- **COST:** Kivi abstains in cases where a hedged answer would have helped. Users may find it unhelpfully strict.
- **CONFIDENCE:** high

---

### Q230 — What should change over time: parameters, topology, ontology, effect estimates, or retained claims?

- **DECISION:** Only the standing of retained claims (`Q773`). Not parameters (frozen model), not topology, not ontology (`Q142` fixes it), not estimates (none exist).
- **BECAUSE: POSITION.** `P§9`'s two time mechanisms, and `P§4`'s fixed ontology.
- **REJECTED:** Ontology evolution. It wins if the corpus reveals a fourth durable type (`Q142`) — a live risk flagged in **Section A**.
- **COST:** A fixed ontology that may not fit the reviewer's corpus.
- **CONFIDENCE:** medium

---

### Q279 — What information must be retained as provenance so later access and accountability decisions remain possible?

- **DECISION:** Per memory: the source transcript ids (immutable), the extraction run id, the extractor model and version, `first_seen_at`, `last_confirmed_at`, and every tier-change event with its timestamp and cause (user confirmation / decay / expiry / supersession). Per answer: the full trace. Not "contributing agents" or "resources accessed" — there are none.
- **BECAUSE: POSITION.** `P§4`'s schema plus "Promotion requires an explicit user confirmation event, which is itself recorded with a timestamp"; `P§9`'s audit requirement.
- **REJECTED:** A lighter provenance record without the tier-change event log. It wins on write cost. It would make the promotion timestamp unverifiable, which is the one thing `P§4` says must be recorded about promotion.
- **COST:** An event log per memory. Storage grows with interaction, and the memory surface must decide how much of it to show without becoming a database view.
- **CONFIDENCE:** high

---

### Q296 — F2 — Current graph + provenance determines eligibility (D02–D03)

- **DECISION:** Not adopted as posed. Eligibility to *retrieve* is unconditional (`P§6`); eligibility to *disclose* is determined by tier and the dial, not by a graph or an access matrix. There is no access-control layer and no revocation mechanism, because there is one user (`E1`).
- **BECAUSE: POSITION.** `P§6`: "The dial governs disclosure, not retrieval." That replaces the access-matrix framing entirely.
- **REJECTED:** Graph-plus-provenance access eligibility with revocation. It wins in a multi-actor system where different readers have different rights. The one place it would matter here — a memory the user has forgotten — is handled by suppression and purge instead (`Q622`).
- **COST:** No access model to extend if Kivi ever gains a second reader.
- **CONFIDENCE:** high

---

### Q308 — When an inference combines several past and present items, should it preserve the supporting sources and derivation?

- **DECISION:** Yes, both. An observation records every source transcript that evidenced it. An **answer** records every memory used and, through those, every transcript — this is the Why panel's "what was used in the answer" plus "the source transcript behind each memory."
- **BECAUSE: POSITION.** `P§8`'s trace contract, and `P§AppC` claim 3: "A memory was assembled from evidence distributed across multiple separate dictations." That claim is only provable if the derivation is preserved.
- **REJECTED:** Passing retrieved memories to the model without stored derivation records (the surveyed answer — "underspecified"). It wins on write cost. It makes claim 3 a story rather than a demonstration.
- **COST:** The trace must be persisted per answer, not just rendered, so that the evaluation can inspect it after the fact. That is a growing table the brief's "database growth" metric will reflect.
- **CONFIDENCE:** high

---

### Q315 — How should candidate memories be ranked, and should recency, source authority, epistemic tier, risk, or user pinning alter semantic similarity?

- **DECISION:** Yes to tier, evidence, recency, and **pinning**; no to risk. Order: fused relevance → pinned first → tier → evidence → recency (`Q193`). Pinning is an explicit user action that forces a memory into the retrieved set when relevant.
- **BECAUSE: POSITION.** `P§9`: "Everything is editable, **pinnable**, or removable." Pinning is named as a user action and has to mean something in retrieval or it is decoration.
- **REJECTED:** Pure dense retrieval with a fixed top-k per query (the surveyed answer). It wins on simplicity and on not needing tuned weights. It has no place for tier or for pinning, both of which the position requires.
- **COST:** Pinning is a user lever that can distort results, and a user who pins liberally will crowd out relevance. Needs a cap, which is another unset parameter (**Section A**).
- **CONFIDENCE:** medium

---

### Q324 — Should repeated observation automatically become a stronger belief or require explicit user confirmation before changing epistemic status?

- **DECISION:** Explicit user confirmation, always (`Q191`, `Q149`).
- **BECAUSE: POSITION.** `P§4`: "Nothing self-promotes."
- **REJECTED:** Automatic strengthening. See `Q191`.
- **COST:** As `Q191`.
- **CONFIDENCE:** high

---

### Q326 — What should retrieval optimize for: semantic relevance, narrative coherence, recency, epistemic authority, source type, or task-specific constraints?

- **DECISION:** Semantic relevance first, then epistemic authority and recency as re-rank (`Q193`). Not narrative coherence (no narrative), not source type (one source type), not task-specific constraints (the tool set is too small to specialise).
- **BECAUSE: ENGINEERING for the mechanics, POSITION for authority's inclusion.**
- **REJECTED:** Task-specific retrieval constraints — e.g. the draft tool weighting preferences, the recall tool weighting episodes. It wins on precision per tool and is a cheap improvement. It loses on `E5` for now and because it introduces a per-tool retrieval variation the trace must explain. This is a reasonable first upgrade.
- **COST:** One retrieval policy serves three tools with different needs.
- **CONFIDENCE:** medium

---

### Q330 — What provenance should accompany a memory or answer: none, source links, evidence counts, transformation history, or a full response trace?

- **DECISION:** All four of the substantive options. Per memory: source links, evidence count, and transformation history (tier changes, supersessions). Per answer: a full response trace.
- **BECAUSE: POSITION.** `P§9` for the first three ("Each entry shows evidence count and the last date it was seen. Tapping shows the source transcripts"); `P§8` for the trace.
- **REJECTED:** Source links only. It wins on cost and covers the common case. It cannot show why a memory's standing changed, which is `P§9`'s audit requirement.
- **COST:** As `Q279`/`Q308` — significant stored metadata, reflected in database growth.
- **CONFIDENCE:** high

---

### Q331 — Should a user-visible system expose a coherent biography, atomic memories grouped by epistemic status, or only task outputs?

- **DECISION:** Atomic memories grouped by epistemic status. Three groups: *Things you told me / Things I've noticed / Things I'm wondering about.*
- **BECAUSE: POSITION.** `P§9`: "The memory surface is grouped by tier — *Things you told me / Things I've noticed / Things I'm wondering about* — because that grouping is what carries the epistemics to a normal user without a single word of explanation."
- **REJECTED:** A coherent biography. It is the most appealing interface of the three — it is what a user would most enjoy reading, and it would make the product feel like it understands them. `P§2` refuses it: that biography is the psychological profile, and reading it is exactly the moment a user discovers they have been studied.
- **COST:** The memory surface is a list, and at scale a long one (`Q784`, `Q399`). The product's most emotionally compelling possible screen is deliberately not built.
- **CONFIDENCE:** high

---

### Q332 — What should determine whether the system acts on a memory: relevance alone, epistemic tier, explicit confirmation, task risk, or user permission?

- **DECISION:** Relevance determines retrieval; **epistemic tier plus the permission dial** determine disclosure and use. Stated memories may be acted on. Observed memories may be mentioned under Koottu but never acted on. Hypotheses may be voiced under Daari and never acted on. Task risk is not modelled.
- **BECAUSE: POSITION.** `P§4`'s tier table column "What Kivi may do with it" — "Use freely" / "Never as a rule" / "Never act on." And `P§6`'s dial.
- **REJECTED:** Relevance alone, which is what a system without tiers does by default. It wins on usefulness per retrieval. It is the "silently enforces things you never agreed to" failure.
- **COST:** Kivi's actions are driven only by the stated tier, which is small (`Q191`). Most of what Kivi knows can never change what it does.
- **CONFIDENCE:** high

---

### Q341 — What unit of state should receive a consistency guarantee: raw interactions, extracted semantic facts, embeddings, graph nodes/edges, task checkpoints, or a compound record?

- **DECISION:** The compound write — transcript, its extracted memories, its entity updates, and its drop-log rows — commits as one transaction. Embeddings are outside it (`Q148`). No other unit needs a guarantee (`Q339`).
- **BECAUSE: ENGINEERING (E2, E4).** Position is silent. The compound boundary is chosen so that a transcript is never half-processed in a way the drop log would misreport — a partially-written transcript would make the "3 extracted, 1 dropped" display wrong, and that display is `P§2`'s proof.
- **REJECTED:** Per-row commits. It wins on write granularity and crash recovery. It would allow a state where memories exist without their drop log.
- **COST:** A long transaction per transcript during import; embeddings fall outside it and need repair (`Q148`).
- **CONFIDENCE:** high

---

### Q344 — When content changes, should the semantic record and every derived retrieval index become visible atomically, or may they lag independently?

- **DECISION:** The record and the lexical index are atomic (same database, same transaction). The vector index may lag, and the lag is visible — a memory without a current embedding is marked and its retrieval is reported as lexical-only in the trace.
- **BECAUSE: ENGINEERING (E4), following `Q148`.** The position is silent, but the visibility requirement is `E4`: an unembedded memory is a memory that will not be found by paraphrase, which looks exactly like a memory that does not exist.
- **REJECTED:** Full atomicity including embeddings. It is the better design and is achievable by computing embeddings before the transaction; `Q148` explains why it loses (network latency inside a write transaction during a 500-record import).
- **COST:** A transient window where retrieval is degraded and the trace says so. The evaluation must not run during that window or its numbers are wrong.
- **CONFIDENCE:** medium

---

### Q351 — When retrieved memories differ in authority, certainty, or permission, should those distinctions affect retrieval, ranking, generation, or only disclosure?

- **DECISION:** Authority affects **ranking** (`Q193`) and **generation** (a stated fact is asserted, an observation is offered). Permission affects **disclosure only** — it never touches retrieval (`P§6`). Certainty is not modelled separately from tier.
- **BECAUSE: POSITION.** `P§6`: "The dial governs disclosure, not retrieval." `P§4`'s tier column governs use, which is generation.
- **REJECTED:** Letting permission affect retrieval. It is simpler and marginally safer (`Q268`). It destroys the withheld-count claim.
- **COST:** As `Q268` — wasted retrieval on Anbu requests, and withheld content held in process memory.
- **CONFIDENCE:** high

---

### Q360 — How should memories be represented so later conversation can use them?

- **DECISION:** As short natural-language sentences with typed metadata (`Q63`), single-subject (the user), with typed relations rather than binary similarity links (`Q749`).
- **BECAUSE: POSITION.** `P§9` (readable to a user), `P§4` (typed fields), `P§5` (no speaker partition — there is only one subject).
- **REJECTED:** Speaker-partitioned memory sentences with binary related-links. It is close on the sentence half and wrong on both the partition (forbidden by `P§5`) and the links (`Q749`).
- **COST:** As `Q749` — no associative recall.
- **CONFIDENCE:** high

---

### Q367 — When a memory is used, what should the user be told about its source, confidence, or withholding?

- **DECISION:** Everything, on demand, through the Why panel: which memories were used, their tier, their evidence, their source transcripts, and what was withheld and why. Not pushed into the reply text — the reply stays a reply; the trace is expandable.
- **BECAUSE: POSITION.** `P§8`'s trace contract, and `P§6`'s Anbu behaviour ("Says: the result. Nothing else"), which requires the explanation to live outside the reply.
- **REJECTED:** Nothing explicit, with memory incorporated naturally into the reply (the surveyed answer, and what almost every product does). It wins on conversational quality. It is incompatible with the entire trust argument in `P§3`.
- **COST:** Every response carries an affordance the user may never open, and designing it to be inviting rather than noisy is a real interface problem the position does not solve.
- **CONFIDENCE:** high

---

### Q369 — What changes over time: the memory, its confidence, its availability, or only its connections?

- **DECISION:** Its **availability** (surfacing standing, via decay and expiry) and its **status** (via supersession and user action). Not its content except by explicit correction, not its confidence (none), not merely its connections.
- **BECAUSE: POSITION.** `P§9`'s mechanics.
- **REJECTED:** Accumulating sentences and links, with "updates" represented as relationships between old and new (the surveyed answer). It wins on auditability — nothing is ever superseded, only related. It loses because `P§9` says replacement, not relation, and because a system that only relates will state both versions (`Q361`).
- **COST:** As `Q361` — the dual retrieval semantics (current facts vs evidence history) must not leak.
- **CONFIDENCE:** high

---

### Q374 — Where is a conversational episode boundary decided: client, fixed size, or model?

- **DECISION:** By the client, structurally: a transcript is a transcript because the client submitted it as one. No boundary detection, no size forcing, no model segmentation.
- **BECAUSE: ENGINEERING (E3).** The corpus arrives as discrete records; the brief's format is "approximately 500 dictations," each a record. Inventing boundaries would be solving a problem the input does not pose.
- **REJECTED:** A model-based boundary detector with a token/message cap. It wins for continuous conversation streams. It would make `transcript_id` a derived rather than given identity, breaking `Q667`.
- **COST:** If the reviewer's corpus contains long multi-topic records, each becomes one unit and extraction quality on them is untested.
- **CONFIDENCE:** high

---

### Q379 — Should every belief carry source-level provenance?

- **DECISION:** Yes, uniformly and without exception, and it must be exposed uniformly through the API and the UI — not just stored (`Q188`, `Q518`).
- **BECAUSE: POSITION.** `P§9`: "Every memory shows its provenance."
- **REJECTED:** Storing parent/session ids without uniformly exposing transcript spans (the surveyed answer's actual state). It wins on API surface. Note the specific failure: provenance that exists in the database but not in the response DTO is provenance the product cannot show, which for this position is the same as not having it.
- **COST:** Every response payload carries provenance, and every UI surface must render it.
- **CONFIDENCE:** high

---

### Q393 — Are similarity scores comparable enough to drive confidence?

- **DECISION:** No, and nothing depends on their comparability. Scores are used only to produce per-leg *ranks*, which are fused by RRF (`Q209`) — rank fusion is chosen precisely because it needs no cross-leg score calibration. Raw scores are shown in the trace as diagnostics, never as confidence.
- **BECAUSE: ENGINEERING**, and reinforced by **POSITION** — `Q100`/`Q537` mean there is no confidence field for a score to drive even if it could.
- **REJECTED:** Treating hybrid scores as calibrated in [0,1] with a threshold (the surveyed answer, which is careful about which routes are calibrated). It wins when a single absolute relevance threshold is needed, e.g. for deciding "nothing relevant found." Here that decision is made by the top-k plus the abstention path, not by a threshold.
- **COST:** No absolute "is anything relevant?" signal. Top-k always returns k things, some of which may be irrelevant, and the generator must decide — which is a place a plausible guess could creep in and is worth an explicit evaluation case.
- **CONFIDENCE:** medium

---

### Q404 — How should architectural or structured facts be represented alongside narrative history?

- **DECISION:** As ordinary typed memories — entities with relations. There is no separate structured-metadata file and no narrative history to sit alongside.
- **BECAUSE: POSITION.** `P§4`'s three types are meant to cover the user's world; `P§AppA`'s cast (people, projects, surfaces) maps entirely onto entities and relations.
- **REJECTED:** A separate metadata file for structural facts. It wins for a coding agent where repository structure is genuinely a different kind of fact. Kivi's world has no analogue.
- **COST:** None obvious for this corpus; a risk if the reviewer's corpus contains structural facts that resist the three types (`Q142`).
- **CONFIDENCE:** high

---

### Q413 — When objects share labels, properties, or identities, should ambiguity be resolved before verification or represented inside its model?

- **DECISION:** Resolved before storage. Entity resolution runs at extraction; a candidate that cannot be resolved to an existing entity creates a new one; ambiguity is not represented in the model (`Q656`). If two entities later prove to be one, a merge is an explicit operation with an audit record.
- **BECAUSE: ENGINEERING (E4).** Position is silent. Representing ambiguity would require the memory surface to show a user two possible Priyas, which is exactly the developer-facing complexity `P§9` refuses.
- **REJECTED:** Representing ambiguity in the model. It wins for correctness under genuine uncertainty and avoids irreversible bad merges. It loses on `P§9`'s legibility requirement.
- **COST:** Premature resolution creates false merges and false splits, both of which are visible and embarrassing on the memory surface, and a false merge is hard to unwind (`Q173`).
- **CONFIDENCE:** medium

---

### Q416 — When two data models need joint reasoning, should they share one verification representation or retain separate native representations?

- **DECISION:** One representation. The entity graph lives in the same relational database as the memories, as ordinary tables — not in a separate graph engine requiring joint reasoning across two models.
- **BECAUSE: ENGINEERING (E2).** A second engine is a second process in `RUN.md`. At this graph size, a relational edge table with one or two joins is exact and instant.
- **REJECTED:** A native graph store alongside the relational one. It wins for deep traversal, which `Q752` already declines to do.
- **COST:** Multi-hop queries are awkward SQL and will stay shallow (`Q752`).
- **CONFIDENCE:** high

---

### Q417 — When constructing an intermediate schema, should it preserve each graph element directly or optimize for the target workload?

- **DECISION:** Preserve directly — one table for entities, one for typed edges with source/target foreign keys and their own properties. No workload-specific denormalisation.
- **BECAUSE: ENGINEERING (E5).** Position is silent. At this scale there is no workload pressure justifying denormalisation, and a direct mapping is what makes the schema readable to the reviewing agent.
- **REJECTED:** Workload-optimised denormalisation. It wins at scale. It would make the committed schema harder to understand, which the brief penalises indirectly.
- **COST:** No query-shape optimisation available without a schema change.
- **CONFIDENCE:** high

---

### Q419 — When predicates ask only whether a relationship exists, which equivalent relational construction should represent that test?

- **DECISION:** Existence tests are ordinary `EXISTS` subqueries over the edge table, projected onto entity ids. No specialised construction.
- **BECAUSE: ENGINEERING (E5).** Position is silent; this is an implementation detail with an obvious correct answer at this scale.
- **REJECTED:** Any optimised alternative. Wins at scale.
- **COST:** None material.
- **CONFIDENCE:** high

---

### Q420 — When the target schema differs from the intermediate schema, should translation absorb that difference or should a separate mapping carry it?

- **DECISION:** A separate, explicit, documented mapping — the corpus **import adapter**. The internal schema does not bend to accommodate an external corpus shape; a documented adapter translates the reviewer's format into it.
- **BECAUSE: ENGINEERING (E2).** The brief requires "the exact procedure for importing another corpus," and says the reviewing agent "will… translate our internal corpus into the documented import format." That sentence makes the adapter boundary the contract, so the internal schema must stay fixed and the adapter must be precisely documented.
- **REJECTED:** A flexible schema that absorbs format differences. It wins on import robustness. It makes the import contract vague, which is the specific thing the brief warns will make the submission unreviewable.
- **COST:** If the reviewer's corpus lacks a field the adapter requires — a stable id, a usable timestamp (`Q667`) — the import fails rather than degrading. That failure must be loud, documented, and have a stated fallback.
- **CONFIDENCE:** high

---

### Q432 — What is the atomic remembered object?

- **DECISION:** The typed memory record (`Q800`). Transcripts are preserved as primary *records* but are not memories; there are no synthesized profiles.
- **BECAUSE: POSITION.** `P§4` (the record), `P§9` (transcripts), `P§2` (no profiles).
- **REJECTED:** Transcripts as the primary remembered object with facts derived at query time. That is the reconstruct-on-demand design `Q134` rejects.
- **COST:** As `Q134`.
- **CONFIDENCE:** high

---

### Q433 — Is provenance part of the value or optional payload?

- **DECISION:** Part of the value. Required on write (`Q86`), immutable (`Q188`), carried through every read (`Q379`), never reconstructed and never omitted for speed.
- **BECAUSE: POSITION.** `P§9`.
- **REJECTED:** Reconstructable or omittable provenance. It wins on read payload size and latency, both of which the brief asks to be reported. It is the one place I will not trade for latency.
- **COST:** Larger payloads on every read path.
- **CONFIDENCE:** high

---

### Q437 — Should retrieved observations hide their source facts?

- **DECISION:** No — an observation always shows its evidence, and showing it is mandatory rather than caller-optional. `P§4` makes evidence part of what an observation *is* when surfaced.
- **BECAUSE: POSITION.** `P§4`: observed memories are "Surface as an observation with its evidence." `P§6`'s Koottu example carries the evidence inline: "You've moved this deadline three times: the 4th, the 11th, and the 18th."
- **REJECTED:** Letting the caller choose, or showing synthesis only. It wins on response brevity — the Koottu example is noticeably longer than the Anbu one. It loses because an observation without its evidence is indistinguishable from a rule, which is the whole distinction `P§4` protects.
- **COST:** Koottu responses are verbose, and a fourteen-instance observation cannot list fourteen dates. The presentation rule for large evidence sets is undecided — see **Section A**.
- **CONFIDENCE:** high

---

### Q448 — Which memory dimensions should the schema preserve rather than collapse into text?

- **DECISION:** Type, tier, status, evidence count, source ids, event time, first-seen, last-confirmed, extractor model and version. Not confidence (`Q100`), not task label, not substrate or control policy.
- **BECAUSE: POSITION.** `P§4`'s schema list, plus the engineering additions from `Q673`/`Q799`.
- **REJECTED:** Adding a confidence tag, which the surveyed answer recommends alongside timestamp, source, and task label. It wins for ranking. Rejected by `P§4`'s two-axis argument.
- **COST:** As `Q42`.
- **CONFIDENCE:** high

---

### Q468 — What should determine which past episodes are relevant to a new input?

- **DECISION:** Hybrid relevance to the **request**, plus entity overlap, plus temporal constraints where the query states one — then the deterministic re-rank (`Q193`). Not pure embedding similarity to past questions.
- **BECAUSE: ENGINEERING**, with `P§7`'s emphasis on exact entity naming forcing the lexical/entity component.
- **REJECTED:** Pure semantic similarity between the new question and stored questions. It wins for few-shot case retrieval, which `Q463` already removes. It is also weak exactly where Kivi is strongest — entity-anchored queries.
- **COST:** As `Q182`.
- **CONFIDENCE:** high

---

### Q481 — What representation should be the durable substrate: source text, structured entities/relations, summaries, embeddings, or several in parallel?

- **DECISION:** Three in parallel with a strict hierarchy of authority: **structured typed memories + entities/relations** (authoritative), **source text** (immutable provenance), **embeddings** (rebuildable cache, never authoritative, `Q155`). No summaries.
- **BECAUSE: POSITION.** `P§4` + `P§9`; the no-summaries half is `Q154`.
- **REJECTED:** Parallel indexing including summaries. It wins on retrieval breadth.
- **COST:** As `Q154`.
- **CONFIDENCE:** high

---

### Q483 — When several extracted claims refer to the same entity, what should determine identity resolution and merging?

- **DECISION:** A documented three-step policy, not left underspecified: (1) exact match on canonical name or a known alias; (2) normalised match (case, punctuation, known ASR variants) proposed and accepted automatically; (3) fuzzy or semantic match proposed to an LLM judge whose verdict is recorded with evidence (`Q92`). A merge writes an audit record and is reversible only by re-extraction.
- **BECAUSE: POSITION.** `P§7` requires ASR variants (*Prea* → *Priya Raghavan*) to resolve, which forces step 2 to exist and to be automatic. The rest is `ENGINEERING`.
- **REJECTED:** Leaving resolution policy underspecified, which is what the surveyed system does and is the single most common gap in the inventory. It wins never — but naming it matters, because this is where an unspecified policy silently becomes whatever the model does that day.
- **COST:** As `Q413` — false merges and splits, visible on the memory surface, hard to unwind.
- **CONFIDENCE:** medium

---

### Q487 — How should candidates be ranked when semantic relevance, graph proximity, recency, authority, and permission disagree?

- **DECISION:** A fixed precedence, applied in order and fully recorded in the trace: fused relevance → pinned → tier → evidence → recency. Graph proximity enters only as one-hop entity expansion *into* the candidate pool, never as a ranking term. Permission never ranks — it filters at disclosure, after ranking (`Q351`).
- **BECAUSE: POSITION** for permission's placement (`P§6`) and tier's presence (`P§4`); **ENGINEERING** for the rest of the order.
- **REJECTED:** An underspecified fusion, which is the surveyed answer and the honest description of most systems. It wins on nothing; it is the absence of a decision. Naming the precedence is what makes the Why panel possible.
- **COST:** A fixed precedence is wrong for some queries (`Q326`) and cannot be tuned without reopening `Q212`'s refusal of learned reranking.
- **CONFIDENCE:** medium

---

### Q503 — In what representation should the result of reflection be retained?

- **DECISION:** Not retained — there is no reflection (`Q459`, `Q707`).
- **BECAUSE: POSITION.** `P§4`'s tiers admit user statements, patterns across them, and questions about them. A model's reflection on its own performance is none of these and would have no tier.
- **REJECTED:** A natural-language consensus reflection appended to memory. It wins for self-improving agents. Note also that its schema is "underspecified" in the source — a model-authored free-text artefact tends to resist schematisation, which is itself an argument against admitting it to a typed store.
- **COST:** As `Q12` — no learning from Kivi's own performance.
- **CONFIDENCE:** high

---

### Q519 — How much confidence is a memory entitled to?

- **DECISION:** Exactly what its tier entitles it to, and no more. Stated: treated as true, used freely. Observed: offered with evidence, never enforced. Hypothesised: voiced as a question when invited, never asserted. There is no numeric entitlement.
- **BECAUSE: POSITION.** `P§4`'s tier table column is literally "What Kivi may do with it." The inventory question's own phrasing — "entitled to" — is the position's word.
- **REJECTED:** One flat tier where everything is asserted (the surveyed answer, and what MemGPT-class systems do). It wins on generation simplicity: everything in context can be stated in the same voice. It is the failure `P§4` describes as the origin of both product failures.
- **COST:** Generation must vary its voice by tier, which means the prompt has to carry tier and the model has to honour it — a compliance dependency in a system that otherwise enforces promises in code (`Q247`). This is a real weak point: **tier-appropriate phrasing is the one product promise enforced by prompt rather than by code.** Flagged in **Section A**.
- **CONFIDENCE:** high on the rule, medium on its enforcement.

---

### Q521 — Is a hypothesis representable at all?

- **DECISION:** Yes, and it is representable **only as an interrogative**. The `content` of a hypothesised memory is stored as a question string; the schema rejects a declarative at that tier. `"Does the user disagree with the Atlas pricing rationale?"` — not `user_disagrees_with_pricing: true`.
- **BECAUSE: POSITION.** `P§4`, verbatim: "Hypotheses are stored as questions, never as claims… The grammar of storage enforces the epistemics. You cannot accidentally use a question as a fact."
- **REJECTED:** No grammar for hypotheses; storage can only assert (the surveyed answer). It wins on schema simplicity. It makes Daari impossible — there would be nowhere to put a proposed reason that was not also a stored belief.
- **COST:** Enforcing "must be a question" is a validation rule that a determined model can evade by writing a rhetorical question. The enforcement is weaker than it looks and needs an explicit test.
- **CONFIDENCE:** high

---

### Q533 — Who has authority to write to memory: the model, a deterministic component, or the user?

- **DECISION:** Split, with the deterministic component holding final authority. The model **proposes** candidates; deterministic code **admits or rejects** them and assigns nothing the model can override; the user **overrides everything**. The model never writes.
- **BECAUSE: POSITION.** `P§2`: "Exclusions are enforced by a check that runs on candidate memories, not by a line in a prompt hoping for good behaviour." That sentence makes code the gatekeeper. `P§9` makes the user supreme.
- **REJECTED:** The model, alone (the surveyed answer, and the MemGPT design). It wins on flexibility and is far less code. It means every product promise depends on prompt compliance.
- **COST:** Extraction is a two-stage pipeline with a rejection path, which is more code and more cost per transcript (`Q701`).
- **CONFIDENCE:** high

---

### Q534 — What is the unit of a memory: an utterance, or a claim assembled from several?

- **DECISION:** A claim, assemblable from several — one memory may be evidenced by many transcripts, and one transcript may produce many memories (`Q547`). The mapping is many-to-many.
- **BECAUSE: POSITION.** `P§AppC` claim 3: "A memory was assembled from evidence distributed across multiple separate dictations." That is the claim the many-to-many mapping exists to make provable, and it is also what the brief tests ("whether it can recover information distributed across multiple dictations").
- **REJECTED:** One utterance, one memory. It wins on provenance simplicity — one link, no join table. It makes claim 3 unexpressible.
- **COST:** A join table to maintain through merges and supersessions (`Q87`), and merge quality becomes load-bearing (`Q479`).
- **CONFIDENCE:** high

---

### Q554 — How is provenance represented?

- **DECISION:** Source transcript ids, extraction run id, extractor model and version, tier-change events with cause and timestamp, supersession pointers, and per-answer traces. All persisted, all exposed (`Q279`, `Q379`).
- **BECAUSE: POSITION.** `P§4` + `P§9` + `P§8`.
- **REJECTED:** A lighter subset. See `Q279`. Note this surveyed system persists roughly the right set — source turn ids, change logs, audit logs — and is one of the few that does; the gap elsewhere is usually exposure rather than storage (`Q860`).
- **COST:** As `Q330` — substantial metadata, reflected in database growth.
- **CONFIDENCE:** high

---

### Q569 — At what semantic granularity should retained dialogue be represented?

- **DECISION:** As discrete typed claims expressed in short natural-language sentences (`Q63`), not as decomposed subject–predicate–object triples. Triples exist only for entity relations.
- **BECAUSE: POSITION.** `P§9` requires the memory surface to show each belief to a normal user. A triple is not a belief a person reads; a sentence is. `P§4`'s own examples are sentences: "*Client emails in prose, not bullet lists. Signs off 'Best, Meera'.*"
- **REJECTED:** Atomic SPO triples throughout. It wins on merge precision, on multi-hop query, and on token economy — measurably, which is why its source claims a token advantage. It loses on the surface requirement, and it cannot express a preference cleanly ("prefers prose over bullets in client email" is not naturally a triple).
- **COST:** Merging sentence-shaped memories is fuzzier than merging triples, which makes `Q479`'s sameness judgement harder and more model-dependent.
- **CONFIDENCE:** high

---

### Q570 — When atomic representation removes narrative context, what secondary representation should restore it?

- **DECISION:** The **source transcript**, reachable in one tap, restores context. Not a generated conversation-level summary. This is the position's answer to the narrative-loss problem and it is a weaker answer than a summary would be.
- **BECAUSE: POSITION.** `P§9`: provenance is "the actual transcript, with a date." The transcript is the context-restoring artefact, and it has the advantage of being true rather than generated.
- **REJECTED:** Generating a conversation-level summary capturing intent and chronology, linked to the atomic facts. It is the single most useful thing in the inventory that this design refuses, and its source adds it specifically because triples alone "would likely worsen chronology/context." That diagnosis applies here too. It wins if narrative questions turn out to matter — and the brief's example question ("find the dictation I did around 5 PM yesterday in Slack and polish it") is chronological. This is `Q154`'s gap stated at its sharpest.
- **COST:** Narrative and chronological questions are served only by raw-transcript fallback (`Q211`) and episode retrieval. **This is the most likely place the system will underperform on the reviewer's corpus.**
- **CONFIDENCE:** medium

---

### Q576 — What should cap retrieved context: a fixed count, token budget, score threshold, marginal utility, or confidence threshold?

- **DECISION:** A fixed top-k, plus a token budget as a hard secondary cap, with drops reported (`Q562`, `Q708`). No score threshold (`Q393` — scores are not calibrated), no marginal-utility model, no confidence threshold (none exists).
- **BECAUSE: ENGINEERING**, with the parameter deferred by **POSITION** (`P§AppB`).
- **REJECTED:** A score threshold, which would let the system return nothing when nothing is relevant — a genuinely useful property that `Q393` notes is currently missing. It wins if scores can be calibrated, which for RRF-fused ranks they cannot without work.
- **COST:** As `Q393` — no absolute relevance signal; top-k always returns k things.
- **CONFIDENCE:** medium

---

### Q586 — F1 — Atomic triples instead of raw conversational chunks (D3)

- **DECISION:** Neither, exactly: atomic typed claims as sentences (`Q569`), with raw transcripts retained separately as the fallback and provenance layer (`Q211`, `Q28`).
- **BECAUSE: POSITION.** `P§4` (claims) + `P§9` (raw).
- **REJECTED:** Raw conversational chunks as the retrieval unit. It wins on context fidelity and on avoiding extraction loss entirely. Its cost — higher context use, weaker single-hop precision — is exactly what the inventory note predicts, and the position's typed-claim requirement settles it regardless.
- **COST:** Extraction loss is permanent for anything not captured as a claim.
- **CONFIDENCE:** high

---

### Q587 — F2 — Dual representation: triples plus summaries (D4, D12)

- **DECISION:** Dual representation, but the second layer is **raw transcripts**, not summaries (`Q570`). Typed claims plus immutable sources.
- **BECAUSE: POSITION.** `P§9` supplies the second layer and forbids it being a generated artefact in place of the real one.
- **REJECTED:** Claims plus generated summaries. As `Q570` — this is the strongest rejected alternative in the representation stage and the cost is real.
- **COST:** As `Q570`. Note the inventory's own observation that "larger source passages would weaken the token claim" — retaining raw transcripts and using them as fallback means Kivi's token economics are worse than a summary-based system's, and the cost report will show it.
- **CONFIDENCE:** medium

---

### Q594 — When a persistent assistant changes models or instances, what should determine whether it remains the same entity?

- **DECISION:** The question does not arise, because Kivi is not an entity with identity. It is a product with a database. A model change is a migration event (`Q673`), not an identity event. What must survive a model change is the *user's* memory and their corrections — nothing about Kivi's continuity matters.
- **BECAUSE: POSITION.** `P§3`: Kivi should become "a colleague who has been in the room — not a system that has a theory about you." The position never grants Kivi selfhood; `P§9` makes the memory the user's property.
- **REJECTED:** Continuity of memory as identity, with model replacement as "re-shelling." It wins in a product whose premise is a persistent digital being. It would imply Kivi has an interest in its own memory, which `Q595` explicitly denies.
- **COST:** None conceptually. Practically: a model change invalidates extractions (`Q673`) and the user's corrections must survive the reprocess, which is an unsolved operational problem (`Q406`, `Q526`).
- **CONFIDENCE:** high

---

### Q601 — When low-level experience becomes durable identity or cognition, what should trigger promotion?

- **DECISION:** Nothing. There is no identity layer and no promotion into one. The only promotion is `observed → stated`, and its trigger is an explicit user confirmation (`Q191`).
- **BECAUSE: POSITION.** `P§2` refuses the identity/profile layer; `P§4` refuses automatic promotion.
- **REJECTED:** Periodic distillation and sedimentation upward. It wins for a system building a persistent self-model. Note its source leaves "thresholds, evidence aggregation, reviewer, and algorithm underspecified" — the recurring pattern (`Q24`, `Q642`, `Q773`) of promotion mechanisms shipped without their parameters.
- **COST:** As `Q378`/`Q399` — no aggregate view.
- **CONFIDENCE:** high

---

### Q607 — When multiple actors can modify one category of memory, how should concurrent authority be controlled?

- **DECISION:** Single writer per category by construction: the extractor owns extraction-derived writes, the user-action handler owns user writes, and they are serialised through one writer process (`Q660`). Where they touch the same memory, the user always wins (`Q269`).
- **BECAUSE: ENGINEERING (E2) for the serialisation, POSITION for the precedence** (`P§9`: the user's authority is total).
- **REJECTED:** Optimistic concurrent modification with conflict resolution. Wins at scale; `E1` removes the need.
- **COST:** As `Q96`.
- **CONFIDENCE:** high

---

### Q611 — When the system is wrong, how should correction burden be divided between the system, the user, and a governance authority?

- **DECISION:** The **system** carries the burden of making correction cheap; the **user** carries only the act of correcting; there is no governance authority. Concretely: corrections are inline and ceremony-free (`P§8`), the four actions are one tap each, suppression is automatic so the user never corrects the same thing twice (`P§9`), and prompts are budgeted so the user is not conscripted into review.
- **BECAUSE: POSITION.** `P§8`: "Corrections are cheap and inline. *'No, Priya's at Northwind now'* in the middle of a request should update the entity without ceremony." And: "it's rationed, because the person must not become the administrator of the system." `P§9`: suppression exists so "the user learns that their corrections don't stick" never happens.
- **REJECTED:** Append-only history with risk-sensitive due process (the surveyed answer). It wins on auditability and for high-stakes systems. Due process is administration, which `P§8` explicitly refuses to impose on the user.
- **COST:** Cheap correction means a correction can be made carelessly or accidentally, with no confirmation step for destructive actions — `Forget` in particular. That needs a confirmation, which is friction the position's language does not anticipate.
- **CONFIDENCE:** high

---

### Q614 — When one identity splits into concurrent descendants, how should memory histories diverge and later reconcile?

- **DECISION:** Not applicable. No branching, no descendants, one linear memory state (`Q400`). **Out of scope** (`E1`, `E5`).
- **BECAUSE: ENGINEERING (E1, E5).**
- **REJECTED:** Branch-and-merge identity histories. Wins for forked autonomous agents.
- **COST:** None here.
- **CONFIDENCE:** high

---

### Q621 — When a stored representation is inaccurate or stale, should correction modify the existing memory, append a correction, or preserve versions?

- **DECISION:** All three, distinguished by cause. **User `Correct`:** modifies the memory in place, keeping its id, and writes a superseded snapshot to history. **New contradicting evidence:** appends a new memory and marks the old superseded with a pointer. **User demote/forget:** changes status and writes a suppression. Every one of the three preserves a version.
- **BECAUSE: POSITION.** `P§9`: "Contradictions supersede… the superseded version stays in history so the change is auditable," and separately the four per-entry actions.
- **REJECTED:** Direct user editing of the object with no version preserved (the surveyed answer). It wins on simplicity and matches the user's mental model ("I fixed it"). It loses `P§9`'s audit.
- **COST:** As `Q114` — the boundary between "correct in place, keep id" and "supersede with a new row" is subtle and will be implemented inconsistently at least once.
- **CONFIDENCE:** medium

---

### Q628 — Should memories represent what was said, what the system inferred, or both—and how should their epistemic status be exposed?

- **DECISION:** Both, in separate tiers, with the status exposed in three places: the memory surface's three named groups, the tier label on every memory in the Why panel, and the voice of the generated answer (asserted vs offered vs asked).
- **BECAUSE: POSITION.** `P§4` (the tiers), `P§9` ("*Things you told me. Things I've noticed. Things I'm wondering about*"), `P§6` (the three modes' speech acts).
- **REJECTED:** Treating memory as conversational history or its summary with no tiers (the surveyed answer, and the field default). It wins on simplicity and recall. `P§4` is written against it.
- **COST:** As `Q14`, plus the `Q519` weakness that the third exposure (answer voice) is prompt-enforced.
- **CONFIDENCE:** high

---

### Q635 — At what granularity should an experience be remembered: verbatim trajectory, abstract script, both, or smaller claims/steps?

- **DECISION:** Smaller claims. Not trajectories, not scripts, not proceduralisation (`Q634`, `Q650`).
- **BECAUSE: POSITION.** `P§4`'s three types contain no procedure. `Q235` establishes there is no procedural memory.
- **REJECTED:** Proceduralisation combining trajectories and scripts — which the inventory notes "performs best overall." That is a real performance claim being declined. It wins for an agent that must repeat tasks; Kivi's value is knowing things, not doing sequences.
- **COST:** As `Q235`. Kivi cannot learn how to do anything.
- **CONFIDENCE:** high

---

### Q640 — When stored guidance conflicts with the current environment or new experience, should the system preserve both, choose by recency/authority, or revise one in place?

- **DECISION:** Choose by authority first, then recency (`Q174`, `Q672`), and preserve the loser as superseded history. Never revise a memory in place on the system's own initiative — only a user `Correct` revises in place (`Q621`).
- **BECAUSE: POSITION.** `P§9` (supersede, preserve) and `P§4` (tier precedence). The prohibition on system-initiated in-place revision follows from `Q269`: the user owns corrections.
- **REJECTED:** Combining a failure with the retrieved memory and revising in place (the Adjustment mechanism). It wins for self-improving agents and is an elegant mechanism. It is Kivi silently rewriting a belief about the user — the fastest possible way to make corrections not stick, inverted.
- **COST:** Stale beliefs persist until the user acts (`Q269`).
- **CONFIDENCE:** high

---

### Q646 — What should the system expose about memory use to the person affected: nothing, retrieved content, source evidence, confidence, withheld items, or update history?

- **DECISION:** Retrieved content, source evidence, withheld items with reasons, and update history. Not confidence (none exists). Exposed by default as an affordance on every answer, expandable.
- **BECAUSE: POSITION.** `P§8` names exactly four: "what was retrieved, what was withheld and why, what was used in the answer, and the source transcript behind each memory." `P§9` adds update history to the memory surface.
- **REJECTED:** Exposing only task outputs (the surveyed answer, and what every benchmark system does — the inventory notes "no user-facing memory surface, retrieval trace, confidence, source inspection, or correction interface is described"). It wins on build cost. The brief forecloses it.
- **COST:** As `Q44` — a large UI surface with a hard design problem.
- **CONFIDENCE:** high

---

### Q653 — Is the durable unit a source-faithful passage, a normalized exchange, or a proposition with epistemic state?

- **DECISION:** A proposition with epistemic state. Source-faithful passages are retained separately as provenance, never as the memory unit.
- **BECAUSE: POSITION.** `P§4`.
- **REJECTED:** Verbatim drawer text with flat provenance metadata, whose mission explicitly rejects summarisation. It wins on fidelity — nothing is lost, nothing is a model's interpretation. It is a genuinely principled position and the mirror image of this one: it trusts the source and distrusts extraction. It loses because without propositions there is no tier, and without tier there is no dial.
- **COST:** Everything depends on extraction quality, which is a model's interpretation of what was said (`Q307`).
- **CONFIDENCE:** high

---

### Q654 — Should boundaries follow characters, paragraphs, exchanges, semantic statements, or model token limits?

- **DECISION:** Whole transcripts for extraction (`Q480`); semantic statements for memories (`Q547`). No character chunking, no overlap, no token-limit splitting.
- **BECAUSE: ENGINEERING (E3)** and **POSITION** for provenance integrity (`P§9`).
- **REJECTED:** 800-character chunks with overlap. It wins for document corpora. Overlap in particular would duplicate candidates across chunk boundaries and break idempotence (`Q722`).
- **COST:** As `Q480` — a long record must fail rather than chunk.
- **CONFIDENCE:** high

---

### Q662 — Semantic closeness, lexical match, recency, confidence, epistemic tier, or user permission?

- **DECISION:** Semantic closeness and lexical match fused by rank (`Q209`), then epistemic tier, evidence, recency as re-rank (`Q193`); user permission filters at disclosure only (`Q351`); no confidence.
- **BECAUSE: POSITION** for tier's inclusion and permission's placement; **ENGINEERING** for the fusion mechanics.
- **REJECTED:** A fixed weighted blend (0.6 vector + 0.4 BM25) with recency tie-breaks — the surveyed answer, which is a reasonable and common choice. It wins if the two score distributions are stable enough for fixed weights to be meaningful. RRF is preferred precisely because it does not assume that (`Q393`).
- **COST:** RRF discards score magnitude, so a very strong lexical match and a marginal one contribute the same rank signal.
- **CONFIDENCE:** medium

---

### Q670 — How is knowledge represented?

- **DECISION:** As typed memory rows with natural-language `content` plus typed metadata, and typed entity/relation rows. Never as an entity-slot-string triple with JSON smuggled inside the string value.
- **BECAUSE: POSITION.** `P§4`'s schema. The surveyed pattern — "complex values may be JSON embedded inside the string" — is the specific failure mode of over-atomised representation: structure that does not fit the triple gets hidden in a string where nothing can query it.
- **REJECTED:** Atomic entity-slot-string triples. See `Q569`.
- **COST:** As `Q569` — fuzzier merging.
- **CONFIDENCE:** high

---

### Q671 — Is confidence the same as authority?

- **DECISION:** No — and only authority exists. Confidence (how likely a claim is true) is not modelled. Authority (what Kivi may do with a claim, given where it came from) is `tier`. Conflating them is the specific error `P§4` names.
- **BECAUSE: POSITION.** `P§4`: "memory has two independent axes — what kind of thing it is, and how confident we're entitled to be." The word is *entitled*, not *likely*. Entitlement is authority.
- **REJECTED:** An optional clamped float serving as both (the surveyed answer). It wins on expressiveness. An optional confidence is also the `Q145` hazard: absent values fail open.
- **COST:** As `Q42` — no way to say "probably."
- **CONFIDENCE:** high

---

### Q691 — How should candidates from different stores be merged and ranked when recency, similarity, importance, graph connectivity, and epistemic authority disagree?

- **DECISION:** There are no different stores to merge — one memory table, two indexes over it (`Q447`). The indexes' results fuse by RRF, then re-rank by tier/evidence/recency (`Q487`). No importance (`Q100`), no activation filtering, no graph connectivity term.
- **BECAUSE: POSITION** for tier and the absence of importance; **ENGINEERING** for the single-store design (`E2`).
- **REJECTED:** A tiered hot-cache/warm-store/graph priority with importance filtering and a recency boost. It wins at scale with genuinely different stores. Here it would introduce store-of-origin as a hidden ranking factor the Why panel would have to explain.
- **COST:** No caching tier; every query hits the database. Fine at this scale.
- **CONFIDENCE:** high

---

### Q695 — What should the user be shown about remembered content, retrieved evidence, withheld material, confidence, and provenance?

- **DECISION:** Duplicate of `Q646`/`Q44`. Content, evidence, withheld-with-reasons, provenance — yes, by default, on every answer. Confidence — does not exist.
- **BECAUSE: POSITION.** `P§8`, `P§9`.
- **REJECTED:** See `Q646`.
- **COST:** See `Q44`.
- **CONFIDENCE:** high

---

### Q723 — When extraction, coreference resolution, and temporal anchoring interact, should they be decided jointly or independently?

- **DECISION:** Jointly, in one extraction call — the model resolves references, normalises time, and produces typed candidates in a single structured output. The subsequent **exclusion check** is a separate stage (`Q701`), and **entity resolution against the existing store** is a separate deterministic-then-judged stage (`Q483`).
- **BECAUSE: ENGINEERING.** Position is silent on extraction internals. Joint decision is right because time and coreference are mutually constraining within a transcript ("move it to Tuesday" needs both). Separating the exclusion check is `P§2`-forced.
- **REJECTED:** Fully independent stages. It wins on inspectability — each stage's output could be examined. It loses on quality for exactly the anaphoric cases `Q516`/`Q845` already identify as weak.
- **COST:** One large extraction prompt doing four jobs, whose failures are harder to attribute to a stage.
- **CONFIDENCE:** medium

---

### Q725 — What epistemic distinctions should the memory schema preserve?

- **DECISION:** Tier (stated/observed/hypothesised) and status (active/superseded/demoted/expired). Plus type. Not salience (`Q100`).
- **BECAUSE: POSITION.** `P§4`'s schema.
- **REJECTED:** Content + entities + topic + timestamp + salience with everything framed as factual (the surveyed answer). The "all outputs framed as factual memory units" phrase is the failure precisely.
- **COST:** As `Q14`.
- **CONFIDENCE:** high

---

### Q744 — When an interaction enters memory, what should be the atomic episodic unit?

- **DECISION:** An **episode memory** — a typed claim that something happened, with an event time, entities, and sources. Not a concatenated turn node containing raw text and an embedding; that object is the transcript, which is provenance, not memory.
- **BECAUSE: POSITION.** `P§4`'s Episode row: "Something that happened, with a time — *On 12 March the user moved the Atlas review from Tuesday to Thursday.*" That is a claim, not a transcript.
- **REJECTED:** Raw-turn episodic nodes. It wins on fidelity and on zero extraction loss for episodes. It cannot be tiered, corrected, or superseded individually.
- **COST:** Episode extraction can miss events the raw turn contained.
- **CONFIDENCE:** high

---

### Q746 — When raw episodes accumulate, what additional representation should carry generalized knowledge?

- **DECISION:** The **observed tier** carries generalisation, as ordinary memory rows with evidence pointing at multiple transcripts. Not a second semantic layer, not concept nodes.
- **BECAUSE: POSITION.** `P§4`: an observation is "A pattern across multiple transcripts, pointable-at." Generalisation is a tier, not a layer.
- **REJECTED:** A dual-layer graph with LLM-extracted semantic concept nodes above raw episodic nodes. It wins on multi-hop and conceptual retrieval (`Q752`). It would create generalisations with no tier and no correction path.
- **COST:** As `Q752` — weak conceptual and multi-hop retrieval.
- **CONFIDENCE:** high

---

### Q747 — What kinds of abstraction may the system derive from episodes?

- **DECISION:** Exactly one: an **observed pattern** across multiple transcripts, expressed as a memory of one of the three types, carrying its evidence. No new categories, no confidence, no identity/persona abstraction.
- **BECAUSE: POSITION.** `P§4`'s tier system provides one abstraction mechanism; `P§2` forbids the identity/persona kind. The surveyed answer's "Identity" category is the profile `P§2` refuses.
- **REJECTED:** LLM-extracted categorised facts including Identity and with confidence. It wins on richness. The Identity category and the confidence field are both directly excluded.
- **COST:** As `Q378`.
- **CONFIDENCE:** high

---

### Q750 — When the memory graph grows, what should be discarded from the active structure?

- **DECISION:** Nothing is discarded (`Q54`). Observations lose surfacing standing by decay; hypotheses expire; nothing is archived by activation, and no edges are pruned by degree.
- **BECAUSE: POSITION.** `P§9` reserves removal for the user; `P§4` makes evidence permanent.
- **REJECTED:** Top-15-edge retention with activation-based archival, targeting a bounded active graph. It wins at scale and is a well-designed forgetting policy. At a few hundred memories there is nothing to bound.
- **COST:** As `Q54` — no scale path, and no mechanism if the reviewer's corpus is much richer than expected.
- **CONFIDENCE:** high for this build, low as a permanent answer.

---

### Q757 — After retrieval passes a confidence gate, what should constrain the generator's use of evidence?

- **DECISION:** A hard grounding contract enforced structurally, not only by prompt: the generator may only cite memories present in its assembled context (`Q255`), every claim in the answer must map to a cited memory or to a labelled raw-transcript excerpt, and unsupported content triggers abstention. The prompt says "answer only from what is here; otherwise say what you do not have."
- **BECAUSE: POSITION.** `P§8`: "Kivi never fills a gap with a plausible guess." And the abstention example, which answers by describing the search rather than by guessing.
- **REJECTED:** A strict verification prompt alone ("answer only if explicitly mentioned; otherwise 'Not mentioned'"). It is the right instruction and it is what I use — but relying on it *alone* leaves the product's central promise as prompt compliance. The structural half (the model only sees permitted, retrieved memories) is what makes the instruction enforceable. The residual gap — the model can still paraphrase beyond its evidence — is real and is why `Q592` grades evidence attribution separately.
- **COST:** The grounding check cannot be fully automated; attribution grading is partly manual (`Q429`). Kivi will occasionally over-claim and only sampling will catch it.
- **CONFIDENCE:** medium

---

### Q762 — When should a new episode begin: at every session boundary, at fixed size, or when a model infers a topic change using surrounding context?

- **DECISION:** None of these. An episode is not a segment of a stream — it is a typed claim about a dated event (`Q744`). Episode boundaries are a non-question in this design, because transcripts arrive pre-bounded (`Q374`).
- **BECAUSE: POSITION.** `P§4`'s Episode definition is a fact with a time, not a span.
- **REJECTED:** Model-inferred topic-change segmentation. It wins for continuous streams. Note the naming collision it exposes: "episode" means a *span* in most of the surveyed work and a *dated fact* in `P§4`. That collision will confuse anyone reading the papers alongside the spec and is worth calling out in the README (`Q235` makes the same point about episodic memory).
- **COST:** No span-level structure; chronological questions have no episode-span to retrieve (`Q570`).
- **CONFIDENCE:** high

---

### Q766 — When many traces accumulate, should organization be chronological, graph-based, schema-based, or discovered through semantic clustering?

- **DECISION:** Schema-based: by type and tier, with an entity graph beside it. Chronology is a queryable field, not an organising structure. No clustering (`Q767`, `Q802`).
- **BECAUSE: POSITION.** `P§9`'s memory surface is organised by tier, which is schema.
- **REJECTED:** PCA→UMAP→HDBSCAN clustering into topics and threads. It wins for navigating a large unlabelled corpus and it directly addresses the navigation gap (`Q784`). Rejected because discovered clusters have no tier, cannot be corrected, and would present the user with an organisation of themselves they did not choose — a soft form of the profile `P§2` refuses.
- **COST:** As `Q784` — the navigation problem is unsolved.
- **CONFIDENCE:** medium

---

### Q778 — When a stream contains multiple activities, what should determine the boundary of an episode?

- **DECISION:** Duplicate of `Q762`/`Q374`. The client's transcript boundary. No inferred segmentation.
- **BECAUSE: ENGINEERING (E3).**
- **REJECTED:** Utterance-level topic-change classification. See `Q762`.
- **COST:** See `Q762`.
- **CONFIDENCE:** high

---

### Q779 — What kinds of claims about a person may become durable memory: concrete facts only, patterns, inferred self-knowledge, or narrative characterizations?

- **DECISION:** Concrete work-level facts and patterns over them. **Never** inferred self-knowledge. **Never** narrative characterisations. Patterns are permitted only at the observed tier, with evidence, never enforced.
- **BECAUSE: POSITION.** `P§2`, and this is the question that section exists to answer: "The first version of this design was an ontology of everything Kivi could learn: entities, projects, preferences, working style, goals, motivations, insecurities, self-image. It was thorough. It was also the wrong product." The surveyed answer's examples — "self-care, overwhelm, family" — are three excluded categories in a row.
- **REJECTED:** Aggregating experiences into narrative threads and a coherent persona or life story. It wins on user delight and on answer quality for broad questions. It is the single most direct antagonist to `P§2` in the entire inventory, and `P§2`'s four arguments against it (achievable, unverifiable, uncorrectable, changes what the user is) are the whole basis of this product.
- **COST:** As `Q331`/`Q378` — the most compelling possible screen is not built, and broad questions answer poorly.
- **CONFIDENCE:** high

---

### Q781 — Should a memory preserve the original episode, a summary, atomic facts, or several representations at once?

- **DECISION:** Two: the original transcript (provenance) and atomic typed facts (memory). Not summaries, not narrative threads, not memory cards.
- **BECAUSE: POSITION.** `P§9` + `P§4`; summaries rejected at `Q154`/`Q570`.
- **REJECTED:** Five parallel representations including narrative threads and persona summaries. It wins on retrieval coverage across question types — measurably. The persona half is excluded by `P§2`; the narrative half is `Q570`'s live cost.
- **COST:** As `Q570`.
- **CONFIDENCE:** high

---

### Q786 — When the system derives a pattern or explanation, what should distinguish evidence, observation, and hypothesis?

- **DECISION:** They are three structurally different things. **Evidence** is a link from a memory to a transcript. **Observation** is a memory at `tier = observed` whose content is a pattern and which carries ≥N evidence links. **Hypothesis** is a memory at `tier = hypothesised` whose content is an interrogative (`Q521`), which is never asserted and expires. The schema makes it impossible to use one as another.
- **BECAUSE: POSITION.** `P§4`: "The grammar of storage enforces the epistemics."
- **REJECTED:** No separate tiers, with narrative summaries collapsing experiences into a persona account (the surveyed answer). It is the collapse `P§4` and `P§2` jointly refuse.
- **COST:** As `Q14`.
- **CONFIDENCE:** high

---

### Q788 — How should the system choose which person's memory or topic schema to inspect?

- **DECISION:** There is one person and no topic schema (`E1`, `Q802`). The question dissolves. The analogous real decision — which entity a query concerns — is resolved by entity matching in retrieval, not by an LLM selecting a card.
- **BECAUSE: POSITION.** `P§1` principle 2 and `P§5` leave one subject.
- **REJECTED:** An LLM agent selecting person-cards from query cues. It wins for a multi-subject memory, which is the design `Q11` rejects.
- **COST:** As `Q11`.
- **CONFIDENCE:** high

---

### Q814 — When a remembered statement refers to a time other than when it was said, which clock should organize it?

- **DECISION:** Event time organises the fact; system time organises decay and audit. Both stored, never conflated (`Q172`, `Q799`).
- **BECAUSE: POSITION.** `P§4`'s episode example carries an event date distinct from the telling; `P§9`'s decay window is a system-time window.
- **REJECTED:** Dialogue time only. See `Q172`. The inventory marks this load-bearing, and it is: getting it wrong makes every temporal answer subtly wrong.
- **COST:** As `Q799` — date-parsing errors are permanent and silent unless flagged approximate.
- **CONFIDENCE:** high

---

### Q815 — What should be the atomic durable representation of an event-level memory?

- **DECISION:** A typed episode memory: a natural-language statement of what happened, with `event_time`, linked entities, tier, evidence, and source transcripts. Not a temporal knowledge-graph quad.
- **BECAUSE: POSITION.** `P§4`'s Episode example is a sentence with a date. `P§9` requires it to be readable on the memory surface.
- **REJECTED:** A (subject, relation, object, time) TKG fact with the graph as an index. It wins on temporal query precision and multi-hop reasoning, which are genuine weaknesses here (`Q752`, `Q570`). It loses on the surface requirement (`Q569`).
- **COST:** Temporal queries operate over sentence-shaped memories with a date field rather than over a temporal graph, so "what changed between March and May" is weak.
- **CONFIDENCE:** medium

---

### Q818 — What kinds of durative abstraction should be constructed from a cluster of episodes?

- **DECISION:** None. No topic summaries, and emphatically no persona summaries. The only abstraction is the observed tier (`Q747`).
- **BECAUSE: POSITION.** `P§2` for the persona half — "persona captures stable traits, preferences, and behavioral patterns" is the profile, verbatim. `Q154` for the topic-summary half.
- **REJECTED:** Topic plus persona summaries. The inventory marks persona summaries "load-bearing for preference questions" — meaning the system measurably answers preference questions better with them. **That is a direct performance cost of a position-driven refusal, and preference questions are one of Kivi's three memory types.** The mitigation is that Kivi stores preferences as first-class typed memories rather than needing to infer them from a persona, which should recover most of the gap — but it is a claim to test, not assume.
- **COST:** Preference questions that require aggregation across many weak signals will answer poorly, where a persona summary would have handled them.
- **CONFIDENCE:** medium

---

### Q819 — What should determine which episodes belong to the same durative memory?

- **DECISION:** Nothing — there are no durative memories (`Q818`). Episodes relate through shared entities and time, both queryable, never clustered.
- **BECAUSE: POSITION.** `P§4`'s ontology has no durative type.
- **REJECTED:** Time-sliced GMM clustering over entity-name embeddings. See `Q802`.
- **COST:** As `Q818`.
- **CONFIDENCE:** high

---

### Q831 — What should count as a reusable memory unit: an episode, a claim, a pattern, or a procedure?

- **DECISION:** A claim (any of three types) or a pattern (a claim at observed tier). Not an episode-as-trajectory, not a procedure.
- **BECAUSE: POSITION.** `P§4`.
- **REJECTED:** One completed trajectory as one episodic record. Wins for agent case retrieval (`Q463`).
- **COST:** As `Q235`.
- **CONFIDENCE:** high

---

### Q832 — What should determine whether a stored experience is treated as trustworthy?

- **DECISION:** Its tier, which is determined by its provenance — did the user say it, or did Kivi observe it, or is it a proposed reason. Not a success label, not source-agent metadata.
- **BECAUSE: POSITION.** `P§4`'s tier table maps origin to permission. "Trustworthy" in this system means "sourced from the user," not "worked last time."
- **REJECTED:** A `final_success` label distinguishing successful from unsuccessful runs. It wins for procedural memory; `Q704` removes the success signal entirely.
- **COST:** As `Q704` — no quality signal.
- **CONFIDENCE:** high

---

### Q837 — When the Coach intervenes, what form and authority should guidance have?

- **DECISION:** There is no coach. The nearest analogue is a **Koottu observation**, and its authority is deliberately minimal: it is appended to the answer as an observation with evidence, it does not alter what Kivi does, and the user may ignore it. It is never injected as a system message that changes behaviour.
- **BECAUSE: POSITION.** `P§4`: observations are surfaced "as an observation with its evidence. **Never as a rule.**" `P§6`: Koottu "Says: the pattern, as an observation you can act on or ignore."
- **REJECTED:** Synchronously appending actionable guidance as a system message before the next action. It wins for task performance. It is precisely "silently enforces things you never agreed to."
- **COST:** Observations change nothing unless the user acts. Kivi can watch the user repeat a mistake and only mention it.
- **CONFIDENCE:** high

---

### Q843 — What happens to source material after a summary is stored, and how can a downstream consumer verify it?

- **DECISION:** No summary is stored; source material is retained permanently and every memory links to it; a consumer verifies by following `source_transcript_ids[]` to the immutable transcript, one tap away in the UI and one field away in the API.
- **BECAUSE: POSITION.** `P§9`. The inventory's note on the surveyed system — "claim-to-source traceability and user-facing provenance are underspecified" — is the gap this position exists to close.
- **REJECTED:** Retaining logs for replay while leaving claim-to-source traceability unspecified. It wins on engineering reproducibility without the UI cost. It fails the normal-user half of `P§8`.
- **COST:** As `Q28` — the raw store holds what the memory store refuses.
- **CONFIDENCE:** high

---

### Q844 — What is the unit of ingestion — the thing that gets processed as one indivisible input?

- **DECISION:** One transcript record, carrying its own `occurred_at` (`Q480`, `Q667`).
- **BECAUSE: ENGINEERING (E3).**
- **REJECTED:** A single typed message with its own reference time — which is nearly the same answer at a finer grain. It wins for message-stream products. For dictations, the transcript is the message.
- **COST:** As `Q374`.
- **CONFIDENCE:** high

---

### Q847 — What does an entity carry besides its name?

- **DECISION:** Canonical name, aliases (including ASR variants), type, typed relations to other entities, `first_seen_at`, and links to the memories that mention it. **Not** an LLM-generated free-text summary.
- **BECAUSE: POSITION.** `P§4` defines entities by their relations. An entity summary is `P§2`'s profile at entity scope — and for a third-party entity like Priya it is precisely the characterisation `P§5` forbids.
- **REJECTED:** An LLM-generated entity summary regenerated on merge (the surveyed answer). It wins on retrieval — an entity summary is an excellent retrieval target for "tell me about Atlas," which `Q850` identifies as a hard query. For **project** entities that argument is strong and the privacy objection does not apply. For **person** entities it is forbidden. Splitting the rule by entity type would be defensible; I am not splitting it, because a rule that permits summaries of projects but not people is one refactor away from summarising people. Noted as a deliberate over-restriction.
- **COST:** "Tell me about Atlas" has no summary to answer from (`Q850`).
- **CONFIDENCE:** medium

---

### Q848 — How is time represented?

- **DECISION:** Bi-temporally but asymmetrically: **event time** as a point plus an optional validity end when the transcript states one; **system time** as `first_seen_at`, `last_seen_at`, `last_confirmed_at`, plus status transitions with timestamps. Not a full four-field bi-temporal model with transaction and validity intervals on every row.
- **BECAUSE: POSITION** for which fields must exist (`P§4`'s schema, `P§9`'s decay); **ENGINEERING** for declining the full model — `E5`, since supersession plus status already answers "what did we believe then."
- **REJECTED:** Full bi-temporality with created/expired transaction times and valid/invalid event times (the Zep/Graphiti model). It wins for auditing "what did the system believe at time T," which is a real evaluation question and arguably one the brief's reviewer would like to ask. It is the strongest rejected alternative here.
- **COST:** "What did Kivi believe on 1 May?" can only be reconstructed from the status-transition log, not queried directly. That reconstruction is possible but awkward.
- **CONFIDENCE:** medium

---

### Q860 — Is provenance available to whoever consumes the memory?

- **DECISION:** Yes — in the store, in the retrieval result, in the generator context, in the API response, and in the UI. Structural availability is not sufficient; it must reach the consumer.
- **BECAUSE: POSITION.** `P§9`: "Every memory shows its provenance." The surveyed failure — "structurally yes… but it is absent from the generator context" — is exactly the gap: provenance the generator cannot see is provenance the answer cannot cite, which makes `P§8`'s "which memories produced each answer" unanswerable.
- **REJECTED:** Structural-only provenance. It wins on prompt size (`Q734`). It defeats the purpose.
- **COST:** Larger prompts and payloads throughout (`Q433`).
- **CONFIDENCE:** high

---

### Q863 — Which model constructs the graph?

- **DECISION:** The pinned extraction model (`Q531`), at temperature 0, producing typed entity and relation candidates that deterministic code then resolves against the existing store (`Q483`). The model proposes; code disposes (`Q533`).
- **BECAUSE: ENGINEERING (E2)**, with **POSITION** forcing the propose/dispose split (`P§2`).
- **REJECTED:** A single small model constructing the graph end to end with no deterministic resolution layer. It wins on cost and simplicity, and is what most systems do. It makes entity identity a per-call model decision, which breaks idempotence and makes merges unauditable.
- **COST:** A resolution layer to build and tune (`Q413`, `Q483`), and a new class of bug (false merges) that model-only construction would have had in a different form.
- **CONFIDENCE:** high

---

## Stage: STORAGE

---

### Q07 — When result tables are compared, which differences should count: values alone, duplicate counts, column identity, or ordering?

- **DECISION:** As posed (SQL equivalence checking) this is **out of scope** — there is no translation layer to verify. The decision it forces in this system is the **sameness test for memories**: two memories are the same if they assert the same fact about the same subject, judged by content equivalence, not by string identity, ordering, or duplicate count. Sameness is decided by the two-stage test in `Q729`.
- **BECAUSE: ENGINEERING (E5)** for the out-of-scope half; the sameness half follows from `Q159`, which is `POSITION`-forced by `P§4`'s `evidence_count`.
- **REJECTED:** Exact content-hash equality as the only sameness test (the surveyed answer at document level). It wins on determinism and auditability — hash equality is never wrong. It cannot merge "Priya is the client contact" with "Priya Raghavan handles the Acme account," which is the whole point of evidence accumulation.
- **COST:** Sameness is model-judged and therefore fallible in both directions (`Q479`).
- **CONFIDENCE:** high

---

### Q31 — When graph and relational schemas differ, who or what determines which records mean the same thing?

- **DECISION:** Not applicable as posed — one schema, one store (`Q416`). The analogous real decision: **write-time resolution** using hybrid candidate search then an LLM verdict, with the verdict recorded (`Q483`). Not a user-supplied transformer, not read-time reconciliation.
- **BECAUSE: ENGINEERING (E2)** for the single schema; **POSITION** for write-time resolution — `P§7` requires canonical spellings to be resolved *before* the dictation path reads them, so resolution cannot be deferred to read time.
- **REJECTED:** Read-time reconciliation. It wins because it is reversible — a bad match costs nothing permanent. That is a genuine advantage given `Q413`'s cost note, and the condition under which it wins is if false merges prove common in the corpus.
- **COST:** As `Q413` — premature resolution, hard to unwind.
- **CONFIDENCE:** medium

---

### Q52 — Should all product surfaces have the same memory access, or should access rights depend on the interaction contract?

- **DECISION:** Rights depend on the contract, structurally. Dictation: entity, lexical, and stated formatting preferences only. Hey Kivi: all types, tier-gated by the dial. Two paths, not one path with a parameter (`Q138`, `Q270`).
- **BECAUSE: POSITION.** `P§7`: "dictation is a transcription contract. You said words; you expect those words back, correctly spelled. A dictation surface that starts noticing patterns in your writing has broken the contract." And: "two separate retrieval paths, not one path with a filter."
- **REJECTED:** Uniform access across surfaces (the surveyed answer, and what every framework does). It wins on architectural economy. It is the brief's explicit test: "Decide what belongs in each mode and make that boundary coherent in the product."
- **COST:** Duplicated retrieval code (`Q138`), and the rule is subtler than "two paths" (`Q270`, **Section A**).
- **CONFIDENCE:** high

---

### Q68 — When memory contains near-duplicates, redundant patterns, or stale episodes, what should remain stored?

- **DECISION:** Everything remains stored. Near-duplicates merge into one memory with accumulated evidence (`Q159`); redundant patterns are one observation with a higher count; stale episodes keep their rows and lose only surfacing standing if they are observations. No clustering-based consolidation, no deletion.
- **BECAUSE: POSITION.** `P§9`: supersession keeps history; removal is the user's. `P§4`: demotion and supersession "are not deletions."
- **REJECTED:** Aggressive cluster merging into LLM gists. The inventory's note is worth quoting back: its own source "finds aggressive cluster merging destructive." That is independent evidence for the conservative choice, not just a position-driven one.
- **COST:** As `Q54` — unbounded growth.
- **CONFIDENCE:** high

---

### Q90 — Should the local database or cloud be authoritative?

- **DECISION:** Local, and exclusively local. One embedded database is the sole authority. No cloud replication, no sync, no shared access.
- **BECAUSE: ENGINEERING (E2, E1).** The brief permits hosted arrangements but requires one declared primary review method that a coding agent can reproduce. Local embedded is the arrangement with the fewest failure modes for that agent.
- **REJECTED:** Local-authoritative with opt-in cloud replication. It wins for a real product with multiple devices. It adds configuration surface to `RUN.md` for a capability the review never exercises.
- **COST:** Single-device, no backup story, no multi-device continuity.
- **CONFIDENCE:** high

---

### Q103 — On re-ingesting the same content, does the system dedupe, version, or duplicate?

- **DECISION:** Dedupe — idempotent on `transcript_id` (`Q08`, `Q180`). Never duplicate.
- **BECAUSE: POSITION.** `P§AppC` claim 6 requires reprocessing to be a defined operation.
- **REJECTED:** Duplicate (the surveyed answer, and the most common accidental behaviour). Wins never.
- **COST:** As `Q08` — determinism requirements on extraction.
- **CONFIDENCE:** high

---

### Q121 — Is multi-user separation a namespace column, separate database, or authorization boundary?

- **DECISION:** None of them. One user, one database, no separation mechanism (`E1`, `Q82`).
- **BECAUSE: ENGINEERING (E1).**
- **REJECTED:** A namespace column, which is the cheapest forward-compatible option and would cost almost nothing now. It wins if multi-user is ever likely. I am declining even the cheap version because an unused namespace column invites the assumption that isolation exists when nothing enforces it — which is worse than its obvious absence.
- **COST:** Multi-tenancy is a schema-wide migration later (`Q82`).
- **CONFIDENCE:** high

---

### Q146 — How are duplicates defined and resolved?

- **DECISION:** Three levels. **Transcript:** same `transcript_id` → ignored. **Candidate within one extraction:** normalised exact match → collapsed. **Memory across transcripts:** similarity candidates → LLM sameness verdict → merge with evidence increment and source append (`Q729`).
- **BECAUSE: POSITION** for the third level (`P§4`'s `evidence_count` and `source_transcript_ids[]`); **ENGINEERING** for the first two.
- **REJECTED:** Only within-response normalised deduplication (the surveyed answer). It wins on determinism and avoids false merges entirely. It makes cross-transcript evidence accumulation impossible, and `P§AppC` claim 3 depends on it.
- **COST:** As `Q479`.
- **CONFIDENCE:** high

---

### Q157 — Should short or trivial utterances be permanently dropped, stored raw but not indexed, or retained as episode context?

- **DECISION:** Stored raw always (`Q555`), and simply yield no memory. Triviality is not a separate gate: a short utterance either contains an eligible fact or it does not, and the four gates decide. No length heuristics, no pattern-based triviality detection.
- **BECAUSE: POSITION.** `P§3`'s test is about durability and work-relevance, not length. `P§AppA` requires "transcripts that produce nothing" to exist as an identifiable outcome (`Q171`), which a triviality pre-filter would conflate with "was never looked at."
- **REJECTED:** Fixed triviality patterns with language-dependent length checks. It wins on extraction cost — skipping obviously empty transcripts saves LLM calls, which the cost report would reflect. That is the one real argument for it and it is measurable.
- **COST:** ~500 extraction calls including on transcripts that obviously yield nothing (`Q170`, `Q532`).
- **CONFIDENCE:** medium

---

### Q158 — Should inactive duplicates be deleted or retained with lineage?

- **DECISION:** Retained with lineage. Merged-away and superseded rows keep `status`, a pointer to the survivor, and their original sources. Retrieval sees only active rows (`Q88`).
- **BECAUSE: POSITION.** `P§9`: "the superseded version stays in history so the change is auditable."
- **REJECTED:** Deletion of inactive duplicates. It wins on storage and on a cleaner forget story (`Q309`). The audit requirement outweighs it.
- **COST:** As `Q88` — every read must filter by status, and a missed filter is the most likely retrieval bug.
- **CONFIDENCE:** high

---

### Q200 — Legible files or transactional DB as truth?

- **DECISION:** The transactional database is truth. Not Markdown files.
- **BECAUSE: ENGINEERING (E2, E4).** Position is silent. The database is required for status transitions, suppression enforcement, and atomic compound writes (`Q341`); files cannot enforce a status filter, and the brief asks for "the database schema and migrations" as an artefact.
- **REJECTED:** Markdown-in-git as primary with the database derived. It is a genuinely attractive design for inspectability — `P§9`'s legibility goal and `P§8`'s dual-audience trace are both served by human-readable truth, and git gives supersession history for free. It wins if the inspection surface were the filesystem. It loses because `P§9` says the inspection surface is the product, not a directory.
- **COST:** Truth is not human-readable without the app. A reviewer inspecting "memory state" needs the UI or SQL, which `RUN.md` must document explicitly (the brief requires "where evaluation results and memory state can be inspected").
- **CONFIDENCE:** high

---

### Q202 — Separate stores per memory kind or one polymorphic table?

- **DECISION:** One polymorphic memory table with `type` and `tier`, plus a separate entities table and separate tables for transcripts, drop logs, suppressions, and events (`Q551`).
- **BECAUSE: POSITION** for the tier/type columns (`P§4`); **ENGINEERING** for the polymorphism.
- **REJECTED:** Separate stores per kind. It wins because it would make `P§7`'s "no access to the observation or hypothesis tables" literally true at the table level (`Q551`). That is a real loss and the mitigation — enforcing at the query/grant layer — is a weaker demonstration of `P§AppC` claim 7.
- **COST:** As `Q551` — claim 7 is demonstrated at the query layer, not the table layer.
- **CONFIDENCE:** medium

---

### Q207 — How are delivery duplicates handled?

- **DECISION:** A stable key per candidate — `(transcript_id, candidate_index)` — with the memory write and the processed-marker committed in one transaction (`Q341`). No at-least-once downstream effects, because there are no downstream effects outside the transaction except embeddings, which are idempotent by key.
- **BECAUSE: ENGINEERING (E2, `Q08`).**
- **REJECTED:** At-least-once downstream with a completion marker. It wins for distributed pipelines. Here the transaction covers it.
- **COST:** As `Q341` — a long transaction per transcript.
- **CONFIDENCE:** high

---

### Q217 — Should causal-effect magnitude be stored outside the graph or attached directly to graph statements?

- **DECISION:** Neither — no causal effects are stored (`Q215`, `Q214`). **Out of scope.**
- **BECAUSE: POSITION.** `P§4`: hypotheses are questions, never claims to be quantified.
- **REJECTED:** Attaching effect properties to causal relations. Wins in a causal product.
- **COST:** None here.
- **CONFIDENCE:** high

---

### Q262 — When new information overlaps or conflicts with stored memory, should the system append, merge, replace, version, or ask?

- **DECISION:** Four distinct behaviours, selected by relationship, never by a general policy. **Same fact, new source:** merge (evidence + source). **Contradicting fact:** replace current, version the old as superseded. **Related but distinct:** append as a new memory. **Contradiction involving a stated memory:** do not resolve — surface it under Koottu and, if it is high-value, spend a confirmation prompt (`Q174`, `Q269`).
- **BECAUSE: POSITION.** `P§9` (supersede + version), `P§4` (user authority over stated), `P§8` (budgeted asking).
- **REJECTED:** A single general update policy with underspecified conflict semantics (the surveyed answer, and the inventory's most frequent gap). It wins nowhere; the four cases genuinely behave differently and collapsing them produces either lost history or stacked contradictions.
- **COST:** Four paths to implement and test, and the classifier that routes between them is another fallible model decision.
- **CONFIDENCE:** high

---

### Q264 — How should the system avoid repeatedly paying to reconstruct prior reasoning?

- **DECISION:** It should not try. Each request re-retrieves from scratch (`Q250`, `Q251`). The only caching is deterministic and content-addressed: embeddings are cached by content hash, and extraction is idempotent so it never re-runs on unchanged input.
- **BECAUSE: POSITION.** `P§8`'s trace must fully explain each answer; a session cache means an answer depends on state that is not in its own trace. Caching *reasoning* would be the strongest version of this problem.
- **REJECTED:** Session caching with prefix inheritance and LTM preloading. It wins on cost and latency, both of which the brief asks to be reported — so this decision costs measurable, reportable resources. The condition under which it wins: if per-request retrieval latency proves user-hostile, which at a few hundred memories it should not.
- **COST:** Higher per-request cost and latency than a cached design, and the report will show it.
- **CONFIDENCE:** high

---

### Q265 — Where should short-lived and persistent memory physically live?

- **DECISION:** Persistent memory in the embedded database, including vectors (`Q155`, `Q447`). Short-lived per-request state in process memory, discarded at request end (`Q538`). No Redis, no separate vector service.
- **BECAUSE: ENGINEERING (E2).**
- **REJECTED:** RAM/Redis for session state plus a vector database for LTM. It wins at scale and for multi-process deployment. Two more processes in `RUN.md`.
- **COST:** As `Q447` — no scale path.
- **CONFIDENCE:** high

---

### Q276 — How many confidentiality states should stored memory have, and what should distinguish them?

- **DECISION:** One. Everything stored is the user's and is equally confidential; there is no shared state and no second reader (`E1`, `Q273`). Confidentiality is handled by what is **never stored**, not by states within the store.
- **BECAUSE: POSITION.** `P§5`'s boundary is at the write path, not at a visibility flag: "It does not enter the write path." A private/shared distinction presumes material that could be shared.
- **REJECTED:** Two tiers, private and shared. It wins for a collaborative product. Note the subtle point: introducing a "private" state implies the default is not private, which inverts this product's premise.
- **COST:** As `Q273`/`Q185` — no consent model to extend.
- **CONFIDENCE:** high

---

### Q282 — Should repeated observations automatically become authoritative, remain probabilistic, or require explicit confirmation?

- **DECISION:** Explicit confirmation (`Q191`, `Q149`, `Q324`). They do not remain probabilistic either — there is no probability, only tier.
- **BECAUSE: POSITION.** `P§4`: "Nothing self-promotes."
- **REJECTED:** Remaining probabilistic. See `Q42`.
- **COST:** As `Q191`.
- **CONFIDENCE:** high

---

### Q301 — F8 — Accumulate memory across repeated/evolving query blocks (D13)

- **DECISION:** Memory accumulates monotonically across the corpus and is never reset between queries or sessions. The evaluation, by contrast, **does** control for this: claim-specific tests run against a stated memory state, and the state is reported.
- **BECAUSE: ENGINEERING (E3, E4).** Position is silent. Accumulation is the product's normal behaviour; the evaluation discipline is `E4` — an evaluation whose results depend on undisclosed accumulated state is not evidence.
- **REJECTED:** A fresh store per evaluation state. The inventory's note is right that "a fresh store per state would test a different phenomenon" — and both phenomena matter. The compromise: the product accumulates, the evaluation reports the state it ran against.
- **COST:** Evaluation results are state-dependent and must be reported with their state, which makes them harder to summarise.
- **CONFIDENCE:** high

---

### Q302 — F9 — Reuse overlapping or semantically related queries (dataset design)

- **DECISION:** The evaluation set deliberately includes both overlapping and non-overlapping queries, and reports them separately. A headline number that averages over both would hide whether the system works or is merely reusing.
- **BECAUSE: POSITION.** `P§AppC` requires each claim to be "provable from the evaluation output," which means per-claim reporting rather than an aggregate. The brief adds: "whether the conclusions follow from the evidence."
- **REJECTED:** Designing the set for reuse opportunity, which is what produces headline resource-saving results. It wins for a paper. It would be the exact "corpus generated to flatter the system" failure `Q370` already worries about.
- **COST:** Lower headline numbers, more reporting complexity.
- **CONFIDENCE:** high

---

### Q311 — When two memories overlap, should the system keep both, delete one, or synthesize a replacement—and how much detail should survive?

- **DECISION:** Keep one and accumulate — merge into the existing memory, increment evidence, append the source, keep the clearer wording. Never synthesize a new replacement that loses the original wording, and never delete the merged-away row (`Q158`).
- **BECAUSE: POSITION.** `P§9` (keep history) and `P§4` (`evidence_count` exists to accumulate).
- **REJECTED:** Classify-as-redundant, merge details into a new insight, delete the old (the surveyed answer). It wins on conciseness and produces better-worded memories. It deletes, which `P§9` forbids, and synthesizing a new insight from two makes the result a model artefact with no single source (`Q33`).
- **COST:** Merged memories keep one wording that may be worse than a synthesis. Detail present in the losing wording is lost unless it created a separate memory.
- **CONFIDENCE:** medium

---

### Q375 — Should repeated input be appended, rejected, or coalesced?

- **DECISION:** Rejected at transcript level (idempotent, `Q103`); coalesced at fact level (merge with evidence, `Q311`). Never blindly appended.
- **BECAUSE: POSITION** for the fact level; **ENGINEERING** for the transcript level.
- **REJECTED:** Buffer-merge-and-replace semantics. Wins for streaming message buffers; not the shape of this input.
- **COST:** As `Q479`.
- **CONFIDENCE:** high

---

### Q377 — Should durable truth be an opaque database or inspectable files?

- **DECISION:** A database, made inspectable through the product's own surfaces rather than through the filesystem (`Q200`). The vector index is explicitly disposable (`Q155`); the database is not.
- **BECAUSE: ENGINEERING (E2)**, with **POSITION** determining where inspection lives — `P§9`: "No developer console anywhere in this. The Why panel and the memory surface are the whole inspection story, and they're built for the person."
- **REJECTED:** Markdown as truth with SQLite as coordination. See `Q200` — the strongest rejected alternative in the storage stage.
- **COST:** As `Q200`.
- **CONFIDENCE:** high

---

### Q383 — Should predicted future needs be stored?

- **DECISION:** No. No foresight, no anticipation, no predictive memory of any kind.
- **BECAUSE: POSITION.** `P§2`'s soft-failure warning: "'You've been dictating late, you must be behind.' Possibly true. Also possibly none of Kivi's business, and stored as a durable belief." A prediction about the user's future needs is that inference pointed forwards.
- **REJECTED:** Storing extracted foresight. It wins for proactive assistance — a genuinely valuable product direction. Note the surveyed system built it and then **shipped it disabled** because it cost one LLM call per sender per unit "for data no route or consumer used." That is an independent, non-ideological reason for the same answer, and it is worth recording that the position and the economics agree here.
- **COST:** Kivi is never proactive. It cannot surface "the Atlas review is Thursday and you haven't drafted the deck."
- **CONFIDENCE:** high

---

### Q410 — When two implementations are compared, should correctness mean agreement on present examples or agreement on every admissible database?

- **DECISION:** Out of scope as posed. The analogous evaluation decision: correctness means **agreement with the source transcripts**, checked on the specific cases the evaluation runs, with false-negative rates estimated by sampling (`Q429`) rather than claimed universally.
- **BECAUSE: ENGINEERING (E5)** for the out-of-scope half; `Q429` for the sampling half.
- **REJECTED:** Universal equivalence claims. It wins in formal verification where it is achievable. Claiming it for an LLM pipeline would be dishonest, and the brief penalises conclusions that outrun evidence.
- **COST:** No universal correctness guarantee. Every quality claim is empirical and sampled.
- **CONFIDENCE:** high

---

### Q414 — Which conditions should determine the admissible database states: basic structural integrity or application-specific invariants too?

- **DECISION:** Both, and the application invariants are enforced in the schema wherever possible: `tier` and `type` and `status` as constrained enums; `source_transcript_ids` non-empty (a memory cannot exist without provenance, `Q86`); a `hypothesised` memory's content must be interrogative (`Q521`); foreign keys on every link; not-null on every required field.
- **BECAUSE: POSITION.** `P§4`: "The grammar of storage enforces the epistemics." That sentence asks for application invariants to live in the schema, not in application code.
- **REJECTED:** Structural constraints only, with invariants enforced in application code. It wins on flexibility during development. It loses the thing `P§4` claims: that you *cannot* accidentally use a question as a fact.
- **COST:** Schema constraints make migrations and test-data setup stricter, and a legitimate edge case that violates an invariant cannot be stored at all.
- **CONFIDENCE:** high

---

### Q431 — When comparing translators, should evidence prioritize feature coverage, correctness within overlap, or equal-budget end-to-end usefulness?

- **DECISION:** Out of scope as posed. The analogous decision — how to compare this system against anything — is answered in `Q477`/`Q585`: **no comparison against external baselines**, because the failure classes that matter are invisible to every published benchmark. What is reported is per-claim pass/fail plus the brief's metrics.
- **BECAUSE: POSITION.** `P§AppC`.
- **REJECTED:** An equal-budget end-to-end comparison against a baseline memory system. It wins on credibility with a technical reviewer and would be genuinely informative about retrieval quality. It loses because any baseline would win on accuracy by doing the things this position forbids, and reporting that without heavy caveats would misrepresent the trade.
- **COST:** No external reference point. A reviewer cannot tell whether the retrieval is good or merely defensible.
- **CONFIDENCE:** medium

---

### Q434 — Are repeated facts deduplicated or accumulated as evidence?

- **DECISION:** One belief plus an evidence count and a source list — the third option, explicitly (`Q159`, `Q146`).
- **BECAUSE: POSITION.** `P§4`'s schema names both `evidence_count` and `source_transcript_ids[]`, which only coexist under this answer.
- **REJECTED:** Preserving every mention as a separate record. It wins on provenance fidelity and makes merges reversible (`Q173`). Rejected because the memory surface would then show twenty copies of one belief.
- **COST:** As `Q173` — merges are hard to unwind.
- **CONFIDENCE:** high

---

### Q443 — When information is admitted, at what granularity should it be indexed?

- **DECISION:** Two fixed granularities, not adaptive: **memory-level** indexing (lexical + vector) for the primary path, and **transcript-level** lexical indexing for the fallback path (`Q211`). No multi-resolution adaptive selection.
- **BECAUSE: ENGINEERING (E5).** Position is silent on indexing. Two levels are what the two retrieval paths need; a third would need a consumer.
- **REJECTED:** Multi-granularity indexing with adaptive resolution selection. It wins on recall across query types and its source argues sentence- or session-level alone is inadequate — which is a direct challenge to this choice. It is the obvious upgrade if evaluation shows recall gaps.
- **COST:** Queries whose right granularity is neither memory nor whole transcript (a paragraph, a topic span) are served badly.
- **CONFIDENCE:** medium

---

### Q449 — When two records overlap but do not clearly contradict, should they merge, coexist, or remain linked?

- **DECISION:** Coexist as separate memories, linked only through shared entities. Merge only on a positive sameness verdict; never merge on mere overlap. Ambiguity resolves toward keeping both.
- **BECAUSE: POSITION.** `P§9`'s per-entry actions require each belief to be separately correctable. A speculative merge removes one belief the user might have wanted to correct independently; the reverse error (two rows that should be one) is visible and fixable.
- **REJECTED:** Merging on overlap with periodic consolidation. It wins on tidiness and on a shorter memory surface. It makes false merges the default failure direction, which is the harder one to unwind (`Q173`).
- **COST:** The memory surface will contain near-duplicates that a user perceives as the system not understanding that two things are the same.
- **CONFIDENCE:** high

---

### Q490 — What should happen to memory as time passes without confirmation or repetition?

- **DECISION:** Observations decay out of surfacing; hypotheses expire and are dropped; stated memories persist unchanged (`Q283`). Memory is never reset between evaluation trials except where the evaluation explicitly states a fresh state (`Q301`).
- **BECAUSE: POSITION.** `P§9`.
- **REJECTED:** Leaving aging underspecified and resetting memory each trial (the surveyed answer — and the inventory notes experiments reset memory each trial, which quietly avoids the question). It wins for clean experiments. It is exactly the avoidance `Q301` refuses.
- **COST:** As `Q24` — unset windows.
- **CONFIDENCE:** medium

---

### Q517 — Who decides what is salient enough to store?

- **DECISION:** Nobody decides salience. Deterministic gates decide **eligibility** (`Q307`), and eligibility is about category and subject, not importance (`Q721`, `Q681`).
- **BECAUSE: POSITION.** `P§3`'s two tests are about repetition-cost and recording-discomfort. Neither is salience, and `P§2` makes judging what matters about a person a characterisation.
- **REJECTED:** An untyped, uncapped LLM prompt asking for salient facts (the surveyed answer, and by far the most common design in the field). It wins on recall and on implementation speed — it is one prompt. Its two named flaws, untyped and uncapped, are precisely what `P§4`'s schema and `Q307`'s gates fix.
- **COST:** As `Q721` — trivia accumulates, and there is no importance signal for ranking (`Q100`).
- **CONFIDENCE:** high

---

### Q536 — On what basis should memory be split into stores?

- **DECISION:** By **role**, not by origin or kind: an authoritative memory store, an immutable provenance store, and a disposable index (`Q481`). Origin is a column (`Q150`), not a store boundary.
- **BECAUSE: POSITION.** `P§9` forces the provenance store to be separate and immutable; `P§4` keeps types in one store.
- **REJECTED:** Splitting by origin. It wins when origins have genuinely different rights — which, note, is nearly true here: user-authored versus third-party content do have different rights. But the third-party split is enforced by never writing (`Q342`), not by a separate store, so an origin split would be a store for something that does not exist.
- **COST:** None material.
- **CONFIDENCE:** high

---

### Q550 — Should tool calls/results/reasoning be stored alongside conversational text?

- **DECISION:** In the **trace**, yes — tool calls, results, retrieved and withheld sets, and the assembled context are all recorded per answer, because `P§8` requires them. In **memory**, never (`Q12`, `Q198`). The trace and the memory store are different things with different retention rules, and the product must say so.
- **BECAUSE: POSITION.** `P§8` for the trace; `P§4`'s tiers for the memory exclusion.
- **REJECTED:** Storing tool material in the same store as conversational text. It wins for agent debugging in one place. It would put untiered material in the memory table, where a retrieval bug could surface it as a belief.
- **COST:** Two stores with different rules, a divergence the README must explain (`Q198`). Also: the trace accumulates and is never decayed, so "database growth" is driven as much by traces as by memories.
- **CONFIDENCE:** high

---

### Q567 — How is it represented and stored?

- **DECISION:** Duplicate of `Q202`/`Q551`. One polymorphic memory table with type and tier; separate entity, transcript, drop-log, suppression, and event tables.
- **BECAUSE: POSITION.** `P§4`.
- **REJECTED:** See `Q202`.
- **COST:** See `Q202`.
- **CONFIDENCE:** medium

---

### Q574 — When the same entity or proposition appears repeatedly, what should determine whether records merge, accumulate, reinforce, or remain separate?

- **DECISION:** A documented three-step rule for entities (`Q483`) and a documented two-stage rule for propositions (`Q729`), both producing recorded verdicts. Repetition accumulates evidence and never reinforces standing (`Q682`).
- **BECAUSE: POSITION.** `P§4`'s "Nothing self-promotes" for the reinforcement half; the rest is `ENGINEERING`.
- **REJECTED:** Leaving identity resolution, deduplication, and evidence aggregation unspecified — which is what the surveyed source does and what most do. It is not a rival design; it is the absence of one, and it is the single most common gap across the 45 sources.
- **COST:** As `Q413`/`Q479`.
- **CONFIDENCE:** high

---

### Q627 — When the same memory is shared among conversations, what should happen when it is edited at the source or destination?

- **DECISION:** There is one memory store and no copies, so there is no source/destination distinction. An edit applies to the one row and affects every future retrieval immediately. No copy-by-reference, no synchronisation problem.
- **BECAUSE: POSITION.** `P§9`: the user changes "what Kivi thinks about them **in one action**." A copy model would mean one action does not necessarily change what Kivi thinks.
- **REJECTED:** Copy-by-reference with synchronisation. It wins for a product with per-conversation memory scoping. It reintroduces the problem `P§9`'s one-action promise exists to eliminate.
- **COST:** No per-conversation memory scoping (`Q164`).
- **CONFIDENCE:** high

---

### Q659 — Are source files, SQLite records, or vector-index state authoritative after failure?

- **DECISION:** The database record is authoritative, always. The vector index is a rebuildable projection with no authority (`Q155`). Imported source files are not authoritative either — once imported, the stored transcript is the record, and re-importing the same file is idempotent (`Q103`).
- **BECAUSE: ENGINEERING (E2, E4).** Position is silent. The rule matters because divergence between the record and the index is a real failure (`Q344`), and the recovery procedure must be unambiguous: rebuild the index, never reconcile toward it.
- **REJECTED:** Treating source files as the driver of incremental ingest with index metadata as recoverable truth. It wins for a file-watching ingester (`Q97` declines that shape).
- **COST:** An index rebuild is an operator action documented in `RUN.md` (`Q665`).
- **CONFIDENCE:** high

---

### Q683 — How should anomalous ordering, duplicate delivery, or causal inversion affect ingestion?

- **DECISION:** Ordering anomalies do not arise — the importer sorts by `occurred_at` before processing (`Q76`). Duplicates are idempotent (`Q103`). A record with a missing or unparseable `occurred_at` is a **loud import failure**, not a quarantine, because ordering is load-bearing for supersession.
- **BECAUSE: POSITION.** `P§9`'s supersession requires a reliable ordering, so a record without one cannot be silently accepted.
- **REJECTED:** Detect-and-quarantine with a timed release. It wins for a live stream with out-of-order delivery. Its weakness — "resolution after quarantine is underspecified" — is the usual outcome, and a batch importer can simply sort instead.
- **COST:** As `Q667` — a reviewer corpus lacking usable timestamps fails to import rather than degrading. That failure must be documented with a stated fallback.
- **CONFIDENCE:** high

---

### Q731 — What should happen when the same information is encountered repeatedly?

- **DECISION:** Evidence increments, source appends, `last_seen` updates, and decay resistance improves. Nothing else — no standing change, no confidence change, no gating away of the repeat (`Q682`, `Q159`).
- **BECAUSE: POSITION.** `P§4`.
- **REJECTED:** Gating that drops redundant confirmations unless they finalise a decision. It wins on write economy. It would discard the repetitions that constitute an observation's evidence — the count *is* the product.
- **COST:** Evidence counts grow, and a mechanically repetitive corpus could inflate one observation misleadingly. Worth an evaluation check.
- **CONFIDENCE:** high

---

### Q748 — When two extracted concepts look similar, what should determine whether they are the same memory?

- **DECISION:** A similarity threshold **proposes**; an LLM verdict **decides**; the verdict is recorded (`Q729`). Embeddings are never updated by a moving average — a memory's embedding is a function of its own content, recomputable from it (`Q155`).
- **BECAUSE: ENGINEERING (E2)**, and **POSITION** for the recomputability — a rebuildable cache (`Q155`) cannot have accumulated state that recomputation would lose.
- **REJECTED:** Cosine above 0.92 merges automatically, with an exponential-moving-average node embedding. It wins on cost — no LLM call per merge. The EMA half is the specific problem: it makes the embedding path-dependent, so a rebuild produces a different index, which silently changes retrieval.
- **COST:** An LLM call per merge candidate, which shows in the cost report.
- **CONFIDENCE:** high

---

### Q807 — Can repetition alone change an item's status?

- **DECISION:** No. Never. Status changes only by user action, supersession, decay, or expiry (`Q526`, `Q149`).
- **BECAUSE: POSITION.** `P§4`: "Nothing self-promotes… Twenty is still a pattern." And: "Promotion requires an explicit user confirmation event."
- **REJECTED:** Implicit strengthening through cluster size and summary confidence — the surveyed answer, which the inventory notes bluntly: "There is no confirmation event anywhere in the system." That sentence describes the entire field. The confirmation event is this product's distinguishing mechanism.
- **COST:** As `Q191` — the stated tier grows only at the rate of budgeted prompts.
- **CONFIDENCE:** high

---

### Q821 — How should identity resolution and duplicate mentions affect an entity memory?

- **DECISION:** Unseen entity → created. Known entity → mention counted, attributes integrated only if they are permitted facts (`Q55`), aliases extended. Matching by the documented three-step rule, never left underspecified (`Q483`).
- **BECAUSE: POSITION.** `P§7` (aliases must resolve) and `P§5` (attributes limited to role and affiliation).
- **REJECTED:** Integrating attributes and evidence generally with matching criteria underspecified. The attribute half is the `P§5` violation: "integrate attributes" for a person entity is how *Priya's mother is ill* becomes an entity attribute.
- **COST:** As `Q413`.
- **CONFIDENCE:** high

---

### Q851 — What must never be stored, regardless of relevance?

- **DECISION:** Health; mood or emotional state; relationships and family; faith; politics; finances beyond work-level; any characterisation of the user's competence or character; any third-party personal content; any characterisation of a third party. Enforced by a code check before storage, with reason-coded drops logged (`Q629`, `Q169`).
- **BECAUSE: POSITION.** `P§2` verbatim, plus `P§5`.
- **REJECTED:** "Nothing; there are no content-based exclusions, sensitive categories, or privacy constraints" — the surveyed answer, and the honest description of most systems in the inventory. It wins on capability and recall. `P§2`'s four arguments are the whole answer, and the fact that this is the field's default is the reason the position exists.
- **COST:** As `Q305`/`Q442`/`Q764` — a large class of useful facts is permanently unlearnable, with no user override (`Q605`).
- **CONFIDENCE:** high

---

## Stage: RETRIEVAL

---

### Q06 — When the product has multiple interaction surfaces, should they share one retrieval path or have structurally different memory rights?

- **DECISION:** Structurally different rights, enforced by two separate retrieval paths with different data access (`Q52`, `Q138`, `Q270`).
- **BECAUSE: POSITION.** `P§7`: "two separate retrieval paths, not one path with a filter. The dictation path can only query the entity and lexical store. It has no access to the observation or hypothesis tables at all. This is enforceable in the schema and checkable in the evaluation." `P§AppC` claim 7 makes it a demonstrable commitment.
- **REJECTED:** One store, one path (the plurality answer across ten sources, and the answer nobody in the inventory disputes on merit). It wins on every engineering axis: less code, one thing to optimise, one thing to test. It loses because the brief asks for the boundary and the position makes it a proof obligation.
- **COST:** Duplicated retrieval code; the rule is subtler than two paths (`Q270`); every retrieval improvement must be made twice or deliberately once (`Q138`).
- **CONFIDENCE:** high

---

### Q18 — When a query arrives, should memory always be consulted, or should the system first decide whether retrieval is warranted?

- **DECISION:** Always consulted, on the Hey Kivi path, with no gating decision. On the dictation path, the entity/lexical lookup always runs too. There is no "should I retrieve?" step.
- **BECAUSE: POSITION.** `P§6`: "Kivi always retrieves everything it has. The dial decides what may be *said*." A retrieval-warranted gate would be a third filter that is neither the dial nor relevance, and a memory suppressed by it would leave no trace — destroying the withheld/never-retrieved distinction.
- **REJECTED:** Deciding whether to invoke memory per query. It wins on cost and latency, materially — many requests need no memory at all and pay for retrieval anyway. It is the obvious optimisation and the inventory notes one source defers it as future work. The condition under which it wins: if the gate's decision were recorded in the trace as a first-class step. That is achievable, and this is the most defensible efficiency concession available.
- **COST:** Every request pays retrieval cost and latency, reported.
- **CONFIDENCE:** medium

---

### Q19 — Which operations are idempotent, and what ordering is assumed?

- **DECISION:** Duplicate of `Q08`/`Q438`. Transcript ingestion idempotent on `transcript_id`; candidate writes keyed by `(transcript_id, candidate_index)`; ordering by `occurred_at`; writes serialised through one queue; retrieval is read-only and trivially idempotent.
- **BECAUSE: ENGINEERING (E2, E3).**
- **REJECTED:** UUID-default writes (non-idempotent under retry) — the surveyed system's own flaw. Wins never.
- **COST:** See `Q08`.
- **CONFIDENCE:** high

---

### Q23 — When a query arrives, which retrieval signals should determine candidate memory relevance?

- **DECISION:** Lexical match, dense similarity, and one-hop entity linkage determine **candidacy**. Tier, evidence, recency, and pinning determine **order** (`Q487`). Importance is not a signal (`Q100`); causal relevance does not exist (`Q215`).
- **BECAUSE: ENGINEERING for the candidacy signals; POSITION for the ordering signals** (`P§4`'s tier permissions, `P§9`'s pinning).
- **REJECTED:** Combining semantic relevance with recency and importance in one score, with a fast stage plus a slow reranker. It wins on quality and is the mainstream answer. The importance term is excluded by `P§4`; the reranker is excluded by `Q212`; the fused score is excluded by `Q393`'s calibration problem.
- **COST:** As `Q26`/`Q212` — ranking quality is capped by untuned deterministic weights.
- **CONFIDENCE:** high

---

### Q25 — Should retrieval be lexical, semantic, structural, or hybrid?

- **DECISION:** Hybrid, with all three components: lexical FTS, dense vector, and structural (one-hop entity linkage), fused by RRF then deterministically re-ranked (`Q182`, `Q209`).
- **BECAUSE: ENGINEERING.** `P§AppB` explicitly defers this. The forcing constraint is that `P§7` makes exact entity names load-bearing (weak for embeddings) while preferences are paraphrase-heavy (weak for lexical).
- **REJECTED:** Lexical-only with trigram FTS and weighted BM25. It wins on determinism, explicability, and cost — and note that it would make the Why panel's relevance explanation genuinely simple ("these words matched"). That is a real argument given `Q212`'s explicability constraint. It loses on paraphrase recall, which preference questions need.
- **COST:** Two indexes, two failure modes, and a relevance explanation that must describe rank fusion to a normal user.
- **CONFIDENCE:** high

---

### Q35 — What is retrieved and how is it ordered?

- **DECISION:** Typed memories across all three types and all tiers (unfiltered by permission), each with score components, tier, evidence, and sources; ordered by fused relevance → pinned → tier → evidence → recency; then top-k; then the disclosure filter produces the used set and the withheld set (`Q388`, `Q487`).
- **BECAUSE: POSITION.** `P§6` (retrieve everything, filter at disclosure) and `P§4` (tier ordering).
- **REJECTED:** One similarity query per type merged by backend score descending. It wins on simplicity. Merging by raw backend score across types is the `Q393` calibration error.
- **COST:** As `Q268` — retrieval work discarded on Anbu requests.
- **CONFIDENCE:** high

---

### Q36 — Is permission applied at retrieval or disclosure?

- **DECISION:** Disclosure, exclusively. Retrieval is permission-blind. The permission filter runs after ranking and produces two sets — used and withheld-with-reasons — and the withheld set never reaches the model (`Q255`).
- **BECAUSE: POSITION.** `P§1` principle 1: "What Kivi knows and what Kivi says are different questions. Retrieval and disclosure must be separable." `P§6`: "The dial governs disclosure, not retrieval… a withheld memory leaves a trace that a never-retrieved memory doesn't."
- **REJECTED:** Filtering at retrieval — the surveyed answer ("scope filters retrieval itself"). It wins on efficiency and on a smaller exposure surface. It is the single decision the position most explicitly forecloses, and `P§AppC` claim 4 exists to prove it was not taken.
- **COST:** As `Q268`.
- **CONFIDENCE:** high

---

### Q37 — Is retrieval separable from disclosure?

- **DECISION:** Yes, and separating them is the architecture. Duplicate of `Q36`/`Q268`, kept because the inventory notes both surveyed sources answer "no" — and one answers that the question is "not present," which is the more telling failure.
- **BECAUSE: POSITION.** `P§1` principle 1.
- **REJECTED:** "No. Nowhere in the repo" and "the question is not present. One path, one audience; everything retrieved is available to the answer." That second phrasing is the default assumption this position exists to break.
- **COST:** As `Q268`.
- **CONFIDENCE:** high

---

### Q39 — How should high-recall candidate retrieval and semantic ranking be divided?

- **DECISION:** Candidate generation is high-recall and cheap (lexical + vector + one-hop entity, generous per-leg limits); ranking is deterministic and applied once over the fused pool (`Q487`). Temporal constraints filter the candidate pool rather than bypassing ranking.
- **BECAUSE: ENGINEERING**, with **POSITION** forbidding a model reranker (`Q212`).
- **REJECTED:** Letting extracted time ranges bypass score ordering and return the most recent N chronologically (the surveyed answer). It wins for "what did I say yesterday" queries — which is exactly the brief's example question ("the dictation I did around 5 PM yesterday"). **This is a real and specific gap:** a purely relevance-ranked retrieval handles time-anchored recall badly. A chronological path for explicitly temporal queries is probably necessary and is the strongest case for a second retrieval mode. Flagged in **Section A**.
- **COST:** Time-anchored recall ("around 5 PM yesterday") is weak without a dedicated chronological path.
- **CONFIDENCE:** medium

---

### Q40 — When retrieved conversations are used, should their order matter?

- **DECISION:** Yes, and it is made explicit rather than incidental. Memories are presented to the generator in the deterministic rank order, grouped by type, with tier labels — and the order is recorded in the trace, so its effect on the answer is inspectable.
- **BECAUSE: ENGINEERING (E4).** Position is silent. The inventory's note on the surveyed system — "Yes, unavoidably, and it's never mentioned" — is the point: prompt order affects output in every LLM system, and leaving it unmentioned means the trace is incomplete.
- **REJECTED:** Ignoring order as an implementation detail. Wins never under `E4`.
- **COST:** Order is another variable the evaluation must hold fixed for reproducibility.
- **CONFIDENCE:** high

---

### Q43 — Which memory representations should compete for retrieval?

- **DECISION:** Memories (all types, all tiers) compete on the primary path. Raw transcripts do **not** compete — they are a labelled fallback only after a memory miss (`Q211`). No summaries or personas exist to compete (`Q816`).
- **BECAUSE: POSITION.** `P§4` makes memories the unit; `P§8`'s worked abstention shows the raw layer entering only as a named near-miss, not as a co-equal result.
- **REJECTED:** Searching a union of topic summaries, persona summaries, and raw turns with dense similarity, plus a separate temporal graph. It wins on coverage across question types — measurably, and it is the design that handles both narrative (`Q570`) and temporal (`Q39`) questions this system handles poorly. The persona half is forbidden; the rest is a genuine capability gap.
- **COST:** As `Q570` and `Q39` — narrative and time-anchored questions are the two weakest areas.
- **CONFIDENCE:** medium

---

### Q47 — How many memories should be retrieved when relevance is uncertain: a fixed top-k, an adaptive set, or abstention?

- **DECISION:** Fixed top-k for retrieval; **abstention is decided at generation**, not at retrieval. Retrieval always returns k; the generator abstains when nothing in the set supports an answer (`Q757`). The two decisions are deliberately separate.
- **BECAUSE: POSITION.** `P§8`'s abstention is about the *answer*, not the retrieval — the worked example retrieves things (Arun on Atlas backend, a March migration discussion) and still abstains on the question asked. That only works if retrieval and abstention are separate stages.
- **REJECTED:** Adaptive-k or retrieval-level abstention on a score threshold. It wins on efficiency and would give an absolute relevance signal (`Q393`). It would also make abstention a retrieval property, which would lose the "here is what I did find" half of `P§8`'s example — the most useful part of it.
- **COST:** As `Q576`/`Q859` — fixed k is wrong at both extremes; and the generator is the sole guard against answering from irrelevant top-k results, which is a prompt-enforced boundary (`Q757`).
- **CONFIDENCE:** high

---

### Q57 — When a memory becomes stale, what should change: its rank, its status, its content, or its existence?

- **DECISION:** Its **status** (observations decay out of surfacing; hypotheses expire) and, through recency, its **rank**. Never its content. Never its existence, except by user action (`Q369`, `Q283`).
- **BECAUSE: POSITION.** `P§9`.
- **REJECTED:** Injecting everything in a bounded recent window with no relevance retrieval — the second surveyed answer, which is the degenerate case. And versioning-plus-consolidation-plus-expiry with the effect underspecified — the first, which is the usual gap. Neither is a rival design.
- **COST:** As `Q24` — unset windows.
- **CONFIDENCE:** medium

---

### Q02 — How should episodic retrieval candidates be ranked, and how many should enter the reasoning context?

- **DECISION:** Ranked by fused relevance → pinned → tier → evidence → recency (`Q487`); a configured top-k enters context, with the value deferred to corpus data (`Q469`, `Q859`). No cross-encoder, no MMR, no mention-frequency term, no affect or trust weighting.
- **BECAUSE: POSITION** for tier and pinning and for excluding the affective/trust terms (`P§2` forbids affect; there is one trust source); **ENGINEERING** for the rest, with the parameter deferred by `P§AppB`.
- **REJECTED:** A configurable reranker offering RRF, MMR, node distance, cross-encoder, or mention frequency. It wins on tunability and would let the evaluation choose empirically — a genuinely good property. It loses on `Q212` (no model reranking) and on `E5` (a configuration surface with no consumer, `Q440`).
- **COST:** As `Q26` — no path to better ranking without reopening a settled decision.
- **CONFIDENCE:** medium

---

### Q77 — How is retrieval ordered?

- **DECISION:** Duplicate of `Q35`/`Q487`. Deterministic: fused relevance → pinned → tier → evidence → recency, with every component recorded. The raw-transcript fallback, when used, is ordered chronologically and labelled as a separate section.
- **BECAUSE: POSITION** for tier's place; **ENGINEERING** for the rest.
- **REJECTED:** Preserving a vector store's native relevance order unmodified. It wins on simplicity and on not second-guessing the index. It has no place for tier, which `P§4` requires.
- **COST:** See `Q26`.
- **CONFIDENCE:** high

---

### Q78 — How is retrieval scoped?

- **DECISION:** By surface (dictation vs Hey Kivi, `Q06`) and by nothing else. No project scope, no platform scope, no session scope. Entities narrow candidates when a query names one, but that is relevance, not scoping.
- **BECAUSE: POSITION.** `P§6`: "Kivi always retrieves everything it has." A project filter would be a silent restriction with no trace.
- **REJECTED:** Project and platform scoping. It wins for multi-workspace products, and the inventory's note is instructive — platform scoping was added "after leakage bugs," meaning unscoped retrieval leaked between contexts. Under `E1` with one user and one working world there is no second context to leak into, but if Kivi's user had two unrelated clients, cross-contamination would be a real complaint.
- **COST:** No context isolation. Memories from unrelated projects compete in every query.
- **CONFIDENCE:** medium

---

### Q80 — What happens when semantic search fails?

- **DECISION:** Report the degradation in the trace and abstain rather than silently answering from lexical-only (`Q27`, `Q183`, `Q665`). The lexical leg still runs, and its results are shown, but the answer is not built as if retrieval were complete.
- **BECAUSE: POSITION.** `P§8`: a fluent answer built on half the index is "indistinguishable from a real one until it costs you something."
- **REJECTED:** Fall back to FTS and continue, logging a warning (the surveyed answer, and the sane engineering default). It wins on availability. The warning goes to a log nobody reads while the user gets a confident answer — exactly the shape `P§8` forbids.
- **COST:** Visible brittleness. Embedding-provider outages become abstentions.
- **CONFIDENCE:** high

---

### Q89 — Are scopes ownership/security boundaries or retrieval conveniences?

- **DECISION:** There are no scopes (`Q78`). The only boundary that exists — the dictation/Hey Kivi path split — is a **hard structural boundary**, not a convenience: it is enforced by data access, not by a filter parameter (`P§7`).
- **BECAUSE: POSITION.** `P§7`: "Not filtered out — structurally unable to load them."
- **REJECTED:** Project/personal/global scopes with cross-scope rules. Wins for multi-context products; `E1` removes the need.
- **COST:** As `Q78`.
- **CONFIDENCE:** high

---

### Q94 — How much content should a first retrieval expose?

- **DECISION:** Full memory content on first retrieval — memories are single short sentences, so there is nothing to preview. Raw **transcripts** are exposed as bounded excerpts with the full text one tap away (`Q211`).
- **BECAUSE: ENGINEERING (E5).** Position is silent. Memory content is short by construction (`Q63`), so a preview mechanism would be machinery with no payload.
- **REJECTED:** Bounded previews with separate full-content fetch. It wins for long documents. Here it would add a round trip for no reason.
- **COST:** None for memories. Transcript excerpting needs a sensible boundary rule so an excerpt is not misleading — a small but real presentation risk.
- **CONFIDENCE:** high

---

### Q104 — How is relevant memory found — search, embedding, or "read everything"?

- **DECISION:** Hybrid search plus entity linkage (`Q25`). Not "read everything."
- **BECAUSE: ENGINEERING**, and **POSITION** via `P§8` — the trace must show what was retrieved *and what was not*, which presupposes selection. If everything is always loaded, "what was retrieved" is meaningless and the withheld/never-retrieved distinction (`P§6`) collapses at the retrieval end.
- **REJECTED:** Read everything (the surveyed answer, and viable at this corpus size — a few hundred short memories fit in a modern context window). It wins on recall, absolutely: nothing is ever missed. It is the single most tempting shortcut available here, and it fails `P§8` rather than failing technically. Note that `Q337` rejected long-context-as-storage for a different reason; this is long-context-as-*retrieval*, and it fails on inspectability.
- **COST:** Retrieval misses are possible and will happen (`Q403`), where read-everything would have had none.
- **CONFIDENCE:** high

---

### Q118 — Retrieve by explicit address, lexical relevance, graph neighborhood, semantic similarity, or all of them?

- **DECISION:** Four of the five: explicit address (a memory or transcript by id, used by the UI and the trace), lexical relevance, one-hop entity neighbourhood, and semantic similarity. Not multi-hop graph traversal (`Q752`).
- **BECAUSE: ENGINEERING**, with `P§7` forcing the lexical/entity components.
- **REJECTED:** Lexical FTS with no embeddings at all. It wins on determinism and explicability (`Q25`). It loses paraphrase recall.
- **COST:** As `Q25`.
- **CONFIDENCE:** high

---

### Q123 — What should enter retrieval as the query: the last utterance, the full conversation, a structured task state, or several queries?

- **DECISION:** The user's request, plus resolved entity mentions from it, plus any explicit temporal constraint parsed from it. One query per request. **Not** an LLM-generated latent question, and not multi-query fan-out.
- **BECAUSE: POSITION.** `P§8`'s abstention message says what Kivi "looked for," and it must be something the user recognises as their own question. A model-generated latent query would make the trace report a search the user did not ask for, which is harder to trust rather than easier.
- **REJECTED:** LLM query rewriting and multi-query fan-out (`Q314`'s answer, and the mainstream RAG technique). It wins on recall, materially, and is probably the single highest-value rejected optimisation in the retrieval stage. The condition under which it wins: if the rewritten query is **shown in the trace as a rewrite**, which preserves the honesty requirement. That is achievable and this decision should be revisited if recall proves poor.
- **COST:** Recall depends on the user phrasing their question close to how the memory is worded. Vocabulary mismatch is unmitigated.
- **CONFIDENCE:** medium

---

### Q126 — How should target context interact with retrieved material: concatenate it, encode it separately, or construct an explicit intermediate memory?

- **DECISION:** Concatenate into an explicit, code-owned, recorded context object (`Q234`, `Q255`) — with application context (third-party material) and retrieved memories kept in **separately labelled sections**, so the generator can use both and the extractor can be given only one (`Q342`).
- **BECAUSE: POSITION.** `P§5`'s structural rule requires the two to be distinguishable throughout the pipeline, not blended into one prompt blob.
- **REJECTED:** Constructing an intermediate memory that fuses request context with retrieved material. It wins on generation coherence. It would create an artefact that is part third-party content and part memory, which is precisely the mixture `P§5` exists to prevent.
- **COST:** Prompt structure is more rigid; the generator must be told how to use two labelled sections.
- **CONFIDENCE:** high

---

### Q130 — When producing text, should the system generate, copy from memory, retrieve verbatim, or choose among them?

- **DECISION:** Three different answers by content type. **Facts** are copied from memory, not generated — a claim in an answer must correspond to a retrieved memory (`Q757`). **Quotations and sources** are retrieved verbatim from transcripts. **Phrasing** is generated. The boundary is: generate the sentence, never the fact.
- **BECAUSE: POSITION.** `P§8`: "Kivi never fills a gap with a plausible guess." That is a rule about facts, not about wording.
- **REJECTED:** Free generation conditioned on memory, which is what every RAG system does. It wins on fluency. The failure it permits — a fluent claim slightly beyond the evidence — is the one `Q592` grades for and `Q757` admits cannot be fully prevented.
- **COST:** As `Q757` — the fact/phrasing boundary is prompt-enforced and leaky, caught only by sampled attribution grading.
- **CONFIDENCE:** medium

---

### Q135 — When evidence is weak or absent, should the system answer, retrieve a generic pattern, ask, or abstain?

- **DECISION:** Abstain, and show what was searched and what was found nearby (`Q228`). Never a generic pattern. Ask only within the budget, and asking is not a substitute for abstaining — Kivi abstains *and may* spend a prompt if the gap is high-value.
- **BECAUSE: POSITION.** `P§8`, including the worked example, which abstains and offers a near-miss in the same breath.
- **REJECTED:** Retrieving a generic pattern. It wins on apparent helpfulness. A generic pattern presented in a memory product reads as a memory, which is the worst version of the invented answer.
- **COST:** As `Q228` — strictness users may find unhelpful.
- **CONFIDENCE:** high

---

### Q143 — Is memory a structured assertion or a searchable card?

- **DECISION:** A structured assertion that is *also* searchable. Fields are typed columns; the embedding is computed over the content sentence plus entity names, never over a flattened blob of title+content+tags+metadata.
- **BECAUSE: POSITION.** `P§4`'s schema. The flattening the surveyed system does — "title/content/tags are folded into a single embedded string" — makes the embedding a function of metadata, so a tier change or a tag edit silently changes similarity.
- **REJECTED:** Searchable card text with flat metadata. It wins on retrieval simplicity. The folding is a subtle correctness bug worth naming.
- **COST:** Entity names must be included in the embedded text deliberately, or entity-relevant memories under-retrieve — a small design detail with outsized effect.
- **CONFIDENCE:** high

---

### Q144 — Who owns timestamps and ordering?

- **DECISION:** The **source** owns event time (`occurred_at` from the import, `event_time` parsed from content); the **system** owns system time (`first_seen_at`, `last_confirmed_at`, status transitions). Imported provenance timestamps are preserved, never restamped. Ordering is by source event time (`Q667`).
- **BECAUSE: POSITION.** `P§9`'s provenance is "the actual transcript, **with a date**" — the transcript's date, not the import's.
- **REJECTED:** Server-stamped current UTC throughout. It wins on trust in the timestamp's integrity and removes a class of bad-input problem. It would make every imported record appear to have happened at import time, which destroys the entire temporal layer for a corpus import — the primary write path (`E3`).
- **COST:** The system trusts source timestamps it cannot verify. A corpus with wrong timestamps produces confidently wrong temporal answers (`Q683`).
- **CONFIDENCE:** high

---

### Q162 — Should ranking optimize relevance alone, relevance plus diversity, or relevance plus time?

- **DECISION:** Relevance plus tier plus evidence plus time. No diversity/MMR (`Q561`). Recency enters as a ranking term, not as an exponential decay multiplier on score — decay is a **standing** mechanism for observations, not a score adjustment for everything (`Q137`).
- **BECAUSE: POSITION.** `P§9` describes decay as loss of standing ("stops being surfaced"), not as a score multiplier. Keeping them separate is what lets the memory surface explain why something is no longer shown.
- **REJECTED:** Rank fusion + MMR at λ=0.7 + 14-day exponential half-life with a floor + threshold filtering — the surveyed answer, and a well-engineered retrieval stack. It wins on retrieval quality, probably significantly. Every component is individually rejected for a different reason: MMR by `Q561`, the half-life by the standing/score distinction above, the threshold by `Q393`'s calibration problem. **This is the clearest case where the position costs measurable retrieval quality.**
- **COST:** Measurably worse ranking than a tuned stack, with no path to the tuned version without reopening three decisions.
- **CONFIDENCE:** medium

---

### Q167 — Should time affect record truth, retrieval priority, or both?

- **DECISION:** Both, through different mechanisms. **Truth:** newer evidence supersedes older, ordered by event time (`Q667`) — but tier outranks recency (`Q174`). **Priority:** recency is the last tiebreaker in ranking. **Standing:** decay removes observations from surfacing. Three distinct roles for time, never merged into one multiplier.
- **BECAUSE: POSITION.** `P§9` (supersession and decay as separate mechanisms) and `P§4` (tier precedence).
- **REJECTED:** A single retrieval decay applied uniformly. See `Q162`.
- **COST:** Three temporal mechanisms to explain and test.
- **CONFIDENCE:** high

---

### Q177 — Does retrieval reinforce?

- **DECISION:** No, never, unconditionally. Reading a memory changes nothing about it (`Q685`).
- **BECAUSE: POSITION.** `P§4`: "Nothing self-promotes." A reinforcement-on-retrieval rule makes standing depend on what the user happened to ask about, which is neither evidence about the user nor a user action.
- **REJECTED:** Yes, unconditionally (the surveyed answer). It wins for a usage-adaptive memory that surfaces what you actually use. It is a self-promotion mechanism driven by a signal the user never consented to provide.
- **COST:** No usage-based ranking. A memory the user relies on daily ranks the same as one they have never needed.
- **CONFIDENCE:** high

---

### Q194 — Should the mode gate retrieval or disclosure?

- **DECISION:** Disclosure. Duplicate of `Q36`/`Q268`/`Q37`, and the inventory marks this one "decision left open" in its source — which is worth noting, because it is the one question in the inventory whose answer is most completely determined by the position.
- **BECAUSE: POSITION.** `P§6`, section heading "Two decisions that matter more than the names": "**The dial governs disclosure, not retrieval.**"
- **REJECTED:** Gating retrieval. See `Q36`.
- **COST:** As `Q268`.
- **CONFIDENCE:** high

---

### Q208 — Wall clock or generation ordering?

- **DECISION:** Wall clock — specifically event time from the source (`Q144`). Never a generation counter or observation-count ordering.
- **BECAUSE: POSITION.** `P§9`'s decay windows and `P§4`'s dated episodes are both wall-clock concepts; a generation counter cannot express "six months ago."
- **REJECTED:** Observation-count generation ordering. It wins for deterministic replay where wall-clock time is unavailable or untrustworthy. It cannot support decay.
- **COST:** As `Q144` — dependent on source timestamp quality.
- **CONFIDENCE:** high

---

### Q210 — Should durable knowledge outrank episodes?

- **DECISION:** No. Type does not affect rank; **tier** does (`Q193`). A stated episode outranks an observed preference; a stated preference and a stated episode rank equally on tier and are separated by relevance, evidence, and recency.
- **BECAUSE: POSITION.** `P§4`'s two axes are independent: "The two axes are independent, and the interesting cells are the ones people usually flatten." Ranking by type would flatten them by making type an authority proxy.
- **REJECTED:** A bounded type multiplier raising rules/decisions/procedures and lowering episodes (the surveyed answer). It wins on practical relevance — durable knowledge usually *is* more useful. It is exactly the flattening `P§4` names, and it would make an episode about yesterday's reschedule rank below a general preference for a query about yesterday.
- **COST:** No type-aware relevance. A preference query and an episode query get identical ranking treatment (`Q326`).
- **CONFIDENCE:** high

---

### Q224 — When answering a why/what-if question, what should determine candidate retrieval?

- **DECISION:** The same retrieval as any other question — relevance over memories — with the difference appearing at **disclosure**, not retrieval. A "why" question is an invitation that unlocks Daari for that one answer (`P§6`), and the hypothesis offered is generated from the retrieved observations, not retrieved from a causal store (`Q215`).
- **BECAUSE: POSITION.** `P§6`: "Asking *'what do you think?'* or *'why do you reckon I keep doing this?'* unlocks hypotheses for that one answer, and the answer is not written to memory."
- **REJECTED:** Using a knowledge graph as a search space for intervention and counterfactual variables. Wins in a causal product (`Q219`).
- **COST:** Daari's hypotheses are ungrounded single-shot guesses over observations, with no structure and no persistence (`Q229`).
- **CONFIDENCE:** high

---

### Q257 — How should candidate persistent memories be represented and searched?

- **DECISION:** Typed rows (`Q800`) searched by hybrid lexical + dense + one-hop entity (`Q25`), with embedding model, metric, k, and thresholds all explicitly specified and recorded — not left underspecified.
- **BECAUSE: ENGINEERING (E2).** The brief requires reproducibility; the inventory's recurring complaint that these are "underspecified" is the condition that makes a system unreviewable.
- **REJECTED:** Semantic-similarity-only over a vector service. See `Q25`, `Q447`.
- **COST:** As `Q25`.
- **CONFIDENCE:** high

---

### Q267 — When retrieval returns several plausible memories, what should determine their ordering and admission?

- **DECISION:** Ordering by the fixed precedence (`Q487`); admission to the model by top-k, token budget, and then the disclosure filter, in that order, with each stage's drops recorded (`Q708`, `Q562`).
- **BECAUSE: POSITION** for the disclosure stage's position (last) and tier's inclusion; **ENGINEERING** for the rest.
- **REJECTED:** "Most relevant memories supplied" with ranking, k, thresholds, weighting, dedup, and reranking all underspecified. Not a rival design — the absence of one, and the inventory's most common state.
- **COST:** As `Q487`.
- **CONFIDENCE:** high

---

### Q284 — What should be retrieved from each memory population for a new subquery?

- **DECISION:** There is one population (`Q273`). Top-k over it. No private/cross-user split, no per-population quotas, no provenance-based admissibility filtering.
- **BECAUSE: POSITION.** `P§1` principle 2 and `E1`.
- **REJECTED:** Top-k private plus top-k cross-user after provenance filtering. Wins in a shared-knowledge product.
- **COST:** As `Q273`.
- **CONFIDENCE:** high

---

### Q285 — Should policy filtering happen before retrieval, after retrieval, or both?

- **DECISION:** After. Always after. Retrieval is policy-blind; the disclosure filter runs on the ranked set (`Q36`).
- **BECAUSE: POSITION.** `P§6`. This is the same decision as `Q36`/`Q194`/`Q268`/`Q37`/`Q327`/`Q387`/`Q488` — seven inventory questions, one decision (see **Section C**).
- **REJECTED:** Building an admissible set first and retrieving within it. It wins on efficiency and is the only correct design for genuine access control, where retrieving what you may not see is a breach. **Note the important distinction:** in a multi-user system, pre-filtering is right and post-filtering is a security bug. Here there is one user and the "permission" is self-imposed calibration, not access control — which is the only reason post-filtering is defensible. That distinction should be stated plainly in the README, because a security-minded reviewer will otherwise read `P§6` as a mistake.
- **COST:** As `Q268` — and the design does not generalise to a multi-user product without inverting.
- **CONFIDENCE:** high

---

### Q314 — What should generate retrieval intent: the raw dialogue, a model-generated latent question, explicit task fields, or several independent queries?

- **DECISION:** The raw request plus parsed entities and temporal constraints (`Q123`). No model-generated latent question.
- **BECAUSE: POSITION.** `P§8`'s "shows what it looked for" requires the search to be the user's own question.
- **REJECTED:** Two queries — recent dialogue context plus an LLM-generated salient high-level question. It wins on recall. As `Q123`: it becomes acceptable if the rewrite is displayed as a rewrite, and that is the upgrade path.
- **COST:** As `Q123` — vocabulary mismatch is unmitigated.
- **CONFIDENCE:** medium

---

### Q316 — Should retrieval be limited to the same subject/speaker, or may cross-person and cross-project information enter if semantically similar?

- **DECISION:** There is one subject (`E1`, `Q846`), so subject-limiting is vacuous. Cross-project material may enter freely (`Q78`) — there is no project boundary.
- **BECAUSE: POSITION.** `P§5`/`P§1` for the single subject; `P§6` for no scoping.
- **REJECTED:** Speaker-scoped retrieval with enforcement. It presupposes multi-subject memory, which `Q11` rejects.
- **COST:** As `Q78` — no project isolation.
- **CONFIDENCE:** high

---

### Q327 — Should the system retrieve only what it may disclose, or retrieve broadly and gate what may be said?

- **DECISION:** Retrieve broadly, gate what may be said. Duplicate of `Q36` (see **Section C**).
- **BECAUSE: POSITION.** `P§1` principle 1; `P§6`.
- **REJECTED:** See `Q285`.
- **COST:** As `Q268`.
- **CONFIDENCE:** high

---

### Q329 — When evidence is absent or ambiguous, should the system abstain, ask, retrieve adjacent material, or generate the most coherent continuation?

- **DECISION:** Abstain, and *name* the adjacent material rather than answering from it. Ask only within the budget. Never generate a coherent continuation.
- **BECAUSE: POSITION.** `P§8`'s worked example does exactly this — it names the adjacent material ("Arun on Atlas backend work (4 mentions) and one migration discussion from 6 March") and offers it rather than using it.
- **REJECTED:** Generating the most coherent continuation. It wins on fluency and is what an unconstrained LLM does by default. It is the failure the whole section is written against.
- **COST:** As `Q228`.
- **CONFIDENCE:** high

---

### Q364 — How much of ranked memory should be exposed to the generator?

- **DECISION:** The disclosure-permitted subset of the top-k, subject to a token budget, with everything dropped at each stage recorded (`Q267`). Not top-1-plus-linked-neighbours.
- **BECAUSE: POSITION.** `P§AppC` claim 3 requires evidence distributed across multiple dictations to reach an answer, which a top-1 strategy cannot do.
- **REJECTED:** Top-1 plus all linked memories as extended context. It wins when the link graph is high quality — the single best hit pulls its own context. It depends on the associative link graph `Q749` declines to build.
- **COST:** As `Q403` — a hard k with no associative expansion.
- **CONFIDENCE:** high

---

### Q365 — When no candidate is sufficiently relevant, should the system return nothing, guess, or retrieve the nearest item anyway?

- **DECISION:** Retrieval returns the nearest items anyway (fixed k, `Q47`); **generation** then abstains because nothing supports an answer, and the trace shows the near-misses as near-misses. The two behaviours together are what `P§8`'s example does.
- **BECAUSE: POSITION.** `P§8`.
- **REJECTED:** Always selecting top-1 with no abstention behaviour (the surveyed answer). It wins never here; it is the mechanism by which a memory system confidently answers from an unrelated memory.
- **COST:** As `Q47` — the generator is the sole guard, and it is prompt-enforced (`Q757`).
- **CONFIDENCE:** high

---

### Q376 — What ordering guarantees exist under concurrent ingest?

- **DECISION:** Total order, by construction — one writer, one serialised queue, sorted by `occurred_at` before processing (`Q76`, `Q660`).
- **BECAUSE: ENGINEERING (E2).**
- **REJECTED:** Per-session FIFO locks with partition growth. Wins for concurrent multi-session ingest.
- **COST:** As `Q96` — throughput ceiling.
- **CONFIDENCE:** high

---

### Q386 — Does the caller choose retrieval strategy?

- **DECISION:** No. One strategy per surface, fixed in code. The caller chooses nothing about retrieval.
- **BECAUSE: POSITION.** `P§8`'s trace must explain the result; a caller-selected strategy means the explanation depends on a parameter the user never set and cannot see. Also `Q440` — no configuration surface.
- **REJECTED:** Wire-level strategy selection (keyword/vector/hybrid/agentic/multiround). It wins for a memory service with diverse consumers. Kivi has two consumers, both internal.
- **COST:** No per-query strategy adaptation (`Q326`).
- **CONFIDENCE:** high

---

### Q387 — Retrieve all memory then gate disclosure, or filter before retrieval?

- **DECISION:** Retrieve, then gate. Duplicate of `Q36` (see **Section C**).
- **BECAUSE: POSITION.** `P§6`.
- **REJECTED:** Pre-retrieval filters with no disclosure tier (the surveyed answer — note it has *no* disclosure tier at all, which is the field norm). See `Q285`.
- **COST:** As `Q268`.
- **CONFIDENCE:** high

---

### Q390 — How is "unlimited" retrieval handled?

- **DECISION:** There is no unlimited mode. k is bounded, always, and the bound is a stated configuration value. A request for more than the cap is an error, not a silent internal cap.
- **BECAUSE: ENGINEERING (E4).** A silently capped "unlimited" produces a result the caller believes is complete and is not — the trace would then overstate what was searched.
- **REJECTED:** Accepting `top_k=-1` and capping internally with low-score filtering (the surveyed answer). It wins on API convenience. It is a silent behaviour on the answer path.
- **COST:** Callers must choose a k; there is no "give me everything" affordance for debugging. The memory surface serves that need instead.
- **CONFIDENCE:** high

---

### Q391 — On missing embedding/reranker, fail or degrade?

- **DECISION:** Fail visibly on the answer path (`Q80`). On the **write** path, an embedding provider outage does not block the memory write — the memory is stored, flagged for embedding repair, and its lexical-only retrievability is recorded (`Q148`, `Q344`).
- **BECAUSE: POSITION** for the answer path (`P§8`); **ENGINEERING (E4)** for the write path.
- **REJECTED:** Capability tiers where dense recall silently becomes empty (the surveyed answer). "Dense recall becomes empty if embedding is absent" is the precise failure: retrieval returns fewer results and nothing says why.
- **COST:** Two behaviours for one missing dependency, which must be documented so the reviewer is not surprised.
- **CONFIDENCE:** high

---

### Q402 — Once retrieval is requested, what should determine the resolution and amount of history exposed to the model?

- **DECISION:** One resolution: the memories themselves, top-k, plus labelled transcript excerpts only on the fallback path. No global snapshot, no progressive disclosure, no windowed drill-down.
- **BECAUSE: ENGINEERING (E5)**, with **POSITION** ruling out the snapshot (`Q399` — no global account) and progressive disclosure (`Q403` — model-determined context weakens the trace).
- **REJECTED:** Progressive resolution from snapshot to branch summaries to exact commits. It wins for long-horizon agent work and gives the model control over its own context depth — genuinely powerful. It makes the used-context set model-determined (`Q403`).
- **COST:** Fixed depth. A question needing more depth abstains rather than drilling.
- **CONFIDENCE:** high

---

### Q418 — When producing target code, should the generator prioritize a compositional correctness argument or search for efficient equivalent plans?

- **DECISION:** Out of scope as posed. The analogous rule: generation prioritises **traceable correctness** over fluency — every factual claim maps to a cited memory (`Q130`, `Q757`) — and efficiency of phrasing is secondary.
- **BECAUSE: POSITION.** `P§8`.
- **REJECTED:** Optimising for the best-reading output independent of traceability. Wins on user-perceived quality.
- **COST:** As `Q130`.
- **CONFIDENCE:** high

---

### Q422 — When retrieval produces candidates, should relevance be determined by exact predicates, explicit ordering, or a separate ranking model?

- **DECISION:** Exact predicates where the query supplies them (entity, time range, type), a deterministic ranking function otherwise, and never a separate ranking model (`Q212`).
- **BECAUSE: POSITION.** `P§8`'s explicability requirement.
- **REJECTED:** A learned ranking model. See `Q212`/`Q02`.
- **COST:** As `Q26`.
- **CONFIDENCE:** high

---

### Q424 — When counterexample search is inconclusive, should the resource budget buy deeper search, more cases, or quicker feedback?

- **DECISION:** Out of scope as posed. The analogous evaluation decision: the budget buys **more cases and manual inspection of them** (`Q429`), not deeper automated search. Breadth of varied cases beats depth on few, because the failure classes that matter (`Q585`) are categorical rather than deep.
- **BECAUSE: POSITION.** `P§AppA`: the corpus "needs enough variety to exercise all of it," listing five kinds. Variety, not depth.
- **REJECTED:** Deeper bounded search per case. Wins for formal verification.
- **COST:** As `Q428` — small-N per case, demonstrations rather than measurements.
- **CONFIDENCE:** high

---

### Q426 — When correctness is asserted, should the observable surface include only query output or also the explanation and disclosure trace?

- **DECISION:** The explanation and the disclosure trace, both, as first-class observable output — for the user and for the evaluation. An answer without its trace is not a complete result.
- **BECAUSE: POSITION.** `P§8`: the trace is "simultaneously the user's trust mechanism and the engineer's inspection tool." `P§AppC` claim 4 requires the withheld set to be observable.
- **REJECTED:** Output-only observability with counterexamples as the diagnostic surface. It wins in a verification setting where the output is the whole contract. Here disclosure behaviour is half the product, so an evaluation that only inspects answers cannot see the half that matters most.
- **COST:** Traces must be persisted per answer (`Q308`), growing the database and appearing in the growth metric.
- **CONFIDENCE:** high

---

### Q436 — Which retrieval strategies compete?

- **DECISION:** Dense, lexical, and one-hop structural, fused by RRF. Not temporal-only as a competing lane — though `Q39` flags that a dedicated chronological path is probably needed and is the strongest candidate for a fourth lane.
- **BECAUSE: ENGINEERING.** `P§AppB` defers retrieval mechanics.
- **REJECTED:** Any single-strategy design. See `Q25`.
- **COST:** As `Q39` — time-anchored recall is weak.
- **CONFIDENCE:** medium

---

### Q452 — On each request, what should determine whether memory retrieval runs at all?

- **DECISION:** Nothing — it always runs (`Q18`).
- **BECAUSE: POSITION.** `P§6`: "Kivi always retrieves everything it has."
- **REJECTED:** A retrieval-or-not gate skipping straightforward requests to save latency. It wins on cost and latency, which the brief asks to be reported — so this refusal has a measurable price. As `Q18`: it becomes acceptable if the gate's decision is a recorded trace step, and that is the defensible version of the optimisation.
- **COST:** Every request pays retrieval.
- **CONFIDENCE:** medium

---

### Q453 — When retrieval returns more than fits in context, what should determine what is injected?

- **DECISION:** The deterministic rank order, truncated by top-k then by token budget, never dropping a higher tier before a lower one, with every drop recorded (`Q708`, `Q562`).
- **BECAUSE: POSITION** for the tier-protection rule (`P§4`); **ENGINEERING** for the rest.
- **REJECTED:** Dynamic token-budget allocation injecting a small set of highly relevant passages. It is close to the same answer; the difference is that "dynamic allocation" typically means model- or heuristic-driven, which reintroduces an unexplained step.
- **COST:** As `Q708`.
- **CONFIDENCE:** high

---

### Q456 — When memory behavior changes because the retriever, embedding model, schema, or policy changes, what should protect prior behavior?

- **DECISION:** A committed regression suite mapping fixed queries to expected memories and expected *disclosure behaviour*, run as part of the evaluation — plus the model and version recorded on every row (`Q531`, `Q673`) so a behaviour change is attributable to a component.
- **BECAUSE: ENGINEERING (E2, E4).** Position is silent. The brief requires a reproducible evaluation, and a model swap silently changing retrieval is exactly the kind of invisible change `E4` forbids.
- **REJECTED:** Relying on operation-log analysis over time. It wins for a live product with traffic. This system has an evaluation corpus instead.
- **COST:** A regression suite to maintain, and expected-memory fixtures that must be updated deliberately when behaviour legitimately changes — which creates a temptation to update them carelessly.
- **CONFIDENCE:** high

---

### Q470 — Should retrieval return a fixed quota even when none of the memories is sufficiently relevant?

- **DECISION:** Yes — fixed k at retrieval, abstention at generation (`Q47`, `Q365`).
- **BECAUSE: POSITION.** `P§8`'s worked example depends on having near-misses to report.
- **REJECTED:** A relevance threshold returning nothing. See `Q47`.
- **COST:** As `Q47`.
- **CONFIDENCE:** high

---

### Q472 — What should determine whether retrieved memory is allowed to influence the answer or be disclosed to the user?

- **DECISION:** The tier and the dial, applied as a disclosure filter after ranking; withheld memories are excluded from the model's context entirely (`Q255`), so they cannot influence the answer even implicitly.
- **BECAUSE: POSITION.** `P§6`. Note the subtlety this forces: "may not be said" is implemented as "may not be seen," because a model that sees an observation will let it colour the answer even if instructed not to state it. `P§6` says the dial governs disclosure, and the only faithful implementation of that is exclusion from context.
- **REJECTED:** Making all injected memory available as prompt context with no permission layer (the surveyed answer, and the universal default). It wins on answer quality. It is the absence of the product's central mechanism.
- **COST:** Anbu answers are strictly worse than they could be, because the model is denied context it could have used silently. The `P§6` affordance ("Kivi noticed something here") must be rendered outside the model (`Q255`).
- **CONFIDENCE:** high

---

### Q484 — Should summaries be created and made retrievable, or should retrieval preserve original evidence only?

- **DECISION:** Original evidence only — typed memories plus raw transcripts. No summaries (`Q154`, `Q570`).
- **BECAUSE: POSITION.** `P§4` and `P§9`; summaries have no tier and cannot be corrected (`Q33`).
- **REJECTED:** Summaries generated during construction and made retrievable. Its source treats this as a tunable and finds it matters. It is `Q570`'s gap, and the strongest recurring rejected alternative in this whole document.
- **COST:** As `Q570` — narrative and broad questions.
- **CONFIDENCE:** medium

---

### Q485 — For a user request, what should determine whether retrieval returns text chunks or graph relations?

- **DECISION:** Neither/both — retrieval returns **typed memories**, which carry their entity links. Entity relations are traversed one hop to expand candidates (`Q118`), not returned as a separate result kind. There is no chunk/graph mode choice.
- **BECAUSE: POSITION.** `P§4`'s unit is the memory; a chunk has no tier and a bare triple is not readable on the memory surface (`Q569`).
- **REJECTED:** A tunable retriever-type choice between chunks and graph triples. It wins for empirical tuning and its source treats it as a real dial. It presupposes two representations this design deliberately collapses into one.
- **COST:** No representation-level tuning.
- **CONFIDENCE:** high

---

### Q486 — How much retrieved material should enter generation, and should the limit be a fixed item count across representations?

- **DECISION:** A fixed item count **plus** a token budget, both applied uniformly because there is one representation (`Q485`). The value is deferred to corpus data (`Q469`).
- **BECAUSE: ENGINEERING**, parameter deferred by **POSITION** (`P§AppB`).
- **REJECTED:** A pure item count with no token bound. It wins on predictability. Memory content length varies enough that k alone does not bound the prompt.
- **COST:** Two limits interacting, and a drop can be attributed to either — the trace must say which (`Q562`).
- **CONFIDENCE:** high

---

### Q488 — Should retrieval eligibility and disclosure permission be the same decision or separate decisions?

- **DECISION:** Separate. Duplicate of `Q36` (see **Section C**).
- **BECAUSE: POSITION.** `P§1` principle 1.
- **REJECTED:** One decision. See `Q285`.
- **COST:** As `Q268`.
- **CONFIDENCE:** high

---

### Q505 — How should stored reflection be selected and ranked for use on a later attempt?

- **DECISION:** Not applicable — no reflections (`Q503`).
- **BECAUSE: POSITION.** `P§4`'s tiers.
- **REJECTED:** Injecting the newest reflection with ranking underspecified. Wins in agent loops.
- **COST:** None here.
- **CONFIDENCE:** high

---

### Q527 — How are memories found at query time?

- **DECISION:** Hybrid lexical + dense over memory content and entity names, plus one-hop entity-anchored expansion, fused by RRF, deterministically re-ranked (`Q25`, `Q118`).
- **BECAUSE: ENGINEERING**, with `P§7` forcing the lexical/entity component.
- **REJECTED:** Embedding top-k alone, with an entity-anchored subgraph as an add-on. It is close to the same answer minus the lexical leg, and the entity-anchored subgraph half is effectively what `Q118` adopts. The lexical leg is the difference, and it exists for exact names.
- **COST:** As `Q25`.
- **CONFIDENCE:** high

---

### Q528 — What ranks a memory above another?

- **DECISION:** Fused relevance, then pinning, then tier, then evidence, then recency (`Q487`).
- **BECAUSE: POSITION** for tier, evidence, and pinning (`P§4`, `P§9`); **ENGINEERING** for the order.
- **REJECTED:** Cosine similarity alone, with no recency prior, no evidence weight, no tier (the surveyed answer, stated by the inventory as a bare fact). It wins on simplicity. It has no way to prefer what the user told you over what you noticed, which is `P§4`'s central distinction.
- **COST:** As `Q162` — measurably worse than a tuned stack.
- **CONFIDENCE:** high

---

### Q529 — Is everything retrieved allowed to be said?

- **DECISION:** No. Retrieved ⇒ ranked ⇒ **filtered by tier and dial** ⇒ only then in prompt ⇒ sayable. The withheld set is counted and reported but never reaches the model (`Q472`).
- **BECAUSE: POSITION.** `P§1` principle 1 and `P§6`. The surveyed answer — "Yes — no separation. Retrieved ⇒ in prompt ⇒ sayable" — is the exact chain this product breaks, and breaking it is `P§AppC` claim 4.
- **REJECTED:** No separation. See `Q285`.
- **COST:** As `Q472`.
- **CONFIDENCE:** high

---

### Q542 — Who decides when enough has been retrieved?

- **DECISION:** Code, by the fixed k and token budget. Not the model, and there is no paging or iterative retrieval.
- **BECAUSE: POSITION.** `P§8`'s trace must state what was searched and retrieved; a model deciding to request another page makes the retrieved set a model artefact, reconstructable only after the fact (`Q403`).
- **REJECTED:** The model requesting further pages. It wins on adaptive recall and would directly address `Q403`'s hard-k ceiling — a real limitation. It is the most defensible model-in-the-loop retrieval option and the condition for accepting it is the same as `Q123`'s: each additional request must appear in the trace as a step.
- **COST:** As `Q403` — a relevant memory at k+1 is invisible with no recovery.
- **CONFIDENCE:** medium

---

### Q560 — One retrieval channel or parallel lanes?

- **DECISION:** Parallel lanes over **one store** (lexical, dense, entity), merged by RRF, with same-memory hits across lanes collapsing into one result carrying both lanes' rank provenance (`Q209`).
- **BECAUSE: ENGINEERING**, with **POSITION** requiring the per-lane provenance to survive into the trace (`P§8`).
- **REJECTED:** Parallel lanes over *separate stores* (UserMemory / L1 / agent memory). It wins when the stores genuinely differ. Here one store with three indexes is the same idea without the divergence risk.
- **COST:** None material.
- **CONFIDENCE:** high

---

### Q575 — Should retrieval operate over one memory representation or coordinate multiple representations?

- **DECISION:** One representation (typed memories), with raw transcripts as a labelled fallback rather than a co-retrieved second representation (`Q43`).
- **BECAUSE: POSITION.** `P§4`.
- **REJECTED:** Retrieving triples *and* their summaries together, so facts are precise and summaries restore context. It is the cleanest statement in the inventory of the problem `Q570` leaves open, and its answer is the one this design cannot take. It wins if context loss proves damaging — which the brief's chronological example question suggests it might.
- **COST:** As `Q570` — **this is the most-cited cost in this document and it recurs because it is one decision, not many** (see **Section C**).
- **CONFIDENCE:** medium

---

### Q577 — Should user permission constrain what is retrieved, what is disclosed, both, or neither?

- **DECISION:** Disclosed only. Duplicate of `Q36` (see **Section C**).
- **BECAUSE: POSITION.** `P§6`.
- **REJECTED:** Neither (the surveyed answer — "No user permission model is described"). See `Q285`.
- **COST:** As `Q268`.
- **CONFIDENCE:** high

---

### Q588 — F3 — Hybrid dense + BM25 retrieval (D11)

- **DECISION:** Adopted — hybrid dense + lexical, plus one-hop entity (`Q25`).
- **BECAUSE: ENGINEERING**, with `P§7` forcing the lexical leg.
- **REJECTED:** Any single-mode alternative. The inventory's note is accurate: each would "change recall, category performance, and footprint." Temporal retrieval in particular is the one this design lacks and probably needs (`Q39`).
- **COST:** As `Q39`.
- **CONFIDENCE:** high

---

### Q590 — F5 — Short answer conditioned only on retrieved memory (D15–D16)

- **DECISION:** Rejected as an evaluation design. Answers carry citations, explicit abstention, and a trace — and the grading accounts for them (`Q592`). Kivi's answers are not short answers conditioned only on retrieved memory; they are answers plus their justification.
- **BECAUSE: POSITION.** `P§8` requires the trace and the abstention; `P§AppC` claims 4 and 5 are both about things a short-answer protocol cannot express.
- **REJECTED:** Short answers conditioned only on retrieved memory. It wins on comparability with published results and on judge simplicity. The inventory's own note says it: "Explanations, uncertainty, abstention, or citations could change both token cost and how the judge labels an answer." Both effects are real and both are accepted deliberately.
- **COST:** Higher token cost per answer, and results that cannot be compared to any published number (`Q431`).
- **CONFIDENCE:** high

---

### Q602 — When memory becomes less useful over time, should it disappear, become less retrievable, be compressed, or remain fully active?

- **DECISION:** By tier: observations become less retrievable and stop being surfaced (decay); hypotheses disappear (expiry); stated memories remain fully active. Nothing is compressed and nothing is archived (`Q750`, `Q283`).
- **BECAUSE: POSITION.** `P§9`.
- **REJECTED:** Layered natural decay with compression/archival plus active forgetting that reduces recall weight without deletion. It is the closest design in the inventory to `P§9`'s intent, and its "active forgetting without deletion" is nearly the same mechanism as demotion-with-suppression. Its compression layer is what `Q154` rejects.
- **COST:** As `Q24` — unset windows; and no relief valve at scale (`Q54`).
- **CONFIDENCE:** medium

---

### Q603 — When a memory is intentionally forgotten, should the content cease to exist or merely cease to be recalled?

- **DECISION:** Both, split across two actions. **"That's not me anymore"** = cease to be recalled: the row stays with `status = demoted`, plus a suppression. **"Forget"** = cease to exist: the memory and its history are purged, and a **suppression record survives** so the pattern cannot regrow. The suppression is the part that cannot be forgotten.
- **BECAUSE: POSITION.** `P§9` names both actions separately — "**That's not me anymore** (demote + suppress), **Forget** (remove + suppress)" — and insists on the suppression in both: "deleting the row is useless, because the same pattern will regrow from the same transcripts within a week."
- **REJECTED:** Non-invocation only, never deletion (the surveyed answer). It wins on auditability and is what `P§9` already does for demotion. It cannot be the answer for Forget, because a user who says "forget this" and learns the content is retained has been misled.
- **COST:** **Forget cannot mean forget** — a suppression record specific enough to block re-derivation necessarily describes the thing suppressed, and the source transcript remains (`Q28`). This is the sharpest gap between the product's language and its behaviour. See **Section B, conflict B5**.
- **CONFIDENCE:** high on the mechanism, low on the naming.

---

### Q609 — Should safety and permission determine what enters retrieval, what may be used internally, what may be disclosed, or all three?

- **DECISION:** Two different things, deliberately separated. **Content policy** (exclusions) determines what may ever be *stored*, enforced on the write path. **Permission** (the dial) determines only what may be *disclosed*, enforced after ranking. Neither touches retrieval. There is no "used internally but not disclosed" state — a withheld memory is excluded from the model's context (`Q472`), so it is not used internally either.
- **BECAUSE: POSITION.** `P§2` (write-path exclusion) and `P§6` (disclosure-only permission). The absence of a third state follows from `Q472`'s reasoning: a model that sees something uses it.
- **REJECTED:** Governance embedded across all memory operations with no retrieval/disclosure separation (the surveyed answer). It wins for a system needing uniform policy enforcement. It cannot produce the withheld count (`P§AppC` claim 4).
- **COST:** As `Q472` — Anbu answers are denied context they could have used silently.
- **CONFIDENCE:** high

---

### Q623 — When multiple memories compete for limited/context-sensitive model attention, should ordering be system-selected or user-controlled?

- **DECISION:** System-selected, deterministically (`Q40`), with one user lever: **pinning** (`Q315`). The user cannot reorder per request.
- **BECAUSE: POSITION.** `P§9`: "pinnable" is the named user control over prominence, and `P§8`'s warning that "the person must not become the administrator of the system" rules out per-request ordering.
- **REJECTED:** Draggable, user-ordered context objects. It is a genuinely good interface and honest about the fact that position affects model use. It wins if the user wants direct control over context. It is administration, which `P§8` refuses to impose.
- **COST:** As `Q616` — the user's only levers are editing memories and pinning; a mis-ranked result has no per-request remedy.
- **CONFIDENCE:** high

---

### Q631 — Should the system expose memories that were retrieved but not used or not permitted in the answer?

- **DECISION:** Yes, and it distinguishes all four states explicitly: **retrieved**, **withheld by permission (with the tier that would unlock it)**, **used in the answer**, and **dropped for budget**. Four states, four labels, in the Why panel.
- **BECAUSE: POSITION.** `P§6`: "The response trace… shows withheld memories explicitly: *'3 memories retrieved, 1 withheld (observation, requires Koottu).'*" `P§8` adds used and retrieved. Budget drops are `ENGINEERING` from `Q562`.
- **REJECTED:** Showing only what the model could see, without distinguishing states (the surveyed answer — it "does not distinguish retrieved, attended-to, used-in-output, or withheld-by-policy states"). It wins on interface simplicity, and that simplicity is a real concern: four states is a lot to render for a normal user. The position accepts the complexity because claim 4 depends on it.
- **COST:** A dense trace UI. Making four states legible to a non-technical user without it reading like a debugger is the hardest interface problem in this build (`Q44`).
- **CONFIDENCE:** high

---

### Q636 — When compressing experience, should the abstraction be global and shared across tasks, retrieved per task, or bound to each source episode?

- **DECISION:** Bound to source. Every abstraction Kivi makes — an observation — is bound to the specific transcripts that evidenced it and is retrieved per request like anything else. No global shared scripts.
- **BECAUSE: POSITION.** `P§4`: observations are "pointable-at." A global abstraction detached from its sources cannot be pointed at, so it could not be surfaced with its evidence (`Q437`).
- **REJECTED:** Global distilled procedural scripts supplied before each task. It wins for procedural transfer; `Q235`/`Q635` already exclude procedural memory.
- **COST:** As `Q635`.
- **CONFIDENCE:** high

---

### Q637 — What should a memory's retrieval key represent: the whole incoming request, selected task features, the memory content itself, or structured fields?

- **DECISION:** The memory's own content plus its entity names, embedded (`Q143`), and its structured fields indexed separately for filtering. The query side embeds the request as written (`Q123`). No LLM-extracted keyword keys.
- **BECAUSE: POSITION** for the query side (`P§8`'s "shows what it looked for"); **ENGINEERING** for the memory side.
- **REJECTED:** LLM-extracted keywords on either side (the "AveFact" approach). It wins on recall by bridging vocabulary gaps — the same argument as `Q123`, and it is the most-repeated rejected optimisation in this document.
- **COST:** As `Q123` — vocabulary mismatch unmitigated.
- **CONFIDENCE:** medium

---

### Q661 — Vector-first, lexical-first, structured-first, or union all candidate sources before ranking?

- **DECISION:** Union all three, over-fetched per leg, then fuse by RRF and re-rank deterministically (`Q560`). Structured constraints (entity, time, type) are applied as **pre-filters on the candidate pool**, not as post-filters — with one documented exception (`Q824`).
- **BECAUSE: ENGINEERING.** Union avoids either index's blind spot deciding the candidate set.
- **REJECTED:** Vector-first with optional lexical union and post-filtered dates. Post-filtering dates is the specific problem: over-fetching k then filtering by date can return fewer than k, or none, when a date-filtered search would have found plenty. See `Q824`.
- **COST:** Three legs run on every query; cost and latency reflect it.
- **CONFIDENCE:** high

---

### Q663 — Return text only, ranked evidence with provenance, or a disclosure decision and trace?

- **DECISION:** All of it: ranked evidence with provenance **and** the disclosure decision **and** the trace (`Q165`, `Q631`). Never text only.
- **BECAUSE: POSITION.** `P§8`'s four trace elements plus `P§6`'s withheld display.
- **REJECTED:** A programmatic envelope of documents, metadata, and distances without a disclosure decision. It wins as a general retrieval API. It has no place for the one thing that makes this system what it is.
- **COST:** As `Q433` — wide payloads everywhere.
- **CONFIDENCE:** high

---

### Q664 — Filter, lower-rank, warn, abstain, or ask the user?

- **DECISION:** Abstain (`Q135`), with near-misses named. Never lower-rank-and-answer-anyway, never a silent filter, never a warning attached to an answer that is given regardless.
- **BECAUSE: POSITION.** `P§8`: a hedged or warned answer is still an answer. "A fluent invented answer is worse than no answer."
- **REJECTED:** A caller-set distance cutoff with diagnostic envelopes and lexical fallback. It wins for a general-purpose API where the caller decides policy. Here the policy is the product (`Q386`).
- **COST:** As `Q228`.
- **CONFIDENCE:** high

---

### Q674 — How is retrieval selected and ordered?

- **DECISION:** Duplicate of `Q35`/`Q487`/`Q77`. Hybrid by default and by the only option; ordered by the fixed precedence.
- **BECAUSE: ENGINEERING**, with tier from **POSITION**.
- **REJECTED:** See `Q77`.
- **COST:** See `Q26`.
- **CONFIDENCE:** high

---

### Q676 — What ordering and concurrency model applies?

- **DECISION:** Monotonic per-transcript processing order by `occurred_at`, one exclusive writer, serialised queue (`Q376`, `Q660`).
- **BECAUSE: ENGINEERING (E2).**
- **REJECTED:** Dense monotonic frame indexes with per-file exclusive writers. Nearly the same model at a different granularity; ours is per-database rather than per-file because there is one store.
- **COST:** As `Q96`.
- **CONFIDENCE:** high

---

### Q688 — When should an extracted semantic memory become explicitly retrievable, and may it influence behavior before that?

- **DECISION:** Immediately retrievable on write, at its assigned tier. It may **never** influence behaviour before it is disclosable — there is no silent priming, no maturation period, no sub-threshold influence.
- **BECAUSE: POSITION.** `P§1` principle 1 makes knowing and saying separate but both *visible*: a withheld memory "leaves a trace." A memory that silently primes ranking while being unsurfaceable leaves no trace and influences answers invisibly — the purest violation of `P§8`'s inspection contract.
- **REJECTED:** Sigmoidal maturation over a week with implicit ranking priming while silent. It is a sophisticated and cognitively-motivated design, and its instinct — that a new pattern should not immediately be asserted — is the same instinct behind `P§4`'s tiers. The difference is that `P§4` handles it with an explicit tier and this handles it with an invisible weight. The tier is inspectable; the weight is not.
- **COST:** A single-instance observation is retrievable immediately and may be surfaced under Koottu on thin evidence. The evidence threshold N (`Q139`) is the only guard, and it is unset (**Section A**).
- **CONFIDENCE:** high

---

### Q690 — Which retrieval pathways should answer a query, and when should each dominate?

- **DECISION:** One pathway for all queries: hybrid union, fused, deterministically re-ranked (`Q661`). No query-conditional dominance between an episodic path and a graph path.
- **BECAUSE: POSITION.** `P§8`'s trace must explain the result, and "the graph path dominated because your question was about something old" is a rule the user did not set and cannot predict.
- **REJECTED:** Vector-seeded graph expansion with episodic dominating recent queries and graph dominating older ones. It wins on quality — it is a sensible adaptation and directly addresses the temporal weakness (`Q39`). It loses on predictability and on `Q752`'s refusal of graph traversal.
- **COST:** As `Q39`/`Q752`.
- **CONFIDENCE:** medium

---

### Q692 — How much retrieved context should the answerer receive, and should the budget be fixed, adaptive, or value/risk-aware?

- **DECISION:** Fixed k plus a fixed token budget (`Q486`). Not adaptive, not risk-aware.
- **BECAUSE: ENGINEERING (E5)**, parameter deferred by **POSITION** (`P§AppB`).
- **REJECTED:** Adaptive token targets scaling to very large contexts. The inventory's note is worth taking seriously: parity with raw RAG appeared only at a 200K token target — meaning the structured-memory approach needed an enormous budget to match simply stuffing the context. That is a direct challenge to the value of extraction, and it is the empirical form of `Q104`'s read-everything temptation. This system answers it on inspectability grounds, not on quality grounds, and should say so.
- **COST:** As `Q859` — uniform k, wrong at both extremes.
- **CONFIDENCE:** medium

---

### Q694 — Should retrieval success reinforce memories, and should failure or wrong answers be stored as learning signals?

- **DECISION:** No to both. Retrieval does not reinforce (`Q177`); failures are trace records, not memories (`Q707`).
- **BECAUSE: POSITION.** `P§4`'s "Nothing self-promotes" and the tier system's exclusion of Kivi-authored beliefs.
- **REJECTED:** Scores rising on contribution to successful decisions, with errors preserved as learning signals. It wins for a self-improving system. Note its own admission that "definitions, attribution, and safeguards are underspecified" — attributing an answer's success to a specific memory is genuinely hard, and doing it wrong reinforces the wrong things silently.
- **COST:** As `Q177` — no usage-based ranking.
- **CONFIDENCE:** high

---

### Q698 — Should permission govern what is retrieved, what is disclosed, what influences ranking, or all three?

- **DECISION:** Disclosure only. Tier influences ranking, but tier is not permission — it is provenance class. The dial is permission and it touches nothing but disclosure (`Q609`, `Q351`).
- **BECAUSE: POSITION.** `P§6`.
- **REJECTED:** No permission model, with silent immature memories influencing relevance before they can be surfaced (the surveyed answer). That second clause is exactly `Q688`'s violation.
- **COST:** As `Q268`.
- **CONFIDENCE:** high

---

### Q715 — Should exploration arise from explicit search or from stochastic retries conditioned on reflection?

- **DECISION:** Neither. There is no exploration. One attempt, temperature 0 for extraction, low temperature for generation, no retries (`Q508`).
- **BECAUSE: POSITION.** `P§8` for the no-retry rule; `Q72` for determinism on extraction.
- **REJECTED:** Sampled behaviour with revised prompts. Wins in agent loops.
- **COST:** As `Q508`.
- **CONFIDENCE:** high

---

### Q724 — How should context-dependent statements be represented for later retrieval?

- **DECISION:** Rewritten at extraction into context-independent statements with explicit entities and absolute times (`Q65`, `Q723`). "Move it to Tuesday" becomes "The Atlas review moved to Tuesday 18 March."
- **BECAUSE: POSITION.** `P§4`'s examples are all context-independent sentences; `P§9`'s memory surface shows them standalone to a user who has no conversational context.
- **REJECTED:** Storing statements as said, with context resolved at query time. It wins on fidelity and avoids baking in resolution errors. It loses because a memory surface entry reading "move it to Tuesday" is meaningless, and because query-time resolution breaks reproducibility (`Q65`).
- **COST:** Resolution errors are permanent and silent (`Q799`). And this is the decision that most depends on the extractor having enough context — which `Q342`/`Q516` deliberately restrict. **The two decisions are in tension**: `Q724` demands resolution, `Q516` withholds the context needed to resolve. See **Section B, conflict B6**.
- **CONFIDENCE:** medium

---

### Q726 — Which categories should be excluded even when they are informative and retrievable?

- **DECISION:** The `P§2` list plus third-party personal content (`Q851`), specifically *because* they are informative. Filler and redundant confirmations are not excluded as a category — they simply fail the eligibility gates (`Q157`).
- **BECAUSE: POSITION.** `P§2`: "It is achievable. Someone who dictates forty emails a week is handing over a great deal… A model can build a psychological read from this without much effort." The exclusion exists precisely where the information is available and useful.
- **REJECTED:** Excluding only filler and redundancy, with no content-category or consent exclusions (the surveyed answer, and the field default). It wins on capability.
- **COST:** As `Q851`.
- **CONFIDENCE:** high

---

### Q727 — How should each retained memory be indexed when future query shape is unknown?

- **DECISION:** Three parallel views over one store: dense embedding, lexical full-text, and SQL metadata for structured constraints (`Q560`, `Q661`).
- **BECAUSE: ENGINEERING.** This surveyed answer is the same as the decision here and is right for the same reason: query shape is genuinely unknown, and three cheap views cover the space.
- **REJECTED:** A single index. See `Q25`.
- **COST:** Three indexes to maintain and keep consistent (`Q344`).
- **CONFIDENCE:** high

---

### Q733 — When retrieval channels disagree on relevance, how should candidates be combined and ranked?

- **DECISION:** Union the per-leg top-n, deduplicate by memory id keeping both legs' rank provenance, fuse by RRF, then re-rank deterministically (`Q560`, `Q209`).
- **BECAUSE: ENGINEERING**, with per-leg provenance required by **POSITION** (`P§8`).
- **REJECTED:** Set union with ID dedup and no weighting at all. It is close, and its avoidance of "complex linear weighting" is the same instinct as choosing RRF over weighted fusion (`Q662`). The difference is that RRF still produces an ordering across legs, where a bare union does not.
- **COST:** As `Q662` — score magnitude is discarded.
- **CONFIDENCE:** high

---

### Q736 — Should memory retrieval and memory disclosure be governed by the same decision?

- **DECISION:** No. Duplicate of `Q36` (see **Section C**).
- **BECAUSE: POSITION.** `P§1` principle 1.
- **REJECTED:** One decision (the surveyed answer — "no distinct disclosure policy is described"). See `Q285`.
- **COST:** As `Q268`.
- **CONFIDENCE:** high

---

### Q741 — Which memory stores may influence ordinary dictation versus an explicit assistant request?

- **DECISION:** Dictation: the entity/lexical store and stated formatting preferences only, through a path with no access to observations or hypotheses. Hey Kivi: all types and tiers, dial-gated (`Q06`, `Q270`).
- **BECAUSE: POSITION.** `P§7` in full, and `P§AppC` claim 7.
- **REJECTED:** No product-surface distinction, one path (the surveyed answer, and every system's answer). It wins on economy. The brief and the position both make the boundary a deliverable.
- **COST:** As `Q138`/`Q270`.
- **CONFIDENCE:** high

---

### Q751 — How should time change a memory's retrieval standing?

- **DECISION:** Two separate effects, never merged. **Standing:** observations decay out of surfacing, hypotheses expire — a status change, visible on the memory surface. **Rank:** recency is the final tiebreaker. No exponential decay multiplier on scores (`Q162`).
- **BECAUSE: POSITION.** `P§9` describes decay as a loss of standing, not a score adjustment: an observation "loses standing and stops being surfaced."
- **REJECTED:** Exponential time decay on edge weights and activation. It wins on ranking quality for recency-sensitive queries. It is invisible: a memory that ranks lower because of an exponential weight has no explanation the user can read (`Q162`).
- **COST:** As `Q162` — measurably worse ranking on recency-sensitive queries.
- **CONFIDENCE:** medium

---

### Q755 — When should ranking features be recomputed?

- **DECISION:** At query time, every time, from stored fields. No cached factor scores, no consolidation-boundary recomputation. The fields ranking reads (tier, evidence count, timestamps) are cheap and exact.
- **BECAUSE: ENGINEERING (E4).** A cached ranking factor is stale state that changes results without appearing in the trace. At this scale there is nothing to cache away.
- **REJECTED:** Caching factor scores, refreshed at consolidation boundaries, so query latency is independent of history length. It wins at scale, and the latency-independence property is genuinely valuable. `E1`/`E5` remove the need.
- **COST:** Query cost grows with memory count. Fine at hundreds; not at millions.
- **CONFIDENCE:** high

---

### Q760 — Which changes over time should alter the memory itself versus merely its retrieval score?

- **DECISION:** Time alters **status** (decay/expiry) and contributes to **rank** (recency). It never alters memory **content** and never alters **embeddings** — no EMA merging, no drift (`Q748`).
- **BECAUSE: POSITION.** `P§9`'s mechanics change standing, not content. The embedding rule is `ENGINEERING` from `Q155` — a rebuildable cache cannot accumulate state.
- **REJECTED:** Score-only change with archival of low-use nodes and EMA-merged embeddings, leaving the belief lifecycle underspecified. The last clause is the whole gap: this position's contribution is an explicit belief lifecycle.
- **COST:** As `Q24`.
- **CONFIDENCE:** high

---

### Q768 — At query time, should retrieval use one index or combine direct episodic similarity with navigation through a user-level schema?

- **DECISION:** One combined retrieval over one store (`Q661`). No user-level schema to navigate — there are no person-cards (`Q788`), no persona (`Q801`).
- **BECAUSE: POSITION.** `P§2` refuses the user-level schema; `P§4`'s flat two axes replace it.
- **REJECTED:** Parallel episodic similarity plus LLM-driven card/thread navigation. It wins for large multi-person memories. The card layer is the profile.
- **COST:** As `Q784` — no navigational structure at scale.
- **CONFIDENCE:** high

---

### Q769 — What should select the relevant person-level memory: explicit identity, query cues inferred by a model, authorization scope, or all available cards?

- **DECISION:** Not applicable — one person, no cards (`Q788`).
- **BECAUSE: POSITION.** `P§1` principle 2, `E1`.
- **REJECTED:** LLM card selection from query cues. Wins in multi-subject memory.
- **COST:** None here.
- **CONFIDENCE:** high

---

### Q770 — When memory exists but the interaction contract does not call for it, should the system still retrieve it, suppress retrieval, or retrieve and gate disclosure?

- **DECISION:** Depends which contract. **Dictation:** suppress structurally — the path cannot load it (`P§7`). **Hey Kivi under Anbu:** retrieve and gate disclosure (`P§6`). These are two different answers for two different reasons, and conflating them is a common misreading of the position.
- **BECAUSE: POSITION.** `P§7`: "Not filtered out — structurally unable to load them." `P§6`: "Kivi always retrieves everything it has. The dial decides what may be *said*." The position uses opposite mechanisms for the surface boundary and the permission boundary, deliberately: the surface contract is absolute, the permission is calibration.
- **REJECTED:** One uniform answer for both. It wins on architectural consistency and is what a reviewer would expect. The position's asymmetry is defensible — a transcription contract is a promise about the product, a dial is a promise about disclosure — but it must be explained or it looks like inconsistency. Noted in **Section B, conflict B7** as a tension worth stating plainly rather than a contradiction.
- **COST:** Two enforcement mechanisms for what looks like one idea, and a README paragraph to justify it.
- **CONFIDENCE:** high

---

### Q776 — Should generation receive all retrieved content, a reranked subset, or a permission-filtered trace with reasons?

- **DECISION:** A permission-filtered, reranked, budget-bounded subset — and the **reasons** go to the trace, not to the generator. The generator receives content it may use; the trace receives the accounting (`Q472`, `Q631`).
- **BECAUSE: POSITION.** `P§6` (filter before generation) and `P§8` (reasons in the trace).
- **REJECTED:** Fusing everything retrieved into the answering context with reranking and deduplication underspecified. It wins on answer quality. It is the no-separation default (`Q529`).
- **COST:** As `Q472`.
- **CONFIDENCE:** high

---

### Q787 — What should be retrieved first: raw episodes, semantic claims, user narratives, or a combination?

- **DECISION:** Semantic claims (typed memories) first and primarily; raw transcripts only as a labelled fallback after a memory miss; no user narratives (`Q43`).
- **BECAUSE: POSITION.** `P§4` + `P§8`'s abstention example, where raw material appears as a named near-miss.
- **REJECTED:** Parallel episodic summaries plus agent-selected cards and threads, fused. See `Q768`.
- **COST:** As `Q570`.
- **CONFIDENCE:** high

---

### Q789 — What should happen when retrieved memories disagree, contain uncertainty, or support more than one answer?

- **DECISION:** Surface the disagreement rather than resolving it silently. Precedence (`Q174`) determines which is *stated as current*; where a genuine unresolved conflict exists between a stated memory and strong contradicting evidence, Kivi says so under Koottu, may spend a confirmation prompt if it is high-value, and abstains rather than picking under Anbu.
- **BECAUSE: POSITION.** `P§8`'s no-guess rule plus `P§9`'s reservation of resolution to the user. `P§6`'s Koottu promise — "I'll tell you what I've noticed, even if you'd rather not hear it" — is exactly the contradiction case.
- **REJECTED:** Fusing everything into a reasoning engine with no conflict arbitration (the surveyed answer, and the inventory notes "no conflict arbitration, confidence display, or contradiction-aware ranking is described"). It wins on fluency. It produces an answer that silently picked a side.
- **COST:** Under Anbu, a contradiction produces an abstention the user cannot understand without switching modes — which is a poor experience and a real cost of the dial's default. Flagged in **Section A**.
- **CONFIDENCE:** medium

---

### Q801 — Should inferred user traits be stored as durable, retrievable objects?

- **DECISION:** No. Absolutely not, in any form — no persona, no trait summary, no behavioural-pattern object.
- **BECAUSE: POSITION.** `P§2`, and this is the single question the position exists to answer. The surveyed answer — "Persona = LLM summary of 'stable user traits, preferences, and behavioral patterns', written to store, embedded, injected into context" — is a precise description of what `P§2` rejects: "A product that models your goals and insecurities is studying you."
- **REJECTED:** Storing an inferred persona. It wins on preference-question performance, which the inventory marks as load-bearing (`Q818`), and on broad-question answering (`Q850`). It is the highest-value rejected alternative in the entire document, and the rejection is the product.
- **COST:** As `Q818`/`Q850`/`Q331` — measurably worse on preference aggregation and broad questions, and the most appealing screen is not built.
- **CONFIDENCE:** high

---

### Q808 — Retrieve over one pool or several?

- **DECISION:** One pool — every query sees every memory, subject only to surface path (`Q06`) and disclosure filtering (`Q36`).
- **BECAUSE: POSITION.** `P§6`: "Kivi always retrieves everything it has."
- **REJECTED:** Several pools. The surveyed answer here happens to agree ("Every query sees everything") — and that agreement is worth noting, because it comes from a system with no disclosure layer at all. Same retrieval philosophy, opposite disclosure philosophy.
- **COST:** As `Q78` — no isolation.
- **CONFIDENCE:** high

---

### Q810 — Retrieve-then-filter, or filter-then-retrieve?

- **DECISION:** Split by filter kind, and this is a real distinction. **Structured constraints** (entity, time range, type): filter-then-retrieve — applied to the candidate pool before top-k. **Permission**: retrieve-then-filter, always, after ranking (`Q36`).
- **BECAUSE: POSITION** for the permission half (`P§6`); **ENGINEERING** for the structured half — post-filtering a top-k by date is the bug `Q661` names, where a date-filtered search would have found results that top-k discarded.
- **REJECTED:** Uniform post-retrieval filtering, which the surveyed source flags in its own parenthetical as an implementation choice rather than a principle. It wins on implementation simplicity — one pipeline. It systematically under-returns on constrained queries.
- **COST:** Two filter placements to reason about; mixing them up produces either a permission bug or a recall bug.
- **CONFIDENCE:** high

---

### Q823 — How should the system infer the time interval intended by a recall query?

- **DECISION:** Parse explicit and relative expressions against the **request's own timestamp**, deterministically, with the resolved interval shown in the trace. If the expression cannot be resolved, the constraint is dropped visibly rather than guessed (`Q809`).
- **BECAUSE: ENGINEERING (E4)**, with **POSITION** requiring the resolution to be visible (`P§8`'s "shows what it looked for" must include the time window it searched).
- **REJECTED:** Falling back to session start when query timestamps are absent (the surveyed workaround for LOCOMO's missing timestamps). It wins when no better reference exists. Here requests always have a timestamp, and inventing a reference would silently shift every relative query.
- **COST:** Relative-expression parsing is a fixed ruleset that will not cover everything ("the week before the launch"). Uncovered expressions drop the constraint (`Q809`).
- **CONFIDENCE:** high

---

### Q824 — Should temporal constraints narrow candidates before semantic retrieval, after it, or participate jointly in retrieval?

- **DECISION:** Before — as a pre-filter on the candidate pool (`Q810`, `Q661`). A resolved time constraint restricts what is searched; it does not prune what was found.
- **BECAUSE: ENGINEERING.** Position is silent. The reasoning is the recall bug named in `Q661`: semantic-top-k-then-temporal-filter returns whatever survives, which can be nothing even when many in-range memories exist.
- **REJECTED:** Semantic top-k first, then temporal filtering, promoting graph-supported raw turns (the surveyed answer, which its own source marks load-bearing). It wins when temporal metadata is unreliable enough that pre-filtering would wrongly exclude — which, given `Q799`'s parsing risk, is a real concern. The mitigation is that approximate event times are flagged (`Q65`) and the pre-filter can be widened for them.
- **COST:** A wrong `event_time` (`Q799`) now excludes a memory from a temporal query entirely, rather than merely ranking it badly. Pre-filtering makes date-parsing errors more consequential.
- **CONFIDENCE:** medium

---

### Q825 — When temporal validity and semantic similarity disagree, which should dominate ranking?

- **DECISION:** Temporal validity dominates, lexicographically: an explicitly stated time constraint is a filter, not a ranking term, so a semantically perfect out-of-range match does not appear at all (`Q824`). Where no explicit constraint exists, recency is only the final tiebreaker (`Q487`).
- **BECAUSE: ENGINEERING**, with the same reasoning as `Q824`.
- **REJECTED:** Lexicographic ranking with binary time alignment as primary key and similarity secondary — which keeps out-of-range results visible below in-range ones. It wins on graceful degradation: if the time parse was wrong, the user still sees something. That is a genuine advantage and is the better answer if `Q799` parsing proves unreliable.
- **COST:** As `Q824` — a date-parse error produces an empty result rather than a degraded one.
- **CONFIDENCE:** medium

---

### Q828 — Should one retrieval architecture serve every user task, or should task contracts impose structural access boundaries?

- **DECISION:** Structural boundaries by **surface** (dictation vs Hey Kivi, `Q06`). Not by task — the three Hey Kivi tools share one retrieval (`Q326`).
- **BECAUSE: POSITION.** `P§7` for the surface boundary; the absence of a task boundary is `ENGINEERING` (`E5`).
- **REJECTED:** One pipeline for everything (the surveyed answer). Wins on economy; loses the brief's boundary requirement.
- **COST:** As `Q326` — one retrieval policy serves three tools with different needs.
- **CONFIDENCE:** high

---

### Q833 — How many candidate memories should downstream reasoning receive, and what should set that number?

- **DECISION:** A configured k, set from corpus data rather than chosen in advance (`Q469`, `P§AppB`). The evaluation reports sensitivity to k rather than asserting a value.
- **BECAUSE: POSITION.** `P§AppB`: parameters "need corpus data before they can be set honestly."
- **REJECTED:** A fixed K=5 chosen as "enough variety without overwhelming context." It wins on decisiveness and the reasoning is sound. Declining to pick a number before the corpus exists is what `P§AppB` asks for, and reporting sensitivity is more useful than a defended guess.
- **COST:** k is unset in this document (**Section A**) and the evaluation must do the work.
- **CONFIDENCE:** high

---

### Q836 — When retrieved memories are relevant, who should decide whether they influence the actor?

- **DECISION:** The **tier and the dial**, in code — not a model. There is no intervention-decision model. A stated memory influences; an observation is mentioned under Koottu and influences nothing; a hypothesis is voiced under Daari and influences nothing (`Q332`, `Q837`).
- **BECAUSE: POSITION.** `P§4`'s "What Kivi may do with it" column and `P§6`'s dial. `Q247`'s rule: promises are enforced in code.
- **REJECTED:** A separate small model deciding whether to intervene. It wins on judgement quality — a model can tell when an observation is genuinely worth raising, which a tier cannot. It makes a product promise depend on a model's discretion.
- **COST:** Koottu will surface observations at moments when they are unhelpful, because relevance is the only gate and there is no judgement of timeliness. `P§8` asks prompts to appear "at natural moments" — observations have no equivalent rule, which is an unfilled gap (**Section A**).
- **CONFIDENCE:** high

---

### Q838 — When retrieved memory is irrelevant or uncertain, what should the system expose?

- **DECISION:** Expose it — in the trace, always, as retrieved-but-unused with the reason. Never silently inject nothing and say nothing (`Q631`).
- **BECAUSE: POSITION.** `P§8`'s trace shows "what was retrieved" and "what was used," which only differ if the unused set is exposed.
- **REJECTED:** Returning `intervene:false` and injecting nothing, with retrieved detail shown only in a paper appendix rather than a user surface. It wins on interface cleanliness. The inventory's phrasing — shown in "the appendix example, not specified as a user surface" — is the recurring gap this position closes.
- **COST:** As `Q631` — a dense trace.
- **CONFIDENCE:** high

---

### Q857 — How are candidates found?

- **DECISION:** Duplicate of `Q527`/`Q25`. Hybrid embedding + lexical + one-hop entity expansion. Not breadth-first graph traversal (`Q752`).
- **BECAUSE: ENGINEERING**, with `P§7` forcing the lexical leg and `P§8` limiting traversal depth.
- **REJECTED:** Adding breadth-first graph traversal. It wins on multi-hop recall — the acknowledged weakness (`Q752`).
- **COST:** As `Q752`.
- **CONFIDENCE:** high

---

## Stage: CONFLICT

---

### Q13 — What happens on contradiction: keep both, overwrite, or supersede with lineage?

- **DECISION:** Supersede with lineage. The new claim becomes current; the old keeps its row with `status = superseded` and a `superseded_by` pointer; both remain retrievable as *evidence* while only the current one is retrievable as *fact* (`Q361`, `Q88`).
- **BECAUSE: POSITION.** `P§9`: "Contradictions supersede. New evidence doesn't stack alongside old evidence; it replaces it, and the superseded version stays in history so the change is auditable."
- **REJECTED:** Keeping both with temporal validity ranges. It wins for facts that were genuinely true in sequence — "Priya was at Acme, now at Northwind" is two true facts, not one corrected one. That is a real modelling distinction this design flattens: supersession treats every change as a correction. Under `Q848` validity intervals are only stored when the transcript states them, so most sequence facts lose their earlier validity.
- **COST:** Kivi cannot answer "who was the Acme contact in March" well once the fact has been superseded, unless the supersession preserved a validity end — which it usually will not.
- **CONFIDENCE:** medium

---

### Q15 — When the system is wrong, who can correct the memory, what is changed, and how is recurrence prevented?

- **DECISION:** The **user**, through four actions plus inline correction. What changes: the memory's content or status, with the prior version preserved. Recurrence is prevented by a **suppression record the extractor consults on every future run** — not by deleting the row.
- **BECAUSE: POSITION.** `P§9`, the whole "That's not me anymore" paragraph: "deleting the row is useless, because the same pattern will regrow from the same transcripts within a week. The action must record a suppression that the extractor respects going forward. Otherwise the user learns that their corrections don't stick, which is the fastest way to lose them."
- **REJECTED:** No correction path at all — which is the answer in three of the four surveyed camps, including the blunt "Nobody. No user write path exists." It wins on build cost, and its prevalence is the reason `P§AppC` claim 6 exists as a demonstration rather than an assumption.
- **COST:** As `Q293` — a monotonically growing suppression list whose matching scope is undetermined (**Section A**).
- **CONFIDENCE:** high

---

### Q22 — Who may correct durable knowledge, and should correction overwrite, version, demote, or suppress future re-derivation?

- **DECISION:** The user only. All four behaviours exist, mapped to four named actions: **Correct** (edit + version), **Confirm** (promote), **That's not me anymore** (demote + suppress), **Forget** (remove + suppress). Every one of them versions or suppresses; none is a bare overwrite.
- **BECAUSE: POSITION.** `P§9`'s action list verbatim.
- **REJECTED:** Edit/delete/supersede/pin/feedback/TTL without source-level suppression — the surveyed answer, and the inventory's own note that "no source-level suppression was found" in any of them. That absence is the single most distinguishing gap between this position and the field: everyone has editing, nobody has suppression, so nobody's corrections stick.
- **COST:** As `Q293`.
- **CONFIDENCE:** high

---

### Q34 — What happens on storage conflict?

- **DECISION:** A uniqueness conflict on the candidate key returns the existing memory and increments nothing — it is an idempotent no-op (`Q08`). A **batch** with one bad candidate does not fail the batch: the bad candidate is rejected and logged, the rest commit, and the rejection is visible (`Q86`).
- **BECAUSE: ENGINEERING (E4).** Position is silent. Both surveyed behaviours are defensible; the choice here is per-candidate rejection with visibility, because a whole-batch rejection would lose a transcript's good candidates and a silent non-strict store would admit malformed ones.
- **REJECTED:** Strict mode rejecting the entire batch. It wins on consistency — a transcript is all-or-nothing. It conflicts with `Q341`'s compound transaction only superficially: the transaction still commits atomically, it just commits the valid subset plus the rejection records.
- **COST:** A transcript can be partially extracted, which the transcript view must show honestly (`Q675`).
- **CONFIDENCE:** high

---

### Q50 — What should users be able to do when memory is wrong: edit, delete, demote, supersede, suppress re-derivation, or merely correct the current answer?

- **DECISION:** All of them except "merely correct the current answer." Four actions on the memory surface, plus inline correction during a request that writes through to the memory — never a correction that only affects the current response.
- **BECAUSE: POSITION.** `P§8`: "Corrections are cheap and inline. *'No, Priya's at Northwind now'* in the middle of a request should update the entity without ceremony." The words "update the entity" make it a durable write, not a local fix.
- **REJECTED:** Autonomous model refinement with the user correction interface underspecified. It wins on user effort — the system fixes itself. It is `Q269`'s rejected self-correction and `Q640`'s rejected in-place revision.
- **COST:** As `Q611` — cheap correction with no confirmation step is dangerous for `Forget`.
- **CONFIDENCE:** high

---

### Q51 — Should observations weaken with age or non-recurrence even if no explicit contradiction appears?

- **DECISION:** Yes. That is exactly what decay is, and it applies only to observations and hypotheses, never to stated memories (`Q283`).
- **BECAUSE: POSITION.** `P§9`: "An observation not re-observed within a window loses standing and stops being surfaced. Behaviour from six months ago should not be presented as who you are."
- **REJECTED:** No decay; memories change only on contradiction (the surveyed answer). It wins on simplicity and sidesteps the unset-window problem (`Q24`). This is the fourth time the same objection appears — the window value is genuinely unset (**Section A**) and shipping decay before it can be calibrated is the weakest link in `P§9`.
- **COST:** As `Q24`.
- **CONFIDENCE:** medium

---

### Q58 — When evidence is missing or conflicting, what should determine whether the system answers, abstains, asks, or exposes near misses?

- **DECISION:** A fixed rule, not a judgement. **No supporting memory** → abstain, expose near misses, show the search. **Conflicting memories** → precedence decides the current fact; if the conflict is between a stated memory and strong contradicting evidence, abstain under Anbu and surface it under Koottu (`Q789`). **Asking** happens only within the budget and never instead of abstaining.
- **BECAUSE: POSITION.** `P§8` (abstention + near misses + rationed prompts) and `P§9`/`P§4` (precedence).
- **REJECTED:** Treating abstention as unevaluated and always generating an answer from retrieved context (the surveyed answer, and the standard benchmark protocol). It wins on measurability. `P§AppC` claim 5 makes abstention a first-class evaluated output here.
- **COST:** As `Q789` — abstention on conflict under Anbu is opaque to the user.
- **CONFIDENCE:** high

---

### Q59 — How should the system react when memory is wrong or adversarial?

- **DECISION:** Wrong → the four user actions plus suppression (`Q15`). Adversarial input is **not** a modelled threat: single user, local, no untrusted writer (`E1`). The nearest real case — third-party content in application context attempting to influence what is remembered — is structurally handled, because application context cannot reach the write path at all (`Q342`).
- **BECAUSE: POSITION** for the correction half; **ENGINEERING (E1)** for declining an adversarial model. Worth noting: `P§5`'s structural rule gives prompt-injection resistance on the write path as a side effect, which is a genuine security benefit the position did not argue for.
- **REJECTED:** Diagnosing model suggestibility without a runtime remedy (the surveyed answer). It wins as research. It offers the user nothing.
- **COST:** No defence against a user's own compromised corpus, and no handling of injected instructions in application context on the *generation* path — where they can still influence an answer even though they cannot influence memory. That gap is real and unaddressed (**Section A**).
- **CONFIDENCE:** medium

---

### Q66 — When new evidence conflicts with an existing belief, what should determine the surviving state and history?

- **DECISION:** Tier first, then event-time recency; the loser survives as `superseded` history; a user correction outranks both (`Q174`, `Q672`, `Q13`).
- **BECAUSE: POSITION.** `P§4` (tier permissions) + `P§9` (supersession + history).
- **REJECTED:** Temporal decay prioritising newer information with no contradiction detection or version history (the surveyed answer). It wins on simplicity — newer just ranks higher, nothing to detect. It means Kivi states both versions when both rank (`Q361`).
- **COST:** As `Q13` — sequence facts flatten into corrections.
- **CONFIDENCE:** high

---

### Q03 — When memories contradict, what should determine which claim governs the answer and what happens to the displaced claim?

- **DECISION:** Governance order: **user correction > stated > observed > hypothesised**, and within a tier, later event time wins. The displaced claim is marked `superseded`, keeps its sources, stays out of current-fact retrieval, and remains available as evidence and in history.
- **BECAUSE: POSITION.** `P§4`'s tier table is the precedence; `P§9` is the disposal rule.
- **REJECTED:** Overwrite-and-discard (the plurality behaviour across twelve sources), and "ordinary writes do not synchronously check contradictions" (the more common one). The second is the honest field default: most systems do not detect contradiction at all, which is why the inventory marks this contested across twelve sources without a clear winner. Synchronous checking costs a similarity search and an LLM verdict per candidate — a real, reportable cost.
- **COST:** Contradiction detection runs per candidate on the write path, adding cost and latency to import, and its false negatives leave contradictory memories both active (`Q475`).
- **CONFIDENCE:** high

---

### Q91 — Does a conflict block the write, annotate it, or get resolved before persistence?

- **DECISION:** Resolved before persistence, within the same transaction as the write (`Q341`). Not commit-then-detect.
- **BECAUSE: POSITION.** `P§9`'s supersession makes the old row's status part of what the new fact means. A window in which both are active is a window in which Kivi would state both.
- **REJECTED:** Commit first, then run non-fatal candidate detection where detection failure never fails the save (the surveyed answer, and the pragmatic choice). It wins on write availability — a flaky detector never blocks a memory. It creates exactly the both-active window above, and "detection failure never fails save" means contradictions silently survive whenever the detector errors.
- **COST:** A detector outage blocks writes (`Q394`'s fail-closed rule applied here). Import stalls rather than admitting unchecked memories.
- **CONFIDENCE:** medium

---

### Q93 — Should "not a conflict" be remembered?

- **DECISION:** Yes. A negative verdict on a candidate pair is persisted with its model and evidence, so the same pair is not re-judged on every subsequent write.
- **BECAUSE: ENGINEERING (E2, E5).** Position is silent. Without it, every new memory re-judges against every similar existing one, and the cost grows quadratically — a real problem during a 500-record import. Persisting the verdict also makes merge behaviour reproducible (`Q08`).
- **REJECTED:** Re-judging every time. It wins on freshness — a better model would judge differently, and a cached negative verdict freezes an old model's opinion. That is a genuine downside and the mitigation is that the verdict is keyed by model version (`Q673`), so a model change invalidates it.
- **COST:** A cached wrong "not a conflict" persists until a model change, leaving two contradictory memories both active.
- **CONFIDENCE:** high

---

### Q115 — On update, overwrite in place or append a version and supersede the old one?

- **DECISION:** Append and supersede, with an explicit link (`Q88`, `Q380`). In-place editing happens only for a user `Correct`, and even that writes a superseded snapshot (`Q621`).
- **BECAUSE: POSITION.** `P§9`'s audit requirement.
- **REJECTED:** Overwrite in place. See `Q88`. Note the surveyed answer here — append, deprecate all active versions, link via `migrated_to`, then activate the new row — is essentially the same design, which is reassuring.
- **COST:** As `Q88` — every read must filter by status.
- **CONFIDENCE:** high

---

### Q117 — Who resolves contradictions: last write, explicit correction, accumulation, or user confirmation?

- **DECISION:** Code resolves them by the fixed precedence (`Q03`); the **user** resolves the cases precedence cannot — a stated fact contradicted by strong evidence — via confirmation or correction. Never last-write-wins, never accumulation.
- **BECAUSE: POSITION.** `P§4` (precedence) and `P§9` (user authority).
- **REJECTED:** Latest-timestamp selection when multiple active versions exist (the surveyed answer). It wins on determinism and needs no tier. It is recency-first, which `Q174` rejects.
- **COST:** As `Q174` — Kivi can be confidently stale and can only flag it.
- **CONFIDENCE:** high

---

### Q133 — When retrieved evidence conflicts or contradicts, what should determine which version influences output?

- **DECISION:** Only the current (non-superseded) version influences a factual answer; superseded versions influence only observations about change ("you've moved this three times"). Two retrieval semantics, strictly separated (`Q361`).
- **BECAUSE: POSITION.** `P§9` (supersession) and `P§6`'s Koottu example, which needs the superseded versions as evidence: "You've moved this deadline three times: the 4th, the 11th, and the 18th."
- **REJECTED:** Letting all versions influence output. It wins on completeness. It makes Kivi state stale facts alongside current ones.
- **COST:** As `Q361` — the two semantics must never leak into each other, and this is the subtlest invariant in the retrieval layer.
- **CONFIDENCE:** medium

---

### Q160 — When a new statement changes an old one, should the system merge text, supersede the old record, retain both, or ask?

- **DECISION:** A three-way classified verdict — DUPLICATE / UPDATE / NEW — with DUPLICATE incrementing evidence (`Q159`), UPDATE superseding with lineage (`Q13`), and NEW appending. Never merging text into a synthesized replacement (`Q311`).
- **BECAUSE: POSITION.** `P§4` (`evidence_count`) + `P§9` (supersession).
- **REJECTED:** UPDATE creating a new chunk with a **merged summary** and retiring the target (the surveyed answer). It is nearly identical except for the merged summary, which is `Q311`'s rejected synthesis — the merged text is a model artefact with no single source.
- **COST:** As `Q311` — the surviving wording may be worse than a merge would produce.
- **CONFIDENCE:** high

---

### Q161 — Should conflict resolution be synchronous on write or asynchronous/versioned?

- **DECISION:** Synchronous on write, inside the transaction (`Q91`).
- **BECAUSE: POSITION.** `P§9`'s supersession must be true the moment the new fact exists.
- **REJECTED:** Asynchronous conflict-aware versioning added later — the surveyed system's own history, where the inventory notes it "previously lacked conflict-aware" handling. That retrofit pattern is instructive: conflict handling added after the fact tends to be asynchronous because the write path was not built for it, and asynchronous handling leaves the both-active window permanently.
- **COST:** As `Q91`/`Q03` — write-path cost and latency, and a fail-closed dependency.
- **CONFIDENCE:** high

---

### Q189 — What happens on conflict: preserve both, merge, reject, or supersede?

- **DECISION:** Supersede, preserving the displaced version in history (`Q13`, `Q03`).
- **BECAUSE: POSITION.** `P§9`: "Contradictions supersede."
- **REJECTED:** Preserve both as competing claims. It wins when both may be true in different contexts — which `Q13` notes is a real gap for sequence facts.
- **COST:** As `Q13`.
- **CONFIDENCE:** high

---

### Q205 — Overwrite, fork, merge, or supersede conflicting writes?

- **DECISION:** Supersede, with serialised writes preserving the losing version (`Q660`, `Q115`). Never fork.
- **BECAUSE: POSITION.** `P§9`.
- **REJECTED:** Fork. Wins for branching workflows (`Q400`).
- **COST:** As `Q88`.
- **CONFIDENCE:** high

---

### Q206 — Resolve contradictions or surface them?

- **DECISION:** Both, split by tier. Contradictions **within or below the observed tier** are resolved by precedence and supersession. Contradictions **involving a stated memory** are not resolved by the system — they are surfaced under Koottu, and only a user action settles them (`Q789`, `Q117`).
- **BECAUSE: POSITION.** `P§9` gives the user authority over stated beliefs; `P§6`'s Koottu promise — "I'll tell you what I've noticed, even if you'd rather not hear it" — is the surfacing mechanism.
- **REJECTED:** Typed `contradicts` edges plus lint, surfacing everything and resolving nothing (the surveyed answer). It wins on honesty — nothing is ever silently decided. It would mean Kivi holds contradictory current facts and states both, which `Q361` rejects for factual answers.
- **COST:** Under Anbu, an unresolved stated-level contradiction becomes an abstention with no visible reason (`Q789`).
- **CONFIDENCE:** medium

---

### Q223 — When two causal assertions contradict one another or the world changes, should the graph replace, version, qualify, or coexist with both?

- **DECISION:** Not applicable — no causal assertions (`Q215`, `Q214`). **Out of scope.**
- **BECAUSE: POSITION.** `P§4`: hypotheses are questions, never claims.
- **REJECTED:** Any of the four. Wins in a causal product.
- **COST:** None here.
- **CONFIDENCE:** high

---

### Q245 — When candidate actions conflict, what should count as value and how should one winner be selected?

- **DECISION:** One model call selects one tool from three, deterministically routed thereafter, with the choice recorded (`Q244`). No value function, no sampling, no voting, no replanning.
- **BECAUSE: ENGINEERING (E5).** Position is silent; the action space is three (`Q246`).
- **REJECTED:** Value-based selection with argmax/softmax/voting. Wins in large action spaces.
- **COST:** As `Q244` — no in-turn recovery from a bad tool choice.
- **CONFIDENCE:** high

---

### Q248 — When memory contains conflict, error, staleness, or information the user wants gone, should the system append, revise, supersede, delete, or forget by decay?

- **DECISION:** All five, each mapped to a distinct cause: conflict → supersede; error → user Correct (revise + version); staleness → decay (observations) or expiry (hypotheses); information the user wants gone → Forget (delete + suppress); new distinct fact → append.
- **BECAUSE: POSITION.** `P§9` specifies each of these separately; the position's contribution here is precisely that it does not have one policy.
- **REJECTED:** Leaving conflict semantics unspecified and listing deletion as future work — the CoALA answer, and an unusually honest one. The inventory's note that "modification, deletion, and unlearning are understudied" is accurate and is why `P§9`'s suppression mechanism is the position's sharpest differentiator.
- **COST:** Five behaviours, five explanations, five ways to be inconsistent (`Q621`).
- **CONFIDENCE:** high

---

### Q281 — When stored claims conflict, should the system append both, choose one, supersede, merge, or ask?

- **DECISION:** Supersede, with asking reserved for stated-level conflicts and rationed (`Q262`).
- **BECAUSE: POSITION.** `P§9` + `P§8`'s prompt budget.
- **REJECTED:** Append both with no resolution policy. See `Q206`.
- **COST:** As `Q789`.
- **CONFIDENCE:** high

---

### Q310 — When new evidence conflicts with old memory, what should determine whether the old claim is deleted, superseded, retained as a competing claim, or sent for confirmation?

- **DECISION:** **Tier determines it.** Old claim below stated → superseded, retained in history. Old claim at stated tier → not overridden automatically; retained as current, the conflict surfaced, and sent for confirmation if high-value. Never deleted by the system.
- **BECAUSE: POSITION.** `P§4`'s tier permissions and `P§9`'s user authority. This is `Q174` stated from the conflict side.
- **REJECTED:** An LLM labelling the new insight "Updated," identifying the corresponding retrieved memories, **deleting them**, and adding the new one (the surveyed answer). It wins on tidiness and on keeping the store consistent. Two problems: it deletes (no audit), and it lets a model override a user-stated fact.
- **COST:** As `Q174` — stale stated facts persist.
- **CONFIDENCE:** high

---

### Q312 — What should cause forgetting: contradiction, redundancy, elapsed time, user action, lack of re-observation, risk category, or some combination?

- **DECISION:** A combination, with each cause producing a **different outcome**: contradiction → supersession (not forgetting); redundancy → merge (not forgetting); elapsed time without re-observation → decay for observations, expiry for hypotheses; user action → demote or forget with suppression; risk category → never stored in the first place, so there is nothing to forget.
- **BECAUSE: POSITION.** `P§9` for the time and user causes; `P§2` for risk category being a write-time exclusion rather than a forgetting rule.
- **REJECTED:** Forgetting triggered only by Redundant/Updated classification within retrieved candidates, with time-based decay discussed but unused. It wins on simplicity. It has the flaw `Q313` names: unretrieved memories are never reconsidered.
- **COST:** As `Q24` — unset windows.
- **CONFIDENCE:** high

---

### Q313 — What should happen to an unretrieved memory that has become outdated or contradictory?

- **DECISION:** Decay and expiry operate on **all** memories by a scheduled sweep, not only on retrieved ones. Contradiction detection runs at **write** time against similarity candidates across the whole store (`Q523`), not only against what a query happened to retrieve.
- **BECAUSE: POSITION.** `P§9`: "An observation not re-observed within a window loses standing." That is a property of the memory and the clock, not of whether anyone queried it.
- **REJECTED:** Operating only over top-k retrieved memories — the surveyed answer, whose own source "explicitly acknowledges it may miss relationships or removals outside that set." That acknowledgement is the whole argument: retrieval-scoped maintenance means the memories nobody asks about are the ones that go stale unchecked.
- **COST:** A sweep job and a write-time similarity search across the store. Both cost money and appear in the metrics; the write-time search is the expensive one (`Q03`).
- **CONFIDENCE:** high

---

### Q319 — When evidence is insufficient or conflicting, should the system answer, abstain, ask for confirmation, or offer nearby evidence?

- **DECISION:** Abstain **and** offer nearby evidence, in the same response. Ask only within the budget (`Q58`, `Q135`).
- **BECAUSE: POSITION.** `P§8`'s worked example does both at once.
- **REJECTED:** No explicit abstention policy (the surveyed answer, and the majority state across the inventory). Wins on build cost.
- **COST:** As `Q228`.
- **CONFIDENCE:** high

---

### Q323 — When evidence changes over time, should the system preserve competing claims, overwrite, supersede with history, or reconcile them into a narrative?

- **DECISION:** Supersede with history. Never reconcile into a narrative.
- **BECAUSE: POSITION.** `P§9` says supersede-with-history explicitly; narrative reconciliation is `Q33`/`Q570`'s rejected summarisation, and here it would additionally be a model authoring a story about how the user changed — which `P§2` refuses.
- **REJECTED:** Narrative reconciliation. It wins on readability — a paragraph explaining how a project evolved is more useful than a chain of superseded rows. It is the most seductive version of the narrative gap.
- **COST:** As `Q570`.
- **CONFIDENCE:** high

---

### Q345 — When a later memory contradicts an earlier one, should the system overwrite, preserve both, supersede with history, merge, or defer to a resolver?

- **DECISION:** Supersede with history (`Q13`, `Q189`, `Q323` — one decision, four questions).
- **BECAUSE: POSITION.** `P§9`.
- **REJECTED:** See `Q13`.
- **COST:** See `Q13`.
- **CONFIDENCE:** high

---

### Q353 — When the memory store lacks adequate support or contains conflicting/stale evidence, should the agent answer, qualify, ask, abstain, or attempt repair?

- **DECISION:** Abstain with near misses; never qualify; ask only within budget; never self-repair (`Q58`, `Q640`).
- **BECAUSE: POSITION.** `P§8` and `P§9`.
- **REJECTED:** Validating that temporary inconsistency does not mislead, with runtime behaviour unspecified. Not a rival design.
- **COST:** As `Q228`.
- **CONFIDENCE:** high

---

### Q363 — When evidence conflicts, what should determine which account governs the next response?

- **DECISION:** The current (non-superseded) highest-tier account (`Q133`, `Q03`).
- **BECAUSE: POSITION.** `P§4` + `P§9`.
- **REJECTED:** The latest retrieved memory guiding access to linked history, with resolution otherwise unspecified. See `Q369`.
- **COST:** As `Q133` — the two retrieval semantics must not leak.
- **CONFIDENCE:** high

---

### Q401 — When two histories are combined, what should determine the surviving account and the handling of conflict?

- **DECISION:** Not applicable — no branching, so no merge (`Q400`, `Q614`). **Out of scope.**
- **BECAUSE: ENGINEERING (E5).**
- **REJECTED:** LLM synthesis merging branch purposes and progress. Wins for branching agent work; also note it produces a model-authored account, which `Q323` rejects independently.
- **COST:** None here.
- **CONFIDENCE:** high

---

### Q408 — When retrieved context contains uncertainty, contradiction, or insufficient evidence, what should the system expose or do?

- **DECISION:** Expose it in the trace — the conflicting memories, their tiers, their sources — and abstain or surface rather than resolving silently (`Q789`, `Q631`).
- **BECAUSE: POSITION.** `P§8`.
- **REJECTED:** Providing synthesis and retrieval with no uncertainty model or contradiction state. Wins on build cost; is the field default.
- **COST:** As `Q631`.
- **CONFIDENCE:** high

---

### Q427 — When stored claims conflict or change, should verification concern each snapshot or the sequence of revisions?

- **DECISION:** Both, and the evaluation tests both: the current state (does Kivi answer correctly now) and the sequence (did a correction stick, did a superseded fact stop being stated, did a suppressed pattern stay suppressed on reprocessing). `P§AppC` claim 6 is explicitly a sequence property.
- **BECAUSE: POSITION.** `P§AppC` claim 6: "A correction demoted a memory and the memory did not regrow on reprocessing." That cannot be tested on a snapshot.
- **REJECTED:** Snapshot-only verification. It wins on evaluation simplicity — most evaluations are snapshot evaluations. It cannot see the product's distinguishing behaviour.
- **COST:** The evaluation needs multi-phase scenarios (ingest → correct → reingest → assert), which are more complex to write and slower to run.
- **CONFIDENCE:** high

---

### Q435 — How are entities identified and conflicts resolved?

- **DECISION:** Three-step resolution — exact/alias, normalised, then LLM adjudication with a recorded verdict (`Q483`). Conflicts between entity attributes resolve by the same tier-then-recency precedence as any memory.
- **BECAUSE: POSITION** for the normalisation step (`P§7`'s ASR variants) and the precedence (`P§4`); **ENGINEERING** for the rest.
- **REJECTED:** Caller-owned IDs, which would be exact and free of merge errors. It wins if the corpus supplied entity ids — the reviewer's will not.
- **COST:** As `Q413`.
- **CONFIDENCE:** high

---

### Q460 — When the critic's prior belief conflicts with supplied supervision, what should anchor the critique?

- **DECISION:** Not applicable — no critic (`Q459`). The analogous rule: when the extractor's prior (the existing entity list) conflicts with the transcript, **the transcript wins** — it is the supervision. A stated correction in a dictation overrides what the entity store believed.
- **BECAUSE: POSITION.** `P§8`: "*No, Priya's at Northwind now*… should update the entity without ceremony." The user's words override the store.
- **REJECTED:** Anchoring on the prior. Wins never here.
- **COST:** A misheard correction propagates immediately and confidently (`Q611`).
- **CONFIDENCE:** high

---

### Q471 — What should happen when retrieved memories conflict with one another, the semantic summary, or the model's parametric knowledge?

- **DECISION:** Memory conflicts resolve by precedence (`Q03`). There is no semantic summary to conflict with (`Q154`). Against **parametric knowledge**, memory always wins, and the generator is instructed and structurally constrained to answer only from provided memories (`Q757`) — a claim the model believes but cannot source is an invented answer.
- **BECAUSE: POSITION.** `P§8`: "Kivi never fills a gap with a plausible guess." Parametric knowledge is the largest available source of plausible guesses.
- **REJECTED:** Expecting the model to weigh pertinent critiques with no explicit adjudication or provenance priority. It wins on fluency and is what concatenate-and-hope does. It has no defined behaviour when the model's prior contradicts a memory.
- **COST:** As `Q757` — the constraint is partly prompt-enforced and leaks, caught only by sampled attribution grading (`Q592`).
- **CONFIDENCE:** medium

---

### Q491 — What objective should choose a pipeline configuration when accuracy, latency, cost, safety, privacy, and user burden conflict?

- **DECISION:** A **lexicographic** objective, not a scalar: (1) no impermissible retention, (2) no impermissible disclosure, (3) corrections stick, (4) no invented answers — then, only among configurations satisfying all four, optimise accuracy, then latency and cost. Privacy and safety are constraints, never terms in a sum.
- **BECAUSE: POSITION.** `P§AppC`'s seven claims are pass/fail, not weighted; `P§585`'s severity ordering follows from `P§2`'s and `P§5`'s absoluteness — "a hard exclusion list," "does not enter the write path."
- **REJECTED:** One scalar objective per run (mean EM, token F1, or LLM correctness) searched over many trials. It wins on tunability — it is the only way to actually optimise a pipeline, and this system consequently has no tuning story. That is a genuine methodological cost.
- **COST:** No hyperparameter search. Configuration is chosen by judgement and reported, not optimised. Parameters like k and the decay windows (**Section A**) therefore stay guesses informed by corpus inspection rather than search results.
- **CONFIDENCE:** high

---

### Q495 — What event should cause the system to create corrective memory?

- **DECISION:** A **user action** — Correct, Confirm, demote, or forget — and nothing else. Not an evaluator signal, not a detected failure (`Q459`, `Q704`).
- **BECAUSE: POSITION.** `P§9`'s four actions and `P§4`'s confirmation event are the only authorised memory-changing events besides extraction.
- **REJECTED:** An evaluator's failure signal triggering reflection. Wins for self-correcting agents; requires a success signal Kivi does not have.
- **COST:** As `Q704`.
- **CONFIDENCE:** high

---

### Q502 — When critics conflict, what should determine the single guidance used downstream?

- **DECISION:** Not applicable — no critics (`Q496`).
- **BECAUSE: ENGINEERING (E5).**
- **REJECTED:** A judge synthesising a consensus reflection. Wins in debate architectures.
- **COST:** None here.
- **CONFIDENCE:** high

---

### Q506 — Should corrective memory apply only to the current item, transfer across items, or update a global store?

- **DECISION:** A correction updates the **global store** and applies to every future request — and, crucially, its suppression applies to future *extraction* as well, which is what makes it stick (`Q15`).
- **BECAUSE: POSITION.** `P§9`: "The action must record a suppression that the extractor respects going forward."
- **REJECTED:** Guidance that operationally only affects retries on the same item. The inventory's note is sharp: "Claims of stable/transferable improvement are not backed by a cross-task memory-transfer evaluation." Corrections that do not transfer are the failure `P§9` names — "the user learns that their corrections don't stick."
- **COST:** A global suppression can over-apply, blocking a legitimately new fact that resembles a suppressed one. Suppression matching scope is undetermined (**Section A**).
- **CONFIDENCE:** high

---

### Q510 — When the evaluator contradicts a seemingly correct answer, should the agent trust the evaluator, preserve the answer, or challenge the signal?

- **DECISION:** Not applicable — no evaluator in the loop (`Q704`). The analogous case: when the **user** contradicts Kivi, the user is always right, immediately and without argument.
- **BECAUSE: POSITION.** `P§9`: "What Kivi thinks of you is [in your hands]." `P§6`'s Daari promise: "You tell me if I'm wrong."
- **REJECTED:** Challenging the signal. Wins never here. Note the surveyed system's documented pathology — trusting the evaluator "driving a correct semantic answer into a timeout/wrong result" — which is the cost of blind trust in an automated judge. Trusting a *human* correction has no equivalent failure worth defending against.
- **COST:** A user who corrects Kivi wrongly makes Kivi wrong, permanently, with no pushback. That is the intended trade.
- **CONFIDENCE:** high

---

### Q511 — How should contradictions among critics or between memory and new evidence be represented over time?

- **DECISION:** As supersession chains with status and lineage, queryable as history (`Q88`, `Q309`). There are no critics.
- **BECAUSE: POSITION.** `P§9`'s audit requirement.
- **REJECTED:** Judge synthesis with no supersession, versioning, decay, or suppression — the surveyed state, and the inventory's note names all four absences at once, which is a fair summary of the field.
- **COST:** As `Q88`.
- **CONFIDENCE:** high

---

### Q522 — Where does a contradicted memory go?

- **DECISION:** It stays, marked `superseded`, with its sources and a pointer to what replaced it. Retrievable as evidence and history; not retrievable as current fact (`Q133`).
- **BECAUSE: POSITION.** `P§9`: "the superseded version stays in history so the change is auditable."
- **REJECTED:** Physical deletion (base Mem0's behaviour). It wins on storage and on a clean forget story. Note that Mem0g — the same project's graph variant — marks invalid and retains "for temporal reasoning," arriving at the same answer as this position for a purely functional reason. Two independent routes to the same place is worth noting.
- **COST:** As `Q88`/`Q309` — status filtering everywhere, and `Forget` must purge history or be a lie.
- **CONFIDENCE:** high

---

### Q523 — Which existing memories are checked for conflict?

- **DECISION:** The top-s most similar existing memories by hybrid retrieval, with s a configured value, checked at **write** time across the whole store (`Q313`). Not only memories that a user query happened to retrieve, and not the entire store exhaustively.
- **BECAUSE: ENGINEERING**, with `Q313`'s position-derived requirement that maintenance not be retrieval-scoped.
- **REJECTED:** Exhaustive checking against every memory. It wins on recall of contradictions — no missed conflicts. It is quadratic in corpus size and would dominate import cost.
- **COST:** Contradictions between memories that are semantically dissimilar but logically opposed are missed. s is another unset parameter (**Section A**).
- **CONFIDENCE:** medium

---

### Q540 — What has to be true for a contradiction to be noticed at all?

- **DECISION:** Only that a new candidate is written. Contradiction detection is a deliberate write-path step against similarity candidates (`Q523`) — it does not depend on the old fact being in a context window, and it does not depend on a model happening to notice mid-conversation.
- **BECAUSE: POSITION.** `P§9`'s supersession is presented as a mechanism the system has, not as something that occasionally happens. A mechanism that fires only when the model notices is not a mechanism.
- **REJECTED:** Relying on the model spotting the conflict in-context (the surveyed answer, stated with admirable bluntness: "The old fact must already be in the context window, and the model must happen to spot the conflict"). It wins on cost — zero extra calls. It makes supersession a coincidence.
- **COST:** As `Q03` — per-candidate similarity search and LLM verdict on the write path, which is the single largest cost driver in ingestion after extraction itself.
- **CONFIDENCE:** high

---

### Q557 — What happens when a user corrects a belief?

- **DECISION:** The correction creates a replacement at stated tier with a user-action provenance, archives the target with bidirectional links, rejects a no-op correction whose normalised content is unchanged, **and writes a suppression** so the old belief cannot be re-derived (`Q15`).
- **BECAUSE: POSITION.** `P§9`, including the suppression clause which the surveyed answer lacks.
- **REJECTED:** The same flow without suppression (the surveyed answer, which otherwise matches closely). The missing suppression is exactly the gap `P§9` calls out, and the reason it matters: "the same pattern will regrow from the same transcripts within a week."
- **COST:** As `Q506` — over-applying suppressions.
- **CONFIDENCE:** high

---

### Q559 — How should bundle-import conflicts resolve?

- **DECISION:** Skip by default — re-importing a corpus that overlaps an existing one is idempotent per transcript (`Q103`). `--replace` and `--error` are available as documented options, and the reset procedure is separate and explicit (`Q107`).
- **BECAUSE: ENGINEERING (E2).** The brief requires a documented import and a documented reset; skip-by-default means a reviewer who runs import twice gets the right answer rather than a doubled corpus.
- **REJECTED:** Replace-by-default. It wins when the second import is authoritative. It would silently discard user corrections attached to existing memories.
- **COST:** A genuinely updated corpus record is ignored unless the reviewer knows to pass `--replace`.
- **CONFIDENCE:** high

---

### Q578 — When retrieved evidence is absent, weak, or conflicting, what should the system expose instead of a fluent answer?

- **DECISION:** An abstention that names what was searched, what was found nearby, and — where relevant — that a conflict exists. Plus the trace (`Q58`, `Q135`).
- **BECAUSE: POSITION.** `P§8`, whole section.
- **REJECTED:** A prompt that says to answer from memories and summaries, with no abstention rule and conflict resolved by recency (the surveyed answer). It wins on always producing something. It is the two failures `P§8` and `Q174` name, together.
- **COST:** As `Q228`.
- **CONFIDENCE:** high

---

### Q589 — F4 — Recency resolves contradiction (D9, D10)

- **DECISION:** Rejected as the rule. **Tier resolves contradiction; recency is the tiebreaker within a tier** (`Q174`, `Q672`).
- **BECAUSE: POSITION.** `P§4`'s tier table.
- **REJECTED:** Recency alone. The inventory's own note states the consequence precisely: "Preserving conflicts, weighting source authority, or requiring confirmation would change temporal answers and abstention behavior." All three of those are what this system does, so its temporal answers and abstention behaviour will indeed differ from recency-based systems — in both directions.
- **COST:** As `Q174` — stale stated facts outrank fresh observations.
- **CONFIDENCE:** high

---

### Q597 — At first activation, should identity and governance emerge through use or be installed before any operation?

- **DECISION:** Installed before any operation, but as **product rules in code**, not as a governance layer. The exclusion list, the tier semantics, the path separation, and the disclosure defaults are all in force from the first transcript. There is no provisional phase in which memory is collected under looser rules.
- **BECAUSE: POSITION.** `P§2`: exclusions run "before anything reaches storage" — there is no window in which they do not. `P§6`: "Default **Anbu**."
- **REJECTED:** Emergence through use. It wins for systems that must adapt their own norms. It would mean the first N transcripts are processed under rules the user never agreed to, which is unrecoverable because the transcripts have already been extracted.
- **COST:** Rules cannot be relaxed per user even knowingly (`Q605`).
- **CONFIDENCE:** high

---

### Q604 — When memory rules conflict, what should determine precedence?

- **DECISION:** A fixed three-level precedence in code, not a runtime hierarchy: (1) **content exclusions** — nothing overrides them, not even the user; (2) **user actions** — override extraction, tiers, and system inference; (3) **system rules** — tier precedence, decay, ranking. A user cannot override an exclusion; the system cannot override a user.
- **BECAUSE: POSITION.** `P§2`'s list is a product promise ("Kivi **never** infers or stores"), so it cannot be user-overridable. `P§9`'s user authority is total over everything else.
- **REJECTED:** A four-level normative hierarchy amendable by designated authorities. It wins for a long-lived governed system. Here it would make the exclusion list negotiable (`Q605`).
- **COST:** A user who genuinely wants Kivi to remember a health-related work fact cannot have it, ever, even with informed consent. That is a real product limitation and the honest defence is only that the promise is worth more than the exception.
- **CONFIDENCE:** high

---

### Q608 — When a correction is made, what should prevent the old belief from returning?

- **DECISION:** A **suppression record the extractor consults on every future run**, keyed to the fact's normalised content and its subject, surviving reprocessing and model changes.
- **BECAUSE: POSITION.** `P§9`, verbatim and emphatic — this is the mechanism the position singles out as "easy to get wrong."
- **REJECTED:** Appending a correction and preserving audit history without a re-derivation block (the surveyed answer, and the inventory notes explicitly: "A re-derivation block is not specified"). It wins on simplicity and is what every system does. It is the exact failure `P§9` names, and `P§AppC` claim 6 exists to prove this system does not have it.
- **COST:** As `Q506`/`Q622` — a permanent, growing, content-describing suppression list, and `Forget` that cannot fully forget (**Section B, conflict B5**).
- **CONFIDENCE:** high

---

### Q626 — When context should cross conversation boundaries, should it be copied, referenced, re-derived, or globally retrieved?

- **DECISION:** Globally retrieved. There are no conversation boundaries in memory — one store, retrieved fresh per request (`Q627`, `Q808`).
- **BECAUSE: POSITION.** `P§6`: "Kivi always retrieves everything it has."
- **REJECTED:** Dragging a memory into another conversation, copied by reference. It wins as a user-controlled context tool. It is administration (`Q623`) and reintroduces the copy-synchronisation problem (`Q627`).
- **COST:** As `Q78` — no scoping, no per-conversation context curation.
- **CONFIDENCE:** high

---

### Q632 — When users correct or confirm memories, when should the system interrupt them?

- **DECISION:** Only at a moment when the memory in question was **actually relevant to the request in hand**, and only within a small weekly cap, spent on the highest-value uncertain memories. Never as a review queue, never at session start, never in ordinary dictation.
- **BECAUSE: POSITION.** `P§8`: "Confirmation prompts are budgeted — a small cap per week, spent on the highest-value uncertain memories. A prompt is a cost paid by the user. Prompts appear at natural moments, attached to a request where the memory was actually relevant. Never as a review queue."
- **REJECTED:** Direct manipulation with prompting policy left underspecified (the surveyed answer). It wins by putting the user in charge entirely — no interruption at all. That is close to viable, and the argument against it is that without prompts the stated tier never grows (`Q191`), so promotion would depend on the user visiting the memory surface unprompted.
- **COST:** The cap size and the "highest-value" ranking are both unset (`P§AppB` defers the budget size explicitly). See **Section A**.
- **CONFIDENCE:** high

---

### Q638 — When several memories appear relevant, what should determine their rank: semantic similarity alone or similarity combined with reliability, recency, outcome, scope, and conflict state?

- **DECISION:** Similarity combined with **tier** (reliability), **evidence**, **recency**, and **pinning** — plus conflict state as a filter, since superseded memories do not compete as current facts (`Q487`, `Q133`). Not outcome (none exists), not scope (none exists).
- **BECAUSE: POSITION.** `P§4` for tier and evidence, `P§9` for pinning and supersession.
- **REJECTED:** Cosine similarity alone with other factors underspecified. See `Q528`.
- **COST:** As `Q162`.
- **CONFIDENCE:** high

---

### Q641 — What evidence should authorize a memory update: any new experience, successful completion, failure after use, explicit user correction, or accumulated observations?

- **DECISION:** Two authorities, and only two. **New user-authored evidence** authorises evidence increments, new memories, and supersession — never tier promotion. **Explicit user correction or confirmation** authorises everything, including tier promotion. Success and failure authorise nothing (`Q704`).
- **BECAUSE: POSITION.** `P§4`: "Promotion requires an explicit user confirmation event." `P§9`'s four actions.
- **REJECTED:** Benchmark feedback authorising updates with user confirmation absent — the surveyed answer, and the inventory names the absence directly. It wins in a benchmark-optimising system. The absence of a confirmation event is the field's defining gap (`Q807`).
- **COST:** As `Q191`.
- **CONFIDENCE:** high

---

### Q647 — When retrieval is weak, contradictory, or absent, should the agent guess, search more broadly, ask, or abstain?

- **DECISION:** One bounded broadening, then abstain with near misses; ask only within budget; never guess (`Q675`, `Q135`).
- **BECAUSE: POSITION.** `P§8`.
- **REJECTED:** No abstention policy. See `Q319`.
- **COST:** The broadening bound is unset (**Section A**).
- **CONFIDENCE:** high

---

### Q657 — Reject, merge, append, overwrite by deterministic ID, or preserve every occurrence?

- **DECISION:** Deterministic-ID upsert at the transcript level (replay is a no-op, `Q103`) and at the candidate level (`Q207`); merge at the fact level (`Q311`); append for genuinely new facts. Never preserve every occurrence, never purge-and-rebuild a changed source.
- **BECAUSE: ENGINEERING (E2)**, with the merge behaviour from **POSITION** (`P§4`).
- **REJECTED:** Purging and fully rebuilding a changed source (the surveyed answer). It wins on consistency with the source. It would destroy user corrections and suppressions attached to memories derived from that source — the `Q406`/`Q526` problem in its most concrete form.
- **COST:** A genuinely edited source transcript leaves stale derived memories unless explicitly reprocessed with `--replace` (`Q559`).
- **CONFIDENCE:** medium

---

### Q666 — Do memories decay, get reinforced, supersede, expire, or remain forever?

- **DECISION:** By tier: observations decay, hypotheses expire, stated memories remain until superseded or removed by the user. Nothing is reinforced by retrieval (`Q177`).
- **BECAUSE: POSITION.** `P§9`.
- **REJECTED:** Persisting until explicit deletion (the surveyed answer, and the most common one). See `Q525`.
- **COST:** As `Q24`.
- **CONFIDENCE:** medium

---

### Q684 — When information conflicts, should the system preserve alternatives, choose a winner, supersede history, or ask the user?

- **DECISION:** Choose a winner by precedence, supersede with history, and ask the user only for stated-level conflicts within budget (`Q310`).
- **BECAUSE: POSITION.** `P§4` + `P§9` + `P§8`.
- **REJECTED:** A 60-minute lability window blending by confidence, recency, and contradiction severity. It is the most sophisticated conflict design in the inventory and it handles graded disagreement, which this system cannot express (`Q42`). It wins if confidence existed. Blending also produces a claim whose content neither source asserted, which `Q311` rejects.
- **COST:** As `Q42` — no graded conflict; a partial contradiction is treated as a full one or not at all.
- **CONFIDENCE:** high

---

### Q709 — When stored reflections conflict or a later outcome discredits an earlier reflection, what should happen?

- **DECISION:** Not applicable — no reflections (`Q503`).
- **BECAUSE: POSITION.** `P§4`'s tiers.
- **REJECTED:** Appending and evicting by recency with no conflict, confidence, correction, or provenance rule. Wins never; the inventory's four-way absence is the point.
- **COST:** None here.
- **CONFIDENCE:** high

---

### Q735 — When retrieved memories conflict, should the system resolve silently, expose uncertainty, or seek confirmation?

- **DECISION:** Resolve by precedence where precedence applies, and **never silently** — the resolution is visible in the trace. Expose the conflict under Koottu. Seek confirmation only within budget (`Q206`, `Q789`).
- **BECAUSE: POSITION.** `P§8`'s trace makes silent resolution impossible by construction.
- **REJECTED:** Silently favouring the most recent unit (the surveyed answer). It wins on answer cleanliness. It is silent and it is recency-first — two rejections in one.
- **COST:** As `Q789` — Anbu abstention on conflict is opaque.
- **CONFIDENCE:** high

---

### Q758 — When the system is wrong, how should a user correct memory and prevent recurrence?

- **DECISION:** Duplicate of `Q15`/`Q608`. Four actions plus inline correction; recurrence prevented by an extractor-respected suppression record.
- **BECAUSE: POSITION.** `P§9`.
- **REJECTED:** Noting poisoning, auditing, user-controlled forgetting, and unlearning as future concerns with no protocol (the surveyed answer). It is the most common state in the inventory, and it is why this mechanism is a differentiator rather than table stakes.
- **COST:** As `Q506`.
- **CONFIDENCE:** high

---

### Q771 — When retrieved evidence is missing, ambiguous, or contradictory, should the system abstain, ask, expose uncertainty, or guess?

- **DECISION:** Abstain, expose, ask within budget. Never guess.
- **BECAUSE: POSITION.** `P§8`: "Kivi never fills a gap with a plausible guess."
- **REJECTED:** A prompt instructing the model to "try your best guess" when evidence is unavailable — the surveyed answer, quoted because it is the single most direct antithesis of `P§8` in the entire inventory. It wins on answer rate and on benchmark scores, since a guess sometimes lands and an abstention never does.
- **COST:** As `Q228`. And note the scoring asymmetry: on any benchmark that does not reward abstention, this decision costs points on every unanswerable question, by design (`Q591`).
- **CONFIDENCE:** high

---

### Q772 — When newer information conflicts with an older memory, should both remain, should one supersede the other, or should the system reconcile them into a revised claim?

- **DECISION:** Supersede (`Q13`). Never reconcile into a revised claim (`Q311`).
- **BECAUSE: POSITION.** `P§9`.
- **REJECTED:** Chronological threads retaining sequences with no contradiction policy. It preserves sequence — which `Q13` identifies as this design's real weakness for facts that were true in turn.
- **COST:** As `Q13`.
- **CONFIDENCE:** high

---

### Q785 — When facts conflict or a person changes, what should determine which version is current and what remains visible?

- **DECISION:** Precedence determines current (`Q672`); everything remains visible in history, and the memory surface can show a memory's change history on demand (`Q330`).
- **BECAUSE: POSITION.** `P§9`: "the superseded version stays in history so the change is auditable." And `P§1`'s third principle: "people change… A memory that can't be revised stops being memory and becomes a cage."
- **REJECTED:** Underspecified. Not a design.
- **COST:** As `Q13`.
- **CONFIDENCE:** high

---

### Q820 — When a fact changes or conflicts with stored memory, what should happen to the old and new versions?

- **DECISION:** A four-way verdict — DUPLICATE (evidence increment), ADD (new memory), SUPERSEDE (old marked superseded with a pointer), UPDATE (user correction only) — decided semantically and temporally at write time (`Q160`, `Q820`). Validity end times are recorded when the transcript states them (`Q848`).
- **BECAUSE: POSITION.** `P§9` + `P§4`.
- **REJECTED:** Nothing substantive — this surveyed answer (DUPLICATE/ADD/INVALIDATE/UPDATE with valid and invalid times) is the closest match in the entire inventory to what the position requires. The one difference: it records validity intervals on every edge, where this design records them only when stated (`Q848`), which is the weaker choice and the reason `Q13`'s sequence-fact gap exists.
- **COST:** As `Q13`/`Q848`.
- **CONFIDENCE:** high

---

### Q853 — How wide a net does contradiction-detection cast?

- **DECISION:** Top-s most similar memories across the whole store, regardless of entity (`Q523`). Not only memories sharing an entity pair.
- **BECAUSE: ENGINEERING.** Position is silent. Preferences and episodes contradict without sharing an entity pair — "I write client emails in prose" versus "use bullets for Acme" involves different entities — so an entity-pair restriction would miss the contradictions that matter most for preferences, which are the product's most valuable type.
- **REJECTED:** Restricting to semantically related edges between the same entity pair. It wins on precision and cost — far fewer comparisons, far fewer false positives. It is exactly right for an entity-relation graph and wrong for a store whose most important memories are preferences.
- **COST:** More comparisons per write and more false-positive contradiction candidates to adjudicate (`Q540`).
- **CONFIDENCE:** medium

---

### Q855 — May the system decline to resolve a contradiction?

- **DECISION:** Yes, and it must, in one specific case: a contradiction involving a **stated** memory is not resolved by the system (`Q206`, `Q310`). Every other contradiction is resolved by precedence.
- **BECAUSE: POSITION.** `P§9` reserves changes to stated beliefs for the user; `P§4`'s stated tier means "the user said it," and only the user can unsay it.
- **REJECTED:** Resolving every detected contradiction immediately in favour of the newer claim (the surveyed answer). It wins on store consistency — no contradictions ever coexist. It means new evidence silently overrides something the user told Kivi, which is the "silently enforces things you never agreed to" failure applied to correction.
- **COST:** The store can hold an unresolved contradiction indefinitely, and every query touching it either abstains (Anbu) or surfaces it (Koottu). A user who never visits Koottu never learns it exists (`Q789`, **Section A**).
- **CONFIDENCE:** high

---

### Q861 — Does anything lose standing without being contradicted?

- **DECISION:** Yes — observations decay and hypotheses expire, both without contradiction (`Q51`, `Q283`).
- **BECAUSE: POSITION.** `P§9`: "An observation not re-observed within a window loses standing… Behaviour from six months ago should not be presented as who you are."
- **REJECTED:** Facts remaining current until contradicted, with no decay, expiry, last-seen field, or confirmation event (the surveyed answer). The inventory names four missing mechanisms in one clause, and this position supplies all four. That is a fair summary of what `P§4` and `P§9` add to the state of the art.
- **COST:** As `Q24` — two unset windows shipped on judgement.
- **CONFIDENCE:** medium

---

## Stage: LIFECYCLE

---

### Q09 — When an episode contains both useful and irrelevant or hazardous details, what should be discarded before storage?

- **DECISION:** Discarded before storage: excluded-category content, third-party personal content, characterisations, and literal secrets — by a code check on candidates, with reason-coded logs (`Q655`, `Q851`). Nothing else is discarded for being "irrelevant"; irrelevance is handled by the eligibility gates, not by a salience judgement (`Q721`).
- **BECAUSE: POSITION.** `P§2` and `P§5`.
- **REJECTED:** Capturing outcome and key workflows with no privacy, subject, sensitivity, or claim-level retention filter (the surveyed answer, and the inventory notes this absence as an inference across several sources). It wins on capability.
- **COST:** As `Q307`/`Q851`.
- **CONFIDENCE:** high

---

### Q10 — How should the system represent and recover from a wrong merge or deletion?

- **DECISION:** A wrong **merge** is recovered by re-extracting from the listed source transcripts, which is possible because every memory keeps its sources (`Q173`) — but it is not a one-click undo, and the position does not provide one. A wrong **deletion** (`Forget`) is not recoverable, deliberately: the memory and its history are purged. A wrong **demotion** is recoverable, because the row survives and the suppression can be lifted.
- **BECAUSE: POSITION for the asymmetry.** `P§9` distinguishes "Forget (remove + suppress)" from "That's not me anymore (demote + suppress)" — the first removes, the second does not. A reversible Forget would make the two actions the same.
- **REJECTED:** A thorough multi-tier delete with full audit records enabling recovery (the surveyed answer, which the inventory notes is the only one of thirty techniques that tries). It wins on safety — an accidental Forget is unrecoverable here, and `Q611` notes corrections are deliberately ceremony-free, which makes an accidental Forget plausible. **These two decisions are in tension and Forget needs a confirmation step that the position does not mention.** Flagged in **Section A**.
- **COST:** Unrecoverable accidental deletion; no one-click merge undo.
- **CONFIDENCE:** medium

---

### Q29 — Should memory management and response generation share a model or be isolated components?

- **DECISION:** Isolated components with separate prompts and separately pinned models (`Q531`, `Q794`). Extraction, exclusion classification, and sameness judgement are memory-management roles; tool selection and wording are generation roles. They never share a call.
- **BECAUSE: POSITION.** `P§2`'s requirement that the exclusion check be a separate check rather than an instruction inside a larger prompt; `Q247`'s general rule.
- **REJECTED:** One model doing generation, summarisation, and linking via task prefixes. It wins on cost and operational simplicity. It makes the exclusion check a prompt section, which is precisely what `P§2` forbids.
- **COST:** More calls per transcript and more model surface to maintain and price (`Q701`).
- **CONFIDENCE:** high

---

### Q32 — When raw episodes imply a reusable pattern, what should authorize consolidation into semantic memory?

- **DECISION:** **N independent transcripts with no contradicting instance in the window** authorises creating an *observation* — which is a pattern at the observed tier, not a fact. Only user confirmation authorises it becoming stated (`Q139`, `Q191`). There is no separate consolidation step producing a different kind of object.
- **BECAUSE: POSITION.** `P§4`: an observation is "a pattern across multiple transcripts, pointable-at," and "Nothing self-promotes."
- **REJECTED:** Periodic consolidation summarising episodes into semantic knowledge — whose own source calls the heuristics "fragile" and the policy "underspecified." That candour is the argument: consolidation policies are hard to get right and this design avoids needing one by making the pattern a tier rather than a transformation.
- **COST:** N is unset (**Section A**), and the window for "no contradicting instance" is the same unset decay window (`Q24`).
- **CONFIDENCE:** medium

---

### Q38 — As time passes without confirming evidence, should a memory remain stable, decay, expire, or be revalidated?

- **DECISION:** By tier: stated stays stable; observed decays; hypothesised expires. Revalidation only through a budgeted confirmation (`Q283`, `Q861`).
- **BECAUSE: POSITION.** `P§9`.
- **REJECTED:** Accumulate forever. See `Q525` — and note this is the fifth inventory question that is the same decision (see **Section C**).
- **COST:** As `Q24`.
- **CONFIDENCE:** medium

---

### Q49 — After a user rejects or deletes a derived memory, should the same conclusion be allowed to reappear from the same evidence?

- **DECISION:** No. A suppression record is written and consulted by the extractor on every subsequent run, including full reprocessing and model upgrades (`Q608`).
- **BECAUSE: POSITION.** `P§9`: "deleting the row is useless, because the same pattern will regrow from the same transcripts within a week. The action must record a suppression that the extractor respects going forward."
- **REJECTED:** Deletion across all tiers and backups without preventing re-derivation from retained sources — which is what both surveyed camps do, and the inventory flags the same gap in both. It wins on a clean privacy story (nothing retained). It fails the only test that matters to the user: whether the thing comes back.
- **COST:** As `Q506`/`Q622` — a suppression record that describes what it suppresses, and **Section B, conflict B5**.
- **CONFIDENCE:** high

---

### Q53 — When memories age or cease to be re-observed, should they remain equally active, decay, expire, archive, or require reconfirmation?

- **DECISION:** Decay (observations), expire (hypotheses), remain (stated). No archiving, no mandatory reconfirmation (`Q38`).
- **BECAUSE: POSITION.** `P§9`.
- **REJECTED:** Weekly lossy reflection merging cluster members and hiding originals — notable because the surveyed system ships it **disabled**. A lossy consolidation that hides originals is `Q311`'s rejected synthesis plus `Q68`'s destructive merging, and its own authors turned it off.
- **COST:** As `Q24`.
- **CONFIDENCE:** medium

---

### Q60 — At what point should the system turn language into structured facts, and how exhaustive should that extraction be?

- **DECISION:** At transcript completion, asynchronously (`Q242`), and **selectively, not exhaustively** — only candidates passing the four gates become facts (`Q307`). Exhaustiveness is explicitly not the goal.
- **BECAUSE: POSITION.** `P§3`: "A memory system may be capable of learning ten things while only three of them create meaningful value" is the brief's framing, and `P§3`'s test — annoyed to repeat it / unsettled to learn it was recorded — is a selection criterion, not an extraction-completeness criterion.
- **REJECTED:** Real-time exhaustive extraction of every factual element from each utterance (the surveyed answer). It wins on recall and is the higher-scoring choice on any benchmark. Exhaustive extraction plus no category exclusion is precisely how a psychological profile assembles itself without anyone deciding to build one (`P§2`).
- **COST:** As `Q307` — recall capped by four gates with false positives.
- **CONFIDENCE:** high

---

### Q46 — When a user retracts, corrects, forgets, or suppresses a belief, what durability and propagation guarantee should that negative update receive?

- **DECISION:** The strongest guarantee in the system. A negative update is: committed synchronously; durable across reprocessing, model upgrades, and index rebuilds; propagated to the extractor as a standing suppression; and **never silently dropped** — a suppression that cannot be applied is a loud failure, not a skipped step.
- **BECAUSE: POSITION.** `P§9`: "Otherwise the user learns that their corrections don't stick, which is the fastest way to lose them." That sentence makes negative updates the most durability-critical writes in the product — more so than the memories themselves, since a lost memory is a gap and a lost suppression is a betrayal.
- **REJECTED:** Treating negative updates like any other write. It wins on implementation uniformity. It is the near-universal state in the inventory, and `Q381`'s observation — "no general suppression/tombstone model is visible" — is the field's honest summary.
- **COST:** Suppressions are a second, permanent, monotonically growing store that every extraction consults, and a full reprocess must replay them before extracting, not after.
- **CONFIDENCE:** high

---

### Q83 — Who decides what is memorable: an upstream agent/user, or a memory-owned extractor?

- **DECISION:** A memory-owned extractor, gated by memory-owned rules. The application submits transcripts; it does not submit curated memories. The one exception is a direct user action on the memory surface (`Q620`).
- **BECAUSE: POSITION.** `P§2`: the exclusion check runs on candidates inside the memory system, "before anything reaches storage." If an upstream caller submitted finished memories, the check would be advisory rather than structural.
- **REJECTED:** The agent deciding, with persistence accepting already-curated observations (the Engram answer). It wins for a memory service with many clients, each knowing its own domain. It would put the write-path promise outside the component that makes it.
- **COST:** No way for a well-informed caller to contribute a memory directly, and extraction quality is the sole determinant of what is learned.
- **CONFIDENCE:** high

---

### Q95 — Does old knowledge expire, disappear from retrieval, or merely require review?

- **DECISION:** By tier, not by type. Observations disappear from surfacing (decay); hypotheses expire; stated memories neither expire nor require review. There are **no type-based review dates**.
- **BECAUSE: POSITION.** `P§4`'s two independent axes: a review schedule keyed to type (preferences 3 months, decisions 6, policies 12) would make type carry epistemic weight, which `P§4` says is the collapse to avoid. And `P§8`'s prompt budget forbids scheduled review: "Never as a review queue."
- **REJECTED:** Type-keyed review dates with virtual review state. It is a thoughtful design and its instinct — preferences go stale faster than policies — is probably correct. It wins if review could be free. `P§8` prices it: "A prompt is a cost paid by the user."
- **COST:** A stale stated preference is never revisited unless the user notices (`Q283`, **Section A**).
- **CONFIDENCE:** high

---

### Q105 — Are consolidations a separate retrieval tier?

- **DECISION:** There are no consolidations (`Q32`). An observation is an ordinary memory at the observed tier, retrieved through the same path as everything else — not a separate tier with its own access.
- **BECAUSE: POSITION.** `P§4`'s schema is one schema across tiers, and `P§6`'s dial gates all tiers through one mechanism.
- **REJECTED:** A distinct consolidation-history tool and tier. It wins for inspecting how knowledge formed. Here that need is served by the observation's evidence links and the memory's change history (`Q330`).
- **COST:** None material.
- **CONFIDENCE:** high

---

### Q110 — Is consolidation a one-way ratchet?

- **DECISION:** Nothing is a one-way ratchet. Every state change is reversible or recorded: promotion is reversible by demotion; supersession keeps history; the only irreversible operation is `Forget`, and that irreversibility is deliberate (`Q10`).
- **BECAUSE: POSITION.** `P§1` principle 3: "A memory that can't be revised stops being memory and becomes a cage." A ratcheting flag is a cage.
- **REJECTED:** A one-way consolidated flag that nothing flips back (the surveyed answer). It wins on idempotence and simplicity. It is the mechanism by which a system's beliefs become unchangeable.
- **COST:** More state transitions to implement and test; every reversal path needs a test.
- **CONFIDENCE:** high

---

### Q111 — When does consolidation run — on volume, on time, or on demand?

- **DECISION:** Not applicable as a separate process. Observation detection runs incrementally per transcript on the write path (`Q680`); decay and expiry run on a scheduled sweep (`Q313`). Neither is volume-triggered and neither is on demand.
- **BECAUSE: ENGINEERING (E3)** for the incremental half; **POSITION** (`P§9`) for the sweep, since decay is a function of elapsed time and must run whether or not anything is written.
- **REJECTED:** A fixed timer gated by a count, plus a manual endpoint. It wins on batching efficiency (`Q680` notes the real argument for a periodic observation pass). The manual endpoint is also genuinely useful for a reviewer, and `RUN.md` should expose the sweep as a runnable command even though it is scheduled.
- **COST:** Per-transcript observation detection is more expensive than a periodic pass (`Q680`).
- **CONFIDENCE:** medium

---

### Q116 — If deleting a path would orphan descendants, reject, cascade-delete, or auto-heal?

- **DECISION:** There is no path hierarchy to orphan (`Q784`, `Q395`). The analogous case — deleting an **entity** that memories reference — is rejected: entities are not user-deletable while referenced; the user forgets *memories*, and an entity with no remaining memories is garbage-collected silently since it holds no content of its own.
- **BECAUSE: ENGINEERING (E4).** Position is silent. Cascade-deleting memories because an entity was removed would delete beliefs the user did not ask to remove, which `P§9`'s per-entry control forbids.
- **REJECTED:** Cascade or auto-heal with UUID-suffixed rehoming. It wins in a hierarchical store; there is no hierarchy here.
- **COST:** "Forget everything about Priya" is not a single action — it is many memory-level Forgets. That is a plausible user request with no affordance (**Section A**).
- **CONFIDENCE:** medium

---

### Q124 — At what unit should retrieval operate: whole conversations, turns, passages, facts, or entities?

- **DECISION:** Facts, primarily; entities as an expansion mechanism; whole transcripts only on the labelled fallback (`Q43`, `Q118`). Never turns or passages.
- **BECAUSE: POSITION.** `P§4`'s unit is the fact; `P§8`'s trace attributes answers to memories.
- **REJECTED:** Passage-level retrieval. It wins on context fidelity (`Q586`) and would address the narrative gap. It has no tier.
- **COST:** As `Q570`.
- **CONFIDENCE:** high

---

### Q140 — What unit owns isolation: person, agent, project, tenant, or source?

- **DECISION:** Nothing owns isolation — there is one user, one namespace, no partitioning (`Q121`, `Q78`). The only structural boundary is the surface path (`Q89`).
- **BECAUSE: ENGINEERING (E1)**, with **POSITION** supplying the one boundary that does exist (`P§7`).
- **REJECTED:** A per-agent namespace. See `Q121` — even the cheap forward-compatible version is declined, because an unenforced namespace implies isolation that does not exist.
- **COST:** As `Q82` — multi-tenancy is a schema-wide migration.
- **CONFIDENCE:** high

---

### Q175 — Is diversity or redundancy managed at read time?

- **DECISION:** No. Redundancy is managed at **write** time by merging (`Q311`); read time applies no diversity mechanism (`Q561`).
- **BECAUSE: POSITION.** `P§4`'s `evidence_count` is the redundancy mechanism, and it operates on write. Applying diversity at read would hide memories the user can see on the memory surface, producing an inconsistency between what Kivi shows and what Kivi uses.
- **REJECTED:** Read-time diversity as an optional menu. It wins when write-time dedupe is unreliable — which `Q479` warns it may be. That dependency is real: read-time MMR is the cheap insurance against merge failures, and declining it means merge quality has no backstop.
- **COST:** As `Q561` — an over-split fact can monopolise a result set.
- **CONFIDENCE:** medium

---

### Q176 — Decay by wall-clock age, or by idle time since last use?

- **DECISION:** By **time since last re-observation** — that is, since new evidence last arrived — not by wall-clock age from creation and not by idle time since last retrieval.
- **BECAUSE: POSITION.** `P§9`: "An observation **not re-observed** within a window loses standing." Re-observation is new evidence, not a read. Decaying by idle-since-last-use would make standing depend on what the user asked about, which is `Q177`'s rejected reinforcement inverted.
- **REJECTED:** Idle time since last use (the surveyed answer). It wins as a usefulness proxy — memories nobody needs fade. It makes standing a function of query history, which is neither evidence nor a user action.
- **COST:** A behaviour the user genuinely still has but has not dictated about recently decays out of surfacing, even if they ask about it constantly.
- **CONFIDENCE:** high

---

### Q178 — Are some memories exempt from decay?

- **DECISION:** Yes, explicitly: **stated memories never decay**, and **pinned memories never decay** regardless of tier. Only observed and hypothesised memories are subject to time.
- **BECAUSE: POSITION.** `P§9` applies decay specifically to observations ("An observation not re-observed…") and expiry specifically to hypotheses. Stated memories are outside both sentences, and `P§4` gives them "Treat as true. Use freely" with no time qualifier. Pinning is a user action (`Q315`) and user actions outrank system mechanisms (`Q604`).
- **REJECTED:** No exemptions, applied uniformly and admitted as such (the surveyed answer). It wins on uniformity and avoids a stated memory going stale forever (`Q95`). It would mean something the user explicitly told Kivi fades without their involvement, which inverts `P§9`'s control promise.
- **COST:** A stated fact from three years ago is treated exactly like yesterday's (`Q283`, **Section A**).
- **CONFIDENCE:** high

---

### Q179 — Does storage pressure change the forgetting policy?

- **DECISION:** No. There is no storage-pressure mechanism and no capacity-driven forgetting (`Q54`, `Q750`).
- **BECAUSE: POSITION.** `P§9` reserves removal for the user. A policy that forgets more aggressively when the disk fills means what Kivi remembers about you depends on disk utilisation — indefensible in a product whose claim is that you control what it thinks.
- **REJECTED:** A prune threshold rising with utilisation (the surveyed answer, and a perfectly sensible engineering mechanism). It wins at scale, and at scale this system has no answer (`Q54`).
- **COST:** Unbounded growth with no relief valve. At a much larger corpus this is a genuine failure mode, not a deferred nicety.
- **CONFIDENCE:** high for this build, low as a permanent answer.

---

### Q190 — May deleted/corrected beliefs regrow from old evidence?

- **DECISION:** No. Duplicate of `Q49`/`Q608`. Suppression records block re-derivation, and `P§AppC` claim 6 is the test.
- **BECAUSE: POSITION.** `P§9`.
- **REJECTED:** See `Q49`.
- **COST:** See `Q49`.
- **CONFIDENCE:** high

---

### Q192 — How is recency/use turned into forgetting?

- **DECISION:** Recency of **evidence** drives decay of observations (`Q176`); use drives nothing (`Q177`). Neither produces deletion — only loss of standing (`Q602`).
- **BECAUSE: POSITION.** `P§9`.
- **REJECTED:** Use-driven forgetting. See `Q176`/`Q177`.
- **COST:** As `Q176`.
- **CONFIDENCE:** high

---

### Q197 — Automatically retain bounded lifecycle projections, or require explicit semantic admission?

- **DECISION:** Explicit semantic admission through four gates (`Q307`). Nothing is retained automatically for being a bounded projection of activity.
- **BECAUSE: POSITION.** `P§3`'s two tests are admission criteria; `P§2`'s exclusions are admission blocks.
- **REJECTED:** Automatic capture with manual writes only for explicitly durable knowledge. It wins on recall and on not missing things. Automatic capture with configurable exclusions is precisely the "line in a prompt hoping for good behaviour" posture `P§2` rejects, moved to a config file.
- **COST:** As `Q307`.
- **CONFIDENCE:** high

---

### Q227 — What should the user actually see: graph structure, numeric effects, natural-language explanations, or an action trace?

- **DECISION:** Natural-language explanations plus a structured trace, in one surface, with no graph visualisation and no numeric scores presented as meaning. Specifically: which memories were used (as sentences), which were withheld and why (in plain words), what was searched, and one tap to the source transcript.
- **BECAUSE: POSITION.** `P§8`: "if the explanation is only intelligible to a developer, we've failed the brief's requirement that the product be legible to a normal user." `P§9`: "No developer console anywhere in this."
- **REJECTED:** Exposing graph paths and numeric effect values. It wins for a technical audience and is more complete. It is the developer console `P§9` forbids.
- **COST:** Engineering diagnostics have nowhere to live (`Q405`, **Section A**).
- **CONFIDENCE:** high

---

### Q232 — When an LLM must behave over time and act in a world, should the LLM itself be treated as the agent, or as one component inside a larger system?

- **DECISION:** One component — several components, in fact — inside a system whose control flow, promises, and state are owned by deterministic code (`Q247`, `Q533`).
- **BECAUSE: POSITION.** `P§2`: exclusions enforced "by a check… not by a line in a prompt hoping for good behaviour." That is a statement about where authority lives.
- **REJECTED:** The LLM as the agent. It wins on capability breadth and adaptability. Every product promise would then rest on prompt compliance.
- **COST:** As `Q247` — rigidity; unanticipated cases handled badly.
- **CONFIDENCE:** high

---

### Q233 — What top-level concepts should partition an agent so that designs can be compared and assembled?

- **DECISION:** For Kivi: **memory** (typed store with tiers), **retrieval** (two paths), **disclosure** (the dial), **tools** (three), and **inspection** (the trace). Disclosure as a top-level concept is the non-standard one, and it is the product.
- **BECAUSE: POSITION.** `P§1` principle 1 makes disclosure a first-class concern separate from memory and retrieval: "Retrieval and disclosure must be separable."
- **REJECTED:** CoALA's memory / action space / decision-making partition. It is a good general partition and it has no slot for disclosure — which is exactly why the surveyed systems built from it have no disclosure layer (`Q529`, `Q736`, `Q577`).
- **COST:** Kivi's architecture does not map cleanly onto the standard agent vocabulary, which makes it harder to describe to people who know that vocabulary. The README has to introduce a term.
- **CONFIDENCE:** high

---

### Q236 — When the environment is non-textual or structured, what representation should mediate between it and the language model?

- **DECISION:** Text throughout (`Q98`). Structured data — entity rows, tiers, scores — is rendered into labelled text sections for the model, and the model's outputs are parsed back into typed structures with strict validation (`Q72`).
- **BECAUSE: ENGINEERING**, with the text-client scope from **POSITION** (the position's scope note).
- **REJECTED:** Richer modality mediation. Out of scope.
- **COST:** None here.
- **CONFIDENCE:** high

---

### Q237 — Which external worlds should count as first-class agent environments?

- **DECISION:** One: the text client, replaying transcripts, application context, and Hey Kivi requests. No physical environment, no live APIs, no code execution, no browsing.
- **BECAUSE: POSITION.** The scope note: "Transcripts, application context, and Hey Kivi requests are replayed through an interface of our own design." The brief agrees: "You may replay transcripts, application context, and other events through a client of your own design."
- **REJECTED:** Live integrations. It wins on realism and would make the *schedule* tool real rather than simulated (`Q246`). That is the weakest of the three tools precisely because it has no environment to act on, and this decision is why.
- **COST:** The schedule/reschedule tool acts on internal state only, which makes it the least convincing demonstration of the three (`Q246`).
- **CONFIDENCE:** high

---

### Q238 — When information is needed from long-term memory, should recall be an implicit side effect of prompting or an explicit action in the agent's action space?

- **DECISION:** Neither, exactly: retrieval is an **explicit pipeline stage in code**, run before the model is called, not an action the model chooses (`Q542`) and not an implicit side effect of a prompt template.
- **BECAUSE: POSITION.** `P§6`: "Kivi always retrieves everything it has" — always, not when the model decides. And `P§8`'s trace requires the retrieval to be a recorded stage with known inputs.
- **REJECTED:** Retrieval as an explicit internal action in the model's action space (the CoALA answer). It wins on adaptivity — the model retrieves when it needs to and can retrieve again (`Q542`). It makes retrieval conditional on model judgement, which breaks the always-retrieve guarantee that the withheld count depends on.
- **COST:** As `Q18`/`Q452` — every request pays retrieval; and as `Q542` — no iterative deepening.
- **CONFIDENCE:** high

---

### Q241 — When an agent can change its own behavior, which parts may be learned and which must remain designer-controlled?

- **DECISION:** Nothing is learned. Prompts, code, rules, thresholds, and the exclusion list are all designer-controlled and change only by release (`Q131`, `Q605`). What changes at runtime is *memory content*, which is the user's, not Kivi's behaviour.
- **BECAUSE: POSITION.** `P§2`'s exclusions are a product promise; `P§6`'s dial is an explicit user setting; `Q247` puts promises in code. A system that rewrites its own prompts can rewrite its promises.
- **REJECTED:** Procedural learning including code skills and prompt updates — which the CoALA source itself flags as "riskier" and "mostly unstudied." That candour is the argument.
- **COST:** As `Q131`/`Q457` — Kivi never improves from use.
- **CONFIDENCE:** high

---

### Q243 — When an agent has several possible internal and external moves, what process should determine the next one?

- **DECISION:** A fixed pipeline, not a decision cycle: retrieve → filter by disclosure → select one tool from three → execute → generate → record trace. No planning loop, no candidate evaluation, no feedback step.
- **BECAUSE: ENGINEERING (E5)**, with **POSITION** forbidding the feedback step (`Q239` — nothing derived mid-task becomes durable).
- **REJECTED:** A repeated propose/evaluate/select/execute/feedback cycle. It wins for multi-step tasks. Kivi's three tools are single-turn (`Q252`).
- **COST:** No multi-step tasks. A request needing two tools in sequence is not served.
- **CONFIDENCE:** high

---

### Q249 — When an agent is uncertain, tied, missing evidence, or unable to act, what should happen?

- **DECISION:** Abstain and say what is missing (`Q135`). No impasse subgoaling, no replanning, no candidate rejection loop.
- **BECAUSE: POSITION.** `P§8`: abstention is "a designed feature with a visible surface, not a fallback for when generation fails."
- **REJECTED:** Impasse-driven subgoal creation. It wins in a problem-solving agent. Kivi's uncertainty is about what it knows, not about how to act, and the honest response to not knowing is to say so.
- **COST:** As `Q228`.
- **CONFIDENCE:** high

---

### Q258 — Should reasoning and memory maintenance be performed by the same model invocation or separated into roles?

- **DECISION:** Separated, into separate calls with separate prompts and separately pinned models (`Q29`, `Q794`).
- **BECAUSE: POSITION.** `P§2`'s separate-check requirement.
- **REJECTED:** A capable reasoning agent plus a lightweight memory agent cooperating — which is close to the same answer, and reasonable. The difference is that "cooperating agents" implies the memory agent makes judgement calls at runtime; here the memory components are pipeline stages whose outputs are validated by code.
- **COST:** As `Q701` — more calls, more cost.
- **CONFIDENCE:** high

---

### Q259 — When should memory maintenance block the user-visible response?

- **DECISION:** Never, with one exception: a **user correction** blocks, because it must be true before the next answer (`Q62`, `Q382`). Extraction, observation detection, decay sweeps, and index maintenance are all asynchronous.
- **BECAUSE: ENGINEERING (E3)** for the general rule; **POSITION** for the exception — `P§8`'s "*No, Priya's at Northwind now*… should update the entity without ceremony" means the update is in effect immediately, or the correction has not stuck.
- **REJECTED:** Fully asynchronous maintenance including corrections. It wins on response latency uniformly. A correction that takes effect eventually is the `P§9` failure.
- **COST:** Two write paths with different timing that must not race (`Q62`), and a correction's latency is user-visible.
- **CONFIDENCE:** high

---

### Q263 — What should be discarded as an interaction ages, and what should survive?

- **DECISION:** Per-request state is discarded at request end (`Q538`). Traces survive (`Q426`). Transcripts survive permanently (`Q28`). Memories survive subject to tier-based standing (`Q38`). Nothing is discarded on an age schedule.
- **BECAUSE: POSITION.** `P§9` (transcripts, memory standing) and `P§8` (traces).
- **REJECTED:** Deleting expired sessions and cached entries. There are no sessions to expire (`Q250`).
- **COST:** Traces grow without bound and are never pruned — a real contributor to the brief's "database growth" metric that the position never considers (**Section A**).
- **CONFIDENCE:** medium

---

### Q266 — What should determine garbage-collection timing: clock time, capacity, events, task completion, or user action?

- **DECISION:** Clock time, for the one sweep that exists (decay and expiry, `Q111`). Not capacity (`Q179`), not events, not user action.
- **BECAUSE: POSITION.** `P§9`'s decay is defined by a window, which is a clock concept.
- **REJECTED:** Event-triggered GC to bound latency independently of session length. It wins for long sessions; there are none.
- **COST:** A sweep must run for decay to take effect, so a system that is never started for a month applies a month of decay at once — which is correct but will look abrupt.
- **CONFIDENCE:** medium

---

### Q278 — Should write policy vary by user, agent, time, or system, and where should the default live?

- **DECISION:** One global system-level policy, in code, invariant across users and time (`Q605`, `Q597`). The only per-user variation in the product is the disclosure dial, which is not a write policy.
- **BECAUSE: POSITION.** `P§2`'s exclusions are a product promise, and `Q604` establishes they are not user-overridable.
- **REJECTED:** Permitting all four scopes. It wins on flexibility and would allow a user to opt into remembering more. See `Q604`'s cost — this is the same limitation and it is real.
- **COST:** As `Q604` — no informed-consent exception.
- **CONFIDENCE:** high

---

### Q286 — When several specialists could answer, who chooses which agents run and when to stop?

- **DECISION:** Not applicable — no specialists (`Q300`). One model call selects one tool from three (`Q244`).
- **BECAUSE: ENGINEERING (E5).**
- **REJECTED:** A coordinator emitting one agent/subquery per round. Wins for broad action spaces.
- **COST:** None here.
- **CONFIDENCE:** high

---

### Q287 — When agents produce multiple partial answers, how should disagreement, omission, and ordering affect the final response?

- **DECISION:** Not applicable — one answer from one call (`Q286`). Where *memories* disagree, `Q789` applies: surface rather than silently synthesise.
- **BECAUSE: ENGINEERING (E5)**, with **POSITION** for the memory-disagreement half (`P§8`).
- **REJECTED:** An aggregator synthesising subquery responses with conflict handling and citation preservation underspecified. The unpreserved citations are the specific failure: synthesis across sources is where provenance usually dies (`Q860`).
- **COST:** None here.
- **CONFIDENCE:** high

---

### Q306 — When current language supports both a direct fact and a higher-level inference, what level of abstraction should be stored?

- **DECISION:** The direct fact, at stated tier. The higher-level inference is stored **only** if it is a pattern across multiple transcripts (then it is an observation at observed tier) or a proposed reason (then it is a question at hypothesised tier, expiring). A single utterance never yields a higher-level inference.
- **BECAUSE: POSITION.** `P§2`'s soft failure: "'You've been dictating late, you must be behind.' Possibly true. Also possibly none of Kivi's business." `P§4`: observations require "multiple transcripts."
- **REJECTED:** Generating two insights per input — one direct, one high-level — through integration and inference (the surveyed answer). It wins on richness and on answering broad questions. Generating a high-level inference from a single utterance is the mechanism `P§2` names, and doing it routinely is how a profile accumulates.
- **COST:** Kivi misses inferences a human would draw immediately. It needs repetition to notice anything.
- **CONFIDENCE:** high

---

### Q321 — At what memory scale should retrieval and refinement remain correct, and what maintenance mechanism should appear as the store grows?

- **DECISION:** Correctness is targeted at the brief's scale — ~500 transcripts, memories in the low hundreds — and the evaluation reports behaviour at that scale honestly rather than claiming more. The maintenance mechanisms that exist (decay, expiry, supersession, suppression) are not capacity mechanisms and do not bound growth (`Q54`, `Q179`).
- **BECAUSE: ENGINEERING (E5)**, and honesty about it is **POSITION**-adjacent: `P§AppB` defers parameters until corpus data exists rather than guessing, and the same discipline applies to scale claims.
- **REJECTED:** Claiming scale not demonstrated. Also rejected: building capacity management now (`Q179`). The honest position is that this system has no scale story and says so.
- **COST:** No scale story. At 10× the corpus the memory surface, the write-time contradiction search (`Q540`), and the unbounded trace store (`Q263`) all degrade, and none has a designed remedy.
- **CONFIDENCE:** high

---

### Q325 — Should old information decay, remain indefinitely, or change standing based on type, reaffirmation, and time?

- **DECISION:** Change standing based on **tier**, reaffirmation, and time — not type (`Q95`, `Q38`).
- **BECAUSE: POSITION.** `P§4`'s two independent axes; type must not carry epistemic weight.
- **REJECTED:** Type-based standing. See `Q95`.
- **COST:** As `Q95`.
- **CONFIDENCE:** high

---

### Q333 — What should determine the unit and timing of memory extraction: per turn, per transcript, scheduled batch, periodic narrative synthesis, or on demand?

- **DECISION:** Per transcript, asynchronously on arrival (`Q242`, `Q515`). Not per turn, not scheduled, never narrative synthesis, not on demand.
- **BECAUSE: ENGINEERING (E3)**, with `P§AppB` deferring timing and `P§9` fixing the transcript as the provenance unit.
- **REJECTED:** Periodic narrative synthesis. See `Q323`/`Q570`.
- **COST:** As `Q62` — the freshness window.
- **CONFIDENCE:** high

---

### Q335 — What security and isolation boundary should protect a longitudinal memory: ordinary application storage, encrypted per-user vault, local-only storage, purpose-separated stores, or no persistent sensitive data?

- **DECISION:** Primarily **no persistent sensitive data** — the exclusion list and the third-party barrier mean the categories that would need a vault are never stored (`Q851`, `Q668`). Secondarily, local-only embedded storage (`Q90`). Not an encrypted vault, not purpose-separated stores.
- **BECAUSE: POSITION.** `P§2` and `P§5` make non-retention the primary protection; `Q668` establishes that locality is not the privacy story. The strongest protection this product offers is that the sensitive thing was never written.
- **REJECTED:** An encrypted per-user vault. It wins for a product that must store sensitive data — and note that this system **does** store one sensitive thing: the raw transcripts, which contain everything the memory layer refused (`Q28`). A vault for the transcript store is the strongest available mitigation of **Section B, conflict B2**, and declining it is the weakest link in the privacy story. At-rest encryption of the transcript store is a cheap, honest addition that the position does not mention and probably should.
- **COST:** The raw transcript store is protected only by filesystem permissions, while holding the material the product most loudly refuses to remember.
- **CONFIDENCE:** medium

---

### Q336 — When the model derives a narrative or psychological interpretation from sources, should deleting a source also delete, recompute, or preserve the derived belief?

- **DECISION:** There are no narrative or psychological interpretations (`Q779`, `Q801`). For ordinary derived memories: deleting a **source transcript** is not an offered operation — transcripts are immutable (`Q28`). Deleting a **memory** is `Forget`, and it does not touch sources. The two are deliberately decoupled.
- **BECAUSE: POSITION.** `P§9` gives the user control over *memories*, and provenance requires sources to persist. The position never offers transcript deletion, and that omission is itself a decision worth surfacing — **Section A**.
- **REJECTED:** Cascading source deletion to derived beliefs. It wins as a data-subject-rights mechanism ("delete this dictation and everything from it"), which is a request a user will reasonably make and which this product cannot satisfy.
- **COST:** No "delete this dictation" operation. Given `Q28`'s permanent transcript store, this is a meaningful gap (**Section B, conflict B2**).
- **CONFIDENCE:** medium

---

### Q338 — When multiple components can access memory, should semantic memory be treated as shared distributed state or as private state scoped to one client/agent?

- **DECISION:** Private state, single-owner, single-process, accessed through one service boundary (`Q579`, `Q660`). Not shared distributed state.
- **BECAUSE: ENGINEERING (E1, E2).**
- **REJECTED:** A shared data store read and written by multiple agents. Wins at scale; brings `Q339`'s consistency questions with it.
- **COST:** As `Q339` — no distribution path.
- **CONFIDENCE:** high

---

### Q343 — When the system converts language into durable memory, how should meaning and retrieval structure be represented?

- **DECISION:** Meaning as typed claims in natural language (`Q63`); retrieval structure as three parallel indexes over them plus an entity graph (`Q727`). The two are separate: meaning is what the user reads, structure is how it is found, and the structure never determines the meaning.
- **BECAUSE: POSITION.** `P§9` (readable meaning) and `P§4` (typed claims). The separation matters because `Q143` shows what happens when retrieval structure leaks into the representation — folding metadata into the embedded string.
- **REJECTED:** Hierarchical/graph memory with semantic anchoring, unchosen among alternatives. Not a decision.
- **COST:** As `Q752` — a shallow graph means weak multi-hop.
- **CONFIDENCE:** high

---

### Q373 — Is the deployment simultaneously capable of chat and agent memory, or does one process choose one mode?

- **DECISION:** One process serves both surfaces simultaneously, with the separation enforced by **path**, not by process mode (`Q06`). A restart is never needed to change behaviour.
- **BECAUSE: POSITION.** `P§7`'s boundary is structural within the system, not a deployment mode: "two separate retrieval paths." Both paths exist at once because both surfaces exist at once.
- **REJECTED:** One process, one mode, restart to change (the surveyed answer). It wins on isolation — the wrong path literally cannot run. It would mean a user cannot dictate and ask Hey Kivi in the same session, which is the product.
- **COST:** Both paths live in one process, so the structural separation is enforced by code discipline and schema access rather than by process isolation. `P§AppC` claim 7 is therefore a test, not a deployment fact (`Q551`, `Q202`).
- **CONFIDENCE:** high

---

### Q381 — Should a user rejection delete evidence or prevent re-derivation?

- **DECISION:** Prevent re-derivation. Never delete evidence — the source transcripts stay (`Q28`), and even `Forget` purges the memory rather than its sources (`Q336`).
- **BECAUSE: POSITION.** `P§9` verbatim.
- **REJECTED:** Deletion as a storage operation with no suppression model — the surveyed answer, and the inventory's note that "no general suppression/tombstone model is visible" applies to nearly every source.
- **COST:** As `Q49` — and the honest discomfort that rejecting a belief leaves both the evidence and a record of the rejection (**Section B, conflict B5**).
- **CONFIDENCE:** high

---

### Q385 — Should low-quality agent experience be retained and clustered?

- **DECISION:** Not applicable — no agent experience is retained (`Q634`). And no quality score exists to filter on (`Q704`).
- **BECAUSE: POSITION.** `P§4`'s tiers.
- **REJECTED:** Skipping cases below a quality threshold. Wins in a case-based agent.
- **COST:** None here.
- **CONFIDENCE:** high

---

### Q389 — Should unprocessed recent messages be searchable?

- **DECISION:** Yes, and they must be clearly labelled as unprocessed. A transcript that has arrived but not yet been extracted is searchable through the raw-transcript fallback (`Q211`), and the trace says the memory layer has not seen it yet. This is the mitigation for the `Q62` freshness window.
- **BECAUSE: POSITION.** `P§8`: Kivi should say what it does not have and show what it looked for. "I have the dictation but haven't processed it yet" is a far better answer than silence, and it is honest about a real system state.
- **REJECTED:** Returning unprocessed messages without labelling, scoped only by session because buffer rows lack owner attribution (the surveyed answer). The unlabelled part is the problem: a raw hit presented as a memory hides that extraction has not run.
- **COST:** Another state the trace must render (`Q631`), and a user-visible admission that Kivi has a processing lag.
- **CONFIDENCE:** high

---

### Q411 — When mappings must express correspondence, should their language favor tractable relational rules or richer transformations?

- **DECISION:** Out of scope as posed. The analogous decision — the corpus **import adapter** (`Q420`) — favours a simple, declarative, documented field mapping over a rich transformation language. A reviewer must be able to read the mapping and know what it does.
- **BECAUSE: ENGINEERING (E2).** The brief says the reviewing agent "will not infer missing setup."
- **REJECTED:** A rich transformation DSL. It wins on corpus flexibility. It makes the import contract something a reviewer has to learn.
- **COST:** A corpus whose shape needs real transformation requires a code change, not a config change (`Q667`).
- **CONFIDENCE:** high

---

### Q415 — When the source language exceeds what the verification target can express, should the supported surface shrink or the reasoning machinery expand?

- **DECISION:** Shrink the supported surface. Where Kivi cannot support something honestly — multi-hop reasoning (`Q752`), narrative questions (`Q570`), procedural memory (`Q235`) — it abstains and says so rather than approximating. The supported surface is narrow and stated.
- **BECAUSE: POSITION.** `P§8`'s abstention discipline is exactly this principle applied to answers, and `E5`/`P§AppB`'s narrow tool set applies it to capability.
- **REJECTED:** Expanding machinery to cover more. It wins on capability. The brief agrees with the position: "narrow enough to finish and complete enough to interrogate."
- **COST:** A visibly limited product. Reviewers will find questions it cannot answer, and the defence is that it says so rather than guessing.
- **CONFIDENCE:** high

---

### Q423 — When full proof and broad language coverage cannot both be obtained, which kind of evidence should the checker produce?

- **DECISION:** Counterexamples and sampled inspection, not proofs (`Q410`, `Q429`). The evaluation demonstrates specific claims on specific cases and reports estimated false-negative rates; it proves nothing universally.
- **BECAUSE: ENGINEERING**, with **POSITION** on honesty — `P§AppC` asks for claims "provable from the evaluation output," which for an LLM pipeline means demonstrated, not proved, and the README must not overstate it.
- **REJECTED:** Claiming proof. Impossible here and dishonest to imply.
- **COST:** As `Q410` — all quality claims are empirical and sampled.
- **CONFIDENCE:** high

---

### Q439 — What happens when extraction or consolidation fails?

- **DECISION:** Keep good partial outputs, log the failure, retry with backoff, then quarantine visibly (`Q108`, `Q34`). Never fail the whole batch, never silently skip, never dead-letter without surfacing it.
- **BECAUSE: ENGINEERING (E4).**
- **REJECTED:** Silently skipping. It is the common accident (`Q81`) and produces holes in memory that look like forgetting.
- **COST:** Quarantine is a state the memory surface must explain without a developer console (`Q108`).
- **CONFIDENCE:** high

---

### Q445 — When storage grows, what should be discarded, summarized, or retained at full fidelity?

- **DECISION:** Everything retained at full fidelity; nothing discarded; nothing summarised (`Q54`, `Q154`). Raw records preserved permanently.
- **BECAUSE: POSITION.** `P§9` (raw provenance, user-only removal) and `Q154` (no summaries).
- **REJECTED:** Filter/dedupe/summarize/expire/consolidate with raw preserved externally. Note the surveyed reasoning for preserving raw — "because repeated compression drifts" — is an independent argument for `Q28`, arrived at from an engineering direction rather than a trust one. Two routes, same answer.
- **COST:** As `Q321`/`Q179` — no scale story.
- **CONFIDENCE:** high

---

### Q451 — When an agent has multiple memory types, who should control store, retrieve, update, summarize, and discard operations?

- **DECISION:** Deterministic code controls all five, with models used only as proposers and judges inside stages code owns (`Q533`, `Q247`). Never learned control.
- **BECAUSE: POSITION.** `P§2`'s enforcement principle.
- **REJECTED:** Heuristic/prompted control initially, learned control when workload evidence justifies it. It is a sensible staged recommendation and the first half matches this decision. The second half — learned control — is declined permanently here, not deferred, because its "cost and opacity" (the source's own words) are exactly what `P§8`'s inspection contract forbids.
- **COST:** As `Q247`/`Q457` — no adaptation.
- **CONFIDENCE:** high

---

### Q474 — When evidence is absent or ambiguous, should the agent answer, abstain, or ask?

- **DECISION:** Abstain, with near misses; ask within budget (`Q135`).
- **BECAUSE: POSITION.** `P§8`.
- **REJECTED:** Forcing a choice within a closed label set, with abstention not an available action (the surveyed answer, and the standard benchmark construction). It wins on measurability. It is worth noting how deeply this is baked into the field's evaluation practice: abstention is *not an action* in most benchmarks, which is why `P§AppC` claim 5 has to be demonstrated bespoke (`Q591`).
- **COST:** As `Q591` — incomparable to published results.
- **CONFIDENCE:** high

---

### Q482 — When extraction is uncertain, should one prompt make all structural decisions at once or should extraction be decomposed into constrained stages?

- **DECISION:** Decomposed, but only into two: **one extraction call** making the interpretive decisions jointly (`Q723`), then **separate code-owned stages** for exclusion checking, entity resolution, sameness judgement, and contradiction detection. Interpretation is joint; enforcement is staged.
- **BECAUSE: POSITION.** `P§2` forces the exclusion check to be a separate stage; `Q723`'s reasoning keeps coreference and time together because they are mutually constraining.
- **REJECTED:** A single prompt making every structural decision including exclusion. It wins on cost and coherence. It puts the product's hard promise inside a prompt that is also doing four other jobs — the highest-risk possible placement.
- **COST:** As `Q701` — more calls; and the joint extraction call's failures are hard to attribute to a sub-decision (`Q723`).
- **CONFIDENCE:** high

---

### Q494 — When an agent fails, should improvement change model parameters or change the context supplied to another attempt?

- **DECISION:** Neither. There is no second attempt (`Q508`) and no parameter change (`Q458`). Improvement comes only from the user correcting memory or stating something new.
- **BECAUSE: POSITION.** `P§8` (no retry-guessing) and `P§4` (user-sourced memory only).
- **REJECTED:** Turning feedback into natural-language guidance in episodic memory. It wins for self-improving agents; it is `Q707`'s rejected reflection.
- **COST:** As `Q12`.
- **CONFIDENCE:** high

---

### Q514 — What evidence should establish that multi-agent reflection, rather than extra computation, causes the improvement?

- **DECISION:** Out of scope (no multi-agent reflection). The transferable discipline: **any claim that a mechanism causes an improvement must be tested against an equal-cost control**. Where this system claims that typed tiered memory improves over a simpler baseline, the baseline must get comparable budget — otherwise the claim is about spending, not design.
- **BECAUSE: ENGINEERING (E4)**, and reinforced by `Q692`'s observation that a structured-memory system needed a very large token budget to match naive context-stuffing. That is the exact confound, and it is directly relevant here.
- **REJECTED:** Reporting improvement without an equal-token or equal-call control — which the inventory notes this source does not report. It is the most common methodological gap in the surveyed work.
- **COST:** Equal-budget controls are more evaluation work, and they may show the design's advantage is smaller than claimed. That is the point.
- **CONFIDENCE:** high

---

### Q553 — Local-first storage or remote service?

- **DECISION:** Local embedded, exclusively, as the declared primary review method (`Q90`).
- **BECAUSE: ENGINEERING (E2).**
- **REJECTED:** Local default with a remote backend available. It wins on flexibility; it adds a configuration path the review never exercises but the reviewer must still read past (`Q440`).
- **COST:** As `Q90` — single-device, no backup.
- **CONFIDENCE:** high

---

### Q565 — Do memories decay, archive, or remain until deleted?

- **DECISION:** By tier — observations decay out of surfacing, hypotheses expire and are dropped, stated memories remain until the user acts (`Q666`, `Q602`). No TTLs on arbitrary classes, no archival by threshold, no reactivation.
- **BECAUSE: POSITION.** `P§9`.
- **REJECTED:** TTLs with configurable half-lives, threshold archival, and field-level reactivation. It is a rich and well-considered lifecycle, and it is keyed to layers and gain thresholds rather than to epistemic tier — which is precisely the axis `P§4` says should govern. Same machinery, wrong axis.
- **COST:** As `Q24` — unset windows.
- **CONFIDENCE:** medium

---

### Q581 — What should happen to memories as evidence ages, the person changes, or an inference remains unconfirmed?

- **DECISION:** Three different answers for the three clauses, and the question's own structure is the position's: evidence ages → observations decay; the person changes → supersession, plus the demote-and-suppress action; an inference remains unconfirmed → it expires (`Q38`, `Q49`).
- **BECAUSE: POSITION.** `P§1` principle 3: "people change. The friend who was terrified of speaking in public three years ago now runs workshops. A memory that can't be revised stops being memory and becomes a cage." `P§9` supplies all three mechanisms.
- **REJECTED:** Favouring the most recent contradictory memory with no decay, expiry, demotion, or consolidation lifecycle. It wins on simplicity and is the most common answer in the inventory.
- **COST:** As `Q24`.
- **CONFIDENCE:** medium

---

### Q584 — What storage/index substrate should carry the memory, and what scale or tenancy properties must it support?

- **DECISION:** One embedded relational database with lexical FTS and in-process brute-force vector search; single-tenant; documented deletion semantics; scale stated honestly as ~500 transcripts and not claimed beyond (`Q447`, `Q321`).
- **BECAUSE: ENGINEERING (E2, E1).**
- **REJECTED:** Local FAISS for benchmarking with production properties left underspecified. The inventory's phrasing — "production persistence, multi-tenancy, deletion guarantees, and scale limits are underspecified" — names four things the brief explicitly asks about, and the honest answer for three of them is "not supported, deliberately."
- **COST:** As `Q321` — no scale story.
- **CONFIDENCE:** high

---

### Q598 — What property of a memory should determine its storage tier and protection level?

- **DECISION:** There are no storage tiers or protection levels. All memories live in one store with one protection level. What varies by **tier** is disclosure and lifecycle, not storage or protection (`Q276`).
- **BECAUSE: POSITION.** `P§4`'s tier is epistemic, not custodial. Introducing a protection level keyed to identity-significance would require Kivi to judge which memories are central to who the user is — a characterisation `P§2` forbids.
- **REJECTED:** Tiering by semantic role in identity, with high tiers holding identity and low tiers operational records. It is a coherent design for an agent with a self. Applied to a user's memories it becomes a ranking of how important each fact is to who they are, which is the profile in a storage schema.
- **COST:** No differential protection for genuinely more sensitive memories — though `Q851` means the most sensitive ones are never stored (`Q335`).
- **CONFIDENCE:** high

---

### Q599 — When two proposed storage layers have similar behavior, what should justify keeping them separate?

- **DECISION:** Only two things justify a separate store here: **immutability** (transcripts must be immutable while memories are not) and **disposability** (the vector index is rebuildable while the record is not). Nothing else. Three stores, three justifications (`Q536`).
- **BECAUSE: ENGINEERING (E5)**, with the immutability requirement from **POSITION** (`P§9`).
- **REJECTED:** Separating by semantic type, stability, and governance. It is a good general rule, and applied here it would produce a layer per tier — which `Q202` rejects because promotion must be a field update, not a migration between stores.
- **COST:** As `Q202`/`Q551` — the structural claim is enforced at the query layer.
- **CONFIDENCE:** high

---

### Q600 — When a stored claim changes, should the old representation be overwritten, deleted, archived, or preserved as an event?

- **DECISION:** Preserved as history with a status and a link (`Q88`, `Q115`) — which is functionally append-only for everything except `Forget`, the one destructive operation.
- **BECAUSE: POSITION.** `P§9`'s audit requirement, with `Forget` as the deliberate exception.
- **REJECTED:** Fully append-only with complete history and no deletion at all (the surveyed answer). It is the cleaner invariant and it is what I would choose absent `P§9`'s `Forget`. It wins if `Forget` could mean "hide" — but a user who asks to forget something and finds it retained has been misled (`Q603`).
- **COST:** One destructive operation breaks an otherwise clean append-only invariant, and it must purge history without breaking referential integrity — the fiddliest operation in the schema.
- **CONFIDENCE:** high

---

### Q617 — What unit should users manipulate when controlling an agent's memory?

- **DECISION:** The **memory** — one typed belief, shown as a sentence with its tier, evidence count, last-seen date, and a tap to its sources. Not a conversation fragment, not a context object, not a raw turn.
- **BECAUSE: POSITION.** `P§9`: "Actions per entry: Confirm (promote), Correct (edit), That's not me anymore (demote + suppress), Forget (remove + suppress)." "Per entry" fixes the unit, and the entry is a belief.
- **REJECTED:** A "memory object" that is an interactive piece of conversational history, movable, editable, and summarisable. It is a genuinely good interface and gives the user more direct control. It manipulates *history*, not *belief* — and `P§9`'s promise is about what Kivi thinks, not about what is in the transcript.
- **COST:** The user cannot manipulate transcripts at all (`Q336`) — no "delete this dictation," no "ignore this conversation."
- **CONFIDENCE:** high

---

### Q639 — At what stage should retrieved memory influence behavior: before planning as prompt context, during action selection, through a separate policy, or only after an initial attempt?

- **DECISION:** Before, as permission-filtered prompt context available to both tool selection and generation (`Q255`). Never through a separate policy, never after an attempt.
- **BECAUSE: POSITION.** `P§6`'s dial filters what the model may see, which requires filtering to happen before the model runs. And `P§3`'s value claim — removing re-explanation — requires memory to shape the first attempt, not correct a second one.
- **REJECTED:** Influence only after an initial attempt. Wins in retry architectures (`Q508`).
- **COST:** A memory whose relevance only becomes clear mid-task cannot enter (`Q835`).
- **CONFIDENCE:** high

---

### Q658 — Keep both passages, replace old state, temporally close it, or ask for confirmation?

- **DECISION:** Replace current state with supersession and lineage; temporally close it **only when the transcript states a validity end** (`Q848`); ask only for stated-level conflicts within budget (`Q684`). Never let contradictory passages coexist as current facts.
- **BECAUSE: POSITION.** `P§9`.
- **REJECTED:** Ordinary coexistence where search can retrieve contradictory passages (the surveyed answer). It wins on fidelity — both were said, both are retrievable. It guarantees Kivi will sometimes state both, which is the most corrosive possible failure for a memory product.
- **COST:** As `Q13` — sequence facts flatten into corrections.
- **CONFIDENCE:** high

---

### Q686 — What should determine forgetting: age, low predicted utility, interference, user intent, legal/sensitivity rules, or storage cost?

- **DECISION:** Two only: **user intent** (Forget/demote) and **age without re-observation** (decay/expiry, observations and hypotheses only). Not predicted utility (`Q100`), not interference, not storage cost (`Q179`). Sensitivity rules act at the write path, so there is nothing to forget (`Q312`).
- **BECAUSE: POSITION.** `P§9` names exactly these two causes and no others.
- **REJECTED:** TTL expiry plus exponential importance decay plus selective forgetting of high-interference low-value memories. It is the most complete forgetting design in the inventory and would keep the store healthy at scale. Every component beyond the two above requires Kivi to judge the value of facts about the user, which `Q681` and `Q721` reject on the same grounds.
- **COST:** As `Q54`/`Q179`/`Q321` — no scale story.
- **CONFIDENCE:** high

---

### Q687 — Before deleting a memory, should the system reduce fidelity, retain a tombstone, archive the source, or keep it intact until removal?

- **DECISION:** Keep it intact until removal. No graceful degradation to gists, no fidelity reduction. What survives removal is a **suppression record** — which is a tombstone in function, though a narrow one: it records enough to block re-derivation and nothing more (`Q622`).
- **BECAUSE: POSITION.** `P§9`'s lifecycle has no degradation step; a memory either has standing or does not, and a gist would be a model-authored artefact replacing a correctable belief (`Q311`).
- **REJECTED:** Six-step graceful degradation from full record to summary to tombstone, triggered by age and score. It is a thoughtful design and its trigger — "age plus score, not storage economics" — is the right instinct. It produces intermediate representations with no tier and no source.
- **COST:** As `Q622` — the suppression record is the uncomfortable residue of `Forget` (**Section B, conflict B5**).
- **CONFIDENCE:** high

---

### Q689 — Should long-term semantic memory be permanent, decay, or remain revisable with history?

- **DECISION:** Revisable with history, plus tier-based decay (`Q600`, `Q38`). Not permanent, not purely decaying.
- **BECAUSE: POSITION.** `P§1` principle 3 (revisability) and `P§9` (history + decay).
- **REJECTED:** A permanent semantic graph with reconsolidation on retrieval, leaving the interaction of permanence, deletion, and versioning underspecified. The underspecification is the tell: permanence and reconsolidation are hard to reconcile, and `Q685` rejects reconsolidation separately.
- **COST:** As `Q88` — status filtering everywhere.
- **CONFIDENCE:** high

---

### Q697 — Should lifecycle mechanisms be deterministic, model-mediated, or jointly learned?

- **DECISION:** Deterministic, entirely. Decay, expiry, promotion eligibility, suppression, and status transitions are all code operating on stored fields and the clock. Models are used only for extraction, exclusion classification, sameness and contradiction judgement, tool choice, and wording (`Q794`). Never learned.
- **BECAUSE: POSITION.** `Q247`'s rule derived from `P§2`: product promises are enforced in code. Every lifecycle mechanism is a promise — decay is a promise that old behaviour will not be presented as who you are; suppression is a promise that corrections stick.
- **REJECTED:** Deterministic lifecycle with model-generated gists — which is nearly this answer, minus the gists (`Q687`). Also rejected: jointly learned lifecycle (`Q451`).
- **COST:** Lifecycle thresholds are hand-set and unset (**Section A**), with no mechanism to learn them.
- **CONFIDENCE:** high

---

### Q699 — When an agent should improve from trial-and-error, what part of the system should change?

- **DECISION:** Nothing. There is no trial-and-error improvement (`Q494`, `Q131`). What changes is memory content, from user evidence and user actions only.
- **BECAUSE: POSITION.** `P§4`'s tiers and `P§9`'s user authority.
- **REJECTED:** Fixed weights with verbal reflections added to context. Wins for self-improving agents; is `Q707`'s rejected reflection.
- **COST:** As `Q12`.
- **CONFIDENCE:** high

---

### Q728 — When related observations accumulate, should consolidation happen at write time, query time, or asynchronously?

- **DECISION:** Write time, inside the extraction transaction — merge, evidence increment, contradiction detection, and observation formation all happen before commit (`Q91`, `Q341`). Never at query time, never as a separate asynchronous consolidation.
- **BECAUSE: POSITION.** `P§9`'s supersession must be true as soon as the new fact exists (`Q161`); `Q08`'s idempotence requires the result of processing a transcript to be fully determined by that transcript plus prior state.
- **REJECTED:** Query-time consolidation. It wins on write cost and keeps the store simple. It would make what Kivi believes depend on what it was asked, which is unaccountable.
- **COST:** The write path carries similarity search, LLM sameness judgement, and contradiction detection per candidate — the dominant ingestion cost after extraction (`Q540`).
- **CONFIDENCE:** high

---

### Q730 — After synthesis, should original atoms remain independently available and attributable?

- **DECISION:** There is no synthesis (`Q311`). Merged memories keep every source id, so every contributing transcript remains attributable, and superseded versions remain in history (`Q188`).
- **BECAUSE: POSITION.** `P§9`'s provenance requirement.
- **REJECTED:** Allowing both abstracts and detailed units with lineage underspecified. The underspecified lineage is the failure: an abstract whose relation to its atoms is undefined cannot be corrected or attributed.
- **COST:** As `Q311` — the surviving wording may be worse than a synthesis.
- **CONFIDENCE:** high

---

### Q738 — How should a user correct, demote, delete, or confirm a memory?

- **DECISION:** Four named actions on the memory surface, phrased in human terms — **Confirm**, **Correct**, **That's not me anymore**, **Forget** — plus inline correction during a request. Each writes a recorded event; demote and forget also write suppressions (`Q22`, `Q269`).
- **BECAUSE: POSITION.** `P§9`, verbatim, including the insistence that "the actions are phrased in human terms rather than database terms."
- **REJECTED:** No user memory-management operation (the surveyed answer, and the majority state). It wins on build cost and is why this is a differentiator.
- **COST:** As `Q611` — cheap, ceremony-free actions with no confirmation step make an accidental `Forget` plausible and unrecoverable (`Q10`, **Section A**).
- **CONFIDENCE:** high

---

### Q739 — How should deleted or rejected beliefs be prevented from reappearing after reprocessing?

- **DECISION:** Suppression records consulted by the extractor before candidates are written, replayed before any full reprocess, surviving model upgrades (`Q46`, `Q49`). `P§AppC` claim 6 is the test.
- **BECAUSE: POSITION.** `P§9`.
- **REJECTED:** Underspecified (the surveyed answer, and the honest description of nearly every system).
- **COST:** As `Q506` — over-application; scope undetermined (**Section A**).
- **CONFIDENCE:** high

---

### Q740 — How should memory change as facts, preferences, and patterns age?

- **DECISION:** By tier, not by type — the question's framing (facts / preferences / patterns) is a type framing, and the position's answer is that aging is governed by tier (`Q325`, `Q95`).
- **BECAUSE: POSITION.** `P§4`'s independence of the two axes.
- **REJECTED:** Newer conflicting units winning at answer time with no lifecycle. See `Q589`.
- **COST:** As `Q24`.
- **CONFIDENCE:** high

---

### Q759 — Where should persistent memory live, and what threat model should storage satisfy?

- **DECISION:** Local embedded storage (`Q90`). The threat model is deliberately minimal — single user, local machine, no network exposure by default (`Q107`) — and the primary protection is non-retention rather than storage security (`Q335`). **At-rest encryption of the transcript store is the one addition worth making** and the position does not mention it.
- **BECAUSE: ENGINEERING (E1, E2)**, with the non-retention primacy from **POSITION** (`P§2`, `P§5`).
- **REJECTED:** On-device or encrypted-enclave storage as an aspiration with the evaluated implementation underspecified. The aspiration is right and the underspecification is the problem — "should be encrypted" in a paper is `P§2`'s "line in a prompt hoping for good behaviour" applied to storage.
- **COST:** As `Q335` — the transcript store holds what the memory store refuses and is protected only by filesystem permissions.
- **CONFIDENCE:** medium

---

### Q765 — When information is filtered out, should the system delete it silently, preserve it as an episode, log the rejection, or expose the reason?

- **DECISION:** Log the rejection **and expose the reason** — per item, not just in aggregate, as a non-content reason-coded row surfaced in the transcript's inspection view (`Q199`, `Q852`).
- **BECAUSE: POSITION.** `P§2`: "Dropped candidates are logged with the reason. The extraction log for any transcript can show: *3 candidates extracted, 1 dropped — excluded category: emotional state.*" That is per item, with a reason, user-visible.
- **REJECTED:** Reporting an aggregate discard rate with per-item reason logging and user exposure underspecified (the surveyed answer). It wins on privacy (`Q199`) and on interface simplicity. An aggregate rate proves a filter exists; it does not let a user see that *their* dictation about a colleague's health was dropped, which is `P§5`'s "read, not kept" moment.
- **COST:** As `Q199` — a reason-coded trail about sensitive categories (**Section B, conflict B3**).
- **CONFIDENCE:** high

---

### Q775 — What happens when the memory system is wrong: automatic rewrite, silent persistence, user correction, rollback, or deletion?

- **DECISION:** User correction, always (`Q269`). Never automatic rewrite (`Q640`), never silent persistence (`Q855` surfaces unresolved conflicts), rollback only as a full documented reset (`Q406`), deletion only as user-initiated `Forget`.
- **BECAUSE: POSITION.** `P§9`.
- **REJECTED:** No correction, edit, removal, appeal, or rollback surface, with rewriting on retrieval as future speculation. The inventory names five absences at once; that is the field baseline this position departs from.
- **COST:** As `Q406` — no partial rollback of a bad extraction run without losing user corrections.
- **CONFIDENCE:** high

---

### Q780 — What should decide whether an extracted candidate survives consolidation?

- **DECISION:** Four code-enforced gates (`Q307`): category exclusion, third-party/work-level test, typability, completeness. Not a prompt-defined retention rule.
- **BECAUSE: POSITION.** `P§2`: "enforced by a check that runs on candidate memories, not by a line in a prompt."
- **REJECTED:** A prompt rule retaining "users' own personal experiences and contextual details," with discard quantity inferred rather than logged. Two failures in one: the rule is a prompt, and "personal experiences" is the category `P§2` excludes.
- **COST:** As `Q307`.
- **CONFIDENCE:** high

---

### Q782 — What should determine which memories belong together over the long term?

- **DECISION:** Shared **entities** and explicit typed relations (`Q362`). Not embedding clusters, not narrative threads (`Q766`, `Q767`).
- **BECAUSE: POSITION.** `P§4`'s entity type is the grouping mechanism the ontology provides; discovered clusters have no tier and present the user with an organisation of themselves they did not choose.
- **REJECTED:** PCA → UMAP → HDBSCAN into coarse topics then temporally ordered narrative threads. It is the strongest organisational design in the inventory and directly addresses the navigation gap (`Q784`, `Q399`). It wins if the memory surface proves unusable as tier-grouped lists — a plausible outcome this document has now flagged four times.
- **COST:** As `Q784` — navigation at scale is unsolved.
- **CONFIDENCE:** medium

---

### Q791 — How should users correct, delete, pin, demote, or suppress a memory, and how far should that change propagate?

- **DECISION:** Through the four actions plus pinning, propagating to: current retrieval immediately, the extractor's suppression list permanently, and any full reprocess (`Q506`, `Q46`).
- **BECAUSE: POSITION.** `P§9`.
- **REJECTED:** Memory rewriting as future work with no user-facing path. See `Q775`.
- **COST:** As `Q506`.
- **CONFIDENCE:** high

---

### Q792 — What should cause old memory to weaken, expire, or be forgotten?

- **DECISION:** Absence of re-observation within a window (observations weaken; hypotheses expire) and user action (forget). Nothing else (`Q686`).
- **BECAUSE: POSITION.** `P§9`.
- **REJECTED:** Persistent threads with access-based decay and regulated forgetting as future work with no rate or policy. The "no rate or policy" admission is the recurring pattern (`Q24`, `Q642`, `Q773`, `Q601`) — the field consistently defers the parameters. `P§AppB` at least names them as deferred rather than implying they exist.
- **COST:** As `Q24` — and note this position is in the same position as the field on the parameter values; the difference is that it says so.
- **CONFIDENCE:** medium

---

### Q793 — When new evidence arrives, should organization be rebuilt globally, updated incrementally, or remain fixed?

- **DECISION:** Fixed. The organisation is the schema — type and tier — and it never changes. New evidence updates individual memories incrementally (`Q475`); nothing is globally rebuilt.
- **BECAUSE: POSITION.** `P§4`'s axes are fixed, and `P§9`'s per-entry identity requires memories to survive the arrival of new evidence rather than being regenerated (`Q475`).
- **REJECTED:** Self-evolving narrative threads rebuilt by batch clustering, with cadence and incremental mechanics underspecified. Global rebuilds destroy memory identity, which breaks every `P§9` action attached to a memory.
- **COST:** No reorganisation as understanding improves. If the initial ontology is wrong for a corpus, it stays wrong (`Q142`).
- **CONFIDENCE:** high

---

### Q804 — Is anything ever removed?

- **DECISION:** Yes, in exactly one case: user-initiated `Forget`, which purges the memory and its history while leaving a suppression and the source transcripts (`Q600`, `Q603`). Nothing else is ever removed.
- **BECAUSE: POSITION.** `P§9`'s `Forget` action. Everything else in `P§9` is demotion, supersession, or decay — none of which delete.
- **REJECTED:** No delete path at all, with INVALIDATE closing a validity interval and the row staying (the surveyed answer). It is the cleaner invariant (`Q600`) and it is what this system does for every case except one. The exception exists because `P§9` offers the user `Forget` and a `Forget` that retains is not one.
- **COST:** As `Q600` — one destructive operation in an otherwise append-only store.
- **CONFIDENCE:** high

---

### Q805 — Does consolidation respect prior state?

- **DECISION:** Yes, absolutely. Every operation is incremental and respects prior state, including user corrections, confirmations, suppressions, and pins. **Nothing ever fully recomputes from scratch** — because a full recompute would silently discard exactly the user-contributed state `P§9` protects.
- **BECAUSE: POSITION.** `P§9`: corrections must stick. A sleep-time full recompute would reorganise and re-summarise from the source material, which contains no record of the user's corrections.
- **REJECTED:** Full recompute from the mention set at consolidation (the surveyed answer, quoted in the inventory as "reorganize[s] all entity mentions… and re-summarise[s]"). It wins on coherence — a recomputed state is internally consistent, where an incrementally-built one drifts (`Q475`). This is the sharpest statement of that trade-off in the inventory, and this position takes the incremental side every time.
- **COST:** Incremental state can drift from what a fresh extraction would produce, and there is no reconciliation mechanism. Over a long life, the store accumulates the residue of old extractor versions (`Q673`, `Q406`).
- **CONFIDENCE:** high

---

### Q806 — Does old evidence lose standing over time?

- **DECISION:** Yes, for observations and hypotheses (`Q861`, `Q51`).
- **BECAUSE: POSITION.** `P§9`.
- **REJECTED:** No decay, with items aging only insofar as a query's time window excludes them. It wins on simplicity and honesty about unset parameters.
- **COST:** As `Q24`.
- **CONFIDENCE:** medium

---

### Q817 — When several observations are temporally continuous and semantically related, should they remain separate or be consolidated into a duration-level memory?

- **DECISION:** Remain separate. No durative memories, no topic summaries, no persona summaries (`Q818`, `Q819`).
- **BECAUSE: POSITION.** `P§4`'s three types contain no durative kind; `P§2` forbids the persona half.
- **REJECTED:** Consolidation into durative topic and persona summaries — marked load-bearing by its own source. The topic half is `Q570`'s gap; the persona half is `P§2`'s refusal. This is the single question where the inventory most directly tells us that the rejected option measurably helps.
- **COST:** As `Q818` — preference questions requiring aggregation answer poorly, and preferences are one of three memory types.
- **CONFIDENCE:** medium

---

### Q822 — Which work belongs on the interactive path and which can wait for offline maintenance?

- **DECISION:** **Interactive:** retrieval, disclosure filtering, tool selection, generation, trace recording, and user corrections. **Offline/async:** extraction, merge, contradiction detection, observation formation, embedding, and the decay sweep. Nothing that changes an answer waits; nothing that costs an LLM call blocks a response except the answer's own generation.
- **BECAUSE: ENGINEERING (E3)**, with **POSITION** placing corrections on the interactive path (`Q259`).
- **REJECTED:** Incremental graph updates inline plus periodic expensive summary refresh ("sleep time"). Its split is sensible and close to this one; the difference is that it puts summary refresh offline, and there are no summaries here (`Q154`).
- **COST:** As `Q62` — the freshness window between dictation and knowledge, mitigated only by `Q389`'s labelled unprocessed-transcript search.
- **CONFIDENCE:** high

---

### Q854 — Is an invalidated item deleted or retained?

- **DECISION:** Retained, with `status = superseded` and a pointer, preserving relationship history (`Q522`, `Q158`).
- **BECAUSE: POSITION.** `P§9`.
- **REJECTED:** Deletion. See `Q522`. Note this surveyed answer agrees with the position, for the functional reason that relationship history is needed — another case of two routes to one answer.
- **COST:** As `Q88`.
- **CONFIDENCE:** high

---

### Q862 — How does the aggregate layer stay current, and what is drift worth?

- **DECISION:** There is no aggregate layer (`Q850`, `Q399`). Nothing drifts because nothing aggregates.
- **BECAUSE: POSITION.** `P§2`'s refusal of the profile; `Q850`'s refusal of community summaries.
- **REJECTED:** Label propagation on insert with periodic full community refreshes. It wins for global-question answering over a large graph — the strongest technique available for "tell me about X" (`Q850`). Note it also requires periodic full refreshes, which `Q805` rejects independently.
- **COST:** As `Q850` — global and broad questions answer poorly.
- **CONFIDENCE:** high

---

## Stage: GENERATION

---

### Q04 — On missing data or low confidence, return an error/empty set, ask, abstain with trace, or guess?

- **DECISION:** **Abstain with trace** — name what was searched, name near misses, show the trace. Not an error, not an empty set, not a guess. Asking happens only within the confirmation budget and is not a substitute for abstaining.
- **BECAUSE: POSITION.** `P§8`, whole section: "Kivi says what it doesn't have, and shows what it looked for. Not 'I'm not sure' — that's a shrug. Something a person can act on." And: "The trace exists for abstentions too. An abstention is a result with reasons, and reasons are exactly what makes it credible."
- **REJECTED:** Letting the LLM synthesize anyway, which is what "no abstention path in the repo" amounts to and what the plurality of ten sources do. It wins on answer rate and benchmark score. It is the product's defining refusal.
- **COST:** As `Q228` — Kivi abstains where a hedge would have helped, and scores worse on any benchmark that does not reward abstention (`Q591`).
- **CONFIDENCE:** high

---

### Q45 — When available memory cannot support an answer, what behavior should count as success?

- **DECISION:** A well-formed abstention that (a) states Kivi does not have it, (b) names what was searched, (c) offers genuine near misses, and (d) carries a trace — counts as a **full pass**, indistinguishable in scoring from a correct answer. A fluent guess counts as a **severity-one failure** even if it happens to be right.
- **BECAUSE: POSITION.** `P§AppC` claim 5 makes abstention a demonstrable success. `P§8`: "A fluent invented answer is worse than no answer, because it's indistinguishable from a real one until it costs you something" — which means a correct guess is also a failure, since it was indistinguishable from a wrong one at the time.
- **REJECTED:** Counting abstention as correct only when the benchmark labels the question unanswerable. It wins on measurability. It cannot score the *quality* of an abstention, which is the part `P§8` cares about — "I don't have that" and `P§8`'s worked example are both abstentions and only one is good.
- **COST:** Abstention quality is graded partly by hand (`Q429`), so it is small-N and subjective.
- **CONFIDENCE:** high

---

### Q64 — When memory doesn't contain the answer, what should the system do?

- **DECISION:** Abstain with the search description and near misses (`Q04`).
- **BECAUSE: POSITION.** `P§8`.
- **REJECTED:** Answer anyway under a terse-answer mandate, with unanswerable questions removed from the evaluation; or reply with a best guess from core memory. The inventory's two surveyed answers here are worth reading together — one system removed unanswerable questions from its evaluation, the other instructs the model to guess. Between them they describe how the field arrives at high scores on memory benchmarks.
- **COST:** As `Q04`.
- **CONFIDENCE:** high

---

### Q67 — When the system lacks adequate evidence, should it guess, abstain, retrieve again, or expose nearby evidence?

- **DECISION:** Abstain and expose nearby evidence, in one response. One bounded broadening before abstaining (`Q675`); no iterative re-retrieval (`Q542`).
- **BECAUSE: POSITION.** `P§8`'s worked example.
- **REJECTED:** Iterative re-retrieval until something is found. It wins on recall. Unbounded broadening converts abstention into a weak answer (`Q675`).
- **COST:** As `Q542` — no iterative deepening; the broadening bound is unset (**Section A**).
- **CONFIDENCE:** high

---

### Q69 — When evidence is insufficient, should the system abstain, answer from partial evidence, ask a clarification, or present nearby results?

- **DECISION:** Abstain **and** present nearby results. Never answer from partial evidence. Clarification is not a routine behaviour — Kivi says what it does not have rather than asking the user to refine their question, because the user should not have to guess what Kivi knows.
- **BECAUSE: POSITION.** `P§8`'s example answers a vague question with specifics about what exists, which is more useful than "could you be more specific?" It also "teaches the user what Kivi's memory actually contains, which is how they learn to trust it."
- **REJECTED:** A fixed "I do not have enough information in my memory." It is honest and it is the shrug `P§8` explicitly rejects: "Not 'I'm not sure' — that's a shrug. Something a person can act on."
- **COST:** Abstentions are expensive to produce well — they require a description of the search and a selection of near misses, which is extra generation on every failed query.
- **CONFIDENCE:** high

---

### Q106 — Does the caller get memories or an answer?

- **DECISION:** Both, structurally separated: an answer, plus a machine-readable list of the memory ids that produced it, **validated by code** — a citation that does not resolve to a retrieved memory is a generation defect, not a formatting quirk.
- **BECAUSE: POSITION.** `P§8`: the trace shows "what was used in the answer, and the source transcript behind each memory, one tap away." One tap requires a resolvable id, not a bracketed label.
- **REJECTED:** Prompt-requested `[Memory N]` citations — the surveyed answer, and the inventory's note is the whole argument: "therefore not guaranteed, not validated, not resolvable to a row by any code." A citation format the code does not check is decoration.
- **COST:** Citation validation can fail on well-formed answers, forcing a retry or a degraded response. And validation only catches *unresolvable* citations, not *wrong* ones — attribution correctness still needs sampled grading (`Q592`).
- **CONFIDENCE:** high

---

### Q256 — When the first reconstructed context seems insufficient, who should decide what additional evidence is fetched?

- **DECISION:** Nobody — there is no second fetch (`Q542`). Insufficient context produces an abstention, not a follow-up retrieval.
- **BECAUSE: POSITION.** `P§8`'s trace must state what was searched; iterative model-driven fetching makes the searched set a model artefact (`Q403`).
- **REJECTED:** The reasoning agent returning identifiers of missing turns and a second context being built. It wins on recall and is well-bounded — it is the most defensible version of iterative retrieval, because the model names specific missing items rather than searching freely. The condition for accepting it is `Q542`'s: each fetch appears in the trace as a step.
- **COST:** As `Q403`/`Q542` — a hard k with no deepening.
- **CONFIDENCE:** medium

---

### Q260 — What should become the durable record of a turn after a response is produced?

- **DECISION:** Two separate things. The user's turn becomes a **transcript**, queued for extraction. The interaction becomes a **trace** — retrieved, withheld, used, tool calls, answer — which is an inspection artefact, not memory. Kivi's response is in the trace and never in memory (`Q550`, `Q198`).
- **BECAUSE: POSITION.** `P§8` (the trace) and `P§4` (tiers exclude Kivi's output).
- **REJECTED:** A turn record comprising user input, model response, and a model-generated summary. The summary is `Q154`'s refusal; the model response entering the durable record is `Q198`'s.
- **COST:** Two durable artefacts per turn with different retention rules, both growing (`Q263`).
- **CONFIDENCE:** high

---

### Q271 — Which content should be categorically barred from durable memory even when it helps the current answer?

- **DECISION:** The `P§2` exclusion list and all third-party personal content — barred **precisely because** they help the current answer. That is the case the rule exists for: `P§5`'s worked example uses Priya's mother's illness to write a better reply and refuses to keep it.
- **BECAUSE: POSITION.** `P§5`: "Kivi writes the reply. Uses everything. Kivi retains: … Kivi drops: everything about Priya's mother."
- **REJECTED:** No content-level exclusion policy, with sensitive data absent from the benchmark and safeguards deferred (the surveyed answer). The inventory's phrasing is instructive — the benchmark contains no personal data, so the absence of a policy costs nothing *in evaluation*. That is how this gap survives: it is invisible to the metrics.
- **COST:** As `Q851`/`Q442`.
- **CONFIDENCE:** high

---

### Q288 — When memory and tools can both answer, which should be preferred and when should the system re-check the source?

- **DECISION:** Memory first for anything memory can answer; tools only for acting, not for knowing. Kivi's three tools (draft, schedule, recall) do not fetch external facts, so there is no external source to re-check and no staleness question (`Q237`).
- **BECAUSE: ENGINEERING (E5)**, following from the narrow tool set (`Q246`) and the closed environment (`Q237`).
- **REJECTED:** Memory-first with tools when memory is insufficient, revalidation underspecified. It wins for an agent with live sources. The underspecified revalidation is the real gap in that design, and this system avoids it by having no live sources — which is a simplification, not a solution.
- **COST:** Kivi cannot check anything against the world. Every answer is bounded by the corpus.
- **CONFIDENCE:** high

---

### Q289 — Should the system abstain when evidence is absent, infer a plausible answer, or return the nearest related memory?

- **DECISION:** Abstain, and *name* the nearest related memory without answering from it (`Q329`).
- **BECAUSE: POSITION.** `P§8`'s example names near misses and offers them: "Want me to show that one?"
- **REJECTED:** Returning the nearest related memory as the answer. It wins on apparent helpfulness and is nearly indistinguishable from abstention-with-near-misses in the interface — the difference is whether Kivi asserts it. That difference is the whole of `P§8`.
- **COST:** As `Q04`.
- **CONFIDENCE:** high

---

### Q298 — F4 — Transform intermediate responses into shared key–value memory (D05–D10)

- **DECISION:** Not adopted. Intermediate responses are not memory (`Q198`), there is no shared memory (`Q273`), and there are no key–value fragments (`Q280`).
- **BECAUSE: POSITION.** `P§4` and `P§1` principle 2.
- **REJECTED:** The transformation. The inventory's note that it affects "both efficiency and privacy" and that "failed transformation changes confidentiality" is precisely the objection: a privacy guarantee that depends on an LLM transformation succeeding is `P§2`'s "prompt hoping for good behaviour."
- **COST:** As `Q273` — no reuse, no efficiency gains from shared knowledge.
- **CONFIDENCE:** high

---

### Q299 — F6 — Memory-first, tools-if-insufficient behavior (D20)

- **DECISION:** Adopted in a narrow form (`Q288`): memory answers knowing, tools do acting, and no reuse threshold exists because there is no external source to fall back to.
- **BECAUSE: ENGINEERING (E5).**
- **REJECTED:** A tunable reuse threshold. The inventory's note — "resource utilization is directly sensitive to the reuse threshold, even at identical answer quality" — is a warning that headline efficiency results in this space are often threshold artefacts. Worth remembering when reporting this system's own cost figures.
- **COST:** None here.
- **CONFIDENCE:** high

---

### Q317 — Should memory construction happen before response generation, after it, or asynchronously—and should newly inferred memory affect the same response?

- **DECISION:** Asynchronously, **after**, and newly extracted memory does **not** affect the response that produced it. The one exception is an explicit user correction, which is synchronous and affects the current response (`Q259`).
- **BECAUSE: ENGINEERING (E3)** for the async default; **POSITION** for the correction exception (`P§8`'s inline correction) and for the general prohibition — `P§2`'s worry about plausible inference means a memory created mid-turn and immediately used would be a belief formed and acted on within one breath, with no opportunity for the user to see it.
- **REJECTED:** Blend/refine before responding, injecting newly created insights into the same turn's generator (the surveyed answer). It wins on coherence and immediacy — the system feels like it is listening. It creates and acts on a belief in one step, which is the mechanism `P§2` warns about most directly.
- **COST:** As `Q62` — the freshness window, and a demo in which Kivi does not immediately know what was just said.
- **CONFIDENCE:** high

---

### Q366 — What contextual inputs should the response generator receive?

- **DECISION:** The request, the permission-filtered retrieved memories with tiers and sources, the entity list, the bounded turn history, application context in a separately labelled section, and the current date. **Not** relationship information about participants (`Q128`), not linked-memory expansions (`Q749`), not a persona.
- **BECAUSE: POSITION.** `P§6` (filtered memories), `P§5` (labelled application context), `P§2` (no relationship or persona information). The date is `ENGINEERING` from `Q693`.
- **REJECTED:** Including speakers' identities, jobs, and relationships. Jobs and roles are permitted (`Q55`); **relationships** are a `P§2` excluded category, and their inclusion here is a good example of how naturally that information enters a generator prompt when nobody has drawn the line.
- **COST:** Kivi cannot modulate register by relationship (`Q128`).
- **CONFIDENCE:** high

---

### Q371 — Which generated samples should be discarded before they become training evidence?

- **DECISION:** Nothing is training evidence (`Q131`). For the **corpus**: generated transcripts are filtered for format validity, cast consistency with `P§AppA`, and coverage of the seven `P§AppC` claims — and the generation procedure is committed so a reviewer can see what was filtered and why.
- **BECAUSE: POSITION.** `P§AppA` fixes the cast "so the corpus, the evaluation, and the demo all use one consistent world," and lists the required varieties.
- **REJECTED:** Heavy filtering for topic diversity and quality without publishing the procedure. It wins on corpus quality; unpublished filtering is how a corpus quietly becomes one the system is good at (`Q370`).
- **COST:** As `Q370` — a self-generated corpus proves little; the reviewer's corpus is the real test.
- **CONFIDENCE:** high

---

### Q462 — Should critique be generated for every labeled event or only errors/uncertain/high-value events?

- **DECISION:** No critiques (`Q459`). The analogous rationing decision — which uncertain memories get a **confirmation prompt** — is: only the highest-value ones, within a weekly cap, at a moment when the memory was relevant (`Q632`).
- **BECAUSE: POSITION.** `P§8`: "Confirmation prompts are budgeted — a small cap per week, spent on the highest-value uncertain memories."
- **REJECTED:** Generating a critique for every event regardless of outcome. Wins for training-data generation.
- **COST:** "Highest-value" is an unset ranking (**Section A**).
- **CONFIDENCE:** high

---

### Q489 — What output contract should the generator optimize for: terse answer, explanation, structured response, or conversational help?

- **DECISION:** By mode. **Anbu:** terse — the result and nothing else. **Koottu:** the result plus one observation with its evidence. **Daari:** the result plus a hypothesis phrased as a question. The trace is always available and never inline. This is `P§6`'s worked example as an output contract.
- **BECAUSE: POSITION.** `P§6`'s three-permission worked example is literally three output contracts for one request, and `P§6`'s Anbu rule — "Says: the result. Nothing else."
- **REJECTED:** A single constrained, direct prompt aligned to benchmark answer formats. It wins on benchmark alignment (the surveyed finding). It collapses the three modes into one voice, which erases the product.
- **COST:** Three generation contracts to implement and evaluate, and the mode's effect on output is enforced by prompt (`Q519`, **Section A**).
- **CONFIDENCE:** high

---

### Q493 — How much nondeterminism is acceptable in durable extraction and answer generation?

- **DECISION:** **Extraction: none** — temperature 0, pinned model, strict schema, deterministic candidate keys (`Q72`). **Generation: wording may vary; facts and citations may not** — every claim resolves to a retrieved memory (`Q106`), so the variation is in phrasing, not content.
- **BECAUSE: ENGINEERING (E2)** for extraction (idempotence, `Q08`); **POSITION** for generation (`P§8`'s grounding).
- **REJECTED:** Treating minor extraction variation as immaterial because aggregate scores are stable (the surveyed answer). It wins when only aggregate quality matters. Here `P§AppC` claim 6 is a per-item property — this memory did not regrow — and aggregate stability says nothing about it.
- **COST:** Pinned models and temperature 0 cap extraction quality and make model upgrades migrations (`Q673`).
- **CONFIDENCE:** high

---

### Q499 — Should critic roles be fixed globally, generated per dataset, selected per failure, or learned over time?

- **DECISION:** Not applicable — no critics (`Q496`). The analogous decision, **prompts**, is: fixed globally, committed to the repository, never per-corpus and never learned (`Q241`, `Q440`).
- **BECAUSE: ENGINEERING (E2).** The reviewer runs a different corpus; prompts tuned per-corpus would not transfer and would make the submitted commit's behaviour corpus-dependent.
- **REJECTED:** Hand-crafting per dataset based on observed failure modes. It wins on per-dataset performance and is standard practice. It is exactly what makes a system look better on its own corpus than on the reviewer's (`Q370`).
- **COST:** Prompts are not tuned to the corpus and will underperform a tuned baseline on it.
- **CONFIDENCE:** high

---

### Q512 — Should the system abstain when evidence is missing or keep iterating toward an answer?

- **DECISION:** Abstain (`Q04`, `Q508`).
- **BECAUSE: POSITION.** `P§8`.
- **REJECTED:** Iterating within a trial budget with calibrated abstention neither designed nor evaluated (the surveyed answer). The phrasing is the point: abstention is not merely absent, it is *not designed* — it is not treated as a thing a system could have. `P§8` treats it as a designed feature with a surface.
- **COST:** As `Q04`.
- **CONFIDENCE:** high

---

### Q610 — When the system lacks enough evidence to answer, what behavior should replace a plausible completion?

- **DECISION:** A specific, actionable abstention: what was searched, what was found nearby, what would be needed to answer, and an offer (`Q69`). Not metacognitive hedging.
- **BECAUSE: POSITION.** `P§8`'s worked example is exactly this shape and the position argues it "is more useful than a guess *and* it teaches the user what Kivi's memory actually contains."
- **REJECTED:** Including metacognition as a capability with criteria, form, trace, and escalation all underspecified. Naming the capability without specifying the behaviour is the gap `P§8` fills.
- **COST:** As `Q69` — good abstentions cost generation.
- **CONFIDENCE:** high

---

### Q648 — Should memory be portable across model backbones, or tuned to the model that generated and consumes it?

- **DECISION:** Portable in principle — memories are typed rows with natural-language content, readable by any model and by a person. But **extraction is pinned** (`Q531`) and a model change is a migration event (`Q673`), so portability is a property of the data, not a supported operation.
- **BECAUSE: POSITION** for the data property (`P§9`'s memory surface requires human-readable content, which also makes it model-agnostic); **ENGINEERING** for the pinning.
- **REJECTED:** Treating memory as a freely transferable external artefact created by one model and consumed by another. It wins on flexibility and its finding — that this works — is encouraging for this design. The pinning here is about reproducibility of *extraction*, not about consumption, so the two are compatible.
- **COST:** Changing the extraction model invalidates the idempotency key and requires a reprocess that must replay suppressions (`Q46`).
- **CONFIDENCE:** high

---

### Q693 — What temporal information should the generator see, and should it interpret time itself or receive normalized temporal facts?

- **DECISION:** Both: the current date, plus **already-normalised absolute event times** on every retrieved memory (`Q65`). The generator renders times for the reader; it never resolves relative expressions into facts.
- **BECAUSE: ENGINEERING (E2)** for the normalisation (reproducibility, `Q65`), with the surveyed finding — that including dates and timestamps adds roughly ten percentage points — as strong independent support for including them at all.
- **REJECTED:** Giving the generator raw relative expressions to interpret. It wins on naturalness of phrasing. It makes answers depend on when they were asked in a way the trace cannot fix (`Q65`).
- **COST:** A wrong normalisation is confidently rendered as an absolute date (`Q799`).
- **CONFIDENCE:** high

---

### Q713 — What should be discarded from self-generated test evidence?

- **DECISION:** Not applicable — no self-generated tests (`Q704`). For the **evaluation corpus**, the filtering is published (`Q371`) and the discard criteria are stated rather than left to "syntactic validity plus judgement."
- **BECAUSE: POSITION.** `P§AppA`'s corpus requirements; `P§AppC`'s provability requirement.
- **REJECTED:** Discarding only syntactically invalid items with semantic filtering underspecified. Unstated filtering is how a corpus becomes flattering (`Q370`).
- **COST:** As `Q370`.
- **CONFIDENCE:** high

---

### Q718 — When model capability is insufficient for reliable self-correction, should the same architecture still be used?

- **DECISION:** The question does not arise — there is no self-correction (`Q494`). But the underlying finding matters and is adopted as a design principle: **the architecture must not depend on emergent model capability**. Every product promise is enforced in code (`Q247`) precisely so that a weaker or different model degrades answer *quality* without breaking any *guarantee*.
- **BECAUSE: POSITION.** `P§2`: "not by a line in a prompt hoping for good behaviour." The surveyed finding — that self-correction "emerges in stronger/larger models" and produced no gain on a weaker one — is direct evidence for why promises should not be prompt-dependent.
- **REJECTED:** Keeping an architecture whose benefit depends on model scale. It wins when you control the model. It is the fragility this design is built to avoid — except at the two places it could not (`Q519` tier-appropriate voice, `Q757` grounding), which are the honest exceptions (**Section A**).
- **COST:** None; this is an argument for the design already chosen.
- **CONFIDENCE:** high

---

### Q756 — When evidence is weak, what should determine whether the system answers at all?

- **DECISION:** Whether a retrieved memory actually supports the claim, judged at generation (`Q47`, `Q757`) — not a retrieval confidence threshold. Kivi answers if it can cite; it abstains if it cannot.
- **BECAUSE: POSITION.** `P§8`'s standard is support, not confidence: an answer is acceptable when it rests on something retrievable and attributable.
- **REJECTED:** Treating top-node activation as retrieval confidence with a calibrated rejection threshold and a measured false-refusal rate. It is the most rigorous abstention design in the inventory and it has something this one lacks: **a calibrated false-refusal rate**. That is a number this system should report and currently has no mechanism to produce, because it has no confidence signal to calibrate (`Q393`). Worth flagging: the alternative is better-instrumented even if its basis is weaker.
- **COST:** No calibrated refusal rate; abstention correctness is assessed by sampling (`Q429`), not measured.
- **CONFIDENCE:** medium

---

### Q803 — Is the knowledge graph itself returned as answer context?

- **DECISION:** No — the entity graph is an index and an expansion mechanism, never answer content (`Q485`). What reaches the generator is memories, which are sentences (`Q734`).
- **BECAUSE: POSITION.** `P§4`'s memories are the unit of answer-worthy content; `P§9` requires them to be readable.
- **REJECTED:** Returning graph facts as context. The inventory's note quotes the surveyed system's own case study: facts alone are "insufficient, point-wise, and instant"; raw turns carry the answer. **That is a direct warning about this design** — sentence-shaped memories are richer than triples, but the same criticism partly applies, and it is why `Q211`'s raw-transcript fallback exists.
- **COST:** As `Q570` — and this is independent evidence that the fallback is load-bearing rather than a nicety.
- **CONFIDENCE:** high

---

### Q813 — What happens when the system doesn't have the answer?

- **DECISION:** It abstains, in a defined form, and the abstention is **reported in the results** as a first-class outcome with its own counts (`Q45`, `Q591`).
- **BECAUSE: POSITION.** `P§AppC` claim 5.
- **REJECTED:** Leaving it to the generator and not reporting abstention in any results table (the surveyed answer). The inventory's observation — abstention appears in the stated abilities and the judge prompts but "is not reported in any results table" — is the field's pattern: abstention is aspired to and unmeasured.
- **COST:** As `Q591` — abstention counts make headline accuracy look worse and need explaining.
- **CONFIDENCE:** high

---

### Q856 — What does the retriever return when nothing relevant exists?

- **DECISION:** The top-k anyway, with their scores, and the *generator* abstains (`Q47`, `Q365`, `Q470`). The near misses are then used to build the abstention.
- **BECAUSE: POSITION.** `P§8`'s example needs near misses to report.
- **REJECTED:** A relevance floor returning null. It wins by giving an absolute "nothing relevant" signal that this system lacks (`Q393`, `Q756`), which would make abstention a retrieval property and therefore measurable. That is a real advantage and the reason `Q756`'s confidence is only medium.
- **COST:** As `Q47` — the generator is the sole guard against answering from irrelevant results, and it is prompt-enforced (`Q757`).
- **CONFIDENCE:** high

---

### Q858 — What does memory hand to the generator?

- **DECISION:** A structured, labelled set — not a flat string. Each memory carries its id, content sentence, type, tier, evidence count, event time, and source ids; plus separately labelled sections for application context, turn history, and the current date (`Q126`, `Q366`).
- **BECAUSE: POSITION.** `P§6` requires the generator's voice to vary by tier, which requires tier to be legible per memory. `P§8` requires per-memory citation (`Q106`), which requires ids. A flat string supports neither.
- **REJECTED:** A flat text string of facts with date ranges and entity summaries. It wins on prompt economy and simplicity. It is where per-memory attribution and tier-awareness are lost, which is `Q860`'s failure in its most common form.
- **COST:** Larger prompts, reflected in the cost report (`Q734`).
- **CONFIDENCE:** high

---

## Stage: USER

---

### Q21 — Should retrieval and disclosure be one operation, or should the system retrieve broadly and separately decide what may influence or be shown in the answer?

- **DECISION:** Separate. Retrieve broadly and permission-blind; then filter for disclosure; then the withheld set is counted and reported but never enters the model's context (`Q36`, `Q472`).
- **BECAUSE: POSITION.** `P§1` principle 1: "What Kivi knows and what Kivi says are different questions. Retrieval and disclosure must be separable." `P§6`: "The dial governs disclosure, not retrieval."
- **REJECTED:** One operation — all four surveyed camps, and the inventory's phrasing for one of them is the clearest statement of the default anywhere in this document: "no permission layer between knowing, using, and saying is described." It wins on efficiency, simplicity, and answer quality. It is the single decision that most defines this product, and `P§AppC` claim 4 exists to prove it was taken (see **Section C**, where seven inventory questions collapse into this one).
- **COST:** As `Q268`/`Q472` — wasted retrieval on Anbu requests, withheld content held in process, and Anbu answers denied context they could have used silently.
- **CONFIDENCE:** high

---

### Q56 — What is exposed to the caller?

- **DECISION:** Ranked memories with content, id, type, tier, evidence count, event time, source ids, per-leg rank provenance and fused score; plus the withheld set with reasons; plus budget drops; plus the search description; plus timings. Not a synthesized answer from the retrieval layer — the answer is a separate stage (`Q165`, `Q663`).
- **BECAUSE: POSITION.** `P§8`'s four trace elements and `P§6`'s withheld display.
- **REJECTED:** Facts only, or a synthesized answer from the retrieval call. The former loses the trace; the latter fuses two stages that `P§1` principle 1 requires to be separable.
- **COST:** As `Q433` — wide payloads.
- **CONFIDENCE:** high

---

### Q05 — What evidence and internal decisions should be exposed to the user when an answer is produced?

- **DECISION:** Four things, on every answer including abstentions, in one expandable surface: **what was retrieved**, **what was withheld and why**, **what was used in the answer**, and **the source transcript behind each memory, one tap away**. Plus, for the memory surface, each entry's evidence count, last-seen date, and change history.
- **BECAUSE: POSITION.** `P§8`, verbatim — this is the Why panel, and the position names all four. `P§9` adds evidence count and last-seen.
- **REJECTED:** "Nothing. No trace, no sources, no 'what was withheld'" — the plurality answer across eleven sources, and the bluntest. Also rejected: append-only audit logs with a user-facing timeline as future work, which is the sophisticated version of the same absence. The first wins on build cost; the second wins with auditors rather than users. The brief forecloses both: "The product should begin and end in an interface intended for a normal user."
- **COST:** The single largest interface surface in the build, with a genuine design difficulty — four states rendered legibly for a non-technical reader (`Q631`), and nowhere to put developer-only diagnostics (`Q405`, **Section A**).
- **CONFIDENCE:** high

---

### Q75 — What happens when a user rejects memory?

- **DECISION:** Two distinct rejections. **"That's not me anymore"** — reversible: the row stays demoted, the suppression can be lifted, the memory can be restored. **"Forget"** — irreversible: purged, suppression permanent (`Q10`, `Q603`).
- **BECAUSE: POSITION.** `P§9` lists them as separate actions with separate effects.
- **REJECTED:** A single reversible dismiss that hides from surfacing (the surveyed answer, added later in that project's history — which is telling: hide-from-surfacing is what teams arrive at once they discover deletion is too blunt). It wins on safety. It cannot honour a user who means "get rid of this."
- **COST:** Two rejection actions to explain, and the irreversible one is one tap away with no confirmation (`Q611`, **Section A**).
- **CONFIDENCE:** high

---

### Q79 — What is exposed initially?

- **DECISION:** On the memory surface: three tier-grouped lists, each entry a sentence with its evidence count and last-seen date, with sources and history one tap deeper. On an answer: the reply, plus a single quiet affordance for the trace. Nothing is dumped; nothing requires a fetch-by-ID tool.
- **BECAUSE: POSITION.** `P§9`: "The memory surface is grouped by tier… because that grouping is what carries the epistemics to a normal user without a single word of explanation. Each entry shows evidence count and the last date it was seen. Tapping shows the source transcripts."
- **REJECTED:** A compact index with explicit fetch-by-ID tools. It wins for an agent consumer. It is a developer interface (`P§9`: "No developer console anywhere in this").
- **COST:** Progressive disclosure must be designed rather than delegated to tools, and three flat lists scale badly (`Q784`).
- **CONFIDENCE:** high

---

### Q84 — Should raw user input be retained alongside curated memory?

- **DECISION:** Yes — permanently, as the provenance substrate, in a separate store with separate rules, never retrieved as memory (`Q28`, `Q141`).
- **BECAUSE: POSITION.** `P§9`: provenance is "the actual transcript, with a date."
- **REJECTED:** Storing user prompts as first-class retrievable records alongside memories. It wins on recall — and note this is nearly what `Q211`'s fallback does, with one difference: the fallback is labelled and secondary, not first-class. That labelling is what keeps a raw hit from being mistaken for a belief.
- **COST:** As `Q28`/`Q186` — the raw store holds what the memory store refuses (**Section B, conflict B2**).
- **CONFIDENCE:** high

---

### Q112 — Is concurrent access considered?

- **DECISION:** Yes, minimally and deliberately: WAL mode, one connection pool, single writer, busy timeout with bounded retry, serialised import queue (`Q96`, `Q184`).
- **BECAUSE: ENGINEERING (E2).** The surveyed answer — a fresh connection per call, no WAL, no busy timeout, three concurrent async writers — is the accidental default and produces intermittent lock errors under exactly the conditions a corpus import creates.
- **REJECTED:** No concurrency handling. Wins never.
- **COST:** As `Q96` — write throughput ceiling.
- **CONFIDENCE:** high

---

### Q119 — Is disclosure a machine-enforced permission or a human-readable hint to the caller?

- **DECISION:** **Machine-enforced.** The dial is a setting read by code that filters the ranked set before the model sees it; withheld memories are excluded from context, not marked as sensitive and passed along (`Q472`).
- **BECAUSE: POSITION.** `P§2`'s enforcement principle generalised by `Q247`: promises live in code. And `P§6`'s withheld count is only meaningful if something actually withheld.
- **REJECTED:** Free-text disclosure on an edge, included in reads with no policy engine interpreting it (the surveyed answer). It wins on flexibility and is a common pattern — a `sensitivity` field that nothing enforces. It is the purest example of a permission that is a label rather than a mechanism.
- **COST:** As `Q472` — Anbu answers are denied context.
- **CONFIDENCE:** high

---

### Q120 — What is exposed to callers: raw content, metadata, graph context, evidence, or an explanation trace?

- **DECISION:** Content, metadata, evidence, and an explanation trace. Graph context only as the entity links already on each memory — never a subgraph payload (`Q803`).
- **BECAUSE: POSITION.** `P§8`.
- **REJECTED:** Content plus metadata without a trace. See `Q05`.
- **COST:** As `Q433`.
- **CONFIDENCE:** high

---

### Q122 — When producing the next turn, should additional information come from the current user's durable history, other users' analogous conversations, or an authored knowledge source?

- **DECISION:** The current user's durable history, exclusively. No other users (`Q273`), no authored knowledge base, no parametric world knowledge presented as memory (`Q471`).
- **BECAUSE: POSITION.** `P§1` principle 2 and `P§3`: the value is "what you no longer have to re-explain," which is by definition the user's own history.
- **REJECTED:** Other users' analogous conversations. It wins for a product with a population and is where most memory products eventually go. It is forbidden here.
- **COST:** As `Q273` — no network effects, no cold-start help.
- **CONFIDENCE:** high

---

### Q136 — What should users see about memory use?

- **DECISION:** Duplicate of `Q05`. The four trace elements plus the memory surface.
- **BECAUSE: POSITION.** `P§8`, `P§9`.
- **REJECTED:** See `Q05`.
- **COST:** See `Q05`.
- **CONFIDENCE:** high

---

### Q151 — Should memory ingest every conversational role, only user-authored statements, or a separately classified subset?

- **DECISION:** A separately classified subset of user-authored content only (`Q01`). Role is recorded on transcripts; only the user's role produces memory candidates.
- **BECAUSE: POSITION.** `P§4`'s tier definitions.
- **REJECTED:** Accepting user|assistant|tool|system and storing role on every chunk. It wins on completeness and keeps the option open. Storing everything and classifying later means the exclusion boundary is a query filter rather than a write barrier (`Q73`).
- **COST:** As `Q01`/`Q153` — acceptance is not evidence.
- **CONFIDENCE:** high

---

### Q204 — Should access determine survival?

- **DECISION:** No. Retrieval does not reinforce (`Q177`) and access does not affect decay (`Q176`). Survival depends on tier, evidence, time-since-re-observation, and user action — never on being read.
- **BECAUSE: POSITION.** `P§4`'s "Nothing self-promotes" and `P§9`'s re-observation criterion.
- **REJECTED:** Salience × age decay with logarithmic access reinforcement and reader breadth. It is the most elaborate survival function in the inventory and it would keep the store healthy. Every term is a judgement about the user's memories made without their involvement.
- **COST:** As `Q177` — no usage signal; a memory used daily ranks like one never needed.
- **CONFIDENCE:** high

---

### Q213 — When an AI must explain an outcome, should the explanation expose model mechanics, statistical associations, contextual interventions, or domain-level causes?

- **DECISION:** None of these. Kivi explains **provenance and process**, not causes: which memories were used, where they came from, what was withheld and why, what was searched. It never explains *why the user does something* except as an explicitly-invited, non-persisted Daari hypothesis.
- **BECAUSE: POSITION.** `P§8`'s trace defines what an explanation is here. `P§2` forbids the domain-cause version when the domain is the user: "If you disagree with a characterisation, you are arguing with a system about who you are."
- **REJECTED:** Domain-level causal explanation answering why/what-if questions. It wins for a decision-support product and is genuinely what people want from "explainable AI." Applied to a person it is the psychological read `P§2` rejects.
- **COST:** Kivi's explanations answer "where did this come from" and never "why is this happening," which will feel thin to users who expected insight (`Q215`).
- **CONFIDENCE:** high

---

### Q231 — At what scope should one causal model apply: globally, per domain, per context, per user, or per episode?

- **DECISION:** Not applicable — no causal model (`Q215`). **Out of scope.**
- **BECAUSE: POSITION.** `P§4`.
- **REJECTED:** A per-context CBN. Wins in a causal product.
- **COST:** None here.
- **CONFIDENCE:** high

---

### Q253 — What should persistent cross-session memory preserve: world facts, user facts, episodes, or reusable reasoning procedure?

- **DECISION:** User facts (entities, preferences) and episodes. Not world facts — Kivi's memory is about the user's working world, not the world. Not reasoning procedures (`Q235`).
- **BECAUSE: POSITION.** `P§4`'s three types, all scoped to "the user's world."
- **REJECTED:** Distilled reasoning strategies and reusable problem-solving patterns, with the schema and boundaries underspecified. It wins for a reasoning assistant. The underspecified boundary is the recurring symptom: procedural memory resists schematisation (`Q503`).
- **COST:** As `Q235`.
- **CONFIDENCE:** high

---

### Q274 — What should be the primary unit on which access is granted and revoked?

- **DECISION:** Nothing — there is no access-control model (`Q296`). One user, all access. The only unit on which anything is granted or revoked is the **memory**, and the grant is the user's own `Forget`/demote.
- **BECAUSE: ENGINEERING (E1)**, with **POSITION** supplying the only real control surface (`P§9`).
- **REJECTED:** Time-varying bipartite user→agent and agent→resource graphs. It wins in a multi-agent system with real access control, and it is the right design there. Here it would model permissions between parties that do not exist.
- **COST:** As `Q296` — no access model to extend.
- **CONFIDENCE:** high

---

### Q275 — When access changes, should old memory eligibility follow current permission, creation-time permission, or an immutable historical grant?

- **DECISION:** Current state, always. A memory's eligibility is determined by its **current tier and status** and the **current dial setting** — never by what was true when it was created. A demoted memory stops being surfaced immediately; a raised dial immediately unlocks observations that were always retrievable.
- **BECAUSE: POSITION.** `P§9`: the user changes what Kivi thinks "in one action," which requires the change to take effect everywhere at once. `P§6`'s dial is a live setting, not a stamp applied at write time.
- **REJECTED:** Creation-time permission or an immutable grant. It wins for auditing what was permissible when. Here it would mean raising the dial does not reveal older observations, which would make the dial incomprehensible.
- **COST:** No record of what was disclosable at a past moment — only the traces show what was actually disclosed (`Q848`).
- **CONFIDENCE:** high

---

### Q290 — Should what the system may retrieve be the same as what it may disclose?

- **DECISION:** No. Duplicate of `Q21`/`Q36` (see **Section C**).
- **BECAUSE: POSITION.** `P§1` principle 1.
- **REJECTED:** Access policy as a read-eligibility boundary, with admissible fragments returned verbatim. Note this is the one place where the *opposite* choice is correct for a different product: in a real multi-user access-control system, retrieval eligibility must equal disclosure eligibility, because retrieving what you may not see is itself the breach. `Q285` makes this distinction explicitly and the README should too.
- **COST:** As `Q268`.
- **CONFIDENCE:** high

---

### Q292 — How should permission escalation be initiated and how long should it last?

- **DECISION:** Two mechanisms with two durations. **Anbu↔Koottu:** an explicit persistent setting, changed by the user, lasting until changed. **Daari:** a per-request invitation — asking "what do you think?" or "why do you reckon…" unlocks hypotheses for that one answer only, and the answer is not written to memory.
- **BECAUSE: POSITION.** `P§6`, verbatim: "The dial is an explicit setting. Default Anbu. **Daari is not a persistent mode.** It's a per-request invitation… unlocks hypotheses for that one answer, and the answer is not written to memory."
- **REJECTED:** Administrative escalation with unmodelled user-facing semantics. Also implicitly rejected: making Daari persistent, which `P§6` considered and refused partly for tractability ("two persistent modes to implement and evaluate, one escalation path").
- **COST:** Detecting a Daari invitation is an intent-classification problem on natural language, which will have false positives and negatives — Kivi will occasionally volunteer a hypothesis unasked, or refuse one that was invited. `P§6` treats the invitation as obvious; it is not. **Section A**.
- **CONFIDENCE:** medium

---

### Q295 — F1 — Share across users or isolate (D01)

- **DECISION:** Isolate, absolutely (`Q273`).
- **BECAUSE: POSITION.** `P§1` principle 2.
- **REJECTED:** Sharing across users. The inventory's note is the honest accounting: "the reported 59–61% reductions in resource use at high overlap… would disappear." Sharing is where the efficiency is, and this product forgoes all of it.
- **COST:** As `Q273` — no reuse, no efficiency gains, no cold start.
- **CONFIDENCE:** high

---

### Q318 — Once a memory is retrieved, what should determine whether it is exposed in the response?

- **DECISION:** Its tier, against the current dial setting, enforced in code before the model sees it (`Q119`, `Q472`).
- **BECAUSE: POSITION.** `P§6`.
- **REJECTED:** A response prompt instructing the model to "reflect the memory," with no separate disclosure policy (the surveyed answer). It wins on simplicity. It is disclosure as an instruction rather than a mechanism.
- **COST:** As `Q472`.
- **CONFIDENCE:** high

---

### Q322 — What kinds of user information should be representable: events and explicit facts only, or also emotions, psychology, aspirations, and inferred identity?

- **DECISION:** Entities, preferences, and episodes about the user's **work** — explicit facts, stated preferences, dated events, and patterns across them. **Never** emotions, psychology, aspirations, or inferred identity. The exclusion is structural, checked in code, and logged when it fires.
- **BECAUSE: POSITION.** `P§2`, which exists to answer this question: "Kivi never infers or stores: health, mood or emotional state, relationships and family, faith, politics, finances beyond work-level facts, or any characterisation of the person's competence or character." And the reasoning: "A product that models your goals and insecurities is studying you. A product that remembers your projects and preferences is working with you. The second is the one people keep using."
- **REJECTED:** Representing the full set. It wins on capability, on user delight, and on every benchmark that measures what a system knows about a person. It is the product `P§2` explicitly built and then discarded — "It was thorough. It was also the wrong product."
- **COST:** As `Q851`/`Q764`/`Q801` — a large class of useful, achievable understanding is permanently out of reach, with no user opt-in (`Q604`).
- **CONFIDENCE:** high

---

### Q348 — When a user moves across requests or sessions, which client-centric guarantees should follow them?

- **DECISION:** Read-your-writes for user actions, unconditionally: a correction is visible to the very next request (`Q259`). Monotonic reads are automatic from the single-writer single-store design. No other guarantees are needed or claimed.
- **BECAUSE: POSITION** for read-your-writes (`P§9`'s corrections must stick, immediately); **ENGINEERING (E2)** for the rest being free.
- **REJECTED:** Full system-wide strong consistency as a stated guarantee. Already have it by construction (`Q339`); stating it as a guarantee would overclaim for a single-node system.
- **COST:** None. Note the one real asymmetry: user corrections are read-your-writes, extraction is not (`Q62`), and that difference is user-visible and must be explained (`Q389`).
- **CONFIDENCE:** high

---

### Q352 — When memory influences an answer, what should the user be shown about what was retrieved, withheld, or used?

- **DECISION:** Duplicate of `Q05`. All three, plus sources.
- **BECAUSE: POSITION.** `P§8`.
- **REJECTED:** Naming user experience as affected while designing no trace (the surveyed answer). See `Q05`.
- **COST:** See `Q05`.
- **CONFIDENCE:** high

---

### Q425 — When implementations disagree, should the tool expose a concrete witness, propose a repair, or make the repair itself?

- **DECISION:** Expose a concrete witness. Where the evaluation finds a defect — a wrongly-dropped candidate, an unresolvable citation, a memory that regrew — it reports the specific case with its transcript and trace, and does not attempt automatic repair (`Q640`, `Q775`).
- **BECAUSE: POSITION.** `P§9` reserves repair for the user; automatic repair is `Q640`'s rejected in-place revision.
- **REJECTED:** Automatic repair. It wins on throughput; it is the system changing beliefs without the user (`Q269`).
- **COST:** Every defect the evaluation finds requires human follow-up, so the evaluation produces work rather than fixes.
- **CONFIDENCE:** high

---

### Q446 — When should writes happen relative to responding to the user?

- **DECISION:** After, asynchronously — except user corrections, which are synchronous and block (`Q259`, `Q317`).
- **BECAUSE: ENGINEERING (E3)** for the default; **POSITION** for the exception (`P§8`'s inline correction).
- **REJECTED:** Asynchronous writes uniformly, including corrections. It wins on latency consistency. A correction that lands eventually is the `P§9` failure.
- **COST:** As `Q62`.
- **CONFIDENCE:** high

---

### Q450 — When memory content is sensitive, should the system redact it, refuse to store it, scope access to it, or retain it under stronger controls?

- **DECISION:** **Refuse to store it.** Redaction is a backstop for literal secrets only (`Q85`); there is no access scoping (`Q274`) and no stronger-controls tier (`Q598`). The primary mechanism is non-retention.
- **BECAUSE: POSITION.** `P§2`: "A hard exclusion list enforced at extraction, **before anything reaches storage**." `P§5`: "It does not enter the write path."
- **REJECTED:** Encryption plus PII redaction plus access scoping plus retention policy plus auditable deletion, with admission exclusions underspecified (the surveyed answer). It is a complete and professional data-protection posture, and the inventory's final clause is the whole difference: **admission exclusions are underspecified**. Every control in that list governs data already stored. This position's control is that it is not stored.
- **COST:** As `Q442` — no way to retain a sensitive-but-important fact under stronger controls. And the one place the surveyed answer is better: at-rest encryption of the transcript store, which this design lacks (`Q335`, `Q759`).
- **CONFIDENCE:** high

---

### Q454 — When a memory is retrieved but the user has not authorized its disclosure, should it be withheld before retrieval, before generation, or only at presentation?

- **DECISION:** **Before generation.** Retrieved, ranked, counted — then removed from the context the model receives (`Q472`). Not before retrieval (that loses the count), not at presentation (that lets it colour the answer).
- **BECAUSE: POSITION.** `P§6` requires retrieval to be complete and disclosure to be filtered; `Q472`'s reasoning fixes the filter point at the context boundary, because a model that sees an observation will use it even if told not to state it.
- **REJECTED:** Withholding at presentation. It wins on answer quality — the model could use the observation implicitly to give a better answer while not naming it. That is precisely what the position calls a violation: Anbu "Never: points out a pattern," and an answer silently shaped by a pattern is worse than one that names it, because the user cannot see it happened.
- **COST:** As `Q472` — Anbu answers are strictly worse than the retrieval would allow.
- **CONFIDENCE:** high

---

### Q455 — When memory contributes to an answer, what should the user be able to inspect and change?

- **DECISION:** Inspect: everything in `Q05`. Change: the memory (four actions plus pin), the dial, and nothing else. Not the retrieval, not the ranking, not the per-request context (`Q616`, `Q623`).
- **BECAUSE: POSITION.** `P§9`'s per-entry actions and `P§6`'s dial are the complete control surface; `P§8`'s administrator warning bounds it.
- **REJECTED:** Developer operation logs plus source attribution plus deletion plus access controls, with a normal-user explanation surface underspecified. The inventory's phrasing recurs across the whole user stage: the developer surface exists, the user surface does not. `P§8` builds one thing for both (`Q405`), and that is the position's distinctive bet.
- **COST:** As `Q405` — developer-only diagnostics have nowhere to live (**Section A**).
- **CONFIDENCE:** high

---

### Q464 — What should semantic memory represent: user facts, task rules, or a compressed model of prior critiques?

- **DECISION:** User facts — entities, preferences, episodes — about the user's work (`Q253`). Not task rules, not compressed critiques.
- **BECAUSE: POSITION.** `P§4`'s three types and `P§3`'s value claim.
- **REJECTED:** A task-level summary of all critiques as a bulleted instruction list. It wins for task performance and is a real technique. It is a model-authored instruction set with no tier, no source, and no correction path — and functionally it would be Kivi instructing itself about the user.
- **COST:** As `Q235`.
- **CONFIDENCE:** high

---

### Q466 — When specific experience and abstract guidance are both available, should the system choose one or expose both to the model?

- **DECISION:** Expose both — the **specific** (episodes, with dates and sources) and the **general** (observations, with evidence counts) — clearly labelled by tier so the model and the reader can tell which is which (`Q858`).
- **BECAUSE: POSITION.** `P§4`'s two independent axes mean type and tier both travel with every memory; `P§6`'s three response contracts depend on the model knowing which is which.
- **REJECTED:** Choosing one. It wins on prompt economy. The hybrid finding from the surveyed source agrees with this decision, which is worth noting: including both performs best there too.
- **COST:** Larger prompts (`Q734`).
- **CONFIDENCE:** high

---

### Q473 — What should the system expose to the end user about memory use?

- **DECISION:** Duplicate of `Q05`/`Q136`/`Q352`. The four trace elements plus the memory surface (see **Section C** — six inventory questions, one decision).
- **BECAUSE: POSITION.** `P§8`, `P§9`.
- **REJECTED:** Only the classification answer, with memory text presented to the model and never surfaced to the user. See `Q05`.
- **COST:** See `Q05`.
- **CONFIDENCE:** high

---

### Q476 — At what boundary should different users' memories be isolated?

- **DECISION:** There is one user (`E1`). No isolation boundary exists, and none is simulated (`Q121`).
- **BECAUSE: ENGINEERING (E1)**, with **POSITION** ruling out sharing even in principle (`P§1` principle 2).
- **REJECTED:** Treating preference users independently while using dataset-wide memory for fact tasks (the surveyed answer). It is a revealing split: isolation is applied where it affects results and dropped where it does not, which is how isolation becomes a benchmark artefact rather than a property.
- **COST:** As `Q82`.
- **CONFIDENCE:** high

---

### Q492 — Should one configuration serve all datasets, users, and request types, or should configuration adapt?

- **DECISION:** One configuration, fixed and committed, serving everything (`Q499`, `Q440`). The evaluation reports sensitivity to key parameters rather than optimising them per corpus.
- **BECAUSE: ENGINEERING (E2).** The reviewer runs a different corpus with the submitted commit; per-corpus configuration would not transfer, and tuning on my own corpus is how a system looks better on it than on theirs (`Q370`).
- **REJECTED:** Per-dataset × per-metric optimisation, which found no single best configuration and argued for task-specific adaptation. That finding is a genuine warning: a single fixed configuration is probably not optimal for the reviewer's corpus, and this system will underperform a tuned baseline on it. The honest response is to report sensitivity so the reviewer can see how much configuration matters, not to claim the fixed one is best.
- **COST:** Measurably suboptimal on any specific corpus, including the reviewer's. Combined with `Q491`'s refusal of scalar optimisation, this system has no tuning story at all.
- **CONFIDENCE:** high

---

### Q524 — What can the user do about a memory directly?

- **DECISION:** Four actions plus pin plus inline correction, each one tap, phrased in human terms (`Q738`).
- **BECAUSE: POSITION.** `P§9`.
- **REJECTED:** "Nothing. Correction only via saying something contradictory in a later turn" — the surveyed answer, and it describes most shipping memory products. It wins on build cost. `P§9`'s entire argument is against it: "What Kivi thinks of you is [in your hands]."
- **COST:** As `Q611` — cheap destructive actions without confirmation (**Section A**).
- **CONFIDENCE:** high

---

### Q530 — How much of the user's attention may the system spend?

- **DECISION:** A small, fixed weekly budget of confirmation prompts, spent on the highest-value uncertain memories, at moments when the memory was relevant to the request in hand. Never a review queue. Never during ordinary dictation. Observations under Koottu are not budgeted — they attach to relevant requests and are the mode's purpose — but they are also not interruptions.
- **BECAUSE: POSITION.** `P§8`: "Confirmation prompts are budgeted — a small cap per week… A prompt is a cost paid by the user." And: "the person must not become the administrator of the system."
- **REJECTED:** Never asking anything (the surveyed answer — "the question never arises"). It wins on non-intrusiveness absolutely. It means the stated tier can only grow when the user volunteers something, which makes promotion (`Q191`) nearly vestigial.
- **COST:** The cap size and the "highest-value" ranking are unset (`P§AppB` defers the budget size explicitly). See **Section A**.
- **CONFIDENCE:** high

---

### Q543 — How much of the memory system should the user be able to see?

- **DECISION:** All of it that concerns them: every memory, its tier, its evidence, its sources, its history; every answer's retrieved/withheld/used sets; every transcript's extraction outcome including drops. Not the machinery — no scores presented as meaning, no queue state, no model names in the user surface.
- **BECAUSE: POSITION.** `P§9`: "Every memory shows its provenance… Everything is editable, pinnable, or removable." `P§8`'s trace. And the boundary: "No developer console anywhere in this."
- **REJECTED:** "None of it" (the surveyed answer, and the norm). It wins on interface simplicity and is what nearly every product does.
- **COST:** As `Q405` — the machinery has nowhere to be inspected, which is a problem for the brief's engineer-inspection requirement (**Section A**).
- **CONFIDENCE:** high

---

### Q548 — Should UserMemory capture be coupled to episodic/L1 capture?

- **DECISION:** Not applicable as two systems — there is one memory table (`Q202`). Within it, the three **types** are extracted by one call and judged independently: a transcript may produce an entity, a preference, an episode, several, or none.
- **BECAUSE: POSITION.** `P§4`'s types are independent, and `P§5`'s worked example produces two memories of different types plus two drops from one transcript (`Q547`).
- **REJECTED:** Two independently judged capture branches over two stores. Functionally similar; the two-store version reintroduces `Q551`'s separation questions without benefit.
- **COST:** None material.
- **CONFIDENCE:** high

---

### Q549 — Should questions, transient commands, dynamic current facts, and assistant guesses become durable user beliefs?

- **DECISION:** No to all four, and for four different reasons. **Questions** the user asks are not statements of fact. **Transient commands** ("send that now") fail the durability test. **Dynamic current facts** ("I'm in a meeting") fail durability. **Assistant guesses** are not user-authored (`Q198`). All four are handled by the eligibility gates, not by regex.
- **BECAUSE: POSITION.** `P§3`: "the **durable**, work-level things you would be annoyed to have to repeat." Durability is the gate.
- **REJECTED:** Regex gates rejecting question-like and dynamic-current patterns (the surveyed answer). It wins on determinism and cost — regex is free and never hallucinates. It is brittle across phrasings and cannot express "durable," which is semantic. Worth noting as the one place a cheap deterministic filter would plausibly outperform a model, and it is declined for coverage rather than principle.
- **COST:** Durability is a model judgement and will be wrong at the edges; a transient fact stored as durable is a memory that ages badly with no decay to catch it (stated memories do not decay, `Q178`).
- **CONFIDENCE:** medium

---

### Q558 — If the user states a new current fact, is it a correction?

- **DECISION:** Not automatically. A new stated fact that **contradicts** an existing one triggers supersession (`Q13`) — which is the system's judgement, recorded and visible. A new fact that merely differs coexists. An explicit correction ("no, actually…") is unambiguous and takes the correction path with a suppression (`Q557`).
- **BECAUSE: POSITION.** `P§9`'s supersession is evidence-driven and automatic for contradictions; `P§8`'s inline correction is user-signalled and additionally suppresses. The two differ in whether a suppression is written, and that difference matters: supersession can be undone by newer evidence, suppression cannot be undone by evidence at all.
- **REJECTED:** Both remaining active unless the caller sends an explicit correction target (the surveyed answer). It wins on safety — nothing is superseded by accident. It means Kivi holds contradictory current facts whenever the user does not use correction language (`Q658`).
- **COST:** Distinguishing "contradicts" from "differs" is a model judgement on the write path, and a false positive silently supersedes a fact the user still holds. **This is the most consequential fallible judgement in the system after extraction itself.**
- **CONFIDENCE:** medium

---

### Q563 — Expose only answer text or also evidence and decision traces?

- **DECISION:** Both, and the trace includes drop reasons, degradation notices, latency, and the recall-event record (`Q56`, `Q05`).
- **BECAUSE: POSITION.** `P§8`.
- **REJECTED:** Answer text only. See `Q05`. Note this surveyed answer largely agrees — hits, source ids, drop reasons, latency tiers, and a recall audit row is close to the right set, and is one of the few in the inventory that is.
- **COST:** As `Q433`.
- **CONFIDENCE:** high

---

### Q571 — Should provenance point to a derived contextual object or to the original evidence a person can inspect?

- **DECISION:** To the **original transcript**, stored in full, inspectable by a person, one tap from the memory. Not to a derived object and not to a summary (`Q570`).
- **BECAUSE: POSITION.** `P§9`, verbatim: "Not a category label — the actual transcript, with a date, that produced it."
- **REJECTED:** Linking to the conversation and its summary, with whether the original span is stored or exposed left underspecified (the surveyed answer). That underspecification is the exact failure mode: provenance that points at a derived object is provenance you cannot check.
- **COST:** As `Q28` — the transcript store holds everything (**Section B, conflict B2**).
- **CONFIDENCE:** high

---

### Q583 — How should confirmation requests be selected so memory improves without turning the user into its administrator?

- **DECISION:** A weekly cap; selection by expected value — an uncertain memory's evidence strength times how often it would change Kivi's behaviour if confirmed; presented only when that memory was relevant to the request in hand; never queued, never batched, never at session start.
- **BECAUSE: POSITION.** `P§8`, which states the constraint and the placement rule but not the selection function: "spent on the highest-value uncertain memories," "attached to a request where the memory was actually relevant," "Never as a review queue."
- **REJECTED:** No confirmation loop at all (the surveyed answer). See `Q530`.
- **COST:** The value function and the cap are both unset, and `P§AppB` explicitly defers "confirmation budget size." **This is the most product-critical of the unset parameters** (**Section A**), because it directly governs how fast the stated tier grows and therefore how often Kivi is allowed to act confidently.
- **CONFIDENCE:** medium

---

### Q618 — Should the user-facing memory representation match the context actually exposed to the model?

- **DECISION:** Yes, exactly — with one deliberate asymmetry. The memory surface shows every memory including withheld ones (the user can always see what Kivi knows); the model sees only the disclosure-filtered subset. The **trace** reconciles them by showing what was withheld and why. Within the disclosed set, what the user sees and what the model saw are identical.
- **BECAUSE: POSITION.** `P§8`'s trace shows "what was used in the answer," which is only meaningful if it is the actual model input. And `P§6`'s calibration means the user and the model see different things *by design* — the user is entitled to more than the model, which is the inverse of the usual arrangement and worth stating plainly.
- **REJECTED:** A shared representation where the front end is exactly what the model sees. It wins on conceptual cleanliness — "common ground" is a good principle. Here it would mean either showing the user less than Kivi knows, or giving the model everything. Both break the product.
- **COST:** Three views to keep consistent — memory surface, model context, trace — and any divergence is a trust bug rather than a display bug.
- **CONFIDENCE:** high

---

### Q619 — When a user's intent or conversational context changes, what should determine whether an existing memory can influence the next response?

- **DECISION:** Relevance to the new request (retrieval) and tier against the dial (disclosure). Nothing else — no per-memory visibility toggles, no context switching (`Q623`, `Q616`).
- **BECAUSE: POSITION.** `P§8`'s administrator warning; `P§6`'s dial is the only user-facing influence control.
- **REJECTED:** Per-object visible/hidden toggles with hidden objects greyed out. It is direct, legible, and gives the user real control. It is per-request administration (`Q623`), and it would compete with the four `P§9` actions for the same conceptual space — a user would not know whether to hide a memory or demote it.
- **COST:** No temporary exclusion. A user working on something unrelated cannot tell Kivi to ignore a project for an hour.
- **CONFIDENCE:** medium

---

### Q633 — What happens when the memory system itself is wrong about what it stored, summarized, or exposed?

- **DECISION:** The user corrects it through the four actions, having inspected the original transcript behind the memory (`Q05`). There are no summaries to be wrong about (`Q154`). Wrong **exposure** — a disclosure that should not have happened — is a severity-one failure caught by the evaluation (`Q585`), not by a user-facing remedy, because by then it has been said.
- **BECAUSE: POSITION.** `P§9` for correction; `P§AppC` for exposure being an evaluation obligation.
- **REJECTED:** Edit/delete plus inspection with no automatic detection or rollback semantics (the surveyed answer). It is close to this answer and missing suppression (`Q608`) and an exposure story.
- **COST:** A wrong disclosure has no remedy at all. Once Kivi has said something it should not have, the product offers the user nothing — and the position, which is otherwise careful about failure, does not address this. **Section A**.
- **CONFIDENCE:** medium

---

### Q645 — Should memories preserve provenance and revision history for inspection, or only the currently useful representation?

- **DECISION:** Both, always: provenance is required on write (`Q86`), revision history is preserved through supersession and status events (`Q330`), and both are inspectable by the user.
- **BECAUSE: POSITION.** `P§9`.
- **REJECTED:** Operationally using the current representation with source links, version history, and audit underspecified. The recurring gap.
- **COST:** As `Q330` — substantial metadata and database growth.
- **CONFIDENCE:** high

---

### Q649 — Should memory be shared across tasks/users/environments, or isolated by owner, tenant, project, and source?

- **DECISION:** One user, one pool, shared across tasks and requests; isolated from nothing because there is nothing to isolate from (`Q78`, `Q273`).
- **BECAUSE: ENGINEERING (E1)** for the isolation half; **POSITION** for the no-cross-user half.
- **REJECTED:** A repository reused across related tasks with ownership and tenant boundaries unrepresented. The unrepresented boundaries are the problem — sharing without an ownership model is how cross-user leakage happens by default.
- **COST:** As `Q78`/`Q273`.
- **CONFIDENCE:** high

---

### Q703 — How should an action policy expose its intermediate reasoning?

- **DECISION:** Through the **trace**, as structured recorded steps — retrieved set, withheld set, ranking components, tool chosen, memories cited — not through model-generated chain-of-thought presented to the user. The reasoning exposed is the *system's*, not the model's.
- **BECAUSE: POSITION.** `P§8`'s trace elements are all system facts, not model narration. And `P§8`'s standard — "Something a person can act on" — is met by "these three memories, from these transcripts" and not by a paragraph of model reasoning, which is itself unverifiable.
- **REJECTED:** Exposing chain-of-thought or ReAct thought/action/observation traces. It wins on apparent transparency and is what most agent products show. Model-narrated reasoning is a plausible account of a decision, not a record of it — the same objection as `Q212`'s to LLM reranking.
- **COST:** The trace cannot explain *why the model chose a tool* or *why it worded something a way* — only what it was given and what it did. That is a genuine gap in explainability that the position's framing does not acknowledge.
- **CONFIDENCE:** high

---

### Q711 — For generated code without access to hidden tests, what should determine whether the candidate is revised or returned?

- **DECISION:** Out of scope — Kivi does not generate code or self-test (`Q508`, `Q704`). The transferable rule: an answer is returned when every claim resolves to a cited memory (`Q106`), and revised never — it is returned or abstained (`Q512`).
- **BECAUSE: POSITION.** `P§8`.
- **REJECTED:** Self-generated tests with early return. Wins for code generation.
- **COST:** None here.
- **CONFIDENCE:** high

---

### Q717 — Across tasks or users, what should persist over time?

- **DECISION:** Memories about the user's work — permanently, subject to tier-based standing — plus transcripts, suppressions, confirmations, and traces (`Q263`). Across users: nothing (`Q273`).
- **BECAUSE: POSITION.** `P§4`, `P§9`, `P§1` principle 2.
- **REJECTED:** Task-local reflections in a tiny sliding window with no cross-task durable learning (the surveyed answer). It is the opposite failure from most of the inventory: too little persistence rather than too much.
- **COST:** As `Q263` — traces grow unbounded and unpruned (**Section A**).
- **CONFIDENCE:** high

---

### Q737 — What should users be able to inspect about a memory-backed answer?

- **DECISION:** Duplicate of `Q05`. Retrieved, withheld-with-reasons, used, and sources (see **Section C**).
- **BECAUSE: POSITION.** `P§8`.
- **REJECTED:** Exposing only the final answer while the retrieval rationale exists in a planner's JSON (the surveyed answer). The rationale existing internally and not reaching the user is `Q860`'s failure applied to explanation rather than provenance — and it is the most common shape of this gap.
- **COST:** See `Q05`.
- **CONFIDENCE:** high

---

### Q774 — What provenance should survive compression, and who should be able to inspect it?

- **DECISION:** There is no compression (`Q539`). Provenance survives everything — merges append sources, supersessions keep them, and `Forget` is the only operation that removes a memory, leaving its sources untouched (`Q381`). The user inspects it; so does the evaluation; there is no third audience.
- **BECAUSE: POSITION.** `P§9`, `P§8`.
- **REJECTED:** Thread IDs linking summaries to contents with claim-to-source granularity and the user interface both underspecified. Two gaps in one sentence, and they are the two `P§9` and `P§8` respectively close.
- **COST:** As `Q330`.
- **CONFIDENCE:** high

---

### Q777 — What should the user see of memory operation: only the final answer, citations, the retrieved memories, withheld memories, or the whole editable model?

- **DECISION:** All of them: answer, citations, retrieved, withheld, and an editable memory surface — with editing scoped to memories rather than to retrieval or context (`Q455`).
- **BECAUSE: POSITION.** `P§8` and `P§9` together specify all five.
- **REJECTED:** Specifying answer generation and leaving exposure underspecified. See `Q05`. That this is the eighth inventory question whose answer is "build the Why panel" is itself informative about how uniformly the field omits it (see **Section C**).
- **COST:** See `Q05`.
- **CONFIDENCE:** high

---

### Q790 — What information from retrieval should the response generator be allowed to expose?

- **DECISION:** Only what it was given, which is only what the dial permits — the generator cannot expose a withheld memory because it never received one (`Q472`, `Q454`).
- **BECAUSE: POSITION.** `P§6`, enforced structurally rather than by instruction.
- **REJECTED:** Providing all fused context to generation with no disclosure layer, permission dial, sensitivity filter, or withheld state (the surveyed answer). The inventory names four absent mechanisms; this position supplies all four, and they are the same mechanism seen from four angles (see **Section C**).
- **COST:** As `Q472`.
- **CONFIDENCE:** high

---

### Q812 — Is knowing separated from saying?

- **DECISION:** Yes. That separation is the product (`Q21`, `Q36`).
- **BECAUSE: POSITION.** `P§1` principle 1, verbatim: "What Kivi knows and what Kivi says are different questions. Retrieval and disclosure must be separable." And the human argument it comes from: "When a friend tells you something they're insecure about, you hold it. You don't repeat it back to them at dinner to demonstrate that you were listening. Knowing something and saying it are two separate acts."
- **REJECTED:** "No. Retrieved ⇒ injected into the prompt ⇒ sayable. There is no disclosure stage" — the surveyed answer, and the universal default. It wins on everything except the one thing this product is for.
- **COST:** As `Q472`.
- **CONFIDENCE:** high

---

### Q826 — When memory is retrieved, should it be silently applied, disclosed as an observation, or withheld pending permission?

- **DECISION:** All three, by tier and mode, and never ambiguously. **Stated:** silently applied — Kivi just does the thing correctly without announcing that it remembered. **Observed:** disclosed as an observation with evidence under Koottu; withheld under Anbu, with a quiet affordance saying something was noticed. **Hypothesised:** withheld unless invited.
- **BECAUSE: POSITION.** `P§6`'s worked example is this answer: Anbu says "Done — Atlas pricing section scheduled for Friday" (stated memory silently applied); Koottu adds the pattern with dates; Daari adds the hypothesis only if invited. And `P§6`: "When Anbu withholds something, the interface shows a single quiet affordance rather than the content itself: *'Kivi noticed something here.'*"
- **REJECTED:** Supplying everything as context with no tier or disclosure mechanism (the surveyed answer, and the default). See `Q812`.
- **COST:** The silent application of stated memories is invisible — the user cannot easily tell that Kivi remembered rather than guessed, except through the trace. That is intentional (`Q544`) and it is why the product's memory is largely unnoticeable in its default mode (**Section B, conflict B4**).
- **CONFIDENCE:** high

---

### Q827 — What should the user be shown about why a memory affected an answer?

- **DECISION:** Duplicate of `Q05`. Which memories were used, their tier and evidence, the source transcript behind each, what was withheld and why, and what was searched.
- **BECAUSE: POSITION.** `P§8`.
- **REJECTED:** Internal graph-to-turn links with user-facing explanation underspecified (the surveyed answer). This is the ninth question resolving to "build the Why panel" (see **Section C**), and the uniformity of the gap across the inventory is the strongest available evidence that building it is a genuine differentiator rather than table stakes.
- **COST:** See `Q05`.
- **CONFIDENCE:** high

---

## Stage: EVALUATION

---

### Q30 — What should determine whether the system's memory design is successful?

- **DECISION:** The seven `P§AppC` claims as pass/fail gates, plus the brief's inspection list, plus reported latency, database growth, model usage, and cost. Severity-ordered per `Q585`: impermissible retention and impermissible disclosure are failures no accuracy can offset.
- **BECAUSE: POSITION.** `P§AppC`: "Each of these should be provable from the evaluation output, not asserted in the README."
- **REJECTED:** End-task success metrics — Pass@1, binary answer accuracy, end-state task success with action steps and completion time. All three surveyed camps measure whether the task got done. They are better metrics than mine in every respect except that they cannot see four of this product's six failure classes (`Q585`). The honest framing: their metrics are more rigorous, mine are more relevant.
- **COST:** As `Q477`/`Q431` — bespoke, small-N, partly manual, incomparable to anything published.
- **CONFIDENCE:** high

---

### Q41 — What should count as success for a memory system?

- **DECISION:** Four things, in order: (1) it kept nothing it should not have; (2) it said nothing it should not have; (3) corrections stuck; (4) its answers were supported by the user's actual history, and it abstained when they were not. Task success is fifth and is not a memory metric.
- **BECAUSE: POSITION.** `P§3`: "why someone trusts it enough to keep using it: because every belief is attributable, the boundaries are demonstrable rather than promised, and the person can change what Kivi thinks about them in one action." Those three clauses are criteria 1–3.
- **REJECTED:** Human ratings of consistency, coherence, humanness, engagingness, and memorability. It wins on capturing what users actually experience, and it is a better proxy for whether people keep using a product. It measures none of the four above, and "memorability" in particular rewards exactly the volunteering behaviour `Q544` rejects.
- **COST:** No measure of whether the product is pleasant to use. The evaluation can show it is trustworthy and cannot show it is good.
- **CONFIDENCE:** high

---

### Q125 — How many retrieved cases should influence an answer when quality and cost trade off?

- **DECISION:** A configured top-k with a token budget, value set from corpus data, with sensitivity reported rather than a single number defended (`Q833`, `Q469`).
- **BECAUSE: POSITION.** `P§AppB`: parameters "need corpus data before they can be set honestly."
- **REJECTED:** Picking a defensible number now. It wins on decisiveness. See **Section A** — k is one of the parameters deliberately left open.
- **COST:** As `Q859` — uniform k, wrong at both extremes.
- **CONFIDENCE:** high

---

### Q163 — Should low absolute scores be compared to a global cutoff or to the best result in the current query?

- **DECISION:** Neither — there is no score cutoff at all (`Q393`, `Q576`). RRF ranks are not calibrated, so no absolute or relative score threshold is meaningful. Top-k always returns k; the generator decides whether anything supports an answer (`Q47`).
- **BECAUSE: ENGINEERING**, following from `Q209`'s choice of rank fusion over score fusion.
- **REJECTED:** A relative cutoff (topScore × minScore × factor, normalised). It wins by giving a per-query "nothing good enough" signal, which this system lacks and which `Q756` identifies as a genuine instrumentation gap. It is the most practical available fix for that gap and is worth revisiting.
- **COST:** As `Q756` — no calibrated false-refusal rate.
- **CONFIDENCE:** medium

---

### Q166 — If summarization, embedding, or dedup fails, should ingestion fail closed, fail open, preserve raw memory, or report partial success?

- **DECISION:** Split. **Exclusion check fails → fail closed**, no write (`Q394`). **Extraction fails → quarantine and retry**, raw transcript preserved regardless (`Q108`). **Embedding fails → write proceeds, flagged for repair**, degradation recorded (`Q148`). **Dedup/merge judgement fails → treat as NEW**, which is the safe direction (`Q449`). Every case reports partial success explicitly; none is silent.
- **BECAUSE: POSITION** for the fail-closed exclusion (`P§2`'s absoluteness) and the merge-conservative default (`P§9`'s per-entry correctability); **ENGINEERING (E4)** for the rest.
- **REJECTED:** Counting errors and continuing per message, logging and proceeding (the surveyed answer). It wins on ingestion throughput and is the right default for a general pipeline. Applied to the exclusion check it would mean a classifier outage silently admits everything, which is the one failure this product cannot survive.
- **COST:** A classifier outage halts memory formation entirely (`Q394`), and four distinct failure behaviours must be documented and tested.
- **CONFIDENCE:** high

---

### Q195 — What does the caller receive on success?

- **DECISION:** The answer, the validated citation list, the trace (retrieved / withheld-with-reasons / used / searched / dropped-for-budget), and timings (`Q56`, `Q106`).
- **BECAUSE: POSITION.** `P§8`.
- **REJECTED:** Answer only. See `Q05`.
- **COST:** As `Q433`.
- **CONFIDENCE:** high

---

### Q272 — What optimization target should govern memory design: answer accuracy, token/latency efficiency, inspectability, privacy, or correction cost?

- **DECISION:** A lexicographic order, not a blend (`Q491`): **privacy** (non-retention, non-disclosure) → **correction cost** (corrections must stick and be cheap) → **inspectability** → **answer accuracy** → **token/latency efficiency**. The first two are constraints; only the last two are optimised.
- **BECAUSE: POSITION.** `P§3` names the trust preconditions before any capability claim; `P§2` and `P§5` are absolute; `P§8` and `P§9` make inspectability and correction structural. Accuracy appears nowhere in the position as a goal — the value claim is "you no longer have to re-explain," not "Kivi answers correctly."
- **REJECTED:** Optimising sustained accuracy under bounded tokens. It wins as a research target and is measurable. The ordering above is a product position, not a measurement, and it will produce a system that scores worse and is more defensible.
- **COST:** As `Q491`/`Q492` — no tuning story, measurably suboptimal accuracy.
- **CONFIDENCE:** high

---

### Q294 — What scale and latency proxy should shape the architecture and evaluation?

- **DECISION:** The brief's scale — one user, ~500 transcripts — measured with **real wall-clock latency and real monetary cost**, not call-count proxies. Retrieval latency, end-to-end latency, database growth, model usage, and cost are all reported as measured values with their measurement conditions stated.
- **BECAUSE: ENGINEERING (E2, E3).** The brief asks for exactly these four and will measure them itself on a different corpus, so a proxy would be immediately contradicted.
- **REJECTED:** Call counts as an overhead proxy because real latency fluctuates. It wins on stability — call counts are reproducible where latency is not. `Q303`'s note is the objection: a call-count proxy hides coordinator, embedding, write-transform, and aggregator costs, so it systematically flatters architectures with many cheap calls.
- **COST:** Latency and cost numbers vary by machine and by provider, so they must be reported with conditions and will not be directly comparable to the reviewer's run.
- **CONFIDENCE:** high

---

### Q303 — F10 — Call count as the efficiency measure (D28)

- **DECISION:** Rejected as the measure. Efficiency is reported as **total measured cost and latency across the whole pipeline** — extraction, exclusion classification, merge and contradiction judgement, embedding, retrieval, generation — itemised by stage so the expensive parts are visible.
- **BECAUSE: ENGINEERING (E2)**, and it matters here because this design is call-heavy by choice: per-transcript extraction (`Q170`), a separate exclusion check (`Q701`), per-candidate sameness and contradiction judgement (`Q540`). A call-count measure would make this system look bad; a total-cost measure will make it look expensive and honest. Both are true and the second is useful.
- **REJECTED:** Call count. See above.
- **COST:** The cost report will show this system is more expensive per transcript than a single-prompt extractor, and the README has to justify that rather than hide it.
- **CONFIDENCE:** high

---

### Q320 — How should cost and latency be traded against memory quality across query generation, dual retrieval, blending/refinement, and response generation?

- **DECISION:** Measured and reported, never silently traded. Concretely: no query generation (`Q123`), dual retrieval always (`Q732`), no blending (`Q317`), one generation pass. The per-request LLM budget is one call; the per-transcript budget is extraction plus classification plus per-candidate judgements.
- **BECAUSE: ENGINEERING (E5)**, with `P§AppB` deferring cost targets and the brief requiring the numbers.
- **REJECTED:** Multiple LLM passes per turn (query generation, blend/refine, response) with no latency, token, or cost evaluation reported. The missing evaluation is the point: a design with three LLM calls per turn and no cost reporting is making a trade it has not measured.
- **COST:** Per-request cost is low; per-transcript ingestion cost is high (`Q303`).
- **CONFIDENCE:** high

---

### Q334 — How should a lifetime corpus fit within compute, context, and latency budgets: full replay, hierarchical summaries, retrieval, compression, or bounded windows?

- **DECISION:** Retrieval over extracted facts, with raw transcripts retained but never replayed wholesale (`Q104`, `Q33`). No hierarchical summaries, no compression, no bounded window.
- **BECAUSE: POSITION.** `P§4` (typed facts) and `P§9` (raw retained, not replayed). The rejection of summaries is `Q154`.
- **REJECTED:** Hierarchical summaries. It is the standard answer for lifetime corpora and it is `Q570`'s recurring gap. At the brief's scale the question is not pressing; at a lifetime corpus it would be decisive, and this design has no answer (`Q321`).
- **COST:** As `Q321` — no lifetime-scale story.
- **CONFIDENCE:** high

---

### Q349 — When context does not affect the immediate outcome, may replicas temporarily diverge to gain latency, throughput, and availability?

- **DECISION:** Not applicable — no replicas (`Q339`). The one analogous divergence that does exist is the embedding index lagging the record (`Q344`), and it is permitted **only because it is visible**: a memory retrievable lexically but not semantically is marked and reported.
- **BECAUSE: ENGINEERING (E2)** for the no-replicas half; **E4** for the visibility condition on the one permitted divergence.
- **REJECTED:** Eventual consistency for background knowledge. Wins in a distributed deployment.
- **COST:** As `Q344` — a transient degraded window the evaluation must avoid measuring.
- **CONFIDENCE:** high

---

### Q430 — When runtime depends on data shape, which data distribution and scale should determine the comparison?

- **DECISION:** The brief's distribution and scale — ~500 dictations from one user — with results reported at that scale and **no extrapolation**. Where scaling behaviour matters (write-time contradiction search, `Q540`), its complexity is stated analytically rather than measured at scales the build does not reach.
- **BECAUSE: ENGINEERING (E3)**, with `Q321`'s honesty discipline.
- **REJECTED:** Synthetic scaling from ten thousand to a million rows. It wins by characterising the performance curve, which is genuinely useful and would expose `Q540`'s quadratic behaviour. It is also work that serves no `P§AppC` claim and would test paths the product does not have (`E5`). A middle position — reporting the complexity and one larger synthetic run for the write path — is probably right and is not currently planned.
- **COST:** Scaling behaviour is asserted analytically, not demonstrated.
- **CONFIDENCE:** medium

---

### Q497 — When the same model family performs acting, evaluating, criticizing, and judging, what should create independence between roles?

- **DECISION:** Structural independence where it matters and honest reporting where it does not. The **exclusion check** is a separate call with a separate prompt whose verdict is enforced in code (`Q533`) — independence by mechanism, not by persona. The **evaluation judge**, where one is used, is a different model from the extractor and the generator, its agreement with human grading is sampled and reported, and it is never the primary grader (`Q592`).
- **BECAUSE: POSITION** for the exclusion check (`P§2`); **ENGINEERING (E4)** for the judge.
- **REJECTED:** Prompted personas and role separation using one model for every role. It wins on cost and operational simplicity. Prompted personas over one model produce correlated errors, and using the same model as generator and judge is the specific case where the correlation is most damaging.
- **COST:** A second model dependency for grading, and agreement rates that will have wide intervals at small N (`Q429`).
- **CONFIDENCE:** high

---

### Q509 — What should count as authoritative feedback when evaluating an attempt?

- **DECISION:** Three sources, ranked: (1) **the source transcripts** — did the answer's claims appear there; (2) **human inspection** on a fixed sample; (3) an LLM judge as an assistant whose agreement is measured. Never an automated scalar as the sole authority.
- **BECAUSE: POSITION.** `P§8`'s standard is support by the user's actual history, which makes the transcripts the ground truth. `P§AppC`'s claims are mostly structural properties checkable against the database and the logs, not against a gold answer.
- **REJECTED:** Normalised exact match or hidden-test execution. Both are excellent where they apply and neither applies: there is no gold answer for "draft a reply in her voice," and no executable test for "did it correctly abstain."
- **COST:** As `Q428`/`Q429` — small-N, partly manual, subjective at the edges.
- **CONFIDENCE:** high

---

### Q513 — How should the system trade correction quality against API calls, tokens, latency, and energy?

- **DECISION:** Spend on the **write** path and economise on the **read** path. Ingestion is deliberately expensive — separate exclusion check, per-candidate sameness and contradiction judgement — because those calls are what make the product's guarantees real. Answering is one call. No multi-pass answering, no debate, no retries (`Q508`).
- **BECAUSE: POSITION.** `P§2`'s check and `P§9`'s supersession are both write-path mechanisms the position requires; `P§8`'s no-retry rule constrains the read path. The asymmetry falls straight out of the position.
- **REJECTED:** Multi-agent debate at roughly 3× calls and latency with capped rounds. It wins on correction quality for reasoning tasks. It spends on the read path, which is where this product least wants to spend — a user waiting for an answer is paying, and `P§8` would rather abstain than deliberate.
- **COST:** Ingestion cost is high and visible (`Q303`); answer quality has no second chance (`Q508`).
- **CONFIDENCE:** high

---

### Q580 — When should extraction occur, and how much latency may memory creation add to the interaction?

- **DECISION:** After the response, asynchronously, adding **zero** latency to the interaction — with the explicit consequence that freshness is not guaranteed, the lag is bounded and reported, and an unprocessed transcript is searchable and labelled as such (`Q389`).
- **BECAUSE: ENGINEERING (E3)**, with the labelling requirement from **POSITION** (`P§8`'s honesty about what Kivi has).
- **REJECTED:** A background pipeline with scheduling, batching, completion semantics, and freshness guarantees underspecified (the surveyed answer). The four underspecified things are exactly what a reviewer importing a corpus needs to know: when is ingestion done? This system must answer that precisely — `RUN.md` needs a "processing complete" signal, or a reviewer will query a half-ingested store and get wrong results.
- **COST:** As `Q62`. And a concrete operational requirement the position never mentions: **the import must expose completion status**, or the whole evaluation is racy.
- **CONFIDENCE:** high

---

### Q593 — F8 — Prompt-token footprint as the cost boundary (D13, D19, D25)

- **DECISION:** Rejected as the boundary. Cost is reported **whole**: extraction, exclusion classification, merge and contradiction judgement, embeddings, indexing, storage growth, traces, and confirmation-prompt generation — not just the prompt tokens of the answering call.
- **BECAUSE: ENGINEERING (E2)**, and the inventory's own note is the argument: "Including extraction, summarization, embeddings, indexing, storage, corrections, traces, and confirmation prompts could change system economics." For this design it certainly does — ingestion dominates.
- **REJECTED:** Prompt-token footprint at answer time. It wins on comparability with published token-efficiency claims. It is the measure that makes extraction-heavy architectures look cheap by excluding the extraction.
- **COST:** This system's reported cost will be substantially higher than any figure computed the conventional way, and that gap needs explaining every time the number appears.
- **CONFIDENCE:** high

---

### Q612 — When a successor instance takes over, what should count as successful memory transfer?

- **DECISION:** Not applicable as posed (`Q594`, `Q613`). The analogous real test is the brief's own: after importing a **foreign corpus**, can Hey Kivi answer questions grounded in that user's history, show which memories and sources produced each answer, and refuse to invent? That is the transfer test that matters, and it is the second stage of the brief's evaluation.
- **BECAUSE: ENGINEERING (E2).** The brief defines the test; the position defines what a good answer looks like (`P§8`).
- **REJECTED:** Byte-copy completeness. Rejected by the surveyed source too, for the right reason.
- **COST:** The real test is run by someone else on data I cannot see, so my own evaluation cannot predict it (`Q370`).
- **CONFIDENCE:** high

---

### Q651 — What should count as memory quality: task success and efficiency, faithful representation, user-confirmed truth, safe non-use, or some combination?

- **DECISION:** A combination, ordered: **safe non-use** (nothing retained or disclosed that should not have been) → **faithful representation** (memories match their sources; citations resolve) → **user-confirmed truth** (corrections stick; confirmed memories are honoured) → task success. Efficiency is reported, not optimised.
- **BECAUSE: POSITION.** `P§AppC`'s seven claims map onto the first three almost exactly: claims 1, 2, 7 are safe non-use; claims 3, 5 are faithful representation; claim 6 is user-confirmed truth; claim 4 is both 1 and 2.
- **REJECTED:** Inferring memory quality from downstream task success (the surveyed answer, and the field norm). It wins on measurability and on being the thing users actually care about. It cannot distinguish a system that succeeded because it remembered from one that succeeded because it guessed well — and it is blind to safe non-use entirely.
- **COST:** As `Q41` — no measure of whether the product is good, only whether it is trustworthy.
- **CONFIDENCE:** high

---

### Q679 — Should recent experience and durable knowledge share one representation, or should fidelity and access differ by timescale?

- **DECISION:** One representation. No hot/warm/cold tiering. Timescale affects **standing** (decay, `Q176`) and **ranking** (recency), never fidelity or access path.
- **BECAUSE: POSITION.** `P§4`'s axes are type and tier; timescale is not a third axis. A tiered-by-age store would mean a memory's accessibility depends on its age independent of its tier, which cuts across `P§4`'s two-axis model.
- **REJECTED:** Three tiers — hot in-memory cache, warm full-fidelity episodic vectors, permanent semantic graph. It wins at scale and is a sound engineering design. At a few hundred memories the hot tier has nothing to cache and the cold tier has nothing to demote to (`Q691`).
- **COST:** As `Q321` — no scale path; every query touches the one store.
- **CONFIDENCE:** high

---

### Q696 — Should thresholds be tuned on target data, borrowed as universal defaults, or calibrated without benchmark exposure?

- **DECISION:** Calibrated on the **development corpus** I generate, declared explicitly in configuration, reported with sensitivity analysis, and **never tuned on the reviewer's corpus** — which I cannot see anyway. The evaluation reports how results change across a range, not a single tuned value (`Q492`, `Q833`).
- **BECAUSE: POSITION.** `P§AppB`: parameters "need corpus data before they can be set honestly." The word *honestly* is doing the work — it licenses calibration on available data and forbids presenting a tuned value as a principled one.
- **REJECTED:** Borrowing universal defaults and claiming percentile rules transfer without retuning (the surveyed answer). It wins on generalisation claims and is attractive here precisely because the reviewer's corpus is unseen. The claim that thresholds transfer is exactly the claim that cannot be checked, and asserting it would be the overclaiming `P§AppC` guards against.
- **COST:** Thresholds calibrated on a self-generated corpus will be wrong for the reviewer's, and the sensitivity report is the only mitigation (`Q370`).
- **CONFIDENCE:** high

---

### Q700 — When a trial produces only sparse success/failure evidence, what should carry credit assignment into the next trial?

- **DECISION:** Nothing — there are no trials and no credit assignment (`Q494`, `Q508`). The analogous mechanism, the only one this product has, is the **user's correction**, which carries forward as a suppression (`Q506`).
- **BECAUSE: POSITION.** `P§9` makes the user the source of corrective signal; `P§4` gives no tier to a self-generated reflection.
- **REJECTED:** An LLM-generated natural-language reflection identifying likely mistakes. Wins for self-improving agents; is `Q707`'s rejection.
- **COST:** As `Q12` — no learning from performance.
- **CONFIDENCE:** high

---

### Q710 — What form should evaluation feedback take before reflection?

- **DECISION:** Not a scalar. Evaluation feedback is a **structured finding** — which claim failed, on which case, with the transcript, the trace, and the memory state — reported for human action (`Q425`). There is no reflection step to feed.
- **BECAUSE: POSITION.** `P§AppC`'s claims are pass/fail with evidence, not scores; `Q425` rejects automatic repair, so feedback goes to a person.
- **REJECTED:** Reducing evaluation to a scalar or binary reward. It wins for automated loops. A scalar cannot express "an excluded-category candidate reached storage," which is the failure that matters most.
- **COST:** Evaluation output is verbose and needs reading (`Q425`).
- **CONFIDENCE:** high

---

### Q712 — When test evidence is noisy, which evaluator error should the system prefer?

- **DECISION:** **Prefer false negatives over false positives**, everywhere, and this is the system's general error-preference rule: prefer dropping a good candidate to storing a bad one (`Q307`); prefer abstaining to answering (`Q04`); prefer treating two memories as distinct to merging them wrongly (`Q449`); prefer failing loudly to degrading quietly (`Q183`).
- **BECAUSE: POSITION.** `P§8`: "A fluent invented answer is worse than no answer." `P§2`: a hard exclusion list. Both are statements that the false positive is the worse error, and every gate in the system inherits it. **This is arguably the single most pervasive design principle in the whole set, and the position never states it as one** — it is implicit in every section. Worth naming explicitly in the README.
- **REJECTED:** Preferring false positives, on the reasoning that a wrong inclusion can be corrected later. It wins when correction is cheap and inclusion is valuable — a recommender, a search engine. Here a wrong inclusion can be a retention breach, which correction cannot undo.
- **COST:** Systematically lower recall, lower answer rate, and more duplicate memories than a system tuned the other way. Every one of those is visible in the evaluation and is a deliberate choice.
- **CONFIDENCE:** high

---

### Q716 — When the system is wrong but its evaluator says "pass," what recovery path should exist?

- **DECISION:** There is no in-loop evaluator to be wrong (`Q704`). The analogous case — the evaluation passes a claim that is actually violated — is handled by **sampled human inspection** (`Q429`) and by the fact that the most important claims are checked against the **database and logs** rather than against model output: an excluded-category memory in the store is a fact, not a judgement.
- **BECAUSE: POSITION.** `P§2`'s drop log exists so the boundary is "demonstrable rather than claimed," which means checkable mechanically.
- **REJECTED:** Relying on the evaluator's pass with no post-pass monitoring. The surveyed system's documented outcome — prematurely returning an invalid submission — is the cost.
- **COST:** The mechanically-checkable claims (1, 2, 4, 6, 7) are strong; the judgement-dependent ones (3, 5) rest on sampling. That asymmetry should be stated when reporting.
- **CONFIDENCE:** high

---

### Q719 — How should executable outputs be contained before evaluation?

- **DECISION:** Not applicable — nothing executable is generated or run (`Q237`). The only analogous containment concern is that the reviewing agent runs this system on **their** corpus with **their** credentials, so the system must not make undeclared network calls beyond the named model provider, and `.env.example` must name every variable precisely.
- **BECAUSE: ENGINEERING (E2).** The brief: "If an LLM key is required, name the environment variable precisely and include an .env.example. Do not commit private credentials."
- **REJECTED:** N/A.
- **COST:** None.
- **CONFIDENCE:** high

---

### Q720 — When environmental conditions are nondeterministic or externally coupled, should test-driven self-evaluation remain the feedback mechanism?

- **DECISION:** There is no self-evaluation. The evaluation handles nondeterminism by pinning models and temperature for extraction (`Q493`), fixing the corpus and its order (`Q76`), reporting the memory state each assertion ran against (`Q301`), and treating generation variance as expected — which is why claims are graded on citation resolution and support rather than on exact text.
- **BECAUSE: ENGINEERING (E2)**, with `P§AppC`'s provability requirement forcing the claims to be phrased so that generation variance cannot flip them.
- **REJECTED:** Test-driven self-evaluation. Its own source identifies the limitation and offers no alternative; this system's alternative is to make the claims structural rather than textual.
- **COST:** Claims that depend on wording — whether an abstention was *good* — cannot be made structural and stay manual (`Q45`).
- **CONFIDENCE:** high

---

### Q742 — Where should compute and latency be paid: writing, retrieval, or answer generation?

- **DECISION:** Writing. Heavily and deliberately (`Q513`). Retrieval is cheap (two index queries plus a join). Generation is one call. Ingestion carries extraction, exclusion classification, per-candidate sameness and contradiction judgement, and embedding.
- **BECAUSE: POSITION.** Every write-path cost buys a `P§AppC` claim: the exclusion call buys claim 1, the source-separation structure buys claim 2, per-candidate judgement buys supersession and claim 6's stability, evidence accumulation buys claim 3. None of them improves an answer directly; all of them make a promise real.
- **REJECTED:** One ingestion pass with immediate synthesis, then a planning pass and bounded parallel retrieval, optimising total efficiency. It is a good balance and it is cheaper. It buys no guarantees.
- **COST:** As `Q303` — ingestion is expensive, visibly, and the cost report will invite the question "why so many calls?" The answer is the seven claims.
- **CONFIDENCE:** high

---

### Q743 — What failure should system optimization treat as most costly?

- **DECISION:** Impermissible retention first, impermissible disclosure second (`Q585`, `Q272`). Not accuracy, not distractor robustness, not runtime.
- **BECAUSE: POSITION.** `P§2` and `P§5` are absolute; `P§3` makes the boundaries the reason anyone trusts the product.
- **REJECTED:** Optimising answer F1, distractor robustness, retrieval tokens, and runtime. It wins as a research target and is measurable. It treats the failures this product exists to prevent as invisible.
- **COST:** As `Q272` — a system that scores worse on every published metric.
- **CONFIDENCE:** high

---

### Q795 — What scale and density should determine clustering parameters?

- **DECISION:** Not applicable — no clustering (`Q766`, `Q802`). The analogous parameters that do exist — evidence threshold N, decay window, hypothesis expiry window, top-k, contradiction candidate count s, confirmation budget — are all set from the development corpus with sensitivity reported (`Q696`), and are listed as open in **Section A**.
- **BECAUSE: POSITION.** `P§AppB` defers exactly these.
- **REJECTED:** Fixed clustering settings. Wins in a clustering design; note the surveyed values (min_cluster_size=2 at thread level) are tuned to a specific corpus and would not transfer — the same problem `Q696` names.
- **COST:** As **Section A** — six unset parameters.
- **CONFIDENCE:** high

---

### Q796 — Against what alternatives should the system be compared to establish that its headline architecture matters?

- **DECISION:** Against **internal ablations only**, not external systems (`Q431`). Specifically: retrieval without the tier re-rank; retrieval without the lexical leg; the disclosure filter disabled; the exclusion check disabled; suppression disabled. Each ablation is designed to show that a specific mechanism produces a specific claimed behaviour — and several of them will *improve* accuracy while breaking a claim, which is the most informative result the evaluation can produce.
- **BECAUSE: POSITION.** `P§AppC` asks each claim to be provable, and an ablation that removes the mechanism is the cleanest proof that the mechanism is what does it.
- **REJECTED:** Comparing against named external memory systems (FullText, NaiveRAG, A-Mem, LightMem, Nemori). It wins on credibility with a technical reviewer and would situate the work. `Q431`'s objection stands: any of them would win on accuracy by doing what this position forbids, and reporting that without heavy framing would misrepresent the trade. **The ablation showing "disabling the exclusion check improves recall" is the honest version of that same comparison, contained within the system.**
- **COST:** No external reference point for retrieval quality (`Q431`).
- **CONFIDENCE:** high

---

### Q811 — How much compute at recall time?

- **DECISION:** Very little: deterministic date parsing, two index queries, a join, rank fusion, a sort, a filter, and one generation call. No LLM in retrieval, no reranking, no iterative fetching (`Q212`, `Q542`).
- **BECAUSE: POSITION** for excluding the LLM from retrieval (`P§8`'s explicability); **ENGINEERING** for the rest.
- **REJECTED:** Heavier recall-time computation. It wins on quality (`Q162`). This design deliberately front-loads cost to the write path (`Q742`).
- **COST:** As `Q26`/`Q162` — ranking quality capped.
- **CONFIDENCE:** high

---

### Q841 — When a task repeats exactly, should its earlier episode be retrievable during evaluation?

- **DECISION:** Yes — and this is a deliberate inversion of the surveyed answer. Kivi's whole purpose is that a repeated situation is answered from what was said before (`P§3`: "you said this once, so say it once"). Excluding the earlier episode would test a capability the product does not claim. What the evaluation **must** exclude instead is **leakage from the question into memory**: an evaluation question must never have been ingested as a transcript.
- **BECAUSE: POSITION.** `P§3`'s value claim makes repetition the point, not a confound.
- **REJECTED:** Excluding episodes with the same task id. It is correct for an agent-skill benchmark, where retrieving the identical prior solution is cheating. Here it would be removing the product.
- **COST:** The evaluation must carefully separate corpus transcripts from evaluation questions, and any overlap invalidates results silently. This is a real and easy mistake (`Q370`).
- **CONFIDENCE:** high

---

### Q842 — What latency tradeoff is acceptable for memory guidance?

- **DECISION:** Near-zero added latency on the interactive path (one retrieval, one generation call, `Q811`); substantial latency accepted on the **ingestion** path, where it is not user-facing (`Q742`). A corpus import may take minutes; an answer may not.
- **BECAUSE: ENGINEERING (E3)**, with `P§8`'s user-cost framing extended: the position prices the user's attention explicitly ("A prompt is a cost paid by the user"), and waiting is the same kind of cost.
- **REJECTED:** Accepting substantial wall-clock overhead on the interactive path because success rises — the surveyed answer, roughly 395s versus 215s. It wins when task success is what the user wants and they will wait. For a voice-first product where "Hey Kivi" is meant to feel immediate, it is not available.
- **COST:** Ingestion of ~500 transcripts takes real time and the reviewer must be told how long and given a completion signal (`Q580`).
- **CONFIDENCE:** high

---

### Q839 — When the memory-guided system is wrong, what should correct the stored cause rather than just the current action?

- **DECISION:** The user's action on the **memory**, not on the answer. Correcting an answer corrects nothing; correcting the memory behind it corrects everything downstream, and the suppression stops it re-forming. Inline correction during a request therefore writes through to the entity or memory rather than patching the response (`Q50`, `Q557`).
- **BECAUSE: POSITION.** `P§8`: "*No, Priya's at Northwind now*… should update the entity without ceremony." The object of the correction is the entity, not the reply. And `P§9`: "deleting the row is useless… The action must record a suppression that the extractor respects going forward."
- **REJECTED:** Storing failed episodes without any correction, editing, rollback, suppression, or feedback path (the surveyed answer). It wins on build cost. It is the failure `P§9` names: corrections that do not stick.
- **COST:** As `Q506` — an accumulating suppression list whose matching scope is undetermined.
- **CONFIDENCE:** high

---
---

# A. POSITION GAPS

Questions the position document does not determine, and which no engineering constraint settles either. **These are yours to decide by hand.** I have not decided them; where a resolution above depended on one, it says so and leaves the value open.

They fall into four kinds. The parameters are the least interesting and the most often mistaken for the hard part. The last group is where the real exposure is.

## A1 — Parameters the position explicitly defers

`P§AppB` names these as "parameters; they need corpus data before they can be set honestly." That is a correct instinct and it leaves eight numbers undetermined:

1. **Evidence threshold N** — how many independent transcripts constitute an observation. `P§4` says "a pattern across multiple transcripts"; multiple is not a number. Low N produces observations on thin evidence that Koottu will surface embarrassingly; high N means almost nothing reaches the observed tier.
2. **Observation decay window** — how long without re-observation before an observation stops being surfaced. `P§9` says "Behaviour from six months ago should not be presented as who you are," which is an illustration, not a setting.
3. **Hypothesis expiry window** — how long an unconfirmed question survives before being dropped.
4. **Retrieval top-k** and its token budget.
5. **Contradiction candidate count s** — how many similar existing memories each new candidate is checked against at write time. Directly trades ingestion cost against missed contradictions.
6. **Confirmation budget: the cap.** `P§AppB` defers "confirmation budget size" by name.
7. **Confirmation budget: the selection function.** `P§8` says "spent on the highest-value uncertain memories" and does not define value. This is the most product-critical of the eight — it governs how fast the stated tier grows, and therefore how often Kivi is permitted to act confidently rather than merely observe.
8. **Abstention broadening bound** — how far a failed query may broaden before it must abstain.

## A2 — Boundaries the position draws but does not locate

These are places where the position states a distinction clearly and gives no test for applying it. A classifier has to be built against each one, and where it sits is a judgement call, not a derivation.

9. **Implied relation vs. plausible inference.** `P§4` requires entity relations to be extracted; `P§2` forbids "plausible inference." *"Priya at Acme wants the deck by Friday"* → *Priya is associated with Acme* is clearly permitted. *"I'll handle Priya myself this time"* → *Priya requires careful handling* is clearly forbidden. The line between them is where extraction lives, and the position does not draw it.
10. **Work-behaviour hypothesis vs. character characterisation.** `P§AppA`'s live hypothesis — *"rewrites the Atlas pricing rationale repeatedly — does she disagree with the pricing?"* — is permitted. *"Is she conflict-avoidant?"* is forbidden by `P§2`. These are closer than the document admits, and Daari's entire output sits between them.
11. **Durable vs. transient.** `P§3`'s test is "the **durable**, work-level things you would be annoyed to have to repeat." *"I'm in a meeting"* is transient; *"I sign off Best, Meera"* is durable; *"the review is Thursdays now"* is somewhere between. Since stated memories never decay (`Q178`), a transience misjudgement is permanent.
12. **Suppression matching scope.** `P§9` requires a suppression "that the extractor respects going forward" and does not say what it matches on — the exact fact, a paraphrase class, a pattern, or a subject. Too narrow and the belief regrows in different words; too broad and legitimately new facts are silently blocked. This is the single most consequential undetermined rule in the set, because it is the mechanism the position calls "easy to get wrong."
13. **Type boundaries.** `P§4` fixes three types and does not adjudicate the hard cells. *"The Atlas review is on Thursdays now"* — recurring event: episode or preference? *"Arun owns the backend"* — entity relation or stated preference about allocation? The corpus will be full of these.

## A3 — Things the product needs that the position never mentions

14. **A confirmation step on `Forget`.** `P§8` insists corrections are "cheap and inline… without ceremony"; `P§9` makes `Forget` irreversible. Cheap plus irreversible is a bad combination and the position does not reconcile it.
15. **Entity-scoped forgetting.** "Forget everything about Priya" is an obvious user request. `P§9`'s actions are all per-memory. There is no affordance and no stated position on whether there should be.
16. **Transcript deletion.** The user can change every belief and cannot touch a single transcript (`P§9` requires transcripts for provenance; nothing grants control over them). "Delete this dictation" has no answer.
17. **Remedy for a wrong disclosure.** `P§8` and `P§9` are careful about wrong *beliefs*. Once Kivi has *said* something it should not have, the product offers nothing. There is no equivalent of `Forget` for a disclosure.
18. **Where developer diagnostics live.** `P§8` builds one surface for both audiences and `P§9` says "No developer console anywhere in this." Token counts, model latencies, embedding distances, queue depth, and quarantine state genuinely do not belong in a user's Why panel, and the brief separately requires an engineer to inspect why memory did or did not affect a result. The position forecloses the obvious answer without supplying another.
19. **Trace retention.** Every answer persists a trace (`P§8`); nothing in `P§9`'s lifecycle applies to traces. They grow forever, and the brief measures database growth.
20. **Memory-surface navigation at scale.** `P§9` specifies three tier-grouped lists. At a few hundred memories that is a long scroll with no search, filter, or grouping specified — and the obvious remedies (topics, clusters, a summary view) are the ones `P§2` and `Q766` rule out.
21. **At-rest encryption of the transcript store.** The position's strongest privacy claim concerns what is *not kept*; the store that holds everything it refuses to remember has no stated protection.
22. **Injected instructions in application context.** `P§5` structurally prevents third-party content reaching the write path. It still reaches the *generation* path, where hostile text can influence an answer. The position does not consider it.

## A4 — Choices the position defers to work that does not exist yet

23. **Which three Hey Kivi tools.** `P§AppB` says the tool set "follows from the use cases" and names draft/reply, schedule-or-reschedule, and recall/search as "likely candidates." The use cases are not written. Note specifically that **schedule/reschedule has no environment to act on** in a replayed-transcript client (`Q237`), which makes it the weakest of the three as a demonstration.
24. **The entity relation vocabulary.** A closed set is required (`Q849`); which five or six relations it contains is a guess made before the corpus exists, and `P§AppA`'s world is small enough that it may not generalise to the reviewer's corpus.
25. **Daari invitation detection.** `P§6` treats *"what do you think?"* as a recognisable invitation. Recognising it is intent classification on free text, with false positives (Kivi volunteering a hypothesis unasked) and false negatives (refusing one that was invited). The position gives no rule and the failure is asymmetric — a false positive is a breach of the Anbu promise.
26. **When an observation is timely.** `P§8` requires confirmation prompts to "appear at natural moments." Koottu observations have no equivalent rule, so relevance is the only gate on surfacing them, and Kivi will raise patterns at moments that are accurate and unwelcome.

---

# B. POSITION CONFLICTS

Places where two parts of the position imply opposite answers, or where a decision the document clearly wants is incompatible with something else it says. I have not softened these.

---

## B1 — "Kivi doesn't keep other people" is false as written

> **§1, principle 2:** "**Non-retention of others.** Kivi encounters other people constantly — in messages you're replying to, in documents you're summarising. It works with them and does not keep them."

> **§5:** "What survives is the work-level residue about *your* world, derived and not copied: ***Priya is the Acme client contact.***"

> **§7:** "Names, project nouns, spellings… ***Priya Raghavan***, not *Prea Raghavan*."

Kivi keeps Priya's full name, her employer, her role, her project association, and the canonical spelling of her name. She did not agree to any of it. The retained set is small and defensible; the principle as stated is not true, and the first page of the README is where `§1` says these principles go.

**What has to change:** either the principle is restated as non-*characterisation* of others rather than non-retention, or `§7`'s spelling requirement and `§5`'s worked example have to give up the name. The second is not survivable — dictation needs the lexicon. So the principle is the thing that moves.

---

## B2 — The transcript store holds everything the memory store refuses

> **§5:** "Third-party content enters the context window. It does not enter the write path. This is a structural rule, not a filter applied afterward." … "**Kivi drops:** everything about Priya's mother, Priya's absence, and Priya's apology."

> **§9:** "**Every memory shows its provenance.** Not a category label — the actual transcript, with a date, that produced it."

Provenance requires the transcript to be kept. The transcript contains Priya's mother's hospitalisation. So the sentence "Kivi drops everything about Priya's mother" is true of the memory layer and false of the system, and the "read, not kept" marker in `§5` — the position's "single most demonstrable trust claim" — is demonstrating something narrower than its wording claims.

This is the sharpest conflict in the document. Everything else is a matter of degree; this one is two requirements that cannot both be fully satisfied.

**The options, none of which the position takes:** keep transcripts but redact third-party content in the stored copy (weakens provenance to "here is a redacted version of what you said"); keep transcripts under separate encryption with a separate retention policy (does not remove the contradiction, reduces the exposure); or restate the claim as "did not enter memory" everywhere it currently reads as "was not kept."

---

## B3 — The drop log is a record of the thing it refuses to record

> **§2:** "Kivi never infers or stores: health, mood or emotional state…"

> **§2, three lines later:** "Dropped candidates are logged with the reason. The extraction log for any transcript can show: *3 candidates extracted, 1 dropped — excluded category: emotional state.* This is how we prove the boundary is real rather than claimed."

A row reading `transcript 412 — dropped — emotional state` is a durable record asserting that something about the user's emotional state was present in transcript 412. It is not content, and it is not nothing. The proof mechanism is made of small amounts of the thing being refused.

This is survivable — the log is metadata, reason-coded, never content — but it is a genuine tension and a sharp reviewer will find it. It is also unavoidable: `§AppC` claim 1 requires the drop to be demonstrable, and an undemonstrable boundary is the one `§2` says it refuses to be.

---

## B4 — Anbu is the default, and Anbu is where the product is invisible

> **§6:** "The dial is an explicit setting. **Default Anbu.**"
> **§6, Anbu:** "Says: the result. Nothing else. **Never:** points out a pattern, questions your choice, guesses a reason."

> **§1:** "When a friend tells you something they're insecure about, you hold it. You don't repeat it back to them at dinner to demonstrate that you were listening."

> **§3:** "**Why someone trusts it enough to keep using it:** because every belief is attributable, the boundaries are demonstrable rather than promised…"

In the default mode, Kivi applies stated memories silently and says nothing about anything else. A user can use the product for a week and reasonably conclude it has no memory — the value arrives as things not going wrong, which is exactly the kind of value nobody notices. Demonstrability requires the user to open the Why panel; silence gives them no reason to.

The document is aware of this and answers it in one sentence:

> **§6:** "When Anbu withholds something, the interface shows a single quiet affordance rather than the content itself: *'Kivi noticed something here.'*"

That one affordance is carrying the entire discoverability of the product's distinguishing behaviour. It is a sentence where the rest of the document would put a section. Either it deserves that weight and should be designed as a primary surface, or the default should be Koottu — and `§6` gives no reason for Anbu-as-default beyond the general principle of restraint.

---

## B5 — `Forget` cannot mean forget

> **§9:** "Actions per entry: … **Forget** (remove + suppress)."

> **§9:** "'That's not me anymore' demotes and blocks re-derivation. This matters and is easy to get wrong: deleting the row is useless, because the same pattern will regrow from the same transcripts within a week. The action must record **a suppression that the extractor respects going forward.**"

A suppression the extractor can respect must be specific enough to match the thing it suppresses. So after `Forget`, the system retains a durable record describing the belief the user asked it to forget — plus the source transcripts, which are never deleted (`B2`).

"Forget" is therefore the one action in `§9` whose human-terms name misdescribes what happens. The position is explicit that the actions are "phrased in human terms rather than database terms," and here the human term promises more than the mechanism delivers.

**This is not fixable by mechanism** — the alternative is corrections that do not stick, which `§9` correctly identifies as fatal. It is fixable only by naming and by what the interface says.

---

## B6 — Extraction is required to resolve context it is forbidden to see

> **§5:** "Third-party content enters the context window. **It does not enter the write path.**"

> **§4** (every example) and **§9** (the memory surface shows entries to a user with no conversational context) require memories to be standalone, context-independent statements: *"On 12 March the user moved the Atlas review from Tuesday to Thursday."*

> **§5, worked example — the dictation:** "Reply to Priya saying that's completely fine, we'll move it to the following Tuesday, and tell her not to worry about the notice."

Read that dictation alone, without Priya's message. *Move what?* *From when?* The retained memory the position claims — *Atlas review moved from Thursday to the following Tuesday* — is **not derivable from the dictation**. Both the subject and the original date come from the third-party message the write path is forbidden to see.

The position's own worked example, the one written to demonstrate the rule, cannot be produced under the rule.

**The options:** allow the extractor to see application context and enforce the boundary at the candidate check instead of structurally (weakens `§5` from a structural rule to a filter — the thing it explicitly says it is not); or accept that anaphoric and deictic dictations extract poorly and let the `§5` example stand as aspirational; or pass a narrow, derived, non-personal digest of application context to the extractor (a middle path the document does not consider, and which needs its own boundary argument).

This is the conflict most likely to surface as a concrete failure during the build.

---

## B7 — Two opposite mechanisms for what looks like one idea

> **§7:** "two separate retrieval paths, not one path with a filter. The dictation path can only query the entity and lexical store. It has **no access** to the observation or hypothesis tables at all. **Not filtered out — structurally unable to load them.**"

> **§6:** "The dial governs disclosure, **not retrieval**. Kivi always retrieves everything it has. The dial decides what may be *said*."

For the surface boundary, filtering is condemned and structure is required. For the permission boundary, structure is condemned and filtering is required. Both positions are argued well and they are argued against each other.

They are reconcilable — a transcription contract is a promise about what the product *is*, a dial is a promise about what Kivi *says* — but the document never notices it needs to reconcile them, and a reader comparing `§6` and `§7` will read it as inconsistency. It needs one sentence somewhere and does not have it.

---

## B8 — The promotion mechanism is rate-limited to near-uselessness

> **§4:** "**Nothing self-promotes.** An observation does not become stated because it was seen twenty times. It becomes stated when the user confirms it. Twenty is still a pattern."

> **§8:** "Confirmation prompts are budgeted — **a small cap per week**, spent on the highest-value uncertain memories. A prompt is a cost paid by the user." … "the person must not become the administrator of the system."

Promotion is the only route from observed to stated. Stated is the only tier Kivi may act on (`§4`: "Treat as true. Use freely"; observed: "Never as a rule"). Promotion requires a prompt. Prompts are capped at a few per week.

So the tier that drives Kivi's behaviour grows at a few facts per week, and only for facts the user happens to be asked about at a relevant moment. Everything else stays permanently in a tier Kivi is forbidden to act on. The observed tier — which is where most of what Kivi learns will live — is, by construction, mostly inert.

Both halves are right on their own terms. Together they mean the memory system's most valuable output is throttled to a trickle, and the position does not acknowledge the arithmetic.

---

## B9 — §3 rules out insight; §6 builds a mode for it

> **§3:** "**Where the value is created:** in what you no longer have to re-explain. Every use case we choose should be one where the cost being removed is *repeating yourself*. **Not insight. Not advice.** Not being understood at a deep level."

> **§3:** "Every use case we select gets tested against one question — *does this remove a re-explanation, or does it deliver an insight?* **If it's the second, it doesn't ship in v1.**"

> **§6, Daari:** "*I'll tell you what I think it means.* You tell me if I'm wrong."
> **§6, worked example:** "You've moved it three times, and each version rewrites the pricing rationale rather than the numbers. **Is the disagreement with the pricing itself?**"

Daari delivers insight. That is its entire function. By `§3`'s own shipping test, Daari does not ship in v1.

The document contains the answer to this and does not apply it — `§6` makes Daari a per-request invitation whose output is not stored, which arguably makes it a *response mode* rather than a *use case*. But `§3`'s test is stated as absolute and `§6` is a fully specified third mode with a promise, a worked example, and a place in the dial. One of them is overstated.

---

## B10 — §2 excludes characterisation; §4 and §AppA build one

> **§2:** "Kivi never infers or stores: … **any characterisation of the person's competence or character.**"
> **§2:** "'Meera avoids conflict with senior stakeholders' is not a fact with a source. It is a characterisation assembled from fragments."

> **§4:** "Instead: `"Does the user disagree with the Atlas pricing rationale?" — unconfirmed`."
> **§AppA:** "**Live hypothesis:** rewrites the Atlas pricing rationale repeatedly — does she disagree with the pricing?"

*Does she disagree with the pricing?* is a proposed belief about her professional judgement, assembled from fragments across multiple transcripts, with no single dictation that proves or disproves it. It satisfies `§2`'s own definition of a characterisation in every respect except that it ends in a question mark.

The interrogative form is the defence, and `§4` makes it explicitly: "The grammar of storage enforces the epistemics." That is a real mechanism and it does real work. But it is a formatting rule applied to content `§2` excludes by category, and the position leans on it harder than one sentence can bear. If the interrogative form is sufficient, then *"Is Meera conflict-averse with senior stakeholders? — unconfirmed"* is also storable, and `§2` has been defeated by punctuation.

**What is missing:** `§2`'s exclusion is by category; `§4`'s hypothesis tier is by form. Nothing in the document says which wins, or states that hypotheses are additionally subject to the category exclusions. They need to be, and it is not written down.

---

# C. DECISIONS THAT ARE ACTUALLY ONE DECISION

Fifteen clusters. Answering the parent settles every child. Together they account for roughly 470 of the 863 questions — a little over half the inventory is fifteen decisions wearing different clothes.

---

**C1 — Retrieval is separated from disclosure.** *(Parent: `Q21`)*
`Q36` `Q37` `Q119` `Q194` `Q268` `Q285` `Q290` `Q318` `Q327` `Q351` `Q387` `Q454` `Q472` `Q488` `Q529` `Q577` `Q609` `Q698` `Q736` `Q790` `Q812` `Q826`
Twenty-two questions, one answer, forced by `§1` principle 1 and `§6`. Every surveyed system answers "no separation"; this is the product's defining structural commitment. Note `Q285`'s caveat: post-filtering is right here and would be a security bug in a multi-user system.

---

**C2 — There is one inspection surface, built for the person, showing four states.** *(Parent: `Q05`)*
`Q44` `Q56` `Q120` `Q136` `Q165` `Q195` `Q352` `Q367` `Q405` `Q455` `Q473` `Q543` `Q563` `Q631` `Q646` `Q663` `Q695` `Q737` `Q777` `Q827` `Q838`
Twenty-one questions. Forced by `§8`'s Why panel and `§9`'s memory surface. The uniformity of the gap in the inventory — nearly every source claims interpretability and specifies no user surface — is the strongest evidence that building it is a differentiator. See gap **A18**: it has no room for developer diagnostics.

---

**C3 — Tier is the epistemic axis, and it is categorical, not scalar.** *(Parent: `Q14`)*
`Q42` `Q48` `Q100` `Q113` `Q145` `Q149` `Q291` `Q324` `Q332` `Q519` `Q521` `Q537` `Q572` `Q628` `Q671` `Q725` `Q786` `Q800` `Q807`
Nineteen questions. Forced by `§4`. Everything about confidence scores, importance, salience, promotion, and how a memory may be used collapses into this. Its cost — no representation of partial belief — is paid nineteen times.

---

**C4 — Contradictions supersede, with history.** *(Parent: `Q13`)*
`Q03` `Q66` `Q88` `Q115` `Q117` `Q189` `Q205` `Q262` `Q281` `Q310` `Q323` `Q345` `Q361` `Q363` `Q369` `Q380` `Q522` `Q600` `Q640` `Q658` `Q684` `Q772` `Q785` `Q804` `Q820` `Q854`
Twenty-six questions. Forced by `§9`. Carries one unresolved weakness through all of them: facts that were *true in sequence* (Priya at Acme, then at Northwind) are modelled as corrections rather than as intervals, because validity ends are only recorded when a transcript states one.

---

**C5 — Corrections stick, via a suppression the extractor respects.** *(Parent: `Q15`)*
`Q22` `Q46` `Q49` `Q75` `Q190` `Q293` `Q368` `Q381` `Q506` `Q524` `Q557` `Q603` `Q608` `Q622` `Q738` `Q739` `Q758` `Q775` `Q791` `Q839`
Twenty questions. Forced by `§9`'s "easy to get wrong" paragraph. This is the mechanism no surveyed system has — the inventory repeatedly notes "no suppression or anti-re-derivation mechanism is described." It is also where conflict **B5** and gap **A12** live.

---

**C6 — Abstention is a designed result with a visible surface.** *(Parent: `Q04`)*
`Q27` `Q45` `Q58` `Q64` `Q67` `Q69` `Q135` `Q228` `Q249` `Q289` `Q319` `Q329` `Q353` `Q365` `Q392` `Q470` `Q474` `Q512` `Q578` `Q610` `Q647` `Q664` `Q756` `Q771` `Q813` `Q856`
Twenty-six questions. Forced by `§8`. Pay attention to `Q756`: the alternative designs are *better instrumented* than this one — they have a calibrated false-refusal rate and this does not, because rank fusion leaves no calibrated score to threshold on.

---

**C7 — Third-party content never reaches the write path.** *(Parent: `Q342`)*
`Q11` `Q20` `Q55` `Q61` `Q126` `Q271` `Q316` `Q356` `Q358` `Q478` `Q596` `Q745` `Q763` `Q788` `Q846`
Fifteen questions. Forced by `§5`. This is the single most architecturally consequential sentence in the position — it fixes the shape of the pipeline — and it is the source of conflict **B6**, the one most likely to bite during the build.

---

**C8 — A hard, code-enforced, category exclusion list.** *(Parent: `Q629`)*
`Q09` `Q169` `Q221` `Q305` `Q322` `Q442` `Q450` `Q573` `Q655` `Q726` `Q764` `Q779` `Q780` `Q801` `Q818` `Q851`
Sixteen questions. Forced by `§2`. `Q801` and `Q818` are the ones to read: the inventory says explicitly that the excluded thing (a persona summary of stable traits and preferences) is *load-bearing for preference questions*. This refusal has a measured cost.

---

**C9 — Only user-authored content is evidence.** *(Parent: `Q12`)*
`Q153` `Q198` `Q235` `Q240` `Q385` `Q459` `Q463` `Q494` `Q503` `Q634` `Q635` `Q644` `Q699` `Q707` `Q831` `Q840`
Sixteen questions. Forced by `§4`'s tier definitions. Consequence: no procedural memory, no reflection, no learning from Kivi's own output or performance. `Q153` is the uncomfortable one — accepted drafts are excellent, free evidence of preference, and are refused by an argument extended from `§8` rather than stated in the position.

---

**C10 — No summaries, no narrative, no aggregate profile.** *(Parent: `Q154`)*
`Q33` `Q323` `Q378` `Q384` `Q398` `Q399` `Q484` `Q539` `Q570` `Q575` `Q587` `Q624` `Q625` `Q761` `Q781` `Q816` `Q830` `Q850` `Q862`
Nineteen questions. Forced by `§4` (nothing without a tier) and `§2` (no profile). **This cluster's cost is cited more often in this document than any other**, and it is one decision: narrative, chronological, and broad questions have no artefact to answer from, and the raw-transcript fallback is doing more work than the position acknowledges.

---

**C11 — Decay and expiry by tier; nothing else changes with time.** *(Parent: `Q24`)*
`Q38` `Q51` `Q53` `Q57` `Q95` `Q137` `Q176` `Q178` `Q283` `Q312` `Q325` `Q407` `Q490` `Q525` `Q545` `Q565` `Q581` `Q602` `Q666` `Q686` `Q740` `Q773` `Q792` `Q806` `Q861`
Twenty-five questions. Forced by `§9`. Every one carries the same live objection: **the windows are unset** (gap **A2**, **A3**), and shipping decay before the corpus can calibrate it is the weakest link in `§9`.

---

**C12 — Ordering is deterministic and code-owned.** *(Parent: `Q26`)*
`Q02` `Q35` `Q77` `Q182` `Q193` `Q209` `Q212` `Q422` `Q487` `Q528` `Q638` `Q662` `Q674` `Q691` `Q733`
Fifteen questions. Forced by `§8`'s explicability requirement. `Q162` is the honest accounting: a tuned stack (rank fusion + MMR + a recency half-life + a threshold) would measurably beat this, and every component is rejected for a different reason.

---

**C13 — Ingestion is idempotent on the transcript, ordered by event time.** *(Parent: `Q08`)*
`Q19` `Q103` `Q180` `Q207` `Q375` `Q438` `Q559` `Q657` `Q667` `Q673` `Q683`
Eleven questions. Forced by `§AppC` claim 6 plus the reviewer-reproducibility constraint. Drags temperature 0, a pinned model, and model-identity-in-the-idempotency-key along behind it, which in turn makes every model upgrade a migration.

---

**C14 — One user, one pool, no sharing, no isolation machinery.** *(Parent: `Q273` / constraint `E1`)*
`Q61` `Q82` `Q121` `Q140` `Q276` `Q277` `Q284` `Q295` `Q296` `Q297` `Q476` `Q649` `Q769` `Q788`
Fourteen questions. Forced jointly by `§1` principle 2 and the brief's single-user corpus — the only cluster where position and scope point the same way, which is why it is the cheapest. `Q295` prices it: the surveyed efficiency gain from sharing was 59–61%, forgone entirely.

---

**C15 — Out of scope by build constraint.** *(Parents: `Q215` causal · `Q339` distributed consistency · `Q496` multi-agent debate · `Q400` branching · `Q131` training)*
Causal: `Q214` `Q216` `Q217` `Q218` `Q219` `Q220` `Q222` `Q223` `Q224` `Q225` `Q226` `Q228` `Q229` `Q231`
Consistency: `Q340` `Q344` `Q346` `Q347` `Q349` `Q350` `Q353` `Q354`
Multi-agent: `Q286` `Q287` `Q298` `Q300` `Q498` `Q500` `Q501` `Q502` `Q504` `Q507` `Q514`
Branching / instances: `Q401` `Q406` `Q595` `Q597` `Q604` `Q605` `Q612` `Q613` `Q614` `Q615`
Agent loops: `Q243` `Q244` `Q245` `Q249` `Q508` `Q510` `Q705` `Q706` `Q708` `Q711` `Q714` `Q715` `Q716` `Q718` `Q719` `Q720`
Roughly sixty questions, resolved by scope rather than by judgement. **They are marked so you can see at a glance which parts of this document are decisions and which are absences.** The inventory was built from 45 systems solving problems Kivi does not have; treating their questions as open would make the design look more considered than it is.

---

## What the clustering says

Fifteen decisions, each traceable to a numbered section of the position, cover more than half the inventory. Six of the fifteen come from `§4` and `§9` alone. That is the strongest available evidence that the position is doing real work — it is not a preamble that the architecture then ignores; it determines the majority of the decision space directly.

The corollary is less comfortable. Because so few decisions carry so much, each one's cost is paid many times over, and three of them are load-bearing in ways the document does not price:

- **C10** (no summaries) costs recall on narrative, chronological, and broad questions — and the brief's own example question is chronological.
- **C11** (decay) ships on two numbers nobody has yet.
- **C3 + B8** together mean the tier that drives behaviour grows a few facts a week.

Those three are where I would look first if the build starts to feel thin.
