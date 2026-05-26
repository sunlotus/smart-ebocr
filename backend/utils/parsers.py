# Copyright 2026 smart-ebocr Contributors
# SPDX-License-Identifier: Apache-2.0

"""Parse OCR output into structured electricity data.

Strategy: Extract data from the statistics module (统计模块) of the
electricity app screenshot. Each screenshot contains one day's data:
date, total kWh, and peak/valley/sharp/flat breakdown.
"""

import re
from datetime import date

from backend.utils.logger import get_ocr_logger

_ocr_logger = get_ocr_logger()

# Common OCR misreads for digits
DIGIT_FIXES = {
    'O': '0', 'o': '0', 'l': '1', 'I': '1', '|': '1',
    'S': '5', 's': '5', 'B': '8', 'g': '9',
}
BRACKET_FIXES = {']': '1', '[': '1', ')': '1', '(': '1'}

# Regex patterns for statistics module
DATE_RE = re.compile(r'(\d{1,2})\s*月\s*(\d{1,2})\s*日')
TOTAL_KWH_RE = re.compile(r'(\d+\.?\d*)\s*千瓦时')
# 尖/峰/平: strict match (label immediately before value)
# 谷: allow 1 extra OCR token between label and value (e.g., "国 从 2.97")
PERIOD_PATTERNS = {
    'sharp_kwh': re.compile(r'尖\s*(\d+\.?\d*)'),
    'peak_kwh': re.compile(r'峰\s*(\d+\.?\d*)'),
    'flat_kwh': re.compile(r'平\s*(\d+\.?\d*)'),
    'valley_kwh': re.compile(r'[谷国图](?!\s*(?:峰|平|尖))(?:\s+[^\d\s]+)?\s*(\d+\.?\d*)'),
}


def _fix_ocr_digits(text):
    """Fix common OCR digit misreads in a string."""
    result = []
    for ch in text:
        if ch in DIGIT_FIXES:
            result.append(DIGIT_FIXES[ch])
        elif ch in BRACKET_FIXES:
            result.append(BRACKET_FIXES[ch])
        else:
            result.append(ch)
    return ''.join(result)


def _try_parse_number(text):
    """Try to parse text as a kWh number, applying OCR fixes.

    Returns float or None.
    """
    text = text.strip()
    fixed = _fix_ocr_digits(text)
    fixed = fixed.replace(' ', '')

    if fixed.startswith('.'):
        fixed = '0' + fixed

    if not any(c.isdigit() for c in fixed):
        return None

    try:
        val = float(fixed)
        if 0 <= val <= 200:
            return val
    except ValueError:
        pass

    return None


def _join_text(text_blocks):
    """Concatenate all text blocks into a single string for regex matching."""
    parts = []
    for block in text_blocks:
        text = block.get('text', '').strip()
        if text:
            parts.append(_fix_ocr_digits(text))
    return ' '.join(parts)


