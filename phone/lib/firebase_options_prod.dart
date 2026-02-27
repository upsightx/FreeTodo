// STUB – LifeTrace mode skips Firebase initialization.
import 'package:firebase_core/firebase_core.dart' show FirebaseOptions;

class DefaultFirebaseOptions {
  static FirebaseOptions get currentPlatform => const FirebaseOptions(
        apiKey: 'stub',
        appId: 'stub',
        messagingSenderId: 'stub',
        projectId: 'stub',
      );
}
