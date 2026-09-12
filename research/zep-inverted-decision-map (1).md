# Zep, inverted

**Paper:** Rasmussen et al., *Zep: A Temporal Knowledge Graph Architecture for Agent Memory*, arXiv:2501.13956 (Jan 2025).
**Read against:** *The Things Kivi Comes to Know*.

A note on the source text: my extraction of the PDF lost the opening characters of §2.2.1 and the opening sentence of §2.2.2 (Facts), and truncated guideline 6 of the entity-extraction prompt in §6.1.1. Where the fact-proposal mechanism matters I've read it off the appendix prompts instead of the body, and I say so. Check those two spots yourself.

Throughout: "Kivi" refers to the position document's commitments, not to anything you've built. Where the position document itself is silent, I say so rather than inferring.

---

## 1. Decision inventory

### A. What enters the system

**D1. What is the unit of ingestion — the thing that gets processed as one indivisible input?**

- **Paper:** A single message. Episodes are typed `message | text | JSON`; a message is "relatively short text… along with the associated actor who produced the utterance" and carries its own `t_ref`. (§2.1)
- **Alternatives:** A whole session; a semantically bounded work-episode; a variable-length unit determined by topic segmentation; lazy — never chunk, extract on demand at query time.
- **Assumes:** Turn-taking dialogue with short turns, arriving one at a time, where each turn is a plausible carrier of one or two facts. Also assumes a continuous stream — there's no "session boundary" object in the schema at all.
- **For Kivi:** Breaks. A dictation is a monologue delivered in one go, and the unit that has a meaning is the transcript plus its application context (§5's worked example needs *both* Priya's message and Meera's dictated reply to produce the right two candidates and drop the right two). Per-message extraction would split that pair across two units. Pushes toward: transcript-plus-context as the atomic unit, which in turn makes the extractor's input larger and more expensive per call but fewer calls overall. It also makes the drop-log per-transcript, which is what your inspection view (§5) wants anyway.

**D2. When the extractor interprets a unit, what surrounding material is it entitled to see?**

- **Paper:** The last *n* = 4 messages, "providing two complete conversation turns for context evaluation." (§2.2.1; the prompts pass `<PREVIOUS MESSAGES>` alongside `<CURRENT MESSAGE>`, §6.1.1–6.1.5.)
- **Alternatives:** No context (unit is self-contained); the whole session; a retrieved context — pull the *currently relevant graph state* rather than the *temporally adjacent messages*; adaptive window based on referring expressions.
- **Assumes:** Relevant disambiguating context is temporally local. Reasonable for chat. Note that they use the same window for five different jobs (extraction, resolution, fact extraction, temporal extraction) without asking whether those jobs need the same context.
- **For Kivi:** Partly breaks. "The review" in a dictation resolves against a *project*, not against the previous four utterances — the disambiguating context is the entity store, not the transcript history. Pushes toward: context-by-retrieval rather than context-by-adjacency, which is architecturally different and adds a read to the write path.

**D3. Who is a legitimate subject of memory?**

- **Paper:** Everyone. "ALWAYS extract the speaker/actor as the first node" and "extract other significant entities, concepts, or actors mentioned." (§6.1.1, §2.2.1) There is no user/non-user distinction anywhere in the schema.
- **Alternatives:** Subject-only (facts about the account holder); subject-and-their-world-derived (Kivi's line); consent-scoped tiers; role-scoped — organisations and projects retained, natural persons not.
- **Assumes:** Everyone in the conversation is either a party to the system or irrelevant as a rights-holder. Sensible for a two-party agent chat where both parties are the customer. Not stated as an assumption anywhere, which is the tell.
- **For Kivi:** Breaks completely — this is §5, the load-bearing trust claim. But the interesting part isn't that it breaks, it's that Zep's mechanism makes the break *structural rather than filterable*: the speaker node is created before fact extraction runs, and facts are only extractable "between the provided entities" (§6.1.3). If third parties aren't entities, third-party-derived facts about the user's world (*the review moved to Thursday* — an episode whose evidence is Priya's message) can't be expressed at all. Pushes toward: entities and persons being different things in your schema, or a person-node that is a resolution handle carrying no attributes.

**D4. After extraction, is the raw input kept?**

- **Paper:** Yes, permanently and by design. The episode subgraph is "a non-lossy data store," with bidirectional indices so "semantic artifacts can be traced to their sources for citation." (§2, §2.1)
- **Alternatives:** Discard raw after extraction; keep raw for a fixed window then discard; keep a redacted raw; keep raw but partition it so the retrieval path cannot reach it.
- **Assumes:** Storage is cheap, retention is costless, and there is no category of input that is dangerous to hold. Also assumes provenance and retention are the same decision.
- **For Kivi:** This is where you have a genuine collision the paper never has to face. §9 requires provenance to be "the actual transcript, with a date." §5 requires third-party personal content not to be retained. Zep resolves both with one non-lossy store; you can't. Pushes toward either (a) a redacted transcript as the provenance artefact, which weakens the "here is what you actually said" claim, or (b) an exclusion rule that binds the derived layer only, which weakens the "read, not kept" claim to "read, not *derived from*." Neither is free, and the position document does not pick.

**D5. When does extraction run relative to the interaction?**

- **Paper:** At ingestion, inline. Every message triggers entity extraction, a reflexion pass, embedding, cosine + full-text candidate search, LLM resolution, fact extraction, fact embedding, fact dedup, temporal extraction, invalidation check, and a community update. (§2.2, §2.3) Whether this blocks the response is **underspecified** — the paper reports retrieval latency (Table 2) and never reports ingestion latency or cost.
- **Alternatives:** Async post-hoc; batched nightly; lazy at first query; two-speed (cheap synchronous write, expensive consolidation later).
- **Assumes:** Ingestion cost is not on the user's critical path, or is affordable if it is. Unmeasured either way.
- **For Kivi:** Holds more easily than for them, with one constraint: your exclusion check runs "on candidate memories, before anything reaches storage" (§2), so async is fine as long as nothing is written pre-check. But it interacts with D14 — if extraction is batched, the drop log the user sees in the transcript inspection view arrives after the transcript does. Pushes toward: deciding whether "read, not kept" is a live marker or a retrospective one, which is a product decision disguised as a scheduling one. Appendix B leaves extraction timing open; this is the constraint that should close it.

### B. How it's represented

**D6. What shape must a memory take to be storable?**

- **Paper:** A typed binary relation between two distinct entity nodes. "Extract facts only between the provided entities. Each fact should represent a clear relationship between two DISTINCT nodes. The relation_type should be a concise, all-caps description (e.g., LOVES, IS_FRIENDS_WITH, WORKS_FOR)." (§6.1.3) Multi-entity facts are approximated by re-extracting the same fact between different pairs — "an implementation of hyper-edges." (§2.2.2)
- **Alternatives:** N-ary frames with named roles; free-text propositions with structured metadata; typed records per memory category; a mix (relations for entities, records for everything else).
- **Assumes:** Everything worth remembering is a relation between two named things. This is inherited from the KG literature rather than derived from the data.
- **For Kivi:** Breaks for two of your three types. *"Client emails in prose, not bullets"* is a preference whose object is not an entity. *"On 12 March the user moved the Atlas review from Tuesday to Thursday"* is a 4-place fact (actor, artefact, from, to) that the binary constraint would shred into pieces which are individually true and jointly uninformative. Pushes toward: type-specific representations, and away from a single graph as the storage substrate. Note the cost — you lose the traversal properties that make D20's BFS possible.

**D7. What does an entity carry besides its name?**

- **Paper:** An LLM-generated free-text summary, extracted "to facilitate subsequent entity resolution and retrieval," and *regenerated* on every duplicate merge: "when the system identifies a duplicate entity, it generates an updated name and summary." (§2.2.1) The summary is returned to the agent at retrieval as `ENTITY_NAME: entity summary`. (§3)
- **Alternatives:** Name only; a set of attributes each with its own provenance; a summary computed at read time from the attached edges rather than stored; a summary with version history.
- **Assumes:** A rolling LLM-written characterisation is a safe thing to hold and to serve. There is no version history on summaries (edges get four timestamps; summaries get none that the paper mentions), so a summary can drift arbitrarily far from anything anyone said, with no diff and no invalidation path.
- **For Kivi:** Breaks hard, and this is the most under-noticed break of the set. An entity summary is precisely the "characterisation assembled from fragments" that §2 rules out — unverifiable and uncorrectable, and here it's applied to third parties too (*Priya Raghavan: client contact at Acme who has been slow to respond and seems stretched*). It is also the exact artefact that makes §9's provenance requirement unsatisfiable, because no single transcript produces it. Pushes toward: entities as attribute sets with per-attribute source IDs, and any prose about an entity being generated at read time and never stored.

**D8. Is the epistemic status of a stored item represented at all?**

- **Paper:** No. Everything in the semantic layer is a "fact." The fact-extraction prompt asks for facts "pertaining to the listed ENTITIES," with no distinction between what a speaker asserted, what was implied, and what the extractor inferred; entity extraction explicitly covers entities "explicitly **or implicitly** mentioned." (§6.1.1, §6.1.3) Nothing in the schema carries confidence, evidence count, or source-type.
- **Alternatives:** Confidence scores; provenance-type tags (asserted / observed / inferred); Kivi's tier system; a two-store split with different write rules.
- **Assumes:** The downstream consumer is an LLM producing an answer, and an answer doesn't need to know how sure to be. Defensible when the output is a QA response and the cost of being wrong is a wrong answer.
- **For Kivi:** Breaks — this is §4, and you've called it "the entire product." Worth being precise about what Zep's absence costs: without a tier field there is nowhere to *condition* any other behaviour. No tier-aware conflict resolution (D15), no disclosure gate (D24), no promotion event (D28). Every one of your mechanisms needs this field to exist first. Pushes toward: tier as a primary key-level property, not a computed attribute.

**D9. How is time represented?**

- **Paper:** Bi-temporally, with four timestamps per edge: `t'_created`, `t'_expired` on the transaction timeline, `t_valid`, `t_invalid` on the event timeline. Relative expressions are resolved against `t_ref` at extraction time. (§2.1, §2.2.3, §6.1.5)
- **Alternatives:** Single timestamp (ingestion only); event time only; interval-free with an ordering relation; no explicit time, let the text carry it.
- **Assumes:** The distinction between "when we learned it" and "when it was true" is worth 4× the timestamp storage and an extra LLM call per fact. Their Table 3 vindicates this — temporal-reasoning is where they gain most (+38.4% / +48.2%).
- **For Kivi:** Holds, and is probably the most directly transferable thing in the paper. *"The review moved to Thursday"* has a validity interval and a learned-at date, and confusing them produces exactly the failure where a superseded schedule is quoted as current. But note the gap: bi-temporality handles *facts that stop being true*. It does not handle *observations that stop being representative* (see D28). Pushes toward: adopting the four timestamps for episodes and entity facts, and recognising that your decay mechanism is a **separate** axis they don't have.

**D10. Is the relation vocabulary closed?**

- **Paper:** No. Relation types are LLM-generated ad hoc per fact. The conclusion flags this as a known open question: "current research on LLM-generated knowledge graphs has primarily operated without formal ontologies… domain-specific ontologies present significant potential." (§5)
- **Alternatives:** Fixed ontology; open vocabulary with post-hoc clustering; hybrid — closed for a core set, open for the tail.
- **Assumes:** Domain-generality matters more than queryability. Correct for a memory-layer-as-a-service; the customer's domain isn't known at build time.
- **For Kivi:** Inverts. You have exactly one domain and a fixed cast (Appendix A). An open vocabulary buys you nothing and costs you the ability to write deterministic queries and deterministic exclusion checks. Pushes toward: a closed ontology — which also makes the §2 exclusion list checkable by type rather than by classifier, i.e. enforceable "by a check, not by a line in a prompt."

**D11. Is there a level of abstraction above individual entities?**

- **Paper:** Yes — community nodes, clusters of strongly connected entities carrying "high-level summarizations," built by label propagation with a dynamic single-step extension, plus "periodic community refreshes." Community names are embedded for search. (§2.3)
- **Alternatives:** No aggregate layer; aggregate computed at query time; user-defined groupings (projects, clients) rather than discovered ones.
- **Assumes:** (a) the graph is large enough that clusters are meaningful, (b) a synthesised cross-entity summary is a safe artefact, (c) the drift they acknowledge ("communities gradually diverge from those that would be generated by a complete label propagation run") is acceptable between refreshes.
- **For Kivi:** Breaks on all three. Your world is five people and two projects — label propagation over that is noise. And a community summary is an unattributable synthesis one level worse than D7's entity summary. Pushes toward: dropping the layer entirely, and, if you want grouping, using the user's own structures (project, channel, thread) which are attributable by construction. Note also: **communities appear unused in the evaluation** — §4 says they retrieved "edges (facts) and entity nodes (entity summaries)" only. So there's no evidence for this layer even on their own terms.

**D12. When are two mentions the same thing, and when is that decided?**

- **Paper:** At write time. Embed the name into 1024-d, cosine search plus separate full-text search over existing names and summaries, then an LLM resolution prompt over the candidates; on duplicate, generate a merged name and summary. (§2.2.1, §6.1.2) Graph writes then use predefined Cypher rather than LLM-generated queries, "to ensure consistent schema formats and reduce the potential for hallucinations."
- **Alternatives:** Late binding — keep mentions distinct, resolve at query time; deterministic resolution on exact/alias match with LLM only for the residual; human-confirmed merges; probabilistic co-reference with a confidence field.
- **Assumes:** A merge is cheap to make and rarely wrong, and there is never a need to undo one. There is no unmerge operation described anywhere.
- **For Kivi:** Breaks on the undo. §9 requires everything to be "editable, pinnable, or removable," and a wrong merge (two Priyas, or Atlas-the-project vs Atlas-the-doc) is a memory error the user will notice and try to correct. Early binding makes that correction destructive to reverse. Pushes toward: recording the merge as an event with the pre-merge state retained — same treatment you're already giving supersession — or toward late binding, which costs query-time latency on the dictation path where you can least afford it.

### C. What is discarded

**D13. What must never be stored, regardless of relevance?**

- **Paper:** Nothing. The only exclusions are representational housekeeping: don't make nodes for relationships or actions, don't make nodes for dates, don't extract entities mentioned only [truncated in my extraction — §6.1.1 guideline 6]. There is no content-based exclusion concept, no sensitive-category notion, and no privacy discussion in the paper.
- **Alternatives:** Category exclusion at extraction; classifier gate before storage; consent-scoped write; store-but-mark-restricted; store everything, gate at read.
- **Assumes:** All conversation content is fair game for indefinite retention. This is not argued; it's absent. Note it isn't even a *storage* question for them — non-lossy episodes (D4) mean the content is retained regardless of what the extractor does, so an exclusion at extraction would be cosmetic in their architecture.
- **For Kivi:** Breaks, and the interaction with D4 is the thing to take. Your §2 exclusion list is only meaningful if the non-lossy store is also bounded, otherwise you've built an exclusion at the derived layer sitting on top of a complete recording. Pushes toward: exclusion has to be a property of the whole pipeline, and "candidates dropped before storage" needs to mean *storage*, not *the semantic layer*.

**D14. What happens to candidates the extractor considered and rejected?**

- **Paper:** They vanish, and the pipeline is deliberately tuned against rejection: a reflexion pass runs after initial extraction to "minimize hallucinations and **enhance extraction coverage**" (§2.2.1) — a recall-increasing step with no precision-increasing counterpart. No drop log exists.
- **Alternatives:** Log drops with reasons; log drops without reasons; a precision pass instead of/alongside the recall pass; a human-visible extraction receipt.
- **Assumes:** Over-extraction is cheaper than under-extraction. True when the failure mode is a missing answer and false when it's an unwanted retention.
- **For Kivi:** Inverts. Your failure asymmetry is the opposite — a retained thing that shouldn't be is worse than a missed thing, and the drop log is a *product surface* (§2: "the most interesting thing to show a reviewer"; §5's "read, not kept" marker). Pushes toward: reflexion applied to the exclusion check rather than to coverage, and a drop record as a first-class stored object with a reason code, which means the exclusion classifier's output schema is part of the data model, not part of the prompt.

