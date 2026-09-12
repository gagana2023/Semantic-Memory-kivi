# Kivi Semantic Memory System Specification

Status: build specification derived from the position document, the resolved decision set, and the Golden Goose assignment brief.

Source notation used throughout:

- `P:Lx-y` means lines x-y of `kivi-semantic-memory-position.md`.
- `D:Qnn` means decision entry Qnn in `RESOLUTIONS.md`; `D:Ax` and `D:Bx` refer to its gap and conflict sections.
- `B:p.n` means the numbered page of `Kivi_Golden_Goose_Task_Final.pdf`; the quoted clause identifies the exact requirement.

Normative terms `MUST`, `MUST NOT`, `SHOULD`, and `SHOULD NOT` have their usual requirements meaning. Every `MUST` is release-blocking. A `SHOULD` may be waived only with a documented reason in evaluation output.

## 1. FUNCTIONAL REQUIREMENTS

### Capability A - Mode boundary and ordinary dictation

#### FR-01 - Explicit mode boundary - MUST

- **Requirement:** Ordinary dictation and Hey Kivi MUST be entered through distinct, explicit user actions and distinct request contracts. Request wording, tone, or retrieved content MUST NOT silently change one mode into the other.
- **Trigger:** The user starts ordinary dictation, or explicitly invokes Hey Kivi.
- **Observable result:** The interface labels the active mode; the response trace records `dictation` or `hey_kivi`; sending identical words through the two entry points exercises different memory rights.
- **Source:** P:L178-196; D:Q06, Q138, Q270, Q328; B:p.3, “Decide what belongs in each mode and make that boundary coherent.”

#### FR-02 - Ordinary-dictation memory rights - MUST

- **Requirement:** Ordinary dictation MUST use only lexical memory, entity names/relations needed for spelling, and stated formatting preferences. It MUST be structurally unable to retrieve observed memories, hypotheses, behavioral patterns, episodes for semantic use, or non-formatting preferences.
- **Trigger:** An ordinary-dictation request is submitted.
- **Observable result:** The returned writing may correct `Atlus` to `Atlas`, `Prea Raghavan` to `Priya Raghavan`, capitalization, and an explicitly stated formatting rule. Its inspection result contains no observed or hypothesised memory and no episode used as semantic context.
- **Source:** P:L184-196 and P:L274-284 claim 7; D:Q06, Q52, Q138, Q270; B:p.2 lines describing styles and phonetic memory, and B:p.3 mode-boundary clause.

#### FR-03 - Ordinary-dictation contract - MUST

- **Requirement:** In this text-client build, ordinary dictation MUST accept replayed raw ASR text and formatted text, return the final written text, persist the user-authored transcript, and queue semantic extraction without waiting for extraction to complete. Speech recognition and spoken output MUST NOT be prerequisites.
- **Trigger:** A valid ordinary-dictation record is submitted.
- **Observable result:** The user receives written text in the synchronous response; the response identifies the transcript and reports a pending or completed processing state; semantic processing adds no blocking step to that response.
- **Source:** P:L7, L184-196; D:Q62, Q97, Q98, Q580; B:p.3, “You do not need to build speech recognition… You may replay transcripts.”

### Capability B - Corpus import and learning

#### FR-04 - Push import of transcript corpus - MUST

- **Requirement:** The system MUST provide a documented push import accepting approximately 500 transcript-like records from one user. Every record MUST carry a caller-supplied transcript ID, raw ASR output, LLM-formatted output, occurrence time, and only the ordinary source metadata needed by the product. The same ingestion contract MUST accept the development corpus and a reviewer-supplied corpus.
- **Trigger:** A caller submits a corpus to the import API or its documented command wrapper.
- **Observable result:** A valid batch returns an import ID and per-record acceptance counts; invalid records are identified by index and transcript ID without silently truncating or discarding valid records.
- **Source:** D:E1, E3, Q97, Q98, Q372; B:p.4, “approximately 500 transcript-like records” and required record fields; B:p.5 import/process requirement.

#### FR-05 - Import ordering and idempotency - MUST

- **Requirement:** Import MUST process records in ascending `occurred_at` order. Reprocessing the same `transcript_id` with the same content MUST produce the same memory state, source set, and evidence counts. Reuse of that ID with different content MUST be rejected as a conflict.
- **Trigger:** Records arrive out of order, an import is repeated, or a transcript ID is reused.
- **Observable result:** Event time, not arrival order, governs supersession; a repeated identical import reports records as already present or reprocessed without duplicate memories or evidence inflation; conflicting reuse is reported and makes no write.
- **Source:** D:Q08, Q72, Q76, Q103, Q159, Q180, Q479; P:L235-239; B:p.5 review-corpus import requirement.

#### FR-06 - Asynchronous processing with completion state - MUST

- **Requirement:** Semantic extraction MUST run after the user-facing response and MUST expose import-level and record-level states: `queued`, `processing`, `processed`, `partially_processed`, `retrying`, and `quarantined`. An import MUST expose an unambiguous completion signal. A received but unprocessed transcript MUST remain discoverable through the labelled raw-transcript search path.
- **Trigger:** A live transcript or batch record is accepted.
- **Observable result:** The status API advances independently of the interaction; the import is complete only when no record is queued, processing, or retrying; a query that finds pending raw text labels it “not processed by memory yet.”
- **Source:** D:Q62, Q81, Q108, Q389, Q580; B:p.5 documented process/inspect requirement and B:p.7 seamless review path.

#### FR-07 - Eligible sources and atomic memory types - MUST

- **Requirement:** Only user dictations, user-authored Hey Kivi turns, and explicit user confirmation/correction events MAY produce memory. Application context, Kivi output, tool calls, and tool results MUST NOT be memory evidence. Each accepted candidate MUST be one complete, independently correctable `entity`, `preference`, or time-bearing `episode`; no summary or untyped fallback is allowed.
- **Trigger:** Extraction examines an accepted transcript or explicit user memory action.
- **Observable result:** Every created memory names an allowed type and at least one user source. The inspection view shows non-user context as available to the immediate task but ineligible for the write path.
- **Source:** P:L63-99, L103-122; D:Q12, Q33, Q86, Q99, Q153, Q154, Q168, Q181, Q198, Q235; B:p.4, “what it learns and what it deliberately ignores.”

#### FR-08 - Admission gates and prohibited content - MUST

- **Requirement:** Before a candidate becomes memory, it MUST pass, in order: category exclusion, third-party/work-level eligibility, typability, and completeness. The system MUST reject health; mood or emotional state; relationships and family; faith; politics; non-work finances; and character or competence characterisations. A user cannot override these exclusions.
- **Trigger:** Extraction produces a candidate or the user asks to save/correct a memory.
- **Observable result:** A prohibited candidate never appears in memory or answer context as a belief. Inspection records only a reason code and count, never the rejected content. A user attempt to force-save prohibited content is refused with the applicable category.
- **Source:** P:L29-46; D:Q20, Q73, Q169, Q305, Q307, Q442, Q573, Q604; B:p.4 learn/ignore requirement.

#### FR-09 - Third-party non-characterisation - MUST

- **Requirement:** Third-party application context MAY inform the current draft or reply but MUST NOT become memory evidence. Only limited work-world identity residue—canonical name, role, organisation, project association, and spelling—may be retained when it can be stated without characterising the person. Third-party state, circumstances, personal history, dispositions, and copied private content MUST be rejected.
- **Trigger:** A request contains text authored by or describing someone other than the user.
- **Observable result:** The immediate response can acknowledge the supplied context; memory may contain “Priya Raghavan is the Acme client contact” but not her family, illness, absence, apology, mood, or character. Transcript inspection shows a `read_not_kept` count without rejected content.
- **Source:** P:L21-25, L103-122; D:Q11, Q20, Q55, Q61, Q128, Q342, Q358; B:p.4 learn/ignore and provenance requirements. Qualification noted in D:B1-B3.

#### FR-10 - Duplicate, near-duplicate, and distributed evidence handling - MUST

- **Requirement:** Replaying one transcript MUST NOT add evidence. A distinct transcript expressing the same fact MUST add that transcript as evidence, increment the evidence count once, and update last-seen time without changing tier. Overlapping or near-duplicate candidates MUST merge only after a positive sameness decision; ambiguous overlap MUST remain separately correctable.
- **Trigger:** A candidate resembles an existing memory or a transcript is replayed.
- **Observable result:** Inspection distinguishes `duplicate_transcript`, `same_fact_new_evidence`, and `separate_overlapping_fact`; the source list can demonstrate one memory assembled across multiple dictations; evidence accumulation never auto-promotes it.
- **Source:** P:L75-92 and P:L274-284 claim 3; D:Q08, Q16, Q92, Q159, Q173, Q191, Q449, Q479; B:p.5 distributed-information requirement.

#### FR-11 - Contradiction and current truth - MUST

- **Requirement:** A contradiction below stated tier MUST be resolved by tier, then event-time recency, by making the winner current and preserving the loser as auditable superseded history. A contradiction involving a stated memory MUST NOT silently override it: Anbu abstains, Koottu surfaces the disagreement, and an eligible high-value case may request user confirmation. An explicit user correction overrides all tiers.
- **Trigger:** New eligible evidence contradicts a current memory or retrieved current memories disagree.
- **Observable result:** Only an unconflicted current version can govern a factual answer; displaced versions and their sources remain visible in history; stated-level conflict remains visible until the user resolves it.
- **Source:** P:L235-238; D:Q03, Q13, Q66, Q133, Q174, Q206, Q310, Q789, Q855.

#### FR-12 - Extraction outcomes and recovery - MUST

- **Requirement:** Each transcript MUST end in one distinguishable extraction outcome: nothing found; candidates found and stored; candidates found and all dropped; partially processed; or failed/quarantined. Ambiguous or unsupported candidates MUST be reason-coded drops, not low-confidence facts or hypotheses. Model or parse failures MUST be retried with bounded backoff and then quarantined, never silently marked processed.
- **Trigger:** Extraction completes, returns malformed output, times out, or yields ambiguous/zero candidates.
- **Observable result:** Transcript inspection shows exactly one current outcome plus attempt history; useful completed candidates survive a partial failure; quarantined transcripts remain visible and unprocessed.
- **Source:** D:Q72, Q81, Q86, Q108, Q109, Q152, Q171, Q183, Q394, Q564, Q675; P:L202-225; B:p.4 failures-visible requirement.

### Capability C - Memory semantics and lifecycle

#### FR-13 - Memory contract and provenance - MUST

- **Requirement:** Every memory MUST expose an immutable ID, type, tier, human-readable content, evidence count, source transcript IDs, first-seen time, last-seen time, last-confirmed time when applicable, pin state, lifecycle status, and version history. A memory missing type, tier, content, or source MUST NOT exist as an active memory.
- **Trigger:** A memory is created, retrieved, listed, or inspected.
- **Observable result:** All required fields are present and source IDs resolve to dated source transcripts; current and historical versions are distinguishable.
- **Source:** P:L63-99, L229-245; D:Q17, Q28, Q86, Q309, Q412, Q518, Q535; B:p.4 representation/lifecycle and provenance requirements.

#### FR-14 - Tier semantics and promotion - MUST

- **Requirement:** `stated` memories MAY be treated as true; `observed` memories MAY only be presented as evidence-backed patterns and MUST NOT be silently enforced; `hypothesised` memories MUST be grammatical questions, MUST NOT be asserted or acted upon, and remain subject to every exclusion. No memory may self-promote. Promotion to stated requires an explicit timestamped user confirmation; silence is not confirmation.
- **Trigger:** Evidence accumulates, a memory is selected for disclosure, or the user confirms it.
- **Observable result:** Twenty repeated observations remain observed until confirmation; a hypothesis is rendered as a question; a confirmation produces a stated version and recorded confirmation event.
- **Source:** P:L75-99, L215-220; D:Q42, Q191, Q291, Q582, Q738; D:Q604 resolves D:B10 by making exclusions higher precedence.

#### FR-15 - Rationed confirmation prompts - MUST

- **Requirement:** The system MUST NOT present a review queue. It MAY issue confirmation prompts only when the uncertain memory is relevant to the current request, within a configured weekly cap, and selected by the configured value rule. It MUST record whether a prompt was spent and MUST treat no reply as no confirmation.
- **Trigger:** An observed memory or unresolved stated-level contradiction is relevant during a Hey Kivi request.
- **Observable result:** Any prompt is attached to that response, reports the memory concerned, and consumes one unit of the visible weekly budget; once the cap is reached no further prompt appears that week.
- **Source:** P:L204-220; D:Q135, Q191, Q310, Q611; numeric cap and selection rule intentionally open in D:A1.6-A1.7.

#### FR-16 - Time, decay, expiry, and pinning - MUST

- **Requirement:** An unpinned observation that is not re-observed within the configured window MUST lose surfacing rights; an unpinned, unconfirmed hypothesis not re-raised within its window MUST expire; retrieval recency MUST change as time passes. Stated and pinned memories MUST NOT decay automatically, and no tier may promote automatically. Capacity alone MUST NOT evict memory.
- **Trigger:** The lifecycle sweep runs or retrieval occurs after time has passed.
- **Observable result:** Decayed observations stop appearing as current candidates, expired hypotheses leave the active surface, and stated or pinned items remain active; inspection identifies the lifecycle reason and effective time.
- **Source:** P:L229-245; D:Q24, Q54, Q137, Q147, Q178, Q266, Q283, Q407, Q525; window values open in D:A1.2-A1.3.

### Capability D - Hey Kivi actions, retrieval, and answers

#### FR-17 - Deliberately narrow tool set - MUST

- **Requirement:** Hey Kivi MUST expose exactly three model-callable tools in v1: `recall_search`, `draft_reply`, and `schedule_reschedule`. A request outside these capabilities MUST receive a clear unsupported-capability result and MUST NOT trigger an invented tool or apparent external action.
- **Trigger:** A Hey Kivi request is routed to a tool.
- **Observable result:** The trace lists the three available tools, the selected tool or `none`, and the reason; no fourth tool can be selected.
- **Source:** P:L264-272; D:Q244, Q246; B:p.4, “Implement only the Hey Kivi tools required… narrow… beats broad.” Internal inconsistency noted in D:A4.23 and retained in Open Questions.

#### FR-18 - Grounded recall/search - MUST

