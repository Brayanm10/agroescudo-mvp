import 'package:fl_chart/fl_chart.dart';
import 'package:flutter/material.dart';
import 'package:go_router/go_router.dart';
import 'package:intl/intl.dart';
import 'package:provider/provider.dart';

import '../core/api_client.dart';
import '../core/app_store.dart';
import 'pilot_operations_screen.dart';

const darkGreen = Color(0xff053f31);
const emerald = Color(0xff075b44);
const amber = Color(0xffc89116);
const ink = Color(0xff16352d);
const muted = Color(0xff62756f);
const danger = Color(0xffb42318);

final formatDate = DateFormat('dd/MM/yyyy, HH:mm');

class LoginScreen extends StatefulWidget {
  const LoginScreen({super.key});

  @override
  State<LoginScreen> createState() => _LoginScreenState();
}

class _LoginScreenState extends State<LoginScreen> {
  final email = TextEditingController();
  final password = TextEditingController();
  bool hidePassword = true;

  @override
  void dispose() {
    email.dispose();
    password.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    final store = context.watch<AppStore>();
    return Scaffold(
      body: SafeArea(
        child: ListView(
          padding: const EdgeInsets.fromLTRB(24, 28, 24, 20),
          children: [
            Center(
              child: Image.asset(
                'assets/brand/shield-transparent.png',
                height: 104,
              ),
            ),
            const SizedBox(height: 18),
            const Text(
              'AgroEscudo',
              textAlign: TextAlign.center,
              style: TextStyle(
                color: darkGreen,
                fontSize: 34,
                fontWeight: FontWeight.w800,
              ),
            ),
            const Text(
              'CONTROL OPERATIVO POSTCOSECHA',
              textAlign: TextAlign.center,
              style: TextStyle(
                color: amber,
                fontSize: 11,
                fontWeight: FontWeight.w800,
                letterSpacing: 1.1,
              ),
            ),
            const SizedBox(height: 30),
            const Text(
              'Acceso seguro',
              style: TextStyle(fontSize: 25, fontWeight: FontWeight.w800),
            ),
            const SizedBox(height: 8),
            const Text(
              'Revisa el estado de tus silos, alertas y evidencia operativa desde campo.',
              style: TextStyle(color: muted, height: 1.45),
            ),
            const SizedBox(height: 22),
            TextField(
              controller: email,
              keyboardType: TextInputType.emailAddress,
              decoration: const InputDecoration(
                labelText: 'Correo',
                prefixIcon: Icon(Icons.alternate_email),
              ),
            ),
            const SizedBox(height: 12),
            TextField(
              controller: password,
              obscureText: hidePassword,
              decoration: InputDecoration(
                labelText: 'Contrasena',
                prefixIcon: const Icon(Icons.lock_outline),
                suffixIcon: IconButton(
                  icon: Icon(
                    hidePassword ? Icons.visibility_off : Icons.visibility,
                  ),
                  onPressed: () => setState(() => hidePassword = !hidePassword),
                ),
              ),
            ),
            if (store.error != null) ...[
              const SizedBox(height: 12),
              _Notice(text: store.error!, danger: true),
              const SizedBox(height: 8),
              OutlinedButton.icon(
                onPressed: store.loading
                    ? null
                    : () async {
                        try {
                          await context.read<AppStore>().checkConnection();
                          if (!context.mounted) return;
                          _toast(
                            context,
                            'Conexion con AgroEscudo API verificada.',
                          );
                        } on ApiException {
                          // The store exposes the detailed connection diagnosis.
                        }
                      },
                icon: const Icon(Icons.refresh),
                label: const Text('Reintentar conexion'),
              ),
            ],
            const SizedBox(height: 16),
            ElevatedButton.icon(
              onPressed: store.loading
                  ? null
                  : () async {
                      try {
                        await context.read<AppStore>().login(
                          email.text.trim(),
                          password.text,
                        );
                      } on ApiException {
                        // The store exposes a polished error message.
                      }
                    },
              icon: store.loading
                  ? const SizedBox(
                      width: 18,
                      height: 18,
                      child: CircularProgressIndicator(strokeWidth: 2),
                    )
                  : const Icon(Icons.login),
              label: Text(store.loading ? 'Ingresando...' : 'Ingresar'),
            ),
            const SizedBox(height: 22),
          ],
        ),
      ),
    );
  }
}

class MobileShell extends StatefulWidget {
  const MobileShell({super.key});

  @override
  State<MobileShell> createState() => _MobileShellState();
}

class _MobileShellState extends State<MobileShell> {
  var index = 0;

