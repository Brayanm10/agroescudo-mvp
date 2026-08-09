import { AgroTrendChart, type AgroTrendChartProps } from "./AgroTrendChart";
import { conditionFor } from "./chart-model";

export function AgroLevelChart({
  distanceCm,
  updatedAt,
  calibrationStatus,
  ...props
}: Omit<AgroTrendChartProps, "title" | "eyebrow" | "color" | "variant" | "percentage"> & {
  distanceCm?: number | null;
  updatedAt?: string | null;
  calibrationStatus?: "configured" | "pending" | "not_applicable";
}) {
  const current = props.summary.current;
  const condition = conditionFor(current, props.thresholds ?? {});
  const fill = Math.max(0, Math.min(100, current ?? 0));
  const tone = condition.tone === "critical" ? "#b42318" : condition.tone === "warning" ? "#d99a00" : "#0c7654";
  return (
    <div className="grid gap-4 lg:grid-cols-[260px_minmax(0,1fr)]">
      <section className="rounded-lg border border-emerald-950/10 bg-[#fbfaf6] p-5 shadow-[0_12px_38px_rgba(2,60,46,0.07)]">
        <p className="text-[10px] font-black uppercase tracking-[0.14em] text-emerald-800">Gemelo operativo</p>
        <h3 className="mt-1 text-base font-black text-[#1b2622]">Nivel del silo</h3>
        <p className="mt-1 text-xs leading-5 text-slate-500">Altura ocupada estimada. No representa volumen ni toneladas.</p>
        <svg viewBox="0 0 180 245" className="mx-auto mt-5 h-56 w-44" role="img" aria-label={current === null ? "Nivel no disponible" : `Nivel ${current.toFixed(1)} por ciento`}>
          <defs>
            <clipPath id="agro-premium-level-clip"><path d="M32 48 L90 14 L148 48 V184 L124 226 H56 L32 184 Z" /></clipPath>
            <linearGradient id="agro-level-fill" x1="0" y1="1" x2="0" y2="0"><stop offset="0" stopColor={tone} /><stop offset="1" stopColor="#35a77e" /></linearGradient>
          </defs>
          <path d="M32 48 L90 14 L148 48 V184 L124 226 H56 L32 184 Z" fill="#f2f7f4" stroke="#064f3b" strokeWidth="5" />
          <rect x="30" y={226 - fill * 2.12} width="120" height={fill * 2.12} fill="url(#agro-level-fill)" opacity="0.9" clipPath="url(#agro-premium-level-clip)" />
          {[25, 50, 75].map((mark) => <line key={mark} x1="39" x2="141" y1={226 - mark * 2.12} y2={226 - mark * 2.12} stroke="#fff" strokeOpacity="0.6" strokeDasharray="4 5" />)}
          <path d="M32 48 L90 14 L148 48 V184 L124 226 H56 L32 184 Z" fill="none" stroke="#064f3b" strokeWidth="5" />
        </svg>
        <div className="mt-2 text-center">
          <p className="text-4xl font-black text-[#1b2622]">{current === null ? "--" : `${current.toFixed(1)}%`}</p>
          <p className="mt-1 text-xs font-bold" style={{ color: tone }}>{condition.label}</p>
        </div>
        <dl className="mt-5 space-y-2 text-xs">
          <LevelRow label="Variación" value={props.summary.change === null ? "Sin dato" : `${props.summary.change > 0 ? "+" : ""}${props.summary.change.toFixed(1)} pts`} />
          <LevelRow label="Distancia" value={distanceCm === null || distanceCm === undefined ? "Sin dato" : `${distanceCm.toFixed(1)} cm`} />
          <LevelRow label="Calibración" value={calibrationStatus === "configured" ? "Configurada" : calibrationStatus === "pending" ? "Pendiente" : "No aplica"} />
          <LevelRow label="Actualización" value={updatedAt ? new Intl.DateTimeFormat("es-BO", { dateStyle: "short", timeStyle: "short" }).format(new Date(updatedAt)) : "Sin dato"} />
        </dl>
      </section>
      <AgroTrendChart
        {...props}
        title="Tendencia del nivel"
        eyebrow="Evolución del periodo"
        description="Cambios de altura ocupada y ventanas sin información"
        color="#0f766e"
        variant="compact"
        percentage
      />
    </div>
  );
}

function LevelRow({ label, value }: { label: string; value: string }) {
  return <div className="flex items-center justify-between gap-3 border-b border-emerald-950/8 pb-2 last:border-0"><dt className="text-slate-500">{label}</dt><dd className="text-right font-black text-slate-800">{value}</dd></div>;
}
