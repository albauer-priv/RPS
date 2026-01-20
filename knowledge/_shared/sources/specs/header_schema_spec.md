---
Type: Specification
Specification-For: HEADER_SCHEMA
Specification-ID: HeaderSchemaSpec
Version: 1.1

Scope: Shared
Authority: Binding

Applies-To:
  - Data-Pipeline
  - Macro-Planner
  - Meso-Architect
  - Micro-Planner
  - Workout-Builder
  - Performance-Analyst
  - Policy-Owner

Notes: >
  Repository-wide header schema for agents, specs, templates, artefacts, and contracts.
---

# Header Schema


## 1. Purpose

This document defines a **canonical YAML header schema** for Markdown repository documents
(specifications, contracts, policies, principles). JSON artefacts are governed by
`artefact_json_schema_spec.md` and the JSON Schemas in ``.

For any header fields that overlap with JSON artefact meta, the authoritative
definitions live in `artefact_meta.schema.json`. This spec governs YAML formatting
and Markdown document headers only.

Goals:
- enable consistent linting / CI validation
- make authority and ownership explicit
- support traceability and versioning
- reduce ambiguity between **specs**, **templates**, **contracts**, and **artefacts**

**Rule:** Every governed Markdown document MUST start with a YAML header: `--- ... ---`

---

## 2. Global Conventions

### 2.1 Field naming
- Use **Title-Case keys** with hyphens: `Created-At`, `Owner-Agent`, `Run-ID`
- Keys are case-sensitive for tooling (lint should enforce canonical keys)

### 2.2 Date/time formats
- `Created-At`: ISO-8601 timestamp (e.g., `2025-01-12T09:30:00Z`)
- ISO week format: `yyyy-ww` (e.g., `2025-50`)

### 2.3 Authority levels
- `Binding`: MUST be followed; overrides informational sources
- `Informational`: may be used; MUST NOT override binding sources

### 2.4 Immutability
- All artefacts are immutable; changes produce a new artefact with a new `Run-ID`

### 2.5 Compliance Levels (Transition)

This spec supports a **hybrid transition**:

- **Strict**: only canonical fields are allowed (lint = error on legacy fields).
- **Transitional**: legacy aliases are allowed (lint = warning, with migration guidance).

Canonical fields use **ID-based references** (not file paths) wherever possible.
File references may be included as optional convenience fields, but never replace IDs.

### 2.6 Agent identifiers
- Use **Title-Case with hyphens** (e.g., `Macro-Planner`, `Meso-Architect`).

---

## 3. Document Types & Required Headers

There are **five** governed document types. The first four are Markdown; artefacts are JSON:

1) **Specification** (rules, semantics, calculations)  
2) **InterfaceSpecification** (structure of artefacts)  
3) **Contract** (agent-to-agent agreement)  
4) **Template** (instantiation blueprint)  
5) **Artefact** (instantiated output exchanged between agents) — **JSON only** (see Artefact JSON Schema spec)

Each type has its own required fields.

---

## 4. Schema: Specification

### 4.1 Required Fields

```

Legacy aliases (Transitional mode):
- `Dependencies-ID` is accepted but will be deprecated.

Legacy aliases (Transitional mode):
- `Binding-Specs-ID` and `Dependencies-ID` are accepted but will be deprecated.

Legacy aliases (Transitional mode):
- `Dependencies-ID` (list of strings or ID objects) is accepted but will be deprecated.
---
Type: Specification
Specification-For: <CONCEPT>
Specification-ID: <StableID>
Version: <SemVer>

Scope: <Shared|Agent|Context>
Authority: <Binding|Informational>
---
```

### 4.2 Optional Fields

```
---
Applies-To:
  - <agent>
Explicitly-Not-For:
  - <agent>
Dependencies:
  - Specification-ID: <StableID>
    Version: <SemVer>
  # or
  - Interface-ID: <StableID>
    Version: <SemVer>
Implements:
  Interface-ID: <StableID>
  Version: <SemVer>
Normative-Role: <Guardrails|DecisionGates|JustificationOnly|ReferenceOnly|StructuralRules|Execution>
Decision-Authority: <None|GuardrailOnly|GateAndProgression>
Purpose: <text>
Source: <text>
Notes: <text>
---
```

### 4.3 Example: Load Estimation Spec

```
---
Type: Specification
Specification-For: LOAD_ESTIMATION
Specification-ID: LoadEstimationSpec
Version: 1.0

Scope: Shared
Authority: Binding

Applies-To:
  - Macro-Planner
  - Meso-Architect
  - Micro-Planner
  - Performance-Analyst

Dependencies:
  - Specification-ID: TraceabilitySpec
    Version: 1.0

---
```

