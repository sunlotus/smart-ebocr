import 'package:paddle_ocr_flutter/paddle_ocr_flutter.dart';

class OcrDateExtractor {
  OcrDateExtractor._();
  static final OcrDateExtractor instance = OcrDateExtractor._();

  final _ocr = PaddleOcrFlutter();
  bool _initialized = false;

  Future<void> init() async {
    if (_initialized) return;
    await _ocr.init();
    _initialized = true;
  }

  Future<String?> extractDate(String imagePath) async {
    if (!_initialized) return null;

    final results = await _ocr.recognize(imagePath);
    if (results == null || results.isEmpty) return null;

    // 按置信度排序，优先高置信度
    final sorted = List<OcrResult>.from(results)
      ..sort((a, b) => (b.confidence ?? 0).compareTo(a.confidence ?? 0));

    for (final r in sorted) {
      final text = r.text?.trim();
      if (text == null || (r.confidence ?? 0) < 0.5) continue;

      final date = _extractDateFromText(text);
      if (date != null) return date;
    }

    return null;
  }

  String? _extractDateFromText(String text) {
    // YYYY年M月D日
    var m = RegExp(r'(\d{4})\s*年\s*(\d{1,2})\s*月\s*(\d{1,2})\s*日').firstMatch(text);
    if (m != null) return _formatDate(m[1]!, m[2]!, m[3]!);

    // YYYY/MM/DD
    m = RegExp(r'(\d{4})\s*/\s*(\d{1,2})\s*/\s*(\d{1,2})').firstMatch(text);
    if (m != null) return _formatDate(m[1]!, m[2]!, m[3]!);

    // YYYY-MM-DD
    m = RegExp(r'(\d{4})\s*-\s*(\d{1,2})\s*-\s*(\d{1,2})').firstMatch(text);
    if (m != null) return _formatDate(m[1]!, m[2]!, m[3]!);

    // M月D日 (补全当前年份)
    m = RegExp(r'(\d{1,2})\s*月\s*(\d{1,2})\s*日').firstMatch(text);
    if (m != null) {
      final year = DateTime.now().year.toString();
      return _formatDate(year, m[1]!, m[2]!);
    }

    // YYYYMMDD (8位纯数字)
    m = RegExp(r'\b(\d{4})(\d{2})(\d{2})\b').firstMatch(text);
    if (m != null) return _formatDate(m[1]!, m[2]!, m[3]!);

    return null;
  }

  String? _formatDate(String y, String m, String d) {
    final year = int.tryParse(y);
    final month = int.tryParse(m);
    final day = int.tryParse(d);
    if (year == null || month == null || day == null) return null;
    if (month < 1 || month > 12 || day < 1 || day > 31) return null;
    if (year < 2000 || year > 2100) return null;
    return '$y${m.padLeft(2, '0')}${d.padLeft(2, '0')}';
  }
}
