"use client";

import { CloudRain } from "lucide-react";
import {
  Bar,
  BarChart,
  CartesianGrid,
  ReferenceArea,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis
} from "recharts";
import type { MetricDataGap } from "@/lib/types";
import { formatChartTimeInTimeZone, parseUtcTimestamp } from "@/lib/format";
import { AgroChartTooltip } from "./AgroChartTooltip";
import { buildAgroChartData, formatGapDuration, type AgroChartInputPoint } from "./chart-model";

export function AgroRainChart({
  points,
  gaps,
  decimals,
  periodLabel,
  resolutionLabel,
  timeZone
}: {
  points: AgroChartInputPoint[];
  gaps: MetricDataGap[];
  decimals: number;
  periodLabel: string;
  resolutionLabel: string;
  timeZone?: string;
}) {
  const data = buildAgroChartData(points, gaps, [], []);
  const valid = data.filter((point) => point.value !== null);
  const span = valid.length > 1 ? valid.at(-1)!.at - valid[0].at : 0;
  const maximum = Math.max(0, ...valid.map((point) => point.value ?? 0));

  if (!valid.length) {
    return (
      <section className="flex min-h-72 flex-col items-center justify-center rounded-lg border border-dashed border-sky-900/20 bg-white p-8 text-center">
        <span className="grid h-12 w-12 place-items-center rounded-lg bg-sky-50 text-sky-700"><CloudRain size={22} /></span>
        <h3 className="mt-4 font-black text-slate-900">Lluvia</h3>
        <p className="mt-1 max-w-sm text-sm text-slate-500">No existen lecturas de lluvia para el periodo seleccionado.</p>
      </section>
    );
  }

  return (
    <section className="overflow-hidden rounded-lg border border-sky-950/10 bg-white shadow-[0_12px_38px_rgba(2,60,46,0.07)]" aria-label={`Lluvia: serie histórica con ${valid.length} intervalos registrados`}>
      <header className="border-b border-sky-950/10 px-5 py-4 sm:px-6">
        <p className="text-[10px] font-black uppercase tracking-[0.14em] text-sky-700">Precipitación incremental</p>
        <h3 className="mt-1 text-lg font-black text-slate-950">Lluvia por intervalo</h3>
        <p className="mt-1 text-xs text-slate-500">{periodLabel} · {resolutionLabel} · Cada barra representa lluvia realmente registrada.</p>
      </header>
      <div className="h-[300px] bg-[linear-gradient(180deg,#f4fbff_0%,#ffffff_100%)] px-2 pb-2 pt-4 sm:h-[360px] sm:px-4">
        <ResponsiveContainer width="100%" height="100%">
          <BarChart data={data} margin={{ left: -8, right: 18, top: 18, bottom: 8 }}>
            <CartesianGrid stroke="#dbeafe" strokeDasharray="2 7" vertical={false} />
            {gaps.map((gap, index) => (
              <ReferenceArea key={`${gap.from}-${index}`} x1={parseUtcTimestamp(gap.from).getTime()} x2={parseUtcTimestamp(gap.to).getTime()} fill="#94a3b8" fillOpacity={0.1} />
            ))}
            <XAxis type="number" dataKey="at" domain={["dataMin", "dataMax"]} scale="time" minTickGap={42} tickFormatter={(value) => formatTime(Number(value), span, timeZone)} tick={{ fontSize: 10, fill: "#64748b" }} tickLine={false} axisLine={false} />
            <YAxis domain={[0, maximum > 0 ? maximum * 1.15 : 1]} width={42} tick={{ fontSize: 10, fill: "#64748b" }} tickLine={false} axisLine={false} unit=" mm" />
            <Tooltip content={<AgroChartTooltip unit=" mm" decimals={decimals} thresholds={{}} timeZone={timeZone} />} />
            <Bar dataKey="value" fill="#0284c7" radius={[4, 4, 0, 0]} maxBarSize={38} isAnimationActive={false} />
          </BarChart>
        </ResponsiveContainer>
      </div>
      {gaps.length ? (
        <div className="flex flex-wrap gap-2 border-t border-sky-950/10 px-5 py-3">
          {gaps.slice(0, 3).map((gap) => <span key={gap.from} className="rounded-md bg-slate-100 px-2.5 py-1.5 text-[11px] font-bold text-slate-600">Sin datos durante {formatGapDuration(gap.duration_seconds)}</span>)}
        </div>
      ) : null}
    </section>
  );
}

function formatTime(value: number, span: number, timeZone?: string) {
  const options: Intl.DateTimeFormatOptions = span > 3 * 86400000
    ? { day: "2-digit", month: "short", timeZone }
    : { hour: "2-digit", minute: "2-digit", timeZone };
  return formatChartTimeInTimeZone(value, timeZone, options);
}
