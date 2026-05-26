import 'dart:async';
import 'package:flutter/material.dart';
import 'package:permission_handler/permission_handler.dart';
import '../data/capture_service.dart';
import '../data/capture_orchestrator.dart';

class CaptureScreen extends StatefulWidget {
  const CaptureScreen({super.key});

  @override
  State<CaptureScreen> createState() => _CaptureScreenState();
}

class _CaptureScreenState extends State<CaptureScreen> {
  late final CaptureService _captureService;
  late final CaptureOrchestrator _orchestrator;
  bool _isCapturing = false;
  bool _isAutoRunning = false;
  int _selectedYear = DateTime.now().year;
  int _selectedMonth = DateTime.now().month;
  CaptureProgress _progress = const CaptureProgress();
  StreamSubscription? _progressSub;

  @override
  void initState() {
    super.initState();
    _captureService = AndroidCaptureService();
    _orchestrator = CaptureOrchestrator(_captureService);
    _orchestrator.setTargetMonth(_selectedYear, _selectedMonth);
    _progressSub = _orchestrator.progressStream.listen((progress) {
      if (mounted) {
        setState(() {
          _progress = progress;
          _isAutoRunning = progress.isRunning;
        });
      }
    });
  }

  @override
  void dispose() {
    _progressSub?.cancel();
    super.dispose();
  }

  Future<void> _startManualCapture() async {
    // Android 13+ 需要通知权限才能启动前台服务
    final notifStatus = await Permission.notification.status;
    if (!notifStatus.isGranted) {
      final result = await Permission.notification.request();
      if (!result.isGranted) {
        if (!mounted) return;
        ScaffoldMessenger.of(context).showSnackBar(
          const SnackBar(content: Text('需要通知权限才能运行截屏服务')),
        );
        return;
      }
    }

    final granted = await _captureService.requestPermission();
    if (!granted) {
      if (!mounted) return;
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(content: Text('需要屏幕录制权限才能截图')),
      );
      return;
    }

    if (!await _captureService.canDrawOverlays()) {
      if (!mounted) return;
      final go = await showDialog<bool>(
        context: context,
        builder: (ctx) => AlertDialog(
          title: const Text('需要悬浮窗权限'),
          content: const Text('截图功能需要「显示在其他应用上层」权限才能显示悬浮按钮。'),
          actions: [
            TextButton(onPressed: () => Navigator.pop(ctx, false), child: const Text('取消')),
            FilledButton(onPressed: () => Navigator.pop(ctx, true), child: const Text('去设置')),
          ],
        ),
      );
      if (go == true) {
        await _captureService.requestOverlayPermission();
      }
      return;
    }

    if (!mounted) return;
    final overlayReady = await _captureService.startCapture();
    if (overlayReady != true) {
      await _captureService.stopCapture();
      if (!mounted) return;
      showDialog(
        context: context,
        builder: (ctx) => AlertDialog(
          title: const Text('悬浮窗未就绪'),
          content: const Text('请在系统设置中授予「显示在其他应用上层」权限后重试。\n\n路径：设置 → 应用 → Smart EBOCR截图 → 显示在其他应用上层'),
          actions: [
            TextButton(onPressed: () => Navigator.pop(ctx), child: const Text('知道了')),
          ],
        ),
      );
      return;
    }

