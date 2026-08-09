import 'package:fl_chart/fl_chart.dart';
import 'package:flutter/material.dart';
import 'package:intl/intl.dart';

const _deepGreen = Color(0xff023c2e);
const _emerald = Color(0xff0c7654);
const _gold = Color(0xffd99a00);
const _ivory = Color(0xfffbfaf6);
const _graphite = Color(0xff1b2622);
const _muted = Color(0xff69736f);
const _danger = Color(0xffb42318);

class AgroMetricChart extends StatelessWidget {
  const AgroMetricChart({
    super.key,
    required this.metric,
    required this.series,
    required this.context,
    required this.thresholds,
  });

  final Map<String, dynamic> metric;
  final Map<String, dynamic> series;
  final Map<String, dynamic> context;
  final Map<String, dynamic> thresholds;

  @override
  Widget build(BuildContext context) {
    final code = metric['metric_code']?.toString() ?? '';
    final props = AgroChartProps(metric, series, this.context, thresholds);
    if (code == 'GRAIN_TEMPERATURE_C') {
      return AgroTemperatureChart(props: props);
    }
    if (code == 'AMBIENT_RELATIVE_HUMIDITY_PCT') {
      return AgroHumidityChart(props: props);
    }
    if (code == 'LEVEL_PERCENT') return AgroLevelChart(props: props);
    return AgroTrendChart(props: props);
  }
}

class AgroLegacyReadingChart extends StatelessWidget {
  const AgroLegacyReadingChart({
    super.key,
    required this.readings,
    required this.keyName,
    required this.title,
    required this.unit,
  });

  final List<Map<String, dynamic>> readings;
  final String keyName;
  final String title;
  final String unit;

  @override
  Widget build(BuildContext context) {
    final points = readings
        .where((reading) => reading[keyName] is num)
        .map(
          (reading) => {
            'sampled_at': reading['timestamp'],
            'value': reading[keyName],
            'sample_count': 1,
          },
        )
        .toList();
    final metric = <String, dynamic>{
      'metric_code': keyName == 'grain_temperature'
          ? 'GRAIN_TEMPERATURE_C'
          : keyName.toUpperCase(),
      'display_name': title,
      'channel_key': 'legacy',
      'canonical_unit': unit == '%'
          ? 'percent'
          : unit.trim() == 'C'
          ? 'degC'
          : unit.trim(),
    };
    return AgroTrendChart(
      props: AgroChartProps(
        metric,
        {'points': points},
        const {'events': [], 'actions': []},
        const {},
        title: title,
        eyebrow: 'SERIE HISTORICA',
      ),
    );
  }
}

class AgroTemperatureChart extends StatelessWidget {
  const AgroTemperatureChart({super.key, required this.props});
  final AgroChartProps props;

  @override
  Widget build(BuildContext context) => AgroTrendChart(
    props: props.copyWith(
      title: 'Temperatura del grano',
      eyebrow: 'CONDICION TERMICA',
      color: _deepGreen,
      primary: true,
    ),
  );
}

class AgroHumidityChart extends StatelessWidget {
  const AgroHumidityChart({super.key, required this.props});
  final AgroChartProps props;

  @override
  Widget build(BuildContext context) => AgroTrendChart(
    props: props.copyWith(
      title: 'Humedad ambiente',
      eyebrow: 'CONDICION AMBIENTAL',
      color: _gold,
      percentage: true,
    ),
  );
}

class AgroLevelChart extends StatelessWidget {
  const AgroLevelChart({super.key, required this.props});
  final AgroChartProps props;

