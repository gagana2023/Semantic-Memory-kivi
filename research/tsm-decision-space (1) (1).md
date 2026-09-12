# TSM (Findings ACL 2026) — inverted

Paper: *Beyond Dialogue Time: Temporal Semantic Memory for Personalized LLM Agents*. Read as a decision space, not a result.
Kivi = `kivi-semantic-memory-position.md`.

---

## 1. DECISION INVENTORY

**Legend:** Q = the open question · A = TSM's answer · Rej = alternatives rejected or unconsidered · Asm = what the answer assumes · **K** = holds for Kivi?

### Intake — what enters

**D1 · When a turn arrives, what determines whether anything is written at all?**
A: Nothing. Everything extractable is extracted; the only gate is dedupe.
Rej: salience threshold; category exclusion; consent test; write-worthiness classifier.
Asm: benign single-user corpus; over-retention costs nothing; the metric only punishes missing facts.
**K: fails, hardest divergence.** Kivi §2/§5 put a *hard exclusion check and a third-party barrier on the write path*. Pushes you to add a stage TSM has no slot for: candidate → admissibility check → store-or-drop-with-reason. TSM's pipeline has no place to log a drop, because dropping is not a thing it does.

**D2 · Whose words count as evidence?**
A: User messages only, at construction (stated as an efficiency choice, App. A.1.1).
Rej: both speakers; speaker-weighted; provenance-tagged multi-source.
Asm: one channel, two parties, and the non-user side carries no facts about the user's world.
**K: fails in both directions.** Kivi's application context (Priya's Slack message) is non-user text that *must* be read to act and *must not* be written from. TSM excludes non-user text for cost; Kivi must admit it to the context window and bar it from the write path. Same knob, opposite justification — you cannot inherit their setting, only the position of it.

**D3 · What time does a memory carry?**
A: Semantic/event time, parsed from language, not dialogue time. The headline.
Rej: dialogue time; both, kept separately; interval-with-uncertainty; "no time".
Asm: every fact has one inferable, single-valued event time.
**K: partial.** Correct and valuable for episodes (*review moved to Thursday*). But Kivi's entities and stated preferences are largely atemporal — "signs off Best, Meera" has no event time, only a first-seen and a last-confirmed. TSM has one time model for one memory type; Kivi's two-axis grid needs time to mean something different per row. Pushes toward: event-time for episodes, validity-time for entities, confirmation-time for preferences.

**D4 · What is discarded?**
A: Duplicates. Nothing else.
Rej: redaction, category filtering, third-party stripping, minimisation.
Asm: the corpus is already safe to keep.
**K: fails.** Kivi's most demonstrable claim (App. C.1, C.2) is about what was *seen and not kept*. TSM gives no precedent for a discard path, so nothing about it can be borrowed.

### Representation

**D5 · What is a memory, structurally?**
A: Two tiers. Episodic = `(subject, relation, object, t)` in a TKG plus an LLM-written entity summary. Durative = LLM summaries over clusters ("topics") and over the underlying dialogue ("personas").
Rej: attributable atomic claims; raw spans with pointers; typed records with fixed fields.
Asm: lossy abstraction is acceptable because nobody will ask the system to justify a line.
**K: partially fails.** Kivi's schema (`type, tier, evidence_count, source_transcript_ids[], first_seen_at`) is a record; TSM's durative memory is prose. You can reconstruct which *entities* fed a cluster, not which *sentence* of a persona came from where. Pushes you away from LLM free-text summaries as the storage unit toward summaries as a *view over* attributable rows.

**D6 · Should inferred user traits be stored as durable, retrievable objects?**
A: Yes — `Persona_z` = LLM summary of "stable user traits, preferences, and behavioral patterns", written to store, embedded, injected into context.
Rej: infer at query time and discard; store as unconfirmed; store the evidence only; don't infer.
Asm: characterising the user is the point of personalisation, and is harmless.
**K: fails at the level of intent.** This is precisely the artefact Kivi §2 refuses to build — unverifiable, uncorrectable, and stored as durable belief. TSM's persona is Kivi's hypothesis tier with none of the guardrails: no question grammar, no expiry, no confirmation, no source. Pushes you to keep TSM's *aggregation machinery* (cluster → summarise) while inverting its *status*: the artefact is a candidate to be shown and confirmed, not a fact to be injected.

