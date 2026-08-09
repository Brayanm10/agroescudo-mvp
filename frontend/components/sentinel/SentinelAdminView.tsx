"use client";

import { FormEvent, useCallback, useEffect, useState } from "react";
import type { ReactNode } from "react";
import {
  CheckCircle2,
  Copy,
  KeyRound,
  MessageSquareText,
  PhoneCall,
  Plus,
  RefreshCw,
  ShieldAlert,
  Wifi,
  WifiOff
} from "lucide-react";
import {
  createAlertContact,
  createSentinelDevice,
  getAlertContacts,
  getSentinelDevices,
  getSentinelJobs,
  rotateSentinelToken,
  setSentinelActive,
  testAlertContact,
  updateAlertContact
} from "@/lib/api";
import type { AlertContact, AppData, SentinelDevice, SentinelJob } from "@/lib/types";
import { ErrorState } from "@/components/ErrorState";
import { LoadingState } from "@/components/LoadingState";

type ContactDraft = {
  company_id: number;
  storage_unit_id: number | null;
  name: string;
  phone_e164: string;
  priority: number;
  escalation_delay_minutes: number;
  receive_sms: boolean;
  receive_call: boolean;
  minimum_severity: "info" | "technical" | "warning" | "critical";
};

export function SentinelAdminView({ data, token }: { data: AppData; token: string }) {
  const firstCompany = data.companies[0]?.id ?? 0;
  const [contacts, setContacts] = useState<AlertContact[]>([]);
  const [devices, setDevices] = useState<SentinelDevice[]>([]);
  const [jobs, setJobs] = useState<SentinelJob[]>([]);
  const [draft, setDraft] = useState<ContactDraft>({
    company_id: firstCompany,
    storage_unit_id: null,
    name: "",
    phone_e164: "+591",
    priority: 1,
    escalation_delay_minutes: 0,
    receive_sms: true,
    receive_call: false,
    minimum_severity: "critical"
  });
  const [deviceDraft, setDeviceDraft] = useState({ device_uid: "sentinel-home-001", name: "AgroEscudo Sentinel Casa" });
  const [editingContactId, setEditingContactId] = useState<number | null>(null);
  const [revealedToken, setRevealedToken] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const [busy, setBusy] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [notice, setNotice] = useState<string | null>(null);

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const [contactRows, deviceRows, jobRows] = await Promise.all([
        getAlertContacts(token),
        getSentinelDevices(token),
        getSentinelJobs(token)
      ]);
      setContacts(contactRows);
      setDevices(deviceRows);
      setJobs(jobRows);
    } catch (err) {
      setError(err instanceof Error ? err.message : "No se pudo cargar Sentinel.");
    } finally {
      setLoading(false);
    }
  }, [token]);

  useEffect(() => {
    void load();
  }, [load]);

  async function submitContact(event: FormEvent) {
    event.preventDefault();
    setBusy("contact");
    setError(null);
    try {
      if (editingContactId) {
        await updateAlertContact(token, editingContactId, draft);
      } else {
        await createAlertContact(token, { ...draft, active: true, consent_at: null });
      }
      setDraft((current) => ({ ...current, name: "", phone_e164: "+591" }));
      setEditingContactId(null);
      setNotice(editingContactId ? "Contacto y política actualizados." : "Contacto incorporado a la política de escalamiento.");
      await load();
    } catch (err) {
      setError(err instanceof Error ? err.message : "No se pudo crear el contacto.");
    } finally {
      setBusy(null);
    }
  }

  async function submitDevice(event: FormEvent) {
    event.preventDefault();
    setBusy("device");
    setError(null);
    try {
      const created = await createSentinelDevice(token, deviceDraft);
      setRevealedToken(created.token);
      setNotice("Sentinel creado. Guarda el token ahora: no volverá a mostrarse.");
      await load();
    } catch (err) {
      setError(err instanceof Error ? err.message : "No se pudo crear el Sentinel.");
    } finally {
      setBusy(null);
    }
  }

  async function runContactTest(contact: AlertContact, channel: "sms" | "call") {
    setBusy(`${contact.id}-${channel}`);
    setError(null);
    try {
      await testAlertContact(token, contact.id, channel);
      setNotice(channel === "sms" ? "SMS de prueba agregado a la cola." : "Llamada de prueba agregada a la cola.");
      await load();
    } catch (err) {
      setError(err instanceof Error ? err.message : "No se pudo programar la prueba.");
    } finally {
      setBusy(null);
    }
  }

  async function toggleContact(contact: AlertContact) {
    setBusy(`contact-${contact.id}`);
    try {
      await updateAlertContact(token, contact.id, { active: !contact.active });
      await load();
    } catch (err) {
      setError(err instanceof Error ? err.message : "No se pudo actualizar el contacto.");
    } finally {
      setBusy(null);
    }
  }

  function editContact(contact: AlertContact) {
    setEditingContactId(contact.id);
    setDraft({
      company_id: contact.company_id,
      storage_unit_id: contact.storage_unit_id,
      name: contact.name,
      phone_e164: contact.phone_e164,
      priority: contact.priority,
      escalation_delay_minutes: contact.escalation_delay_minutes,
      receive_sms: contact.receive_sms,
      receive_call: contact.receive_call,
      minimum_severity: contact.minimum_severity
    });
    window.scrollTo({ top: 0, behavior: "smooth" });
  }

  async function toggleDevice(device: SentinelDevice) {
    setBusy(`device-${device.id}`);
    try {
      await setSentinelActive(token, device.id, !device.active);
      await load();
    } catch (err) {
      setError(err instanceof Error ? err.message : "No se pudo actualizar el Sentinel.");
    } finally {
      setBusy(null);
    }
  }

  async function rotateToken(device: SentinelDevice) {
    if (!window.confirm("El token anterior dejará de funcionar. ¿Continuar?")) return;
    setBusy(`rotate-${device.id}`);
    try {
      const updated = await rotateSentinelToken(token, device.id);
      setRevealedToken(updated.token);
      setNotice("Token rotado. Actualiza secrets.h antes del siguiente poll.");
      await load();
    } catch (err) {
      setError(err instanceof Error ? err.message : "No se pudo rotar el token.");
    } finally {
      setBusy(null);
    }
  }

  const scopedUnits = data.storageUnits.filter((unit) => unit.company_id === draft.company_id);

  return (
    <div className="space-y-6">
      <section className="overflow-hidden rounded-lg border border-emerald-900/15 bg-[#073f32] text-white shadow-sm">
        <div className="grid gap-6 px-6 py-7 lg:grid-cols-[1.4fr_0.6fr] lg:items-end">
          <div>
            <p className="section-kicker !text-amber-300">Infraestructura de respaldo GSM</p>
            <h2 className="mt-2 text-2xl font-semibold">AgroEscudo Sentinel</h2>
            <p className="mt-2 max-w-3xl text-sm leading-6 text-emerald-50/80">
              FastAPI decide, PostgreSQL conserva la trazabilidad y el ESP32 ejecuta un único SMS o llamada por vez.
              Un Sentinel puede atender varios silos sin conocer usuarios ni credenciales de la plataforma.
            </p>
          </div>
          <div className="grid grid-cols-2 gap-3 text-sm">
            <Metric label="Sentinel online" value={String(devices.filter((item) => item.online).length)} />
            <Metric label="Jobs pendientes" value={String(devices[0]?.pending_jobs ?? jobs.filter((item) => item.status === "pending").length)} />
          </div>
        </div>
      </section>

      {error ? <ErrorState message={error} onRetry={() => void load()} /> : null}
      {notice ? (
        <div className="flex items-center gap-2 rounded-lg border border-emerald-200 bg-emerald-50 px-4 py-3 text-sm text-emerald-800">
          <CheckCircle2 size={18} /> {notice}
        </div>
      ) : null}
      {loading ? <LoadingState label="Actualizando infraestructura Sentinel" /> : null}

      {revealedToken ? (
        <section className="rounded-lg border border-amber-300 bg-amber-50 p-5">
          <div className="flex flex-wrap items-start justify-between gap-4">
            <div>
              <p className="text-xs font-bold uppercase text-amber-800">Token visible una sola vez</p>
              <p className="mt-1 text-sm text-amber-900">Guárdalo en `secrets.h`. La base de datos conserva únicamente su hash.</p>
            </div>
            <button className="btn-secondary" onClick={() => void navigator.clipboard.writeText(revealedToken)}>
              <Copy size={16} /> Copiar token
            </button>
          </div>
          <code className="mt-4 block overflow-x-auto rounded-md bg-white px-4 py-3 text-xs text-emerald-950">{revealedToken}</code>
        </section>
      ) : null}

      <section className="panel overflow-hidden">
        <div className="border-b border-slate-200 px-6 py-5">
          <p className="section-kicker">Relay operativo</p>
          <h3 className="section-title">Dispositivos Sentinel</h3>
        </div>
        <form onSubmit={submitDevice} className="grid gap-4 border-b border-slate-200 bg-slate-50/70 px-6 py-5 md:grid-cols-[1fr_1.4fr_auto] md:items-end">
          <Field label="UID del equipo">
            <input className="input" value={deviceDraft.device_uid} onChange={(event) => setDeviceDraft({ ...deviceDraft, device_uid: event.target.value })} required />
          </Field>
          <Field label="Nombre operativo">
            <input className="input" value={deviceDraft.name} onChange={(event) => setDeviceDraft({ ...deviceDraft, name: event.target.value })} required />
          </Field>
          <button className="btn-primary h-12" disabled={busy === "device"}>
            <Plus size={17} /> Crear Sentinel
          </button>
        </form>
        <div className="divide-y divide-slate-200">
          {devices.length ? devices.map((device) => (
            <div key={device.id} className="grid gap-4 px-6 py-5 lg:grid-cols-[1.3fr_0.8fr_0.8fr_auto] lg:items-center">
              <div className="flex items-center gap-3">
                <span className={`grid h-11 w-11 place-items-center rounded-md ${device.online ? "bg-emerald-100 text-emerald-800" : "bg-slate-100 text-slate-500"}`}>
                  {device.online ? <Wifi size={20} /> : <WifiOff size={20} />}
                </span>
                <div>
                  <p className="font-semibold text-slate-950">{device.name}</p>
                  <p className="text-xs text-slate-500">{device.device_uid} · firmware {device.firmware_version ?? "sin reporte"}</p>
                </div>
              </div>
              <StatusLine label="Estado" value={device.online ? "Online" : "Offline"} emphasis={device.online ? "good" : "muted"} />
              <StatusLine label="Último poll" value={device.last_seen_at ? relativeDate(device.last_seen_at) : "Sin comunicación"} />
              <div className="flex flex-wrap gap-2">
                <button className="btn-secondary" onClick={() => void rotateToken(device)} disabled={busy === `rotate-${device.id}`} title="Rotar token">
                  <KeyRound size={16} />
                </button>
                <button className="btn-secondary" onClick={() => void toggleDevice(device)} disabled={busy === `device-${device.id}`}>
                  {device.active ? "Desactivar" : "Activar"}
                </button>
              </div>
            </div>
          )) : <EmptyRow text="Todavía no existe un Sentinel. Créalo y configura el token en el ESP32." />}
        </div>
      </section>

      <section className="panel overflow-hidden">
        <div className="border-b border-slate-200 px-6 py-5">
          <p className="section-kicker">Escalamiento por organización y silo</p>
          <h3 className="section-title">Contactos de alerta</h3>
        </div>
        <form onSubmit={submitContact} className="grid gap-4 border-b border-slate-200 bg-slate-50/70 px-6 py-5 md:grid-cols-2 xl:grid-cols-4">
          <Field label="Empresa *">
            <select className="input" value={draft.company_id} onChange={(event) => setDraft({ ...draft, company_id: Number(event.target.value), storage_unit_id: null })} required>
              {data.companies.map((company) => <option key={company.id} value={company.id}>{company.name}</option>)}
            </select>
          </Field>
          <Field label="Alcance">
            <select className="input" value={draft.storage_unit_id ?? ""} onChange={(event) => setDraft({ ...draft, storage_unit_id: event.target.value ? Number(event.target.value) : null })}>
              <option value="">Toda la empresa</option>
              {scopedUnits.map((unit) => <option key={unit.id} value={unit.id}>{unit.name}</option>)}
            </select>
          </Field>
          <Field label="Responsable *">
            <input className="input" value={draft.name} onChange={(event) => setDraft({ ...draft, name: event.target.value })} required />
          </Field>
          <Field label="Teléfono E.164 *">
            <input className="input" value={draft.phone_e164} onChange={(event) => setDraft({ ...draft, phone_e164: event.target.value })} placeholder="+5917XXXXXXX" required />
          </Field>
          <Field label="Nivel mínimo">
            <select className="input" value={draft.minimum_severity} onChange={(event) => setDraft({ ...draft, minimum_severity: event.target.value as ContactDraft["minimum_severity"] })}>
              <option value="critical">Crítica</option>
              <option value="warning">Atención</option>
              <option value="technical">Técnica</option>
              <option value="info">Informativa</option>
            </select>
          </Field>
          <Field label="Prioridad">
            <input className="input" type="number" min={1} max={20} value={draft.priority} onChange={(event) => setDraft({ ...draft, priority: Number(event.target.value) })} />
          </Field>
          <Field label="Escalamiento (min)">
            <input className="input" type="number" min={0} max={1440} value={draft.escalation_delay_minutes} onChange={(event) => setDraft({ ...draft, escalation_delay_minutes: Number(event.target.value) })} />
          </Field>
          <div className="flex items-end justify-between gap-3">
            <label className="flex h-12 items-center gap-2 text-sm font-medium"><input type="checkbox" checked={draft.receive_sms} onChange={(event) => setDraft({ ...draft, receive_sms: event.target.checked })} /> SMS</label>
            <label className="flex h-12 items-center gap-2 text-sm font-medium"><input type="checkbox" checked={draft.receive_call} onChange={(event) => setDraft({ ...draft, receive_call: event.target.checked })} /> Llamada</label>
            <button className="btn-primary h-12" disabled={busy === "contact"}>{editingContactId ? <CheckCircle2 size={17} /> : <Plus size={17} />} {editingContactId ? "Guardar" : "Agregar"}</button>
          </div>
        </form>
        <div className="divide-y divide-slate-200">
          {contacts.length ? contacts.map((contact) => (
            <div key={contact.id} className="grid gap-4 px-6 py-5 xl:grid-cols-[1.2fr_0.9fr_0.7fr_1fr_auto] xl:items-center">
              <div>
                <div className="flex items-center gap-2">
                  <p className="font-semibold text-slate-950">{contact.name}</p>
                  <span className={`rounded-full px-2.5 py-1 text-[11px] font-bold uppercase ${contact.active ? "bg-emerald-100 text-emerald-800" : "bg-slate-100 text-slate-600"}`}>{contact.active ? "Activo" : "Inactivo"}</span>
                </div>
                <p className="mt-1 text-sm text-slate-600">{contact.phone_e164}</p>
              </div>
              <StatusLine label="Canales" value={[contact.receive_sms ? "SMS" : "", contact.receive_call ? "Llamada" : ""].filter(Boolean).join(" + ") || "Ninguno"} />
              <StatusLine label="Desde" value={severityLabel(contact.minimum_severity)} />
              <StatusLine label={`Prioridad ${contact.priority}`} value={contact.escalation_delay_minutes ? `${contact.escalation_delay_minutes} min` : "Inmediato"} />
              <div className="flex flex-wrap gap-2">
                {contact.receive_sms ? <button className="btn-secondary" onClick={() => void runContactTest(contact, "sms")} disabled={busy === `${contact.id}-sms`} title="Enviar SMS de prueba"><MessageSquareText size={16} /></button> : null}
                {contact.receive_call ? <button className="btn-secondary" onClick={() => void runContactTest(contact, "call")} disabled={busy === `${contact.id}-call`} title="Probar llamada"><PhoneCall size={16} /></button> : null}
                <button className="btn-secondary" onClick={() => editContact(contact)}>Editar</button>
                <button className="btn-secondary" onClick={() => void toggleContact(contact)} disabled={busy === `contact-${contact.id}`}>{contact.active ? "Desactivar" : "Activar"}</button>
              </div>
            </div>
          )) : <EmptyRow text="No hay contactos configurados. Las alertas seguirán en la plataforma, pero no generarán jobs GSM." />}
        </div>
      </section>

      <section className="panel overflow-hidden">
        <div className="flex flex-wrap items-center justify-between gap-3 border-b border-slate-200 px-6 py-5">
          <div><p className="section-kicker">Auditoría de ejecución</p><h3 className="section-title">Historial de jobs</h3></div>
          <button className="btn-secondary" onClick={() => void load()}><RefreshCw size={16} /> Actualizar</button>
        </div>
        <div className="overflow-x-auto">
          <table className="min-w-full text-left text-sm">
            <thead className="bg-slate-50 text-xs uppercase text-slate-500"><tr><th className="px-5 py-3">Creado</th><th className="px-5 py-3">Canal</th><th className="px-5 py-3">Destino</th><th className="px-5 py-3">Estado</th><th className="px-5 py-3">Intentos</th><th className="px-5 py-3">Resultado</th></tr></thead>
            <tbody className="divide-y divide-slate-200">
              {jobs.slice(0, 100).map((job) => <tr key={job.id}><td className="px-5 py-4 text-slate-600">{formatDate(job.created_at)}</td><td className="px-5 py-4 font-semibold uppercase">{job.job_type}</td><td className="px-5 py-4 font-mono text-xs">{job.destination_phone}</td><td className="px-5 py-4"><JobStatus status={job.status} /></td><td className="px-5 py-4">{job.attempt_count}/{job.max_attempts}</td><td className="px-5 py-4 text-slate-600">{job.result_code ?? job.last_error_code ?? "Pendiente"}</td></tr>)}
              {!jobs.length ? <tr><td colSpan={6} className="px-5 py-10 text-center text-slate-500">Aún no existen trabajos Sentinel.</td></tr> : null}
            </tbody>
          </table>
        </div>
      </section>
    </div>
  );
}

