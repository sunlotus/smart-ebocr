# Copyright 2026 smart-ebocr Contributors
# SPDX-License-Identifier: Apache-2.0

from datetime import datetime, timezone

from backend.extensions import db


class User(db.Model):
    __tablename__ = 'users'

    id = db.Column(db.Integer, primary_key=True)
    afdian_uid = db.Column(db.String(64), unique=True, nullable=False, index=True)
    name = db.Column(db.String(100))
    avatar_url = db.Column(db.String(500))
    plan_id = db.Column(db.String(64))      # 爱发电 plan_id
    plan_name = db.Column(db.String(50), default='free')  # free|supporter
    expires_at = db.Column(db.DateTime)      # 赞助到期时间
    last_sync_at = db.Column(db.DateTime)    # 上次同步爱发电状态
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))

    def to_dict(self):
        return {
            'id': self.id,
            'name': self.name,
            'avatar_url': self.avatar_url,
            'plan_name': self.plan_name,
            'expires_at': self.expires_at.isoformat() if self.expires_at else None,
        }