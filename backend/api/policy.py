# Copyright 2026 smart-ebocr Contributors
# SPDX-License-Identifier: Apache-2.0

from flask import Blueprint, request, jsonify, g

from backend.extensions import db
from backend.models.pricing_policy import PricingPolicy
from backend.api.decorators import require_login_or_default, get_current_user_or_default
from backend.utils.logger import get_logger

bp = Blueprint('policy', __name__)
logger = get_logger(__name__)


def _get_policy_context():
    """获取当前策略查询上下文"""
    user = get_current_user_or_default()
    member_id = request.args.get('family_member_id', type=int)

    # supporter 及以上支持子账户独立策略
    if member_id and user.plan_name in ['supporter', 'premium', 'super']:
        from backend.models.family_member import FamilyMember
        member = FamilyMember.query.filter_by(id=member_id, parent_user_id=user.id).first()
        if member:
            return {'user_id': user.id, 'family_member_id': member_id}

    return {'user_id': user.id, 'family_member_id': None}


@bp.route('/', methods=['GET'])
@require_login_or_default
def get_active():
    """Get the active pricing policy."""
    context = _get_policy_context()

    # 优先返回用户自定义策略
    if context['family_member_id']:
        policy = PricingPolicy.query.filter_by(
            family_member_id=context['family_member_id'],
            is_active=True
        ).first()
    else:
        policy = PricingPolicy.query.filter_by(
            user_id=context['user_id'],
            family_member_id=None,
            is_active=True
        ).first()

    # 回退到全局默认策略
    if not policy:
        policy = PricingPolicy.query.filter_by(
            user_id=None,
            family_member_id=None,
            is_active=True
        ).first()

    if not policy:
        logger.warning("Get policy: no active policy found")
        return jsonify({'error': 'No active policy'}), 404

    logger.debug(f"Retrieved active policy: {policy.name}")
    return jsonify(policy.to_dict())


@bp.route('/', methods=['PUT'])
@require_login_or_default
def update_policy():
    """Update pricing policy."""
    context = _get_policy_context()
    data = request.get_json()

    # 查找或创建用户策略
    if context['family_member_id']:
        policy = PricingPolicy.query.filter_by(
            family_member_id=context['family_member_id'],
            is_active=True
        ).first()
    else:
        policy = PricingPolicy.query.filter_by(
            user_id=context['user_id'],
            family_member_id=None,
            is_active=True
        ).first()

    if not policy:
        # 创建用户自定义策略（复制全局默认）
        default = PricingPolicy.query.filter_by(
            user_id=None,
            family_member_id=None,
            is_active=True
        ).first()

        policy = PricingPolicy(
            user_id=context['user_id'],
            family_member_id=context['family_member_id'],
            name=f"自定义策略",
            is_active=True
        )

        if default:
            # 复制默认策略的参数
            for field in ['tier1_rate', 'tier2_rate', 'tier3_rate',
                         'tier1_limit', 'tier2_limit',
                         'peak_rate', 'valley_rate', 'heating_valley_rate', 'sharp_rate',
                         'flat_rate', 'peak_hours', 'valley_hours', 'region']:
                setattr(policy, field, getattr(default, field))

        db.session.add(policy)

    changed_fields = []
    for key in ['tier1_rate', 'tier2_rate', 'tier3_rate',
                'tier1_limit', 'tier2_limit',
                'peak_rate', 'valley_rate', 'heating_valley_rate', 'sharp_rate',
                'peak_hours', 'valley_hours', 'name', 'region']:
        if key in data:
            old_value = getattr(policy, key, None)
            setattr(policy, key, data[key])
            changed_fields.append(f"{key}: {old_value} -> {data[key]}")

    db.session.commit()

    if changed_fields:
        logger.info(f"Policy updated: {policy.name}, changes: {', '.join(changed_fields)}")

    return jsonify(policy.to_dict())


@bp.route('/advanced', methods=['GET'])
@require_login_or_default
def list_advanced_policies():
    """获取当前用户的电价策略列表（高级功能）"""
    user = g.current_user
    member_id = request.args.get('family_member_id', type=int)

    query = PricingPolicy.query
    if member_id:
        query = query.filter_by(family_member_id=member_id)
    else:
        query = query.filter(
            (PricingPolicy.user_id == user.id) | (PricingPolicy.user_id == None)
        )

    policies = query.order_by(PricingPolicy.id).all()
    return jsonify({'policies': [p.to_dict() for p in policies]})


@bp.route('/advanced', methods=['POST'])
@require_login_or_default
def create_advanced_policy():
    """创建新的电价策略（高级功能）— 自定义阶梯/地区"""
    user = g.current_user
    data = request.get_json()
    if not data or 'name' not in data:
        return jsonify({'error': 'name is required'}), 400

    policy = PricingPolicy(
        name=data['name'],
        region=data.get('region', 'custom'),
        tier1_rate=data.get('tier1_rate', 0.5469),
        tier1_limit=data.get('tier1_limit', 2520),
        tier2_rate=data.get('tier2_rate', 0.5969),
        tier2_limit=data.get('tier2_limit', 4800),
        tier3_rate=data.get('tier3_rate', 0.8469),
        peak_rate=data.get('peak_rate', 0.5769),
        valley_rate=data.get('valley_rate', 0.3769),
        heating_valley_rate=data.get('heating_valley_rate', 0.3469),
        sharp_rate=data.get('sharp_rate', 0.6769),
        flat_rate=data.get('flat_rate', 0.0),
        peak_hours=data.get('peak_hours', '[{"start":"08:00","end":"22:00"}]'),
        valley_hours=data.get('valley_hours', '[{"start":"22:00","end":"06:00"}]'),
        is_active=data.get('is_active', False),
        user_id=user.id,
        family_member_id=data.get('family_member_id'),
    )
    db.session.add(policy)
    db.session.commit()

    logger.info(f"Created advanced policy: {policy.name}")
    return jsonify(policy.to_dict()), 201


@bp.route('/advanced/<int:policy_id>', methods=['PUT'])
@require_login_or_default
def update_advanced_policy(policy_id):
    """更新指定电价策略（高级功能）"""
    user = g.current_user
    policy = PricingPolicy.query.filter_by(id=policy_id, user_id=user.id).first()
    if not policy:
        return jsonify({'error': 'Policy not found'}), 404

    data = request.get_json()
    for key in ['name', 'region', 'tier1_rate', 'tier2_rate', 'tier3_rate',
                'tier1_limit', 'tier2_limit', 'peak_rate', 'valley_rate',
                'heating_valley_rate', 'sharp_rate', 'flat_rate',
                'peak_hours', 'valley_hours', 'is_active']:
        if key in data:
            setattr(policy, key, data[key])

    db.session.commit()
    logger.info(f"Updated advanced policy: {policy.name}")
    return jsonify(policy.to_dict())


@bp.route('/advanced/<int:policy_id>', methods=['DELETE'])
@require_login_or_default
def delete_advanced_policy(policy_id):
    """删除指定电价策略（高级功能）"""
    user = g.current_user
    policy = PricingPolicy.query.filter_by(id=policy_id, user_id=user.id).first()
    if not policy:
        return jsonify({'error': 'Policy not found'}), 404
    if policy.is_active:
        return jsonify({'error': 'Cannot delete active policy'}), 400

    db.session.delete(policy)
    db.session.commit()
    logger.info(f"Deleted advanced policy: {policy.name}")
    return jsonify({'message': 'Deleted'})