  @override
  Widget build(BuildContext context) {
    final current = props.summary['current'] as num?;
    final percent = (current?.toDouble() ?? 0).clamp(0, 100).toDouble();
    final condition = _condition(current?.toDouble(), props.thresholds);
    return Column(
      children: [
        Card(
          color: _ivory,
          child: Padding(
            padding: const EdgeInsets.all(18),
            child: Row(
              children: [
                SizedBox(
                  width: 108,
                  height: 154,
                  child: CustomPaint(
                    painter: _SiloPainter(
                      percent: percent,
                      color: condition.color,
                    ),
                  ),
                ),
                const SizedBox(width: 18),
                Expanded(
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      const Text(
                        'GEMELO OPERATIVO',
                        style: TextStyle(
                          color: _emerald,
                          fontSize: 10,
                          fontWeight: FontWeight.w900,
                          letterSpacing: 1.2,
                        ),
                      ),
                      const SizedBox(height: 5),
                      const Text(
                        'Nivel del silo',
                        style: TextStyle(
                          color: _graphite,
                          fontSize: 19,
                          fontWeight: FontWeight.w900,
                        ),
                      ),
                      const SizedBox(height: 10),
                      Text(
                        current == null
                            ? 'Sin dato'
                            : '${current.toStringAsFixed(1)}%',
                        style: const TextStyle(
                          color: _graphite,
                          fontSize: 32,
                          fontWeight: FontWeight.w900,
                        ),
                      ),
                      Text(
                        condition.label,
                        style: TextStyle(
                          color: condition.color,
                          fontSize: 12,
                          fontWeight: FontWeight.w800,
                        ),
                      ),
                      const SizedBox(height: 10),
                      Text(
                        _changeLabel(props.summary['change'] as num?, ' pts'),
                        style: const TextStyle(color: _muted, fontSize: 12),
                      ),
                      const SizedBox(height: 4),
                      const Text(
                        'Altura ocupada estimada; no representa toneladas.',
                        style: TextStyle(
                          color: _muted,
                          fontSize: 10,
                          height: 1.35,
                        ),
                      ),
                    ],
                  ),
                ),
              ],
            ),
          ),
        ),
        const SizedBox(height: 10),
        AgroTrendChart(
          props: props.copyWith(
            title: 'Tendencia del nivel',
            eyebrow: 'EVOLUCION DEL PERIODO',
            color: _emerald,
            percentage: true,
            compact: true,
          ),
        ),
      ],
    );
  }
}

class AgroTrendChart extends StatelessWidget {
  const AgroTrendChart({super.key, required this.props});
  final AgroChartProps props;

