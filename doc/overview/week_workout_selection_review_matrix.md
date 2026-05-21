---
Version: 1.0
Status: Implemented
Last-Updated: 2026-05-21
Owner: Planning / Workouts
---
# Week Workout Selection Review Matrix

Diese Matrix ist für fachliches Review gedacht. Sie zeigt nicht die gesamte Scoring-Logik, sondern die beabsichtigten **sinnvollen Wochenkombinationen** und die wichtigsten **Vermeidungsregeln** pro Kontext.

Leseregeln:

* `Soll` = primär gewünschte Kombination
* `Kann` = legal und oft sinnvoll
* `Nur wenn` = nur unter zusätzlicher Bedingung
* `Vermeiden` = formal evtl. legal, methodisch aber unerwünscht

## Kurzlegende

| Kürzel | Bedeutung |
|---|---|
| `Z2 Anchor` | `ENDURANCE_LONG_STEADY` |
| `Tempo Classic` | `TEMPO_CLASSIC` |
| `Tempo Steady` | `TEMPO_STEADY_BREVET` |
| `Tempo O/U` | `TEMPO_OVER_UNDER` |
| `SST Classic` | `SWEET_SPOT_CLASSIC` |
| `SST Extensive` | `SWEET_SPOT_EXTENSIVE` |
| `K3` | `K3_CLASSIC` |
| `Fatigue Finish` | `ENDURANCE_FATIGUE_FINISH` |
| `Pre-Fatigue Finish` | `ENDURANCE_PREFATIGUE_FINISH` |
| `Threshold` | `THRESHOLD_CLASSIC` |
| `VO2 30/15` | `VO2_30_15` |
| `VO2 40/20` | `VO2_40_20` |
| `VO2 20/10` | `VO2_20_10` |
| `VO2 Long` | `VO2_LONG_INTERVALS` |

## Phase-Intent Review Matrix

| Phase Intent / Week Role | Soll | Kann | Nur wenn | Vermeiden | Review-Fokus |
|---|---|---|---|---|---|
| `shortened_re_entry` / `SHORTENED_RE_ENTRY` | `1x Tempo Classic + Z2 Anchor + Endurance Support` | `Tempo Classic + SST Classic + Z2 Anchor`; `Tempo Classic + K3 + Z2 Anchor` falls K3 legal | `Tempo Classic + Tempo Classic(damped) + Z2 Anchor` nur wenn keine legale differenzierte Alternative bleibt | `2x identisches oberes Tempo` | Re-Entry konservativ, Monotonie vermeiden, Long Z2 schützen |
| `general_base` / `SHORTENED_CONSOLIDATION` | `Tempo Classic + differenzierter 2. moderater Quality-Reiz + Z2 Anchor` | `Tempo Classic + SST Classic + Z2 Anchor` | `Tempo Classic + K3 + Z2 Anchor` nur wenn K3 effektiv erlaubt ist | `2x dieselbe Quality-Struktur ohne Mehrwert` | Stabilisieren ohne unnötige Härtedichte |
| `general_base` / `*` | `Tempo Classic + Z2 Anchor` | `SST Classic + Z2 Anchor`, `K3 + Z2 Anchor` | `2. Quality-Reiz` nur wenn Quality-Cap und Wochenlast es tragen | `VO2/Threshold ohne passenden Intent` | Basis stabil, Progression konservativ |
| `aerobic_base` / `*` | `Z2 Anchor + Endurance Support` | `Tempo Classic + Z2 Anchor` | `SST Classic` nur moderat und nur wenn Kontinuität stabil ist | `VO2/Threshold` | Aerobe Basis und niedrige Risikodichte priorisieren |
| `strength_endurance_base` / `*` | `Tempo Classic + K3 + Z2 Anchor` | `K3 + Z2 Anchor`, `Tempo Classic + Z2 Anchor` | `SST Classic` nur wenn muskuläre Last tragbar bleibt | `VO2-lastige Mischwochen` | Torque/Struktur robust aufbauen |
| `sweet_spot_base` / `*` | `SST Classic + Z2 Anchor` | `Tempo Classic + SST Classic + Z2 Anchor` | `K3` nur wenn strukturell gewollt und K3 legal ist | `SST Extensive als Default` | Nachhaltige Subthreshold-Kapazität ohne Build-Dichte |
| `durability_build` / `*` | `Tempo Steady + Fatigue Finish + Z2 Anchor` | `Tempo Steady + Pre-Fatigue Finish + Z2 Anchor` | `Tempo Steady + K3 + Z2 Anchor` nur wenn strukturell gewollt und Modalität erlaubt | `zu viel klassische Indoor-Tempo-Monotonie ohne Durability-Logik` | Hard-late / durability-spezifische Formate bevorzugen |
| `specificity_build` / `*` | `Tempo Steady + Tempo O/U + Z2 Anchor` | `Tempo O/U + SST Extensive + Z2 Anchor` | kurzer `VO2`-Erhaltungsreiz oder abgeschlossener `VO2`-Mikroblock nur wenn Phase/Guardrails es wirklich tragen | `breite Mischwoche aus VO2 + SST + Tempo + K3` | Spezifität rauf, aber Struktur bleibt fokussiert |
| `vo2_build` / `*` | `VO2 30/15 oder 40/20 + Z2 Anchor` | `VO2 Long + Z2 Anchor` | `2. harter Reiz` nur wenn Budget klar frei ist | `gleichzeitig VO2 + Threshold + SST + K3` | VO2 als klarer Hauptreiz, nicht als Mischwoche |
| `threshold_build` / `*` | `Threshold Classic + Z2 Anchor` | `Tempo O/U + Z2 Anchor` | `SST Classic` nur als Support, nicht als zweiter Hauptreiz | `VO2 + Threshold + SST` gleichzeitig | Sustained Power klar fokussieren |
| `sst_build` / `*` | `SST Extensive + Z2 Anchor` | `SST Classic + Tempo Steady + Z2 Anchor` nur wenn `SST Classic` moderat bleibt und `Tempo Steady` nicht zusätzlich extensive wird | `Threshold` nur wenn Struktur es explizit trägt | `SST als Lösung für jede Woche` | Extensive Subthreshold-Arbeit dosiert halten |
| `vlamax_lowering` / `*` | `Z2 Anchor + Tempo/SST dosiert` | `Tempo Classic + Z2 Anchor`, `SST Classic + Z2 Anchor` | `Threshold` nur sparsam und nur wenn ökonomisch sinnvoll | `VO2/anaerobe Mischdichte` | Glykolytische Last senken, Effizienz erhöhen |
| `peak_sharpening` / `*` | `Tempo Steady + Z2 Anchor` | `schmale spezifische Quality + Z2 Anchor` | `zweiter Quality-Reiz` nur wenn Peak-Logik das ausdrücklich trägt | `Build-artige Dichte oder breite Reizmischung` | Dichte senken, Spezifität schärfen |
| `taper_freshening` / `*` | `Z2 Anchor + kurze Aktivierung` | `kurzer Tempo-Steady Primer + Z2` | `kurzer VO2-Opener` nur wenn bewährt und klar begründet | `neue Lastblöcke oder große TiZ-Akkumulation` | Ermüdung abbauen, Form erhalten |
| `race_execution` / `*` | `Event + Recovery + minimale Supporttage` | `kurze Openers` | `zusätzliche Quality` nur wenn direkt an Event-Logik gebunden | `Build-artige Zusatzlast` | Event-Woche ausführen, nicht weiter aufbauen |

