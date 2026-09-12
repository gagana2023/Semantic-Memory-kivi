# MemGPT, inverted

**Paper:** Packer et al., *MemGPT: Towards LLMs as Operating Systems*, arXiv:2310.08560v2
**Read against:** *The Things Kivi Comes to Know*

Section references are to the paper. Where the paper doesn't say, this document says **underspecified** rather than guessing.

One framing note before the inventory. MemGPT's governing question is *how do I fit more into a fixed context window*. Kivi's is *what am I entitled to keep and entitled to say*. Almost every divergence below is downstream of that. MemGPT treats memory as a resource-management problem; Kivi treats it as an epistemic and permission problem. That means the paper is a strong precedent on retrieval mechanics and a weak-to-actively-misleading one on everything from extraction to disclosure.

---

## 1. Decision inventory

### A. What enters the system

**D1 — When something worth keeping is said, what should trigger the write?**

- **Paper:** Context scarcity. The queue manager fires a memory-pressure system message at ~70% of the window, and the LLM then decides whether to save anything from the queue before eviction (§2.2; Fig. 1 caption is explicit that the write follows the alert).
- **Rejected/unconsidered:** Value-triggered writes (a fact is durable, so store it, regardless of pressure); scheduled batch extraction; user-initiated saves; write-on-every-turn.
- **Assumes:** Importance is only worth adjudicating when space runs short; the context window is the scarce resource; anything not saved is recoverable because raw messages persist anyway (§2.2), so a missed write is cheap.
- **For Kivi:** Doesn't hold. Kivi cannot fall back on "we still have the raw text" for third-party content, so a missed extraction decision is not recoverable the same way — and an *unmade* decision to drop is a retention. Pressure-triggered writing also means importance is judged under a token deadline and only over what's still in the queue. Pushes toward extraction as a first-class pass with its own trigger, decoupled from any context budget. Your Appendix B leaves timing open; this decision says the paper gives you no reason to couple it to conversation length.

**D2 — Who has authority to write to memory: the model, a deterministic component, or the user?**

- **Paper:** The model, alone. Memory edits and retrieval are self-directed via function calls, governed by natural-language instructions in the system prompt describing the hierarchy and the function schema (§2.3). The user is never consulted.
- **Rejected/unconsidered:** A separate extractor model with its own prompt; a deterministic classifier gate on candidates; user confirmation before write; any write path the model cannot reach.
- **Assumes:** No category of content is forbidden, so a prompt-level policy is adequate; the agent's judgement about what matters is good enough; there is no auditor who needs to know why a write happened.
- **For Kivi:** Doesn't hold, and this is the sharpest divergence in the paper. Your §2 commits to exclusions "enforced by a check that runs on candidate memories, not by a line in a prompt hoping for good behaviour" — MemGPT is the paradigm case of the thing you're rejecting. Pushes toward a candidate-generation step (model) followed by an admission gate (deterministic), which is also the only shape that produces your drop log. Note the cost: a deterministic gate needs a closed category vocabulary, and "characterisation of the person's competence" is not obviously classifiable by rule.

**D3 — What happens to raw input after it's been used?**

- **Paper:** Kept forever. The queue manager writes both the incoming message and the generated output to recall storage, and evicted messages are stored indefinitely and remain searchable (§2.2). Nothing is ever deleted.
- **Rejected/unconsidered:** Retain derived facts only; retain raw with a TTL; retain raw but partition by subject; retain a redacted transcript.
- **Assumes:** Retention is free and unobjectionable; the only cost of keeping something is tokens, and out-of-context tokens cost nothing; there is no adverse party.
- **For Kivi:** Doesn't hold. But the interesting part is where it collides with *your* doc rather than just contradicting it. §9 defines provenance as "the actual transcript, with a date"; §5 says third-party content must not enter the write path. If the transcript is retained to serve provenance, Priya's message about her mother is retained — just not as a memory row. Your doc is **underspecified** on whether "read, not kept" is a claim about the derived store or about storage generally. The paper offers no help here because it never separated the two.

