import {
  AlertTriangle,
  BarChart3,
  BellRing,
  Building2,
  ClipboardList,
  Cpu,
  Factory,
  Headphones,
  History,
  LayoutDashboard,
  MapPinned,
  ShieldCheck,
  SlidersHorizontal,
  Users,
  Wrench
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
      { key: "sensors", label: "Dispositivos", icon: Cpu },
      { key: "alerts", label: "Alertas e incidentes", icon: AlertTriangle },
      { key: "logs", label: "Bitacora", icon: ClipboardList }
    ]
  },
  {
    title: "Analisis",
    items: [
      { key: "history", label: "Historial", icon: History },
      { key: "reports", label: "Reportes", icon: BarChart3 }
    ]
  },
  {
    title: "Soporte",
    items: [{ key: "support", label: "Chat de ayuda", icon: Headphones }]
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
      { key: "sites", label: "Mis silos", icon: Factory },
      { key: "alerts", label: "Alertas", icon: AlertTriangle },
      { key: "history", label: "Historial", icon: History },
      { key: "reports", label: "Reportes", icon: BarChart3 },
      { key: "support", label: "Soporte", icon: Headphones }
    ]
  }
];

const technicianGroups: NavGroup[] = [
  {
    title: "Operacion tecnica",
    items: [
      { key: "sites", label: "Sitios asignados", icon: MapPinned },
      { key: "sensors", label: "Dispositivos", icon: Cpu },
      { key: "alerts", label: "Alertas tecnicas", icon: AlertTriangle },
      { key: "maintenance", label: "Mantenimiento", icon: Wrench },
      { key: "logs", label: "Bitacora", icon: ClipboardList },
      { key: "support", label: "Chat de ayuda", icon: Headphones }
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
  const groups = groupsForRole(role)
    .map((group) => ({
      ...group,
      items: allowedViews ? group.items.filter((item) => allowedViews.includes(item.key)) : group.items
    }))
    .filter((group) => group.items.length > 0);

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
      <nav className="flex gap-2 overflow-x-auto p-3 lg:block lg:space-y-5 lg:p-4">
        {groups.map((group) => (
          <div key={group.title} className="lg:space-y-1.5">
            <p className="mb-2 hidden px-2 text-[10px] font-black uppercase tracking-[0.18em] text-emerald-100/50 lg:block">{group.title}</p>
            <div className="flex gap-2 lg:block lg:space-y-1.5">
              {group.items.map((item) => {
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
  );
}
