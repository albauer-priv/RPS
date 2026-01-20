---
Type: Specification
Specification-For: CONTRACT_PRECEDENCE
Specification-ID: ContractPrecedenceSpec
Version: 1.0

Scope: Shared
Authority: Binding

Applies-To:
  - Data-Pipeline
  - Macro-Planner
  - Meso-Architect
  - Micro-Planner
  - Workout-Builder

Notes: >
  Defines binding precedence and conflict-resolution rules between
  contracts, governance artefacts, specifications, and previews.
---

# Contract Precedence Specification

## 1. Global Precedence Order (Highest → Lowest)

1. Governance Artefacts
   - `block_governance_yyyy-ww--yyyy-ww+3.json`
   - `block_feed_forward_yyyy-ww.json` (within validity window)
2. Agent Contracts
3. Specifications & Schemas
4. Templates (legacy, deprecated)
5. Previews & Informational Artefacts

Higher layers always override lower layers.

## 2. Contract vs. Governance

- Contracts must never override governance.
- In conflicts, governance always wins.

## 3. Contract vs. Contract

If multiple contracts apply:
1. More specific scope wins (Micro > Meso > Macro > Shared)
2. If equal scope, upstream governance intent wins
3. If unresolved, STOP and require explicit resolution

## 4. Contract vs. Specification

- Contracts may restrict behaviour further
- Contracts may not contradict binding specifications

## 5. Preview Artefacts

- Previews are never authoritative
- In conflicts, previews are ignored

## 6. Data Artefacts

- Data artefacts never decide
- Rules and governance always override data implication

## 7. Lint Rules (Implied)

- Preview referenced as authority ⇒ FAIL
- Contract overriding governance ⇒ FAIL
- Conflicting active contracts without resolution ⇒ FAIL
- Decision derived directly from data artefact ⇒ FAIL
