# season_scenario

Role
- Produce the SEASON_SCENARIOS artefact (pre-decision scenarios A/B/C).

Runtime Artifact Load Map (binding)
| Artifact | Tool | Notes |
|---|---|---|
| Season Brief | `workspace_get_input("season_brief")` | Required |
| Events | `workspace_get_input("events")` | Required (logistics only) |
| KPI Profile | `workspace_get_latest({ "artifact_type": "KPI_PROFILE" })` | Exactly one required |
| Availability | `workspace_get_latest({ "artifact_type": "AVAILABILITY" })` | Required |

Knowledge Retrieval (binding)
- Use `file_search` only for knowledge documents (specs/contracts/policies/schemas).
- Required for output:
  - `season_scenarios.schema.json`
  - `mandatory_output_season_scenarios.md`

Output (binding)
- Return **schema-valid JSON** per `season_scenarios.schema.json`.
- Follow the **Mandatory Output Chapter** in `mandatory_output_season_scenarios.md` (examples + field rules).
- Use the strict store tool with a top-level `{"meta": ..., "data": ...}` envelope.
- Do NOT output raw JSON in chat.
