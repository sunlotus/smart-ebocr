# Copyright 2026 smart-ebocr Contributors
# SPDX-License-Identifier: Apache-2.0

"""Tests for the OCR parser (statistics module strategy)."""

import unittest

from backend.utils.parsers import (
    parse_screenshot_data,
    parse_stats_module,
    _try_parse_number,
    _fix_ocr_digits,
)


def make_block(text, x=0, y=0, w=50, h=20, conf=90):
    """Helper to create a text block dict."""
    return {'text': text, 'x': x, 'y': y, 'w': w, 'h': h, 'conf': conf}


class TestFixOcrDigits(unittest.TestCase):
    def test_common_misreads(self):
        self.assertEqual(_fix_ocr_digits('O'), '0')
        self.assertEqual(_fix_ocr_digits('l'), '1')
        self.assertEqual(_fix_ocr_digits('S'), '5')
        self.assertEqual(_fix_ocr_digits('B'), '8')
        self.assertEqual(_fix_ocr_digits('g'), '9')

    def test_mixed(self):
        self.assertEqual(_fix_ocr_digits('O.l5'), '0.15')

    def test_normal_digits(self):
        self.assertEqual(_fix_ocr_digits('12.34'), '12.34')

    def test_bracket_fixes(self):
        self.assertEqual(_fix_ocr_digits(']'), '1')
        self.assertEqual(_fix_ocr_digits('['), '1')


class TestTryParseNumber(unittest.TestCase):
    def test_normal_decimal(self):
        self.assertAlmostEqual(_try_parse_number('12.34'), 12.34)

    def test_integer(self):
        self.assertEqual(_try_parse_number('5'), 5.0)

    def test_ocr_error(self):
        self.assertAlmostEqual(_try_parse_number('O.5'), 0.5)
        self.assertAlmostEqual(_try_parse_number('l2.3'), 12.3)

    def test_leading_dot(self):
        self.assertAlmostEqual(_try_parse_number('.5'), 0.5)

    def test_out_of_range(self):
        self.assertIsNone(_try_parse_number('999'))

    def test_negative(self):
        self.assertIsNone(_try_parse_number('-5'))

    def test_non_number(self):
        self.assertIsNone(_try_parse_number('峰段'))


class TestParseStatsModule(unittest.TestCase):
    """Test statistics module parsing (current strategy)."""

    def test_full_single_day(self):
        """Parse a screenshot with one day's data in stats module format."""
        blocks = [
            make_block('4月10日', x=50, y=100),
            make_block('用电量', x=300, y=100),
            make_block('12.5 千瓦时', x=400, y=100),
            make_block('峰', x=50, y=200),
            make_block('5.23', x=100, y=200),
            make_block('谷', x=200, y=200),
            make_block('3.10', x=250, y=200),
            make_block('尖', x=350, y=200),
            make_block('0.50', x=400, y=200),
            make_block('平', x=500, y=200),
            make_block('3.67', x=550, y=200),
        ]

        result = parse_stats_module(blocks, 2026, 4)

        self.assertIn('daily_records', result)
        records = result['daily_records']
        self.assertEqual(len(records), 1)

        r = records[0]
        self.assertEqual(r['date'], '2026-04-10')
        self.assertAlmostEqual(r['peak_kwh'], 5.23)
        self.assertAlmostEqual(r['valley_kwh'], 3.10)
        self.assertAlmostEqual(r['sharp_kwh'], 0.50)
        self.assertAlmostEqual(r['flat_kwh'], 3.67)
        # total = peak + valley + sharp + flat
        self.assertAlmostEqual(r['total_kwh'], 12.50)

    def test_no_text_blocks(self):
        """Empty input should return empty records with warning."""
        result = parse_stats_module([], 2026, 4)
        self.assertEqual(result['daily_records'], [])
        self.assertTrue(len(result['warnings']) > 0)

    def test_no_date_found(self):
        """Blocks without a date pattern should fail gracefully."""
        blocks = [
            make_block('峰', x=50, y=200),
            make_block('5.23', x=100, y=200),
        ]
        result = parse_stats_module(blocks, 2026, 4)
        self.assertEqual(result['daily_records'], [])
        self.assertTrue(len(result['warnings']) > 0)

    def test_no_period_values(self):
        """Date found but no peak/valley values → all zeros → empty."""
        blocks = [
            make_block('4月10日', x=50, y=100),
        ]
        result = parse_stats_module(blocks, 2026, 4)
        self.assertEqual(result['daily_records'], [])

    def test_valley_with_ocr_noise(self):
        """Valley pattern should handle OCR noise (e.g. '国 从 2.97')."""
        blocks = [
            make_block('4月5日', x=50, y=100),
            make_block('峰', x=50, y=200),
            make_block('3.50', x=100, y=200),
            make_block('国', x=200, y=200),
            make_block('从', x=220, y=200),
            make_block('2.97', x=260, y=200),
        ]
        result = parse_stats_module(blocks, 2026, 4)
        records = result['daily_records']
        self.assertEqual(len(records), 1)
        self.assertAlmostEqual(records[0]['peak_kwh'], 3.50)
        # valley should be parsed despite OCR noise
        self.assertGreater(records[0]['valley_kwh'], 0)

    def test_high_usage_warning(self):
        """Usage above 100 kWh should generate a warning."""
        blocks = [
            make_block('4月1日', x=50, y=100),
            make_block('峰', x=50, y=200),
            make_block('60', x=100, y=200),
            make_block('谷', x=200, y=200),
            make_block('50', x=250, y=200),
        ]
        result = parse_stats_module(blocks, 2026, 4)
        records = result['daily_records']
        self.assertEqual(len(records), 1)
        self.assertAlmostEqual(records[0]['total_kwh'], 110.0)
        # Should have warning about high usage
        has_high_warning = any('异常偏高' in w for w in result.get('warnings', []))
        self.assertTrue(has_high_warning)

    def test_invalid_date(self):
        """Invalid date (e.g. 2月30日) should fail gracefully."""
        blocks = [
            make_block('2月30日', x=50, y=100),
            make_block('峰', x=50, y=200),
            make_block('5.00', x=100, y=200),
        ]
        result = parse_stats_module(blocks, 2026, 2)
        self.assertEqual(result['daily_records'], [])
        self.assertTrue(len(result['warnings']) > 0)


class TestParseScreenshotData(unittest.TestCase):
    """Test the main entry point that delegates to parse_stats_module."""

    def test_delegates_to_stats_module(self):
        blocks = [
            make_block('4月10日', x=50, y=100),
            make_block('峰', x=50, y=200),
            make_block('5.00', x=100, y=200),
            make_block('谷', x=200, y=200),
            make_block('3.00', x=250, y=200),
        ]
        result = parse_screenshot_data(blocks, 2026, 4)
        self.assertIn('daily_records', result)
        self.assertEqual(len(result['daily_records']), 1)

    def test_empty_blocks(self):
        result = parse_screenshot_data([], 2026, 4)
        self.assertEqual(result['daily_records'], [])


if __name__ == '__main__':
    unittest.main()