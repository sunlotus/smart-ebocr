# Copyright 2026 smart-ebocr Contributors
# SPDX-License-Identifier: Apache-2.0

from datetime import date as date_type
from flask import Blueprint, request, jsonify, g

from backend.extensions import db
from backend.models.daily_usage import DailyUsage
from backend.services.data_service import DataService
from backend.api.decorators import require_login_or_default, get_current_user_or_default
from backend.utils.logger import get_logger, log_exception

bp = Blueprint('usage', __name__)
logger = get_logger(__name__)


def _split_flat_by_tier(total_kwh, policy, year_cumulative_before):
    """将分时电价费用按阶梯拆分为 [tier1_cost, tier2_cost, tier3_cost]"""
    tier_costs = [0.0, 0.0, 0.0]
    remaining = total_kwh
    tier1_remaining = max(0, policy.tier1_limit - year_cumulative_before)
    tier2_remaining = max(0, policy.tier2_limit - year_cumulative_before)

    t1 = min(remaining, tier1_remaining)
    tier_costs[0] = round(t1 * policy.tier1_rate, 2)
    remaining -= t1

    if remaining > 0:
        t2_capacity = tier2_remaining - tier1_remaining
        t2 = min(remaining, max(0, t2_capacity))
        tier_costs[1] = round(t2 * policy.tier2_rate, 2)
        remaining -= t2

    if remaining > 0:
        tier_costs[2] = round(remaining * policy.tier3_rate, 2)

    return tier_costs


def _calc_distribution(records):
    """计算日用电量分布直方图"""
    if not records:
        return {'buckets': [], 'median': 0, 'average': 0}

    values = sorted(r.total_kwh for r in records)
    avg = round(sum(values) / len(values), 2)
    mid = len(values) // 2
    median = round((values[mid] + values[~mid]) / 2, 2) if len(values) % 2 == 0 else round(values[mid], 2)

    bucket_size = 5
    max_val = max(values)
    buckets = []
    for low in range(0, int(max_val) + bucket_size, bucket_size):
        high = low + bucket_size
        count_heating = sum(1 for r in records
                          if low <= r.total_kwh < high and r.date.month in (11, 12, 1, 2, 3))
        count_non_heating = sum(1 for r in records
                              if low <= r.total_kwh < high and r.date.month not in (11, 12, 1, 2, 3))
        buckets.append({
            'range': f'{low}-{high}',
            'count_heating': count_heating,
            'count_non_heating': count_non_heating,
        })

    return {'buckets': buckets, 'median': median, 'average': avg}


def _calc_compare_trend(query_month, year, month):
    """计算同比环比数据"""
    current_total = round(sum(r.total_kwh for r in query_month(year, month)), 2)
    prev_year_total = round(sum(r.total_kwh for r in query_month(year - 1, month)), 2)
    prev_month = month - 1 if month > 1 else 12
    prev_month_year = year if month > 1 else year - 1
    prev_month_total = round(sum(r.total_kwh for r in query_month(prev_month_year, prev_month)), 2)

    monthly_totals = [round(sum(r.total_kwh for r in query_month(year, m)), 2) for m in range(1, 13)]
    prev_year_totals = [round(sum(r.total_kwh for r in query_month(year - 1, m)), 2) for m in range(1, 13)]

    yoy_change = round((current_total - prev_year_total) / prev_year_total * 100, 1) if prev_year_total > 0 else None
    mom_change = round((current_total - prev_month_total) / prev_month_total * 100, 1) if prev_month_total > 0 else None

    return {
        'year': year, 'month': month,
        'current_total': current_total,
        'prev_year_total': prev_year_total,
        'prev_month_total': prev_month_total,
        'yoy_change': yoy_change,
        'mom_change': mom_change,
        'monthly_totals': monthly_totals,
        'prev_year_totals': prev_year_totals,
    }


def _calc_forecast(query_month, year):
    """计算预测数据"""
    monthly_totals = [round(sum(r.total_kwh for r in query_month(year, m)), 2) for m in range(1, 13)]
    last_year_monthly = [round(sum(r.total_kwh for r in query_month(year - 1, m)), 2) for m in range(1, 13)]

    valid_months = [t for t in monthly_totals if t > 0]
    avg_monthly = round(sum(valid_months) / len(valid_months), 2) if valid_months else 0

    last_year_total = sum(last_year_monthly)
    forecast = []
    for m in range(12):
        if monthly_totals[m] > 0:
            forecast.append({'month': m + 1, 'value': monthly_totals[m], 'type': 'actual'})
        elif last_year_total > 0 and last_year_monthly[m] > 0:
            ratio = last_year_monthly[m] / (last_year_total / 12)
            forecast.append({'month': m + 1, 'value': round(avg_monthly * ratio, 2), 'type': 'forecast'})
        else:
            forecast.append({'month': m + 1, 'value': avg_monthly, 'type': 'forecast'})

    return {
        'year': year,
        'forecast': forecast,
        'avg_monthly': avg_monthly,
        'forecasted_total': round(sum(f['value'] for f in forecast), 2),
    }


