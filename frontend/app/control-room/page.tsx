"use client";

import { useEffect, useMemo, useState } from "react";
import { AlertTriangle, Battery, Clock3, ExternalLink, Pause, Play, Radio, ShieldCheck, Wifi } from "lucide-react";
import { ApiError, getControlCenterSummary } from "@/lib/api";
import { formatDateTime, formatNumber } from "@/lib/format";
import type { ControlCenterSummary } from "@/lib/types";

const TOKEN_KEY = "agroescudo_token";

export default function ControlRoomPage() {
  const [summary, setSummary] = useState<ControlCenterSummary | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [paused, setPaused] = useState(false);
  const [dark, setDark] = useState(true);
  const [updatedAt, setUpdatedAt] = useState<string | null>(null);

  async function refresh() {
    const token = window.localStorage.getItem(TOKEN_KEY);
    if (!token) {
      setError("No hay sesion activa. Inicia sesion en el dashboard y vuelve a abrir Sala de Control.");
      return;
    }
    try {
      setError(null);
      const payload = await getControlCenterSummary(token);
      setSummary(payload);
      setUpdatedAt(new Date().toISOString());
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "No se pudo actualizar la Sala de Control.");
    }
  }

  useEffect(() => {
    refresh();
  }, []);

  useEffect(() => {
    if (paused) return;
    const handle = window.setInterval(refresh, 45000);
    return () => window.clearInterval(handle);
  }, [paused]);

  const tone = useMemo(() => {
    if (!summary) return "neutral";
    if (summary.status === "CRITICA") return "critical";
    if (summary.status === "ATENCION") return "warning";
    if (summary.status === "SIN_DATOS") return "neutral";
    return "normal";
  }, [summary]);

  const surface = dark ? "bg-[#031f19] text-white" : "bg-slate-50 text-slate-950";
  const card = dark ? "border-white/10 bg-white/[0.07]" : "border-slate-200 bg-white";
  const muted = dark ? "text-emerald-50/70" : "text-slate-500";

  return (
    <main className={`min-h-screen overflow-hidden ${surface}`}>
      <div className="absolute inset-0 bg-[linear-gradient(rgba(255,255,255,0.035)_1px,transparent_1px),linear-gradient(90deg,rgba(255,255,255,0.035)_1px,transparent_1px)] bg-[size:48px_48px]" />
      <section className="relative mx-auto flex min-h-screen max-w-[1920px] flex-col p-6">
        <header className={`flex items-center justify-between rounded-2xl border px-5 py-4 shadow-2xl ${card}`}>
          <div className="flex items-center gap-4">
            <img src="/brand/shield-transparent.png" alt="" className="h-14 w-14 rounded-xl bg-white p-1 object-contain" />
            <div>
              <p className="text-xs font-black uppercase tracking-[0.2em] text-amber-300">AgroEscudo Control Room</p>
              <h1 className="text-3xl font-black tracking-tight">Sala de Control Operativa</h1>
            </div>
          </div>
          <div className="flex items-center gap-2">
            <button type="button" onClick={() => setPaused((value) => !value)} className={`rounded-xl border px-4 py-3 text-sm font-black ${card}`}>
              {paused ? <Play className="mr-2 inline" size={16} /> : <Pause className="mr-2 inline" size={16} />}
              {paused ? "Reanudar" : "Pausar"}
            </button>
            <button type="button" onClick={() => setDark((value) => !value)} className={`rounded-xl border px-4 py-3 text-sm font-black ${card}`}>
              {dark ? "Modo claro" : "Modo oscuro"}
            </button>
            <a href="/" className={`rounded-xl border px-4 py-3 text-sm font-black ${card}`}>
              <ExternalLink className="mr-2 inline" size={16} /> Dashboard
            </a>
          </div>
        </header>

        {error ? (
          <div className="mt-5 rounded-2xl border border-red-300 bg-red-50 p-5 text-red-950">
            <p className="font-black">No se pudo cargar Sala de Control</p>
            <p className="mt-2 whitespace-pre-line text-sm">{error}</p>
            <button type="button" onClick={refresh} className="mt-4 rounded-xl bg-red-700 px-4 py-2 text-sm font-black text-white">Reintentar</button>
          </div>
        ) : null}

        <div className="grid flex-1 gap-5 py-5 xl:grid-cols-[0.85fr_1.15fr]">
          <section className={`rounded-3xl border p-7 shadow-2xl ${card}`}>
            <p className={`text-xs font-black uppercase tracking-[0.2em] ${muted}`}>Indice Operativo de Proteccion</p>
            <div className="mt-6 flex items-end justify-between gap-4">
              <div>
                <p className={`text-[120px] font-black leading-none tracking-tight ${statusText(tone)}`}>{summary?.score ?? "--"}</p>
                <p className={`mt-2 text-3xl font-black ${statusText(tone)}`}>{summary?.status?.replace("_", " ") ?? "SIN DATOS"}</p>
              </div>
              <ShieldCheck className={statusText(tone)} size={96} />
            </div>
            <p className={`mt-6 max-w-2xl text-lg leading-8 ${muted}`}>
              Vista 16:9 para sala de planta: estado de sitios, alertas, sensores y prioridades. Actualizacion automatica cada 45 segundos.
            </p>
            <div className="mt-8 grid grid-cols-3 gap-3">
              <RoomKpi label="Unidades" value={String(summary?.kpis.storage_units ?? 0)} icon={Radio} card={card} />
              <RoomKpi label="Alertas" value={String(summary?.kpis.active_alerts ?? 0)} icon={AlertTriangle} card={card} />
              <RoomKpi label="Lecturas 24h" value={String(summary?.kpis.readings_24h ?? 0)} icon={Clock3} card={card} />
            </div>
            <p className={`mt-6 text-sm ${muted}`}>
              Datos actualizados: {updatedAt ? formatDateTime(updatedAt) : "pendiente"} · API: {summary?.formula_version ?? "sin formula"}
            </p>
          </section>

          <section className="grid gap-5">
            <div className={`rounded-3xl border p-5 shadow-2xl ${card}`}>
              <p className={`text-xs font-black uppercase tracking-[0.2em] ${muted}`}>Prioridades activas</p>
              <div className="mt-4 grid gap-3 lg:grid-cols-3">
                {(summary?.priorities.length ? summary.priorities.slice(0, 3) : [{ title: "Operacion estable", detail: "Sin prioridades criticas al momento.", severity: "normal" }]).map((priority, index) => (
                  <article key={`${priority.title}-${index}`} className={`rounded-2xl border p-4 ${card}`}>
                    <p className="text-[10px] font-black uppercase tracking-[0.18em] text-amber-300">{priority.severity}</p>
                    <h2 className="mt-2 text-xl font-black">{priority.title}</h2>
                    <p className={`mt-2 text-sm leading-6 ${muted}`}>{priority.detail}</p>
                  </article>
                ))}
              </div>
            </div>

            <div className="grid gap-5 xl:grid-cols-2">
              <div className={`rounded-3xl border p-5 shadow-2xl ${card}`}>
                <p className={`text-xs font-black uppercase tracking-[0.2em] ${muted}`}>Estado por sitio</p>
                <div className="mt-4 space-y-3">
                  {summary?.sites.slice(0, 6).map((site) => (
                    <div key={site.site_id} className={`rounded-2xl border p-4 ${card}`}>
                      <div className="flex items-center justify-between">
                        <p className="text-lg font-black">{site.site_name}</p>
                        <span className={`rounded-full px-3 py-1 text-xs font-black ${siteBadge(site.status)}`}>{site.status}</span>
                      </div>
                      <div className="mt-3 h-2 overflow-hidden rounded-full bg-white/20">
                        <div className="h-full rounded-full bg-emerald-400" style={{ width: `${site.score}%` }} />
                      </div>
                      <p className={`mt-2 text-sm ${muted}`}>{site.storage_units} unidad(es) · {site.active_alerts} alerta(s)</p>
                    </div>
                  ))}
                </div>
              </div>

              <div className={`rounded-3xl border p-5 shadow-2xl ${card}`}>
                <p className={`text-xs font-black uppercase tracking-[0.2em] ${muted}`}>Salud de dispositivos</p>
                <div className="mt-4 space-y-3">
                  {summary?.device_health.slice(0, 7).map((device) => (
                    <div key={device.device_id} className={`grid grid-cols-[1fr_auto_auto] items-center gap-3 rounded-2xl border p-3 ${card}`}>
                      <div>
                        <p className="font-black">{device.external_id}</p>
                        <p className={`text-xs ${muted}`}>{device.last_seen_at ? formatDateTime(device.last_seen_at) : "sin lectura"}</p>
                      </div>
                      <div className="flex items-center gap-1 text-sm font-black">
                        <Battery size={16} /> {device.battery_voltage ? formatNumber(device.battery_voltage, " V") : "--"}
                      </div>
                      <div className="flex items-center gap-1 text-sm font-black">
                        <Wifi size={16} /> {device.signal_quality ?? "--"}
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            </div>
          </section>
        </div>
      </section>
    </main>
  );
}

function RoomKpi({ label, value, icon: Icon, card }: { label: string; value: string; icon: typeof Radio; card: string }) {
  return (
    <div className={`rounded-2xl border p-4 ${card}`}>
      <Icon size={22} className="text-amber-300" />
      <p className="mt-3 text-3xl font-black">{value}</p>
      <p className="text-xs font-black uppercase tracking-[0.16em] opacity-65">{label}</p>
    </div>
  );
}

function statusText(tone: string) {
  if (tone === "critical") return "text-red-300";
  if (tone === "warning") return "text-amber-300";
  if (tone === "normal") return "text-emerald-300";
  return "text-slate-300";
}

function siteBadge(status: string) {
  if (status === "CRITICA") return "bg-red-100 text-red-800";
  if (status === "ATENCION") return "bg-amber-100 text-amber-800";
  if (status === "PROTEGIDA") return "bg-emerald-100 text-emerald-800";
  return "bg-slate-100 text-slate-700";
}
