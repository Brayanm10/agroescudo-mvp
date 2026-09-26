"use client";

import { useState } from "react";
import { CloudRain } from "lucide-react";
import { updateAdminCompanyFeature } from "@/lib/api";
import type { Company } from "@/lib/types";

export function CompanyFeatureToggle({ company, token, onChanged }: { company: Company; token: string; onChanged: () => void | Promise<void> }) {
  const enabled = company.features?.includes("PLUVIOMETRY") ?? false;
  const [busy, setBusy] = useState(false);
  const [message, setMessage] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  async function toggle() {
    setBusy(true);
    setMessage(null);
    setError(null);
    try {
      await updateAdminCompanyFeature(token, company.id, "PLUVIOMETRY", !enabled);
      setMessage(!enabled ? "Pluviometría habilitada." : "Pluviometría deshabilitada.");
      await onChanged();
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : "No se pudo actualizar el módulo.");
    } finally {
      setBusy(false);
    }
  }

  return (
    <section className="mt-5 border-t border-slate-200 pt-4" aria-label={`Módulos habilitados de ${company.name}`}>
      <p className="section-kicker">Módulos habilitados</p>
      <div className="mt-3 flex items-center justify-between gap-4 rounded-xl border border-slate-200 bg-slate-50 p-4">
        <div className="flex min-w-0 items-start gap-3">
          <CloudRain className="mt-0.5 shrink-0 text-emerald-700" size={20} aria-hidden="true" />
          <div>
            <p className="font-black text-slate-950">Pluviometría</p>
            <p className="text-xs leading-5 text-slate-500">Monitoreo meteorológico de predios y parcelas</p>
          </div>
        </div>
        <button
          type="button"
          role="switch"
          aria-checked={enabled}
          disabled={busy}
          onClick={toggle}
          className={`min-w-20 rounded-full px-3 py-2 text-xs font-black text-white transition ${enabled ? "bg-emerald-700" : "bg-slate-500"}`}
        >
          {busy ? "Guardando" : enabled ? "ON" : "OFF"}
        </button>
      </div>
      {message ? <p className="mt-2 text-xs font-bold text-emerald-700" role="status">{message}</p> : null}
      {error ? <p className="mt-2 text-xs font-bold text-red-700" role="alert">{error}</p> : null}
    </section>
  );
}
