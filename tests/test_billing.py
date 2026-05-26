# Copyright 2026 smart-ebocr Contributors
# SPDX-License-Identifier: Apache-2.0

"""Tests for the billing calculation engine."""

import unittest

from backend.services.billing_service import BillingService


class MockPolicy:
    """Mock pricing policy for testing."""
    def __init__(self):
        self.tier1_rate = 0.5469
        self.tier1_limit = 2520
        self.tier2_rate = 0.5969
        self.tier2_limit = 4800
        self.tier3_rate = 0.8469
        self.peak_rate = 0.5769
        self.valley_rate = 0.3769
        self.sharp_rate = 0.6769
        self.flat_rate = 0.5469
        self.heating_valley_rate = 0.3469


class TestFlatBilling(unittest.TestCase):
    """Test flat-rate tiered billing calculations."""

    def setUp(self):
        self.policy = MockPolicy()
        self.service = BillingService()

    def test_tier1_only(self):
        """Usage within tier 1 limit (no prior cumulative)."""
        cost = self.service.calculate_flat_billing(100, self.policy)
        expected = 100 * 0.5469
        self.assertAlmostEqual(cost, round(expected, 2), places=2)

    def test_tier1_and_tier2(self):
        """Usage spanning tier 1 and tier 2 using year_cumulative_before.

        year_cumulative_before=2400 means:
          tier1_remaining = 2520 - 2400 = 120 kWh at tier1
          tier2_remaining = 4800 - 2400 = 2400 kWh capacity
          tier2 capacity = 2400 - 120 = 2280 kWh at tier2
        With 300 kWh usage: 120 @ tier1 + 180 @ tier2.
        """
        cost = self.service.calculate_flat_billing(300, self.policy, year_cumulative_before=2400)
        expected = 120 * 0.5469 + 180 * 0.5969
        self.assertAlmostEqual(cost, round(expected, 2), places=2)

    def test_all_three_tiers(self):
        """Usage spanning all three tiers using year_cumulative_before.

        year_cumulative_before=2400 means:
          tier1_remaining = 2520 - 2400 = 120 kWh
          tier2_remaining = 4800 - 2400 = 2400 kWh, tier2 capacity = 2280
        With 2500 kWh: 120 @ tier1 + 2280 @ tier2 + 100 @ tier3.
        """
        cost = self.service.calculate_flat_billing(2500, self.policy, year_cumulative_before=2400)
        expected = 120 * 0.5469 + 2280 * 0.5969 + 100 * 0.8469
        self.assertAlmostEqual(cost, round(expected, 2), places=2)

    def test_zero_usage(self):
        """Zero usage should cost zero."""
        cost = self.service.calculate_flat_billing(0, self.policy)
        self.assertEqual(cost, 0)