  @override
  Widget build(BuildContext context) {
    final store = context.watch<AppStore>();
    final pages = [
      const DashboardScreen(),
      const UnitsScreen(),
      const AlertsScreen(),
      const LogsScreen(),
      const ReportsScreen(),
    ];
    return Scaffold(
      appBar: AppBar(
        titleSpacing: 16,
        title: Row(
          children: [
            Image.asset(
              'assets/brand/shield-transparent.png',
              width: 34,
              height: 34,
            ),
            const SizedBox(width: 9),
            const Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(
                  'AgroEscudo',
                  style: TextStyle(fontSize: 18, fontWeight: FontWeight.w800),
                ),
                Text(
                  'MONITOREO POSTCOSECHA',
                  style: TextStyle(
                    fontSize: 8,
                    color: Color(0xffe4bd58),
                    fontWeight: FontWeight.w700,
                    letterSpacing: .8,
                  ),
                ),
              ],
            ),
          ],
        ),
        actions: [
          IconButton(
            tooltip: 'Actualizar',
            onPressed: store.loading
                ? null
                : () async {
                    try {
                      await context.read<AppStore>().refresh();
                    } on ApiException {
                      if (!context.mounted) return;
                      _toast(context, 'Mostrando el ultimo estado disponible.');
                    }
                  },
            icon: const Icon(Icons.refresh),
          ),
          IconButton(
            tooltip: 'Cerrar sesion',
            onPressed: () async {
              await context.read<AppStore>().logout();
              if (context.mounted) context.go('/login');
            },
            icon: const Icon(Icons.logout),
          ),
        ],
      ),
      body: Column(
        children: [
          if (store.cached)
            const _OfflineBanner()
          else if (store.loading)
            const LinearProgressIndicator(minHeight: 2),
          Expanded(child: pages[index]),
        ],
      ),
      bottomNavigationBar: NavigationBar(
        selectedIndex: index,
        onDestinationSelected: (value) => setState(() => index = value),
        destinations: const [
          NavigationDestination(
            icon: Icon(Icons.dashboard_outlined),
            label: 'Inicio',
          ),
          NavigationDestination(
            icon: Icon(Icons.sensors_outlined),
            label: 'Silos/Campo',
          ),
          NavigationDestination(
            icon: Icon(Icons.warning_amber),
            label: 'Alertas',
          ),
          NavigationDestination(
            icon: Icon(Icons.fact_check_outlined),
            label: 'Bitacora',
          ),
          NavigationDestination(
            icon: Icon(Icons.picture_as_pdf_outlined),
            label: 'Reportes',
          ),
        ],
      ),
    );
  }
}

class DashboardScreen extends StatelessWidget {
  const DashboardScreen({super.key});

  @override
  Widget build(BuildContext context) {
    final store = context.watch<AppStore>();
    final latest = store.readings.isEmpty ? null : _newest(store.readings);
    final critical = store.activeAlerts
        .where((item) => item['severity'] == 'critical')
        .length;
    final state = critical > 0
        ? 'Atencion critica'
        : store.activeAlerts.isNotEmpty
        ? 'Seguimiento requerido'
        : 'Operacion estable';
    return _Page(
      children: [
        _SectionTitle(
          eyebrow: _roleLabel(store.role),
          title: store.role == 'client'
              ? 'Portal del propietario'
              : 'Centro operativo',
          subtitle: 'Estado consolidado del monitoreo postcosecha.',
        ),
        _RiskPanel(
          title: state,
          critical: critical > 0,
          subtitle: critical > 0
              ? '$critical alerta(s) critica(s) requieren intervencion.'
              : 'Sin eventos criticos pendientes en este momento.',
        ),
        const SizedBox(height: 14),
        GridView.count(
          shrinkWrap: true,
          physics: const NeverScrollableScrollPhysics(),
          crossAxisCount: 2,
          childAspectRatio: 1.5,
          mainAxisSpacing: 10,
          crossAxisSpacing: 10,
          children: [
            _Metric(
              label: 'SITIOS',
              value: '${store.sites.length}',
              icon: Icons.location_on_outlined,
            ),
            _Metric(
              label: 'UNIDADES',
              value: '${store.units.length}',
              icon: Icons.warehouse_outlined,
            ),
            _Metric(
              label: 'DISPOSITIVOS',
              value: '${store.devices.length}',
              icon: Icons.sensors_outlined,
            ),
            _Metric(
              label: 'ALERTAS ACTIVAS',
              value: '${store.activeAlerts.length}',
              icon: Icons.warning_amber,
            ),
          ],
        ),
        const SizedBox(height: 20),
        const _BlockTitle('Ultima evidencia recibida'),
        if (latest == null)
          const _Empty('Todavia no hay lecturas disponibles.')
        else
          _ReadingSummary(reading: latest, showSignal: store.role != 'client'),
        const SizedBox(height: 20),
        const _BlockTitle('Atencion prioritaria'),
        if (store.activeAlerts.isEmpty)
          const _Empty('No existen alertas activas.')
        else
          ...store.activeAlerts.take(3).map((item) => _AlertTile(alert: item)),
        if (store.role == 'technician') ...[
          const SizedBox(height: 20),
          const _BlockTitle('Operacion tecnica'),
          _ActionCard(
            icon: Icons.engineering_outlined,
            title: 'Centro tecnico del piloto',
            text:
                'Gestiona mantenimiento, checklist, QR y evidencia desde campo.',
            onTap: () => _showInstallation(context),
          ),
        ],
      ],
    );
  }
}

class UnitsScreen extends StatelessWidget {
  const UnitsScreen({super.key});

  @override
  Widget build(BuildContext context) {
    final store = context.watch<AppStore>();
    final storageUnits = store.units
        .where((unit) => _operationType(unit) == 'storage')
        .toList();
    final fieldUnits = store.units
        .where((unit) => _operationType(unit) == 'field')
        .toList();
    return _Page(
      children: [
        const _SectionTitle(
          eyebrow: 'ACTIVOS MONITOREADOS',
          title: 'Silos y campo',
          subtitle:
              'Productos separados, telemetria por nodo y valores calibrados.',
        ),
        if (store.units.isEmpty)
          const _Empty('No hay unidades asignadas a este usuario.')
        else ...[
          if (storageUnits.isNotEmpty) const _BlockTitle('SiloSensor'),
          ...storageUnits.map((unit) => _unitCard(context, store, unit)),
          if (fieldUnits.isNotEmpty) ...[
            const SizedBox(height: 16),
            const _BlockTitle('CampoSensor'),
          ],
          ...fieldUnits.map((unit) => _unitCard(context, store, unit)),
        ],
      ],
    );
  }

