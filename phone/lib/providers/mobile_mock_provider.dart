import 'dart:async';

import 'package:flutter/material.dart';

import 'package:omi/backend/http/api/action_items.dart';
import 'package:omi/backend/http/api/messages.dart';
import 'package:omi/backend/schema/message.dart';
import 'package:omi/backend/schema/schema.dart';
import 'package:omi/env/env.dart';

enum MobileTaskPriority { high, normal }

enum MobileTaskStatus { todo, doing, done, ignored }

class MobileMockTask {
  MobileMockTask({
    required this.id,
    required this.title,
    required this.source,
    required this.priority,
    required this.status,
    required this.dueAt,
  });

  final String id;
  String title;
  String source;
  MobileTaskPriority priority;
  MobileTaskStatus status;
  DateTime dueAt;
}

class MobileChatMessage {
  MobileChatMessage({
    required this.id,
    required this.text,
    required this.isUser,
    required this.createdAt,
    this.hasAction = false,
    this.extractedTasks = const <String>[],
  });

  final String id;
  final String text;
  final bool isUser;
  final DateTime createdAt;
  final bool hasAction;
  final List<String> extractedTasks;

  MobileChatMessage copyWith({
    String? id,
    String? text,
    bool? isUser,
    DateTime? createdAt,
    bool? hasAction,
    List<String>? extractedTasks,
  }) {
    return MobileChatMessage(
      id: id ?? this.id,
      text: text ?? this.text,
      isUser: isUser ?? this.isUser,
      createdAt: createdAt ?? this.createdAt,
      hasAction: hasAction ?? this.hasAction,
      extractedTasks: extractedTasks ?? this.extractedTasks,
    );
  }
}

class MobileMockProvider extends ChangeNotifier {
  final List<MobileMockTask> _tasks = <MobileMockTask>[];
  final List<MobileChatMessage> _messages = <MobileChatMessage>[];
  StreamSubscription<String>? _apiBaseUrlSub;

  bool _loading = false;
  bool _syncingTasks = false;
  bool _syncingMessages = false;
  DateTime? _lastTasksSyncAt;
  DateTime? _lastMessagesSyncAt;

  MobileMockProvider() {
    _apiBaseUrlSub = Env.onApiBaseUrlChanged.listen((_) {
      unawaited(refreshAll());
    });
    unawaited(refreshAll());
  }

  List<MobileMockTask> get tasks => _tasks;
  List<MobileChatMessage> get messages => _messages;
  bool get isLoading => _loading;
  bool get syncingTasks => _syncingTasks;
  bool get syncingMessages => _syncingMessages;
  DateTime? get lastTasksSyncAt => _lastTasksSyncAt;
  DateTime? get lastMessagesSyncAt => _lastMessagesSyncAt;

  List<MobileMockTask> get todayTasks {
    final now = DateTime.now();
    final dayStart = DateTime(now.year, now.month, now.day);
    final dayEnd = dayStart.add(const Duration(days: 1));
    return _tasks.where((t) => t.dueAt.isAfter(dayStart) && t.dueAt.isBefore(dayEnd)).toList();
  }

  List<MobileMockTask> get weekTasks {
    final now = DateTime.now();
    final end = now.add(const Duration(days: 7));
    return _tasks.where((t) => t.dueAt.isBefore(end)).toList();
  }

  Future<void> refreshAll() async {
    _loading = true;
    notifyListeners();
    await Future.wait<void>([
      refreshTasks(),
      refreshMessages(),
    ]);
    _loading = false;
    notifyListeners();
  }

  Future<void> refreshTasks() async {
    _syncingTasks = true;
    notifyListeners();
    try {
      final response = await getActionItems(limit: 200, offset: 0);
      final list = response.actionItems.map(_mapActionItemToTask).toList();
      _tasks
        ..clear()
        ..addAll(list);
      _lastTasksSyncAt = DateTime.now();
    } finally {
      _syncingTasks = false;
      notifyListeners();
    }
  }

  Future<void> refreshMessages() async {
    _syncingMessages = true;
    notifyListeners();
    try {
      final serverMessages = await getMessagesServer();
      _messages
        ..clear()
        ..addAll(
          serverMessages.map(
            (m) => MobileChatMessage(
              id: m.id,
              text: m.text,
              isUser: m.sender == MessageSender.human,
              createdAt: m.createdAt,
            ),
          ),
        );
      _lastMessagesSyncAt = DateTime.now();
    } finally {
      _syncingMessages = false;
      notifyListeners();
    }
  }

  Future<void> addTask({
    required String title,
    required String source,
    MobileTaskPriority priority = MobileTaskPriority.normal,
    DateTime? dueAt,
  }) async {
    final trimmed = title.trim();
    if (trimmed.isEmpty) return;

    final created = await createActionItem(
      description: trimmed,
      dueAt: dueAt ?? DateTime.now().add(const Duration(days: 1)),
      completed: false,
    );

    if (created == null) {
      return;
    }

    _tasks.insert(0, _mapActionItemToTask(created, sourceOverride: source, priorityOverride: priority));
    notifyListeners();
  }