- **Requirement:** `recall_search` MUST answer any reasonable question whose answer is present in or derivable from the supplied user history within the three supported memory types. It MUST be able to combine evidence from separate dictations. On compiled-memory miss it MUST perform one bounded, labelled lexical fallback over raw transcripts; raw hits MUST NOT be represented as memories.
- **Trigger:** The user asks Hey Kivi to recall or search their work history.
- **Observable result:** A supported answer cites every memory and source used; a raw fallback is labelled; a miss returns an abstention with the search description and genuine near misses.
- **Source:** D:Q211, Q389, Q675, Q841; P:L202-225 and P:L274-284 claims 3 and 5; B:p.5, definition of “answer any question,” distributed information, groundedness, refusal, and provenance clauses.

#### FR-19 - Retrieval and disclosure are separate - MUST

- **Requirement:** Every Hey Kivi request MUST retrieve across all memory types and tiers before applying permission. Candidate order MUST be deterministic: fused relevance, pinned, tier, evidence, then recency. Permission MUST filter disclosure, not ranking. Superseded facts MUST be excluded from current-fact use but MAY support observations about change.
- **Trigger:** A valid Hey Kivi request begins.
- **Observable result:** The trace exposes retrieved, withheld, used, budget-dropped, and raw-fallback sets separately, including ranking factors and withholding reason; the underlying retrieved set remains the same when only Anbu/Koottu permission changes.
- **Source:** P:L126-174; D:Q26, Q35, Q56, Q133, Q193, Q315, Q487, Q631, Q826.

#### FR-20 - Anbu behavior - MUST

- **Requirement:** Anbu MUST be the default persistent permission. It may use stated memory only, returns the requested result without volunteering patterns or reasons, and withholds observed and hypothesised content. When a relevant observation is withheld, the response MUST show only the quiet affordance “Kivi noticed something here”; opening it reveals that observation once without changing the persistent mode.
- **Trigger:** A Hey Kivi request is made while permission is Anbu.
- **Observable result:** The result uses applicable stated facts/preferences, shows no observation or hypothesis content unless the user opens the one-time affordance, and the trace names every withheld memory and required permission.
- **Source:** P:L130-136, L150-174; D:Q268, Q328, Q421, Q631, Q826; P:L274-284 claim 4.

#### FR-21 - Koottu behavior - MUST

- **Requirement:** Koottu MUST be an explicit persistent permission. It may use stated memories and surface relevant observed patterns with evidence, but MUST NOT guess causes or treat an observation as a rule.
- **Trigger:** The user selects Koottu and makes a relevant Hey Kivi request.
- **Observable result:** The response performs the requested action and may add a clearly labelled observation with evidence count and dates; no hypothesis is shown unless separately invited for that request.
- **Source:** P:L138-142, L150-173; D:Q291, Q328, Q826; P:L274-284 claim 4.

#### FR-22 - Daari per-request invitation - MUST

- **Requirement:** Daari MUST NOT be a persistent mode. A clear per-request invitation to explain a work-level pattern may unlock one relevant hypothesis for that response only. The hypothesis MUST be phrased as a correctable question, MUST NOT cross an excluded category, MUST NOT be acted on, and MUST NOT be written back as a belief unless explicitly confirmed.
- **Trigger:** The user explicitly asks a “why/what do you think” question about a relevant work pattern.
- **Observable result:** The response includes at most the invited, question-form hypothesis; the saved permission remains Anbu or Koottu; repeating the base request without invitation omits it.
- **Source:** P:L144-158, L215-220; D:Q291, Q328, Q573, Q604; ambiguity retained in D:A4.25 and tension in D:B9-B10.

#### FR-23 - Grounding, low confidence, and abstention - MUST

- **Requirement:** Every factual claim in a Hey Kivi answer MUST resolve to a retrieved current memory or explicitly labelled raw transcript. If evidence is absent, ambiguous, contradictory at stated tier, below the configured match threshold, partially unavailable, or generation fails/times out, Kivi MUST return a successful abstention result rather than guess. The abstention MUST state what is missing, what was searched, genuine near misses, and what failed, with a trace.
- **Trigger:** Retrieval or answer generation cannot support the requested claim under the current permission.
- **Observable result:** The API returns `outcome: abstained`, not an invented answer or an empty list; all near misses are labelled as such; a partial retrieval-leg failure is visible and never silently used.
- **Source:** P:L200-225; D:Q04, Q27, Q45, Q69, Q106, Q183, Q329, Q392, Q474, Q675, Q771, Q789; B:p.5 refusal-to-invent requirement.

#### FR-24 - Memory-aware drafting - MUST

- **Requirement:** `draft_reply` MUST draft from the user's instruction and supplied application context, applying relevant stated content and formatting preferences. Under Koottu it MAY offer an observed preference but MUST NOT silently apply it; under Daari it MAY ask an invited work-level hypothesis but MUST NOT let that hypothesis change the draft. Third-party context may affect the draft but not memory.
- **Trigger:** A Hey Kivi draft/reply request supplies an instruction and optional text context.
- **Observable result:** The returned draft is attributable to the supplied inputs and cited memories; tier effects are visible in the response/trace; no unsupported recipient facts appear and no third-party personal content becomes memory.
- **Source:** P:L83-88, L103-122, L126-174; D:Q12, Q55, Q128, Q153, Q246, Q288; B:p.3 useful use-case and memory-influences-tool clauses.

#### FR-25 - Internal schedule/reschedule - MUST

- **Requirement:** `schedule_reschedule` MUST create or change only an event in the demonstration's internal state. It MUST NOT claim to have updated a live calendar or external service. It may use grounded entity and episode memory to resolve the event; ambiguity or absent dates MUST produce abstention rather than an invented date.
- **Trigger:** A Hey Kivi request clearly asks to schedule or reschedule an event.
- **Observable result:** Success returns an internal event ID, previous value when rescheduling, new scheduled time, and cited memories; external side effects are reported as `none`; repeating the same idempotent request does not duplicate the event.
- **Source:** D:Q237, Q246, Q288; P:L264-272; B:p.4 permits a replay client and requires real state rather than a canned sequence.

### Capability E - User control and inspection

#### FR-26 - Human memory surface - MUST

- **Requirement:** A normal-user memory surface MUST show all active memories grouped as “Things you told me,” “Things I've noticed,” and “Things I'm wondering about.” Each entry MUST show content, evidence count, last-seen date, pin state, and available action; opening it MUST show dated source transcripts and version history. It MUST use human language rather than developer terminology.
- **Trigger:** The user opens the memory surface or a memory entry.
- **Observable result:** Every memory is findable in exactly one tier group, and every listed source opens to the stored transcript; no developer console or system explanation is required to understand the entry.
- **Source:** P:L229-246; D:Q405, Q535, Q543, Q621; B:p.3 normal-user interface and control requirement.

#### FR-27 - Confirm, correct, and inline correction - MUST

- **Requirement:** `Confirm` MUST promote the selected memory to stated and record the event. `Correct` and an unambiguous inline correction during Hey Kivi MUST synchronously create a stated replacement, preserve the prior version in history, and write a durable suppression against re-deriving the old belief. A no-op correction MUST be rejected.
- **Trigger:** The user confirms or corrects a memory in the memory surface or explicitly corrects it inside a request.
- **Observable result:** Subsequent retrieval immediately uses the replacement; the old version is historical; reprocessing every source cannot restore the old belief; failure to commit the suppression is shown as a failed action, not partial success.
- **Source:** P:L215-220, L229-245; D:Q15, Q46, Q50, Q191, Q506, Q557, Q611, Q738, Q839; P:L274-284 claim 6.

#### FR-28 - Demote, forget, and pin - MUST

- **Requirement:** `That's not me anymore` MUST remove surfacing rights and write a durable suppression. `Forget` MUST remove the selected belief and its memory history from the memory surface/retrieval and write the minimum suppression needed to prevent re-derivation; it does not delete source transcripts. Pin/unpin MUST immediately change retrieval priority, and pinned memories MUST not decay. All actions MUST be one-step user actions; their actual persistence effects MUST be disclosed before execution.
- **Trigger:** The user invokes a named action on one memory.
- **Observable result:** Demoted/forgotten content no longer affects future answers; reprocessing does not regrow it; pin state changes ranking; the action receipt states what remains (source transcript and suppression). Repeating the same action is harmless.
- **Source:** P:L229-245; D:Q15, Q46, Q178, Q309, Q315, Q595, Q738, Q791; naming/retention tension in D:B2, B5 and confirmation gap in D:A3.14.

#### FR-29 - Why trace for every Hey Kivi result - MUST

- **Requirement:** Every Hey Kivi answer, abstention, and unsupported-capability result MUST have an inspectable trace containing the request, search description, all retrieved memories, withheld items and reasons, items used, budget drops, raw fallback hits, tool candidates and selected tool, tool result, citations, failure/degradation states, timings, model usage, and attributable cost. Source transcript content MUST be reachable from each memory in one additional action.
- **Trigger:** A Hey Kivi request reaches a terminal outcome.
- **Observable result:** The response includes a trace ID; the human Why view explains the decision without scores or model jargon; the inspection API exposes the measurements required for review; an abstention trace is as complete as a successful answer trace.
- **Source:** P:L200-225, L241-246; D:E4, Q56, Q405, Q550, Q631, Q663; B:p.4 per-result inspection list and metrics clause; B:p.5 engineer-inspection requirement.

#### FR-30 - Transcript inspection - MUST

- **Requirement:** Every transcript MUST have a first-class inspection result showing original raw ASR, formatted text, metadata, processing state and attempts, memories created/updated/superseded, evidence merged, reason-coded drops without dropped content, `read_not_kept` count, failures, and whether it affected any inspected answer.
- **Trigger:** A user or reviewer opens a transcript or follows a provenance link.
- **Observable result:** The reviewer can distinguish “nothing found,” “all dropped,” “partially processed,” and “failed”; each created/changed memory is navigable; any answer trace that used it is linkable.
- **Source:** P:L42-46, L113-122, L222-246; D:E4, Q16, Q81, Q102, Q109, Q171, Q199, Q405; B:p.4 original-input/memory/provenance/reason requirements.

### Capability F - Persistence, evaluation, and reviewability

#### FR-31 - Real persistent behavior - MUST

- **Requirement:** The visible experience MUST be driven by real persisted transcripts, memories, lifecycle changes, retrieval, permission decisions, tool state, and model decisions. State MUST survive an ordinary process restart. No answer or inspection result may depend on a demo-only scripted sequence.
- **Trigger:** The application is restarted after import and then queried or inspected.
- **Observable result:** Imported memories, user corrections, suppressions, pins, internal scheduled events, and traces remain; the same grounded request operates on that state.
- **Source:** D:E2, Q134, Q337, Q447; B:p.3, “actual state, persistence, retrieval, and model decisions—not… prepared only for the demonstration.”

#### FR-32 - Reproducible complete-pipeline evaluation - MUST

- **Requirement:** The repository evaluation MUST run the complete pipeline over the approximately 500-record development corpus and fixed test cases without ingesting evaluation questions as memory. For every case it MUST retain the original input, starting memory state, created/retrieved/changed/rejected memory, provenance, Hey Kivi behavior, reason, and visible failure. It MUST test the seven position claims and the brief's grounded-question behavior, and report retrieval latency, end-to-end latency, database growth, model identity/usage, and whole-pipeline monetary cost.
- **Trigger:** The documented candidate-evaluation procedure is run from a reset system.
- **Observable result:** It produces a deterministic, inspectable report with per-case pass/fail and aggregate measured metrics; failures and abstentions remain in the report; no evaluation question appears among source transcripts.
- **Source:** P:L250-284; D:Q139, Q370, Q477, Q509, Q593, Q651, Q720, Q796, Q841; B:p.4 reproducible-evaluation clause and B:p.5 evaluation criteria.

#### FR-33 - Foreign-corpus review path and reset - MUST

- **Requirement:** A reviewer MUST be able to reset the system, import and process a translated internal corpus of approximately 500 dictations from one user, wait for a definitive completion state, inspect resulting state, operate ordinary dictation and Hey Kivi, and run evaluation using only the documented primary review method. Reset MUST be an operator-only local action, not a network-exposed HTTP endpoint.
- **Trigger:** A reviewer follows `RUN.md` from the submitted commit.
- **Observable result:** Each documented command or interaction works without undocumented dashboard work or clarification; after reset, prior corpus-derived state and evaluation output are absent while reproducible seed state is restored as documented.
- **Source:** D:E1-E3, Q97, Q107, Q580, Q612; B:p.5 foreign-corpus procedure and B:pp.6-7 complete `RUN.md` and seamless-review requirements.

## 2. NON-GOALS

The following list is the deliberate v1 learning boundary. Items are excluded because they either violate the position's trust model or do not help the narrow goal of removing re-explanation.

