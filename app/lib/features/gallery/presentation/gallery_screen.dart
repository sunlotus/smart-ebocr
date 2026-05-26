import 'dart:io';
import 'package:flutter/material.dart';

import '../../../core/storage/local_storage.dart';
import '../../../core/utils/date_utils.dart' as du;
import '../../capture/domain/screenshot_model.dart';

class GalleryScreen extends StatefulWidget {
  final ValueNotifier<int>? refreshTrigger;
  const GalleryScreen({super.key, this.refreshTrigger});

  @override
  State<GalleryScreen> createState() => _GalleryScreenState();
}

class _GalleryScreenState extends State<GalleryScreen> {
  final LocalStorage _storage = LocalStorage();
  Map<int, List<ScreenshotModel>> _groupedByDay = {};
  int _selectedYear = DateTime.now().year;
  int _selectedMonth = DateTime.now().month;
  bool _loading = false;
  int _totalCount = 0;

  @override
  void initState() {
    super.initState();
    widget.refreshTrigger?.addListener(_loadScreenshots);
    _loadScreenshots();
  }

  @override
  void dispose() {
    widget.refreshTrigger?.removeListener(_loadScreenshots);
    super.dispose();
  }

  Future<void> _loadScreenshots() async {
    setState(() => _loading = true);
    try {
      final files = await _storage.listScreenshots();
      final grouped = <int, List<ScreenshotModel>>{};
      var total = 0;

      for (final f in files) {
        final name = f.path.split('/').last;
        final date = du.parseYyyyMMdd(name);
        if (date != null &&
            date.year == _selectedYear &&
            date.month == _selectedMonth) {
          final day = date.day;
          grouped.putIfAbsent(day, () => []);
          grouped[day]!.add(ScreenshotModel(
            date: date,
            filePath: f.path,
            status: ScreenshotStatus.captured,
            sequence: du.parseSequence(name),
          ));
          total++;
        }
      }

      setState(() {
        _groupedByDay = grouped;
        _totalCount = total;
      });
    } finally {
      setState(() => _loading = false);
    }
  }

  @override
  Widget build(BuildContext context) {
    final days = du.getDaysInMonth(_selectedYear, _selectedMonth);
    final totalDays = days.length;
    final firstWeekday = DateTime(_selectedYear, _selectedMonth, 1).weekday;
    final leadingEmpty = firstWeekday % 7;

    return Scaffold(
      appBar: AppBar(
        title: const Text('截图管理'),
        centerTitle: true,
        actions: [
          TextButton(
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
                _loadScreenshots();
              }
            },
            child: Text(
              '$_selectedYear-${_selectedMonth.toString().padLeft(2, '0')}',
              style: const TextStyle(color: Colors.white),
            ),
          ),
        ],
      ),
      body: _loading
          ? const Center(child: CircularProgressIndicator())
          : RefreshIndicator(
              onRefresh: _loadScreenshots,
              child: Column(
                children: [
                  _buildSummary(),
                  _buildWeekdayHeader(),
                  Expanded(child: _buildMonthGrid(totalDays, leadingEmpty)),
                ],
              ),
            ),
    );
  }

  Widget _buildSummary() {
    return Padding(
      padding: const EdgeInsets.all(12),
      child: Row(
        mainAxisAlignment: MainAxisAlignment.center,
        children: [
          _buildStatChip('截图总数', _totalCount, Colors.green),
          const SizedBox(width: 12),
          _buildStatChip('已截图天数', _groupedByDay.length, Colors.blue),
        ],
      ),
    );
  }

  Widget _buildStatChip(String label, int count, Color color) {
    return Chip(
      avatar: CircleAvatar(
        backgroundColor: color.withValues(alpha: 0.2),
        child: Text('$count', style: TextStyle(color: color, fontSize: 12)),
      ),
      label: Text(label),
    );
  }

  Widget _buildWeekdayHeader() {
    const days = ['日', '一', '二', '三', '四', '五', '六'];
    return Padding(
      padding: const EdgeInsets.symmetric(horizontal: 8),
      child: Row(
        children: days.map((d) => Expanded(
          child: Center(
            child: Text(d, style: TextStyle(fontSize: 12, color: Colors.grey.shade600)),
          ),
        )).toList(),
      ),
    );
  }

  Widget _buildMonthGrid(int totalDays, int leadingEmpty) {
    if (_groupedByDay.isEmpty) {
      return Center(
        child: Column(
          mainAxisAlignment: MainAxisAlignment.center,
          children: [
            Icon(Icons.photo_library_outlined, size: 64, color: Colors.grey),
            const SizedBox(height: 16),
            Text(
              '$_selectedYear-$_selectedMonth 暂无截图',
              style: const TextStyle(fontSize: 18, color: Colors.grey),
            ),
            const SizedBox(height: 8),
            Text(
              '点击悬浮按钮开始截图',
              style: TextStyle(fontSize: 14, color: Colors.grey.shade600),
            ),
          ],
        ),
      );
    }

    final cells = <Widget>[];
    for (int i = 0; i < leadingEmpty; i++) {
      cells.add(const SizedBox());
    }
    for (int day = 1; day <= totalDays; day++) {
      cells.add(_buildDayCell(day));
    }

    return GridView.count(
      padding: const EdgeInsets.all(8),
      crossAxisCount: 7,
      crossAxisSpacing: 4,
      mainAxisSpacing: 4,
      children: cells,
    );
  }

  Widget _buildDayCell(int day) {
    final screenshots = _groupedByDay[day];
    final hasScreenshots = screenshots != null && screenshots.isNotEmpty;
    final count = screenshots?.length ?? 0;

    return GestureDetector(
      onTap: hasScreenshots ? () => _showDayDetail(day, screenshots!) : null,
      child: Container(
        decoration: BoxDecoration(
          color: hasScreenshots ? Colors.green.shade50 : Colors.grey.shade50,
          borderRadius: BorderRadius.circular(6),
          border: Border.all(
            color: hasScreenshots ? Colors.green.shade300 : Colors.grey.shade200,
          ),
        ),
        child: Stack(
          alignment: Alignment.center,
          children: [
            Text(
              '$day',
              style: TextStyle(
                fontSize: 16,
                fontWeight: hasScreenshots ? FontWeight.bold : FontWeight.normal,
                color: hasScreenshots ? Colors.green.shade800 : Colors.grey.shade400,
              ),
            ),
            if (count > 1)
              Positioned(
                right: 2,
                top: 2,
                child: Container(
                  padding: const EdgeInsets.symmetric(horizontal: 3, vertical: 1),
                  decoration: BoxDecoration(
                    color: Colors.blue.shade400,
                    borderRadius: BorderRadius.circular(8),
                  ),
                  child: Text(
                    '$count',
                    style: const TextStyle(fontSize: 9, color: Colors.white),
                  ),
                ),
              ),
            if (hasScreenshots)
              Positioned(
                right: 2,
                bottom: 2,
                child: Icon(Icons.check_circle, size: 10, color: Colors.green.shade600),
              ),
          ],
        ),
      ),
    );
  }

  void _showDayDetail(int day, List<ScreenshotModel> screenshots) {
    screenshots.sort((a, b) => (a.sequence ?? 0).compareTo(b.sequence ?? 0));
    Navigator.push(
      context,
      MaterialPageRoute(
        builder: (_) => _DayDetailPage(
          year: _selectedYear,
          month: _selectedMonth,
          day: day,
          screenshots: screenshots,
        ),
      ),
    );
  }
}

