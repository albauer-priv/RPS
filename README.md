# RPS — Randonneur Performance System

RPS is a planning and feedback system for endurance athletes (with a focus on
long‑distance and brevet cycling). It turns athlete context + inputs into a
structured Season → Phase → Week → Workouts plan, and then evaluates progress
with data‑driven reports and feed‑forward guidance.

The primary interface is a **Streamlit UI**. The system is designed to be
deterministic, auditable, and safe: every planning step produces versioned
artifacts, and every decision is traceable to inputs and governance.

---

## 1) What does RPS do?

**RPS helps athletes** keep their season trajectory and weekly planning
consistent, traceable, and robust — especially for long distances where
durability (performance stability under fatigue) matters more than short‑term
peak performance.

**Core capabilities**

- **Planning:** Season → Phase → Week → Workouts (with explicit rules/artifact chains)
- **Feedback:** Performance Report + Feed Forward (what fits, what’s missing, what’s risky)
- **Transparency:** every decision produces versioned artifacts with references
  to inputs/upstream sources.
- **Safety:** readiness checks prevent steps from running without valid inputs.

---

## 2) Who is this for?

**Primary:** Athletes (Randonneur/Brevet, ultra‑distance, long‑term endurance goals)  
**Secondary:** Coaches who need predictable governance and stable process chains  
**Ops/Engineering:** Installation, deployment, monitoring

---

## 3) Principles (Planning & Feed Forward)

### 3.1 Planung (Season → Phase → Week)

- **Durability‑first:** stability under load beats short‑term peaks.
- **kJ‑first:** mechanical work (kJ) is the primary steering metric.
- **Governance‑first:** KPI profiles + policies define limits, not ad‑hoc decisions.
- **Deterministic:** same inputs → same artifacts.
- **Artifact chain:** every step has defined inputs/outputs; no “implicit” changes.

### 3.2 Feed Forward (feedback loop)

- **Completed weeks only:** Feed Forward relies on available data.
- **No weekly planning:** Feed Forward is **not** the planner, but the
  diagnosis/adjustment layer.
- **Upstream priority:** adjustments happen at Season/Phase level, not as
  ad‑hoc week edits.
- **Transparency:** recommendations reference concrete artifacts and KPI signals.

---

### 3.3 Foundations: Key Specs & Policies

Planning and Feed Forward are grounded in binding specifications and policies.
The most important building blocks:

- **Durability‑First Principles** — guiding principles for long‑distance planning and durability focus.  
  [specs/knowledge/_shared/sources/principles/principles_durability_first_cycling.md](specs/knowledge/_shared/sources/principles/principles_durability_first_cycling.md)
- **Load Estimation Spec** — defines how kJ‑based load is calculated and compared consistently.  
  [specs/knowledge/_shared/sources/specs/load_estimation_spec.md](specs/knowledge/_shared/sources/specs/load_estimation_spec.md)
- **Progressive Overload Policy** — binding rules for progression/deload on a kJ basis.  
  [specs/knowledge/_shared/sources/policies/progressive_overload_policy.md](specs/knowledge/_shared/sources/policies/progressive_overload_policy.md)
- **KPI Signal Effects Policy** — how KPI signals are allowed to affect planning decisions.  
  [specs/knowledge/_shared/sources/policies/kpi_signal_effects_policy.md](specs/knowledge/_shared/sources/policies/kpi_signal_effects_policy.md)
- **Workout Policy** — what workouts may/must contain, including limits on structure/progression.  
  [specs/knowledge/_shared/sources/policies/workout_policy.md](specs/knowledge/_shared/sources/policies/workout_policy.md)

Missing a core foundation? I would also recommend:
- **Traceability Spec** (artifact lineage/upstream references)  
- **File Naming Spec** (artifact names are binding for routing/validation)  
- **Season → Phase / Phase → Week Contracts** (binding handoff rules)
---

### 3.4 Traceability & Governance

RPS ensures planning steps are traceable and versioned.
These foundations govern **artifact lineage**, **naming conventions**, and
**binding handoffs** between planning stages:

- **Traceability Spec** — defines upstream references, run IDs, and artifact lineage.  
  [specs/knowledge/_shared/sources/specs/traceability_spec.md](specs/knowledge/_shared/sources/specs/traceability_spec.md)
