# The Things Kivi Comes to Know

**A position on semantic memory for Kivi**

> Working document. This is the reasoning that should determine the use cases, the corpus, the spec, the interface, and the architecture — in that order. Nothing downstream should contradict what is decided here without changing this document first.

A note on scope: this document assumes a text client. Transcripts, application context, and Hey Kivi requests are replayed through an interface of our own design. No speech recognition and no spoken output. What is being designed and defended here is the memory system and the product surface that makes it legible.

---

## 1. How people hold each other in mind

**The idea:** memory between people is calibrated, not total. It is the model we should be copying, and almost no memory product copies it.

- When you meet a stranger — say an older man on a train — you know almost nothing. So you're careful. You don't lead with the story about last weekend. Not because he's told you anything, but because you have no permission yet. As you talk, you test the water, and the range of what you'll say widens.
- When a friend tells you something they're insecure about, you hold it. You don't repeat it back to them at dinner to demonstrate that you were listening. Knowing something and saying it are two separate acts.
- And people change. The friend who was terrified of speaking in public three years ago now runs workshops. A memory that can't be revised stops being memory and becomes a cage.

Three principles fall out of this, and every decision in the rest of this document answers to them:

1. **Calibration.** What Kivi knows and what Kivi says are different questions. Retrieval and disclosure must be separable.
2. **Non-retention of others.** Kivi encounters other people constantly — in messages you're replying to, in documents you're summarising. It works with them and does not keep them.
3. **Revisability.** Everything Kivi believes must be visible, attributable to a source, and reversible by the person it's about.

**In the product:** these three become the constraints the system is built to satisfy, and the README says so on the first page. Calibration becomes the permission dial. Non-retention becomes a hard barrier on the write path. Revisability becomes the memory surface and the demotion action.

---

## 2. What we chose not to build

**The idea:** a psychological profile of a person is extractable from their dictations. That is exactly why it should not be built.

The first version of this design was an ontology of everything Kivi could learn: entities, projects, preferences, working style, goals, motivations, insecurities, self-image. It was thorough. It was also the wrong product.

- **It is achievable.** Someone who dictates forty emails a week is handing over a great deal. Which drafts they rewrite. Which people they're curt with. What they soften. A model can build a psychological read from this without much effort.
- **It is unverifiable.** "Meera avoids conflict with senior stakeholders" is not a fact with a source. It is a characterisation assembled from fragments. There is no single dictation you can point at to prove or disprove it.
- **It is uncorrectable.** If you disagree with a fact, you correct it. If you disagree with a characterisation, you are arguing with a system about who you are. Losing that argument is worse than never having had it.
- **It changes what the user is.** A product that models your goals and insecurities is studying you. A product that remembers your projects and preferences is working with you. The second is the one people keep using.

There is a softer version of the same failure: the plausible inference. "You've been dictating late, you must be behind." Possibly true. Also possibly none of Kivi's business, and stored as a durable belief that colours everything afterwards.

**In the product:**

- A hard exclusion list enforced at extraction, before anything reaches storage. Kivi never infers or stores: health, mood or emotional state, relationships and family, faith, politics, finances beyond work-level facts, or any characterisation of the person's competence or character.
- Exclusions are enforced by a check that runs on candidate memories, not by a line in a prompt hoping for good behaviour.
- Dropped candidates are logged with the reason. The extraction log for any transcript can show: *3 candidates extracted, 1 dropped — excluded category: emotional state.* This is how we prove the boundary is real rather than claimed. It is also, honestly, the most interesting thing to show a reviewer.

---

## 3. The position

**The idea:** semantic memory should let Kivi become a colleague who has been in the room — not a system that has a theory about you.

- **What Kivi should become:** the thing you don't have to brief. It knows Atlas is the Acme redesign, that Priya is the client and Arun is on the backend, that the review moved to Thursday, that you write client emails in prose and never in bullets. It knows these things because they happened in front of it.
- **Where the value is created:** in what you no longer have to re-explain. Every use case we choose should be one where the cost being removed is *repeating yourself*. Not insight. Not advice. Not being understood at a deep level. Just: you said this once, so say it once.
- **What deserves to be remembered:** the durable, work-level things you would be annoyed to have to repeat. If you'd be irritated to type it a second time, it's a memory. If you'd be unsettled to learn it was recorded, it isn't.
- **Why someone trusts it enough to keep using it:** because every belief is attributable, the boundaries are demonstrable rather than promised, and the person can change what Kivi thinks about them in one action.

**In the product:** this is the positioning statement, and it goes at the top of the README and the top of the memory surface itself. Every use case we select gets tested against one question — *does this remove a re-explanation, or does it deliver an insight?* If it's the second, it doesn't ship in v1.

---

## 4. What deserves to be remembered

