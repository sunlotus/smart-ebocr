# Copyright 2026 smart-ebocr Contributors
# SPDX-License-Identifier: Apache-2.0

from functools import wraps

from flask import session, jsonify, g

from backend.extensions import db
from backend.models.user import User


def get_current_user() -> User | None:
    """从 session 获取当前用户"""
    user_id = session.get('user_id')
    if not user_id:
        return None
    return db.session.get(User, user_id)


def get_current_user_or_default() -> User:
    """获取当前登录用户，未登录返回系统默认用户（宽松隔离模式）"""
    user = get_current_user()
    if not user:
        user = User.query.filter_by(afdian_uid='system_default').first()
        if not user:
            user = User(
                afdian_uid='system_default',
                name='系统默认',
                plan_name='premium'
            )
            db.session.add(user)
            db.session.commit()
    return user


def require_login_or_default(f):
    """装饰器：未登录使用系统默认用户"""
    @wraps(f)
    def wrapper(*args, **kwargs):
        g.current_user = get_current_user_or_default()
        return f(*args, **kwargs)
    return wrapper
