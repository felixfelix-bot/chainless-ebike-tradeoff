#!/usr/bin/env python3
"""
chainless-ebike-tradeoff: the numbers behind a chainless (series-hybrid) bicycle.

Everything here is closed-form physics plus component figures loaded from
data/components.json. No measured dyno data lives in this repo yet -- see
README "What is measured vs. modelled".

Usage:
    python3 analysis/model.py            # full report
    python3 analysis/model.py --section drivetrain
"""

from __future__ import annotations

import argparse
import json
import math
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
COMPONENTS = os.path.join(ROOT, "data", "components.json")

G = 9.81  # m/s^2


# --------------------------------------------------------------------------
# loading
# --------------------------------------------------------------------------

def load_components(path: str = COMPONENTS) -> dict:
    with open(path, "r", encoding="utf-8") as fh:
        data = json.load(fh)
    if "generators" not in data or "storage" not in data:
        raise ValueError("components.json is missing required sections")
    return data


def by_id(comp: dict, section: str, cid: str) -> dict:
    for item in comp[section]:
        if item["id"] == cid:
            return item
    raise KeyError(f"{section}/{cid} not found in components.json")


# --------------------------------------------------------------------------
# drivetrain efficiency
# --------------------------------------------------------------------------

def chain_efficiency(comp: dict, stages: int = 2) -> float:
    per_stage = by_id(comp, "mechanical", "chain_per_stage")["efficiency"]
    return per_stage ** stages


SERIAL_PATH = [
    ("generators", "axial_flux_pmg"),
    ("electronics", "rectifier_3ph"),
    ("electronics", "dc_bus"),
    ("electronics", "motor_controller"),
    ("motors", "hub_motor_partload"),
]

# Same components, but pedal power goes through the pack (Mando/Schaeffler style)
# rather than feeding the motor bus directly.
SERIAL_PATH_BATTERY = [
    ("generators", "axial_flux_pmg"),
    ("electronics", "rectifier_3ph"),
    ("electronics", "battery_roundtrip"),
    ("electronics", "motor_controller"),
    ("motors", "hub_motor_partload"),
]


def serial_efficiency(comp: dict, path=SERIAL_PATH) -> tuple[float, list[tuple[str, float, float]]]:
    """Return (total efficiency, [(label, stage_eta, cumulative_eta), ...])."""
    total = 1.0
    rows = []
    for section, cid in path:
        item = by_id(comp, section, cid)
        total *= item["efficiency"]
        rows.append((item["label"], item["efficiency"], total))
    return total, rows


def serial_efficiency_with(comp: dict, generator_id: str, extra=()) -> float:
    path = [("generators", generator_id)] + SERIAL_PATH[1:] + list(extra)
    return serial_efficiency(comp, path)[0]


def break_even_generator_efficiency(comp: dict, stages: int = 2) -> float:
    """Generator efficiency at which the serial path merely matches a chain."""
    chain = chain_efficiency(comp, stages)
    rest = serial_efficiency(comp)[0] / by_id(comp, "generators", "axial_flux_pmg")["efficiency"]
    return chain / rest


# --------------------------------------------------------------------------
# energy, regen, range
# --------------------------------------------------------------------------

def kinetic_energy_j(mass_kg: float, speed_kmh: float) -> float:
    v = speed_kmh / 3.6
    return 0.5 * mass_kg * v * v


def recoverable_stop_j(comp: dict, speed_kmh: float, mass_kg: float | None = None) -> float:
    """Energy actually returned to the bus when braking from speed to 0."""
    mass = mass_kg if mass_kg is not None else comp["vehicle"]["mass_kg"]
    ke = kinetic_energy_j(mass, speed_kmh)
    motor = by_id(comp, "motors", "hub_motor_partload")["efficiency"]
    controller = by_id(comp, "electronics", "motor_controller")["efficiency"]
    return ke * motor * controller


def descent_energy_j(mass_kg: float, drop_m: float) -> float:
    return mass_kg * G * drop_m


