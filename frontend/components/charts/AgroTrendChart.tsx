"use client";

import { useId } from "react";
import { Activity, ArrowDownRight, ArrowRight, ArrowUpRight, CircleAlert } from "lucide-react";
import {
  Area,
  AreaChart,
  Brush,
  CartesianGrid,
  ReferenceArea,
  ReferenceDot,
  ReferenceLine,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis
} from "recharts";
import type { DeviceChartAction, DeviceChartEvent, MetricDataGap } from "@/lib/types";
import { AgroChartTooltip } from "./AgroChartTooltip";
import {
  buildAgroChartData,
  chartDomain,
  conditionFor,
  formatGapDuration,
  type AgroChartInputPoint,
  type AgroChartThresholds,
  type AgroSeriesSummary
} from "./chart-model";

export type AgroTrendChartProps = {
  title: string;
  eyebrow?: string;
  description?: string;
  points: AgroChartInputPoint[];
  summary: AgroSeriesSummary;
  gaps?: MetricDataGap[];
  events?: DeviceChartEvent[];
  actions?: DeviceChartAction[];
  thresholds?: AgroChartThresholds;
  unit: string;
  decimals?: number;
  color?: string;
  periodLabel?: string;
  resolutionLabel?: string;
  variant?: "primary" | "secondary" | "compact";
  percentage?: boolean;
};

