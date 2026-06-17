"use client";

import { Area, AreaChart, CartesianGrid, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import type { Reading } from "@/lib/types";

type Props = {
  title: string;
  readings: Reading[];
  metric: "grain_temperature" | "ambient_humidity";
  color: string;
  unit: string;
};

export function ReadingChart({ title, readings, metric, color, unit }: Props) {
  const latest = readings[0]?.[metric];
  const max = readings.length ? Math.max(...readings.map((reading) => reading[metric])) : null;
  const data = readings
    .slice()
    .reverse()
    .map((reading) => ({
      time: new Intl.DateTimeFormat("es-BO", { hour: "2-digit", minute: "2-digit" }).format(new Date(reading.timestamp)),
      value: reading[metric]
    }));

  return (
    <section className="rounded-panel border border-slate-200/80 bg-white p-5 shadow-panel">
      <div className="flex items-center justify-between gap-3">
        <div>
          <p className="section-kicker">Tendencia</p>
          <h3 className="mt-1 text-base font-bold text-slate-950">{title}</h3>
        </div>
        <div className="text-right">
          <p className="text-xs font-bold uppercase tracking-[0.12em] text-slate-400">Actual</p>
          <p className="text-lg font-black tracking-tight text-slate-950">{latest === undefined ? "--" : `${latest.toFixed(1)}${unit}`}</p>
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
            <YAxis tick={{ fontSize: 11, fill: "#64748b" }} stroke="#cbd5e1" tickLine={false} axisLine={false} />
            <Tooltip
              formatter={(value) => [`${Number(value).toFixed(1)}${unit}`, title]}
              contentStyle={{ borderRadius: 12, border: "1px solid #e2e8f0", boxShadow: "0 10px 30px rgba(15, 23, 42, 0.12)" }}
            />
            <Area type="monotone" dataKey="value" stroke={color} fill={`url(#${metric}-fill)`} strokeWidth={2.5} />
          </AreaChart>
        </ResponsiveContainer>
      </div>
      <div className="mt-3 flex items-center justify-between text-xs font-semibold text-slate-500">
        <span>{readings.length} lecturas</span>
        <span>Max. {max === null ? "--" : `${max.toFixed(1)}${unit}`}</span>
      </div>
    </section>
  );
}
