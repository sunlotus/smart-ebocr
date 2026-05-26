import '../../../core/utils/date_utils.dart' as du;

enum ScreenshotStatus { captured, skipped, missing }

class ScreenshotModel {
  final DateTime date;
  final String? filePath;
  final ScreenshotStatus status;
  final int? sequence;

  const ScreenshotModel({
    required this.date,
    this.filePath,
    this.status = ScreenshotStatus.missing,
    this.sequence,
  });

  String get filename {
    if (sequence != null) {
      return '${du.formatDateYyyyMMdd(date)}-$sequence.jpg';
    }
    return '${du.formatDateYyyyMMdd(date)}.jpg';
  }

  ScreenshotModel copyWith({ScreenshotStatus? status, String? filePath, int? sequence}) {
    return ScreenshotModel(
      date: date,
      filePath: filePath ?? this.filePath,
      status: status ?? this.status,
      sequence: sequence ?? this.sequence,
    );
  }
}
