# Known design limitations

These are intentional non-fixes found by the full-pipeline evaluation. They are not acceptance waivers.

## Application metadata is excluded from semantic extraction

**Mechanism.** The extractor receives user-authored text but not application/channel metadata. Channel-specific demonstrated preferences such as “Slack openings” or “client-email sign-off” therefore have weak or ambiguous scope even when the corpus metadata identifies that scope.

**Why the design chose it.** `DESIGN.md` keeps raw application context ineligible for the memory write path to reduce accidental retention of third-party or ambient context and to preserve the boundary that only user-authored content becomes memory.

**Cost of fixing it.** The eligibility model, extraction contract, provenance UI, privacy tests, and foreign-corpus schema would need a new distinction between trusted structural metadata and semantic context. Every allowed metadata field would need threat modelling and reason-coded inspection.

**When that cost is justified.** Only if evaluation on multiple independently collected corpora shows that text-only evidence cannot recover useful scoped preferences, and a reviewed allow-list of non-content metadata materially improves recall without increasing prohibited retention or false preference inference.

## Anbu does not disclose observed preferences

**Mechanism.** Default Anbu retrieval may find an observed preference but disclosure withholds its content. Several evaluation questions ask Kivi to state a pattern it has noticed without first selecting Koottu or defining that phrasing as an explicit disclosure grant.

**Why the design chose it.** Observations are lower-authority inferences. Withholding them by default prevents repetition from silently becoming user intent and keeps disclosure permission separate from relevance.

**Cost of fixing it.** Either the permission contract would need another explicit request-level grant, or “what have you noticed?” would need to become a security-sensitive Koottu intent classifier. That requires adversarial phrasing tests, UI disclosure, trace changes, and false-positive measurement.

**When that cost is justified.** Only if users demonstrably need observation questions in Anbu and an explicit-intent classifier meets a declared low false-positive bound across unseen language variants. Until then, evaluation must set Koottu when it expects observed content.

## Required provenance can exceed evidence needed for an answer

**Mechanism.** Some ground-truth cases require every corroborating record even when a strict subset independently supports the complete answer. `t1_atlas_dates`, for example, required record `meera_2026_0460` although other retrieved records support both dates and launch completion.

**Why the design chose it.** Exhaustive required-provenance lists make distributed recovery and omission measurable and discourage answers assembled from a convenient single summary record.

**Cost of fixing it.** Ground truth would need claim-level evidence sets with alternatives, such as a Boolean expression of sufficient source combinations, plus a scorer that validates each answer claim against those combinations. Maintaining fixtures becomes more expensive and reviewers must adjudicate equivalent evidence paths.

**When that cost is justified.** When redundant or summary records are common enough that mandatory flat source lists create material false failures, and claim-level provenance annotations can be maintained independently of model output.

## Model availability and portability

**Mechanism.** The design names `qwen3:8b`; the evaluation host did not have that model and used installed `qwen2.5:7b-instruct`. Extraction quality and therefore downstream scores are not comparable to a run on the designed model digest.

**Why the design chose it.** A pinned local model keeps private data local and makes model identity inspectable without vendoring model weights.

**Cost of fixing it.** Shipping or automatically acquiring the exact model adds multi-gigabyte distribution, licensing, installation, and hardware compatibility costs. Supporting multiple models requires separately locked prompts and acceptance baselines.

**When that cost is justified.** Release claims require the exact locked digest. Alternative-model results are diagnostic only unless that model receives its own fixed prompt, digest, hardware conditions, and full acceptance run.
