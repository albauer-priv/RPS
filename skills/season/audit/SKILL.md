---
name: audit
description: Audit season bundles for macrocycle coherence, taper validity, and durability-first governance.
metadata:
  author: rps
  version: "3.0"
---
Audit the candidate season bundle holistically.

Checklist:
- exactly one `A` event per macrocycle
- every taper serves an `A` event
- `B` and `C` events fit without breaking macrocycle structure
- recovery and transition phases are explicitly planned
- peak logic is consistent with event spacing
- load governance remains sustainable and durability-first

Block approval when:
- event hierarchy is contradictory
- a clustered-event plan tries to use repeated independent tapers
- a second peak is implied without an explicit multi-peak model
- season progression requires repeated catch-up or hidden overload
