import 'package:flutter/material.dart';
import 'features/capture/presentation/capture_screen.dart';
import 'features/gallery/presentation/gallery_screen.dart';
import 'features/settings/presentation/settings_screen.dart';

class SmartEbocrApp extends StatelessWidget {
  const SmartEbocrApp({super.key});

  @override
  Widget build(BuildContext context) {
    return MaterialApp(
      title: 'Smart EBOCR 截图工具',
      theme: ThemeData(
        colorScheme: ColorScheme.fromSeed(seedColor: Colors.blue),
        useMaterial3: true,
      ),
      home: const HomePage(),
    );
  }
}

class HomePage extends StatefulWidget {
  const HomePage({super.key});

  @override
  State<HomePage> createState() => _HomePageState();
}

class _HomePageState extends State<HomePage> {
  int _currentIndex = 0;
  final _galleryRefresh = ValueNotifier<int>(0);

  late final List<Widget> _pages = [
    const CaptureScreen(),
    GalleryScreen(refreshTrigger: _galleryRefresh),
    const SettingsScreen(),
  ];

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      body: _pages[_currentIndex],
      bottomNavigationBar: NavigationBar(
        selectedIndex: _currentIndex,
        onDestinationSelected: (index) {
          setState(() => _currentIndex = index);
          if (index == 1) _galleryRefresh.value++;
        },
        destinations: const [
          NavigationDestination(icon: Icon(Icons.photo_camera), label: '截屏'),
          NavigationDestination(icon: Icon(Icons.photo_library), label: '截图'),
          NavigationDestination(icon: Icon(Icons.settings), label: '设置'),
        ],
      ),
    );
  }
}
