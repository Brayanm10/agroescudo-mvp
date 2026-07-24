import 'package:flutter/material.dart';
import 'package:image_picker/image_picker.dart';
import 'package:mobile_scanner/mobile_scanner.dart';
import 'package:provider/provider.dart';

import '../core/api_client.dart';
import '../core/app_store.dart';

const _emerald = Color(0xff075b44);
const _ink = Color(0xff16352d);
const _muted = Color(0xff62756f);

class PilotOperationsScreen extends StatefulWidget {
  const PilotOperationsScreen({super.key, this.initialTab = 0});

  final int initialTab;

  @override
  State<PilotOperationsScreen> createState() => _PilotOperationsScreenState();
}

class _PilotOperationsScreenState extends State<PilotOperationsScreen> {
  Future<void>? _loading;

  @override
  void didChangeDependencies() {
    super.didChangeDependencies();
    _loading ??= context.read<AppStore>().loadPilotOperations();
  }

  Future<void> _reload() async {
    final future = context.read<AppStore>().loadPilotOperations();
    setState(() => _loading = future);
    await future;
  }

  @override
  Widget build(BuildContext context) {
    final store = context.watch<AppStore>();
    return DefaultTabController(
      initialIndex: widget.initialTab,
      length: 3,
      child: Scaffold(
        appBar: AppBar(
          title: const Text('Operacion del piloto'),
          actions: [
            IconButton(
              tooltip: 'Escanear QR',
              onPressed: () => _scanQr(context),
              icon: const Icon(Icons.qr_code_scanner),
            ),
            IconButton(
              tooltip: 'Actualizar',
              onPressed: _reload,
              icon: const Icon(Icons.refresh),
            ),
          ],
          bottom: const TabBar(
            tabs: [
              Tab(icon: Icon(Icons.build_outlined), text: 'Mantenimiento'),
              Tab(icon: Icon(Icons.fact_check_outlined), text: 'Instalacion'),
              Tab(icon: Icon(Icons.photo_library_outlined), text: 'Evidencia'),
            ],
          ),
        ),
        body: FutureBuilder<void>(
          future: _loading,
          builder: (context, snapshot) {
            if (snapshot.connectionState == ConnectionState.waiting &&
                store.maintenanceRecords.isEmpty &&
                store.installationChecklists.isEmpty) {
              return const Center(child: CircularProgressIndicator());
            }
            if (snapshot.hasError &&
                store.maintenanceRecords.isEmpty &&
                store.installationChecklists.isEmpty) {
              return _LoadError(error: snapshot.error, onRetry: _reload);
            }
            return TabBarView(
              children: [
                _MaintenanceTab(store: store, onChanged: _reload),
                _InstallationTab(store: store, onChanged: _reload),
                _EvidenceTab(store: store, onChanged: _reload),
              ],
            );
          },
        ),
      ),
    );
  }

  Future<void> _scanQr(BuildContext context) async {
    final result = await Navigator.of(context).push<Map<String, dynamic>>(
      MaterialPageRoute(builder: (_) => const DeviceQrScannerScreen()),
    );
    if (!context.mounted || result == null) return;
    final deviceId = result['device_id'];
    final product = result['product_name'] ?? 'Dispositivo AgroEscudo';
    showDialog<void>(
      context: context,
      builder: (dialogContext) => AlertDialog(
        title: const Text('Nodo identificado'),
        content: Text(
          '$product\nDispositivo: ${deviceId ?? "Acceso restringido"}\n'
          'Acciones autorizadas: ${(result['allowed_actions'] as List?)?.join(", ") ?? "ninguna"}',
        ),
        actions: [
          TextButton(
            onPressed: () => Navigator.pop(dialogContext),
            child: const Text('Cerrar'),
          ),
        ],
      ),
    );
  }
}

class _MaintenanceTab extends StatelessWidget {
  const _MaintenanceTab({required this.store, required this.onChanged});

  final AppStore store;
  final Future<void> Function() onChanged;

