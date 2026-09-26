import { ArrowUp, Compass } from "lucide-react";
import type { CanonicalMetricSeries } from "@/lib/types";
import { circularMeanDegrees, windDirectionPresentation } from "./wind-direction";

export function WindDirectionSummary({ series, decimals }: { series: CanonicalMetricSeries; decimals: number }) {
  const current = windDirectionPresentation(series.summary.current);
  const predominant = windDirectionPresentation(circularMeanDegrees(series.points));
  if (!current) {
    return (
      <div className="panel p-5" role="status">
        <p className="text-sm font-bold text-slate-500">Sin dirección de viento disponible en este periodo.</p>
      </div>
    );
  }

  return (
    <section className="panel overflow-hidden p-5 sm:p-6" aria-label="Lectura de dirección del viento">
      <div className="grid items-center gap-5 sm:grid-cols-[auto_minmax(0,1fr)_minmax(12rem,auto)]">
        <div className="relative flex h-24 w-24 shrink-0 items-center justify-center rounded-full border border-violet-200 bg-violet-50" aria-hidden="true">
          <span className="absolute top-1 text-[10px] font-black text-violet-900">N</span>
          <span className="absolute bottom-1 text-[10px] font-black text-violet-900">S</span>
          <span className="absolute left-1.5 text-[10px] font-black text-violet-900">O</span>
          <span className="absolute right-2 text-[10px] font-black text-violet-900">E</span>
          <ArrowUp
            size={42}
            strokeWidth={2.5}
            className="text-violet-700 transition-transform"
            style={{ transform: `rotate(${current.arrowRotation}deg)` }}
          />
        </div>
        <div>
          <p className="inline-flex items-center gap-2 text-xs font-black uppercase tracking-[0.12em] text-violet-700"><Compass size={15} />Dirección actual</p>
          <p className="mt-1 text-3xl font-black tracking-tight text-slate-950">{current.degrees.toFixed(decimals)}° <span className="text-violet-700">{current.from}</span></p>
          <p className="mt-2 text-sm font-bold text-slate-700">Viene de <span className="text-violet-800">{current.from}</span> <span aria-hidden="true">→</span> hacia <span className="text-violet-800">{current.to}</span></p>
          <p className="mt-1 text-xs leading-5 text-slate-500">Convención meteorológica: indica desde dónde llega el viento.</p>
        </div>
        <div className="rounded-xl border border-slate-200 bg-slate-50 px-4 py-3">
          <p className="text-[10px] font-black uppercase tracking-wide text-slate-500">Dirección predominante</p>
          <p className="mt-1 text-xl font-black text-slate-950">{predominant ? `${predominant.from} · ${predominant.degrees.toFixed(decimals)}°` : "—"}</p>
          <p className="mt-1 text-xs font-semibold text-slate-500">Calculada con media circular</p>
        </div>
      </div>
    </section>
  );
}
