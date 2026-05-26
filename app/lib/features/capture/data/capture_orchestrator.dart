import '../../../core/storage/local_storage.dart';
import '../../../core/utils/date_utils.dart' as du;
import 'capture_service.dart';

class CaptureOrchestrator {
  final CaptureService _captureService;
  final LocalStorage _localStorage = LocalStorage();
  int? _targetYear;
  int? _targetMonth;

  CaptureOrchestrator(this._captureService);

  void setTargetMonth(int year, int month) {
    _targetYear = year;
    _targetMonth = month;
  }

  int? get targetYear => _targetYear;
  int? get targetMonth => _targetMonth;

  Future<void> startAutoCapture() async {
    if (_targetYear == null || _targetMonth == null) return;
    await _captureService.startAutoCapture(_targetYear!, _targetMonth!);
  }

  Future<void> stopAutoCapture() async {
    await _captureService.stopAutoCapture();
  }

  List<DateTime> getDaysInTargetMonth() {
    if (_targetYear == null || _targetMonth == null) return [];
    return du.getDaysInMonth(_targetYear!, _targetMonth!);
  }

  Future<bool> hasScreenshotsForDay(DateTime day) async {
    final dateStr = du.formatDateYyyyMMdd(day);
    final files = await _localStorage.getScreenshotsByDate(dateStr);
    return files.isNotEmpty;
  }

  Stream<CaptureProgress> get progressStream => _captureService.progressStream;
}
