import 'package:flutter/material.dart';
import 'package:font_awesome_flutter/font_awesome_flutter.dart';
import 'package:provider/provider.dart';

import 'package:omi/pages/capture/connect.dart';
import 'package:omi/pages/settings/data_privacy_page.dart';
import 'package:omi/pages/settings/settings_drawer.dart';
import 'package:omi/providers/connectivity_provider.dart';
import 'package:omi/providers/device_provider.dart';
import 'package:omi/providers/perception_provider.dart';
import 'package:omi/ui/mobile/mobile_tokens.dart';
import 'package:omi/widgets/mobile_page_header.dart';

class MyPage extends StatefulWidget {
  const MyPage({super.key});

  @override
  State<MyPage> createState() => _MyPageState();
}

class _MyPageState extends State<MyPage> with AutomaticKeepAliveClientMixin {
  @override
  bool get wantKeepAlive => true;

  final ScrollController _scrollController = ScrollController();

  @override
  void dispose() {
    _scrollController.dispose();
    super.dispose();
  }

  void scrollToTop() {
    if (_scrollController.hasClients) {
      _scrollController.animateTo(0, duration: const Duration(milliseconds: 260), curve: Curves.easeOut);
    }
  }

  @override
  Widget build(BuildContext context) {
    super.build(context);

    return Container(
      decoration: const BoxDecoration(gradient: MobileTokens.appBackground),
      child: SafeArea(
        top: false,
        bottom: false,
        child: ListView(
          controller: _scrollController,
          padding: const EdgeInsets.fromLTRB(16, 12, 16, 24),
          children: [
            const MobilePageHeader(
              title: '我的',
              subtitle: '设备管理、感知权限与隐私配置',
              padding: EdgeInsets.fromLTRB(4, 0, 4, 14),
            ),
            _sectionTitle('设备与连接'),
            _deviceCard(),
            const SizedBox(height: 16),
            _sectionTitle('感知与隐私'),
            _perceptionCard(),
            const SizedBox(height: 16),
            _sectionTitle('通知偏好'),
            _simpleCard([
              _navTile(
                icon: FontAwesomeIcons.bell,
                title: '推送设置',
                subtitle: '消息分级、频率与提醒方式',
                onTap: () {},
              ),
              _divider(),
              _navTile(
                icon: FontAwesomeIcons.moon,
                title: '免打扰时段',
                subtitle: '默认 22:00 - 08:00',
                onTap: () {},
              ),
            ]),
            const SizedBox(height: 16),
            _sectionTitle('账号'),
            _simpleCard([
              _navTile(
                icon: FontAwesomeIcons.user,
                title: '账号信息',
                subtitle: '查看个人资料与绑定设备',
                onTap: () {},
              ),
              _divider(),
              _navTile(
                icon: FontAwesomeIcons.gear,
                title: '更多设置',
                subtitle: '进入完整设置面板',
                onTap: () => SettingsDrawer.show(context),
              ),
            ]),
          ],
        ),
      ),
    );
  }

  Widget _deviceCard() {
    return Consumer2<ConnectivityProvider, DeviceProvider>(
      builder: (context, connectivityProvider, deviceProvider, child) {
        final connected = connectivityProvider.isConnected;
        final device = deviceProvider.connectedDevice;
        final battery = deviceProvider.batteryLevel;

        return _simpleCard([
          _statusTile(
            icon: FontAwesomeIcons.server,
            title: '核心节点',
            subtitle: connected ? '已连接 · 运行正常' : '离线 · 请检查网络与中心节点',
            statusColor: connected ? MobileTokens.success : MobileTokens.danger,
            onTap: null,
          ),
          _divider(),
          _statusTile(
            icon: FontAwesomeIcons.headphonesSimple,
            title: device?.name ?? '录音设备',
            subtitle: device == null
                ? '未连接设备'
                : battery >= 0
                    ? '已连接 · 电量 ${battery.toStringAsFixed(0)}%'
                    : '已连接',
            statusColor: device == null ? MobileTokens.textSecondary : MobileTokens.success,
            onTap: null,
          ),
          _divider(),
          _navTile(
            icon: FontAwesomeIcons.plus,
            title: '添加新设备',
            subtitle: '扫描并连接蓝牙设备',
            onTap: () {
              Navigator.push(
                context,
                MaterialPageRoute(builder: (context) => const ConnectDevicePage()),
              );
            },
          ),
        ]);
      },
    );
  }

