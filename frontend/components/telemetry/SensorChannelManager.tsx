"use client";

import { useState } from "react";
import { Eye, EyeOff, Plus, Power } from "lucide-react";
import { createSensorChannel, updateSensorChannel } from "@/lib/api";
import type { DeviceDashboardSchema, SensorChannel } from "@/lib/types";

export function SensorChannelManager({
  token,
  deviceId,
  schema,
  onChanged
}: {
  token: string;
  deviceId: number;
  schema: DeviceDashboardSchema;
  onChanged: () => void;
}) {
  const [busy, setBusy] = useState<number | null>(null);
  const [showAdd, setShowAdd] = useState(false);
  const [error, setError] = useState("");

  async function patch(channel: SensorChannel, payload: Parameters<typeof updateSensorChannel>[3]) {
    setBusy(channel.id);
    setError("");
    try {
      await updateSensorChannel(token, deviceId, channel.id, payload);
      onChanged();
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : "No se pudo actualizar el canal.");
    } finally {
      setBusy(null);
    }
  }

  return (
    <section className="rounded-panel border border-slate-200 bg-white p-5 shadow-panel">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div>
          <p className="section-kicker">Configuración técnica</p>
          <h3 className="mt-1 font-black text-slate-950">Sensores y gráficas</h3>
        </div>
        <button type="button" className="btn-secondary" onClick={() => setShowAdd((value) => !value)}>
          <Plus className="mr-2" size={16} />
          Agregar sensor
        </button>
      </div>
      {error ? <p className="mt-3 rounded-lg bg-red-50 p-3 text-sm font-semibold text-red-700">{error}</p> : null}
      {showAdd ? (
        <AddChannelForm
          profile={schema.device_profile}
          onCancel={() => setShowAdd(false)}
          onSubmit={async (payload) => {
            await createSensorChannel(token, deviceId, payload);
            setShowAdd(false);
            onChanged();
          }}
        />
      ) : null}
      <div className="mt-4 overflow-x-auto">
        <table className="w-full min-w-[760px] text-left text-sm">
          <thead className="border-b border-slate-200 text-[10px] font-black uppercase tracking-[0.12em] text-slate-500">
            <tr><th className="pb-3">Sensor</th><th className="pb-3">Canal</th><th className="pb-3">Estado</th><th className="pb-3">Última lectura</th><th className="pb-3">Gráfica</th><th className="pb-3">Alertas</th></tr>
          </thead>
          <tbody className="divide-y divide-slate-100">
            {schema.channels.map((channel) => (
              <tr key={channel.id}>
                <td className="py-3 font-bold text-slate-950">{channel.display_name}<span className="block text-xs font-medium text-slate-500">{channel.sensor_type}</span></td>
                <td className="py-3 font-mono text-xs text-slate-600">{channel.channel_key}</td>
                <td className="py-3 text-xs font-bold text-slate-600">{channel.status}</td>
                <td className="py-3 text-xs text-slate-500">{channel.last_valid_reading_at ? new Date(channel.last_valid_reading_at).toLocaleString("es-BO") : "Aún no vista"}</td>
                <td className="py-3">
                  <button
                    type="button"
                    disabled={busy === channel.id}
                    className="icon-button"
                    title={channel.chart_enabled ? "Ocultar gráfica" : "Mostrar gráfica"}
                    onClick={() => patch(channel, { chart_enabled: !channel.chart_enabled })}
                  >
                    {channel.chart_enabled ? <Eye size={17} /> : <EyeOff size={17} />}
                  </button>
                </td>
                <td className="py-3">
                  <button
                    type="button"
                    disabled={busy === channel.id}
                    className="icon-button"
                    title={channel.alert_enabled ? "Desactivar alertas" : "Activar alertas"}
                    onClick={() => patch(channel, { alert_enabled: !channel.alert_enabled })}
                  >
                    <Power size={17} className={channel.alert_enabled ? "text-emerald-700" : "text-slate-400"} />
                  </button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </section>
  );
}

function AddChannelForm({
  profile,
  onCancel,
  onSubmit
}: {
  profile: "silo_sensor" | "field_sensor";
  onCancel: () => void;
  onSubmit: (payload: Parameters<typeof createSensorChannel>[2]) => Promise<void>;
}) {
  const options = profile === "field_sensor"
    ? [{ key: "soil_moisture_2", sensor: "ANALOG_SOIL", port: "ADC1:GPIO32", metrics: ["SOIL_MOISTURE_RAW", "SOIL_MOISTURE_PCT"], name: "Humedad de suelo adicional" }]
    : [{ key: "level_ultrasonic_1", sensor: "JSN_SR04T", port: "TRIG:GPIO32:ECHO:GPIO33_LEVEL_SHIFTED", metrics: ["LEVEL_DISTANCE_MM", "LEVEL_PERCENT"], name: "Nivel ultrasónico" }];
  const [selected, setSelected] = useState(options[0]);
  const [busy, setBusy] = useState(false);
  return (
    <div className="mt-4 grid gap-3 rounded-lg border border-emerald-100 bg-emerald-50/50 p-4 md:grid-cols-[1fr_auto]">
      <label className="text-sm font-bold text-slate-700">
        Sensor compatible
        <select className="input mt-1" value={selected.key} onChange={(event) => setSelected(options.find((item) => item.key === event.target.value) || options[0])}>
          {options.map((option) => <option key={option.key} value={option.key}>{option.name}</option>)}
        </select>
      </label>
      <div className="flex items-end gap-2">
        <button type="button" className="btn-secondary" onClick={onCancel}>Cancelar</button>
        <button
          type="button"
          className="btn-primary"
          disabled={busy}
          onClick={async () => {
            setBusy(true);
            try {
              await onSubmit({
                channel_key: selected.key,
                sensor_type: selected.sensor,
                hardware_port: selected.port,
                metric_codes: selected.metrics,
                is_installed: true,
                is_required: false,
                is_visible_to_client: true,
                chart_enabled: true,
                alert_enabled: true,
                calibration_required: true,
                display_name: selected.name,
                display_order: 90
              });
            } finally {
              setBusy(false);
            }
          }}
        >
          {busy ? "Guardando…" : "Confirmar instalación"}
        </button>
      </div>
    </div>
  );
}
