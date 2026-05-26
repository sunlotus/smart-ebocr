import 'dart:async';
import 'dart:isolate';
import 'package:flutter/services.dart';
import '../../../core/constants/app_constants.dart' show channelName;
import '../../../core/storage/local_storage.dart';
import 'ocr_date_extractor.dart';
import 'screenshot_renamer.dart';

abstract class CaptureService {
  Future<bool> requestPermission();
  Future<bool> canDrawOverlays();
  Future<void> requestOverlayPermission();
  Future<bool?> startCapture();
  Future<void> stopCapture();
  Future<String?> captureScreenshot(String yyyyMMdd);
  Future<void> startAutoCapture(int year, int month);
  Future<void> stopAutoCapture();
  Stream<CaptureProgress> get progressStream;
  Stream<String?> get onScreenshotCaptured => const Stream.empty();
}

class CaptureProgress {
  final int completed;
  final int skipped;
  final int total;
  final String? currentDate;
  final bool isRunning;

  const CaptureProgress({
    this.completed = 0,
    this.skipped = 0,
    this.total = 0,
    this.currentDate,
    this.isRunning = false,
  });
}

class AndroidCaptureService implements CaptureService {
  static const _channel = MethodChannel(channelName);
  final _progressController = StreamController<CaptureProgress>.broadcast();
  final _screenshotController = StreamController<String?>.broadcast();
  final _localStorage = LocalStorage();
  bool _ocrInitialized = false;

  AndroidCaptureService() {
    _channel.setMethodCallHandler(_handleMethodCall);
    _initOcr();
  }

  Future<void> _initOcr() async {
    if (_ocrInitialized) return;
    await OcrDateExtractor.instance.init();
    _ocrInitialized = true;
  }

  @override
  Stream<String?> get onScreenshotCaptured => _screenshotController.stream;

  Future<dynamic> _handleMethodCall(MethodCall call) async {
    switch (call.method) {
      case 'onProgress':
        final args = call.arguments as Map;
        _progressController.add(CaptureProgress(
          completed: args['completed'] ?? 0,
          skipped: args['skipped'] ?? 0,
          total: args['total'] ?? 0,
          currentDate: args['currentDate'],
          isRunning: true,
        ));
        break;
      case 'onComplete':
        _progressController.add(const CaptureProgress(isRunning: false));
        break;
      case 'onScreenshotCaptured':
        final args = call.arguments as Map;
        final tempPath = args['path'] as String?;
        if (tempPath != null) {
          // 立即通知 UI 截图已完成
          _screenshotController.add(tempPath);
          // 后台执行 OCR + rename，不阻塞 UI
          _processInBackground(tempPath);
        } else {
          _screenshotController.add(null);
        }
        break;
    }
  }

  Future<void> _processInBackground(String tempPath) async {
    try {
      await _initOcr();
      final dir = await _localStorage.getScreenshotDir();
      final dirPath = dir.path;

      // OCR 必须在主 isolate（平台通道限制）
      final ocrDate = await OcrDateExtractor.instance.extractDate(tempPath);

      // 文件 I/O 放到独立 isolate
      final newPath = await Isolate.run(() async {
        return ScreenshotRenamer.instance.renameWithOcrDirect(
          tempPath, dirPath, ocrDate,
        );
      });

      if (newPath != null) {
        _screenshotController.add(newPath);
      }
    } catch (_) {
      // 后台处理失败不影响 UI
    }
  }

  @override
  Future<bool> requestPermission() async {
    try {
      final result = await _channel.invokeMethod<bool>('requestPermission');
      return result ?? false;
    } on PlatformException {
      return false;
    }
  }

  @override
  Future<bool> canDrawOverlays() async {
    try {
      return await _channel.invokeMethod<bool>('canDrawOverlays') ?? false;
    } on PlatformException {
      return false;
    }
  }

  @override
  Future<void> requestOverlayPermission() async {
    await _channel.invokeMethod('requestOverlayPermission');
  }

  @override
  Future<bool?> startCapture() async {
    try {
      return await _channel.invokeMethod<bool>('startCapture');
    } on PlatformException {
      return false;
    }
  }

  @override
  Future<void> stopCapture() async {
    await _channel.invokeMethod('stopCapture');
  }

  @override
  Future<String?> captureScreenshot(String yyyyMMdd) async {
    try {
      final path = await _channel.invokeMethod<String>('captureScreenshot', {
        'filename': 'temp_${DateTime.now().millisecondsSinceEpoch}.jpg',
      });
      return path;
    } on PlatformException {
      return null;
    }
  }

  @override
  Future<void> startAutoCapture(int year, int month) async {
    await _channel.invokeMethod('startAutoCapture', {
      'year': year,
      'month': month,
    });
  }

  @override
  Future<void> stopAutoCapture() async {
    await _channel.invokeMethod('stopAutoCapture');
  }

  @override
  Stream<CaptureProgress> get progressStream => _progressController.stream;

  void dispose() {
    _progressController.close();
    _screenshotController.close();
  }
}