def climbing_power_w(mass_kg: float, grade: float, speed_kmh: float) -> float:
    v = speed_kmh / 3.6
    return mass_kg * G * v * grade


def rolling_power_w(mass_kg: float, crr: float, speed_kmh: float) -> float:
    v = speed_kmh / 3.6
    return crr * mass_kg * G * v


def wh(joules: float) -> float:
    return joules / 3600.0


# --------------------------------------------------------------------------
# supercapacitor sizing and comparison
# --------------------------------------------------------------------------

def capacitance_for_energy_f(energy_wh_: float, v_full: float, v_empty: float) -> float:
    """C = 2E / (V1^2 - V2^2). Energy here is the usable window."""
    if v_full <= v_empty:
        raise ValueError("v_full must exceed v_empty")
    return 2.0 * (energy_wh_ * 3600.0) / (v_full ** 2 - v_empty ** 2)


def cap_usable_energy_wh(capacitance_f: float, v_full: float, v_empty: float) -> float:
    return wh(0.5 * capacitance_f * (v_full ** 2 - v_empty ** 2))


def storage_metrics(item: dict) -> dict:
    energy = item["energy_wh"]
    mass = item.get("mass_kg")
    price = item.get("price_eur", item.get("price_usd"))
    currency = "EUR" if "price_eur" in item else "USD"
    return {
        "label": item["label"],
        "energy_wh": energy,
        "mass_kg": mass,
        "wh_per_kg": energy / mass if mass else None,
        "price": price,
        "currency": currency,
        "price_per_wh": price / energy if price else None,
    }


# --------------------------------------------------------------------------
# reporting
# --------------------------------------------------------------------------

def fmt_table(headers, rows) -> str:
    widths = [len(h) for h in headers]
    srows = [[str(c) for c in r] for r in rows]
    for r in srows:
        for i, c in enumerate(r):
            widths[i] = max(widths[i], len(c))
    line = "| " + " | ".join(h.ljust(widths[i]) for i, h in enumerate(headers)) + " |"
    sep = "|" + "|".join("-" * (widths[i] + 2) for i in range(len(headers))) + "|"
    body = ["| " + " | ".join(c.ljust(widths[i]) for i, c in enumerate(r)) + " |" for r in srows]
    return "\n".join([line, sep] + body)


def section_drivetrain(comp: dict) -> None:
    pedal_w = 200.0
    print("## 1. Drivetrain efficiency at 200 W rider input\n")

    rows = []
    for stages in (2, 3):
        eff = chain_efficiency(comp, stages)
        rows.append([f"Chain, {stages} stages", f"{eff*100:.1f}%", f"{pedal_w*eff:.0f} W",
                     f"{pedal_w*(1-eff):.0f} W"])
    print(fmt_table(["Path", "Efficiency", "At wheel", "Lost"], rows))
    print()

    variants = [
        ("Car alternator, peak + hub", "car_alternator_peak"),
        ("Car alternator, part load + hub", "car_alternator_partload"),
        ("Bicycle hub dynamo + hub", "bike_hub_dynamo"),
        ("Hub motor as PMG + hub", "hub_motor_as_pmg"),
        ("Axial-flux PMG + hub", "axial_flux_pmg"),
    ]
    rows = []
    for label, gid in variants:
        eff = serial_efficiency_with(comp, gid)
        rows.append([label, f"{eff*100:.1f}%", f"{pedal_w*eff:.0f} W", f"{pedal_w*(1-eff):.0f} W"])
    print("Serial electric path, same 200 W (generator -> rectifier -> bus -> controller -> hub):\n")
    print(fmt_table(["Generator", "Efficiency", "At wheel", "Lost"], rows))
    print()

    direct, _ = serial_efficiency(comp, SERIAL_PATH)
    via_batt, _ = serial_efficiency(comp, SERIAL_PATH_BATTERY)
    print("Two ways to build the serial path, with the same good components:\n")
    print(fmt_table(
        ["Topology", "Efficiency", "At wheel", "Lost"],
        [["Direct to motor bus", f"{direct*100:.1f}%", f"{pedal_w*direct:.0f} W",
          f"{pedal_w*(1-direct):.0f} W"],
         ["Through the battery", f"{via_batt*100:.1f}%", f"{pedal_w*via_batt:.0f} W",
          f"{pedal_w*(1-via_batt):.0f} W"]],
    ))
    print()
    print("The through-battery topology is what Mando and Schaeffler actually shipped, and it")
    print("is the worse one for efficiency. Feeding the motor bus directly avoids the")
    print("round-trip penalty but needs the generator, bus and motor voltages to track.")
    print()

    total, stages_rows = serial_efficiency(comp, SERIAL_PATH)
    print(f"Best-case serial path, stage by stage ({total*100:.1f}% total):\n")
    print(fmt_table(["Stage", "Stage eta", "Cumulative"],
                    [[lbl, f"{e*100:.0f}%", f"{c*100:.1f}%"] for lbl, e, c in stages_rows]))
    print()

    chain = chain_efficiency(comp, 2)
    be = break_even_generator_efficiency(comp, 2)
    print(f"Break-even: to match a 2-stage chain ({chain*100:.1f}%), the generator plus the")
    print(f"electronics downstream of it must reach {be*100:.1f}% combined.")
    print(f"Serial drive at best case leaves the rider effectively {chain/direct:.2f}x weaker.")
    print()


