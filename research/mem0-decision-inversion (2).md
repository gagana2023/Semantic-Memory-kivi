# Mem0 (2504.19413) inverted — decision space, read against Kivi

Legend for the Kivi column: **✗** assumption fails, **~** partly holds, **✓** holds.

---

## 1. Decision inventory

### Ingest

| # | Question | Mem0's answer | Rejected / unconsidered | Assumes | Holds for Kivi? |
|---|---|---|---|---|---|
| D1 | When new content arrives, what is the unit that triggers extraction? | Every message pair (user turn + assistant turn), incrementally. | Whole session; single turn; sliding window; event-triggered; only-when-something-durable-appears. | Input is turn-structured, uniform density, arrives continuously; extraction is cheap enough to run on everything. | **✗** Kivi's units are heterogeneous: a dictation, an app-context blob (Priya's Slack message), a Hey Kivi exchange. They have different memory rights. Pushes to *typed ingestion by source*, with the source recorded, not one uniform loop. |
| D2 | What context should the extractor see besides the new content? | Rolling async conversation summary + last 10 messages. | Stateless per-unit; full history; **retrieval-conditioned** (pull the memories this content touches). | Staleness of the summary is harmless; global gist is what disambiguates. | **✗** Kivi must know whether a candidate is *new* or *the 15th instance of a known pattern* (evidence_count). A summary can't tell you that. Pushes to retrieval-conditioned extraction keyed on entities in the input. |
| D3 | Who decides what is salient enough to store? | An LLM prompt asking for salient facts. Untyped, uncapped. | Schema-constrained extraction into fixed types; deterministic gate; user-authored memory; extract-nothing-and-re-derive. | Nothing is off-limits; benchmark rewards recall; a spurious memory costs almost nothing. | **✗** "Salient" will happily return *Priya's mother is ill*. Kivi needs typed slots (entity/preference/episode) plus a **separate deterministic exclusion check on candidates**, not a prompt clause. Difference pushes hard toward precision over recall. |
| D4 | Whose facts get retained? | Both speakers, symmetric stores (`speaker_1_memories`, `speaker_2_memories`). | Principal user only; others retained only as work-level relational residue; others not retained at all. | Both parties are consenting users of the same system (true of LOCOMO's two-friend chats). | **✗** Directly inverted. Kivi's §5: third parties enter the context window, never the write path. Mem0's architecture has **no write-path barrier to remove** — it would have to be added, and added before storage, not after. |
| D5 | When does extraction run relative to the request? | Synchronously per pair; summary refresh async. (They attack Zep for async lag.) | Batch nightly; end-of-session; two-speed (fast lexical/entity now, slow pattern work later). | Memory must be usable on the very next turn. | **~** True for entity/spelling memory feeding dictation. False for observations, which need cross-transcript evidence and are fine batched. Pushes to a **split write path** matching Kivi's split read path (§7). |

### Representation

| # | Question | Mem0's answer | Rejected / unconsidered | Assumes | Holds for Kivi? |
|---|---|---|---|---|---|
| D6 | What shape does a stored memory take? | A dense natural-language sentence (Mem0); entity–relation triplets (Mem0g). | Typed record with fields; span pointer into the source; hybrid record + rendered string. | Retrieval is embedding similarity, consumer is an LLM prompt, so text is the native form. | **✗** A string can't carry `tier`, `evidence_count`, `status`, `source_transcript_ids[]`. Kivi's schema is load-bearing for the product surface. Pushes to typed row + NL rendering *derived* from it. |
| D7 | What links a memory to where it came from? | Nothing in base Mem0. Mem0g keeps a creation timestamp on nodes. (Notably LOCOMO's own baseline system *does* keep dialog-turn refs — Mem0 dropped that.) | Store source ids; store the span; store nothing and accept it. | Nobody will ever audit a memory; the answer is the product. | **✗** Provenance *is* Kivi's product (§9: "the actual transcript, with a date"). Every downstream feature — Why panel, demotion, read-not-kept marker — is impossible without it. |
| D8 | How much confidence is a memory entitled to? | One flat tier. Everything is asserted. | Source-based tiers; probability; evidence count; separate "unconfirmed" store. | Extraction is reliable; a wrong belief is recoverable next turn. | **✗** Kivi's two axes (type × tier). Note Mem0 doesn't reject tiering — it never poses the question. |
| D9 | May the extractor infer beyond what was said? | Yes, explicitly: Mem0g prompts the LLM to reason about "implicit information". | Literal-only extraction; inference at read time only, never persisted. | Inference raises multi-hop recall and costs nothing when wrong. | **✗** Inference is the exact thing Kivi fences (§2). If inference happens, it must be typed `hypothesised`, stored **as a question**, and never at write-tier `stated`. |
| D10 | Is a hypothesis representable at all? | No grammar for it. Storage can only assert. | Store as an interrogative with an unconfirmed status. | Uncertainty can be handled by omission. | **✗** Kivi's `"Does she disagree with the pricing?" — unconfirmed`. This is a schema question, not a prompt question, and Mem0 gives no precedent. |

### Conflict and change

| # | Question | Mem0's answer | Rejected / unconsidered | Assumes | Holds for Kivi? |
|---|---|---|---|---|---|
| D11 | When a new fact contradicts a stored one, what resolves it? | An LLM function-call picks ADD / UPDATE / DELETE / NOOP at write time. | Deterministic rules over typed fields; classifier; defer to read time; ask the user. | Non-determinism in the write path is acceptable; no one needs to know why a memory vanished. | **✗** Kivi needs the resolution to be explainable and reversible. Also: an LLM can't distinguish *correction* / *change over time* / *context-dependent both-true* — Kivi needs all three separated (§9 supersession vs §4 evidence). |
| D12 | Where does a contradicted memory go? | Base Mem0: physically deleted. Mem0g: marked invalid, retained for temporal reasoning. | Version chain with superseded history; append-only + read-time recency. | History has no value except for temporal Q&A. | **✗** Kivi requires "the superseded version stays in history so the change is auditable". The Mem0g answer is closer; adopt that, not the base one. |
| D13 | Which existing memories are checked for conflict? | Top-s = 10 by embedding similarity to the candidate. | Entity-keyed structured lookup; graph neighbourhood; all memories of that type. | Similarity search reliably surfaces the contradicting memory. Silent failure mode: a paraphrased contradiction ranked 11th → two contradictory memories coexist, undetected. | **~** Kivi's entities are typed and named, so an exact key lookup is available and strictly better. Take the structured path; keep similarity as a fallback. |
| D14 | What can the user do about a memory directly? | Nothing. Correction only via saying something contradictory in a later turn. | Edit / delete / pin / confirm; suppression records. | The store is infrastructure, not a surface. | **✗** Kivi §9. And worse: Mem0 re-extracts from the same content, so a corrected fact **regrows**. Mem0 offers no suppression concept at all — this is a build-from-scratch, not an adaptation. |
| D15 | What happens to a memory nobody re-observes? | Nothing. Memories persist forever unless contradicted. | Time decay (MemoryBank does it); evidence-based decay; expiry for unconfirmed items. | The corpus is finite and replayed once; a stale fact is never surfaced as current. | **✗** Kivi decays observations and expires hypotheses. Note this is a question the whole line of work has quietly stopped asking since MemoryBank. |
| D16 | Can a memory change status without new content? | No. Status is a function of content only. | Promotion on explicit user confirmation, recorded as its own event. | The user is not a participant in memory maintenance. | **✗** Kivi's promotion is a *user event with a timestamp*, and nothing self-promotes at any evidence count. |

### Retrieval, ranking, disclosure

| # | Question | Mem0's answer | Rejected / unconsidered | Assumes | Holds for Kivi? |
|---|---|---|---|---|---|
| D17 | How are memories found at query time? | Embedding top-k over memory strings; Mem0g adds entity-anchored subgraph + triplet similarity above threshold t. | Structured query; hybrid; per-type routing; recency-weighted. | One retrieval path serves every query type. | **~** Fine for Hey Kivi recall. Wrong for the dictation path, where the query is "how is this name spelled" — a lexicon lookup, not a semantic search. |
| D18 | What ranks a memory above another? | Cosine similarity alone. No recency prior, no evidence weight, no tier. | Recency decay; evidence count; tier priority; source authority. | Similarity ≈ relevance; temporal reasoning can be pushed into the answering prompt instead ("prioritize the most recent memory"). | **✗** Kivi's tier must gate before the model sees anything at Anbu... except it doesn't (see D19). Evidence count and last-seen are already in Kivi's schema and should enter ranking. |
| D19 | Is everything retrieved allowed to be said? | Yes — no separation. Retrieved ⇒ in prompt ⇒ sayable. | Retrieve-all / disclose-by-permission; retrieve-by-permission. | Knowing and saying are the same act. | **✗** This is Kivi's founding principle (§1, §6): the dial governs **disclosure, not retrieval**, precisely so a withheld memory leaves a trace. Mem0 gives zero precedent and its architecture has nowhere to put the gate. |
| D20 | Do different surfaces get different memory rights? | No. One store, one path. | Separate stores per surface; one store with enforced views. | All interaction is the same kind of interaction. | **✗** Kivi §7: dictation is structurally unable to load observations. Enforce as separate stores/views, not a filter — a filter is a runtime claim, a schema is a demonstrable one. |
| D21 | What does the user see about how an answer was produced? | Nothing. No trace, no sources, no "what was withheld". | Expandable trace; source links; withheld-count. | Explanation has no value in the benchmark, and users won't ask. | **✗** The Why panel is a core deliverable. Note it must also render *withheld* and *dropped* — states Mem0's pipeline never materialises. |

### Failure

| # | Question | Mem0's answer | Rejected / unconsidered | Assumes | Holds for Kivi? |
|---|---|---|---|---|---|
| D22 | What should the system do when memory doesn't contain the answer? | Answer anyway. The generation prompt mandates an answer "less than 5-6 words". The unanswerable question category was **removed from the evaluation**. | Abstain; abstain with a trace of what was searched; return near-misses. | A confident wrong answer costs the same as no answer. | **✗** Directly inverted (§8). Kivi's abstention needs retrieval to return *near misses* ("I found Arun on Atlas backend work, 4 mentions") — Mem0's thresholded top-k discards exactly that signal. Design retrieval to return the below-threshold set, labelled. |
| D23 | How much of the user's attention may the system spend? | Question never arises; the system never asks anything. | Confirmation prompts; budgeted prompts; prompts attached to relevant moments. | The user is a data source, not a participant. | **✗** Kivi's rationed confirmation budget and the value-of-information ranking behind it have no precedent here. |
| D24 | What model does the extraction and update? | GPT-4o-mini for everything, temperature 0. | Larger model on the write path; small on read; two-pass extract-then-verify. | Write volume is high and continuous, so writes must be cheap. | **~** Kivi's write volume is one user's dictations. Cheapness is not the binding constraint. Difference pushes toward a **more expensive, verified extractor** — the exclusion check and tier assignment are worth a second pass. |

---

## 2. Forced choices — where a different answer changes the results

| # | Why load-bearing |
|---|---|
| **F1 — Store distilled facts, not text chunks (D3, D6)** | The entire headline: 7k tokens vs 26k full-context, p95 1.44s vs 17.1s, and J above every RAG configuration. Retrieve chunks instead and the paper has no result. Everything Mem0 claims is downstream of *compression*, not of any epistemic property of memory. |
| **F2 — Eager, destructive consolidation via LLM tool call (D11, D12)** | Contradiction handling is what produces the temporal and single-hop wins. Append-only would leave contradictory duplicates competing at retrieval. But see EG2 — their own evaluation can't actually see this. |
| **F3 — Excluding the adversarial/unanswerable category (D22)** | Makes their numbers incomparable with any system that abstains, and removes the only measurement that would have penalised confabulation. Every J score reported is on questions guaranteed to have an answer. |
| **F4 — A deliberately generous LLM judge** | The prompt instructs: be generous, count it correct if it touches the same topic. This inflates all systems and specifically **cannot penalise a fluent answer with the wrong detail** — Kivi's primary failure mode. A strict judge would compress the gaps and change the ranking. |
| **F5 — 5-6 word answers** | Forces guessing, forbids hedging, and makes the judge's job easy. A system built to answer with evidence would score worse on this metric while being better for Kivi's purpose. |
| **F6 — Graph as add-on, not primary (D6)** | Their own evidence is ambivalent: +2% overall, *worse* on multi-hop, better on temporal. Precedent for "hybrid", not for graph. Don't read this as a settled result. |
| **F7 — m = 10, s = 10, threshold t** | Stated once, never ablated. s=10 sets the recall ceiling of contradiction detection (D13); m=10 sets what the extractor can see. Both are free parameters presented as facts. |

---

## 3. Unexamined defaults

| Default | The alternative nobody in this line tries |
|---|---|
| **Memory is a set of true assertions.** No grammar for a question, a doubt, or an unconfirmed proposal. | Storage whose *grammar* encodes epistemic status, so a hypothesis is structurally unusable as a fact (Kivi §4). |
| **Everything extractable is storable.** LOCOMO transcripts contain health, family, sexuality (the sample prompt shows an LGBTQ support group being ingested), and no system in the comparison set has a category it refuses. | A hard exclusion list enforced at extraction, with dropped candidates logged as a visible artifact. |
| **Every speaker is a memory subject.** No concept of a person whose data appears but who is not a user. | Read-not-kept: third-party content usable in the context window, barred from the write path. |
| **Retrieval implies disclosure.** | Separating the two, which also makes withholding *observable*. |
| **Recency = truth.** DELETE-on-contradiction and "prioritize the most recent memory" both encode it. | Source authority: a stated preference outranking a fresher observed one, regardless of order. |
| **Extraction is a one-way transform.** The transcript is consumed, not kept as the record of account. | Treating raw source as canonical and memory as a rebuildable index — which is also the only way suppression can be verified (re-run and check the memory doesn't return). |
| **Memory is infrastructure with no surface.** Every system compared here is a library. | Memory as the product surface, where legibility to a non-developer is a requirement rather than a nice-to-have. |
| **Write-side cost is invisible.** Token consumption is measured *only at retrieval*. Extraction runs an LLM call on every message pair and the cost is never reported. | Reporting cost per stored fact, which is where a selective system wins and a promiscuous one loses. |
| **Memory quality is only ever measured through answer accuracy.** | Measuring the store directly: precision of stored facts, false-fact rate, duplicate rate, drop correctness. |
| **The user is never interrupted, and never consulted.** | A confirmation budget and a value-of-information policy for spending it. |
| **No ablations at all.** The paper contains zero internal ablation — summary vs no summary, tool-call vs classifier, m, s, t all unmeasured. | Any of them. This is the single biggest gap: nearly every internal decision is precedent, not evidence. |

---

## 4. Questions the paper never faced

Derived from the Kivi position doc, not from Mem0.

1. **Where exactly does the third-party barrier sit** — before context assembly, at candidate generation, or as a post-extraction check? Only the third is testable by replay, but only the first is actually a barrier. (Kivi §5 says "structural rule, not a filter applied afterward" — that commits you to the first, and then you must find another way to produce the drop *count* the UI promises.)
2. **What counts as one memory, for evidence counting?** Fourteen client emails without bullets is one observation with count 14 — but only if you have a canonical key for "writes client email in prose". Mem0 has no such key; embedding similarity would create near-duplicates. This is the schema decision the whole tier system rests on.
3. **Is suppression lexical or semantic?** Lexical suppression regrows in paraphrase; semantic suppression silently over-blocks adjacent true things. Neither is obviously right, and "corrections must stick" (§9) makes this the highest-stakes unsolved mechanic in the doc.
4. **Can the dictation path need something only the observation path knows?** A spelling learned from repeated usage is an *observed* lexical fact. If dictation is structurally barred from observations, either the lexicon is a separate tier-free store, or dictation gets worse over time. Decide which.
5. **How do you display a withheld memory without disclosing it?** "Kivi noticed something here" is itself a disclosure of the existence of a belief. At Anbu, is the *existence* of an observation within budget?
6. **What is the expiry of a true episode?** *The Atlas review moved to Thursday* stays true forever and becomes irrelevant within a week. Decay handles observations; episodes need a separate relevance horizon that no tier in §4 covers.
7. **Where do Daari's hypotheses go, given they must not be written?** Kivi's per-request escalation means some generated content is explicitly excluded from the write path — but the write path is fed by transcripts of interactions. If Kivi's own hypothesis-bearing reply is later ingested as context, it launders itself into evidence. Mem0 ingests the assistant's turn by default (D1); Kivi cannot.
8. **How is a near-miss surfaced for abstention?** Requires retrieval to return the sub-threshold set *with why it missed*, which is a different retrieval contract from top-k.
9. **Which uncertain memory earns a confirmation prompt this week?** A ranking problem — expected reduction in future error × frequency of relevance — that nothing in this literature formulates.
10. **What is the failure cost asymmetry, and does it invert the recall/precision default?** Mem0's worst case is a wrong answer, so it optimises recall. Kivi's worst cases are (a) a retained fact about Priya's mother, (b) a characterisation that regrows after correction. Both are precision failures and both are unrecoverable in trust terms. **Every threshold in the pipeline should be set from the opposite end than Mem0 sets it.**
11. **Does Kivi's scale license a slower, better write path?** One user, one studio, a bounded corpus. Mem0's p95 engineering solves a problem Kivi doesn't have; that budget should be spent on a verified two-pass extractor and read-time reasoning instead.
12. **Is the corpus itself a design artifact?** Kivi's Appendix A requires transcripts that produce nothing, transcripts with droppable third-party content, and questions with genuinely absent answers. LOCOMO has none of these by construction (they deleted the last category). Kivi has to build its evaluation set, not borrow one.

---

## 5. Evaluation gap

**Measured:** F1, BLEU-1, LLM-as-judge across single-hop / multi-hop / open-domain / temporal on LOCOMO (10 conversations, ~26k tokens each); retrieval-side token consumption; search and total latency p50/p95; memory store size.

**What those metrics cannot distinguish:**

| Gap | Consequence for you |
|---|---|
| **EG1 — Nothing penalises over-storage.** No metric falls when you store too much, store things you shouldn't, or store the wrong person's facts. | Zero evidence on D3, D4, D9. The metrics actively reward the opposite of what Kivi needs. Every selectivity decision is yours to make from scratch. |
| **EG2 — Consolidation strategy is untested.** The answering prompt already instructs "prioritize the most recent memory". An append-only store with read-time recency would very likely score the same. | D11/D12 are **precedent, not evidence** — despite being F2, the paper's own load-bearing choice. You are free to pick supersession-with-history on other grounds. |
| **EG3 — Provenance is free and unmeasured.** Storing source ids changes no reported number, and write-side cost is never reported, so it isn't shown to be expensive either. | No evidence against D7. Adopt provenance without arguing with this paper. |
| **EG4 — Tiering is invisible.** A system storing identical facts with tier labels scores identically. | D8 unmeasured in both directions. |
| **EG5 — Abstention was structurally removed.** The one discriminating category was dropped for lack of ground truth. | The paper offers **no evidence at all** on D22, and its scores include forced guesses on questions a careful system would have declined. Any Kivi comparison against these numbers is invalid unless you re-score abstentions. |
| **EG6 — The judge can't see confabulation.** "Generous… as long as it touches on the same topic" scores a right-topic, wrong-detail answer as CORRECT. | Kivi's primary failure mode is unmeasurable under their metric. You need a strict judge plus a separate fabrication rate. |
| **EG7 — Nothing changes over time.** LOCOMO is static and replayed once. No correction, no decay, no regrowth is exercised. | D14, D15, D16 have no evidence. Kivi's claims C6 (correction doesn't regrow) and the decay windows need a purpose-built longitudinal corpus. |
| **EG8 — Path separation is unmeasurable.** One surface, one store. | D20 has no precedent. But it is trivially *testable* in Kivi (schema-level assertion), which makes it a cheap claim to demonstrate. |
| **EG9 — Representation choice is weakly evidenced.** Graph vs no-graph is +2% overall with opposite signs by category and overlapping stated deviations. | Don't inherit either. Choose from Kivi's schema needs (D6), which point to typed records regardless. |
| **EG10 — No hyperparameter is ablated.** m, s, t, model choice. | Every number in F7 is a convention. Kivi's own decay windows, evidence thresholds, and confirmation budget (Appendix B) get no help from this paper — set them from your corpus, as your doc already says. |

**Net:** the paper is strong evidence for exactly one thing — that distilled fact-level memory beats chunk retrieval on cost and latency at competitive accuracy (F1/EG-none). On every decision Kivi's position document treats as central — what is refused, whose data it is, how confident you're entitled to be, what may be said versus known, what happens when you're wrong, and what changes over time — it supplies precedent and no evidence.