export function AgroTrendChart({
  title,
  eyebrow = "Telemetría operacional",
  description,
  points,
  summary,
  gaps = [],
  events = [],
  actions = [],
  thresholds = {},
  unit,
  decimals = 1,
  color = "#0c7654",
  periodLabel,
  resolutionLabel,
  variant = "secondary",
  percentage = false
}: AgroTrendChartProps) {
  const gradientId = `agro-${useId().replaceAll(":", "")}`;
  const data = buildAgroChartData(points, gaps, events, actions);
  const valid = data.filter((point) => point.value !== null);
  const domain = chartDomain(summary, thresholds, percentage);
  const condition = conditionFor(summary.current, thresholds);
  const maxPoint = summary.maximum === null
    ? null
    : valid.find((point) => point.bucketMax === summary.maximum || point.value === summary.maximum) ?? null;
  const height = variant === "primary" ? "h-[390px]" : variant === "compact" ? "h-[235px]" : "h-[300px]";
  const span = valid.length > 1 ? valid.at(-1)!.at - valid[0].at : 0;
  const hasThresholds = Object.values(thresholds).some((value) => value !== null && value !== undefined);
  const conditionTone = {
    normal: "bg-emerald-50 text-emerald-800",
    warning: "bg-amber-50 text-amber-800",
    critical: "bg-rose-50 text-rose-800",
    muted: "bg-slate-100 text-slate-600"
  }[condition.tone];

  if (!valid.length) return <AgroChartEmptyState title={title} />;

  return (
    <section className="overflow-hidden rounded-lg border border-emerald-950/10 bg-white shadow-[0_12px_38px_rgba(2,60,46,0.07)]">
      <header className="flex flex-col gap-5 border-b border-emerald-950/8 px-5 py-5 sm:flex-row sm:items-start sm:justify-between lg:px-6">
        <div className="min-w-0">
          <p className="text-[10px] font-black uppercase tracking-[0.14em] text-emerald-800">{eyebrow}</p>
          <h3 className={`${variant === "primary" ? "text-xl" : "text-base"} mt-1 font-black text-[#1b2622]`}>{title}</h3>
          <p className="mt-1.5 text-xs leading-5 text-slate-500">
            {[periodLabel, resolutionLabel, description].filter(Boolean).join(" · ")}
          </p>
        </div>
        <div className="flex shrink-0 items-center gap-4">
          <div className="text-left sm:text-right">
            <p className="text-[10px] font-black uppercase text-slate-400">Valor actual</p>
            <p className={`${variant === "primary" ? "text-3xl" : "text-2xl"} mt-0.5 font-black text-[#1b2622]`}>
              {formatValue(summary.current, decimals, unit)}
            </p>
          </div>
          <span className={`rounded-md px-2.5 py-1.5 text-[10px] font-black uppercase ${conditionTone}`}>{condition.label}</span>
        </div>
      </header>

      <div className={`${height} bg-[linear-gradient(180deg,#f8fbf9_0%,#ffffff_100%)] px-2 pb-2 pt-4 sm:px-4`}>
        <ResponsiveContainer width="100%" height="100%">
          <AreaChart data={data} margin={{ left: -6, right: 24, top: 22, bottom: variant === "compact" ? 0 : 8 }}>
            <defs>
              <linearGradient id={gradientId} x1="0" y1="0" x2="0" y2="1">
                <stop offset="4%" stopColor={color} stopOpacity={0.2} />
                <stop offset="90%" stopColor={color} stopOpacity={0.01} />
              </linearGradient>
            </defs>
            <CartesianGrid stroke="#dfe8e4" strokeDasharray="2 7" vertical={false} />
            <ThresholdZones thresholds={thresholds} domain={domain} />
            {gaps.map((gap, index) => (
              <ReferenceArea
                key={`${gap.from}-${index}`}
                x1={new Date(gap.from).getTime()}
                x2={new Date(gap.to).getTime()}
                fill="#94a3b8"
                fillOpacity={0.07}
                ifOverflow="hidden"
              />
            ))}
            <XAxis
              type="number"
              dataKey="at"
              domain={["dataMin", "dataMax"]}
              scale="time"
              minTickGap={42}
              tickFormatter={(value) => formatAxisTime(Number(value), span)}
              tick={{ fontSize: 10, fill: "#69736f" }}
              tickLine={false}
              axisLine={false}
            />
            <YAxis domain={domain} width={46} tick={{ fontSize: 10, fill: "#69736f" }} tickLine={false} axisLine={false} />
            <Tooltip content={<AgroChartTooltip unit={unit} decimals={decimals} thresholds={thresholds} />} />
            <ThresholdLines thresholds={thresholds} unit={unit} />
            {maxPoint ? <ReferenceDot x={maxPoint.at} y={summary.maximum!} r={4.5} fill="#d99a00" stroke="#fff" strokeWidth={2.5} /> : null}
            {data.flatMap((point) => point.events.map((event) => (
              <ReferenceDot
                key={`event-${event.id}`}
                x={point.at}
                y={event.observed_value ?? point.value ?? summary.current ?? 0}
                r={5}
                fill={event.severity === "critical" ? "#b42318" : "#d99a00"}
                stroke="#fff"
                strokeWidth={2.5}
              />
            )))}
            {data.flatMap((point) => point.actions.map((action) => (
              <ReferenceDot key={`action-${action.id}`} x={point.at} y={point.value ?? summary.current ?? 0} r={4.5} fill="#0c7654" stroke="#fff" strokeWidth={2.5} />
            )))}
            <Area
              type="monotone"
              dataKey="value"
              connectNulls={false}
              stroke={color}
              strokeWidth={variant === "primary" ? 3 : 2.5}
              strokeLinecap="round"
              fill={`url(#${gradientId})`}
              activeDot={{ r: 5, fill: color, stroke: "#fff", strokeWidth: 2.5 }}
              isAnimationActive={false}
            />
            {variant !== "compact" && data.length > 24 ? (
              <Brush dataKey="timestamp" height={22} stroke="#0c7654" fill="#f8faf9" travellerWidth={8} tickFormatter={() => ""} />
            ) : null}
          </AreaChart>
        </ResponsiveContainer>
      </div>

      <div className="grid grid-cols-2 divide-x divide-y divide-emerald-950/8 border-t border-emerald-950/8 sm:grid-cols-4 sm:divide-y-0">
        <ChartStat label="Mínimo" value={formatValue(summary.minimum, decimals, unit)} />
        <ChartStat label="Promedio" value={formatValue(summary.average, decimals, unit)} />
        <ChartStat label="Máximo" value={formatValue(summary.maximum, decimals, unit)} emphasis />
        <ChartStat label="Variación" value={formatSigned(summary.change, decimals, unit)} trend={summary.change} />
      </div>

      <AnnotationRail events={events} actions={actions} gaps={gaps} />
      {!hasThresholds ? (
        <div className="flex items-center gap-2 border-t border-emerald-950/8 px-5 py-3 text-xs font-semibold text-slate-500">
          <CircleAlert size={15} aria-hidden="true" />
          Umbrales no configurados. La gráfica muestra únicamente evidencia recibida.
        </div>
      ) : null}
    </section>
  );
}

function ThresholdZones({ thresholds, domain }: { thresholds: AgroChartThresholds; domain: [number, number] }) {
  const [low, high] = domain;
  return (
    <>
      {thresholds.max !== null && thresholds.max !== undefined ? <ReferenceArea y1={thresholds.max} y2={thresholds.criticalMax ?? high} fill="#d99a00" fillOpacity={0.07} /> : null}
      {thresholds.criticalMax !== null && thresholds.criticalMax !== undefined ? <ReferenceArea y1={thresholds.criticalMax} y2={high} fill="#b42318" fillOpacity={0.07} /> : null}
      {thresholds.min !== null && thresholds.min !== undefined ? <ReferenceArea y1={thresholds.criticalMin ?? low} y2={thresholds.min} fill="#d99a00" fillOpacity={0.07} /> : null}
      {thresholds.criticalMin !== null && thresholds.criticalMin !== undefined ? <ReferenceArea y1={low} y2={thresholds.criticalMin} fill="#b42318" fillOpacity={0.07} /> : null}
    </>
  );
}

