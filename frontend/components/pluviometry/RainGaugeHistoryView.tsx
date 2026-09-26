"use client";

import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { ArrowLeft, CloudRain, Gauge, Radio } from "lucide-react";
import { AgroRainChart, AgroTrendChart } from "@/components/charts";
import { EmptyState } from "@/components/EmptyState";
import { ErrorState } from "@/components/ErrorState";
import { LoadingState } from "@/components/LoadingState";
import {
  ApiError,
  getCanonicalMetricReadings,
  getDevice,
  getDeviceDashboardSchema,
  getPluviometryMapSnapshot
} from "@/lib/api";
import { readSessionToken } from "@/lib/session";
import { formatDateTimeInTimeZone } from "@/lib/format";
import type {
  CanonicalMetricSeries,
  DashboardMetric,
  DeviceDashboardSchema,
  PluviometryMapSnapshot,
  RainGaugeMapDevice
} from "@/lib/types";
import {
  detailQueryPath,
  displayUnit,
  hasRecordedZero,
  historyStats,
  METRIC_UI,
  periodLabel,
  periodRequest,
  PERIODS,
  resolveHistorySelection,
  supportedRainGaugeMetrics,
  type RainGaugeMetricCode,
  type RainGaugePeriod
} from "./detail-model";
import { pluviometryQueryPath, STATUS_PRESENTATION } from "./map-model";
import { WindDirectionSummary } from "./WindDirectionSummary";