def section_regen(comp: dict) -> None:
    mass = comp["vehicle"]["mass_kg"]
    print("## 2. Regenerative braking: how much is actually there\n")
    print(f"Vehicle mass {mass:.0f} kg (rider + bike + kit).\n")
    rows = []
    for v in (10, 15, 18, 20, 25, 30):
        ke = kinetic_energy_j(mass, v)
        rec = recoverable_stop_j(comp, v, mass)
        rows.append([f"{v}", f"{ke:.0f}", f"{wh(ke):.3f}", f"{wh(rec):.3f}"])
    print(fmt_table(["km/h", "KE (J)", "KE (Wh)", "Recovered (Wh)"], rows))
    print()

    pack = by_id(comp, "storage", "lifepo4_48v_20ah")
    rec20 = recoverable_stop_j(comp, 20, mass)
    pct = wh(rec20) / pack["energy_wh"] * 100
    stops_per_wh = 3600.0 / rec20
    print(f"One stop from 20 km/h returns {wh(rec20):.2f} Wh, which is {pct:.3f}% of a "
          f"{pack['energy_wh']:.0f} Wh pack.")
    print(f"That is {stops_per_wh:.1f} stops per Wh. At 15 Wh/km, one kilometre of range costs "
          f"{15.0/wh(rec20):.0f} stops.")
    print()

    drop = 300.0
    print(f"A {drop:.0f} m descent instead yields {wh(descent_energy_j(mass, drop)):.0f} Wh at the "
          f"wheel before conversion losses -- two orders of magnitude more than a stop.")
    print("Regen is a hill and brake-wear feature, not a traffic-light feature.")
    print()


