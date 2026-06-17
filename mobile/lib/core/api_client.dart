import 'dart:convert';
import 'dart:typed_data';

import 'package:http/http.dart' as http;

const apiBaseUrl = String.fromEnvironment(
  'API_BASE_URL',
  defaultValue: 'http://10.0.2.2:8010',
);

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
    final response = await _client
        .get(Uri.parse('$apiBaseUrl$path'), headers: _headers(token))
        .timeout(const Duration(seconds: 20));
    if (response.statusCode < 200 || response.statusCode >= 300) {
      throw _exceptionFrom(response);
    }
    return response.bodyBytes;
  }

  Future<dynamic> _requestJson(
    String path, {
    String method = 'GET',
    String? token,
    Object? body,
  }) async {
    final uri = Uri.parse('$apiBaseUrl$path');
    final headers = _headers(token);
    late http.Response response;
    try {
      if (method == 'POST') {
        response = await _client
            .post(uri, headers: headers, body: jsonEncode(body))
            .timeout(const Duration(seconds: 15));
      } else if (method == 'PATCH') {
        response = await _client.patch(uri, headers: headers).timeout(
              const Duration(seconds: 15),
            );
      } else if (method == 'PUT') {
        response = await _client
            .put(uri, headers: headers, body: jsonEncode(body))
            .timeout(const Duration(seconds: 15));
      } else {
        response = await _client.get(uri, headers: headers).timeout(
              const Duration(seconds: 15),
            );
      }
    } on Exception {
      throw ApiException('No se pudo conectar con AgroEscudo API.', 0);
    }
    if (response.statusCode < 200 || response.statusCode >= 300) {
      throw _exceptionFrom(response);
    }
    return jsonDecode(utf8.decode(response.bodyBytes));
  }

  Map<String, String> _headers(String? token) => {
        'Content-Type': 'application/json',
        if (token != null) 'Authorization': 'Bearer $token',
      };

  ApiException _exceptionFrom(http.Response response) {
    var message = 'No se pudo completar la solicitud.';
    try {
      final payload = jsonDecode(utf8.decode(response.bodyBytes));
      message = payload['detail']?.toString() ?? message;
    } on Exception {
      if (response.reasonPhrase?.isNotEmpty ?? false) {
        message = response.reasonPhrase!;
      }
    }
    return ApiException(message, response.statusCode);
  }
}
