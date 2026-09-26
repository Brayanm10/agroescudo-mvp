"use client";

import { useCallback, useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import Link from "next/link";
import { CloudRain, MapPinOff, Settings } from "lucide-react";
import { EmptyState } from "@/components/EmptyState";
import { ErrorState } from "@/components/ErrorState";
import { LoadingState } from "@/components/LoadingState";
import { getPluviometryMapSnapshot, getPluviometrySites } from "@/lib/api";
import { readSessionToken } from "@/lib/session";
import type { PluviometryMapSnapshot, PluviometrySite, UserRole } from "@/lib/types";
import { RainGaugeMap } from "./RainGaugeMap";
import { pluviometryQueryPath, rainGaugeDetailPath, resolveSelectedSite, STATUS_PRESENTATION } from "./map-model";

export function PluviometryMapView({ role }: { role?: UserRole }) {
  const router = useRouter();
  const [sites, setSites] = useState<PluviometrySite[]>([]);
  const [selectedSiteId, setSelectedSiteId] = useState<number | null>(null);
  const [snapshot, setSnapshot] = useState<PluviometryMapSnapshot | null>(null);
  const [sitesLoading, setSitesLoading] = useState(true);
  const [mapLoading, setMapLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const token = readSessionToken();
    if (!token) return;
    const controller = new AbortController();
    setSitesLoading(true);
    setError(null);
    void getPluviometrySites(token, controller.signal)
      .then((items) => {
        const requested = new URLSearchParams(window.location.search).get("predio");
        const selected = resolveSelectedSite(items, requested);
        setSites(items);
        setSelectedSiteId(selected?.id ?? null);
        if (selected && requested !== String(selected.id)) {
          window.history.replaceState(null, "", pluviometryQueryPath(selected.id));
        }
      })
      .catch((reason: unknown) => {
        if (reason instanceof DOMException && reason.name === "AbortError") return;
        setError(reason instanceof Error ? reason.message : "No se pudieron cargar los predios.");
      })
      .finally(() => {
        if (!controller.signal.aborted) setSitesLoading(false);
      });
    return () => controller.abort();
  }, []);

  useEffect(() => {
    if (selectedSiteId == null) {
      setSnapshot(null);
      return;
    }
    const token = readSessionToken();
    if (!token) return;
    const controller = new AbortController();
    setMapLoading(true);
    setError(null);
    setSnapshot(null);
    void getPluviometryMapSnapshot(token, selectedSiteId, controller.signal)
      .then(setSnapshot)
      .catch((reason: unknown) => {
        if (reason instanceof DOMException && reason.name === "AbortError") return;
        setError(reason instanceof Error ? reason.message : "No se pudo cargar el mapa del predio.");
      })
      .finally(() => {
        if (!controller.signal.aborted) setMapLoading(false);
      });
    return () => controller.abort();
  }, [selectedSiteId]);

  const selectSite = useCallback((siteId: number) => {
    setSelectedSiteId(siteId);
    window.history.replaceState(null, "", pluviometryQueryPath(siteId));
  }, []);
  const openDevice = useCallback((deviceId: number) => router.push(rainGaugeDetailPath(deviceId)), [router]);

  return (
    <PluviometryMapContent
      sites={sites}
      selectedSiteId={selectedSiteId}
      snapshot={snapshot}
      sitesLoading={sitesLoading}
      mapLoading={mapLoading}
      error={error}
      onSelectSite={selectSite}
      onOpenDevice={openDevice}
      canConfigure={role === "admin"}
    />
  );
}

type ContentProps = {
  sites: PluviometrySite[];
  selectedSiteId: number | null;
  snapshot: PluviometryMapSnapshot | null;
  sitesLoading: boolean;
  mapLoading: boolean;
  error: string | null;
  onSelectSite: (siteId: number) => void;
  onOpenDevice: (deviceId: number) => void;
  mapApiKey?: string | null;
  canConfigure?: boolean;
};

