"use client";

import { FormEvent, useState } from "react";
import { Eye, EyeOff, KeyRound, Save } from "lucide-react";
import { ErrorState } from "@/components/ErrorState";
import { changePassword } from "@/lib/api";
import { passwordRequirements, validatePasswordStrength } from "@/lib/validation/password";

export function ChangePasswordView({ token }: { token: string }) {
  const [form, setForm] = useState({ current_password: "", new_password: "", confirm_password: "" });
  const [show, setShow] = useState(false);
  const [saving, setSaving] = useState(false);
  const [message, setMessage] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const validation = form.new_password ? validatePasswordStrength(form.new_password) : null;
  const mismatch = form.confirm_password && form.new_password !== form.confirm_password ? "La confirmacion no coincide." : null;

  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setError(null);
    setMessage(null);
    const strengthError = validatePasswordStrength(form.new_password);
    if (strengthError) {
      setError(strengthError);
      return;
    }
    if (form.new_password !== form.confirm_password) {
      setError("La confirmacion no coincide.");
      return;
    }
    setSaving(true);
    try {
      await changePassword(token, form);
      setForm({ current_password: "", new_password: "", confirm_password: "" });
      setMessage("Contrasena actualizada. Usa la nueva clave en tu proximo inicio de sesion.");
    } catch (err) {
      setError(err instanceof Error ? err.message : "No se pudo cambiar la contrasena.");
    } finally {
      setSaving(false);
    }
  }

  return (
    <section className="mx-auto max-w-4xl space-y-5">
      {error ? <ErrorState message={error} /> : null}
      {message ? (
        <div className="rounded-2xl border border-emerald-200 bg-emerald-50 p-4 text-sm font-bold text-emerald-800">
          {message}
        </div>
      ) : null}
      <form onSubmit={submit} className="panel p-6">
        <div className="flex items-start gap-4">
          <div className="rounded-2xl bg-emerald-50 p-3 text-emerald-700">
            <KeyRound size={28} aria-hidden="true" />
          </div>
          <div>
            <p className="section-kicker">Seguridad de cuenta</p>
            <h2 className="section-title">Cambiar contrasena</h2>
            <p className="section-subtitle">Actualiza tu acceso sin afectar sensores, reportes ni asignaciones del piloto.</p>
          </div>
        </div>
        <div className="mt-6 grid gap-4">
          <PasswordInput label="Contrasena actual" value={form.current_password} show={show} onChange={(value) => setForm({ ...form, current_password: value })} />
          <PasswordInput label="Nueva contrasena" value={form.new_password} show={show} onChange={(value) => setForm({ ...form, new_password: value })} />
          <PasswordInput label="Confirmar nueva contrasena" value={form.confirm_password} show={show} onChange={(value) => setForm({ ...form, confirm_password: value })} />
        </div>
        <div className="mt-4 rounded-2xl border border-slate-200 bg-slate-50 p-4">
          <div className="flex flex-wrap items-center justify-between gap-3">
            <p className="text-xs font-black uppercase tracking-[0.14em] text-slate-500">Requisitos</p>
            <button type="button" onClick={() => setShow((value) => !value)} className="btn-secondary py-2 text-xs">
              {show ? <EyeOff className="mr-2" size={14} aria-hidden="true" /> : <Eye className="mr-2" size={14} aria-hidden="true" />}
              {show ? "Ocultar" : "Mostrar"}
            </button>
          </div>
          <ul className="mt-3 grid gap-2 text-sm font-semibold text-slate-600 sm:grid-cols-3">
            {passwordRequirements.map((item) => <li key={item}>{item}</li>)}
          </ul>
          {validation || mismatch ? <p className="mt-3 text-sm font-bold text-amber-700">{validation || mismatch}</p> : null}
        </div>
        <div className="mt-5 flex justify-end">
          <button type="submit" className="btn-primary" disabled={saving || Boolean(validation) || Boolean(mismatch)}>
            <Save className="mr-2" size={16} aria-hidden="true" />
            {saving ? "Actualizando..." : "Actualizar contrasena"}
          </button>
        </div>
      </form>
    </section>
  );
}

function PasswordInput({
  label,
  value,
  show,
  onChange
}: {
  label: string;
  value: string;
  show: boolean;
  onChange: (value: string) => void;
}) {
  return (
    <label className="space-y-2">
      <span className="label">{label}</span>
      <input className="input" type={show ? "text" : "password"} value={value} onChange={(event) => onChange(event.target.value)} required />
    </label>
  );
}
