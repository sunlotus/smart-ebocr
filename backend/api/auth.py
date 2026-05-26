# Copyright 2026 smart-ebocr Contributors
# SPDX-License-Identifier: Apache-2.0

import secrets
from datetime import datetime, timezone, timedelta

from flask import Blueprint, session, jsonify, redirect, request, current_app

from backend.extensions import db
from backend.models.user import User
from backend.services.afdian_service import AfdianService
from backend.config import AFDIAN_SPONSOR_CACHE_TTL
from backend.api.decorators import get_current_user

bp = Blueprint('auth', __name__)


@bp.route('/login', methods=['GET'])
def login():
    """发起爱发电 OAuth 授权"""
    state = secrets.token_urlsafe(32)
    session['oauth_state'] = state
    authorize_url = AfdianService.get_authorize_url(state)
    return redirect(authorize_url)


@bp.route('/callback', methods=['GET'])
def callback():
    """OAuth 回调：换 token → 获取用户信息 → 同步赞助状态"""
    code = request.args.get('code')
    state = request.args.get('state')
    saved_state = session.pop('oauth_state', '')

    if not code or state != saved_state:
        return redirect('/#/upgrade?error=auth_failed')

    # 换 access_token
    token_data = AfdianService.get_token(code)
    if not token_data:
        return redirect('/#/upgrade?error=token_failed')

    access_token = token_data.get('access_token')

    # 获取用户信息
    user_info = AfdianService.get_user_info(access_token)
    if not user_info:
        return redirect('/#/upgrade?error=user_info_failed')

    afdian_uid = user_info.get('user_private_id') or user_info.get('user_id')
    name = user_info.get('name', '')
    avatar_url = user_info.get('avatar', '')

    # 创建或更新用户
    user = User.query.filter_by(afdian_uid=afdian_uid).first()
    if not user:
        user = User(afdian_uid=afdian_uid)
        db.session.add(user)

    user.name = name
    user.avatar_url = avatar_url

    # 同步赞助状态
    _sync_sponsor_status(user)

    db.session.commit()

    # 写入 session
    session['user_id'] = user.id
    session['plan_name'] = user.plan_name
    session.permanent = True

    return redirect('/#/profile?login=success')


@bp.route('/logout', methods=['POST'])
def logout():
    """退出登录"""
    session.clear()
    return jsonify({'message': '已退出登录'})


@bp.route('/me', methods=['GET'])
def me():
    """返回当前用户信息，超时则自动刷新赞助状态"""
    user = get_current_user()
    if not user:
        return jsonify({'error': '未登录'}), 401

    # 超时自动刷新赞助状态
    now = datetime.now(timezone.utc)
    if user.last_sync_at:
        sync_age = (now - user.last_sync_at).total_seconds()
    else:
        sync_age = float('inf')

    if sync_age > AFDIAN_SPONSOR_CACHE_TTL:
        _sync_sponsor_status(user)
        db.session.commit()

    return jsonify({
        'user': user.to_dict(),
        'features': _get_unlocked_features(user.plan_name),
    })


@bp.route('/sync', methods=['POST'])
def sync():
    """手动同步赞助状态"""
    user = get_current_user()
    if not user:
        return jsonify({'error': '未登录'}), 401

    _sync_sponsor_status(user)
    db.session.commit()

    session['plan_name'] = user.plan_name

    return jsonify({
        'user': user.to_dict(),
        'features': _get_unlocked_features(user.plan_name),
    })


def _sync_sponsor_status(user: User):
    """同步用户的赞助状态"""
    try:
        sponsor_data = AfdianService.query_sponsor()
        plan_name, plan_id = AfdianService.determine_plan(sponsor_data or {}, user.afdian_uid)
        user.plan_name = plan_name
        user.plan_id = plan_id
        user.last_sync_at = datetime.now(timezone.utc)

        # 赞助到期时间：从订单数据推算
        if plan_name != 'free':
            user.expires_at = datetime.now(timezone.utc) + timedelta(days=32)
        else:
            user.expires_at = None
    except Exception:
        # API 调用失败时保持现有状态
        pass


def _get_unlocked_features(plan_name: str) -> list[str]:
    """返回当前档位解锁的功能列表"""
    from backend.config import PLAN_LEVELS
    level = PLAN_LEVELS.get(plan_name, 0)

    features = []
    if level >= 1:  # supporter
        features.extend(['backers_list'])
    if level >= 2:  # premium
        features.extend(['multi_meter', 'advanced_charts', 'advanced_pricing', 'pdf_export'])
    if level >= 3:  # super
        features.extend(['feature_voting', 'priority_support'])
    return features