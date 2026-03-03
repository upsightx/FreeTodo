import 'dart:convert';

import 'package:flutter/material.dart';

import 'package:freeu/backend/http/shared.dart';
import 'package:freeu/env/env.dart';

class CenterNodeTestPage extends StatefulWidget {
  const CenterNodeTestPage({super.key});

  @override
  State<CenterNodeTestPage> createState() => _CenterNodeTestPageState();
}

class _CenterNodeTestPageState extends State<CenterNodeTestPage> {
  bool _loadingUser = false;
  bool _loadingConversations = false;
  bool _loadingTodo = false;
  bool _loadingMessages = false;
  bool _loadingChatSend = false;

  String _userResult = '';
  String _conversationResult = '';
  String _todoResult = '';
  String _messagesResult = '';
  String _chatSendResult = '';
  final TextEditingController _chatInputController = TextEditingController(text: '你好，帮我测试一下聊天链路');

  Future<void> _testUser() async {
    setState(() {
      _loadingUser = true;
      _userResult = '请求中...';
    });
    final response = await makeApiCall(
      url: '${Env.apiBaseUrl}v1/users/me',
      headers: {},
      method: 'GET',
      body: '',
    );
    if (!mounted) return;
    setState(() {
      _loadingUser = false;
      if (response == null) {
        _userResult = '失败：无响应';
        return;
      }
      if (response.statusCode != 200) {
        _userResult = '失败：HTTP ${response.statusCode}\n${response.body}';
        return;
      }
      final body = jsonDecode(response.body) as Map<String, dynamic>;
      _userResult = '成功：uid=${body['uid'] ?? ''}';
    });
  }

  Future<void> _testConversations() async {
    setState(() {
      _loadingConversations = true;
      _conversationResult = '请求中...';
    });
    final response = await makeApiCall(
      url: '${Env.apiBaseUrl}v1/conversations?limit=10&offset=0',
      headers: {},
      method: 'GET',
      body: '',
    );
    if (!mounted) return;
    setState(() {
      _loadingConversations = false;
      if (response == null) {
        _conversationResult = '失败：无响应';
        return;
      }
      if (response.statusCode != 200) {
        _conversationResult = '失败：HTTP ${response.statusCode}\n${response.body}';
        return;
      }
      final decoded = jsonDecode(response.body);
      if (decoded is List) {
        _conversationResult = '成功：拉到 ${decoded.length} 条会话';
        return;
      }
      _conversationResult = '失败：返回格式异常 ${decoded.runtimeType}';
    });
  }

  Future<void> _testActionItems() async {
    setState(() {
      _loadingTodo = true;
      _todoResult = '请求中...';
    });
    try {
      final response = await makeApiCall(
        url: '${Env.apiBaseUrl}v1/action-items?limit=10&offset=0',
        headers: {},
        method: 'GET',
        body: '',
      );
      if (!mounted) return;
      setState(() {
        _loadingTodo = false;
        if (response == null) {
          _todoResult = '失败：无响应';
          return;
        }
        if (response.statusCode != 200) {
          _todoResult = '失败：HTTP ${response.statusCode}\n${response.body}';
          return;
        }
        final decoded = jsonDecode(response.body);
        if (decoded is List) {
          _todoResult = '成功：拉到 ${decoded.length} 条待办（list）';
          return;
        }
        if (decoded is Map<String, dynamic>) {
          final rawItems = decoded['action_items'];
          final items = rawItems is List ? rawItems : const [];
          _todoResult = '成功：拉到 ${items.length} 条待办（map）';
          return;
        }
        _todoResult = '失败：返回格式异常 ${decoded.runtimeType}';
      });
    } catch (e) {
      if (!mounted) return;
      setState(() {
        _loadingTodo = false;
        _todoResult = '失败：$e';
      });
    }
  }

  Future<void> _testMessages() async {
    setState(() {
      _loadingMessages = true;
      _messagesResult = '请求中...';
    });
    final response = await makeApiCall(
      url: '${Env.apiBaseUrl}v2/messages',
      headers: {},
      method: 'GET',
      body: '',
    );
    if (!mounted) return;
    setState(() {
      _loadingMessages = false;
      if (response == null) {
        _messagesResult = '失败：无响应';
        return;
      }
      if (response.statusCode != 200) {
        _messagesResult = '失败：HTTP ${response.statusCode}\n${response.body}';
        return;
      }
      final decoded = jsonDecode(response.body);
      if (decoded is List) {
        _messagesResult = '成功：拉到 ${decoded.length} 条消息';
        return;
      }
      if (decoded is Map<String, dynamic>) {
        final list = decoded['messages'];
        final size = list is List ? list.length : 0;
        _messagesResult = '成功：拉到 $size 条消息';
        return;
      }
      _messagesResult = '失败：返回格式异常 ${decoded.runtimeType}';
    });
  }