function Field({ label, children }: { label: string; children: ReactNode }) {
  return <label className="block"><span className="mb-2 block text-xs font-bold uppercase text-slate-600">{label}</span>{children}</label>;
}

function Metric({ label, value }: { label: string; value: string }) {
  return <div className="rounded-md border border-white/15 bg-white/10 px-4 py-3"><p className="text-xs uppercase text-emerald-100/70">{label}</p><p className="mt-1 text-xl font-semibold">{value}</p></div>;
}

function StatusLine({ label, value, emphasis }: { label: string; value: string; emphasis?: "good" | "muted" }) {
  return <div><p className="text-xs font-bold uppercase text-slate-500">{label}</p><p className={`mt-1 text-sm font-semibold ${emphasis === "good" ? "text-emerald-700" : emphasis === "muted" ? "text-slate-500" : "text-slate-800"}`}>{value}</p></div>;
}

function EmptyRow({ text }: { text: string }) {
  return <div className="flex items-center gap-3 px-6 py-8 text-sm text-slate-500"><ShieldAlert size={20} /> {text}</div>;
}

function JobStatus({ status }: { status: string }) {
  const good = status === "submitted" || status === "attempted";
  const bad = status === "failed" || status === "expired";
  return <span className={`rounded-full px-2.5 py-1 text-[11px] font-bold uppercase ${good ? "bg-emerald-100 text-emerald-800" : bad ? "bg-red-100 text-red-800" : "bg-slate-100 text-slate-600"}`}>{statusLabel(status)}</span>;
}

function statusLabel(value: string) {
  return ({ pending: "Pendiente", claimed: "Reclamado", submitted: "SMS aceptado", attempted: "Llamada intentada", failed: "Falló", cancelled: "Cancelado", expired: "Expirado" } as Record<string, string>)[value] ?? value;
}

function severityLabel(value: string) {
  return ({ critical: "Crítica", warning: "Atención", technical: "Técnica", info: "Informativa" } as Record<string, string>)[value] ?? value;
}

function formatDate(value: string) {
  return new Intl.DateTimeFormat("es-BO", { dateStyle: "short", timeStyle: "short" }).format(new Date(value));
}

function relativeDate(value: string) {
  const seconds = Math.max(0, Math.round((Date.now() - new Date(value).getTime()) / 1000));
  if (seconds < 60) return `hace ${seconds} s`;
  if (seconds < 3600) return `hace ${Math.floor(seconds / 60)} min`;
  return `hace ${Math.floor(seconds / 3600)} h`;
}