def _parse_date(date_str):
    """Parse date string to Python date object."""
    if isinstance(date_str, date_type):
        return date_str
    return date_type.fromisoformat(date_str)


def get_current_context():
    """获取当前用户上下文（user_id, family_member_id）"""
    user = get_current_user_or_default()
    member_id = request.args.get('family_member_id', type=int)

    # 如果指定了 member_id，检查权限（supporter 及以上）
    if member_id and user.plan_name in ['supporter', 'premium', 'super']:
        from backend.models.family_member import FamilyMember
        member = FamilyMember.query.filter_by(id=member_id, parent_user_id=user.id).first()
        if member:
            return {'user_id': user.id, 'family_member_id': member_id}

    return {'user_id': user.id, 'family_member_id': None}


@bp.route('/', methods=['GET'])
@require_login_or_default
def list_usage():
    """List daily usage records for a given month, with yearly cumulative and warnings."""
    year = request.args.get('year', type=int)
    month = request.args.get('month', type=int)
    if not year or not month:
        logger.warning("List usage: missing year or month parameter")
        return jsonify({'error': 'year and month are required'}), 400

    context = get_current_context()
    logger.debug(f"Listing usage: year={year}, month={month}, context={context}")

    # 基础查询：用户/子账户过滤
    query = DailyUsage.query
    if context['family_member_id']:
        query = query.filter_by(family_member_id=context['family_member_id'])
    else:
        query = query.filter_by(user_id=context['user_id'], family_member_id=None)

    # 月份过滤
    records = query.filter(
        db.extract('year', DailyUsage.date) == year,
        db.extract('month', DailyUsage.date) == month,
    ).order_by(DailyUsage.date).all()

    # Calculate yearly cumulative before this month
    prev_records = query.filter(
        db.extract('year', DailyUsage.date) == year,
        db.extract('month', DailyUsage.date) < month,
    ).all()
    year_cumulative_before = round(sum(r.total_kwh for r in prev_records), 2)

    # Build response with per-day yearly cumulative and validation warnings
    result = []
    running = year_cumulative_before
    for r in records:
        running = round(running + r.total_kwh, 2)
        item = r.to_dict()
        item['yearly_cumulative_kwh'] = running
        item['warnings'] = DataService.validate_record(item)
        result.append(item)

    logger.info(f"List usage: found {len(records)} records for {year}-{month:02d}, year_cumulative_before={year_cumulative_before}")
    return jsonify({
        'records': result,
        'year_cumulative_before': year_cumulative_before,
    })


@bp.route('/check-conflicts', methods=['POST'])
@require_login_or_default
def check_conflicts():
    """Check which dates already have records. Body: {dates: [...]}."""
    data = request.get_json()
    if not data or 'dates' not in data:
        return jsonify({'error': 'dates array is required'}), 400

    context = get_current_context()
    conflicts = DataService.check_conflicts(
        data['dates'],
        user_id=context['user_id'],
        family_member_id=context['family_member_id']
    )
    return jsonify({'conflicts': conflicts})