  Widget _perceptionCard() {
    return Consumer<PerceptionProvider>(
      builder: (context, perceptionProvider, child) {
        return _simpleCard([
          _switchTile(
            icon: FontAwesomeIcons.eye,
            title: '感知总开关',
            value: perceptionProvider.perceptionEnabled,
            onChanged: (value) {
              perceptionProvider.setPerceptionEnabled(value);
            },
          ),
          _divider(),
          _switchTile(
            icon: FontAwesomeIcons.locationDot,
            title: 'GPS 位置',
            value: perceptionProvider.gpsEnabled,
            onChanged: (value) {
              perceptionProvider.setGpsEnabled(value);
            },
          ),
          _divider(),
          _switchTile(
            icon: FontAwesomeIcons.paste,
            title: '剪贴板监听',
            value: perceptionProvider.clipboardEnabled,
            onChanged: (value) {
              perceptionProvider.setClipboardEnabled(value);
            },
          ),
          _divider(),
          _switchTile(
            icon: FontAwesomeIcons.bell,
            title: '通知栏监听',
            value: perceptionProvider.notificationListenerEnabled,
            onChanged: (value) {
              perceptionProvider.setNotificationListenerEnabled(value);
            },
          ),
          _divider(),
          _navTile(
            icon: FontAwesomeIcons.shield,
            title: '数据与隐私',
            subtitle: '查看和管理本地记忆数据',
            onTap: () {
              Navigator.push(
                context,
                MaterialPageRoute(builder: (context) => const DataPrivacyPage()),
              );
            },
          ),
        ]);
      },
    );
  }

  Widget _sectionTitle(String text) {
    return Padding(
      padding: const EdgeInsets.fromLTRB(6, 0, 6, 8),
      child: Text(
        text,
        style: const TextStyle(
          color: MobileTokens.textSecondary,
          fontSize: 13,
          fontWeight: FontWeight.w600,
        ),
      ),
    );
  }

  Widget _simpleCard(List<Widget> children) {
    return Container(
      decoration: MobileTokens.cardDecoration(),
      child: Column(children: children),
    );
  }

  Widget _divider() {
    return const Divider(height: 1, thickness: 1, color: MobileTokens.border, indent: 48, endIndent: 12);
  }

  Widget _statusTile({
    required IconData icon,
    required String title,
    required String subtitle,
    required Color statusColor,
    VoidCallback? onTap,
  }) {
    return _baseTile(
      icon: icon,
      title: title,
      subtitle: subtitle,
      iconColor: statusColor,
      trailing: Container(
        width: 8,
        height: 8,
        decoration: BoxDecoration(color: statusColor, shape: BoxShape.circle),
      ),
      onTap: onTap,
    );
  }

  Widget _switchTile({
    required IconData icon,
    required String title,
    required bool value,
    required ValueChanged<bool> onChanged,
  }) {
    return _baseTile(
      icon: icon,
      title: title,
      subtitle: null,
      iconColor: value ? MobileTokens.accent : MobileTokens.textSecondary,
      trailing: Switch(
        value: value,
        onChanged: onChanged,
        activeColor: MobileTokens.accent,
        activeTrackColor: MobileTokens.accentSoft,
      ),
      onTap: null,
    );
  }

  Widget _navTile({
    required IconData icon,
    required String title,
    required String subtitle,
    required VoidCallback onTap,
  }) {
    return _baseTile(
      icon: icon,
      title: title,
      subtitle: subtitle,
      iconColor: MobileTokens.accent,
      trailing: const Icon(FontAwesomeIcons.chevronRight, size: 12, color: MobileTokens.textSecondary),
      onTap: onTap,
    );
  }

  Widget _baseTile({
    required IconData icon,
    required String title,
    required String? subtitle,
    required Color iconColor,
    required Widget trailing,
    required VoidCallback? onTap,
  }) {
    final tile = Padding(
      padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 12),
      child: Row(
        children: [
          Container(
            width: 30,
            height: 30,
            decoration: BoxDecoration(
              color: iconColor.withOpacity(0.15),
              borderRadius: BorderRadius.circular(8),
            ),
            child: Center(child: FaIcon(icon, size: 13, color: iconColor)),
          ),
          const SizedBox(width: 10),
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(
                  title,
                  style: const TextStyle(
                    color: MobileTokens.textPrimary,
                    fontSize: 15,
                    fontWeight: FontWeight.w600,
                  ),
                ),
                if (subtitle != null) ...[
                  const SizedBox(height: 3),
                  Text(
                    subtitle,
                    style: const TextStyle(color: MobileTokens.textSecondary, fontSize: 12.5),
                  ),
                ],
              ],
            ),
          ),
          trailing,
        ],
      ),
    );

    if (onTap == null) return tile;

    return InkWell(
      onTap: onTap,
      borderRadius: BorderRadius.circular(12),
      child: tile,
    );
  }
}
