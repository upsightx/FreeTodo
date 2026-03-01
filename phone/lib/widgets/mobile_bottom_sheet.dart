import 'package:flutter/material.dart';

import 'package:omi/ui/mobile/mobile_tokens.dart';

Future<T?> showMobileBottomSheet<T>({
  required BuildContext context,
  required WidgetBuilder builder,
  bool isScrollControlled = false,
}) {
  return showModalBottomSheet<T>(
    context: context,
    backgroundColor: Colors.transparent,
    isScrollControlled: isScrollControlled,
    builder: builder,
  );
}

class MobileBottomSheet extends StatelessWidget {
  const MobileBottomSheet({
    super.key,
    required this.child,
    this.margin = const EdgeInsets.fromLTRB(12, 0, 12, 12),
    this.padding = const EdgeInsets.all(12),
    this.radius = 16,
    this.showHandle = true,
    this.backgroundColor,
  });

  final Widget child;
  final EdgeInsets margin;
  final EdgeInsets padding;
  final double radius;
  final bool showHandle;
  final Color? backgroundColor;

  @override
  Widget build(BuildContext context) {
    return Container(
      margin: margin,
      padding: padding,
      decoration: BoxDecoration(
        color: backgroundColor ?? MobileTokens.surface,
        borderRadius: BorderRadius.circular(radius),
        border: Border.all(color: MobileTokens.border),
      ),
      child: SafeArea(
        top: false,
        child: Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            if (showHandle)
              Container(
                width: 36,
                height: 4,
                margin: const EdgeInsets.only(bottom: 12),
                decoration: BoxDecoration(
                  color: MobileTokens.textSecondary.withOpacity(0.45),
                  borderRadius: BorderRadius.circular(999),
                ),
              ),
            child,
          ],
        ),
      ),
    );
  }
}
