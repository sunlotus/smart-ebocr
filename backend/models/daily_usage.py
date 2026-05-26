# Copyright 2026 smart-ebocr Contributors
# SPDX-License-Identifier: Apache-2.0

from datetime import date, datetime, timezone

from backend.extensions import db


class DailyUsage(db.Model):
    __tablename__ = 'daily_usage'
    __table_args__ = (
        db.UniqueConstraint('user_id', 'family_member_id', 'date', name='uq_usage_user_date'),
    )

    id = db.Column(db.Integer, primary_key=True)
    date = db.Column(db.Date, nullable=False, index=True)
    total_kwh = db.Column(db.Float, nullable=False, default=0)
    peak_kwh = db.Column(db.Float, default=0)
    valley_kwh = db.Column(db.Float, default=0)
    sharp_kwh = db.Column(db.Float, default=0)
    flat_kwh = db.Column(db.Float, default=0)
    source = db.Column(db.String(10), default='manual')  # 'ocr' or 'manual'

    # 多账户数据隔离
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False, index=True)
    family_member_id = db.Column(db.Integer, db.ForeignKey('family_members.id'), index=True)
    meter_id = db.Column(db.Integer, db.ForeignKey('meters.id'), index=True)

    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))

    # 关系
    user = db.relationship('User', backref='usage_records')
    family_member = db.relationship('FamilyMember', backref='usage_records')
    meter = db.relationship('Meter', backref='usage_records')

    def to_dict(self):
        return {
            'id': self.id,
            'date': self.date.isoformat(),
            'total_kwh': self.total_kwh,
            'peak_kwh': self.peak_kwh,
            'valley_kwh': self.valley_kwh,
            'sharp_kwh': self.sharp_kwh,
            'flat_kwh': self.flat_kwh,
            'source': self.source,
            'user_id': self.user_id,
            'family_member_id': self.family_member_id,
            'meter_id': self.meter_id,
        }