"use client";

import { useEffect, useMemo, useState } from "react";
import { RefreshCw } from "lucide-react";
import { ApiError, getCanonicalMetricReadings, getDeviceChartContext, getDeviceDashboardSchema, getDeviceReadings } from "@/lib/api";
import type { CanonicalMetricSeries, DeviceChartContext, DeviceDashboardSchema, Reading, UserRole } from "@/lib/types";
import { automaticResolution, type ReadingMetric, type TelemetryResolution } from "@/lib/telemetry";
import { EmptyState } from "@/components/EmptyState";
import { ErrorState } from "@/components/ErrorState";
import { LoadingState } from "@/components/LoadingState";
import { ReadingChart, type ChartThresholds } from "@/components/ReadingChart";
import { MetricChart } from "./MetricChart";
import { SensorStatusCard } from "./SensorStatusCard";
import { SensorChannelManager } from "./SensorChannelManager";

export function DynamicDeviceDashboard({
  token,
  deviceId,
  role,
  from,
  to,
  resolution = "auto",
  rangeLabel
}: {
  token: string;
  deviceId: number;
  role: UserRole;
  from?: string;
  to?: string;
  resolution?: TelemetryResolution;
  rangeLabel?: string;
}) {
  const [schema, setSchema] = useState<DeviceDashboardSchema | null>(null);
  const [series, setSeries] = useState<Record<string, CanonicalMetricSeries>>({});
  const [context, setContext] = useState<DeviceChartContext | null>(null);
  const [legacyReadings, setLegacyReadings] = useState<Reading[] | null>(null);
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(true);
  const [reload, setReload] = useState(0);
  const effectiveResolution = resolution === "auto" ? automaticResolution(from, to) : resolution;

  useEffect(() => {
    const controller = new AbortController();
    setLoading(true);
    setError("");
    setSchema(null);
    setSeries({});
    setContext(null);
    setLegacyReadings(null);
    (async () => {
      try {
        const [nextSchema, nextContext] = await Promise.all([
          getDeviceDashboardSchema(token, deviceId, controller.signal),
          getDeviceChartContext(token, deviceId, { from, to, signal: controller.signal }).catch((cause) => {
            if (cause instanceof ApiError && cause.status === 404) return null;
            throw cause;
          })
        ]);
        if (controller.signal.aborted) return;
        setSchema(nextSchema);
        setContext(nextContext);
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
              resolution: effectiveResolution,
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
  }, [deviceId, effectiveResolution, from, reload, to, token]);

  const channels = useMemo(
    () => new Map(schema?.channels.map((channel) => [channel.id, channel]) ?? []),
    [schema]
  );
  if (loading) return <LoadingState label="Cargando sensores y gráficas del nodo" />;
  if (error) return <ErrorState message={error} onRetry={() => setReload((value) => value + 1)} />;
  if (legacyReadings) {
    return (
      <section className="space-y-4">
        <LegacyDeviceDashboard
          readings={legacyReadings}
          thresholds={schema?.thresholds ?? {}}
          context={context}
          periodLabel={rangeLabel}
          resolutionLabel={resolutionName(effectiveResolution)}
        />
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

  const visibleMetrics = schema.metrics
    .filter((metric) => metric.chart_enabled)
    .sort((a, b) => metricPriority(a.metric_code) - metricPriority(b.metric_code) || a.display_order - b.display_order);
  const distanceSeries = Object.values(series).find((item) => item.metric_code === "LEVEL_DISTANCE_MM");
  const distanceCurrent = distanceSeries?.summary?.current ?? null;
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
            const metricSeries = series[key];
            const channel = channels.get(metric.channel_id);
            if (!channel) return null;
            const annotations = annotationsForMetric(metric.metric_code, context);
            return metricSeries?.points.length
              ? <MetricChart
                  key={key}
                  metric={metric}
                  series={metricSeries}
                  thresholds={thresholdsForMetric(metric.metric_code, schema.thresholds ?? {})}
                  events={annotations.events}
                  actions={annotations.actions}
                  periodLabel={rangeLabel}
                  resolutionLabel={resolutionName(effectiveResolution)}
                  levelDistanceCm={distanceCurrent === null ? null : distanceCurrent / 10}
                  calibrationStatus={metric.metric_code === "LEVEL_PERCENT" ? (metricSeries.summary?.current === null && distanceCurrent !== null ? "pending" : "configured") : undefined}
                />
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

function LegacyDeviceDashboard({
  readings,
  thresholds,
  context,
  periodLabel,
  resolutionLabel
}: {
  readings: Reading[];
  thresholds: Record<string, number>;
  context: DeviceChartContext | null;
  periodLabel?: string;
  resolutionLabel?: string;
}) {
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
            <div key={item.metric} className={item.metric === "grain_temperature" || item.metric === "level_percent" ? "xl:col-span-2" : ""}>
              <ReadingChart
                title={item.title}
                readings={readings}
                metric={item.metric}
                color={item.color}
                unit={item.unit}
                thresholds={thresholdsForLegacyMetric(item.metric, thresholds)}
                events={annotationsForMetric(legacyMetricCode(item.metric), context).events}
                actions={annotationsForMetric(legacyMetricCode(item.metric), context).actions}
                periodLabel={periodLabel}
                resolutionLabel={resolutionLabel}
              />
            </div>
          ))}
        </div>
      ) : (
        <EmptyState title="Sin lecturas para este nodo" message="No se recibieron métricas en el periodo seleccionado." />
      )}
    </section>
  );
}

