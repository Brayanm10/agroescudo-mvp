import { RefreshCw } from "lucide-react";
import type { ReactNode } from "react";
import { Sidebar } from "./Sidebar";
import { AccountMenu } from "./account/AccountMenu";
import type { User, ViewKey } from "@/lib/types";

const pageCopy: Record<ViewKey, { eyebrow: string; title: string }> = {
  dashboard: { eyebrow: "Inicio", title: "Prioridades operativas" },
  demo: { eyebrow: "Demo separada", title: "Presentacion ejecutiva" },
  pilots: { eyebrow: "Operacion", title: "Alta y seguimiento de pilotos" },
  companies: { eyebrow: "Operacion", title: "Empresas, sitios y silos" },
  storage: { eyebrow: "Operacion", title: "Silos y galpones" },
  sensors: { eyebrow: "Operacion", title: "Dispositivos y sensores" },
  sites: { eyebrow: "Operacion", title: "Sitios y silos asignados" },
  alerts: { eyebrow: "Operacion", title: "Alertas e incidentes" },
  logs: { eyebrow: "Trazabilidad", title: "Bitacora operativa" },
  maintenance: { eyebrow: "Operacion tecnica", title: "Mantenimiento" },
  history: { eyebrow: "Analisis", title: "Historial y tendencias" },
  thresholds: { eyebrow: "Administracion", title: "Umbrales por dispositivo" },
  reports: { eyebrow: "Analisis", title: "Reportes" },
  users: { eyebrow: "Administracion", title: "Usuarios y accesos" },
  notifications: { eyebrow: "Administracion", title: "Configuracion" },
  support: { eyebrow: "Soporte", title: "Soporte operativo" },
  profile: { eyebrow: "Cuenta", title: "Mi perfil" },
  changePassword: { eyebrow: "Cuenta", title: "Cambiar contrasena" },
  preferences: { eyebrow: "Cuenta", title: "Preferencias" }
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

  return (
    <div className="min-h-screen bg-field lg:flex">
      <Sidebar current={current} onChange={onChange} allowedViews={allowedViews} role={user.role} />
      <div className="min-w-0 flex-1">
        <header className="sticky top-0 z-10 border-b border-slate-200/80 bg-white/90 px-4 py-4 backdrop-blur-xl lg:px-8">
          <div className="flex flex-wrap items-center justify-between gap-3">
            <div>
              <p className="section-kicker">{copy.eyebrow}</p>
              <h1 className="text-xl font-black tracking-tight text-slate-950">{copy.title}</h1>
            </div>
            <div className="flex items-center gap-2">
              <AccountMenu user={user} onNavigate={onChange} onLogout={onLogout} />
              <button
                type="button"
                onClick={onRefresh}
                className="rounded-lg border border-slate-200 bg-white p-2.5 text-slate-600 shadow-soft transition hover:border-emerald-200 hover:bg-emerald-50 hover:text-emeraldDeep"
                title="Actualizar datos"
              >
                <RefreshCw size={18} aria-hidden="true" />
              </button>
            </div>
          </div>
        </header>
        <main className="mx-auto max-w-[1500px] px-4 py-6 lg:px-8">{children}</main>
      </div>
    </div>
  );
}
