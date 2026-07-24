import { describe, expect, it } from "vitest";
import {
  canViewDeviceDiagnostics,
  chartSeries,
  deviceProfile,
  nodeSelectionPath,
  periodStart,
  readingsForDevice,
  replaceNodeReadings,
  storageOperation,
  storageUnitSelectionPath
} from "./telemetry";
import type { Device, Reading } from "./types";

const baseReading: Reading = {
  id: 1,
  company_id: 1,
  site_id: 1,
  storage_unit_id: 1,
  device_id: 1,
  grain_temperature: 25,
  ambient_temperature: 22,
  ambient_humidity: 60,
  battery_voltage: 3.9,
  signal_quality: -67,
  level_distance_cm: null,
  level_percent: null,
  soil_moisture_percent: null,
  soil_temperature_c: null,
  sensor_status: null,
  timestamp: "2026-07-22T10:00:00Z",
  received_at: "2026-07-22T10:00:01Z",
  metrics: []
};

describe("telemetria por nodo", () => {
  it("separa las lecturas de dos nodos del mismo silo", () => {
    const readings = [baseReading, { ...baseReading, id: 2, device_id: 2, grain_temperature: 40 }];
    expect(readingsForDevice(readings, 1)).toHaveLength(1);
    expect(readingsForDevice(readings, 1)[0].grain_temperature).toBe(25);
  });

  it("inserta un corte cuando falta telemetria durante un intervalo prolongado", () => {
    const readings = [
      baseReading,
      { ...baseReading, id: 2, timestamp: "2026-07-22T10:05:00Z" },
      { ...baseReading, id: 3, timestamp: "2026-07-22T12:00:00Z" }
    ];
    expect(chartSeries(readings, "grain_temperature").some((point) => point.value === null)).toBe(true);
  });

  it("no inventa puntos para una metrica ausente", () => {
    expect(chartSeries([baseReading], "level_percent")).toEqual([]);
  });

  it("mantiene dispositivos legacy como SiloSensor", () => {
    const device = { device_type: "esp32_lora_wifi_node" } as Device;
    expect(deviceProfile(device)).toBe("silo_sensor");
    expect(deviceProfile({ ...device, device_type: "field_sensor" })).toBe("field_sensor");
  });

  it("reemplaza la serie al cambiar de nodo y conserva el nodo en la URL", () => {
    const oldNode = [baseReading];
    const nextNode = [{ ...baseReading, id: 2, device_id: 2 }];
    expect(replaceNodeReadings(nextNode)).toEqual(nextNode);
    expect(replaceNodeReadings(nextNode)).not.toContain(oldNode[0]);
    expect(nodeSelectionPath("https://app.agroescudo.com/?section=sites", 2)).toBe("/?section=sites&node=2");
    expect(storageUnitSelectionPath("https://app.agroescudo.com/?node=2", 9)).toBe("/?unit=9");
  });

  it("reserva RSSI y diagnostico para tecnico y admin", () => {
    expect(canViewDeviceDiagnostics("client")).toBe(false);
    expect(canViewDeviceDiagnostics("technician")).toBe(true);
    expect(canViewDeviceDiagnostics("admin")).toBe(true);
  });

  it("clasifica unidades de almacenamiento y campo sin romper tipos legacy", () => {
    expect(storageOperation({ operation_type: "field", unit_type: "parcela" } as never)).toBe("field");
    expect(storageOperation({ operation_type: "storage", unit_type: "silo" } as never)).toBe("storage");
    expect(storageOperation({ unit_type: "campo" } as never)).toBe("field");
  });

  it("calcula periodos de consulta en UTC", () => {
    const start = new Date(periodStart("24h")).getTime();
    const elapsedHours = (Date.now() - start) / (60 * 60 * 1000);
    expect(elapsedHours).toBeGreaterThan(23.9);
    expect(elapsedHours).toBeLessThan(24.1);
  });
});
