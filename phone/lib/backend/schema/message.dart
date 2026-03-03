import 'package:collection/collection.dart';
import 'package:uuid/uuid.dart';

enum MessageSender { ai, human }

enum MessageType {
  text('text'),
  daySummary('day_summary');

  final String value;

  const MessageType(this.value);

  static MessageType valuesFromString(String value) {
    return MessageType.values.firstWhereOrNull((e) => e.value == value) ?? MessageType.text;
  }
}

class MessageConversationStructured {
  String title;
  String emoji;

  MessageConversationStructured(this.title, this.emoji);

  static MessageConversationStructured fromJson(Map<String, dynamic> json) {
    return MessageConversationStructured(
      (json['title'] ?? '').toString(),
      (json['emoji'] ?? '').toString(),
    );
  }

  Map<String, dynamic> toJson() {
    return {
      'title': title,
      'emoji': emoji,
    };
  }
}

class MessageConversation {
  String id;
  DateTime createdAt;
  MessageConversationStructured structured;

  MessageConversation(this.id, this.createdAt, this.structured);

  static MessageConversation fromJson(Map<String, dynamic> json) {
    return MessageConversation(
      (json['id'] ?? '').toString(),
      DateTime.tryParse((json['created_at'] ?? '').toString())?.toLocal() ?? DateTime.now(),
      MessageConversationStructured.fromJson(json['structured'] is Map<String, dynamic>
          ? json['structured'] as Map<String, dynamic>
          : <String, dynamic>{}),
    );
  }

  Map<String, dynamic> toJson() {
    return {
      'id': id,
      'created_at': createdAt.toUtc().toIso8601String(),
      'structured': structured.toJson(),
    };
  }
}

class MessageFile {
  String id;
  String openaiFileId;
  String? thumbnail;
  String? thumbnailName;
  String name;
  String mimeType;
  DateTime createdAt;

  MessageFile(this.openaiFileId, this.thumbnail, this.name, this.mimeType, this.id, this.createdAt, this.thumbnailName);

  static MessageFile fromJson(Map<String, dynamic> json) {
    return MessageFile(
      (json['openai_file_id'] ?? '').toString(),
      json['thumbnail']?.toString(),
      (json['name'] ?? '').toString(),
      (json['mime_type'] ?? '').toString(),
      (json['id'] ?? '').toString(),
      DateTime.tryParse((json['created_at'] ?? '').toString())?.toLocal() ?? DateTime.now(),
      json['thumb_name']?.toString(),
    );
  }

  static List<MessageFile> fromJsonList(List<dynamic> json) {
    return json.whereType<Map<String, dynamic>>().map(MessageFile.fromJson).toList();
  }

  Map<String, dynamic> toJson() {
    return {
      'openai_file_id': openaiFileId,
      'thumbnail': thumbnail,
      'name': name,
      'mime_type': mimeType,
      'id': id,
      'created_at': createdAt.toUtc().toIso8601String(),
      'thumb_name': thumbnailName,
    };
  }

  String mimeTypeToFileType() {
    if (mimeType.contains('image')) {
      return 'image';
    }
    return 'file';
  }
}

class ChartDataPoint {
  String label;
  double value;

  ChartDataPoint(this.label, this.value);

  static ChartDataPoint fromJson(Map<String, dynamic> json) {
    return ChartDataPoint(
      (json['label'] ?? '').toString(),
      ((json['value'] as num?) ?? 0).toDouble(),
    );
  }

  Map<String, dynamic> toJson() {
    return {'label': label, 'value': value};
  }
}

class ChartDataset {
  String label;
  List<ChartDataPoint> dataPoints;
  String? color;

  ChartDataset(this.label, this.dataPoints, {this.color});

  static ChartDataset fromJson(Map<String, dynamic> json) {
    return ChartDataset(
      (json['label'] ?? 'Data').toString(),
      ((json['data_points'] ?? const <dynamic>[]) as List)
          .whereType<Map<String, dynamic>>()
          .map(ChartDataPoint.fromJson)
          .toList(),
      color: json['color']?.toString(),
    );
  }

  Map<String, dynamic> toJson() {
    return {
      'label': label,
      'data_points': dataPoints.map((p) => p.toJson()).toList(),
      'color': color,
    };
  }
}

class ChartData {
  String chartType;
  String title;
  String? xLabel;
  String? yLabel;
  List<ChartDataset> datasets;

  ChartData(this.chartType, this.title, this.datasets, {this.xLabel, this.yLabel});

