// STUB – LifeTrace mode skips Firebase initialization.
// Replace with real FlutterFire config if you need Firebase:
//   flutterfire configure --project=your-project
import 'package:firebase_core/firebase_core.dart' show FirebaseOptions;

class DefaultFirebaseOptions {
  static FirebaseOptions get currentPlatform => const FirebaseOptions(
        apiKey: 'stub',
        appId: 'stub',
        messagingSenderId: 'stub',
        projectId: 'stub',
      );
}