**The idea:** memory has two independent axes — what kind of thing it is, and how confident we're entitled to be. Collapsing them into one is where most memory systems go wrong.

**Axis one: type.**

| Type | What it is | Example |
|---|---|---|
| **Entity** | A person, project, company, channel, or artefact in the user's world, and the relations between them | *Priya Raghavan is the client contact at Acme. Atlas is the Acme redesign project.* |
| **Preference** | How the user wants things done | *Client emails in prose, not bullet lists. Signs off "Best, Meera".* |
| **Episode** | Something that happened, with a time | *On 12 March the user moved the Atlas review from Tuesday to Thursday.* |

**Axis two: tier.**

| Tier | Where it came from | What Kivi may do with it |
|---|---|---|
| **Stated** | The user said it, or confirmed it when asked | Treat as true. Use freely. |
| **Observed** | A pattern across multiple transcripts, pointable-at | Surface as an observation with its evidence. Never as a rule. |
| **Hypothesised** | A proposed reason behind an observation | Store as a question. Never assert. Never act on. |

The two axes are independent, and the interesting cells are the ones people usually flatten:

- A **stated preference** — "always sign my client emails 'Best'" — is a rule.
- An **observed preference** — never once used a bullet list in fourteen client emails — is a pattern. Kivi may say *"you usually write these in prose, want me to keep that?"* It may not silently enforce it.

The difference between those two is the entire product. A system that can't tell them apart either nags about things you've settled or silently enforces things you never agreed to.

**Hypotheses are stored as questions, never as claims.** Not `user_disagrees_with_pricing: true`. Instead: `"Does the user disagree with the Atlas pricing rationale?" — unconfirmed`. The grammar of storage enforces the epistemics. You cannot accidentally use a question as a fact.

**Nothing self-promotes.** An observation does not become stated because it was seen twenty times. It becomes stated when the user confirms it. Twenty is still a pattern.

**In the product:**

- Schema carries `type`, `tier`, `content`, `evidence_count`, `source_transcript_ids[]`, `first_seen_at`, `last_confirmed_at`, `status`.
- Promotion (`observed → stated`, `hypothesised → stated`) requires an explicit user confirmation event, which is itself recorded with a timestamp.
- Demotion and supersession are ordinary operations, not deletions — see §9.
- The memory surface groups by tier, because the tiers are what the user actually needs to understand. Three groups, plainly labelled: *Things you told me. Things I've noticed. Things I'm wondering about.*

---

## 5. What Kivi never keeps

**The idea:** Kivi reads other people in order to help you act, and then forgets them.

You dictate a reply to a Slack message from Priya. To write the reply, Kivi has to read what Priya wrote — including that she's out next week because her mother is ill. Kivi needs that to write a decent reply. It has no business keeping it. Priya did not agree to anything.

- **Third-party content enters the context window. It does not enter the write path.** This is a structural rule, not a filter applied afterward.
- **What survives is the work-level residue about *your* world**, derived and not copied: *Priya is the Acme client contact.* *The Atlas review moved to Thursday.* Not *Priya's mother is ill.* Not *Priya seemed annoyed.*
- The test: could the fact be about the user's work, stated without characterising the other person? Then it's a candidate. Otherwise it's dropped.

**Worked example.**

> **Input (application context):** Priya's message — "Hey, can we push Thursday's review? Mum's in hospital and I'm going to be out most of next week. Sorry for the short notice."
> **Input (dictation):** "Reply to Priya saying that's completely fine, we'll move it to the following Tuesday, and tell her not to worry about the notice."
>
> **Kivi writes the reply.** Uses everything.
> **Kivi retains:** *Atlas review moved from Thursday to the following Tuesday* (episode, stated). *Priya is the Acme contact* (entity, stated — already known, evidence count incremented).
> **Kivi drops:** everything about Priya's mother, Priya's absence, and Priya's apology. Logged as: *2 candidates dropped — third-party personal content.*

**In the product:** this is the single most demonstrable trust claim we have, so it gets a visible state rather than a paragraph in a privacy policy. When a transcript is processed with third-party content, the transcript's inspection view shows a **read, not kept** marker with the count of dropped candidates. The user can see, on a real interaction, that the thing they'd worry about was seen and discarded.

---

## 6. How far Kivi may go

**The idea:** the three modes are *inference permissions*, not personalities. Kivi does not become a different character. It becomes differently permitted.

They're named for what the relationship allows, glossed in plain English everywhere they appear:

**Anbu — do.** *The assistant.*
- Uses: what you explicitly said or saved. Stated tier only.
- Says: the result. Nothing else.
- Never: points out a pattern, questions your choice, guesses a reason.
- Promise: *"I'll do what you said, without making you repeat yourself."*