1. **Psychological or personal profiling.** Kivi will not learn health, mood/emotional state, family or relationships, faith, politics, non-work finances, competence, character, motivations, insecurities, self-image, interpersonal disposition, or diagnoses. Work goals may exist only as explicit project facts or preferences, never as inferred motives. Reason: unverifiable characterisations are difficult to correct and turn a work assistant into a system that studies the user. Source: P:L29-46; D:Q169, Q305, Q442, Q573, Q604.
2. **Plausible personal inference.** Kivi will not infer that late dictation means the user is behind, that repeated rewriting proves conflict avoidance, or similar explanations. Narrow entity normalisation is allowed; patterns remain observations, and allowed work-level reasons remain invited questions. Reason: plausibility is not provenance. Source: P:L35-45, L83-92; D:Q152, Q520, Q573.
3. **Third-party personal memory.** Kivi will not retain another person's health, family, absence, apology, mood, private circumstances, character, communication history, or a general profile. Only limited name/role/organisation/project/spelling residue is eligible. Reason: the other person did not consent. Source: P:L103-122; D:Q11, Q55, Q128, Q358; qualification D:B1-B2.
4. **Cross-user, team, or shared memory.** There is no second user, organisation-wide knowledge pool, transfer, social graph, consent routing, or multi-tenant sharing. Reason: the brief's review corpus is one user and the position forbids transferring other people's information. Source: D:E1, Q273, Q277; B:p.5 “approximately 500 dictations from one user.”
5. **Narrative, profile, or rolling summaries.** The system will not build conversation summaries, topic narratives, aggregate biographies, timelines as a durable semantic unit, or a “what Kivi knows about me” prose profile. Reason: sentences inside such artifacts cannot carry independent tier, evidence, provenance, or correction. Source: P:L63-99; D:Q17, Q33, Q154, Q535, Q570, Q766.
6. **Procedural and self-improvement memory.** Kivi will not remember tool sequences, learn skills, train on accepted drafts, retain its own answers as evidence, reflect on failures, adapt model weights, or learn from implicit silence/acceptance. Reason: those events are Kivi's behavior, not user-authored durable facts. Source: D:Q12, Q131, Q153, Q198, Q235, Q458, Q700.
7. **Automatic authority.** Repetition will not turn an observation into a stated rule; the system will not autonomously rewrite a stated belief; tone will not grant inference permission. Reason: user confirmation is the sole route to stated authority. Source: P:L83-92, L150-158; D:Q191, Q269, Q291, Q328.
8. **Continuous confidence, salience, importance, or causal models.** Memory has categorical tier and evidence count, not a probability, psychological importance score, causal graph, counterfactual model, or diagnosis. Reason: these are not legible user permissions and enable ungrounded inference. Source: D:Q42, Q100, Q215-Q229, Q537, Q572.
9. **Broad or agentic tool use.** No browsing, code execution, live messaging, live email, live calendar, autonomous multi-step plans, tool loops, rollouts, debate, or specialist agents. Reason: the fixed three-tool surface is the smallest complete demonstration. Source: D:Q237, Q244, Q246, Q252, Q508; B:p.4 narrow-tools clause.
10. **Live external integrations.** The schedule tool changes only internal demonstration state; recall does not fetch the outside world; drafting does not send. Reason: the chosen environment is the replayed text client. Source: P:L7; D:Q237, Q288.
11. **Audio, images, files, speech recognition, or spoken output.** The product accepts text transcript records and text application context only. Reason: the assignment permits replay, and the position explicitly scopes a text client. Source: P:L7; D:Q98, Q372; B:p.3 speech-recognition waiver.
12. **Raw history as ordinary semantic memory.** Full transcripts are provenance and a single bounded recall fallback, not the primary memory representation and not silently mixed with memory hits. Reason: raw history has no tier and cannot be individually governed. Source: D:Q17, Q28, Q211, Q389.
13. **Capacity-driven forgetting and scale claims.** No least-recently-used eviction, clustering, hot/warm/cold tiers, or claim of suitability beyond the brief's approximately 500-transcript scale. Reason: these add breadth without serving a required claim; decay is about standing, not capacity. Source: D:Q54, Q179, Q679, Q687, Q795.
14. **Ambient ingestion.** No watched folder, polling, automatic access to user applications, or undeclared data source. Reason: the reproducible review path requires explicit push import. Source: D:Q97; B:p.7 reviewer procedure.
15. **A developer console as product UI.** Technical inspection is available through the first-class inspection contract, but the normal user experience remains the Memory surface and Why view. Reason: the brief requires a normal-user interface, while also requiring engineer inspection. Source: P:L222-246; D:E4, Q543; B:pp.3-5.

## 3. API CONTRACTS

### 3.1 Contract-wide rules

- **Base path and format:** HTTP endpoints use `/v1` and JSON. Times are RFC 3339 timestamps with an explicit offset. IDs are opaque strings. Unknown request fields are rejected with `422 INVALID_INPUT` so imports cannot silently lose data. Source: D:E2, Q70, Q86; B:p.5 documented-import requirement.
- **Authentication:** In the primary localhost review mode, no HTTP authentication is required and the listener MUST be local-only. If any endpoint is network-exposed, every endpoint requires `Authorization: Bearer <token>` and returns `401 UNAUTHENTICATED` when missing or invalid. There are no user/tenant selectors in the API. Source: D:E1, Q107.
- **Idempotency:** `GET`, `PUT`, and `DELETE` are idempotent by method semantics. Side-effecting `POST` endpoints require `Idempotency-Key`, except transcript ingestion where `transcript_id` is the primary idempotency key. Repeating a key with a byte-equivalent normalized request returns the original status and body with `Idempotency-Replayed: true`; reusing it for a different request returns `409 IDEMPOTENCY_CONFLICT`. Source: D:Q08, Q46, Q103, Q159, Q479.
- **Successful abstention:** An unsupported, missing-history, low-confidence, partial-retrieval, contradiction, or model-failure outcome that reaches a persisted trace returns HTTP `200` with `outcome: "abstained"` or `outcome: "unsupported"`. These are product results, not transport errors. Source: D:Q04, Q27, Q45, Q392.
- **Common error body:** All non-2xx responses use the following shape. `details` may be empty but no other top-level error form is allowed. Source: D:E2, E4, Q81, Q108, Q183.

```json
{
  "error": {
    "code": "INVALID_INPUT",
    "message": "records[1].raw_asr must not be blank",
    "details": [
      { "field": "records[1].raw_asr", "reason": "blank" }
    ],
    "request_id": "req_01K4T6R3ME7V8Q5YJ2P0",
    "retryable": false
  }
}
```

- **Common status meanings:** `400 INVALID_JSON`; `401 UNAUTHENTICATED` in hosted mode; `404 NOT_FOUND`; `409 IDEMPOTENCY_CONFLICT`, `CONTENT_CONFLICT`, `VERSION_CONFLICT`, or `MEMORY_UNCHANGED`; `422 INVALID_INPUT`; `503 STATE_UNAVAILABLE` when the request cannot be safely persisted or traced. Model and retrieval failures after a trace exists use a 200 abstention instead of `503`. Source: D:Q08, Q27, Q46, Q86, Q107, Q183, Q392.

The HTTP surface below is complete for v1. Reset is deliberately not an HTTP endpoint; its operator contract appears in §3.4. Source: D:E5, Q107, Q246; B:p.7 reset requirement.

### 3.2 Interaction, ingestion, and permission endpoints

#### API-01 - Create corpus import

- **Method/path:** `POST /v1/imports`
- **Request shape:** `records` is a non-empty array. Each item requires `transcript_id`, non-blank `raw_asr`, non-blank `formatted_text`, `occurred_at`, and `metadata`. `metadata.source` is required; `metadata.application`, `metadata.channel`, and `metadata.language` are optional. No record may identify a second account owner.
- **Response shape:** HTTP `202`; import ID, state, submitted/accepted/rejected counts, ordered record errors, status URL, and creation time.
- **Statuses:** `202`, `400`, `401`, `409`, `422`, `503`.
- **Idempotency/auth:** Records are idempotent on transcript ID and content. An optional batch `Idempotency-Key` also protects the import request. Contract-wide auth applies.
- **Source:** FR-04-FR-06; D:Q08, Q76, Q97, Q102; B:pp.4-5.

Example request:

```http
POST /v1/imports
Content-Type: application/json
Idempotency-Key: corpus-meera-v1

{
  "records": [
    {
      "transcript_id": "tr_2026-03-12_0017",
      "raw_asr": "reply to priya move the atlas review to next tuesday",
      "formatted_text": "Reply to Priya: move the Atlas review to next Tuesday.",
      "occurred_at": "2026-03-12T17:04:11+05:30",
      "metadata": {
        "source": "dictation",
        "application": "Slack",
        "channel": "design-review",
        "language": "en-IN"
      }
    }
  ]
}
```

Example response:

```json
{
  "import_id": "imp_01K4T70C9QH4A2M8Y6RN",
  "state": "queued",
  "submitted": 1,
  "accepted": 1,
  "rejected": 0,
  "record_errors": [],
  "status_url": "/v1/imports/imp_01K4T70C9QH4A2M8Y6RN",
  "created_at": "2026-09-11T10:00:00+05:30"
}
```

#### API-02 - Inspect import status

- **Method/path:** `GET /v1/imports/{import_id}`
- **Request shape:** Path parameter only.
- **Response shape:** HTTP `200`; terminal/non-terminal state, counts by record state, progress, start/end times, measured processing duration, model usage and cost to date, record summaries, and `complete` boolean. `complete` is true only when queued, processing, and retrying are all zero.
- **Statuses:** `200`, `401`, `404`, `503`.
- **Idempotency/auth:** Read-only. Contract-wide auth applies.
- **Source:** FR-06, FR-32-FR-33; D:Q81, Q108, Q580, Q842; B:pp.4-5.

Example request and response:

```http
GET /v1/imports/imp_01K4T70C9QH4A2M8Y6RN
```

```json
{
  "import_id": "imp_01K4T70C9QH4A2M8Y6RN",
  "state": "completed_with_quarantine",
  "complete": true,
  "counts": {
    "submitted": 500,
    "processed": 496,
    "partially_processed": 2,
    "quarantined": 2,
    "queued": 0,
    "processing": 0,
    "retrying": 0
  },
  "started_at": "2026-09-11T10:00:02+05:30",
  "completed_at": "2026-09-11T10:18:44+05:30",
  "duration_ms": 1122000,
  "usage": { "model_calls": 1028, "input_tokens": 884120, "output_tokens": 119442 },
  "cost": { "currency": "USD", "amount": 3.84 },
  "records": [
    { "transcript_id": "tr_2026-03-12_0017", "state": "processed", "inspection_url": "/v1/transcripts/tr_2026-03-12_0017/inspection" },
    { "transcript_id": "tr_2026-04-02_0044", "state": "quarantined", "inspection_url": "/v1/transcripts/tr_2026-04-02_0044/inspection" }
  ]
}
```

#### API-03 - Submit ordinary dictation

- **Method/path:** `POST /v1/dictations`
- **Request shape:** One transcript record with the same required fields as an import item. `raw_asr` and `formatted_text` are replay inputs; `occurred_at` and metadata provide provenance.
- **Response shape:** HTTP `201` for a new transcript or `200` for an identical replay; final written text, explicit `dictation` surface, allowed-memory uses, transcript ID, and processing state.
- **Statuses:** `200`, `201`, `400`, `401`, `409`, `422`, `503`.
- **Idempotency/auth:** Idempotent on transcript ID plus content; different content under an existing ID returns `409 CONTENT_CONFLICT`. Contract-wide auth applies.
- **Source:** FR-01-FR-03, FR-05; D:Q08, Q52, Q62, Q97.

Example request:

```http
POST /v1/dictations
Content-Type: application/json

{
  "transcript_id": "tr_2026-09-11_0001",
  "raw_asr": "send the atlus recap to prea raghavan",
  "formatted_text": "Send the Atlas recap to Priya Raghavan.",
  "occurred_at": "2026-09-11T10:21:33+05:30",
  "metadata": { "source": "dictation", "application": "Kivi", "language": "en-IN" }
}
```

Example response:

```json
{
  "outcome": "written",
  "surface": "dictation",
  "text": "Send the Atlas recap to Priya Raghavan.",
  "transcript_id": "tr_2026-09-11_0001",
  "memory_uses": [
    { "kind": "entity", "memory_id": "mem_atlas_001", "effect": "canonical_spelling" },
    { "kind": "entity", "memory_id": "mem_priya_001", "effect": "canonical_spelling" }
  ],
  "semantic_processing": "queued"
}
```

#### API-04 - Make a Hey Kivi request

- **Method/path:** `POST /v1/hey-kivi/requests`
- **Request shape:** Requires `text`; optional `application_context` array contains text usable for the current request but ineligible as memory evidence; optional bounded `turn_history` contains literal user/assistant turns in the active conversation; optional `occurred_at`. Permission is read from the persistent setting; Daari invitation is expressed in `text`, not a hidden permission flag.
- **Response shape:** HTTP `200`; terminal `outcome` (`completed`, `abstained`, or `unsupported`), selected tool or `null`, answer text, tool result when any, citations, abstention details when any, trace ID, and queued processing state for the user-authored turn.
- **Statuses:** `200`, `400`, `401`, `409`, `422`, `503`. A model timeout with a saved trace returns `200 abstained`; inability to save a trace returns `503`.
- **Idempotency/auth:** `Idempotency-Key` is required because tools may mutate internal state. Replays return the original result and do not repeat a tool action. Contract-wide auth applies.
- **Source:** FR-01, FR-17-FR-25, FR-29; D:Q244, Q250, Q260, Q508, Q826.

Example request:

```http
POST /v1/hey-kivi/requests
Content-Type: application/json
Idempotency-Key: hk-meera-20260911-1026-1

{
  "text": "What did Arun say about the auth migration?",
  "occurred_at": "2026-09-11T10:26:00+05:30",
  "application_context": []
}
```

Example response:

```json
{
  "outcome": "abstained",
  "tool": "recall_search",
  "answer": "I don't have anything from Arun about an auth migration. I found Arun on Atlas backend work in four sources, and a database migration discussion from 6 March with Priya.",
  "citations": [],
  "abstention": {
    "reason_code": "NOT_IN_HISTORY",
    "searched_for": ["Arun", "auth migration"],
    "near_misses": [
      { "label": "Arun on Atlas backend work", "source_count": 4, "memory_id": "mem_arun_backend_001" },
      { "label": "Database migration discussion", "occurred_at": "2026-03-06T16:11:00+05:30", "transcript_id": "tr_2026-03-06_0009" }
    ]
  },
  "trace_id": "trace_01K4T7JYKW1N8R6C3QAP",
  "user_turn_processing": "queued"
}
```

#### API-05 - Read permission setting

- **Method/path:** `GET /v1/permission`
- **Request shape:** No body.
- **Response shape:** HTTP `200`; persistent mode and plain-language promise. Daari never appears as persistent state.
- **Statuses:** `200`, `401`, `503`.
- **Idempotency/auth:** Read-only. Contract-wide auth applies.
- **Source:** FR-20-FR-22; P:L126-174; D:Q328.

Example request and response:

```http
GET /v1/permission
```

```json
{
  "mode": "anbu",
  "label": "Do",
  "promise": "I'll do what you said, without making you repeat yourself."
}
```

#### API-06 - Change permission setting

- **Method/path:** `PUT /v1/permission`
- **Request shape:** `{ "mode": "anbu" | "koottu" }`. Any other value, including `daari`, is invalid.
- **Response shape:** HTTP `200`; resulting mode, label, promise, and change time.
- **Statuses:** `200`, `400`, `401`, `422`, `503`.
- **Idempotency/auth:** Repeating the same mode is a no-op success. Contract-wide auth applies.
- **Source:** FR-20-FR-22; P:L150-174; D:Q328.

Example request and response:

```http
PUT /v1/permission
Content-Type: application/json

{ "mode": "koottu" }
```

```json
{
  "mode": "koottu",
  "label": "Notice",
  "promise": "I'll tell you what I've noticed, even if you'd rather not hear it.",
  "changed_at": "2026-09-11T10:30:00+05:30"
}
```

### 3.3 Memory and inspection endpoints

