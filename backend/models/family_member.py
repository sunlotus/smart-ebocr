# Copyright 2026 smart-ebocr Contributors
# SPDX-License-Identifier: Apache-2.0

from datetime import datetime, timezone
import random

from backend.extensions import db


class FamilyMember(db.Model):
    __tablename__ = 'family_members'

    id = db.Column(db.Integer, primary_key=True)
    parent_user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False, index=True)
    name = db.Column(db.String(100), nullable=False)
    avatar_color = db.Column(db.String(20))  # 头像颜色
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))

    parent = db.relationship('User', backref='family_members')

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        if not self.avatar_color:
            self.avatar_color = random.choice([
                '#3B82F6', '#10B981', '#F59E0B', '#EF4444',
                '#8B5CF6', '#EC4899', '#06B6D4', '#84CC16'
            ])

    def to_dict(self):
        return {
            'id': self.id,
            'name': self.name,
            'avatar_color': self.avatar_color,
            'is_active': self.is_active
        }