**D4 — What is the unit of a memory: an utterance, or a claim assembled from several?**

- **Paper:** An utterance or a short agent-authored line. Working-context items are independent strings appended one at a time (Fig. 1: a line for the boyfriend's name, a line for the birthday). Nothing aggregates; a fact seen twice is written twice or not at all.
- **Rejected/unconsidered:** A claim with an evidence set; entity-centric records that accumulate mentions; dedupe-on-write.
- **Assumes:** Facts are stated once and stated plainly; the value of a memory doesn't depend on how often it was seen.
- **For Kivi:** Doesn't hold. `evidence_count` and `source_transcript_ids[]` are load-bearing in your §4 — the difference between an observed preference (14 instances) and a one-off is the difference between the product working and nagging. And your demonstrable claim 3 is explicitly about assembling a memory from evidence across separate dictations. MemGPT has no aggregation primitive at all. Pushes toward a claim-keyed store with a merge/matching function on write — which raises a question the paper never faced (see §4, Q4).

### B. How it's represented

**D5 — What shape should durable memory have: text the model writes for itself, or records something else can read?**

- **Paper:** A fixed-size read/write block of unstructured text, editable only through function calls (§2.1). No fields, no ids, no timestamps, no source, no confidence.
- **Rejected/unconsidered:** Typed records; a graph; key-value with metadata; text plus a structured sidecar.
- **Assumes:** The only reader is the model that wrote it; nothing needs to be queried, filtered, counted, sorted, or rendered; the whole block can afford to sit in-context every turn.
- **For Kivi:** Doesn't hold, in three separate ways. Your schema needs fields (§4); your memory surface has to render and group by tier (§9); your permission dial has to filter by tier at generation time. Unstructured text supports none of these. Pushes hard toward typed records. Counter-consideration the paper implicitly makes: the blob is always in-context and free to consult, whereas typed records have to be retrieved, which reintroduces a retrieval failure mode on facts you were confident about.

**D6 — On what basis should memory be split into stores?**

- **Paper:** By origin. Recall storage holds the message log written by the queue manager; archival storage holds arbitrary text the agent chose to write (§2.1–2.2). Both are reachable by the same agent through the same function interface at all times.
- **Rejected/unconsidered:** Split by epistemic status; by disclosure permission; by data subject; by which caller may reach it.
- **Assumes:** There is one consumer, so partitioning for access control is meaningless; the split exists to distinguish "logged" from "curated", not to constrain anyone.
- **For Kivi:** Doesn't hold. Your §7 requires a split by *consumer path* — the dictation path must be structurally unable to load observations, not filtered from them. That's an access-control partition, a concept MemGPT has no place for. Pushes toward defining stores by who may read them first and by what they contain second. Note this can conflict with D5's typed-record store: an entity record that serves both dictation (spelling) and Hey Kivi (relations) has to live on both sides of a barrier you've promised is structural.

**D7 — When a fact enters memory, what should record how much the system is entitled to believe it?**

- **Paper:** Nothing. Everything in working context is a flat assertion in the same voice. A fact the user stated and a fact the agent inferred are indistinguishable objects once written (§2.1, Figs. 1 and 4).
- **Rejected/unconsidered:** Provenance tiers; confidence scores; separating claims from open questions; storing inferences in a different grammar.
- **Assumes:** The cost of treating an inference as a fact is low, because the consequence is at worst a slightly wrong conversational reference; nobody will contest a memory.
- **For Kivi:** Doesn't hold — this is the axis your entire §4 is built on. Worth noting the paper doesn't reject tiering; it appears not to have seen the question. Pushes toward tier-at-write. The real design choice this leaves open for you is whether tier is a column on one table or a partition into separate tables, and your §7 barrier argues for the second while your supersession logic (D12) argues for the first.

**D8 — Whose facts is the system storing?**

- **Paper:** Anyone's. The worked example stores relationship status and a named third party's role in the user's life (Fig. 1, Fig. 4), and recall storage retains every message verbatim. The paper has no concept of a data subject distinct from the user.
- **Rejected/unconsidered:** Subject-tagged rows; a retention rule keyed to who the fact is about; deriving user-side residue from third-party content.
- **Assumes:** A single consenting user; a chat setting where the other participant is the agent; no one whose data enters without agreeing.
- **For Kivi:** Doesn't hold at all — application context and inbound messages are constitutive of your setting (§5). Pushes toward subject as a required field on every candidate, computed before the exclusion gate rather than after. The paper gives you no precedent, only an illustration of what happens without it.

### C. What's discarded

**D9 — What should cause information to leave the working set?**

- **Paper:** Token thresholds. Warn at ~70%, flush at 100%, evict ~50% of the window (§2.2). Recency determines what goes.
- **Rejected/unconsidered:** Relevance-scored eviction; importance/recency hybrids (Generative Agents, cited in §4 but not adopted for eviction); no eviction with retrieval-only access; user-controlled pinning.
- **Assumes:** Recency proxies relevance well enough; eviction is not really *forgetting* because recall storage still has it; the window is the binding constraint.
- **For Kivi:** Partly holds, mostly irrelevant. Your binding constraints are disclosure and trust, not tokens — and your forgetting is semantic (observations decay when not re-observed; hypotheses expire) rather than capacity-driven. The one thing that transfers: MemGPT's eviction is safe *because* nothing is really lost. Kivi's decay is meant to actually reduce standing. Different mechanism, different failure mode — decay that silently retains is a broken promise; MemGPT's never made that promise.

**D10 — When information has to be compressed, what should the compressed form be?**

- **Paper:** A recursive summary — the previous summary plus the newly evicted messages, regenerated at each flush and parked at the head of the queue (§2.1–2.2).
- **Rejected/unconsidered:** Pointers with no summary; extracted typed facts; a summary that retains attribution to source turns.
- **Assumes:** Lossy, unattributable, compounding compression is acceptable because the originals remain searchable; nobody will need to know which turn a summarised claim came from.
- **For Kivi:** Doesn't hold. A recursive summary is exactly the object your §2 refuses — a characterisation assembled from fragments with no single source you can point at to disprove it. Pushes away from summarisation as a memory primitive entirely, toward extraction-with-provenance. Note the paper hands you the argument for free: the summary is what the *baselines* rely on, and the baselines lose (Table 2).

### D. Conflict and contradiction

**D11 — When new information contradicts something stored, what happens to the old version?**

- **Paper:** It's overwritten. `working_context.replace(old, new)` destroys the prior string (Fig. 4: boyfriend becomes ex-boyfriend). No history, no timestamp on the change, no record that a belief was revised.
- **Rejected/unconsidered:** Supersession with the old version retained; append-both-with-dates; confidence-weighted coexistence; asking the user which is right.
- **Assumes:** Newer is truer; the change will never need to be explained or reversed; the old value has no evidentiary use.
- **For Kivi:** Doesn't hold. §9 requires the superseded version to stay in history so the change is auditable, and your Why panel needs to be able to explain a revision. Pushes toward soft-delete/versioning. The cost the paper avoids and you inherit: a version chain is a growing record of what the user used to be, which sits uneasily with the same section's promise that the user can change what Kivi thinks. Retained history and "that's not me anymore" are not obviously compatible.

**D12 — What has to be true for a contradiction to be noticed at all?**

- **Paper:** The old fact must already be in the context window, and the model must happen to spot the conflict mid-conversation. There is no contradiction check on write and no scan of the archive (§2.3 — retrieval and edits are self-directed; nothing systematic runs).
- **Rejected/unconsidered:** Retrieve-before-write on the candidate's subject; periodic consistency sweeps; contradiction detection as a scheduled event (the paper *has* timed events per §2.4 but doesn't use them for this).
- **Assumes:** Contradictions arrive close in time to the thing they contradict; a missed contradiction just means a stale fact sits harmlessly.
- **For Kivi:** Doesn't hold. Your contradictions are the interesting case ("No, Priya's at Northwind now" in the middle of an unrelated request) and your corpus is built to contain them. A stale entity fact leaks into the dictation path as a wrong spelling or a wrong role. Pushes toward retrieve-before-write on every candidate — which puts a retrieval on the write path and raises the latency question your Appendix B defers.

