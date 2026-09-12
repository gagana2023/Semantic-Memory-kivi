# Decision space: `always-on-memory-agent`

Read against `kivi-semantic-memory-position.md`. This maps the questions the repo answered, not the answers it is proud of.

---

## 0. Orientation

**What I read, in full:** `agent.py` (677 lines), `dashboard.py` (323), `README.md` (230), `requirements.txt` (5).
**What I skipped:** `docs/*.png|jpeg` (image assets — `architecture.png` may encode design intent I did not extract), `LICENSE`.
**What does not exist:** no tests, no CI config, no `.env.example`, no migrations directory, no issues/PRs accessible from a shallow checkout. The repo is 4 files plus assets.

**History caveat:** this was obtained via a sparse, `--depth 1` checkout of `GoogleCloudPlatform/generative-ai`. `git log` for this path shows one unrelated commit (`d8d4719`, a Deep Research fix). **Section 3 is therefore mostly empty, and that is a limitation of my checkout, not evidence about the project.** The README (`README.md:117`) points at a different origin — `github.com/Shubhamsaboo/always-on-memory-agent` — which is where any real history lives.

### Core logic vs. glue

- **Real logic:** the tool functions, `agent.py:114–312` — `store_memory`, `read_all_memories`, `read_unconsolidated_memories`, `store_consolidation`, `read_consolidation_history`, `get_memory_stats`, `delete_memory`, `clear_all_memories`. This is the entire memory model. Everything semantic (what a memory *is*, what consolidation *means*) lives in four prompt strings in `build_agents()` (`agent.py:318–392`).
- **Glue:** `MemoryAgent` (`agent.py:398–475`) is a thin ADK `Runner` wrapper. `build_http` (`agent.py:603–660`) is a 1:1 HTTP mapping onto the tools. `main`/`main_async` (`agent.py:666–730`) is process wiring.
- **Adapter/demo:** `dashboard.py` in its entirety — it holds no memory logic, only `requests` calls against `AGENT_URL` (`dashboard.py:22`) plus four hardcoded sample texts (`dashboard.py:33–72`).

**Structural observation:** the logic/prompt split is the single most important fact about this repo. The Python is a CRUD layer; the *policy* is natural language inside `instruction=` blocks. Nothing in the code can enforce anything the prompt asks for.

### Data model (`agent.py:88–112`)

Three tables, created idempotently on every connection (`CREATE TABLE IF NOT EXISTS` inside `get_db`, `agent.py:83–112`) — i.e. **no migration mechanism at all**. Schema change means manual DB surgery or `/clear`.

- `memories`: `id`, `source`, `raw_text`, `summary`, `entities` (JSON string), `topics` (JSON string), `connections` (JSON string), `importance REAL DEFAULT 0.5`, `created_at TEXT`, `consolidated INTEGER DEFAULT 0` (`agent.py:85–96`).
- `consolidations`: `id`, `source_ids` (JSON), `summary`, `insight`, `created_at` (`agent.py:97–103`).
- `processed_files`: `path TEXT PRIMARY KEY`, `processed_at` (`agent.py:104–107`).

Serialization: everything structured is `json.dumps`'d into a TEXT column (`agent.py:140`). No FTS table, no vector column, no index beyond the implicit PKs. Timestamps are ISO-8601 UTC strings (`agent.py:136`) and are sorted **lexically** as TEXT (`agent.py:156`) — correct for that format, but an unstated dependency.

### Main execution path (file → persistence)

`watch_folder` (`agent.py:535`) polls the directory every 5s → skips dotfiles (`agent.py:544`) and unsupported suffixes (`agent.py:547`) → dedupe check against `processed_files` (`agent.py:549`) → text branch reads and truncates to 10 000 chars (`agent.py:557`), media branch reads bytes and refuses >20 MB (`agent.py:510`) → `MemoryAgent.ingest` wraps it in `"Remember this information (source: …)"` (`agent.py:494`) → `Runner.run_async` on a **freshly created session** (`agent.py:463`) → orchestrator routes to `ingest_agent` → model calls `store_memory` → `INSERT` (`agent.py:137`) → **the file is marked processed regardless of whether ingestion threw** (`agent.py:565–571`; the `except` at `:564` only logs).