- **File Naming Spec** — binding filenames for routing, validation, and linting.  
  [specs/knowledge/_shared/sources/specs/file_naming_spec.md](specs/knowledge/_shared/sources/specs/file_naming_spec.md)
- **Season → Phase Contract** — handoff rules between Season Planner and Phase Architect.  
  [specs/knowledge/_shared/sources/contracts/season__phase_contract.md](specs/knowledge/_shared/sources/contracts/season__phase_contract.md)
- **Phase → Week Contract** — handoff rules between Phase Architect and Week Planner.  
  [specs/knowledge/_shared/sources/contracts/phase__week_contract.md](specs/knowledge/_shared/sources/contracts/phase__week_contract.md)

---

## 4) Example Athlete Workflow (Short)

1. **Fill profile:** Athlete Profile → About You & Goals  
2. **Enter events & logistics:** Athlete Profile → Events, Logistics  
3. **Set availability:** Athlete Profile → Availability  
4. **Choose KPI profile:** Athlete Profile → KPI Profile  
5. **Refresh data:** Analyse → Data & Metrics → Refresh Intervals Data  
6. **Open Plan Hub:** check readiness, fix missing inputs  
7. **Start planning:** Plan Hub → Orchestrated Run  
8. **Review week:** Plan → Week  
9. **Export/post workouts:** Plan → Workouts  
10. **Feedback:** Analyse → Report / Feed Forward

For readiness rules and artifact chains, see:
- [doc/ui/flows.md](doc/ui/flows.md)
- [doc/overview/artefact_flow.md](doc/overview/artefact_flow.md)

---

## 5) Index — Where to find what

### Getting started
- [doc/README.md](doc/README.md) — documentation index
- [doc/overview/system_overview.md](doc/overview/system_overview.md) — system overview
- [doc/overview/how_to_plan.md](doc/overview/how_to_plan.md) — planning flow (conceptual)

### UI & behavior
- [doc/ui/ui_spec.md](doc/ui/ui_spec.md) — UI structure and page responsibilities
- [doc/ui/flows.md](doc/ui/flows.md) — UI‑Aktionen + Flow‑Diagramme
- [doc/ui/streamlit_contract.md](doc/ui/streamlit_contract.md) — verbindliche UI‑Regeln
- [doc/ui/pages/](doc/ui/pages/) — Page‑Spezifikationen

### Architektur
- [doc/architecture/system_architecture.md](doc/architecture/system_architecture.md)
- [doc/architecture/workspace.md](doc/architecture/workspace.md)
- [doc/architecture/subsystems/](doc/architecture/subsystems/)
- [doc/architecture/deployment.md](doc/architecture/deployment.md)
- [doc/architecture/schema_versioning.md](doc/architecture/schema_versioning.md)

### Planning / Governance / Policies
- [doc/overview/artefact_flow.md](doc/overview/artefact_flow.md)
- [doc/overview/planning_principles.md](doc/overview/planning_principles.md)
- [doc/specs/](doc/specs/) (Features + Policies + Contracts)

### Runbooks & Ops
- [doc/runbooks/validation.md](doc/runbooks/validation.md)
- [doc/adr/README.md](doc/adr/README.md)

---

## 6) Installation & Deployment (Docker, short)

**Goal:** run RPS as a UI‑only Streamlit app.

1. Create `.env` (see `.env.example`)
2. Build Docker image
3. Start container

Example (simplified):

```bash
docker build -t rps .
docker run --env-file .env -p 8501:8501 rps
```

**Configuration:**  
Runtime depends on LLM keys, model settings, and athlete ID. See:
- [doc/architecture/deployment.md](doc/architecture/deployment.md)
- `.env.example`

**GHCR publishing (optional):**  
A GitHub Actions workflow is included for GHCR publishing but left disabled by default.
Enable the `push` trigger in `.github/workflows/ghcr-image.yml` when you are ready to publish on each `main` commit.

---

## 7) Project structure (short)

- `src/rps/` — application code + UI
- `doc/` — documentation (overview, UI, architecture, specs, runbooks)
- `prompts/` — agent prompts
- `specs/` — knowledge sources, schemas, KPI profiles
- `runtime/` — runtime data (gitignored)

---

## License

See [LICENSE](LICENSE).
