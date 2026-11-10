#!/usr/bin/env python3
"""
Tests for the tradeoff model. Run: python3 -m unittest discover -s tests -v

These pin the physics and the sanity of the component data, not the exact
efficiency verdicts. If a number in components.json is edited, the ranges
here are what stop it from silently producing nonsense.
"""

import os
import sys
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "analysis"))

import model  # noqa: E402


class TestEnergy(unittest.TestCase):
    def test_kinetic_energy_hand_computed(self):
        # 100 kg at 20 km/h = 15.5556 m/s
        self.assertAlmostEqual(model.kinetic_energy_j(100, 20), 1543.2, delta=0.5)

    def test_kinetic_energy_scales_with_square_of_speed(self):
        a = model.kinetic_energy_j(100, 10)
        b = model.kinetic_energy_j(100, 20)
        self.assertAlmostEqual(b / a, 4.0, places=6)

    def test_recoverable_is_less_than_kinetic(self):
        comp = model.load_components()
        for speed in (10, 20, 30):
            self.assertLess(model.recoverable_stop_j(comp, speed), model.kinetic_energy_j(100, speed))

    def test_descent_beats_a_stop_by_orders_of_magnitude(self):
        comp = model.load_components()
        stop = model.recoverable_stop_j(comp, 20)
        hill = model.descent_energy_j(100, 300)
        self.assertGreater(hill / stop, 100)

    def test_wh_conversion(self):
        self.assertAlmostEqual(model.wh(3600), 1.0, places=9)


class TestCapacitance(unittest.TestCase):
    def test_roundtrip_energy_from_capacitance(self):
        c = model.capacitance_for_energy_f(10.0, 48.0, 24.0)
        self.assertAlmostEqual(model.cap_usable_energy_wh(c, 48.0, 24.0), 10.0, places=6)

    def test_3000f_cell_energy_matches_datasheet(self):
        # 0.5 * 3000 * 2.7^2 = 10935 J = 3.04 Wh
        self.assertAlmostEqual(model.wh(0.5 * 3000 * 2.7 ** 2), 3.04, delta=0.01)

    def test_series_string_of_eighteen_cells(self):
        # 18 x 3000 F in series = 166.7 F, 48.6 V max
        c = 3000.0 / 18
        self.assertAlmostEqual(c, 166.67, delta=0.01)
        self.assertAlmostEqual(model.cap_usable_energy_wh(c, 48.6, 24.3), 41.0, delta=0.5)

    def test_square_law_penalty(self):
        # Half the voltage is three quarters of the energy: a cap bank that is
        # "half full" by voltage is only a quarter empty.
        e_full = model.cap_usable_energy_wh(100, 48, 0)
        e_half = model.cap_usable_energy_wh(100, 48, 24)
        self.assertAlmostEqual(e_half / e_full, 0.75, places=6)

    def test_rejects_inverted_window(self):
        with self.assertRaises(ValueError):
            model.capacitance_for_energy_f(10, 24, 48)


class TestDrivetrain(unittest.TestCase):
    def setUp(self):
        self.comp = model.load_components()

    def test_chain_is_high_nineties(self):
        for stages in (1, 2, 3):
            eff = model.chain_efficiency(self.comp, stages)
            self.assertGreater(eff, 0.90)
            self.assertLessEqual(eff, 1.0)

    def test_serial_is_much_worse_than_chain(self):
        serial, _ = model.serial_efficiency(self.comp)
        self.assertLess(serial, model.chain_efficiency(self.comp, 2))

    def test_serial_efficiency_in_plausible_band(self):
        serial, _ = model.serial_efficiency(self.comp)
        self.assertGreater(serial, 0.60)
        self.assertLess(serial, 0.80)

    def test_alternator_path_is_worse_than_pmg_path(self):
        alt = model.serial_efficiency_with(self.comp, "car_alternator_peak")
        pmg = model.serial_efficiency_with(self.comp, "axial_flux_pmg")
        self.assertLess(alt, pmg)

    def test_part_load_alternator_worse_than_peak(self):
        part = model.serial_efficiency_with(self.comp, "car_alternator_partload")
        peak = model.serial_efficiency_with(self.comp, "car_alternator_peak")
        self.assertLess(part, peak)

    def test_through_battery_is_worse_than_direct(self):
        direct, _ = model.serial_efficiency(self.comp, model.SERIAL_PATH)
        batt, _ = model.serial_efficiency(self.comp, model.SERIAL_PATH_BATTERY)
        self.assertLess(batt, direct)

    def test_break_even_is_above_unity(self):
        # That is the whole point: no generator can rescue the serial topology.
        be = model.break_even_generator_efficiency(self.comp, 2)
        self.assertGreater(be, 1.0)

    def test_cumulative_is_monotonic(self):
        _, rows = model.serial_efficiency(self.comp)
        prev = 1.0
        for _, _, cum in rows:
            self.assertLessEqual(cum, prev)
            prev = cum


