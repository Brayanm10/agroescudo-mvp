import { describe, expect, it } from "vitest";
import { buildAgroChartData, conditionFor, summarizePoints } from "./chart-model";

describe("modelo visual AgroEscudo", () => {
  it("mantiene extremos y resumen sin alterar los puntos originales", () => {
    const points = [
      { timestamp: "2026-08-01T10:00:00Z", value: 25, bucketMin: 24, bucketMax: 31, sampleCount: 4 },
      { timestamp: "2026-08-01T11:00:00Z", value: 27, bucketMin: 26, bucketMax: 29, sampleCount: 4 }
    ];
    expect(summarizePoints(points).change).toBe(2);
    const data = buildAgroChartData(points, [], [], []);
    expect(data[0].bucketMax).toBe(31);
    expect(data[0].sampleCount).toBe(4);
  });

  it("crea una discontinuidad explícita para cada hueco del backend", () => {
    const data = buildAgroChartData(
      [
        { timestamp: "2026-08-01T10:00:00Z", value: 25 },
        { timestamp: "2026-08-01T18:00:00Z", value: 26 }
      ],
      [{ from: "2026-08-01T10:00:00Z", to: "2026-08-01T18:00:00Z", duration_seconds: 28800 }],
      [],
      []
    );
    expect(data.filter((point) => point.gap && point.value === null)).toHaveLength(2);
  });

  it("asocia eventos y acciones al punto real más cercano", () => {
    const data = buildAgroChartData(
      [
        { timestamp: "2026-08-01T10:00:00Z", value: 25 },
        { timestamp: "2026-08-01T11:00:00Z", value: 35 }
      ],
      [],
      [{ id: 1, timestamp: "2026-08-01T10:58:00Z", event_type: "temperature_high", severity: "critical", title: "Temperatura alta", metric_code: "GRAIN_TEMPERATURE_C", observed_value: 35, threshold_value: 32, status: "active" }],
      [{ id: 2, timestamp: "2026-08-01T11:04:00Z", category: "corrective_action", title: "Aireación", result: null, operator_name: "Técnico", alert_id: 1 }]
    );
    expect(data[1].events[0].title).toBe("Temperatura alta");
    expect(data[1].actions[0].title).toBe("Aireación");
  });

  it("acompaña el color con una condición textual", () => {
    expect(conditionFor(25, { max: 28, criticalMax: 32 }).label).toBe("Normal");
    expect(conditionFor(29, { max: 28, criticalMax: 32 }).label).toBe("Atención");
    expect(conditionFor(35, { max: 28, criticalMax: 32 }).label).toBe("Crítico");
  });
});
