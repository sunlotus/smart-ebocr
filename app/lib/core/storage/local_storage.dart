import 'dart:io';
import 'package:flutter/foundation.dart';
import 'package:path_provider/path_provider.dart';
import '../constants/app_constants.dart';

class LocalStorage {
  Future<Directory> getScreenshotDir() async {
    // 优先使用外部存储（用户可访问）
    if (!kIsWeb) {
      final externalDir = await getExternalStorageDirectory();
      if (externalDir != null) {
        final dir = Directory('${externalDir.path}/$screenshotsDir');
        if (!await dir.exists()) {
          await dir.create(recursive: true);
        }
        return dir;
      }
    }

    // 降级到内部存储
    final appDir = await getApplicationDocumentsDirectory();
    final dir = Directory('${appDir.path}/$screenshotsDir');
    if (!await dir.exists()) {
      await dir.create(recursive: true);
    }
    return dir;
  }

  Future<List<File>> listScreenshots() async {
    final dir = await getScreenshotDir();
    final files = await dir.list().toList();
    return files
        .whereType<File>()
        .where((f) => f.path.endsWith('.jpg') || f.path.endsWith('.png'))
        .toList()
      ..sort((a, b) => b.path.compareTo(a.path));
  }

  Future<List<File>> getScreenshotsByDate(String yyyyMMdd) async {
    final dir = await getScreenshotDir();
    final files = <File>[];
    await for (final entity in dir.list()) {
      if (entity is File) {
        final name = entity.path.split('/').last;
        // 匹配 yyyyMMdd-N.jpg 和旧格式 yyyyMMdd.jpg
        if ((name.startsWith('$yyyyMMdd-') || name == '$yyyyMMdd.jpg') &&
            name.endsWith('.jpg')) {
          files.add(entity);
        }
      }
    }
    files.sort((a, b) => a.path.compareTo(b.path));
    return files;
  }
}
