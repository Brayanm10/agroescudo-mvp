"use client";

import { FormEvent, useEffect, useMemo, useState } from "react";
import {
  Activity,
  CheckCircle2,
  ClipboardCheck,
  Download,
  FileImage,
  FileText,
  HardDriveDownload,
  Loader2,
  Play,
  QrCode,
  Radio,
  RefreshCw,
  RotateCcw,
  Save,
  ServerCog,
  ShieldCheck,
  Upload,
  Wrench
} from "lucide-react";
import { QRCodeSVG } from "qrcode.react";
import { EmptyState } from "@/components/EmptyState";
import { ErrorState } from "@/components/ErrorState";
import { LoadingState } from "@/components/LoadingState";
import {
  compareDevicePeriods,
  completeMaintenanceRecord,
  createDeviceInstallationChecklist,
  createDeviceQr,
  createFirmwareRelease,
  createMaintenanceRecord,
  downloadEvidence,
  getCsvExport,
  getDeviceFirmwareStatuses,
  getEvidence,
  getExecutiveReportPdf,
  getFirmwareReleases,
  getGateways,
  getInstallationChecklists,
  getMaintenanceRecords,
  getPilotMetrics,
  getSystemHealth,
  getTechnicalReportPdf,
  startMaintenanceRecord,
  updateGateway,
  updateInstallationChecklist,
  uploadEvidence,
  validateInstallationChecklist
} from "@/lib/api";
import { formatDateTime } from "@/lib/format";
import type {
  AppData,
  DeviceComparison,
  DeviceFirmwareStatus,
  DeviceQr,
  EvidenceFile,
  FirmwareRelease,
  GatewayStatus,
  InstallationChecklistRecord,
  MaintenanceRecord,
  NotificationDelivery,
  PilotMetrics,
  SystemHealth
} from "@/lib/types";

export function MaintenanceOperationsView({
  data,
  token
}: {
  data: AppData;
  token: string;
}) {
  const [rows, setRows] = useState<MaintenanceRecord[]>([]);
  const [deviceId, setDeviceId] = useState(data.devices[0]?.id ?? 0);
  const [selectedId, setSelectedId] = useState<number | null>(null);
  const [type, setType] = useState("INSPECTION");
  const [priority, setPriority] = useState("MEDIUM");
  const [observations, setObservations] = useState("");
  const [diagnosis, setDiagnosis] = useState("");
  const [action, setAction] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const selected = rows.find((item) => item.id === selectedId) ?? null;

  async function load() {
    setBusy(true);
    setError(null);
    try {
      setRows(await getMaintenanceRecords(token));
    } catch (err) {
      setError(messageOf(err));
    } finally {
      setBusy(false);
    }
  }

  useEffect(() => {
    void load();
  }, [token]);

  async function create(event: FormEvent) {
    event.preventDefault();
    if (!deviceId) return;
    setBusy(true);
    setError(null);
    try {
      await createMaintenanceRecord(token, {
        device_id: deviceId,
        maintenance_type: type,
        priority,
        observations: observations || null
      });
      setObservations("");
      await load();
    } catch (err) {
      setError(messageOf(err));
      setBusy(false);
    }
  }

  async function start(item: MaintenanceRecord) {
    setBusy(true);
    setError(null);
    try {
      await startMaintenanceRecord(token, item.id, "Intervencion iniciada por el tecnico responsable.");
      await load();
    } catch (err) {
      setError(messageOf(err));
      setBusy(false);
    }
  }

  async function complete(event: FormEvent) {
    event.preventDefault();
    if (!selected) return;
    setBusy(true);
    setError(null);
    try {
      await completeMaintenanceRecord(token, selected.id, {
        observations: observations || "Intervencion completada y verificada en sitio.",
        diagnosis,
        action_taken: action,
        device_status_after: "operational",
        parts_replaced: [],
        battery_replaced: selected.maintenance_type === "BATTERY_CHANGE",
        sensor_replaced: false,
        calibration_required: false,
        firmware_updated: false
      });
      setSelectedId(null);
      setDiagnosis("");
      setAction("");
      setObservations("");
      await load();
    } catch (err) {
      setError(messageOf(err));
      setBusy(false);
    }
  }

  return (
    <section className="space-y-5">
      <PageIntro
        icon={Wrench}
        eyebrow="Operacion tecnica"
        title="Mantenimiento trazable"
        copy="Planifica, asigna, inicia y cierra intervenciones sin perder el historial del nodo."
      />
      {error ? <ErrorState message={error} onRetry={load} /> : null}
      {data.me.role === "admin" ? (
        <form onSubmit={create} className="panel grid gap-4 p-5 md:grid-cols-4">
          <Field label="Nodo *">
            <select className="input" value={deviceId} onChange={(event) => setDeviceId(Number(event.target.value))}>
              {data.devices.map((device) => <option key={device.id} value={device.id}>{device.external_id} / {device.name}</option>)}
            </select>
          </Field>
          <Field label="Intervencion *">
            <select className="input" value={type} onChange={(event) => setType(event.target.value)}>
              {["INSPECTION", "CALIBRATION", "BATTERY_CHANGE", "SENSOR_REPLACEMENT", "CLEANING", "SIGNAL_ADJUSTMENT", "FIRMWARE_UPDATE", "GATEWAY_CHECK"].map((item) => <option key={item}>{item.replaceAll("_", " ")}</option>)}
            </select>
          </Field>
          <Field label="Prioridad *">
            <select className="input" value={priority} onChange={(event) => setPriority(event.target.value)}>
              {["LOW", "MEDIUM", "HIGH", "CRITICAL"].map((item) => <option key={item}>{item}</option>)}
            </select>
          </Field>
          <div className="flex items-end">
            <button className="btn-primary h-12" disabled={busy || !deviceId} type="submit">
              <Save className="mr-2" size={16} />Programar
            </button>
          </div>
          <div className="md:col-span-4">
            <Field label="Observaciones">
              <input className="input" value={observations} onChange={(event) => setObservations(event.target.value)} placeholder="Alcance y condicion que origina la intervencion" />
            </Field>
          </div>
        </form>
      ) : null}
      <div className="grid gap-4 xl:grid-cols-[1.4fr_0.8fr]">
        <div className="panel overflow-hidden">
          <PanelHeader title="Intervenciones" copy={`${rows.length} registros dentro de tu alcance`} onRefresh={load} />
          {busy && !rows.length ? <LoadingState label="Cargando mantenimiento" /> : null}
          <div className="divide-y divide-slate-200">
            {rows.map((item) => (
              <article key={item.id} className="grid gap-3 p-5 md:grid-cols-[1fr_auto]">
                <div>
                  <div className="flex flex-wrap items-center gap-2">
                    <strong className="text-slate-950">{deviceLabel(data, item.device_id)}</strong>
                    <StatusPill value={item.effective_status} />
                    <span className="text-xs font-bold text-slate-500">{item.priority}</span>
                  </div>
                  <p className="mt-2 text-sm font-semibold text-slate-700">{item.maintenance_type.replaceAll("_", " ")}</p>
                  <p className="mt-1 text-xs text-slate-500">{formatDateTime(item.scheduled_at || item.created_at)}</p>
                </div>
                <div className="flex flex-wrap items-center gap-2">
                  {data.me.role === "technician" && ["ASSIGNED", "SCHEDULED", "OVERDUE"].includes(item.effective_status) ? (
                    <button className="btn-secondary" onClick={() => start(item)} disabled={busy} type="button"><Play className="mr-2" size={15} />Iniciar</button>
                  ) : null}
                  {data.me.role === "technician" && item.effective_status === "IN_PROGRESS" ? (
                    <button className="btn-primary" onClick={() => setSelectedId(item.id)} type="button"><CheckCircle2 className="mr-2" size={15} />Cerrar</button>
                  ) : null}
                </div>
              </article>
            ))}
            {!rows.length && !busy ? <EmptyState title="Sin mantenimiento" message="No hay intervenciones registradas dentro de tu alcance." /> : null}
          </div>
        </div>
        <div className="panel p-5">
          <p className="section-kicker">Cierre tecnico</p>
          <h3 className="mt-1 font-black text-slate-950">{selected ? `Intervencion #${selected.id}` : "Selecciona una intervencion"}</h3>
          {selected ? (
            <form onSubmit={complete} className="mt-4 space-y-3">
              <Field label="Diagnostico *"><textarea className="input min-h-24" value={diagnosis} onChange={(event) => setDiagnosis(event.target.value)} /></Field>
              <Field label="Accion realizada *"><textarea className="input min-h-24" value={action} onChange={(event) => setAction(event.target.value)} /></Field>
              <Field label="Observaciones"><textarea className="input min-h-20" value={observations} onChange={(event) => setObservations(event.target.value)} /></Field>
              <button className="btn-primary w-full" disabled={busy || diagnosis.length < 3 || action.length < 5}>Completar y registrar</button>
            </form>
          ) : (
            <p className="mt-3 text-sm leading-6 text-slate-500">El cierre exige diagnostico y accion. El backend registra bitacora, responsable y estado final.</p>
          )}
        </div>
      </div>
    </section>
  );
}

