String formatDateYyyyMMdd(DateTime date) {
  final y = date.year.toString();
  final m = date.month.toString().padLeft(2, '0');
  final d = date.day.toString().padLeft(2, '0');
  return '$y$m$d';
}

String formatDateYyyyMMddSeq(DateTime date, int seq) {
  return '${formatDateYyyyMMdd(date)}-$seq';
}

DateTime? parseYyyyMMdd(String filename) {
  final name = filename.replaceAll(RegExp(r'\.\w+$'), '');
  final datePart = name.split('-').first;
  if (datePart.length != 8) return null;
  final year = int.tryParse(datePart.substring(0, 4));
  final month = int.tryParse(datePart.substring(4, 6));
  final day = int.tryParse(datePart.substring(6, 8));
  if (year == null || month == null || day == null) return null;
  if (month < 1 || month > 12 || day < 1 || day > 31) return null;
  return DateTime.tryParse('${datePart.substring(0, 4)}-${datePart.substring(4, 6)}-${datePart.substring(6, 8)}');
}

int? parseSequence(String filename) {
  final name = filename.replaceAll(RegExp(r'\.\w+$'), '');
  final parts = name.split('-');
  if (parts.length == 2) return int.tryParse(parts[1]);
  return null;
}

List<DateTime> getDaysInMonth(int year, int month) {
  final totalDays = DateTime(year, month + 1, 0).day;
  return List.generate(totalDays, (i) => DateTime(year, month, i + 1));
}
