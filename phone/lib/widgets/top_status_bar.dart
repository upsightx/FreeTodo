import 'package:flutter/material.dart';
import 'package:font_awesome_flutter/font_awesome_flutter.dart';
import 'package:provider/provider.dart';

import 'package:omi/providers/connectivity_provider.dart';
import 'package:omi/providers/device_provider.dart';
import 'package:omi/providers/perception_provider.dart';
import 'package:omi/ui/mobile/mobile_tokens.dart';

class TopStatusBar extends StatelessWidget {
  const TopStatusBar({super.key});

  @override
  Widget build(BuildContext context) {
    return Consumer3<ConnectivityProvider, DeviceProvider, PerceptionProvider>(
      builder: (context, connectivityProvider, deviceProvider, perceptionProvider, child) {
        final isNodeConnected = connectivityProvider.isConnected;
        final connectedDevice = deviceProvider.connectedDevice;
        final batteryLevel = deviceProvider.batteryLevel;
        final isPerceptionPaused = !perceptionProvider.perceptionEnabled;

        return Container(
          width: double.infinity,
          padding: const EdgeInsets.fromLTRB(16, 8, 16, 8),
          decoration: BoxDecoration(
            color: const Color(0xFF0C1222),
            border: Border(
              bottom: BorderSide(color: MobileTokens.border, width: 1),
            ),
          ),
          child: SingleChildScrollView(
            scrollDirection: Axis.horizontal,
            child: Row(
              mainAxisSize: MainAxisSize.min,
              children: [
                _chip(
                  icon: isNodeConnected ? FontAwesomeIcons.server : FontAwesomeIcons.triangleExclamation,
                  text: isNodeConnected ? '核心节点已连接' : '核心节点离线',
                  color: isNodeConnected ? MobileTokens.success : MobileTokens.warning,
                ),
                if (connectedDevice != null) ...[
                  const SizedBox(width: 8),
                  _chip(
                    icon: FontAwesomeIcons.headphonesSimple,
                    text: batteryLevel >= 0
                        ? '${connectedDevice.name ?? '录音设备'} ${batteryLevel.toStringAsFixed(0)}%'
                        : '${connectedDevice.name ?? '录音设备'} 已连接',
                    color: MobileTokens.textSecondary,
                  ),
                ],
                if (isPerceptionPaused) ...[
                  const SizedBox(width: 8),
                  _chip(
                    icon: FontAwesomeIcons.pause,
                    text: '感知已暂停',
                    color: MobileTokens.warning,
                  ),
                ],
              ],
            ),
          ),
        );
      },
    );
  }

  Widget _chip({
    required IconData icon,
    required String text,
    required Color color,
  }) {
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 5),
      decoration: BoxDecoration(
        color: MobileTokens.surfaceElevated,
        borderRadius: BorderRadius.circular(999),
        border: Border.all(color: MobileTokens.border),
      ),
      child: Row(
        mainAxisSize: MainAxisSize.min,
        children: [
          FaIcon(icon, size: 10.5, color: color),
          const SizedBox(width: 6),
          Text(
            text,
            maxLines: 1,
            overflow: TextOverflow.ellipsis,
            style: const TextStyle(
              color: MobileTokens.textPrimary,
              fontSize: 12,
              fontWeight: FontWeight.w600,
            ),
          ),
        ],
      ),
    );
  }

}
