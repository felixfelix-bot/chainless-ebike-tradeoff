# Crank alternator efficiency: what Mando and Schaeffler actually achieve

The question this document answers: **what is the efficiency of the crank
generator inside the Mando Footloose and the Schaeffler/Heinzmann Free Drive?**

Short answer: **the makers publish almost nothing**, and the one number in
circulation is widely misread. What can be established:

| System | Published efficiency | Provenance |
|---|---|---|
| Schaeffler Free Drive | "approximately 5% less efficient than chain drives" | company statement to Electrek, 2021-08-31 — a *system* claim, not a generator figure |
| CIXI PERS Standalone | "higher than 80%" | CIXI PERS KIT Catalog 2026, spec table |
| Mando Footloose | **none found** | no datasheet, press kit, or interview gives a figure |
| Tournon prototype (thesis) | 36% as built, 62–73% optimised | Tournon 2020 doctoral thesis, Université de Lyon / ESTACA |

## The "5%" claim is not what it looks like

A Schaeffler representative told Electrek the Free Drive is "approximately 5%
less efficient than chain drives", adding that the rider "would either need a
5% larger battery to get the same distance, or experience a 5% shorter range."

Read carefully, that is a claim about **battery range on an assisted bike**, not
about drivetrain efficiency. The two are not the same number, because on an
assisted bike most of the energy at the wheel comes from the battery, and only
the rider's contribution passes through the lossy conversion twice.

Modelling it (see `analysis/model.py --section crank`): with a chain at 97% and
a 250–400 W wheel load, a **5% higher battery draw corresponds to roughly
81–89% serial-path efficiency**, depending on how hard the rider is working —
not 91%.

| Rider input | Wheel power | Serial η implied by a 5% battery penalty |
|---|---|---|
| 60 W | 250 W | 81.0% |
| 100 W | 250 W | 89.3% |
| 150 W | 250 W | 93.5% |
| 60 W | 400 W | 68.5% |
| 100 W | 400 W | 81.8% |
| 150 W | 400 W | 88.5% |

So the 5% statement is consistent with a serial path anywhere from 68% to 93%
— it barely constrains the answer. It is a marketing-shaped number: true,
carefully worded, and uninformative.

Note also that the commenters under the original New Atlas piece independently
spotted the contradiction and worked out 36–64% for a two-machine chain, which
is much closer to the thesis result than to the press figure.

## What the numbers actually are

### CIXI PERS: the only honest datasheet

The CIXI PERS KIT Catalog 2026 lists, for the Standalone unit:

- Efficiency: **higher than 80%**
- 360 W continuous, 2000 W peak
- 185 Nm max torque, 100 rpm max, 48 V

This is the most forthcoming number from any chainless-drive vendor. It is still
a lower bound on a spec sheet, not a curve: no part-load data, no statement of
whether it includes the controller.

### Tournon: the real answer, from someone who built one

Edgar Tournon's 2020 doctoral thesis is the definitive study — a series-hybrid
bicycle **with supercapacitors**, which is almost exactly the design in this
repo's question. Findings:

- Minimum viable drivetrain efficiency: **61%** to match any chain bike in
  stop-and-go town riding; **70%** for hilly routes.
- A prototype built mostly from off-the-shelf parts simulated at **36%** on the
  hilly route — i.e. unusable.
- The best optimised design reached **73% on the flat** without stops, and
  **62% with a 50 m climb** — passing the town threshold, falling short of the
  70% hill target.
- On flat ground with no stops, a series hybrid is **never faster** than a chain
  bike, even at 100% efficiency, because of the ~5 W controller overhead.
- Supercapacitors vs batteries: a multi-criterion comparison plus **aging tests
  at equivalent energy throughput**, which is exactly the wear question raised
  in the original design discussion.

Tournon also states the system's own transmission efficiency in a public
comment: *"le rendement de transmission est plus faible et de l'ordre de 60 %
voire 70 % en régime stationnaire favorable"* — 60%, or 70% under favourable
steady-state conditions.

That maps to a generator around **80–86%** and a motor around **85–88%**, which
lands almost exactly on the 70.7% best-case figure this repo's model computes
from first principles for the direct-to-motor-bus topology.

## Reconciling everything

| Claim | Value | Consistent? |
|---|---|---|
| CIXI generator alone | >80% | yes |
| Best-case serial path (this repo) | 70.7% | yes |
| Tournon best optimised design, flat | 73% | yes |
| Tournon best optimised design, with hill | 62% | yes |
| Tournon off-the-shelf prototype | 36% | yes — bad part selection |
| Schaeffler "5% less efficient" | implies 68–93% | too vague to contradict anything |
| Commenter estimate (New Atlas) | 36–64% | pessimistic but in range |

The one figure that would be a genuine contradiction — a drivetrain at 91–95% —
is not what Schaeffler said, and nobody has published it.

## What this means for the design

1. **The generator is not 90%.** Best real parts reach ~85–88% at their design
   point and fall off outside it. A car alternator at bicycle power is far
   worse — 30–45%.
2. **No vendor publishes a generator efficiency curve.** Every number in
   circulation is either a bound, a system claim, or a thesis simulation. Treat
   all of them as ±5 points.
3. **The 70.7% in this repo's README is corroborated.** Independent modelling
   (Tournon) and independent measurement-adjacent work (the thesis prototype)
   land in the same 62–73% band.
4. **The supercapacitor question has been tested.** Tournon's thesis did the
   aging comparison at equivalent energy throughput — the exact experiment the
   original design discussion asked for. See the README for why the answer still
   comes out as "battery, with a small cap buffer".

## Sources

- Schaeffler press release, Eurobike 2021 (PDF, `ED_FDS_001_21_08_e`): 1:29
  cyclone gearbox, 250 W continuous, 1200 W peak, 48 V.
- Electrek, 2021-08-31: the "approximately 5% less efficient" statement and the
  5%-larger-battery gloss.
- New Atlas, 2021: reports the claim, plus reader comments deriving 36–64%.
- CIXI PERS KIT Catalog 2026: "Efficiency higher than 80%".
- Tournon, E. (2020). *Conception optimale d'un vélo à architecture hybride
  série et à base de supercondensateurs*. Doctoral thesis, Université de Lyon /
  ESTACA / Laboratoire Ampère. HAL: `tel-03120708`.
- Tournon, E., Venet, P., Barbedette, B., Lelièvre, A., Aubry, J., Sari, A.
  (2019). *Efficiency Comparison between Series Hybrid Bike and Traditional
  Bike*. EVER 2019. DOI: 10.1109/EVER.2019.8813618.
- Aubry, J., Barbedette, B. (2014). *Assessment of the interest of series
  hybridisation for a human-powered vehicle*. EJEE 17(5-6):419-438. Assumes 80%
  pedal-to-wheel for the series case; optimises a pedal generator reaching 96%
  at 80 rpm / 100 W with a 10:1 step-up.
- Fuchs, A. (2008). *Series Hybrid Drive-System: Advantages for Velomobiles*.
  Human Power eJournal 15. Reports 55–70% brushed generators in the first working
  models, and the 4.3 kg generator module.
