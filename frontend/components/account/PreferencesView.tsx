"use client";

import { FormEvent, useState } from "react";
import { BellRing, Clock3, Save, Settings2 } from "lucide-react";
import { ErrorState } from "@/components/ErrorState";
import { updateMe } from "@/lib/api";
import type { AppData } from "@/lib/types";

export function PreferencesView({
  data,
  token,
  onChanged
}: {
  data: AppData;
  token: string;
  onChanged: () => void;
}) {
  const [form, setForm] = useState({
    receives_alerts: data.me.receives_alerts,
    language: data.me.language || "es",
    timezone: data.me.timezone || "America/La_Paz",
    phone_whatsapp: data.me.phone_whatsapp || "",
    telegram_chat_id: data.me.telegram_chat_id || ""
  });
  const [saving, setSaving] = useState(false);
  const [message, setMessage] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setSaving(true);
    setMessage(null);
    setError(null);
    try {
      await updateMe(token, {
        receives_alerts: form.receives_alerts,
        language: form.language,
        timezone: form.timezone,
        phone_whatsapp: form.phone_whatsapp || null,
        telegram_chat_id: form.telegram_chat_id || null
      });
      setMessage("Preferencias guardadas correctamente.");
      onChanged();
    } catch (err) {
      setError(err instanceof Error ? err.message : "No se pudieron guardar las preferencias.");
    } finally {
      setSaving(false);
    }
  }

  return (
    <section className="mx-auto max-w-5xl space-y-5">
      {error ? <ErrorState message={error} /> : null}
      {message ? <div className="rounded-2xl border border-emerald-200 bg-emerald-50 p-4 text-sm font-bold text-emerald-800">{message}</div> : null}
      <form onSubmit={submit} className="panel p-6">
        <div className="flex items-start gap-4">
          <div className="rounded-2xl bg-emerald-50 p-3 text-emerald-700">
            <Settings2 size={28} aria-hidden="true" />
          </div>
          <div>
            <p className="section-kicker">Preferencias</p>
            <h2 className="section-title">Alertas y entorno operativo</h2>
            <p className="section-subtitle">Controla como se presenta la informacion de cuenta y los canales usados para seguimiento operativo.</p>
          </div>
        </div>
        <div className="mt-6 grid gap-4 lg:grid-cols-2">
          <div className="rounded-2xl border border-slate-200 bg-white p-5 shadow-soft">
            <BellRing className="text-emerald-700" size={22} aria-hidden="true" />
            <h3 className="mt-3 font-black text-slate-950">Canales de alerta</h3>
            <div className="mt-4 grid gap-3">
              <label className="flex items-center gap-3 rounded-xl bg-slate-50 p-3 text-sm font-bold text-slate-700">
                <input type="checkbox" checked={form.receives_alerts} onChange={(event) => setForm({ ...form, receives_alerts: event.target.checked })} />
                Recibir alertas operativas
              </label>
              <input className="input" placeholder="WhatsApp operativo" value={form.phone_whatsapp} onChange={(event) => setForm({ ...form, phone_whatsapp: event.target.value })} />
              <input className="input" placeholder="Telegram chat ID" value={form.telegram_chat_id} onChange={(event) => setForm({ ...form, telegram_chat_id: event.target.value })} />
            </div>
          </div>
          <div className="rounded-2xl border border-slate-200 bg-white p-5 shadow-soft">
            <Clock3 className="text-emerald-700" size={22} aria-hidden="true" />
            <h3 className="mt-3 font-black text-slate-950">Formato operativo</h3>
            <div className="mt-4 grid gap-3">
              <label className="space-y-2">
                <span className="label">Idioma</span>
                <select className="input" value={form.language} onChange={(event) => setForm({ ...form, language: event.target.value })}>
                  <option value="es">Espanol</option>
                  <option value="en">English</option>
                </select>
              </label>
              <label className="space-y-2">
                <span className="label">Zona horaria</span>
                <input className="input" value={form.timezone} onChange={(event) => setForm({ ...form, timezone: event.target.value })} />
              </label>
            </div>
          </div>
        </div>
        <div className="mt-5 flex justify-end">
          <button type="submit" className="btn-primary" disabled={saving}>
            <Save className="mr-2" size={16} aria-hidden="true" />
            {saving ? "Guardando..." : "Guardar preferencias"}
          </button>
        </div>
      </form>
    </section>
  );
}
