import { LogOut, RefreshCw } from "lucide-react";
import type { ReactNode } from "react";
import { Sidebar } from "./Sidebar";
import type { User, ViewKey } from "@/lib/types";

const pageCopy: Record<ViewKey, { eyebrow: string; title: string }> = {
  dashboard: { eyebrow: "Centro operativo", title: "Monitoreo industrial AgroEscudo" },
  demo: { eyebrow: "Demo comercial", title: "Modo presentacion" },
  pilots: { eyebrow: "Implementacion comercial", title: "Alta y seguimiento de pilotos" },
  sites: { eyebrow: "Red monitoreada", title: "Sitios y unidades de almacenamiento" },
  alerts: { eyebrow: "Gestion de riesgo", title: "Alertas operativas" },
  logs: { eyebrow: "Trazabilidad", title: "Bitacora operativa" },
  thresholds: { eyebrow: "Configuracion", title: "Umbrales por dispositivo" },
  reports: { eyebrow: "Reporte", title: "Resumen semanal" },
  users: { eyebrow: "Administracion", title: "Usuarios y accesos" },
  notifications: { eyebrow: "Canales externos", title: "Notificaciones dry-run" }
};

export function AppLayout({
  current,
  onChange,
  allowedViews,
  user,
  onLogout,
  onRefresh,
  children
}: {
  current: ViewKey;
  onChange: (view: ViewKey) => void;
  allowedViews?: ViewKey[];
  user: User;
  onLogout: () => void;
  onRefresh: () => void;
  children: ReactNode;
}) {
  const copy = pageCopy[current];
  const roleLabel = user.role === "admin" ? "Admin AgroEscudo" : user.role === "technician" ? "Tecnico AgroEscudo" : "Cliente silo";

  return (
    <div className="min-h-screen bg-field lg:flex">
      <Sidebar current={current} onChange={onChange} allowedViews={allowedViews} />
      <div className="min-w-0 flex-1">
        <header className="sticky top-0 z-10 border-b border-slate-200/80 bg-white/90 px-4 py-4 backdrop-blur-xl lg:px-8">
          <div className="flex flex-wrap items-center justify-between gap-3">
            <div>
              <p className="section-kicker">{copy.eyebrow}</p>
              <h1 className="text-xl font-black tracking-tight text-slate-950">{copy.title}</h1>
            </div>
            <div className="flex items-center gap-2">
              <div className="hidden rounded-xl border border-slate-200 bg-white px-3 py-2 text-right shadow-soft sm:block">
                <p className="text-sm font-semibold text-slate-900">{user.full_name}</p>
                <p className="text-xs text-slate-500">{user.company?.name || user.email}</p>
                <p className="mt-1 text-[10px] font-black uppercase tracking-[0.13em] text-emerald-700">{roleLabel}</p>
              </div>
              <button
                type="button"
                onClick={onRefresh}
                className="rounded-lg border border-slate-200 bg-white p-2.5 text-slate-600 shadow-soft transition hover:border-emerald-200 hover:bg-emerald-50 hover:text-emeraldDeep"
                title="Actualizar datos"
              >
                <RefreshCw size={18} aria-hidden="true" />
              </button>
              <button
                type="button"
                onClick={onLogout}
                className="rounded-lg border border-slate-200 bg-white p-2.5 text-slate-600 shadow-soft transition hover:border-red-200 hover:bg-red-50 hover:text-red-700"
                title="Cerrar sesion"
              >
                <LogOut size={18} aria-hidden="true" />
              </button>
            </div>
          </div>
        </header>
        <main className="mx-auto max-w-[1500px] px-4 py-6 lg:px-8">{children}</main>
      </div>
    </div>
  );
}