Query path: `GET /query?q=` (`agent.py:606`) → `agent.query` → `"Based on my memories, answer: {q}"` (`agent.py:525`) → `query_agent` calls `read_all_memories` (last 50) and `read_consolidation_history` (last 10) → the model does retrieval by reading everything.

### Config surface (complete)

| Setting | Where | Default | Mechanism |
|---|---|---|---|
| `MODEL` | `agent.py:38` | `gemini-3.1-flash-lite` | env var |
| `MEMORY_DB` | `agent.py:39` | `memory.db` | env var |
| `GOOGLE_API_KEY` | `README.md:125` | — | env var, consumed by the SDK, never referenced in code |
| `--watch` | `agent.py:705` | `./inbox` | CLI |
| `--port` | `agent.py:706` | `8888` | CLI |
| `--consolidate-every` | `agent.py:707` | `30` (minutes) | CLI |
| `AGENT_URL` | `dashboard.py:22` | `http://localhost:8888` | **hardcoded** |
| `INBOX_DIR` | `dashboard.py:23` | `./inbox` | **hardcoded**, duplicating `--watch` |

Everything else — every limit, every threshold, every prompt — is a literal in source. Note `poll_interval` is a *parameter* of `watch_folder` (`agent.py:535`) but is never passed from `main_async` (`agent.py:680`), so it is effectively hardcoded at 5.

### What the tests exercise

Nothing. There is no test file, no test dependency in `requirements.txt`, no assertion anywhere in the repo. Section 6 is therefore about the whole system.

---

## 1. Decision inventory

### 1.1 What enters the system

**Q: Is memory ingestion a push (caller submits) or a pull (system watches a source)?**
Answered: both, with the watcher primary — `watch_folder` polls a directory (`agent.py:535`) and `POST /ingest` exists (`agent.py:613`). **Hardcoded** as a pair; you cannot disable either. The watcher's unconditional place in `main_async`'s task list (`agent.py:679`) reads as conviction, not convenience — it is the product thesis.
*Assumes:* a filesystem is the integration surface; a single machine; ingestion latency of seconds is fine.
*For Kivi:* your input is a transcript stream plus application context (§7), not a folder. The push shape maps; the watcher does not. Pushes you toward an explicit `ingest(transcript, app_context)` boundary — which you need anyway, because §5 requires distinguishing user speech from third-party content at the entry point, and a folder-drop has no such distinction.

**Q: Does the system accept any modality, or only the modality it can reason about carefully?**
Answered: 27 extensions across text/image/audio/video/PDF (`agent.py:42–68`). **Hardcoded** in two module-level sets, plus a *third* duplicated list in `dashboard.py:25–31` that can drift. Media is inlined as bytes (`agent.py:475–479`).
*Assumes:* one extraction prompt generalises across modality (`agent.py:324–338`).
*For Kivi:* you declared text-only scope, so this is inapplicable — but its *shape* is a warning. One prompt covering five modalities is why the extraction contract here is so loose. Your §2 exclusion list cannot be enforced by a prompt simultaneously trying to describe a video.

**Q: Is raw input retained, or only the derived representation?**
Answered: both — `raw_text` and `summary` are separate columns (`agent.py:87–88`), and the ingest prompt tells the model to put its *own full description* into `raw_text` (`agent.py:334`), so for media the "raw" text is already model output. **Hardcoded.**
*Assumes:* storage is cheap and re-derivation may be wanted.
*For Kivi:* directly load-bearing and inverted. Your §5 says third-party content enters context but **not** the write path. A `raw_text` column holding the whole input is precisely the leak that rule exists to prevent. Pushes hard toward storing the derived memory plus a *transcript ID*, never the transcript body, in the memory row.

### 1.2 How it is represented

