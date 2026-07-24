"use client";

type Props = {
  percent: number | null;
  distanceCm: number | null;
  updatedAt?: string | null;
  calibrationStatus: "configured" | "pending" | "not_applicable";
  sensorConnected: boolean;
};

export function SiloLevelIndicator({ percent, distanceCm, updatedAt, calibrationStatus, sensorConnected }: Props) {
  const state = !sensorConnected
    ? "Sensor desconectado"
    : distanceCm === null
      ? "Sin datos"
      : calibrationStatus === "pending"
        ? "Calibración pendiente"
        : percent === null
          ? "Lectura fuera de rango"
          : percent < 15
            ? "Nivel bajo"
            : percent > 92
              ? "Nivel alto"
              : "Operación normal";
  const fill = percent ?? 0;
  const tone = state === "Operación normal" ? "#047857" : state === "Nivel bajo" || state === "Nivel alto" ? "#d99a00" : "#b91c1c";

  return (
    <section className="panel p-5" aria-label="Nivel estimado del silo">
      <div className="flex flex-wrap items-start justify-between gap-4">
        <div>
          <p className="section-kicker">Altura ocupada</p>
          <h3 className="mt-1 text-lg font-black text-slate-950">Nivel estimado</h3>
          <p className="mt-1 text-xs leading-5 text-slate-500">Representación de altura, no volumen exacto.</p>
        </div>
        <span className="rounded-full px-3 py-1 text-xs font-black" style={{ backgroundColor: `${tone}14`, color: tone }}>{state}</span>
      </div>
      <div className="mt-5 grid items-center gap-5 sm:grid-cols-[150px_1fr]">
        <svg viewBox="0 0 160 220" className="mx-auto h-56 w-40" role="img" aria-label={`${percent === null ? "Nivel no disponible" : `${percent.toFixed(1)} por ciento`}`}>
          <defs>
            <clipPath id="silo-level-clip">
              <path d="M30 45 L80 15 L130 45 V168 L110 205 H50 L30 168 Z" />
            </clipPath>
          </defs>
          <path d="M30 45 L80 15 L130 45 V168 L110 205 H50 L30 168 Z" fill="#f8faf9" stroke="#064e3b" strokeWidth="5" />
          <rect x="28" y={205 - (fill * 1.9)} width="104" height={fill * 1.9} fill={tone} opacity="0.88" clipPath="url(#silo-level-clip)" />
          <path d="M30 45 L80 15 L130 45 V168 L110 205 H50 L30 168 Z" fill="none" stroke="#064e3b" strokeWidth="5" />
        </svg>
        <div>
          <p className="text-4xl font-black text-slate-950">{percent === null ? "--" : `${percent.toFixed(1)}%`}</p>
          <dl className="mt-4 space-y-3 text-sm">
            <div className="flex justify-between gap-4 border-b border-slate-100 pb-2"><dt className="text-slate-500">Distancia a superficie</dt><dd className="font-black text-slate-900">{distanceCm === null ? "Sin dato" : `${distanceCm.toFixed(1)} cm`}</dd></div>
            <div className="flex justify-between gap-4 border-b border-slate-100 pb-2"><dt className="text-slate-500">Calibración</dt><dd className="font-black text-slate-900">{calibrationStatus === "configured" ? "Configurada" : "Pendiente"}</dd></div>
            <div className="flex justify-between gap-4"><dt className="text-slate-500">Actualización</dt><dd className="text-right font-black text-slate-900">{updatedAt ? new Intl.DateTimeFormat("es-BO", { dateStyle: "short", timeStyle: "short" }).format(new Date(updatedAt)) : "Sin dato"}</dd></div>
          </dl>
        </div>
      </div>
    </section>
  );
}
