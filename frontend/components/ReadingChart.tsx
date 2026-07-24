"use client";

import { Area, AreaChart, CartesianGrid, ReferenceLine, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import type { Reading } from "@/lib/types";
import { chartSeries, type ReadingMetric } from "@/lib/telemetry";

type Props = {
  title: string;
  readings: Reading[];
  metric: ReadingMetric;
  color: string;
  unit: string;
  threshold?: number;
};

export function ReadingChart({ title, readings, metric, color, unit, threshold }: Props) {
  const values = readings.map((reading) => reading[metric]).filter((value): value is number => value !== null);
  const latest = readings.find((reading) => reading[metric] !== null)?.[metric] ?? null;
  const min = values.length ? Math.min(...values) : null;
  const max = values.length ? Math.max(...values) : null;
  const avg = values.length ? values.reduce((sum, value) => sum + value, 0) / values.length : null;
  const previous = readings.filter((reading) => reading[metric] !== null)[1]?.[metric] ?? null;
  const trend = latest === null || previous === null ? null : latest - previous;
  const data = chartSeries(readings, metric);

  return (
    <section className="rounded-panel border border-slate-200/80 bg-white p-5 shadow-panel">
      <div className="flex items-center justify-between gap-3">
        <div>
          <p className="section-kicker">Tendencia</p>
          <h3 className="mt-1 text-base font-bold text-slate-950">{title}</h3>
        </div>
        <div className="text-right">
          <p className="text-xs font-bold uppercase tracking-[0.12em] text-slate-400">Actual</p>
          <p className="text-lg font-black tracking-tight text-slate-950">{latest === null ? "--" : `${latest.toFixed(1)}${unit}`}</p>
        </div>
      </div>
      <div className="mt-4 h-64 rounded-xl border border-slate-100 bg-gradient-to-b from-slate-50/80 to-white p-2">
        <ResponsiveContainer width="100%" height="100%">
          <AreaChart data={data} margin={{ left: -12, right: 10, top: 12, bottom: 0 }}>
            <defs>
              <linearGradient id={`${metric}-fill`} x1="0" y1="0" x2="0" y2="1">
                <stop offset="5%" stopColor={color} stopOpacity={0.25} />
                <stop offset="95%" stopColor={color} stopOpacity={0.02} />
              </linearGradient>
            </defs>
            <CartesianGrid strokeDasharray="3 3" stroke="#e2e8f0" vertical={false} />
            <XAxis dataKey="time" tick={{ fontSize: 11, fill: "#64748b" }} stroke="#cbd5e1" tickLine={false} axisLine={false} />
            <YAxis domain={metric === "level_percent" ? [0, 100] : ["auto", "auto"]} tick={{ fontSize: 11, fill: "#64748b" }} stroke="#cbd5e1" tickLine={false} axisLine={false} />
            <Tooltip
              formatter={(value) => [`${Number(value).toFixed(1)}${unit}`, title]}
              contentStyle={{ borderRadius: 12, border: "1px solid #e2e8f0", boxShadow: "0 10px 30px rgba(15, 23, 42, 0.12)" }}
            />
            {threshold !== undefined ? (
              <ReferenceLine
                y={threshold}
                stroke="#b45309"
                strokeDasharray="4 4"
                label={{ value: `Umbral ${threshold}${unit}`, fill: "#92400e", fontSize: 11, position: "insideTopRight" }}
              />
            ) : null}
            <Area type="monotone" dataKey="value" connectNulls={false} stroke={color} fill={`url(#${metric}-fill)`} strokeWidth={2.5} />
          </AreaChart>
        </ResponsiveContainer>
      </div>
      <div className="mt-3 grid grid-cols-2 gap-2 text-xs font-semibold text-slate-500 sm:grid-cols-4">
        <span>{values.length} lecturas</span>
        <span>Mín. {min === null ? "--" : `${min.toFixed(1)}${unit}`}</span>
        <span>Prom. {avg === null ? "--" : `${avg.toFixed(1)}${unit}`}</span>
        <span className="text-right">
          Max. {max === null ? "--" : `${max.toFixed(1)}${unit}`}
          {trend === null ? "" : ` / ${trend >= 0 ? "+" : ""}${trend.toFixed(1)}${unit}`}
        </span>
      </div>
    </section>
  );
}