### E. Retrieval and ranking

**D13 — What should determine which memories come back for a given request?**

- **Paper:** Embedding cosine similarity, pgvector + HNSW over ada-002 vectors, paginated (§3.2.1). Ranking is similarity, full stop — no recency weighting, no type or tier weighting, no structure.
- **Rejected/unconsidered:** Structured query on entity/date/type; lexical/BM25; hybrid; graph traversal over relations; recency-decayed scoring.
- **Assumes:** A large homogeneous corpus of prose chunks (20M Wikipedia articles) where the query is semantic and the answer is a passage; approximate is fine; there is no exactness requirement.
- **For Kivi:** Doesn't hold. Your corpus is tiny, typed, and entity-centric; "what did Arun say about the auth migration" is a join on person × topic, not a similarity lookup. And your dictation path needs exact lexical resolution — *Atlas* not *Atlus* — which is the one thing embeddings are structurally bad at. Pushes toward structured-first with lexical exact-match for names, and vector search only as a fallback for episode content. The paper itself reports the ceiling: doc-QA accuracy tracks the retriever, and the gold document often sits well outside the first dozen results (§3.2.1).

**D14 — Who decides when enough has been retrieved?**

- **Paper:** The model, by choosing whether to request another page (§2.3–2.4, function chaining via `request_heartbeat`). The paper reports the failure candidly: MemGPT often stops paging before exhausting the results (§3.2.1), and on nested KV the weaker models stop making lookups too early (§3.2.2).
- **Rejected/unconsidered:** Exhaustive deterministic search over a small store; fixed-k; a stopping rule tied to score thresholds; search-until-empty with a hard budget.
- **Assumes:** The store is too large to search exhaustively, so discretionary stopping is the only option; an incomplete search degrades gracefully into a worse answer.
- **For Kivi:** Doesn't hold, and this is the one I'd flag hardest for you. Your claim 5 is that Kivi abstained *and showed what it searched*. An abstention is only credible if the search was complete — "I looked and it isn't there" is a different speech act from "I stopped looking." Agent-discretionary paging makes your headline trust claim unverifiable. Pushes toward deterministic exhaustive retrieval, which your corpus size makes affordable in a way the paper's never was.