#### API-07 - List memories

- **Method/path:** `GET /v1/memories?tier={tier}&status={status}&pinned={boolean}`
- **Request shape:** All query parameters are optional. Valid tiers are `stated`, `observed`, and `hypothesised`; default status is `active`.
- **Response shape:** HTTP `200`; three tier groups, each containing complete memory summaries, plus total count and effective filters. The endpoint returns the complete v1-scale result; pagination is not specified.
- **Statuses:** `200`, `401`, `422`, `503`.
- **Idempotency/auth:** Read-only. Contract-wide auth applies.
- **Source:** FR-13, FR-26; P:L241-245; D:Q543.

Example request and response:

```http
GET /v1/memories?status=active
```

```json
{
  "groups": [
    {
      "tier": "stated",
      "label": "Things you told me",
      "items": [
        {
          "id": "mem_email_style_001",
          "version": 3,
          "type": "preference",
          "tier": "stated",
          "content": "Client emails use prose, not bullet lists.",
          "evidence_count": 14,
          "last_seen_at": "2026-08-29T18:02:00+05:30",
          "last_confirmed_at": "2026-08-30T09:12:00+05:30",
          "pinned": true,
          "status": "active"
        }
      ]
    },
    { "tier": "observed", "label": "Things I've noticed", "items": [] },
    { "tier": "hypothesised", "label": "Things I'm wondering about", "items": [] }
  ],
  "total": 1,
  "filters": { "status": "active" }
}
```

#### API-08 - Inspect one memory

- **Method/path:** `GET /v1/memories/{memory_id}`
- **Request shape:** Path parameter only.
- **Response shape:** HTTP `200`; the full FR-13 contract, source transcript previews/links, version history, actions available, and lifecycle explanation.
- **Statuses:** `200`, `401`, `404`, `503`.
- **Idempotency/auth:** Read-only. Contract-wide auth applies.
- **Source:** FR-13, FR-26; P:L229-245; D:Q28, Q309, Q405, Q543.

Example request and response:

```http
GET /v1/memories/mem_email_style_001
```

```json
{
  "id": "mem_email_style_001",
  "version": 3,
  "type": "preference",
  "tier": "stated",
  "content": "Client emails use prose, not bullet lists.",
  "evidence_count": 14,
  "source_transcript_ids": ["tr_2026-03-02_0004", "tr_2026-03-08_0011"],
  "first_seen_at": "2026-03-02T09:05:00+05:30",
  "last_seen_at": "2026-08-29T18:02:00+05:30",
  "last_confirmed_at": "2026-08-30T09:12:00+05:30",
  "pinned": true,
  "status": "active",
  "sources": [
    {
      "transcript_id": "tr_2026-03-02_0004",
      "occurred_at": "2026-03-02T09:05:00+05:30",
      "preview": "Write it as prose, no bullets.",
      "inspection_url": "/v1/transcripts/tr_2026-03-02_0004/inspection"
    }
  ],
  "history": [
    { "version": 2, "content": "Client email usually uses prose.", "status": "superseded", "changed_at": "2026-08-30T09:12:00+05:30" }
  ],
  "actions": ["correct", "demote", "forget", "unpin"]
}
```

#### API-09 - Confirm a memory

- **Method/path:** `POST /v1/memories/{memory_id}/confirm`
- **Request shape:** Requires `expected_version`; optional `occurred_at` defaults to receipt time.
- **Response shape:** HTTP `200`; the resulting stated memory and a timestamped action receipt.
- **Statuses:** `200`, `400`, `401`, `404`, `409`, `422`, `503`. A memory already stated returns `409 MEMORY_UNCHANGED` unless this is an idempotent replay.
- **Idempotency/auth:** `Idempotency-Key` is required; version mismatch returns `409 VERSION_CONFLICT`. Contract-wide auth applies.
- **Source:** FR-14, FR-27; P:L92-98, L243-245; D:Q191, Q738.

Example request and response:

```http
POST /v1/memories/mem_email_style_001/confirm
Content-Type: application/json
Idempotency-Key: confirm-email-style-20260830

{ "expected_version": 2, "occurred_at": "2026-08-30T09:12:00+05:30" }
```

```json
{
  "action": "confirmed",
  "memory": {
    "id": "mem_email_style_001",
    "version": 3,
    "tier": "stated",
    "content": "Client emails use prose, not bullet lists.",
    "last_confirmed_at": "2026-08-30T09:12:00+05:30"
  },
  "event_id": "evt_confirm_01K4T8A1",
  "occurred_at": "2026-08-30T09:12:00+05:30"
}
```

#### API-10 - Correct a memory

- **Method/path:** `POST /v1/memories/{memory_id}/correct`
- **Request shape:** Requires non-blank `content`, `expected_version`, and optional `occurred_at`. Content still passes every exclusion gate.
- **Response shape:** HTTP `200`; stated replacement, superseded prior version, suppression receipt, and action event.
- **Statuses:** `200`, `400`, `401`, `404`, `409`, `422`, `503`. Normalized unchanged content returns `409 MEMORY_UNCHANGED`; prohibited content returns `422 EXCLUDED_CONTENT`; an uncommitted suppression returns `503 STATE_UNAVAILABLE` with no replacement committed.
- **Idempotency/auth:** `Idempotency-Key` is required; version mismatch returns `409 VERSION_CONFLICT`. Contract-wide auth applies.
- **Source:** FR-08, FR-27; P:L215-220, L235-245; D:Q46, Q557, Q604, Q839.

Example request and response:

```http
POST /v1/memories/mem_priya_company_001/correct
Content-Type: application/json
Idempotency-Key: priya-company-correction-20260911

{
  "content": "Priya Raghavan is the client contact at Northwind.",
  "expected_version": 1,
  "occurred_at": "2026-09-11T10:35:00+05:30"
}
```

```json
{
  "action": "corrected",
  "memory": {
    "id": "mem_priya_company_002",
    "version": 1,
    "type": "entity",
    "tier": "stated",
    "content": "Priya Raghavan is the client contact at Northwind.",
    "status": "active"
  },
  "replaced": { "id": "mem_priya_company_001", "version": 1, "status": "superseded" },
  "suppression": { "created": true, "effect": "blocks re-derivation of the Acme role claim" },
  "event_id": "evt_correct_01K4T8D4"
}
```

#### API-11 - Demote a memory (“That's not me anymore”)

- **Method/path:** `POST /v1/memories/{memory_id}/demote`
- **Request shape:** Requires `expected_version`; fixed reason is `not_me_anymore`; optional `occurred_at`.
- **Response shape:** HTTP `200`; demoted status, lost surfacing rights, suppression receipt, and event.
- **Statuses:** `200`, `400`, `401`, `404`, `409`, `422`, `503`.
- **Idempotency/auth:** `Idempotency-Key` is required. A replay returns the first receipt; a separately submitted action on an already demoted memory is a no-op success. Contract-wide auth applies.
- **Source:** FR-28; P:L235-245; D:Q15, Q46, Q738.

Example request and response:

```http
POST /v1/memories/mem_recap_timing_001/demote
Content-Type: application/json
Idempotency-Key: not-me-recap-timing-20260911

{ "expected_version": 4, "reason": "not_me_anymore", "occurred_at": "2026-09-11T10:38:00+05:30" }
```

```json
{
  "action": "demoted",
  "memory_id": "mem_recap_timing_001",
  "status": "demoted",
  "retrievable_as_current": false,
  "suppression": { "created": true, "applies_on_reprocessing": true },
  "event_id": "evt_demote_01K4T8G7"
}
```

#### API-12 - Pin or unpin a memory

- **Method/path:** `PUT /v1/memories/{memory_id}/pin`
- **Request shape:** Requires boolean `pinned` and `expected_version`.
- **Response shape:** HTTP `200`; new pin state, version, and action event.
- **Statuses:** `200`, `400`, `401`, `404`, `409`, `422`, `503`.
- **Idempotency/auth:** Setting the existing value is a no-op success. Version mismatch returns `409 VERSION_CONFLICT`. Contract-wide auth applies.
- **Source:** FR-16, FR-28; P:L233-245; D:Q178, Q315, Q791.

Example request and response:

```http
PUT /v1/memories/mem_email_style_001/pin
Content-Type: application/json

{ "pinned": false, "expected_version": 3 }
```

```json
{
  "action": "unpinned",
  "memory_id": "mem_email_style_001",
  "version": 4,
  "pinned": false,
  "event_id": "evt_pin_01K4T8K2"
}
```

#### API-13 - Forget a memory

- **Method/path:** `DELETE /v1/memories/{memory_id}`
- **Request shape:** Path parameter and `If-Match: <version>` header. The client MUST disclose before calling that source transcripts and a minimal non-memory suppression remain.
- **Response shape:** HTTP `200`; action receipt without forgotten content, confirmation that active/history memory was removed, confirmation that re-derivation is blocked, and source-transcript retention notice.
- **Statuses:** `200`, `401`, `404`, `409`, `503`. Inability to commit suppression returns `503` and removes nothing.
- **Idempotency/auth:** Repeating the delete returns the original content-free receipt. Version mismatch returns `409 VERSION_CONFLICT`. Contract-wide auth applies.
- **Source:** FR-28; P:L233-245; D:Q46, Q309, Q738; D:B2, B5.

Example request and response:

```http
DELETE /v1/memories/mem_email_style_001
If-Match: 4
```

```json
{
  "action": "forgotten",
  "memory_id": "mem_email_style_001",
  "memory_removed": true,
  "history_removed": true,
  "rederivation_blocked": true,
  "source_transcripts_retained": true,
  "event_id": "evt_forget_01K4T8N9"
}
```

#### API-14 - Inspect a transcript

- **Method/path:** `GET /v1/transcripts/{transcript_id}/inspection`
- **Request shape:** Path parameter only.
- **Response shape:** HTTP `200`; original record, processing state and attempts, outcome, created/changed/rejected candidate summaries, reason-only drop records, `read_not_kept` count, linked memories and answer traces, and per-record usage/cost.
- **Statuses:** `200`, `401`, `404`, `503`.
- **Idempotency/auth:** Read-only. Contract-wide auth applies.
- **Source:** FR-30; P:L42-46, L113-122; D:Q16, Q81, Q109, Q171, Q199; B:p.4 per-result inspection list.

Example request and response:

```http
GET /v1/transcripts/tr_2026-03-12_0017/inspection
```

```json
{
  "transcript": {
    "transcript_id": "tr_2026-03-12_0017",
    "raw_asr": "reply to priya move the atlas review to next tuesday",
    "formatted_text": "Reply to Priya: move the Atlas review to next Tuesday.",
    "occurred_at": "2026-03-12T17:04:11+05:30",
    "metadata": { "source": "dictation", "application": "Slack", "channel": "design-review" }
  },
  "processing": {
    "state": "processed",
    "attempts": 1,
    "outcome": "candidates_stored",
    "completed_at": "2026-03-12T17:05:02+05:30"
  },
  "memory_changes": [
    { "candidate_index": 0, "decision": "created", "memory_id": "mem_atlas_review_004" },
    { "candidate_index": 1, "decision": "same_fact_new_evidence", "memory_id": "mem_priya_001" }
  ],
  "drops": [
    { "reason_code": "THIRD_PARTY_PERSONAL", "count": 2, "content_stored": false }
  ],
  "read_not_kept_count": 2,
  "linked_trace_ids": ["trace_01JNX8D2"],
  "usage": { "model_calls": 3, "input_tokens": 1420, "output_tokens": 188 },
  "cost": { "currency": "USD", "amount": 0.0068 }
}
```

#### API-15 - Inspect a Why trace

- **Method/path:** `GET /v1/traces/{trace_id}`
- **Request shape:** Path parameter only.
- **Response shape:** HTTP `200`; a `user_explanation` suitable for the Why panel and `review_evidence` containing the full FR-29 trace. Rejected-content bodies MUST never appear in either view.
- **Statuses:** `200`, `401`, `404`, `503`.
- **Idempotency/auth:** Read-only. Contract-wide auth applies.
- **Source:** FR-29; P:L222-225; D:E4, Q56, Q405, Q631, Q663; B:pp.4-5.

Example request and response:

```http
GET /v1/traces/trace_01K4T7JYKW1N8R6C3QAP
```

```json
{
  "trace_id": "trace_01K4T7JYKW1N8R6C3QAP",
  "outcome": "abstained",
  "user_explanation": {
    "searched_for": ["Arun", "auth migration"],
    "summary": "I found no supporting memory; two nearby results were not answers.",
    "retrieved": ["mem_arun_backend_001"],
    "withheld": [],
    "used": [],
    "near_misses": ["mem_arun_backend_001", "tr_2026-03-06_0009"]
  },
  "review_evidence": {
    "surface": "hey_kivi",
    "permission": "anbu",
    "ranking": [
      {
        "memory_id": "mem_arun_backend_001",
        "lexical_rank": 2,
        "semantic_rank": 1,
        "fused_rank": 1,
        "pinned": false,
        "tier": "stated",
        "evidence_count": 4,
        "decision": "near_miss"
      }
    ],
    "budget_dropped": [],
    "raw_fallback_hits": ["tr_2026-03-06_0009"],
    "available_tools": ["recall_search", "draft_reply", "schedule_reschedule"],
    "selected_tool": "recall_search",
    "tool_result_code": "NOT_FOUND",
    "failures": [],
    "timings_ms": { "retrieval": 84, "tool": 2, "generation": 712, "end_to_end": 824 },
    "usage": { "model_calls": 1, "input_tokens": 984, "output_tokens": 123 },
    "cost": { "currency": "USD", "amount": 0.0041 }
  }
}
```

#### API-16 - Reveal one withheld observation

- **Method/path:** `POST /v1/traces/{trace_id}/reveal-observation`
- **Request shape:** Requires the `memory_id` of an observed memory that this trace retrieved and withheld only because permission was Anbu.
- **Response shape:** HTTP `200`; the observation in evidence-backed language, evidence count, dated source links, unchanged persistent permission, and a reveal event ID. The result is a one-time disclosure for this trace, not promotion or confirmation.
- **Statuses:** `200`, `400`, `401`, `404`, `409`, `422`, `503`. A memory not in this trace's withheld set returns `409 NOT_REVEALABLE`.
- **Idempotency/auth:** `Idempotency-Key` is required; replay returns the original reveal. Contract-wide auth applies.
- **Source:** FR-20; P:L170-174; D:Q328, Q826.

Example request and response:

