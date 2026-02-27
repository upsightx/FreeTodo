import 'package:flutter/foundation.dart';
import 'package:flutter/material.dart';

import 'package:firebase_crashlytics/firebase_crashlytics.dart';

import 'package:omi/env/lifetrace_env.dart';
import 'package:omi/utils/debugging/crash_reporter.dart';
import 'package:omi/utils/logger.dart';
import 'package:omi/utils/platform/platform_service.dart';

class CrashlyticsManager implements CrashReporter {
  static final CrashlyticsManager _instance = CrashlyticsManager._internal();
  static CrashlyticsManager get instance => _instance;

  CrashlyticsManager._internal();

  factory CrashlyticsManager() {
    return _instance;
  }

  static Future<void> init() async {
    if (LifeTraceEnv.enabled) return;
    if (kDebugMode) {
      await FirebaseCrashlytics.instance.setCrashlyticsCollectionEnabled(false);
    } else {
      await FirebaseCrashlytics.instance.setCrashlyticsCollectionEnabled(true);
    }
  }

  @override
  void identifyUser(String email, String name, String userId) {
    if (LifeTraceEnv.enabled) return;
    PlatformService.executeIfSupported(
      true,
      () async {
        await FirebaseCrashlytics.instance.setUserIdentifier(userId);
        if (email.isNotEmpty) {
          await FirebaseCrashlytics.instance.setCustomKey('user_email', email);
        }
        if (name.isNotEmpty) {
          await FirebaseCrashlytics.instance.setCustomKey('user_name', name);
        }
      },
    );
  }

  @override
  void logInfo(String message) {
    if (LifeTraceEnv.enabled) return;
    PlatformService.executeIfSupported(true, () => FirebaseCrashlytics.instance.log(message));
  }

  @override
  void logError(String message) {
    if (LifeTraceEnv.enabled) return;
    PlatformService.executeIfSupported(true, () => FirebaseCrashlytics.instance.log('ERROR: $message'));
  }

  @override
  void logWarn(String message) {
    if (LifeTraceEnv.enabled) return;
    PlatformService.executeIfSupported(true, () => FirebaseCrashlytics.instance.log('WARN: $message'));
  }

  @override
  void logDebug(String message) {
    if (LifeTraceEnv.enabled) return;
    PlatformService.executeIfSupported(true, () => FirebaseCrashlytics.instance.log('DEBUG: $message'));
  }

  @override
  void logVerbose(String message) {
    if (LifeTraceEnv.enabled) return;
    PlatformService.executeIfSupported(true, () => FirebaseCrashlytics.instance.log('VERBOSE: $message'));
  }

  @override
  void setUserAttribute(String key, String value) {
    if (LifeTraceEnv.enabled) return;
    PlatformService.executeIfSupported(true, () => FirebaseCrashlytics.instance.setCustomKey(key, value));
  }

  @override
  void setEnabled(bool isEnabled) {
    if (LifeTraceEnv.enabled) return;
    PlatformService.executeIfSupported(true, () async {
      await FirebaseCrashlytics.instance.setCrashlyticsCollectionEnabled(isEnabled);
    });
  }

  @override
  Future<void> reportCrash(Object exception, StackTrace stackTrace, {Map<String, String>? userAttributes}) async {
    if (LifeTraceEnv.enabled) return;
    await PlatformService.executeIfSupportedAsync(true, () async {
      if (userAttributes != null) {
        for (final entry in userAttributes.entries) {
          await FirebaseCrashlytics.instance.setCustomKey(entry.key, entry.value);
        }
      }
      await FirebaseCrashlytics.instance.recordError(exception, stackTrace);
    });
  }

  @override
  NavigatorObserver? getNavigatorObserver() {
    return null;
  }

  @override
  bool get isSupported => !LifeTraceEnv.enabled;
}