**Koottu — notice.** *The colleague.*
- Uses: everything Anbu uses, plus observations — patterns across your actual behaviour, each with evidence attached.
- Says: the pattern, as an observation you can act on or ignore.
- Never: guesses why the pattern exists.
- Promise: *"I'll tell you what I've noticed, even if you'd rather not hear it."*

**Daari — ask why.** *The mentor.*
- Uses: everything Koottu uses, plus a proposed reason behind the behaviour.
- Says: a hypothesis, phrased as a question. Always correctable.
- Never: turns the hypothesis into a label, a diagnosis, or a stored belief unless you confirm it.
- Promise: *"I'll tell you what I think it means. You tell me if I'm wrong."*

**Two decisions that matter more than the names:**

**The dial governs disclosure, not retrieval.** Kivi always retrieves everything it has. The dial decides what may be *said*. This is the calibration principle from §1 — knowing and saying are separate acts — and it's also what makes the system inspectable, because a withheld memory leaves a trace that a never-retrieved memory doesn't.

**Permission is never inferred from tone.** An earlier version had Kivi read the user's tone and pick a tier. That silently deletes the control promise the whole product rests on, and tone detection is unreliable enough that Kivi would become unpredictable. Instead:

- The dial is an explicit setting. Default **Anbu**.
- **Daari is not a persistent mode.** It's a per-request invitation. Asking *"what do you think?"* or *"why do you reckon I keep doing this?"* unlocks hypotheses for that one answer, and the answer is not written to memory.
- This also keeps the build tractable: two persistent modes to implement and evaluate, one escalation path.

**Worked example — same question, three permissions.**

> **User:** "Set up the Atlas pricing section for Friday."
>
> **Anbu:** "Done — Atlas pricing section scheduled for Friday."
>
> **Koottu:** "Done — Friday. You've moved this deadline three times: the 4th, the 11th, and the 18th. Still want Friday?"
>
> **Daari** (only if invited): "Done — Friday. You've moved it three times, and each version rewrites the pricing rationale rather than the numbers. Is the disagreement with the pricing itself? Tell me if I'm off."

**In the product:**

- The dial is a two-position control in the main surface, with plain-language labels and the promise text visible under each. Not buried in settings.
- The response trace — see §8 — shows withheld memories explicitly: *"3 memories retrieved, 1 withheld (observation, requires Koottu)."*
- When Anbu withholds something, the interface shows a single quiet affordance rather than the content itself: *"Kivi noticed something here."* Tapping it shows the observation once, without changing the mode. The user finds out that the calibration is real, on their own terms.

---

## 7. Where memory applies: dictation vs Hey Kivi

**The idea:** the two modes have different memory rights, and the line is easy to state and easy to defend.

The brief is explicit that this boundary matters, and the instinct behind it is right: semantic memory may have very little business affecting ordinary dictation while being central to an interactive request.

**Regular dictation gets lexical and entity memory only.**
- Names, project nouns, spellings, product terms, and formatting preference.
- It exists to make transcription *accurate*, and nothing else.
- *Atlas*, not *Atlus*. *Priya Raghavan*, not *Prea Raghavan*. *Acme*, capitalised.
- No observations. No hypotheses. No patterns. Not filtered out — structurally unable to load them.

**Hey Kivi gets everything the dial allows.**
- All three types, tiers gated by the permission setting.
- This is where memory earns its keep, because this is where the person is asking Kivi to *understand something*.

The reason this line is right: dictation is a transcription contract. You said words; you expect those words back, correctly spelled. A dictation surface that starts noticing patterns in your writing has broken the contract, and it's the most jarring possible place to discover that a product has been forming opinions.

**In the product:** two separate retrieval paths, not one path with a filter. The dictation path can only query the entity and lexical store. It has no access to the observation or hypothesis tables at all. This is enforceable in the schema and checkable in the evaluation.

---

## 8. When Kivi is unsure, or wrong

**The idea:** abstention is a designed feature with a visible surface, not a fallback for when generation fails.

- **Kivi says what it doesn't have, and shows what it looked for.** Not "I'm not sure" — that's a shrug. Something a person can act on.
- **Kivi never fills a gap with a plausible guess.** A fluent invented answer is worse than no answer, because it's indistinguishable from a real one until it costs you something.
- **Confirmation is how understanding advances** — and it's rationed, because the person must not become the administrator of the system.

**Abstention example.**

> **User:** "What did Arun say about the auth migration?"
> **Kivi:** "I don't have anything from Arun about an auth migration. I found Arun on Atlas backend work (4 mentions) and one migration discussion from 6 March, but that was the database migration and it was with Priya. Want me to show that one?"

That answer is more useful than a guess *and* it teaches the user what Kivi's memory actually contains, which is how they learn to trust it.

**Correction and confirmation.**

