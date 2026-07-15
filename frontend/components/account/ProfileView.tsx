"use client";

import { FormEvent, useState } from "react";
import { BellRing, CheckCircle2, Save, ShieldCheck, UserCircle } from "lucide-react";
import type { LucideIcon } from "lucide-react";
import { ErrorState } from "@/components/ErrorState";
import { formatDateTime } from "@/lib/format";
import { updateMe } from "@/lib/api";
import type { AppData, User } from "@/lib/types";

function userAssignments(data: AppData, user: User) {
  return data.storageUnits.filter((unit) => unit.assigned_client_id === user.id || unit.assigned_technician_id === user.id);
}

export function ProfileView({
  data,
  token,
  onChanged
}: {
  data: AppData;
  token: string;
  onChanged: () => void;
}) {
  const user = data.me;
  const [form, setForm] = useState({
    full_name: user.full_name,
    phone_whatsapp: user.phone_whatsapp || "",
    telegram_chat_id: user.telegram_chat_id || "",
    receives_alerts: user.receives_alerts,
    language: user.language || "es",
    timezone: user.timezone || "America/La_Paz"
  });
  const [saving, setSaving] = useState(false);
  const [message, setMessage] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const assignments = userAssignments(data, user);

  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setSaving(true);
    setError(null);
    setMessage(null);
    try {
      await updateMe(token, {
        full_name: form.full_name,
        phone_whatsapp: form.phone_whatsapp || null,
        telegram_chat_id: form.telegram_chat_id || null,
        receives_alerts: form.receives_alerts,
        language: form.language,
        timezone: form.timezone
      });
      setMessage("Perfil actualizado correctamente.");
      onChanged();
    } catch (err) {
      setError(err instanceof Error ? err.message : "No se pudo actualizar el perfil.");
    } finally {
      setSaving(false);
    }
  }

  return (
    <section className="space-y-5">
      {error ? <ErrorState message={error} /> : null}
      {message ? (
        <div className="rounded-2xl border border-emerald-200 bg-emerald-50 p-4 text-sm font-bold text-emerald-800">
          {message}
        </div>
      ) : null}
      <div className="grid gap-5 xl:grid-cols-[0.9fr_1.1fr]">
        <div className="panel p-5">
          <div className="flex items-start gap-4">
            <div className="rounded-2xl bg-emerald-50 p-3 text-emerald-700">
              <UserCircle size={28} aria-hidden="true" />
            </div>
            <div>
              <p className="section-kicker">Cuenta operativa</p>
              <h2 className="section-title">{user.full_name}</h2>
              <p className="section-subtitle">{user.email}</p>
            </div>
          </div>
          <div className="mt-5 grid gap-3">
            <InfoTile label="Rol" value={user.role} icon={ShieldCheck} />
            <InfoTile label="Empresa" value={user.company?.name || "Cuenta interna AgroEscudo"} icon={CheckCircle2} />
            <InfoTile label="Ultimo ingreso" value={user.last_login_at ? formatDateTime(user.last_login_at) : "Sin registro"} icon={BellRing} />
          </div>
          <div className="mt-5 rounded-2xl border border-slate-200 bg-slate-50 p-4">
            <p className="text-xs font-black uppercase tracking-[0.14em] text-slate-500">Silos asignados</p>
            <div className="mt-3 space-y-2">
              {assignments.length ? assignments.map((unit) => (
                <div key={unit.id} className="rounded-xl bg-white px-3 py-2 text-sm font-bold text-slate-700 shadow-soft">
                  {unit.name}
                </div>
              )) : <p className="text-sm text-slate-500">Sin asignacion directa registrada.</p>}
            </div>
          </div>
        </div>

        <form onSubmit={submit} className="panel p-5">
          <p className="section-kicker">Datos editables</p>
          <h2 className="section-title">Perfil y contacto</h2>
          <div className="mt-5 grid gap-4 md:grid-cols-2">
            <label className="space-y-2">
              <span className="label">Nombre completo</span>
              <input className="input" value={form.full_name} onChange={(event) => setForm({ ...form, full_name: event.target.value })} required />
            </label>
            <label className="space-y-2">
              <span className="label">WhatsApp operativo</span>
              <input className="input" value={form.phone_whatsapp} onChange={(event) => setForm({ ...form, phone_whatsapp: event.target.value })} placeholder="+591..." />
            </label>
            <label className="space-y-2">
              <span className="label">Telegram chat ID</span>
              <input className="input" value={form.telegram_chat_id} onChange={(event) => setForm({ ...form, telegram_chat_id: event.target.value })} />
            </label>
            <label className="space-y-2">
              <span className="label">Zona horaria</span>
              <input className="input" value={form.timezone} onChange={(event) => setForm({ ...form, timezone: event.target.value })} />
            </label>
            <label className="space-y-2">
              <span className="label">Idioma</span>
              <select className="input" value={form.language} onChange={(event) => setForm({ ...form, language: event.target.value })}>
                <option value="es">Espanol</option>
                <option value="en">English</option>
              </select>
            </label>
            <label className="flex items-center gap-3 rounded-2xl border border-slate-200 bg-slate-50 p-4 text-sm font-bold text-slate-700">
              <input type="checkbox" checked={form.receives_alerts} onChange={(event) => setForm({ ...form, receives_alerts: event.target.checked })} />
              Recibir alertas operativas
            </label>
          </div>
          <div className="mt-5 flex justify-end">
            <button type="submit" className="btn-primary" disabled={saving}>
              <Save className="mr-2" size={16} aria-hidden="true" />
              {saving ? "Guardando..." : "Guardar perfil"}
            </button>
          </div>
        </form>
      </div>
    </section>
  );
}

function InfoTile({ label, value, icon: Icon }: { label: string; value: string; icon: LucideIcon }) {
  return (
    <div className="rounded-2xl border border-slate-200 bg-white p-4 shadow-soft">
      <div className="flex items-center gap-2 text-xs font-black uppercase tracking-[0.14em] text-slate-500">
        <Icon size={15} aria-hidden="true" />
        {label}
      </div>
      <p className="mt-2 text-sm font-bold text-slate-900">{value}</p>
    </div>
  );
}
