import 'dart:async';

import 'package:firebase_core/firebase_core.dart';
import 'package:firebase_messaging/firebase_messaging.dart';
import 'package:flutter/foundation.dart';

import 'api_client.dart';

const _fcmEnabled = bool.fromEnvironment('ENABLE_FCM', defaultValue: false);

@pragma('vm:entry-point')
Future<void> _firebaseMessagingBackgroundHandler(RemoteMessage message) async {
  await Firebase.initializeApp();
}

class PushNotifications {
  PushNotifications._();

  static bool _ready = false;
  static StreamSubscription<String>? _tokenRefreshSubscription;

  static bool get enabled => _fcmEnabled;
  static bool get ready => _ready;

  static Future<void> initialize() async {
    if (!_fcmEnabled) return;
    try {
      await Firebase.initializeApp();
      FirebaseMessaging.onBackgroundMessage(_firebaseMessagingBackgroundHandler);
      await FirebaseMessaging.instance.setAutoInitEnabled(true);
      await FirebaseMessaging.instance.requestPermission(
        alert: true,
        badge: true,
        sound: true,
      );
      _ready = true;
    } on FirebaseException catch (error) {
      debugPrint('AgroEscudo FCM no disponible: ${error.code}.');
      _ready = false;
    }
  }

  static Future<void> registerForSession(ApiClient api, String authToken) async {
    if (!_ready) return;
    try {
      final registrationToken = await FirebaseMessaging.instance.getToken();
      if (registrationToken != null && registrationToken.isNotEmpty) {
        await _register(api, authToken, registrationToken);
      }

      await _tokenRefreshSubscription?.cancel();
      _tokenRefreshSubscription = FirebaseMessaging.instance.onTokenRefresh.listen(
        (token) => _register(api, authToken, token),
        onError: (Object error) => debugPrint('No se pudo renovar el token FCM: ${error.runtimeType}.'),
      );
    } on FirebaseException catch (error) {
      debugPrint('No se pudo obtener el token FCM: ${error.code}.');
    }
  }

  static Future<void> unregisterSession(ApiClient api, String authToken) async {
    if (!_ready) return;
    await _tokenRefreshSubscription?.cancel();
    _tokenRefreshSubscription = null;
    try {
      final registrationToken = await FirebaseMessaging.instance.getToken();
      if (registrationToken != null && registrationToken.isNotEmpty) {
        await api.deleteJson(
          '/api/notifications/push-tokens/current',
          {'token': registrationToken, 'platform': 'android'},
          token: authToken,
        );
      }
    } on FirebaseException {
      // Logout must still complete when Firebase is unavailable.
    } on ApiException {
      // Logout must still complete when Firebase or the backend is unavailable.
    }
  }

  static Future<void> _register(ApiClient api, String authToken, String registrationToken) async {
    try {
      await api.postJson(
        '/api/notifications/push-tokens',
        {'token': registrationToken, 'platform': 'android'},
        token: authToken,
      );
    } on ApiException catch (error) {
      debugPrint('No se pudo registrar FCM en AgroEscudo: HTTP ${error.statusCode}.');
    }
  }
}