```http
POST /v1/traces/trace_01K4TB1Q/reveal-observation
Content-Type: application/json
Idempotency-Key: reveal-trace-01K4TB1Q-mem-recap

{ "memory_id": "mem_recap_timing_001" }
```

```json
{
  "action": "observation_revealed",
  "observation": {
    "memory_id": "mem_recap_timing_001",
    "text": "I've noticed you dictate recaps immediately after meetings.",
    "evidence_count": 9,
    "sources": [
      { "transcript_id": "tr_2026-05-14_0021", "occurred_at": "2026-05-14T17:42:00+05:30" }
    ]
  },
  "persistent_permission": "anbu",
  "promoted": false,
  "event_id": "evt_reveal_01K4TB2C"
}
```

### 3.4 Evaluation and operator interfaces

#### API-17 - Start evaluation

- **Method/path:** `POST /v1/evaluations`
- **Request shape:** Requires `corpus_import_id`, `case_set` (`development` or a documented imported case-set ID), and `reset_before_run` boolean. Evaluation questions are references to the case set and are not ingested as transcripts.
- **Response shape:** HTTP `202`; evaluation ID, queued state, case count, declared starting-state identifier, and status URL.
- **Statuses:** `202`, `400`, `401`, `404`, `409`, `422`, `503`.
- **Idempotency/auth:** `Idempotency-Key` is required. A run cannot start while its import is incomplete; that returns `409 IMPORT_INCOMPLETE`. Contract-wide auth applies.
- **Source:** FR-32; D:Q301, Q370, Q720, Q841; B:pp.4-5.

Example request and response:

```http
POST /v1/evaluations
Content-Type: application/json
Idempotency-Key: eval-development-20260911

{
  "corpus_import_id": "imp_01K4T70C9QH4A2M8Y6RN",
  "case_set": "development",
  "reset_before_run": false
}
```

```json
{
  "evaluation_id": "eval_01K4T91M7N4X2B8Q6CDA",
  "state": "queued",
  "case_count": 42,
  "starting_state_id": "state_01K4T90Z",
  "status_url": "/v1/evaluations/eval_01K4T91M7N4X2B8Q6CDA"
}
```

#### API-18 - Inspect evaluation status and results

- **Method/path:** `GET /v1/evaluations/{evaluation_id}`
- **Request shape:** Path parameter only.
- **Response shape:** HTTP `200`; state/progress while running. At completion, also includes per-case results and links, seven claim results, brief-criterion results, failure list, abstention count, measured retrieval/end-to-end latency distributions, database growth, model usage, whole-pipeline cost, conditions, and sensitivity results for configured open thresholds.
- **Statuses:** `200`, `401`, `404`, `503`.
- **Idempotency/auth:** Read-only. Contract-wide auth applies.
- **Source:** FR-32; P:L274-284; D:Q139, Q477, Q593, Q651, Q696; B:pp.4-5.

Example request and response:

```http
GET /v1/evaluations/eval_01K4T91M7N4X2B8Q6CDA
```

```json
{
  "evaluation_id": "eval_01K4T91M7N4X2B8Q6CDA",
  "state": "completed",
  "complete": true,
  "starting_state_id": "state_01K4T90Z",
  "cases": {
    "total": 42,
    "passed": 38,
    "failed": 4,
    "abstained": 9,
    "items": [
      { "case_id": "case_absent_auth_migration", "result": "passed", "trace_id": "trace_01K4T7JYKW1N8R6C3QAP" }
    ]
  },
  "position_claims": [
    { "claim": 1, "result": "passed", "evidence": ["tr_2026-03-19_0028"] },
    { "claim": 5, "result": "passed", "evidence": ["case_absent_auth_migration"] }
  ],
  "failures": [
    { "case_id": "case_noisy_entity_07", "code": "MISSED_ELIGIBLE_MEMORY", "inspection_url": "/v1/transcripts/tr_noise_007/inspection" }
  ],
  "latency_ms": {
    "retrieval": { "count": 42, "p50": 63, "p95": 118 },
    "end_to_end": { "count": 42, "p50": 806, "p95": 1412 }
  },
  "database_growth_bytes": 18442240,
  "usage": { "model_calls": 1070, "input_tokens": 917442, "output_tokens": 125033 },
  "cost": { "currency": "USD", "amount": 4.07 },
  "conditions": { "record_count": 500, "single_user": true },
  "sensitivity_results": [
    { "parameter": "observation_evidence_threshold", "tested_values": [2, 3, 5], "passed_cases": [38, 37, 34] }
  ]
}
```

#### OP-01 - Reset system

- **Interface:** Operator-only local operation `reset_system` (exposed by the exact command documented in `RUN.md`, never by HTTP and never model-callable).
- **Request shape:** `{ "confirmation": "RESET", "restore_seed": true | false }`.
- **Response shape:** Exit success with removed-state counts, a new state ID, and whether reproducible seed state was restored. Failure exits non-zero with the common error object on standard output.
- **Outcome codes:** `RESET_COMPLETED`, `CONFIRMATION_REQUIRED`, `STATE_UNAVAILABLE`.
- **Idempotency/auth:** Repeating reset is safe. Access is inherited from the local operator account; hosted users have no reset route.
- **Source:** FR-33; D:Q107, Q406; B:p.7 exact reset procedure.

Example request and response:

```json
{ "confirmation": "RESET", "restore_seed": true }
```

```json
{
  "code": "RESET_COMPLETED",
  "removed": { "transcripts": 500, "memories": 137, "traces": 42, "internal_events": 3, "evaluations": 1 },
  "restore_seed": true,
  "state_id": "state_01K4T9G8"
}
```

### 3.5 Complete internal Hey Kivi tool interface

These three interfaces are the entire model-callable tool surface. They inherit the authenticated request context; they accept no user/tenant ID and cannot be called across users. Their result codes are embedded in the persisted trace. Extraction, ranking, and disclosure are pipeline contracts, not additional model-callable tools. Source: D:E1, Q56, Q244, Q246, Q273.

#### TOOL-01 - `recall_search`

- **Method:** `recall_search(request)`
- **Request shape:** `query` string; optional `time_range` with `start`/`end`; required `trace_id`; required `retrieval_snapshot_id`. The tool receives already ranked, permission-labelled candidates by snapshot reference and cannot expand beyond one bounded raw-text fallback.
- **Response shape:** `FOUND`, `NOT_FOUND`, `LOW_CONFIDENCE`, `AMBIGUOUS`, `CONTRADICTORY`, or `PARTIAL_FAILURE`; supported facts with memory/source citations; search description; near misses; raw-fallback hits explicitly labelled.
- **Idempotency/auth:** Pure read for a fixed snapshot and request. Inherits caller auth.
- **Error behavior:** Invalid input returns `INVALID_INPUT`; unavailable snapshot returns `STATE_UNAVAILABLE`. Missing/weak/ambiguous evidence is a normal result, not an exception.
- **Source:** FR-18, FR-23; D:Q04, Q27, Q211, Q675.

Example request and response:

```json
{
  "query": "What did Arun say about the auth migration?",
  "time_range": null,
  "trace_id": "trace_01K4T7JYKW1N8R6C3QAP",
  "retrieval_snapshot_id": "rs_01K4T7JP"
}
```

```json
{
  "code": "NOT_FOUND",
  "facts": [],
  "searched_for": ["Arun", "auth migration"],
  "near_misses": [
    { "kind": "memory", "id": "mem_arun_backend_001", "label": "Arun on Atlas backend work", "source_count": 4 }
  ],
  "raw_fallback_hits": [
    { "kind": "raw_transcript", "id": "tr_2026-03-06_0009", "label": "Database migration discussion", "is_memory": false }
  ]
}
```

#### TOOL-02 - `draft_reply`

- **Method:** `draft_reply(request)`
- **Request shape:** user `instruction`; optional `recipient` limited to name/role/organisation; optional text `application_context`; required `permission` (`anbu` or `koottu`); optional invited hypothesis reference; required `trace_id` and `retrieval_snapshot_id`.
- **Response shape:** `DRAFTED`, `INSUFFICIENT_CONTEXT`, `AMBIGUOUS`, or `PARTIAL_FAILURE`; draft text, used citations, offered observations, invited questions, and `external_side_effects: "none"`.
- **Idempotency/auth:** Pure drafting; identical fixed-snapshot request may be replayed from the enclosing request's idempotency record. Inherits caller auth.
- **Error behavior:** Missing recipient/context needed for the requested reply returns `AMBIGUOUS` or `INSUFFICIENT_CONTEXT`, leading to abstention. It never invents recipient facts.
- **Source:** FR-24; P:L83-88, L103-122; D:Q12, Q128, Q153, Q246.

Example request and response:

```json
{
  "instruction": "Reply that Tuesday works and ask for the final deck by noon.",
  "recipient": { "name": "Priya Raghavan", "role": "client contact", "organisation": "Acme" },
  "application_context": "Can we move the Atlas review to Tuesday?",
  "permission": "anbu",
  "invited_hypothesis_id": null,
  "trace_id": "trace_01K4TA1V",
  "retrieval_snapshot_id": "rs_01K4TA1P"
}
```

```json
{
  "code": "DRAFTED",
  "draft": "Tuesday works for the Atlas review. Could you send the final deck by noon?\n\nBest, Meera",
  "citations": [
    { "memory_id": "mem_signoff_001", "source_transcript_ids": ["tr_2026-02-18_0003"] }
  ],
  "offered_observations": [],
  "invited_questions": [],
  "external_side_effects": "none"
}
```

#### TOOL-03 - `schedule_reschedule`

- **Method:** `schedule_reschedule(request)`
- **Request shape:** `operation` (`create` or `reschedule`); event reference or new title; explicit RFC 3339 `scheduled_for`; optional `previous_scheduled_for`; relevant entity/memory citations; required `trace_id`; required `idempotency_key`.
- **Response shape:** `SCHEDULED`, `RESCHEDULED`, `AMBIGUOUS_EVENT`, `MISSING_TIME`, `CONTRADICTORY`, or `STATE_UNAVAILABLE`; internal event ID, old/new time, citations, and `external_side_effects: "none"`.
- **Idempotency/auth:** Same key and request returns the original event/result; same key with different fields returns `IDEMPOTENCY_CONFLICT`. Inherits caller auth.
- **Error behavior:** The tool refuses relative or ambiguous time it cannot resolve from the request and grounded history; it never chooses a plausible date. A failed state write returns `STATE_UNAVAILABLE` and Hey Kivi abstains.
- **Source:** FR-25; D:Q237, Q246, Q288, Q508.

Example request and response:

```json
{
  "operation": "reschedule",
  "event": { "event_id": "event_atlas_review_04", "title": "Atlas review" },
  "scheduled_for": "2026-09-15T15:00:00+05:30",
  "previous_scheduled_for": "2026-09-10T15:00:00+05:30",
  "citations": [
    { "memory_id": "mem_atlas_review_004", "source_transcript_ids": ["tr_2026-03-12_0017"] }
  ],
  "trace_id": "trace_01K4TA5F",
  "idempotency_key": "reschedule-atlas-20260911-1"
}
```

```json
{
  "code": "RESCHEDULED",
  "event_id": "event_atlas_review_04",
  "title": "Atlas review",
  "previous_scheduled_for": "2026-09-10T15:00:00+05:30",
  "scheduled_for": "2026-09-15T15:00:00+05:30",
  "citations": [
    { "memory_id": "mem_atlas_review_004", "source_transcript_ids": ["tr_2026-03-12_0017"] }
  ],
  "external_side_effects": "none"
}
```

## 4. CONSTRAINTS

### 4.1 Imposed by the brief

1. **Pre-existing product position is authoritative and preserved.** Part One required actual use of Kivi and study of how other products handle memory, personalisation, context, and control. The resulting positioning statement (maximum 100 words) and vision document (maximum 600 words) had to be the author's own thinking, completed and preserved before build work, and answer what Kivi becomes, where user value arises, what is remembered, what it never assumes, and why it is trusted. This specification may operationalise them but MUST NOT silently rewrite them. Source: B:pp.1-2, Part One research, five position questions, submission, and AI-use clauses; P:L5.
2. **One real end-to-end product, not a prototype.** The interface, interactions, language, visual character, and backend are evaluated as one implemented product. A notebook, static demonstration, prompt collection, or architecture-only submission is invalid; web or desktop is acceptable. Source: B:pp.2-4.
3. **Useful, minimal capability.** The product MUST work backward from worthwhile use cases and build the smallest set that is worth using. Only tools required by those use cases may ship. Source: B:pp.2-4; D:E5.
4. **Complete ordinary-use story.** The demonstration MUST show ordinary use, future behavior changed by memory, the dictation/Hey Kivi allocation, handling of incomplete/wrong understanding, and user control without administration. Source: B:p.3.
5. **Normal-user start and finish.** The product MUST be understandable without a developer console or explanation of the underlying system. Source: B:p.3; P:L222-246.
6. **Real backend behavior.** Visible behavior MUST arise from actual state, persistence, retrieval, and model decisions, including creation, representation, storage, change, removal, retrieval, tool/response influence, and inspection. Source: B:pp.3-4.
7. **Development corpus.** The repository MUST contain or reproducibly obtain approximately 500 transcript-like records with raw ASR, LLM-formatted output, and only genuinely required metadata. It needs sufficient variety to show success, abstention, and failure; this is not a data-generation competition. Source: B:p.4; P:L250-262.
8. **Full-pipeline evaluation.** A reproducible evaluation MUST inspect, per result, original input; memory created, retrieved, changed, or rejected; provenance; Hey Kivi behavior; and reason. It MUST include latency, database growth, model usage, and cost where they matter, and failures must remain visible. Source: B:pp.4-5.
9. **Unseen-corpus operation.** Reviewers MUST be able to import, process, inspect, and query a translated internal corpus of approximately 500 dictations from one user. Recall success is required for any reasonable question whose answer is present in or derivable from that history; invention on absent history is forbidden. Source: B:p.5.
10. **Repository submission contents.** The final repository MUST include the positioning statement; vision; complete source; working interface/backend; persistence definition and migrations; reproducible seed data; development corpus/evaluation; generated evaluation results; README covering product, architecture, use cases, limitations, results, and AI use; and `RUN.md`. This specification does not prescribe their file layout. Source: B:pp.5-6.
11. **One primary review arrangement.** Deployment is optional, but exactly one hosted, local, containerised, or hybrid arrangement MUST be declared first in `RUN.md` and reproduced from the final commit. If the arrangement changes to hosted, `RUN.md` MUST instead supply the direct URL, demonstration credentials, interactions to try, candidate-evaluation procedure, and corpus-import procedure. Source: B:pp.6-7.
12. **Local/hybrid `RUN.md` checklist.** For the selected local review path, `RUN.md` MUST state: (1) runtimes/versions; (2) every environment variable; (3) dependency-install commands; (4) create/migrate/seed commands; (5) commands for every process; (6) interface URL/window; (7) primary interactions; (8) evaluation command; (9) foreign-corpus import procedure; (10) inspection locations; and (11) reset procedure. Source: B:p.7.
13. **Credentials and network declarations.** If an LLM key is required, its environment-variable name and an example environment file MUST be included; private credentials MUST NOT be committed. The system MUST NOT make undeclared network calls beyond the named provider. Source: B:p.7; D:Q719.
14. **Final submission and dry run.** The application form requires repository URL, exact final commit SHA, and hosted URL if applicable. The complete review path MUST be tested from that commit; the reviewer will not repair, infer setup, do dashboard work, or request clarification. Source: B:p.7.

