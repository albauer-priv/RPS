# RPS — Randonneur Performance System

RPS is a planning and feedback system for endurance athletes (with a focus on
long‑distance and brevet cycling). It turns athlete context + inputs into a
structured Season → Phase → Week → Workouts plan, and then evaluates progress
with data‑driven reports and feed‑forward guidance.

The primary interface is a **Streamlit UI**. The system is designed to be
deterministic, auditable, and safe: every planning step produces versioned
artifacts, and every decision is traceable to inputs and governance.

---

## 1) Was macht RPS?

**RPS hilft Athleten**, ihren Saisonverlauf und die Wochenplanung konsistent,
nachvollziehbar und robust zu gestalten — besonders bei langen Distanzen, wo
Durability (Leistungsstabilität unter Ermüdung) wichtiger ist als kurzfristige
Peak‑Leistung.

**Kernfunktionen**

- **Planung:** Season → Phase → Week → Workouts (mit klaren Regeln/Artefakt‑Ketten)
- **Feedback:** Performance Report + Feed Forward (was passt, was fehlt, was ist riskant?)
- **Transparenz:** Jede Entscheidung hinterlässt Artefakte mit Versionen und
  Referenzen auf Inputs/Upstream‑Quellen.
- **Sicherheit:** Readiness‑Checks verhindern, dass Schritte ohne gültige Inputs laufen.

---

## 2) Für wen ist das gedacht?

**Primär:** Athleten (Randonneur/Brevet, Ultra‑Distance, langfristige Ausdauerziele)  
**Sekundär:** Coaches, die planbare Governance und stabile Prozessketten brauchen  
**Ops/Engineering:** Für Installation/Deployment/Monitoring

---

## 3) Prinzipien (Planung & Feed Forward)

### 3.1 Planung (Season → Phase → Week)

- **Durability‑first:** Stabilität unter Belastung schlägt kurzfristigen Peak.
- **kJ‑first:** Mechanische Arbeit (kJ) ist die primäre Steuergröße.
- **Governance‑first:** KPI‑Profile + Policies definieren Grenzen, nicht Ad‑hoc‑Entscheidungen.
- **Deterministisch:** Gleiche Inputs → gleiche Artefakte.
- **Artefakt‑Kette:** Jeder Schritt hat definierte Inputs/Outputs; keine „impliziten“ Änderungen.

### 3.2 Feed Forward (Rückkopplung)

- **Nur abgeschlossene Wochen:** Feed‑Forward basiert auf vorhandenen Daten.
- **Keine Wochen‑Planung:** Feed‑Forward ist **nicht** der Planer, sondern die
  Diagnose‑/Anpassungsschicht.
- **Upstream‑Priorität:** Anpassungen erfolgen auf Season/Phase‑Ebene, nicht
  als spontane Wochen‑Eingriffe.
- **Transparenz:** Empfehlungen referenzieren konkrete Artefakte und KPI‑Signale.

---

## 4) Beispiel‑Workflow für Athleten (Kurzablauf)

1. **Profil ausfüllen:** Athlete Profile → About You & Goals  
2. **Events & Logistik erfassen:** Athlete Profile → Events, Logistics  
3. **Verfügbarkeit angeben:** Athlete Profile → Availability  
4. **KPI‑Profil wählen:** Athlete Profile → KPI Profile  
5. **Daten aktualisieren:** Analyse → Data & Metrics → Refresh Intervals Data  
6. **Plan Hub öffnen:** Readiness prüfen, fehlende Inputs ergänzen  
7. **Planung starten:** Plan Hub → Orchestrated Run  
8. **Woche prüfen:** Plan → Week  
9. **Workouts exportieren/posten:** Plan → Workouts  
10. **Rückkopplung:** Analyse → Report / Feed Forward

Für Details zu Readiness‑Regeln und Artefakt‑Ketten siehe:
- [doc/ui/flows.md](doc/ui/flows.md)
- [doc/overview/artefact_flow.md](doc/overview/artefact_flow.md)

---

## 5) Index — Wo finde ich was?

### Einstieg
- [doc/README.md](doc/README.md) — zentraler Dokumentations‑Index
- [doc/overview/system_overview.md](doc/overview/system_overview.md) — Systemüberblick
- [doc/overview/how_to_plan.md](doc/overview/how_to_plan.md) — Planungsablauf (konzeptionell)

### UI & Bedienlogik
- [doc/ui/ui_spec.md](doc/ui/ui_spec.md) — UI‑Struktur und Page‑Verantwortungen
- [doc/ui/flows.md](doc/ui/flows.md) — UI‑Aktionen + Flow‑Diagramme
- [doc/ui/streamlit_contract.md](doc/ui/streamlit_contract.md) — verbindliche UI‑Regeln
- [doc/ui/pages/](doc/ui/pages/) — Page‑Spezifikationen

### Architektur
- [doc/architecture/system_architecture.md](doc/architecture/system_architecture.md)
- [doc/architecture/workspace.md](doc/architecture/workspace.md)
- [doc/architecture/subsystems/](doc/architecture/subsystems/)
- [doc/architecture/deployment.md](doc/architecture/deployment.md)
- [doc/architecture/schema_versioning.md](doc/architecture/schema_versioning.md)

### Planung / Governance / Policies
- [doc/overview/artefact_flow.md](doc/overview/artefact_flow.md)
- [doc/overview/planning_principles.md](doc/overview/planning_principles.md)
- [doc/specs/](doc/specs/) (Features + Policies + Contracts)

### Runbooks & Ops
- [doc/runbooks/validation.md](doc/runbooks/validation.md)
- [doc/adr/README.md](doc/adr/README.md)

---

## 6) Installation & Deployment (Docker, kurz)

**Ziel:** RPS als UI‑only Streamlit‑App betreiben.

1. `.env` erstellen (siehe `.env.example`)
2. Docker Image bauen
3. Container starten

Beispiel (vereinfachtes Schema):

```bash
docker build -t rps .
docker run --env-file .env -p 8501:8501 rps
```

**Konfiguration:**  
Die Runtime hängt von LLM‑Keys, Modell‑Settings und Athlete‑ID ab. Siehe:
- [doc/architecture/deployment.md](doc/architecture/deployment.md)
- `.env.example`

---

## 7) Projektstruktur (kurz)

- `src/rps/` — Anwendungscode + UI
- `doc/` — Dokumentation (Überblick, UI, Architektur, Specs, Runbooks)
- `prompts/` — Agent‑Prompts
- `specs/` — Wissensquellen, Schemas, KPI‑Profile
- `runtime/` — Laufzeitdaten (gitignored)

---

## Lizenz

Siehe [LICENSE](LICENSE).
