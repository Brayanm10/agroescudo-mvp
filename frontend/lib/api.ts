import type {
  Alert,
  AiAlertRecommendation,
  AppData,
  Company,
  Device,
  DemoSimulation,
  NotificationEvent,
  NotificationPreference,
  OperationalLog,
  Pilot,
  Reading,
  Site,
  StorageUnit,
  Thresholds,
  User,
  WeeklyReport
} from "./types";

const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://127.0.0.1:8010";

type RequestOptions = {
  token?: string;
  method?: string;
  body?: unknown;
};

export class ApiError extends Error {
  status: number;

  constructor(message: string, status: number) {
    super(message);
    this.status = status;
  }
}

async function request<T>(path: string, options: RequestOptions = {}): Promise<T> {
  const headers: HeadersInit = {
    "Content-Type": "application/json"
  };
  if (options.token) {
    headers.Authorization = `Bearer ${options.token}`;
  }

  let response: Response;
  try {
    response = await fetch(`${API_URL}${path}`, {
      method: options.method || "GET",
      headers,
      body: options.body ? JSON.stringify(options.body) : undefined
    });
  } catch {
    throw new ApiError("No se pudo conectar con el servidor.", 0);
  }

  if (!response.ok) {
    let message = "No se pudo conectar con AgroEscudo API.";
    try {
      const payload = await response.json();
      message = payload.detail || message;
    } catch {
      message = response.statusText || message;
    }
    throw new ApiError(message, response.status);
  }

  return response.json() as Promise<T>;
}

export async function login(email: string, password: string) {
  return request<{ access_token: string; token_type: string }>("/api/auth/login", {
    method: "POST",
    body: { email, password }
  });
}

export async function loadAppData(token: string): Promise<AppData> {
  const me = await request<User>("/api/me", { token });
  const [companies, sites, storageUnits, devices, readings, alerts, activeAlerts, logs, pilots, users] = await Promise.all([
    request<Company[]>("/api/companies", { token }),
    request<Site[]>("/api/sites", { token }),
    request<StorageUnit[]>("/api/storage-units", { token }),
    request<Device[]>("/api/devices", { token }),
    request<Reading[]>("/api/readings?limit=100", { token }),
    request<Alert[]>("/api/alerts", { token }),
    request<Alert[]>("/api/alerts/active", { token }),
    request<OperationalLog[]>("/api/operational-logs", { token }),
    request<Pilot[]>("/api/pilots", { token }),
    me.role === "admin" ? request<User[]>("/api/users", { token }) : Promise.resolve([])
  ]);
  return {
    me,
    companies,
    sites,
    storageUnits,
    devices,
    readings,
    alerts,
    activeAlerts,
    logs,
    pilots,
    users
  };
}

export function getStorageUnitReadings(token: string, storageUnitId: number, limit = 100) {
  return request<Reading[]>(`/api/storage-units/${storageUnitId}/readings?limit=${limit}`, { token });
}

export function getStorageUnitLogs(token: string, storageUnitId: number) {
  return request<OperationalLog[]>(`/api/storage-units/${storageUnitId}/operational-logs`, { token });
}

export function acknowledgeAlert(token: string, alertId: number) {
  return request<Alert>(`/api/alerts/${alertId}/acknowledge`, { token, method: "PATCH" });
}

export function resolveAlert(token: string, alertId: number) {
  return request<Alert>(`/api/alerts/${alertId}/resolve`, { token, method: "PATCH" });
}

export function createOperationalLog(
  token: string,
  payload: {
    alert_id: number | null;
    storage_unit_id: number;
    device_id?: number | null;
    category?: "installation" | "maintenance" | "corrective_action" | "inspection" | "general";
    action_taken: string;
    operator_name: string;
    notes: string;
    timestamp: string;
  }
) {
  return request<OperationalLog>("/api/operational-logs", { token, method: "POST", body: payload });
}

export function createInstallationChecklist(
  token: string,
  payload: {
    storage_unit_id: number;
    device_id: number;
    physical_location: string;
    sensor_installed_correctly: boolean;
    connectivity_verified: boolean;
    initial_reading_registered: boolean;
    battery_verified: boolean;
    observations: string;
    technician_name: string;
    timestamp: string;
  }
) {
  return request<OperationalLog>("/api/operational-logs/installations", { token, method: "POST", body: payload });
}

export function createPilot(
  token: string,
  payload: {
    company_name: string;
    company_tax_id: string | null;
    site_name: string;
    site_location: string;
    storage_unit_name: string;
    storage_unit_type: string;
    capacity_tons: number | null;
    device_external_id: string;
    device_name: string;
    device_token: string;
    technician_user_id: number;
    client_email: string;
    client_full_name: string;
    client_password: string;
  }
) {
  return request<Pilot>("/api/pilots", { token, method: "POST", body: payload });
}

export function deletePilotOperationalData(token: string, storageUnitId: number) {
  return request<{
    storage_unit_id: number;
    readings_deleted: number;
    alerts_deleted: number;
    logs_deleted: number;
  }>(`/api/pilots/${storageUnitId}/operational-data`, { token, method: "DELETE" });
}

export function getThresholds(token: string, deviceId: number) {
  return request<Thresholds>(`/api/devices/${deviceId}/thresholds`, { token });
}

export function updateThresholds(token: string, deviceId: number, payload: Omit<Thresholds, "device_id">) {
  return request<Thresholds>(`/api/devices/${deviceId}/thresholds`, {
    token,
    method: "PUT",
    body: payload
  });
}

export function getWeeklyReport(token: string, storageUnitId: number) {
  return request<WeeklyReport>(`/api/reports/weekly?storage_unit_id=${storageUnitId}`, { token });
}

export async function getWeeklyReportPdf(token: string, storageUnitId: number) {
  let response: Response;
  try {
    response = await fetch(`${API_URL}/api/reports/weekly/pdf?storage_unit_id=${storageUnitId}`, {
      headers: { Authorization: `Bearer ${token}` }
    });
  } catch {
    throw new ApiError("No se pudo conectar con el servidor.", 0);
  }
  if (!response.ok) {
    throw new ApiError("No se pudo generar el reporte PDF.", response.status);
  }
  return response.blob();
}

export function simulateCriticalDemoReading(token: string) {
  return request<DemoSimulation>("/api/demo/simulate-critical-reading", { token, method: "POST" });
}

export function getNotificationPreferences(token: string) {
  return request<NotificationPreference[]>("/api/notifications/preferences", { token });
}

export function updateNotificationPreference(
  token: string,
  channel: "whatsapp" | "telegram" | "push",
  payload: {
    enabled: boolean;
    destination?: string | null;
    minimum_severity: "all" | "technical" | "warning" | "critical";
  }
) {
  return request<NotificationPreference>(`/api/notifications/preferences/${channel}`, {
    token,
    method: "PUT",
    body: payload
  });
}

export function getNotificationEvents(token: string) {
  return request<NotificationEvent[]>("/api/notifications/events", { token });
}

export function testNotification(token: string, channel: "whatsapp" | "telegram" | "push") {
  return request<{ channel: string; event: NotificationEvent }>(`/api/notifications/test/${channel}`, {
    token,
    method: "POST"
  });
}

export function getAiAlertRecommendation(token: string, alertId: number) {
  return request<AiAlertRecommendation>(`/api/ai/alerts/${alertId}/recommendation`, { token });
}