## Kombinationen nach Hauptreiz

| Hauptreiz | Gute Folge / Ergänzung | Nur wenn | Vermeiden |
|---|---|---|---|
| `Tempo Classic` | `SST Classic`, `K3`, `Z2 Anchor` | `Tempo Classic` erneut nur gedämpft in Re-Entry-Fallback | `Tempo Classic + Tempo Classic` als Standardlösung |
| `Tempo Steady` | `Z2 Anchor`, `Fatigue Finish`, `Tempo O/U` | `K3` nur bei legaler Modalität | `Tempo Steady` mit unnötig viel zusätzlicher moderater Dichte |
| `SST Classic` | `Tempo Classic`, `Z2 Anchor` | `K3` nur wenn lokale muskuläre Last tragbar ist | `SST + SST + K3` in enger Woche |
| `SST Extensive` | `Z2 Anchor`, `Tempo Steady` | `2. Quality-Reiz` nur bei ausreichend Budget | `SST Extensive` plus weitere große moderate Blöcke ohne Zweck |
| `K3` | `Tempo Classic`, `Z2 Anchor` | nur wenn effektive Modalität `K3` ist | K3 als „gratis“ Zusatz |
| `Threshold` | `Z2 Anchor`, ruhige Endurance-Supporttage | nur Build-/spezifische Kontexte | Threshold in Re-Entry/Base |
| `VO2` | `Z2 Anchor`, ruhiger Endurance-Support | nur wenn VO2 legal und Quality-Budget frei ist | VO2 zusammen mit großer SST- und K3-Dichte |

## Operationalisierte Dämpfung für Re-Entry-Fallbacks

Wenn `Tempo Classic(damped)` als Fallback gewählt wird, sollte das im Audit und im Workout klar erkennbar sein.

| Dämpfungshebel | Erwartete Form |
|---|---|
| weniger TiZ | z. B. `3x15` statt `4x15` |
| niedrigere obere Zielrange | z. B. `80-85%` statt `82-88%` |
| weniger Wiederholungen | z. B. 3 statt 4 Blöcke |
| anderer Charakter bei Bedarf | `Endurance Support + kurzer Tempo-Finish` statt voller zweiter Tempo-Kopie |
| Audit-Markierung | Warning / Reason-Code für gedämpften Duplicate-Fallback |