@bp.route('/', methods=['POST'])
@require_login_or_default
def add_usage():
    """Add or update a daily usage record."""
    data = request.get_json()
    if not data or 'date' not in data or 'total_kwh' not in data:
        logger.warning("Add usage: missing required fields")
        return jsonify({'error': 'date and total_kwh are required'}), 400

    context = get_current_context()
    warnings = DataService.validate_record(data)
    d = _parse_date(data['date'])

    # 查找冲突记录时考虑用户上下文
    conflict = DailyUsage.query.filter_by(
        date=d,
        user_id=context['user_id'],
        family_member_id=context['family_member_id']
    ).first() is not None
    is_new = not conflict

    if conflict:
        logger.debug(f"Updating usage record for {data['date']}")
        record = DailyUsage.query.filter_by(
            date=d,
            user_id=context['user_id'],
            family_member_id=context['family_member_id']
        ).first()
        record.total_kwh = data['total_kwh']
        record.peak_kwh = data.get('peak_kwh', 0)
        record.valley_kwh = data.get('valley_kwh', 0)
        record.sharp_kwh = data.get('sharp_kwh', 0)
        record.flat_kwh = data.get('flat_kwh', 0)
        record.source = data.get('source', 'manual')
    else:
        logger.debug(f"Creating new usage record for {data['date']}")
        record = DailyUsage(
            date=d,
            total_kwh=data['total_kwh'],
            peak_kwh=data.get('peak_kwh', 0),
            valley_kwh=data.get('valley_kwh', 0),
            sharp_kwh=data.get('sharp_kwh', 0),
            flat_kwh=data.get('flat_kwh', 0),
            source=data.get('source', 'manual'),
            user_id=context['user_id'],
            family_member_id=context['family_member_id'],
        )
        db.session.add(record)

    db.session.commit()
    action = 'updated' if not is_new else 'created'
    logger.info(f"Usage record {action}: {data['date']}, {data['total_kwh']} kWh")
    return jsonify({
        **record.to_dict(),
        'warnings': warnings,
        'conflict': not is_new,
    })


@bp.route('/batch', methods=['POST'])
@require_login_or_default
def batch_add():
    """Batch add or update daily usage records."""
    data = request.get_json()
    if not data or 'records' not in data:
        logger.warning("Batch add: missing records array")
        return jsonify({'error': 'records array is required'}), 400

    record_count = len(data['records'])
    conflict_mode = data.get('conflict_mode', 'overwrite')
    logger.info(f"Batch add: processing {record_count} records, conflict_mode={conflict_mode}")

    # Set default source for records that don't have one
    for item in data['records']:
        item.setdefault('source', 'manual')

    context = get_current_context()
    result = DataService.batch_upsert(
        data['records'],
        conflict_mode=conflict_mode,
        user_id=context['user_id'],
        family_member_id=context['family_member_id']
    )
    logger.info(f"Batch add complete: saved={result['saved']}, skipped={result['skipped']}")
    return jsonify(result)


@bp.route('/batch', methods=['DELETE'])
@require_login_or_default
def batch_delete():
    """Batch delete daily usage records."""
    data = request.get_json()
    if not data or 'dates' not in data:
        logger.warning("Batch delete: missing dates array")
        return jsonify({'error': 'dates array is required'}), 400

    dates = data['dates']
    if not dates:
        logger.warning("Batch delete: empty dates array")
        return jsonify({'error': 'dates array is empty'}), 400

    context = get_current_context()
    query = DailyUsage.query.filter(
        DailyUsage.date.in_([_parse_date(d) for d in dates]),
        DailyUsage.user_id == context['user_id'],
        DailyUsage.family_member_id == context['family_member_id'],
    )
    count = query.delete(synchronize_session=False)

    db.session.commit()
    logger.info(f"Batch delete: {count}/{len(dates)} records deleted")
    return jsonify({'message': f'{count} records deleted'})


@bp.route('/<date_str>', methods=['DELETE'])
@require_login_or_default
def delete_usage(date_str):
    """Delete a daily usage record."""
    d = _parse_date(date_str)
    context = get_current_context()
    record = DailyUsage.query.filter_by(
        date=d,
        user_id=context['user_id'],
        family_member_id=context['family_member_id']
    ).first()
    if not record:
        logger.warning(f"Delete usage: record not found for {date_str}")
        return jsonify({'error': 'Record not found'}), 404

    logger.info(f"Deleting usage record: {date_str}")
    db.session.delete(record)
    db.session.commit()
    return jsonify({'message': 'Deleted'})


