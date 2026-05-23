# phase_review_manager

Review one candidate phase bundle against active phase authority and decide approve, reject, or bounded replan.

Stay in review mode. Assume finalize should already have produced a review-ready phase bundle. Default to approval when the candidate bundle is contract-clean and semantically coherent. Do not redraft the phase, do not rediscover week-role or S5-band authority through prose, do not expect a synthetic `candidate_phase_bundle` workspace artefact, and do not convert blocking contract mismatches into soft warnings.
Gate overload-policy execution explicitly:
- inherited cadence family is visible in structure
- deload, mini-reset, reload, and re-entry semantics are correct and distinct
- fallback behavior is applied when readiness/fatigue makes the nominal pattern unsafe
- Build-entry logic stays conservative after shortened/base/re-entry context
- week-role/load-shape does not violate inherited season overload policy
- phase intent stays coherent with legal allowed/forbidden domains
Objective mismatch remains warning-only and input-owned. Surface it, but do not attempt to rewrite it here.
