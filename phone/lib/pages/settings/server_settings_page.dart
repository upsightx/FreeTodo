import 'package:flutter/material.dart';
import 'package:flutter/services.dart';

import 'package:omi/backend/preferences.dart';
import 'package:omi/env/env.dart';
import 'package:omi/env/lifetrace_env.dart';

class ServerSettingsPage extends StatefulWidget {
  const ServerSettingsPage({super.key});

  @override
  State<ServerSettingsPage> createState() => _ServerSettingsPageState();
}

class _ServerSettingsPageState extends State<ServerSettingsPage> {
  final _customUrlController = TextEditingController();
  String _activeUrl = '';
  bool _isCustom = false;

  @override
  void initState() {
    super.initState();
    _activeUrl = Env.apiBaseUrl ?? LifeTraceEnv.defaultApiBaseUrl;
    _isCustom = !LifeTraceEnv.serverPresets.any((p) => p.url == _activeUrl);
    if (_isCustom) {
      _customUrlController.text = _activeUrl;
    }
  }

  @override
  void dispose() {
    _customUrlController.dispose();
    super.dispose();
  }

  void _selectPreset(LifeTraceServerPreset preset) {
    _applyUrl(preset.url);
    setState(() {
      _isCustom = false;
      _customUrlController.clear();
    });
  }

  void _applyCustomUrl() {
    var url = _customUrlController.text.trim();
    if (url.isEmpty) return;
    if (!url.startsWith('http://') && !url.startsWith('https://')) {
      url = 'http://$url';
    }
    if (!url.endsWith('/')) url = '$url/';
    _applyUrl(url);
    setState(() => _isCustom = true);
  }

  void _applyUrl(String url) {
    Env.overrideApiBaseUrl(url);
    SharedPreferencesUtil().lifetraceApiBaseUrl = url;
    setState(() => _activeUrl = url);
    ScaffoldMessenger.of(context).showSnackBar(
      SnackBar(
        content: Text('服务器已切换到 $url\n重新连接后生效'),
        backgroundColor: const Color(0xFF22C55E),
        duration: const Duration(seconds: 3),
      ),
    );
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: Colors.black,
      appBar: AppBar(
        backgroundColor: Colors.black,
        title: const Text('服务器设置', style: TextStyle(color: Colors.white)),
        iconTheme: const IconThemeData(color: Colors.white),
      ),
      body: ListView(
        padding: const EdgeInsets.all(16),
        children: [
          // Current server
          Container(
            padding: const EdgeInsets.all(16),
            decoration: BoxDecoration(
              color: const Color(0xFF1C1C1E),
              borderRadius: BorderRadius.circular(16),
            ),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(
                  '当前服务器',
                  style: TextStyle(color: Colors.grey.shade400, fontSize: 13, fontWeight: FontWeight.w600),
                ),
                const SizedBox(height: 8),
                Row(
                  children: [
                    Container(
                      width: 8,
                      height: 8,
                      decoration: const BoxDecoration(color: Color(0xFF22C55E), shape: BoxShape.circle),
                    ),
                    const SizedBox(width: 8),
                    Expanded(
                      child: Text(
                        _activeUrl,
                        style: const TextStyle(color: Colors.white, fontSize: 14, fontFamily: 'monospace'),
                      ),
                    ),
                    GestureDetector(
                      onTap: () {
                        Clipboard.setData(ClipboardData(text: _activeUrl));
                        ScaffoldMessenger.of(context).showSnackBar(
                          const SnackBar(content: Text('已复制'), duration: Duration(seconds: 1)),
                        );
                      },
                      child: Icon(Icons.copy, size: 16, color: Colors.grey.shade500),
                    ),
                  ],
                ),
              ],
            ),
          ),
          const SizedBox(height: 24),

          // Presets
          Text(
            '预设服务器',
            style: TextStyle(color: Colors.grey.shade400, fontSize: 13, fontWeight: FontWeight.w600),
          ),
          const SizedBox(height: 8),
          ...LifeTraceEnv.serverPresets.map((preset) {
            final isActive = !_isCustom && preset.url == _activeUrl;
            return Padding(
              padding: const EdgeInsets.only(bottom: 8),
              child: GestureDetector(
                onTap: () => _selectPreset(preset),
                child: Container(
                  padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 14),
                  decoration: BoxDecoration(
                    color: const Color(0xFF1C1C1E),
                    borderRadius: BorderRadius.circular(12),
                    border: isActive ? Border.all(color: const Color(0xFF22C55E), width: 1.5) : null,
                  ),
                  child: Row(
                    children: [
                      Icon(
                        isActive ? Icons.radio_button_checked : Icons.radio_button_off,
                        color: isActive ? const Color(0xFF22C55E) : Colors.grey.shade600,
                        size: 20,
                      ),
                      const SizedBox(width: 12),
                      Expanded(
                        child: Column(
                          crossAxisAlignment: CrossAxisAlignment.start,
                          children: [
                            Text(
                              preset.name,
                              style: TextStyle(
                                color: isActive ? Colors.white : Colors.grey.shade300,
                                fontSize: 15,
                                fontWeight: FontWeight.w500,
                              ),
                            ),
                            const SizedBox(height: 2),
                            Text(
                              preset.url,
                              style: TextStyle(
                                color: Colors.grey.shade500,
                                fontSize: 12,
                                fontFamily: 'monospace',
                              ),
                            ),
                          ],
                        ),
                      ),
                    ],
                  ),
                ),
              ),
            );
          }),
          const SizedBox(height: 24),