### D. Conflict and contradiction

**D15. When new information contradicts stored information, what determines which survives?**

- **Paper:** Recency, unconditionally. "Following the transactional timeline T′, Graphiti consistently prioritizes new information when determining edge invalidation." The new edge's `t_valid` becomes the old edge's `t_invalid`. (§2.2.3)
- **Alternatives:** Source authority; confidence-weighted; hold both and mark disputed; ask the user; specificity-wins; frequency-wins.
- **Assumes:** Later statements are better statements, and the world changes more often than speakers err. Reasonable for schedule changes, wrong for corrections-that-are-themselves-mistaken and for cases where an offhand remark contradicts a deliberate one.
- **For Kivi:** Holds in direction (§9: "contradictions supersede… the superseded version stays in history") but is **under-conditioned** for your setting, because you have a tier field and they don't. Recency-only means a new *observation* can invalidate a *stated* preference — fourteen prose emails followed by one bulleted one. That's the exact behaviour §4 says is fatal ("silently enforces things you never agreed to," in reverse). Pushes toward: a resolution rule keyed on the tier pair, not on time alone — and toward deciding whether a lower-tier item may invalidate a higher-tier one at all, or only flag it.

**D16. How wide a net does contradiction-detection cast?**

- **Paper:** Narrow, and deliberately so. Edge dedup and invalidation compare a new edge only against "semantically related existing edges," with the search "constrained to edges existing between the same entity pairs." This "significantly reduces the computational complexity… by limiting the search space." (§2.2.2–2.2.3)
- **Alternatives:** Global semantic search over all edges; n-hop neighbourhood; type-scoped rather than pair-scoped; scheduled full-graph consistency sweeps.
- **Assumes:** Contradictions are local — they occur between statements about the same pair of things. A cost/completeness trade made explicitly for cost.
- **For Kivi:** Breaks for preferences and observations, which don't live between entity pairs at all (see D6) and therefore have no natural scoping key. *"Never uses bullets in client email"* vs *"always bullet the summary section"* is a contradiction with no shared entity pair. Pushes toward: contradiction scope defined per memory type — which is more design work, but at your corpus size the cost argument that motivated their constraint doesn't apply. A full sweep over a few hundred memories is affordable.