  Widget _unitCard(
    BuildContext context,
    AppStore store,
    Map<String, dynamic> unit,
  ) {
    final latest = store.latestReadingFor(unit['id'] as int);
    final field = _operationType(unit) == 'field';
    return Card(
      margin: const EdgeInsets.only(bottom: 10),
      child: InkWell(
        borderRadius: BorderRadius.circular(12),
        onTap: () => Navigator.of(
          context,
        ).push(MaterialPageRoute(builder: (_) => UnitDetailScreen(unit: unit))),
        child: Padding(
          padding: const EdgeInsets.all(15),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Row(
                children: [
                  Icon(
                    field ? Icons.grass_outlined : Icons.warehouse_outlined,
                    color: emerald,
                  ),
                  const SizedBox(width: 10),
                  Expanded(
                    child: Text(
                      unit['name']?.toString() ?? 'Unidad',
                      style: const TextStyle(
                        fontWeight: FontWeight.w800,
                        fontSize: 17,
                      ),
                    ),
                  ),
                  const Icon(Icons.chevron_right, color: muted),
                ],
              ),
              const SizedBox(height: 10),
              Text(
                field
                    ? '${unit['unit_type']}  |  ${_surface(unit)}'
                    : '${unit['unit_type']}  |  ${_capacity(unit)}',
                style: const TextStyle(color: muted),
              ),
              const Divider(height: 22),
              Text(
                latest == null
                    ? 'Sin lectura reciente'
                    : field
                    ? '${_num(latest['soil_moisture_percent'])}% suelo  |  ${_num(latest['ambient_humidity'])}% ambiente'
                    : '${_num(latest['grain_temperature'])} C grano  |  ${_num(latest['ambient_humidity'])}% humedad',
                style: const TextStyle(color: ink, fontWeight: FontWeight.w700),
              ),
            ],
          ),
        ),
      ),
    );
  }
}

class UnitDetailScreen extends StatefulWidget {
  const UnitDetailScreen({super.key, required this.unit});

  final Map<String, dynamic> unit;

  @override
  State<UnitDetailScreen> createState() => _UnitDetailScreenState();
}

class _UnitDetailScreenState extends State<UnitDetailScreen> {
  int? deviceId;
  Future<Map<String, dynamic>>? telemetry;

  void _selectDevice(AppStore store, int id) {
    setState(() {
      deviceId = id;
      telemetry = store.loadDeviceTelemetry(id);
    });
  }

