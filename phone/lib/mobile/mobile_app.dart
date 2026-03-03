import 'package:flutter/material.dart';

import 'package:provider/provider.dart';

import 'package:freeu/backend/preferences.dart';
import 'package:freeu/pages/home/page.dart';
import 'package:freeu/pages/onboarding/device_selection.dart';
import 'package:freeu/pages/onboarding/wrapper.dart';
import 'package:freeu/pages/persona/persona_profile.dart';
import 'package:freeu/providers/auth_provider.dart';

class MobileApp extends StatelessWidget {
  const MobileApp({super.key});

  @override
  Widget build(BuildContext context) {
    return Consumer<AuthenticationProvider>(
      builder: (context, authProvider, child) {
        if (authProvider.isSignedIn()) {
          if (SharedPreferencesUtil().onboardingCompleted) {
            return const HomePageWrapper();
          } else {
            return const OnboardingWrapper();
          }
        } else if (SharedPreferencesUtil().hasOmiDevice == false &&
            SharedPreferencesUtil().hasPersonaCreated &&
            SharedPreferencesUtil().verifiedPersonaId != null) {
          return const PersonaProfilePage();
        } else {
          return const DeviceSelectionPage();
        }
      },
    );
  }
}
