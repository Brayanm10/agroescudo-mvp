import { renderToStaticMarkup } from "react-dom/server";
import { afterEach, describe, expect, it, vi } from "vitest";
import { buildAgroChartData } from "@/components/charts";
import { getCanonicalMetricReadings } from "@/lib/api";
import type { CanonicalMetricSeries, DashboardMetric, DeviceDashboardSchema, PluviometryMapSnapshot } from "@/lib/types";
import {
  detailQueryPath,
  displayUnit,
  historyStats,
  periodRequest,
  resolveHistorySelection,
  supportedRainGaugeMetrics
} from "./detail-model";
import { RainGaugeHistoryContent } from "./RainGaugeHistoryView";
import {
  circularMeanDegrees,
  degreesToCompass,
  oppositeCompassDirection,
  windDirectionPresentation
} from "./wind-direction";

const metric = (metricCode: string, canonicalUnit: string, aggregationStrategy: DashboardMetric["aggregation_strategy"]): DashboardMetric => ({
  numeric_id: 1,
  metric_code: metricCode,
  display_name: metricCode,
  description: `Descripción ${metricCode}`,
  canonical_unit: canonicalUnit,
  physical_min: null,
  physical_max: null,
  default_decimals: metricCode === "AMBIENT_RELATIVE_HUMIDITY_PCT" ? 0 : 1,
  default_chart_type: metricCode === "RAIN_DELTA_MM" ? "bar" : "line",
  aggregation_strategy: aggregationStrategy,
  client_visibility: true,
  is_derived: false,
  calibration_method: null,
  alert_supported: true,
  display_order: 1,
  registry_version: 2,
  channel_id: 1,
  channel_key: `${metricCode.toLowerCase()}_1`,
  chart_enabled: true,
  client_visible: true,
  display_name_override: null,
  chart_type_override: null
});

const rainMetric = metric("RAIN_DELTA_MM", "mm", "sum");
const temperatureMetric = metric("AMBIENT_TEMPERATURE_C", "degC", "avg");
const humidityMetric = metric("AMBIENT_RELATIVE_HUMIDITY_PCT", "percent", "avg");
const windDirectionMetric = metric("WIND_DIRECTION_DEG", "degree", "circular_mean");
const metrics = [humidityMetric, windDirectionMetric, rainMetric, temperatureMetric];

const series = (metricCode = "RAIN_DELTA_MM", values: Array<number | null> = [1.2, 0, 2.3]): CanonicalMetricSeries => ({
  device_id: 71,
  channel_key: `${metricCode.toLowerCase()}_1`,
  metric_code: metricCode,
  resolution: "15m",
  reconciliation_approved: false,
  points: values.map((value, index) => ({
    id: index + 1,
    telemetry_event_id: index + 1,
    device_id: 71,
    channel_key: `${metricCode.toLowerCase()}_1`,
    metric_code: metricCode,
    raw_value: value,
    calibrated_value: null,
    value,
    unit: metricCode === "RAIN_DELTA_MM" ? "mm" : "degC",
    quality_status: "VALID",
    calibration_version: null,
    sampled_at: `2026-09-24T0${index + 4}:00:00Z`,
    source: "normalized",
    bucket_min: value,
    bucket_max: value,
    sample_count: 1
  })),
  period: { from: "2026-09-24T04:00:00Z", to: "2026-09-24T07:00:00Z" },
  summary: {
    current: values.at(-1) ?? null,
    initial: values[0] ?? null,
    minimum: 0,
    maximum: 2.3,
    average: 1.166,
    change: 1.1,
    sample_count: values.filter((value) => value !== null).length,
    point_count: values.length,
    coverage_seconds: 10800
  },
  gaps: [{ from: "2026-09-24T05:00:00Z", to: "2026-09-24T06:00:00Z", duration_seconds: 3600 }]
});

const schema: DeviceDashboardSchema = {
  registry_version: 2,
  capabilities_version: 1,
  device_id: 71,
  device_external_id: "PLUV-001",
  device_name: "P-01",
  device_profile: "rain_gauge",
  template_code: "RAIN_GAUGE_BASE",
  channels: [],
  metrics,
  thresholds: {}
};

