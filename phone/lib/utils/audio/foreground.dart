import 'dart:io';

import 'package:flutter/foundation.dart';
import 'package:flutter/material.dart';

import 'package:flutter_foreground_task/flutter_foreground_task.dart';
import 'package:geolocator/geolocator.dart';
import 'package:permission_handler/permission_handler.dart';

import 'package:freeu/utils/logger.dart';
import 'package:freeu/utils/platform/platform_service.dart';

@pragma('vm:entry-point')
void _startForegroundCallback() {
  FlutterForegroundTask.setTaskHandler(_ForegroundFirstTaskHandler());
}

class _ForegroundFirstTaskHandler extends TaskHandler {
  DateTime? _locationUpdatedAt;

  @override
  Future<void> onStart(DateTime timestamp, TaskStarter taskStarter) async {
    Logger.debug("Starting foreground task");
    _locationInBackground();
  }

  Future _locationInBackground() async {
    if (await Geolocator.isLocationServiceEnabled()) {
      if (await Geolocator.checkPermission() == LocationPermission.always) {
        var locationData = await Geolocator.getCurrentPosition();
        if (_locationUpdatedAt == null ||
            _locationUpdatedAt!.isBefore(DateTime.now().subtract(const Duration(minutes: 5)))) {
          Object loc = {
            "latitude": locationData.latitude,
            "longitude": locationData.longitude,
            'altitude': locationData.altitude,
            'accuracy': locationData.accuracy,
            'time': locationData.timestamp.toUtc().toIso8601String(),
          };
          FlutterForegroundTask.sendDataToMain(loc);
          _locationUpdatedAt = DateTime.now();
        }
      } else {
        Object loc = {'error': 'Always location permission is not granted'};
        FlutterForegroundTask.sendDataToMain(loc);
      }
    } else {
      Object loc = {'error': 'Location service is not enabled'};
      FlutterForegroundTask.sendDataToMain(loc);
    }
  }

  @override
  void onReceiveData(Object data) async {
    Logger.debug('onReceiveData: $data');
    await _locationInBackground();
  }

  @override
  void onRepeatEvent(DateTime timestamp) async {
    Logger.debug("Foreground repeat event triggered");
    await _locationInBackground();
  }

  @override
  Future<void> onDestroy(DateTime timestamp, bool isTimeout) async {
    Logger.debug("Destroying foreground task");
    FlutterForegroundTask.stopService();
  }
}

class ForegroundUtil {
  static bool _isInitialized = false;
  static bool _isStarting = false;

  static Future<void> requestPermissions() async {
    // Android 13+, you need to allow notification permission to display foreground service notification.
    //
    // iOS: If you need notification, ask for permission.
    final NotificationPermission notificationPermissionStatus =
        await FlutterForegroundTask.checkNotificationPermission();
    if (notificationPermissionStatus != NotificationPermission.granted) {
      await FlutterForegroundTask.requestNotificationPermission();
    }

    if (Platform.isAndroid) {
      // FGS type is connectedDevice only — no microphone/location permissions needed.
      if (!await FlutterForegroundTask.isIgnoringBatteryOptimizations) {
        await FlutterForegroundTask.requestIgnoreBatteryOptimization();
      }
    }
  }

  Future<bool> get isIgnoringBatteryOptimizations async => await FlutterForegroundTask.isIgnoringBatteryOptimizations;

  static Future<void> initializeForegroundService() async {
    if (PlatformService.isDesktop) return;

    if (_isInitialized) {
      Logger.debug('ForegroundService already initialized, skipping');
      return;
    }

    if (await FlutterForegroundTask.isRunningService) {
      _isInitialized = true;
      return;
    }

    Logger.debug('initializeForegroundService');

    try {
      FlutterForegroundTask.init(
        androidNotificationOptions: AndroidNotificationOptions(
          channelId: 'foreground_service',
          channelName: 'Foreground Service Notification',
          channelDescription: 'Transcription service is running in the background.',
          channelImportance: NotificationChannelImportance.LOW,
          priority: NotificationPriority.HIGH,
          // iconData: const NotificationIconData(
          //   resType: ResourceType.mipmap,
          //   resPrefix: ResourcePrefix.ic,
          //   name: 'launcher',
          // ),
        ),
        iosNotificationOptions: const IOSNotificationOptions(
          showNotification: false,
          playSound: false,
        ),
        foregroundTaskOptions: ForegroundTaskOptions(
          eventAction: ForegroundTaskEventAction.repeat(60 * 1000 * 5),
          autoRunOnBoot: true,
          allowWakeLock: true,
          allowWifiLock: true,
        ),
      );
      _isInitialized = true;
      Logger.debug('ForegroundService initialized successfully');
    } catch (e) {
      Logger.debug('ForegroundService initialization failed: $e');
      _isInitialized = false;
    }
  }

  static Future<ServiceRequestResult> startForegroundTask() async {
    if (PlatformService.isDesktop) return const ServiceRequestSuccess();

    if (_isStarting) {
      Logger.debug('ForegroundTask already starting, skipping');
      return const ServiceRequestSuccess();
    }

    _isStarting = true;
    Logger.debug('startForegroundTask');

    try {
      final alreadyRunning = await FlutterForegroundTask.isRunningService;
      Logger.debug('[BGDBG] ForegroundTask alreadyRunning=$alreadyRunning');
      ServiceRequestResult result;
      if (alreadyRunning) {
        result = await FlutterForegroundTask.restartService();
        Logger.debug('[BGDBG] ForegroundTask restarted, result=$result');
      } else {
        result = await FlutterForegroundTask.startService(
          notificationTitle: 'Your FreeU Device is connected.',
          notificationText: 'Transcription service is running in the background.',
          callback: _startForegroundCallback,
        );
        Logger.debug('[BGDBG] ForegroundTask freshStart, result=$result');
      }
      final runningAfter = await FlutterForegroundTask.isRunningService;
      Logger.debug('[BGDBG] ForegroundTask isRunning after start=$runningAfter');
      return result;
    } catch (e) {
      Logger.debug('ForegroundTask start failed: $e');
      return ServiceRequestFailure(error: e.toString());
    } finally {
      _isStarting = false;
    }
  }

  static Future<void> stopForegroundTask() async {
    if (PlatformService.isDesktop) return;
    Logger.debug('stopForegroundTask');

    try {
      if (await FlutterForegroundTask.isRunningService) {
        await FlutterForegroundTask.stopService();
        _isInitialized = false;
      }
    } catch (e) {
      Logger.debug('ForegroundTask stop failed: $e');
    }
  }
}