function ThresholdLines({ thresholds, unit }: { thresholds: AgroChartThresholds; unit: string }) {
  const rows = [
    [thresholds.min, "Atención", "#b77900"],
    [thresholds.max, "Atención", "#b77900"],
    [thresholds.criticalMin, "Crítico", "#b42318"],
    [thresholds.criticalMax, "Crítico", "#b42318"]
  ] as const;
  return <>{rows.map(([value, label, stroke], index) => value === null || value === undefined ? null : (
    <ReferenceLine key={`${label}-${index}`} y={value} stroke={stroke} strokeDasharray="5 5" strokeOpacity={0.8} label={{ value: `${label} ${value}${unit}`, fill: stroke, fontSize: 9, position: "insideTopRight" }} />
  ))}</>;
}

function AnnotationRail({ events, actions, gaps }: { events: DeviceChartEvent[]; actions: DeviceChartAction[]; gaps: MetricDataGap[] }) {
  if (!events.length && !actions.length && !gaps.length) return null;
  return (
    <div className="flex flex-wrap gap-2 border-t border-emerald-950/8 px-5 py-3" aria-label="Eventos de la gráfica">
      {events.slice(0, 4).map((event) => (
        <span key={`event-${event.id}`} className={`inline-flex items-center gap-1.5 rounded-md px-2.5 py-1.5 text-[11px] font-bold ${event.severity === "critical" ? "bg-rose-50 text-rose-800" : "bg-amber-50 text-amber-800"}`}>
          <span className="h-2 w-2 rounded-full bg-current" aria-hidden="true" />
          {formatAnnotationDate(event.timestamp)} · {event.title}
        </span>
      ))}
      {actions.slice(0, 4).map((action) => (
        <span key={`action-${action.id}`} className="inline-flex items-center gap-1.5 rounded-md bg-emerald-50 px-2.5 py-1.5 text-[11px] font-bold text-emerald-800">
          <span className="h-2 w-2 rounded-full bg-current" aria-hidden="true" />
          {formatAnnotationDate(action.timestamp)} · {action.title}
        </span>
      ))}
      {gaps.slice(0, 2).map((gap) => (
        <span key={gap.from} className="inline-flex items-center gap-1.5 rounded-md bg-slate-100 px-2.5 py-1.5 text-[11px] font-bold text-slate-600">
          Sin datos durante {formatGapDuration(gap.duration_seconds)}
        </span>
      ))}
    </div>
  );
}

function ChartStat({ label, value, emphasis = false, trend }: { label: string; value: string; emphasis?: boolean; trend?: number | null }) {
  const Icon = trend === undefined || trend === null || Math.abs(trend) < 0.05 ? ArrowRight : trend > 0 ? ArrowUpRight : ArrowDownRight;
  return (
    <div className="px-4 py-3.5">
      <p className="text-[9px] font-black uppercase text-slate-400">{label}</p>
      <p className={`mt-1 flex items-center gap-1 text-sm font-black ${emphasis ? "text-emerald-800" : "text-slate-700"}`}>
        {trend !== undefined ? <Icon size={13} aria-hidden="true" /> : null}{value}
      </p>
    </div>
  );
}

function AgroChartEmptyState({ title }: { title: string }) {
  return (
    <section className="flex min-h-72 flex-col items-center justify-center rounded-lg border border-dashed border-emerald-950/15 bg-white p-8 text-center">
      <span className="grid h-12 w-12 place-items-center rounded-lg bg-emerald-50 text-emerald-700"><Activity size={22} /></span>
      <h3 className="mt-4 font-black text-[#1b2622]">{title}</h3>
      <p className="mt-1 max-w-sm text-sm text-slate-500">No existen lecturas válidas para esta variable en el periodo seleccionado.</p>
    </section>
  );
}

function formatAxisTime(value: number, span: number) {
  return new Intl.DateTimeFormat("es-BO", span > 3 * 86400000 ? { day: "2-digit", month: "short" } : { hour: "2-digit", minute: "2-digit" }).format(new Date(value));
}

function formatAnnotationDate(value: string) {
  return new Intl.DateTimeFormat("es-BO", { day: "2-digit", month: "short", hour: "2-digit", minute: "2-digit" }).format(new Date(value));
}

function formatValue(value: number | null, decimals: number, unit: string) {
  return value === null ? "Sin dato" : `${value.toFixed(decimals)}${unit}`;
}

function formatSigned(value: number | null, decimals: number, unit: string) {
  if (value === null) return "Sin dato";
  return `${value > 0 ? "+" : ""}${value.toFixed(decimals)}${unit}`;
}
