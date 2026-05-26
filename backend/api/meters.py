# Copyright 2026 smart-ebocr Contributors
# SPDX-License-Identifier: Apache-2.0

from flask import Blueprint, request, jsonify, g

from backend.extensions import db
from backend.models.meter import Meter
from backend.api.decorators import require_login_or_default, get_current_user_or_default

bp = Blueprint('meters', __name__)


@bp.route('/', methods=['GET'])
@require_login_or_default
def list_meters():
    """列出当前用户的电表"""
    user = get_current_user_or_default()
    member_id = request.args.get('family_member_id', type=int)

    query = Meter.query.filter_by(user_id=user.id)
    if member_id:
        query = query.filter_by(family_member_id=member_id)
    else:
        query = query.filter(Meter.family_member_id == None)

    meters = query.order_by(Meter.id).all()
    return jsonify({'meters': [m.to_dict() for m in meters]})


@bp.route('/', methods=['POST'])
@require_login_or_default
@require_login_or_default
def create_meter():
    """创建电表"""
    user = get_current_user_or_default()
    data = request.get_json()
    if not data or 'name' not in data:
        return jsonify({'error': 'name is required'}), 400

    meter = Meter(
        name=data['name'],
        description=data.get('description', ''),
        user_id=user.id,
        family_member_id=data.get('family_member_id'),
    )
    db.session.add(meter)
    db.session.commit()
    return jsonify(meter.to_dict()), 201


@bp.route('/<int:meter_id>', methods=['GET'])
@require_login_or_default
@require_login_or_default
def get_meter(meter_id):
    """获取单个电表"""
    user = get_current_user_or_default()
    meter = Meter.query.filter_by(id=meter_id, user_id=user.id).first()
    if not meter:
        return jsonify({'error': 'Meter not found'}), 404
    return jsonify(meter.to_dict())


@bp.route('/<int:meter_id>', methods=['PUT'])
@require_login_or_default
@require_login_or_default
def update_meter(meter_id):
    """更新电表"""
    user = get_current_user_or_default()
    meter = Meter.query.filter_by(id=meter_id, user_id=user.id).first()
    if not meter:
        return jsonify({'error': 'Meter not found'}), 404

    data = request.get_json()
    if data.get('name'):
        meter.name = data['name']
    if 'description' in data:
        meter.description = data['description']

    db.session.commit()
    return jsonify(meter.to_dict())


@bp.route('/<int:meter_id>', methods=['DELETE'])
@require_login_or_default
@require_login_or_default
def delete_meter(meter_id):
    """删除电表"""
    user = get_current_user_or_default()
    meter = Meter.query.filter_by(id=meter_id, user_id=user.id).first()
    if not meter:
        return jsonify({'error': 'Meter not found'}), 404

    db.session.delete(meter)
    db.session.commit()
    return jsonify({'message': 'Deleted'})
