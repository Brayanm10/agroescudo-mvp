import type {
  Alert,
  AiAlertRecommendation,
  AppData,
  Company,
  ControlCenterSummary,
  Device,
  DeviceWithApiKey,
  DemoSimulation,
  InsightsResponse,
  NotificationDelivery,
  NotificationEvent,
  NotificationPreference,
  OperationalLog,
  Pilot,
  Reading,
  Site,
  StorageUnitInsight,
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
      message = formatApiDetail(payload.detail) || message;
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

export function signupCompany(payload: {
  responsible_name: string;
  work_email: string;
  phone?: string | null;
  commercial_name: string;
  legal_name?: string | null;
  tax_id?: string | null;
  sector?: string | null;
  city?: string | null;
  department?: string | null;
  estimated_sites?: number | null;
  estimated_storage_units?: number | null;
  use_case?: string | null;
  password: string;
  language?: string;
  consent_terms: boolean;
  consent_privacy: boolean;
  consent_marketing?: boolean;
}) {
  return request<{
    request_id: number;
    company_id: number;
    user_id: number;
    status: string;
    email_required: boolean;
    verification_preview_token: string | null;
    message: string;
  }>("/api/auth/signup/company", { method: "POST", body: payload });
}

export function requestDemo(payload: {
  name: string;
  company_name: string;
  position?: string | null;
  email: string;
  phone?: string | null;
  city?: string | null;
  interest?: string | null;
  consent: boolean;
}) {
  return request<{ message: string; status: string }>("/api/auth/demo-request", { method: "POST", body: payload });
}

export function previewInvite(token: string) {
  return request<{ email: string; role: string; company_name: string; expires_at: string; status: string }>("/api/auth/invites/preview", {
    method: "POST",
    body: { token }
  });
}

export function acceptInvite(payload: { token: string; full_name: string; password: string }) {
  return request<{ access_token: string; token_type: string }>("/api/auth/invites/accept", {
    method: "POST",
    body: payload
  });
}

export function verifyEmail(token: string) {
  return request<{ message: string; status: string }>("/api/auth/email/verify", { method: "POST", body: { token } });
}

export function forgotPassword(email: string) {
  return request<{ message: string; reset_preview_token: string | null }>("/api/auth/password/forgot", {
    method: "POST",
    body: { email }
  });
}

export function resetPassword(payload: { token: string; password: string }) {
  return request<{ message: string; status: string }>("/api/auth/password/reset", { method: "POST", body: payload });
}

export function logout(token: string) {
  return request<{ message: string; status: string }>("/api/auth/logout", { token, method: "POST" });
}

export async function loadAppData(token: string): Promise<AppData> {
  const me = await request<User>("/api/me", { token });
  const [companies, sites, storageUnits, devices, readings, alerts, activeAlerts, logs, pilots, users, insights, controlCenter] = await Promise.all([
    request<Company[]>("/api/companies", { token }),
    request<Site[]>("/api/sites", { token }),
    request<StorageUnit[]>("/api/storage-units", { token }),
    request<Device[]>("/api/devices", { token }),
    request<Reading[]>("/api/readings?limit=100", { token }),
    request<Alert[]>("/api/alerts", { token }),
    request<Alert[]>("/api/alerts/active", { token }),
    request<OperationalLog[]>("/api/operational-logs", { token }),
    request<Pilot[]>("/api/pilots", { token }),
    me.role === "admin" ? request<User[]>("/api/admin/users", { token }) : Promise.resolve([]),
    request<InsightsResponse>("/api/insights?period=24h", { token }).then((payload) => payload.insights).catch(() => []),
    request<ControlCenterSummary>("/api/control-center/summary", { token }).catch(() => null)
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
    users,
    insights,
    controlCenter
  };
}

export function getControlCenterSummary(token: string) {
  return request<ControlCenterSummary>("/api/control-center/summary", { token });
}

export function getStorageUnitReadings(
  token: string,
  storageUnitId: number,
  options: { limit?: number; from?: string; to?: string; deviceId?: number } = {}
) {
  const params = new URLSearchParams();
  params.set("limit", String(options.limit ?? 100));
  if (options.from) params.set("from", options.from);
  if (options.to) params.set("to", options.to);
  if (options.deviceId) params.set("device_id", String(options.deviceId));
  return request<Reading[]>(`/api/storage-units/${storageUnitId}/readings?${params.toString()}`, { token });
}

export function updateMe(
  token: string,
  payload: {
    full_name?: string;
    phone_whatsapp?: string | null;
    telegram_chat_id?: string | null;
    receives_alerts?: boolean;
    language?: string;
    timezone?: string;
  }
) {
  return request<User>("/api/me", { token, method: "PATCH", body: payload });
}

export function changePassword(
  token: string,
  payload: {
    current_password: string;
    new_password: string;
    confirm_password: string;
  }
) {
  return request<{ status: string }>("/api/auth/change-password", { token, method: "POST", body: payload });
}

export function getInsights(token: string, period: "24h" | "7d" | "30d" = "24h") {
  return request<InsightsResponse>(`/api/insights?period=${period}`, { token });
}

export function getStorageUnitInsights(token: string, storageUnitId: number, period: "24h" | "7d" | "30d" = "24h") {
  return request<StorageUnitInsight>(`/api/storage-units/${storageUnitId}/insights?period=${period}`, { token });
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
      message = formatApiDetail(payload.detail) || message;
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
  if (status === 400 || status === 422) {
    return [
      "No se pudo guardar porque hay informacion incompleta o invalida.",
      `Endpoint probado: ${path}`,
      `Codigo HTTP: ${status}`,
      `Detalle: ${detail}`,
      "Revisa los campos marcados y vuelve a intentar."
    ].join("\n");
  }

  return [
    "No se pudo completar la solicitud a AgroEscudo API.",
    `URL de API usada: ${apiUrl}`,
    `Endpoint probado: ${path}`,
    `Código HTTP: ${status}`,
    `Mensaje técnico: ${detail}`,
    "Posibles causas: backend dormido por Render Free, API caída, NEXT_PUBLIC_API_URL incorrecta, CORS o error de internet."
  ].join("\n");
}

function formatApiDetail(detail: unknown): string | null {
  if (!detail) return null;
  if (typeof detail === "string") return detail;
  if (Array.isArray(detail)) {
    return detail
      .map((item) => {
        if (typeof item === "string") return item;
        if (item && typeof item === "object") {
          const record = item as { msg?: unknown; loc?: unknown };
          const location = Array.isArray(record.loc)
            ? record.loc.filter((part) => part !== "body").join(".")
            : "";
          const message = typeof record.msg === "string" ? record.msg : JSON.stringify(item);
          return location ? `${location}: ${message}` : message;
        }
        return String(item);
      })
      .join("\n");
  }
  if (typeof detail === "object") {
    try {
      return JSON.stringify(detail);
    } catch {
      return "Error de validacion en la solicitud.";
    }
  }
  return String(detail);
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

export function askAgroAssistant(token: string, message: string, storageUnitId?: number | null) {
  return request<{
    source: string;
    answer: string;
    facts: string[];
    interpretation: string;
    recommended_actions: string[];
    conversation_id: number;
  }>("/api/agro-assistant/messages", {
    token,
    method: "POST",
    body: { message, storage_unit_id: storageUnitId ?? null }
  });
}

export function createAdminCompany(
  token: string,
  payload: {
    name: string;
    tax_id?: string | null;
    type: string;
    city?: string | null;
    contact_name?: string | null;
    contact_email?: string | null;
    contact_phone?: string | null;
  }
) {
  return request<Company>("/api/admin/companies", { token, method: "POST", body: payload });
}

export function updateAdminCompany(token: string, companyId: number, payload: Partial<Company>) {
  return request<Company>(`/api/admin/companies/${companyId}`, { token, method: "PATCH", body: payload });
}

export function activateAdminCompany(token: string, companyId: number) {
  return request<Company>(`/api/admin/companies/${companyId}/activate`, { token, method: "POST" });
}

export function deactivateAdminCompany(token: string, companyId: number) {
  return request<Company>(`/api/admin/companies/${companyId}/deactivate`, { token, method: "POST" });
}

export function createAdminStorageUnit(
  token: string,
  payload: {
    company_id: number;
    site_id: number;
    name: string;
    unit_type: string;
    capacity_tons: number | null;
    location?: string | null;
    crop_type?: string | null;
    assigned_technician_id?: number | null;
    assigned_client_id?: number | null;
  }
) {
  return request<StorageUnit>("/api/admin/storage-units", { token, method: "POST", body: payload });
}

export function updateAdminStorageUnit(token: string, storageUnitId: number, payload: Partial<StorageUnit>) {
  return request<StorageUnit>(`/api/admin/storage-units/${storageUnitId}`, { token, method: "PATCH", body: payload });
}

export function activateAdminStorageUnit(token: string, storageUnitId: number) {
  return request<StorageUnit>(`/api/admin/storage-units/${storageUnitId}/activate`, { token, method: "POST" });
}

export function deactivateAdminStorageUnit(token: string, storageUnitId: number) {
  return request<StorageUnit>(`/api/admin/storage-units/${storageUnitId}/deactivate`, { token, method: "POST" });
}

export function createAdminDevice(
  token: string,
  payload: {
    storage_unit_id: number;
    external_id: string;
    name: string;
    device_type: string;
    is_active?: boolean;
  }
) {
  return request<DeviceWithApiKey>("/api/admin/devices", { token, method: "POST", body: payload });
}

export function updateAdminDevice(token: string, deviceId: number, payload: Partial<Device>) {
  return request<Device>(`/api/admin/devices/${deviceId}`, { token, method: "PATCH", body: payload });
}

export function resetAdminDeviceApiKey(token: string, deviceId: number) {
  return request<DeviceWithApiKey>(`/api/admin/devices/${deviceId}/reset-api-key`, { token, method: "POST" });
}

export function activateAdminDevice(token: string, deviceId: number) {
  return request<Device>(`/api/admin/devices/${deviceId}/activate`, { token, method: "POST" });
}

export function deactivateAdminDevice(token: string, deviceId: number) {
  return request<Device>(`/api/admin/devices/${deviceId}/deactivate`, { token, method: "POST" });
}

export function createAdminUser(
  token: string,
  payload: {
    company_id: number | null;
    email: string;
    full_name: string;
    password: string;
    role: "admin" | "technician" | "client";
    phone_whatsapp?: string | null;
    telegram_chat_id?: string | null;
    receives_alerts?: boolean;
    storage_unit_ids?: number[];
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

export function getIntegrationStatus(token: string) {
  return request<{
    notifications_dry_run: boolean;
    services: Record<string, { enabled?: boolean; configured: boolean; provider?: string; model?: string; template_configured?: boolean }>;
  }>("/api/admin/integrations/status", { token });
}

export function testAdminNotification(
  token: string,
  channel: "whatsapp" | "telegram",
  payload: { user_id?: number | null; storage_unit_id?: number | null; destination?: string | null; severity?: string; message: string }
) {
  return request<NotificationDelivery>(`/api/admin/notifications/test/${channel}`, {
    token,
    method: "POST",
    body: payload
  });
}
