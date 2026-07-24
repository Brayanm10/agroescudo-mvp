"use client";

import { FormEvent, ReactNode, useCallback, useEffect, useMemo, useState } from "react";
import { CheckCircle2, Eye, History, Power, Save, SlidersHorizontal } from "lucide-react";
import {
  activateDeviceCalibration,
  createDeviceCalibration,
  deactivateDeviceCalibration,
  getDeviceCalibrations,
  previewDeviceCalibration
} from "@/lib/api";
import type { Calibration, CalibrationInput, CalibrationMethod, Device, UserRole } from "@/lib/types";
import { deviceProfile } from "@/lib/telemetry";

type Props = {
  token: string;
  device: Device;
  role: UserRole;
  onChanged?: () => void;
};

type FormState = {
  variable_type: string;
  method: CalibrationMethod;
  raw_value: number;
  offset: number;
  dry_raw: number;
  wet_raw: number;
  dry_percent: number;
  wet_percent: number;
  empty_distance_cm: number;
  full_distance_cm: number;
  reference_instrument: string;
  notes: string;
};

const labelByVariable: Record<string, string> = {
  level_percent: "Nivel estimado",
  soil_moisture_percent: "Humedad de suelo",
  grain_temperature: "Temperatura de grano",
  ambient_temperature: "Temperatura ambiente",
  ambient_humidity: "Humedad ambiente",
  soil_temperature_c: "Temperatura de suelo"
};

function initialState(device: Device): FormState {
  const field = deviceProfile(device) === "field_sensor";
  return {
    variable_type: field ? "soil_moisture_percent" : "level_percent",
    method: field ? "LINEAR_TWO_POINT" : "LEVEL_GEOMETRY",
    raw_value: field ? 2048 : 300,
    offset: 0,
    dry_raw: 3200,
    wet_raw: 900,
    dry_percent: 0,
    wet_percent: 100,
    empty_distance_cm: device.empty_distance_cm ?? 600,
    full_distance_cm: device.full_distance_cm ?? 50,
    reference_instrument: "",
    notes: ""
  };
}

function variablesFor(device: Device) {
  if (deviceProfile(device) === "field_sensor") {
    return ["soil_moisture_percent", "ambient_temperature", "ambient_humidity", "soil_temperature_c"];
  }
  return ["level_percent", "grain_temperature", "ambient_temperature", "ambient_humidity"];
}

function defaultMethod(variable: string): CalibrationMethod {
  if (variable === "level_percent") return "LEVEL_GEOMETRY";
  if (variable === "soil_moisture_percent") return "LINEAR_TWO_POINT";
  return "OFFSET";
}

function payloadFrom(form: FormState): CalibrationInput {
  const base: CalibrationInput = {
    variable_type: form.variable_type,
    method: form.method,
    raw_value: form.raw_value,
    reference_instrument: form.reference_instrument || null,
    notes: form.notes || null
  };
  if (form.method === "OFFSET") return { ...base, offset: form.offset };
  if (form.method === "LINEAR_TWO_POINT") {
    return {
      ...base,
      dry_raw: form.dry_raw,
      wet_raw: form.wet_raw,
      dry_percent: form.dry_percent,
      wet_percent: form.wet_percent
    };
  }
  return {
    ...base,
    parameters: {
      mode: "two_distance",
      empty_distance_cm: form.empty_distance_cm,
      full_distance_cm: form.full_distance_cm
    }
  };
}

