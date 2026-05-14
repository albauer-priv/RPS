# Per-Workout Load Math

Binding math concepts:
- derive representative session intensity from parsed segments
- clamp raw segment intensities before power weighting
- compute raw mechanical kJ from FTP, representative intensity, and duration
- normalize governance load through athlete-aware IF reference and alpha exponent
- round only at output boundaries

Fallback rules:
- if no parseable segments exist, use IF-direct fallback by canonical domain default
- zero-duration sessions produce zero outputs