  @override
  Widget build(BuildContext context) {
    final rows = store.maintenanceRecords;
    return RefreshIndicator(
      onRefresh: onChanged,
      child: ListView(
        padding: const EdgeInsets.all(16),
        children: [
          const _Intro(
            title: 'Intervenciones asignadas',
            copy:
                'Inicia el trabajo, registra diagnostico y cierra con una accion verificable.',
          ),
          if (rows.isEmpty)
            const _Empty('No hay mantenimientos asignados.')
          else
            ...rows.map(
              (item) => Card(
                margin: const EdgeInsets.only(bottom: 10),
                child: Padding(
                  padding: const EdgeInsets.all(15),
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Row(
                        children: [
                          Expanded(
                            child: Text(
                              _deviceLabel(store, item['device_id']),
                              style: const TextStyle(
                                color: _ink,
                                fontWeight: FontWeight.w800,
                              ),
                            ),
                          ),
                          _Status(value: item['effective_status']?.toString()),
                        ],
                      ),
                      const SizedBox(height: 7),
                      Text(
                        '${_human(item['maintenance_type'])}  |  ${item['priority'] ?? "MEDIUM"}',
                        style: const TextStyle(color: _muted),
                      ),
                      if (item['observations'] != null) ...[
                        const SizedBox(height: 7),
                        Text(
                          item['observations'].toString(),
                          style: const TextStyle(height: 1.35),
                        ),
                      ],
                      const SizedBox(height: 12),
                      Wrap(
                        spacing: 8,
                        children: [
                          if (store.canOperate &&
                              const {
                                'ASSIGNED',
                                'SCHEDULED',
                                'OVERDUE',
                              }.contains(item['effective_status']))
                            OutlinedButton.icon(
                              onPressed: () => _run(
                                context,
                                () => store.startMaintenance(item['id'] as int),
                                'Mantenimiento iniciado.',
                              ),
                              icon: const Icon(Icons.play_arrow),
                              label: const Text('Iniciar'),
                            ),
                          if (store.canOperate &&
                              item['effective_status'] == 'IN_PROGRESS')
                            ElevatedButton.icon(
                              onPressed: () =>
                                  _completeMaintenance(context, store, item),
                              icon: const Icon(Icons.check_circle_outline),
                              label: const Text('Completar'),
                            ),
                        ],
                      ),
                    ],
                  ),
                ),
              ),
            ),
        ],
      ),
    );
  }
}

class _InstallationTab extends StatelessWidget {
  const _InstallationTab({required this.store, required this.onChanged});

  final AppStore store;
  final Future<void> Function() onChanged;

  @override
  Widget build(BuildContext context) {
    final rows = store.installationChecklists;
    return RefreshIndicator(
      onRefresh: onChanged,
      child: ListView(
        padding: const EdgeInsets.all(16),
        children: [
          const _Intro(
            title: 'Checklist digital',
            copy:
                'La aprobacion requiere primera lectura, alerta de prueba y controles tecnicos completos.',
          ),
          if (rows.isEmpty)
            const _Empty(
              'No hay checklists asignados. El administrador debe crear y asignar la instalacion desde la web.',
            )
          else
            ...rows.map(
              (item) => Card(
                margin: const EdgeInsets.only(bottom: 10),
                child: ListTile(
                  contentPadding: const EdgeInsets.all(15),
                  leading: const CircleAvatar(
                    backgroundColor: Color(0xffe8f7f0),
                    foregroundColor: _emerald,
                    child: Icon(Icons.install_mobile_outlined),
                  ),
                  title: Text(
                    _deviceLabel(store, item['device_id']),
                    style: const TextStyle(fontWeight: FontWeight.w800),
                  ),
                  subtitle: Padding(
                    padding: const EdgeInsets.only(top: 7),
                    child: Text(
                      'Version ${item['checklist_version']}  |  ${_human(item['status'])}',
                    ),
                  ),
                  trailing:
                      store.canOperate &&
                          !const {
                            'PASSED',
                            'PASSED_WITH_OBSERVATIONS',
                            'FAILED',
                          }.contains(item['status'])
                      ? IconButton(
                          tooltip: 'Completar checklist',
                          onPressed: () =>
                              _editInstallation(context, store, item),
                          icon: const Icon(Icons.edit_note, color: _emerald),
                        )
                      : _Status(value: item['status']?.toString()),
                ),
              ),
            ),
        ],
      ),
    );
  }
}