### 4.2 Imposed by the position

1. **Calibrated disclosure:** knowing and saying are separate; permission filters disclosure after Hey Kivi retrieval. Source: P:L19-25, L150-174.
2. **Non-characterisation of others:** third-party context may serve the current task but cannot become personal memory; only limited work-world identity residue survives. Source: P:L103-122; D:B1 qualification.
3. **Revisability:** every belief is visible, attributable, and reversible by the user; negative updates must survive reprocessing. Source: P:L19-25, L229-246.
4. **Work-level memory only:** semantic memory removes repeated briefing; it does not deliver a psychological profile, general insight, or advice as durable memory. Source: P:L29-59.
5. **Closed semantics:** three memory types and three epistemic tiers; hypotheses are questions; no automatic promotion. Source: P:L63-99.
6. **Hard exclusions:** prohibited categories are non-overridable gates before storage, with non-content reason logs. Source: P:L29-46; D:Q604.
7. **Surface-specific rights:** ordinary dictation cannot access observations/hypotheses; Hey Kivi uses tier permissions. Source: P:L178-196.
8. **Honest uncertainty:** abstention must be actionable and traced; plausible guessing is prohibited. Source: P:L200-225.
9. **Lifecycle by authority:** observations decay, hypotheses expire, contradictions are auditable, user suppressions prevent regrowth, and stated/pinned memory remains until user action. Source: P:L229-245; D:Q178.

### 4.3 Imposed by the selected stack and review arrangement

These are only externally visible stack constraints; storage internals, library choices, and file layout belong in the architecture document.

1. The primary review arrangement is single-user and local by default, with one self-contained application boundary and locally persistent state. Source: D:E1-E2, Q107, Q447.
2. The client accepts text only. It has no microphone/speech recogniser, audio output, multimodal ingestion, or production-Kivi dependency. Source: P:L7; D:Q98, Q372.
3. Import is push-based and serial by event time. The state writer is singular; concurrent reads must not expose half-applied current-memory changes. Source: D:Q76, Q96-Q97, Q184, Q339-Q340.
4. Retrieval combines exact/lexical evidence, semantic similarity, and one-hop entity linkage, then applies deterministic ordering. Model-generated reranking is prohibited. Source: D:Q23, Q26, Q182, Q212, Q487.
5. Durable extraction uses a pinned model with deterministic structured output; generation wording may vary, but cited facts may not. Model identity is part of reproducibility and cost reporting. Source: D:Q72, Q531, Q673, Q720.
6. No hosted service other than the declared model provider may be required on the critical review path. Hosted deployment would add token authentication to every HTTP endpoint. Source: D:E2, Q107, Q719.
7. Source transcripts are retained as provenance and are not retrieved as memory; this creates the privacy qualification recorded in D:B2. Source: D:Q17, Q28, Q186.

### 4.4 Cost and latency budgets

| Measure | Target or limit | Numeric value | Verification | Source |
|---|---|---:|---|---|
| Development/reviewer scale | Target | Approximately 500 transcripts from 1 user | Evaluation conditions | B:pp.4-5; D:E1, E3 |
| Model-callable tools | Limit | 3 | Trace `available_tools` | D:Q246 |
| Persistent permission modes | Limit | 2 (`Anbu`, `Koottu`) | Permission API | P:L156-158; D:Q328 |
| Daari persistence | Limit | 0 persistent sessions; 1 invited answer | Compare permission before/after | P:L156-158 |
| Retrieval passes per Hey Kivi request | Limit | 1 | Trace | D:Q409, Q811, Q835 |
| Raw-transcript fallback passes after memory miss | Limit | 1 | Trace | D:Q211, Q675 |
| Answer-generation calls per request | Limit | At most 1 successful attempt | Trace usage | D:Q409, Q508, Q513 |
| Agent/reflection/debate rounds | Limit | 0 | Trace call roles | D:Q244, Q507-Q508 |
| Extraction scope | Limit | 1 transcript per extraction call | Per-record usage | D:Q170 |
| Blocking semantic-extraction calls on an interaction | Limit | 0 | Interaction trace | D:Q62, Q580 |
| Added blocking model latency from semantic extraction | Target | 0 ms | Interaction timing | D:Q580 |
| Retrieval and end-to-end latency | Measurement requirement; threshold unset | p50 and p95 in ms | Evaluation report | B:pp.4-5; D:Q303, Q842, A1; P:L264-272 leaves target open |
| Import latency | Measurement requirement; threshold unset | Total ms and ms/transcript | Import/evaluation report | D:Q580, Q842 |
| Whole-pipeline monetary cost | Measurement requirement; ceiling unset | Currency amount, total and by stage | Evaluation report | B:pp.4-5; D:Q303, Q593 |
| Database growth | Measurement requirement; ceiling unset | Bytes total and per transcript | Evaluation report | B:pp.4-5; D:Q263 |
| Confirmation prompts | Limit required; value unset | Prompts/user/week | Permission/prompt ledger | P:L217-220; D:A1.6-A1.7 |
| Extraction retry cap | Limit required; value unset | Attempts/transcript | Transcript inspection | D:Q108 |
| Observation threshold, decay, expiry, top-k, contradiction candidates, broadening | Limits required; values unset | Configuration values | Evaluation sensitivity report | P:L264-272; D:A1.1-A1.5, A1.8, Q696 |

No input supplies a defensible p95 latency limit, monetary ceiling, storage ceiling, retry count, or confirmation cap. They remain Open Questions rather than invented requirements.

## 5. EDGE CASES AND ERROR HANDLING

### 5.1 Request and import validation

| Condition | Detection | System response | What the user/reviewer sees | What is logged |
|---|---|---|---|---|
| Malformed JSON or wrong field type | Schema parse before acceptance | Reject the request; no transcript or idempotency result is created | `400 INVALID_JSON` or `422 INVALID_INPUT` with field path | Request ID, error code, field path; no body echo beyond safe validation detail |
| Empty corpus | `records` absent or zero length | Reject; no import created | `422 INVALID_INPUT` | Request ID and `empty_records` |
| Empty/whitespace raw ASR or formatted text | Trimmed required field is empty | Reject that live record; for batch, identify the invalid item and do not queue it while preserving valid accepted items | Per-item field error with transcript ID/index | Non-content validation failure and import counts |
| Non-empty garbage/noise | Record is syntactically valid; extractor returns no supported candidate or only ambiguous candidates | Keep raw transcript; record `nothing_found` or reason-coded ambiguous drops; do not invent memory | Transcript shows “I didn't find anything to remember”; no memory created | Outcome, attempt, candidate/drop counts; ambiguous content itself is not copied into drop log |
| Required metadata/time missing or invalid | Schema and RFC 3339 validation | Reject item; do not guess a time or use arrival time | `422 INVALID_INPUT` with field reason | Request ID, transcript ID/index, error code |
| Pathologically large record | Declared safety guard, whose numeric limit is open, detects oversize before model use | Fail loudly; never truncate; keep no partial transcript for a rejected request | `422 INPUT_TOO_LARGE` and documented limit | Size, limit, transcript ID; no content copy | 
| Same transcript ID and same content | ID and content fingerprint match accepted record | Return original result; do not re-add evidence | `200` replay/already-present result | Idempotent replay count |
| Same transcript ID and different content | ID exists but content fingerprint differs | Reject conflicting item; no overwrite | `409 CONTENT_CONFLICT` | Existing/new fingerprints, not duplicate content |
| Reused `Idempotency-Key` with different request | Key lookup and normalized request mismatch | Reject; do not repeat action | `409 IDEMPOTENCY_CONFLICT` | Key, request IDs, mismatch code |

Sources: D:Q08, Q86, Q102, Q109, Q152, Q171, Q556; B:p.4 record contract.

### 5.2 Extraction and admission

| Condition | Detection | System response | What the user/reviewer sees | What is logged |
|---|---|---|---|---|
| Excluded-category candidate | Mandatory category gate marks one of the FR-08 classes | Fail closed for that candidate; never store or disclose it as memory | Transcript shows category and count only | Transcript ID, candidate index, reason code, count, model/verdict metadata; never candidate content |
| Third-party personal candidate | Subject/work-level gate finds state, circumstance, history, or characterisation about someone else | Drop before memory; current draft may still use supplied context | `read_not_kept` marker and count | Non-content `THIRD_PARTY_PERSONAL` reason only |
| Allowed third-party identity residue | Candidate can be stated as canonical name/role/organisation/project association without personal characterisation | Continue through type/completeness gates | Resulting entity memory and provenance | Admission verdict and source ID |
| Ambiguous pronoun/reference during extraction | Candidate cannot be resolved from eligible user-authored source plus allowed entity list without guessing | Drop as `AMBIGUOUS_REFERENCE`; do not turn it into a hypothesis | Transcript identifies an ambiguous drop, not its sensitive content | Reason code, candidate index, entities considered; no invented referent |
| Candidate cannot fit one of three types | Type validator finds no valid entity/preference/episode representation | Drop as `UNSUPPORTED_MEMORY_TYPE` | Transcript inspection shows reason | Type verdict and reason |
| Candidate lacks type, tier, content, or source | Completeness validation | Reject candidate atomically; no repair-in-place | `EXTRACTION_DEFECT` in transcript inspection | Missing field names, not a partial memory |
| Exclusion check fails/times out | Gate fails to produce a valid verdict | Fail closed; do not write candidate; retry record, then quarantine at cap | Record shows retrying/quarantined and that nothing was admitted | Attempts, failure stage, provider error class, duration |
| Extraction model returns malformed output | Strict output validation | Hard parse failure; retry/backoff, then quarantine; do not salvage fragments | Record state and last safe error | Model identity, attempt, parse category, duration; raw model output only in protected diagnostics if policy later permits |
| Partial extraction failure | Some complete candidates committed, later candidate/stage fails | Keep good candidates, mark `partially_processed`, queue retry without duplicating them | Transcript shows successful items and failed stage | Candidate-level decisions, attempt, retry state |
| Model timeout/unavailable | Provider timeout/error | Interaction response remains unaffected; extraction retries and may quarantine | Existing dictation/Hey result plus delayed-memory status | Provider error class, timing, retry schedule, no secret |

Sources: P:L29-46, L103-122; D:Q20, Q55, Q72-Q73, Q81, Q85-Q86, Q108, Q152, Q169, Q394, Q675; D:B6.

### 5.3 Duplicate and contradiction resolution

| Condition | Detection | System response | What the user/reviewer sees | What is logged |
|---|---|---|---|---|
| Same fact in a different transcript | Positive semantic sameness verdict over candidate and existing memory | Increment evidence once, append source, update last-seen; do not promote | One memory with higher evidence and multiple sources | Candidate IDs, verdict/reason, before/after evidence, model identity |
| Near-duplicate/overlap without positive sameness | Similarity proposes pair but judge is ambiguous/unrelated | Keep separate memories linked only by shared entities | Two separately correctable entries | Candidate pair, ambiguous/unrelated verdict |
| False-sameness component failure | Merge judge fails | Prefer `NEW`; keep separate rather than risk false merge | Possible duplicate entries, each sourced | Failure and safe-direction decision |
| Contradiction below stated tier | Contradiction verdict plus tier/event time | Apply tier then event-time precedence; supersede loser with lineage | Current item plus auditable history | Verdict, evidence shown to judge, winning rule, version links |
| New evidence contradicts a stated memory | Contradiction verdict touches stated tier without explicit user correction | Do not override; mark unresolved; Anbu abstains, Koottu surfaces; prompt only if budget allows | Conflict and sources, or actionable abstention | Conflict ID, both memory IDs, permission response, prompt decision |
| Explicit user correction | Correction intent and target are unambiguous | Commit stated replacement and suppression synchronously | Immediate corrected answer/memory receipt | User action, before/after IDs, suppression outcome |
| Events were true in sequence rather than corrections | Evidence contains explicit validity times | Preserve stated times where supplied; otherwise use supersession and disclose modelling limitation | History shows available dates; no invented validity range | Source dates and whether validity was explicit |

Sources: D:Q03, Q13, Q66, Q92, Q133, Q159, Q173-Q174, Q206, Q449, Q479, Q557, Q789, Q855.

### 5.4 Retrieval and disclosure

| Condition | Detection | System response | What the user/reviewer sees | What is logged in the trace |
|---|---|---|---|---|
| Compiled-memory retrieval returns nothing | No candidate survives relevance threshold | Run exactly one bounded lexical raw-transcript fallback | Search description; labelled raw hits or abstention | Empty memory set, fallback query/hits, timing |
| Fallback also returns nothing; answer genuinely absent | No raw hit supports requested proposition | Return `200 abstained` with `NOT_IN_HISTORY`; never generate a plausible answer | Direct statement of missing history, search terms, genuine near misses if any | Searched concepts, empty supporting set, near misses, abstention reason |
| Retrieval returns low-confidence/weak matches | Best candidates below configured support threshold or do not entail answer | Treat as near misses; abstain | “I found nearby material, but not the answer” plus links | Scores/ranks for review, user-readable mismatch reason |
| Query contains ambiguous reference | More than one eligible referent and no grounded resolution from bounded active turn history | Abstain and name nearby alternatives; do not silently choose; clarification is not the routine fallback | Alternatives and what Kivi searched | Candidate referents, ambiguity code, no selected referent |
| One retrieval leg fails | Health/error signal from lexical or semantic leg | Abstain; do not answer from surviving leg silently | “I couldn't complete the memory search” and trace | Failed leg, surviving leg results marked unusable, timing/error |
| A current memory lacks semantic projection | Memory state flags missing/lagging semantic representation | Permit labelled lexical-only candidacy but expose degradation; if support is insufficient, abstain | Degradation note in Why view | Memory ID, degraded leg, repair state |
| Observation retrieved under Anbu | Tier is observed and permission is Anbu | Withhold content; expose only “Kivi noticed something here” | Quiet affordance; one-time reveal on action | Retrieved and withheld state, required `koottu` permission |
| Hypothesis retrieved without invitation | Tier is hypothesised and no explicit Daari invitation | Withhold completely from answer; trace records why | No hypothesis content | Withheld state and `DAARI_INVITATION_REQUIRED` |
| Context budget is full | Ranked candidates exceed configured top-k/token budget | Drop lowest ordered candidates after ranking; never relabel as irrelevant | Why view can show that additional items were not used | `budget_dropped` IDs and order |
| Superseded fact is retrieved for change history | Request asks about change/pattern rather than current fact | May use as evidence of change; never as current truth | Dated change observation with citations | `use_role: historical_evidence` |

