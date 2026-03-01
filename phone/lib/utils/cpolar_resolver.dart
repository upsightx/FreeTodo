import 'dart:async';
import 'dart:io';

import 'package:omi/env/env.dart';

/// Probes multiple cpolar domain suffixes to find a reachable backend.
///
/// cpolar may assign `.cpolar.cn`, `.cpolar.top`, or other suffixes that
/// change between tunnel restarts.  This resolver tries each candidate
/// and returns the first URL that responds to a health-check.
class CpolarResolver {
  CpolarResolver._();
  static final CpolarResolver instance = CpolarResolver._();

  static const List<String> _suffixes = [
    'cpolar.cn',
    'cpolar.top',
  ];

  static const String _subdomain = 'tybbackend';
  static const Duration _probeTimeout = Duration(seconds: 5);

  String? _resolvedUrl;

  String? get resolvedUrl => _resolvedUrl;

  /// Probe all candidate URLs and return the first healthy one.
  ///
  /// Tries all suffixes in parallel; returns the fastest responder.
  /// Falls back to the default from [Env.apiBaseUrl] if none respond.
  Future<String> resolve() async {
    final candidates = _suffixes
        .map((s) => 'https://$_subdomain.$s')
        .toList();

    final completer = Completer<String>();
    int failures = 0;

    for (final base in candidates) {
      _probe(base).then((ok) {
        if (ok && !completer.isCompleted) {
          completer.complete(base);
        } else if (!ok) {
          failures++;
          if (failures == candidates.length && !completer.isCompleted) {
            completer.complete(Env.apiBaseUrl ?? candidates.first);
          }
        }
      });
    }

    final winner = await completer.future;
    final normalized = winner.endsWith('/') ? winner : '$winner/';
    _resolvedUrl = normalized;
    return normalized;
  }

  Future<bool> _probe(String baseUrl) async {
    final uri = Uri.parse('$baseUrl/api/health');
    try {
      final client = HttpClient()
        ..connectionTimeout = _probeTimeout
        ..badCertificateCallback = (_, __, ___) => true;
      final request = await client.getUrl(uri).timeout(_probeTimeout);
      final response = await request.close().timeout(_probeTimeout);
      await response.drain<void>();
      client.close(force: true);
      return response.statusCode >= 200 && response.statusCode < 500;
    } on TimeoutException {
      return false;
    } on SocketException {
      return false;
    } on HandshakeException {
      return false;
    } catch (_) {
      return false;
    }
  }
}
