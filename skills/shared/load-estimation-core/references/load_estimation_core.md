---
Version: 1.0
Status: Updated
Last-Updated: 2026-05-14
Owner: Planning Specs
---
# Load Estimation Core

## Purpose

Shared rules for translating athlete context, duration, intensity intent, and durability constraints into planned load guidance.

## Binding rules

- Planned load must be expressed in kJ and must remain traceable to the selected athlete context and reference mass assumptions.
- Load estimation is durability-first. Unknown data confidence tightens claims; it never justifies optimistic escalation.
- Weekly load planning must respect higher-level guardrails before session-level ambition.
- When athlete inputs are incomplete, planners must state assumptions explicitly and stay conservative.

## Required inputs

- Athlete profile and current planning context
- Availability, logistics, and planning events
- Relevant current plan artefacts and feed-forward inputs
- Data-confidence state for any estimate derived from incomplete inputs

## Per-workout rule

- Estimate workout kJ from duration, intended metabolic role, and athlete-specific reality.
- Avoid copying historical intensity blindly; use history only as a realism bound.
- When revising an existing workout, preserve role clarity before chasing exact kJ parity.