**D17. Is an invalidated item deleted or retained?**

- **Paper:** Retained, with `t_invalid` set. The bi-temporal model keeps "historical records of relationship evolution over time." (§2.2.3)
- **Alternatives:** Hard delete; tombstone without content; retain with retention limit.
- **Assumes:** History is worth its storage and carries no liability.
- **For Kivi:** Holds and is required (§9's auditable supersession). The divergence is at the *read* side, not the write side: Zep's constructor emits `FACT (Date range: from - to)` for every returned edge (§3), so invalid facts are eligible for retrieval and disambiguated only by a date string in the prompt. Whether superseded memories are retrievable, or only inspectable in history, is a decision they made by default and you have to make deliberately.

**D18. May the system decline to resolve a contradiction?**

- **Paper:** No such state exists. Every detected contradiction is resolved immediately in favour of the new edge.
- **Alternatives:** A disputed state; deferred resolution; escalate to the user.
- **Assumes:** No one is available to ask, and an unresolved graph is worse than a possibly-wrong one.
- **For Kivi:** Breaks — you have a user, a confirmation budget, and an explicit "store as a question" grammar (§4). A contradiction is arguably the highest-value thing to spend a budgeted prompt on, since it's the case where you *know* you're wrong about something. Pushes toward: contradictions being a source of confirmation prompts, which makes the budget allocation policy (§8) a scheduling problem over a queue you don't currently have a name for.

### E. Retrieval and ranking

**D19. What does the retriever return when nothing relevant exists?**

- **Paper:** The top *k* anyway. `f: S → S` always produces a context string; §4 fixes k at 20 edges + 20 nodes (§4.2 says 10 for DMR — **inconsistent between sections**). No threshold, no null return, no relevance floor.
- **Alternatives:** Score threshold with empty return; explicit no-evidence signal; return the search trace instead of results.
- **Assumes:** The generator will handle irrelevance gracefully, and every question has an answer in the store. The benchmarks guarantee the second (every DMR and LME question is answerable from the conversation), so the assumption is never tested.
- **For Kivi:** Breaks — §8 makes abstention "a designed feature with a visible surface." A fixed-k retriever cannot produce your abstention example, because it will always hand the generator twenty plausible-looking facts about Arun and migrations, which is precisely the condition under which a fluent invented answer gets produced. Pushes toward: a relevance floor and a structured "searched X, found nothing" return — and note that the floor is a *parameter you have no data to set*, which is a corpus problem before it's an architecture problem.

**D20. How are candidates found?**

- **Paper:** Three-way hybrid — cosine over embeddings, Okapi BM25 full-text, and breadth-first traversal over the graph, on the theory that they "target different aspects of similarity" (word / semantic / contextual). BFS can be seeded with recent episodes' entities. (§3.1)
- **Alternatives:** Any single method; two of three; structured query where the schema permits it; query-planning that picks a method per query type.
- **Assumes:** Recall is the binding constraint and three methods are affordable. No ablation is reported, so there is no evidence any one of the three contributes.
- **For Kivi:** Partly holds, partly overkill. BM25 is doing the work for the dictation path (spelling *Atlas* not *Atlus* is exact lexical lookup, and it has to be fast). BFS presupposes D6's graph substrate. Pushes toward: separate retrieval mechanisms per consumer, which you already need for §7's structural isolation — the dictation path's inability to load observations is easier to guarantee if it uses a different index, not a filtered view of the same one.

**D21. What determines rank among retrieved candidates?**

- **Paper:** Configurable. RRF, MMR, a node-distance reranker relative to a centroid, cross-encoder scoring, and an **episode-mentions reranker** that "prioritizes results based on the frequency of entity or fact mentions within a conversation, enabling a system where frequently referenced information becomes more readily accessible." (§3.2) Which reranker was used in the reported experiments is **underspecified**.
- **Alternatives:** Pure similarity; recency-weighted; confidence-weighted; user-pinned priority; diversity-first.
- **Assumes:** Frequency is a proxy for importance. Defensible.
- **For Kivi:** This is a subtler collision than it looks. §4 says "nothing self-promotes… twenty is still a pattern" — but that rule is about *tier*, and Zep's frequency signal operates on *rank*. Those are separable, and your position document doesn't say whether evidence count may influence ranking. It probably has to, or a preference seen fourteen times ranks equal to one seen once. Pushes toward: making explicit that frequency moves rank and never moves tier, and checking that a user can't experience rank-promotion as de facto assertion.

**D22. What does memory hand to the generator?**

- **Paper:** A flat text string. `f: S → S`; the constructor emits facts with date ranges and entities with summaries under `<FACTS>` and `<ENTITIES>` tags. (§3) No structure, no tier, no provenance, no scores, no withheld set.
- **Alternatives:** A structured object the caller interprets; string plus sidecar metadata; multiple typed channels.
- **Assumes:** The only consumer is a prompt, and everything memory knows is safe to put in front of the model.
- **For Kivi:** Breaks, and it's the quiet blocker for two of your surfaces. The Why panel (§8) needs "what was retrieved, what was withheld and why, what was used"; the trace *"3 memories retrieved, 1 withheld (observation, requires Koottu)"* (§6) can't be produced from a string. Pushes toward: the retrieval return being a structured result set of which the prompt string is a *projection* — and once it's structured, the disclosure gate (D24) is a filter over the result set with the withheld items still present as objects.

**D23. How much context is returned?**

- **Paper:** Fixed k, ~1.6k tokens average against a 115k full-context baseline (Table 2). Fixed regardless of query.
- **Alternatives:** Adaptive by query type; budget-based; return-all-above-threshold; cost-tiered.
- **Assumes:** A uniform budget suits all questions. Their own Table 3 undercuts this — single-session-assistant *regresses* (−17.7% on gpt-4o), which is what you'd expect when a fixed small budget replaces a context that already contained the answer.
- **For Kivi:** Mostly unbinding at your corpus size — your whole memory store may fit in context. The 90% latency claim is a large-corpus result. Pushes toward: not inheriting the fixed-k discipline for its stated reason, and noticing that if you *can* fit everything, D19's abstention problem gets harder rather than easier, because there's no retrieval step doing implicit filtering.

### F. What's exposed to the user

**D24. Are retrieval and disclosure separable?**

- **Paper:** Not represented. Retrieved ⇒ in the context string ⇒ available to the answer. There is no gate and no concept of a memory the system holds but may not use.
- **Alternatives:** A disclosure policy layer over the result set; separate stores per permission level; per-item disclosure flags; retrieval scoped by permission (never fetch what you may not say).
- **Assumes:** Knowing and saying are the same act. Fine when there's one user, one context, and nothing sensitive.
- **For Kivi:** Breaks — this is §1's calibration principle and §6's dial. Their architecture makes your specific choice (*"the dial governs disclosure, not retrieval"*) impossible to express, and it's worth noting that yours is the more expensive of the two options: retrieve-everything-then-gate means the withheld content is in the process, which is what enables the trace and the *"Kivi noticed something here"* affordance, but it also means an exclusion bug is a disclosure bug. Retrieve-only-what's-permitted is the safer and less inspectable answer. That trade is yours to make and the paper offers nothing on it.

**D25. Is provenance available to whoever consumes the memory?**

- **Paper:** Structurally yes, functionally no. Bidirectional episode↔entity indices exist "for citation or quotation," but "these connections are not directly examined in this paper's experiments" and no provenance appears in the context template. (§2.1, §3)
- **Alternatives:** Provenance in the context string; provenance available on demand; provenance as a user-facing surface only; no provenance.
- **Assumes:** The consumer is a model, and models don't need sources. If a human ever needs one, the index is there.
- **For Kivi:** Breaks — §9 makes provenance the mechanism of revisability, not an audit feature. The direction to notice: they built the index and never wired it to anything, which is the natural outcome when provenance isn't on the evaluated path. Pushes toward: putting a provenance-dependent claim in your eval (Appendix C items 1–3 already do this), because provenance that isn't measured tends to rot.

### G. When the system is wrong

**D26. Who can correct the memory?**

- **Paper:** No one. There is no user-facing write, edit, confirm, or delete path anywhere in the paper. Correction happens only as a side effect of the user later saying something contradictory in conversation, which the invalidation machinery picks up (D15).
- **Alternatives:** Direct edit; conversational correction with confirmation; a review surface; correction as a privileged episode type.
- **Assumes:** The user doesn't see the memory, so they can't disagree with it. Consistent with Zep being a layer behind someone else's product.
- **For Kivi:** Breaks — §9 is entirely this. And the derived requirement is the one Zep's architecture makes hardest: *"deleting the row is useless, because the same pattern will regrow from the same transcripts within a week."* In a non-lossy episode store with deterministic re-extraction, a deletion is guaranteed to be undone. Suppression has to be an object the extractor reads, which means the extractor has state beyond its prompt. Nothing in the Zep pipeline has that shape.

**D27. What does the system do when it doesn't know?**

- **Paper:** Not addressed. There is no abstention path, no confidence output, and no unanswerable-question handling. The failure mode is a generated answer over whatever the top-k returned.
- **Alternatives:** Abstain on threshold; abstain with a search trace; hedge; answer with confidence attached.
- **Assumes:** A wrong answer costs a benchmark point. That is literally the cost in their setting.
- **For Kivi:** Breaks — §8. The asymmetry is worth stating precisely: for Zep, abstaining and answering wrongly score identically (both are a miss), so there is no incentive to build abstention. For you, they differ by the entire trust proposition. Any metric you inherit from this literature will reproduce their incentive.

### H. What changes over time

**D28. Does anything lose standing without being contradicted?**

- **Paper:** No. The only path out of currency is invalidation by a contradicting edge (§2.2.3). A fact stated once and never revisited stays as current as one stated fifty times. There is no decay, no expiry, no last-seen field, no confirmation event.
- **Alternatives:** Time decay; use-based decay; re-observation windows; explicit expiry on some types; confirmation-refreshed TTL.
- **Assumes:** Facts are true until superseded. Correct for *Priya works at Acme*; wrong for behavioural patterns, which are claims about a distribution that has a shelf life.
- **For Kivi:** Breaks, and this is the second axis I flagged at D9. §9 requires observations to decay by non-re-observation and hypotheses to expire by default — both are *silence-triggered*, and bi-temporality has no notion of silence. Note the additional structure you need and they don't: `last_confirmed_at` and `evidence_count` are in your schema (§4), but decay also needs a *window*, and Appendix B correctly says you can't set it without corpus data. Pushes toward: decay windows being a per-type parameter, and toward deciding whether decay is computed at read time from `last_seen` (cheap, reversible) or applied as a write (auditable, matches supersession).

**D29. How does the aggregate layer stay current, and what is drift worth?**

- **Paper:** Dynamic single-step label propagation on insert — a new node joins the community held by the plurality of its neighbours — with the acknowledgement that "communities gradually diverge" and "periodic community refreshes remain necessary." Label propagation was chosen over Leiden specifically for its "straightforward dynamic extension." (§2.3)
- **Alternatives:** Full recompute on every insert; Leiden with scheduled batch refresh; no aggregate layer; user-defined groups.
- **Assumes:** Bounded incorrectness in a summarisation layer is an acceptable price for latency and LLM cost. An honest and well-stated trade.
- **For Kivi:** Moot if you drop communities (D11), but the *pattern* transfers to your observation layer, which has the same shape: a derived, aggregated artefact over a growing evidence base, expensive to recompute. The question you inherit is whether an observation's evidence count and standing are updated incrementally per transcript or recomputed periodically over the corpus — and unlike them, you have a correctness requirement (Appendix C item 6: a demoted memory must not regrow on **reprocessing**) that presupposes reprocessing happens. Reprocessing is a full recompute. They chose incremental; your own acceptance criterion pushes the other way.

---

## 2. Forced choices

Decisions where a different answer changes their reported results materially. Everything else in §1 is a preference they could have flipped without moving a number.

1. **D23 + D19 — retrieve a small fixed context instead of passing everything.** This *is* the paper. The 90% latency reduction is 1.6k tokens vs 115k (Table 2), and the accuracy gain on gpt-4o (60.2% → 71.2%) is a lost-in-the-middle effect on the baseline as much as a memory effect. It also causes their one regression: single-session-assistant drops 17.7%, because for questions whose answer was already in context, replacing context with extraction can only lose. Flip this and there is no result.

2. **D9 + D15 — bi-temporal modelling with recency-wins invalidation.** Drives temporal-reasoning (+38.4% / +48.2%) and knowledge-update (+6.5% on gpt-4o), which are the categories that distinguish Zep from ordinary RAG. Without it the paper is a graph-RAG paper with a marginal DMR win.

3. **D4 — non-lossy episode retention.** Load-bearing structurally rather than numerically: it is what makes aggressive extraction safe for them. If extraction drops something, the episode still has it. Every downstream permission they take — over-extract, merge eagerly, invalidate on recency — is underwritten by the raw store. Remove it and the whole pipeline's risk tolerance has to change. **This is the one to stare at**, because your §5 removes it and you inherit none of the permissions it was paying for.

4. **D12 — write-time entity resolution.** Resolution quality bounds fact quality, because facts are only extractable "between the provided entities" (§6.1.3). Two Priyas means half the facts attach to a phantom. No ablation, but this is the single point where a quiet error propagates to everything.

5. **D6 — facts as binary typed edges.** Determines what is expressible. Also plausibly explains the *absolute* preference numbers (see §5 below): preferences are the memory type least suited to a binary-relation shape, and preference is where Zep's absolute scores are worst despite the largest relative gains.

6. **Model choice for construction.** gpt-4o-mini for graph construction throughout (§4.1), with the admission that "additional development may be needed to improve less capable models' understanding of Zep's temporal data." The temporal machinery's value is model-dependent, and they only show it at one construction-model point.

---

## 3. Unexamined defaults

Choices made without visible awareness that a choice was occurring. Most are inherited from the RAG/KG line rather than from Zep specifically.

**U1. There is no human in the loop, and no one notices.** Not a single confirm, correct, or delete affordance appears in the paper, and their absence is never justified. The whole line of work — MemGPT, GraphRAG, AriGraph, LightRAG — evaluates memory as a fully autonomous read-write process. *The alternative nobody tries:* memory as a jointly authored artefact where the user's confirmations are a distinct and privileged input type. Your entire §9 lives in this gap, which means you get no engineering precedent for it, only your own reasoning.

**U2. Retrieved equals sayable.** Nobody in this literature separates what the store returns from what the answer may use. There's no vocabulary for it — a "withheld" result isn't a concept any of these systems can express. *The alternative:* a policy layer between retriever and generator, with the withheld set retained as evidence.

**U3. More retention is strictly better.** "Non-lossy" is used as a virtue term (§2, §2.1) and never priced. No paper in this cluster asks what shouldn't be stored. *The alternative:* a system whose quality metric includes what it declined to keep — where an over-retention is a scored error, not a free win.

**U4. Every entity deserves a summary.** The entity summary was introduced to help resolution (§2.2.1) and then quietly promoted to a retrieval payload served to the generator (§3), with no version history and no invalidation path. Nobody asks whether a stored characterisation is a different kind of object from a stored fact. *The alternative:* summaries computed at read time and never persisted, so there is nothing to drift.

**U5. Extraction confidence doesn't exist.** LLM extraction is treated as a measurement, not an inference. The reflexion pass increases coverage; nothing estimates reliability; no field records how the item was obtained. *The alternative:* extraction that emits a distribution or an abstention, and a store that can hold "probably."

**U6. The consumer of memory is singular.** One `f: S → S` for all call sites. The idea that different callers might have different rights to the same store doesn't come up. *The alternative:* memory as a set of capability-scoped views — which is exactly your §7.

**U7. Evaluation is end-to-end QA judged by an LLM.** DMR and LongMemEval both score a generated answer against a golden one (§4). The memory layer is never measured directly — only through a generator, and only where a golden answer exists. *The alternative:* measuring the store itself — precision and recall of extraction, retention correctness, provenance accuracy — none of which requires a generator.

**U8. Benchmarks over deployments.** Every number comes from replayed synthetic conversations with no live user. Consequently no failure in the paper has a cost, and no design choice is disciplined by one. This is why U1 and U3 survive unexamined.

**U9. Ingestion cost is invisible.** Retrieval latency is reported to three significant figures with IQRs; ingestion runs roughly a dozen LLM calls per message and is never costed. The paper explicitly criticises the field for ignoring "production system scalability in terms of cost and latency" (§5) and then reports only the read side. *The alternative:* a write-side budget as a first-class design constraint — which for you decides D5.

---

## 4. Questions the paper never faced

Derived from your setting, not theirs.

**Q1. Does the exclusion boundary bind the raw store or only the derived layer?** §5 says third-party content "enters the context window, it does not enter the write path," while §9 says provenance is "the actual transcript, with a date." If transcripts persist, Priya's mother is in your database and the claim is really *not derived from*, not *not kept*. If they don't, your provenance artefact is a redaction and the *"here's what you actually said"* promise weakens. Zep never has to choose because non-lossy retention is free for them.

**Q2. What is the provenance object for a memory assembled from evidence across many transcripts?** Appendix C item 3 requires demonstrating exactly this. A single episode ID is a citation; fourteen episode IDs is a *characterisation with receipts* — which is closer to the thing §2 rules out than a plain fact is. Whether an observation shows all fourteen sources, a sample, or a count is a disclosure decision hiding inside a schema field.

**Q3. Can a suppression be wrong, and how is one undone?** "That's not me anymore" writes a suppression the extractor must respect forever (§9). That's a durable user-authored constraint on future extraction — the only such object in the system. If the user suppresses something that later becomes true again, does the pattern regrow? Does the suppression itself decay? Nothing in Zep has this shape, so there's no prior art on the failure mode.

**Q4. What is the dictation path's latency budget, and does it survive entity resolution?** §7 requires lexical and entity memory during transcription, which is real-time. Zep's read path is 2.58–3.20s (Table 2) — three orders of magnitude too slow for inline spelling correction. So the dictation path's store is not just permission-restricted, it's a different performance class. That may force it to be a materialised lexicon rather than a query over the memory graph, and then the question is when the lexicon is rebuilt and what happens between rebuilds.

**Q5. Is structural isolation between the two paths verifiable, or only asserted?** §7 says the dictation path is "structurally unable" to load observations and that this is "checkable in the evaluation" (Appendix C item 7). A check that the path *didn't* is a test; a check that it *can't* is a proof about the code. Which one you're claiming determines whether the isolation is a schema property, a process boundary, or a test assertion.

**Q6. What is the retention status of Kivi's own outputs?** Drafts Kivi wrote, and the user's edits to them, are the richest available signal — §2 names rewriting patterns as exactly what makes psychological profiling achievable, and the live hypothesis in Appendix A (*rewrites the pricing rationale repeatedly*) is derived from precisely this. So the same signal is both your best hypothesis source and your most dangerous one. Zep's analogous category is single-session-assistant, which is the one place their system got *worse*.

**Q7. What allocates the confirmation budget?** §8 rations prompts to "the highest-value uncertain memories." Value of what, to whom, measured how? Candidates: expected retrieval frequency, tier-promotion payoff, contradiction resolution (D18), decay rescue. This is a scheduling policy over a queue, and it's the only place where the user's attention is spent, so it's the one parameter whose mis-setting is directly felt.

**Q8. What happens to a hypothesis raised in an ephemeral Daari turn?** §6 says the answer "is not written to memory," but a hypothesis that has been *voiced* has been disclosed, and Appendix A carries a live hypothesis as a stored object. So some hypotheses are stored-as-questions (§4) and some are generated-and-discarded. What distinguishes them is undecided in the document, and it determines whether the "quiet file of unanswered questions" (§9) exists in the ephemeral path.

**Q9. Does a third party ever become a legitimate subject?** Priya is a client contact — a role — but also a person whose behaviour is observable across fourteen email threads. The rule in §5 ("could the fact be about the user's work, stated without characterising the other person?") is a per-fact test; it doesn't say what happens when a hundred permitted per-fact retentions add up to a profile of Priya. Aggregate leakage through individually-clean facts is a failure mode Zep's setting can't produce because it has no boundary to leak across.

**Q10. What is the single-user cost floor?** Zep amortises a heavy pipeline across enterprise volume. You have one user, a handful of entities, and an extraction pipeline that must run an exclusion check on every candidate. At your scale, per-transcript LLM cost is the dominant cost and there's nothing to amortise it against. Appendix B defers this; note that it interacts with D5, D16, and D29 — batch reprocessing, full-sweep contradiction detection, and periodic recompute are all things you can afford *only* at small scale, and they're each the better answer there.

---

## 5. Evaluation gap

**What they measured.** DMR: 500 five-session conversations, one QA pair each, LLM judge against a golden answer, single accuracy number (Table 1). LongMemEval-S: ~115k-token conversations, six question types, GPT-4o judge with the original paper's prompts, plus end-to-end latency, latency IQR, and average context tokens (Tables 2–3).

**What that can't distinguish.**

- **No ablations, anywhere.** Communities, BFS, the choice of reranker, the reflexion pass, the *n*=4 window, hybrid vs single-method search — none is isolated. Zep-with-communities and Zep-without would score identically on everything reported, and in fact **§4 suggests communities weren't used in the evaluation at all** (they retrieved edges and entity nodes only). For D11, D20, D21 and D2 the paper gives you precedent and no evidence.
- **Retention is unpriced, so D3, D4 and D13 are unmeasurable.** A system that retained nothing about third parties and a system that retained everything would score the same, because no question penalises over-retention. This is the largest gap for you: on their metrics, your §5 is invisible, and their metrics are the ones the field uses.
- **The store is never measured directly.** Everything is judged through a generator on a final answer. Extraction precision, merge errors (D12), summary drift (D7), invalidation correctness (D15) surface only when a question happens to depend on them. Two stores with very different contents can produce identical scores.
- **Abstention is untested.** LongMemEval's six reported categories are all answerable. Nothing measures a wrong-but-fluent answer, so D19 and D27 have no evidence attached — and worse, the metric *rewards* always answering. Any eval you inherit from here will silently penalise your §8.
- **Provenance is untested,** and the authors say so: the episode↔entity indices are "not directly examined in this paper's experiments" (§2.1). D25 has zero support.
- **Ingestion cost and latency are unreported.** Table 2 is read-side only. D5, D12, D16 and D29 are all cost-motivated choices whose costs are not in the paper.
- **Contradiction handling is only tested in the easy direction.** knowledge-update tests updates that are correct; nothing tests a correction that's itself wrong, or a conflict a human should arbitrate. D15's recency rule and a tier-aware rule would score the same. D18 has no evidence at all.
- **The comparison baseline is weak in a specific way.** On DMR, full-conversation context scored 94.4% vs Zep's 94.8% (gpt-4-turbo) and 98.0% vs 98.2% (gpt-4o-mini) — statistically indistinguishable on 500 items. **At small corpus sizes, their entire architecture is worth nothing over putting the transcripts in the prompt, by their own numbers.** Your corpus is small. Whatever justifies memory architecture for you, it is not retrieval accuracy — it has to be the things they didn't measure: non-retention, disclosure control, provenance, abstention.
- **One number deserves a hard look before you build on this line.** Single-session-preference — the category closest to your core product — shows the largest *relative* gain (+77.7% / +184%) from the worst *absolute* base: 30.0% → 53.3% and 20.0% → 56.7% (Table 3). The state of the art on preference recall is roughly a coin flip. If your product is *"you said this once, so say it once,"* this literature has not demonstrated that the thing works.

---

## Appendix: things the paper leaves underspecified

Listed so you don't spend time looking for them.

1. Which reranker(s) were used in the reported experiments (§3.2 lists five; §4 says only "the techniques described in Section 3").
2. Retrieval *k* — 20 edges + 20 nodes (§4) vs "top 10 most relevant nodes and edges" (§4.2).
3. Whether communities were constructed or retrieved during evaluation. The context template includes them (§3); the experimental description doesn't.
4. BFS hop count *n*, and how the three search methods' result sets are merged before reranking.
5. Whether ingestion is synchronous with the user turn; ingestion latency and cost entirely.
6. Whether entity and community summaries are versioned or invalidatable. Edges get four timestamps; summaries get none that's stated.
7. The reflexion pass — what it checks, whether it can remove as well as add.
8. Whether episodes are ever deleted, expired, or capped.
9. Handling of the `text` and `JSON` episode types ("this paper focuses on the message type," §2.1) — the structured-business-data claim in the abstract is not evaluated.
10. Community refresh cadence ("periodic," §2.3).
11. The fact-proposal step in §2.2.2 — the opening sentence is truncated in my extraction; I read the mechanism off the §6.1.3 prompt instead.
