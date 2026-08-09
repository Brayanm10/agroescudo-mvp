import type { AgroChartDatum, AgroChartThresholds } from "./chart-model";
import { conditionFor } from "./chart-model";

export function AgroChartTooltip({
  active,
  payload,
  unit,
  decimals,
  thresholds
}: {
  active?: boolean;
  payload?: Array<{ payload?: AgroChartDatum }>;
  unit: string;
  decimals: number;
  thresholds: AgroChartThresholds;
}) {
  const point = payload?.[0]?.payload;
  if (!active || !point || point.value === null) return null;
  const condition = conditionFor(point.value, thresholds);
  const conditionClass = {
    normal: "bg-emerald-50 text-emerald-800",
    warning: "bg-amber-50 text-amber-800",
    critical: "bg-rose-50 text-rose-800",
    muted: "bg-slate-100 text-slate-600"
  }[condition.tone];
  const date = new Intl.DateTimeFormat("es-BO", { dateStyle: "medium", timeStyle: "short" }).format(new Date(point.timestamp));
  return (
    <div className="max-w-[280px] rounded-xl border border-emerald-950/10 bg-[#fbfaf6] p-3.5 text-left shadow-[0_16px_36px_rgba(2,60,46,0.14)]">
      <p className="text-[11px] font-bold text-slate-500">{date}</p>
      <div className="mt-2 flex items-end justify-between gap-5">
        <p className="text-xl font-black text-[#1b2622]">{point.value.toFixed(decimals)}{unit}</p>
        <span className={`rounded-md px-2 py-1 text-[10px] font-black uppercase ${conditionClass}`}>{condition.label}</span>
      </div>
      {point.sampleCount && point.sampleCount > 1 ? (
        <p className="mt-2 text-[11px] text-slate-500">
          Intervalo: {point.bucketMin?.toFixed(decimals)}–{point.bucketMax?.toFixed(decimals)}{unit} · {point.sampleCount} muestras
        </p>
      ) : null}
      {point.events.map((event) => (
        <div key={`event-${event.id}`} className="mt-3 border-t border-rose-100 pt-2">
          <p className="text-[10px] font-black uppercase text-rose-700">Evento · {event.severity}</p>
          <p className="mt-1 text-xs font-bold text-slate-800">{event.title}</p>
        </div>
      ))}
      {point.actions.map((action) => (
        <div key={`action-${action.id}`} className="mt-3 border-t border-emerald-100 pt-2">
          <p className="text-[10px] font-black uppercase text-emerald-700">Acción posterior</p>
          <p className="mt-1 text-xs font-bold text-slate-800">{action.title}</p>
        </div>
      ))}
    </div>
  );
}
