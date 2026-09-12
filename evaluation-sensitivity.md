# Evaluation mutation sensitivity

## Environment

- Corpus: `fixtures/development-500.json` (500 records)
- Questions: `EVAL_QUESTIONS.json` (52 cases)
- Extraction model: `qwen2.5:7b-instruct` (the configured `qwen3:8b` was not installed)
- Seed: `7`; temperature: `0`; Ollama structured JSON schema enabled
- Persisted memory inventory: 55 entity, 24 episode, 20 preference; all 99 active, zero superseded

The initial scorer reported 14/52. Its three superseded-fact passes were invalid because it checked answer text and provenance but not persisted supersession state. After adding that invariant, the trustworthy baseline is 11/52.

## Class movement

| Class | Corrected baseline | Remove `entity` type | Disable supersession | Disable empty-result abstention |
|---|---:|---:|---:|---:|
| distributed-recovery | 10/22 | **0/22 (-10)** | 10/22 (0) | 10/22 (0) |
| superseded-facts | 0/8 | 0/8 (0) | **0/8 (0; invalid baseline precondition)** | 0/8 (0) |
| demonstrated-preferences | 0/8 | 0/8 (0) | 0/8 (0) | 0/8 (0) |
| episodic-retrieval | 0/3 | 0/3 (0) | 0/3 (0) | 0/3 (0) |
| unanswerable | 1/11 | 1/11 (0) | 1/11 (0) | **0/11 (-1)** |

## Conclusions

- Removing one memory type is detected decisively by distributed-recovery. It loses every passing case.
- Disabling abstention is detected by unanswerable, although that class is already extremely weak: the baseline has one correct refusal and ten fabrications.
- The supersession mutation cannot reduce the number because the clean baseline contains no superseded memory at all. The system is already behaving like the requested mutant. The evaluator previously concealed this by awarding three text-only passes; it now requires persisted supersession evidence, so the class correctly scores 0/8.
- Demonstrated-preferences and episodic-retrieval have zero baseline passes. Their questions expose missing behavior, but pass-count mutation sensitivity cannot be established until there is a passing baseline to perturb.

No mutation was retained in production code. The structured-output compatibility fix and the stricter supersession scoring invariant remain because both were defects in the real evaluation path.
