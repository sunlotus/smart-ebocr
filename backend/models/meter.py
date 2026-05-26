# Copyright 2026 smart-ebocr Contributors
# SPDX-License-Identifier: Apache-2.0

from datetime import datetime, timezone

from backend.extensions import db


class Meter(db.Model):
    __tablename__ = 'meters'

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    description = db.Column(db.String(500), default='')

    # 多账户数据隔离
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False, index=True)
    family_member_id = db.Column(db.Integer, db.ForeignKey('family_members.id'), index=True)

    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))

    # 关系
    user = db.relationship('User', backref='meters')
    family_member = db.relationship('FamilyMember', backref='meters')

    def to_dict(self):
        return {
            'id': self.id,
            'name': self.name,
            'description': self.description,
            'user_id': self.user_id,
            'family_member_id': self.family_member_id,
            'created_at': self.created_at.isoformat() if self.created_at else None,
        }