class _EvidenceTab extends StatelessWidget {
  const _EvidenceTab({required this.store, required this.onChanged});

  final AppStore store;
  final Future<void> Function() onChanged;

  @override
  Widget build(BuildContext context) {
    final files = store.evidenceFiles;
    return RefreshIndicator(
      onRefresh: onChanged,
      child: ListView(
        padding: const EdgeInsets.all(16),
        children: [
          const _Intro(
            title: 'Evidencia del piloto',
            copy:
                'Fotografias protegidas y vinculadas a una intervencion dentro de tu alcance.',
          ),
          if (store.canOperate && store.maintenanceRecords.isNotEmpty)
            Card(
              margin: const EdgeInsets.only(bottom: 14),
              child: Padding(
                padding: const EdgeInsets.all(15),
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    const Text(
                      'Adjuntar a mantenimiento',
                      style: TextStyle(fontWeight: FontWeight.w800),
                    ),
                    const SizedBox(height: 10),
                    Row(
                      children: [
                        Expanded(
                          child: ElevatedButton.icon(
                            onPressed: () => _captureEvidence(
                              context,
                              store,
                              ImageSource.camera,
                            ),
                            icon: const Icon(Icons.photo_camera_outlined),
                            label: const Text('Tomar foto'),
                          ),
                        ),
                        const SizedBox(width: 8),
                        Expanded(
                          child: OutlinedButton.icon(
                            onPressed: () => _captureEvidence(
                              context,
                              store,
                              ImageSource.gallery,
                            ),
                            icon: const Icon(Icons.photo_library_outlined),
                            label: const Text('Galeria'),
                          ),
                        ),
                      ],
                    ),
                  ],
                ),
              ),
            ),
          if (files.isEmpty)
            const _Empty('Todavia no hay evidencia disponible.')
          else
            ...files.map(
              (item) => Card(
                margin: const EdgeInsets.only(bottom: 8),
                child: ListTile(
                  leading: const Icon(Icons.verified_outlined, color: _emerald),
                  title: Text(
                    item['original_filename']?.toString() ?? 'Evidencia',
                    maxLines: 1,
                    overflow: TextOverflow.ellipsis,
                  ),
                  subtitle: Text(
                    '${_human(item['entity_type'])} #${item['entity_id']}  |  ${_size(item['size_bytes'])}',
                  ),
                ),
              ),
            ),
        ],
      ),
    );
  }
}

class DeviceQrScannerScreen extends StatefulWidget {
  const DeviceQrScannerScreen({super.key});

  @override
  State<DeviceQrScannerScreen> createState() => _DeviceQrScannerScreenState();
}

class _DeviceQrScannerScreenState extends State<DeviceQrScannerScreen> {
  var processing = false;
  String? error;

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(title: const Text('Escanear nodo AgroEscudo')),
      body: Stack(
        fit: StackFit.expand,
        children: [
          MobileScanner(
            onDetect: (capture) async {
              if (processing || capture.barcodes.isEmpty) return;
              final value = capture.barcodes.first.rawValue;
              if (value == null || value.isEmpty) return;
              setState(() {
                processing = true;
                error = null;
              });
              try {
                final result = await context.read<AppStore>().scanDeviceQr(
                  value,
                );
                if (context.mounted) Navigator.pop(context, result);
              } on ApiException catch (exception) {
                if (!mounted) return;
                setState(() {
                  processing = false;
                  error = exception.message;
                });
              }
            },
          ),
          Center(
            child: Container(
              width: 245,
              height: 245,
              decoration: BoxDecoration(
                border: Border.all(color: Colors.white, width: 3),
                borderRadius: BorderRadius.circular(18),
              ),
            ),
          ),
          Positioned(
            left: 20,
            right: 20,
            bottom: 28,
            child: Card(
              color: Colors.white.withValues(alpha: .94),
              child: Padding(
                padding: const EdgeInsets.all(14),
                child: Text(
                  error ??
                      (processing
                          ? 'Validando acceso al dispositivo...'
                          : 'Alinea el QR seguro del nodo dentro del recuadro.'),
                  textAlign: TextAlign.center,
                  style: TextStyle(
                    color: error == null ? _ink : Colors.red.shade800,
                    fontWeight: FontWeight.w700,
                  ),
                ),
              ),
            ),
          ),
        ],
      ),
    );
  }
}

