import 'dart:convert';
import 'dart:io';

import 'package:connectivity_plus/connectivity_plus.dart';
import 'package:flutter/foundation.dart';
import 'package:flutter_secure_storage/flutter_secure_storage.dart';
import 'package:open_filex/open_filex.dart';
import 'package:path_provider/path_provider.dart';
import 'package:shared_preferences/shared_preferences.dart';

import 'api_client.dart';

class AppStore extends ChangeNotifier {
  AppStore({
    ApiClient? api,
    FlutterSecureStorage? secureStorage,
  })  : _api = api ?? ApiClient(),
        _secureStorage = secureStorage ?? const FlutterSecureStorage();

  static const _tokenKey = 'agroescudo.jwt';
  static const _cacheKey = 'agroescudo.mobile.cache';

  final ApiClient _api;
  final FlutterSecureStorage _secureStorage;

  String? token;
  Map<String, dynamic>? me;
  Map<String, dynamic> data = {};
  bool initializing = true;
  bool loading = false;
  bool cached = false;
  String? error;

  bool get authenticated => token != null && me != null;
  String get role => me?['role']?.toString() ?? '';
  bool get canOperate => role == 'admin' || role == 'technician';
  bool get canResolve => role == 'admin';

  List<Map<String, dynamic>> get companies => _list('companies');
  List<Map<String, dynamic>> get sites => _list('sites');
  List<Map<String, dynamic>> get units => _list('storage_units');
  List<Map<String, dynamic>> get devices => _list('devices');
  List<Map<String, dynamic>> get readings => _list('readings');
  List<Map<String, dynamic>> get alerts => _list('alerts');
  List<Map<String, dynamic>> get activeAlerts => _list('active_alerts');
  List<Map<String, dynamic>> get logs => _list('logs');
  List<Map<String, dynamic>> get pilots => _list('pilots');

  Future<void> restore() async {
    token = await _secureStorage.read(key: _tokenKey);
    if (token != null) {
      try {
        await refresh();
      } on ApiException catch (exception) {
        if (exception.statusCode == 401) {
          await logout();
        } else {
          await _loadCache();
        }
      }
    }
    initializing = false;
    notifyListeners();
  }

  Future<void> login(String email, String password) async {
    loading = true;
    error = null;
    notifyListeners();
    try {
      final payload = await _api.postJson('/api/auth/login', {
        'email': email,
        'password': password,
      }) as Map<String, dynamic>;
      token = payload['access_token']?.toString();
      if (token == null) throw ApiException('Token no recibido.', 500);
      await _secureStorage.write(key: _tokenKey, value: token);
      await refresh();
    } on ApiException catch (exception) {
      error = exception.statusCode == 401
          ? 'Credenciales incorrectas. Verifica correo y contrasena.'
          : exception.message;
      rethrow;
    } finally {
      loading = false;
      notifyListeners();
    }
  }

  Future<void> refresh() async {
    final authToken = token;
    if (authToken == null) return;
    loading = true;
    error = null;
    notifyListeners();
    try {
      final results = await Future.wait([
        _api.getJson('/api/me', token: authToken),
        _api.getJson('/api/companies', token: authToken),
        _api.getJson('/api/sites', token: authToken),
        _api.getJson('/api/storage-units', token: authToken),
        _api.getJson('/api/devices', token: authToken),
        _api.getJson('/api/readings?limit=300', token: authToken),
        _api.getJson('/api/alerts', token: authToken),
        _api.getJson('/api/alerts/active', token: authToken),
        _api.getJson('/api/operational-logs', token: authToken),
        _api.getJson('/api/pilots', token: authToken),
      ]);
      me = _map(results[0]);
      data = {
        'companies': results[1],
        'sites': results[2],
        'storage_units': results[3],
        'devices': results[4],
        'readings': results[5],
        'alerts': results[6],
        'active_alerts': results[7],
        'logs': results[8],
        'pilots': results[9],
      };
      cached = false;
      await _saveCache();
    } on ApiException catch (exception) {
      if (exception.statusCode == 401) {
        await logout();
      } else if (!await _loadCache()) {
        error = exception.message;
      }
      rethrow;
    } finally {
      loading = false;
      notifyListeners();
    }
  }

  Future<void> logout() async {
    token = null;
    me = null;
    data = {};
    cached = false;
    error = null;
    await _secureStorage.delete(key: _tokenKey);
    final prefs = await SharedPreferences.getInstance();
    await prefs.remove(_cacheKey);
    notifyListeners();
  }

  Future<void> acknowledge(int alertId) async {
    await _mutate('/api/alerts/$alertId/acknowledge', method: 'PATCH');
  }

  Future<void> resolve(int alertId) async {
    await _mutate('/api/alerts/$alertId/resolve', method: 'PATCH');
  }