def parse_stats_module(text_blocks, year, month):
    """Parse statistics module from OCR text blocks.

    Extracts one day's data: date, total kWh, sharp/peak/flat/valley kWh.

    Args:
        text_blocks: List of dicts with 'text', 'x', 'y', 'w', 'h', 'conf'.
        year: The year for date context.
        month: The month for date context (fallback if date has no month).

    Returns:
        dict with 'daily_records' (list with one item) and 'warnings' (list).
    """
    if not text_blocks:
        _ocr_logger.warning("parse_stats_module: 无 text_blocks 输入")
        return {'daily_records': [], 'warnings': ['OCR 未识别到任何文本']}

    full_text = _join_text(text_blocks)
    _ocr_logger.info(f"parse_stats_module: 输入 {len(text_blocks)} 个 text block, year={year}, month={month}")
    _ocr_logger.debug(f"parse_stats_module: joined 全文（前500字）: {full_text[:500]}")

    warnings = []

    # 1. Extract date
    m = DATE_RE.search(full_text)
    if not m:
        _ocr_logger.warning(f"parse_stats_module: 未找到日期（'X月X日'模式），原文前100字: {full_text[:100]}")
        return {
            'daily_records': [],
            'warnings': [f'未找到日期（"X月X日"模式），原文前100字符: {full_text[:100]}'],
        }

    parsed_month = int(m.group(1))
    day = int(m.group(2))
    date_end = m.end()
    _ocr_logger.debug(f"parse_stats_module: 日期正则匹配: 月={parsed_month}, 日={day}")
    try:
        row_date = date(year, parsed_month, day)
        _ocr_logger.info(f"parse_stats_module: 解析日期: {row_date.isoformat()}")
    except ValueError:
        _ocr_logger.error(f"parse_stats_module: 日期无效: {parsed_month}月{day}日")
        return {
            'daily_records': [],
            'warnings': [f'日期无效: {parsed_month}月{day}日'],
        }

    # 时段值搜索范围限定在日期之后（排除 UI 噪音干扰）
    stats_text = full_text[date_end:]

    # 2. Extract period kWh values (尖/峰/平/谷)
    record = {
        'date': row_date.isoformat(),
        'sharp_kwh': 0,
        'peak_kwh': 0,
        'flat_kwh': 0,
        'valley_kwh': 0,
    }

    for key, pattern in PERIOD_PATTERNS.items():
        m = pattern.search(stats_text)
        if m:
            raw = m.group(1)
            val = _try_parse_number(raw)
            if val is not None:
                record[key] = val
                _ocr_logger.debug(f"parse_stats_module: {key} 匹配成功, raw='{raw}', val={val}")
            else:
                _ocr_logger.warning(f"parse_stats_module: {key} 匹配到 '{raw}' 但无法解析为数字")
        else:
            _ocr_logger.debug(f"parse_stats_module: {key} 未匹配到值")

    # 2.5 Extract total kWh from OCR and calibrate peak/valley
    ocr_total = None

    # Method 1: Find number on the same line as "用电量" header (right side of screen)
    usage_header_y = None
    for block in text_blocks:
        text = block.get('text', '')
        if '用电量' in text and '千瓦时' in text:
            usage_header_y = block.get('y', 0)
            break

    if usage_header_y is not None:
        candidates = []
        for block in text_blocks:
            by = block.get('y', 0)
            if abs(by - usage_header_y) <= 10:  # same line (within 10px)
                val = _try_parse_number(block.get('text', ''))
                if val is not None and block.get('x', 0) > 400:  # right side of screen
                    candidates.append(val)
        if candidates:
            ocr_total = candidates[-1]  # take the rightmost number
            _ocr_logger.debug(f"parse_stats_module: OCR 总电量={ocr_total} (坐标匹配法)")

    # Method 2: Fallback to regex "数字 千瓦时" or "千瓦时 ... 数字"
    if ocr_total is None:
        m_total = TOTAL_KWH_RE.search(stats_text)
        if m_total:
            ocr_total = _try_parse_number(m_total.group(1))
            if ocr_total is not None:
                _ocr_logger.debug(f"parse_stats_module: OCR 总电量={ocr_total} (正则匹配法)")
    if ocr_total is None:
        # Method 2b: "千瓦时 ... 数字" (total appears AFTER 千瓦时)
        m_kwh = re.search(r'千瓦时\)?\s*', stats_text)
        if m_kwh:
            remainder = stats_text[m_kwh.end():].strip()
            m_num = re.match(r'(\d+\.?\d*)', remainder)
            if m_num:
                ocr_total = _try_parse_number(m_num.group(1))
                if ocr_total is not None:
                    _ocr_logger.debug(f"parse_stats_module: OCR 总电量={ocr_total} (千瓦时后匹配法)")

    if ocr_total is not None:
        sum_pv = record['peak_kwh'] + record['valley_kwh']
        diff = sum_pv - ocr_total
        if abs(diff) <= 0.2:
            if diff > 0:
                record['valley_kwh'] = round(record['valley_kwh'] - diff, 4)
                _ocr_logger.info(f"parse_stats_module: 电量校准 谷段-{diff:.4f} (合计={sum_pv}, 总={ocr_total})")
            elif diff < 0:
                record['peak_kwh'] = round(record['peak_kwh'] - diff, 4)
                _ocr_logger.info(f"parse_stats_module: 电量校准 峰段+{abs(diff):.4f} (合计={sum_pv}, 总={ocr_total})")
        else:
            _ocr_logger.debug(f"parse_stats_module: 差值={diff:.4f} 超出±0.2范围，跳过校准")

    # 3. Calculate total from components
    total = record['sharp_kwh'] + record['peak_kwh'] + record['flat_kwh'] + record['valley_kwh']
    record['total_kwh'] = round(total, 2)

    _ocr_logger.info(
        f"parse_stats_module: {row_date.isoformat()} | "
        f"尖={record['sharp_kwh']} 峰={record['peak_kwh']} "
        f"平={record['flat_kwh']} 谷={record['valley_kwh']} | "
        f"合计={record['total_kwh']} kWh"
    )

    # Validate: all zeros means something went wrong
    if total == 0:
        _ocr_logger.warning(f"parse_stats_module: {row_date} 所有分时电量为零，解析可能失败")
        return {
            'daily_records': [],
            'warnings': [f'{row_date}: 所有分时电量为零，解析可能失败'],
        }

    if total > 100:
        warnings.append(f'{row_date}: 日用电量 {total} kWh 异常偏高')
        _ocr_logger.warning(f"parse_stats_module: {row_date} 日用电量 {total} kWh 异常偏高")

    return {
        'daily_records': [record],
        'warnings': warnings,
    }


def parse_screenshot_data(text_blocks, year, month):
    """Main entry point: parse OCR text blocks into daily electricity records.

    Extracts one record per screenshot from the statistics module.

    Args:
        text_blocks: List of dicts with 'text', 'x', 'y', 'w', 'h', 'conf'.
        year: The year for date context.
        month: The month for date context.

    Returns:
        dict with 'daily_records' (list) and 'warnings' (list).
    """
    return parse_stats_module(text_blocks, year, month)