  @override
  Widget build(BuildContext context) {
    final points = props.points;
    if (points.isEmpty) {
      return const Card(
        child: Padding(
          padding: EdgeInsets.all(22),
          child: Text(
            'Sin lecturas validas para esta variable.',
            style: TextStyle(color: _muted),
          ),
        ),
      );
    }
    final spots = _lineSpots(points, props.gaps);
    final values = points
        .map((point) => (point['value'] as num).toDouble())
        .toList();
    final thresholds = props.thresholds.values
        .whereType<num>()
        .map((value) => value.toDouble())
        .toList();
    final allValues = [...values, ...thresholds];
    var minY = props.percentage
        ? 0.0
        : allValues.reduce((a, b) => a < b ? a : b);
    var maxY = props.percentage
        ? 100.0
        : allValues.reduce((a, b) => a > b ? a : b);
    if (!props.percentage) {
      final padding = ((maxY - minY) * .15).clamp(.5, double.infinity);
      minY -= padding;
      maxY += padding;
    }
    final minX = points.first['_x'] as double;
    final maxX = points.last['_x'] as double;
    final current = props.summary['current'] as num?;
    final condition = _condition(current?.toDouble(), props.thresholds);
    final markerBars = _markerBars(points, props.events, props.actions);
    return Card(
      child: Padding(
        padding: const EdgeInsets.fromLTRB(16, 17, 16, 14),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text(
              props.resolvedEyebrow,
              style: const TextStyle(
                color: _emerald,
                fontSize: 10,
                fontWeight: FontWeight.w900,
                letterSpacing: 1.1,
              ),
            ),
            const SizedBox(height: 4),
            Row(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Expanded(
                  child: Text(
                    props.resolvedTitle,
                    style: TextStyle(
                      color: _graphite,
                      fontSize: props.primary ? 20 : 17,
                      fontWeight: FontWeight.w900,
                    ),
                  ),
                ),
                Column(
                  crossAxisAlignment: CrossAxisAlignment.end,
                  children: [
                    Text(
                      _value(current, props.unit),
                      style: TextStyle(
                        color: _graphite,
                        fontSize: props.primary ? 25 : 21,
                        fontWeight: FontWeight.w900,
                      ),
                    ),
                    Text(
                      condition.label,
                      style: TextStyle(
                        color: condition.color,
                        fontSize: 10,
                        fontWeight: FontWeight.w800,
                      ),
                    ),
                  ],
                ),
              ],
            ),
            const SizedBox(height: 16),
            SizedBox(
              height: props.primary
                  ? 260
                  : props.compact
                  ? 170
                  : 210,
              child: LineChart(
                LineChartData(
                  minX: minX,
                  maxX: maxX == minX ? minX + 1 : maxX,
                  minY: minY,
                  maxY: maxY,
                  rangeAnnotations: _thresholdRanges(
                    props.thresholds,
                    minY,
                    maxY,
                  ),
                  extraLinesData: _thresholdLines(props.thresholds),
                  gridData: const FlGridData(
                    show: true,
                    drawVerticalLine: false,
                    horizontalInterval: null,
                  ),
                  borderData: FlBorderData(show: false),
                  titlesData: FlTitlesData(
                    topTitles: const AxisTitles(
                      sideTitles: SideTitles(showTitles: false),
                    ),
                    rightTitles: const AxisTitles(
                      sideTitles: SideTitles(showTitles: false),
                    ),
                    leftTitles: const AxisTitles(
                      sideTitles: SideTitles(
                        showTitles: true,
                        reservedSize: 38,
                        interval: null,
                      ),
                    ),
                    bottomTitles: AxisTitles(
                      sideTitles: SideTitles(
                        showTitles: true,
                        reservedSize: 26,
                        interval: ((maxX - minX) / 3).clamp(1, double.infinity),
                        getTitlesWidget: (value, meta) => Padding(
                          padding: const EdgeInsets.only(top: 7),
                          child: Text(
                            _axisDate(value),
                            style: const TextStyle(fontSize: 9, color: _muted),
                          ),
                        ),
                      ),
                    ),
                  ),
                  lineTouchData: LineTouchData(
                    touchTooltipData: LineTouchTooltipData(
                      tooltipBorderRadius: BorderRadius.circular(12),
                      tooltipPadding: const EdgeInsets.symmetric(
                        horizontal: 12,
                        vertical: 9,
                      ),
                      getTooltipColor: (_) => _deepGreen,
                      fitInsideHorizontally: true,
                      getTooltipItems: (items) => items
                          .map(
                            (item) => item.barIndex == 0
                                ? LineTooltipItem(
                                    '${DateFormat('dd MMM, HH:mm').format(DateTime.fromMillisecondsSinceEpoch((item.x * 1000).round()))}\n${item.y.toStringAsFixed(1)}${props.unit}',
                                    const TextStyle(
                                      color: Colors.white,
                                      fontSize: 11,
                                      fontWeight: FontWeight.w700,
                                    ),
                                  )
                                : null,
                          )
                          .toList(),
                    ),
                  ),
                  lineBarsData: [
                    LineChartBarData(
                      spots: spots,
                      color: props.color,
                      barWidth: props.primary ? 3.2 : 2.6,
                      isCurved: true,
                      dotData: const FlDotData(show: false),
                      belowBarData: BarAreaData(
                        show: true,
                        color: props.color.withValues(alpha: .08),
                      ),
                    ),
                    ...markerBars,
                  ],
                ),
              ),
            ),
            const SizedBox(height: 12),
            Row(
              children: [
                _Stat(
                  label: 'MIN',
                  value: _value(props.summary['minimum'] as num?, props.unit),
                ),
                _Stat(
                  label: 'PROM',
                  value: _value(props.summary['average'] as num?, props.unit),
                ),
                _Stat(
                  label: 'MAX',
                  value: _value(props.summary['maximum'] as num?, props.unit),
                ),
                _Stat(
                  label: 'CAMBIO',
                  value: _changeLabel(
                    props.summary['change'] as num?,
                    props.unit,
                  ),
                ),
              ],
            ),
            if (props.events.isNotEmpty ||
                props.actions.isNotEmpty ||
                props.gaps.isNotEmpty) ...[
              const Divider(height: 22),
              Wrap(
                spacing: 7,
                runSpacing: 7,
                children: [
                  ...props.events
                      .take(3)
                      .map(
                        (event) => _Annotation(
                          label: event['title']?.toString() ?? 'Alerta',
                          color: event['severity'] == 'critical'
                              ? _danger
                              : _gold,
                        ),
                      ),
                  ...props.actions
                      .take(3)
                      .map(
                        (action) => _Annotation(
                          label: action['title']?.toString() ?? 'Accion',
                          color: _emerald,
                        ),
                      ),
                  ...props.gaps
                      .take(2)
                      .map(
                        (gap) => _Annotation(
                          label:
                              'Sin datos ${_gapDuration(gap['duration_seconds'] as num?)}',
                          color: _muted,
                        ),
                      ),
                ],
              ),
            ],
            if (props.thresholds.values.whereType<num>().isEmpty) ...[
              const Divider(height: 22),
              const Text(
                'Umbrales no configurados. Se muestra solo la evidencia recibida.',
                style: TextStyle(
                  color: _muted,
                  fontSize: 11,
                  fontWeight: FontWeight.w600,
                ),
              ),
            ],
          ],
        ),
      ),
    );
  }
}