**D7 · Does a stored item carry epistemic status?**
A: No. A parsed fact, an entity summary and an inferred persona are the same kind of object with the same standing.
Rej: confidence scores; source tiers; asserted-vs-observed-vs-hypothesised.
Asm: downstream generation can be trusted to hedge appropriately, or hedging doesn't matter.
**K: fails.** The stated/observed/hypothesised axis is, per §4, "the entire product". TSM offers no precedent — it is the flattening Kivi names as the standard failure.

**D8 · What temporal granularity groups durative memory?**
A: Fixed one-month slices. Acknowledged in Limitations as possibly wrong, left to future work.
Rej: adaptive granularity by event density (named, not tried); multi-scale hierarchy; topic-driven boundaries; session-aligned.
Asm: histories span many months (LongMemEval_S: 30–40 sessions), and user states change on a monthly scale.
**K: likely fails.** A studio's cadence is a weekly review, a sprint, a project phase. A demo corpus spanning three weeks collapses to one slice, at which point clustering runs once over everything and "durative memory" degenerates to a single global summary. Pushes to: project/thread-scoped slices rather than calendar-scoped, or a much shorter fixed window.

**D9 · What signal groups mentions into a topic?**
A: GMM over embeddings of *entity names* within a slice (Eq. 4: `GMM(h^name_e)`).
Rej: cluster on entity summaries; on evidence text; graph community detection; user-declared project structure.
Asm: the name string is semantically informative — "Neptune Oyster", "lavender syrup", "gin & tonic" cluster because the words are related.
**K: fails.** Kivi's names are opaque codenames. *Atlas*, *Anbu*, *#design-review*, *Q3 pricing page* have no name-space geometry that puts Atlas near Priya near Thursday. Pushes hard toward clustering on the entity *summary* or on the graph edges — you already have a project structure the user declared; use it instead of inferring it.

**D10 · Is the knowledge graph itself returned as answer context?**
A: No — index only. Their own case study (App. A.2) says facts alone are "insufficient, point-wise, and instant"; raw turns carry the answer.
Rej: fact-as-context; graph-walk answering.
Asm: fluent answers need narrative text, not triples.
**K: holds, with an edge.** Useful and transferable. But note the consequence: the thing the user would find legible (the triple) isn't what the system reads, and the thing it reads (raw transcript chunks) is what Kivi's provenance UI wants to show anyway. Compatible.

### Conflict and change

**D11 · When new evidence contradicts stored evidence, what resolves it?**
A: An LLM compares the new fact against existing edges on semantics and time, then applies one of DUPLICATE / ADD / INVALIDATE / UPDATE, online, at write time.
Rej: keep both with disjoint validity and resolve at read; defer to user confirmation; last-write-wins; flag as contested.
Asm: contradiction means staleness; it can be settled without the user; a wrong resolution is cheap and recoverable.
**K: partially fails.** Kivi §9 requires supersession to be *auditable* and *reversible* — "the superseded version stays in history". TSM's INVALIDATE writes a time bound but there is no user-visible record of the judgement and no way to contest it. Pushes: keep the four-op vocabulary, add a resolution log and a revert.

**D12 · Is anything ever removed?**
A: No delete path. INVALIDATE closes a validity interval; the row stays.
Rej: forget; suppress; tombstone.
Asm: nobody will ask the system to unknow something.
**K: fails.** Kivi needs *Forget* and *That's not me anymore* as first-class ops.

**D13 · Does consolidation respect prior state?**
A: No. Sleep-time consolidation "reorganize[s] **all** entity mentions via GMM-based clustering and re-summarise[s]" — a full recompute from the mention set.
Rej: incremental update; honouring a suppression list; append-only snapshots.
Asm: the mention set is the ground truth and the summary is a pure function of it.
**K: fails, and this one is structural.** Kivi App. C.6 requires that a corrected memory *does not regrow on reprocessing*. Under TSM's design it regrows by construction at the next consolidation, because suppression isn't in the input. Pushes: the suppression list must be an input to consolidation, not a filter on its output — i.e. a second source of truth alongside the transcripts.