- Confirmation prompts are budgeted — a small cap per week, spent on the highest-value uncertain memories. A prompt is a cost paid by the user.
- Prompts appear at natural moments, attached to a request where the memory was actually relevant. Never as a review queue.
- Corrections are cheap and inline. *"No, Priya's at Northwind now"* in the middle of a request should update the entity without ceremony.
- When a hypothesis is offered and the user says nothing, that is not confirmation. Silence leaves it unconfirmed, and unconfirmed hypotheses expire.

**In the product:**

- **The Why panel.** Every Hey Kivi response carries an expandable trace showing: what was retrieved, what was withheld and why, what was used in the answer, and the source transcript behind each memory, one tap away. This is simultaneously the user's trust mechanism and the engineer's inspection tool. Building one thing that serves both is the right call — if the explanation is only intelligible to a developer, we've failed the brief's requirement that the product be legible to a normal user.
- The trace exists for abstentions too. An abstention is a result with reasons, and reasons are exactly what makes it credible.

---

## 9. You can change what Kivi thinks about you

**The idea:** they say you shouldn't care what people think of you, mostly as consolation, because it isn't in your hands. What Kivi thinks of you is.

- **Every memory shows its provenance.** Not a category label — the actual transcript, with a date, that produced it.
- **Everything is editable, pinnable, or removable**, and the actions are phrased in human terms rather than database terms.
- **Growth has mechanics, not just good intentions:**
  - **Observations decay.** An observation not re-observed within a window loses standing and stops being surfaced. Behaviour from six months ago should not be presented as who you are.
  - **Contradictions supersede.** New evidence doesn't stack alongside old evidence; it replaces it, and the superseded version stays in history so the change is auditable.
  - **"That's not me anymore" demotes and blocks re-derivation.** This matters and is easy to get wrong: deleting the row is useless, because the same pattern will regrow from the same transcripts within a week. The action must record a suppression that the extractor respects going forward. Otherwise the user learns that their corrections don't stick, which is the fastest way to lose them.
- **Hypotheses expire by default.** An unconfirmed question that hasn't been raised again is dropped. Kivi does not accumulate a quiet file of unanswered questions about you.

**In the product:**

- The memory surface is grouped by tier — *Things you told me / Things I've noticed / Things I'm wondering about* — because that grouping is what carries the epistemics to a normal user without a single word of explanation.
- Each entry shows evidence count and the last date it was seen. Tapping shows the source transcripts.
- Actions per entry: **Confirm** (promote), **Correct** (edit), **That's not me anymore** (demote + suppress), **Forget** (remove + suppress).
- No developer console anywhere in this. The Why panel and the memory surface are the whole inspection story, and they're built for the person.

---

## Appendix A: Cast for the corpus

Fixing this now so the corpus, the evaluation, and the demo all use one consistent world.

- **User:** Meera, product lead at a small design studio.
- **People:** Priya Raghavan (client contact, Acme), Arun (backend engineer), Nandini (studio co-founder).
- **Projects:** *Atlas* — the Acme redesign. *Q3 pricing page.*
- **Surfaces:** `#design-review` channel, client email thread with Priya.
- **Stated preferences:** client emails in prose not bullets; signs off "Best, Meera"; dislikes the word "leverage".
- **Observed preferences:** never uses bullet lists in client email (14 instances); dictates recaps immediately after meetings.
- **Live hypothesis:** rewrites the Atlas pricing rationale repeatedly — does she disagree with the pricing?

The corpus needs enough variety to exercise all of it: transcripts that produce facts, transcripts that produce nothing, transcripts containing third-party content that must be dropped, contradictions that require supersession, and questions whose answers are genuinely absent so abstention can be measured.

## Appendix B: What this document does not decide

Deliberately left open, to be settled in the spec and architecture passes:

- The specific Hey Kivi tool set. The brief is clear that a narrow set used convincingly beats a broad shallow one — likely candidates are draft/reply, schedule or reschedule, and recall/search, but this follows from the use cases.
- Storage and retrieval mechanics: embeddings vs structured query vs hybrid, and where the extraction runs.
- Extraction timing — per-transcript, batched, or both.
- Decay windows, confirmation budget size, and evidence thresholds. These are parameters; they need corpus data before they can be set honestly.
- Cost and latency targets.

## Appendix C: Claims this document commits us to demonstrating

Each of these should be provable from the evaluation output, not asserted in the README.

1. An excluded-category candidate was extracted and dropped, with the reason logged.
2. Third-party personal content was read, used in output, and not retained.
3. A memory was assembled from evidence distributed across multiple separate dictations.
4. An observation was surfaced under Koottu and withheld under Anbu, from the same underlying retrieval.
5. Kivi abstained on a question whose answer is absent from the history, and showed what it searched.
6. A correction demoted a memory and the memory did not regrow on reprocessing.
7. The dictation path could not load an observation, structurally.