export function PluviometryMapContent({
  sites,
  selectedSiteId,
  snapshot,
  sitesLoading,
  mapLoading,
  error,
  onSelectSite,
  onOpenDevice,
  mapApiKey,
  canConfigure = false
}: ContentProps) {
  const devicesWithoutLocation = snapshot?.devices.filter((device) => device.latitude == null || device.longitude == null).length ?? 0;
  const devicesWithoutReadings = snapshot?.devices.filter((device) =>
    device.rain_today_mm == null && Object.values(device.latest).every((value) => value == null)
  ).length ?? 0;

  return (
    <section className="space-y-5" aria-labelledby="pluviometry-title">
      <div className="flex flex-col gap-4 sm:flex-row sm:items-end sm:justify-between">
        <div>
          <p className="section-kicker">Monitoreo meteorológico</p>
          <h1 id="pluviometry-title" className="section-title mt-1 text-2xl sm:text-3xl">Pluviometría</h1>
          <p className="section-subtitle">Monitoreo de lluvia y condiciones de campo en predios y parcelas</p>
        </div>
        <div className="flex w-full flex-col gap-2 sm:max-w-xs">
        {canConfigure ? (
          <Link href="/pluviometria/configuracion" className="btn-secondary gap-2 self-end"><Settings size={16} /> Configuración</Link>
        ) : null}
        <label>
          <span className="mb-1.5 block text-xs font-black uppercase tracking-[0.12em] text-slate-600">Predio</span>
          <select
            className="input"
            disabled={sitesLoading || sites.length === 0}
            aria-label="Seleccionar predio"
            value={selectedSiteId ?? ""}
            onChange={(event) => onSelectSite(Number(event.target.value))}
          >
            {sites.length === 0 ? <option value="">Selecciona un predio</option> : null}
            {sites.map((site) => <option key={site.id} value={site.id}>{site.name}</option>)}
          </select>
        </label>
        </div>
      </div>

      {sitesLoading ? <LoadingState label="Cargando predios autorizados" /> : null}
      {!sitesLoading && error ? <ErrorState message={error} onRetry={() => window.location.reload()} /> : null}
      {!sitesLoading && !error && sites.length === 0 ? (
        <EmptyState title="Sin predios disponibles" message="No tienes predios de campo asignados para consultar en este módulo." />
      ) : null}
      {!sitesLoading && !error && sites.length > 0 && mapLoading ? <LoadingState label="Cargando snapshot cartográfico" /> : null}

      {!sitesLoading && !error && !mapLoading && snapshot ? (
        <>
          <div className="grid gap-3 sm:grid-cols-3">
            <SummaryCard label="Parcelas autorizadas" value={snapshot.parcels.length} />
            <SummaryCard label="Pluviómetros" value={snapshot.devices.length} />
            <SummaryCard label="Sin ubicación" value={devicesWithoutLocation} />
          </div>
          {snapshot.parcels.length === 0 ? <NeutralNotice text="Este predio todavía no tiene parcelas de campo disponibles." /> : null}
          {snapshot.devices.length === 0 ? <NeutralNotice text="Este predio todavía no tiene pluviómetros registrados." /> : null}
          {devicesWithoutLocation > 0 ? <NeutralNotice text={`${devicesWithoutLocation} pluviómetro(s) no aparecen en el mapa porque no tienen ubicación configurada.`} icon="location" /> : null}
          {devicesWithoutReadings > 0 ? <NeutralNotice text={`${devicesWithoutReadings} pluviómetro(s) todavía no tienen lecturas meteorológicas.`} /> : null}

          <article className="panel overflow-hidden p-2 sm:p-3">
            <div className="mb-3 flex flex-col gap-3 px-2 pt-1 sm:flex-row sm:items-center sm:justify-between">
              <div className="flex items-center gap-2 text-sm font-bold text-slate-700">
                <CloudRain size={18} className="text-emerald-700" aria-hidden="true" />
                Vista satelital · {snapshot.site.name}
              </div>
              <div className="flex flex-wrap gap-3 text-[11px] font-bold text-slate-600" aria-label="Leyenda de estados">
                {Object.entries(STATUS_PRESENTATION).map(([status, presentation]) => (
                  <span key={status} className="inline-flex items-center gap-1.5">
                    <span className="h-2.5 w-2.5 rounded-full" style={{ backgroundColor: presentation.color }} />
                    {presentation.label}
                  </span>
                ))}
              </div>
            </div>
            <RainGaugeMap snapshot={snapshot} apiKey={mapApiKey} onOpenDevice={onOpenDevice} />
          </article>
        </>
      ) : null}
    </section>
  );
}

function SummaryCard({ label, value }: { label: string; value: number }) {
  return (
    <div className="rounded-xl border border-slate-200 bg-white px-4 py-3 shadow-soft">
      <p className="text-xs font-bold uppercase tracking-wide text-slate-500">{label}</p>
      <p className="mt-1 text-2xl font-black text-slate-950">{value}</p>
    </div>
  );
}

function NeutralNotice({ text, icon }: { text: string; icon?: "location" }) {
  return (
    <p className="flex items-center gap-2 rounded-xl border border-slate-200 bg-slate-50 px-4 py-3 text-sm text-slate-600">
      {icon === "location" ? <MapPinOff size={17} aria-hidden="true" /> : <CloudRain size={17} aria-hidden="true" />}
      {text}
    </p>
  );
}