function thresholdsForMetric(metricCode: string, values: Record<string, number>): ChartThresholds {
  switch (metricCode) {
    case "GRAIN_TEMPERATURE_C":
      return { max: values.grain_temperature, criticalMax: values.critical_temperature };
    case "AMBIENT_RELATIVE_HUMIDITY_PCT":
      return { max: values.ambient_humidity, criticalMax: values.critical_humidity };
    case "LEVEL_PERCENT":
      return { min: values.level_percent_low, max: values.level_percent_high };
    case "SOIL_MOISTURE_PCT":
      return { min: values.soil_moisture_low, max: values.soil_moisture_high };
    case "BATTERY_VOLTAGE_MV":
      return { min: values.battery_voltage === undefined ? undefined : values.battery_voltage * 1000 };
    default:
      return {};
  }
}

function metricPriority(metricCode: string) {
  return ({ GRAIN_TEMPERATURE_C: 0, AMBIENT_RELATIVE_HUMIDITY_PCT: 1, LEVEL_PERCENT: 2 } as Record<string, number>)[metricCode] ?? 10;
}

function annotationsForMetric(metricCode: string, context: DeviceChartContext | null) {
  if (!context) return { events: [], actions: [] };
  const events = context.events.filter((event) => event.metric_code === metricCode);
  const alertIds = new Set(events.map((event) => event.id));
  const actions = context.actions.filter((action) =>
    action.alert_id !== null ? alertIds.has(action.alert_id) : metricCode === "GRAIN_TEMPERATURE_C"
  );
  return { events, actions };
}

function legacyMetricCode(metric: ReadingMetric) {
  return ({
    grain_temperature: "GRAIN_TEMPERATURE_C",
    ambient_temperature: "AMBIENT_TEMPERATURE_C",
    ambient_humidity: "AMBIENT_RELATIVE_HUMIDITY_PCT",
    level_distance_cm: "LEVEL_DISTANCE_MM",
    level_percent: "LEVEL_PERCENT",
    soil_moisture_percent: "SOIL_MOISTURE_PCT",
    soil_temperature_c: "SOIL_TEMPERATURE_C",
    battery_voltage: "BATTERY_VOLTAGE_MV"
  } as Record<ReadingMetric, string>)[metric];
}

function thresholdsForLegacyMetric(metric: ReadingMetric, values: Record<string, number>): ChartThresholds {
  switch (metric) {
    case "grain_temperature":
      return { max: values.grain_temperature, criticalMax: values.critical_temperature };
    case "ambient_humidity":
      return { max: values.ambient_humidity, criticalMax: values.critical_humidity };
    case "level_percent":
      return { min: values.level_percent_low, max: values.level_percent_high };
    case "soil_moisture_percent":
      return { min: values.soil_moisture_low, max: values.soil_moisture_high };
    case "battery_voltage":
      return { min: values.battery_voltage };
    default:
      return {};
  }
}

function resolutionName(value: Exclude<TelemetryResolution, "auto">) {
  return ({ raw: "cada lectura", "5m": "promedio 5 min", "15m": "promedio 15 min", "1h": "promedio horario", "1d": "promedio diario" } as const)[value];
}
