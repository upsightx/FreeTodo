import 'package:flutter/material.dart';

class MobileTokens {
  static const Color background = Color(0xFF090B13);
  static const Color surface = Color(0xFF121624);
  static const Color surfaceElevated = Color(0xFF1A2133);
  static const Color border = Color(0x332C3D5D);
  static const Color textPrimary = Colors.white;
  static const Color textSecondary = Color(0xFF9BA7C4);
  static const Color accent = Color(0xFF6FA9FF);
  static const Color accentSoft = Color(0x264E83D9);
  static const Color success = Color(0xFF76BFA0);
  static const Color warning = Color(0xFFC8A46A);
  static const Color danger = Color(0xFFB98383);

  static const LinearGradient appBackground = LinearGradient(
    begin: Alignment.topCenter,
    end: Alignment.bottomCenter,
    colors: [Color(0xFF0C1020), Color(0xFF090B13)],
  );

  static BoxDecoration cardDecoration({bool highlight = false}) {
    return BoxDecoration(
      color: highlight ? surfaceElevated : surface,
      borderRadius: BorderRadius.circular(18),
      border: Border.all(
        color: highlight ? accentSoft : border,
      ),
      boxShadow: const [
        BoxShadow(
          color: Color(0x26000000),
          blurRadius: 18,
          offset: Offset(0, 10),
        ),
      ],
    );
  }
}
