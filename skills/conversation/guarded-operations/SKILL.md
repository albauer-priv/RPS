---
name: guarded-operations
description: Bounded operational rules for Coach-style preview, apply, and scoped replan actions.
metadata:
  author: rps
  version: "1.0"
---
Operate only on the selected athlete and selected week context.

Method:
1. Use `Deterministic Coach Operation Context` for selected athlete/week, allowed operations, pending status, and confirmation boundary.
2. Read current context before previewing or applying anything.
3. Prefer preview-first operations whenever a change would persist or rebuild artifacts.
4. Keep scope bounded to the requested operation; do not branch into unrelated planning.
5. When the action is ambiguous, return a preview or clarification-oriented result instead of applying.
6. Report affected artifacts, confirmation requirements, and downstream rebuild effects explicitly.
7. When explaining durability, fatigue resistance, VO2max, fueling, Sweet Spot, VLamax, LT1, K3/low-cadence work, periodization, or masters/recovery decisions, use the durability evidence layer as justification only.

Evidence and web-source rules:
- Evidence explains why a bounded recommendation is reasonable; it never overrides active corridors, S5 bands, availability, phase guardrails, schemas, or explicit user constraints.
- Prefer peer-reviewed or DOI-backed sources first: Maunder/Seiler/Kilding/Plews, Valenzuela, Leo/Spragg/Mujika, Jones, Barsumyan, Meixner/Joyner/Sperlich, Peeters/Barrett/Podlogar, Ronnestad, Buchheit/Laursen, San Millan/Brooks, Coggan/Allen, Friel, Olbrecht.
- Prefer these source domains when web research is available: `doi.org`, `link.springer.com`, `journals.physiology.org`, `frontiersin.org`, `journals.humankinetics.com`, `journals.lww.com`, `onlinelibrary.wiley.com`, `sciencedirect.com`, `tandfonline.com`, `biomedcentral.com`, `jsc-journal.com`.
- Use applied/practitioner sources only after stronger sources or for practical framing: `fasttalklabs.com`, `trainright.com`, `inscyd.com`, `trainingpeaks.com`, `joefrieltraining.com`, `science2performance.at`, `max-training.pro`, `empiricalcycling.com`, `trainerroad.com`, `scientifictriathlon.com`, `silca.cc`.
- If web search is available and the user asks for a source-backed explanation, search by author plus title or DOI from `references/durability_bibliography.md`.
- Cite only sources you actually found in injected knowledge or web results. Use compact citations with author, year, title/source, and DOI or URL when available.
- If evidence is weak, conflicting, podcast-only, or practitioner-only, label it as applied rationale instead of scientific proof.

Hard rules:
- never persist outside guarded store operations
- never claim persistence before a confirmed pending operation is applied successfully
- never widen the requested scope on your own
- never invent follow-up planning that was not requested
- never invent source titles, authors, DOIs, URLs, study outcomes, or numerical thresholds
