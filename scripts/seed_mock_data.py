# Copyright 2026 smart-ebocr Contributors
# SPDX-License-Identifier: Apache-2.0

"""
Generate mock daily electricity usage data for Jan-Apr 2026.
Usage: python scripts/seed_mock_data.py
"""
import random
import sys
from datetime import date, timedelta

# Ensure project root is importable
sys.path.insert(0, '.')

from backend.app import create_app
from backend.extensions import db
from backend.models.daily_usage import DailyUsage

SEED = 42
START_DATE = date(2026, 1, 1)
END_DATE = date(2026, 4, 30)

# Monthly baseline consumption (kWh/day) — winter heating → mild spring
MONTHLY_BASELINE = {1: 17.0, 2: 15.5, 3: 12.0, 4: 9.0}

# Consumption range clamp
MIN_KWH = 5.0
MAX_KWH = 25.0


def generate_daily_record(d: date, rng: random.Random) -> dict:
    month = d.month
    baseline = MONTHLY_BASELINE[month]

    # Weekend boost (Sat=5, Sun=6)
    weekend_boost = rng.uniform(0.5, 3.0) if d.weekday() >= 5 else 0.0

    # Random noise
    noise = rng.uniform(-2.5, 2.5)

    total = round(max(MIN_KWH, min(MAX_KWH, baseline + weekend_boost + noise)), 1)

    # Peak/Valley/Sharp/Flat split
    peak_ratio = rng.uniform(0.55, 0.65)
    valley_ratio = rng.uniform(0.30, 0.40)
    sharp_ratio = rng.uniform(0.01, 0.04)

    peak_kwh = round(total * peak_ratio, 1)
    valley_kwh = round(total * valley_ratio, 1)
    sharp_kwh = round(total * sharp_ratio, 1)
    flat_kwh = round(max(0, total - peak_kwh - valley_kwh - sharp_kwh), 1)

    source = 'ocr' if rng.random() < 0.7 else 'manual'

    return {
        'date': d,
        'total_kwh': total,
        'peak_kwh': peak_kwh,
        'valley_kwh': valley_kwh,
        'sharp_kwh': sharp_kwh,
        'flat_kwh': flat_kwh,
        'source': source,
    }


def main():
    app = create_app()

    with app.app_context():
        # Clear existing data
        deleted = DailyUsage.query.delete()
        db.session.commit()
        print(f"Cleared {deleted} existing records")

        rng = random.Random(SEED)
        records = []
        current = START_DATE

        while current <= END_DATE:
            data = generate_daily_record(current, rng)
            records.append(DailyUsage(**data))
            current += timedelta(days=1)

        db.session.bulk_save_objects(records)
        db.session.commit()
        print(f"Inserted {len(records)} records ({START_DATE} ~ {END_DATE})")

        # Summary
        monthly_totals = {}
        for r in records:
            m = r.date.month
            monthly_totals[m] = monthly_totals.get(m, 0) + r.total_kwh
        for m in sorted(monthly_totals):
            print(f"  {m}月: {monthly_totals[m]:.1f} kWh")


if __name__ == '__main__':
    main()