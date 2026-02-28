import 'dart:io';

import 'package:just_audio/just_audio.dart';

import 'package:omi/utils/logger.dart';

/// Plays a silent audio loop on iOS to prevent the system from suspending
/// the app when it moves to the background.  Android does not need this
/// because it has a proper foreground-service mechanism with WakeLock.
class IosBackgroundKeepAlive {
  IosBackgroundKeepAlive._();
  static final IosBackgroundKeepAlive instance = IosBackgroundKeepAlive._();

  AudioPlayer? _player;
  bool _active = false;

  bool get isActive => _active;

  Future<void> start() async {
    if (!Platform.isIOS) return;
    if (_active) return;

    try {
      _player ??= AudioPlayer();
      await _player!.setAsset('assets/audio/silence.wav');
      await _player!.setLoopMode(LoopMode.one);
      await _player!.setVolume(0.0);
      await _player!.play();
      _active = true;
      Logger.debug('[iOSKeepAlive] Silent audio loop started');
    } catch (e) {
      Logger.debug('[iOSKeepAlive] Failed to start: $e');
    }
  }

  Future<void> stop() async {
    if (!_active) return;

    try {
      await _player?.stop();
      _active = false;
      Logger.debug('[iOSKeepAlive] Silent audio loop stopped');
    } catch (e) {
      Logger.debug('[iOSKeepAlive] Failed to stop: $e');
    }
  }

  Future<void> dispose() async {
    await stop();
    await _player?.dispose();
    _player = null;
  }
}
