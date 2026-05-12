---
Version: 1.0
Status: Updated
Last-Updated: 2026-05-12
Owner: UI
---
# Coach Page

## Purpose
- Conversational coaching interface with active planning operations.

## UI elements
- Chat transcript
- Input box
- Pending operation banner when a preview exists
- Preview/apply workflow through coach tools
- Optional dev/debug panel for tool traces

## Notes
- Uses compaction and summary UI for long sessions.
- Preloads snapshot-first planning context where available.
- Supports bounded selected-week workout edits, scoped week replans, and report/feed-forward triggers.
- Mutations remain preview-first and require explicit confirmation through the chat tool surface.