---

## 5. Schema: InterfaceSpecification

### 5.1 Required Fields

```
---
Type: InterfaceSpecification
Interface-For: <ARTIFACT_TYPE>
Interface-ID: <StableID>
Version: <SemVer>

Scope: <Shared|Agent|Context>
Authority: <Binding|Informational>
---
```

### 5.2 Optional Fields

```
---
Applies-To:
  - <agent>
Temporal-Scope:
  From: <YYYY-MM-DD>
  To: <YYYY-MM-DD>
Binding-Specs:
  - Specification-ID: <StableID>
    Version: <SemVer>
Dependencies:
  - Specification-ID: <StableID>
    Version: <SemVer>
Notes: <text>
---
```

### 5.3 Example: Events Interface Spec

```
---
Type: InterfaceSpecification
Interface-For: EVENTS
Interface-ID: EventInterface
Version: 1.0

Scope: Context
Authority: Informational

Applies-To:
  - Macro-Planner
  - Performance-Analyst

Temporal-Scope:
  From: 2025-01-01
  To: 2025-12-31

Binding-Specs:
  - Specification-ID: TraceabilitySpec
    Version: 1.0
---
```

---

## 6. Schema: Contract

### 6.1 Required Fields

```
---
Type: Contract
Contract-Name: string
Version: string
Status: Draft | Active | Deprecated

Scope: Shared | Macro | Meso | Micro
Authority: Binding | Informational | Derived

From-Agent: Agent-ID
To-Agent: Agent-ID

Dependencies:               # OPTIONAL
  - ID: string              # Specification-ID | Interface-ID
    Version: string

Notes: string               # OPTIONAL
---
```


### 6.2 Optional Fields

```
---
Dependencies:
  - ID: <StableID>
    Version: <SemVer>
Notes: <text>
---
```

### 6.3 Example: micro__builder contract

```
---
Type: Contract
Contract-Name: micro__builder
Version: 1.2
Status: Active

Scope: Shared
Authority: Binding

From-Agent: Micro-Planner
To-Agent: Workout-Builder

Dependencies:
  - ID: LoadEstimationSpec
    Version: 1.0
---
```

---

## 7. Schema: Template

Templates are **not outputs**; they are blueprints. They should declare the interface they implement.

### 7.1 Required Fields

```
---
Type: Template
Template-For: <ARTIFACT_TYPE>
Template-ID: <StableID>
Version: <SemVer>

Authority: <Binding|Informational>
Implements:
  Interface-ID: <StableID>
  Version: <SemVer>
---
```

### 7.2 Optional Fields

```
---
Scope: <Shared|Agent|Context>
Owner-Agent: <agent>
Dependencies:
  - Specification-ID: <StableID>
    Version: <SemVer>
Notes: <text>
---
```

### 7.3 Example: activities_actual template

```
---
Type: Template
Template-For: ACTIVITIES_ACTUAL
Template-ID: ActivitiesActualTemplate
Version: 1.1

Scope: Shared
Authority: Binding
Implements:
  Interface-ID: ActivitiesActualInterface
  Version: 1.0

Owner-Agent: Data-Pipeline
Dependencies:
  - Specification-ID: TraceabilitySpec
    Version: 1.0
---
```

---

## 8. Schema: Artefact

Artefacts are the **instantiated outputs** exchanged between agents.
JSON artefacts MUST NOT use YAML headers. Use `artefact_json_schema_spec.md`
and the JSON Schemas in `` instead.

### 8.1 Required Fields (All Artefacts)

```
---
Artifact-Type: <ARTIFACT_TYPE>
Version: <SemVer>

Owner-Agent: <agent>
Authority: <Binding|Informational>

Run-ID: <unique>
Created-At: <ISO-8601 timestamp>

Implements:
  Interface-ID: <StableID>
  Version: <SemVer>

Trace-Upstream: []
---
```

### 8.1.1 Transitional (Legacy) Header (Allowed During Migration)

Legacy artefacts may use a reduced header. Lint should warn and request upgrades.

```
---
Artifact-Type: <ARTIFACT_TYPE>     # OR Type: <ARTIFACT_TYPE> (legacy)
Version: <SemVer>
Interface-ID: <StableID>
Interface-Version: <SemVer>        # optional
Owner-Agent: <agent>               # recommended
Created-At: <ISO-8601 date or timestamp>
Run-ID: <unique>                    # recommended
---
```

Legacy aliases (Transitional mode):
- `Type` is accepted as a legacy alias for `Artifact-Type`.
- `Interface-ID` / `Interface-Version` are accepted as legacy aliases for `Implements`.
- `Stand` is accepted as a legacy alias for `Created-At` (date-only, should be upgraded).

