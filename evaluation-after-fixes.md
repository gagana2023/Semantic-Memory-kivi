# Evaluation after design-conforming fixes

## Runs

- Before: corrected baseline from the original 500-record run, 11/52.
- After: clean database, all 500 records re-ingested, all 52 fixture-bound questions executed, 24/52.
- Model for both live runs: installed `qwen2.5:7b-instruct`, seed 7, temperature 0. This differs from the unavailable model named by the design and is documented in `LIMITATIONS.md`.

## Before and after

| Class | Before | After | Change | Regression? |
|---|---:|---:|---:|---|
| distributed-recovery | 10/22 (45.5%) | 15/22 (68.2%) | +5 | No |
| superseded-facts | 0/8 (0%) | 0/8 (0%) | 0 | No; still broken |
| demonstrated-preferences | 0/8 (0%) | 0/8 (0%) | 0 | No; still broken |
| episodic-retrieval | 0/3 (0%) | 1/3 (33.3%) | +1 | No |
| unanswerable | 1/11 (9.1%) | 8/11 (72.7%) | +7 | No |
| **Overall** | **11/52 (21.2%)** | **24/52 (46.2%)** | **+13** | **No class regressed** |

## Break tests after fixes

| Class | Control | Remove entity memory type | Disable supersession | Disable empty-result abstention |
|---|---:|---:|---:|---:|
| distributed-recovery | 15/22 | **0/22** | 15/22 | 15/22 |
| superseded-facts | 0/8 | 0/8 | **0/8 (no movement)** | 0/8 |
| demonstrated-preferences | 0/8 | 0/8 | 0/8 | 0/8 |
| episodic-retrieval | 1/3 | **0/3** | 1/3 | 1/3 |
| unanswerable | 8/11 | 9/11 | 8/11 | **0/11** |

Removing entity memory is detected strongly, but it is not class-isolated: it also removes the only passing episodic case and improves unanswerable by eliminating one false-positive match. Disabling abstention is detected exactly by the unanswerable class.

The supersession break remains undetectable. The clean after-run contains no superseded memory. Most paired old/new statements were omitted or emitted with incompatible semantic keys, so the implemented exact-key comparison never activated. The evaluator correctly refuses to award supersession passes without persisted supersession evidence; it does not fabricate sensitivity where the system has no working baseline feature.

All temporary fault-injection branches were removed after these runs.