class AgroChartProps {
  AgroChartProps(
    this.metric,
    this.series,
    this.context,
    this.thresholds, {
    this.title,
    this.eyebrow,
    this.color = _emerald,
    this.primary = false,
    this.compact = false,
    this.percentage = false,
  });
  final Map<String, dynamic> metric;
  final Map<String, dynamic> series;
  final Map<String, dynamic> context;
  final Map<String, dynamic> thresholds;
  final String? title;
  final String? eyebrow;
  final Color color;
  final bool primary;
  final bool compact;
  final bool percentage;

  List<Map<String, dynamic>> get points =>
      (series['points'] as List? ?? const [])
          .map((item) {
            final point = Map<String, dynamic>.from(item as Map);
            point['_x'] =
                (DateTime.tryParse(
                      point['sampled_at']?.toString() ?? '',
                    )?.millisecondsSinceEpoch.toDouble() ??
                    0) /
                1000;
            return point;
          })
          .where((point) => point['value'] is num)
          .toList()
        ..sort((a, b) => (a['_x'] as double).compareTo(b['_x'] as double));
  Map<String, dynamic> get summary => Map<String, dynamic>.from(
    series['summary'] as Map? ?? _fallbackSummary(points),
  );
  List<Map<String, dynamic>> get gaps => (series['gaps'] as List? ?? const [])
      .map((item) => Map<String, dynamic>.from(item as Map))
      .toList();
  String get unit => _unit(metric['canonical_unit']?.toString());
  String get resolvedTitle =>
      title ??
      metric['display_name_override']?.toString() ??
      metric['display_name']?.toString() ??
      'Metrica';
  String get resolvedEyebrow =>
      eyebrow ??
      metric['channel_key']?.toString().replaceAll('_', ' ').toUpperCase() ??
      'SENSOR';
  List<Map<String, dynamic>> get events =>
      (context['events'] as List? ?? const [])
          .map((item) => Map<String, dynamic>.from(item as Map))
          .where((item) => item['metric_code'] == metric['metric_code'])
          .toList();
  List<Map<String, dynamic>> get actions {
    final ids = events.map((event) => event['id']).toSet();
    return (context['actions'] as List? ?? const [])
        .map((item) => Map<String, dynamic>.from(item as Map))
        .where(
          (item) => item['alert_id'] != null
              ? ids.contains(item['alert_id'])
              : metric['metric_code'] == 'GRAIN_TEMPERATURE_C',
        )
        .toList();
  }

  AgroChartProps copyWith({
    String? title,
    String? eyebrow,
    Color? color,
    bool? primary,
    bool? compact,
    bool? percentage,
  }) => AgroChartProps(
    metric,
    series,
    context,
    thresholds,
    title: title ?? this.title,
    eyebrow: eyebrow ?? this.eyebrow,
    color: color ?? this.color,
    primary: primary ?? this.primary,
    compact: compact ?? this.compact,
    percentage: percentage ?? this.percentage,
  );
}

List<FlSpot> _lineSpots(
  List<Map<String, dynamic>> points,
  List<Map<String, dynamic>> gaps,
) {
  final result = <FlSpot>[];
  for (var index = 0; index < points.length; index++) {
    if (index > 0) {
      final previous = points[index - 1]['_x'] as double;
      final current = points[index]['_x'] as double;
      final crossesGap = gaps.any((gap) {
        final fromValue = DateTime.tryParse(
          gap['from']?.toString() ?? '',
        )?.millisecondsSinceEpoch.toDouble();
        final toValue = DateTime.tryParse(
          gap['to']?.toString() ?? '',
        )?.millisecondsSinceEpoch.toDouble();
        final from = fromValue == null ? null : fromValue / 1000;
        final to = toValue == null ? null : toValue / 1000;
        return from != null && to != null && previous <= from && current >= to;
      });
      if (crossesGap) result.add(FlSpot.nullSpot);
    }
    result.add(
      FlSpot(
        points[index]['_x'] as double,
        (points[index]['value'] as num).toDouble(),
      ),
    );
  }
  return result;
}

