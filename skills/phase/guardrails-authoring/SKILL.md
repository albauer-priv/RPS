---
name: guardrails-authoring
description: Author exact-range phase guardrails as weekly bands plus execution boundaries.
metadata:
  author: rps
  version: "5.0"
---
Author guardrails for one exact phase range.

Method:
1. Convert season governance into exact-range weekly load bands.
2. Resolve a deterministic baseline week from the recent history when baseline-based progression logic is needed.
3. Derive a feasible band from availability hours, allowed intensity domains, and governance load semantics.
4. If KPI gating is enabled, intersect feasible bands with KPI capacity guidance instead of inventing extra headroom.
5. Express execution boundaries that later structure and week planning must respect.
6. Encode what is allowed, suppressed, or protected in this phase.

Baseline selection:
- use the recent `6-8` week lookback, default `8`
- exclude clear deload/disrupted weeks, spike weeks, and too-sparse weeks
- choose the most recent structurally valid week that passes the baseline quality gates
- if no week qualifies, use the median week as a low-confidence baseline

Feasible-band logic:
- start from `availability_hours * 3600`
- derive a realistic feasible min/max from the available time and allowed intensity domains
- interpret the result in governance-load space, not raw mechanical work
- if the season corridor is infeasible for this exact phase, narrow it rather than silently pushing overload downstream

Execution boundaries:
- specify what intensity domains are allowed, suppressed, or only touched sparingly
- make recovery protection explicit where cadence or event context requires it
- keep exact-range traceability visible in every guardrail result

Hard rules:
- guardrails are binding for downstream structure and week planning
- exact range must stay traceable and must not drift
- do not hide unrealistic load pressure behind wide bands
- do not let execution rules contradict season-owned cadence or taper logic
