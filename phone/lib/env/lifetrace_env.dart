/// LifeTrace self-hosted environment.
///
/// Provides a hardcoded API base URL pointing to the user's own
/// LifeTrace Center. No envied code-gen needed — values can be
/// changed here directly or overridden at runtime via developer settings.
import 'env.dart';

class LifeTraceServerPreset {
  final String name;
  final String url;
  const LifeTraceServerPreset(this.name, this.url);
}

class LifeTraceEnv implements EnvFields {
  const LifeTraceEnv();

  /// LifeTrace-specific configuration ///

  /// Static bearer token that must match the value in
  /// `lifetrace/config/config.yaml → omi_compat.token`.
  static const String lifetraceToken = 'lifetrace-omi-compat-2026';

  /// Single-user UID that must match `omi_compat.uid` in the Center config.
  static const String lifetraceUid = 'lifetrace-user';

  /// Whether we are running in LifeTrace self-hosted mode.
  /// When true the app skips Firebase Auth and uses the static token above.
  static bool enabled = false;

  /// Pre-configured server endpoints.
  /// Users can switch between these in Settings or enter a custom URL.
  static const List<LifeTraceServerPreset> serverPresets = [
    LifeTraceServerPreset('TCP 隧道', 'http://2.tcp.cpolar.cn:12691/'),
    LifeTraceServerPreset('HTTP 隧道', 'https://tybbackend.cpolar.cn/'),
    LifeTraceServerPreset('局域网', 'http://192.168.1.100:8001/'),
  ];

  static const String defaultApiBaseUrl = 'http://2.tcp.cpolar.cn:12691/';

  /// Standard EnvFields ///

  @override
  String? get openAIAPIKey => null;

  @override
  String? get mixpanelProjectToken => null;

  @override
  String? get apiBaseUrl => defaultApiBaseUrl;

  @override
  String? get growthbookApiKey => null;

  @override
  String? get googleMapsApiKey => null;

  @override
  String? get intercomAppId => null;

  @override
  String? get intercomIOSApiKey => null;

  @override
  String? get intercomAndroidApiKey => null;

  @override
  String? get googleClientId => null;

  @override
  String? get googleClientSecret => null;

  @override
  bool? get useWebAuth => false;

  @override
  bool? get useAuthCustomToken => false;

  @override
  String? get stagingApiUrl => null;
}
