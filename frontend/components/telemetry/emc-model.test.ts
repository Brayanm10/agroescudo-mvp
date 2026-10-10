import { describe, expect, it } from "vitest";
import type { CanonicalMetricSeries } from "@/lib/types";
import { formatEmcSummary, toEmcChartPoints } from "./emc-model";

const series: CanonicalMetricSeries = {
  device_id: 16,
  channel_key: "emc_derived",
  metric_code: "GRAIN_MOISTURE_EMC_PCT",
  resolution: "raw",
  reconciliation_approved: false,
  period: { from: null, to: null },
  summary: { current: 13, initial: 12, minimum: 12, maximum: 13, average: 12.5, change: 1, sample_count: 2, point_count: 2, coverage_seconds: 60 },
  gaps: [],
  points: [{
    id: null, telemetry_event_id: null, device_id: 16, channel_key: "emc_derived", metric_code: "GRAIN_MOISTURE_EMC_PCT",
    raw_value: 11.8, calibrated_value: 13, value: 13, unit: "percent_wb", quality_status: "DERIVED_CALIBRATED",
    calibration_version: null, sampled_at: "2026-10-10T12:00:00Z", source: "derived", ultrasonic_distance_mm: null,
    product_height_mm: null, emc_raw_wb: 11.8, grain_temperature_c: 18.6, intergranular_temperature_c: 17.9,
    intergranular_humidity_pct: 51.4, calibration_offset_pp: 1.2, bucket_min: 13, bucket_max: 13, sample_count: 1
  }]
};

describe("EMC presentation model", () => {
  it("keeps calibrated and raw values plus environmental context in the chart point", () => {
    expect(toEmcChartPoints(series)[0]).toMatchObject({ value: 13, emcRawWb: 11.8, grainTemperatureC: 18.6, intergranularTemperatureC: 17.9, intergranularHumidityPct: 51.4, calibrationOffsetPp: 1.2 });
  });

  it("shows pending without valid derived data and formats wet-basis values", () => {
    expect(formatEmcSummary(null)).toBe("Pendiente");
    expect(formatEmcSummary(11.85)).toBe("11.8% wb");
  });
});