export function RainGaugeHistoryView({ deviceId }: { deviceId: number }) {
  const router = useRouter();
  const [schema, setSchema] = useState<DeviceDashboardSchema | null>(null);
  const [snapshot, setSnapshot] = useState<PluviometryMapSnapshot | null>(null);
  const [mapDevice, setMapDevice] = useState<RainGaugeMapDevice | null>(null);
  const [metric, setMetric] = useState<DashboardMetric | null>(null);
  const [period, setPeriod] = useState<RainGaugePeriod>("24h");
  const [series, setSeries] = useState<CanonicalMetricSeries | null>(null);
  const [metaLoading, setMetaLoading] = useState(true);
  const [seriesLoading, setSeriesLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [reload, setReload] = useState(0);
  const requestSequence = useRef(0);

  useEffect(() => {
    const token = readSessionToken();
    if (!token) return;
    const controller = new AbortController();
    setMetaLoading(true);
    setError(null);
    setSchema(null);
    setSnapshot(null);
    setMapDevice(null);
    setSeries(null);
    void Promise.all([
      getDevice(token, deviceId, controller.signal),
      getDeviceDashboardSchema(token, deviceId, controller.signal)
    ])
      .then(async ([device, nextSchema]) => {
        if (device.device_type !== "rain_gauge" || nextSchema.device_profile !== "rain_gauge") {
          throw new ApiError("El dispositivo solicitado no es un pluviómetro.", 404);
        }
        const nextSnapshot = await getPluviometryMapSnapshot(token, device.site_id, controller.signal);
        if (controller.signal.aborted) return;
        const nextMapDevice = nextSnapshot.devices.find((item) => item.id === deviceId);
        if (!nextMapDevice) throw new ApiError("El pluviómetro no está disponible para este usuario.", 403);
        const query = new URLSearchParams(window.location.search);
        const selection = resolveHistorySelection(nextSchema.metrics, query.get("variable"), query.get("period"));
        setSchema(nextSchema);
        setSnapshot(nextSnapshot);
        setMapDevice(nextMapDevice);
        setMetric(selection.metric);
        setPeriod(selection.period);
        if (selection.metric) {
          window.history.replaceState(null, "", detailQueryPath(deviceId, selection.metric.metric_code, selection.period));
        }
      })
      .catch((reason: unknown) => {
        if (controller.signal.aborted) return;
        setError(detailError(reason));
      })
      .finally(() => {
        if (!controller.signal.aborted) setMetaLoading(false);
      });
    return () => controller.abort();
  }, [deviceId, reload]);

  const availableMetrics = useMemo(() => supportedRainGaugeMetrics(schema?.metrics ?? []), [schema]);

  useEffect(() => {
    if (!availableMetrics.length) return;
    const handleHistory = () => {
      const query = new URLSearchParams(window.location.search);
      const selection = resolveHistorySelection(availableMetrics, query.get("variable"), query.get("period"));
      setMetric(selection.metric);
      setPeriod(selection.period);
    };
    window.addEventListener("popstate", handleHistory);
    return () => window.removeEventListener("popstate", handleHistory);
  }, [availableMetrics]);

  useEffect(() => {
    if (!metric) {
      setSeries(null);
      return;
    }
    const token = readSessionToken();
    if (!token) return;
    const controller = new AbortController();
    const sequence = ++requestSequence.current;
    const request = periodRequest(period);
    setSeriesLoading(true);
    setError(null);
    setSeries(null);
    void getCanonicalMetricReadings(token, deviceId, metric.metric_code, {
      channelKey: metric.channel_key,
      ...request,
      signal: controller.signal
    })
      .then((nextSeries) => {
        if (!controller.signal.aborted && sequence === requestSequence.current) setSeries(nextSeries);
      })
      .catch((reason: unknown) => {
        if (!controller.signal.aborted && sequence === requestSequence.current) setError(detailError(reason));
      })
      .finally(() => {
        if (!controller.signal.aborted && sequence === requestSequence.current) setSeriesLoading(false);
      });
    return () => controller.abort();
  }, [deviceId, metric, period]);

  const updateSelection = useCallback((nextMetric: DashboardMetric, nextPeriod: RainGaugePeriod) => {
    window.history.pushState(null, "", detailQueryPath(deviceId, nextMetric.metric_code, nextPeriod));
    setMetric(nextMetric);
    setPeriod(nextPeriod);
  }, [deviceId]);

  if (metaLoading) return <LoadingState label="Cargando pluviómetro autorizado" />;
  if (error && !schema) return <ErrorState message={error} onRetry={() => setReload((value) => value + 1)} />;
  if (!schema || !snapshot || !mapDevice) return <EmptyState title="Pluviómetro no disponible" message="No se encontró un pluviómetro autorizado para esta ruta." />;

  return (
    <RainGaugeHistoryContent
      schema={schema}
      snapshot={snapshot}
      device={mapDevice}
      metrics={availableMetrics}
      metric={metric}
      period={period}
      series={series}
      seriesLoading={seriesLoading}
      error={error}
      onMetricChange={(nextMetric) => updateSelection(nextMetric, period)}
      onPeriodChange={(nextPeriod) => metric && updateSelection(metric, nextPeriod)}
      onDeviceChange={(nextDeviceId) => metric && router.push(detailQueryPath(nextDeviceId, metric.metric_code, period))}
      onRetry={() => setMetric((current) => current ? { ...current } : current)}
    />
  );
}

type ContentProps = {
  schema: DeviceDashboardSchema;
  snapshot: PluviometryMapSnapshot;
  device: RainGaugeMapDevice;
  metrics: DashboardMetric[];
  metric: DashboardMetric | null;
  period: RainGaugePeriod;
  series: CanonicalMetricSeries | null;
  seriesLoading: boolean;
  error: string | null;
  onMetricChange: (metric: DashboardMetric) => void;
  onPeriodChange: (period: RainGaugePeriod) => void;
  onDeviceChange: (deviceId: number) => void;
  onRetry: () => void;
};

export function RainGaugeHistoryContent({
  schema,
  snapshot,
  device,
  metrics,
  metric,
  period,
  series,
  seriesLoading,
  error,
  onMetricChange,
  onPeriodChange,
  onDeviceChange,
  onRetry
}: ContentProps) {
  const status = STATUS_PRESENTATION[device.status];
  const stats = metric && series ? historyStats(metric, series) : [];
  const currentMetricUi = metric ? METRIC_UI[metric.metric_code as RainGaugeMetricCode] : null;
  const points = series?.points.map((point) => ({
    timestamp: point.sampled_at,
    value: point.value,
    bucketMin: point.bucket_min,
    bucketMax: point.bucket_max,
    sampleCount: point.sample_count
  })) ?? [];

  return (
    <section className="space-y-5" aria-labelledby="rain-gauge-detail-title">
      <nav className="flex flex-wrap items-center gap-2 text-sm font-bold text-slate-500" aria-label="Migas de pan">
        <Link href={pluviometryQueryPath(snapshot.site.id)} className="rounded-md focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-emerald-600">Pluviometría</Link>
        <span aria-hidden="true">/</span>
        <span className="text-slate-800">{device.name}</span>
      </nav>

      <header className="panel p-5 sm:p-6">
        <div className="flex flex-col gap-5 lg:flex-row lg:items-start lg:justify-between">
          <div className="min-w-0">
            <p className="section-kicker">Detalle histórico</p>
            <h1 id="rain-gauge-detail-title" className="section-title mt-1 break-words">Pluviómetro {schema.device_name}</h1>
            <div className="mt-3 flex flex-wrap gap-x-5 gap-y-2 text-sm text-slate-600">
              <span><strong className="text-slate-800">Predio:</strong> {snapshot.site.name || "—"}</span>
              <span><strong className="text-slate-800">Parcela:</strong> {device.parcel_name || "—"}</span>
              <span className="inline-flex items-center gap-1.5 font-bold" style={{ color: status.color }}><span className="h-2.5 w-2.5 rounded-full bg-current" />{status.label}</span>
              <span><strong className="text-slate-800">Última comunicación:</strong> {formatSeen(device.last_seen_at, snapshot.site.timezone)}</span>
            </div>
          </div>
          <Link href={pluviometryQueryPath(snapshot.site.id)} className="btn-secondary shrink-0"><ArrowLeft className="mr-2" size={16} />Volver al mapa</Link>
        </div>
      </header>

      <div className="grid gap-4 lg:grid-cols-[minmax(0,1fr)_minmax(16rem,22rem)]">
        <div className="panel p-4">
          <p className="text-xs font-black uppercase tracking-[0.12em] text-slate-500">Pluviómetro</p>
          <label className="mt-2 block">
            <span className="sr-only">Cambiar pluviómetro</span>
            <select className="input" value={device.id} onChange={(event) => onDeviceChange(Number(event.target.value))} aria-label="Cambiar pluviómetro">
              {snapshot.devices.map((item) => <option key={item.id} value={item.id}>{item.name} · {item.parcel_name}</option>)}
            </select>
          </label>
        </div>
        <div className="panel p-4">
          <p className="text-xs font-black uppercase tracking-[0.12em] text-slate-500">Periodo</p>
          <div className="mt-2 flex max-w-full gap-1 overflow-x-auto rounded-lg bg-slate-50 p-1" role="group" aria-label="Periodo histórico">
            {PERIODS.map((item) => <button key={item.value} type="button" aria-pressed={period === item.value} onClick={() => onPeriodChange(item.value)} className={`shrink-0 rounded-md px-3 py-2 text-xs font-bold focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-emerald-600 ${period === item.value ? "bg-white text-emerald-800 shadow-sm" : "text-slate-500"}`}>{item.value}</button>)}
          </div>
        </div>
      </div>

      {metrics.length ? (
        <div className="panel p-4">
          <p className="text-xs font-black uppercase tracking-[0.12em] text-slate-500">Variable</p>
          <div className="mt-2 flex max-w-full gap-2 overflow-x-auto pb-1" role="group" aria-label="Variable meteorológica">
            {metrics.map((item) => {
              const ui = METRIC_UI[item.metric_code as RainGaugeMetricCode];
              return <button key={`${item.channel_key}:${item.metric_code}`} type="button" aria-pressed={metric?.metric_code === item.metric_code} onClick={() => onMetricChange(item)} className={`shrink-0 rounded-lg border px-3 py-2 text-xs font-bold focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-emerald-600 ${metric?.metric_code === item.metric_code ? "border-emerald-700 bg-emerald-50 text-emerald-900" : "border-slate-200 bg-white text-slate-600"}`}>{ui.label}</button>;
            })}
          </div>
        </div>
      ) : <EmptyState title="Sin métricas disponibles" message="Este pluviómetro no tiene variables históricas habilitadas para tu usuario." />}

      {seriesLoading ? <LoadingState label={`Cargando ${currentMetricUi?.label.toLowerCase() ?? "serie histórica"}`} /> : null}
      {!seriesLoading && error ? <ErrorState message={error} onRetry={onRetry} /> : null}
      {!seriesLoading && !error && metric && series ? (
        <>
          {metric.metric_code === "WIND_DIRECTION_DEG" ? <WindDirectionSummary series={series} decimals={metric.default_decimals} /> : null}
          <div className="grid gap-3 sm:grid-cols-3" aria-label={`Resumen de ${currentMetricUi?.label ?? metric.display_name}`}>
            {stats.map((stat) => <div key={stat.label} className="rounded-xl border border-slate-200 bg-white px-4 py-3 shadow-soft"><p className="text-[10px] font-black uppercase tracking-wide text-slate-500">{stat.label}</p><p className="mt-1 text-xl font-black text-slate-950">{stat.value}</p></div>)}
          </div>
          {metric.metric_code === "RAIN_DELTA_MM" && series.points.length > 0 && hasRecordedZero(series) && series.points.every((point) => point.value === 0) ? (
            <p className="rounded-xl border border-sky-200 bg-sky-50 px-4 py-3 text-sm font-semibold text-sky-800">No hubo lluvia registrada durante este periodo; sí existen lecturas reales en cero.</p>
          ) : null}
          <p className="sr-only">{textualSummary(currentMetricUi?.label ?? metric.display_name, stats, series.gaps.length)}</p>
          {metric.metric_code === "RAIN_DELTA_MM" ? (
            <AgroRainChart points={points} gaps={series.gaps} decimals={metric.default_decimals} periodLabel={periodLabel(period)} resolutionLabel={series.resolution} timeZone={snapshot.site.timezone} />
          ) : (
            <AgroTrendChart title={currentMetricUi?.label ?? metric.display_name} eyebrow="Histórico del pluviómetro" description={metric.description} points={points} summary={series.summary} gaps={series.gaps} unit={displayUnit(metric.canonical_unit)} decimals={metric.default_decimals} color={currentMetricUi?.color} periodLabel={periodLabel(period)} resolutionLabel={series.resolution} percentage={metric.canonical_unit === "percent"} variant="primary" hideStats timeZone={snapshot.site.timezone} />
          )}
        </>
      ) : null}
    </section>
  );
}

function detailError(reason: unknown) {
  if (reason instanceof ApiError && reason.status === 403) return "No tienes autorización para consultar este pluviómetro.";
  if (reason instanceof ApiError && reason.status === 404) return "El pluviómetro o la métrica solicitada no están disponibles.";
  return reason instanceof Error ? reason.message : "No se pudo cargar el histórico del pluviómetro.";
}

function formatSeen(value: string | null, timeZone: string) {
  return value ? formatDateTimeInTimeZone(value, timeZone) : "—";
}

function textualSummary(label: string, stats: Array<{ label: string; value: string }>, gaps: number) {
  return `${label}. ${stats.map((item) => `${item.label}: ${item.value}`).join(". ")}. ${gaps ? `${gaps} huecos de telemetría identificados.` : "Sin huecos de telemetría identificados."}`;
}
