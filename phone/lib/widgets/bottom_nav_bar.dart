import 'package:flutter/material.dart';
import 'package:flutter/services.dart';

import 'package:font_awesome_flutter/font_awesome_flutter.dart';
import 'package:provider/provider.dart';

import 'package:omi/providers/home_provider.dart';
import 'package:omi/providers/notification_center_provider.dart';
import 'package:omi/ui/mobile/mobile_tokens.dart';
import 'package:omi/utils/analytics/mixpanel.dart';

class BottomNavBar extends StatelessWidget {
  const BottomNavBar({
    super.key,
    required this.onTabTap,
    this.showCenterButton = false,
  });

  final void Function(int index, bool isRepeat) onTabTap;
  final bool showCenterButton;

  @override
  Widget build(BuildContext context) {
    return Consumer<HomeProvider>(
      builder: (context, home, child) {
        final bottomInset = MediaQuery.of(context).padding.bottom;
        const double navContentHeight = 64;
        return Material(
          color: const Color(0xFF0C1222),
          child: Container(
            width: double.infinity,
            height: navContentHeight + bottomInset,
            padding: EdgeInsets.only(top: 4, bottom: bottomInset),
            decoration: const BoxDecoration(
              border: Border(
                top: BorderSide(color: MobileTokens.border, width: 1),
              ),
            ),
            child: Row(
              children: [
                _buildTab(
                  context: context,
                  home: home,
                  index: 0,
                  icon: FontAwesomeIcons.inbox,
                  label: '消息',
                  analyticsName: 'Messages',
                  badgeCount: context.watch<NotificationCenterProvider>().pendingCount,
                ),
                _buildTab(
                  context: context,
                  home: home,
                  index: 1,
                  icon: FontAwesomeIcons.listCheck,
                  label: '待办',
                  analyticsName: 'Tasks',
                ),
                _buildTab(
                  context: context,
                  home: home,
                  index: 2,
                  icon: FontAwesomeIcons.comments,
                  label: '对话',
                  analyticsName: 'Chat',
                ),
                _buildTab(
                  context: context,
                  home: home,
                  index: 3,
                  icon: FontAwesomeIcons.userLarge,
                  label: '我的',
                  analyticsName: 'My',
                ),
              ],
            ),
          ),
        );
      },
    );
  }

  Widget _buildTab({
    required BuildContext context,
    required HomeProvider home,
    required int index,
    required IconData icon,
    required String label,
    required String analyticsName,
    int badgeCount = 0,
  }) {
    final selected = home.selectedIndex == index;
    return Expanded(
      child: InkWell(
        borderRadius: BorderRadius.circular(18),
        onTap: () {
          HapticFeedback.mediumImpact();
          MixpanelManager().bottomNavigationTabClicked(analyticsName);
          primaryFocus?.unfocus();
          onTabTap(index, selected);
        },
        child: AnimatedContainer(
          duration: const Duration(milliseconds: 180),
          curve: Curves.easeOut,
          padding: const EdgeInsets.only(top: 5, bottom: 3),
          child: Column(
            mainAxisSize: MainAxisSize.min,
            mainAxisAlignment: MainAxisAlignment.center,
            children: [
              Stack(
                clipBehavior: Clip.none,
                children: [
                  FaIcon(
                    icon,
                    size: 16,
                    color: selected ? MobileTokens.accent : MobileTokens.textSecondary,
                  ),
                  if (badgeCount > 0)
                    Positioned(
                      right: -10,
                      top: -8,
                      child: Container(
                        padding: const EdgeInsets.symmetric(horizontal: 5, vertical: 1),
                        decoration: BoxDecoration(
                          color: MobileTokens.danger,
                          borderRadius: BorderRadius.circular(999),
                        ),
                        child: Text(
                          badgeCount > 99 ? '99+' : '$badgeCount',
                          style: const TextStyle(
                            color: Colors.white,
                            fontSize: 9,
                            fontWeight: FontWeight.w700,
                          ),
                        ),
                      ),
                  ),
                ],
              ),
              const SizedBox(height: 5),
              Text(
                label,
                maxLines: 1,
                overflow: TextOverflow.fade,
                softWrap: false,
                style: TextStyle(
                  fontSize: 11.5,
                  fontWeight: selected ? FontWeight.w700 : FontWeight.w500,
                  color: selected ? MobileTokens.accent : MobileTokens.textSecondary,
                ),
              ),
              const SizedBox(height: 3),
              AnimatedContainer(
                duration: const Duration(milliseconds: 180),
                curve: Curves.easeOut,
                width: selected ? 18 : 0,
                height: 2,
                decoration: BoxDecoration(
                  color: MobileTokens.accent,
                  borderRadius: BorderRadius.circular(999),
                ),
              ),
            ],
          ),
        ),
      ),
    );
  }
}
