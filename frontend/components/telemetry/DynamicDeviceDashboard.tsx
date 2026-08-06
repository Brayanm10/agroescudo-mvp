"use client";

import { useEffect, useMemo, useState } from "react";
import { RefreshCw } from "lucide-react";
import { ApiError, getCanonicalMetricReadings, getDeviceDashboardSchema, getDeviceReadings } from "@/lib/api";
import type { CanonicalMetricSeries, DeviceDashboardSchema, Reading, UserRole } from "@/lib/types";
import type { ReadingMetric } from "@/lib/telemetry";
import { EmptyState } from "@/components/EmptyState";
import { ErrorState } from "@/components/ErrorState";
import { LoadingState } from "@/components/LoadingState";
import { ReadingChart } from "@/components/ReadingChart";
import { MetricChart } from "./MetricChart";
import { SensorStatusCard } from "./SensorStatusCard";
import { SensorChannelManager } from "./SensorChannelManager";

export function DynamicDeviceDashboard({
  token,
  deviceId,
  role,
  from,
  to
}: {
  token: string;
  deviceId: number;
  role: UserRole;
  from?: string;
  to?: string;
}) {
  const [schema, setSchema] = useState<DeviceDashboardSchema | null>(null);
  const [series, setSeries] = useState<Record<string, CanonicalMetricSeries>>({});
  const [legacyReadings, setLegacyReadings] = useState<Reading[] | null>(null);
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(true);
  const [reload, setReload] = useState(0);

  useEffect(() => {
    const controller = new AbortController();
    setLoading(true);
    setError("");
    setSchema(null);
    setSeries({});
    setLegacyReadings(null);
    (async () => {
      try {
        const nextSchema = await getDeviceDashboardSchema(token, deviceId, controller.signal);
        if (controller.signal.aborted) return;
        setSchema(nextSchema);
        if (nextSchema.metrics.length === 0) {
          const readings = await getDeviceReadings(token, deviceId, controller.signal, {
            from,
            to,
            limit: 2000,
            order: "desc"
          });
          if (!controller.signal.aborted) setLegacyReadings(readings);
          return;
        }
        const visible = nextSchema.metrics.filter((metric) => metric.chart_enabled);
        const loaded = await Promise.all(
          visible.map(async (metric) => [
            `${metric.channel_key}:${metric.metric_code}`,
            await getCanonicalMetricReadings(token, deviceId, metric.metric_code, {
              channelKey: metric.channel_key,
              from,
              to,
              resolution: resolutionForRange(from, to),
              limit: 2000,
              signal: controller.signal
            })
          ] as const)
        );
        if (!controller.signal.aborted) setSeries(Object.fromEntries(loaded));
      } catch (cause) {
        if (controller.signal.aborted) return;
        if (cause instanceof ApiError && cause.status === 404) {
          try {
            const readings = await getDeviceReadings(token, deviceId, controller.signal, {
              from,
              to,
              limit: 2000,
              order: "desc"
            });
            if (!controller.signal.aborted) setLegacyReadings(readings);
            return;
          } catch (fallbackCause) {
            if (controller.signal.aborted) return;
            setError(fallbackCause instanceof ApiError ? fallbackCause.message : "No se pudo cargar la telemetría del nodo.");
            return;
          }
        }
        setError(cause instanceof ApiError ? cause.message : "No se pudo cargar el esquema de telemetría.");
      } finally {
        if (!controller.signal.aborted) setLoading(false);
      }
    })();
    return () => controller.abort();
  }, [deviceId, from, reload, to, token]);

  const channels = useMemo(
    () => new Map(schema?.channels.map((channel) => [channel.id, channel]) ?? []),
    [schema]
  );
  if (loading) return <LoadingState label="Cargando sensores y gráficas del nodo" />;
  if (error) return <ErrorState message={error} onRetry={() => setReload((value) => value + 1)} />;
  if (legacyReadings) {
    return (
      <section className="space-y-4">
        <LegacyDeviceDashboard readings={legacyReadings} />
        {schema && (role === "admin" || role === "technician") ? (
          <SensorChannelManager
            token={token}
            deviceId={deviceId}
            schema={schema}
            onChanged={() => setReload((value) => value + 1)}
          />
        ) : null}
      </section>
    );
  }
  if (!schema) return null;

  const visibleMetrics = schema.metrics.filter((metric) => metric.chart_enabled);
  return (
    <section className="space-y-4">
      <div className="flex flex-wrap items-end justify-between gap-3">
        <div>
          <p className="section-kicker">Telemetría canónica</p>
          <h3 className="mt-1 text-lg font-black text-slate-950">Sensores instalados y series verificadas</h3>
          <p className="mt-1 text-sm text-slate-500">
            Registro v{schema.registry_version} / capacidades v{schema.capabilities_version}. Cada serie pertenece a un canal explícito.
          </p>
        </div>
        <button type="button" className="btn-secondary" onClick={() => setReload((value) => value + 1)}>
          <RefreshCw className="mr-2" size={16} />
          Actualizar
        </button>
      </div>
      {visibleMetrics.length ? (
        <div className="grid gap-4 xl:grid-cols-2">
          {visibleMetrics.map((metric) => {
            const key = `${metric.channel_key}:${metric.metric_code}`;
            const points = series[key]?.points ?? [];
            const channel = channels.get(metric.channel_id);
            if (!channel) return null;
            return points.length
              ? <MetricChart key={key} metric={metric} points={points} />
              : <SensorStatusCard key={key} metric={metric} channel={channel} />;
          })}
        </div>
      ) : (
        <EmptyState title="Sin gráficas habilitadas" message="Los datos históricos se conservan aunque una gráfica esté oculta." />
      )}
      {role === "admin" || role === "technician" ? (
        <SensorChannelManager
          token={token}
          deviceId={deviceId}
          schema={schema}
          onChanged={() => setReload((value) => value + 1)}
        />
      ) : null}
    </section>
  );
}