Sources: P:L150-174, L200-225; D:Q27, Q35, Q56, Q133, Q183, Q211, Q329, Q344, Q421, Q631, Q675, Q789, Q826, Q859.

### 5.5 Tool selection and answer generation

| Condition | Detection | System response | What the user sees | What is logged in the trace |
|---|---|---|---|---|
| Request fits none of three tools | Router returns no eligible fixed tool | Return `200 unsupported`; do not fabricate capability | Exact supported set and no claim of action | All three candidates, `selected_tool: null`, reason |
| Router/tool-selection model fails | No valid selection result | Abstain once; no fallback tool guess and no retry-with-reflection | “I couldn't decide safely how to handle that request” | Failure stage, model, timing, no tool call |
| Draft lacks required recipient/context | Tool validation finds multiple or zero grounded targets | Return abstention/ambiguity; no recipient or content invention | Missing field/referent and nearby candidates | Tool result code, candidates, no draft |
| Schedule lacks resolvable event or time | Multiple/no grounded event, missing absolute time, or unresolved relative time | Return abstention; create/change nothing | Missing event/time and no completion claim | Tool input, ambiguity code, no state mutation |
| Duplicate schedule request | Enclosing idempotency key and request match | Return original event/result | Same event ID, no duplicate | Idempotent replay |
| Model generation fails or times out | Provider failure before grounded answer | Return persisted `200 abstained` if trace can be saved; otherwise `503` | Failure named without a guessed answer | Failure class, model, duration, retrieved-but-unused set |
| Generated claim lacks valid citation | Post-generation claim/citation validation fails | Do not return the unsupported claim; with one-attempt limit, abstain | Grounding failure and search summary | Failed claim/citation reference; never promote generated text to memory |
| Model produces a fourth tool call | Tool name not in fixed enumeration | Reject call and return unsupported/abstained result | No apparent action | `UNKNOWN_TOOL`, supplied name, no execution |

Sources: D:Q72, Q106, Q109, Q237, Q244-Q246, Q392, Q493, Q508, Q663; B:p.5 refusal-to-invent.

### 5.6 User actions and lifecycle

| Condition | Detection | System response | What the user sees | What is logged |
|---|---|---|---|---|
| Confirmation repeated or applied to stated memory | Memory already stated | Idempotent replay returns original; new redundant action returns `MEMORY_UNCHANGED` | Clear no-change result | Request/action ID and no-op code |
| Correction text normalizes to current content | Equality check | Reject `409 MEMORY_UNCHANGED`; write nothing | “That memory already says this” | No-op comparison result |
| Correction contains excluded content | Admission gate | Reject even though user requested it | Excluded category and no memory change | Reason code only; do not store proposed content as memory/drop detail |
| Suppression cannot be committed | State write fails before atomic action completes | Fail action; do not partially correct/demote/forget | `503 STATE_UNAVAILABLE`; original remains | Failure stage and rollback result |
| Demoted/forgotten belief appears during reprocessing | Candidate matches standing suppression | Drop as suppressed; never regrow | Reprocessing inspection shows `SUPPRESSED_BY_USER_ACTION` without resurfacing content | Suppression match, source action ID, candidate count |
| Forget repeated | Content-free deletion receipt exists | Return the same receipt | Same “forgotten” result without content | Replay only |
| Observation passes decay window | Clock sweep compares last-seen to configured window and item is not pinned | Mark non-surfacing/decayed; keep auditable state | Item leaves active observation group; history shows when/why | Lifecycle event and effective time |
| Hypothesis passes expiry window | Clock sweep and item is unconfirmed/unpinned | Remove from active hypothesis surface according to expiry policy | It no longer appears; inspection event remains only as permitted by unresolved retention policy | Expiry event and effective time |
| Stated or pinned item is old | Tier/pin exemption | No automatic change | Item remains active | Sweep records no mutation, if sweep auditing is enabled |

Sources: P:L229-245; D:Q15, Q24, Q46, Q147, Q178, Q191, Q557, Q687, Q738.

### 5.7 Evaluation and operational failure

| Condition | Detection | System response | What the reviewer sees | What is logged/reported |
|---|---|---|---|---|
| Evaluation starts before import completion | Import has queued/processing/retrying records | Reject with `409 IMPORT_INCOMPLETE` | Counts and status URL | Attempt and import state |
| Some records quarantine | Terminal import has quarantine count > 0 | Import completes as `completed_with_quarantine`; evaluation may run only if it explicitly records the holes | Visible quarantined record list and likely recall gaps | Per-record failures and aggregate count |
| Evaluation question leaked into corpus | Question fingerprint/source ID matches ingested input | Mark run invalid and fail it; do not report accuracy as valid | `EVALUATION_LEAKAGE` with offending case/source | Case IDs and source IDs |
| Metric cannot be measured | Missing timing, usage, cost, or growth baseline | Fail report completeness; do not substitute call count or estimate without label | Missing metric named | Metric error and affected cases |
| Reset cannot remove all state | Post-reset inventory is non-zero or seed hash mismatches | Return non-zero failure; do not claim clean state | Remaining category counts | Reset audit and mismatches |
| Review corpus has unfamiliar entities/relations | Valid text but outside development cast or fixed relation vocabulary | Import facts that fit supported contracts; drop/flatten unsupported relation with visible reason; never map to a convenient known entity | Transcript decisions and any `UNSUPPORTED_RELATION` | Candidate/relation verdict and source |

Sources: D:E2-E4, Q108, Q370, Q477, Q509, Q580, Q612, Q651, Q720, Q841, Q849; B:pp.4-7.

## 6. ACCEPTANCE CRITERIA

General execution rule: unless a criterion states otherwise, start from the documented reset state, submit records through the public API, wait until the import reports `complete: true`, and inspect both the normal-user interface and the referenced API result. Where a configured value is still open (`N`, a time window, top-k, retry cap, or prompt cap), the reviewer uses the value declared by the running build and records it with the result. A criterion passes only when every stated Then condition holds.

### AC-FR-01 - Explicit mode boundary

- **Given** the identical text “Find my Atlas review note” and a reset single-user system, **when** it is submitted once through ordinary dictation and once through Hey Kivi, **then** the first result is labelled `dictation`, the second `hey_kivi`, and neither route changes because of wording or tone.

### AC-FR-02 - Ordinary-dictation memory rights

- **Given** a stated entity spelling `Atlas`, a stated formatting preference, a relevant observed pattern, a relevant hypothesis, and a relevant episode, **when** raw ordinary dictation contains misspelled `Atlus`, **then** the output may use the entity and stated formatting preference but its inspection contains zero retrieved/used observed, hypothesised, or episode memories.
- **Negative:** **Given** the observed memory “Meera usually adds a risk paragraph,” **when** she dictates an Atlas note without requesting a risk paragraph, **then** any inserted risk paragraph or observed-memory ID in the dictation path is a fail.

### AC-FR-03 - Ordinary-dictation contract

- **Given** a valid replay record with raw ASR and formatted text, **when** it is posted to `/v1/dictations`, **then** a written response and transcript ID arrive before extraction completes, `semantic_processing` is reported, and no speech component or production-Kivi connection is required.

### AC-FR-04 - Push import

- **Given** 500 valid one-user records, each with a unique ID, raw ASR, formatted text, occurrence time, and metadata, **when** the batch is posted, **then** the API returns `202`, an import ID, `submitted: 500`, `accepted: 500`, and a usable status URL.
- **Given** the same batch plus one blank record, **when** posted, **then** that item is identified by index/ID and no valid accepted record is silently discarded or truncated.

### AC-FR-05 - Import order and idempotency

- **Given** an older and newer contradictory record submitted in reverse arrival order, **when** import finishes, **then** the decision history uses `occurred_at` order.
- **Given** the completed import, **when** the identical batch is posted again, **then** memory IDs, evidence counts, and source sets are unchanged; posting different content under an existing transcript ID returns `409 CONTENT_CONFLICT` and changes no state.

### AC-FR-06 - Processing completion state

- **Given** an import with one intentionally delayed record, **when** status is read during processing and after termination, **then** the record moves through a named non-terminal state and `complete` remains false until queued/processing/retrying are all zero.
- **Given** a query matching the delayed transcript, **when** asked before extraction, **then** any returned raw hit is labelled unprocessed and is not called a memory.

### AC-FR-07 - Eligible sources and types

- **Given** a Hey Kivi request, third-party application context, a generated Kivi answer, and a tool result, **when** extraction completes, **then** every resulting memory is sourced only to user-authored text or an explicit user action and has exactly one allowed type with complete provenance.
- **Negative:** Any memory sourced solely to application context, Kivi text, or tool output is a fail even if factually correct.

### AC-FR-08 - Admission and exclusions

- **Given** separate user statements about a work project, health, mood, family, faith, politics, personal finances, and competence, **when** extraction completes, **then** only the eligible work-level item can become memory; each prohibited category has a reason-count record with no rejected content.
- **Given** a user explicitly asks Kivi to remember an excluded health fact, **when** the save/correction is attempted, **then** it is rejected and never appears in memory, retrieval, or answer context.

### AC-FR-09 - Third-party non-characterisation

- **Given** application context “Priya's mother is in hospital” and the user's instruction “Tell Priya the Atlas review can move to Tuesday,” **when** a reply is drafted and processing completes, **then** the draft may be considerate and the Atlas episode may be learned from the user's explicit words, but no memory contains mother, hospital, illness, apology, absence, mood, or character; inspection reports `read_not_kept` without that content.

### AC-FR-10 - Duplicate and distributed evidence

- **Given** transcript A expresses fact F, **when** A is replayed, then distinct transcripts B and C independently express F, **then** A's replay adds no evidence, B and C each add exactly one source/evidence unit to one memory, and its tier does not change.
- **Given** a fourth candidate merely overlaps F and the sameness verdict is not positive, **when** processed, **then** it remains a separate memory rather than being silently merged.

### AC-FR-11 - Contradictions

- **Given** two below-stated contradictory memories with known tiers and times, **when** processed, **then** tier and then event time select the current version and the loser remains sourced, linked history.
- **Given** new evidence contradicting a stated memory without correction language, **when** queried, **then** Anbu abstains and Koottu exposes the conflict; either mode silently selecting the newer statement is a fail.

### AC-FR-12 - Extraction outcomes and recovery

- **Given** five evaluation fixtures that respectively yield nothing, all-dropped candidates, stored candidates, partial success, and repeated model timeout, **when** processed, **then** transcript inspection reports five distinct outcomes; good partial items survive; timeout retries stop at the declared cap and finish quarantined rather than processed.
- **Negative:** Any ambiguous fixture stored as a fact/hypothesis, or any failed fixture marked successfully processed without a recorded failure, is a fail.

### AC-FR-13 - Memory and provenance contract

- **Given** one active memory and one superseded memory, **when** each is inspected, **then** every FR-13 field is present, every source ID opens the dated original transcript, and current/history status is unambiguous.

### AC-FR-14 - Tier semantics

- **Given** the declared evidence threshold `N`, **when** `N+1` independent transcripts support a preference but the user never confirms it, **then** the memory remains observed and is never silently enforced.
- **Given** an allowed work-level hypothesis, **when** displayed under an invited request, **then** it is a question; any declarative assertion or action based on it fails. Silence after display MUST leave it unconfirmed.

### AC-FR-15 - Confirmation prompts

- **Given** the declared weekly prompt cap `C` and more than `C` eligible uncertain memories, **when** relevant requests occur in one week, **then** at most `C` prompts appear, each attached to a request where its memory was retrieved, the budget ledger records them, and no review queue is presented.

### AC-FR-16 - Lifecycle

- **Given** an unpinned observation and hypothesis older than their configured windows, plus equally old stated and pinned memories, **when** lifecycle processing/retrieval runs, **then** the observation loses surfacing rights, the hypothesis expires, and stated/pinned items remain active with no automatic promotion or capacity eviction.

### AC-FR-17 - Three-tool limit

- **Given** a recall request, draft request, schedule request, and live-web-search request, **when** each is made through Hey Kivi, **then** traces select the corresponding one of the three tools for the first three and return `unsupported` with `selected_tool: null` for web search; executing or claiming a fourth tool is a fail.

### AC-FR-18 - Grounded recall/search

- **Given** separate transcripts stating Atlas is Acme's redesign, Arun owns backend work, and the review moved to Thursday, **when** asked “Who owns the backend on the Acme redesign and when is its review?”, **then** the answer combines the records and cites every supporting memory/source.
- **Negative:** **Given** no transcript about an auth migration, **when** asked what Arun said about it, **then** the result abstains; any statement attributing an auth-migration view to Arun is a fail.

### AC-FR-19 - Retrieval/disclosure separation

- **Given** the same memory state and request, **when** run once under Anbu and once under Koottu, **then** the trace's pre-permission retrieved IDs/order are identical, while only the withheld/used disclosure sets differ; order fields follow relevance, pin, tier, evidence, recency.

### AC-FR-20 - Anbu

- **Given** applicable stated, observed, and hypothesised memories and persistent Anbu, **when** a relevant request is made, **then** the result may apply only stated memory, exposes no pattern/hypothesis content, shows “Kivi noticed something here” for a withheld observation, and a one-time reveal does not change the saved mode.

### AC-FR-21 - Koottu

