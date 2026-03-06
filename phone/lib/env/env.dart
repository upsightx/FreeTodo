import 'package:freeu/env/dev_env.dart';

abstract class Env {
  static late final EnvFields _instance;
  static String? _apiBaseUrlOverride;
  static String? _wsBaseUrlOverride;
  static String? _agentProxyWsUrlOverride;
  static bool isTestFlight = false;

  static void init([EnvFields? instance]) {
    _instance = instance ?? DevEnv() as EnvFields;
  }

  static void overrideApiBaseUrl(String url) {
    _apiBaseUrlOverride = url;
  }

  /// Override the base URL used for WebSocket connections (e.g. TCP tunnel).
  /// When not set, WebSocket URLs are derived from [apiBaseUrl].
  static void overrideWsBaseUrl(String url) {
    _wsBaseUrlOverride = url;
  }

  /// The base URL for WebSocket connections.
  /// Falls back to [apiBaseUrl] if no separate override is set.
  static String? get wsBaseUrl => _wsBaseUrlOverride ?? apiBaseUrl;

  static void overrideAgentProxyWsUrl(String url) {
    _agentProxyWsUrlOverride = url;
  }

  static String? get openAIAPIKey => _instance.openAIAPIKey;

  static String? get mixpanelProjectToken => _instance.mixpanelProjectToken;

  // static String? get apiBaseUrl => 'https://omi-backend.ngrok.app/';
  static String? get apiBaseUrl => _apiBaseUrlOverride ?? _instance.apiBaseUrl;

  static String get stagingApiUrl {
    final url = _instance.stagingApiUrl;
    if (url != null && url.isNotEmpty) return url;
    return 'https://api.omiapi.com/';
  }

  static bool get isUsingStagingApi => _apiBaseUrlOverride != null && _apiBaseUrlOverride == stagingApiUrl;

  /// WebSocket URL for the agent proxy service.
  /// Derives from apiBaseUrl: api.omi.me → agent.omi.me, api.omiapi.com → agent.omiapi.com.
  /// Can be overridden via Env.overrideAgentProxyWsUrl() for local testing.
  static String get agentProxyWsUrl {
    if (_agentProxyWsUrlOverride != null) return _agentProxyWsUrlOverride!;
    final base = apiBaseUrl ?? 'https://tybbackend.cpolar.cn';
    final host = Uri.parse(base).host;
    return 'wss://$host/v1/agent/ws';
  }

  static String? get growthbookApiKey => _instance.growthbookApiKey;

  static String? get googleMapsApiKey => _instance.googleMapsApiKey;

  static String? get intercomAppId => _instance.intercomAppId;

  static String? get intercomIOSApiKey => _instance.intercomIOSApiKey;

  static String? get intercomAndroidApiKey => _instance.intercomAndroidApiKey;

  static String? get googleClientId => _instance.googleClientId;

  static String? get googleClientSecret => _instance.googleClientSecret;

  static bool get useWebAuth => _instance.useWebAuth ?? false;

  static bool get useAuthCustomToken => _instance.useAuthCustomToken ?? false;
}

abstract class EnvFields {
  String? get openAIAPIKey;

  String? get mixpanelProjectToken;

  String? get apiBaseUrl;

  String? get growthbookApiKey;

  String? get googleMapsApiKey;

  String? get intercomAppId;

  String? get intercomIOSApiKey;

  String? get intercomAndroidApiKey;

  String? get googleClientId;

  String? get googleClientSecret;

  bool? get useWebAuth;

  bool? get useAuthCustomToken;

  String? get stagingApiUrl;
}
