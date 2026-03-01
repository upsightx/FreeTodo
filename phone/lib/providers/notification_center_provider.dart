import 'package:flutter/material.dart';

import 'package:omi/backend/http/api/notifications.dart';

class NotificationCenterProvider extends ChangeNotifier {
  List<AppNotification> _notifications = <AppNotification>[];
  final Set<String> _laterIds = <String>{};
  bool _loading = false;
  bool _useMockData = true;
  DateTime? _lastLoadedAt;

  List<AppNotification> get notifications => _notifications;
  Set<String> get laterIds => _laterIds;
  bool get loading => _loading;
  bool get useMockData => _useMockData;
  int get pendingCount => _notifications.where((n) => !_laterIds.contains(n.id)).length;

  Future<void> setUseMockData(bool value) async {
    if (_useMockData == value) return;
    _useMockData = value;
    _lastLoadedAt = null;
    notifyListeners();
    await refresh(force: true);
  }

  Future<void> refresh({bool force = false}) async {
    if (_loading) return;
    if (!force && _lastLoadedAt != null && DateTime.now().difference(_lastLoadedAt!).inSeconds < 20) {
      return;
    }

    _loading = true;
    notifyListeners();
    try {
      if (_useMockData) {
        _notifications = _mockNotifications();
      } else {
        final data = await getNotifications();
        _notifications = data;
      }
      _laterIds.removeWhere((id) => !_notifications.any((n) => n.id == id));
      _lastLoadedAt = DateTime.now();
    } finally {
      _loading = false;
      notifyListeners();
    }
  }

  void markLater(String id) {
    _laterIds.add(id);
    notifyListeners();
  }

  void clearLater(String id) {
    _laterIds.remove(id);
    notifyListeners();
  }

  Future<bool> acceptOrIgnore(String id) async {
    final ok = _useMockData ? true : await deleteNotification(id);
    if (!ok) return false;
    _notifications = _notifications.where((n) => n.id != id).toList();
    _laterIds.remove(id);
    notifyListeners();
    return true;
  }

  List<AppNotification> _mockNotifications() {
    final now = DateTime.now();
    return <AppNotification>[
      AppNotification(
        id: 'n_1',
        title: '导师追问论文进度',
        content: '“初稿今天能发我看一下吗？”',
        timestamp: now.subtract(const Duration(minutes: 10)),
        source: 'Feishu',
        aiSuggestion: '建议今天 16:30 前发送，先整理摘要与目录。',
      ),
      AppNotification(
        id: 'n_2',
        title: '日程冲突提醒',
        content: '明天下午 “项目评审会” 与 “羽毛球” 时间冲突。',
        timestamp: now.subtract(const Duration(minutes: 34)),
        source: 'Calendar',
        aiSuggestion: '建议保留评审会，自动改约周末打球。',
      ),
      AppNotification(
        id: 'n_3',
        title: '会议纪要已生成',
        content: '产品评审会已提取 3 条可执行项。',
        timestamp: now.subtract(const Duration(hours: 2)),
        source: 'Meeting',
        aiSuggestion: '可一键转为待办并分配截止时间。',
      ),
      AppNotification(
        id: 'n_4',
        title: '客户消息待回复',
        content: '客户询问报价是否可在周五前确认。',
        timestamp: now.subtract(const Duration(hours: 4)),
        source: 'Email',
        aiSuggestion: '建议先发确认邮件，再补正式报价单。',
      ),
    ];
  }
}