export function CalibrationWizard({ token, device, role, onChanged }: Props) {
  const canEdit = role === "admin" || role === "technician";
  const [form, setForm] = useState<FormState>(() => initialState(device));
  const [history, setHistory] = useState<Calibration[]>([]);
  const [preview, setPreview] = useState<string | null>(null);
  const [message, setMessage] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const variables = useMemo(() => variablesFor(device), [device]);

  const loadHistory = useCallback(async () => {
    setHistory(await getDeviceCalibrations(token, device.id));
  }, [device.id, token]);

  useEffect(() => {
    setForm(initialState(device));
    setPreview(null);
    setMessage(null);
    loadHistory().catch(() => setMessage("No se pudo consultar el historial de calibración."));
  }, [device, loadHistory]);

  async function previewCalibration() {
    setBusy(true);
    setMessage(null);
    try {
      const result = await previewDeviceCalibration(token, device.id, payloadFrom(form));
      setPreview(
        result.calibrated_value === null
          ? "La configuración no produce un valor calibrado para esta muestra."
          : `${result.raw_value ?? form.raw_value} → ${result.calibrated_value.toFixed(2)}`
      );
    } catch (error) {
      setMessage(error instanceof Error ? error.message : "No se pudo previsualizar la calibración.");
    } finally {
      setBusy(false);
    }
  }

  async function save(event: FormEvent) {
    event.preventDefault();
    setBusy(true);
    setMessage(null);
    try {
      await createDeviceCalibration(token, device.id, payloadFrom(form));
      await loadHistory();
      onChanged?.();
      setMessage("Nueva versión creada y activada. Las lecturas históricas no fueron modificadas.");
    } catch (error) {
      setMessage(error instanceof Error ? error.message : "No se pudo guardar la calibración.");
    } finally {
      setBusy(false);
    }
  }

  async function toggle(item: Calibration) {
    setBusy(true);
    setMessage(null);
    try {
      if (item.is_active) {
        await deactivateDeviceCalibration(token, device.id, item.id);
      } else {
        await activateDeviceCalibration(token, device.id, item.id);
      }
      await loadHistory();
      onChanged?.();
    } catch (error) {
      setMessage(error instanceof Error ? error.message : "No se pudo cambiar la versión activa.");
    } finally {
      setBusy(false);
    }
  }

  if (!canEdit) {
    const active = history.filter((item) => item.is_active);
    return (
      <section className="panel p-5">
        <p className="section-kicker">Trazabilidad metrológica</p>
        <h3 className="mt-1 font-black text-slate-950">Estado de calibración</h3>
        <div className="mt-4 space-y-2">
          {active.length ? active.map((item) => (
            <div key={item.id} className="flex items-center justify-between gap-3 rounded-xl border border-emerald-100 bg-emerald-50 p-3">
              <div>
                <p className="font-bold text-slate-950">{labelByVariable[item.variable_type] || item.variable_type}</p>
                <p className="text-xs text-slate-600">Versión {item.calibration_version} · {new Date(item.calibrated_at).toLocaleDateString("es-BO")}</p>
              </div>
              <CheckCircle2 className="text-emerald-700" size={20} />
            </div>
          )) : <p className="text-sm text-slate-600">Calibración pendiente de validación técnica.</p>}
        </div>
      </section>
    );
  }

  return (
    <section className="panel overflow-hidden">
      <div className="border-b border-slate-200 bg-slate-50 px-5 py-4">
        <div className="flex items-center gap-3">
          <span className="flex h-10 w-10 items-center justify-center rounded-xl bg-emerald-100 text-emerald-800">
            <SlidersHorizontal size={19} />
          </span>
          <div>
            <p className="section-kicker">Asistente técnico</p>
            <h3 className="font-black text-slate-950">Calibración versionada</h3>
          </div>
        </div>
        <p className="mt-2 text-sm leading-6 text-slate-600">Previsualiza el resultado antes de crear una versión. El valor raw y las versiones anteriores se conservan.</p>
      </div>
      <form onSubmit={save} className="p-5">
        <div className="grid gap-3 md:grid-cols-2">
          <Label text="Variable">
            <select
              className="input"
              value={form.variable_type}
              onChange={(event) => {
                const variable = event.target.value;
                setForm((current) => ({ ...current, variable_type: variable, method: defaultMethod(variable) }));
                setPreview(null);
              }}
            >
              {variables.map((variable) => <option key={variable} value={variable}>{labelByVariable[variable]}</option>)}
            </select>
          </Label>
          <Label text="Método">
            <select className="input" value={form.method} onChange={(event) => setForm({ ...form, method: event.target.value as CalibrationMethod })}>
              <option value="OFFSET">Corrección por offset</option>
              <option value="LINEAR_TWO_POINT">Dos puntos lineales</option>
              {form.variable_type === "level_percent" ? <option value="LEVEL_GEOMETRY">Geometría de nivel</option> : null}
            </select>
          </Label>
          <Label text="Muestra raw para previsualizar">
            <input className="input" type="number" step="0.01" value={form.raw_value} onChange={(event) => setForm({ ...form, raw_value: Number(event.target.value) })} />
          </Label>
          {form.method === "OFFSET" ? (
            <Label text="Offset">
              <input className="input" type="number" step="0.01" value={form.offset} onChange={(event) => setForm({ ...form, offset: Number(event.target.value) })} />
            </Label>
          ) : null}
          {form.method === "LINEAR_TWO_POINT" ? (
            <>
              <Label text="Raw seco"><input className="input" type="number" value={form.dry_raw} onChange={(event) => setForm({ ...form, dry_raw: Number(event.target.value) })} /></Label>
              <Label text="Valor seco (%)"><input className="input" type="number" min="0" max="100" value={form.dry_percent} onChange={(event) => setForm({ ...form, dry_percent: Number(event.target.value) })} /></Label>
              <Label text="Raw húmedo"><input className="input" type="number" value={form.wet_raw} onChange={(event) => setForm({ ...form, wet_raw: Number(event.target.value) })} /></Label>
              <Label text="Valor húmedo (%)"><input className="input" type="number" min="0" max="100" value={form.wet_percent} onChange={(event) => setForm({ ...form, wet_percent: Number(event.target.value) })} /></Label>
            </>
          ) : null}
          {form.method === "LEVEL_GEOMETRY" ? (
            <>
              <Label text="Distancia en vacío (cm)"><input className="input" type="number" min="0.1" step="0.1" value={form.empty_distance_cm} onChange={(event) => setForm({ ...form, empty_distance_cm: Number(event.target.value) })} /></Label>
              <Label text="Distancia en lleno (cm)"><input className="input" type="number" min="0.1" step="0.1" value={form.full_distance_cm} onChange={(event) => setForm({ ...form, full_distance_cm: Number(event.target.value) })} /></Label>
            </>
          ) : null}
          <Label text="Instrumento de referencia"><input className="input" value={form.reference_instrument} onChange={(event) => setForm({ ...form, reference_instrument: event.target.value })} placeholder="Opcional" /></Label>
          <Label text="Notas"><input className="input" value={form.notes} onChange={(event) => setForm({ ...form, notes: event.target.value })} placeholder="Condiciones y responsable" /></Label>
        </div>
        <div className="mt-4 flex flex-wrap items-center gap-2">
          <button type="button" disabled={busy} onClick={previewCalibration} className="btn-secondary"><Eye className="mr-2" size={16} />Previsualizar</button>
          <button type="submit" disabled={busy} className="btn-primary"><Save className="mr-2" size={16} />Crear versión</button>
          {preview ? <span className="rounded-lg bg-emerald-50 px-3 py-2 text-sm font-bold text-emerald-800">{preview}</span> : null}
        </div>
        {message ? <p className="mt-3 text-sm font-semibold text-slate-600">{message}</p> : null}
      </form>
      <div className="border-t border-slate-200 px-5 py-4">
        <div className="flex items-center gap-2">
          <History size={16} className="text-emerald-700" />
          <h4 className="font-black text-slate-950">Historial inmutable</h4>
        </div>
        <div className="mt-3 space-y-2">
          {history.length ? history.map((item) => (
            <div key={item.id} className="grid gap-3 rounded-xl border border-slate-200 p-3 sm:grid-cols-[1fr_auto] sm:items-center">
              <div>
                <p className="font-bold text-slate-950">{labelByVariable[item.variable_type] || item.variable_type} · versión {item.calibration_version}</p>
                <p className="text-xs leading-5 text-slate-500">{item.method} · {new Date(item.calibrated_at).toLocaleString("es-BO")} · {item.calibrated_by_name || "Responsable no registrado"}</p>
              </div>
              <button type="button" disabled={busy} onClick={() => toggle(item)} className={item.is_active ? "btn-secondary" : "btn-primary"}>
                <Power className="mr-2" size={15} />{item.is_active ? "Desactivar" : "Activar"}
              </button>
            </div>
          )) : <p className="text-sm text-slate-500">No existen versiones registradas para este nodo.</p>}
        </div>
      </div>
    </section>
  );
}

function Label({ text, children }: { text: string; children: ReactNode }) {
  return (
    <label className="block">
      <span className="mb-1.5 block text-xs font-black uppercase tracking-[0.1em] text-slate-500">{text}</span>
      {children}
    </label>
  );
}
