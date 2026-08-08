"use client";

import { useState } from "react";
import {
  AlertTriangle,
  BarChart3,
  BellRing,
  Building2,
  Camera,
  ClipboardCheck,
  ClipboardList,
  Cpu,
  FileDown,
  GitCompareArrows,
  HeartPulse,
  Sprout,
  Factory,
  Headphones,
  History,
  LayoutDashboard,
  MapPinned,
  Menu,
  Network,
  ShieldCheck,
  SlidersHorizontal,
  Users,
  Wrench,
  X
} from "lucide-react";
import type { LucideIcon } from "lucide-react";
import type { UserRole, ViewKey } from "@/lib/types";

type NavItem = { key: ViewKey; label: string; icon: LucideIcon };
type NavGroup = { title: string; items: NavItem[] };

const adminGroups: NavGroup[] = [
  {
    title: "Inicio",
    items: [{ key: "dashboard", label: "Inicio", icon: LayoutDashboard }]
  },
  {
    title: "Operacion",
    items: [
      { key: "companies", label: "Empresas y sitios", icon: Building2 },
      { key: "silos", label: "Silos", icon: Factory },
      { key: "fields", label: "Campo", icon: Sprout },
      { key: "sensors", label: "Dispositivos", icon: Cpu },
      { key: "alerts", label: "Alertas e incidentes", icon: AlertTriangle },
      { key: "logs", label: "Bitacora", icon: ClipboardList },
      { key: "maintenance", label: "Mantenimiento", icon: Wrench },
      { key: "installations", label: "Instalaciones", icon: ClipboardCheck },
      { key: "evidence", label: "Evidencia", icon: Camera }
    ]
  },
  {
    title: "Analisis",
    items: [
      { key: "history", label: "Historial", icon: History },
      { key: "comparison", label: "Comparar periodos", icon: GitCompareArrows },
      { key: "pilotMetrics", label: "Metricas de piloto", icon: BarChart3 },
      { key: "reports", label: "Reportes", icon: BarChart3 },
      { key: "exports", label: "Exportaciones", icon: FileDown }
    ]
  },
  {
    title: "Infraestructura",
    items: [
      { key: "systemHealth", label: "Salud del sistema", icon: HeartPulse },
      { key: "gateways", label: "Gateways", icon: Network },
      { key: "firmware", label: "Firmware", icon: Cpu }
    ]
  },
  {
    title: "Soporte",
    items: [{ key: "support", label: "AgroAsistente", icon: Headphones }]
  },
  {
    title: "Administracion",
    items: [
      { key: "users", label: "Usuarios y accesos", icon: Users },
      { key: "thresholds", label: "Umbrales", icon: SlidersHorizontal },
      { key: "notifications", label: "Configuracion", icon: BellRing }
    ]
  }
];

const clientGroups: NavGroup[] = [
  {
    title: "Portal cliente",
    items: [
      { key: "dashboard", label: "Inicio", icon: LayoutDashboard },
      { key: "silos", label: "Mis silos", icon: Factory },
      { key: "fields", label: "Mi campo", icon: Sprout },
      { key: "alerts", label: "Alertas", icon: AlertTriangle },
      { key: "history", label: "Historial", icon: History },
      { key: "reports", label: "Reportes", icon: BarChart3 },
      { key: "support", label: "AgroAsistente", icon: Headphones }
    ]
  }
];

const technicianGroups: NavGroup[] = [
  {
    title: "Operacion tecnica",
    items: [
      { key: "silos", label: "Silos asignados", icon: Factory },
      { key: "fields", label: "Campo asignado", icon: Sprout },
      { key: "sensors", label: "Dispositivos", icon: Cpu },
      { key: "alerts", label: "Alertas tecnicas", icon: AlertTriangle },
      { key: "maintenance", label: "Mantenimiento", icon: Wrench },
      { key: "installations", label: "Instalaciones", icon: ClipboardCheck },
      { key: "evidence", label: "Evidencia", icon: Camera },
      { key: "systemHealth", label: "Salud y gateways", icon: HeartPulse },
      { key: "comparison", label: "Comparar periodos", icon: GitCompareArrows },
      { key: "exports", label: "Reportes tecnicos", icon: FileDown },
      { key: "firmware", label: "Firmware", icon: Cpu },
      { key: "logs", label: "Bitacora", icon: ClipboardList },
      { key: "support", label: "AgroAsistente", icon: Headphones }
    ]
  }
];