  @override
  Widget build(BuildContext context) {
    final store = context.watch<AppStore>();
    final unit = widget.unit;
    final id = unit['id'] as int;
    final devices = store.devicesFor(id);
    if (deviceId == null && devices.isNotEmpty) {
      deviceId = devices.first['id'] as int;
      telemetry = store.loadDeviceTelemetry(deviceId!);
    }
    final selectedDevice = devices.cast<Map<String, dynamic>?>().firstWhere(
      (device) => device?['id'] == deviceId,
      orElse: () => null,
    );
    final unitAlerts = store.activeAlerts.where(
      (item) =>
          item['storage_unit_id'] == id &&
          (deviceId == null || item['device_id'] == deviceId),
    );
    final unitLogs = store.logs.where(
      (item) =>
          item['storage_unit_id'] == id &&
          (deviceId == null ||
              item['device_id'] == null ||
              item['device_id'] == deviceId),
    );
    final field = _deviceProfile(selectedDevice) == 'field_sensor';

    return Scaffold(
      appBar: AppBar(title: Text(unit['name']?.toString() ?? 'Unidad')),
      body: FutureBuilder<Map<String, dynamic>>(
        future: telemetry,
        builder: (context, snapshot) {
          final payload = snapshot.data;
          final readings =
              (payload?['readings'] as List<Map<String, dynamic>>?) ?? const [];
          final summary =
              (payload?['summary'] as Map<String, dynamic>?) ?? const {};
          final latest =
              summary['latest_reading'] as Map<String, dynamic>? ??
              (readings.isEmpty ? null : readings.last);
          final calibrations =
              (summary['calibration_statuses'] as List?) ?? const [];

          return _Page(
            children: [
              _SectionTitle(
                eyebrow: field ? 'CAMPOSENSOR' : 'SILOSENSOR',
                title: unit['name']?.toString() ?? 'Unidad monitoreada',
                subtitle: field
                    ? '${_surface(unit)} monitoreadas. Datos calibrados por nodo.'
                    : '${_capacity(unit)} de capacidad instalada. Datos calibrados por nodo.',
              ),
              if (devices.length > 1)
                DropdownButtonFormField<int>(
                  initialValue: deviceId,
                  decoration: const InputDecoration(
                    labelText: 'Nodo monitoreado',
                  ),
                  items: devices
                      .map(
                        (device) => DropdownMenuItem<int>(
                          value: device['id'] as int,
                          child: Text(
                            '${device['name']} / ${device['external_id']}',
                          ),
                        ),
                      )
                      .toList(),
                  onChanged: (value) {
                    if (value != null) _selectDevice(store, value);
                  },
                ),
              if (devices.length > 1) const SizedBox(height: 14),
              _RiskPanel(
                title: unitAlerts.any((item) => item['severity'] == 'critical')
                    ? 'Riesgo critico'
                    : unitAlerts.isNotEmpty
                    ? 'Seguimiento requerido'
                    : 'Condicion estable',
                critical: unitAlerts.any(
                  (item) => item['severity'] == 'critical',
                ),
                subtitle: unitAlerts.isEmpty
                    ? 'No se observan alertas activas para este nodo.'
                    : '${unitAlerts.length} alerta(s) activas requieren revision.',
              ),
              const SizedBox(height: 14),
              if (devices.isEmpty)
                const _Empty('Esta unidad no tiene nodos asignados.')
              else if (snapshot.connectionState == ConnectionState.waiting &&
                  payload == null)
                const Center(child: CircularProgressIndicator())
              else if (snapshot.hasError && payload == null)
                _Empty('No se pudo cargar el nodo. Desliza para reintentar.')
              else if (latest == null)
                const _Empty('No hay lecturas para este nodo.')
              else
                GridView.count(
                  shrinkWrap: true,
                  physics: const NeverScrollableScrollPhysics(),
                  crossAxisCount: 2,
                  childAspectRatio: 1.42,
                  mainAxisSpacing: 10,
                  crossAxisSpacing: 10,
                  children: [
                    if (!field)
                      _Metric(
                        label: 'GRANO',
                        value: '${_num(latest['grain_temperature'])} C',
                        icon: Icons.device_thermostat,
                      ),
                    if (field)
                      _Metric(
                        label: 'HUMEDAD SUELO',
                        value: '${_num(latest['soil_moisture_percent'])}%',
                        icon: Icons.grass_outlined,
                      ),
                    _Metric(
                      label: 'HUMEDAD AMB.',
                      value: '${_num(latest['ambient_humidity'])}%',
                      icon: Icons.water_drop_outlined,
                    ),
                    if (field)
                      _Metric(
                        label: 'TEMP. SUELO',
                        value: '${_num(latest['soil_temperature_c'])} C',
                        icon: Icons.thermostat_outlined,
                      ),
                    if (!field)
                      _Metric(
                        label: 'NIVEL',
                        value: '${_num(latest['level_percent'])}%',
                        icon: Icons.straighten_outlined,
                      ),
                    _Metric(
                      label: 'BATERIA',
                      value: store.role == 'client'
                          ? _batteryState(latest['battery_voltage'])
                          : '${_num(latest['battery_voltage'])} V',
                      icon: Icons.battery_4_bar,
                    ),
                    if (store.role != 'client')
                      _Metric(
                        label: 'SENAL',
                        value: latest['signal_quality'] == null
                            ? 'Sin dato'
                            : '${latest['signal_quality']} dBm',
                        icon: Icons.network_cell,
                      ),
                  ],
                ),
              const SizedBox(height: 18),
              const _BlockTitle('Estado de calibracion'),
              if (calibrations.isEmpty)
                const _Empty(
                  'Calibracion pendiente o lectura legacy sin version.',
                )
              else
                ...calibrations.map(
                  (item) => _CalibrationStatus(
                    calibration: Map<String, dynamic>.from(item as Map),
                  ),
                ),
              if (readings.isNotEmpty) ...[
                const SizedBox(height: 20),
                _ReadingChart(
                  readings: readings,
                  keyName: field
                      ? 'soil_moisture_percent'
                      : 'grain_temperature',
                  suffix: field ? '%' : ' C',
                ),
                const SizedBox(height: 20),
                _ReadingChart(
                  readings: readings,
                  keyName: 'ambient_humidity',
                  suffix: '%',
                ),
              ],
              const SizedBox(height: 20),
              const _BlockTitle('Alertas activas'),
              if (unitAlerts.isEmpty)
                const _Empty('Sin alertas activas.')
              else
                ...unitAlerts.map((alert) => _AlertTile(alert: alert)),
              const SizedBox(height: 20),
              const _BlockTitle('Bitacora reciente'),
              if (unitLogs.isEmpty)
                const _Empty('Sin acciones registradas.')
              else
                ...unitLogs.take(4).map((log) => _LogTile(log: log)),
              const SizedBox(height: 18),
              ElevatedButton.icon(
                onPressed: () => _downloadPdf(context, unit),
                icon: const Icon(Icons.picture_as_pdf_outlined),
                label: const Text('Descargar reporte PDF'),
              ),
              if (store.canOperate) ...[
                const SizedBox(height: 10),
                OutlinedButton.icon(
                  onPressed: () => _showLogForm(context, initialUnit: unit),
                  icon: const Icon(Icons.add_task_outlined),
                  label: const Text('Registrar accion correctiva'),
                ),
              ],
            ],
          );
        },
      ),
    );
  }
}

class AlertsScreen extends StatelessWidget {
  const AlertsScreen({super.key});

  @override
  Widget build(BuildContext context) {
    final store = context.watch<AppStore>();
    return _Page(
      children: [
        const _SectionTitle(
          eyebrow: 'GESTION DE RIESGO',
          title: 'Alertas operativas',
          subtitle: 'Prioriza intervenciones y deja evidencia de seguimiento.',
        ),
        if (store.alerts.isEmpty)
          const _Empty('No hay alertas registradas.')
        else
          ...store.alerts.map(
            (alert) => _AlertTile(alert: alert, actions: store.canOperate),
          ),
      ],
    );
  }
}

class LogsScreen extends StatelessWidget {
  const LogsScreen({super.key});

  @override
  Widget build(BuildContext context) {
    final store = context.watch<AppStore>();
    return _Page(
      children: [
        _SectionTitle(
          eyebrow: 'TRAZABILIDAD OPERATIVA',
          title: 'Bitacora',
          subtitle: store.canOperate
              ? 'Documenta mantenimiento y acciones correctivas desde campo.'
              : 'Consulta el historial de intervenciones registradas.',
        ),
        if (store.canOperate)
          Row(
            children: [
              Expanded(
                child: ElevatedButton.icon(
                  onPressed: () => _showLogForm(context),
                  icon: const Icon(Icons.add_task_outlined),
                  label: const Text('Registrar accion'),
                ),
              ),
              const SizedBox(width: 8),
              IconButton.filledTonal(
                tooltip: 'Checklist de instalacion',
                onPressed: () => _showInstallation(context),
                icon: const Icon(Icons.install_mobile_outlined),
              ),
            ],
          ),
        const SizedBox(height: 16),
        if (store.logs.isEmpty)
          const _Empty('No hay registros de bitacora.')
        else
          ...store.logs.map((log) => _LogTile(log: log)),
      ],
    );
  }
}