**D14 · Does old evidence lose standing over time?**
A: No decay. An item ages only in the sense that the query's time window may exclude it.
Rej: Ebbinghaus-style decay (cited in their own related work via MemoryBank, not adopted); re-observation windows; recency priors.
Asm: a query naming a time period wants that period; there is no "who you are now".
**K: fails.** Kivi §9: observations not re-observed within a window stop being surfaced. Note the subtlety — TSM's time filter *looks* like decay but does the opposite: it makes a six-month-old persona maximally retrievable for a query about six months ago. Kivi wants the reverse for identity claims and the same behaviour for episodes. Two different time semantics for two tiers; TSM has one.

**D15 · Can repetition alone change an item's status?**
A: Implicitly yes — more mentions means a stronger cluster and a more confident summary. There is no confirmation event anywhere in the system.
Rej: explicit confirmation as the only promotion path.
Asm: frequency is evidence of truth and of endorsement.
**K: fails.** §4: "Nothing self-promotes… Twenty is still a pattern." Pushes you to make `evidence_count` a display field, not a ranking or status input.

### Retrieval

**D16 · Retrieve over one pool or several?**
A: One: `M = M_topic ∪ M_persona ∪ M_raw`. Every query sees everything.
Rej: query-type-conditional pools; permission-scoped pools; capability-scoped stores.
Asm: one interaction mode, one user, one entitlement level.
**K: fails.** Kivi §7 and App. C.7 require the dictation path to be *structurally unable* to load observations — "two separate retrieval paths, not one path with a filter". TSM is exactly the one-path-with-a-filter design, and its filter (Eq. 14) is post-retrieval.

**D17 · What determines rank?**
A: Lexicographic — time-match indicator is the primary key, semantic similarity only breaks ties (Eq. 16).
Rej: weighted sum; learned reranker; soft temporal prior; similarity-primary.
Asm: `ParseTime` is reliable enough that being outside the window is disqualifying rather than merely unlikely.
**K: partly holds, but the assumption is thinner.** spaCy resolving "last weekend" against a dated query is one thing; Kivi's "the review we moved" has no time expression at all. Pushes toward similarity-primary with temporal *promotion*, i.e. the inverse ordering, whenever the query has no parseable time.

**D18 · What happens when the temporal constraint is wrong or absent?**
A: Asymmetric. Topics and personas are hard-filtered out (`I[τ ∈ T_q]`); raw chat turns are exempt (`Keep = 1` unconditionally).
Rej: soft penalty; abstain; ask the user; widen the window.
Asm: raw turns are an adequate safety net — that is, plain RAG is the floor the system falls back to.
**K: fails silently, which is worse.** Kivi has no raw-transcript-as-answer fallback in the same sense, and more importantly the failure is invisible: the user sees a confident answer built from raw chunks with all structured memory silently zeroed. The Why panel makes that visible in Kivi, which means you must *decide* what the panel says in this case. TSM never had to.

**D19 · Retrieve-then-filter, or filter-then-retrieve?**
A: Top-K = 25 first, temporal filter second, "post-retrieval in our implementation" — their own parenthetical flags this as an implementation choice.
Rej: constraint-first candidate generation; adaptive K; two-stage widening.
Asm: 25 semantically-nearest items will contain enough in-window material to survive filtering.
**K: pushes the other way.** With a small corpus and a narrow window, K=25 then filter can leave you with zero summaries and no signal that it happened.

**D20 · How much compute at recall time?**
A: Almost none — spaCy parse, dense retrieval, sort. No LLM call during recall. P50 1.57s, P95 2.39s; all extraction cost pushed to construction and sleep-time consolidation.
Rej: agentic retrieval; LLM query rewriting; iterative retrieve-read.
Asm: an interactive latency budget, and a tolerance for large offline token spend (~2.07M tokens).
**K: holds, and is the cleanest thing to inherit.** Kivi's dictation path especially cannot afford an LLM in the loop. The construction/utilisation cost split is the right shape; note it also determines D13 (cheap consolidation is *why* they recompute from scratch).