  Future<void> createLog({
    required int storageUnitId,
    required String category,
    required String action,
    required String operatorName,
    required String notes,
    int? deviceId,
    int? alertId,
  }) async {
    await _ensureOnline();
    await _api.postJson(
      '/api/operational-logs',
      {
        'storage_unit_id': storageUnitId,
        'device_id': deviceId,
        'alert_id': alertId,
        'category': category,
        'action_taken': action,
        'operator_name': operatorName,
        'notes': notes,
        'timestamp': DateTime.now().toUtc().toIso8601String(),
      },
      token: token,
    );
    await refresh();
  }

  Future<void> createInstallation({
    required int storageUnitId,
    required int deviceId,
    required String location,
    required String technicianName,
    required String notes,
    required bool sensorOk,
    required bool connectivityOk,
    required bool readingOk,
    required bool batteryOk,
  }) async {
    await _ensureOnline();
    await _api.postJson(
      '/api/operational-logs/installations',
      {
        'storage_unit_id': storageUnitId,
        'device_id': deviceId,
        'physical_location': location,
        'sensor_installed_correctly': sensorOk,
        'connectivity_verified': connectivityOk,
        'initial_reading_registered': readingOk,
        'battery_verified': batteryOk,
        'observations': notes,
        'technician_name': technicianName,
        'timestamp': DateTime.now().toUtc().toIso8601String(),
      },
      token: token,
    );
    await refresh();
  }

  Future<String> downloadWeeklyPdf(Map<String, dynamic> unit) async {
    await _ensureOnline();
    final bytes = await _api.getBytes(
      '/api/reports/weekly/pdf?storage_unit_id=${unit['id']}',
      token: token!,
    );
    final directory = await getApplicationDocumentsDirectory();
    final slug = _slug(unit['name']?.toString() ?? 'unidad');
    final day = DateTime.now().toIso8601String().substring(0, 10);
    final file = File('${directory.path}/agroescudo-reporte-$slug-$day.pdf');
    await file.writeAsBytes(bytes, flush: true);
    await OpenFilex.open(file.path);
    return file.path;
  }

  Future<List<Map<String, dynamic>>> notificationPreferences() async {
    final payload = await _api.getJson('/api/notifications/preferences', token: token);
    return (payload as List).map((item) => Map<String, dynamic>.from(item as Map)).toList();
  }

  Future<void> updateNotificationPreference({
    required String channel,
    required bool enabled,
    String? destination,
    String minimumSeverity = 'critical',
  }) async {
    await _api.putJson(
      '/api/notifications/preferences/$channel',
      {
        'enabled': enabled,
        'destination': destination,
        'minimum_severity': minimumSeverity,
      },
      token: token,
    );
  }

  Future<Map<String, dynamic>> aiRecommendationForAlert(int alertId) async {
    final payload = await _api.getJson('/api/ai/alerts/$alertId/recommendation', token: token);
    return Map<String, dynamic>.from(payload as Map);
  }

  Map<String, dynamic>? latestReadingFor(int storageUnitId) {
    final values = readings
        .where((reading) => reading['storage_unit_id'] == storageUnitId)
        .toList()
      ..sort((a, b) => _date(b['timestamp']).compareTo(_date(a['timestamp'])));
    return values.isEmpty ? null : values.first;
  }

  List<Map<String, dynamic>> readingsFor(int storageUnitId) => readings
      .where((reading) => reading['storage_unit_id'] == storageUnitId)
      .toList()
    ..sort((a, b) => _date(a['timestamp']).compareTo(_date(b['timestamp'])));

  Map<String, dynamic>? deviceFor(int storageUnitId) {
    return devices.cast<Map<String, dynamic>?>().firstWhere(
          (device) => device?['storage_unit_id'] == storageUnitId,
          orElse: () => null,
        );
  }

  Future<void> _mutate(String path, {required String method}) async {
    await _ensureOnline();
    if (method == 'PATCH') await _api.patchJson(path, token: token);
    await refresh();
  }

  Future<void> _ensureOnline() async {
    final status = await Connectivity().checkConnectivity();
    if (status.contains(ConnectivityResult.none)) {
      throw ApiException('Esta accion requiere conexion a internet.', 0);
    }
  }

  Future<void> _saveCache() async {
    final prefs = await SharedPreferences.getInstance();
    await prefs.setString(_cacheKey, jsonEncode({'me': me, 'data': data}));
  }

  Future<bool> _loadCache() async {
    final prefs = await SharedPreferences.getInstance();
    final content = prefs.getString(_cacheKey);
    if (content == null) return false;
    final payload = jsonDecode(content) as Map<String, dynamic>;
    me = _map(payload['me']);
    data = _map(payload['data']);
    cached = true;
    return true;
  }

  List<Map<String, dynamic>> _list(String key) {
    return ((data[key] as List?) ?? []).map(_map).toList();
  }

  Map<String, dynamic> _map(dynamic value) {
    return Map<String, dynamic>.from(value as Map);
  }

  DateTime _date(dynamic value) {
    return DateTime.tryParse(value?.toString() ?? '') ??
        DateTime.fromMillisecondsSinceEpoch(0);
  }

  String _slug(String value) {
    return value
        .toLowerCase()
        .replaceAll(RegExp(r'[^a-z0-9]+'), '-')
        .replaceAll(RegExp(r'^-|-$'), '');
  }
}