## Sweet Spot in Re-Entry und Base

`SST Classic` ist in Re-Entry/Base nur als moderater zweiter Reiz sinnvoll, nicht als aggressive Extensive-Lösung.

| SST-Variante | Re-Entry / Base |
|---|---|
| `SST Classic` kurz/moderat (`3x12`, `3x15`, `2x20`) | Kann |
| `SST Extensive` | eher nicht |
| sehr große TiZ-Blöcke (`3x25`, `2x40`) | Vermeiden |

## Build-Subtypen

Die generische Build-Logik ist nur die Oberkategorie. Für fachliches Review sollte nach Build-Subtyp gelesen werden.

| Build-Subtyp | Soll | Kann | Vermeiden |
|---|---|---|---|
| `vo2_build` | `VO2 30/15 oder 40/20 + Z2 Anchor` | `VO2 Long + Z2 Anchor` | breite Zusatzmischung mit SST + K3 + weiterem Tempo |
| `threshold_build` | `Threshold Classic + Z2 Anchor` | `Tempo O/U + Z2 Anchor` | Threshold plus weitere große Moderate-Dichte |
| `sst_build` | `SST Extensive + Z2 Anchor` | `SST Classic + Tempo Steady + Z2 Anchor`, nur wenn `SST Classic` moderat bleibt und `Tempo Steady` nicht zusätzlich extensive wird | SST als Lösung für jede Woche |
| `durability_build` | `Tempo Steady + Fatigue Finish + Z2 Anchor` | `Pre-Fatigue Finish + Z2 Anchor` | generische monotone Tempo-Dopplung |
| `specificity_build` | `Tempo Steady + Tempo O/U + Z2 Anchor` | gezielte VO2-Blöcke, wenn legal | unspezifische breite Reizmischung |

## VO2-Unterteilung

`VO2` sollte im Review nicht als ein einziger Block verstanden werden.

| VO2-Typ | Bewertung |
|---|---|
| `VO2 30/15` | bevorzugt |
| `VO2 40/20` | bevorzugt / Kann |
| `VO2 Long` | nur wenn gezielt gewollt |
| `VO2 20/10` | Spezialfall, eher nicht als Default |

## Klare Review-Ampel für Quality-Dichte

| Wochenmuster | Bewertung | Begründung |
|---|---|---|
| `1x Quality + Z2 Anchor + lockere Supporttage` | Soll | robust, auditierbar, meist guter Default |
| `2x differenzierte Quality + Z2 Anchor` | Kann | gut, wenn Phase-Intent und Quality-Cap passen |
| `2x identische Quality` | Nur wenn | nur als expliziter Fallback mit dokumentierter Dämpfung |
| `VO2 + SST + Tempo + K3` | Vermeiden | zu breite Reizdichte |
| `K3 zusätzlich auf bereits dichte Woche` | Vermeiden | K3 zählt als echter Reiz |

## Modalitäts-Review

| Fall | Regel |
|---|---|
| `PHASE_GUARDRAILS` erlaubt `K3`, `PHASE_STRUCTURE` aber nur `NONE` | `K3` blocken, bis Schnittmenge / Regel geklärt ist |
| effektive Modalitätsschnittmenge enthält `K3` | `K3` darf als Kandidat bewertet werden |
| Modalitätskonflikt | Warning muss im Audit auftauchen |

## Was Externe im Audit prüfen sollen

| Prüffrage | Erwartung |
|---|---|
| Gibt es für den 2. Quality-Tag eine differenzierte Alternative? | Wenn ja, sollte sie meist vor identischer Wiederholung gewinnen |
| Wurde `K3` nur gewählt, wenn Modalität legal war? | Ja |
| Ist der Z2-Anker in Re-Entry / Durability geschützt? | Ja |
| Ist die gewählte Kombination mit Phase Intent und Week Role plausibel? | Ja |
| Ist ein Fallback als Fallback erkennbar? | Ja, über Rule-ID, Score, Warning, Selection Reason |
| Ist ein Re-Entry-Tempo-Duplikat sichtbar gedämpft? | Ja, sonst Review-Warning |

## Abgrenzung zur Dosislogik

Diese Matrix entscheidet **Kombinationen und Wochenmuster**, nicht die konkrete **TiZ-Dosis** eines einzelnen Reizes.

Für die tatsächliche Größe eines Reizes müssen zusätzlich die separaten Workout-Cap- und Dosisregeln geprüft werden, insbesondere:

* TiZ-/On-Time-Caps pro Reiz
* Standard- vs. Hard-Caps
* phase-spezifische Dämpfung
* Sequencing und Abstand zwischen Reizen
