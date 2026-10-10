import type { CanonicalMetricSeries } from "@/lib/types";
import type { AgroChartInputPoint } from "@/components/charts";

export function toEmcChartPoints(series: CanonicalMetricSeries): AgroChartInputPoint[] {
  return series.points.map((point) => ({
    timestamp: point.sampled_at,
    value: point.value,
    bucketMin: point.bucket_min,
    bucketMax: point.bucket_max,
    sampleCount: point.sample_count,
    emcRawWb: point.emc_raw_wb,
    grainTemperatureC: point.grain_temperature_c,
    intergranularTemperatureC: point.intergranular_temperature_c,
    intergranularHumidityPct: point.intergranular_humidity_pct,
    calibrationOffsetPp: point.calibration_offset_pp
  }));
}

export function formatEmcSummary(value: number | null | undefined) {
  return value == null ? "Pendiente" : `${value.toFixed(1)}% wb`;
}
