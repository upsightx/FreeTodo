import 'package:flutter/material.dart';
import 'package:flutter/services.dart';

import 'package:freeu/utils/logger.dart';

enum Environment {
  prod,
  dev;

  static Environment fromFlavor() {
    return Environment.values.firstWhere(
      (e) => e.name == appFlavor?.toLowerCase(),
      orElse: () {
        Logger.debug('Warning: Unknown flavor "$appFlavor", defaulting to dev');
        return Environment.dev;
      },
    );
  }
}

class F {
  static Environment env = Environment.fromFlavor();

  static String get title {
    switch (env) {
      case Environment.prod:
        return 'freeu';
      case Environment.dev:
        return 'FreeU Dev';
      default:
        return 'FreeU Dev';
    }
  }
}
