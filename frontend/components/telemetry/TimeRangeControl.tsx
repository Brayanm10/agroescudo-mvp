"use client";

import { CalendarRange, SlidersHorizontal } from "lucide-react";
import type { TelemetryRange, TelemetryResolution } from "@/lib/telemetry";

const ranges: Array<{ value: TelemetryRange; label: string }> = [
  { value: "6h", label: "6 h" },
  { value: "24h", label: "24 h" },
  { value: "7d", label: "7 días" },
  { value: "30d", label: "30 días" },
  { value: "90d", label: "90 días" },
  { value: "custom", label: "Personalizado" }
];

export function TimeRangeControl({
  range,
  resolution,
  customFrom,
  customTo,
  onRangeChange,
  onResolutionChange,
  onCustomFromChange,
  onCustomToChange
}: {
  range: TelemetryRange;
  resolution: TelemetryResolution;
  customFrom: string;
  customTo: string;
  onRangeChange: (value: TelemetryRange) => void;
  onResolutionChange: (value: TelemetryResolution) => void;
  onCustomFromChange: (value: string) => void;
  onCustomToChange: (value: string) => void;
}) {
  return (
    <section className="panel overflow-hidden" aria-label="Periodo de análisis">
      <div className="flex flex-col gap-4 p-4 xl:flex-row xl:items-end xl:justify-between">
        <div className="min-w-0">
          <div className="flex items-center gap-2">
            <CalendarRange size={17} className="text-emerald-700" aria-hidden="true" />
            <p className="text-xs font-black uppercase tracking-[0.12em] text-slate-500">Ventana de análisis</p>
          </div>
          <div className="mt-3 flex max-w-full gap-1 overflow-x-auto rounded-lg border border-slate-200 bg-slate-50 p-1" role="group" aria-label="Rango temporal">
            {ranges.map((item) => (
              <button
                key={item.value}
                type="button"
                onClick={() => onRangeChange(item.value)}
                aria-pressed={range === item.value}
                className={`shrink-0 rounded-md px-3 py-2 text-xs font-bold transition focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-emerald-600 ${
                  range === item.value ? "bg-white text-emeraldDeep shadow-sm ring-1 ring-slate-200" : "text-slate-500 hover:bg-white/70 hover:text-slate-800"
                }`}
              >
                {item.label}
              </button>
            ))}
          </div>
        </div>
        <label className="min-w-48">
          <span className="mb-1.5 flex items-center gap-2 text-[10px] font-black uppercase tracking-[0.12em] text-slate-500">
            <SlidersHorizontal size={14} aria-hidden="true" />
            Intervalo del gráfico
          </span>
          <select value={resolution} onChange={(event) => onResolutionChange(event.target.value as TelemetryResolution)} className="input">
            <option value="auto">Automático</option>
            <option value="raw">Cada lectura</option>
            <option value="5m">Promedio cada 5 min</option>
            <option value="15m">Promedio cada 15 min</option>
            <option value="1h">Promedio cada hora</option>
            <option value="1d">Promedio diario</option>
          </select>
        </label>
      </div>
      {range === "custom" ? (
        <div className="grid gap-3 border-t border-slate-200 bg-slate-50/70 p-4 sm:grid-cols-2">
          <label>
            <span className="mb-1 block text-[10px] font-black uppercase tracking-[0.12em] text-slate-500">Desde</span>
            <input className="input" type="datetime-local" value={customFrom} onChange={(event) => onCustomFromChange(event.target.value)} />
          </label>
          <label>
            <span className="mb-1 block text-[10px] font-black uppercase tracking-[0.12em] text-slate-500">Hasta</span>
            <input className="input" type="datetime-local" value={customTo} onChange={(event) => onCustomToChange(event.target.value)} />
          </label>
        </div>
      ) : null}
    </section>
  );
}