### 8.2 Optional Fields (Common)

```
---
Scope: <Shared|Macro|Meso|Micro|Context>
ISO-Week: <yyyy-ww>
ISO-Week-Range: <yyyy-ww--yyyy-ww>
Temporal-Scope:
  From: <YYYY-MM-DD>
  To: <YYYY-MM-DD>
Trace-Data:
  - <file.md>
Trace-Events:
  - <file.md>
Notes: <text>
---
```

### 8.5 Artefact Body-Only Fields (Guidance)

The following **domain-specific fields belong in the artefact body**, not in the YAML header:

- Block status and governance metadata (e.g., `Block-Status`, `Change-Type`, `Block-Type`)
- Applicability/validity controls (e.g., `Applies-To`, `Valid-Until`)
- Planning context markers (e.g., `Planning-Horizon`, `Season-Brief-Ref`, `Athlete-Profile-Ref`)
- Lineage tables or trigger lists (e.g., `Derived-From`, `Upstream-Inputs`, `Upstream-Triggers`)
- Weekly content sections (e.g., kJ corridors, permissions, delta changes)

Use header fields only for **identity, authority, ownership, versioning, and traceability**.

### 8.3 Example: events artefact

```
---
Artifact-Type: EVENTS
Version: 1.0

Owner-Agent: User
Authority: Informational

Run-ID: 20250112_evt01
Created-At: 2025-01-12T09:30:00Z

Temporal-Scope:
  From: 2025-01-10
  To: 2025-01-16

Implements:
  Interface-ID: EventInterface
  Version: 1.0
Trace-Upstream: []
---
```

### 8.4 Example: weekly data artefact (activities_actual)

```
---
Artifact-Type: ACTIVITIES_ACTUAL
Version: 1.1

Owner-Agent: Data-Pipeline
Authority: Binding

Run-ID: 20251215_gw_01
Created-At: 2025-12-15T07:10:00Z
ISO-Week: 2025-50

Implements:
  Interface-ID: ActivitiesActualInterface
  Version: 1.0

Trace-Upstream: []
---
```

---

## 9. Key Rules (Normative)

### 9.1 No mixing document types

* A document with `Type: Specification` MUST NOT use `Artifact-Type`
* A document with `Artifact-Type: ...` MUST NOT use `Type: Specification`

### 9.2 Implements must be resolvable

Any document containing `Implements` MUST reference an existing InterfaceSpecification:

* `Interface-ID` must exist
* `Version` must exist

### 9.3 Authority consistency

* If `Authority: Binding`, the document must not contain optional interpretations framed as prescriptions
* Interpretation sections must be clearly labeled and non-binding

### 9.4 ISO-Week naming rule (for weekly artefacts)

If filename matches `*_yyyy-ww.md`, then header MUST contain `ISO-Week: yyyy-ww` and must match.

### 9.5 ID-first dependencies

Dependencies and binding specs MUST be expressed as **IDs with explicit versions**.
Dependencies may reference Specification-IDs or Interface-IDs where applicable.
File references are optional and must not be the only link.

---

## 10. Recommended File Naming (Excerpt)

Weekly artefacts:

* `<artifact>_yyyy-ww.md`

Examples:

* `activities_actual_2025-50.md`
* `activities_trend_2025-50.md`

---


# Addendum
---

## 1. Purpose

This addendum exists to cover **two special but critical document classes**:

1. **Principles**  
   (time-stable planning guardrails)
2. **KPI Profiles**  
   (decision-relevant threshold sets with gate logic)

These documents:
- are not artefacts
- are not templates
- but directly influence planning decisions

The addendum introduces **explicit semantic roles** to avoid ambiguity.

---

## 2. New Header Fields (Normative)

The following OPTIONAL fields are introduced for `Type: Specification`.

They are **normative if present**.

### 2.1 `Normative-Role`

Describes **how** the document influences downstream planning.

Allowed values:

| Value | Meaning |
|-----|--------|
| `Guardrails` | Constrains decisions, but defines no numeric thresholds |
| `DecisionGates` | Defines explicit thresholds and decision outcomes |
| `JustificationOnly` | Provides evidence or rationale only |
| `ReferenceOnly` | Descriptive reference, no planning impact |

---

### 2.2 `Decision-Authority`

Describes **what kind of decisions** the document is allowed to influence.

Allowed values:

| Value | Meaning |
|-----|--------|
| `None` | Must never influence decisions |
| `GuardrailOnly` | May restrict options, but not gate progression |
| `GateAndProgression` | May trigger progression, hold, regression, deload |

---

## 3. Principles Documents

### 3.1 Semantic Classification