    ScaffoldMessenger.of(context).showSnackBar(
      const SnackBar(content: Text('悬浮按钮已显示，切换到网上国网后点击截图')),
    );
  }

  Future<void> _stopManualCapture() async {
    await _captureService.stopCapture();
    setState(() => _isCapturing = false);
  }

  Future<void> _startAutoCapture() async {
    final notifStatus = await Permission.notification.status;
    if (!notifStatus.isGranted) {
      final result = await Permission.notification.request();
      if (!result.isGranted) {
        if (!mounted) return;
        ScaffoldMessenger.of(context).showSnackBar(
          const SnackBar(content: Text('需要通知权限才能运行截屏服务')),
        );
        return;
      }
    }

    final granted = await _captureService.requestPermission();
    if (!granted) {
      if (!mounted) return;
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(content: Text('需要屏幕录制和无障碍权限')),
      );
      return;
    }

    _orchestrator.setTargetMonth(_selectedYear, _selectedMonth);
    await _orchestrator.startAutoCapture();
    setState(() => _isAutoRunning = true);
  }

  Future<void> _stopAutoCapture() async {
    await _orchestrator.stopAutoCapture();
    setState(() => _isAutoRunning = false);
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(title: const Text('截屏控制'), centerTitle: true),
      body: Padding(
        padding: const EdgeInsets.all(16),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.stretch,
          children: [
            _buildMonthSelector(),
            const SizedBox(height: 24),
            _buildManualSection(),
            const Divider(height: 32),
            _buildAutoSection(),
            if (_isAutoRunning) ...[
              const SizedBox(height: 24),
              _buildProgressBar(),
            ],
          ],
        ),
      ),
    );
  }

  Widget _buildMonthSelector() {
    return Card(
      child: Padding(
        padding: const EdgeInsets.all(16),
        child: Row(
          children: [
            const Icon(Icons.calendar_month),
            const SizedBox(width: 12),
            const Text('目标月份', style: TextStyle(fontSize: 16)),
            const Spacer(),
            Text(
              '$_selectedYear-${_selectedMonth.toString().padLeft(2, '0')}',
              style: const TextStyle(fontSize: 18, fontWeight: FontWeight.bold),
            ),
            const SizedBox(width: 8),
            IconButton(
              icon: const Icon(Icons.edit),
              onPressed: () async {
                final picked = await showDatePicker(
                  context: context,
                  initialDate: DateTime(_selectedYear, _selectedMonth),
                  firstDate: DateTime(2024, 1),
                  lastDate: DateTime.now(),
                );
                if (picked != null) {
                  setState(() {
                    _selectedYear = picked.year;
                    _selectedMonth = picked.month;
                  });
                }
              },
            ),
          ],
        ),
      ),
    );
  }

  Widget _buildManualSection() {
    return Card(
      child: Padding(
        padding: const EdgeInsets.all(16),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            const Text('手动截屏', style: TextStyle(fontSize: 18, fontWeight: FontWeight.bold)),
            const SizedBox(height: 8),
            const Text('显示悬浮按钮，在国网App中逐页点击截图'),
            const SizedBox(height: 12),
            SizedBox(
              width: double.infinity,
              child: FilledButton.icon(
                onPressed: _isCapturing ? _stopManualCapture : _startManualCapture,
                icon: Icon(_isCapturing ? Icons.stop : Icons.play_arrow),
                label: Text(_isCapturing ? '停止悬浮按钮' : '开始手动截屏'),
              ),
            ),
          ],
        ),
      ),
    );
  }

  Widget _buildAutoSection() {
    return Card(
      child: Padding(
        padding: const EdgeInsets.all(16),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            const Text('自动截屏', style: TextStyle(fontSize: 18, fontWeight: FontWeight.bold)),
            const SizedBox(height: 8),
            const Text('自动遍历选定月份，跳过无电量日期'),
            const SizedBox(height: 12),
            SizedBox(
              width: double.infinity,
              child: FilledButton.icon(
                onPressed: _isAutoRunning ? _stopAutoCapture : _startAutoCapture,
                icon: Icon(_isAutoRunning ? Icons.stop : Icons.smart_display),
                label: Text(_isAutoRunning ? '停止自动截屏' : '开始自动截屏'),
                style: _isAutoRunning
                    ? FilledButton.styleFrom(backgroundColor: Colors.red)
                    : null,
              ),
            ),
          ],
        ),
      ),
    );
  }

  Widget _buildProgressBar() {
    final total = _progress.total > 0 ? _progress.total : 30;
    final done = _progress.completed + _progress.skipped;
    final pct = total > 0 ? done / total : 0.0;

    return Card(
      color: Colors.blue.shade50,
      child: Padding(
        padding: const EdgeInsets.all(16),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text('进度: ${_progress.completed} 已截图, ${_progress.skipped} 跳过 / $total 天'),
            const SizedBox(height: 8),
            LinearProgressIndicator(value: pct),
            if (_progress.currentDate != null)
              Padding(
                padding: const EdgeInsets.only(top: 8),
                child: Text('当前: ${_progress.currentDate}'),
              ),
          ],
        ),
      ),
    );
  }
}
