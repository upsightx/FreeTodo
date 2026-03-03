import 'package:flutter/material.dart';

import 'package:freeu/backend/preferences.dart';

/// 感知权限管理Provider
class PerceptionProvider extends ChangeNotifier {
  bool _perceptionEnabled = true;
  bool _gpsEnabled = false;
  bool _clipboardEnabled = false;
  bool _notificationListenerEnabled = false;

  PerceptionProvider() {
    _loadSettings();
  }

  void _loadSettings() {
    final prefs = SharedPreferencesUtil();
    _perceptionEnabled = true; // 默认开启
    _gpsEnabled = prefs.locationEnabled;
    _clipboardEnabled = false; // TODO: 从preferences加载
    _notificationListenerEnabled = false; // TODO: 从preferences加载
    notifyListeners();
  }

  bool get perceptionEnabled => _perceptionEnabled;
  bool get gpsEnabled => _gpsEnabled;
  bool get clipboardEnabled => _clipboardEnabled;
  bool get notificationListenerEnabled => _notificationListenerEnabled;

  Future<void> setPerceptionEnabled(bool value) async {
    if (_perceptionEnabled == value) return;
    _perceptionEnabled = value;
    // TODO: 通知后端暂停/恢复感知
    notifyListeners();
  }

  Future<void> setGpsEnabled(bool value) async {
    if (_gpsEnabled == value) return;

    if (value) {
      // 请求GPS权限
      // TODO: 实现GPS权限请求
      // final permission = await Permission.location.request();
      // if (permission.isGranted) {
      //   _gpsEnabled = true;
      //   SharedPreferencesUtil().locationEnabled = true;
      // }
    } else {
      _gpsEnabled = false;
      SharedPreferencesUtil().locationEnabled = false;
    }
    notifyListeners();
  }

  Future<void> setClipboardEnabled(bool value) async {
    if (_clipboardEnabled == value) return;

    if (value) {
      // TODO: 请求剪贴板权限（Android需要特殊权限）
      // _clipboardEnabled = true;
    } else {
      _clipboardEnabled = false;
    }
    notifyListeners();
  }

  Future<void> setNotificationListenerEnabled(bool value) async {
    if (_notificationListenerEnabled == value) return;

    if (value) {
      // TODO: 请求通知监听权限（Android需要NotificationListenerService）
      // _notificationListenerEnabled = true;
    } else {
      _notificationListenerEnabled = false;
    }
    notifyListeners();
  }
}
