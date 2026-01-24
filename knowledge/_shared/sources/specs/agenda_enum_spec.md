---
Type: Specification
Specification-For: AGENDA_ENUM
Specification-ID: AgendaEnumSpec
Version: 1.2

Scope: Shared
Authority: Binding

Applies-To:
  - Macro-Planner
  - Meso-Architect
  - Micro-Planner
  - Workout-Builder

Notes: >
  Defines the canonical agenda vocabulary and allowed combinations
  for block and micro-level planning artefacts.
  This specification is semantic and normative; enum values are defined in schema and
  this spec defines meanings and combination constraints.
---

# AGENDA ENUM SPECIFICATION
​
This document defines the **authoritative agenda semantics**
used for block execution previews and block execution architectures.
​
It provides:
- standardized day roles
- standardized intensity domains
- standardized load modalities
- strict combination rules
​
This specification is **binding**.
Any artefact violating this spec is INVALID.

## Schema Reference (Normative)

The canonical enum values are defined in:
- `agenda_enum.schema.json`

This spec defines semantics and combination rules only. If there is any mismatch, the schema prevails.
​
---
​
## 1) DAY_ROLE_ENUM
**(Mandatory · exactly one per day)**
​
Describes the **structural role of a day** in the block.

### Semantics

| DAY\_ROLE | Meaning                            |
| --------- | ---------------------------------- |
| REST      | No training                        |
| RECOVERY  | Very light / regenerative          |
| ENDURANCE | Endurance without focused stimulus |
| QUALITY   | One focused training stimulus      |
| OPTIONAL  | Can be dropped without replacement |
| FLEX      | Freely movable                     |
| TRAVEL    | Travel / logistics                 |
| EVENT     | Race, brevet, test                 |
| OFF\_BIKE | No cycling activity                |

## 2) INTENSITY_DOMAIN_ENUM

(Optional · max. one · default = NONE)

Describes the physiological intensity domain (label only).

### Semantics

| Domain    | Meaning                      |
| --------- | ---------------------------- |
| NONE      | No explicit intensity domain |
| RECOVERY  | Regenerative intensity       |
| ENDURANCE | Aerobic base                 |
| TEMPO     | Upper endurance / tempo      |
| SST       | Sweet Spot                   |
| VO2MAX    | VO₂max-oriented              |

⚠️ These are labels, not zones, not targets.

## 3) LOAD_MODALITY_ENUM

(Optional · max. one · default = NONE)

Describes how load is generated, not how intense it is.

### Semantics

|Modality	|Meaning|
|---|---|
|NONE	|No special load modality|
|K3	|Kraftausdauer (high torque / low cadence)|

## 4) Combination Rules (BINDING)

### 4.1 Base Rules

- DAY_ROLE is mandatory.
- INTENSITY_DOMAIN defaults to NONE.
- LOAD_MODALITY defaults to NONE.

Only one value per enum is allowed.

### 4.2 Allowed Combinations

| DAY\_ROLE | INTENSITY\_DOMAIN             | LOAD\_MODALITY |
| --------- | ----------------------------- | -------------- |
| REST      | NONE                          | NONE           |
| OFF\_BIKE | NONE                          | NONE           |
| TRAVEL    | NONE                          | NONE           |
| FLEX      | NONE                          | NONE           |
| RECOVERY  | NONE, RECOVERY                | NONE           |
| ENDURANCE | NONE, ENDURANCE               | NONE           |
| OPTIONAL  | NONE, ENDURANCE               | NONE           |
| QUALITY   | TEMPO, SST, VO2MAX            | NONE           |
| QUALITY   | SST                           | K3             |
| EVENT     | ENDURANCE, TEMPO, SST, VO2MAX | NONE, K3       |

### 4.3 Forbidden Combinations (Examples)

- ENDURANCE + SST
- ENDURANCE + VO2MAX
- RECOVERY + SST
- QUALITY + NONE
- QUALITY + ENDURANCE
- LOAD_MODALITY = K3 with INTENSITY_DOMAIN = VO2MAX
- LOAD_MODALITY = K3 with INTENSITY_DOMAIN = TEMPO
- LOAD_MODALITY = K3 with INTENSITY_DOMAIN = ENDURANCE
- Any day with multiple intensity domains
- Any day with multiple load modalities

Violations invalidate the artefact.

## 5) Explicitly Forbidden Content

Agenda artefacts MUST NOT contain:

- Power zones (Z1–Z7)
- %FTP values
- Durations or time targets
- Interval structures
- kJ / load numbers
- Progression or ramp language

If such content appears, the artefact is INVALID.

## 6) Governance & Usage

This specification is referenced by:

- `block_execution_arch_yyyy-ww--yyyy-ww+3.json`
- `block_execution_preview_yyyy-ww--yyyy-ww+3.json`
- Micro-Planner validation logic

Higher-level artefacts (Meso-Architect, DES)  
may restrict allowed combinations further,  
but may not expand them.

---
End of AGENDA ENUM SPECIFICATION v1.2
