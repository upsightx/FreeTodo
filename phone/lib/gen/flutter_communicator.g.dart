// STUB – Pigeon-generated Apple Watch communication interface.
// LifeTrace Android builds do not use Apple Watch; this stub satisfies the compiler.
// To regenerate: dart run pigeon --input lib/watch_interface.dart

// ignore_for_file: unnecessary_import, unused_import
import 'dart:async';
import 'dart:typed_data' show Uint8List;

import 'package:flutter/foundation.dart' show ReadBuffer, WriteBuffer;
import 'package:flutter/services.dart';

class WatchRecorderHostAPI {
  Future<void> startRecording() async {}
  Future<void> stopRecording() async {}
  Future<void> sendAudioData(Uint8List audioData) async {}
  Future<void> sendAudioChunk(
      Uint8List audioChunk, int chunkIndex, bool isLast, double sampleRate) async {}
  Future<bool> isWatchPaired() async => false;
  Future<bool> isWatchReachable() async => false;
  Future<bool> isWatchSessionSupported() async => false;
  Future<bool> isWatchAppInstalled() async => false;
  Future<void> requestWatchMicrophonePermission() async {}
  Future<void> requestMainAppMicrophonePermission() async {}
  Future<bool> checkMainAppMicrophonePermission() async => false;
  Future<double> getWatchBatteryLevel() async => -1;
  Future<int> getWatchBatteryState() async => 0;
  Future<void> requestWatchBatteryUpdate() async {}
  Future<Map<String, String>> getWatchInfo() async => {};
}

abstract class WatchRecorderFlutterAPI {
  void onRecordingStarted();
  void onRecordingStopped();
  void onAudioData(Uint8List audioData);
  void onAudioChunk(Uint8List audioChunk, int chunkIndex, bool isLast, double sampleRate);
  void onRecordingError(String error);
  void onMicrophonePermissionResult(bool granted);
  void onMainAppMicrophonePermissionResult(bool granted);
  void onWatchBatteryUpdate(double batteryLevel, int batteryState);

  static void setUp(WatchRecorderFlutterAPI? api) {
    // No-op on Android
  }
}