Future<void> _completeMaintenance(
  BuildContext context,
  AppStore store,
  Map<String, dynamic> item,
) async {
  final diagnosis = TextEditingController();
  final action = TextEditingController();
  final observations = TextEditingController();
  var deviceStatus = 'operational';
  await showModalBottomSheet<void>(
    context: context,
    isScrollControlled: true,
    builder: (sheetContext) => StatefulBuilder(
      builder: (context, setSheetState) => Padding(
        padding: EdgeInsets.only(
          left: 18,
          right: 18,
          top: 18,
          bottom: MediaQuery.of(context).viewInsets.bottom + 18,
        ),
        child: ListView(
          shrinkWrap: true,
          children: [
            const Text(
              'Cerrar mantenimiento',
              style: TextStyle(fontSize: 21, fontWeight: FontWeight.w800),
            ),
            const SizedBox(height: 14),
            TextField(
              controller: diagnosis,
              decoration: const InputDecoration(labelText: 'Diagnostico *'),
              maxLines: 2,
            ),
            const SizedBox(height: 10),
            TextField(
              controller: action,
              decoration: const InputDecoration(
                labelText: 'Accion realizada *',
              ),
              maxLines: 2,
            ),
            const SizedBox(height: 10),
            TextField(
              controller: observations,
              decoration: const InputDecoration(labelText: 'Observaciones *'),
              maxLines: 2,
            ),
            const SizedBox(height: 10),
            DropdownButtonFormField<String>(
              initialValue: deviceStatus,
              decoration: const InputDecoration(
                labelText: 'Estado final del nodo',
              ),
              items: const [
                DropdownMenuItem(
                  value: 'operational',
                  child: Text('Operativo'),
                ),
                DropdownMenuItem(value: 'degraded', child: Text('Degradado')),
                DropdownMenuItem(
                  value: 'calibration_pending',
                  child: Text('Calibracion pendiente'),
                ),
                DropdownMenuItem(
                  value: 'offline',
                  child: Text('Fuera de linea'),
                ),
              ],
              onChanged: (value) =>
                  setSheetState(() => deviceStatus = value ?? deviceStatus),
            ),
            const SizedBox(height: 15),
            ElevatedButton(
              onPressed: () async {
                if (diagnosis.text.trim().length < 3 ||
                    action.text.trim().length < 5 ||
                    observations.text.trim().length < 5) {
                  _toast(
                    context,
                    'Completa diagnostico, accion y observaciones.',
                  );
                  return;
                }
                Navigator.pop(sheetContext);
                await _run(
                  context,
                  () => store.completeMaintenance(
                    maintenanceId: item['id'] as int,
                    diagnosis: diagnosis.text.trim(),
                    actionTaken: action.text.trim(),
                    observations: observations.text.trim(),
                    deviceStatusAfter: deviceStatus,
                  ),
                  'Mantenimiento completado y auditado.',
                );
              },
              child: const Text('Completar intervencion'),
            ),
          ],
        ),
      ),
    ),
  );
  diagnosis.dispose();
  action.dispose();
  observations.dispose();
}

