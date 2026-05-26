class CaptureConfig {
  final int year;
  final int month;
  final bool skipEmpty;

  const CaptureConfig({
    required this.year,
    required this.month,
    this.skipEmpty = true,
  });
}
