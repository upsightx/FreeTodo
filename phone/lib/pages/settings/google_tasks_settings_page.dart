import 'package:flutter/material.dart';

import 'package:freeu/pages/settings/integration_settings_page.dart';
import 'package:freeu/services/google_tasks_service.dart';

class GoogleTasksSettingsPage extends StatefulWidget {
  const GoogleTasksSettingsPage({super.key});

  @override
  State<GoogleTasksSettingsPage> createState() => _GoogleTasksSettingsPageState();
}

class _GoogleTasksSettingsPageState extends State<GoogleTasksSettingsPage> {
  final GoogleTasksService _googleTasksService = GoogleTasksService();

  @override
  Widget build(BuildContext context) {
    return IntegrationSettingsPage(
      appName: 'Google Tasks',
      appKey: 'google_tasks',
      disconnectService: _googleTasksService.disconnect,
    );
  }
}