**D15 — Should being retrieved and being usable be the same thing?**

- **Paper:** Yes, necessarily. Retrieval means insertion into main context (§2.2 — retrieved messages are appended to the queue), and anything in context is available to generation. There is no state of "held but not said."
- **Rejected/unconsidered:** Filter at retrieval (cheap, no trace); filter at generation with a withheld set; a two-stage architecture where a second pass decides disclosure.
- **Assumes:** Everything the system knows, it may say; the only reason to withhold would be irrelevance.
- **For Kivi:** Doesn't hold — §6 makes the separation the point, and the trace *"3 memories retrieved, 1 withheld"* is impossible in MemGPT's architecture. Pushes toward retrieve-all-then-gate. The cost you're accepting: a withheld memory is still in the generating model's context, so the barrier is a prompt-level one at exactly the point where §2 says prompt-level barriers aren't good enough. If you want the withholding to be structural rather than hoped-for, you need the gate to run before the generation context is assembled — and then the "withheld" trace has to be produced by the gate, not by the model. The paper doesn't help; it just shows you the version where the question isn't asked.

### F. What's exposed to the user

**D16 — How much of the memory system should the user be able to see?**

- **Paper:** None of it. There is no memory surface anywhere in the paper. The persona instructions go further and tell the agent never to reveal that it's an AI (Appendix 6.1.1), so the mechanism is actively concealed. Memory is described as operating "without any user intervention" (§2.3).
- **Rejected/unconsidered:** A memory browser; per-answer traces; even a debug view.
- **Assumes:** The user is a conversational partner, not an administrator or an owner; the illusion is part of the product; nobody will ask why.
- **For Kivi:** Doesn't hold; §8's Why panel and §9's memory surface are most of your product. No transferable precedent — treat the whole of your inspection design as unprecedented in this line of work rather than as a variation on it.

