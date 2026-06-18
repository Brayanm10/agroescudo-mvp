import type {
  Alert,
  AiAlertRecommendation,
  AppData,
  Company,
  Device,
  DemoSimulation,
  NotificationDelivery,
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

const LOCAL_API_URL = "http://127.0.0.1:8010";

function normalizeApiUrl(value: string) {
  return value.replace(/\/+$/, "");
}

function apiUrlFor(path: string) {
  const configuredUrl = process.env.NEXT_PUBLIC_API_URL?.trim();

  if (configuredUrl) {
    return normalizeApiUrl(configuredUrl);
  }

  if (process.env.NODE_ENV === "production") {
    throw new ApiError(
      [
        "NEXT_PUBLIC_API_URL no configurada. Define la URL pública del backend en Vercel.",
        "URL de API usada: no configurada",
        `Endpoint probado: ${path}`,
        "Código HTTP: no disponible",
        "Mensaje técnico: variable de entorno pública ausente en build de producción.",
        "Posibles causas: backend dormido por Render Free, API caída, NEXT_PUBLIC_API_URL incorrecta, CORS o error de internet."
      ].join("\n"),
      0
    );
  }

  return LOCAL_API_URL;
}

type RequestOptions = {
  token?: string;
  method?: string;
  body?: unknown;
};

export class ApiError extends Error {
  status: number;
  endpoint?: string;
  apiUrl?: string;

  constructor(message: string, status: number, endpoint?: string, apiUrl?: string) {
    super(message);
    this.status = status;
    this.endpoint = endpoint;
    this.apiUrl = apiUrl;
  }
}

async function request<T>(path: string, options: RequestOptions = {}): Promise<T> {
  const apiUrl = apiUrlFor(path);
  const headers: HeadersInit = {
    "Content-Type": "application/json"
  };
  if (options.token) {
    headers.Authorization = `Bearer ${options.token}`;
  }

  let response: Response;
  try {
    response = await fetch(`${apiUrl}${path}`, {
      method: options.method || "GET",
      headers,
      body: options.body ? JSON.stringify(options.body) : undefined
    });
  } catch (err) {
    throw new ApiError(connectionMessage(apiUrl, path, err), 0, path, apiUrl);
  }

  if (!response.ok) {
    let message = "No se pudo conectar con AgroEscudo API.";
    try {
      const payload = await response.json();
      message = payload.detail || message;
    } catch {
      message = response.statusText || message;
    }
    throw new ApiError(httpMessage(apiUrl, path, response.status, message), response.status, path, apiUrl);
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
    me.role === "admin" ? request<User[]>("/api/admin/users", { token }) : Promise.resolve([])
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
  const path = `/api/reports/weekly/pdf?storage_unit_id=${storageUnitId}`;
  const apiUrl = apiUrlFor(path);
  let response: Response;
  try {
    response = await fetch(`${apiUrl}${path}`, {
      headers: { Authorization: `Bearer ${token}` }
    });
  } catch (err) {
    throw new ApiError(connectionMessage(apiUrl, path, err), 0, path, apiUrl);
  }
  if (!response.ok) {
    let message = "No se pudo generar el reporte PDF.";
    try {
      const payload = await response.json();
      message = payload.detail || message;
    } catch {
      message = response.statusText || message;
    }
    throw new ApiError(httpMessage(apiUrl, path, response.status, message), response.status, path, apiUrl);
  }
  return response.blob();
}

function connectionMessage(apiUrl: string, path: string, err: unknown) {
  const technicalMessage = err instanceof Error ? err.message : String(err);
  return [
    "No se pudo conectar con AgroEscudo API.",
    `URL de API usada: ${apiUrl}`,
    `Endpoint probado: ${path}`,
    "Código HTTP: no disponible",
    `Mensaje técnico: ${technicalMessage || "error de red del navegador"}`,
    "Posibles causas: backend dormido por Render Free, API caída, NEXT_PUBLIC_API_URL incorrecta, CORS o error de internet."
  ].join("\n");
}

function httpMessage(apiUrl: string, path: string, status: number, detail: string) {
  return [
    "No se pudo completar la solicitud a AgroEscudo API.",
    `URL de API usada: ${apiUrl}`,
    `Endpoint probado: ${path}`,
    `Código HTTP: ${status}`,
    `Mensaje técnico: ${detail}`,
    "Posibles causas: backend dormido por Render Free, API caída, NEXT_PUBLIC_API_URL incorrecta, CORS o error de internet."
  ].join("\n");
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

export function createAdminUser(
  token: string,
  payload: {
    company_id: number;
    email: string;
    full_name: string;
    password: string;
    role: "admin" | "technician" | "client";
  }
) {
  return request<User>("/api/admin/users", { token, method: "POST", body: payload });
}

export function updateAdminUser(
  token: string,
  userId: number,
  payload: Partial<Pick<User, "company_id" | "email" | "full_name" | "role" | "is_active">>
) {
  return request<User>(`/api/admin/users/${userId}`, { token, method: "PATCH", body: payload });
}

export function resetAdminUserPassword(token: string, userId: number, password: string) {
  return request<User>(`/api/admin/users/${userId}/reset-password`, {
    token,
    method: "POST",
    body: { password }
  });
}

export function activateAdminUser(token: string, userId: number) {
  return request<User>(`/api/admin/users/${userId}/activate`, { token, method: "POST" });
}

export function deactivateAdminUser(token: string, userId: number) {
  return request<User>(`/api/admin/users/${userId}/deactivate`, { token, method: "POST" });
}

export function assignAdminUserStorageUnits(token: string, userId: number, storageUnitIds: number[]) {
  return request<User>(`/api/admin/users/${userId}/assign-storage-units`, {
    token,
    method: "POST",
    body: { storage_unit_ids: storageUnitIds }
  });
}

export function getNotificationDeliveries(token: string) {
  return request<NotificationDelivery[]>("/api/admin/notifications/deliveries", { token });
}

export function testAdminNotification(
  token: string,
  channel: "whatsapp" | "telegram",
  payload: { user_id?: number | null; destination?: string | null; message: string }
) {
  return request<NotificationDelivery>(`/api/admin/notifications/test/${channel}`, {
    token,
    method: "POST",
    body: payload
  });
}
