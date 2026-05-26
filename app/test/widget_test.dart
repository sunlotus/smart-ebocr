import 'package:flutter_test/flutter_test.dart';
import 'package:smart_ebocr_capture/app.dart';

void main() {
  testWidgets('App renders without error', (WidgetTester tester) async {
    await tester.pumpWidget(const SmartEbocrApp());
    expect(find.text('截屏控制'), findsOneWidget);
  });
}