export function InstallationOperationsView({ data, token }: { data: AppData; token: string }) {
  const [rows, setRows] = useState<InstallationChecklistRecord[]>([]);
  const [selectedId, setSelectedId] = useState<number | null>(null);
  const [deviceId, setDeviceId] = useState(data.devices[0]?.id ?? 0);
  const [answers, setAnswers] = useState<Record<string, boolean>>({});
  const [firstReadingId, setFirstReadingId] = useState("");
  const [testAlertId, setTestAlertId] = useState("");
  const [qr, setQr] = useState<DeviceQr | null>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const selected = rows.find((item) => item.id === selectedId) ?? null;
  const checklistItems = [
    ["hardware.enclosure_ok", "Caja y proteccion verificadas"],
    ["hardware.mounting_ok", "Montaje fisico estable"],
    ["hardware.antenna_ok", "Antena correctamente instalada"],
    ["hardware.battery_ok", "Bateria y alimentacion verificadas"],
    ["hardware.sensor_ok", "Sensor responde correctamente"],
    ["hardware.wiring_ok", "Cableado y conectores asegurados"],
    ["hardware.sealed_ok", "Sellado contra polvo y humedad"],
    ["hardware.qr_applied", "QR aplicado al activo"],
    ["communication.first_transmission", "Primera transmision recibida"],
    ["communication.time_synced", "Hora del nodo sincronizada"],
    ["communication.connectivity_ok", "Conectividad validada"],
    ["validation.reading_compared", "Lectura comparada con referencia"],
    ["validation.thresholds_validated", "Umbrales revisados"],
    ["validation.test_alert_passed", "Alerta de prueba validada"],
    ["validation.client_access_validated", "Acceso cliente validado"],
    ["validation.technician_access_validated", "Acceso tecnico validado"],
    ["validation.test_report_generated", "Reporte de prueba generado"]
  ] as const;

  async function load() {
    setBusy(true);
    setError(null);
    try {
      setRows(await getInstallationChecklists(token));
    } catch (err) {
      setError(messageOf(err));
    } finally {
      setBusy(false);
    }
  }

  useEffect(() => {
    void load();
  }, [token]);

  useEffect(() => {
    if (!selected) return;
    setAnswers(flattenBooleanResponses(selected.responses));
    setFirstReadingId(selected.first_reading_id ? String(selected.first_reading_id) : "");
    setTestAlertId(selected.test_alert_id ? String(selected.test_alert_id) : "");
    setDeviceId(selected.device_id);
  }, [selectedId]);

  async function create() {
    setBusy(true);
    setError(null);
    try {
      const technicianId = data.storageUnits.find((unit) => unit.id === data.devices.find((device) => device.id === deviceId)?.storage_unit_id)?.assigned_technician_id;
      const record = await createDeviceInstallationChecklist(token, deviceId, technicianId);
      await load();
      setSelectedId(record.id);
    } catch (err) {
      setError(messageOf(err));
      setBusy(false);
    }
  }

  async function saveAndValidate(finalStatus?: "PASSED" | "FAILED") {
    if (!selected) return;
    setBusy(true);
    setError(null);
    try {
      await updateInstallationChecklist(token, selected.id, {
        responses: expandResponses(answers),
        first_reading_id: firstReadingId ? Number(firstReadingId) : null,
        test_alert_id: testAlertId ? Number(testAlertId) : null,
        notes: "Checklist digital de instalacion P1."
      });
      if (finalStatus) await validateInstallationChecklist(token, selected.id, finalStatus);
      await load();
    } catch (err) {
      setError(messageOf(err));
      setBusy(false);
    }
  }

  async function generateQr() {
    setBusy(true);
    setError(null);
    try {
      setQr(await createDeviceQr(token, deviceId));
    } catch (err) {
      setError(messageOf(err));
    } finally {
      setBusy(false);
    }
  }

  const qrValue = qr ? `${(process.env.NEXT_PUBLIC_API_URL || "http://127.0.0.1:8010").replace(/\/+$/, "")}/api${qr.scan_path}` : "";

  return (
    <section className="space-y-5">
      <PageIntro icon={ClipboardCheck} eyebrow="Puesta en marcha" title="Checklist de instalacion" copy="Valida hardware, comunicacion, datos, alertas, accesos y reporte antes de declarar un nodo operativo." />
      {error ? <ErrorState message={error} onRetry={load} /> : null}
      <div className="grid gap-4 xl:grid-cols-[0.65fr_1.35fr]">
        <div className="space-y-4">
          {data.me.role === "admin" ? (
            <div className="panel p-5">
              <Field label="Nodo">
                <select className="input" value={deviceId} onChange={(event) => setDeviceId(Number(event.target.value))}>
                  {data.devices.map((device) => <option key={device.id} value={device.id}>{device.external_id}</option>)}
                </select>
              </Field>
              <button className="btn-primary mt-3 w-full" onClick={create} disabled={busy || !deviceId}>Crear checklist</button>
              <button className="btn-secondary mt-2 w-full" onClick={generateQr} disabled={busy || !deviceId}><QrCode className="mr-2" size={16} />Generar QR seguro</button>
              {qr ? (
                <div className="mt-4 rounded-xl border border-slate-200 bg-white p-4 text-center">
                  <QRCodeSVG value={qrValue} size={168} level="M" className="mx-auto" />
                  <p className="mt-3 text-xs font-bold text-slate-600">QR version {qr.qr_version}</p>
                  <p className="mt-1 break-all text-[10px] text-slate-400">{qrValue}</p>
                </div>
              ) : null}
            </div>
          ) : null}
          <div className="panel overflow-hidden">
            <PanelHeader title="Instalaciones" copy={`${rows.length} checklists`} onRefresh={load} />
            <div className="divide-y divide-slate-200">
              {rows.map((item) => (
                <button key={item.id} type="button" onClick={() => setSelectedId(item.id)} className={`w-full p-4 text-left transition ${selectedId === item.id ? "bg-emerald-50" : "hover:bg-slate-50"}`}>
                  <div className="flex items-center justify-between gap-2">
                    <strong>{deviceLabel(data, item.device_id)}</strong>
                    <StatusPill value={item.status} />
                  </div>
                  <p className="mt-1 text-xs text-slate-500">{formatDateTime(item.created_at)}</p>
                </button>
              ))}
              {!rows.length && !busy ? <EmptyState title="Sin instalaciones" message="Crea el primer checklist para iniciar la puesta en marcha." /> : null}
            </div>
          </div>
        </div>
        <div className="panel p-5">
          {!selected ? <EmptyState title="Selecciona un checklist" message="Revisa cada control y adjunta las referencias de lectura y alerta de prueba." /> : (
            <>
              <div className="flex flex-wrap items-start justify-between gap-3">
                <div>
                  <p className="section-kicker">Checklist {selected.checklist_version}</p>
                  <h3 className="text-xl font-black text-slate-950">{deviceLabel(data, selected.device_id)}</h3>
                </div>
                <StatusPill value={selected.status} />
              </div>
              <div className="mt-5 grid gap-2 md:grid-cols-2">
                {checklistItems.map(([key, label]) => (
                  <label key={key} className="flex cursor-pointer items-center gap-3 rounded-xl border border-slate-200 p-3 text-sm font-semibold text-slate-700 hover:border-emerald-200">
                    <input type="checkbox" checked={Boolean(answers[key])} onChange={(event) => setAnswers((current) => ({ ...current, [key]: event.target.checked }))} className="h-4 w-4 accent-emerald-700" />
                    {label}
                  </label>
                ))}
              </div>
              <div className="mt-4 grid gap-3 sm:grid-cols-2">
                <Field label="ID primera lectura *"><input className="input" type="number" value={firstReadingId} onChange={(event) => setFirstReadingId(event.target.value)} /></Field>
                <Field label="ID alerta de prueba *"><input className="input" type="number" value={testAlertId} onChange={(event) => setTestAlertId(event.target.value)} /></Field>
              </div>
              {selected.validation_errors.length ? (
                <div className="mt-4 rounded-xl border border-red-200 bg-red-50 p-4 text-sm text-red-800">
                  {selected.validation_errors.map((item) => <p key={item}>- {item}</p>)}
                </div>
              ) : null}
              {!["PASSED", "PASSED_WITH_OBSERVATIONS", "FAILED"].includes(selected.status) ? (
                <div className="mt-5 flex flex-wrap gap-2">
                  <button className="btn-secondary" onClick={() => saveAndValidate()} disabled={busy}><Save className="mr-2" size={16} />Guardar avance</button>
                  <button className="btn-primary" onClick={() => saveAndValidate("PASSED")} disabled={busy}><ShieldCheck className="mr-2" size={16} />Validar instalacion</button>
                  <button className="rounded-lg border border-red-200 bg-red-50 px-4 py-2 text-sm font-bold text-red-700" onClick={() => saveAndValidate("FAILED")} disabled={busy}>Marcar fallida</button>
                </div>
              ) : null}
            </>
          )}
        </div>
      </div>
    </section>
  );
}