function groupsForRole(role: UserRole): NavGroup[] {
  if (role === "admin") return adminGroups;
  if (role === "technician") return technicianGroups;
  return clientGroups;
}

export function Sidebar({
  current,
  onChange,
  allowedViews,
  role
}: {
  current: ViewKey;
  onChange: (view: ViewKey) => void;
  allowedViews?: ViewKey[];
  role: UserRole;
}) {
  const [mobileOpen, setMobileOpen] = useState(false);
  const groups = groupsForRole(role)
    .map((group) => ({
      ...group,
      items: allowedViews ? group.items.filter((item) => allowedViews.includes(item.key)) : group.items
    }))
    .filter((group) => group.items.length > 0);

  function navigate(view: ViewKey) {
    setMobileOpen(false);
    onChange(view);
  }

  return (
    <>
      {mobileOpen ? <button type="button" aria-label="Cerrar menu" className="fixed inset-0 z-20 bg-emeraldInk/55 backdrop-blur-sm lg:hidden" onClick={() => setMobileOpen(false)} /> : null}
      <aside className="brand-grid relative z-30 border-r border-emerald-950/20 bg-emeraldInk text-white lg:sticky lg:top-0 lg:h-screen lg:w-72 lg:shrink-0 lg:overflow-y-auto">
        <div className="flex h-[72px] items-center justify-between border-b border-white/10 px-4 lg:hidden">
          <div className="flex min-w-0 items-center gap-3">
            <img src="/brand/shield-white.png" alt="" className="h-10 w-10 shrink-0 object-contain" />
            <div className="min-w-0">
              <p className="truncate text-lg font-black leading-none text-white">AgroEscudo</p>
              <p className="mt-1 text-[9px] font-black uppercase tracking-[0.14em] text-amber-200">Postcosecha IoT</p>
            </div>
          </div>
          <button
            type="button"
            className="flex h-10 w-10 items-center justify-center rounded-xl border border-white/15 bg-white/10 text-white"
            onClick={() => setMobileOpen((value) => !value)}
            aria-expanded={mobileOpen}
            aria-label={mobileOpen ? "Cerrar menu" : "Abrir menu"}
          >
            {mobileOpen ? <X size={20} /> : <Menu size={20} />}
          </button>
        </div>
        <div className="hidden border-b border-white/10 px-5 py-5 lg:block">
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
        <nav className={`${mobileOpen ? "block" : "hidden"} absolute left-0 right-0 top-[72px] z-40 max-h-[calc(100vh-72px)] overflow-y-auto border-b border-white/10 bg-emeraldInk p-4 shadow-2xl lg:static lg:block lg:max-h-none lg:space-y-5 lg:border-0 lg:bg-transparent lg:shadow-none`} aria-label="Navegacion principal">
        {groups.map((group) => (
          <div key={group.title} className="mb-5 space-y-1.5 last:mb-0 lg:mb-0">
            <p className="mb-2 px-2 text-[10px] font-black uppercase tracking-[0.18em] text-emerald-100/50">{group.title}</p>
            <div className="space-y-1.5">
              {group.items.map((item) => {
                const Icon = item.icon;
                const active = current === item.key;
                return (
                  <button
                    key={item.key}
                    type="button"
                    onClick={() => navigate(item.key)}
                    className={`group flex w-full items-center gap-3 rounded-xl px-3.5 py-2.5 text-left text-sm font-bold transition ${
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
            </div>
          </div>
        ))}
        </nav>
        <div className="mx-4 mt-2 hidden rounded-2xl border border-white/10 bg-white/10 p-4 text-xs leading-5 text-emerald-50/75 shadow-soft lg:block">
        <div className="flex items-center gap-2">
          <span className="h-2 w-2 rounded-full bg-emerald-300 shadow-[0_0_0_5px_rgba(110,231,183,0.12)]" />
          <p className="font-bold text-white">Operacion activa</p>
        </div>
        <p className="mt-1">Monitoreo de silos, sensores, alertas, bitacora y evidencia tecnica.</p>
        </div>
      </aside>
    </>
  );
}