class ReportsScreen extends StatelessWidget {
  const ReportsScreen({super.key});

  @override
  Widget build(BuildContext context) {
    final store = context.watch<AppStore>();
    return _Page(
      children: [
        const _SectionTitle(
          eyebrow: 'EVIDENCIA PARA CLIENTE',
          title: 'Reportes semanales',
          subtitle:
              'Descarga el informe corporativo con indicadores y trazabilidad.',
        ),
        if (store.units.isEmpty)
          const _Empty('No hay unidades disponibles para generar reportes.')
        else
          ...store.units.map((unit) {
            final pilot = store.pilots.cast<Map<String, dynamic>?>().firstWhere(
              (item) => item?['storage_unit_id'] == unit['id'],
              orElse: () => null,
            );
            return Card(
              margin: const EdgeInsets.only(bottom: 11),
              child: Padding(
                padding: const EdgeInsets.all(15),
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Text(
                      unit['name']?.toString() ?? 'Unidad',
                      style: const TextStyle(
                        fontSize: 17,
                        fontWeight: FontWeight.w800,
                      ),
                    ),
                    const SizedBox(height: 5),
                    Text(
                      pilot == null
                          ? 'Reporte tecnico de monitoreo'
                          : '${pilot['reading_count']} lecturas  |  ${pilot['alerts_generated']} alertas  |  ${pilot['actions_registered']} acciones',
                      style: const TextStyle(color: muted, height: 1.35),
                    ),
                    const SizedBox(height: 13),
                    ElevatedButton.icon(
                      onPressed: () => _downloadPdf(context, unit),
                      icon: const Icon(Icons.download_outlined),
                      label: const Text('Descargar PDF semanal'),
                    ),
                  ],
                ),
              ),
            );
          }),
      ],
    );
  }
}

class _Page extends StatelessWidget {
  const _Page({required this.children});

  final List<Widget> children;

  @override
  Widget build(BuildContext context) {
    return RefreshIndicator(
      onRefresh: () async {
        try {
          await context.read<AppStore>().refresh();
        } on ApiException {
          if (!context.mounted) return;
          _toast(
            context,
            'No se pudo actualizar. Se conserva el ultimo estado.',
          );
        }
      },
      child: ListView(
        physics: const AlwaysScrollableScrollPhysics(),
        padding: const EdgeInsets.fromLTRB(16, 18, 16, 26),
        children: children,
      ),
    );
  }
}

class _SectionTitle extends StatelessWidget {
  const _SectionTitle({
    required this.eyebrow,
    required this.title,
    required this.subtitle,
  });

  final String eyebrow;
  final String title;
  final String subtitle;

  @override
  Widget build(BuildContext context) {
    return Padding(
      padding: const EdgeInsets.only(bottom: 16),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Text(
            eyebrow,
            style: const TextStyle(
              color: emerald,
              fontSize: 10,
              fontWeight: FontWeight.w800,
              letterSpacing: 1.2,
            ),
          ),
          const SizedBox(height: 4),
          Text(
            title,
            style: const TextStyle(fontSize: 26, fontWeight: FontWeight.w800),
          ),
          const SizedBox(height: 5),
          Text(subtitle, style: const TextStyle(color: muted, height: 1.4)),
        ],
      ),
    );
  }
}

class _BlockTitle extends StatelessWidget {
  const _BlockTitle(this.text);

  final String text;

  @override
  Widget build(BuildContext context) {
    return Padding(
      padding: const EdgeInsets.only(bottom: 9),
      child: Text(
        text,
        style: const TextStyle(fontSize: 17, fontWeight: FontWeight.w800),
      ),
    );
  }
}

class _RiskPanel extends StatelessWidget {
  const _RiskPanel({
    required this.title,
    required this.subtitle,
    required this.critical,
  });

  final String title;
  final String subtitle;
  final bool critical;

  @override
  Widget build(BuildContext context) {
    final color = critical ? danger : emerald;
    return Container(
      padding: const EdgeInsets.all(16),
      decoration: BoxDecoration(
        color: critical ? const Color(0xfffff1f0) : const Color(0xffeaf8f1),
        borderRadius: BorderRadius.circular(12),
        border: Border.all(color: color.withValues(alpha: .22)),
      ),
      child: Row(
        children: [
          Icon(
            critical ? Icons.warning_rounded : Icons.verified_outlined,
            color: color,
            size: 34,
          ),
          const SizedBox(width: 12),
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(
                  title,
                  style: TextStyle(
                    color: color,
                    fontSize: 18,
                    fontWeight: FontWeight.w800,
                  ),
                ),
                const SizedBox(height: 3),
                Text(
                  subtitle,
                  style: const TextStyle(color: muted, height: 1.3),
                ),
              ],
            ),
          ),
        ],
      ),
    );
  }
}

class _Metric extends StatelessWidget {
  const _Metric({required this.label, required this.value, required this.icon});

  final String label;
  final String value;
  final IconData icon;