class _DayDetailPage extends StatelessWidget {
  final int year;
  final int month;
  final int day;
  final List<ScreenshotModel> screenshots;

  const _DayDetailPage({
    required this.year,
    required this.month,
    required this.day,
    required this.screenshots,
  });

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(title: Text('$month月${day}日 — ${screenshots.length}张截图')),
      body: GridView.builder(
        padding: const EdgeInsets.all(8),
        gridDelegate: const SliverGridDelegateWithFixedCrossAxisCount(
          crossAxisCount: 2,
          crossAxisSpacing: 8,
          mainAxisSpacing: 8,
        ),
        itemCount: screenshots.length,
        itemBuilder: (context, index) {
          final item = screenshots[index];
          return _buildScreenshotCard(context, item);
        },
      ),
    );
  }

  Widget _buildScreenshotCard(BuildContext context, ScreenshotModel item) {
    return GestureDetector(
      onTap: () {
        Navigator.push(
          context,
          MaterialPageRoute(
            builder: (_) => _ScreenshotDetailPage(screenshot: item),
          ),
        );
      },
      child: Card(
        clipBehavior: Clip.antiAlias,
        child: Stack(
          fit: StackFit.expand,
          children: [
            if (item.filePath != null)
              Image.file(
                File(item.filePath!),
                fit: BoxFit.cover,
                filterQuality: FilterQuality.medium,
              ),
            if (item.sequence != null)
              Positioned(
                left: 4,
                top: 4,
                child: Container(
                  padding: const EdgeInsets.symmetric(horizontal: 6, vertical: 2),
                  decoration: BoxDecoration(
                    color: Colors.black54,
                    borderRadius: BorderRadius.circular(4),
                  ),
                  child: Text(
                    '#${item.sequence}',
                    style: const TextStyle(color: Colors.white, fontSize: 12),
                  ),
                ),
              ),
          ],
        ),
      ),
    );
  }
}

class _ScreenshotDetailPage extends StatelessWidget {
  final ScreenshotModel screenshot;

  const _ScreenshotDetailPage({required this.screenshot});

  @override
  Widget build(BuildContext context) {
    final title = screenshot.sequence != null
        ? '${du.formatDateYyyyMMdd(screenshot.date)}-${screenshot.sequence}'
        : du.formatDateYyyyMMdd(screenshot.date);
    return Scaffold(
      appBar: AppBar(title: Text(title)),
      body: Center(
        child: screenshot.filePath != null
            ? Image.file(
                File(screenshot.filePath!),
                fit: BoxFit.contain,
                cacheWidth: 1080,
                filterQuality: FilterQuality.medium,
              )
            : const Text('无截图'),
      ),
    );
  }
}
