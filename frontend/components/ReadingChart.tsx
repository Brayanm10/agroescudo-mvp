"use client";

import type { DeviceChartAction, DeviceChartEvent, MetricDataGap, Reading } from "@/lib/types";
import { chartSeries, type ReadingMetric } from "@/lib/telemetry";
import {
  AgroHumidityChart,
  AgroLevelChart,
  AgroTemperatureChart,
  AgroTrendChart,
  summarizePoints,
  type AgroChartInputPoint,
  type AgroChartThresholds,
  type AgroSeriesSummary
} from "@/components/charts";

export type ChartThresholds = AgroChartThresholds;

type Props = {
  title: string;
  readings: Reading[];
  metric: ReadingMetric;
  color: string;
  unit: string;
  thresholds?: ChartThresholds;
  periodLabel?: string;
  resolutionLabel?: string;
  events?: DeviceChartEvent[];
  actions?: DeviceChartAction[];
};

export function ReadingChart({
  title,
  readings,
  metric,
  color,
  unit,
  thresholds = {},
  periodLabel,
  resolutionLabel,
  events = [],
  actions = []
}: Props) {
  const rawSeries = chartSeries(readings, metric);
  const points: AgroChartInputPoint[] = rawSeries
    .filter((point) => point.value !== null)
    .map((point) => ({ timestamp: point.timestamp, value: point.value }));
  const summary = summarizePoints(points);
  const gaps = legacyGaps(readings, metric);
  const shared = {
    points,
    summary,
    gaps,
    events,
    actions,
    thresholds,
    unit,
    decimals: 1,
    periodLabel,
    resolutionLabel
  };

  if (metric === "grain_temperature") return <AgroTemperatureChart {...shared} />;
  if (metric === "ambient_humidity") return <AgroHumidityChart {...shared} />;
  if (metric === "level_percent") {
    const latest = [...readings].sort((a, b) => new Date(a.timestamp).getTime() - new Date(b.timestamp).getTime()).at(-1);
    return (
      <AgroLevelChart
        {...shared}
        distanceCm={latest?.level_distance_cm}
        updatedAt={latest?.timestamp}
        calibrationStatus={summary.current === null && latest?.level_distance_cm != null ? "pending" : "configured"}
      />
    );
  }
  return (
    <AgroTrendChart
      {...shared}
      title={title}
      color={color}
      percentage={metric === "soil_moisture_percent"}
      variant="secondary"
    />
  );
}

function legacyGaps(readings: Reading[], metric: ReadingMetric): MetricDataGap[] {
  const ordered = readings
    .filter((reading) => reading[metric] !== null && reading[metric] !== undefined)
    .sort((a, b) => new Date(a.timestamp).getTime() - new Date(b.timestamp).getTime());
  const intervals = ordered.slice(1)
    .map((reading, index) => new Date(reading.timestamp).getTime() - new Date(ordered[index].timestamp).getTime())
    .filter((value) => value > 0)
    .sort((a, b) => a - b);
  const median = intervals.length ? intervals[Math.floor((intervals.length - 1) / 2)] : 0;
  const threshold = Math.max(median * 3, 15 * 60 * 1000);
  return ordered.slice(1).flatMap((reading, index) => {
    const previous = ordered[index];
    const duration = new Date(reading.timestamp).getTime() - new Date(previous.timestamp).getTime();
    return duration > threshold ? [{ from: previous.timestamp, to: reading.timestamp, duration_seconds: duration / 1000 }] : [];
  });
}

export function summaryFromLegacy(points: AgroChartInputPoint[]): AgroSeriesSummary {
  return summarizePoints(points);
}
