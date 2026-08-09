"use client";

import type {
  CanonicalMetricSeries,
  DashboardMetric,
  DeviceChartAction,
  DeviceChartEvent
} from "@/lib/types";
import {
  AgroHumidityChart,
  AgroLevelChart,
  AgroTemperatureChart,
  AgroTrendChart,
  summarizePoints,
  type AgroChartInputPoint,
  type AgroChartThresholds
} from "@/components/charts";

const COLORS: Record<string, string> = {
  GRAIN_TEMPERATURE_C: "#064f3b",
  AMBIENT_TEMPERATURE_C: "#2563eb",
  AMBIENT_RELATIVE_HUMIDITY_PCT: "#d99a00",
  SOIL_MOISTURE_PCT: "#0c7654",
  SOIL_MOISTURE_RAW: "#69736f",
  LEVEL_DISTANCE_MM: "#0f766e",
  LEVEL_PERCENT: "#0c7654",
  BATTERY_VOLTAGE_MV: "#475569"
};

function displayUnit(unit: string) {
  return ({ degC: " °C", percent: "%", mV: " mV", mm: " mm", ADC_RAW: "" } as Record<string, string>)[unit] ?? ` ${unit}`;
}

export function MetricChart({
  metric,
  series,
  thresholds = {},
  events = [],
  actions = [],
  periodLabel,
  resolutionLabel,
  levelDistanceCm,
  calibrationStatus
}: {
  metric: DashboardMetric;
  series: CanonicalMetricSeries;
  thresholds?: AgroChartThresholds;
  events?: DeviceChartEvent[];
  actions?: DeviceChartAction[];
  periodLabel?: string;
  resolutionLabel?: string;
  levelDistanceCm?: number | null;
  calibrationStatus?: "configured" | "pending" | "not_applicable";
}) {
  const points: AgroChartInputPoint[] = series.points.map((point) => ({
    timestamp: point.sampled_at,
    value: point.value,
    bucketMin: point.bucket_min,
    bucketMax: point.bucket_max,
    sampleCount: point.sample_count
  }));
  const summary = series.summary ?? summarizePoints(points);
  const shared = {
    points,
    summary,
    gaps: series.gaps ?? [],
    events,
    actions,
    thresholds,
    unit: displayUnit(metric.canonical_unit),
    decimals: metric.default_decimals,
    periodLabel,
    resolutionLabel
  };
  const content = metric.metric_code === "GRAIN_TEMPERATURE_C"
    ? <AgroTemperatureChart {...shared} />
    : metric.metric_code === "AMBIENT_RELATIVE_HUMIDITY_PCT"
      ? <AgroHumidityChart {...shared} />
      : metric.metric_code === "LEVEL_PERCENT"
        ? <AgroLevelChart {...shared} distanceCm={levelDistanceCm} updatedAt={series.period?.to} calibrationStatus={calibrationStatus} />
        : (
          <AgroTrendChart
            {...shared}
            title={metric.display_name_override || metric.display_name}
            eyebrow={metric.channel_key.replaceAll("_", " ")}
            description={metric.description}
            color={COLORS[metric.metric_code] ?? "#0c7654"}
            percentage={metric.canonical_unit === "percent"}
            variant="secondary"
          />
        );

  return (
    <div className={metric.metric_code === "GRAIN_TEMPERATURE_C" || metric.metric_code === "LEVEL_PERCENT" ? "xl:col-span-2" : ""}>
      {content}
      {series.points.some((point) => point.source === "legacy_fallback") ? (
        <p className="mt-2 px-1 text-[11px] font-semibold text-amber-700">Serie histórica compatible, preservada durante la conciliación.</p>
      ) : null}
    </div>
  );
}