          // Custom URL
          Text(
            '自定义地址',
            style: TextStyle(color: Colors.grey.shade400, fontSize: 13, fontWeight: FontWeight.w600),
          ),
          const SizedBox(height: 8),
          Container(
            padding: const EdgeInsets.all(16),
            decoration: BoxDecoration(
              color: const Color(0xFF1C1C1E),
              borderRadius: BorderRadius.circular(16),
              border: _isCustom ? Border.all(color: const Color(0xFF22C55E), width: 1.5) : null,
            ),
            child: Column(
              children: [
                TextField(
                  controller: _customUrlController,
                  style: const TextStyle(color: Colors.white, fontSize: 14, fontFamily: 'monospace'),
                  decoration: InputDecoration(
                    hintText: 'http://192.168.1.100:8001/',
                    hintStyle: TextStyle(color: Colors.grey.shade700),
                    filled: true,
                    fillColor: const Color(0xFF2C2C2E),
                    border: OutlineInputBorder(
                      borderRadius: BorderRadius.circular(10),
                      borderSide: BorderSide.none,
                    ),
                    contentPadding: const EdgeInsets.symmetric(horizontal: 12, vertical: 12),
                  ),
                  keyboardType: TextInputType.url,
                  onSubmitted: (_) => _applyCustomUrl(),
                ),
                const SizedBox(height: 12),
                SizedBox(
                  width: double.infinity,
                  child: ElevatedButton(
                    onPressed: _applyCustomUrl,
                    style: ElevatedButton.styleFrom(
                      backgroundColor: const Color(0xFF2C2C2E),
                      foregroundColor: Colors.white,
                      padding: const EdgeInsets.symmetric(vertical: 12),
                      shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(10)),
                    ),
                    child: const Text('应用自定义地址'),
                  ),
                ),
              ],
            ),
          ),
          const SizedBox(height: 24),

          // Hint
          Container(
            padding: const EdgeInsets.all(12),
            decoration: BoxDecoration(
              color: Colors.orange.shade900.withOpacity(0.3),
              borderRadius: BorderRadius.circular(12),
            ),
            child: Row(
              children: [
                Icon(Icons.info_outline, color: Colors.orange.shade300, size: 18),
                const SizedBox(width: 8),
                Expanded(
                  child: Text(
                    '切换服务器后，当前录音会话需要重新连接才能生效。建议先断开设备再切换。',
                    style: TextStyle(color: Colors.orange.shade300, fontSize: 12),
                  ),
                ),
              ],
            ),
          ),
        ],
      ),
    );
  }
}