  @override
  Widget build(BuildContext context) {
    return Card(
      child: Padding(
        padding: const EdgeInsets.all(13),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          mainAxisAlignment: MainAxisAlignment.spaceBetween,
          children: [
            Icon(icon, color: emerald, size: 21),
            Text(
              value,
              style: const TextStyle(fontSize: 21, fontWeight: FontWeight.w800),
            ),
            Text(
              label,
              maxLines: 1,
              overflow: TextOverflow.ellipsis,
              style: const TextStyle(
                color: muted,
                fontSize: 9,
                fontWeight: FontWeight.w800,
                letterSpacing: .8,
              ),
            ),
          ],
        ),
      ),
    );
  }
}

class _ReadingSummary extends StatelessWidget {
  const _ReadingSummary({required this.reading, required this.showSignal});

  final Map<String, dynamic> reading;
  final bool showSignal;

  @override
  Widget build(BuildContext context) {
    return Card(
      child: Padding(
        padding: const EdgeInsets.all(15),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text(
              _date(reading['timestamp']),
              style: const TextStyle(color: muted, fontSize: 12),
            ),
            const SizedBox(height: 11),
            Wrap(
              spacing: 18,
              runSpacing: 10,
              children: [
                _InlineValue(
                  'Grano',
                  '${_num(reading['grain_temperature'])} C',
                ),
                _InlineValue(
                  'Humedad',
                  '${_num(reading['ambient_humidity'])}%',
                ),
                _InlineValue(
                  'Bateria',
                  '${_num(reading['battery_voltage'])} V',
                ),
                if (showSignal)
                  _InlineValue(
                    'Senal',
                    reading['signal_quality'] == null
                        ? 'Sin dato'
                        : '${reading['signal_quality']} dBm',
                  ),
              ],
            ),
          ],
        ),
      ),
    );
  }
}

class _InlineValue extends StatelessWidget {
  const _InlineValue(this.label, this.value);

  final String label;
  final String value;

  @override
  Widget build(BuildContext context) {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Text(
          label.toUpperCase(),
          style: const TextStyle(
            color: muted,
            fontSize: 9,
            fontWeight: FontWeight.w700,
          ),
        ),
        const SizedBox(height: 2),
        Text(value, style: const TextStyle(fontWeight: FontWeight.w800)),
      ],
    );
  }
}

class _AlertTile extends StatelessWidget {
  const _AlertTile({required this.alert, this.actions = false});

  final Map<String, dynamic> alert;
  final bool actions;

  @override
  Widget build(BuildContext context) {
    final store = context.watch<AppStore>();
    final active = alert['is_active'] == true;
    return Card(
      margin: const EdgeInsets.only(bottom: 9),
      child: Padding(
        padding: const EdgeInsets.all(14),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Row(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                _StatusBadge(
                  value: active
                      ? alert['severity']?.toString() ?? 'warning'
                      : 'resolved',
                ),
                const Spacer(),
                Text(
                  _date(alert['created_at']),
                  style: const TextStyle(color: muted, fontSize: 11),
                ),
              ],
            ),
            const SizedBox(height: 9),
            Text(
              alert['title']?.toString() ?? 'Alerta operativa',
              style: const TextStyle(fontWeight: FontWeight.w800),
            ),
            const SizedBox(height: 3),
            Text(
              alert['message']?.toString() ?? '',
              style: const TextStyle(color: muted, height: 1.35),
            ),
            if (actions && active) ...[
              const SizedBox(height: 10),
              Wrap(
                spacing: 8,
                children: [
                  if (alert['acknowledged_at'] == null)
                    TextButton.icon(
                      onPressed: () => _run(
                        context,
                        () => store.acknowledge(alert['id'] as int),
                        'Alerta reconocida.',
                      ),
                      icon: const Icon(Icons.visibility_outlined),
                      label: const Text('Reconocer'),
                    ),
                  if (store.canResolve)
                    TextButton.icon(
                      onPressed: () => _run(
                        context,
                        () => store.resolve(alert['id'] as int),
                        'Alerta resuelta.',
                      ),
                      icon: const Icon(Icons.check_circle_outline),
                      label: const Text('Resolver'),
                    ),
                ],
              ),
            ],
          ],
        ),
      ),
    );
  }
}

class _LogTile extends StatelessWidget {
  const _LogTile({required this.log});

  final Map<String, dynamic> log;

  @override
  Widget build(BuildContext context) {
    return Card(
      margin: const EdgeInsets.only(bottom: 9),
      child: Padding(
        padding: const EdgeInsets.all(14),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Row(
              children: [
                const Icon(Icons.fact_check_outlined, color: emerald, size: 19),
                const SizedBox(width: 8),
                Expanded(
                  child: Text(
                    log['action_taken']?.toString() ?? 'Accion registrada',
                    style: const TextStyle(fontWeight: FontWeight.w800),
                  ),
                ),
              ],
            ),
            const SizedBox(height: 7),
            Text(
              log['notes']?.toString() ?? '',
              style: const TextStyle(color: muted, height: 1.35),
            ),
            const SizedBox(height: 7),
            Text(
              '${log['operator_name']}  |  ${_date(log['timestamp'])}',
              style: const TextStyle(color: muted, fontSize: 11),
            ),
          ],
        ),
      ),
    );
  }
}

class _ReadingChart extends StatelessWidget {
  const _ReadingChart({
    required this.readings,
    required this.keyName,
    required this.suffix,
  });

  final List<Map<String, dynamic>> readings;
  final String keyName;
  final String suffix;

