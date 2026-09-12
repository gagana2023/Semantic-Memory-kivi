# The Decision Space of `Agent_Memory_Techniques`

**A decision-space extraction, read against [The Things Kivi Comes to Know](./kivi-semantic-memory-position.md)**

> Source: [NirDiamant/Agent_Memory_Techniques](https://github.com/NirDiamant/Agent_Memory_Techniques) @ `b7f7240`
> Cloned to `./Agent_Memory_Techniques`. Analysis date: 2026-09-09.

**Citation convention:** notebook citations are `file:N` where N is the **raw line number in the `.ipynb` JSON**, so `grep -n` will find them. A handful of code cells sit inside a single JSON string and I couldn't resolve a per-line offset; those are cited to the cell's first resolvable line and flagged with "ish".

---

## ORIENT

**What this repo is — and it changes the exercise.** `Agent_Memory_Techniques` is not a working system. It is a teaching corpus: 30 self-contained Jupyter notebooks, one per memory technique, each of which redefines its own `Memory` dataclass, its own `cosine_similarity`, its own store. There is no shared runtime. There is no entry point. Nothing calls anything else.

That matters for the brief. The task was to recover the questions behind a working system's answers. Here, the answers were never load-bearing — they were never under production pressure, never revised, never contradicted by a user. So what follows maps a **space of demonstrated options**, not a set of survived decisions. Where I'd normally say "they chose X and it held," I can only say "they showed X and never tested it." That distinction is flagged throughout rather than allowed to inflate the findings.

### Core logic vs. glue

- **Real logic:** each notebook's code cells. The Kivi-relevant ones are `10_semantic_memory` (extract → dedupe → contradict → archive → retrieve), `19_forgetting_and_decay` (decay/reinforce/prune), `14_memory_consolidation` (cluster → merge → resolve conflict), `18_temporal_memory` (bi-temporal, as-of queries), `07_entity_memory` (entity KV store), `20_memory_retrieval_patterns` (BM25/RRF/rerank/MMR), `17_memory_routing` (write-time classification), `30_production_memory_patterns` (tiering, PII, budgets, GDPR delete).
- **Glue:** `utils/helpers.py` (6 functions: env loading, two client factories, token count, cosine, message formatting). That is the entire shared library — 192 lines. Notably, **the notebooks don't import it.** Each one re-implements `cosine_similarity` inline (`10_semantic_memory/semantic_memory.ipynb:177`, `18_temporal_memory/temporal_memory.ipynb:166`, `19_forgetting_and_decay/forgetting_and_decay.ipynb:385`, `20_memory_retrieval_patterns/memory_retrieval_patterns.ipynb:243`).
- **Adapters/integrations:** techniques 24–27 (Graphiti, Mem0, Letta, Zep) — third-party wrappers, skipped for depth.

### Data model

No migrations, no SQL schemas, no serialization format beyond `json.dump` of `dataclasses.asdict`. The load-bearing decisions are frozen in ~8 independent dataclasses that never reconcile with each other: `Fact` (`10:164`), `DecayableMemory` (`19:173`), `TemporalMemory` (`18:195`), `MemoryRecord` (`30:153`), `MemoryEntry` (`17:132`), plus the untyped `dict` records in `EntityStore` (`07:126`). Persistence is a JSON file per notebook (`10:678`, `07:181`).

### Main execution path

Technique 10, the closest analogue to Kivi's write path:

`process_conversation` (`10:381`) → `extract_facts` (LLM, `10:275`) → `_embed_batch` (`10:251`) → `_find_match` (`10:315`) → one of append / boost / archive-and-append → `retrieve` (`10:435`) → `chat` (`10:448`). Persistence is a manual `save_memory` call at the end.

### Config surface — this is the finding

There is no config surface. No settings file, no CLI flags, no feature toggles. `.env.example` holds six API credentials and nothing else. Every threshold is either a constructor default or a literal in a demo cell. Nothing is environment-driven; nothing is validated; nothing has a range check.

### What the tests exercise

`tests/test_helpers.py` tests cosine similarity, string formatting, and env-var errors. `tests/test_imports.py` checks that every code cell **parses as Python** and that ≥30 notebooks exist (`tests/test_imports.py:28`). `utils/validate_cells.py` enforces cells ≤60 lines and a markdown cell before every code cell. `utils/validate_style.py` enforces banned words and no em dashes in prose. **The CI validates formatting and syntax. No test executes a single memory operation.** Details in §6.

### Coverage

**Read:** all of `utils/`, `tests/`, CI config, `.env.example`, `requirements.txt`; full code of notebooks 07, 10, 14, 17, 18, 19, 20, 30; tradeoff/limitations prose of 07, 10, 19, 30; full git log with per-commit file lists; a repo-wide regex sweep for numeric constants and shortcut admissions.

**Skipped:** notebooks 01–06, 08, 09, 11–13, 15, 16, 21–29 beyond the constant sweep and cell-name scan; `docs/` (architecture.md, FAQ, glossary) — read only enough to confirm they are narrative teaching prose, not spec; all images/diagrams. GitHub issues and PR discussion: merge commits only, no network access to the issue tracker.

---

## 1. DECISION INVENTORY

### 1.1 What enters the system

**Q: Does the write path see raw conversation, or a filtered subset?**

Answered: raw. `extract_facts` (`10:277`) concatenates every message, both roles, into one blob and hands it to the LLM. `EntityMemory.chat` (`07:425`) passes both the user message *and the assistant's own generated reply* into extraction — so the model's output becomes a memory source. **Hardcoded.** No hook, no filter, no parameter.

*Assumes:* single-party conversation, both sides trustworthy, everything in the window is about the user. Cost of a wrong extraction is zero because nobody is watching.

*For Kivi:* this is the sharpest divergence in the repo. §5 requires third-party content to enter the context window and **structurally not enter the write path**. Nothing here has that shape — there is one path, and it reads everything it was given. The repo offers no precedent for a two-input write path (dictation + application context with different retention rights). Pushes toward designing that yourself, and toward treating the extraction input as a typed, per-source structure rather than a flat transcript. Note also that extracting from the assistant's reply (`07:425`) is exactly the mechanism that would let a Kivi-generated inference become a Kivi-stored fact — a loop the tier model forbids.

**Q: Is anything excluded at extraction time?**

Answered: only by prompt instruction, and only for form, not category. The rules at `10:212-218` exclude greetings, questions, hypotheticals, and anything over 20 words. `30`'s `PIIHandler.redact` (`30:666`) is the only category-based exclusion, it runs on the *stored string* (regex over email/phone/SSN/card/IP, `30:646-652`), and it **redacts rather than drops** — the memory is kept with `[REDACTED_EMAIL]` substituted and a `pii_redacted` flag set (`30:167`, `30:994`). **Configurable per-call** via `redact_pii: bool = True` (`30:988`), which is a revealing placement: it's a toggle, so they weren't confident it should always run.

*Assumes* PII is lexically detectable and that redacting the span preserves a useful memory. Their own prose concedes both failures (`30`, md cell 56): regex "won't detect names, addresses, or context-dependent PII without NER," and — the important one — **"even if text is redacted, embeddings may encode PII."**

*For Kivi:* the §2 exclusion list (health, mood, relationships, faith, politics, finances, characterisations) is *semantic*, not lexical. Regex cannot see it. And §2 says exclusions must be "enforced by a check that runs on candidate memories, not by a line in a prompt hoping for good behaviour" — the repo does exactly the thing you've ruled out (`10:212`) except for the regex layer. The embedding-leakage point is a live hazard: if you embed a candidate before the exclusion check, the excluded content is already in your vector store. Pushes toward: check before embed, and drop rather than redact.

**Q: Extraction — one LLM call per turn, or batched?**

Answered: per exchange, synchronously, inline with the response. `07:425` runs extraction on every turn inside `chat`. Their own tradeoff prose calls it out (`07`, md cell 38): "roughly doubles the per-turn API cost… For production, consider extracting entities asynchronously or batching extraction every *N* turns." **Hardcoded**, and admitted to be the wrong answer at scale — an unusual case where the repo names the alternative it didn't take.

*For Kivi:* Appendix B leaves extraction timing open. The repo's cost model (`10`, md cell 35: "2-5 API calls" for a turn producing 3 facts) is the number to reason from. Dictation volume — forty emails a week — makes per-transcript extraction affordable in a way per-turn extraction isn't. Different shape, less pressure toward batching than they faced.

**Q: Does extraction have an "extracted nothing" path?**

Answered: yes, explicitly. `NONE` sentinel at `10:218`, honoured at `10:289`. Also `07:294`: "If no entities are found, call it with an empty list." Deliberate, and worth noting — plenty of extraction pipelines don't have this.

*For Kivi:* you need this *and* its inverse — the drop log. `NONE` distinguishes "nothing here" from "found things, kept none." Appendix C.1 and C.2 both require the second. Nothing in the repo produces a per-candidate drop reason; the closest is `stats` counters (`10:391`) and `PIIHandler.audit_log` (`30:676`), which logs deletions, not extraction drops.

### 1.2 How it's represented

**Q: One memory type, or several?**

Two answers coexist in the repo, uncombined. Technique 10 stores one flat kind (`Fact`, `10:164`) with a float `confidence`. Technique 17 stores three kinds in three separate stores routed by an LLM classifier (`17:125-129`, `17:277`). **Both hardcoded; neither is pluggable.** Technique 17's routing is *write-time* — the classifier decides which store a memory lands in (`17:284-291`), returning a list, so a memory can land in more than one.

*Assumes* the type is inherent to the content and decidable by an LLM at write time from the text alone.

*For Kivi:* §4 is a **two-axis** model — type (entity/preference/episode) × tier (stated/observed/hypothesised). Technique 17 gives precedent for axis one only, and does it by *classifying content*. Axis two is not a property of the content at all — it's a property of the *provenance and evidence*, which you know at write time without asking a model. That asymmetry matters: nothing in this repo suggests you should classify tier with an LLM, and everything about `17:277` (an LLM call, `temperature=0`, JSON parsed with a bare `json.loads` at `17:303` and no try/except) suggests you shouldn't.

**Q: Confidence — a scalar, or a categorical epistemic status?**

Answered: a scalar, everywhere. `Fact.confidence: float = 0.8` (`10:168`), `MemoryRecord.importance: float = 0.5` (`30:163`), `DecayableMemory.strength: float = 1.0` (`19:179`). And crucially, **confidence is arithmetic**: `existing.confidence = min(1.0, existing.confidence + 0.05)` on every repeat mention (`10:403`).

This is the single most consequential divergence from the Kivi position. That line is auto-promotion. A fact seen four times ends at 1.00. §4 says in terms: *"Nothing self-promotes. An observation does not become stated because it was seen twenty times."*

The repo also *shows* the scalar leaking to the user: `chat` renders confidence into the system prompt as a number the model is told to use naturally (`10:456`, `10:461`). So the epistemic status is both auto-inflating and directly disclosed, with no gate.

**Hardcoded** — `+0.05` is a literal, not a parameter, unlike the two thresholds beside it (`10:235-236`) which *are* constructor args. That asymmetry is the tell: they parameterised what they expected to tune and inlined what they never questioned.

*Assumes:* repetition is evidence; a single number can carry both "how sure am I" and "may I say it." Cost of over-confidence is zero in a demo.

*For Kivi:* the `tier` + `evidence_count` + `last_confirmed_at` schema splits exactly what this collapses. The repo is a clean worked example of the named failure mode. Where a difference pushes: keep `evidence_count` as a count and never let it feed a promotion rule; make promotion an event with a timestamp (§4), not an accumulator.

**Q: Is there any bi-temporal modelling?**

Answered: yes, in exactly one notebook. `TemporalMemory` separates `created_at` (when we learned it) from `event_time` (when it happened), defaulting the second to the first (`18:200-208`). `query_as_of` (`18:510`) then filters `m.created_at <= as_of` and scores recency against `as_of` — genuine point-in-time reconstruction of what the system believed at a past moment.

**Hardcoded into that one notebook and used by no other.** `Fact` (`10:164`) has only `created_at`/`last_confirmed`; `MemoryRecord` (`30:160`) only `created_at`/`last_accessed`.

*For Kivi:* `query_as_of` is the most directly reusable thing in the repo. §9 requires "the superseded version stays in history so the change is auditable," and the Why panel (§8) has to explain a past answer. That is an as-of query. Assumption check: `18` assumes a single monotonic clock and no retraction — a memory that was wrong is still visible as-of, which is what you want for audit, but `18` has **no supersession or invalidation concept at all** (`grep -c "supersed\|invalid"` → 0). You get the read side of the pattern and none of the write side.

### 1.3 What's discarded

**Q: On dedupe, does the old record survive?**

Answered: yes in technique 10, no in technique 14. `10:407-414` sets `existing.archived = True` and appends the new fact — the old row stays queryable via `mem.facts`, filtered out of reads by `if fact.archived: continue` (`10:327`, `10:440`). `14:526-527` does the opposite: `working = [m for m in working if m.id not in loser_ids]` — the losing memory is **dropped from the list and never written anywhere**. Duplicates in 14 are worse: the group is replaced by an LLM-authored merged string (`14:507-520`), so the original wording of every merged memory is gone.

**Both hardcoded.** No archive/purge switch in either.

*For Kivi:* technique 10's soft-archive is the pattern §9 needs ("Contradictions supersede… the superseded version stays in history"). Technique 14 is the anti-pattern, and it's worth being precise about why: `merge_memories_with_llm` (`14:363`) destroys provenance. §9 requires every memory to point at "the actual transcript, with a date, that produced it." A merged memory has N sources and a paraphrase nobody said. If you consolidate at all, the merged row needs `source_transcript_ids[]` as a set union — and the repo's `Memory` dataclass has a single `source` string (`14:511`), so it structurally cannot do that.

**Q: Does deletion actually delete?**

Answered: technique 30 is the only one that tries, and it's thorough about breadth: `delete_user` (`30:1174`) hits hot, warm, cold, and graph tiers and writes four audit entries. The graph store rebuilds its adjacency index from scratch after filtering (`30:604-612`) — a deliberate correctness choice over an incremental delete.

But: **deletion is by `user_id` only.** There is no per-memory delete anywhere in `30`, and no suppression concept in the entire repo.

*For Kivi:* §9 says the hard part explicitly — *"deleting the row is useless, because the same pattern will regrow from the same transcripts within a week."* The repo has no answer here at all, not even a wrong one. Every store is append-and-derive; nothing records "do not re-derive this." That's a question this repo never faced (see §5).

### 1.4 Conflict and contradiction

**Q: How is a contradiction detected?**

Answered: two-stage, similarity-gated. `_find_match` (`10:315`) finds the single best-matching stored fact by cosine; if `sim >= 0.85` it's a duplicate; if `0.50 <= sim < 0.85` it asks an LLM "do these contradict? YES/NO" (`10:337-340`, prompt at `10:225`). Below 0.50 it's new and no check runs. **Thresholds configurable** (`10:235-236`), the two-stage structure hardcoded.

The gating is the real decision and it's invisible: a contradiction between two facts whose embeddings sit below 0.50 similarity is structurally undetectable. "Meera works at Acme" vs. "Meera left the design studio in March" may well not clear 0.50.

Also `_find_match` compares against **only the single best match** (`10:323-332`), so a new fact that contradicts two stored facts resolves against one of them.

Their own prose concedes the harder case (`10`, md cell 35): *"'I work remotely' and 'I go to the office on Tuesdays' aren't strict contradictions, but the system may struggle."*

**Q: Who wins?**

Answered: recency, by default, in both places. `ConflictResolver(strategy="recency")` is the constructor default (`14:409`, and again at the pipeline level `14:468`ish), and `_recency_wins` is `max(memories, key=lambda m: m.created_at)` (`14:252`ish). In technique 10 it's implicit and absolute: the new fact archives the old, always (`10:409`), and gets `confidence=0.9` for being new (`10:413`, with the comment "recent statements get high confidence").

**This is the one genuinely pluggable decision in the repo.** `ConflictResolver` takes a strategy string and offers three (`14:409-418`): `recency`, `source_priority`, `llm`. That placement says they knew this was contested. And `_source_priority` encodes a hierarchy worth looking at directly: `{"user": 3, "inferred": 2, "tool": 1}` (`14:256`ish), mirrored in `rescore_importance`'s `source_weights = {"user": 1.0, "inferred": 0.6, "tool": 0.4}` (`14:431`).

That dict is the closest thing in the repo to the Kivi tier model — and it's used as a *tiebreaker weight*, not as a permission gate.

*For Kivi:* recency-wins is defensible for episodes ("the review moved to Thursday" then "moved to Tuesday"). It is not obviously right across tiers. A new *observation* that contradicts an old *stated* preference should not win on recency — §4 says a pattern never overrides a rule the user set. The repo's `(priority, created_at)` lexicographic sort (`14:256`ish) is the shape you want: tier first, recency as tiebreak. Note that `_llm_adjudicate` falls back to `_recency_wins` on any parse failure (`14:290`ish) — a quiet default that means the configured strategy silently becomes recency under error.

### 1.5 What's retrieved and how it's ordered

**Q: Similarity alone, or blended with something?**

Three different answers, none reconciled:

- Pure cosine, sorted descending, top-k (`10:435-445`).
- `similarity * strength` — multiplicative (`19:313`).
- `(1 - w) * semantic + w * recency` with `w = 0.3` — additive (`18:383-386`, `18:310`).

The additive form is **configurable per-query** (`18:412`), which is the most confident-looking parameterisation in the repo — and `18` uses it to demo `weight=0.0` for pure-semantic (`18:834`, `18:837`).

The multiplicative form at `19:313` has a property the additive one doesn't: a fully-decayed memory scores ~0 regardless of relevance, so decay acts as a soft filter. Additive blending can't suppress — a perfectly-matching decayed memory still surfaces at `0.7 × 1.0 = 0.7`.

*For Kivi:* §9 says an observation that isn't re-observed "loses standing and **stops being surfaced**." That's multiplicative or an explicit floor, not a 0.3-weighted addend. Also note both blends are computed over the *whole* store with no pre-filter — fine at demo scale, and `10`'s own prose flags it (`10`, md cell 35: "O(n)… you'll need ANN").

**Q: Is retrieval separable from disclosure?**

Answered: no. Nowhere in the repo. `retrieve` returns rows and `chat` formats every returned row straight into the system prompt (`10:450-462`, `07:364-381`). There is no notion of a retrieved-but-withheld memory, and therefore no trace of one.

`07:376-381` goes further and dumps **every known entity name** into the prompt on every turn ("All known entities: …"), unconditionally, regardless of relevance.

*For Kivi:* this is the §1/§6 calibration principle, and the repo has no precedent for it — retrieval and disclosure are the same act in every notebook. What the repo *does* offer is the observability substrate: `17`'s `routing_log` (`17:274`, appended at `17:307`) records every classification decision with its inputs. That's the shape of the Why panel's retrieval trace, applied to the wrong stage. The withheld-memory trace ("3 retrieved, 1 withheld — requires Koottu") needs the same log at the disclosure gate.

**Q: Is diversity or redundancy managed at read time?**

Answered: only in technique 20, and only as a menu. MMR (`20:441`, `20:459`, `lambda_param=0.7`), RRF over BM25 + semantic (`20:329`, `k=60`), cross-encoder rerank (`20:377`). None of these appear in any other notebook — `10` and `18` and `19` all do plain sorted-cosine.

*For Kivi:* MMR is relevant to a specific problem the repo never states — if fourteen client emails all support "never uses bullet lists," a top-k semantic retrieval over the evidence returns fourteen near-identical rows. The Kivi model handles this by storing one observation with `evidence_count: 14` rather than fourteen memories, which is the better answer, but MMR at `20:441` is the fallback if evidence stays row-per-instance.

### 1.6 What happens on failure or low confidence

**Q: What does the system do when it doesn't know?**

Answered: nothing. There is no abstention path in the repo. `chat` (`10:448`) builds a prompt with whatever `retrieve` returned — if `relevant` is empty it just omits the facts block (`10:454`) and lets the model answer unaided. Nothing tells the model it has no memory; nothing distinguishes "no memory" from "memory says nothing relevant."

**Q: What happens when a component fails?**

Three different answers, all quiet:

- `07:432-433` — extraction failure is caught, printed as `[extraction warning: …]`, and the turn proceeds. Memory silently doesn't update.
- `14:290`ish — LLM adjudication parse failure falls back to recency, unlogged.
- `10:288`, `17:303` — no error handling at all. A malformed LLM response raises, or in `10`'s case, gets silently line-split into garbage facts (`10:292`: `raw.splitlines()`, `lstrip("- ")`). If the model returns a preamble ("Here are the facts:"), that preamble is stored as a fact.

`_check_contradiction` (`10:345`) is the sharpest: `max_tokens=5`, and the answer is accepted as YES only if it `.startswith("YES")` (`10:357`). Anything else — including a truncated or hedged response — is silently NO, i.e. **the failure mode of contradiction detection is "no contradiction," which means the old fact survives and the new one is stored alongside it.** Two contradictory facts, both active, both retrievable, no flag. That's an accident, not a design, and it's the kind of thing a test would have caught.

*For Kivi:* §8 makes abstention a designed surface with a trace. The repo offers zero precedent — not a partial one, none. And its silent-failure defaults are all biased toward *keeping and asserting*, which is the opposite of the bias the position requires.

### 1.7 What changes over time

**Q: Decay by wall-clock age, or by idle time since last use?**

Answered: idle time. `idle_hours` measures from `last_accessed` (`19:186-189`), and `apply_decay` **resets `last_accessed = now` after decaying** (`19:236`). So decay is applied incrementally over the interval since the last decay pass, not since last genuine use — `last_accessed` is doing double duty as "last decay checkpoint."

The consequence: `decay_all` is called at the top of every `search` (`19:308`), so decay is driven by *query frequency*, not elapsed time. A store queried a hundred times an hour decays identically to one queried once — because the exponent is the interval, and `exp(-λt)` composes. That part is correct. But `last_accessed` is now meaningless as an access timestamp, and `30`'s `get_low_access_records` (`30:427`) — a different notebook — sorts on exactly that field for a different purpose.

**Configurable** (`half_life_hours`, `19:218`), and the interaction is admitted (`19`, md cell 32): "the half-life, boost, and threshold parameters interact in non-obvious ways… Expect iterative tuning per use case."

**Q: Does retrieval reinforce?**

Answered: yes, and unconditionally. Every memory in the top-k gets `+0.3` strength on every search (`19:320`, `19:239`), capped at 1.0. The system boosts what it retrieved, whether or not the retrieval was any good, whether or not the user did anything with it.

*For Kivi:* this is a feedback loop worth naming. Retrieved → boosted → more likely retrieved. §9 decay is about "not re-observed," which is a *write-path* signal (did this pattern recur in new transcripts?), not a read-path one. The repo conflates them. Their own prose flags the failure (`19`, md cell 32): "A memory accessed once per year… would decay and get pruned long before its next use. **Access frequency does not always correlate with importance.**"

**Q: Are some memories exempt from decay?**

Answered: no, and admitted. `19`, md cell 32: "A user's allergy, a legal requirement, or a safety protocol should not decay. **You need an exemption mechanism (pinned memories) on top of the decay system.**" Named as missing; not built.

*For Kivi:* §9 lists **pinnable** as a first-class user action. The repo tells you this is needed and doesn't show you how. Note the interaction they don't mention: a pinned memory that's exempt from decay is also exempt from the storage-pressure prune (`19:364`), so pinning is an unbounded commitment unless capped.

**Q: Does storage pressure change the forgetting policy?**

Answered: yes — `apply_storage_pressure` (`19:364`) mutates `self.prune_threshold` from 0.1 up to 0.5 as utilisation goes 80%→100%. **This is a stateful mutation that never resets.** Once pressure has pushed the threshold to 0.5, it stays at 0.5 even after pruning drops utilisation back to 40% — nothing lowers it. Whether that's deliberate hysteresis or an oversight is genuinely unclear; there's no comment and no test.

*For Kivi:* the pattern (forgetting policy tightens under pressure) is worth knowing. The unclamped mutation is a bug to not copy.

### 1.8 Idempotency and ordering

**Q: Is re-processing the same transcript idempotent?**

Answered: **no, and this is the least-examined assumption in the repo.** Run `process_conversation` on the same messages twice and you get: extraction runs again (non-deterministic despite `temperature=0.0` at `10:286`), each re-extracted fact matches the stored one at high cosine, hits the duplicate branch, and **`mention_count` increments and `confidence` rises by 0.05** (`10:402-403`). Reprocessing inflates confidence.

IDs make this concrete. `Fact.fact_id` is `uuid4()` (`10:169`) — random, so the same fact extracted twice is two different identities. `MemoryRecord.id` hashes content **plus `time.time()`** (`30:1003`) — deliberately non-deterministic. Only `TemporalMemory` (`18:213`) and `20`'s `Memory` (`20:161`) use content hashes, and `20`'s is content-only, which makes it stable but collides on identical text at different times.

*For Kivi:* Appendix C.6 is *"A correction demoted a memory and the memory did not regrow on reprocessing."* That claim requires deterministic, content-derived identity **and** a suppression check on the write path. The repo gives you two out of four notebooks with stable IDs, no suppression anywhere, and a duplicate path that actively rewards reprocessing. Pushes hard toward: derive memory identity from `(normalised content, type)`, keep `source_transcript_ids` as a set so re-processing is a no-op union rather than an increment, and make `evidence_count` a function of distinct source transcripts rather than a counter you `+= 1`.

**Q: Does write order matter?**

Answered: yes, unavoidably, and it's never mentioned. `_find_match` (`10:315`) compares against the store *as it is now*. Facts A and B that mutually contradict resolve differently depending on arrival order. `14`'s clustering is order-independent (union-find, `14:298-317`) but its conflict resolution is not — `_process_single_cluster` (`14:495`) merges duplicates *before* detecting contradictions, so a merged text is what gets contradiction-checked, and the merge is LLM-authored.

**Q: Is there any concurrency story?**

No. Every store is a Python list or dict mutated in place (`10:238`, `19:279`, `30:219`). No locks, no transactions, no optimistic versioning. `30` simulates Postgres in a docstring (`30:334-340`) but the code is `dict`.

*For Kivi:* unclear how much this bites — a single-user dictation client may serialise naturally. But extraction may run async (Appendix B leaves timing open), and two transcripts extracting concurrently against a shared entity store is exactly the read-modify-write in `07:120-141`.

---

## 2. MAGIC NUMBERS

**Provenance, up front:** every one of these was traced through `git log`. **Not one has ever been changed.** All were introduced in `4a0d986` ("Initial release", 2026-05-05) and no notebook code cell has been touched since (verified: `git log --name-only 4a0d986..HEAD` lists only READMEs, docs, CI, and images — the sole `all_techniques/` entry is `26_letta_memgpt_patterns/README.md`). So **none of these is tuned in the traceable sense**. The most that can be said is that some have a stated rationale and some don't. Split on that basis:

### Derived or reasoned (have a comment explaining the value)

| Value | Where | Stated basis | If ×10 / ÷10 |
|---|---|---|---|
| `half_life_hours = 168.0` | `19:218`, `19:274`, `18:247` | "Default 168 = 7 days" (`18:252`) — a calendar week, not an observation | ÷10 (17h): a memory unqueried for a day scores 0.36 and is near the 0.1 prune line in three days. ×10 (70 days): decay stops doing anything within a session-scale horizon; prune never fires. |
| `decay_rate = ln(2)/half_life` | `19:220`, `18:257` | "gives exactly 50% strength at one half-life" — correct derivation, not a guess | n/a — derived |
| linear decay hits zero at 2× half-life | `18:272` | Commented as the definition | Arbitrary; a linear decay has no principled zero point |
| `k = 60` (RRF) | `20:331` | Undocumented here but it is the constant from the original RRF paper (Cormack et al. 2009) — inherited, not chosen | ÷10 (k=6): rank-1 dominates, fusion ≈ whichever list ranked it first. ×10 (k=600): all ranks flatten, fusion ≈ "appeared in many lists" |
| ~4 chars per token | `30:187-189` | "Rough token estimate" — the standard English heuristic | Breaks on code, names, non-Latin scripts; under-counts, so budgets over-admit |
| Pricing table | `30:819-824` | "Approximate… update rates as models change" | Correctly flagged as perishable |

### Guessed (no comment, no test, no alternative shown)

| Value | Where | What it gates | If ×10 / ÷10 |
|---|---|---|---|
| `similarity_threshold = 0.85` | `10:235` | duplicate vs. not | ÷10 (0.085): everything is a duplicate; the store never grows past ~1 fact. ×10: >1, impossible — **the parameter has less than one order of magnitude of headroom upward**, which is itself the finding. Realistically 0.85→0.95 means near-identical restatements become separate facts and `evidence_count` never accumulates. |
| `contradiction_threshold = 0.50` | `10:236` | whether the LLM contradiction check runs at all | ÷10 (0.05): the check runs against nearly every stored fact — cost explodes, false-positive contradictions archive good facts. ×10: >1, check never runs, contradictions accumulate silently. |
| `confidence = 0.8` initial | `10:168` | starting belief | Pure convention. Nothing reads it as a gate; it only ever appears in the prompt string (`10:456`) |
| `+0.05` per mention | `10:403` | auto-promotion rate | 4 mentions → 1.00. ÷10: 40 mentions. ×10: saturates immediately. **Inlined, not parameterised — the tell that it was never questioned.** |
| `0.9` post-contradiction | `10:413` | "recent statements get high confidence" | Encodes recency-wins as a number |
| `top_k = 5` | `10:435`, `10:450`, `18:410`, `20:459` | how many facts reach the prompt | The most-repeated constant in the repo — 5 or 3 nearly everywhere. ÷10 → 0/1, ×10 → 50 facts in a system prompt, which is where "use these naturally" (`10:461`) stops working |
| `similarity_threshold = 0.80` / `duplicate_threshold = 0.92` | `14:290`, `14:346` | cluster / merge | 0.92 is stricter than `10`'s 0.85 for the same job. **Two notebooks, same operation, different numbers, no reconciliation.** |
| `prune_below = 0.15`, `size_trigger = 10`, `decay_rate = 0.01` | `14:468`ish, `14:428` | consolidation policy | `0.01/hour` is a ~69h half-life — a third notebook, a third decay rate, unrelated to the other two |
| `0.4/0.3/0.3` importance weights | `14:446` | recency vs frequency vs source | Sums to 1. No sensitivity analysis anywhere |
| `0.6/0.3/0.1` eviction weights | `30:769` | importance vs recency vs access | Sums to 1. Different split, same notebook family, no explanation |
| `prune_threshold = 0.1`, `reinforce_boost = 0.3` | `19:275`, `19:277` | forgetting | Given ranges in the tuning table (`19`, md cell 32: 0.05–0.3, 0.1–0.5) — the only place in the repo where a range is offered instead of a point value |
| `0.8` pressure trigger, `0.1→0.5` ramp | `19:367-369` | storage-pressure escalation | Never resets (§1.7) |
| `lambda_param = 0.7` (MMR) | `20:459`ish | relevance vs diversity | Standard-ish default; 0.5 is equally common |
| `similarity_threshold = 0.3` (timeline) | `18:569` | topic membership | Very loose. Nothing justifies it against the 0.5 used for contradiction gating in `10` |
| `access_count >= 3` → promote to hot | `30:1076` | tiering | Bare literal inside `retrieve`, not a constructor arg |
| `importance < 0.3` → demote to cold | `30:1143` | tiering | Same |
| `threshold_days = 30` | `30:427`, `30:1141` | staleness | Calendar-derived |
| `max_per_user = 50`, `default_ttl = 3600` | `30:218` | cache | 1h TTL is a convention |
| budget: 500 memories / 100k tokens | `30:745-746` | per-user cap | Round numbers |
| `daily_limit = 10.0`, `monthly = 200.0` USD | `30:828-829` | cost | Round numbers; note 10×30 ≠ 200, so the two limits are inconsistent by design or accident — unclear which |
| `temperature = 0.0` | `10:286`, `14:363`, `17:296`, elsewhere | extraction determinism | Deliberate and consistent for extraction. `temperature=0.7` appears only in chat-generation cells (`20:503`, `22:499`, `26:592`) — a real and consistently-applied distinction |
| `max_tokens = 5` | `10:354` | contradiction answer | Under-provisioned; see §1.6 |
| `max_tokens = 8` | `14:406` | adjudication answer | Same shape |
| `MAX_LINES = 60` | `utils/validate_cells.py:19` | notebook style | Enforced in CI — the only threshold in the repo with a test |

**The overall read:** ~45 tunable values, one of which (`MAX_LINES`) is enforced by a test. The three decay rates (168h, 24h demo, 0.01/h) and the three similarity thresholds for near-identical operations (0.80, 0.85, 0.92) are not variants of one considered decision — they're three authors' independent guesses in three files that never meet. **Treat every number above as a starting point with no evidence behind it.** Kivi's Appendix B already says decay windows and evidence thresholds "need corpus data before they can be set honestly." This repo is confirmation that nobody else has that data either.

---

## 3. WHAT THE HISTORY SAYS

**The headline, stated plainly: there are no reversals. Not one.**

Reversals are the highest-value signal, so here is exactly why there are none. The repo has 30 commits. Commit `4a0d986` (2026-05-05) is "Initial release: 30 agent memory techniques as runnable Jupyter notebooks" — every notebook, every dataclass, every threshold, in a single drop. The 29 commits since are:

- **README / marketing / monetisation: 18 commits.** Affiliate CTAs (`a0f5376`, `cae00f2`, `819f62f` "Set affiliate CTA rate to 25%"), coupon codes (`cd1e882`, `4b1b504`, `a3ccba8`), book links (`c6e32ba`, `63ecdc1`), banner placement (`6ea4085`, `1c0e8f3`), course CTAs (`bae45b6`, `b7f7240`).
- **Repo hygiene: 6.** Moving files to `.github/` (`4532e01`), Dependabot (`6a4e5b3`), CITATION fields (`b59fec2`, `622cf8e`).
- **Actual content fixes: 2.** `622cf8e` fixes a BibTeX brace *and* a stale reference to `memory_utils.py` (the file is `utils/helpers.py`) — the docs cited a filename that never existed post-release. `8d19b01` removes the `letta` package from technique 26's prerequisites.

`git log --name-only 4a0d986..HEAD` touches exactly one file under `all_techniques/`: `26_letta_memgpt_patterns/README.md`. **No `.ipynb` has been modified since the day it was written.**

What this means, bluntly: this repo carries **no operational evidence whatsoever**. Every decision in §1 is a first draft that was never revised, because nothing ever ran against a real workload and pushed back. When §1 says "the repo answered X," read it as "the repo demonstrated X once, in a notebook, against a scripted 3-session conversation with a fictional data scientist named Maya." Treat all of §1 as precedent — a catalogue of what people build — and none of it as evidence.

**Decisions that generated recurring bug reports:** none discoverable. The three merged external PRs (`#1`, `#8`, `#9` via `4f3bc2f`, `be27a73`, `b4b2770`) fix a BibTeX brace, missing CITATION.cff fields, and a docs prerequisite. Nobody has reported a memory-behaviour bug, which is unsurprising given nothing depends on the behaviour. *Caveat:* this is from merge commits only — no network access to the issue tracker, so there may be open issues not visible here.

**Abstractions added later:** none. Nothing in the codebase postdates the initial commit, so there is no "the original answer stopped working" signal available. The absence is itself informative: you cannot use this repo to learn which of its answers fail first.

**TODOs, FIXMEs, and admitted shortcuts.** No literal `TODO` or `FIXME` in any code cell. Instead the admissions are structured — the repo has a house style of a `## Tradeoffs` / `## Discussion & Tradeoffs` markdown section per notebook, and these are where the authors say what they know is wrong. The load-bearing ones:

- *"Facts are only added, never expired. Contradictions… need explicit conflict resolution."* (`07`, md cell 38) — technique 7 knows it has no conflict story.
- *"Without a mechanism for temporal decay… outdated facts linger. The user may have switched jobs six months ago, but the old job title persists."* (`10`, md cell 35) — technique 10 knows its confidence only goes up.
- *"You need an exemption mechanism (pinned memories) on top of the decay system."* (`19`, md cell 32) — named, not built.
- *"Access frequency does not always correlate with importance."* (`19`, md cell 32) — the reinforcement loop's core flaw, stated by its author.
- *"Even if text is redacted, embeddings may encode PII."* (`30`, md cell 56).
- *"What This Notebook Does Not Cover"* (`30`, md cell 56) — an explicit list: sharding, distributed caching, observability, backup/recovery, and **A/B testing memory systems**.

And the in-code equivalents, which are unusually honest: five docstrings say "In production, replace with" and then give the real thing — Redis (`30:212-215`), pgvector SQL (`30:334-340`), S3/Glacier (`30:472-475`), Neo4j Cypher (`30:563-571`), the real embeddings call (`30:952-956`). Plus `_generate_embedding` is a **seeded hash-based fake** (`30:958-961`) — deterministic random vectors, so every similarity number printed in that notebook's demo output is meaningless. That's disclosed in the docstring, and it's the right call for a reproducible teaching notebook, but it means technique 30's retrieval demo demonstrates plumbing and not retrieval.

One more, in `10` itself: `_find_match` and `_check_contradiction` are defined as bare functions and then bolted on with `SemanticMemory._find_match = _find_match` (`10:361-362`, again at `10:482-485`, and throughout `19`, `18`, `30`). This is not a design decision — it's a workaround for `validate_cells.py`'s 60-line cap (`utils/validate_cells.py:19`). A style rule is deforming the code's structure. Worth recognising as accident rather than intent when reading these files.

---

## 4. UNEXAMINED DEFAULTS

Choices with no comment, no test, no config, no alternative anywhere in the repo:

**Facts are English sentences.** Every store holds `content: str` (`10:167`, `19:177`, `30:158`) and every comparison is embedding cosine over that string. Nothing is structured. `"User lives in Berlin"` is a sentence, not `(user, lives_in, Berlin)`. The consequence: you cannot query "where does the user live" except by similarity, you cannot detect that a new value for a single-valued attribute arrived, and contradiction detection has to be an LLM call because there's no field to compare.
*The alternative nobody tried:* typed slots with cardinality — a `lives_in` attribute that holds one value, where a second value *is* a contradiction by construction, no LLM required. Technique 8 (knowledge graph) and technique 30's `GraphEdge` (`30:536`) have the triple shape but never use it for conflict detection.

**Third person, under 20 words, "User…" prefix.** `10:214-215` mandates the form. No test checks it, nothing depends on it, and it silently makes every fact about the user — there is no grammatical slot for a fact about Priya. Given Kivi §5, that accidental constraint is closer to what you want than anything deliberate in the repo, but it's accidental.

**Extraction is the same LLM that chats.** `CHAT_MODEL = "gpt-4o-mini"` used for both response and extraction and contradiction-checking (`10:128`, used at `10:281`, `10:348`). `07` has *separate parameters* for `chat_model` and `extraction_model` (`07:338-339`) and then **defaults them to the same model**. The parameter exists; the alternative was never exercised. Their own prose elsewhere recommends the split (`30`, md cell 56: "Use smaller models for extraction… 10-20x lower cost").

**`datetime.utcnow()`, naive, everywhere.** `19:181`, `30:160`, `18:348`, `14:430` (via `time.time()`). Technique 10 is the lone exception, using `datetime.now(timezone.utc)` (`10:170`). So the repo has both a timezone-aware and a naive convention, and `19`'s own prose flags clock sensitivity as a failure mode (`19`, md cell 32) without noticing that its own timestamps are naive.
*The alternative nobody tried:* logical clocks or per-transcript event time as the ordering key, which matters when extraction runs async and "created_at" is the extraction time, not the utterance time. Technique 18 has the right field for this (`event_time`, `18:201`) and no other notebook adopts it.

**Storage is a Python list.** `self.facts: list[Fact]` (`10:238`), `self.memories: list[DecayableMemory]` (`19:279`). Every retrieval is a full scan. `10`'s prose names the alternative (ANN) without adopting it.
*The alternative nobody tried at all:* a relational store where tier, type, and suppression are columns you can filter on before scoring. Every notebook assumes retrieval means "score everything, sort, cut," which is why nothing in the repo can express "the dictation path structurally cannot see observations" (Kivi §7) — there's no query surface to constrain.

**Persistence is `json.dump(asdict(...))`.** `10:678-684`, `07:181`. No schema version field on any record. No migration path. `load_memory` does `Fact(**item)` (`10:693`), which throws on any added or removed field. For a system whose entire premise is that beliefs persist across months, an unversioned schema is a notable omission — and one you'll hit the first time you add a field to a live store.

**`user_id` is a string with no tenancy enforcement.** `30`'s stores key by it (`30:220`, `30:345`) and `search` filters by it (`30:375`), but nothing validates it and there's no test that a query for user A can't return user B's rows.
*The alternative nobody tried:* making isolation a property of the store (separate namespaces) rather than a filter predicate applied correctly by every call site.

**Everything is synchronous and single-process.** No queue, no worker, no async. Extraction blocks the response (`07:425`). Given `07`'s own recommendation to extract asynchronously, this is inherited-from-notebook-format rather than chosen.

---

## 5. QUESTIONS THIS REPO NEVER FACED

Derived from the Kivi position. These have no answer here — not a wrong one, none — so this is design from scratch:

1. **How do you make retrieval and disclosure separable?** (§1, §6.) Every notebook fuses them. The question underneath: does the disclosure gate run *after* scoring (filter the ranked list) or *inside* it (tier as a scoring input)? Filtering post-hoc is what makes "3 retrieved, 1 withheld" expressible; folding tier into the score makes the withheld item invisible. The repo's blended-score habit (`18:383`, `19:313`) would push toward the second, which destroys the trace §8 needs.

2. **How do you structurally prevent a store from being queryable on one path?** (§7.) The dictation path must be *unable* to load observations, not merely filtered. The repo has one store per notebook and, in technique 17, three stores keyed by content type (`17:233-237`) — but the router can address all three. Nothing models a caller with reduced reach. Open sub-question: is the boundary a separate store, a separate connection with column-level grants, or a capability object the dictation path holds?

3. **What is a suppression, and where does the extractor consult it?** (§9.) "That's not me anymore" must block re-derivation. No repo primitive. Sub-questions the repo can't help with: does a suppression match on content, on embedding neighbourhood, or on the (type, subject, predicate) shape? A content-exact suppression regrows the moment the LLM paraphrases; an embedding-radius suppression silently swallows adjacent true facts. This is the hardest unsolved mechanism and nothing here informs it.

4. **How does third-party content pass through the context window without touching the write path?** (§5.) The repo's write path reads the whole context, and technique 7 even extracts from the assistant's own output (`07:425`). The question: is this a taint-tracking problem (mark spans by origin and forbid tainted spans from producing candidates), or a two-call problem (generate with everything, extract from the user's dictation only)? The second is cheap and mostly right; the first is what actually satisfies Appendix C.2 when a fact is *derived* from third-party content rather than copied from it ("the review moved to Tuesday" comes from Priya's message).

5. **What is the storage grammar for a question?** (§4: "Not `user_disagrees_with_pricing: true`. Instead: `'Does the user disagree…?' — unconfirmed`.") Every store in the repo holds assertions. Nothing has a slot whose type is interrogative. Sub-question: does a hypothesis share a table with facts (with `tier='hypothesised'`) or live separately? Sharing invites the accident you're guarding against — a `WHERE` clause forgotten once and a question is retrieved as a fact. Separating costs you a join in the Why panel.

6. **How is a confirmation budget spent?** (§8: "a small cap per week… spent on the highest-value uncertain memories.") The repo has cost budgets in dollars and tokens (`30:743-749`, `30:826-834`) but nothing budgets *user attention*. The question: what makes an uncertain memory "high-value"? Repo instinct would be `evidence_count` or importance score — but by §4, evidence count must not drive promotion, so it probably shouldn't drive the ask either.

7. **What happens to an unconfirmed hypothesis at expiry?** (§9: "Hypotheses expire by default.") Deleted, archived, or suppressed? The repo's two disposal patterns are soft-archive (`10:409`) and hard-drop (`14:527`). But an *expired* hypothesis is a third thing: it should probably not be silently re-derivable next week from the same transcripts, or expiry is decorative — which makes expiry a sibling of suppression (#3), not of archival.

8. **How do you present "read, not kept" — and what's the record that proves it?** (§5, Appendix C.2.) `PIIHandler.audit_log` (`30:676`) is the nearest structure and it logs *deletions by user*, not per-transcript drops with reasons. You need a drop record attached to a transcript, containing a reason category, that is durable and shows in the UI. Sub-question the repo raises by omission: how long do you keep the drop log? A durable record saying "we dropped 2 candidates about Priya's mother" is itself a record about Priya's mother, unless the reason is stored as a category with no content.

9. **Is the Daari escalation stateless?** (§6: per-request, "the answer is not written to memory.") The repo has no concept of a response that doesn't write. Every path that generates also extracts (`07:400-435`). The question: is "don't write" a flag on the request, or a separate code path? A flag is the thing that gets dropped in a refactor.

10. **Do the two axes cross-product cleanly, or are some cells forbidden?** (§4.) Is there such a thing as a hypothesised *entity*? An observed *episode*? The prose works the preference row hard and leaves the others implicit. The repo's type systems are single-axis (`17:125-129`, `07:240-241`) so they offer no precedent for a matrix with holes in it — and whether the holes are enforced in the schema or just never populated is a decision with real consequences for the memory surface's three-group layout.

11. **What is one memory when evidence is distributed?** (Appendix C.3.) Fourteen client emails supporting one observation: one row with `evidence_count: 14` and 14 transcript ids, or 14 rows the retriever clusters? The repo consolidates *after the fact* by embedding-clustering (`14:293`) and destroys the originals in the merge (`14:507`). The provenance requirement forbids that shape. But the alternative — incrementing a count on an existing row — reintroduces the write-time matching problem from `10:315` with all its threshold guesswork, and you'd be matching *patterns*, not restatements, so a 0.85 cosine gate is unlikely to be the right instrument.

---

## 6. WHAT THE TESTS DON'T COVER

The whole suite is 78 lines across three files, plus two validators. Here is what it actually verifies:

- `cosine_similarity` returns 1.0 / 0.0 / −1.0 for orthogonal and antiparallel unit vectors, and raises on length mismatch and zero vectors (`tests/test_helpers.py:6-22`).
- `format_messages` uppercases roles (`tests/test_helpers.py:25`).
- `load_env` raises when a required var is absent and returns it when present (`tests/test_helpers.py:35-50`).
- Every notebook code cell **parses as Python**, after stripping `%` and `!` lines (`tests/test_imports.py:9-25`).
- There are at least 30 notebooks (`tests/test_imports.py:28`).
- No code cell exceeds 60 lines and every code cell has a non-empty markdown cell before it (`utils/validate_cells.py:19`, `:37-46`).
- No banned words or em dashes in prose (`utils/validate_style.py:23-38`).

**Not one test imports, instantiates, or calls anything from a notebook.** `test_imports.py` reads the `.ipynb` as JSON and runs `ast.parse` — it never executes. So the entire behavioural surface is untested, and every decision in §1 could be inverted with the suite still green. Concretely, all of the following would pass CI unchanged:

- `similarity_threshold` 0.85 → 0.5, or 0.99. Duplicates all merge or never merge.
- `+0.05` confidence boost → `+0.5`, or `-0.05`. Auto-promotion in two mentions, or auto-decay.
- Conflict strategy `recency` → `source_priority`. The winner of every contradiction changes.
- `14`'s hard-drop of conflict losers (`14:527`) → soft archive. Or `10`'s archive (`10:409`) → `del`. Auditability appears or vanishes.
- Decay from idle-time to wall-clock age. Reinforcement removed entirely.
- `retrieve` returning archived facts — delete the `if fact.archived: continue` guard at `10:440` and superseded facts flow straight into the prompt. **Nothing catches this.**
- PII redaction disabled by flipping the `redact_pii` default (`30:988`). SSNs stored verbatim, suite green.
- `delete_user` skipping the cold tier or the graph store. Data survives a GDPR deletion, suite green.
- `WarmTierStore.search` dropping its `user_id` filter (`30:375`) — cross-tenant leakage, suite green.
- `_check_contradiction`'s `max_tokens=5` → `1`. Every answer truncates, every contradiction becomes "no," contradictory facts accumulate. Suite green.
- Any change to top-k, blend weights, prune thresholds, tier promotion rules, or cluster thresholds.

**What this means for how to use the repo.** Every point in §1 is **precedent, not evidence** — someone wrote it down once and nothing has ever confirmed it works. There is no exception to this; there is no subset of the repo that is actually verified. The two claims to treat with the most caution, because they *look* authoritative and aren't:

- **Technique 30's retrieval demo.** Embeddings are seeded hashes of the content (`30:958-961`), so its similarity rankings are noise. The tiering plumbing is real; the retrieval quality it appears to show is not.
- **Technique 10's three-session walkthrough** (`10:515-598`), the Berlin→Amsterdam contradiction demo that motivates the whole archive mechanism. Its output is a saved notebook cell from one run against one LLM on one day. Nothing pins it. Re-run it and the extraction may differ; there is no assertion that the contradiction is caught.

For Kivi's Appendix C, which asks for seven claims *provable from evaluation output*: this repo demonstrates the opposite discipline. Technique 28 (`memory_evaluation`) and 29 (LoCoMo) exist and were only sampled for constants — if you want a harness pattern, they're the place to look next, and they are the two notebooks whose own subject matter is the gap described here.

---

## Structural caution

The repo's own organising principle is that these are 30 *independent* techniques, each a clean single-idea illustration. That's why technique 10 has contradiction handling but no decay, technique 19 has decay but no contradictions, technique 18 has bi-temporality but no supersession, and technique 30 has tiering but fake embeddings. Kivi needs most of these at once.

The interactions between them — decay interacting with evidence counts, supersession interacting with as-of queries, tier gates interacting with blended scoring, suppression interacting with consolidation — are precisely what no notebook contains, because containing them would violate the repo's pedagogy. The decision space mapped above is real; the composition problem is entirely yours.