export function EvidenceOperationsView({ data, token }: { data: AppData; token: string }) {
  const [rows, setRows] = useState<EvidenceFile[]>([]);
  const [maintenance, setMaintenance] = useState<MaintenanceRecord[]>([]);
  const [entityId, setEntityId] = useState(0);
  const [file, setFile] = useState<File | null>(null);
  const [description, setDescription] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const selectedMaintenance = maintenance.find((item) => item.id === entityId);

  async function load() {
    setBusy(true);
    setError(null);
    try {
      const [evidenceRows, maintenanceRows] = await Promise.all([getEvidence(token), getMaintenanceRecords(token)]);
      setRows(evidenceRows);
      setMaintenance(maintenanceRows);
      if (!entityId && maintenanceRows[0]) setEntityId(maintenanceRows[0].id);
    } catch (err) {
      setError(messageOf(err));
    } finally {
      setBusy(false);
    }
  }

  useEffect(() => {
    void load();
  }, [token]);

  async function submit(event: FormEvent) {
    event.preventDefault();
    if (!file || !selectedMaintenance) return;
    setBusy(true);
    setError(null);
    try {
      await uploadEvidence(token, {
        storageUnitId: selectedMaintenance.storage_unit_id,
        entityType: "maintenance",
        entityId: selectedMaintenance.id,
        fileType: file.type === "application/pdf" ? "DOCUMENT" : "PHOTO",
        file,
        description
      });
      setFile(null);
      setDescription("");
      await load();
    } catch (err) {
      setError(messageOf(err));
      setBusy(false);
    }
  }

  async function download(item: EvidenceFile) {
    try {
      const blob = await downloadEvidence(token, item.id);
      saveBlob(blob, item.original_filename);
    } catch (err) {
      setError(messageOf(err));
    }
  }

  return (
    <section className="space-y-5">
      <PageIntro icon={FileImage} eyebrow="Evidencia tecnica" title="Fotos y documentos" copy="Cada archivo conserva alcance, responsable, fecha, tipo y control de acceso." />
      {error ? <ErrorState message={error} onRetry={load} /> : null}
      <form onSubmit={submit} className="panel grid gap-4 p-5 lg:grid-cols-[1fr_1.4fr_1fr_auto]">
        <Field label="Mantenimiento *">
          <select className="input" value={entityId} onChange={(event) => setEntityId(Number(event.target.value))}>
            {maintenance.map((item) => <option key={item.id} value={item.id}>#{item.id} / {deviceLabel(data, item.device_id)}</option>)}
          </select>
        </Field>
        <Field label="Archivo PNG, JPG, WEBP o PDF *"><input className="input" type="file" accept="image/png,image/jpeg,image/webp,application/pdf" onChange={(event) => setFile(event.target.files?.[0] || null)} /></Field>
        <Field label="Descripcion"><input className="input" value={description} onChange={(event) => setDescription(event.target.value)} /></Field>
        <div className="flex items-end"><button className="btn-primary h-12" disabled={busy || !file || !entityId}><Upload className="mr-2" size={16} />Cargar</button></div>
      </form>
      {busy && !rows.length ? <LoadingState label="Cargando evidencia" /> : null}
      <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-3">
        {rows.map((item) => (
          <article key={item.id} className="panel p-5">
            <div className="flex items-center justify-between">
              <span className="flex h-10 w-10 items-center justify-center rounded-xl bg-emerald-50 text-emerald-700">{item.content_type === "application/pdf" ? <FileText size={19} /> : <FileImage size={19} />}</span>
              <StatusPill value={item.file_type} />
            </div>
            <h3 className="mt-4 truncate font-black text-slate-950">{item.original_filename}</h3>
            <p className="mt-2 text-sm text-slate-500">{item.description || "Sin descripcion adicional."}</p>
            <p className="mt-3 text-xs text-slate-400">{(item.size_bytes / 1024).toFixed(1)} KB / {formatDateTime(item.created_at)}</p>
            <button className="btn-secondary mt-4 w-full" onClick={() => download(item)}><Download className="mr-2" size={15} />Descargar protegido</button>
          </article>
        ))}
      </div>
      {!rows.length && !busy ? <EmptyState title="Sin evidencias" message="Carga una foto o documento asociado a una intervencion." /> : null}
    </section>
  );
}

export function SystemHealthView({ token, gatewayOnly = false }: { token: string; gatewayOnly?: boolean }) {
  const [health, setHealth] = useState<SystemHealth | null>(null);
  const [gateways, setGateways] = useState<GatewayStatus[]>([]);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function load() {
    setBusy(true);
    setError(null);
    try {
      const [healthResult, gatewayRows] = await Promise.all([getSystemHealth(token), getGateways(token)]);
      setHealth(healthResult);
      setGateways(gatewayRows);
    } catch (err) {
      setError(messageOf(err));
    } finally {
      setBusy(false);
    }
  }

  useEffect(() => {
    void load();
  }, [token]);

  async function markMaintenance(gateway: GatewayStatus) {
    setBusy(true);
    try {
      await updateGateway(token, gateway.id, { status: gateway.effective_status === "MAINTENANCE" ? "UNKNOWN" : "MAINTENANCE" });
      await load();
    } catch (err) {
      setError(messageOf(err));
      setBusy(false);
    }
  }

  return (
    <section className="space-y-5">
      <PageIntro icon={gatewayOnly ? Radio : Activity} eyebrow="Observabilidad P1" title={gatewayOnly ? "Gateways del piloto" : "Salud del sistema"} copy="Estado calculado desde ultimo contacto, cola local, conectividad, ingestiones y errores registrados." />
      {error ? <ErrorState message={error} onRetry={load} /> : null}
      {!gatewayOnly && health ? (
        <div className="grid gap-3 sm:grid-cols-2 xl:grid-cols-5">
          <MetricCard label="Backend" value={String(health.backend.status || "unknown").toUpperCase()} tone="good" />
          <MetricCard label="Base de datos" value={String(health.database.status || "unknown").toUpperCase()} tone="good" />
          <MetricCard label="Lecturas 24 h" value={String(health.data.readings_24h ?? 0)} />
          <MetricCard label="Alertas activas" value={String(health.alerts.active ?? 0)} tone={Number(health.alerts.active) ? "warn" : "good"} />
          <MetricCard label="Rechazadas 24 h" value={String(health.data.rejected_24h ?? 0)} tone={Number(health.data.rejected_24h) ? "warn" : "good"} />
        </div>
      ) : null}
      {busy && !health ? <LoadingState label="Consultando salud" /> : null}
      <div className="panel overflow-hidden">
        <PanelHeader title="Gateways autorizados" copy={`${gateways.length} equipos`} onRefresh={load} />
        <div className="overflow-x-auto">
          <table className="min-w-full text-left text-sm">
            <thead className="bg-slate-50 text-[11px] font-black uppercase tracking-[0.12em] text-slate-500">
              <tr><th className="px-4 py-3">Gateway</th><th className="px-4 py-3">Estado</th><th className="px-4 py-3">Internet</th><th className="px-4 py-3">Cola</th><th className="px-4 py-3">Nodos</th><th className="px-4 py-3">Firmware</th><th className="px-4 py-3">Ultimo contacto</th><th className="px-4 py-3">Accion</th></tr>
            </thead>
            <tbody className="divide-y divide-slate-200">
              {gateways.map((item) => (
                <tr key={item.id}>
                  <td className="px-4 py-3"><strong>{item.name}</strong><p className="text-xs text-slate-500">{item.gateway_id}</p></td>
                  <td className="px-4 py-3"><StatusPill value={item.effective_status} /></td>
                  <td className="px-4 py-3">{item.internet_status}</td>
                  <td className="px-4 py-3">{item.local_queue_size}</td>
                  <td className="px-4 py-3">{item.associated_devices_count}</td>
                  <td className="px-4 py-3">{item.firmware_version || "No registrada"}</td>
                  <td className="px-4 py-3">{item.last_seen_at ? formatDateTime(item.last_seen_at) : "Sin contacto"}</td>
                  <td className="px-4 py-3"><button className="btn-secondary" onClick={() => markMaintenance(item)}>{item.effective_status === "MAINTENANCE" ? "Reactivar" : "Mantenimiento"}</button></td>
                </tr>
              ))}
            </tbody>
          </table>
          {!gateways.length && !busy ? <EmptyState title="Sin gateways" message="Registra y asocia el gateway antes de iniciar la operacion LoRa." /> : null}
        </div>
      </div>
    </section>
  );
}

export function PilotMetricsView({ data, token }: { data: AppData; token: string }) {
  const [storageUnitId, setStorageUnitId] = useState(data.storageUnits[0]?.id ?? 0);
  const [metrics, setMetrics] = useState<PilotMetrics | null>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function load() {
    setBusy(true);
    setError(null);
    try {
      setMetrics(await getPilotMetrics(token, storageUnitId || undefined));
    } catch (err) {
      setError(messageOf(err));
    } finally {
      setBusy(false);
    }
  }

  useEffect(() => {
    void load();
  }, [token, storageUnitId]);

  const sections = metrics ? [
    ["Disponibilidad de datos", metrics.data_availability],
    ["Disponibilidad de dispositivos", metrics.device_availability],
    ["Operacion", metrics.operations],
    ["Mantenimiento", metrics.maintenance],
    ["Calidad", metrics.quality]
  ] as const : [];

  return (
    <section className="space-y-5">
      <PageIntro icon={Activity} eyebrow="Indicadores del piloto" title="Metricas verificables" copy="Solo se presentan indicadores calculados con evidencia disponible. Los valores sin cadencia aparecen como no calculables." />
      <div className="panel flex flex-wrap items-end gap-3 p-5">
        <Field label="Unidad monitoreada">
          <select className="input min-w-72" value={storageUnitId} onChange={(event) => setStorageUnitId(Number(event.target.value))}>
            {data.storageUnits.map((item) => <option key={item.id} value={item.id}>{item.name}</option>)}
          </select>
        </Field>
        <button className="btn-secondary" onClick={load}><RefreshCw className="mr-2" size={16} />Actualizar</button>
      </div>
      {error ? <ErrorState message={error} onRetry={load} /> : null}
      {busy && !metrics ? <LoadingState label="Calculando metricas" /> : null}
      <div className="grid gap-4 xl:grid-cols-2">
        {sections.map(([title, values]) => (
          <article key={title} className="panel p-5">
            <p className="section-kicker">{title}</p>
            <dl className="mt-4 grid gap-3 sm:grid-cols-2">
              {Object.entries(values).map(([key, value]) => (
                <div key={key} className="rounded-xl border border-slate-200 bg-slate-50 p-3">
                  <dt className="text-[10px] font-black uppercase tracking-[0.1em] text-slate-500">{humanize(key)}</dt>
                  <dd className="mt-1 text-lg font-black text-slate-950">{metricValue(value)}</dd>
                </div>
              ))}
            </dl>
          </article>
        ))}
      </div>
    </section>
  );
}

export function ComparisonView({ data, token }: { data: AppData; token: string }) {
  const [deviceId, setDeviceId] = useState(data.devices[0]?.id ?? 0);
  const [variable, setVariable] = useState("grain_temperature");
  const now = new Date();
  const [periodAFrom, setPeriodAFrom] = useState(localInput(new Date(now.getTime() - 14 * 86400000)));
  const [periodATo, setPeriodATo] = useState(localInput(new Date(now.getTime() - 7 * 86400000)));
  const [periodBFrom, setPeriodBFrom] = useState(localInput(new Date(now.getTime() - 7 * 86400000)));
  const [periodBTo, setPeriodBTo] = useState(localInput(now));
  const [result, setResult] = useState<DeviceComparison | null>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function submit(event: FormEvent) {
    event.preventDefault();
    setBusy(true);
    setError(null);
    try {
      setResult(await compareDevicePeriods(token, deviceId, {
        variable,
        periodAFrom: new Date(periodAFrom).toISOString(),
        periodATo: new Date(periodATo).toISOString(),
        periodBFrom: new Date(periodBFrom).toISOString(),
        periodBTo: new Date(periodBTo).toISOString()
      }));
    } catch (err) {
      setError(messageOf(err));
    } finally {
      setBusy(false);
    }
  }

  return (
    <section className="space-y-5">
      <PageIntro icon={Activity} eyebrow="Analisis descriptivo" title="Comparacion de periodos" copy="Compara el mismo nodo, variable y unidad. El resultado no atribuye causalidad a una intervencion." />
      <form onSubmit={submit} className="panel grid gap-4 p-5 lg:grid-cols-3">
        <Field label="Nodo *"><select className="input" value={deviceId} onChange={(event) => setDeviceId(Number(event.target.value))}>{data.devices.map((item) => <option key={item.id} value={item.id}>{item.external_id}</option>)}</select></Field>
        <Field label="Variable *"><select className="input" value={variable} onChange={(event) => setVariable(event.target.value)}>{["grain_temperature", "ambient_temperature", "ambient_humidity", "battery_voltage", "level_percent", "soil_moisture_percent", "soil_temperature_c"].map((item) => <option key={item}>{humanize(item)}</option>)}</select></Field>
        <div className="flex items-end"><button className="btn-primary h-12" disabled={busy}>{busy ? <Loader2 className="mr-2 animate-spin" size={16} /> : <Activity className="mr-2" size={16} />}Comparar</button></div>
        <Field label="Periodo A desde"><input className="input" type="datetime-local" value={periodAFrom} onChange={(event) => setPeriodAFrom(event.target.value)} /></Field>
        <Field label="Periodo A hasta"><input className="input" type="datetime-local" value={periodATo} onChange={(event) => setPeriodATo(event.target.value)} /></Field>
        <div />
        <Field label="Periodo B desde"><input className="input" type="datetime-local" value={periodBFrom} onChange={(event) => setPeriodBFrom(event.target.value)} /></Field>
        <Field label="Periodo B hasta"><input className="input" type="datetime-local" value={periodBTo} onChange={(event) => setPeriodBTo(event.target.value)} /></Field>
      </form>
      {error ? <ErrorState message={error} /> : null}
      {result ? (
        <div className="grid gap-4 lg:grid-cols-3">
          <PeriodCard title="Periodo A" values={result.period_a} unit={result.unit} />
          <PeriodCard title="Periodo B" values={result.period_b} unit={result.unit} />
          <article className={`panel p-5 ${result.sufficient_data ? "border-emerald-200" : "border-amber-200"}`}>
            <p className="section-kicker">Resultado</p>
            <p className="mt-4 text-3xl font-black text-slate-950">{result.absolute_difference === null ? "Sin comparacion" : `${result.absolute_difference > 0 ? "+" : ""}${result.absolute_difference} ${result.unit}`}</p>
            <p className="mt-2 text-sm font-bold text-slate-600">{result.percentage_difference === null ? "Diferencia porcentual no aplicable" : `${result.percentage_difference}% respecto al periodo A`}</p>
            <p className="mt-4 text-sm leading-6 text-slate-500">{result.note}</p>
          </article>
        </div>
      ) : null}
    </section>
  );
}

export function FirmwareView({ data, token }: { data: AppData; token: string }) {
  const [releases, setReleases] = useState<FirmwareRelease[]>([]);
  const [statuses, setStatuses] = useState<DeviceFirmwareStatus[]>([]);
  const [form, setForm] = useState({ device_type: "silo_sensor", version: "", release_notes: "", checksum: "", is_recommended: true });
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function load() {
    setBusy(true);
    setError(null);
    try {
      const [releaseRows, statusRows] = await Promise.all([getFirmwareReleases(token), getDeviceFirmwareStatuses(token)]);
      setReleases(releaseRows);
      setStatuses(statusRows);
    } catch (err) {
      setError(messageOf(err));
    } finally {
      setBusy(false);
    }
  }

  useEffect(() => {
    void load();
  }, [token]);

  async function submit(event: FormEvent) {
    event.preventDefault();
    setBusy(true);
    setError(null);
    try {
      await createFirmwareRelease(token, {
        ...form,
        status: "RELEASED",
        release_notes: form.release_notes || null,
        checksum: form.checksum || null
      });
      setForm({ ...form, version: "", release_notes: "", checksum: "" });
      await load();
    } catch (err) {
      setError(messageOf(err));
      setBusy(false);
    }
  }

  return (
    <section className="space-y-5">
      <PageIntro icon={ServerCog} eyebrow="Firmware P1" title="Inventario y versionado" copy="Registro manual auditado. AgroEscudo no realiza OTA automatica en esta fase." />
      {error ? <ErrorState message={error} onRetry={load} /> : null}
      {data.me.role === "admin" ? (
        <form onSubmit={submit} className="panel grid gap-4 p-5 lg:grid-cols-5">
          <Field label="Producto"><select className="input" value={form.device_type} onChange={(event) => setForm({ ...form, device_type: event.target.value })}><option value="silo_sensor">SiloSensor</option><option value="field_sensor">CampoSensor</option></select></Field>
          <Field label="Version *"><input className="input" value={form.version} onChange={(event) => setForm({ ...form, version: event.target.value })} placeholder="1.2.0" /></Field>
          <Field label="SHA-256"><input className="input" value={form.checksum} onChange={(event) => setForm({ ...form, checksum: event.target.value })} placeholder="64 caracteres" /></Field>
          <Field label="Notas"><input className="input" value={form.release_notes} onChange={(event) => setForm({ ...form, release_notes: event.target.value })} /></Field>
          <div className="flex items-end"><button className="btn-primary h-12" disabled={busy || !form.version}>Registrar release</button></div>
        </form>
      ) : null}
      <div className="grid gap-4 xl:grid-cols-2">
        <div className="panel overflow-hidden">
          <PanelHeader title="Estado por nodo" copy={`${statuses.length} dispositivos`} onRefresh={load} />
          <div className="divide-y divide-slate-200">
            {statuses.map((item) => (
              <div key={item.device_id} className="flex items-center justify-between gap-3 p-4">
                <div><strong>{item.external_id}</strong><p className="text-xs text-slate-500">{item.current_version || "Version no registrada"} / recomendada {item.recommended_version || "sin definir"}</p></div>
                <StatusPill value={item.update_status} />
              </div>
            ))}
          </div>
        </div>
        <div className="panel overflow-hidden">
          <PanelHeader title="Releases" copy={`${releases.length} versiones`} onRefresh={load} />
          <div className="divide-y divide-slate-200">
            {releases.map((item) => (
              <div key={item.id} className="flex items-center justify-between gap-3 p-4">
                <div><strong>{item.device_type} / {item.version}</strong><p className="text-xs text-slate-500">{item.release_notes || "Sin notas publicadas."}</p></div>
                <div className="text-right"><StatusPill value={item.status} />{item.is_recommended ? <p className="mt-1 text-[10px] font-black uppercase text-emerald-700">Recomendada</p> : null}</div>
              </div>
            ))}
          </div>
        </div>
      </div>
    </section>
  );
}

export function ExportsView({ data, token }: { data: AppData; token: string }) {
  const [storageUnitId, setStorageUnitId] = useState(data.storageUnits[0]?.id ?? 0);
  const [busy, setBusy] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  async function download(kind: "readings" | "alerts" | "incidents" | "maintenance" | "executive" | "technical") {
    setBusy(kind);
    setError(null);
    try {
      const blob = kind === "executive"
        ? await getExecutiveReportPdf(token, storageUnitId)
        : kind === "technical"
          ? await getTechnicalReportPdf(token, storageUnitId)
          : await getCsvExport(token, kind, storageUnitId);
      const unit = data.storageUnits.find((item) => item.id === storageUnitId);
      saveBlob(blob, `agroescudo-${kind}-${slug(unit?.name || "operacion")}.${kind === "executive" || kind === "technical" ? "pdf" : "csv"}`);
    } catch (err) {
      setError(messageOf(err));
    } finally {
      setBusy(null);
    }
  }

  const exports = [
    ["readings", "Lecturas", "Valores operativos, raw y calibrados."],
    ["alerts", "Alertas", "Eventos, nivel, valor observado y cierre."],
    ["incidents", "Incidentes", "Casos de servicio y responsables."],
    ["maintenance", "Mantenimiento", "Intervenciones, diagnostico y evidencia."],
    ["executive", "PDF ejecutivo", "Resumen para cliente y comite del piloto."],
    ["technical", "PDF tecnico", "Diagnostico reservado para admin y tecnico."]
  ] as const;

  return (
    <section className="space-y-5">
      <PageIntro icon={HardDriveDownload} eyebrow="Trazabilidad" title="Exportaciones del piloto" copy="Descargas filtradas por unidad, auditadas y limitadas por el backend." />
      <div className="panel p-5"><Field label="Unidad monitoreada"><select className="input max-w-lg" value={storageUnitId} onChange={(event) => setStorageUnitId(Number(event.target.value))}>{data.storageUnits.map((item) => <option key={item.id} value={item.id}>{item.name}</option>)}</select></Field></div>
      {error ? <ErrorState message={error} /> : null}
      <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-3">
        {exports.map(([kind, title, copy]) => {
          const forbidden = kind === "technical" && data.me.role === "client";
          return (
            <article key={kind} className="panel p-5">
              <span className="flex h-11 w-11 items-center justify-center rounded-xl bg-emerald-50 text-emerald-700">{kind.includes("executive") || kind.includes("technical") ? <FileText size={20} /> : <HardDriveDownload size={20} />}</span>
              <h3 className="mt-4 font-black text-slate-950">{title}</h3>
              <p className="mt-2 min-h-12 text-sm leading-6 text-slate-500">{copy}</p>
              <button className="btn-secondary mt-4 w-full" disabled={Boolean(busy) || forbidden || !storageUnitId} onClick={() => download(kind)}>
                {busy === kind ? <Loader2 className="mr-2 animate-spin" size={16} /> : <Download className="mr-2" size={16} />}
                {forbidden ? "Solo equipo tecnico" : "Descargar"}
              </button>
            </article>
          );
        })}
      </div>
    </section>
  );
}

export function NotificationAuditView({
  deliveries,
  onRetry,
  busyId
}: {
  deliveries: NotificationDelivery[];
  onRetry: (id: number) => void;
  busyId: number | null;
}) {
  return (
    <div className="overflow-x-auto">
      <table className="min-w-full text-left text-sm">
        <thead className="bg-slate-50 text-[11px] font-black uppercase tracking-[0.12em] text-slate-500">
          <tr><th className="px-4 py-3">Fecha</th><th className="px-4 py-3">Canal</th><th className="px-4 py-3">Estado</th><th className="px-4 py-3">Intentos</th><th className="px-4 py-3">Proveedor</th><th className="px-4 py-3">Accion</th></tr>
        </thead>
        <tbody className="divide-y divide-slate-200">
          {deliveries.map((item) => (
            <tr key={item.id}>
              <td className="px-4 py-3">{formatDateTime(item.created_at)}</td>
              <td className="px-4 py-3 font-bold">{item.channel}</td>
              <td className="px-4 py-3"><StatusPill value={item.status} /></td>
              <td className="px-4 py-3">{item.retry_count}</td>
              <td className="px-4 py-3">{item.provider || "No configurado"}{item.provider_message_id ? <p className="text-xs text-slate-400">{item.provider_message_id}</p> : null}</td>
              <td className="px-4 py-3">{["failed", "skipped"].includes(item.status) && !item.dry_run ? <button className="btn-secondary" disabled={busyId === item.id} onClick={() => onRetry(item.id)}><RotateCcw className="mr-2" size={15} />Reintentar</button> : <span className="text-xs text-slate-400">{item.status === "sent" ? "Esperando confirmacion" : "Sin accion"}</span>}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

function PageIntro({ icon: Icon, eyebrow, title, copy }: { icon: typeof Activity; eyebrow: string; title: string; copy: string }) {
  return (
    <div className="flex items-start gap-4">
      <span className="flex h-12 w-12 shrink-0 items-center justify-center rounded-xl bg-emerald-50 text-emerald-700"><Icon size={22} /></span>
      <div><p className="section-kicker">{eyebrow}</p><h2 className="section-title">{title}</h2><p className="section-subtitle">{copy}</p></div>
    </div>
  );
}

function PanelHeader({ title, copy, onRefresh }: { title: string; copy: string; onRefresh: () => void }) {
  return <div className="flex items-center justify-between border-b border-slate-200 px-5 py-4"><div><h3 className="font-black text-slate-950">{title}</h3><p className="text-xs text-slate-500">{copy}</p></div><button className="rounded-lg border border-slate-200 p-2 text-slate-500 hover:bg-slate-50" onClick={onRefresh} title="Actualizar"><RefreshCw size={16} /></button></div>;
}

function Field({ label, children }: { label: string; children: React.ReactNode }) {
  return <label className="block"><span className="text-[11px] font-black uppercase tracking-[0.12em] text-slate-500">{label}</span><div className="mt-1.5">{children}</div></label>;
}

function StatusPill({ value }: { value: string }) {
  const normalized = value.toLowerCase();
  const className = normalized.includes("fail") || normalized.includes("offline") || normalized.includes("critical")
    ? "bg-red-50 text-red-700"
    : normalized.includes("overdue") || normalized.includes("delay") || normalized.includes("pending") || normalized.includes("outdated") || normalized.includes("dry")
      ? "bg-amber-50 text-amber-800"
      : normalized.includes("complete") || normalized.includes("passed") || normalized.includes("online") || normalized.includes("current") || normalized.includes("delivered") || normalized.includes("sent")
        ? "bg-emerald-50 text-emerald-800"
        : "bg-slate-100 text-slate-700";
  return <span className={`inline-flex rounded-full px-2.5 py-1 text-[10px] font-black uppercase tracking-[0.1em] ${className}`}>{value.replaceAll("_", " ")}</span>;
}

function MetricCard({ label, value, tone = "default" }: { label: string; value: string; tone?: "default" | "good" | "warn" }) {
  const toneClass = tone === "good" ? "border-emerald-100 bg-emerald-50" : tone === "warn" ? "border-amber-100 bg-amber-50" : "border-slate-200 bg-white";
  return <article className={`rounded-xl border p-4 shadow-soft ${toneClass}`}><p className="text-[10px] font-black uppercase tracking-[0.12em] text-slate-500">{label}</p><p className="mt-2 text-2xl font-black text-slate-950">{value}</p></article>;
}

function PeriodCard({ title, values, unit }: { title: string; values: Record<string, number | string | null>; unit: string }) {
  return <article className="panel p-5"><p className="section-kicker">{title}</p><p className="mt-3 text-3xl font-black text-slate-950">{values.average === null ? "Sin dato" : `${values.average} ${unit}`}</p><div className="mt-4 grid grid-cols-2 gap-2 text-sm"><span>Minimo: <strong>{values.minimum ?? "-"}</strong></span><span>Maximo: <strong>{values.maximum ?? "-"}</strong></span><span>Lecturas: <strong>{values.count ?? 0}</strong></span><span>Cobertura: <strong>{values.coverage_percent === null ? "No calculable" : `${values.coverage_percent}%`}</strong></span></div></article>;
}

function deviceLabel(data: AppData, deviceId: number) {
  const device = data.devices.find((item) => item.id === deviceId);
  return device ? `${device.external_id} / ${device.name}` : `Nodo #${deviceId}`;
}

function flattenBooleanResponses(payload: Record<string, unknown>) {
  const output: Record<string, boolean> = {};
  for (const [group, values] of Object.entries(payload)) {
    if (values && typeof values === "object") {
      for (const [key, value] of Object.entries(values as Record<string, unknown>)) output[`${group}.${key}`] = value === true;
    }
  }
  return output;
}

function expandResponses(values: Record<string, boolean>) {
  const output: Record<string, Record<string, boolean>> = {};
  for (const [path, value] of Object.entries(values)) {
    const [group, key] = path.split(".");
    output[group] ||= {};
    output[group][key] = value;
  }
  output.communication ||= {};
  output.communication.gateway_required = true;
  return output;
}

function messageOf(error: unknown) {
  return error instanceof Error ? error.message : "No se pudo completar la operacion.";
}

function humanize(value: string) {
  return value.replaceAll("_", " ").replace(/\b\w/g, (char) => char.toUpperCase());
}

function metricValue(value: unknown) {
  if (value === null || value === undefined) return "No calculable";
  if (typeof value === "boolean") return value ? "Si" : "No";
  if (typeof value === "number") return Number.isInteger(value) ? String(value) : value.toFixed(2);
  return String(value).replaceAll("_", " ");
}

function localInput(value: Date) {
  const local = new Date(value.getTime() - value.getTimezoneOffset() * 60000);
  return local.toISOString().slice(0, 16);
}

function slug(value: string) {
  return value.toLowerCase().normalize("NFD").replace(/[\u0300-\u036f]/g, "").replace(/[^a-z0-9]+/g, "-").replace(/(^-|-$)/g, "");
}

function saveBlob(blob: Blob, filename: string) {
  const url = URL.createObjectURL(blob);
  const anchor = document.createElement("a");
  anchor.href = url;
  anchor.download = filename;
  document.body.appendChild(anchor);
  anchor.click();
  anchor.remove();
  URL.revokeObjectURL(url);
}