### Output and the user

**D21 · Is knowing separated from saying?**
A: No. Retrieved ⇒ injected into the prompt ⇒ sayable. There is no disclosure stage.
Rej: retrieval/disclosure split; entitlement gating; audience-aware output.
Asm: the only reason to withhold a memory is that it wasn't relevant.
**K: fails, and this is the product.** Kivi §1/§6: the dial governs disclosure, not retrieval, *specifically so that a withheld memory leaves a trace*. TSM offers no precedent — but note that its architecture is compatible: everything is retrieved into a candidate list already, so the gate goes between rank and prompt-assembly.

**D22 · What is exposed to the user about the memory?**
A: Nothing. The answer only. No provenance, no store surface, no trace.
Rej: citation to source turn; inspection view; memory browser.
Asm: memory is infrastructure; the user is a consumer of answers.
**K: fails.** The bidirectional entity↔turn index (Eq. 15) is the one piece you can reuse: it already maps a fact to its originating turn, which is the backbone of "tap to see the transcript". It exists as a ranking mechanism; you'd promote it to a UI mechanism.

**D23 · What happens when the system doesn't have the answer?**
A: Undefined. The generator decides. Abstention appears in LongMemEval's stated abilities and in the judge prompts, and is not reported in any results table.
Rej: designed abstention; show-what-was-searched; confidence thresholding.
Asm: a wrong answer and a missing answer cost the same, because both score zero.
**K: fails.** Kivi's abstention (§8) is a designed surface with a trace, and the failure costs are asymmetric — a fluent invented answer is worse than none. Pushes you to a rule TSM never needed: retrieval returning nothing in-window is a *result*, with reasons, not an empty context to generate over.

**D24 · Who can correct the memory?**
A: Nobody. No user write path exists.
Rej: inline correction; confirm/demote actions; contest.
Asm: the LLM's write-time judgement is final and good enough.
**K: fails.** All four of Kivi's per-entry actions (Confirm / Correct / That's not me anymore / Forget) are new surface with no precedent here — and D13 means naive implementations of the last two won't stick.

---

## 2. FORCED CHOICES

Where a different answer materially changes their result. These are the ones to actually reason about.

| # | Choice | Why load-bearing | What it costs you to copy |
|---|---|---|---|
| D3 | Semantic time over dialogue time | The whole paper. Ablation: −6.0 on Temporal, −2.0 overall. Their two SOTA categories (Temporal +22.6, Multi-Session +20.3) are both time-dependent. | Cheap and correct to inherit for episodes. Don't inherit it for preferences and entities. |
| D17/D18 | Lexicographic rank + asymmetric filter (summaries hard-filtered, raw exempt) | This pair *is* the retrieval system. Make the filter symmetric and a mis-parse kills the answer; make it soft and the temporal gain evaporates. The raw-turn exemption is the hidden safety valve that lets them run a hard filter at all. | You inherit an invisible failure mode. Decide what the Why panel shows when the filter zeroes everything. |
| D8 | Fixed monthly slices | Matches LongMemEval's timescale. At weekly cadence, clustering degenerates; at yearly, topics smear. Their own Limitations concede this. | Almost certainly wrong for a studio corpus. Re-derive from your data before setting it. |
| D9 | GMM over entity *name* embeddings | Determines what a "topic" is at all. Names in their corpora are descriptive nouns; in yours they're codenames. | Breaks on Kivi's cast. Cluster on summaries or on declared project structure. |
| D6 | Personas as stored, injected objects | Removing them costs −16.7 relative on Single-Preference — the category closest to Kivi's core. But TSM's Preference score (40.0) is *below* Naive RAG (53.3) and LangMem (60.0). The component they need most is the one they're worst at. | Do not read this as evidence that stored personas help preference handling. It's evidence they help *TSM's* preference handling relative to TSM without them. |
| D2 | User messages only at construction | Halves extraction cost and shapes what can ever be known. | Directly incompatible with multi-surface input. Your version of this decision has a privacy justification, not a cost one. |

