import 'package:flutter_test/flutter_test.dart';
import 'package:mobile/core/app_store.dart';

void main() {
  group('device QR token', () {
    test('extracts the random token from the full API URL', () {
      expect(
        extractDeviceQrToken(
          'https://api.agroescudo.com/api/devices/scan/random-token-1234567890',
        ),
        'random-token-1234567890',
      );
    });

    test('accepts a raw public token', () {
      expect(
        extractDeviceQrToken('  random-token-1234567890  '),
        'random-token-1234567890',
      );
    });
  });
}
