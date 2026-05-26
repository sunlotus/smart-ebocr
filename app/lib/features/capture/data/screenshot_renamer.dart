import 'dart:io';
import '../../../core/utils/date_utils.dart' as du;
import 'ocr_date_extractor.dart';

class ScreenshotRenamer {
  ScreenshotRenamer._();
  static final ScreenshotRenamer instance = ScreenshotRenamer._();

  static const int maxSequence = 6;

  /// 完整流程：OCR 提取日期 + 重命名（在主 isolate 调用）
  Future<String?> renameWithOcr(String tempPath, String screenshotsDir) async {
    final ocrDate = await OcrDateExtractor.instance.extractDate(tempPath);
    return renameWithOcrDirect(tempPath, screenshotsDir, ocrDate);
  }

  /// 纯文件 I/O：接收已提取的日期，执行重命名（可在 Isolate 中调用）
  Future<String?> renameWithOcrDirect(
    String tempPath, String screenshotsDir, String? ocrDate,
  ) async {
    final tempFile = File(tempPath);
    if (!await tempFile.exists()) return null;

    final now = DateTime.now();
    final dateStr = ocrDate ?? du.formatDateYyyyMMdd(now);

    final nextSeq = await _getNextSequence(screenshotsDir, dateStr);

    final newName = '$dateStr-$nextSeq.jpg';
    final newFile = File('$screenshotsDir/$newName');

    try {
      await tempFile.rename(newFile.path);
      return newFile.path;
    } catch (_) {
      try {
        await tempFile.copy(newFile.path);
        await tempFile.delete();
        return newFile.path;
      } catch (_) {
        return null;
      }
    }
  }

  Future<int> _getNextSequence(String dir, String dateStr) async {
    final directory = Directory(dir);
    if (!await directory.exists()) return 1;

    int maxSeq = 0;
    await for (final entity in directory.list()) {
      if (entity is File) {
        final name = entity.path.split('/').last;
        if (name.startsWith('$dateStr-') && name.endsWith('.jpg')) {
          final seq = du.parseSequence(name);
          if (seq != null && seq > maxSeq) maxSeq = seq;
        }
      }
    }

    final next = maxSeq + 1;
    return next > maxSequence ? maxSequence : next;
  }
}