---

## 3. UNEXAMINED DEFAULTS

Inherited from the line of work, not argued for. Each has an alternative nobody in this literature appears to try.

1. **Storage is unconditional.** Every method compared — Mem0, A-MEM, Zep, MemoryOS, LangMem — asks *how to store well*, none asks *whether to store*. Untried: an admission gate with a logged refusal.
2. **Inferring a person is the goal.** "Persona" enters as an obvious good. Untried: a system that aggregates evidence and deliberately declines to characterise, exposing the pattern instead of the trait.
3. **One speaker's memory is the only memory.** LoCoMo is two-person dialogue; everything either party says becomes the agent's store. The question "whose memory is this, and who consented" is not posed. Untried: a write-path boundary by subject.
4. **Memory is a passive read-store.** Nothing distinguishes what the system knows from what it may say. Untried: entitlement between retrieval and generation.
5. **Accuracy is the value of memory.** Every number is QA accuracy. No metric penalises retaining something, being confidently wrong, or being creepy. Untried: cost-weighted scoring where a wrong memory costs more than a missing one.
6. **Time = when the event happened.** Now well examined. Still unexamined: *how long a belief remains entitled to be held* — validity is attached to facts, never to inferences. A persona from March has no expiry.
7. **Re-derivation is idempotent and therefore free.** Consolidation recomputes from the full mention set on the assumption that recomputing yields the same thing. Untried: user edits as a second, protected input to consolidation.
8. **Slice boundaries are calendar-aligned.** An event spanning a month boundary is split across two topics with no mechanism to notice. Untried: boundaries derived from activity structure.
9. **The system speaks only in answers.** No memory system in this comparison set has a surface. Inspection is assumed to be a developer concern. Untried: one artefact that is simultaneously the trust UI and the debug tool — which is Kivi's §8 bet.
10. **Confirmation isn't a lever.** No system asks the user anything. Untried: a rationed question budget as a first-class resource.

---

## 4. QUESTIONS THE PAPER NEVER FACED

Derived from Kivi, not from TSM. No precedent exists in this paper or its baselines for any of these.

1. **When third-party content enters the context window, what stops it entering the write path?** Not a filter on candidates — a structural barrier. What is the object that crosses the boundary, and what proves it was the only thing that crossed?
2. **What is the admissibility test, and what does a refusal record look like?** Kivi's differentiator is a *log of drops with reasons*. That requires extraction to emit rejected candidates as data, which TSM's pipeline never produces.
3. **Where does the disclosure gate sit, and what does it emit?** Between rerank and prompt assembly, presumably. It must emit a withheld-count and a reason ("observation, requires Koottu") without leaking content. Nothing in TSM produces a structured account of what it chose not to use.
4. **How does an item change tier, and what is the recorded event?** Promotion requires a confirmation event with a timestamp. Demotion writes a suppression. Both are user-authored writes into a store that TSM assumes only the extractor writes to.
5. **How does suppression survive re-derivation?** The hard one. If consolidation recomputes from transcripts, the suppression must be an input to the extractor, versioned and auditable, and you need a test that proves it held.
6. **What can the dictation path physically load?** Kivi needs a store partition, not a query filter — lexical/entity only, provably unable to reach observations. That's a schema and permissions question TSM's single pool never poses.
7. **What does "no answer" return?** Not an empty context. A result object: what was searched, what time window, what was found nearby, what was withheld. TSM's retrieval returns a ranked list or a short one; it has no vocabulary for "searched and found nothing".
8. **How does a memory point at a transcript with a date?** Reusable piece: their entity↔turn index. Missing piece: durative summaries have no sentence-level provenance, so a persona line cannot be traced to a source. If Kivi surfaces observations with evidence, the observation must be generated *from* a citable set, not summarised into prose that loses it.
9. **What does semantic time mean when there is no query?** Dictation has no `t_now`-anchored question and no `ParseTime` target. Entity/lexical retrieval during transcription needs a different retrieval trigger entirely.
10. **How do you get canonical spellings out of the entity store and into transcription?** *Atlas* not *Atlus*. TSM has canonical entity names (`n_e`) as a dedup artefact; using them as a lexical bias for a text client is an unexplored repurposing.
11. **What is the unit of confirmation cost?** Kivi budgets prompts per week. That requires a value estimate per uncertain memory — a ranking problem nobody in this literature has needed.
12. **How does a small corpus behave?** All of TSM's structure (monthly slices, GMM clusters, K=25) is calibrated for 115k tokens over months. A demo corpus of thirty transcripts over three weeks may not have enough mass for any of it to fire.

