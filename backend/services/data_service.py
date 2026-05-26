# Copyright 2026 smart-ebocr Contributors
# SPDX-License-Identifier: Apache-2.0

"""Data CRUD service for daily usage records."""

from datetime import date as date_type

from backend.extensions import db
from backend.models.daily_usage import DailyUsage
from backend.utils.logger import get_logger

logger = get_logger(__name__)


class DataService:

    @staticmethod
    def validate_record(record):
        """Validate a usage record and return warnings list. Empty = OK."""
        warnings = []
        total = record.get('total_kwh', 0) or 0
        peak = record.get('peak_kwh', 0) or 0
        valley = record.get('valley_kwh', 0) or 0
        sharp = record.get('sharp_kwh', 0) or 0
        flat = record.get('flat_kwh', 0) or 0

        if total < 0:
            warnings.append('总电量为负数')
        elif total == 0:
            warnings.append('总电量为零')

        if total > 0 and peak == 0 and valley == 0 and sharp == 0 and flat == 0:
            warnings.append('有总电量但峰谷分量全为零')

        for name, val in [('峰段', peak), ('谷段', valley), ('尖段', sharp), ('平段', flat)]:
            if val < 0:
                warnings.append(f'{name}电量为负数')

        return warnings

    @staticmethod
    def check_conflicts(dates, user_id=None, family_member_id=None):
        """Return list of dates that already exist in the database."""
        parsed = []
        for d in dates:
            if isinstance(d, str):
                d = date_type.fromisoformat(d)
            parsed.append(d)

        query = DailyUsage.query.filter(DailyUsage.date.in_(parsed))
        if user_id is not None:
            query = query.filter_by(user_id=user_id, family_member_id=family_member_id)
        existing = query.all()
        return sorted(r.date.isoformat() for r in existing)

    @staticmethod
    def batch_upsert(records, conflict_mode='overwrite', user_id=None, family_member_id=None):
        """
        Batch insert or update daily usage records.

        Args:
            records: List of record dicts.
            conflict_mode: 'overwrite' (default), 'skip', or 'error'.
            user_id: Owner user ID for data isolation.
            family_member_id: Optional family member ID.

        Returns:
            dict with saved count, skipped count, and warnings.
        """
        saved = 0
        skipped = 0
        all_warnings = {}

        if conflict_mode == 'error':
            dates = [r.get('date') for r in records]
            conflicts = DataService.check_conflicts(dates, user_id=user_id, family_member_id=family_member_id)
            if conflicts:
                return {'saved': 0, 'skipped': 0, 'conflicts': conflicts}

        for item in records:
            d = item.get('date')
            if isinstance(d, str):
                d = date_type.fromisoformat(d)

            # Validate
            warnings = DataService.validate_record(item)
            if warnings:
                all_warnings[item.get('date', '?')] = warnings

            # Query with user context for data isolation
            query = DailyUsage.query.filter_by(date=d)
            if user_id is not None:
                query = query.filter_by(user_id=user_id, family_member_id=family_member_id)
            record = query.first()

            if record:
                if conflict_mode == 'skip':
                    skipped += 1
                    continue
                record.total_kwh = item.get('total_kwh', record.total_kwh)
                record.peak_kwh = item.get('peak_kwh', record.peak_kwh)
                record.valley_kwh = item.get('valley_kwh', record.valley_kwh)
                record.sharp_kwh = item.get('sharp_kwh', record.sharp_kwh)
                record.flat_kwh = item.get('flat_kwh', record.flat_kwh)
                record.source = item.get('source', record.source)
            else:
                record = DailyUsage(
                    date=d,
                    total_kwh=item.get('total_kwh', 0),
                    peak_kwh=item.get('peak_kwh', 0),
                    valley_kwh=item.get('valley_kwh', 0),
                    sharp_kwh=item.get('sharp_kwh', 0),
                    flat_kwh=item.get('flat_kwh', 0),
                    source=item.get('source', 'ocr'),
                    user_id=user_id,
                    family_member_id=family_member_id,
                )
                db.session.add(record)
            saved += 1

        db.session.commit()
        logger.info(f"Batch upsert: saved={saved}, skipped={skipped}, warnings={len(all_warnings)}")
        return {
            'saved': saved,
            'skipped': skipped,
            'warnings': all_warnings,
        }
