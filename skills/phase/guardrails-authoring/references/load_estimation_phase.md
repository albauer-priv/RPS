# Phase Guardrail Load Translation

Translate season governance into exact-range weekly bands.

Method:
1. start from season corridor intent
2. constrain by exact phase purpose, availability, and allowed intensity domains
3. derive feasible min/max weekly governance load
4. return a band that downstream week planning can execute without hidden overload

Binding details:
- `weekly_kj_bands[w]` are in `planned_weekly_load_kj/week`
- use injected deterministic S5 min/max and trace; do not widen or recalculate them
- S5 intersects season corridor, availability-feasible band, optional KPI capacity band, and optional progression band
- if the intersection fails, preserve the code-owned fallback level and reason
- STOP rather than inventing a band when FTP is invalid, availability is negative, allowed domains are missing, KPI gating lacks body mass, or the feasible band is empty