**Q: Is a memory a typed record or an untyped blob with tags?**
Answered: untyped. One flat row with `entities`/`topics` as free-text JSON arrays (`agent.py:89–90`). No `type` column, no `tier`, no entity as a first-class row.
*Placement:* hardcoded schema, no extension point. High confidence in *shapelessness* — the model decides what an entity is, per call.
*Assumes:* one homogeneous store; downstream consumers are LLMs, not queries.
*For Kivi:* your §4 puts `type` × `tier` at the centre. This repo is the counter-position. Every mechanic in your §6 (disclosure gating), §7 (dictation path structurally unable to load observations), and §9 (demotion) requires the typed columns this repo deliberately does without.

**Q: Is confidence/salience a scalar, a category, or absent?**
Answered: a scalar — `importance REAL DEFAULT 0.5` (`agent.py:93`), assigned by the model from a one-line instruction (`agent.py:330`). **Hardcoded** as a column; never used to filter, order, or gate anything in `agent.py`. Its only consumer is a border colour (`dashboard.py:99`).
*Reveals:* speculative addition. A scalar nobody reads is a decision not yet made.
*For Kivi:* your §4 argues that collapsing axes is the failure mode, and `importance` is that collapse. Also a provenance problem: a model-assigned float has no source you can point at, so it cannot satisfy your revisability principle (§1.3).

**Q: Where do relations live — in the schema or in the text?**
Answered: in a JSON blob appended to *both* endpoints of the edge (`agent.py:210–222`). No edges table. The write is a read-modify-write on a JSON string with no uniqueness check, so **re-running consolidation over the same pair duplicates the edge** (`agent.py:215–218` appends unconditionally).
*Deliberate or accident?* The duplicate-append reads as incomplete work, not a decision.
*For Kivi:* your entity type (§4) is relational by definition (*Priya is the client contact at Acme*). This shows what happens when relations are denormalised into blobs: no traversal, no dedupe, no integrity.

### 1.3 What is discarded

**Q: What is dropped at ingest, and is the drop recorded?**
Answered: text truncated at 10 000 characters (`agent.py:557`); media over 20 MB skipped (`agent.py:509–511`). Beyond that, **nothing is deliberately dropped and no drop is recorded**. No exclusion list, no category filter, no PII handling anywhere.
*Placement:* the truncation is a bare literal mid-function; the size skip has an explanatory comment (`agent.py:509`). One was thought about; the other was typed.
*Assumes:* everything in the inbox is fair game and belongs to one owner.
*For Kivi:* this is your §2 and §5, and the repo is blank on both. Note especially that the 10 000-char truncation is a *silent, unlogged* loss of the tail of every long document. Your Appendix C.1 wants dropped candidates logged with reasons; nothing here resembles that. This is precedent for the architecture you are arguing against.

### 1.4 Conflict, contradiction, duplicate

**Q: On re-ingesting the same content, does the system dedupe, version, or duplicate?**
Answered: duplicate. Dedupe exists *only* at the file-path level (`processed_files`, `agent.py:549`), so the same text via `POST /ingest` twice creates two rows, and the same file renamed creates two rows. No content hash. **Hardcoded** absence.
*Assumes:* volume is low enough that duplicates are noise, not corruption.
*For Kivi:* your `evidence_count` (§4) requires the opposite — recognising a new observation as the *same* memory seen again. Your §5 worked example says "already known, evidence count incremented". Nothing here can do that; it would insert a second row.

**Q: When new information contradicts old, what happens?**
Answered: nothing. Both rows persist; the query agent resolves the contradiction in prose, or doesn't. No supersession, no `status`, no `superseded_by`. **Absent and unmentioned** — I found no comment acknowledging it.
*For Kivi:* your §9 makes supersession a first-class auditable operation. Pushes toward a `status` + `superseded_by` column and append-only history, which this schema cannot express.

**Q: Is deletion real deletion?**
Answered: yes — `DELETE FROM memories WHERE id = ?` (`agent.py:275`), hard, unrecoverable, no tombstone. `clear_all_memories` additionally deletes the user's inbox *files* (`agent.py:296–307`) — a surprising blast radius, flagged in the UI (`dashboard.py:308`) but implemented as an unconfirmed one-click POST (`agent.py:648`).
*For Kivi:* your §9 is explicit that deleting the row is useless because the pattern regrows from the same transcripts. This repo demonstrates the failure exactly: delete memory #7, and if its source arrives again under a different path, it comes back. Pushes toward suppression records the extractor consults — a table this design has no slot for.

