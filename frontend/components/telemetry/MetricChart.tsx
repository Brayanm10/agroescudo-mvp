"use client";

import { Area, AreaChart, CartesianGrid, ReferenceLine, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import type { CanonicalMetricPoint, DashboardMetric } from "@/lib/types";

const COLORS: Record<string, string> = {
  GRAIN_TEMPERATURE_C: "#047857",
  AMBIENT_TEMPERATURE_C: "#2563eb",
  AMBIENT_RELATIVE_HUMIDITY_PCT: "#d97706",
  SOIL_MOISTURE_PCT: "#059669",
  SOIL_MOISTURE_RAW: "#64748b",
  LEVEL_DISTANCE_MM: "#0f766e",
  LEVEL_PERCENT: "#047857",
  BATTERY_VOLTAGE_MV: "#475569"
};

function displayUnit(unit: string) {
  return ({ degC: " °C", percent: "%", mV: " mV", mm: " mm", ADC_RAW: "" } as Record<string, string>)[unit] ?? ` ${unit}`;
}

export function MetricChart({
  metric,
  points,
  threshold
}: {
  metric: DashboardMetric;
  points: CanonicalMetricPoint[];
  threshold?: number;
}) {
  const values = points.map((point) => point.value).filter((value): value is number => value !== null);
  const data = withRealGaps(points);
  const latest = values.at(-1) ?? null;
  const min = values.length ? Math.min(...values) : null;
  const max = values.length ? Math.max(...values) : null;
  const average = values.length ? values.reduce((sum, value) => sum + value, 0) / values.length : null;
  const color = COLORS[metric.metric_code] ?? "#047857";
  const unit = displayUnit(metric.canonical_unit);
  const decimals = metric.default_decimals;

  return (
    <section className="rounded-panel border border-slate-200/80 bg-white p-5 shadow-panel">
      <div className="flex items-start justify-between gap-4">
        <div>
          <p className="section-kicker">{metric.channel_key.replaceAll("_", " ")}</p>
          <h3 className="mt-1 text-base font-bold text-slate-950">
            {metric.display_name_override || metric.display_name}
          </h3>
        </div>
        <div className="text-right">
          <p className="text-[10px] font-black uppercase tracking-[0.12em] text-slate-400">Actual</p>
          <p className="text-xl font-black text-slate-950">
            {latest === null ? "--" : `${latest.toFixed(decimals)}${unit}`}
          </p>
        </div>
      </div>
      <div className="mt-4 h-64 rounded-lg border border-slate-100 bg-slate-50/60 p-2">
        <ResponsiveContainer width="100%" height="100%">
          <AreaChart data={data} margin={{ left: -8, right: 8, top: 12, bottom: 0 }}>
            <defs>
              <linearGradient id={`canonical-${metric.numeric_id}-${metric.channel_id}`} x1="0" y1="0" x2="0" y2="1">
                <stop offset="5%" stopColor={color} stopOpacity={0.22} />
                <stop offset="95%" stopColor={color} stopOpacity={0.02} />
              </linearGradient>
            </defs>
            <CartesianGrid strokeDasharray="3 3" stroke="#e2e8f0" vertical={false} />
            <XAxis dataKey="label" tick={{ fontSize: 10, fill: "#64748b" }} tickLine={false} axisLine={false} />
            <YAxis
              domain={metric.canonical_unit === "percent" ? [0, 100] : ["auto", "auto"]}
              tick={{ fontSize: 10, fill: "#64748b" }}
              tickLine={false}
              axisLine={false}
            />
            <Tooltip
              formatter={(value) => [`${Number(value).toFixed(decimals)}${unit}`, metric.display_name]}
              contentStyle={{ borderRadius: 8, border: "1px solid #dbe5e0" }}
            />
            {threshold !== undefined ? <ReferenceLine y={threshold} stroke="#b45309" strokeDasharray="4 4" /> : null}
            <Area
              type="monotone"
              dataKey="value"
              connectNulls={false}
              stroke={color}
              strokeWidth={2.5}
              fill={`url(#canonical-${metric.numeric_id}-${metric.channel_id})`}
            />
          </AreaChart>
        </ResponsiveContainer>
      </div>
      <div className="mt-3 grid grid-cols-2 gap-2 text-xs font-semibold text-slate-500 sm:grid-cols-4">
        <span>{values.length} lecturas</span>
        <span>Mín. {min === null ? "--" : `${min.toFixed(decimals)}${unit}`}</span>
        <span>Prom. {average === null ? "--" : `${average.toFixed(decimals)}${unit}`}</span>
        <span>Máx. {max === null ? "--" : `${max.toFixed(decimals)}${unit}`}</span>
      </div>
      {points.some((point) => point.source === "legacy_fallback") ? (
        <p className="mt-3 text-[11px] font-semibold text-amber-700">
          Serie compatible legacy. La estructura original permanece conservada mientras se aprueba la conciliación P1.5.
        </p>
      ) : null}
    </section>
  );
}

function withRealGaps(points: CanonicalMetricPoint[]) {
  const ordered = [...points].sort((a, b) => new Date(a.sampled_at).getTime() - new Date(b.sampled_at).getTime());
  const intervals = ordered
    .slice(1)
    .map((point, index) => new Date(point.sampled_at).getTime() - new Date(ordered[index].sampled_at).getTime())
    .filter((value) => value > 0)
    .sort((a, b) => a - b);
  const median = intervals.length ? intervals[Math.floor((intervals.length - 1) / 2)] : 0;
  const gap = Math.max(median * 3, 15 * 60 * 1000);
  const result: Array<{ sampled_at: string; label: string; value: number | null }> = [];
  ordered.forEach((point, index) => {
    if (index > 0 && new Date(point.sampled_at).getTime() - new Date(ordered[index - 1].sampled_at).getTime() > gap) {
      result.push({ sampled_at: point.sampled_at, label: "Sin datos", value: null });
    }
    result.push({
      sampled_at: point.sampled_at,
      label: new Intl.DateTimeFormat("es-BO", { day: "2-digit", hour: "2-digit", minute: "2-digit" }).format(new Date(point.sampled_at)),
      value: point.value
    });
  });
  return result;
}