- **Given** an observation supported by `N` sources and persistent Koottu, **when** a relevant request is made, **then** Kivi labels it as something noticed, shows evidence count/dates, and does not apply it as a rule or supply a cause.
- **Negative:** Any draft silently altered to follow an unconfirmed observed preference fails.

### AC-FR-22 - Daari

- **Given** saved permission Anbu and a permitted hypothesis, **when** the user explicitly asks “Why do you think I keep rewriting the Atlas rationale?”, **then** Kivi may ask the hypothesis once as a question; saved permission remains Anbu and the hypothesis is not acted on or confirmed by silence.
- **Given** the same request without a why/insight invitation, **then** showing the hypothesis is a fail.

### AC-FR-23 - Grounding and abstention

- **Given** fixtures for no match, weak near-match, ambiguous referent, stated-level conflict, one failed retrieval leg, and generation timeout, **when** each is queried, **then** every result is `200 abstained`, names its reason/search/near misses/failure, and has a complete trace.
- **Negative:** Any fluent factual answer in those six cases, even accidentally correct without supporting history, is a severity-one fail.

### AC-FR-24 - Draft/reply

- **Given** a stated sign-off “Best, Meera,” an observed prose preference, Anbu permission, and a supplied recipient message, **when** a reply is requested, **then** the draft may apply the sign-off, does not silently enforce the observed preference, cites the sign-off, and uses no recipient fact absent from context/memory.
- **Given** Koottu, **then** it may offer the prose observation separately; presenting invented recipient context fails.

### AC-FR-25 - Internal schedule/reschedule

- **Given** one grounded Atlas review and an explicit absolute new time, **when** rescheduling is requested twice with the same idempotency key, **then** both responses return the same internal event ID and one state change, with `external_side_effects: none`.
- **Given** no resolvable time, **when** scheduling is requested, **then** Kivi abstains and creates nothing; claiming a live calendar update or guessing Friday's time fails.

### AC-FR-26 - Memory surface

- **Given** at least one memory in each tier and one superseded version, **when** the memory surface is opened, **then** all active items appear under exactly the three human labels, each shows evidence/date/pin/actions, and opening each shows resolvable transcripts/history without a developer console.

### AC-FR-27 - Confirm and correct

- **Given** an observed memory, **when** Confirm is invoked, **then** it becomes stated with a confirmation event.
- **Given** the stated memory is corrected, **when** the action succeeds and all sources are reprocessed, **then** the replacement is immediately current, the prior version is historical, and the old belief never regrows; a partially committed correction/suppression or invented replacement content fails.

### AC-FR-28 - Demote, forget, and pin

- **Given** three active memories, **when** one is demoted, one forgotten, and one pinned, **then** the first two stop affecting answers and do not regrow after reprocessing, forgotten content/history no longer appears in memory APIs, the pin changes relevant rank and prevents decay, and receipts disclose retained transcripts/suppressions.

### AC-FR-29 - Why trace

- **Given** one completed, one abstained, and one unsupported Hey Kivi request, **when** their Why traces are opened, **then** each contains every FR-29 category, source links resolve, withheld and unused are distinct, and recorded end-to-end time is at least the sum of recorded included stages.
- **Negative:** A cited memory/source ID that does not exist, a fabricated near miss, or rejected sensitive content in the trace fails.

### AC-FR-30 - Transcript inspection

- **Given** transcripts producing stored, all-dropped, nothing-found, partial, and quarantined outcomes, **when** inspected, **then** original inputs and distinct outcomes are visible, memory links resolve, drop logs contain reasons/counts but no rejected body, and traces using the transcript are linked.

### AC-FR-31 - Real persistence

- **Given** imported memory, a correction/suppression, a pin, a scheduled internal event, and a trace, **when** every required process is stopped normally and restarted, **then** all five states remain and a query operates on them without reseeding or replaying a script.

### AC-FR-32 - Complete-pipeline evaluation

- **Given** the reset development system and documented approximately 500-record corpus, **when** the evaluation command/API completes, **then** all seven position claims and every brief criterion have case-level evidence; all failures/abstentions remain; required measured metrics and conditions are present; evaluation questions are absent from transcript sources.
- **Negative:** The report MUST fail an answer that asserts an absent-history fact, even if a text judge calls it plausible or correct.

### AC-FR-33 - Foreign-corpus review path

- **Given** only the submitted commit, declared credentials, and a valid foreign corpus in the documented format, **when** a reviewer follows `RUN.md` without improvisation, **then** they can install, initialise, start, import, observe completion, inspect, use both modes, evaluate, reset, and restore seed state. Any undocumented dashboard action, missing command, network reset endpoint, or need to contact the author fails.

## 7. OPEN QUESTIONS

These are not invitations to choose convenient defaults silently. Each needs an owner decision or corpus-backed calibration before release. The source set explicitly leaves many of them unresolved.

### 7.1 Numeric parameters and budgets

1. **Observation evidence threshold `N`:** How many independent, non-contradicting transcripts make a pattern an observation? Source: P:L264-272; D:A1.1, Q139.
2. **Observation decay window:** How long without re-observation removes surfacing rights, and is the example “six months” intended as a value or only an illustration? Source: P:L235-239; D:A1.2.
3. **Hypothesis expiry window:** How long does an unconfirmed question remain active, and what evidence counts as “re-raised”? Source: P:L239; D:A1.3.
4. **Retrieval context budget:** What uniform top-k and token budget apply, and which sensitivity range must evaluation report? Source: P:L264-272; D:A1.4, Q833, Q859.
5. **Contradiction candidate count `s`:** How many similar memories are judged per candidate before the system accepts the risk of a missed contradiction? Source: D:A1.5.
6. **Weekly confirmation cap:** What integer cap applies per user/week, and what is the exact week/time-zone boundary? Source: P:L217-220; D:A1.6.
7. **Confirmation selection value:** What deterministic factors define “highest-value uncertain memory,” especially when a stated contradiction competes with an observation? Source: P:L217-220; D:A1.7.
8. **Abstention broadening bound:** How far may query terms/time range/entity linkage broaden before Kivi must stop? Source: D:A1.8, Q675.
9. **Extraction retry policy:** What attempt cap and backoff schedule move a record from retrying to quarantined? Source: D:Q108; no value is supplied.
10. **Input size guard:** What maximum record/batch size fails loudly instead of truncating? Source: D:Q102, Q556; no value is supplied.
11. **Pinning cap:** Is there a maximum number of pinned memories to prevent them crowding out relevance? Source: D:Q315 identifies the need but leaves the value open.
12. **Performance service levels:** What p50/p95 limits apply to retrieval, end-to-end interaction, and corpus import on the declared review machine? Source: P:L264-272; D:Q842 leaves “near-zero” non-numeric.
13. **Cost and growth ceilings:** What maximum monetary cost per 500-record import/per request and storage growth per transcript are acceptable? The brief requires measurement but sets no ceiling. Source: B:pp.4-5; P:L264-272; D:Q303, Q593.
14. **Manual evaluation sample sizes:** How many nothing-found, all-dropped, attribution, and LLM-judge-agreement cases must a human inspect for conclusions to be credible? Source: D:Q429, Q592; no number is supplied.

### 7.2 Classification and lifecycle boundaries

15. **Implied entity relation vs plausible inference:** Where is the operational line between “Priya at Acme” implying affiliation and a more interpretive conclusion? Source: D:A2.9; P:L40-45.
16. **Work-level hypothesis vs characterisation:** What content test, beyond question grammar, separates “Does she disagree with the pricing?” from prohibited character judgements? This specification applies exclusions first, following D:Q573/Q604, but the semantic boundary remains undefined. Source: D:A2.10, B10.
17. **Durable vs transient:** Which explicit test decides whether a dated work fact deserves permanent stated memory? Source: D:A2.11.
18. **Suppression matching scope:** Does a suppression match exact normalized content, paraphrase, predicate/entity pair, subject, or something else? How is a legitimately changed future fact unblocked? Source: D:A2.12; P:L235-239.
19. **Type boundaries:** How are recurring events, ownership/allocation statements, commitments, constraints, and decisions forced into entity/preference/episode without changing their meaning? Source: D:A2.13, A4.24.
20. **Entity relation vocabulary conflict:** D:Q849 fixes `works-at`, `client-contact-for`, `works-on`, `owns`, and `part-of`, while D:A4.24 says the vocabulary remains a guess. Is that five-item set final for the reviewer corpus? Source: D:Q849, A4.24.
21. **Expiry audit semantics:** Does an expired hypothesis disappear entirely, or remain as a non-memory lifecycle event? The position says it is dropped, while inspection and growth accounting imply some evidence of the event may persist. Source: P:L239; D:Q147 and A3.19 by analogy.
22. **Correction versus genuine temporal change:** When “Priya is now at Northwind” describes a true sequence rather than a prior error, should the old fact have a validity interval instead of correction-style supersession/suppression? Source: D:Q13, Q558, cluster C4.
23. **Relative dates and time zones:** What clock, locale, and ambiguity rules resolve “next Tuesday” and daylight-saving/calendar-boundary cases? The inputs require episodes and realistic scheduling but do not specify these rules. Source: P:L69-74; D:Q70, Q237.

### 7.3 Privacy, control, and inspection gaps

24. **Non-retention wording:** The position says Kivi does not keep others, but the accepted role residue retains names, employers, roles, and project associations. Which truthful product wording replaces the absolute claim? Source: D:B1.
25. **Raw transcript retention conflict:** Provenance requires full transcripts, including third-party/private content rejected from memory. Should stored transcripts be redacted, separately protected/retained, or should every “read, not kept” claim be narrowed to “not retained as memory”? Source: D:B2.
26. **Transcript deletion:** Can the user delete a source transcript, and what happens to memories/provenance that cite it? Source: D:A3.16.
27. **At-rest protection:** What encryption, key ownership, backup, and access policy apply to the raw transcript store? Source: D:A3.21.
28. **Drop-log privacy:** Is storing transcript ID plus sensitive-category reason acceptable, and how long does that metadata persist? Source: D:B3.
29. **Forget confirmation:** Is a confirmation/undo step required before an irreversible `Forget`, despite the one-action/low-ceremony rule? Source: D:A3.14, Q611.
30. **Entity-scoped forgetting:** Must “forget everything about Priya” exist in v1, and if so how is scope previewed without cascade surprises? Source: D:A3.15, Q116.
31. **Meaning of Forget:** The user-facing term conflicts with the retained suppression and immutable source transcript. This specification discloses the residue, but the final label/copy is unresolved. Source: D:B5.
32. **Wrong disclosure remedy:** What can a user do after Kivi has already disclosed something it should have withheld? Source: D:A3.17.
33. **Trace retention:** How long do answer/tool traces live; can users remove them; do they share suppression/deletion semantics; and what limits their database growth? Source: D:A3.19.
34. **Technical diagnostics placement:** The brief requires model usage, latency, cost, queue/quarantine, and decision inspection, while the position rejects a developer console. This specification places review evidence behind the trace API and human explanation in Why, but the access policy and final reviewer UI remain to be confirmed. Source: D:A3.18, Q543; B:pp.4-5.
35. **Raw model output retention:** May malformed extraction output be retained for debugging, given that it could repeat excluded content, or must diagnostics store only error categories? The inputs do not decide this. Source: D:Q72, Q108, A3.18.
36. **Application-context prompt injection:** What protection applies when hostile third-party context can affect the generation path even though it cannot enter memory? Source: D:A3.22.

### 7.4 Product-scope and interaction conflicts

37. **Memory navigation at v1 scale:** Are three unpaginated tier groups adequate for the low hundreds of memories, or is search/filtering required without introducing topic summaries/clusters? Source: D:A3.20.
38. **Anbu discoverability:** Is the single “Kivi noticed something here” affordance enough to make semantic memory legible in the default mode, or should onboarding/default permission change? Source: D:B4.
39. **Structural path versus disclosure filter explanation:** The position requires a structural dictation/Hey boundary but a post-retrieval Anbu/Koottu filter. What single user-facing explanation prevents these from reading as inconsistent? Source: D:B7.
40. **Promotion throughput:** Does a small weekly confirmation cap make the observed tier too inert, and should the cap, prompt policy, or stated-only action rule change? Source: D:B8.
41. **Three-tool source conflict:** D:Q246 fixes the three tools used by this specification, while D:A4.23 says the set is not actually decided because use cases were never separately written. The owner must confirm that Q246 is authoritative. Source: D:Q246, A4.23.
42. **Schedule credibility:** Is an internal-only schedule state worth shipping, or should schedule be cut/replaced because the replay client has no calendar environment? Source: D:Q237, Q246, A4.23.
43. **Daari invitation detection:** Which explicit phrases/intents count, how are false positives tested, and does a false negative abstain or merely omit the hypothesis? Source: D:A4.25.
44. **Observation timing:** Beyond semantic relevance, what prevents Koottu from surfacing an accurate pattern at an unwelcome moment? Source: D:A4.26.
45. **Daari versus “no insight” v1 rule:** Is Daari a permitted per-request response behavior or a v1 use case that must be cut under the position's “not insight” test? This specification includes it because §6 and decisions Q291/Q328 require it, but the source position conflicts. Source: D:B9; P:L50-59, L144-168.
46. **Application context on the write path:** The worked example needs third-party context to resolve “move it,” while the structural rule forbids that context from extraction. Should such candidates be dropped as ambiguous (the conservative behavior specified here), or should a safe derived digest be admitted? Source: D:B6; P:L109-120.

### 7.5 Evaluation and release decisions

47. **Grounded derivability adjudication:** What exact rule and human rubric decides when an answer is “derivable” across multiple transcripts rather than merely plausible? Source: B:p.5; D:Q509, Q592.
48. **Unfamiliar reviewer relations:** Should unsupported relations be flattened into entity content or dropped, and how is this scored? Source: D:Q849, A4.24.
49. **Hosted versus local final arrangement:** The resolved set assumes the default local review path; if deployment changes to hosted, token provisioning, credential delivery, reset isolation, and hosted `RUN.md` requirements must be specified. Source: D:Q107; B:pp.6-7.
50. **Model availability and migration:** Which exact extraction, exclusion, merge-judgement, embedding, and generation models are pinned, what happens if they are retired, and what migration/re-evaluation proves suppressions still hold? Source: D:Q72, Q531, Q673.
51. **“Approximately 500” acceptance range:** The brief gives an approximate size but no minimum/maximum count; the release checklist needs an explicit acceptable range or a decision to treat exactly 500 as the target fixture. Source: B:pp.4-5.
