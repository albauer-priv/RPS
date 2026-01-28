# Streamlit UI (RPS)

Minimal browser UI that wraps common RPS flows (preflight, macro, plan-week)
behind a chat-style control surface.

## Run

From repo root:

```bash
PYTHONPATH=src python3.14 -m streamlit run src/rps/ui/streamlit_app.py
```

## Notes

- Uses the same `.env` as the CLI (`OPENAI_API_KEY` is required).
- Preflight runs automatically at startup; on success the UI enters core mode.
- Base state is stored in `st.session_state["rps_state"]`.
- The sidebar provides explicit buttons; the chat input supports commands like:
  - `coach` (enter coach mode; use `:quit` to leave coach mode)
  - `parse availability`
  - `parse intervals`
  - `scenarios`
  - `select scenario`
  - `season plan`
  - `plan week`
  - `show macro`
