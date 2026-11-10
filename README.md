# chainless-ebike-tradeoff

A quantitative evaluation of a chainless (series-hybrid) bicycle drivetrain: pedal a
generator, buffer the electricity, drive a hub motor. Is it better than a chain, and
should the buffer be supercapacitors, a battery, or both?

**Short answer: no on efficiency, and batteries on storage.** The serial path costs
roughly 59 W out of a 200 W rider input versus 8 W for a chain — the rider is
effectively 1.36× weaker. Supercapacitors cost ~170× more per Wh and are ~48× heavier
per Wh than LiFePO4 for a job that only ever needs a few Wh of buffering.

The chainless concept is still defensible — for **packaging**, not efficiency. It has
been shipped twice (Mando Footloose, Schaeffler/Heinzmann Free Drive) and remained
niche both times.

## Why this repo exists

The idea rests on a premise that half-checks out. Hub motors really are ~90%
efficient. Generators at bicycle scale are not: hub dynamos run 45–65% and car
alternators 47–65% at peak, far worse at the low part-load a cyclist imposes. Chained
against a chain at 95–98%, the serial topology loses before it is even built.

Rather than assert that, this repo makes it computable and keeps every component
figure with its provenance so estimates are never mistaken for measurements.

## Quick start

```bash
python3 analysis/model.py                 # full report
python3 analysis/model.py --section regen # one section
python3 -m unittest discover -s tests -v  # 24 tests
```

No dependencies beyond the Python 3.11 standard library.

## What the model says

### Drivetrain efficiency at 200 W rider input

| Path | Efficiency | At wheel | Lost |
|---|---|---|---|
| Chain, 2 stages | 96.0% | 192 W | 8 W |
| Chain, 3 stages | 94.1% | 188 W | 12 W |
| Car alternator (part load) + hub | 30.5% | 61 W | 139 W |
| Car alternator (peak) + hub | 44.2% | 88 W | 112 W |
| Bicycle hub dynamo + hub | 41.8% | 84 W | 116 W |
| Hub motor as PMG + hub | 69.1% | 138 W | 62 W |
| Axial-flux PMG + hub | 70.7% | 141 W | 59 W |

The best-case serial path is 70.7%, stage by stage: PMG 88% → rectifier 98% → bus 97%
→ controller 96% → hub motor 88%. To merely **match** a 2-stage chain, the generator
plus downstream electronics would need to reach **119.6%** — off the table.

### Regen from a stop is negligible; regen from a hill is not

| Speed | KE | Recovered |
|---|---|---|
| 15 km/h | 868 J (0.24 Wh) | 0.20 Wh |
| 20 km/h | 1543 J (0.43 Wh) | 0.36 Wh |
| 30 km/h | 3472 J (0.97 Wh) | 0.82 Wh |

One stop from 20 km/h returns 0.36 Wh — **0.038%** of a 960 Wh pack. At 15 Wh/km that
is **41 traffic lights per kilometre** of range. A 300 m descent yields **82 Wh**, two
orders of magnitude more. Regen is a hill and brake-wear feature.

### Storage, on the market

| Storage | Wh | kg | Wh/kg | Price/Wh |
|---|---|---|---|---|
| Maxwell 48 V/165 F module | 53 | 14.2 | 3.7 | €33.68 |
| 16 V 500 F module | 18 | 1.4 | 12.7 | $15.73 |
| Maxwell 3000 F cell | 3 | 0.5 | 6.0 | $13.16 |
| 48 V 20 Ah LiFePO4 | 960 | 5.4 | 177.8 | $0.20 |

Supercaps are **48× heavier per Wh** and **170× more expensive per Wh** at module
level. Bare cells close some of the cost gap and none of the mass gap. They also sag
as a square law (half the energy sits below 70% of full voltage), so they need a
wide-input controller or another conversion stage.

The wear argument does not survive contact with the duty cycle either: at ~0.36 Wh
recovered per stop and a few hundred Wh/day, a 960 Wh pack runs ~0.3 cycles/day.
Calendar aging and water ingress kill it long before cycle life does.

### Cold start: the alternator question answers itself

A car alternator is **wound-field**: it needs 2–4 A of field current and a battery as
its voltage reference. Caps alone give you unregulated output and no useful
regulation. Permanent-magnet machines self-excite — turn them, voltage appears — so a
caps-only build is electrically possible with a PMG and impractical with an
alternator. Either way you want a small keep-alive cell for logic and pre-charge state.

## Recommended build

- **Generator:** 250 W direct-drive hub motor run as a PMG, belt step-up ~3:1 from cranks
  (reuses the controller's regen mode; ~85–86% rather than a dynamo's ~50%)
- **Energy:** 13S Li-ion 10–20 Ah, or 16S LiFePO4 if cycle life beats cold-weather charging
- **Caps:** 5–15 Wh in parallel on the bus, sized in **watt-seconds for ripple and regen
  surge**, not as energy storage
- **Regen:** DD hub rear, torque-controlled, caps absorbing the surge so the BMS never
  trips on charge current

## Decision, stated as a testable claim

> A serial electric drivetrain cannot beat a chain on efficiency at bicycle power
> levels, because the generator alone consumes more than the chain's entire loss.

Falsify it by measuring, not arguing: crank power meter, a 250 W hub as a generator
into a known load, wheel power measured on a trainer at 200 W rider input. Expected
~141 W (serial) vs ~192 W (chain). That is a Saturday and about €300.

## What is measured vs. modelled

`data/components.json` tags every figure:

- `literature` — quoted from the named source (chain efficiency, dynamo drag tests,
  alternator efficiency studies)
- `datasheet` — from a manufacturer datasheet (supercap energy/mass, pack mass)
- `estimate` — engineering judgement, uncertain, **do not cite as fact**

Nothing in this repo is dyno-measured by its author. The efficiencies tagged
`estimate` are the weakest link in the chain of reasoning and the tests only pin them
to plausible bands, not to truth. The physical relations (kinetic energy, capacitance,
gravitational potential) are exact and tested against hand calculations.

Prices are street prices observed in November 2026 and will drift.

## Prior art

- **Mando Footloose** (2015) — crank alternator → 36 V battery → 250 W hub. Production
  reached, commercial failure.
- **Schaeffler / Heinzmann "Free Drive"** (2021) — chainless pedal-by-wire, aimed at
  cargo bikes and velomobiles. Structurally the same tradeoff documented here.

Both route pedal power **through the battery**, which the model shows costs another
~1.5 points versus feeding the motor bus directly.

## Layout

```
analysis/model.py        the model and report
data/components.json     component figures with provenance tags
docs/model-output.txt    captured output of the full report
tests/test_model.py      24 tests: physics, sizing, data sanity
```

## Licence

MIT — see `LICENSE`.
