---
name: load-estimation-week
description: Translate the active weekly corridor into day and workout load targets conservatively.
metadata:
  author: rps
  version: "5.0"
---
Translate a weekly corridor into executable week targets.

Method:
1. Start from the active corridor and phase intent.
2. Allocate load to structurally important days first: key sessions, durable endurance, and protected recovery.
3. Reconcile residual load with duration-first adjustments before any intensity escalation.
4. Use add-on aerobic load before changing workout classification or intensity domain.
5. Keep the final week structurally coherent even if the corridor is not hit perfectly.

Distribution rules:
- key load belongs on role-consistent key days first
- recovery days are protected before residual load is distributed elsewhere
- long endurance load should stay durable rather than becoming disguised quality work
- slightly under target with explanation is safer than structurally incoherent precision

Reconciliation rules:
- first adjust duration within the day-role intent
- then use aerobic add-ons where appropriate
- avoid intensity inflation that exists only to satisfy a weekly number
- if a week remains slightly low after safe reconciliation, preserve safety and explain the miss

Load semantics:
- work from governance load (`planned_load_kj`) when matching the corridor
- preserve the distinction between corridor compliance and raw mechanical work
- when a workout estimate is weak, expose fallback assumptions instead of pretending precision

Hard rules:
- no intensity inflation purely to hit corridor numbers
- no stealth load compression onto recovery days
- preserve recovery protection and key role logic
- preserve phase intent even when the corridor is tight