**D17 — Should the system volunteer what it remembers, or wait to be asked?**

- **Paper:** Volunteer, enthusiastically. The conversation-opener task (§3.1.2) rewards an agent for spontaneously opening with personal details drawn from prior sessions, scored by similarity to the persona facts. The paper reports MemGPT's openers cover more of the persona than the human-written ones and treats that as the win.
- **Rejected/unconsidered:** Recall on demand only; graduated disclosure; volunteering only work-relevant facts.
- **Assumes:** Demonstrating memory *is* the value; more recall surfaced = better; the user is delighted rather than unsettled to be remembered at.
- **For Kivi:** Inverted. Your §1 says this in so many words — you don't repeat the insecure thing back at dinner to prove you were listening. The engagement metric is a metric your product is designed to lose. This isn't a difference in parameters; the paper's second headline result is optimising the quantity you're trying to bound.

### G. When the system is wrong

**D18 — When memory doesn't contain the answer, what should the system do?**

- **Paper:** Guess. The MemGPT persona is instructed to "reply with a best guess using the information in core memory" and conversation search (Appendix 6.1.1). Separately, the doc-QA and KV personas assert the answer is always present, so failure to find it is treated as failure to search hard enough (Appendix 6.1.4, 6.1.6). Only the *baselines* are given a NO ANSWER option.
- **Rejected/unconsidered:** Abstention with a coverage report; calibrated hedging; returning the neighbourhood of the query (which is what your §8 example does).
- **Assumes:** A wrong guess costs about what a non-answer costs; the setting is companionship, where fluency has independent value.
- **For Kivi:** Inverted, and consequentially. The asymmetry is baked into the evaluation too — see §5.

**D19 — When a stored memory is wrong, how does it get fixed?**

- **Paper:** Only if the model notices and rewrites it (D11). The user has no correction affordance; there is no notion of a user-asserted fact outranking a system-derived one. Function-level errors are fed back to the processor and handled in-loop (§2.3), but a semantically wrong memory produces no error at all.
- **Rejected/unconsidered:** Inline correction; explicit delete; suppression of re-derivation; user-authoritative overrides.
- **Assumes:** Wrongness is self-correcting through conversation; the user won't notice or won't mind.
- **For Kivi:** Doesn't hold. And your §9 identifies the part the paper couldn't have reached: deleting the row is useless if the same pattern regrows from the same transcripts. Suppression is a concept with no analogue here — MemGPT has no re-derivation, because it has no extraction pass to re-run.

### H. What changes over time

**D20 — What should happen to a memory that hasn't been relevant in a long time?**

- **Paper:** Nothing. Working-context entries persist until explicitly overwritten; recall storage is kept indefinitely (§2.2). Working-context items carry no timestamp at all (recall storage messages do — the dated results in Fig. 2). No decay, no expiry, no staleness signal.
- **Rejected/unconsidered:** Time-decayed standing; expiry for unconfirmed items; re-observation windows; archiving-on-age.
- **Assumes:** Facts about a person are stable; staleness is handled reactively when a contradiction shows up (D12); the evaluation horizon is five sessions.
- **For Kivi:** Doesn't hold. §9 makes decay a mechanic and hypothesis expiry a default. The paper offers zero evidence either way because nothing in its evaluation spans enough time for staleness to bite. Pushes you toward setting decay windows from your corpus, as your Appendix B already says — just don't expect the literature to have a number.

---

## 2. Forced choices

Where the paper's answer is doing the work. A different answer here changes the reported results, not just the design.

