import { AlertTriangle, BarChart3, ClipboardList, LayoutDashboard, MapPinned, Presentation, Rocket, ShieldCheck, SlidersHorizontal } from "lucide-react";
import type { LucideIcon } from "lucide-react";
import type { ViewKey } from "@/lib/types";

const items: Array<{ key: ViewKey; label: string; icon: LucideIcon }> = [
  { key: "dashboard", label: "Dashboard", icon: LayoutDashboard },
  { key: "demo", label: "Modo presentacion", icon: Presentation },
  { key: "pilots", label: "Pilotos", icon: Rocket },
  { key: "sites", label: "Sitios", icon: MapPinned },
  { key: "alerts", label: "Alertas", icon: AlertTriangle },
  { key: "logs", label: "Bitacora", icon: ClipboardList },
  { key: "thresholds", label: "Umbrales", icon: SlidersHorizontal },
  { key: "reports", label: "Reportes", icon: BarChart3 }
];

export function Sidebar({
  current,
  onChange,
  allowedViews
}: {
  current: ViewKey;
  onChange: (view: ViewKey) => void;
  allowedViews?: ViewKey[];
}) {
  const visibleItems = allowedViews ? items.filter((item) => allowedViews.includes(item.key)) : items;

  return (
    <aside className="brand-grid border-r border-emerald-950/20 bg-emeraldInk text-white lg:min-h-screen lg:w-72">
      <div className="border-b border-white/10 px-5 py-5">
        <div className="flex items-center gap-3 rounded-2xl border border-white/10 bg-white/[0.08] p-3 shadow-glow">
          <img src="/brand/shield-white.png" alt="" className="h-14 w-14 shrink-0 object-contain" />
          <div className="min-w-0">
            <p className="text-2xl font-black leading-none tracking-tight text-white">AgroEscudo</p>
            <p className="mt-1 text-[10px] font-black uppercase tracking-[0.16em] text-amber-200">Postcosecha IoT</p>
          </div>
        </div>
        <div className="mt-4 flex items-center gap-3 rounded-xl border border-white/10 bg-white/[0.08] p-3 text-emerald-50">
          <div className="flex h-9 w-9 shrink-0 items-center justify-center rounded-lg border border-white/15 bg-white/10">
            <ShieldCheck size={17} aria-hidden="true" />
          </div>
          <div className="min-w-0">
            <p className="text-sm font-bold">Riesgo postcosecha</p>
            <p className="text-xs text-emerald-100/75">Control, trazabilidad y alerta</p>
          </div>
        </div>
      </div>
      <nav className="flex gap-2 overflow-x-auto p-3 lg:block lg:space-y-1.5 lg:p-4">
        <p className="mb-2 hidden px-2 text-[10px] font-black uppercase tracking-[0.18em] text-emerald-100/50 lg:block">Operacion</p>
        {visibleItems.map((item) => {
          const Icon = item.icon;
          const active = current === item.key;
          return (
            <button
              key={item.key}
              type="button"
              onClick={() => onChange(item.key)}
              className={`group flex min-w-fit items-center gap-3 rounded-xl px-3.5 py-2.5 text-sm font-bold transition lg:w-full ${
                active
                  ? "bg-white text-emeraldInk shadow-soft"
                  : "text-emerald-50/70 hover:bg-white/10 hover:text-white"
              }`}
            >
              <span className={`flex h-8 w-8 items-center justify-center rounded-lg transition ${active ? "bg-emerald-50 text-emeraldDeep" : "bg-white/5 text-emerald-50/70 group-hover:bg-white/10 group-hover:text-white"}`}>
                <Icon size={17} aria-hidden="true" />
              </span>
              <span>{item.label}</span>
            </button>
          );
        })}
      </nav>
      <div className="mx-4 mt-2 hidden rounded-2xl border border-white/10 bg-white/10 p-4 text-xs leading-5 text-emerald-50/75 shadow-soft lg:block">
        <div className="flex items-center gap-2">
          <span className="h-2 w-2 rounded-full bg-emerald-300 shadow-[0_0_0_5px_rgba(110,231,183,0.12)]" />
          <p className="font-bold text-white">MVP operativo</p>
        </div>
        <p className="mt-1">Datos reales desde sensores IoT, alertas y bitacora para pilotos industriales.</p>
      </div>
    </aside>
  );
}