  @override
  Widget build(BuildContext context) {
    final available = readings
        .where((reading) => reading[keyName] is num)
        .toList();
    if (available.isEmpty) {
      return const _Empty('No hay datos de esta variable en el periodo.');
    }
    final values = available.length > 28
        ? available.sublist(available.length - 28)
        : available;
    final spots = values.asMap().entries.map((entry) {
      return FlSpot(
        entry.key.toDouble(),
        (entry.value[keyName] as num).toDouble(),
      );
    }).toList();
    return Card(
      child: Padding(
        padding: const EdgeInsets.fromLTRB(10, 18, 16, 12),
        child: SizedBox(
          height: 190,
          child: LineChart(
            LineChartData(
              gridData: const FlGridData(show: true, drawVerticalLine: false),
              titlesData: const FlTitlesData(
                topTitles: AxisTitles(
                  sideTitles: SideTitles(showTitles: false),
                ),
                rightTitles: AxisTitles(
                  sideTitles: SideTitles(showTitles: false),
                ),
                bottomTitles: AxisTitles(
                  sideTitles: SideTitles(showTitles: false),
                ),
              ),
              borderData: FlBorderData(show: false),
              lineTouchData: LineTouchData(
                touchTooltipData: LineTouchTooltipData(
                  getTooltipItems: (items) => items
                      .map(
                        (item) => LineTooltipItem(
                          '${item.y.toStringAsFixed(1)}$suffix',
                          const TextStyle(color: Colors.white),
                        ),
                      )
                      .toList(),
                ),
              ),
              lineBarsData: [
                LineChartBarData(
                  spots: spots,
                  color: emerald,
                  barWidth: 3,
                  isCurved: true,
                  dotData: const FlDotData(show: false),
                  belowBarData: BarAreaData(
                    show: true,
                    color: emerald.withValues(alpha: .08),
                  ),
                ),
              ],
            ),
          ),
        ),
      ),
    );
  }
}

class _CalibrationStatus extends StatelessWidget {
  const _CalibrationStatus({required this.calibration});

  final Map<String, dynamic> calibration;

  @override
  Widget build(BuildContext context) {
    final version = calibration['calibration_version'];
    final responsible =
        calibration['calibrated_by_name']?.toString() ??
        'Responsable no registrado';
    return Card(
      margin: const EdgeInsets.only(bottom: 8),
      child: ListTile(
        leading: const Icon(Icons.verified_outlined, color: emerald),
        title: Text(
          calibration['variable_type']?.toString() ?? 'Variable calibrada',
          style: const TextStyle(fontWeight: FontWeight.w800),
        ),
        subtitle: Text(
          'Version ${version ?? '--'} | $responsible\n'
          '${_date(calibration['calibrated_at'])}',
        ),
      ),
    );
  }
}

class _StatusBadge extends StatelessWidget {
  const _StatusBadge({required this.value});

  final String value;

  @override
  Widget build(BuildContext context) {
    final config = switch (value) {
      'critical' => (danger, const Color(0xffffebe9), 'CRITICA'),
      'technical' => (
        const Color(0xff6b4a00),
        const Color(0xfffff5d6),
        'TECNICA',
      ),
      'resolved' => (emerald, const Color(0xffe8f7f0), 'RESUELTA'),
      _ => (const Color(0xff8a5b00), const Color(0xfffff6df), 'ALERTA'),
    };
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 4),
      decoration: BoxDecoration(
        color: config.$2,
        borderRadius: BorderRadius.circular(20),
      ),
      child: Text(
        config.$3,
        style: TextStyle(
          color: config.$1,
          fontSize: 9,
          fontWeight: FontWeight.w800,
          letterSpacing: .6,
        ),
      ),
    );
  }
}

class _OfflineBanner extends StatelessWidget {
  const _OfflineBanner();

  @override
  Widget build(BuildContext context) {
    return Container(
      color: const Color(0xfffff6df),
      padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 8),
      child: const Row(
        children: [
          Icon(Icons.cloud_off_outlined, size: 17, color: Color(0xff8a5b00)),
          SizedBox(width: 8),
          Expanded(
            child: Text(
              'Modo sin conexion: mostrando el ultimo estado guardado.',
              style: TextStyle(
                color: Color(0xff714d00),
                fontSize: 12,
                fontWeight: FontWeight.w600,
              ),
            ),
          ),
        ],
      ),
    );
  }
}

class _Empty extends StatelessWidget {
  const _Empty(this.text);

  final String text;

  @override
  Widget build(BuildContext context) {
    return Card(
      child: Padding(
        padding: const EdgeInsets.all(20),
        child: Row(
          children: [
            const Icon(Icons.inbox_outlined, color: muted),
            const SizedBox(width: 12),
            Expanded(
              child: Text(text, style: const TextStyle(color: muted)),
            ),
          ],
        ),
      ),
    );
  }
}

class _ActionCard extends StatelessWidget {
  const _ActionCard({
    required this.icon,
    required this.title,
    required this.text,
    required this.onTap,
  });

  final IconData icon;
  final String title;
  final String text;
  final VoidCallback onTap;

  @override
  Widget build(BuildContext context) {
    return Card(
      child: InkWell(
        borderRadius: BorderRadius.circular(12),
        onTap: onTap,
        child: Padding(
          padding: const EdgeInsets.all(15),
          child: Row(
            children: [
              Icon(icon, color: emerald, size: 28),
              const SizedBox(width: 13),
              Expanded(
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Text(
                      title,
                      style: const TextStyle(fontWeight: FontWeight.w800),
                    ),
                    const SizedBox(height: 3),
                    Text(
                      text,
                      style: const TextStyle(color: muted, height: 1.3),
                    ),
                  ],
                ),
              ),
              const Icon(Icons.chevron_right, color: muted),
            ],
          ),
        ),
      ),
    );
  }
}

