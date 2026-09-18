# Fat Adaptation and Substrate Oxidation

Metabolic basis for ultra-endurance performance — the role of fat oxidation capacity, substrate
utilization at ultra pace, and the physiological rationale for aerobic-floor-first training.

This reference file supports `SKILL.md`; operational rules live there, not here.

---

## Why substrate oxidation matters for ultra/brevet

Ultra-distance events (≥ 200 km, > 8 hours) deplete carbohydrate stores multiple times over.
An athlete with high carbohydrate oxidation at event pace is permanently dependent on exogenous
carbohydrate — a supply-chain risk. An athlete with high fat oxidation at event pace conserves
glycogen, tolerates longer intervals without fueling, and maintains output when fueling logistics fail.

**At ultra event pace (55–70% VO2max)**: athletes with lower carbohydrate oxidation at 200W show
better durability profiles (Spragg, Leo, Swart 2023 — `dur_core_004`, PMID 35977108). CarbOx
at submaximal intensity is negatively correlated with durability score.

---

## The metabolic model: VLamax, VO2max, and FTP

The Mader/Weber metabolic model (used in Inscyd) frames FTP as a function of three values:

```
FTP ≈ f(VO2max, VLamax, gross mechanical efficiency)
```

- **VO2max** — aerobic ceiling; upper bound on oxygen delivery and utilization
- **VLamax** — maximal rate of lactate production per unit time; proxy for glycolytic flux;
  higher VLamax → more carbohydrates burned at any given intensity → lower fat oxidation
- **Gross mechanical efficiency** — power output per unit metabolic cost; relatively stable
  in trained athletes

For ultra/brevet: target **high VO2max + low VLamax**.

| Profile | FTP | Fat oxidation | Durability | Ultra suitability |
|---|---|---|---|---|
| High VO2max + low VLamax | High | High | High | Excellent |
| High VO2max + high VLamax | High | Low | Low | Poor — burns carbs, fades |
| Low VO2max + low VLamax | Moderate | High | Moderate | OK for shorter ultra |
| Low VO2max + high VLamax | Low | Low | Low | Not suitable |

The ultra cycling goal is the top-left cell: aerobic capacity + metabolic efficiency.

---

## How Base-phase training shapes the metabolic profile

High-volume low-intensity training (Z1, below VT1) over ≥ 8–12 weeks produces:

- Mitochondrial biogenesis and increased mitochondrial density
- Upregulation of fat oxidation enzymes (β-oxidation pathway)
- Shift of crossover point (the exercise intensity at which fat and carbohydrate oxidation
  are equal) toward higher absolute power outputs — athletes burn fat at intensities that
  previously required carbohydrates
- VLamax reduction — with minimal glycolytic stimulus, the glycolytic enzyme pool adapts
  downward; VLamax falls; CarbOx at submaximal intensity falls
- VT1 power increases — the threshold at which the athlete needs carbohydrates rises

The practical effect: the same absolute watts (ultra event pace) requires less carbohydrate.

---

## What raises VLamax (to avoid in Base phase)

VLamax is raised by repeated high-glycolytic loading (using intervals.icu zone notation):

- Short-duration high-intensity intervals (Z5 VO2max 105–120% FTP, Z6 Anaerobic 120–150% FTP,
  Z7 Neuromuscular sprints) — any work that repeatedly maxes glycolytic flux
- High-power sprint bursts
- Repeated threshold/FTP efforts (Z4, 90–105% FTP) without sufficient Z2 Endurance base to
  buffer the glycolytic demand

In RPS domain terms: `VO2MAX` intervals and repeated `THRESHOLD` density without `ENDURANCE`
foundation both raise VLamax.

For ultra athletes in Base phase: Z3/Z4/Z5 work raises VLamax and competes against the
fat-adaptation signal. This is why Z3+ is strictly bounded in Base phase of `SKILL.md`.

---

## Periodization implications

**Base phase**: maximize time below VT1 → lower VLamax, build fat oxidation base

**Build phase**: fat oxidation is protected; add preload + hard-later sessions that stress
durability without erasing the metabolic adaptation (sessions end at Z2/Z3, not full Z4/Z5 intervals)

**Peak/Taper**: volume drops, intensity maintained; metabolic profile is stable — no point
introducing fat-adaptation work in taper; the adaptation was built in Base

---

## Quantitative reference: fat oxidation rates in cyclists

Typical maximal fat oxidation rates in trained cyclists (from literature):

| Level | MFO (g/min) | Power at MFO | % VO2max at MFO |
|---|---|---|---|
| Well-trained recreational | 0.5–0.8 | 150–200W | 45–55% |
| Trained / amateur competitive | 0.8–1.2 | 200–280W | 50–60% |
| Professional / ultra-adapted | 1.2–2.0 | 280–360W+ | 55–65% |

Ultra event pace for most athletes falls in the 55–70% VO2max range. An athlete whose fat
oxidation is maximized at 45% VO2max is already glycogen-dependent at event pace. An ultra-adapted
athlete's peak fat oxidation falls squarely within event-pace range.

Training time below VT1 shifts this curve rightward — peak fat oxidation occurs at higher
absolute and relative intensities.

---

## Relationship to durability

The link between fat oxidation and durability is mediated by substrate availability:

- High-CarbOx athlete under fatigue: glycogen depleted faster → earlier reliance on carbohydrate
  supplementation → risk of GI distress, bonk, RPE spike → power decline
- High-FatOx athlete under fatigue: glycogen conserved → carbohydrate supplement extends working
  capacity rather than compensating for deficit → power maintained

`dur_core_004` (Spragg, Leo, Swart 2023): CarbOx at 200W is **negatively correlated** with
durability score in professional cyclists. Durability is at least partly a metabolic property —
it can be trained through the same aerobic-floor-first approach that builds fat oxidation.

---

## Evidence cross-references

| id | source | relevance |
|---|---|---|
| `dur_core_004` | Spragg, Leo, Swart 2023 (PMID 35977108) | CarbOx negatively correlated with durability; FatOx and durability linked |
| `ult_core_001` | Spragg, Leo, Swart 2023 (PMID 35239466) | Training time below VT1 → durability improvement |
| `ult_core_002` | Mateo-March, Leo et al. 2024 (PMID 38604818) | Work above CP impairs more than kJ-matched below CP |
| `ult_applied_001` | Kinzlbauer 2024 (Sitzfleisch Podcast #154) | Practitioner: metabolic efficiency as first pillar of prepared state |

All in `references/ultra_cycling_evidence.md`.
