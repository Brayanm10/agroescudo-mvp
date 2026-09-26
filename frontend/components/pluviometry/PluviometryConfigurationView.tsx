"use client";

import Link from "next/link";
import { useCallback, useEffect, useMemo, useState } from "react";
import { AlertTriangle, Check, ChevronRight, CloudRain, LandPlot, MapPin, MapPinned, Pencil, Plus, RotateCcw, Save, Undo2, X } from "lucide-react";
import { EmptyState } from "@/components/EmptyState";
import { ErrorState } from "@/components/ErrorState";
import { LoadingState } from "@/components/LoadingState";
import { createAdminDevice, createAdminStorageUnit, getAdminCompanyFeatures, getAdminDevices, getSites, getStorageUnits, updateAdminDevice, updateAdminStorageUnit, updateSite } from "@/lib/api";
import type { BoundaryGeoJson, Device, GeoJsonPosition, Site, StorageUnit, UserRole } from "@/lib/types";
import { BoundaryEditorMap } from "./BoundaryEditorMap";
import { boundaryStatus, closePolygon, municipalityLabel, parcelAppearsOutside, pointInsideBoundary } from "./configuration-model";

type SiteDraft = Pick<Site, "name" | "location" | "municipality" | "latitude" | "longitude" | "timezone" | "address">;
type ParcelDraft = { name: string; crop_type: string; surface_hectares: string };
type DrawTarget = "site" | "parcel" | null;
type GaugeDraft = { name: string; external_id: string; storage_unit_id: number; interval: string; active: boolean; location: GeoJsonPosition | null };

const emptyParcel: ParcelDraft = { name: "", crop_type: "", surface_hectares: "" };

function siteDraft(site: Site): SiteDraft {
  return {
    name: site.name,
    location: site.location,
    municipality: site.municipality ?? null,
    latitude: site.latitude ?? null,
    longitude: site.longitude ?? null,
    timezone: site.timezone ?? "America/La_Paz",
    address: site.address ?? null
  };
}

export function PluviometryConfigurationView({ token, role }: { token: string; role: UserRole }) {
  if (role !== "admin") return <ConfigurationAccessDenied />;
  return <AdminConfigurationWorkspace token={token} />;
}

export function ConfigurationAccessDenied() {
  return (
    <section className="panel mx-auto max-w-2xl p-8 text-center" role="alert">
      <div className="premium-empty-icon"><MapPinned size={28} /></div>
      <h1 className="section-title">Configuración reservada para administración</h1>
      <p className="section-subtitle">Puedes continuar consultando los predios y la telemetría, pero tu rol no puede modificar límites geográficos.</p>
      <Link href="/pluviometria" className="btn-secondary mt-5">Volver a Pluviometría</Link>
    </section>
  );
}

