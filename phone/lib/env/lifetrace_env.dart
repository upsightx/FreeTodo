/// LifeTrace self-hosted environment.
///
/// Provides a hardcoded API base URL pointing to the user's own
/// LifeTrace Center. No envied code-gen needed — values can be
/// changed here directly or overridden at runtime via developer settings.
import 'env.dart';

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

  /// Standard EnvFields ///

  @override
  String? get openAIAPIKey => null;

  @override
  String? get mixpanelProjectToken => null;

  @override
  String? get apiBaseUrl => 'http://5.tcp.cpolar.cn:13365/';

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
