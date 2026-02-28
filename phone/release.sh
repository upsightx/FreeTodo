#!/bin/bash
set -euo pipefail

echo "=== FreeTodo Release Build ==="

# 1. Clean & regenerate
flutter clean
flutter pub get
dart run build_runner build --delete-conflicting-outputs

# 2. Build release APK & AAB (prod flavor, entry = main.dart)
flutter build appbundle --release --flavor prod -t lib/main.dart
flutter build apk --release --flavor prod -t lib/main.dart

echo "=== Done ==="
echo "APK:  build/app/outputs/flutter-apk/app-prod-release.apk"
echo "AAB:  build/app/outputs/bundle/prodRelease/app-prod-release.aab"