1. **D2 + D14 — self-directed function calling.** This *is* the contribution. It's also the single biggest sensitivity in the results: DMR accuracy is 66.9% on GPT-3.5 versus 92.5% and 93.4% on GPT-4 and GPT-4 Turbo, and §3.2.1 attributes the GPT-3.5 degradation directly to weaker function-calling. Move memory management out of the model and the architecture becomes a different system with a different performance profile. For you this cuts both ways: your gate and your exhaustive retrieval are *less* model-dependent, which is a robustness gain the paper's numbers can't credit you for.

2. **D3 — retaining the full raw history.** The DMR result exists because MemGPT can search complete conversation logs while baselines see only a lossy summary (§3.1.1, explicitly stated as the setup). A version storing only derived facts would score differently and the paper would have a different headline. This matters to you because your non-retention commitment removes exactly the asset the paper's best result is built on.

3. **D13/D14 — retrieval quality as the ceiling.** §3.2.1 says the fixed-context baselines are capped at retriever performance and that MemGPT's advantage is the ability to *keep calling* the retriever. Substitute a better retriever and the gap narrows; substitute exhaustive search on a small store and the contribution mostly evaporates. Kivi's corpus is small. The paper's central mechanism is a workaround for a problem you may not have.

4. **D18 + the judge — the guess/abstain asymmetry.** The MemGPT persona is told to guess; the LLM judge is instructed to be generous and explicitly counts "I don't remember what you're talking about" as WRONG (Appendix 6.1.2). Flip either and the reported accuracies move. This is load-bearing and undisclosed as such.

5. **D17 — engagement as a virtue.** The opener result depends on a metric (similarity to persona facts) that rewards volunteering remembered details. §3.1.2 also asserts that keeping information in working context is key to good openers. A system with a disclosure gate scores worse by construction.

6. **D5 — the always-in-context working block.** Not ablated, but the opener claim leans on it, and it's what makes MemGPT's high-value facts immune to retrieval failure. If you move to typed records that must be retrieved, you take on a failure mode the paper's design doesn't have. Worth deciding deliberately rather than by inheritance.

---

## 3. Unexamined defaults

Choices that don't read as choices — mostly inherited from the surrounding literature (RAG, agents, Multi-Session Chat).

- **Memory is a capacity problem.** The OS metaphor is announced in the title and never interrogated. Everything follows: tiers by speed of access, eviction under pressure, paging. The alternative nobody in this line tries is memory that is *deliberately incomplete* — where forgetting is specified behaviour rather than an artefact of running out of room. Your §1 is that alternative, and you should expect no prior art.

- **More recall is better.** Every metric is recall-shaped. No paper in this lineage reports what was stored that shouldn't have been. The unmeasured quantity is wrongful retention, and there's no baseline for it.

- **Prompt-level governance.** All memory-hierarchy rules live in the system instructions (§2.3). The field treats "we told the model the policy" as implementing the policy. The alternative — an enforcement component the model cannot argue with — is rare enough that your drop log is genuinely novel evidence rather than table stakes.

- **Natural-language English as the storage format.** Inherited from prompt-engineering practice. Nobody asks whether memory should have a grammar that makes illegal states unrepresentable — which is precisely your "hypotheses are stored as questions" move.

- **Vector similarity as the default retrieval mechanism for *personal* memory.** Imported wholesale from open-domain QA over Wikipedia, where the corpus properties are entirely different. The alternative barely tried in this line: a typed store with exact-match on entities and structured filters, using embeddings only for episode content.

- **The user is the only person in the system.** The MSC dataset is two personas talking; there is no third party, so there's no question about them. The alternative nobody tries: subject-aware retention.

- **Retrieval implies permission to speak.** Not defended anywhere, because it never surfaces as a question.

- **The eviction constants.** 70% / 100% / 50% (§2.2). Given as examples, never ablated, and now widely copied. If you adopt anything shaped like this, you're inheriting numbers with no evidence behind them.

