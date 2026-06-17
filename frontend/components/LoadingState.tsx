export function LoadingState({ label = "Cargando datos operativos" }: { label?: string }) {
  return (
    <div className="flex min-h-48 items-center justify-center rounded-panel border border-slate-200/80 bg-white p-8 shadow-soft">
      <div className="flex items-center gap-3 text-sm font-bold text-slate-600">
        <span className="h-3 w-3 animate-pulse rounded-full bg-emeraldTech shadow-[0_0_0_6px_rgba(4,120,87,0.12)]" />
        {label}
      </div>
    </div>
  );
}
