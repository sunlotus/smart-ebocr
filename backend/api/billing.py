# Copyright 2026 smart-ebocr Contributors
# SPDX-License-Identifier: Apache-2.0

from flask import Blueprint, request, jsonify, send_file, g

from backend.services.billing_service import BillingService
from backend.api.decorators import require_login_or_default, get_current_user_or_default
from backend.utils.logger import get_logger

bp = Blueprint('billing', __name__)
logger = get_logger(__name__)


def _get_billing_context():
    """获取计费上下文"""
    user = get_current_user_or_default()
    member_id = request.args.get('family_member_id', type=int)
    if member_id and user.plan_name in ['supporter', 'premium', 'super']:
        from backend.models.family_member import FamilyMember
        member = FamilyMember.query.filter_by(id=member_id, parent_user_id=user.id).first()
        if member:
            return {'user_id': user.id, 'family_member_id': member_id}
    return {'user_id': user.id, 'family_member_id': None}


@bp.route('/compare', methods=['GET'])
@require_login_or_default
def compare():
    """Compare flat-rate vs time-of-use billing for a given month."""
    year = request.args.get('year', type=int)
    month = request.args.get('month', type=int)
    if not year or not month:
        logger.warning("Billing compare: missing year or month parameter")
        return jsonify({'error': 'year and month are required'}), 400

    ctx = _get_billing_context()
    logger.debug(f"Billing compare request: {year}-{month:02d}, context={ctx}")
    result = BillingService.compare_month(year, month, user_id=ctx['user_id'], family_member_id=ctx['family_member_id'])

    if 'flat_cost' in result and 'tou_cost' in result:
        savings = result.get('savings', 0)
        logger.info(f"Billing compare: flat=¥{result['flat_cost']:.2f}, tou=¥{result['tou_cost']:.2f}, savings=¥{savings:.2f}")

    return jsonify(result)


@bp.route('/annual', methods=['GET'])
@require_login_or_default
def annual():
    """Annual billing summary."""
    year = request.args.get('year', type=int)
    if not year:
        logger.warning("Annual billing: missing year parameter")
        return jsonify({'error': 'year is required'}), 400

    ctx = _get_billing_context()
    logger.debug(f"Annual billing request: {year}")
    result = BillingService.annual_summary(year, user_id=ctx['user_id'], family_member_id=ctx['family_member_id'])

    if 'total_flat_cost' in result:
        logger.info(f"Annual billing: {year}, flat=¥{result['total_flat_cost']:.2f}, tou=¥{result['total_tou_cost']:.2f}")

    return jsonify(result)


