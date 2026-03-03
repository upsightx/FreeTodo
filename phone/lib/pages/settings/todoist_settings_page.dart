import 'package:flutter/material.dart';

import 'package:freeu/pages/settings/integration_settings_page.dart';
import 'package:freeu/services/todoist_service.dart';

class TodoistSettingsPage extends StatefulWidget {
  const TodoistSettingsPage({super.key});

  @override
  State<TodoistSettingsPage> createState() => _TodoistSettingsPageState();
}

class _TodoistSettingsPageState extends State<TodoistSettingsPage> {
  final TodoistService _todoistService = TodoistService();

  @override
  Widget build(BuildContext context) {
    return IntegrationSettingsPage(
      appName: 'Todoist',
      appKey: 'todoist',
      disconnectService: _todoistService.disconnect,
    );
  }
}
