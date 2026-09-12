# Meera Sethi development corpus

## Summary

This corpus contains 500 user-authored dictation records for Meera Sethi, Product Lead at Ternary Studio, from 5 January through 30 June 2026 (Asia/Kolkata). It follows the `records` import contract documented in `RUN.md`: every item has a stable `transcript_id`, degraded `raw_asr`, corrected `formatted_text`, `occurred_at`, and only supported source metadata (`source`, `application`, optional `channel`, and `language`).

Meera’s work centres on Acme Mobility’s Atlas portal, the stopped Meterline billing discovery, the Harbor onboarding pilot, Ternary’s Q3 pricing page, and the completed Cedar handoff. The corpus follows her weekday rhythm, including Tuesday/Thursday client-review shifts, late-evening review recaps, sparse weekends, a Cedar handoff lull, prototype-test consolidation, the April office closure, the Atlas beta spike, and the Priya-to-Ria handoff lull.

Most records are intentionally mundane: acknowledgements, link corrections, room corrections, draft moves, attachment notes, reminders, and private scratch items. They are retained as source transcripts but should normally produce no durable semantic memory.

## What is planted

`GROUND_TRUTH.json` is the machine-readable index. Its 33 items cover facts, preferences, and episodes; each lists all carrying record IDs, the correct answer, and the intended recovery behavior.

The planted set includes:

- Single-pass facts, including Meera’s join date, Devika’s QA ownership, Elliot’s approval role, and the Cedar project identity.
- Distributed facts requiring three or more records, including Cedar’s completion, Atlas launch state, project dates, contact handoffs, and the six-month portfolio state.
- Supersession histories for Meera’s manager, the Atlas review cadence, Arun’s role, Meterline’s direction, the Harbor pilot date, Acme’s coordination contact, pricing-page structure, and pricing ownership. Ground truth names the current value and change date where the corpus supports one.
- Demonstrated-only preferences: morning Slack openings, owner-and-date assignments, prose client emails, `Best, Meera` sign-offs, decision-before-action recaps, four-heading decision documents, and replacing “leverage” with “use.” These must remain observed rather than stated.
- Time/app/topic episodes, notably the 18 May Safari invoice-PDF beta bug and its 21 May ship decision, plus dated Atlas reviews and launch events.
- Three near-duplicate Safari bug records created as realistic mobile retries. They should merge into one semantic memory without treating repeated wording as three independent facts.
- One deliberate unresolved stated contradiction: Atlas support-log retention is recorded as both 90 and 120 days. The system should surface both values or abstain, not silently pick the later one.
- Proper-name traps for Priya/Ria Raghavan and Arun/Varun Menon. Formatted output resolves them only where role, organisation, project, or time supplies sufficient context.

Raw ASR is degraded throughout with absent punctuation, lowercasing, fillers, self-repair, spoken punctuation, homophones, and recurring entity errors such as `Atlus`, `Acne`, `Turnery`, `Stripe building`, and mangled names. Every raw/formatted pair differs materially in punctuation, structure, entity spelling, correction, or normalization.

## Why these choices

The corpus is designed to exercise the memory contract rather than maximize the number of extractable facts. Its signal is sparse, temporally ordered, and surrounded by plausible non-memory traffic. Explicit facts test stated memory; repeated structures test observed memory without automatic promotion; reversals test current-versus-historical truth; and the contradiction tests the requirement to preserve unresolved disagreement. Duplicates and similar names stress evidence accounting and disambiguation.

The generator is deterministic (`generate_corpus.py`) so record IDs and ground-truth references are reproducible. The committed JSON is the import artifact; running the generator recreates both JSON files.

## What this corpus does not test

- Audio capture, speech recognition, voice output, images, or document ingestion. Raw ASR is replayed text.
- Multiple account owners, cross-user isolation, multilingual dictation, or timezone/DST changes.
- Application context, copied third-party message bodies, or tool-result admission. Records contain Meera’s authored dictation only.
- Prohibited personal-memory categories such as health, politics, faith, family, mood, or non-work finance. Those require dedicated negative/canary fixtures and should not be embedded in this reusable corpus.
- Explicit confirm/correct/forget actions, pinning, lifecycle expiry, permission-mode transitions, Daari hypotheses, or schedule-tool execution; those are interaction-level tests rather than import records.
- Model failures, malformed JSON, blank fields, duplicate-ID content conflicts, retry/quarantine behavior, or reverse arrival order. The committed corpus is schema-valid and chronologically sorted; separate failure fixtures should cover those paths.
- Exhaustive recall phrasing or relevance-threshold calibration. Ground truth specifies semantic targets, not a complete evaluation question set.

