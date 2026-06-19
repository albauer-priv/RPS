# 30 — UI and Streamlit

## Page discipline

- Page scripts stay thin.
- UI delegates to orchestrator/service helpers.
- UI pages must not call agents directly.

## Streamlit rerun hygiene

- Initialize session state before rendering.
- Avoid expensive module import side effects.
- Never call `st.*` from worker threads.
- Gate repeated banners / toasts with state.

## Layout conventions

- Prefer: Title → Athlete/context → Status hints → Actions → Main content → Details/debug.
- Use containers, columns, forms, and expanders deliberately.
- Keep page scripts small and move logic into helpers/services.

## Charts

Use `st.plotly_chart(...)` only.

Do not use:

- `st.line_chart`
- `st.bar_chart`
- `st.area_chart`
- `st.altair_chart`

## Chat UI

- Use `st.chat_message` + `st.chat_input`.
- Keep chat history in `st.session_state`.
- Show traces/reasoning only in bounded detail views.

## UI test rule

For UI changes, add or update `streamlit.testing.v1.AppTest` coverage under `tests/`.