List<LineChartBarData> _markerBars(
  List<Map<String, dynamic>> points,
  List<Map<String, dynamic>> events,
  List<Map<String, dynamic>> actions,
) {
  Map<String, dynamic>? nearest(String timestamp) {
    final value = DateTime.tryParse(
      timestamp,
    )?.millisecondsSinceEpoch.toDouble();
    final at = value == null ? null : value / 1000;
    if (at == null || points.isEmpty) return null;
    return points.reduce(
      (best, point) =>
          ((point['_x'] as double) - at).abs() <
              ((best['_x'] as double) - at).abs()
          ? point
          : best,
    );
  }

  final markers = <({double x, double y, Color color})>[];
  for (final event in events) {
    final point = nearest(event['timestamp']?.toString() ?? '');
    if (point != null) {
      markers.add((
        x: point['_x'] as double,
        y:
            (event['observed_value'] as num?)?.toDouble() ??
            (point['value'] as num).toDouble(),
        color: event['severity'] == 'critical' ? _danger : _gold,
      ));
    }
  }
  for (final action in actions) {
    final point = nearest(action['timestamp']?.toString() ?? '');
    if (point != null) {
      markers.add((
        x: point['_x'] as double,
        y: (point['value'] as num).toDouble(),
        color: _emerald,
      ));
    }
  }
  return markers
      .map(
        (marker) => LineChartBarData(
          spots: [FlSpot(marker.x, marker.y)],
          barWidth: 0,
          color: Colors.transparent,
          dotData: FlDotData(
            show: true,
            getDotPainter: (spot, percent, barData, index) =>
                FlDotCirclePainter(
                  radius: 5,
                  color: marker.color,
                  strokeWidth: 2,
                  strokeColor: Colors.white,
                ),
          ),
        ),
      )
      .toList();
}

RangeAnnotations _thresholdRanges(
  Map<String, dynamic> values,
  double low,
  double high,
) {
  final max = (values['max'] as num?)?.toDouble();
  final critical = (values['criticalMax'] as num?)?.toDouble();
  final min = (values['min'] as num?)?.toDouble();
  return RangeAnnotations(
    horizontalRangeAnnotations: [
      if (max != null)
        HorizontalRangeAnnotation(
          y1: max,
          y2: critical ?? high,
          color: _gold.withValues(alpha: .07),
        ),
      if (critical != null)
        HorizontalRangeAnnotation(
          y1: critical,
          y2: high,
          color: _danger.withValues(alpha: .07),
        ),
      if (min != null)
        HorizontalRangeAnnotation(
          y1: low,
          y2: min,
          color: _gold.withValues(alpha: .07),
        ),
    ],
  );
}

ExtraLinesData _thresholdLines(Map<String, dynamic> values) => ExtraLinesData(
  horizontalLines: [
    if (values['min'] is num)
      HorizontalLine(
        y: (values['min'] as num).toDouble(),
        color: _gold,
        strokeWidth: 1,
        dashArray: [5, 5],
      ),
    if (values['max'] is num)
      HorizontalLine(
        y: (values['max'] as num).toDouble(),
        color: _gold,
        strokeWidth: 1,
        dashArray: [5, 5],
      ),
    if (values['criticalMax'] is num)
      HorizontalLine(
        y: (values['criticalMax'] as num).toDouble(),
        color: _danger,
        strokeWidth: 1,
        dashArray: [5, 5],
      ),
  ],
);

Map<String, dynamic> _fallbackSummary(List<Map<String, dynamic>> points) {
  final values = points
      .map((point) => (point['value'] as num).toDouble())
      .toList();
  if (values.isEmpty) return const {};
  return {
    'current': values.last,
    'initial': values.first,
    'minimum': values.reduce((a, b) => a < b ? a : b),
    'maximum': values.reduce((a, b) => a > b ? a : b),
    'average': values.reduce((a, b) => a + b) / values.length,
    'change': values.last - values.first,
  };
}