Principles documents:
- define **timeless planning rules**
- contain **no numeric thresholds**
- constrain *how* agents plan, not *when* they progress

They MUST be modeled as `Type: Specification`.

---

### 3.2 Required Header Pattern (Principles)

```
---
Type: Specification
Specification-For: PLANNING_PRINCIPLES
Specification-ID: <StablePrinciplesID>
Version: <SemVer>

Scope: Shared
Authority: Binding

Normative-Role: Guardrails
Decision-Authority: GuardrailOnly

Applies-To:
  - Macro-Planner
  - Performance-Analyst

Related-Evidence:
  - <evidence_layer>.md
---
```

### 3.3 Example (Durability-First Principles)

```
---
Type: Specification
Specification-For: PLANNING_PRINCIPLES
Specification-ID: DurabilityFirstPrinciples
Version: 1.0

Scope: Shared
Authority: Binding

Normative-Role: Guardrails
Decision-Authority: GuardrailOnly

Applies-To:
  - Macro-Planner
  - Performance-Analyst

Related-Evidence:
  - evidence_layer_durability_ultra_endurance.md
---

```

## 4. Evidence Layer Documents
### 4.1 Semantic Classification

Evidence documents:
- justify principles and decisions
- contain no rules, no thresholds
- must never override governance

They MUST be modeled as Type: `Specification`.

### 4.2 Required Header Pattern (Evidence)

```
---
Type: Specification
Specification-For: EVIDENCE_LAYER
Specification-ID: <EvidenceID>
Version: <SemVer>

Scope: Shared
Authority: Informational

Normative-Role: JustificationOnly
Decision-Authority: None

Applies-To:
  - Macro-Planner
  - Performance-Analyst
---
```

### 4.3 Example

```
---
Type: Specification
Specification-For: EVIDENCE_LAYER
Specification-ID: DurabilityEvidenceLayer
Version: 1.0

Scope: Shared
Authority: Informational

Normative-Role: JustificationOnly
Decision-Authority: None

Applies-To:
  - Macro-Planner
  - Performance-Analyst
---
```

## 5. KPI Profiles (DES / Threshold Sets)
### 5.1 Semantic Classification

KPI Profiles:
- define explicit numeric thresholds
- encode decision rules (green / yellow / red)
- influence progression, deloads, and holds

They act as:
- decision authority
- structured profiles with a stable schema

Therefore:
- Structure → InterfaceSpecification
- Values & rules → Specification (profile instance)


### 5.2 KPI Profile Interface Spec (Structure)

```
---
Type: InterfaceSpecification
Interface-For: KPI_PROFILE
Interface-ID: KPIProfileInterface
Version: 1.0

Scope: Shared
Authority: Binding

Applies-To:
  - Macro-Planner
  - Performance-Analyst
---

```

### 5.3 KPI Profile Specification (Concrete Thresholds)

```
---
Type: Specification
Specification-For: KPI_PROFILE
Specification-ID: <ConcreteProfileID>
Version: <SemVer>

Scope: Shared
Authority: Binding

Normative-Role: DecisionGates
Decision-Authority: GateAndProgression

Implements:
  Interface-ID: KPIProfileInterface
  Version: 1.0

Applies-To:
  - Macro-Planner
  - Performance-Analyst

Dependencies:
  - Specification-ID: DurabilityFirstPrinciples
    Version: 1.0
  - Specification-ID: LoadEstimationSpec
    Version: 1.0
---

```

### 5.4 Example (Brevet 200–400 km Masters)

```
---
Type: Specification
Specification-For: KPI_PROFILE
Specification-ID: KPI_Profile_DES_Brevet_200-400km_Masters
Version: 1.0

Scope: Shared
Authority: Binding

Normative-Role: DecisionGates
Decision-Authority: GateAndProgression

Implements:
  Interface-ID: KPIProfileInterface
  Version: 1.0

Applies-To:
  - Macro-Planner
  - Performance-Analyst

Dependencies:
  - principles_paper_durability_first_ultra_cycling.md
  - load_estimation_spec_v1.0.md
---
```
---

## 6. Linting Implications (Normative)

A linter SHOULD enforce:
- Normative-Role: Guardrails ⇒ no numeric thresholds
- Decision-Authority: None ⇒ no decision rules
- DecisionGates ⇒ explicit GREEN/YELLOW/RED logic present
- Implements ⇒ referenced InterfaceSpecification exists
- Evidence documents MUST NOT be cited as binding sources

---
## 7. Summary

This addendum enables:
- clean separation between principles, evidence, and decision logic
- explicit modeling of guardrails vs gates
- safe reuse of KPI profiles across agents
- future-proof linting and CI validation

No existing headers are invalidated by this addendum.
