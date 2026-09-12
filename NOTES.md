# Later-milestone notes

- Semantic/vector recall, raw fallback, exclusions beyond a minimal deny fixture, merge, lifecycle, actions, imports, and full evaluation remain intentionally unavailable per Milestone 1.

- Milestone 2 follow-up: semantic duplicate/contradiction model judging, actual embedding calls and projection-repair worker, full 500-record fixture and `python -m kivi import-corpus` CLI are not implemented; they must remain visible failures rather than be represented as complete.

- Milestone 3 follow-up: real query embedding and projection repair, raw transcript fallback, complete one-hop/disposition coverage, conflict abstention, and full Anbu/Koottu/Daari acceptance matrix remain incomplete and must not be represented as completed acceptance criteria.

- Milestone 4 follow-up: prompt budget/reveal delivery, full trace redaction across historical trace detail, source reprocessing after correction, and per-action browser smoke fixtures remain incomplete. They must fail closed or remain absent rather than be represented as complete control behavior.

- Milestone 5 follow-up: build an isolated public-contract evaluation adapter so fixed cases can execute production behavior without persisting evaluation questions as transcripts. Until then, the durable evaluator records every case as failed with `EVALUATION_PUBLIC_CONTRACT_PATH_UNAVAILABLE`.

- Release gate follow-up: no reviewer-supplied translated foreign 500-record corpus or local Ollama digest was available in this workspace. The CLI validates and imports either when supplied, but AC-FR-33 cannot be claimed until a clean-machine run has completed and the Milestone 5 evaluation adapter is fixed.
