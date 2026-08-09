import type {
  DeviceChartAction,
  DeviceChartEvent,
  MetricDataGap,
  MetricSeriesSummary
} from "@/lib/types";

export type AgroChartThresholds = {
  min?: number | null;
  max?: number | null;
  criticalMin?: number | null;
  criticalMax?: number | null;
};

export type AgroChartInputPoint = {
  timestamp: string;
  value: number | null;
  bucketMin?: number | null;
  bucketMax?: number | null;
  sampleCount?: number;
};

export type AgroChartDatum = AgroChartInputPoint & {
  at: number;
  events: DeviceChartEvent[];
  actions: DeviceChartAction[];
  gap: boolean;
};

export type AgroSeriesSummary = MetricSeriesSummary;

export function buildAgroChartData(
  points: AgroChartInputPoint[],
  gaps: MetricDataGap[],
  events: DeviceChartEvent[],
  actions: DeviceChartAction[]
): AgroChartDatum[] {
  const data = points
    .map((point) => ({
      ...point,
      at: new Date(point.timestamp).getTime(),
      events: [] as DeviceChartEvent[],
      actions: [] as DeviceChartAction[],
      gap: false
    }))
    .filter((point) => Number.isFinite(point.at))
    .sort((a, b) => a.at - b.at);

  if (!data.length) return [];
  const realPoints = data.filter((point) => point.value !== null);
  const nearest = (timestamp: string) => {
    const at = new Date(timestamp).getTime();
    return realPoints.reduce<AgroChartDatum | null>(
      (best, point) => !best || Math.abs(point.at - at) < Math.abs(best.at - at) ? point : best,
      null
    );
  };
  events.forEach((event) => nearest(event.timestamp)?.events.push(event));
  actions.forEach((action) => nearest(action.timestamp)?.actions.push(action));

  const gapPoints = gaps.flatMap((gap) => {
    const from = new Date(gap.from).getTime();
    const to = new Date(gap.to).getTime();
    if (!Number.isFinite(from) || !Number.isFinite(to) || to <= from) return [];
    return [
      { timestamp: new Date(from + 1).toISOString(), at: from + 1 },
      { timestamp: new Date(to - 1).toISOString(), at: to - 1 }
    ].map((point) => ({
      ...point,
      value: null,
      bucketMin: null,
      bucketMax: null,
      sampleCount: 0,
      events: [] as DeviceChartEvent[],
      actions: [] as DeviceChartAction[],
      gap: true
    }));
  });
  return [...data, ...gapPoints].sort((a, b) => a.at - b.at);
}

export function summarizePoints(points: AgroChartInputPoint[]): AgroSeriesSummary {
  const valid = points.filter((point): point is AgroChartInputPoint & { value: number } => point.value !== null);
  const values = valid.map((point) => point.value);
  const current = valid.at(-1)?.value ?? null;
  const initial = valid[0]?.value ?? null;
  return {
    current,
    initial,
    minimum: values.length ? Math.min(...values) : null,
    maximum: values.length ? Math.max(...values) : null,
    average: values.length ? values.reduce((sum, value) => sum + value, 0) / values.length : null,
    change: current === null || initial === null ? null : current - initial,
    sample_count: values.length,
    point_count: values.length,
    coverage_seconds: 0
  };
}

export function conditionFor(value: number | null, thresholds: AgroChartThresholds) {
  if (value === null) return { label: "Sin dato", tone: "muted" as const };
  if (
    (thresholds.criticalMax !== null && thresholds.criticalMax !== undefined && value >= thresholds.criticalMax)
    || (thresholds.criticalMin !== null && thresholds.criticalMin !== undefined && value <= thresholds.criticalMin)
  ) return { label: "Crítico", tone: "critical" as const };
  if (
    (thresholds.max !== null && thresholds.max !== undefined && value >= thresholds.max)
    || (thresholds.min !== null && thresholds.min !== undefined && value <= thresholds.min)
  ) return { label: "Atención", tone: "warning" as const };
  return { label: "Normal", tone: "normal" as const };
}

export function formatGapDuration(seconds: number) {
  if (seconds < 3600) return `${Math.round(seconds / 60)} min`;
  const hours = Math.floor(seconds / 3600);
  const minutes = Math.round((seconds % 3600) / 60);
  return minutes ? `${hours} h ${minutes} min` : `${hours} h`;
}

export function chartDomain(
  summary: AgroSeriesSummary,
  thresholds: AgroChartThresholds,
  percentage: boolean
): [number, number] {
  if (percentage) return [0, 100];
  const values = [
    summary.minimum,
    summary.maximum,
    thresholds.min,
    thresholds.max,
    thresholds.criticalMin,
    thresholds.criticalMax
  ].filter((value): value is number => value !== null && value !== undefined);
  if (!values.length) return [0, 1];
  const low = Math.min(...values);
  const high = Math.max(...values);
  const padding = Math.max((high - low) * 0.14, Math.abs(high || 1) * 0.03, 0.5);
  return [Number((low - padding).toFixed(2)), Number((high + padding).toFixed(2))];
}