const snapshot: PluviometryMapSnapshot = {
  site: { id: 12, name: "Predio Quillacollo", latitude: -17.39, longitude: -66.16, timezone: "America/La_Paz", boundary_geojson: null },
  parcels: [],
  devices: [
    { id: 71, device_id: "PLUV-001", name: "P-01", storage_unit_id: 48, parcel_name: "Parcela Norte", latitude: -17.39, longitude: -66.16, status: "online", last_seen_at: "2026-09-24T06:00:00Z", latest: { temperature_c: 23, humidity_pct: 70, wind_speed_kmh: null, wind_direction_deg: null, battery_pct: 90 }, rain_today_mm: 3.5 },
    { id: 72, device_id: "PLUV-002", name: "P-02", storage_unit_id: 49, parcel_name: "Parcela Sur", latitude: -17.4, longitude: -66.17, status: "delayed", last_seen_at: null, latest: { temperature_c: null, humidity_pct: null, wind_speed_kmh: null, wind_direction_deg: null, battery_pct: null }, rain_today_mm: null }
  ]
};

afterEach(() => vi.unstubAllGlobals());

describe("detalle histórico del pluviómetro", () => {
  it("prioriza solo métricas reales soportadas por el schema", () => {
    expect(supportedRainGaugeMetrics(metrics).map((item) => item.metric_code)).toEqual([
      "RAIN_DELTA_MM",
      "AMBIENT_TEMPERATURE_C",
      "AMBIENT_RELATIVE_HUMIDITY_PCT",
      "WIND_DIRECTION_DEG"
    ]);
  });

  it("resuelve variable y periodo desde query string", () => {
    const selection = resolveHistorySelection(metrics, "AMBIENT_TEMPERATURE_C", "7d");
    expect(selection.metric?.metric_code).toBe("AMBIENT_TEMPERATURE_C");
    expect(selection.period).toBe("7d");
  });

  it("corrige variable y periodo inválidos", () => {
    const selection = resolveHistorySelection(metrics, "FAKE", "forever");
    expect(selection.metric?.metric_code).toBe("RAIN_DELTA_MM");
    expect(selection.period).toBe("24h");
  });

  it("construye navegación real entre dispositivos preservando filtros", () => {
    expect(detailQueryPath(72, "RAIN_DELTA_MM", "30d")).toBe("/pluviometria/pluviometros/72?variable=RAIN_DELTA_MM&period=30d");
  });

  it("usa suma para lluvia y conserva lecturas reales en cero", () => {
    expect(historyStats(rainMetric, series())).toEqual([
      { label: "Acumulado", value: "3.5 mm" },
      { label: "Máx. intervalo", value: "2.3 mm" },
      { label: "Lecturas", value: "3" }
    ]);
  });

  it("usa mínimo promedio máximo para temperatura y humedad con unidades correctas", () => {
    expect(historyStats(temperatureMetric, series("AMBIENT_TEMPERATURE_C"))[1]).toEqual({ label: "Promedio", value: "1.2 °C" });
    expect(displayUnit(humidityMetric.canonical_unit)).toBe("%");
  });

  it("interpreta la dirección meteorológica como origen y destino opuesto", () => {
    expect(degreesToCompass(45)).toBe("NE");
    expect(oppositeCompassDirection("NE")).toBe("SO");
    expect(windDirectionPresentation(45)).toMatchObject({ from: "NE", to: "SO", arrowRotation: 225 });
  });

  it("calcula el cruce 359°/1° como Norte mediante media circular", () => {
    const crossing = series("WIND_DIRECTION_DEG", [359, 1, 5]);
    const predominant = circularMeanDegrees(crossing.points);
    expect(predominant).not.toBeNull();
    expect(predominant!).toBeLessThan(5);
    expect(degreesToCompass(predominant!)).toBe("N");
    expect(historyStats(windDirectionMetric, crossing)[0].value).toContain("N ·");
  });

  it("muestra origen, destino y flecha sin depender del color", () => {
    const windSeries = series("WIND_DIRECTION_DEG", [42, 45, 48]);
    windSeries.summary.current = 45;
    const markup = renderToStaticMarkup(
      <RainGaugeHistoryContent schema={schema} snapshot={snapshot} device={snapshot.devices[0]} metrics={[windDirectionMetric]} metric={windDirectionMetric} period="24h" series={windSeries} seriesLoading={false} error={null} onMetricChange={() => undefined} onPeriodChange={() => undefined} onDeviceChange={() => undefined} onRetry={() => undefined} />
    );
    expect(markup).toContain("Viene de");
    expect(markup).toContain("hacia");
    expect(markup).toContain("NE");
    expect(markup).toContain("SO");
    expect(markup).toContain("rotate(225deg)");
    expect(markup).toContain("media circular");
  });

  it("no inventa cero cuando faltan todos los valores", () => {
    const missing = series("RAIN_DELTA_MM", [null, null]);
    missing.summary = { ...missing.summary, current: null, minimum: null, maximum: null, average: null, sample_count: 0 };
    expect(historyStats(rainMetric, missing)[0].value).toBe("—");
  });

  it("convierte periodos en rangos y resoluciones coherentes", () => {
    const request = periodRequest("30d", Date.parse("2026-09-24T12:00:00Z"));
    expect(request.resolution).toBe("1d");
    expect(request.to).toBe("2026-09-24T12:00:00.000Z");
  });

  it("mantiene huecos como puntos nulos en la serie visual", () => {
    const rain = series();
    const data = buildAgroChartData(rain.points.map((point) => ({ timestamp: point.sampled_at, value: point.value })), rain.gaps, [], []);
    expect(data.some((point) => point.gap && point.value === null)).toBe(true);
  });

  it("renderiza encabezado, selector autorizado y resumen", () => {
    const markup = renderToStaticMarkup(
      <RainGaugeHistoryContent schema={schema} snapshot={snapshot} device={snapshot.devices[0]} metrics={supportedRainGaugeMetrics(metrics)} metric={rainMetric} period="24h" series={series()} seriesLoading={false} error={null} onMetricChange={() => undefined} onPeriodChange={() => undefined} onDeviceChange={() => undefined} onRetry={() => undefined} />
    );
    expect(markup).toContain("Pluviómetro P-01");
    expect(markup).toContain("Predio Quillacollo");
    expect(markup).toContain("P-02 · Parcela Sur");
    expect(markup).toContain("Acumulado");
    expect(markup).toContain("3.5 mm");
  });

  it("renderiza loading y error de API sin mostrar datos obsoletos", () => {
    const loading = renderToStaticMarkup(<RainGaugeHistoryContent schema={schema} snapshot={snapshot} device={snapshot.devices[0]} metrics={supportedRainGaugeMetrics(metrics)} metric={rainMetric} period="24h" series={null} seriesLoading error={null} onMetricChange={() => undefined} onPeriodChange={() => undefined} onDeviceChange={() => undefined} onRetry={() => undefined} />);
    const error = renderToStaticMarkup(<RainGaugeHistoryContent schema={schema} snapshot={snapshot} device={snapshot.devices[0]} metrics={supportedRainGaugeMetrics(metrics)} metric={rainMetric} period="24h" series={null} seriesLoading={false} error="API no disponible" onMetricChange={() => undefined} onPeriodChange={() => undefined} onDeviceChange={() => undefined} onRetry={() => undefined} />);
    expect(loading).toContain("Cargando lluvia");
    expect(error).toContain("API no disponible");
  });

  it("propaga AbortSignal y cancela la solicitud anterior", async () => {
    const controller = new AbortController();
    const fetchMock = vi.fn((_url: string, init: RequestInit) => new Promise<Response>((_resolve, reject) => {
      init.signal?.addEventListener("abort", () => reject(new DOMException("Aborted", "AbortError")));
    }));
    vi.stubGlobal("fetch", fetchMock);
    const pending = getCanonicalMetricReadings("token", 71, "RAIN_DELTA_MM", { channelKey: "rain_1", signal: controller.signal });
    controller.abort();
    await expect(pending).rejects.toMatchObject({ name: "AbortError" });
    expect(fetchMock).toHaveBeenCalledOnce();
  });
});
