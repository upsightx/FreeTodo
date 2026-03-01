import 'dart:async';

import 'package:flutter/material.dart';

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
}

class MobileMockProvider extends ChangeNotifier {
  final List<MobileMockTask> _tasks = <MobileMockTask>[
    MobileMockTask(
      id: 'task_1',
      title: '给导师发送论文初稿',
      source: '飞书消息 · 今天 10:30',
      priority: MobileTaskPriority.high,
      status: MobileTaskStatus.todo,
      dueAt: DateTime.now().add(const Duration(hours: 3)),
    ),
    MobileMockTask(
      id: 'task_2',
      title: '准备明天项目评审材料',
      source: 'AI 日程提醒',
      priority: MobileTaskPriority.high,
      status: MobileTaskStatus.doing,
      dueAt: DateTime.now().add(const Duration(days: 1)),
    ),
    MobileMockTask(
      id: 'task_3',
      title: '约小李周末打球',
      source: '微信消息 · 今天 11:00',
      priority: MobileTaskPriority.normal,
      status: MobileTaskStatus.todo,
      dueAt: DateTime.now().add(const Duration(days: 2)),
    ),
    MobileMockTask(
      id: 'task_4',
      title: '回复客户报价邮件',
      source: '邮件提取',
      priority: MobileTaskPriority.normal,
      status: MobileTaskStatus.done,
      dueAt: DateTime.now().subtract(const Duration(hours: 2)),
    ),
  ];

  final List<MobileChatMessage> _messages = <MobileChatMessage>[
    MobileChatMessage(
      id: 'm0',
      text: '你好，我可以帮你总结消息、生成待办、安排日程。',
      isUser: false,
      createdAt: DateTime.now().subtract(const Duration(minutes: 5)),
    ),
  ];

  List<MobileMockTask> get tasks => _tasks;
  List<MobileChatMessage> get messages => _messages;

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

  void addTask({
    required String title,
    required String source,
    MobileTaskPriority priority = MobileTaskPriority.normal,
    DateTime? dueAt,
  }) {
    if (title.trim().isEmpty) return;
    _tasks.insert(
      0,
      MobileMockTask(
        id: 'task_${DateTime.now().millisecondsSinceEpoch}',
        title: title.trim(),
        source: source,
        priority: priority,
        status: MobileTaskStatus.todo,
        dueAt: dueAt ?? DateTime.now().add(const Duration(days: 1)),
      ),
    );
    notifyListeners();
  }

  void updateTask(MobileMockTask task, {String? title, DateTime? dueAt, MobileTaskPriority? priority}) {
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
  }

  void cycleTaskStatus(MobileMockTask task) {
    switch (task.status) {
      case MobileTaskStatus.todo:
        task.status = MobileTaskStatus.doing;
      case MobileTaskStatus.doing:
        task.status = MobileTaskStatus.done;
      case MobileTaskStatus.done:
        task.status = MobileTaskStatus.todo;
      case MobileTaskStatus.ignored:
        task.status = MobileTaskStatus.todo;
    }
    notifyListeners();
  }

  void ignoreTask(MobileMockTask task) {
    task.status = MobileTaskStatus.ignored;
    notifyListeners();
  }

  void reorderTasksByIds(List<String> orderedIds) {
    final Map<String, MobileMockTask> map = {for (final t in _tasks) t.id: t};
    final List<MobileMockTask> reordered = <MobileMockTask>[];
    for (final id in orderedIds) {
      final task = map[id];
      if (task != null) {
        reordered.add(task);
      }
    }
    for (final t in _tasks) {
      if (!orderedIds.contains(t.id)) {
        reordered.add(t);
      }
    }
    _tasks
      ..clear()
      ..addAll(reordered);
    notifyListeners();
  }

  void addTaskFromText(String text, {String source = 'AI 识别'}) {
    addTask(title: text, source: source, priority: MobileTaskPriority.high);
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

    await Future<void>.delayed(const Duration(milliseconds: 550));

    String reply = '我已记录你的请求。';
    bool hasAction = false;
    List<String> extractedTasks = const <String>[];
    if (trimmed.contains('截图') || trimmed.contains('聊天') || trimmed.contains('跟进')) {
      reply = '我从内容里识别到 3 条可跟进行动，建议一键加入待办。';
      hasAction = true;
      extractedTasks = <String>[
        '给王总确认下周深圳出差时间',
        '跟进设计稿评审并汇总反馈',
        '安排项目评审会前的材料检查',
      ];
    } else if (trimmed.contains('会议')) {
      reply = '会议相关重点已提取：材料准备、与会人确认、会后回执。';
      hasAction = true;
      extractedTasks = <String>[
        '整理会议材料清单',
        '确认评审参会人',
        '会后发送结论回执',
      ];
    } else if (trimmed.contains('今天')) {
      reply = '你今天还有 2 项高优先级待办，建议先处理“论文初稿”。';
    }

    _messages.add(
      MobileChatMessage(
        id: 'a_${DateTime.now().microsecondsSinceEpoch}',
        text: reply,
        isUser: false,
        createdAt: DateTime.now(),
        hasAction: hasAction,
        extractedTasks: extractedTasks,
      ),
    );
    notifyListeners();
  }
}
