---
Type: Specification
Specification-For: EVIDENCE_MANIFEST
Specification-ID: EvidenceManifest
Version: 1.0

Scope: Shared
Authority: Informational

Normative-Role: ReferenceOnly
Decision-Authority: None

Applies-To:
  - Season-Planner
  - Phase-Architect
  - Week-Planner

Notes: >
  Defines the hierarchy, usage rules, and constraints for evidence sources
  within the RPS planning architecture. This document governs how evidence
  may be referenced for justification and explanation purposes only.
  It does not create authority, define rules, or override governance.
---

## 1. Purpose

This document defines **how evidence sources are used** within the RPS  
(Season → Phase → Week) planning architecture.

Evidence exists to:
- support rationale
- justify framing
- anchor decisions in established knowledge

Evidence does not create authority and does not replace governance.

## 2. Evidence Layers

### 2.1 Primary Evidence (Highest Trust)

Characteristics:
- peer-reviewed research
- systematic reviews / meta-analyses
- well-established training theory

Examples:
- Seiler (polarized / pyramidal intensity)
- Rønnestad (long-term endurance adaptation)
- durability / fatigue resistance literature

Primary evidence MAY:
- support season phase design
- justify load corridors
- explain phase intent

Primary evidence MUST NOT:
- prescribe specific workouts
- override governance constraints
- justify week-level changes

### 2.2 Secondary Evidence (Contextual / Interpretive)

Characteristics:
- expert podcasts
- coaching blogs
- practitioner interviews
- synthesis and interpretation of research

Examples:
- CTS / Fast Talk / SITZfleisch
- TrainerRoad podcasts
- practitioner frameworks

Secondary evidence MAY:
- provide terminology
- offer conceptual metaphors
- support explanation sections

Secondary evidence MUST NOT:
- introduce new training rules
- act as a trigger for plan changes
- override Primary Evidence or Principles

## 3. Repository Sources

Authoritative Evidence Files

- durability_bibliography.md

These files are curated reference collections.  
They are not executable instructions.


## 4. Evidence Usage by Agent

### 4.1 Season-Planner

MAY:
- cite evidence to justify phase structure
- reference durability / volume distribution concepts

MUST NOT:
- derive prescriptions directly from evidence
- quote podcasts as decision authority

### 4.2 Phase-Architect

MAY:
- use evidence to justify guardrails
- explain Feed Forward vs Governance decisions

MUST NOT:
- translate evidence into workout rules
- override Season intent using evidence

### 4.3 Week-Planner (Optional, Informational)

MAY:
- reference evidence for explanation only

MUST NOT:
- use evidence to justify load or intensity decisions
- use evidence to override Phase Guardrails

## 5. Evidence in Outputs (Formatting Rules)

When evidence is referenced in an artefact:
- keep references short and descriptive
- avoid quotes or long excerpts
- never cite evidence as binding authority

Good example:
`“Load corridor chosen conservatively to protect durability (Seiler).”`

Bad example:
`“Podcast X says VO₂max intervals are optimal, therefore…”`

## 6. Hierarchy Rule (Critical)

Evidence is always below:
1. Principles
2. Contracts
3. Governance Artefacts
4. Templates
5. Evidence

If evidence conflicts with governance:  
➡️ Governance always wins.

## 7. Forbidden Evidence Usage

Evidence MUST NOT be used to:
- justify compensatory load
- override kJ limits
- introduce progression logic
- bypass Feed Forward or Governance resets
- escalate Week decisions

## 8. Self-Check

Before using evidence, ask:
- Am I supporting a decision, not creating one?
- Is governance unchanged?
- Is this principle-level, not prescriptive?

Would removing this evidence change the decision?  
→ If yes, evidence is misused.