class TestTOUBilling(unittest.TestCase):
    """Test time-of-use billing calculations with flat_kwh."""

    def setUp(self):
        self.policy = MockPolicy()
        self.service = BillingService()

    def test_tier1_tou_with_flat(self):
        """TOU billing within tier 1 with all four components."""
        peak = 30
        valley = 20
        sharp = 10
        flat = 40
        total = 100
        cost = self.service.calculate_tou_billing(peak, valley, sharp, flat, total, self.policy)
        expected = 30 * 0.5769 + 20 * 0.3769 + 10 * 0.6769 + 40 * 0.5469
        self.assertAlmostEqual(cost, round(expected, 2), places=2)

    def test_zero_flat(self):
        """TOU billing with zero flat usage (backward compatible)."""
        peak = 60
        valley = 40
        sharp = 0
        flat = 0
        total = 100
        cost = self.service.calculate_tou_billing(peak, valley, sharp, flat, total, self.policy)
        expected = 60 * 0.5769 + 40 * 0.3769
        self.assertAlmostEqual(cost, round(expected, 2), places=2)

    def test_zero_usage(self):
        """Zero usage should cost zero."""
        cost = self.service.calculate_tou_billing(0, 0, 0, 0, 0, self.policy)
        self.assertEqual(cost, 0)

    def test_all_peak(self):
        """All electricity used during peak hours."""
        cost = self.service.calculate_tou_billing(100, 0, 0, 0, 100, self.policy)
        expected = 100 * 0.5769
        self.assertAlmostEqual(cost, round(expected, 2), places=2)

    def test_all_valley(self):
        """All electricity used during valley hours."""
        cost = self.service.calculate_tou_billing(0, 100, 0, 0, 100, self.policy)
        expected = 100 * 0.3769
        self.assertAlmostEqual(cost, round(expected, 2), places=2)

    def test_all_flat(self):
        """All electricity used during flat hours."""
        cost = self.service.calculate_tou_billing(0, 0, 0, 100, 100, self.policy)
        expected = 100 * 0.5469
        self.assertAlmostEqual(cost, round(expected, 2), places=2)

    def test_tier2_with_flat(self):
        """TOU billing spanning tier 1 and tier 2 with year_cumulative_before.

        year_cumulative_before=2400:
          tier1_remaining = 120 kWh, tier2 capacity = 2280 kWh
        With 300 kWh total: 120 @ tier1 + 180 @ tier2.
        """
        total = 300
        peak = 90
        valley = 60
        sharp = 30
        flat = 120
        cost = self.service.calculate_tou_billing(
            peak, valley, sharp, flat, total, self.policy, year_cumulative_before=2400
        )
        tier_diff = 0.5969 - 0.5469  # 0.05
        peak_ratio = 90 / 300
        valley_ratio = 60 / 300
        sharp_ratio = 30 / 300
        flat_ratio = 120 / 300
        expected = (
            # Tier 1 (120 kWh)
            120 * peak_ratio * 0.5769 +
            120 * valley_ratio * 0.3769 +
            120 * sharp_ratio * 0.6769 +
            120 * flat_ratio * 0.5469 +
            # Tier 2 (180 kWh)
            180 * peak_ratio * (0.5769 + tier_diff) +
            180 * valley_ratio * (0.3769 + tier_diff) +
            180 * sharp_ratio * (0.6769 + tier_diff) +
            180 * flat_ratio * (0.5469 + tier_diff)
        )
        self.assertAlmostEqual(cost, round(expected, 2), places=2)


class TestComparison(unittest.TestCase):
    """Test that flat vs TOU comparison logic is correct."""

    def setUp(self):
        self.policy = MockPolicy()
        self.service = BillingService()

    def test_valley_heavy_saves_with_tou(self):
        """If most usage is valley, TOU should be cheaper."""
        total = 200
        peak = 40
        valley = 160
        sharp = 0
        flat = 0

        flat_cost = self.service.calculate_flat_billing(total, self.policy)
        tou_cost = self.service.calculate_tou_billing(peak, valley, sharp, flat, total, self.policy)
        self.assertLess(tou_cost, flat_cost)

    def test_peak_heavy_costs_more_with_tou(self):
        """If most usage is peak, flat-rate should be cheaper."""
        total = 200
        peak = 180
        valley = 20
        sharp = 0
        flat = 0

        flat_cost = self.service.calculate_flat_billing(total, self.policy)
        tou_cost = self.service.calculate_tou_billing(peak, valley, sharp, flat, total, self.policy)
        self.assertLess(flat_cost, tou_cost)


class TestHeatingSeason(unittest.TestCase):
    """Test heating season valley rate logic."""

    def setUp(self):
        self.policy = MockPolicy()
        self.service = BillingService()

    def test_heating_months(self):
        """Nov-Mar should be heating season."""
        for m in (11, 12, 1, 2, 3):
            self.assertTrue(BillingService.is_heating_season(m), f"Month {m} should be heating season")

    def test_non_heating_months(self):
        """Apr-Oct should NOT be heating season."""
        for m in (4, 5, 6, 7, 8, 9, 10):
            self.assertFalse(BillingService.is_heating_season(m), f"Month {m} should NOT be heating season")

    def test_heating_season_cheaper_valley(self):
        """In heating season, valley rate should be lower (heating_valley_rate)."""
        total = 100
        peak = 40
        valley = 60
        sharp = 0
        flat = 0

        # Non-heating season (April)
        cost_normal = self.service.calculate_tou_billing(
            peak, valley, sharp, flat, total, self.policy, month=4
        )
        # Heating season (January)
        cost_heating = self.service.calculate_tou_billing(
            peak, valley, sharp, flat, total, self.policy, month=1
        )
        # Heating season should be cheaper due to lower valley rate
        self.assertLess(cost_heating, cost_normal)


if __name__ == '__main__':
    unittest.main()