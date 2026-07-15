import 'dart:async';
import 'dart:convert';

import 'package:flutter/foundation.dart';
import 'package:http/http.dart' as http;

const _configuredApiBaseUrl = String.fromEnvironment('API_BASE_URL');
const _localFallbackApiBaseUrl = 'http://10.0.2.2:8010';
const _jsonTimeout = Duration(seconds: 30);
const _longJsonTimeout = Duration(seconds: 75);
const _fileTimeout = Duration(seconds: 120);
const _retryDelays = [
  Duration(seconds: 3),
  Duration(seconds: 6),
  Duration(seconds: 12),
];

String get apiBaseUrl => _resolveApiBaseUrl();

class ApiException implements Exception {
  ApiException(this.message, this.statusCode);

  final String message;
  final int statusCode;

  @override
  String toString() => message;
}

class ApiClient {
  ApiClient({http.Client? client}) : _client = client ?? http.Client();

  final http.Client _client;

  Future<dynamic> getJson(String path, {String? token}) {
    return _requestJson(path, token: token);
  }

  Future<dynamic> postJson(String path, Object body, {String? token}) {
    return _requestJson(path, method: 'POST', token: token, body: body);
  }

  Future<dynamic> patchJson(String path, {String? token}) {
    return _requestJson(path, method: 'PATCH', token: token);
  }

  Future<dynamic> putJson(String path, Object body, {String? token}) {
    return _requestJson(path, method: 'PUT', token: token, body: body);
  }

  Future<dynamic> deleteJson(String path, Object body, {String? token}) {
    return _requestJson(path, method: 'DELETE', token: token, body: body);
  }

  Future<Uint8List> getBytes(String path, {required String token}) async {
    final target = _targetUri(path);
    final response = await _requestWithRetry(
      path,
      target,
      () => _client.get(target, headers: _headers(token)).timeout(_fileTimeout),
    );
    if (response.statusCode < 200 || response.statusCode >= 300) {
      throw _exceptionFrom(response, path, target);
    }
    return response.bodyBytes;
  }

  Future<dynamic> _requestJson(
    String path, {
    String method = 'GET',
    String? token,
    Object? body,
  }) async {
    final uri = _targetUri(path);
    final headers = _headers(token);
    final timeout = _timeoutFor(path);
    final response = await _requestWithRetry(path, uri, () {
      if (method == 'POST') {
        return _client.post(uri, headers: headers, body: jsonEncode(body)).timeout(timeout);
      } else if (method == 'PATCH') {
        return _client.patch(uri, headers: headers).timeout(timeout);
      } else if (method == 'PUT') {
        return _client.put(uri, headers: headers, body: jsonEncode(body)).timeout(timeout);
      } else if (method == 'DELETE') {
        return _client.delete(uri, headers: headers, body: jsonEncode(body)).timeout(timeout);
      }
      return _client.get(uri, headers: headers).timeout(timeout);
    });
    if (response.statusCode < 200 || response.statusCode >= 300) {
      throw _exceptionFrom(response, path, uri);
    }
    return jsonDecode(utf8.decode(response.bodyBytes));
  }

  Map<String, String> _headers(String? token) => {
    'Content-Type': 'application/json',
    if (token != null) 'Authorization': 'Bearer $token',
  };

  Future<http.Response> _requestWithRetry(
    String path,
    Uri uri,
    Future<http.Response> Function() request,
  ) async {
    Object? lastError;
    for (var attempt = 0; attempt <= _retryDelays.length; attempt += 1) {
      try {
        return await request();
      } on ApiException {
        rethrow;
      } on TimeoutException catch (error) {
        lastError = error;
      } on Exception catch (error) {
        lastError = error;
      }
      if (attempt < _retryDelays.length) {
        await Future<void>.delayed(_retryDelays[attempt]);
      }
    }
    throw ApiException(_connectionMessage(path, uri, lastError ?? 'error de red'), 0);
  }

  ApiException _exceptionFrom(http.Response response, String path, Uri uri) {
    var message = 'No se pudo completar la solicitud.';
    try {
      final payload = jsonDecode(utf8.decode(response.bodyBytes));
      message = payload['detail']?.toString() ?? message;
    } on Exception {
      if (response.reasonPhrase?.isNotEmpty ?? false) {
        message = response.reasonPhrase!;
      }
    }
    return ApiException(
      _httpErrorMessage(path, uri, response.statusCode, message),
      response.statusCode,
    );
  }

  Uri _targetUri(String path) {
    final baseUrl = _resolveApiBaseUrl();
    return Uri.parse('$baseUrl$path');
  }
}

Duration _timeoutFor(String path) {
  if (path == '/health' || path == '/api/health/db' || path == '/api/auth/login' || path == '/api/me') {
    return _longJsonTimeout;
  }
  return _jsonTimeout;
}

String _resolveApiBaseUrl() {
  final configured = _configuredApiBaseUrl.trim();
  final selected = configured.isEmpty ? _localFallbackApiBaseUrl : configured;
  final normalized = selected.replaceAll(RegExp(r'/+$'), '');

  if (kReleaseMode) {
    if (configured.isEmpty) {
      throw ApiException(
        'API_BASE_URL no fue configurada para esta APK release.\n'
        'URL usada: no configurada\n'
        'Endpoint probado: no iniciado\n'
        'Codigo HTTP: no disponible\n'
        'Mensaje tecnico: compila con --dart-define=API_BASE_URL=https://agroescudo-api.onrender.com\n'
        'Posibles causas: build release sin API_BASE_URL, URL incorrecta o configuracion de entorno incompleta.',
        0,
      );
    }
    if (_isLocalOnlyUrl(normalized)) {
      throw ApiException(
        'La APK release no puede usar una API local.\n'
        'URL usada: $normalized\n'
        'Endpoint probado: no iniciado\n'
        'Codigo HTTP: no disponible\n'
        'Mensaje tecnico: usa la API publica de Render.\n'
        'Posibles causas: se compilo con localhost, 127.0.0.1, 10.0.2.2 o IP LAN 192.168.x.x.',
        0,
      );
    }
  }

  return normalized;
}

bool _isLocalOnlyUrl(String value) {
  final uri = Uri.tryParse(value);
  final host = uri?.host.toLowerCase() ?? value.toLowerCase();
  return host == 'localhost' ||
      host == '127.0.0.1' ||
      host == '10.0.2.2' ||
      host.startsWith('192.168.');
}

String _connectionMessage(String path, Uri uri, Object error) {
  return 'No se pudo conectar con AgroEscudo API.\n'
      'URL usada: ${uri.origin}\n'
      'Endpoint probado: $path\n'
      'Codigo HTTP: no disponible\n'
      'Mensaje tecnico: ${error.runtimeType}\n'
      'Posibles causas: backend dormido por Render Free, URL incorrecta, sin internet, API caida o endpoint no disponible.';
}

String _httpErrorMessage(String path, Uri uri, int code, String detail) {
  return 'No se pudo completar la solicitud a AgroEscudo API.\n'
      'URL usada: ${uri.origin}\n'
      'Endpoint probado: $path\n'
      'Codigo HTTP: $code\n'
      'Mensaje tecnico: $detail\n'
      'Posibles causas: backend dormido por Render Free, URL incorrecta, sin internet, API caida o endpoint no disponible.';
}