class _Notice extends StatelessWidget {
  const _Notice({required this.text, this.danger = false});

  final String text;
  final bool danger;

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.all(11),
      decoration: BoxDecoration(
        color: danger ? const Color(0xffffebe9) : const Color(0xffe8f7f0),
        borderRadius: BorderRadius.circular(8),
      ),
      child: Text(
        text,
        style: TextStyle(color: danger ? dangerColor : emerald, height: 1.35),
      ),
    );
  }

  Color get dangerColor => const Color(0xff9d2018);
}

Future<void> _showLogForm(
  BuildContext context, {
  Map<String, dynamic>? initialUnit,
}) async {
  final store = context.read<AppStore>();
  if (store.units.isEmpty) return;
  var selected = initialUnit ?? store.units.first;
  var category = 'corrective_action';
  final action = TextEditingController(
    text: 'Se realizo inspeccion operativa del punto monitoreado.',
  );
  final operatorName = TextEditingController(
    text: store.me?['full_name']?.toString() ?? '',
  );
  final notes = TextEditingController();
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
            const _BlockTitle('Registrar accion operativa'),
            DropdownButtonFormField<Map<String, dynamic>>(
              initialValue: selected,
              decoration: const InputDecoration(labelText: 'Unidad'),
              items: store.units
                  .map(
                    (unit) => DropdownMenuItem(
                      value: unit,
                      child: Text(unit['name']),
                    ),
                  )
                  .toList(),
              onChanged: (value) =>
                  setSheetState(() => selected = value ?? selected),
            ),
            const SizedBox(height: 10),
            DropdownButtonFormField<String>(
              initialValue: category,
              decoration: const InputDecoration(labelText: 'Categoria'),
              items: const [
                DropdownMenuItem(
                  value: 'corrective_action',
                  child: Text('Accion correctiva'),
                ),
                DropdownMenuItem(
                  value: 'maintenance',
                  child: Text('Mantenimiento'),
                ),
                DropdownMenuItem(
                  value: 'inspection',
                  child: Text('Inspeccion'),
                ),
              ],
              onChanged: (value) =>
                  setSheetState(() => category = value ?? category),
            ),
            const SizedBox(height: 10),
            TextField(
              controller: action,
              decoration: const InputDecoration(labelText: 'Accion tomada'),
            ),
            const SizedBox(height: 10),
            TextField(
              controller: operatorName,
              decoration: const InputDecoration(labelText: 'Responsable'),
            ),
            const SizedBox(height: 10),
            TextField(
              controller: notes,
              decoration: const InputDecoration(labelText: 'Notas'),
              maxLines: 3,
            ),
            const SizedBox(height: 14),
            ElevatedButton(
              onPressed: () async {
                Navigator.pop(sheetContext);
                await _run(
                  context,
                  () => store.createLog(
                    storageUnitId: selected['id'] as int,
                    category: category,
                    action: action.text,
                    operatorName: operatorName.text,
                    notes: notes.text,
                    deviceId:
                        store.deviceFor(selected['id'] as int)?['id'] as int?,
                  ),
                  'Accion registrada.',
                );
              },
              child: const Text('Guardar en bitacora'),
            ),
          ],
        ),
      ),
    ),
  );
}

Future<void> _showInstallation(BuildContext context) async {
  await Navigator.of(context).push(
    MaterialPageRoute(
      builder: (_) => const PilotOperationsScreen(initialTab: 1),
    ),
  );
}

Future<void> _downloadPdf(
  BuildContext context,
  Map<String, dynamic> unit,
) async {
  await _run(context, () async {
    await context.read<AppStore>().downloadWeeklyPdf(unit);
  }, 'Reporte descargado.');
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

void _toast(BuildContext context, String message) {
  ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text(message)));
}

Map<String, dynamic> _newest(List<Map<String, dynamic>> items) {
  return (items.toList()..sort(
        (a, b) => _parse(b['timestamp']).compareTo(_parse(a['timestamp'])),
      ))
      .first;
}

DateTime _parse(dynamic value) =>
    DateTime.tryParse(value?.toString() ?? '') ??
    DateTime.fromMillisecondsSinceEpoch(0);
String _date(dynamic value) => formatDate.format(_parse(value).toLocal());
String _num(dynamic value) => value is num ? value.toStringAsFixed(1) : '--';
String _capacity(Map<String, dynamic> unit) => unit['capacity_tons'] == null
    ? 'Capacidad no registrada'
    : '${_num(unit['capacity_tons'])} t';
String _surface(Map<String, dynamic> unit) => unit['surface_hectares'] == null
    ? 'Superficie no registrada'
    : '${_num(unit['surface_hectares'])} ha';
String _operationType(Map<String, dynamic> unit) {
  final explicit = unit['operation_type']?.toString().toLowerCase();
  final legacy = unit['unit_type']?.toString().toLowerCase();
  return explicit == 'field' ||
          const {'field', 'campo', 'parcela', 'lote'}.contains(legacy)
      ? 'field'
      : 'storage';
}

String _deviceProfile(Map<String, dynamic>? device) =>
    device?['device_type']?.toString().toLowerCase() == 'field_sensor'
    ? 'field_sensor'
    : 'silo_sensor';

String _batteryState(dynamic value) {
  if (value is! num) return 'Sin dato';
  if (value < 3.5) return 'Baja';
  if (value < 3.75) return 'Atencion';
  return 'Adecuada';
}

String _roleLabel(String role) {
  return switch (role) {
    'admin' => 'ADMINISTRACION AGROESCUDO',
    'technician' => 'OPERACION TECNICA',
    _ => 'ACCESO CLIENTE',
  };
}
