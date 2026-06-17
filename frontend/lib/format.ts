import type { Alert, RiskStatus } from "./types";

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
    warning: "Warning",
    critical: "Critical",
    technical: "Tecnico"
  };
  return labels[status];
}