@bp.route('/compare-trend', methods=['GET'])
@require_login_or_default
def compare_trend():
    """同比环比趋势数据 — 高级功能"""
    year = request.args.get('year', type=int)
    month = request.args.get('month', type=int)

    if not year or not month:
        return jsonify({'error': 'year and month are required'}), 400

    context = get_current_context()

    # 构建基础查询
    def query_month(y, m):
        q = DailyUsage.query
        if context['family_member_id']:
            q = q.filter_by(family_member_id=context['family_member_id'])
        else:
            q = q.filter_by(user_id=context['user_id'], family_member_id=None)
        return q.filter(
            db.extract('year', DailyUsage.date) == y,
            db.extract('month', DailyUsage.date) == m,
        ).all()

    # 当月数据
    current_records = query_month(year, month)
    current_total = round(sum(r.total_kwh for r in current_records), 2)

    # 去年同月（同比）
    prev_year_records = query_month(year - 1, month)
    prev_year_total = round(sum(r.total_kwh for r in prev_year_records), 2)

    # 上月（环比）
    prev_month = month - 1 if month > 1 else 12
    prev_month_year = year if month > 1 else year - 1
    prev_month_records = query_month(prev_month_year, prev_month)
    prev_month_total = round(sum(r.total_kwh for r in prev_month_records), 2)

    # 全年逐月数据
    monthly_totals = []
    for m in range(1, 13):
        records = query_month(year, m)
        monthly_totals.append(round(sum(r.total_kwh for r in records), 2))

    yoy_change = None
    if prev_year_total > 0:
        yoy_change = round((current_total - prev_year_total) / prev_year_total * 100, 1)

    mom_change = None
    if prev_month_total > 0:
        mom_change = round((current_total - prev_month_total) / prev_month_total * 100, 1)

    return jsonify({
        'year': year,
        'month': month,
        'current_total': current_total,
        'prev_year_total': prev_year_total,
        'prev_month_total': prev_month_total,
        'yoy_change': yoy_change,  # 同比变化百分比
        'mom_change': mom_change,  # 环比变化百分比
        'monthly_totals': monthly_totals,
    })


@bp.route('/forecast', methods=['GET'])
@require_login_or_default
def forecast():
    """用电趋势预测 — 基于历史数据的简单移动平均"""
    year = request.args.get('year', type=int)
    if not year:
        return jsonify({'error': 'year is required'}), 400

    context = get_current_context()

    # 构建基础查询
    def query_month(y, m):
        q = DailyUsage.query
        if context['family_member_id']:
            q = q.filter_by(family_member_id=context['family_member_id'])
        else:
            q = q.filter_by(user_id=context['user_id'], family_member_id=None)
        return q.filter(
            db.extract('year', DailyUsage.date) == y,
            db.extract('month', DailyUsage.date) == m,
        ).all()

    # 收集全年逐月数据
    monthly_totals = []
    for m in range(1, 13):
        records = query_month(year, m)
        monthly_totals.append(round(sum(r.total_kwh for r in records), 2))

    # 收集去年逐月数据用于季节性调整
    last_year_monthly = []
    for m in range(1, 13):
        records = query_month(year - 1, m)
        last_year_monthly.append(round(sum(r.total_kwh for r in records), 2))

    # 计算已有的有效月数
    valid_months = [t for t in monthly_totals if t > 0]
    avg_monthly = round(sum(valid_months) / len(valid_months), 2) if valid_months else 0

    # 简单预测：用历史季节性比例 + 当前平均值
    last_year_total = sum(last_year_monthly)
    forecast = []
    for m in range(12):
        if monthly_totals[m] > 0:
            forecast.append({'month': m + 1, 'value': monthly_totals[m], 'type': 'actual'})
        elif last_year_total > 0 and last_year_monthly[m] > 0:
            ratio = last_year_monthly[m] / (last_year_total / 12)
            predicted = round(avg_monthly * ratio, 2)
            forecast.append({'month': m + 1, 'value': predicted, 'type': 'forecast'})
        else:
            forecast.append({'month': m + 1, 'value': avg_monthly, 'type': 'forecast'})

    # 年度预测总量
    forecasted_total = round(sum(f['value'] for f in forecast), 2)

    return jsonify({
        'year': year,
        'forecast': forecast,
        'avg_monthly': avg_monthly,
        'forecasted_total': forecasted_total,
    })