def section_storage(comp: dict) -> None:
    print("## 3. Supercapacitors vs batteries, on the market\n")
    rows = []
    for item in comp["storage"]:
        m = storage_metrics(item)
        rows.append([
            m["label"],
            f"{m['energy_wh']:.0f}",
            f"{m['mass_kg']:.1f}" if m["mass_kg"] else "-",
            f"{m['wh_per_kg']:.1f}" if m["wh_per_kg"] else "-",
            f"{m['price']:.0f} {m['currency']}" if m["price"] else "-",
            f"{m['price_per_wh']:.2f}" if m["price_per_wh"] else "-",
        ])
    print(fmt_table(["Storage", "Wh", "kg", "Wh/kg", "Price", "Price/Wh"], rows))
    print()

    cap = storage_metrics(by_id(comp, "storage", "maxwell_48v_165f"))
    bat = storage_metrics(by_id(comp, "storage", "lifepo4_48v_20ah"))
    print(f"Module-level comparisons: caps are {bat['wh_per_kg']/cap['wh_per_kg']:.0f}x heavier "
          f"per Wh and cost {cap['price_per_wh']/bat['price_per_wh']:.0f}x more per Wh than LiFePO4.")
    print("Bare cells close some of the cost gap but none of the mass gap.")
    print()

    print("### Sizing a cap bank for a given buffer\n")
    rows = []
    for energy, v1, v2 in ((5, 48, 36), (10, 48, 36), (10, 48, 24), (20, 52, 26)):
        c = capacitance_for_energy_f(energy, v1, v2)
        rows.append([f"{energy}", f"{v1}->{v2}", f"{c:.0f}"])
    print(fmt_table(["Usable Wh", "Voltage window", "Capacitance (F)"], rows))
    print()
    print("Note the voltage swing: a cap bank empties as a square law, so half the energy")
    print("sits below 70% of full voltage. A battery holds a flat bus; caps need a")
    print("wide-input controller or another conversion stage.")
    print()


def section_tradeoff(comp: dict) -> None:
    mass = comp["vehicle"]["mass_kg"]
    print("## 4. Mass sensitivity: what a heavy kit costs on grades\n")
    rows = []
    for grade in (0.005, 0.01, 0.03, 0.06):
        p = climbing_power_w(mass, grade, 18)
        p12 = climbing_power_w(12.0, grade, 18)
        rows.append([f"{grade*100:.1f}%", f"{p:.0f} W", f"{p12:.0f} W"])
    print(f"At 18 km/h, climbing power for the whole vehicle vs. just the 12 kg of kit:\n")
    print(fmt_table(["Grade", f"Total @ {mass:.0f} kg", "12 kg of kit"], rows))
    print()
    flat = rolling_power_w(mass, comp["vehicle"]["crr"], 18)
    flat12 = rolling_power_w(12.0, comp["vehicle"]["crr"], 18)
    print(f"On the flat at 18 km/h, 12 kg of kit costs {flat12:.0f} W of rolling resistance")
    print(f"out of {flat:.0f} W total. Gradients are where mass actually bites: 12 kg is a")
    print(f"{12.0/mass*100:.0f}% increase in the mass hauled up every hill.")
    print()


def battery_penalty_pct(rider_w: float, serial_eta: float, wheel_w: float,
                        chain_eta: float = 0.97, motor_eta: float = 0.88) -> float:
    """Extra battery draw (%) of a serial drive vs a chain, at equal wheel power.

    The point of this function: Schaeffler's "5% bigger battery" claim is about
    battery draw on an assisted bike, NOT about drivetrain efficiency. Because
    most wheel power comes from the battery, only the rider's share passes
    through the lossy conversion, so a large efficiency deficit produces a
    small battery penalty.
    """
    draw_chain = max(0.0, wheel_w - rider_w * chain_eta) / motor_eta
    draw_serial = max(0.0, wheel_w - rider_w * serial_eta) / motor_eta
    if draw_chain <= 0:
        return float("nan")
    return (draw_serial - draw_chain) / draw_chain * 100.0


def invert_battery_penalty(rider_w: float, wheel_w: float, target_pct: float = 5.0,
                           chain_eta: float = 0.97) -> float:
    """Serial-path efficiency that yields exactly `target_pct` extra battery draw."""
    lo, hi = 0.30, 1.0
    for _ in range(100):
        mid = (lo + hi) / 2.0
        if battery_penalty_pct(rider_w, mid, wheel_w, chain_eta) > target_pct:
            lo = mid
        else:
            hi = mid
    return (lo + hi) / 2.0