- **Anthropomorphism and persona.** The agent is instructed to deny being an AI (Appendix 6.1.1). Never justified; inherited from the companion-chatbot framing of the dataset. The alternative is a system that presents as a system — which is what your memory surface commits you to.

- **Cost and latency.** Not measured, not mentioned. Function chaining could mean two LLM calls or ten. **Underspecified**, and worth noticing that the field's flagship memory architecture has no reported cost profile at all.

---

## 4. Questions the paper never faced

Derived from your doc, not from the paper.

**Q1 — Can provenance survive non-retention?** §9 defines provenance as the source transcript with a date; §5 says third-party content is read and not kept. If the transcript is deleted, "tap to see the source" has nothing to show; if it's kept, the sentence about Priya's mother is still on disk. Defensible answers exist on both sides (retain a redacted transcript; retain a derivation record instead of the source text; keep the transcript and treat non-retention as a claim about the memory layer only). Your doc currently reads as though both are true.

**Q2 — When a user-level fact is entangled with an excluded fact, does the reason survive?** The review moved because Priya's mother is ill. You retain the move and drop the cause. Later: "why did the Atlas review move?" Kivi has an episode with a hole in it. Either episodes carry causes (and the exclusion leaks) or they don't (and Kivi looks amnesiac about its own records). MemGPT never had to choose because it kept everything.

**Q3 — What does suppression match against?** "That's not me anymore" must block re-derivation (§9). Blocking requires deciding whether a new candidate *is* the suppressed claim — same string, same paraphrase, same underlying pattern, or same evidence? Suppressing by evidence means new transcripts of the same behaviour also produce nothing; suppressing by string means the pattern regrows in different words within a week, which is the exact failure you named. **Underspecified** in your doc, and the paper has no analogue because it has no re-derivation.

**Q4 — What counts as the same memory on write?** Entailed by evidence_count (D4). Is "signs off Best, Meera" the same claim as "signs client emails Best"? Merge too eagerly and evidence counts inflate around a claim nobody made; merge too conservatively and the observation never crosses its threshold. This determines whether your 14-instance observation is real or an artefact of the matcher.

**Q5 — Is the dictation path's entity memory a disclosure channel?** §7 says dictation gets lexical and entity memory only, because that's transcription accuracy rather than memory. But correctly rendering *Priya Raghavan* in a document is Kivi demonstrating it knows Priya. If the user dictates in front of someone, or into a shared doc, memory has spoken without the dial being consulted. Two defensible answers: entity resolution is orthography and not disclosure; or the dial applies to every surface where memory affects output.

**Q6 — What's the latency budget for a memory lookup on the transcription path?** Dictation is real-time and MemGPT's is not. Anything you put on that path — entity lookup, contradiction check on write (D12) — is on the user's critical path. Appendix B defers this; D12 and D13 both push work onto it, so the deferral has a cost.

**Q7 — How is silence distinguished from not-seeing?** §8 says silence isn't confirmation and unconfirmed hypotheses expire. But an ignored prompt and an unseen prompt are the same event in the log. If they're treated identically, a user who never opens the surface expires everything; if impressions are tracked, you're instrumenting attention, which sits awkwardly beside §2.

**Q8 — What's the value function on the confirmation budget?** A small weekly cap spent on the highest-value uncertain memories (§8). Ranking by what — evidence count, recency, how often it would have been retrieved, downstream blast radius if wrong? Different rankings produce visibly different products, and the budget being small makes the ranking matter more, not less.

**Q9 — What happens when the user's correction is wrong?** Your model makes the user authoritative. Kivi has 14 dated instances of prose-only client emails; the user says "I use bullets all the time." Options: user wins silently, user wins with the evidence retained in history, or Kivi shows the evidence once and then defers. §9 implies the first; §8's abstention ethic ("show what you looked for") implies the third.

