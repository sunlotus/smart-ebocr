import 'package:flutter/material.dart';

class SettingsScreen extends StatelessWidget {
  const SettingsScreen({super.key});

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(title: const Text('设置'), centerTitle: true),
      body: ListView(
        children: [
          _buildSection('截图设置', [
            ListTile(
              leading: const Icon(Icons.folder),
              title: const Text('截图保存路径'),
              subtitle: const Text('应用内部存储/screenshots/'),
              trailing: const Icon(Icons.chevron_right),
              onTap: () {
                // TODO: 路径选择
              },
            ),
          ]),
          _buildSection('权限', [
            ListTile(
              leading: const Icon(Icons.screen_search_desktop),
              title: const Text('屏幕录制权限'),
              subtitle: const Text('MediaProjection - 用于截取屏幕'),
              trailing: const Icon(Icons.chevron_right),
              onTap: () {
                // TODO: 引导开启权限
              },
            ),
            ListTile(
              leading: const Icon(Icons.accessibility_new),
              title: const Text('无障碍服务'),
              subtitle: const Text('Accessibility Service - 用于自动截屏'),
              trailing: const Icon(Icons.chevron_right),
              onTap: () {
                // TODO: 引导开启无障碍服务
              },
            ),
            ListTile(
              leading: const Icon(Icons.layers),
              title: const Text('悬浮窗权限'),
              subtitle: const Text('SYSTEM_ALERT_WINDOW - 显示悬浮按钮'),
              trailing: const Icon(Icons.chevron_right),
              onTap: () {
                // TODO: 引导开启悬浮窗权限
              },
            ),
          ]),
          _buildSection('关于', [
            const ListTile(
              leading: Icon(Icons.info),
              title: Text('Smart EBOCR 截图工具'),
              subtitle: Text('v0.1.0'),
            ),
          ]),
        ],
      ),
    );
  }

  Widget _buildSection(String title, List<Widget> children) {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Padding(
          padding: const EdgeInsets.fromLTRB(16, 16, 16, 8),
          child: Text(
            title,
            style: const TextStyle(fontSize: 14, fontWeight: FontWeight.bold, color: Colors.grey),
          ),
        ),
        ...children,
        const Divider(),
      ],
    );
  }
}
