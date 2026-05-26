# Copyright 2026 smart-ebocr Contributors
# SPDX-License-Identifier: Apache-2.0

"""家庭成员/子账户管理 API

登录用户可以创建和管理家庭成员账户，
用于实现多账户数据隔离。
"""

from flask import Blueprint, g, jsonify, request
from backend.extensions import db
from backend.models.family_member import FamilyMember
from backend.models.daily_usage import DailyUsage
from backend.models.pricing_policy import PricingPolicy
from backend.models.meter import Meter
from backend.api.decorators import require_login_or_default

bp = Blueprint('family_members', __name__)


@bp.route('/', methods=['GET'])
@require_login_or_default
def list_members():
    """获取当前用户的子账户列表"""
    user = g.current_user
    members = FamilyMember.query.filter_by(
        parent_user_id=user.id,
        is_active=True
    ).order_by(FamilyMember.id).all()
    return jsonify({'members': [m.to_dict() for m in members]})


@bp.route('/', methods=['POST'])
@require_login_or_default
@require_login_or_default
def create_member():
    """创建子账户，自动复制主账户电价策略"""
    user = g.current_user
    data = request.get_json()

    if not data or not data.get('name'):
        return jsonify({'error': '成员名称不能为空'}), 400

    member = FamilyMember(
        parent_user_id=user.id,
        name=data['name']
    )
    db.session.add(member)
    db.session.flush()

    # 复制主账户电价策略作为初始值
    default_policy = PricingPolicy.query.filter_by(
        user_id=user.id, family_member_id=None, is_active=True
    ).first()
    if default_policy:
        fields = [
            'region', 'tier1_rate', 'tier1_limit', 'tier2_rate', 'tier2_limit',
            'tier3_rate', 'peak_rate', 'valley_rate', 'heating_valley_rate',
            'sharp_rate', 'flat_rate', 'peak_hours', 'valley_hours',
        ]
        new_policy = PricingPolicy(
            user_id=user.id,
            family_member_id=member.id,
            name=f"{member.name}的电价策略",
            is_active=True,
        )
        for field in fields:
            setattr(new_policy, field, getattr(default_policy, field))
        db.session.add(new_policy)

    db.session.commit()
    return jsonify(member.to_dict()), 201


@bp.route('/<int:id>', methods=['DELETE'])
@require_login_or_default
@require_login_or_default
def delete_member(id):
    """删除子账户，级联删除关联数据"""
    user = g.current_user
    member = FamilyMember.query.filter_by(id=id, parent_user_id=user.id).first()

    if not member:
        return jsonify({'error': '子账户不存在'}), 404

    # 级联删除关联数据
    DailyUsage.query.filter_by(family_member_id=member.id).delete()
    PricingPolicy.query.filter_by(family_member_id=member.id).delete()
    Meter.query.filter_by(family_member_id=member.id).delete()
    db.session.delete(member)
    db.session.commit()

    return '', 204


@bp.route('/<int:id>', methods=['PUT'])
@require_login_or_default
@require_login_or_default
def update_member(id):
    """更新子账户名称"""
    user = g.current_user
    data = request.get_json()

    member = FamilyMember.query.filter_by(id=id, parent_user_id=user.id).first()
    if not member:
        return jsonify({'error': '子账户不存在'}), 404

    if 'name' in data:
        member.name = data['name']

    db.session.commit()
    return jsonify(member.to_dict())