Future<void> _editInstallation(
  BuildContext context,
  AppStore store,
  Map<String, dynamic> item,
) async {
  final answers = <String, bool>{
    for (final entry in _checklistItems) entry.$1: _responseAt(item, entry.$1),
  };
  final readings =
      store.readings
          .where((reading) => reading['device_id'] == item['device_id'])
          .toList()
        ..sort(
          (a, b) => _date(b['timestamp']).compareTo(_date(a['timestamp'])),
        );
  final alerts = store.alerts
      .where((alert) => alert['device_id'] == item['device_id'])
      .toList();
  var finalStatus = 'PASSED';
  final notes = TextEditingController(
    text: item['notes']?.toString() ?? 'Instalacion verificada en campo.',
  );
  await showModalBottomSheet<void>(
    context: context,
    isScrollControlled: true,
    builder: (sheetContext) => StatefulBuilder(
      builder: (context, setSheetState) => DraggableScrollableSheet(
        expand: false,
        initialChildSize: .88,
        maxChildSize: .96,
        builder: (context, controller) => ListView(
          controller: controller,
          padding: const EdgeInsets.all(18),
          children: [
            const Text(
              'Validacion de instalacion',
              style: TextStyle(fontSize: 21, fontWeight: FontWeight.w800),
            ),
            const SizedBox(height: 6),
            const Text(
              'Cada punto debe corresponder a una comprobacion realizada en sitio.',
              style: TextStyle(color: _muted),
            ),
            const SizedBox(height: 12),
            ..._checklistItems.map(
              (entry) => CheckboxListTile(
                dense: true,
                contentPadding: EdgeInsets.zero,
                value: answers[entry.$1] ?? false,
                onChanged: (value) =>
                    setSheetState(() => answers[entry.$1] = value ?? false),
                title: Text(entry.$2),
              ),
            ),
            const SizedBox(height: 8),
            TextField(
              controller: notes,
              decoration: const InputDecoration(labelText: 'Observaciones'),
              maxLines: 2,
            ),
            const SizedBox(height: 10),
            DropdownButtonFormField<String>(
              initialValue: finalStatus,
              decoration: const InputDecoration(labelText: 'Resultado final'),
              items: const [
                DropdownMenuItem(value: 'PASSED', child: Text('Aprobado')),
                DropdownMenuItem(
                  value: 'PASSED_WITH_OBSERVATIONS',
                  child: Text('Aprobado con observaciones'),
                ),
                DropdownMenuItem(value: 'FAILED', child: Text('No aprobado')),
              ],
              onChanged: (value) =>
                  setSheetState(() => finalStatus = value ?? finalStatus),
            ),
            const SizedBox(height: 15),
            ElevatedButton(
              onPressed: () async {
                Navigator.pop(sheetContext);
                await _run(context, () async {
                  await store.updateInstallationChecklist(
                    checklistId: item['id'] as int,
                    responses: _expandAnswers(answers),
                    firstReadingId: readings.isEmpty
                        ? item['first_reading_id'] as int?
                        : readings.first['id'] as int,
                    testAlertId: alerts.isEmpty
                        ? item['test_alert_id'] as int?
                        : alerts.first['id'] as int,
                    notes: notes.text.trim(),
                  );
                  await store.validateInstallationChecklist(
                    item['id'] as int,
                    finalStatus,
                  );
                }, 'Checklist guardado y validado.');
              },
              child: const Text('Guardar y validar'),
            ),
          ],
        ),
      ),
    ),
  );
  notes.dispose();
}

Future<void> _captureEvidence(
  BuildContext context,
  AppStore store,
  ImageSource source,
) async {
  final maintenance = await _selectMaintenance(context, store);
  if (maintenance == null || !context.mounted) return;
  final selected = await ImagePicker().pickImage(
    source: source,
    imageQuality: 82,
    maxWidth: 1800,
  );
  if (selected == null || !context.mounted) return;
  final description = source == ImageSource.camera
      ? 'Evidencia fotografica capturada durante intervencion tecnica.'
      : 'Evidencia fotografica seleccionada por el tecnico responsable.';
  await _run(
    context,
    () => store.uploadEvidence(
      storageUnitId: maintenance['storage_unit_id'] as int,
      entityType: 'maintenance',
      entityId: maintenance['id'] as int,
      filePath: selected.path,
      contentType: _imageContentType(selected.path),
      description: description,
    ),
    'Evidencia cargada y vinculada al mantenimiento.',
  );
}