class _Stat extends StatelessWidget {
  const _Stat({required this.label, required this.value});
  final String label;
  final String value;
  @override
  Widget build(BuildContext context) => Expanded(
    child: Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Text(
          label,
          style: const TextStyle(
            color: _muted,
            fontSize: 9,
            fontWeight: FontWeight.w800,
          ),
        ),
        const SizedBox(height: 3),
        Text(
          value,
          style: const TextStyle(
            color: _graphite,
            fontSize: 12,
            fontWeight: FontWeight.w900,
          ),
        ),
      ],
    ),
  );
}

class _Annotation extends StatelessWidget {
  const _Annotation({required this.label, required this.color});
  final String label;
  final Color color;
  @override
  Widget build(BuildContext context) => Container(
    padding: const EdgeInsets.symmetric(horizontal: 9, vertical: 6),
    decoration: BoxDecoration(
      color: color.withValues(alpha: .09),
      borderRadius: BorderRadius.circular(7),
    ),
    child: Row(
      mainAxisSize: MainAxisSize.min,
      children: [
        Container(
          width: 7,
          height: 7,
          decoration: BoxDecoration(color: color, shape: BoxShape.circle),
        ),
        const SizedBox(width: 6),
        Flexible(
          child: Text(
            label,
            style: TextStyle(
              color: color,
              fontSize: 10,
              fontWeight: FontWeight.w800,
            ),
          ),
        ),
      ],
    ),
  );
}

class _SiloPainter extends CustomPainter {
  _SiloPainter({required this.percent, required this.color});
  final double percent;
  final Color color;
  @override
  void paint(Canvas canvas, Size size) {
    final path = Path()
      ..moveTo(size.width * .16, size.height * .22)
      ..lineTo(size.width * .5, 0)
      ..lineTo(size.width * .84, size.height * .22)
      ..lineTo(size.width * .84, size.height * .78)
      ..lineTo(size.width * .68, size.height)
      ..lineTo(size.width * .32, size.height)
      ..lineTo(size.width * .16, size.height * .78)
      ..close();
    canvas.save();
    canvas.clipPath(path);
    canvas.drawRect(
      Offset.zero & size,
      Paint()..color = const Color(0xffeef5f1),
    );
    final fillTop = size.height * (1 - percent / 100);
    canvas.drawRect(
      Rect.fromLTRB(0, fillTop, size.width, size.height),
      Paint()..color = color,
    );
    canvas.restore();
    canvas.drawPath(
      path,
      Paint()
        ..color = _deepGreen
        ..style = PaintingStyle.stroke
        ..strokeWidth = 4
        ..strokeJoin = StrokeJoin.round,
    );
  }

  @override
  bool shouldRepaint(covariant _SiloPainter oldDelegate) =>
      oldDelegate.percent != percent || oldDelegate.color != color;
}

({String label, Color color}) _condition(
  double? value,
  Map<String, dynamic> thresholds,
) {
  if (value == null) return (label: 'Sin dato', color: _muted);
  final critical = (thresholds['criticalMax'] as num?)?.toDouble();
  final max = (thresholds['max'] as num?)?.toDouble();
  final min = (thresholds['min'] as num?)?.toDouble();
  if (critical != null && value >= critical) {
    return (label: 'Critico', color: _danger);
  }
  if ((max != null && value >= max) || (min != null && value <= min)) {
    return (label: 'Atencion', color: _gold);
  }
  return (label: 'Normal', color: _emerald);
}

String _unit(String? unit) => switch (unit) {
  'degC' => ' C',
  'percent' => '%',
  'mV' => ' mV',
  'mm' => ' mm',
  _ => unit == null ? '' : ' $unit',
};
String _value(num? value, String unit) =>
    value == null ? 'Sin dato' : '${value.toStringAsFixed(1)}$unit';
String _changeLabel(num? value, String unit) => value == null
    ? 'Sin dato'
    : '${value > 0 ? '+' : ''}${value.toStringAsFixed(1)}$unit';
String _axisDate(double seconds) => DateFormat(
  'dd MMM',
).format(DateTime.fromMillisecondsSinceEpoch((seconds * 1000).round()));
String _gapDuration(num? seconds) => seconds == null
    ? ''
    : seconds >= 3600
    ? '${(seconds / 3600).toStringAsFixed(1)} h'
    : '${(seconds / 60).round()} min';
