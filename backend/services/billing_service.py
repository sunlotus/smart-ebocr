# Copyright 2026 smart-ebocr Contributors
# SPDX-License-Identifier: Apache-2.0

"""
Billing calculation engine for 电费分析工具.

Supports two billing methods:
1. Flat-rate (不分峰谷): Yearly cumulative × tiered rates
2. Time-of-use (分时): Peak/valley/sharp/flat rates within each tier

Chinese residential electricity uses 3-tier progressive pricing based on
yearly cumulative consumption (e.g. Shandong: 2160/4200 kWh/year).
"""

from backend.extensions import db
from backend.models.daily_usage import DailyUsage
from backend.models.pricing_policy import PricingPolicy
from backend.utils.logger import get_logger

logger = get_logger(__name__)


class BillingService:

    @staticmethod
    def get_active_policy(user_id=None, family_member_id=None):
        """Get the currently active pricing policy for a user/member."""
        # 优先查找用户/成员专属策略
        if family_member_id is not None:
            policy = PricingPolicy.query.filter_by(
                family_member_id=family_member_id, is_active=True
            ).first()
            if policy:
                return policy

        if user_id is not None:
            policy = PricingPolicy.query.filter_by(
                user_id=user_id, family_member_id=None, is_active=True
            ).first()
            if policy:
                return policy

        # 回退到全局默认策略
        return PricingPolicy.query.filter_by(
            user_id=None, family_member_id=None, is_active=True
        ).first()

    @staticmethod
    def get_monthly_records(year, month, user_id=None, family_member_id=None):
        """Get all daily usage records for a given month."""
        query = DailyUsage.query
        if family_member_id is not None:
            query = query.filter_by(family_member_id=family_member_id)
        elif user_id is not None:
            query = query.filter_by(user_id=user_id, family_member_id=None)
        return query.filter(
            db.extract('year', DailyUsage.date) == year,
            db.extract('month', DailyUsage.date) == month,
        ).order_by(DailyUsage.date).all()

    @staticmethod
    def get_yearly_cumulative_before(year, month, user_id=None, family_member_id=None):
        """Calculate yearly cumulative kWh before the given month (Jan ~ prev month)."""
        query = DailyUsage.query
        if family_member_id is not None:
            query = query.filter_by(family_member_id=family_member_id)
        elif user_id is not None:
            query = query.filter_by(user_id=user_id, family_member_id=None)
        records = query.filter(
            db.extract('year', DailyUsage.date) == year,
            db.extract('month', DailyUsage.date) < month,
        ).all()
        return round(sum(r.total_kwh for r in records), 2)

    @staticmethod
    def calculate_flat_billing(total_kwh, policy, year_cumulative_before=0):
        """
        Calculate cost using flat-rate tiered pricing (不分峰谷).

        Tier boundaries are shifted by year_cumulative_before so that
        each month's billing accounts for the full-year cumulative usage.

        Args:
            total_kwh: This month's total consumption.
            policy: Active PricingPolicy.
            year_cumulative_before: Cumulative kWh from Jan to previous month.
        """
        cost = 0.0
        remaining = total_kwh

        # Remaining capacity in each tier after previous months
        tier1_remaining = max(0, policy.tier1_limit - year_cumulative_before)
        tier2_remaining = max(0, policy.tier2_limit - year_cumulative_before)

        # Tier 1
        tier1_amount = min(remaining, tier1_remaining)
        cost += tier1_amount * policy.tier1_rate
        remaining -= tier1_amount

        # Tier 2
        if remaining > 0:
            tier2_capacity = tier2_remaining - tier1_remaining
            tier2_amount = min(remaining, max(0, tier2_capacity))
            cost += tier2_amount * policy.tier2_rate
            remaining -= tier2_amount

        # Tier 3
        if remaining > 0:
            cost += remaining * policy.tier3_rate

        return round(cost, 2)

    @staticmethod
    def is_heating_season(month):
        """Check if a month falls in heating season (November-March)."""
        return month in (11, 12, 1, 2, 3)

    @staticmethod
    def calculate_tou_billing(peak_kwh, valley_kwh, sharp_kwh, flat_kwh, total_kwh, policy, month=None, year_cumulative_before=0):
        """
        Calculate cost using time-of-use pricing within tiered structure.

        Steps:
        1. Determine which tier(s) the monthly usage falls into,
           shifted by year_cumulative_before
        2. Allocate peak/valley/sharp/flat proportionally within each tier
        3. Apply the corresponding peak/valley/sharp/flat rate

        Args:
            month: Optional month (1-12). If provided and in heating season
                   (Nov-Mar), uses heating_valley_rate instead of valley_rate.
            year_cumulative_before: Cumulative kWh from Jan to previous month.
        """
        if total_kwh == 0:
            return 0.0

        peak_ratio = peak_kwh / total_kwh if total_kwh > 0 else 0
        valley_ratio = valley_kwh / total_kwh if total_kwh > 0 else 0
        sharp_ratio = sharp_kwh / total_kwh if total_kwh > 0 else 0
        flat_ratio = flat_kwh / total_kwh if total_kwh > 0 else 0

        remaining = total_kwh
        cost = 0.0

        # Get rates, defaulting flat_rate to tier1_rate if not set
        peak_rate = policy.peak_rate
        sharp_rate = policy.sharp_rate
        flat_rate = getattr(policy, 'flat_rate', None) or policy.tier1_rate

        # Use heating valley rate if in heating season
        if (month is not None
                and BillingService.is_heating_season(month)
                and getattr(policy, 'heating_valley_rate', None)):
            valley_rate = policy.heating_valley_rate
        else:
            valley_rate = policy.valley_rate

        # Remaining capacity in each tier after previous months
        tier1_remaining = max(0, policy.tier1_limit - year_cumulative_before)
        tier2_remaining = max(0, policy.tier2_limit - year_cumulative_before)

        # Tier 1
        tier1_amount = min(remaining, tier1_remaining)
        tier1_peak = tier1_amount * peak_ratio
        tier1_valley = tier1_amount * valley_ratio
        tier1_sharp = tier1_amount * sharp_ratio
        tier1_flat = tier1_amount * flat_ratio

        cost += tier1_peak * peak_rate
        cost += tier1_valley * valley_rate
        cost += tier1_sharp * sharp_rate
        cost += tier1_flat * flat_rate
        remaining -= tier1_amount

        # Tier 2
        if remaining > 0:
            tier2_capacity = tier2_remaining - tier1_remaining
            tier2_amount = min(remaining, max(0, tier2_capacity))
            tier2_peak = tier2_amount * peak_ratio
            tier2_valley = tier2_amount * valley_ratio
            tier2_sharp = tier2_amount * sharp_ratio
            tier2_flat = tier2_amount * flat_ratio

            # Tier 2 adds the tier difference to base rates
            tier_diff = policy.tier2_rate - policy.tier1_rate
            cost += tier2_peak * (peak_rate + tier_diff)
            cost += tier2_valley * (valley_rate + tier_diff)
            cost += tier2_sharp * (sharp_rate + tier_diff)
            cost += tier2_flat * (flat_rate + tier_diff)
            remaining -= tier2_amount

        # Tier 3
        if remaining > 0:
            tier3_amount = remaining
            tier3_peak = tier3_amount * peak_ratio
            tier3_valley = tier3_amount * valley_ratio
            tier3_sharp = tier3_amount * sharp_ratio
            tier3_flat = tier3_amount * flat_ratio

            tier_diff = policy.tier3_rate - policy.tier1_rate
            cost += tier3_peak * (peak_rate + tier_diff)
            cost += tier3_valley * (valley_rate + tier_diff)
            cost += tier3_sharp * (sharp_rate + tier_diff)
            cost += tier3_flat * (flat_rate + tier_diff)

        return round(cost, 2)

    @classmethod
    def compare_month(cls, year, month, user_id=None, family_member_id=None):
        """
        Compare flat-rate vs time-of-use billing for a given month.

        Returns:
            dict with monthly summary, daily breakdown, and yearly cumulative info.
        """
        logger.debug(f"Billing comparison: {year}-{month:02d}")

        policy = cls.get_active_policy(user_id=user_id, family_member_id=family_member_id)
        if not policy:
            logger.error("No active pricing policy found")
            return {'error': 'No active pricing policy'}

        records = cls.get_monthly_records(year, month, user_id=user_id, family_member_id=family_member_id)
        year_cumulative_before = cls.get_yearly_cumulative_before(year, month, user_id=user_id, family_member_id=family_member_id)

        if not records:
            logger.warning(f"No usage records found for {year}-{month:02d}")
            return {
                'year': year,
                'month': month,
                'total_kwh': 0,
                'flat_cost': 0,
                'tou_cost': 0,
                'savings': 0,
                'cheaper_method': None,
                'year_cumulative_before': year_cumulative_before,
                'year_cumulative': year_cumulative_before,
                'daily_breakdown': [],
            }

        logger.debug(f"Found {len(records)} usage records for {year}-{month:02d}")

        total_kwh = sum(r.total_kwh for r in records)
        peak_kwh = sum(r.peak_kwh for r in records)
        valley_kwh = sum(r.valley_kwh for r in records)
        sharp_kwh = sum(r.sharp_kwh for r in records)
        flat_kwh = sum(r.flat_kwh for r in records)

        year_cumulative = round(year_cumulative_before + total_kwh, 2)

        flat_cost = cls.calculate_flat_billing(total_kwh, policy, year_cumulative_before)
        tou_cost = cls.calculate_tou_billing(
            peak_kwh, valley_kwh, sharp_kwh, flat_kwh, total_kwh, policy,
            month=month, year_cumulative_before=year_cumulative_before
        )
        savings = round(flat_cost - tou_cost, 2)

        logger.info(f"Billing comparison {year}-{month:02d}: flat=¥{flat_cost:.2f}, tou=¥{tou_cost:.2f}, savings=¥{savings:.2f}, year_cum={year_cumulative}")

        # Daily breakdown with running cumulative
        daily_breakdown = []
        running_cumulative = year_cumulative_before
        for r in records:
            running_cumulative = round(running_cumulative + r.total_kwh, 2)
            daily_flat = cls.calculate_flat_billing(r.total_kwh, policy, running_cumulative - r.total_kwh)
            daily_tou = cls.calculate_tou_billing(
                r.peak_kwh, r.valley_kwh, r.sharp_kwh, r.flat_kwh, r.total_kwh, policy,
                month=r.date.month, year_cumulative_before=running_cumulative - r.total_kwh
            )
            daily_breakdown.append({
                'date': r.date.isoformat(),
                'total_kwh': r.total_kwh,
                'peak_kwh': r.peak_kwh,
                'valley_kwh': r.valley_kwh,
                'sharp_kwh': r.sharp_kwh,
                'flat_kwh': r.flat_kwh,
                'yearly_cumulative_kwh': running_cumulative,
                'daily_flat': daily_flat,
                'daily_tou': daily_tou,
            })

        return {
            'year': year,
            'month': month,
            'total_kwh': round(total_kwh, 2),
            'peak_kwh': round(peak_kwh, 2),
            'valley_kwh': round(valley_kwh, 2),
            'sharp_kwh': round(sharp_kwh, 2),
            'flat_kwh': round(flat_kwh, 2),
            'flat_cost': flat_cost,
            'tou_cost': tou_cost,
            'savings': savings,
            'cheaper_method': 'flat' if savings > 0 else ('tou' if savings < 0 else 'equal'),
            'year_cumulative_before': year_cumulative_before,
            'year_cumulative': year_cumulative,
            'daily_breakdown': daily_breakdown,
            'policy': policy.to_dict(),
        }

    @classmethod
    def annual_summary(cls, year, user_id=None, family_member_id=None):
        """Generate annual billing summary for all months."""
        logger.debug(f"Annual billing summary: {year}")

        summaries = []
        for month in range(1, 13):
            result = cls.compare_month(year, month, user_id=user_id, family_member_id=family_member_id)
            summaries.append(result)

        total_flat = sum(s.get('flat_cost', 0) for s in summaries)
        total_tou = sum(s.get('tou_cost', 0) for s in summaries)

        logger.info(f"Annual billing summary {year}: flat=¥{total_flat:.2f}, tou=¥{total_tou:.2f}, savings=¥{total_flat - total_tou:.2f}")

        return {
            'year': year,
            'total_flat_cost': round(total_flat, 2),
            'total_tou_cost': round(total_tou, 2),
            'total_savings': round(total_flat - total_tou, 2),
            'cheaper_method': 'flat' if total_flat < total_tou else 'tou',
            'monthly_summaries': summaries,
        }