  Future<void> _testChatSend() async {
    final text = _chatInputController.text.trim();
    if (text.isEmpty) {
      setState(() {
        _chatSendResult = '失败：请输入问题';
      });
      return;
    }
    setState(() {
      _loadingChatSend = true;
      _chatSendResult = '请求中...';
    });

    final response = await makeApiCall(
      url: '${Env.apiBaseUrl}v2/messages',
      headers: {},
      method: 'POST',
      body: jsonEncode({'text': text}),
    );

    if (!mounted) return;
    setState(() {
      _loadingChatSend = false;
      if (response == null) {
        _chatSendResult = '失败：无响应';
        return;
      }
      if (response.statusCode != 200) {
        _chatSendResult = '失败：HTTP ${response.statusCode}\n${response.body}';
        return;
      }

      final body = utf8.decode(response.bodyBytes).trim();
      if (body.isEmpty) {
        _chatSendResult = '失败：空响应';
        return;
      }

      String finalText = body;
      for (final part in body.split('\n\n')) {
        final line = part.trim();
        if (line.startsWith('done: ')) {
          try {
            final decoded = utf8.decode(base64Decode(line.substring(6).trim()));
            final data = jsonDecode(decoded) as Map<String, dynamic>;
            finalText = (data['text'] ?? decoded).toString();
          } catch (_) {}
          break;
        }
      }

      final preview = finalText.length > 280 ? '${finalText.substring(0, 280)}...' : finalText;
      _chatSendResult = '成功：$preview';
    });
  }

  Widget _testTile({
    required String title,
    required String subtitle,
    required bool loading,
    required VoidCallback onTap,
    required String result,
  }) {
    return Container(
      margin: const EdgeInsets.only(bottom: 12),
      decoration: BoxDecoration(
        color: const Color(0xFF171D2D),
        borderRadius: BorderRadius.circular(12),
        border: Border.all(color: const Color(0xFF2A3450)),
      ),
      child: ListTile(
        title: Text(title, style: const TextStyle(color: Colors.white, fontWeight: FontWeight.w700)),
        subtitle: Padding(
          padding: const EdgeInsets.only(top: 6),
          child: Text(
            result.isEmpty ? subtitle : result,
            style: TextStyle(
              color: result.startsWith('成功') ? const Color(0xFF79E5A0) : Colors.white70,
            ),
          ),
        ),
        trailing: loading
            ? const SizedBox(
                width: 18,
                height: 18,
                child: CircularProgressIndicator(strokeWidth: 2),
              )
            : FilledButton(
                onPressed: onTap,
                child: const Text('测试'),
              ),
      ),
    );
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: const Color(0xFF0B1220),
      appBar: AppBar(
        backgroundColor: const Color(0xFF11192B),
        title: const Text('中心节点测试'),
      ),
      body: ListView(
        padding: const EdgeInsets.all(16),
        children: [
          const Text(
            '用于确认 App 是否连接到你的 LifeTrace 中心节点，并与 Web 共享数据。',
            style: TextStyle(color: Colors.white70),
          ),
          const SizedBox(height: 14),
          _testTile(
            title: '/v1/users/me',
            subtitle: '校验 token 与用户身份',
            loading: _loadingUser,
            onTap: _testUser,
            result: _userResult,
          ),
          _testTile(
            title: '/v1/conversations',
            subtitle: '校验会话列表是否可拉取（Web/App 共用）',
            loading: _loadingConversations,
            onTap: _testConversations,
            result: _conversationResult,
          ),
          _testTile(
            title: '/v1/action-items',
            subtitle: '校验待办数据是否可拉取（Web/App 共用）',
            loading: _loadingTodo,
            onTap: _testActionItems,
            result: _todoResult,
          ),
          _testTile(
            title: '/v2/messages',
            subtitle: '校验消息是否可拉取（Web/App 共用）',
            loading: _loadingMessages,
            onTap: _testMessages,
            result: _messagesResult,
          ),
          Container(
            margin: const EdgeInsets.only(bottom: 12),
            padding: const EdgeInsets.all(12),
            decoration: BoxDecoration(
              color: const Color(0xFF171D2D),
              borderRadius: BorderRadius.circular(12),
              border: Border.all(color: const Color(0xFF2A3450)),
            ),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                const Text(
                  'POST /v2/messages',
                  style: TextStyle(color: Colors.white, fontWeight: FontWeight.w700),
                ),
                const SizedBox(height: 8),
                TextField(
                  controller: _chatInputController,
                  style: const TextStyle(color: Colors.white),
                  decoration: InputDecoration(
                    hintText: '输入测试问题',
                    hintStyle: const TextStyle(color: Colors.white54),
                    filled: true,
                    fillColor: const Color(0xFF0F1628),
                    contentPadding: const EdgeInsets.symmetric(horizontal: 12, vertical: 10),
                    border: OutlineInputBorder(
                      borderRadius: BorderRadius.circular(10),
                      borderSide: const BorderSide(color: Color(0xFF2A3450)),
                    ),
                    enabledBorder: OutlineInputBorder(
                      borderRadius: BorderRadius.circular(10),
                      borderSide: const BorderSide(color: Color(0xFF2A3450)),
                    ),
                    focusedBorder: OutlineInputBorder(
                      borderRadius: BorderRadius.circular(10),
                      borderSide: const BorderSide(color: Color(0xFF79E5A0)),
                    ),
                  ),
                  maxLines: 2,
                  minLines: 1,
                ),
                const SizedBox(height: 10),
                Align(
                  alignment: Alignment.centerRight,
                  child: _loadingChatSend
                      ? const SizedBox(
                          width: 18,
                          height: 18,
                          child: CircularProgressIndicator(strokeWidth: 2),
                        )
                      : FilledButton(
                          onPressed: _testChatSend,
                          child: const Text('发送测试'),
                        ),
                ),
                if (_chatSendResult.isNotEmpty) ...[
                  const SizedBox(height: 8),
                  Text(
                    _chatSendResult,
                    style: TextStyle(
                      color: _chatSendResult.startsWith('成功') ? const Color(0xFF79E5A0) : Colors.white70,
                    ),
                  ),
                ],
              ],
            ),
          ),
        ],
      ),
    );
  }
}