function AdminConfigurationWorkspace({ token }: { token: string }) {
  const [sites, setSites] = useState<Site[]>([]);
  const [selectedSiteId, setSelectedSiteId] = useState<number | null>(null);
  const [parcels, setParcels] = useState<StorageUnit[]>([]);
  const [form, setForm] = useState<SiteDraft | null>(null);
  const [loading, setLoading] = useState(true);
  const [parcelsLoading, setParcelsLoading] = useState(false);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState<string | null>(null);
  const [drawTarget, setDrawTarget] = useState<DrawTarget>(null);
  const [vertices, setVertices] = useState<GeoJsonPosition[]>([]);
  const [draftBoundary, setDraftBoundary] = useState<BoundaryGeoJson | null>(null);
  const [selectedParcelId, setSelectedParcelId] = useState<number | null>(null);
  const [parcelForm, setParcelForm] = useState<ParcelDraft | null>(null);
  const [devices, setDevices] = useState<Device[]>([]);
  const [gaugeDraft, setGaugeDraft] = useState<GaugeDraft | null>(null);
  const [editingGaugeId, setEditingGaugeId] = useState<number | null>(null);
  const [selectingLocation, setSelectingLocation] = useState(false);
  const [pluviometryEnabled, setPluviometryEnabled] = useState(false);

  const selectedSite = useMemo(() => sites.find((site) => site.id === selectedSiteId) ?? null, [selectedSiteId, sites]);
  const selectedParcel = useMemo(() => parcels.find((parcel) => parcel.id === selectedParcelId) ?? null, [parcels, selectedParcelId]);
  const formDirty = Boolean(selectedSite && form && JSON.stringify(form) !== JSON.stringify(siteDraft(selectedSite)));
  const hasUnsavedChanges = formDirty || drawTarget !== null || parcelForm !== null || gaugeDraft !== null;
  const siteGauges = useMemo(() => devices.filter((device) => device.device_type === "rain_gauge" && device.site_id === selectedSiteId), [devices, selectedSiteId]);

  const loadSites = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const items = await getSites(token);
      setSites(items);
      setSelectedSiteId((current) => current && items.some((site) => site.id === current) ? current : items[0]?.id ?? null);
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : "No se pudieron cargar los predios.");
    } finally {
      setLoading(false);
    }
  }, [token]);

  useEffect(() => { void loadSites(); }, [loadSites]);

  useEffect(() => {
    if (!selectedSite) { setForm(null); setParcels([]); setDevices([]); return; }
    setForm(siteDraft(selectedSite));
    setDrawTarget(null); setVertices([]); setDraftBoundary(null); setParcelForm(null); setSelectedParcelId(null);
    const controller = new AbortController();
    setParcelsLoading(true); setError(null);
    void Promise.all([getStorageUnits(token, selectedSite.id, controller.signal), getAdminDevices(token, undefined, controller.signal), getAdminCompanyFeatures(token, selectedSite.company_id)])
      .then(([items, deviceItems, features]) => { setParcels(items.filter((item) => item.operation_type === "field")); setDevices(deviceItems); setPluviometryEnabled(features.some((feature) => feature.feature_code === "PLUVIOMETRY" && feature.enabled)); })
      .catch((reason: unknown) => { if (!(reason instanceof DOMException && reason.name === "AbortError")) setError(reason instanceof Error ? reason.message : "No se pudieron cargar las parcelas."); })
      .finally(() => { if (!controller.signal.aborted) setParcelsLoading(false); });
    return () => controller.abort();
  }, [selectedSite, token]);

  useEffect(() => {
    const warn = (event: BeforeUnloadEvent) => { if (hasUnsavedChanges) event.preventDefault(); };
    window.addEventListener("beforeunload", warn);
    return () => window.removeEventListener("beforeunload", warn);
  }, [hasUnsavedChanges]);

  function resetDrawing() { setDrawTarget(null); setVertices([]); setDraftBoundary(null); }

  function cancelChanges() {
    if (selectedSite) setForm(siteDraft(selectedSite));
    setParcelForm(null); setGaugeDraft(null); setEditingGaugeId(null); setSelectingLocation(false); setSelectedParcelId(null); resetDrawing(); setError(null); setSuccess(null);
  }

  function beginNewGauge() {
    if (!pluviometryEnabled) { setError("El módulo Pluviometría no está habilitado para esta empresa."); return; }
    if (!selectedParcel) { setError("Selecciona primero la parcela donde se instalará el pluviómetro."); return; }
    setGaugeDraft({ name: "", external_id: "", storage_unit_id: selectedParcel.id, interval: "15", active: true, location: null });
    setEditingGaugeId(null); setSelectingLocation(true); setSuccess(null); setError(null);
  }

  function beginEditGauge(device: Device) {
    setSelectedParcelId(device.storage_unit_id);
    setGaugeDraft({ name: device.name, external_id: device.external_id, storage_unit_id: device.storage_unit_id, interval: String(device.expected_reading_interval_minutes ?? 15), active: device.is_active, location: device.latitude != null && device.longitude != null ? [device.longitude, device.latitude] : null });
    setEditingGaugeId(device.id); setSelectingLocation(false); setSuccess(null); setError(null);
  }

  function selectGaugeLocation(position: GeoJsonPosition) {
    if (!gaugeDraft) return;
    const parcel = parcels.find((item) => item.id === gaugeDraft.storage_unit_id);
    if (!pointInsideBoundary(position, parcel?.boundary_geojson)) { setError("La ubicación está fuera del límite de la parcela seleccionada."); return; }
    setGaugeDraft({ ...gaugeDraft, location: position }); setSelectingLocation(false); setError(null);
  }

  async function saveGauge() {
    if (!selectedSite || !gaugeDraft) return;
    const parcel = parcels.find((item) => item.id === gaugeDraft.storage_unit_id);
    const interval = Number(gaugeDraft.interval);
    if (!parcel || parcel.site_id !== selectedSite.id || parcel.company_id !== selectedSite.company_id) { setError("La parcela no corresponde al predio y empresa seleccionados."); return; }
    if (!gaugeDraft.name.trim() || !gaugeDraft.external_id.trim()) { setError("Completa el nombre y el ID físico."); return; }
    if (!Number.isInteger(interval) || interval < 1 || interval > 1440) { setError("El intervalo debe ser un número entero entre 1 y 1440 minutos."); return; }
    if (!gaugeDraft.location) { setError("Selecciona la ubicación del pluviómetro en el mapa."); return; }
    if (!pointInsideBoundary(gaugeDraft.location, parcel.boundary_geojson)) { setError("La ubicación debe quedar dentro de la parcela seleccionada."); return; }
    const existing = editingGaugeId ? devices.find((item) => item.id === editingGaugeId) : null;
    const moved = Boolean(existing && (existing.storage_unit_id !== parcel.id || existing.longitude !== gaugeDraft.location[0] || existing.latitude !== gaugeDraft.location[1]));
    const question = moved ? "Cambiarás la ubicación o parcela del pluviómetro. Su historial se conservará. ¿Confirmas?" : `¿Confirmas ${existing ? "los cambios" : "la instalación"} del pluviómetro ${gaugeDraft.external_id}?`;
    if (!window.confirm(question)) return;
    setSaving(true); setError(null); setSuccess(null);
    try {
      const common = { storage_unit_id: parcel.id, name: gaugeDraft.name.trim(), latitude: gaugeDraft.location[1], longitude: gaugeDraft.location[0], expected_reading_interval_minutes: interval, is_active: gaugeDraft.active };
      const saved = existing
        ? await updateAdminDevice(token, existing.id, common)
        : await createAdminDevice(token, { ...common, company_id: selectedSite.company_id, site_id: selectedSite.id, external_id: gaugeDraft.external_id.trim(), device_type: "rain_gauge", template_code: "RAIN_GAUGE_BASE" });
      setDevices((items) => existing ? items.map((item) => item.id === saved.id ? saved : item) : [...items, saved]);
      setGaugeDraft(null); setEditingGaugeId(null); setSelectingLocation(false); setSelectedParcelId(saved.storage_unit_id);
      setSuccess(existing ? "Pluviómetro actualizado; el historial fue preservado." : "Pluviómetro instalado. Quedará offline hasta recibir su primera lectura.");
    } catch (reason) { setError(reason instanceof Error ? reason.message : "No se pudo guardar el pluviómetro."); }
    finally { setSaving(false); }
  }

  function beginSiteBoundary() {
    setDrawTarget("site"); setVertices([]); setDraftBoundary(null); setParcelForm(null); setSuccess(null);
  }

  function beginNewParcel() {
    setParcelForm({ ...emptyParcel }); setSelectedParcelId(null); setDrawTarget("parcel"); setVertices([]); setDraftBoundary(null); setSuccess(null);
  }

  function beginEditParcel(parcel: StorageUnit) {
    setSelectedParcelId(parcel.id);
    setParcelForm({ name: parcel.name, crop_type: parcel.crop_type ?? "", surface_hectares: parcel.surface_hectares?.toString() ?? "" });
    setDrawTarget("parcel"); setVertices([]); setDraftBoundary(null); setSuccess(null);
  }

  function addVertex(position: GeoJsonPosition) {
    if (!drawTarget || draftBoundary) return;
    setVertices((current) => [...current, position]);
  }

  function finishPolygon() {
    const geometry = closePolygon(vertices);
    if (!geometry) { setError("Marca al menos tres vértices distintos antes de cerrar el polígono."); return; }
    setDraftBoundary(geometry); setError(null);
  }

  async function saveSite() {
    if (!selectedSite || !form) return;
    if (drawTarget === "site" && !draftBoundary) { setError("Cierra el nuevo polígono antes de guardar."); return; }
    if (drawTarget === "site" && selectedSite.boundary_geojson && !window.confirm("Reemplazarás el límite actual del predio. ¿Deseas guardar el nuevo polígono?")) return;
    setSaving(true); setError(null); setSuccess(null);
    try {
      const updated = await updateSite(token, selectedSite.id, { ...form, ...(drawTarget === "site" ? { boundary_geojson: draftBoundary } : {}) });
      setSites((items) => items.map((site) => site.id === updated.id ? updated : site));
      setForm(siteDraft(updated)); resetDrawing(); setSuccess("Predio guardado exitosamente.");
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : "No se pudo guardar el predio.");
    } finally { setSaving(false); }
  }

  async function saveParcel() {
    if (!selectedSite || !parcelForm) return;
    if (!parcelForm.name.trim()) { setError("Ingresa el nombre de la parcela."); return; }
    if (!draftBoundary) { setError("Dibuja y cierra el límite de la parcela antes de guardar."); return; }
    const surface = parcelForm.surface_hectares.trim() ? Number(parcelForm.surface_hectares) : null;
    if (surface !== null && (!Number.isFinite(surface) || surface <= 0)) { setError("La superficie debe ser un número mayor que cero."); return; }
    setSaving(true); setError(null); setSuccess(null);
    try {
      const payload = { name: parcelForm.name.trim(), crop_type: parcelForm.crop_type.trim() || null, surface_hectares: surface, boundary_geojson: draftBoundary };
      const saved = selectedParcel
        ? await updateAdminStorageUnit(token, selectedParcel.id, payload)
        : await createAdminStorageUnit(token, { company_id: selectedSite.company_id, site_id: selectedSite.id, unit_type: "field", operation_type: "field", capacity_tons: null, ...payload });
      setParcels((items) => selectedParcel ? items.map((parcel) => parcel.id === saved.id ? saved : parcel) : [...items, saved]);
      setSelectedParcelId(saved.id); setParcelForm(null); resetDrawing(); setSuccess(selectedParcel ? "Parcela actualizada exitosamente." : "Parcela creada exitosamente.");
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : "No se pudo guardar la parcela.");
    } finally { setSaving(false); }
  }

  if (loading) return <LoadingState label="Cargando configuración de predios" />;
  if (error && sites.length === 0) return <ErrorState message={error} onRetry={loadSites} />;
  if (sites.length === 0) return <EmptyState title="Sin predios disponibles" message="Crea un predio antes de configurar límites y parcelas." />;

  const outsideWarning = draftBoundary && drawTarget === "parcel" ? parcelAppearsOutside(draftBoundary, selectedSite?.boundary_geojson) : false;

  return (
    <section className="space-y-5" aria-labelledby="configuration-title">
      <header className="flex flex-col gap-4 sm:flex-row sm:items-end sm:justify-between">
        <div>
          <nav className="mb-2 flex items-center gap-1 text-xs font-bold text-slate-500" aria-label="Migas de pan"><Link href="/pluviometria">Pluviometría</Link><ChevronRight size={14} /><span>Configuración</span></nav>
          <p className="section-kicker">Administración cartográfica</p>
          <h1 id="configuration-title" className="section-title mt-1 text-2xl sm:text-3xl">Predios y parcelas</h1>
          <p className="section-subtitle">Define límites sobre el mapa sin editar GeoJSON manualmente.</p>
        </div>
        <Link href="/pluviometria" className="btn-secondary">Volver al mapa</Link>
      </header>

      {error ? <ErrorState message={error} onRetry={() => setError(null)} /> : null}
      {success ? <div className="flex items-center gap-2 rounded-xl border border-emerald-200 bg-emerald-50 px-4 py-3 text-sm font-bold text-emerald-900" role="status"><Check size={17} />{success}</div> : null}
      {hasUnsavedChanges ? <div className="flex items-center gap-2 rounded-xl border border-amber-200 bg-amber-50 px-4 py-3 text-sm font-bold text-amber-900" role="status"><AlertTriangle size={17} />Cambios sin guardar</div> : null}

      <div className="grid gap-5 xl:grid-cols-[22rem_minmax(0,1fr)]">
        <aside className="space-y-4">
          <div className="panel p-4">
            <label className="text-xs font-black uppercase tracking-wide text-slate-600">Predio</label>
            <select className="input mt-2" value={selectedSiteId ?? ""} onChange={(event) => { if (!hasUnsavedChanges || window.confirm("Hay cambios sin guardar. ¿Deseas descartarlos?")) setSelectedSiteId(Number(event.target.value)); }}>
              {sites.map((site) => <option key={site.id} value={site.id}>{site.name}</option>)}
            </select>
            <div className="mt-3 grid gap-2">
              {sites.map((site) => <button key={site.id} type="button" onClick={() => setSelectedSiteId(site.id)} className={`rounded-xl border p-3 text-left ${site.id === selectedSiteId ? "border-emerald-400 bg-emerald-50" : "border-slate-200 bg-white"}`}><strong className="block text-sm text-slate-950">{site.name}</strong><span className="mt-1 block text-xs text-slate-500">{municipalityLabel(site.municipality)} · {boundaryStatus(site.boundary_geojson)}</span></button>)}
            </div>
          </div>

          {selectedSite && form ? <div className="panel space-y-3 p-4">
            <div><p className="section-kicker">Datos básicos</p><h2 className="mt-1 font-black text-slate-950">Editar predio</h2></div>
            <TextField label="Nombre" value={form.name} onChange={(value) => setForm({ ...form, name: value })} />
            <TextField label="Referencia / dirección" value={form.location ?? ""} onChange={(value) => setForm({ ...form, location: value || null })} />
            <TextField label="Municipio" value={form.municipality ?? ""} onChange={(value) => setForm({ ...form, municipality: value || null })} />
            <div className="grid grid-cols-2 gap-2"><NumberField label="Latitud" value={form.latitude} onChange={(value) => setForm({ ...form, latitude: value })} /><NumberField label="Longitud" value={form.longitude} onChange={(value) => setForm({ ...form, longitude: value })} /></div>
            <TextField label="Zona horaria" value={form.timezone ?? ""} onChange={(value) => setForm({ ...form, timezone: value })} />
            <button type="button" className="btn-secondary w-full gap-2" onClick={beginSiteBoundary}><Pencil size={15} />{selectedSite.boundary_geojson ? "Editar límite" : "Definir límite"}</button>
            <div className="flex gap-2"><button type="button" className="btn-primary flex-1 gap-2" disabled={saving || (drawTarget === "site" && !draftBoundary)} onClick={saveSite}><Save size={15} />{saving ? "Guardando" : "Guardar predio"}</button><button type="button" className="btn-secondary" disabled={!hasUnsavedChanges} onClick={cancelChanges}>Cancelar</button></div>
          </div> : null}

          <div className="panel p-4">
            <div className="flex items-center justify-between gap-2"><div><p className="section-kicker">Parcelas</p><h2 className="mt-1 font-black text-slate-950">{parcels.length} registradas</h2></div><button type="button" className="btn-secondary gap-1" onClick={beginNewParcel}><Plus size={15} />Nueva</button></div>
            {parcelsLoading ? <p className="mt-4 text-sm text-slate-500">Cargando parcelas…</p> : null}
            {!parcelsLoading && parcels.length === 0 ? <p className="mt-4 rounded-xl border border-dashed border-slate-300 p-4 text-sm text-slate-500">Este predio todavía no tiene parcelas.</p> : null}
            <div className="mt-3 space-y-2">{parcels.map((parcel) => <div key={parcel.id} className={`rounded-xl border p-3 ${selectedParcelId === parcel.id ? "border-amber-400 bg-amber-50" : "border-slate-200"}`}><button type="button" onClick={() => setSelectedParcelId(parcel.id)} className="w-full text-left"><span className="flex items-center justify-between gap-2"><strong className="text-sm text-slate-950">{parcel.name}</strong><LandPlot size={16} /></span><span className="mt-1 block text-xs text-slate-500">{parcel.surface_hectares ? `${parcel.surface_hectares.toLocaleString("es-BO")} ha` : "Sin superficie"} · {boundaryStatus(parcel.boundary_geojson)}</span></button>{selectedParcelId === parcel.id ? <button type="button" onClick={() => beginEditParcel(parcel)} className="mt-2 text-xs font-black text-emerald-800">Editar parcela</button> : null}</div>)}</div>
          </div>

          {parcelForm ? <div className="panel space-y-3 p-4">
            <div className="flex items-center justify-between"><h2 className="font-black text-slate-950">{selectedParcel ? "Editar parcela" : "Nueva parcela"}</h2><button type="button" aria-label="Cerrar formulario de parcela" onClick={cancelChanges}><X size={18} /></button></div>
            <TextField label="Nombre" value={parcelForm.name} onChange={(value) => setParcelForm({ ...parcelForm, name: value })} />
            <TextField label="Cultivo" value={parcelForm.crop_type} onChange={(value) => setParcelForm({ ...parcelForm, crop_type: value })} />
            <TextField label="Superficie (ha)" type="number" value={parcelForm.surface_hectares} onChange={(value) => setParcelForm({ ...parcelForm, surface_hectares: value })} />
            <p className="text-xs leading-5 text-slate-500">Dibuja el polígono en el mapa, revísalo y luego guarda.</p>
            <button type="button" className="btn-primary w-full gap-2" disabled={saving || !draftBoundary} onClick={saveParcel}><Save size={15} />{saving ? "Guardando" : "Guardar parcela"}</button>
          </div> : null}

          <div className="panel p-4">
            <div className="flex items-center justify-between gap-2"><div><p className="section-kicker">Pluviómetros</p><h2 className="mt-1 font-black text-slate-950">{siteGauges.length} instalados</h2></div><button type="button" className="btn-primary gap-1" disabled={!pluviometryEnabled} onClick={beginNewGauge}><Plus size={15} />Añadir pluviómetro</button></div>
            {!pluviometryEnabled ? <p className="mt-3 rounded-lg bg-slate-100 px-3 py-2 text-xs font-bold text-slate-600">Módulo Pluviometría no habilitado para esta empresa.</p> : null}
            {!selectedParcel ? <p className="mt-3 text-xs text-slate-500">Selecciona una parcela para instalar un equipo.</p> : null}
            <div className="mt-3 space-y-2">{siteGauges.map((device) => <button key={device.id} type="button" onClick={() => beginEditGauge(device)} className={`w-full rounded-xl border p-3 text-left ${editingGaugeId === device.id ? "border-orange-400 bg-orange-50" : "border-slate-200 bg-white"}`}><span className="flex items-center justify-between gap-2"><strong className="text-sm text-slate-950">{device.name}</strong><CloudRain size={16} className={device.is_active ? "text-emerald-700" : "text-slate-400"} /></span><span className="mt-1 block text-xs text-slate-500">{device.external_id} · {device.last_seen_at ? "con lecturas" : "offline · esperando primera lectura"}</span></button>)}</div>
          </div>

          {gaugeDraft ? <div className="panel space-y-3 p-4">
            <div className="flex items-center justify-between"><div><p className="section-kicker">{editingGaugeId ? "Edición segura" : "Nueva instalación"}</p><h2 className="mt-1 font-black text-slate-950">{editingGaugeId ? gaugeDraft.external_id : "Configurar equipo"}</h2></div><button type="button" aria-label="Cerrar formulario de pluviómetro" onClick={cancelChanges}><X size={18} /></button></div>
            <TextField label="Nombre" value={gaugeDraft.name} onChange={(name) => setGaugeDraft({ ...gaugeDraft, name })} />
            <label className="block text-xs font-bold text-slate-600">ID físico<input className="input mt-1" value={gaugeDraft.external_id} readOnly={editingGaugeId !== null} onChange={(event) => setGaugeDraft({ ...gaugeDraft, external_id: event.target.value })} /></label>
            <label className="block text-xs font-bold text-slate-600">Parcela<select className="input mt-1" value={gaugeDraft.storage_unit_id} onChange={(event) => { const storageUnitId = Number(event.target.value); setSelectedParcelId(storageUnitId); setGaugeDraft({ ...gaugeDraft, storage_unit_id: storageUnitId, location: null }); setSelectingLocation(true); }}>{parcels.map((parcel) => <option key={parcel.id} value={parcel.id}>{parcel.name}</option>)}</select></label>
            <label className="block text-xs font-bold text-slate-600">Intervalo esperado (min)<input className="input mt-1" type="number" min="1" max="1440" value={gaugeDraft.interval} onChange={(event) => setGaugeDraft({ ...gaugeDraft, interval: event.target.value })} /></label>
            <label className="flex items-center gap-2 text-sm font-bold text-slate-700"><input type="checkbox" checked={gaugeDraft.active} onChange={(event) => setGaugeDraft({ ...gaugeDraft, active: event.target.checked })} />Equipo activo</label>
            <div className="rounded-xl bg-slate-50 p-3 text-xs text-slate-600"><strong className="block text-slate-900">Predio: {selectedSite?.name}</strong><span>Plantilla: RAIN_GAUGE_BASE</span><br /><span>{gaugeDraft.location ? `${gaugeDraft.location[1].toFixed(6)}, ${gaugeDraft.location[0].toFixed(6)}` : "Ubicación pendiente"}</span></div>
            <button type="button" className="btn-secondary w-full gap-2" onClick={() => setSelectingLocation(true)}><MapPin size={15} />{gaugeDraft.location ? "Volver a seleccionar ubicación" : "Seleccionar ubicación en mapa"}</button>
            <button type="button" className="btn-primary w-full gap-2" disabled={saving || !gaugeDraft.location} onClick={saveGauge}><Save size={15} />{saving ? "Guardando" : editingGaugeId ? "Guardar cambios" : "Confirmar e instalar"}</button>
          </div> : null}
        </aside>

        <div className="panel overflow-hidden p-3">
          <div className="mb-3 flex flex-wrap items-center justify-between gap-3 px-1">
            <div><p className="text-sm font-black text-slate-950">Mapa satelital · {selectedSite?.name}</p><p className="text-xs text-slate-500">Predio blanco · parcela seleccionada ámbar · dibujo cian</p></div>
            {drawTarget ? <div className="flex flex-wrap gap-2"><button type="button" className="btn-secondary gap-1" disabled={!vertices.length || Boolean(draftBoundary)} onClick={() => setVertices((current) => current.slice(0, -1))}><Undo2 size={15} />Deshacer</button><button type="button" className="btn-secondary gap-1" disabled={vertices.length < 3 || Boolean(draftBoundary)} onClick={finishPolygon}><RotateCcw size={15} />Cerrar polígono</button><button type="button" className="btn-secondary" onClick={cancelChanges}>Cancelar cambios</button></div> : null}
          </div>
          {drawTarget && !draftBoundary ? <p className="mb-3 rounded-lg bg-cyan-50 px-3 py-2 text-xs font-bold text-cyan-900">Haz clic en el mapa para marcar los vértices. Necesitas al menos tres.</p> : null}
          {selectingLocation ? <p className="mb-3 rounded-lg bg-orange-50 px-3 py-2 text-xs font-bold text-orange-900">Haz clic dentro de la parcela seleccionada para ubicar el pluviómetro. Puedes volver a seleccionarlo antes de guardar.</p> : null}
          {outsideWarning ? <p className="mb-3 rounded-lg border border-amber-200 bg-amber-50 px-3 py-2 text-xs font-bold text-amber-900">Advertencia: parte de la parcela parece quedar fuera del límite del predio.</p> : null}
          <BoundaryEditorMap siteBoundary={selectedSite?.boundary_geojson ?? null} parcels={parcels} selectedParcelId={selectedParcelId} draftBoundary={draftBoundary} draftVertices={vertices} drawing={drawTarget !== null && !draftBoundary} onAddVertex={addVertex} devices={siteGauges} provisionalLocation={gaugeDraft?.location ?? null} selectingLocation={selectingLocation} onSelectLocation={selectGaugeLocation} />
          <p className="mt-3 text-xs text-slate-500 sm:hidden">Para editar polígonos con mayor precisión recomendamos una pantalla más grande.</p>
          <p className="mt-2 text-xs text-slate-500">El editor crea polígonos simples. Los límites MultiPolygon existentes se conservan y visualizan sin alteración mientras no los reemplaces.</p>
        </div>
      </div>
    </section>
  );
}

function TextField({ label, value, onChange, type = "text" }: { label: string; value: string; onChange: (value: string) => void; type?: string }) {
  return <label className="block text-xs font-bold text-slate-600">{label}<input className="input mt-1" type={type} value={value} onChange={(event) => onChange(event.target.value)} /></label>;
}

function NumberField({ label, value, onChange }: { label: string; value: number | null | undefined; onChange: (value: number | null) => void }) {
  return <label className="block text-xs font-bold text-slate-600">{label}<input className="input mt-1" type="number" step="any" value={value ?? ""} onChange={(event) => onChange(event.target.value === "" ? null : Number(event.target.value))} /></label>;
}
