import 'dart:async';
import 'dart:io';
import 'dart:typed_data';

import 'package:flutter/widgets.dart';

import 'package:nordic_dfu/nordic_dfu.dart';
import 'package:path_provider/path_provider.dart';
import 'package:provider/provider.dart';

import 'package:omi/backend/http/api/device.dart';
import 'package:omi/backend/http/shared.dart';
import 'package:omi/backend/schema/bt_device/bt_device.dart';
import 'package:omi/providers/device_provider.dart';
import 'package:omi/utils/device.dart';
import 'package:omi/utils/logger.dart';

mixin FirmwareMixin<T extends StatefulWidget> on State<T> {
  Map latestFirmwareDetails = {};
  bool isDownloading = false;
  bool isDownloaded = false;
  int downloadProgress = 0;
  bool isInstalling = false;
  bool isInstalled = false;
  int installProgress = 0;
  bool isLegacySecureDFU = true;
  List<String> otaUpdateSteps = [];

  Future<void> startDfu(BtDevice btDevice, {bool fileInAssets = false, String? zipFilePath}) async {
    if (isLegacySecureDFU) {
      return startLegacyDfu(btDevice, fileInAssets: fileInAssets);
    }
    Logger.debug('MCU DFU not available – mcumgr_flutter removed for LifeTrace build');
    setState(() {
      isInstalling = false;
    });
  }

  Future<void> killMcuUpdateManager() async {}

  Future<void> startLegacyDfu(BtDevice btDevice, {bool fileInAssets = false}) async {
    setState(() {
      isInstalling = true;
    });
    await Provider.of<DeviceProvider>(context, listen: false).prepareDFU();
    await Future.delayed(const Duration(seconds: 2));
    String firmwareFile = '${(await getApplicationDocumentsDirectory()).path}/firmware.zip';
    NordicDfu dfu = NordicDfu();
    await dfu.startDfu(
      btDevice.id,
      firmwareFile,
      fileInAsset: fileInAssets,
      numberOfPackets: 8,
      enableUnsafeExperimentalButtonlessServiceInSecureDfu: true,
      iosSpecialParameter: const IosSpecialParameter(
        packetReceiptNotificationParameter: 8,
        forceScanningForNewAddressInLegacyDfu: true,
        connectionTimeout: 60,
      ),
      androidSpecialParameter: const AndroidSpecialParameter(
        packetReceiptNotificationsEnabled: true,
        rebootTime: 1000,
      ),
      onProgressChanged: (deviceAddress, percent, speed, avgSpeed, currentPart, partsTotal) {
        Logger.debug('deviceAddress: $deviceAddress, percent: $percent');
        setState(() {
          installProgress = percent.toInt();
        });
      },
      onError: (deviceAddress, error, errorType, message) {
        Logger.debug('deviceAddress: $deviceAddress, error: $error, errorType: $errorType, message: $message');
        setState(() {
          isInstalling = false;
        });
        final deviceProvider = Provider.of<DeviceProvider>(context, listen: false);
        deviceProvider.resetFirmwareUpdateState();
      },
      onDeviceConnecting: (deviceAddress) => Logger.debug('deviceAddress: $deviceAddress, onDeviceConnecting'),
      onDeviceConnected: (deviceAddress) => Logger.debug('deviceAddress: $deviceAddress, onDeviceConnected'),
      onDfuProcessStarting: (deviceAddress) => Logger.debug('deviceAddress: $deviceAddress, onDfuProcessStarting'),
      onDfuProcessStarted: (deviceAddress) => Logger.debug('deviceAddress: $deviceAddress, onDfuProcessStarted'),
      onEnablingDfuMode: (deviceAddress) => Logger.debug('deviceAddress: $deviceAddress, onEnablingDfuMode'),
      onFirmwareValidating: (deviceAddress) => Logger.debug('address: $deviceAddress, onFirmwareValidating'),
      onDfuCompleted: (deviceAddress) {
        Logger.debug('deviceAddress: $deviceAddress, onDfuCompleted');
        setState(() {
          isInstalling = false;
          isInstalled = true;
        });
      },
    );
  }

  Future getLatestVersion(
      {required String deviceModelNumber,
      required String firmwareRevision,
      required String hardwareRevision,
      required String manufacturerName}) async {
    latestFirmwareDetails = await getLatestFirmwareVersion(
      deviceModelNumber: deviceModelNumber,
      firmwareRevision: firmwareRevision,
      hardwareRevision: hardwareRevision,
      manufacturerName: manufacturerName,
    );
    if (latestFirmwareDetails['ota_update_steps'] != null) {
      otaUpdateSteps = List<String>.from(latestFirmwareDetails['ota_update_steps']);
    }
    if (latestFirmwareDetails['is_legacy_secure_dfu'] != null) {
      isLegacySecureDFU = latestFirmwareDetails['is_legacy_secure_dfu'];
    }
  }

  Future<(String, bool, String)> shouldUpdateFirmware({required String currentFirmware}) async {
    return DeviceUtils.shouldUpdateFirmware(
        currentFirmware: currentFirmware, latestFirmwareDetails: latestFirmwareDetails);
  }

  Future downloadFirmware() async {
    final zipUrl = latestFirmwareDetails['zip_url'];
    if (zipUrl == null) {
      Logger.debug('Error: zip_url is null in latestFirmwareDetails');
      setState(() {
        isDownloading = false;
      });
      final deviceProvider = Provider.of<DeviceProvider>(context, listen: false);
      deviceProvider.resetFirmwareUpdateState();
      return;
    }

    String dir = (await getApplicationDocumentsDirectory()).path;

    setState(() {
      isDownloading = true;
      isDownloaded = false;
      downloadProgress = 0;
    });

    try {
      final r = await makeRawApiCall(method: 'GET', url: zipUrl);
      final completer = Completer<void>();
      final int? totalBytes = r.contentLength;

      List<List<int>> chunks = [];
      int downloaded = 0;

      r.stream.listen((List<int> chunk) {
        chunks.add(chunk);
        downloaded += chunk.length;
        if (totalBytes != null && totalBytes > 0) {
          Logger.debug('downloadPercentage: ${downloaded / totalBytes * 100}');
          setState(() {
            downloadProgress = (downloaded / totalBytes * 100).toInt();
          });
        }
      }, onDone: () async {
        try {
          Logger.debug('downloadPercentage: 100');
          File file = File('$dir/firmware.zip');
          final Uint8List bytes = Uint8List(downloaded);
          int offset = 0;
          for (List<int> chunk in chunks) {
            bytes.setRange(offset, offset + chunk.length, chunk);
            offset += chunk.length;
          }
          await file.writeAsBytes(bytes);
          setState(() {
            isDownloading = false;
            isDownloaded = true;
            downloadProgress = 100;
          });
          completer.complete();
        } catch (e) {
          completer.completeError(e);
        }
      }, onError: (error) {
        Logger.debug('Download error: $error');
        setState(() {
          isDownloading = false;
        });
        final deviceProvider = Provider.of<DeviceProvider>(context, listen: false);
        deviceProvider.resetFirmwareUpdateState();
        completer.completeError(error);
      });

      await completer.future;
    } catch (e) {
      Logger.debug('Download error: $e');
      if (mounted) {
        setState(() {
          isDownloading = false;
        });
      }
      final deviceProvider = Provider.of<DeviceProvider>(context, listen: false);
      deviceProvider.resetFirmwareUpdateState();
    }
  }
}