@bp.route('/annual-dashboard', methods=['GET'])
@require_login_or_default
def annual_dashboard():
    """年度分析仪表盘聚合数据 — 高级功能"""
    year = request.args.get('year', type=int)
    if not year:
        return jsonify({'error': 'year is required'}), 400

    context = get_current_context()
    user_id = context['user_id']
    member_id = context['family_member_id']

    from backend.services.billing_service import BillingService

    # 获取活跃电价策略
    policy = BillingService.get_active_policy(user_id=user_id, family_member_id=member_id)
    if not policy:
        return jsonify({'error': 'No active pricing policy'}), 404

    # 基础查询函数
    def query_month(y, m):
        q = DailyUsage.query
        if member_id:
            q = q.filter_by(family_member_id=member_id)
        else:
            q = q.filter_by(user_id=user_id, family_member_id=None)
        return q.filter(
            db.extract('year', DailyUsage.date) == y,
            db.extract('month', DailyUsage.date) == m,
        ).all()

    # 全年日度记录
    all_records = []
    monthly_records = {}
    for m in range(1, 13):
        recs = query_month(year, m)
        monthly_records[m] = recs
        all_records.extend(recs)

    # --- 汇总 ---
    total_kwh = round(sum(r.total_kwh for r in all_records), 2)
    peak_kwh = round(sum(r.peak_kwh for r in all_records), 2)
    valley_kwh = round(sum(r.valley_kwh for r in all_records), 2)
    avg_daily = round(total_kwh / len(all_records), 2) if all_records else 0

    # --- 逐月明细（含计费） ---
    cumulative = 0.0
    monthly_breakdown = []
    for m in range(1, 13):
        recs = monthly_records[m]
        m_total = round(sum(r.total_kwh for r in recs), 2)
        m_peak = round(sum(r.peak_kwh for r in recs), 2)
        m_valley = round(sum(r.valley_kwh for r in recs), 2)
        m_sharp = round(sum(r.sharp_kwh for r in recs), 2)
        m_flat_kwh = round(sum(r.flat_kwh for r in recs), 2)
        cumulative_before = cumulative
        cumulative = round(cumulative + m_total, 2)

        flat_cost = BillingService.calculate_flat_billing(m_total, policy, cumulative_before)
        tou_cost = BillingService.calculate_tou_billing(
            m_peak, m_valley, m_sharp, m_flat_kwh, m_total, policy,
            month=m, year_cumulative_before=cumulative_before
        )

        # 阶梯费用拆分
        flat_cost_by_tier = _split_flat_by_tier(m_total, policy, cumulative_before)

        monthly_breakdown.append({
            'month': m,
            'total_kwh': m_total,
            'peak_kwh': m_peak,
            'valley_kwh': m_valley,
            'flat_cost': flat_cost,
            'flat_cost_by_tier': flat_cost_by_tier,
            'tou_cost': tou_cost,
            'savings': round(flat_cost - tou_cost, 2),
            'cumulative_kwh': cumulative,
        })

    total_flat = round(sum(mb['flat_cost'] for mb in monthly_breakdown), 2)
    total_tou = round(sum(mb['tou_cost'] for mb in monthly_breakdown), 2)

    # --- 阶梯进度 ---
    projected_year_end = round(avg_daily * 365, 2) if avg_daily > 0 else 0

    # --- 用电分布 ---
    distribution = _calc_distribution(all_records)

    # --- 季节对比 ---
    heating_total = heating_peak = heating_valley = 0
    non_heating_total = non_heating_peak = non_heating_valley = 0
    heating_months = non_heating_months = 0
    for m in range(1, 13):
        recs = monthly_records[m]
        if BillingService.is_heating_season(m):
            heating_total += sum(r.total_kwh for r in recs)
            heating_peak += sum(r.peak_kwh for r in recs)
            heating_valley += sum(r.valley_kwh for r in recs)
            if recs:
                heating_months += 1
        else:
            non_heating_total += sum(r.total_kwh for r in recs)
            non_heating_peak += sum(r.peak_kwh for r in recs)
            non_heating_valley += sum(r.valley_kwh for r in recs)
            if recs:
                non_heating_months += 1

    # --- 同比环比 ---
    current_month = __import__('datetime').datetime.now().month
    compare_data = _calc_compare_trend(query_month, year, current_month)

    # --- 预测 ---
    forecast_data = _calc_forecast(query_month, year)

    return jsonify({
        'year': year,
        'summary': {
            'total_kwh': total_kwh,
            'peak_kwh': peak_kwh,
            'valley_kwh': valley_kwh,
            'total_cost_flat': total_flat,
            'total_cost_tou': total_tou,
            'savings': round(total_flat - total_tou, 2),
            'avg_daily': avg_daily,
        },
        'tier_progress': {
            'cumulative': cumulative,
            'tier1_limit': policy.tier1_limit,
            'tier2_limit': policy.tier2_limit,
            'tier1_rate': policy.tier1_rate,
            'tier2_rate': policy.tier2_rate,
            'tier3_rate': policy.tier3_rate,
            'projected_year_end': projected_year_end,
        },
        'monthly_breakdown': monthly_breakdown,
        'distribution': distribution,
        'seasonal': {
            'heating': {
                'total_kwh': round(heating_total, 2),
                'peak_kwh': round(heating_peak, 2),
                'valley_kwh': round(heating_valley, 2),
                'months': heating_months,
            },
            'non_heating': {
                'total_kwh': round(non_heating_total, 2),
                'peak_kwh': round(non_heating_peak, 2),
                'valley_kwh': round(non_heating_valley, 2),
                'months': non_heating_months,
            },
        },
        'compare_trend': compare_data,
        'forecast': forecast_data,
    })