Future<Map<String, dynamic>?> _selectMaintenance(
  BuildContext context,
  AppStore store,
) async {
  final rows = store.maintenanceRecords;
  if (rows.isEmpty) return null;
  if (rows.length == 1) return rows.first;
  return showDialog<Map<String, dynamic>>(
    context: context,
    builder: (dialogContext) => SimpleDialog(
      title: const Text('Selecciona la intervencion'),
      children: rows
          .map(
            (item) => SimpleDialogOption(
              onPressed: () => Navigator.pop(dialogContext, item),
              child: Padding(
                padding: const EdgeInsets.symmetric(vertical: 6),
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Text(
                      _deviceLabel(store, item['device_id']),
                      style: const TextStyle(fontWeight: FontWeight.w800),
                    ),
                    Text(
                      '${_human(item['maintenance_type'])}  |  ${_human(item['effective_status'])}',
                      style: const TextStyle(color: _muted, fontSize: 12),
                    ),
                  ],
                ),
              ),
            ),
          )
          .toList(),
    ),
  );
}

Future<void> _run(
  BuildContext context,
  Future<void> Function() action,
  String success,
) async {
  try {
    await action();
    if (context.mounted) _toast(context, success);
  } on ApiException catch (exception) {
    if (context.mounted) _toast(context, exception.message);
  }
}

class _Intro extends StatelessWidget {
  const _Intro({required this.title, required this.copy});

  final String title;
  final String copy;

  @override
  Widget build(BuildContext context) {
    return Padding(
      padding: const EdgeInsets.only(bottom: 14),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Text(
            title,
            style: const TextStyle(
              color: _ink,
              fontSize: 22,
              fontWeight: FontWeight.w800,
            ),
          ),
          const SizedBox(height: 5),
          Text(copy, style: const TextStyle(color: _muted, height: 1.4)),
        ],
      ),
    );
  }
}

class _Status extends StatelessWidget {
  const _Status({required this.value});

  final String? value;

  @override
  Widget build(BuildContext context) {
    final text = value ?? 'UNKNOWN';
    final positive =
        text.contains('COMPLETE') ||
        text.contains('PASSED') ||
        text.contains('ONLINE');
    final warning =
        text.contains('OVERDUE') ||
        text.contains('FAILED') ||
        text.contains('OFFLINE');
    final color = positive
        ? _emerald
        : warning
        ? Colors.red.shade800
        : Colors.orange.shade900;
    final background = positive
        ? const Color(0xffe8f7f0)
        : warning
        ? const Color(0xffffebe9)
        : const Color(0xfffff4d6);
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 9, vertical: 5),
      decoration: BoxDecoration(
        color: background,
        borderRadius: BorderRadius.circular(20),
      ),
      child: Text(
        _human(text),
        style: TextStyle(
          color: color,
          fontSize: 10,
          fontWeight: FontWeight.w800,
        ),
      ),
    );
  }
}

class _Empty extends StatelessWidget {
  const _Empty(this.message);

  final String message;

  @override
  Widget build(BuildContext context) {
    return Card(
      child: Padding(
        padding: const EdgeInsets.all(18),
        child: Row(
          children: [
            const Icon(Icons.inbox_outlined, color: _muted),
            const SizedBox(width: 10),
            Expanded(
              child: Text(message, style: const TextStyle(color: _muted)),
            ),
          ],
        ),
      ),
    );
  }
}

class _LoadError extends StatelessWidget {
  const _LoadError({required this.error, required this.onRetry});

  final Object? error;
  final Future<void> Function() onRetry;