---

## 5. EVALUATION GAP

**What they measured:** accuracy on LongMemEval_S (500 Qs, ~115k token histories) and LoCoMo, judged by GPT-4.1-mini; plus token cost, P50/P95 recall latency, and a two-cell ablation (w/o temporal, w/o persona). Single run, fixed setting, no variance reported.

**What the metrics cannot distinguish.** For each of these, two opposite answers score identically — so the paper gives you precedent, not evidence:

| Decision | Why the metric is blind |
|---|---|
| D1 store-everything vs admission gate | Nothing is scored for having been stored. A system that keeps everything weakly dominates one that doesn't. |
| D4 discard third-party content or don't | Zero retention questions in either benchmark. LoCoMo is *built* from two-party dialogue with no subject boundary. |
| D6 persona-as-stored-belief vs persona-inferred-at-query | Identical answer text either way. Accuracy cannot see where the inference lived. |
| D7 tiered vs flat epistemics | The judge asks only whether the answer contains the gold content. A hedged, sourced answer and a flat assertion both pass. |
| D11 how contradictions resolve | Knowledge-Update scores the *final* answer. Resolving by LLM fiat and resolving by user confirmation score the same when the LLM is right, and confirmation isn't available to score at all. |
| D13 whether corrections regrow | No user edits exist in the benchmark, so nothing can regrow. |
| D21 retrieval/disclosure separation | Nothing measures what was retrieved-and-not-said. There is no observable difference between "not retrieved" and "retrieved and withheld". |
| D22/D24 provenance and correction | No surface, no measurement. |

**Specific holes worth knowing:**

- **Abstention is claimed and not reported.** LongMemEval's five abilities include abstention, and their appendix carries an abstention judge prompt. Table 1's categories sum to exactly 500 with no abstention row. So they had the instrument and published no number. For Kivi App. C.5 there is no baseline to compare against.
- **LoCoMo's adversarial category is dropped.** LoCoMo is described as five categories including adversarial; Table 2 reports four, n = 1,540 of 1,986. The ~446 adversarial questions — the ones that test confident-wrongness — are absent.
- **The judge is deliberately generous.** LoCoMo's prompt: score correct "as long as it touches on the same topic"; temporal off-by-one forgiven. This means calibration is unmeasurable by construction — a vague hedge that names the topic scores identically to a precise answer. Any Kivi decision about *how confidently to say something* gets no signal here.
- **Preference is their weakest and noisiest cell.** n=30, TSM 40.0 vs Naive RAG 53.3 and LangMem 60.0, and the paper waves it off as high variance. Preference handling is most of what Kivi does. Take no design confidence from TSM here in either direction.
- **The ablation is partly self-cancelling.** Removing personas *improves* Single-Session-User (+1.4), Knowledge-Update (+1.3) and Multi-Session (+0.8) while collapsing Preference (−16.7). Read plainly: stored personas are a distractor for factual recall and a crutch for preference. That is an argument for making them a separately-gated store — which is Kivi's tier design — and the paper doesn't draw it.
- **One run, no seeds, no CIs.** Gaps of 1–2 points (the entire "w/o persona" effect) are not distinguishable from noise.

**Net:** the paper is strong evidence on exactly one axis — that grounding retrieval in event time rather than dialogue time helps, and that a cheap post-retrieval filter over pre-built summaries buys it at low latency. On every decision that constitutes Kivi's product — what to keep, whose it is, what standing it has, what may be said, what the user can change — TSM is a precedent with no evidence behind it, and in three places (D13 re-derivation, D16 single pool, D21 no disclosure gate) an actively incompatible one.