### 1.5 Retrieval and ordering

**Q: How is relevant memory found — search, embedding, or "read everything"?**
Answered: read everything. `read_all_memories` does `SELECT * … ORDER BY created_at DESC LIMIT 50` (`agent.py:156`) with **no query parameter at all** — the question never reaches SQL. Relevance is entirely the model's job over a recency-truncated dump. The README states this as a feature: "No vector database. No embeddings." (`README.md:11`).
*Placement:* hardcoded, and celebrated in the README — the repo's headline conviction.
*Assumes:* the corpus fits in context; ≤50 memories is the operating regime; re-reading everything per query is affordable; recency proxies relevance.
*For Kivi:* the scale assumption fails first. A dictation user generates memories continuously; at memory 51 the oldest silently stops existing for the query agent — **with no signal that it happened**. Worse for your §8: an abstention ("I don't have anything from Arun") becomes untrustworthy, because absence-from-the-window is indistinguishable from absence-from-memory. Your Appendix C.5 wants abstention with a shown search; this architecture cannot show one, because it did not perform one.

**Q: Is retrieval separable from disclosure?**
Answered: the question is not present. One path, one audience; everything retrieved is available to the answer.
*For Kivi:* your §6 makes this separation the product. No precedent here — and note the repo also never pays the cost your design pays: a retrieved-but-withheld memory needs a trace record (§8's Why panel), which is a write on the read path.

**Q: Are consolidations a separate retrieval tier?**
Answered: yes — `read_consolidation_history` is a distinct tool (`agent.py:231`, wired at `:372`) returning the last 10. The query agent sees raw memories *and* derived insights, undifferentiated in the prompt (`agent.py:365–370`).
*For Kivi:* the closest thing here to your tier concept, and instructive: it is a *storage* separation with no *epistemic* separation — the prompt never tells the model to treat an insight differently from a fact. Your §4 insists the grammar of storage enforce the epistemics; here the storage separates and the grammar does not.

### 1.6 What is exposed

**Q: Does the caller get memories or an answer?**
Answered: an answer, with `[Memory N]` citations requested by prompt (`agent.py:369`) — therefore not guaranteed, not validated, not resolvable to a row by any code. `GET /memories` (`agent.py:640`) exposes raw rows separately.
*For Kivi:* your §8 Why panel needs machine-checkable provenance, not model-emitted brackets. Pushes toward returning structured `used_memory_ids` from the retrieval layer rather than parsing citations out of prose.

**Q: Is the HTTP surface authenticated?**
Answered: no. Binds `0.0.0.0` (`agent.py:688`) with no auth, no CORS policy, no rate limit, and a `/clear` endpoint that wipes the DB and the user's files. Single-user assumption is total: `user_id="agent"` is a literal (`agent.py:465`, `:485`).
*Deliberate or accident?* Demo scope, not a decision. `0.0.0.0` rather than `127.0.0.1` is the part that turns local-demo into network-exposed.
*For Kivi:* multi-user is the whole setting; every table needs an owner column that does not exist here.

### 1.7 Failure and low confidence

**Q: On extraction failure, is the input retried, quarantined, or dropped?**
Answered: dropped. The `try` around ingestion logs and continues (`agent.py:562–564`), and the `processed_files` insert runs **outside** that try (`agent.py:565`), so a failed file is permanently marked processed. **This is the highest-consequence line in the repo, and there is no comment on it.** I read it as accident, not design.
*For Kivi:* silent permanent data loss on transient API failure. Pushes toward recording ingestion *attempts* with status, not just successes.

**Q: What happens when the model doesn't call the tool?**
Answered: nothing happens and nobody knows. `store_memory` is requested by prompt ("Always call store_memory", `agent.py:335`) and never verified. `_execute` (`agent.py:482`) accumulates text and discards every non-text part, so a tool-call failure is invisible; the HTTP response is a success either way (`agent.py:622`).
*Placement:* prompt-level enforcement of a correctness-critical invariant — the repo's structural weakness in one line.
*For Kivi:* Appendix C.1/C.2 require *proof* that a candidate was dropped for a stated reason. Proof requires a code-level extraction contract (structured output validated against a schema), not an instruction.

**Q: Is low confidence represented at all?**
Answered: no. `importance` is salience, not confidence, and nothing abstains. The query prompt says "If no relevant memories exist, say so honestly" (`agent.py:370`) — abstention as a politeness request.
*For Kivi:* your §8 makes abstention a designed result with a trace. Nothing here.

### 1.8 Change over time

**Q: Does memory decay, expire, or accumulate forever?**
Answered: accumulate forever. No TTL, no decay, no archival. The only forgetting is manual deletion or the implicit invisibility of anything past row 50 (`agent.py:156`).
*Placement:* absence with no comment.
*For Kivi:* your §9 requires decay windows for observations and default expiry for hypotheses. This repo's *implicit* forgetting is the opposite of yours: unprincipled, invisible, and applied to stated facts as readily as to stale patterns.

**Q: Is consolidation a one-way ratchet?**
Answered: yes. `consolidated` flips 0→1 (`agent.py:224`) and nothing flips it back. Once consolidated, a memory never re-enters the pool, so it can never be re-connected against future arrivals. Consolidations are never themselves consolidated.
*Assumes:* the connections worth finding are findable within one 10-memory window.
*For Kivi:* Appendix C.3 wants a memory assembled from evidence distributed across *multiple separate dictations*. If those dictations land in different consolidation batches, this architecture structurally cannot connect them. That is the sharpest architectural lesson in the repo.

**Q: When does consolidation run — on volume, on time, or on demand?**
Answered: a fixed timer (`agent.py:582`) gated by a count check (`>= 2`, `agent.py:591`), plus manual `POST /consolidate` (`agent.py:635`). The timer sleeps *before* the first run (`agent.py:585`), so a process restarted every 25 minutes never consolidates at all — unmarked.
*For Kivi:* your Appendix B leaves extraction timing open. This repo is the batched answer, and its failure modes — the ratchet, the sleep-first ordering, the window size — are the argument for per-transcript extraction with separate batched *consolidation*.

### 1.9 Idempotency and ordering

**Q: What is assumed idempotent?** Schema creation genuinely is (`agent.py:84`); file processing is made idempotent by path (`agent.py:549`), a weaker guarantee than content-idempotency; `store_memory` is **not** idempotent and has no idempotency key.

**Q: What is assumed ordered?** `created_at DESC` as ISO-8601 TEXT (`agent.py:156`) — correct only because the format is lexically sortable and always UTC (`agent.py:136`), an unstated invariant no test protects. Two memories written in the same microsecond have undefined relative order; `id` is never used as a tiebreak.

**Q: Is concurrent access considered?** No. A new `sqlite3.connect` per tool call with default settings (`agent.py:82`), no WAL, no busy timeout, while three concurrent async tasks write (watcher, consolidation loop, HTTP handlers). The connection in `watch_folder` (`agent.py:538`) is opened once and never closed — the only long-lived one. Under load this is a `database is locked` waiting to happen. Unmarked; reads as accident.

---

## 2. Magic numbers

**Provenance caveat:** `git blame` is unavailable (depth-1 checkout), so "traceable" here means a comment or README statement, nothing more.

| Value | Site | Traceable origin | If ×10 | If ÷10 | Tuned or guessed? |
|---|---|---|---|---|---|
| `50` — memories read per query | `agent.py:156` | none | 500 may exceed practical context; cost per query rises linearly with corpus | 5 — most questions unanswerable; abstention rate spikes | **Guessed.** Round number, no comment, and it is the de facto retrieval policy for the whole system |
| `10` — unconsolidated memories per batch | `agent.py:172` | none | 100 in one prompt: connection quality degrades, latency and cost jump | 1 — below the `>= 2` gate, consolidation never produces anything | **Guessed.** Interacts with the 30-min timer with no sign anyone modelled arrival rate |
| `10` — consolidation history depth | `agent.py:246` | none | insights crowd out raw memories in the query prompt | recent insights only; long-term synthesis invisible | **Guessed**, and suspiciously equal to the batch size |
| `2` — minimum memories to consolidate | `agent.py:349`, `:591` | stated in both prompt and code | 20: consolidation almost never fires on a quiet inbox | cannot go lower meaningfully | **Reasoned** — it is the arity of a connection. The only defensible number here |
| `0.5` — default importance | `agent.py:93` | none | n/a (bounded) | n/a | **Convention.** Midpoint of an unused scale |
| `0.7` / `0.4` — importance colour bands | `dashboard.py:99` | none | all cards one colour | all cards another | **Guessed**, cosmetic only |
| `30` — consolidation interval (min) | `agent.py:707`, `:582` | README calls it "like sleep cycles" (`README.md:68`) — a metaphor, not a measurement | 5 hours: batches exceed the 10-limit, memories silently miss consolidation forever (the ratchet) | 3 min: near-empty batches, cost per insight explodes | **Guessed**, dressed as biology |
| `5` — watcher poll seconds | `agent.py:535` | README promises "within 5–10 seconds" (`README.md:149`) | 50s breaks the README's stated promise | 0.5s: pointless syscall churn | **Guessed**, documented after the fact. A defaulted parameter never overridden (`agent.py:679`) |
| `10000` — text truncation chars | `agent.py:557` | none | 100k: cost per ingest ~10× and may exceed limits | 1k: most documents lose their body silently | **Guessed.** No comment, silent, applies to *every* text file |
| `20` — MB media limit | `agent.py:509` | comment cites Gemini's inline limit | raising it breaks the API | needlessly rejects valid files | **Tuned** — the one number sourced from an external constraint |
| `30` / `60` — dashboard HTTP timeouts (s) | `dashboard.py:77`, `:86` | none | slow ingests survive | most LLM calls time out | **Guessed.** Asymmetric with no stated reason |
| `8888` — port | `agent.py:706`, `dashboard.py:22` | none | — | — | Convention; duplicated in two files, will drift |
| `[:60]`, `[:80]`, `[:100]`, `[:16]`, `[:5]` | `agent.py:145`, `:225`, `:594`; `dashboard.py:106`, `:112` | none | — | — | **Cosmetic truncation** — except `entities[:5]` (`dashboard.py:112`), which silently hides entities from the user: presentation making a data decision |

No temperature, `top_p`, or `top_k` is set anywhere — see §4.

---

## 3. What the history says

**I cannot do this section properly, and I will say so rather than reconstruct.** The checkout is `--depth 1` and sparse; `git log` for this path yields one unrelated commit. No issues, PRs, or blame are available. The upstream at `README.md:117` (`Shubhamsaboo/always-on-memory-agent`) is where reversals would be visible. **I found no reversals — that is an artefact of my access, not a finding.**

What the *code* says in place of history:

- **No TODO, FIXME, HACK, or XXX markers anywhere.** I grepped all `.py` and `.md`. For a repo with this many rough edges, zero self-flagged shortcuts is itself informative: the edges were not noticed, or the file was written in one pass as a demo.
- **Only two explanatory comments exist:** the 20 MB Gemini limit (`agent.py:509`) and the mimetypes fallback (`agent.py:501`). Both concern external API constraints. **Not one comment explains a memory-design decision.**
- **Evidence of later addition (inferred from shape, not history — flagged as inference):**
  - `clear_all_memories` (`agent.py:283`) takes an `inbox_path` argument no other tool takes and reaches out of the database into the filesystem. That signature reads as a patch for "I cleared memories and the watcher re-ingested everything" — the path-based dedupe (`agent.py:549`) proving insufficient in practice.
  - `run_multimodal` / `_execute` (`agent.py:469`, `:482`): `_execute` exists purely to share code between `run` and `run_multimodal`, suggesting `run` came first and multimodal was bolted on. Consistent with one instruction block covering five modalities (`agent.py:324–338`).
  - The `svg` entry in `MEDIA_EXTENSIONS` (`agent.py:51`) maps to `image/svg+xml` and is sent as inline bytes to a vision model — SVG is text and is not a supported inline image type. Reads as list-completion, not a decision.
- **Backwards compatibility:** none visible. No versioning, no deprecations, no shims. `CREATE TABLE IF NOT EXISTS` (`agent.py:84`) means the schema can only be added to by hand — a system with no upgrade story, not one preserving compatibility.

---

## 4. Unexamined defaults

Choices with no comment, no config, no test, no alternative visible.

1. **SQLite, single file, default journal mode** (`agent.py:39`, `:82`). Never justified in code; the README mentions it only under "Built With" (`README.md:224`). Untried: WAL mode plus a busy timeout — two lines that would remove the concurrency hazard in §1.9.
2. **A connection per call, no pooling, no `try/finally`** (`agent.py:82`, with `db.close()` scattered manually). Untried: a module-level connection or a `contextlib` wrapper.
3. **JSON-in-TEXT for all structure** (`agent.py:140`). Untried: SQLite's JSON1 operators, or real relational tables for entities. The consequence is that you cannot query "all memories mentioning Priya" in SQL — a capability your §8 abstention example needs ("I found Arun on Atlas backend work (4 mentions)").
4. **No generation config anywhere.** Extraction — a task that wants determinism — runs at SDK defaults alongside consolidation, which wants creativity. Nobody separated them. Untried: temperature 0 for extraction.
5. **A fresh session per request** (`agent.py:463`, `:471`) with `InMemorySessionService` (`agent.py:459`), so conversational context never persists — an odd default for a *memory* product, and unremarked. Untried: a persistent session service, which ADK provides.
6. **`user_id="agent"` hardcoded** in three places (`agent.py:465`, `:473`, `:485`). Untried: anything multi-tenant.
7. **Prompt-as-policy.** All four instruction blocks (`agent.py:318–392`) encode contracts — "Always call store_memory", "Rate importance 0.0 to 1.0", "Reference memory IDs" — with zero validation. Untried: structured output / response schemas, available in the SDK already imported.
8. **`0.0.0.0` bind** (`agent.py:688`). Untried: `127.0.0.1`, the safe default for a localhost dashboard.
9. **Model routing via a natural-language orchestrator** (`agent.py:374–392`) for three mutually exclusive, caller-known intents. The HTTP layer *already knows* whether it is ingesting or querying (`agent.py:606` vs `:613`) and then pays a model call to re-derive it. Untried: calling the sub-agent directly. Inherited ADK idiom, not a reasoned choice.
10. **One model for all four roles** (`MODEL` at `agent.py:320`, `:344`, `:361`, `:378`). Untried: a cheap model for extraction, a stronger one for consolidation — the natural expression of the README's own cost argument (`README.md:212–218`).
11. **Emoji in log output** (`agent.py:145` and throughout) — inherited demo aesthetic; makes logs awkward to grep and parse.

---

## 5. Questions this repo never faced

Derived from your position document.

1. **Who does a memory belong to, and who may it mention?** (§5) Nothing here distinguishes the user from third parties; `entities` flattens both into one list (`agent.py:89`). You need a write-path barrier between "person whose memory this is" and "person appearing in it" — a distinction with no home in this schema.
2. **How do you *prove* a drop happened?** (Appendix C.1, C.2) This repo logs successful stores (`agent.py:145`) and nothing else. A dropped-candidate table with reason codes is a structure this design never needed.
3. **Can a retrieval path be structurally forbidden from seeing certain rows?** (§7) Here one tool reads one table (`agent.py:151`). Your dictation path must be *unable* to load observations — a schema/permission question (separate tables, separate tools, separate agents), and Appendix C.7 wants it demonstrated. No precedent here.
4. **How does knowing differ from saying?** (§6) One dimension here; two in yours. Your withheld-memory trace also implies retrieval must emit records even when the answer omits them — a write on the read path, which this system never performs.
5. **What makes a correction stick against re-derivation?** (§9) The hardest one. `delete_memory` (`agent.py:268`) removes a row; your requirement is a suppression the extractor consults on every future pass — a second store, consulted at write time, that this architecture has no concept of.
6. **When does a pattern become a claim?** (§4) You need `evidence_count`, `first_seen_at`, `last_confirmed_at`, and an explicit promotion event with its own timestamp. This repo has `created_at` only (`agent.py:94`) and no promotion mechanic — its consolidations promote themselves by existing.
7. **How is a hypothesis stored so it cannot be mistaken for a fact?** (§4) Your answer is grammatical — store it as an interrogative. `insight TEXT` (`agent.py:101`) is a declarative field holding model speculation, retrieved into the same prompt as facts (`agent.py:367`). The exact collapse you are designing against.
8. **How do you budget interruptions?** (§8) Rationed confirmation prompts require tracking prompts issued per user per window. Nothing here ever asks the user anything.
9. **What is the unit of provenance the user actually sees?** (§9) Yours is the source transcript with a date. Here it is `source TEXT` — a filename string (`agent.py:86`), unlinked, unresolvable, defaulting to `""`, and `"api"` for HTTP ingests (`agent.py:621`).
10. **Does an observation decay?** (§9) Requires `last_observed_at` and a sweep. No scheduled job here does anything but consolidate.
11. **Latency budget for the interactive path.** Your Hey Kivi is synchronous with a person waiting; this repo's query path is an orchestrator hop plus two tool round-trips plus a synthesis pass (`agent.py:361–372`), and the dashboard simply prints however long it took (`dashboard.py:285`). No budget, no target — your Appendix B leaves yours open, and this repo offers no data point.

---

## 6. What the tests don't cover

**There is no test suite.** Every decision below is therefore precedent, not evidence — nobody has demonstrated any of it works, including the parts that plainly do.

A change to any of these would be undetectable by any check in the repo:

- **Every magic number in §2.** Change `LIMIT 50` to `LIMIT 5` — nothing notices.
- **The extraction contract.** If the model stops calling `store_memory`, ingestion silently no-ops and `/ingest` still returns 200 (`agent.py:622`).
- **The processed-files-on-failure bug** (`agent.py:562–571`): data loss on transient failure.
- **Duplicate connection appends** (`agent.py:215–218`): run consolidation twice over overlapping sets and edges duplicate.
- **Concurrency.** Watcher + timer + HTTP writing to one unlocked SQLite file (§1.9).
- **Timestamp ordering** depending on lexical ISO-8601 sortability (`agent.py:156`). Swap the format and ordering silently inverts.
- **`_execute` discarding non-text parts** (`agent.py:487`): a tool error is indistinguishable from success.
- **The dashboard's third extension list** (`dashboard.py:25–31`) drifting from `agent.py:42–68`. Nothing reconciles them.
- **`GET /query?q=` with un-encoded question text** (`dashboard.py:279` interpolates raw user text into a URL): `&` or `#` in a question breaks it.
- **Whether consolidation actually improves answers.** The repo's entire thesis (`README.md:23`) — that active consolidation beats passive RAG — has no evaluation of any kind. Your Appendix C is a list of exactly the claims this repo asserts and never demonstrates. That contrast is arguably the most useful thing here.

---

## Closing note on classification

Distinguishing the three, as asked:

- **Deliberate design:** no-vector-DB retrieval (`README.md:11`), consolidation-as-sleep (`README.md:23`), prompt-defined memory semantics, the `>= 2` gate, the 20 MB limit.
- **Incomplete work:** duplicate connection appends, the `processed_files`-on-failure ordering, the unclosed watcher connection, `poll_interval` never wired through, `importance` written and never read.
- **Accident / inherited idiom:** `0.0.0.0`, `user_id="agent"`, the LLM orchestrator over already-known intents, one model for four roles, the SVG entry, emoji logging.
- **Backwards compatibility:** none — nothing here is preserving anything.

**Genuinely unclear:** whether `importance` was intended to drive retrieval and was abandoned, or was always decorative; whether the bidirectional-append duplication in `connections` was known; whether `--consolidate-every` was ever run at a value other than 30. Without history I will not guess.
