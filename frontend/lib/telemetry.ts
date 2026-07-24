import type { Device, Reading, StorageUnit } from "./types";

export type ReadingMetric =
  | "grain_temperature"
  | "ambient_temperature"
  | "ambient_humidity"
  | "battery_voltage"
  | "level_distance_cm"
  | "level_percent"
  | "soil_moisture_percent"
  | "soil_temperature_c";

export function deviceProfile(device: Device | undefined): "silo_sensor" | "field_sensor" {
  return device?.device_type?.toLowerCase() === "field_sensor" ? "field_sensor" : "silo_sensor";
}

export function storageOperation(unit: StorageUnit): "storage" | "field" {
  const legacyType = unit.unit_type?.toLowerCase();
  return unit.operation_type === "field" || ["field", "campo", "parcela", "lote"].includes(legacyType) ? "field" : "storage";
}

export function periodStart(period: "24h" | "7d" | "30d"): string {
  const hours = period === "24h" ? 24 : period === "7d" ? 24 * 7 : 24 * 30;
  return new Date(Date.now() - hours * 60 * 60 * 1000).toISOString();
}

export function readingsForDevice(readings: Reading[], deviceId: number): Reading[] {
  return readings
    .filter((reading) => reading.device_id === deviceId)
    .sort((a, b) => new Date(b.timestamp).getTime() - new Date(a.timestamp).getTime());
}

export function replaceNodeReadings(nextReadings: Reading[]): Reading[] {
  return [...nextReadings];
}

export function nodeSelectionPath(currentHref: string, deviceId: number): string {
  const url = new URL(currentHref);
  url.searchParams.set("node", String(deviceId));
  return `${url.pathname}${url.search}${url.hash}`;
}

export function storageUnitSelectionPath(currentHref: string, storageUnitId: number): string {
  const url = new URL(currentHref);
  url.searchParams.set("unit", String(storageUnitId));
  url.searchParams.delete("node");
  return `${url.pathname}${url.search}${url.hash}`;
}

export function canViewDeviceDiagnostics(role: string): boolean {
  return role === "admin" || role === "technician";
}

export function chartSeries(readings: Reading[], metric: ReadingMetric) {
  const points = readings
    .filter((reading) => reading[metric] !== null)
    .slice()
    .sort((a, b) => new Date(a.timestamp).getTime() - new Date(b.timestamp).getTime());
  const intervals = points
    .slice(1)
    .map((point, index) => new Date(point.timestamp).getTime() - new Date(points[index].timestamp).getTime())
    .filter((interval) => interval > 0)
    .sort((a, b) => a - b);
  // Use the lower median so one long outage cannot redefine the expected cadence.
  const median = intervals.length ? intervals[Math.floor((intervals.length - 1) / 2)] : 0;
  const gapThreshold = Math.max(median * 3, 15 * 60 * 1000);
  const series: Array<{ timestamp: string; time: string; value: number | null }> = [];

  points.forEach((point, index) => {
    if (index > 0) {
      const previous = points[index - 1];
      const gap = new Date(point.timestamp).getTime() - new Date(previous.timestamp).getTime();
      if (gap > gapThreshold) {
        series.push({
          timestamp: new Date(new Date(previous.timestamp).getTime() + 1).toISOString(),
          time: "Sin datos",
          value: null
        });
      }
    }
    series.push({
      timestamp: point.timestamp,
      time: new Intl.DateTimeFormat("es-BO", { day: "2-digit", hour: "2-digit", minute: "2-digit" }).format(new Date(point.timestamp)),
      value: point[metric]
    });
  });
  return series;
}
