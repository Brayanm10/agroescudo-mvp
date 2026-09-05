"use client";

import { useMemo, useState } from "react";
import {
  Activity,
  AlertTriangle,
  ArrowRight,
  CheckCircle2,
  Clock3,
  CloudOff,
  Factory,
  FileText,
  Leaf,
  Radio,
  ShieldCheck,
  Sprout,
  SunMedium
} from "lucide-react";
import { Line, LineChart, ResponsiveContainer } from "recharts";

import type { AppData, Reading, RiskStatus, StorageUnit, ViewKey } from "@/lib/types";

type Family = "all" | "storage" | "field";
type StateFilter = "all" | RiskStatus;

export function PremiumClientDashboard({
  data,
  onNavigate,
  onOpenUnit
}: {
  data: AppData;
  onNavigate: (view: ViewKey) => void;
  onOpenUnit: (unitId: number) => void;
}) {
  const [family, setFamily] = useState<Family>("all");
  const [stateFilter, setStateFilter] = useState<StateFilter>("all");
  const units = useMemo(
    () => [...data.storageUnits].sort((a, b) => statePriority(unitState(data, a)) - statePriority(unitState(data, b))),
    [data]
  );
  const counts = countStates(data, units);
  const overall = counts.critical ? "critical" : counts.warning ? "warning" : counts.normal ? "normal" : "no_data";
  const filtered = units.filter((unit) => {
    const matchesFamily = family === "all" || unitFamily(data, unit) === family;
    const matchesState = stateFilter === "all" || unitState(data, unit) === stateFilter;
    return matchesFamily && matchesState;
  });
  const firstName = data.me.full_name.trim().split(/\s+/)[0] || "cliente";
  const activeAlerts = data.activeAlerts.filter((alert) => units.some((unit) => unit.id === alert.storage_unit_id));

  if (!units.length) {
    return (
      <div className="space-y-5">
        <Greeting name={firstName} detail="Tu operación empieza aquí." />
        <section className="premium-empty-state">
          <span className="premium-empty-icon"><Radio size={30} aria-hidden="true" /></span>
          <p className="section-kicker">Primer paso</p>
          <h2 className="mt-2 text-3xl font-black text-slate-950">Aún no tienes unidades vinculadas</h2>
          <p className="mx-auto mt-3 max-w-xl text-sm leading-6 text-slate-600">
            Tu administrador debe asociar un SiloSensor o CampoSensor a esta cuenta. Cuando llegue la primera lectura, aquí verás el estado y las acciones prioritarias.
          </p>
          <button type="button" onClick={() => onNavigate("support")} className="btn-primary mt-6">
            Consultar el proceso <ArrowRight className="ml-2" size={16} />
          </button>
        </section>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <Greeting name={firstName} detail={greetingDetail(overall, counts.no_data)} />

      <OperationHero state={overall} data={data} activeAlerts={activeAlerts.length} onNavigate={onNavigate} />

      <section className="grid gap-3 sm:grid-cols-2 xl:grid-cols-4" aria-label="Indicadores de monitoreo">
        <LiveMetric
          icon={Activity}
          label="Cobertura hoy"
          value={data.monitoring?.coverage_today_pct == null ? "No calculable" : `${Math.round(data.monitoring.coverage_today_pct)}%`}
          detail={data.monitoring?.coverage_today_pct == null ? "Configura la cadencia del sensor" : "Lecturas esperadas recibidas"}
          progress={data.monitoring?.coverage_today_pct ?? null}
        />
        <LiveMetric
          icon={Clock3}
          label="Monitoreo continuo"
          value={data.monitoring?.calculation_status === "available" ? `${data.monitoring.current_streak_days} días` : "No calculable"}
          detail="Continuidad de telemetría, no ausencia de incidentes"
        />
        <LiveMetric icon={AlertTriangle} label="Alertas activas" value={String(activeAlerts.length)} detail={activeAlerts.length ? "Requieren revisión" : "Sin acciones urgentes"} />
        <LiveMetric icon={Radio} label="Unidades conectadas" value={`${data.monitoring?.online_devices ?? 0}/${units.length}`} detail="Con datos recientes" />
      </section>

      <section>
        <div className="mb-4 flex flex-wrap items-end justify-between gap-4">
          <div>
            <p className="section-kicker">Semáforo operativo</p>
            <h2 className="section-title">Elige qué quieres revisar</h2>
          </div>
          <button type="button" className="btn-secondary" onClick={() => onNavigate("sites")}>Ver toda mi operación</button>
        </div>
        <div className="grid grid-cols-2 gap-3 lg:grid-cols-4">
          <TrafficButton state="normal" value={counts.normal} selected={stateFilter === "normal"} onClick={() => setStateFilter(toggleState(stateFilter, "normal"))} />
          <TrafficButton state="warning" value={counts.warning} selected={stateFilter === "warning"} onClick={() => setStateFilter(toggleState(stateFilter, "warning"))} />
          <TrafficButton state="critical" value={counts.critical} selected={stateFilter === "critical"} onClick={() => setStateFilter(toggleState(stateFilter, "critical"))} />
          <TrafficButton state="no_data" value={counts.no_data} selected={stateFilter === "no_data"} onClick={() => setStateFilter(toggleState(stateFilter, "no_data"))} />
        </div>
      </section>

      <section>
        <div className="mb-4 flex flex-wrap items-center justify-between gap-3">
          <div>
            <p className="section-kicker">Mi operación</p>
            <h2 className="section-title">Unidades monitoreadas</h2>
          </div>
          <FamilyTabs family={family} setFamily={setFamily} units={units} data={data} />
        </div>
        {filtered.length ? (
          <div className="grid gap-4 lg:grid-cols-2 2xl:grid-cols-3">
            {filtered.slice(0, 6).map((unit) => (
              <PremiumUnitCard key={unit.id} data={data} unit={unit} onOpen={() => onOpenUnit(unit.id)} />
            ))}
          </div>
        ) : (
          <div className="rounded-panel border border-dashed border-slate-300 bg-white p-8 text-center text-sm text-slate-600">
            No hay unidades que coincidan con este filtro.
          </div>
        )}
      </section>

      <section className="grid gap-6 xl:grid-cols-[1.15fr_0.85fr]">
        <div>
          <div className="mb-3 flex items-center justify-between gap-3">
            <div><p className="section-kicker">Prioridad</p><h2 className="section-title">Lo que debes revisar</h2></div>
            <button type="button" onClick={() => onNavigate("alerts")} className="btn-secondary">Ver alertas</button>
          </div>
          <div className="space-y-3">
            {activeAlerts.slice(0, 3).map((alert) => {
              const unit = units.find((item) => item.id === alert.storage_unit_id);
              return (
                <button key={alert.id} type="button" onClick={() => onNavigate("alerts")} className="premium-action-row">
                  <span className={`premium-action-icon ${alert.severity === "critical" ? "bg-red-50 text-red-700" : "bg-amber-50 text-amber-700"}`}><AlertTriangle size={18} /></span>
                  <span className="min-w-0 flex-1"><strong>{unit?.name || "Unidad monitoreada"}</strong><small>{alert.severity === "critical" ? "Requiere atención inmediata." : "Hay una condición preventiva que revisar."}</small></span>
                  <ArrowRight size={17} className="text-slate-400" />
                </button>
              );
            })}
            {!activeAlerts.length ? (
              <div className="premium-action-row cursor-default"><span className="premium-action-icon bg-emerald-50 text-emerald-700"><CheckCircle2 size={18} /></span><span><strong>Sin acciones pendientes</strong><small>La evidencia actual no muestra alertas activas.</small></span></div>
            ) : null}
          </div>
        </div>

        <div>
          <div className="mb-3"><p className="section-kicker">Trazabilidad</p><h2 className="section-title">Actividad reciente</h2></div>
          <div className="premium-timeline">
            {data.monitoring?.recent_activity.map((item) => (
              <div key={`${item.kind}-${item.timestamp}-${item.title}`} className="premium-timeline-item">
                <span className="premium-timeline-dot" />
                <div><p className="font-bold text-slate-900">{item.title}</p><p className="mt-1 text-xs leading-5 text-slate-500">{item.detail}</p><time className="mt-1 block text-[11px] font-semibold text-slate-400">{formatRelative(item.timestamp)}</time></div>
              </div>
            ))}
            {!data.monitoring?.recent_activity.length ? <p className="text-sm text-slate-500">La actividad aparecerá cuando lleguen lecturas o se registren acciones.</p> : null}
          </div>
        </div>
      </section>

      {data.monitoring?.milestones.length ? (
        <section className="border-t border-slate-200 pt-5">
          <p className="section-kicker">Hitos del piloto</p>
          <div className="mt-3 flex flex-wrap gap-2">
            {data.monitoring.milestones.map((item) => <span key={item.key} className="milestone-chip"><CheckCircle2 size={14} />{item.label}</span>)}
          </div>
      </section>
      ) : null}

      <section className="flex flex-wrap gap-3 border-t border-slate-200 pt-5">
        <button type="button" onClick={() => onNavigate("reports")} className="btn-primary"><FileText className="mr-2" size={17} />Descargar reporte</button>
        <button type="button" onClick={() => onNavigate("support")} className="btn-secondary"><ShieldCheck className="mr-2" size={17} />Consultar AgroAsistente</button>
      </section>
    </div>
  );
}

function Greeting({ name, detail }: { name: string; detail: string }) {
  const hour = new Date().getHours();
  const greeting = hour < 12 ? "Buenos días" : hour < 19 ? "Buenas tardes" : "Buenas noches";
  return <header className="flex items-center gap-4"><span className="hidden h-12 w-12 items-center justify-center rounded-2xl bg-amber-50 text-amber-700 sm:flex"><SunMedium size={23} /></span><div><p className="text-2xl font-black text-slate-950 sm:text-3xl">{greeting}, {name}</p><p className="mt-1 text-sm text-slate-500">{detail}</p></div></header>;
}

function OperationHero({ state, data, activeAlerts, onNavigate }: { state: RiskStatus; data: AppData; activeAlerts: number; onNavigate: (view: ViewKey) => void }) {
  const copy = stateCopy(state);
  const lastSync = data.readings[0]?.timestamp;
  return (
    <section className={`operation-hero operation-hero-${state}`}>
      <div className="relative z-[1] max-w-2xl">
        <p className="text-[11px] font-black uppercase tracking-[0.16em] opacity-70">Estado de tu operación</p>
        <div className="mt-4 flex items-center gap-3"><span className={`status-orbit status-orbit-${state}`} /><span className="text-xs font-black uppercase tracking-[0.14em]">{copy.label}</span></div>
        <h2 className="mt-3 text-3xl font-black tracking-tight sm:text-4xl">{copy.title}</h2>
        <p className="mt-3 max-w-xl text-sm leading-6 opacity-80">{copy.detail}</p>
        <div className="mt-6 flex flex-wrap gap-3"><button type="button" className="btn-primary" onClick={() => onNavigate(state === "critical" || state === "warning" ? "alerts" : "sites")}>{state === "critical" || state === "warning" ? "Revisar ahora" : "Ver operación"}<ArrowRight className="ml-2" size={16} /></button><button type="button" className="btn-secondary" onClick={() => onNavigate("support")}>¿Qué significa este estado?</button></div>
      </div>
      <div className="relative z-[1] mt-6 flex flex-wrap gap-x-8 gap-y-2 border-t border-current/10 pt-4 text-xs font-semibold opacity-75"><span>{activeAlerts} alertas activas</span><span>{data.storageUnits.length} unidades</span><span>{lastSync ? `Actualizado ${formatRelative(lastSync)}` : "Esperando primera sincronización"}</span></div>
    </section>
  );
}

function LiveMetric({ icon: Icon, label, value, detail, progress }: { icon: typeof Activity; label: string; value: string; detail: string; progress?: number | null }) {
  return <article className="live-metric"><div className="flex items-start justify-between gap-3"><span className="live-metric-icon"><Icon size={18} /></span>{progress != null ? <span className="text-xs font-black text-emerald-800">{Math.round(progress)}%</span> : null}</div><p className="mt-4 text-2xl font-black text-slate-950">{value}</p><p className="mt-1 text-[11px] font-black uppercase tracking-[0.12em] text-slate-500">{label}</p><p className="mt-2 text-xs leading-5 text-slate-500">{detail}</p>{progress != null ? <div className="mt-3 h-1.5 overflow-hidden rounded-full bg-slate-100"><div className="h-full rounded-full bg-emerald-600 transition-all" style={{ width: `${Math.min(100, Math.max(0, progress))}%` }} /></div> : null}</article>;
}

function TrafficButton({ state, value, selected, onClick }: { state: RiskStatus; value: number; selected: boolean; onClick: () => void }) {
  const copy = trafficCopy(state);
  return <button type="button" aria-pressed={selected} onClick={onClick} className={`traffic-button traffic-button-${state} ${selected ? "traffic-button-selected" : ""}`}><span className={`traffic-icon ${copy.iconTone}`}>{copy.icon}</span><span><strong>{value}</strong><small>{copy.label}</small><em>{copy.detail}</em></span></button>;
}

function FamilyTabs({ family, setFamily, units, data }: { family: Family; setFamily: (value: Family) => void; units: StorageUnit[]; data: AppData }) {
  const storage = units.filter((unit) => unitFamily(data, unit) === "storage").length;
  const field = units.length - storage;
  return <div className="family-tabs" role="group" aria-label="Filtrar familia de sensor"><button type="button" aria-pressed={family === "all"} onClick={() => setFamily("all")}>Todos <span>{units.length}</span></button><button type="button" aria-pressed={family === "storage"} onClick={() => setFamily("storage")}><Factory size={15} /> SiloSensor <span>{storage}</span></button><button type="button" aria-pressed={family === "field"} onClick={() => setFamily("field")}><Sprout size={15} /> CampoSensor <span>{field}</span></button></div>;
}

function PremiumUnitCard({ data, unit, onOpen }: { data: AppData; unit: StorageUnit; onOpen: () => void }) {
  const family = unitFamily(data, unit);
  const state = unitState(data, unit);
  const readings = data.readings.filter((reading) => reading.storage_unit_id === unit.id).sort((a, b) => +new Date(a.timestamp) - +new Date(b.timestamp));
  const latest = readings.at(-1) || null;
  const chartData = sparkline(readings, family);
  const isField = family === "field";
  return (
    <button type="button" onClick={onOpen} className={`unit-product-card ${isField ? "unit-product-field" : "unit-product-storage"}`}>
      <div className="flex items-start justify-between gap-3"><div className="flex items-center gap-3"><span className="unit-family-icon">{isField ? <Leaf size={20} /> : <Factory size={20} />}</span><div><span className="unit-family-label">{isField ? "CampoSensor" : "SiloSensor"}</span><small>{isField ? "Campo" : "Postcosecha"}</small></div></div><span className={`compact-state compact-state-${state}`}>{stateCopy(state).label}</span></div>
      <h3 className="mt-5 text-xl font-black text-slate-950">{unit.name}</h3>
      <p className="mt-1 text-sm text-slate-500">{unit.crop_type || (isField ? "Parcela monitoreada" : "Almacenamiento monitoreado")}</p>
      <div className="mt-5 grid grid-cols-2 gap-3">
        <UnitMetric label={isField ? "Hum. suelo" : "Temp. grano"} value={metricValue(latest, isField ? "soil_moisture_percent" : "grain_temperature", isField ? "%" : " °C")} />
        <UnitMetric label={isField ? "Ambiente" : "Humedad"} value={metricValue(latest, isField ? "ambient_temperature" : "ambient_humidity", isField ? " °C" : "%")} />
      </div>
      <div className="mt-4 h-12 rounded-lg bg-white/60 px-2 py-1">{chartData.length >= 3 ? <ResponsiveContainer width="100%" height="100%"><LineChart data={chartData}><Line type="monotone" dataKey="value" stroke={isField ? "#0891b2" : "#0b8f68"} strokeWidth={2.3} dot={false} isAnimationActive={false} /></LineChart></ResponsiveContainer> : <span className="flex h-full items-center text-xs text-slate-400">No hay histórico suficiente.</span>}</div>
      <div className="mt-4 flex items-center justify-between border-t border-slate-200/70 pt-4 text-xs font-semibold text-slate-500"><span>{latest ? `Actualizado ${formatRelative(latest.timestamp)}` : "Esperando datos"}</span><span className="inline-flex items-center gap-1 font-black text-slate-800">Ver detalle <ArrowRight size={14} /></span></div>
    </button>
  );
}

function UnitMetric({ label, value }: { label: string; value: string }) {
  return <div><p className="text-lg font-black text-slate-950">{value}</p><p className="mt-0.5 text-[10px] font-black uppercase tracking-[0.1em] text-slate-400">{label}</p></div>;
}

export function unitFamily(data: AppData, unit: StorageUnit): Exclude<Family, "all"> {
  const devices = data.devices.filter((device) => device.storage_unit_id === unit.id);
  return unit.operation_type === "field" || devices.some((device) => device.device_type === "field_sensor") ? "field" : "storage";
}

export function unitState(data: AppData, unit: StorageUnit): RiskStatus {
  const status = data.insights.find((item) => item.storage_unit_id === unit.id)?.status;
  if (status === "critical") return "critical";
  if (status === "attention") return "warning";
  if (status === "normal") return "normal";
  return "no_data";
}

export function countStates(data: AppData, units: StorageUnit[]) {
  const counts = { normal: 0, warning: 0, critical: 0, no_data: 0 };
  units.forEach((unit) => { const state = unitState(data, unit); counts[state === "critical" || state === "warning" || state === "normal" ? state : "no_data"] += 1; });
  return counts;
}

function statePriority(state: RiskStatus) { return state === "critical" ? 0 : state === "warning" ? 1 : state === "normal" ? 2 : 3; }
function toggleState(current: StateFilter, next: RiskStatus): StateFilter { return current === next ? "all" : next; }
function stateCopy(state: RiskStatus) {
  if (state === "critical") return { label: "Crítico", title: "Atención inmediata", detail: "Existe al menos una condición crítica activa. Revisa la unidad afectada y confirma el seguimiento operativo." };
  if (state === "warning") return { label: "Precaución", title: "Hay algo que revisar", detail: "Una o más unidades requieren seguimiento preventivo con la evidencia disponible." };
  if (state === "normal") return { label: "Normal", title: "Todo estable", detail: "Las unidades con datos recientes se encuentran dentro de las condiciones operativas configuradas." };
  return { label: "Sin datos", title: "Esperando datos", detail: "Aún no hay telemetría reciente suficiente para evaluar la operación con confianza." };
}

function trafficCopy(state: RiskStatus) {
  if (state === "critical") return { label: "Crítico", detail: "Atender ahora", iconTone: "bg-red-100 text-red-700", icon: <AlertTriangle size={18} /> };
  if (state === "warning") return { label: "Precaución", detail: "Revisar pronto", iconTone: "bg-amber-100 text-amber-700", icon: <Activity size={18} /> };
  if (state === "normal") return { label: "Normal", detail: "Dentro de rango", iconTone: "bg-emerald-100 text-emerald-700", icon: <CheckCircle2 size={18} /> };
  return { label: "Sin datos", detail: "Sin telemetría", iconTone: "bg-slate-200 text-slate-600", icon: <CloudOff size={18} /> };
}

function greetingDetail(state: RiskStatus, noData: number) {
  if (state === "critical") return "Hay una condición que requiere atención inmediata.";
  if (state === "warning") return "Tienes unidades que requieren seguimiento preventivo.";
  if (state === "normal" && noData) return "La operación está estable, pero hay unidades sin datos recientes.";
  if (state === "normal") return "Tu operación está bajo control con la evidencia disponible.";
  return "Aún no hay datos recientes. Revisa la conexión de tus sensores.";
}

function sparkline(readings: Reading[], family: Exclude<Family, "all">) {
  const key = family === "field" ? "soil_moisture_percent" : "grain_temperature";
  return readings.slice(-18).map((reading) => ({ value: reading[key] })).filter((point) => typeof point.value === "number");
}

function metricValue(reading: Reading | null, key: "soil_moisture_percent" | "grain_temperature" | "ambient_temperature" | "ambient_humidity", suffix: string) {
  const value = reading?.[key];
  return typeof value === "number" ? `${value.toFixed(1)}${suffix}` : "Sin dato";
}

function formatRelative(value: string) {
  const minutes = Math.max(0, Math.round((Date.now() - new Date(value).getTime()) / 60000));
  if (minutes < 1) return "ahora";
  if (minutes < 60) return `hace ${minutes} min`;
  const hours = Math.round(minutes / 60);
  if (hours < 24) return `hace ${hours} h`;
  return `hace ${Math.round(hours / 24)} d`;
}