  static ChartData? fromJson(Map<String, dynamic>? json) {
    if (json == null) return null;
    return ChartData(
      (json['chart_type'] ?? 'line').toString(),
      (json['title'] ?? '').toString(),
      ((json['datasets'] ?? const <dynamic>[]) as List)
          .whereType<Map<String, dynamic>>()
          .map(ChartDataset.fromJson)
          .toList(),
      xLabel: json['x_label']?.toString(),
      yLabel: json['y_label']?.toString(),
    );
  }

  Map<String, dynamic> toJson() {
    return {
      'chart_type': chartType,
      'title': title,
      'x_label': xLabel,
      'y_label': yLabel,
      'datasets': datasets.map((d) => d.toJson()).toList(),
    };
  }
}

class ServerMessage {
  String id;
  DateTime createdAt;
  String text;
  MessageSender sender;
  MessageType type;

  String? appId;
  bool fromIntegration;

  List<MessageFile> files;
  List filesId;

  List<MessageConversation> memories;
  bool askForNps;
  int? rating;

  List<String> thinkings = [];
  ChartData? chartData;

  ServerMessage(
    this.id,
    this.createdAt,
    this.text,
    this.sender,
    this.type,
    this.appId,
    this.fromIntegration,
    this.files,
    this.filesId,
    this.memories, {
    this.askForNps = true,
    this.rating,
    this.chartData,
  });

  static ServerMessage fromJson(Map<String, dynamic> json) {
    final senderRaw = (json['sender'] ?? '').toString().toLowerCase();
    final sender = senderRaw == 'human' || senderRaw == 'user' ? MessageSender.human : MessageSender.ai;

    return ServerMessage(
      (json['id'] ?? '').toString(),
      DateTime.tryParse((json['created_at'] ?? '').toString())?.toLocal() ?? DateTime.now(),
      (json['text'] ?? '').toString(),
      sender,
      MessageType.valuesFromString((json['type'] ?? 'text').toString()),
      json['plugin_id']?.toString(),
      json['from_integration'] == true,
      ((json['files'] ?? const <dynamic>[]) as List)
          .whereType<Map<String, dynamic>>()
          .map(MessageFile.fromJson)
          .toList(),
      ((json['files_id'] ?? const <dynamic>[]) as List).map((m) => m.toString()).toList(),
      ((json['memories'] ?? const <dynamic>[]) as List)
          .whereType<Map<String, dynamic>>()
          .map(MessageConversation.fromJson)
          .toList(),
      askForNps: json['ask_for_nps'] != false,
      rating: json['rating'] is int ? json['rating'] as int : int.tryParse((json['rating'] ?? '').toString()),
      chartData: json['chart_data'] is Map<String, dynamic>
          ? ChartData.fromJson(json['chart_data'] as Map<String, dynamic>)
          : null,
    );
  }

  Map<String, dynamic> toJson() {
    return {
      'id': id,
      'created_at': createdAt.toUtc().toIso8601String(),
      'text': text,
      'sender': sender.toString().split('.').last,
      'type': type.value,
      'plugin_id': appId,
      'from_integration': fromIntegration,
      'memories': memories.map((m) => m.toJson()).toList(),
      'files': files.map((m) => m.toJson()).toList(),
      'ask_for_nps': askForNps,
      'rating': rating,
      'chart_data': chartData?.toJson(),
    };
  }

  bool areFilesOfSameType() {
    if (files.isEmpty) return true;
    final firstType = files.first.mimeTypeToFileType();
    return files.every((element) => element.mimeTypeToFileType() == firstType);
  }

  static ServerMessage empty({String? appId}) {
    return ServerMessage(
      '0000',
      DateTime.now(),
      '',
      MessageSender.ai,
      MessageType.text,
      appId,
      false,
      [],
      [],
      [],
    );
  }

  static ServerMessage failedMessage() {
    return ServerMessage(
      const Uuid().v4(),
      DateTime.now(),
      '服务暂时不可用，请稍后重试。',
      MessageSender.ai,
      MessageType.text,
      null,
      false,
      [],
      [],
      [],
    );
  }

  bool get isEmpty => id == '0000';
}

enum MessageChunkType {
  think('think'),
  data('data'),
  done('done'),
  error('error'),
  message('message');

  final String value;

  const MessageChunkType(this.value);
}

class ServerMessageChunk {
  String messageId;
  MessageChunkType type;
  String text;
  ServerMessage? message;

  ServerMessageChunk(
    this.messageId,
    this.text,
    this.type, {
    this.message,
  });

  static ServerMessageChunk failedMessage() {
    return ServerMessageChunk(
      const Uuid().v4(),
      '服务暂时不可用，请稍后重试。',
      MessageChunkType.error,
    );
  }
}