**Q10 — Do expired hypotheses leave a trace?** §9 promises no quiet file of unanswered questions, while supersession promises an auditable history. An expired hypothesis is either fully gone (and the Why panel can't explain why Kivi once asked about pricing) or retained (and the quiet file exists under another name).

**Q11 — Does suppression apply retroactively?** Claim 6 says a memory didn't regrow *on reprocessing*, which implies you reprocess history. If so, when a suppression is added, does it re-run against the existing store and remove what's already derived? And does reprocessing re-open the third-party question for transcripts that were already gated once?

**Q12 — What is Kivi's stance when the same fact reaches it through two paths with different permissions?** A fact stated in dictation (stated tier, Anbu-visible) and the same fact observed across transcripts. Does the observation collapse into the statement, or coexist with its own evidence? Your §4 says nothing self-promotes — but this is the reverse case, and it decides whether evidence counts survive confirmation.

---

## 5. Evaluation gap

**What they measured.** DMR: LLM-judge accuracy plus ROUGE-L recall on one question per conversation, over MSC's five sessions (§3.1.1, Table 2). Conversation opener: embedding similarity to gold persona facts and to the human opener (§3.1.2, Table 3). Document QA: judged accuracy as retrieved-document count rises, on 50 sampled NaturalQuestions items (§3.2.1). Nested KV: exact accuracy across nesting levels, 140 pairs, 30 orderings (§3.2.2).

All four are recall-shaped, single-turn-scored, and gold-answer-referenced. Here's what that can't separate.

- **Any two write policies that leave the fact findable.** DMR scores retrieval, not extraction — MemGPT succeeds by searching raw logs. A system that extracted nothing but had good full-text search would score the same as one with excellent extraction. **No evidence on D1, D2, or D4; precedent only.**

- **Over-retention, in any form.** Nothing measures what was stored that shouldn't have been. A system that retained every third party's medical disclosure and one that retained none score identically on all four benchmarks. **Zero evidence on D3 and D8.** Your Appendix C claims 1 and 2 have no comparable measurement anywhere in this paper — you're building the metric, not adopting one.

- **Contradiction handling.** Nothing in the evaluation contains a contradiction. Figure 4 is an illustration. Destructive replace, append-with-supersession, and confidence-weighted coexistence would all score the same, because no benchmark ever asks about a revised fact. **No evidence on D11 or D12** — and this is a section of your design where the paper is a picture, not a result.

- **The recursive summary.** MemGPT reads from recall storage, not from its own summary, so summary quality barely touches its score. The summary is doing real work only for the *baselines* — which means the paper's summarisation design is essentially untested and its main appearance in the numbers is as the thing MemGPT beats. **No evidence on D10.**

- **Eviction parameters.** No ablation on 70/100/50 or on eviction policy. Recency-based and relevance-based eviction would likely score identically on DMR, since anything evicted is still searchable. **No evidence on D9.**

- **Abstention versus confident error.** Accuracy conflates them: a wrong guess and a refusal both score WRONG, so there is no separable false-assertion rate and no calibration measure. Combined with a persona told to guess and a judge told to be generous, the setup can't tell a well-calibrated system from a lucky one. **No evidence on D18**, and specifically none on the thing your claim 5 asserts.

- **Time.** Five sessions, all recent, no staleness. Decay and no-decay are indistinguishable here. **No evidence on D20.**

- **Disclosure.** No experiment separates knowing from saying, because the architecture can't. **No evidence on D15 or D17** — worse than none, since the opener metric actively rewards the opposite of your design.

- **Cost and latency.** Not reported. Two calls or ten produce the same accuracy number. **No evidence on anything in D14 or Q6.**

Two smaller cautions on the numbers you might otherwise lean on. The DMR gold answers were generated by an LLM from the same logs and judged by an LLM told to grade generously (Appendix 6.1.2–6.1.3), so the accuracy is a recall-friendly upper bound rather than a strict one. And MemGPT with GPT-4 Turbo scores *worse* than with GPT-4 on nested KV (§3.2.2, Fig. 7) with no explanation offered — which suggests the architecture's benefit isn't cleanly separable from model-specific function-calling behaviour. Small n throughout: 50 questions, 30 configurations.