  Future<void> updateTask(
    MobileMockTask task, {
    String? title,
    DateTime? dueAt,
    MobileTaskPriority? priority,
  }) async {
    if (title != null && title.trim().isNotEmpty) {
      task.title = title.trim();
    }
    if (dueAt != null) {
      task.dueAt = dueAt;
    }
    if (priority != null) {
      task.priority = priority;
    }
    notifyListeners();

    try {
      await updateActionItem(
        task.id,
        description: task.title,
        dueAt: task.dueAt,
        clearDueAt: false,
      );
    } catch (_) {}
    unawaited(refreshTasks());
  }

  Future<void> cycleTaskStatus(MobileMockTask task) async {
    switch (task.status) {
      case MobileTaskStatus.todo:
      case MobileTaskStatus.doing:
      case MobileTaskStatus.ignored:
        task.status = MobileTaskStatus.done;
      case MobileTaskStatus.done:
        task.status = MobileTaskStatus.todo;
    }
    notifyListeners();

    final completed = task.status == MobileTaskStatus.done;
    try {
      await toggleActionItemCompletion(task.id, completed);
    } catch (_) {}
    unawaited(refreshTasks());
  }

  Future<void> ignoreTask(MobileMockTask task) async {
    task.status = MobileTaskStatus.ignored;
    notifyListeners();
    try {
      await updateActionItem(
        task.id,
        status: 'canceled',
        completed: false,
      );
    } catch (_) {}
    unawaited(refreshTasks());
  }

  Future<void> reorderTasksByIds(List<String> orderedIds) async {
    final map = {for (final t in _tasks) t.id: t};
    final reordered = <MobileMockTask>[];
    for (final id in orderedIds) {
      final task = map[id];
      if (task != null) reordered.add(task);
    }
    for (final task in _tasks) {
      if (!orderedIds.contains(task.id)) {
        reordered.add(task);
      }
    }
    _tasks
      ..clear()
      ..addAll(reordered);
    notifyListeners();

    final updates = <Map<String, dynamic>>[];
    for (var i = 0; i < _tasks.length; i++) {
      updates.add({'id': _tasks[i].id, 'sort_order': (i + 1) * 1000});
    }
    try {
      await batchUpdateActionItems(updates);
    } catch (_) {}
    unawaited(refreshTasks());
  }

  void addTaskFromText(String text, {String source = 'AI 识别'}) {
    unawaited(addTask(title: text, source: source, priority: MobileTaskPriority.high));
  }

  Future<void> sendChatMessage(String text) async {
    final trimmed = text.trim();
    if (trimmed.isEmpty) return;

    _messages.add(
      MobileChatMessage(
        id: 'u_${DateTime.now().microsecondsSinceEpoch}',
        text: trimmed,
        isUser: true,
        createdAt: DateTime.now(),
      ),
    );
    notifyListeners();

    var aiText = '';
    var aiMessageId = 'a_${DateTime.now().microsecondsSinceEpoch}';
    final aiPlaceholderId = 'a_stream_${DateTime.now().microsecondsSinceEpoch}';
    _messages.add(
      MobileChatMessage(
        id: aiPlaceholderId,
        text: '...',
        isUser: false,
        createdAt: DateTime.now(),
      ),
    );
    notifyListeners();

    final aiIndex = _messages.length - 1;

    try {
      await for (final chunk in sendMessageStreamServer(trimmed)) {
        if (chunk.type == MessageChunkType.data || chunk.type == MessageChunkType.think) {
          aiText += chunk.text;
          _messages[aiIndex] = _messages[aiIndex].copyWith(text: aiText.isEmpty ? '...' : aiText);
          notifyListeners();
          continue;
        }
        if (chunk.type == MessageChunkType.done && chunk.message != null) {
          aiMessageId = chunk.message!.id;
          aiText = chunk.message!.text;
          _messages[aiIndex] = _messages[aiIndex].copyWith(id: aiMessageId, text: aiText);
          notifyListeners();
          unawaited(refreshMessages());
          return;
        }
        if (chunk.type == MessageChunkType.error) {
          aiText = chunk.text;
          _messages[aiIndex] = _messages[aiIndex].copyWith(text: aiText);
          notifyListeners();
          break;
        }
      }
    } catch (_) {
      aiText = '请求失败，请检查中心节点连接。';
    }

    if (aiText.trim().isEmpty) {
      aiText = '请求失败，请稍后重试。';
    }

    _messages[aiIndex] = _messages[aiIndex].copyWith(id: aiMessageId, text: aiText);
    notifyListeners();
    unawaited(refreshMessages());
  }

  MobileMockTask _mapActionItemToTask(
    ActionItemWithMetadata item, {
    String? sourceOverride,
    MobileTaskPriority? priorityOverride,
  }) {
    final due = item.dueAt ?? DateTime.now().add(const Duration(days: 1));
    final isHigh = due.isBefore(DateTime.now().add(const Duration(days: 1)));
    final normalizedStatus = (item.status ?? '').toLowerCase();
    final taskStatus = switch (normalizedStatus) {
      'canceled' => MobileTaskStatus.ignored,
      'completed' => MobileTaskStatus.done,
      _ => (item.completed ? MobileTaskStatus.done : MobileTaskStatus.todo),
    };
    return MobileMockTask(
      id: item.id,
      title: item.description,
      source: sourceOverride ?? '中心节点同步',
      priority: priorityOverride ?? (isHigh ? MobileTaskPriority.high : MobileTaskPriority.normal),
      status: taskStatus,
      dueAt: due,
    );
  }

  @override
  void dispose() {
    _apiBaseUrlSub?.cancel();
    super.dispose();
  }
}
