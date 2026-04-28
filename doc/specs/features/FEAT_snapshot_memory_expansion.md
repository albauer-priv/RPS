---
Version: 1.0
Status: Implemented
Last-Updated: 2026-04-28
Owner: Planning / Workspace / Coach
---
# FEAT: Snapshot Memory Expansion

* **ID:** `FEAT_snapshot_memory_expansion`
* **Status:** Implemented
* **Owner/Area:** Planning / Workspace / Coach / Performance
* **Last-Updated:** 2026-04-28
* **Related:** `FEAT_central_planner_context_snapshots`, `FEAT_feed_forward_resolved_context`, `ADR-028-snapshot-based-planner-memory`

## 1) Context / Problem

The first snapshot-based planner memory release introduced `ATHLETE_STATE_SNAPSHOT` and `PLANNING_CONTEXT_SNAPSHOT` for season/phase/week planning. Two gaps remained:

* Feed-forward flows still assembled their selected-week context ad hoc instead of using snapshot-first injection.
* There was no separate non-binding narrative memory for coach-style summaries and recent advisory outputs.
* Coach still depended primarily on raw artefact preload instead of preferring the code-owned snapshot layer.

This left the architecture only partially consolidated.

## 2) Goals & Non-Goals

**Goals**
* [x] Extend snapshot-first injection to feed-forward flows.
* [x] Introduce a separate non-binding advisory memory artefact.
* [x] Prefer snapshot/advisory memory in Coach before raw artefact preload.
* [x] Refresh advisory memory when major planning/advisory agents produce new outputs.
* [x] Bump the application version because this materially changes runtime planning architecture.

**Non-Goals**
* [x] Replacing authoritative source artefacts with advisory memory.
* [x] Letting agents mutate memory artefacts directly.
* [x] Removing workspace tools for detailed follow-up reads.

## 3) Proposed Behavior

The system now maintains three code-owned memory artefact classes:

1. `ATHLETE_STATE_SNAPSHOT`
2. `PLANNING_CONTEXT_SNAPSHOT`
3. `ADVISORY_MEMORY`

Behavioral changes:

* Feed Forward builds and injects snapshots before `SEASON_PHASE_FEED_FORWARD` and `PHASE_FEED_FORWARD` agent calls.
* Coach prefers preloaded memory artefacts over raw artefact dumps.
* Advisory memory is explicitly non-binding and narrative. It compresses recent plan/report/feed-forward outputs into a compact block for conversational use.
* Major planning/advisory flows refresh advisory memory after successful writes so the central memory stays aligned with new outputs.

## 4) Implementation Analysis

**Components**
* `src/rps/orchestrator/context_snapshots.py`
  * adds advisory-memory builders and prompt rendering
* `src/rps/ui/pages/performance/feed_forward.py`
  * snapshot-first feed-forward injection + advisory refresh
* `src/rps/ui/pages/coach.py`
  * snapshot/advisory preload path with raw fallback only when snapshots are unavailable
* `src/rps/orchestrator/season_flow.py`
  * advisory refresh after successful season-plan writes
* `src/rps/orchestrator/plan_week.py`
  * advisory refresh after successful DES/phase/week writes
* `src/rps/workspace/*`
  * new artefact type, path, schema, versioning support

**Data flow**
* Authoritative inputs and outputs remain unchanged.
* Code derives `ADVISORY_MEMORY` from authoritative latest outputs.
* Feed-forward and coach consume snapshots/advisory memory first and use raw artefacts/tools only for additional detail.

## 5) Impact Analysis

**Compatibility**
* Backward compatible: Yes.
* Breaking changes: none in artifact contracts consumed by existing planners.
* User-visible change: Coach and feed-forward runs now lean on central memory artefacts first.

**Refactoring required**
* Consolidate feed-forward context assembly behind snapshot builders.
* Add a new advisory artefact with strict source-trace metadata.
* Reduce raw-coach preload dependence.

## 6) Options & Recommendation

### Option A — Extend existing snapshot system + add advisory memory

**Pros**
* Minimal architectural sprawl
* Reuses already accepted snapshot pattern
* Keeps authoritative vs advisory separation explicit

**Cons**
* Adds another derived artefact type
* Requires more refresh points after successful runs

### Option B — Keep feed-forward separate and use coach-only summaries in memory

**Pros**
* Smaller code change

**Cons**
* Leaves feed-forward outside the central memory architecture
* Misses the chance to make the memory model consistent

### Recommendation
* Choose Option A.

## 7) Acceptance Criteria (DoD)

* [x] Feed-forward page injects snapshot-based context before season/phase feed-forward agent calls.
* [x] `ADVISORY_MEMORY` exists as a workspace artefact with schema + versioning support.
* [x] Coach prefers snapshot/advisory memory preload and falls back to raw artefacts only when snapshots are unavailable.
* [x] Successful DES/Season/Phase/Week/Feed-Forward runs refresh advisory memory.
* [x] Docs and ADR reflect the expanded architecture.
* [x] Application version is bumped.

## 8) Migration / Rollout

* No migration required for existing authoritative artefacts.
* New derived artefacts appear opportunistically after the next successful runs.
* Coach and feed-forward fall back safely if snapshots are not yet present.

## 9) Risks & Failure Modes

* Snapshot/advisory artefacts may be temporarily absent for a week if no planning/advisory flow ran yet.
  * Safe behavior: fallback to raw artefact/tool path.
* Advisory summaries may become stale if refresh hooks are missed.
  * Safe behavior: advisory memory remains non-binding; authoritative artefacts still control planning.

## 10) Observability / Logging

* Existing artifact-write logging covers the new advisory artefact.
* Feed-forward and planning logs should show snapshot/advisory writes via normal workspace logging.

## 11) Documentation Updates

* [x] `doc/adr/ADR-028-snapshot-based-planner-memory.md`
* [x] `doc/architecture/workspace.md`
* [x] `doc/overview/artefact_flow.md`
* [x] `CHANGELOG.md`

## 12) Link Map

* `doc/adr/ADR-028-snapshot-based-planner-memory.md`
* `doc/architecture/workspace.md`
* `doc/architecture/schema_versioning.md`
* `doc/overview/artefact_flow.md`
* `doc/specs/contracts/logging_policy.md`