@bp.route('/annual-pdf', methods=['GET'])
@require_login_or_default
def annual_pdf():
    """生成年度 PDF 报告 — 高级功能"""
    import io
    from datetime import datetime

    year = request.args.get('year', type=int)
    if not year:
        return jsonify({'error': 'year is required'}), 400

    ctx = _get_billing_context()
    result = BillingService.annual_summary(year, user_id=ctx['user_id'], family_member_id=ctx['family_member_id'])

    try:
        from reportlab.lib.pagesizes import A4
        from reportlab.lib.units import mm
        from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
        from reportlab.lib.styles import getSampleStyleSheet
        from reportlab.lib import colors
        from reportlab.pdfbase import pdfmetrics
        from reportlab.pdfbase.ttfonts import TTFont
        import os

        # 中文字体注册（ReportLab TTFont 仅支持 TrueType 轮廓，不支持 CFF/OTF）
        font_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'fonts')
        font_name = None
        bold_name = None

        def _try_register(fp, name):
            """尝试注册字体，TTC 文件需指定 subfontIndex"""
            if not os.path.exists(fp):
                return False
            try:
                if fp.endswith('.ttc'):
                    pdfmetrics.registerFont(TTFont(name, fp, subfontIndex=0))
                else:
                    pdfmetrics.registerFont(TTFont(name, fp))
                logger.info(f'PDF 字体注册成功: {fp}')
                return True
            except Exception as e:
                logger.warning(f'PDF 字体注册失败 {fp}: {e}')
                return False

        # 按优先级尝试：静态 TTF > 系统 TTF > 可变 TTF > CID 内置
        # 注意：可变 TTF 默认字重为 Thin(100)，系统/静态字体字重更合适
        regular_candidates = [
            os.path.join(font_dir, 'NotoSansSC-Regular.ttf'),      # 项目内嵌静态 TTF
            'C:/Windows/Fonts/msyh.ttc',                           # Windows 微软雅黑
            '/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc',  # Linux Noto
            '/usr/share/fonts/truetype/noto/NotoSansCJK-Regular.ttc',
            os.path.join(font_dir, 'NotoSansSC-VF.ttf'),           # 可变字体兜底
        ]
        bold_candidates = [
            os.path.join(font_dir, 'NotoSansSC-Bold.ttf'),
            'C:/Windows/Fonts/msyhbd.ttc',
            '/usr/share/fonts/opentype/noto/NotoSansCJK-Bold.ttc',
            '/usr/share/fonts/truetype/noto/NotoSansCJK-Bold.ttc',
            os.path.join(font_dir, 'NotoSansSC-VF.ttf'),
        ]

        for fp in regular_candidates:
            if _try_register(fp, 'CJKFont'):
                font_name = 'CJKFont'
                break
        for fp in bold_candidates:
            if _try_register(fp, 'CJKFont-Bold'):
                bold_name = 'CJKFont-Bold'
                break

        # 保底：ReportLab 内置 CID 字体（华文宋体，无需外部文件）
        if not font_name:
            from reportlab.pdfbase.cidfonts import UnicodeCIDFont
            pdfmetrics.registerFont(UnicodeCIDFont('STSong-Light'))
            font_name = 'STSong-Light'
            bold_name = 'STSong-Light'
            logger.info('PDF 使用内置 CID 字体 STSong-Light')

        buffer = io.BytesIO()
        doc = SimpleDocTemplate(buffer, pagesize=A4,
                                leftMargin=20*mm, rightMargin=20*mm,
                                topMargin=20*mm, bottomMargin=20*mm)

        styles = getSampleStyleSheet()
        title_style = styles['Title']
        normal_style = styles['Normal']

        # 应用中文字体到样式
        if font_name:
            title_style.fontName = bold_name
            title_style.fontSize = 18
            normal_style.fontName = font_name

        elements = []

        # 标题
        elements.append(Paragraph(f'{year} 年度用电报告', title_style))
        elements.append(Spacer(1, 10*mm))

        # 年度汇总
        total_flat = result.get('total_flat_cost', 0)
        total_tou = result.get('total_tou_cost', 0)
        total_savings = result.get('total_savings', 0)

        summary_data = [
            ['项目', '金额'],
            ['阶梯电费合计', f'¥{total_flat:.2f}'],
            ['峰谷电费合计', f'¥{total_tou:.2f}'],
            ['节省金额', f'¥{total_savings:.2f}'],
            ['更省方案', {'flat': '阶梯电价', 'tou': '峰谷电价', 'equal': '两者相同'}.get(result.get('cheaper_method'), 'N/A')],
        ]
        table = Table(summary_data, colWidths=[80*mm, 60*mm])
        table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#1e40af')),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
            ('FONTNAME', (0, 0), (-1, -1), font_name),
            ('FONTNAME', (0, 0), (-1, 0), bold_name),
            ('FONTSIZE', (0, 0), (-1, -1), 10),
            ('PADDING', (0, 0), (-1, -1), 6),
        ]))
        elements.append(table)
        elements.append(Spacer(1, 10*mm))

        # 逐月明细
        monthly = result.get('monthly_summaries', [])
        if monthly:
            month_data = [['月份', '用电量(kWh)', '阶梯电费', '峰谷电费', '节省']]
            for m in monthly:
                if m.get('total_kwh', 0) > 0:
                    month_data.append([
                        f"{m.get('month', '')}",
                        f"{m.get('total_kwh', 0):.1f}",
                        f"¥{m.get('flat_cost', 0):.2f}",
                        f"¥{m.get('tou_cost', 0):.2f}",
                        f"¥{m.get('savings', 0):.2f}",
                    ])

            if len(month_data) > 1:
                month_table = Table(month_data, colWidths=[25*mm, 30*mm, 35*mm, 35*mm, 30*mm])
                month_table.setStyle(TableStyle([
                    ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#3b82f6')),
                    ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
                    ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
                    ('FONTNAME', (0, 0), (-1, -1), font_name),
                    ('FONTNAME', (0, 0), (-1, 0), bold_name),
                    ('FONTSIZE', (0, 0), (-1, -1), 9),
                    ('PADDING', (0, 0), (-1, -1), 4),
                ]))
                elements.append(month_table)

        # 生成时间
        elements.append(Spacer(1, 15*mm))
        elements.append(Paragraph(
            f'生成时间: {datetime.now().strftime("%Y-%m-%d %H:%M")}',
            normal_style
        ))

        doc.build(elements)
        buffer.seek(0)

        return send_file(
            buffer,
            mimetype='application/pdf',
            as_attachment=True,
            download_name=f'electricity-report-{year}.pdf',
        )

    except ImportError:
        return jsonify({'error': 'PDF generation requires reportlab package'}), 500