  @override
  Widget build(BuildContext context) {
    return Center(
      child: Padding(
        padding: const EdgeInsets.all(24),
        child: Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            const Icon(Icons.cloud_off_outlined, size: 44, color: _muted),
            const SizedBox(height: 12),
            Text(
              error is ApiException
                  ? (error! as ApiException).message
                  : 'No se pudo cargar la operacion del piloto.',
              textAlign: TextAlign.center,
            ),
            const SizedBox(height: 12),
            OutlinedButton.icon(
              onPressed: onRetry,
              icon: const Icon(Icons.refresh),
              label: const Text('Reintentar'),
            ),
          ],
        ),
      ),
    );
  }
}

const _checklistItems = <(String, String)>[
  ('hardware.enclosure_ok', 'Caja y proteccion verificadas'),
  ('hardware.mounting_ok', 'Montaje fisico estable'),
  ('hardware.antenna_ok', 'Antena instalada correctamente'),
  ('hardware.battery_ok', 'Bateria y alimentacion verificadas'),
  ('hardware.sensor_ok', 'Sensor responde correctamente'),
  ('hardware.wiring_ok', 'Cableado revisado'),
  ('hardware.sealed_ok', 'Sellado contra polvo y humedad'),
  ('hardware.qr_applied', 'Etiqueta QR instalada'),
  ('communication.first_transmission', 'Primera transmision recibida'),
  ('communication.time_synced', 'Hora sincronizada'),
  ('communication.connectivity_ok', 'Conectividad verificada'),
  ('validation.reading_compared', 'Lectura comparada en sitio'),
  ('validation.thresholds_validated', 'Umbrales revisados'),
  ('validation.test_alert_passed', 'Alerta de prueba confirmada'),
  ('validation.client_access_validated', 'Acceso cliente validado'),
  ('validation.technician_access_validated', 'Acceso tecnico validado'),
  ('validation.test_report_generated', 'Reporte de prueba generado'),
];

Map<String, dynamic> _expandAnswers(Map<String, bool> values) {
  final output = <String, dynamic>{};
  for (final entry in values.entries) {
    final parts = entry.key.split('.');
    final group =
        output.putIfAbsent(parts.first, () => <String, dynamic>{})
            as Map<String, dynamic>;
    group[parts.last] = entry.value;
  }
  final communication =
      output.putIfAbsent('communication', () => <String, dynamic>{})
          as Map<String, dynamic>;
  communication['gateway_required'] = true;
  return output;
}

bool _responseAt(Map<String, dynamic> item, String path) {
  dynamic value = item['responses'];
  for (final segment in path.split('.')) {
    if (value is! Map || !value.containsKey(segment)) return false;
    value = value[segment];
  }
  return value == true;
}

String _deviceLabel(AppStore store, dynamic id) {
  final device = store.devices.cast<Map<String, dynamic>?>().firstWhere(
    (item) => item?['id'] == id,
    orElse: () => null,
  );
  return device == null
      ? 'Nodo #$id'
      : '${device['external_id']} / ${device['name']}';
}

String _human(dynamic value) =>
    value
        ?.toString()
        .replaceAll('_', ' ')
        .toLowerCase()
        .split(' ')
        .map(
          (word) => word.isEmpty
              ? word
              : '${word[0].toUpperCase()}${word.substring(1)}',
        )
        .join(' ') ??
    'No registrado';

String _size(dynamic value) {
  final bytes = value is num ? value.toDouble() : 0;
  if (bytes >= 1024 * 1024) {
    return '${(bytes / 1024 / 1024).toStringAsFixed(1)} MB';
  }
  return '${(bytes / 1024).toStringAsFixed(0)} KB';
}

String _imageContentType(String path) {
  final lower = path.toLowerCase();
  if (lower.endsWith('.png')) return 'image/png';
  if (lower.endsWith('.webp')) return 'image/webp';
  return 'image/jpeg';
}

DateTime _date(dynamic value) =>
    DateTime.tryParse(value?.toString() ?? '') ??
    DateTime.fromMillisecondsSinceEpoch(0);

void _toast(BuildContext context, String message) {
  ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text(message)));
}
