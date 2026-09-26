import type { CanonicalMetricSeries, DashboardMetric, MetricSeriesSummary } from "@/lib/types";
import { circularMeanDegrees, formatWindDirection, windDirectionPresentation } from "./wind-direction";

export const RAIN_GAUGE_METRIC_PRIORITY = [
  "RAIN_DELTA_MM",
  "AMBIENT_TEMPERATURE_C",
  "AMBIENT_RELATIVE_HUMIDITY_PCT",
  "WIND_SPEED_KMH",
  "WIND_DIRECTION_DEG",
  "BATTERY_PERCENT"
] as const;

export type RainGaugeMetricCode = typeof RAIN_GAUGE_METRIC_PRIORITY[number];
export type RainGaugePeriod = "1h" | "24h" | "7d" | "30d";

export const PERIODS: Array<{ value: RainGaugePeriod; label: string }> = [
  { value: "1h", label: "1 hora" },
  { value: "24h", label: "24 horas" },
  { value: "7d", label: "7 días" },
  { value: "30d", label: "30 días" }
];

export const METRIC_UI: Record<RainGaugeMetricCode, { label: string; color: string }> = {
  RAIN_DELTA_MM: { label: "Lluvia", color: "#0284c7" },
  AMBIENT_TEMPERATURE_C: { label: "Temperatura", color: "#2563eb" },
  AMBIENT_RELATIVE_HUMIDITY_PCT: { label: "Humedad", color: "#d97706" },
  WIND_SPEED_KMH: { label: "Velocidad del viento", color: "#0f766e" },
  WIND_DIRECTION_DEG: { label: "Dirección del viento", color: "#7c3aed" },
  BATTERY_PERCENT: { label: "Batería", color: "#475569" }
};

export function supportedRainGaugeMetrics(metrics: DashboardMetric[]) {
  const allowed = new Set<string>(RAIN_GAUGE_METRIC_PRIORITY);
  return metrics
    .filter((metric) => allowed.has(metric.metric_code) && metric.chart_enabled)
    .sort((left, right) =>
      RAIN_GAUGE_METRIC_PRIORITY.indexOf(left.metric_code as RainGaugeMetricCode)
      - RAIN_GAUGE_METRIC_PRIORITY.indexOf(right.metric_code as RainGaugeMetricCode)
    );
}

export function resolveHistorySelection(
  metrics: DashboardMetric[],
  requestedMetric: string | null,
  requestedPeriod: string | null
) {
  const available = supportedRainGaugeMetrics(metrics);
  const metric = available.find((item) => item.metric_code === requestedMetric) ?? available[0] ?? null;
  const period = PERIODS.some((item) => item.value === requestedPeriod) ? requestedPeriod as RainGaugePeriod : "24h";
  return { metric, period };
}

export function detailQueryPath(deviceId: number, metricCode: string, period: RainGaugePeriod) {
  const params = new URLSearchParams({ variable: metricCode, period });
  return `/pluviometria/pluviometros/${deviceId}?${params}`;
}

export function periodRequest(period: RainGaugePeriod, now = Date.now()) {
  const hours = period === "1h" ? 1 : period === "24h" ? 24 : period === "7d" ? 24 * 7 : 24 * 30;
  const resolution = period === "1h" ? "raw" : period === "24h" ? "15m" : period === "7d" ? "1h" : "1d";
  return {
    from: new Date(now - hours * 60 * 60 * 1000).toISOString(),
    to: new Date(now).toISOString(),
    resolution: resolution as "raw" | "15m" | "1h" | "1d",
    limit: 5000
  };
}

export type HistoryStat = { label: string; value: string };

function format(value: number | null, decimals: number, unit: string) {
  return value == null ? "—" : `${value.toFixed(decimals)}${unit}`;
}

export function displayUnit(canonicalUnit: string) {
  return ({ degC: " °C", percent: "%", "km/h": " km/h", degree: "°", mm: " mm" } as Record<string, string>)[canonicalUnit] ?? ` ${canonicalUnit}`;
}

export function historyStats(metric: DashboardMetric, series: CanonicalMetricSeries): HistoryStat[] {
  const summary: MetricSeriesSummary = series.summary;
  const unit = displayUnit(metric.canonical_unit);
  const decimals = metric.default_decimals;
  if (metric.metric_code === "RAIN_DELTA_MM") {
    const accumulated = series.points.reduce((sum, point) => sum + (point.value ?? 0), 0);
    const values = series.points.flatMap((point) => point.value == null ? [] : [point.value]);
    return [
      { label: "Acumulado", value: values.length ? format(accumulated, decimals, unit) : "—" },
      { label: "Máx. intervalo", value: values.length ? format(Math.max(...values), decimals, unit) : "—" },
      { label: "Lecturas", value: String(summary.sample_count) }
    ];
  }
  if (metric.metric_code === "WIND_SPEED_KMH") {
    return [
      { label: "Promedio", value: format(summary.average, decimals, unit) },
      { label: "Máximo", value: format(summary.maximum, decimals, unit) },
      { label: "Lecturas", value: String(summary.sample_count) }
    ];
  }
  if (metric.metric_code === "BATTERY_PERCENT") {
    return [
      { label: "Último", value: format(summary.current, decimals, unit) },
      { label: "Mínimo", value: format(summary.minimum, decimals, unit) },
      { label: "Lecturas", value: String(summary.sample_count) }
    ];
  }
  if (metric.metric_code === "WIND_DIRECTION_DEG") {
    const predominant = circularMeanDegrees(series.points);
    const current = windDirectionPresentation(summary.current);
    return [
      { label: "Dirección predominante", value: formatWindDirection(predominant, decimals) },
      { label: "Dirección actual", value: formatWindDirection(summary.current, decimals) },
      { label: "Se dirige hacia", value: current?.to ?? "—" }
    ];
  }
  return [
    { label: "Mínimo", value: format(summary.minimum, decimals, unit) },
    { label: "Promedio", value: format(summary.average, decimals, unit) },
    { label: "Máximo", value: format(summary.maximum, decimals, unit) }
  ];
}

export function periodLabel(period: RainGaugePeriod) {
  return PERIODS.find((item) => item.value === period)?.label ?? period;
}

export function hasRecordedZero(series: CanonicalMetricSeries) {
  return series.points.some((point) => point.value === 0);
}
