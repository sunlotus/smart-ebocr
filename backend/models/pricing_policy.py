# Copyright 2026 smart-ebocr Contributors
# SPDX-License-Identifier: Apache-2.0

from datetime import datetime, timezone

from backend.extensions import db


class PricingPolicy(db.Model):
    __tablename__ = 'pricing_policy'

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    region = db.Column(db.String(50), default='shandong')
    effective_date = db.Column(db.Date)

    # Tier rates (阶梯电价)
    tier1_rate = db.Column(db.Float, nullable=False, default=0.5469)
    tier1_limit = db.Column(db.Integer, nullable=False, default=2520)
    tier2_rate = db.Column(db.Float, nullable=False, default=0.5969)
    tier2_limit = db.Column(db.Integer, nullable=False, default=4800)
    tier3_rate = db.Column(db.Float, nullable=False, default=0.8469)

    # Time-of-use rates (分时电价)
    peak_rate = db.Column(db.Float, default=0.5769)
    valley_rate = db.Column(db.Float, default=0.3769)
    heating_valley_rate = db.Column(db.Float, default=0.3469)  # 采暖季谷段费率 (11月-3月)
    sharp_rate = db.Column(db.Float, default=0.6769)
    flat_rate = db.Column(db.Float, default=0.0)  # 平段费率（如果有的话）

    # Time periods (JSON string)
    peak_hours = db.Column(db.Text, default='[{"start":"08:00","end":"22:00"}]')
    valley_hours = db.Column(db.Text, default='[{"start":"22:00","end":"06:00"}]')

    # 多账户数据隔离
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), index=True)
    family_member_id = db.Column(db.Integer, db.ForeignKey('family_members.id'), index=True)

    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))

    # 关系
    user = db.relationship('User', backref='pricing_policies')
    family_member = db.relationship('FamilyMember', backref='pricing_policies')

    def to_dict(self):
        return {
            'id': self.id,
            'name': self.name,
            'region': self.region,
            'tier1_rate': self.tier1_rate,
            'tier1_limit': self.tier1_limit,
            'tier2_rate': self.tier2_rate,
            'tier2_limit': self.tier2_limit,
            'tier3_rate': self.tier3_rate,
            'peak_rate': self.peak_rate,
            'valley_rate': self.valley_rate,
            'heating_valley_rate': self.heating_valley_rate,
            'sharp_rate': self.sharp_rate,
            'flat_rate': self.flat_rate,
            'peak_hours': self.peak_hours,
            'valley_hours': self.valley_hours,
            'is_active': self.is_active,
            'user_id': self.user_id,
            'family_member_id': self.family_member_id,
        }