def section_crank(comp: dict) -> None:
    print("## 7. Crank alternator efficiency: what the shipped systems achieve\n")
    print("Manufacturer and literature figures for pedal generators:\n")
    rows = []
    for cid in ("cixi_pers_standalone", "schaeffler_freedrive_generator",
                "tournon_measured_prototype", "car_alternator_peak",
                "bike_hub_dynamo"):
        item = by_id(comp, "generators", cid)
        lo, hi = item["range"]
        shown = f"{lo*100:.0f}%" if lo == hi else f"{lo*100:.0f}-{hi*100:.0f}%"
        rows.append([item["label"][:52], shown, item["kind"]])
    print(fmt_table(["System", "Efficiency", "Provenance"], rows))
    print()

    print("What Schaeffler's 'about 5% less efficient than a chain' actually implies.")
    print("The 5% is extra battery draw, not drivetrain efficiency:\n")
    rows = []
    for rider in (60, 100, 150):
        for wheel in (250, 400):
            rows.append([f"{rider}", f"{wheel}",
                         f"{invert_battery_penalty(rider, wheel)*100:.1f}%"])
    print(fmt_table(["Rider W", "Wheel W", "Serial eta implied"], rows))
    print()
    print("So the claim is consistent with anything from ~68% to ~94%. It is true,")
    print("carefully worded, and almost uninformative.")
    print()

    print("The same efficiency deficit, expressed as what the rider feels:\n")
    rows = []
    for eff in (0.36, 0.62, 0.70, 0.73, 0.86, 0.91):
        slower = (1 - (eff / 0.97) ** (1.0 / 3.0)) * 100
        rows.append([f"{eff*100:.0f}%", f"{slower:.1f}%",
                     f"{battery_penalty_pct(150, eff, 400):.1f}%",
                     f"{battery_penalty_pct(100, eff, 250):.1f}%"])
    print(fmt_table(["Serial eta", "Slower (flat, 1/3-power law)",
                     "Extra battery @150W/400W", "Extra battery @100W/250W"], rows))
    print()
    print("Note the asymmetry: a 30% drivetrain deficit is a 10-15% speed deficit but")
    print("only a ~10% battery penalty. That is why makers quote battery range.")
    print()


def section_bootstrap(comp: dict) -> None:
    print("## 5. Cold start: can a caps-only bike generate at all?\n")
    alt = by_id(comp, "generators", "car_alternator_peak")
    pmg = by_id(comp, "generators", "axial_flux_pmg")
    print(f"- {alt['label']}: wound field. {alt['note']}")
    print(f"- {pmg['label']}: permanent magnet, self-exciting. Turns, volt appears.")
    print()
    print("So a caps-only build is electrically possible with a PM machine, and")
    print("impossible-in-practice with a car alternator. Either way you still want a")
    print("small keep-alive cell for logic and pre-charge state on power-up.")
    print()


def section_cadence(comp: dict) -> None:
    print("## 6. Why decoupling cadence from wheel speed buys less than expected\n")
    print("Human gross efficiency varies only a few percent across 60-100 rpm, and riders")
    print("already self-select near their optimum. A derailleur offers 500-600% of torque")
    print("multiplication at ~97%. Decoupling is a real benefit for packaging and comfort;")
    print("it is not where the drivetrain efficiency argument is won.")
    print()


SECTIONS = {
    "drivetrain": section_drivetrain,
    "regen": section_regen,
    "storage": section_storage,
    "tradeoff": section_tradeoff,
    "bootstrap": section_bootstrap,
    "cadence": section_cadence,
    "crank": section_crank,
}


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--section", choices=sorted(SECTIONS), help="run one section only")
    args = ap.parse_args(argv)

    comp = load_components()

    if args.section:
        SECTIONS[args.section](comp)
        return 0

    print("Chainless bicycle drivetrain: design tradeoff model")
    print("=" * 60)
    print()
    for name in ("drivetrain", "regen", "storage", "tradeoff", "bootstrap", "cadence"):
        SECTIONS[name](comp)
    print("---")
    print("All component figures and their provenance: data/components.json")
    print("Figures tagged 'estimate' are engineering judgement, not measurement.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
