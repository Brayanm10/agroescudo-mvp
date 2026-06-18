import 'dart:async';
import 'dart:convert';

import 'package:flutter/foundation.dart';
import 'package:http/http.dart' as http;

const _configuredApiBaseUrl = String.fromEnvironment('API_BASE_URL');
const _localFallbackApiBaseUrl = 'http://10.0.2.2:8010';

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

  Future<Uint8List> getBytes(String path, {required String token}) async {
    final target = _targetUri(path);
    late http.Response response;
    try {
      response = await _client
          .get(target, headers: _headers(token))
          .timeout(const Duration(seconds: 20));
    } on ApiException {
      rethrow;
    } on TimeoutException catch (error) {
      throw ApiException(_connectionMessage(path, target, error), 0);
    } on Exception catch (error) {
      throw ApiException(_connectionMessage(path, target, error), 0);
    }
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
    late http.Response response;
    try {
      if (method == 'POST') {
        response = await _client
            .post(uri, headers: headers, body: jsonEncode(body))
            .timeout(const Duration(seconds: 15));
      } else if (method == 'PATCH') {
        response = await _client
            .patch(uri, headers: headers)
            .timeout(const Duration(seconds: 15));
      } else if (method == 'PUT') {
        response = await _client
            .put(uri, headers: headers, body: jsonEncode(body))
            .timeout(const Duration(seconds: 15));
      } else {
        response = await _client
            .get(uri, headers: headers)
            .timeout(const Duration(seconds: 15));
      }
    } on ApiException {
      rethrow;
    } on TimeoutException catch (error) {
      throw ApiException(_connectionMessage(path, uri, error), 0);
    } on Exception catch (error) {
      throw ApiException(_connectionMessage(path, uri, error), 0);
    }
    if (response.statusCode < 200 || response.statusCode >= 300) {
      throw _exceptionFrom(response, path, uri);
    }
    return jsonDecode(utf8.decode(response.bodyBytes));
  }

  Map<String, String> _headers(String? token) => {
    'Content-Type': 'application/json',
    if (token != null) 'Authorization': 'Bearer $token',
  };

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
