# Season Backplanning and Event Priority

Use event priority as the fixed anchor for season architecture.

## Event classes
- `A`: true peak objective; deserves full peak-window and taper logic
- `B`: important but subordinate; may shape local structure without stealing the primary peak
- `C`: low-priority participation or training event; no taper, no structural change, and no recovery debt carried forward

## Event state labels
- use explicit labels: `A1`, `A2`, `A_block`, `Peak_Window_1`, `B_support_event`, `C_training_event`
- avoid ambiguous terms like "important race" or "key event" unless the priority class is explicit

## Priority rules
- when A and B conflict, protect the A event
- when two A events exist, choose an explicit multi-peak strategy rather than blending them implicitly
- multiple A events need either separate macrocycles with recovery/rebuild space or one explicit A-event cluster/peak window
- do not let C events consume taper or overload budget

## Backplanning order
1. lock event anchors and peak windows
2. assign taper windows backward from A events
3. place build and base blocks to support those anchors
4. only then resolve local shortening or trade-offs