const LEGACY_METRICS: Array<{
  metric: ReadingMetric;
  title: string;
  color: string;
  unit: string;
}> = [
  { metric: "grain_temperature", title: "Temperatura de grano", color: "#047857", unit: " C" },
  { metric: "ambient_temperature", title: "Temperatura ambiente", color: "#2563eb", unit: " C" },
  { metric: "ambient_humidity", title: "Humedad ambiente", color: "#d97706", unit: "%" },
  { metric: "level_percent", title: "Nivel estimado", color: "#059669", unit: "%" },
  { metric: "level_distance_cm", title: "Distancia ultrasónica", color: "#7c3aed", unit: " cm" },
  { metric: "soil_moisture_percent", title: "Humedad de suelo", color: "#0f766e", unit: "%" },
  { metric: "soil_temperature_c", title: "Temperatura de suelo", color: "#b45309", unit: " C" },
  { metric: "battery_voltage", title: "Batería del nodo", color: "#475569", unit: " V" }
];

function LegacyDeviceDashboard({ readings }: { readings: Reading[] }) {
  const available = LEGACY_METRICS.filter(({ metric }) =>
    readings.some((reading) => reading[metric] !== null && reading[metric] !== undefined)
  );

  return (
    <section className="space-y-4">
      <div>
        <p className="section-kicker">Telemetría del nodo</p>
        <h3 className="mt-1 text-lg font-black text-slate-950">Series históricas disponibles</h3>
        <p className="mt-1 text-sm text-slate-500">
          Vista compatible mientras el registro canónico P1.5 se habilita en el backend público.
        </p>
      </div>
      {available.length ? (
        <div className="grid gap-4 xl:grid-cols-2">
          {available.map((item) => (
            <ReadingChart
              key={item.metric}
              title={item.title}
              readings={readings}
              metric={item.metric}
              color={item.color}
              unit={item.unit}
            />
          ))}
        </div>
      ) : (
        <EmptyState title="Sin lecturas para este nodo" message="No se recibieron métricas en el periodo seleccionado." />
      )}
    </section>
  );
}

function resolutionForRange(from?: string, to?: string): "raw" | "15m" | "1h" {
  if (!from) return "raw";
  const duration = (to ? new Date(to).getTime() : Date.now()) - new Date(from).getTime();
  return duration > 14 * 86400000 ? "1h" : duration > 2 * 86400000 ? "15m" : "raw";
}