class TestComponentData(unittest.TestCase):
    def setUp(self):
        self.comp = model.load_components()

    def test_every_efficiency_is_a_fraction(self):
        for section in ("generators", "electronics", "motors", "mechanical"):
            for item in self.comp[section]:
                with self.subTest(item=item["id"]):
                    self.assertGreater(item["efficiency"], 0.0)
                    self.assertLessEqual(item["efficiency"], 1.0)

    def test_declared_value_sits_inside_declared_range(self):
        for section in ("generators", "electronics", "motors", "mechanical"):
            for item in self.comp[section]:
                if "range" not in item:
                    continue
                with self.subTest(item=item["id"]):
                    lo, hi = item["range"]
                    self.assertLessEqual(lo, item["efficiency"])
                    self.assertLessEqual(item["efficiency"], hi)

    def test_provenance_fields_present(self):
        for section in ("generators", "electronics", "motors", "mechanical", "storage"):
            for item in self.comp[section]:
                with self.subTest(item=item["id"]):
                    self.assertIn(item["kind"], {"literature", "datasheet", "estimate"})
                    self.assertTrue(item.get("source"))

    def test_storage_has_energy_and_price(self):
        for item in self.comp["storage"]:
            with self.subTest(item=item["id"]):
                self.assertGreater(item["energy_wh"], 0)
                self.assertTrue("price_eur" in item or "price_usd" in item)


class TestStorageComparison(unittest.TestCase):
    def setUp(self):
        self.comp = model.load_components()

    def test_caps_are_worse_per_kwh_than_lifepo4(self):
        cap = model.storage_metrics(model.by_id(self.comp, "storage", "maxwell_48v_165f"))
        bat = model.storage_metrics(model.by_id(self.comp, "storage", "lifepo4_48v_20ah"))
        self.assertGreater(cap["price_per_wh"], bat["price_per_wh"] * 50)
        self.assertGreater(bat["wh_per_kg"], cap["wh_per_kg"] * 10)

    def test_lifepo4_energy_is_nominal_volts_times_amp_hours(self):
        bat = model.by_id(self.comp, "storage", "lifepo4_48v_20ah")
        self.assertAlmostEqual(bat["energy_wh"], 48 * 20, delta=1.0)


class TestCrankAlternator(unittest.TestCase):
    def setUp(self):
        self.comp = model.load_components()

    def test_chain_reference_has_zero_penalty(self):
        # A serial path as good as a chain must cost nothing extra.
        self.assertAlmostEqual(model.battery_penalty_pct(100, 0.97, 250), 0.0, places=6)

    def test_worse_efficiency_costs_more_battery(self):
        a = model.battery_penalty_pct(100, 0.85, 250)
        b = model.battery_penalty_pct(100, 0.70, 250)
        self.assertGreater(b, a)
        self.assertGreater(a, 0)

    def test_penalty_is_smaller_when_battery_dominates(self):
        # Same efficiency, more wheel power => the rider's share is a smaller
        # fraction, so the battery penalty shrinks. This is the mechanism behind
        # Schaeffler's misleadingly small 5% claim.
        low = model.battery_penalty_pct(100, 0.75, 250)
        high = model.battery_penalty_pct(100, 0.75, 600)
        self.assertLess(high, low)

    def test_invert_recovers_target(self):
        for rider, wheel in ((60, 250), (100, 400), (150, 250)):
            eta = model.invert_battery_penalty(rider, wheel, 5.0)
            self.assertAlmostEqual(model.battery_penalty_pct(rider, eta, wheel),
                                   5.0, delta=0.05)

    def test_invert_lands_in_published_band(self):
        # The claim maps to a wide, low-information band -- not to ~91%.
        etas = [model.invert_battery_penalty(r, w, 5.0)
                for r in (60, 100, 150) for w in (250, 400)]
        self.assertGreater(min(etas), 0.60)
        self.assertLess(max(etas), 0.96)
        # Spread across the band must be large enough to be uninformative.
        self.assertGreater(max(etas) - min(etas), 0.15)

    def test_vendor_figures_are_in_data(self):
        for cid in ("cixi_pers_standalone", "schaeffler_freedrive_generator"):
            item = model.by_id(self.comp, "generators", cid)
            self.assertGreaterEqual(item["efficiency"], 0.80)
            self.assertLess(item["efficiency"], 0.90)

    def test_tournon_prototype_is_pessimistic(self):
        proto = model.by_id(self.comp, "generators", "tournon_measured_prototype")
        best, _ = model.serial_efficiency(self.comp)
        self.assertLess(proto["efficiency"], best)


if __name__ == "__main__":
    unittest.main()
