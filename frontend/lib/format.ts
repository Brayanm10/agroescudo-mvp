import type { Alert, RiskStatus } from "./types";

export const DEFAULT_OPERATIONAL_TIME_ZONE = "America/La_Paz";

export type TimestampValue = string | number | Date;

export function parseUtcTimestamp(value: TimestampValue) {
  if (value instanceof Date) return new Date(value.getTime());
  if (typeof value === "number") return new Date(value);
  const normalized = value.trim();
  const hasExplicitTimeZone = /(?:Z|[+-]\d{2}(?::?\d{2})?)$/i.test(normalized);
  return new Date(hasExplicitTimeZone ? normalized : `${normalized}Z`);
}

export function formatDateTimeInTimeZone(
  value: TimestampValue,
  timeZone = DEFAULT_OPERATIONAL_TIME_ZONE,
  options: Intl.DateTimeFormatOptions = { dateStyle: "medium", timeStyle: "short" }
) {
  return new Intl.DateTimeFormat("es-BO", { ...options, timeZone }).format(parseUtcTimestamp(value));
}

export function formatChartTimeInTimeZone(
  value: TimestampValue,
  timeZone = DEFAULT_OPERATIONAL_TIME_ZONE,
  options: Intl.DateTimeFormatOptions = { hour: "2-digit", minute: "2-digit", hourCycle: "h23" }
) {
  return new Intl.DateTimeFormat("es-BO", { ...options, timeZone }).format(parseUtcTimestamp(value));
}

export function formatDateTime(value?: string | null) {
  if (!value) return "Sin registro";
  return new Intl.DateTimeFormat("es-BO", {
    dateStyle: "medium",
    timeStyle: "short"
  }).format(new Date(value));
}

export function formatNumber(value: number | null | undefined, suffix = "", digits = 1) {
  if (value === null || value === undefined || Number.isNaN(value)) return "Sin dato";
  return `${value.toFixed(digits)}${suffix}`;
}

export function statusFromAlerts(alerts: Alert[]): RiskStatus {
  if (alerts.some((alert) => alert.severity === "critical")) return "critical";
  if (alerts.some((alert) => alert.severity === "warning")) return "warning";
  if (alerts.some((alert) => alert.severity === "technical")) return "technical";
  return "normal";
}

export function statusLabel(status: RiskStatus) {
  const labels: Record<RiskStatus, string> = {
    normal: "Normal",
    warning: "Precaucion",
    critical: "Critico",
    technical: "Tecnico",
    no_data: "Sin datos",
    offline: "Sin datos"
  };
  return labels[status];
}
