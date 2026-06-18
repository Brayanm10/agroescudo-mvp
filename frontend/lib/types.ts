export type Company = {
  id: number;
  name: string;
  tax_id: string | null;
  created_at: string;
};

export type User = {
  id: number;
  company_id: number;
  email: string;
  full_name: string;
  role: UserRole;
  is_active: boolean;
  company: Company | null;
};

export type UserRole = "admin" | "technician" | "client" | string;

export type Site = {
  id: number;
  company_id: number;
  name: string;
  location: string | null;
  created_at: string;
};

export type StorageUnit = {
  id: number;
  company_id: number;
  site_id: number;
  name: string;
  unit_type: string;
  capacity_tons: number | null;
  assigned_technician_id: number | null;
  assigned_client_id: number | null;
  last_report_generated_at: string | null;
  created_at: string;
};

export type Device = {
  id: number;
  company_id: number;
  site_id: number;
  storage_unit_id: number;
  external_id: string;
  name: string;
  is_active: boolean;
  created_at: string;
};

export type Reading = {
  id: number;
  company_id: number;
  site_id: number;
  storage_unit_id: number;
  device_id: number;
  grain_temperature: number;
  ambient_temperature: number;
  ambient_humidity: number;
  battery_voltage: number;
  signal_quality: number;
  timestamp: string;
  received_at: string;
};

export type AlertSeverity = "critical" | "warning" | "technical" | string;

export type Alert = {
  id: number;
  company_id: number;
  site_id: number;
  storage_unit_id: number;
  device_id: number;
  reading_id: number | null;
  alert_type: string;
  severity: AlertSeverity;
  title: string;
  message: string;
  is_active: boolean;
  acknowledged_at: string | null;
  resolved_at: string | null;
  created_at: string;
};

export type OperationalLog = {
  id: number;
  company_id: number;
  site_id: number;
  storage_unit_id: number;
  device_id: number | null;
  alert_id: number | null;
  user_id: number | null;
  category: "installation" | "maintenance" | "corrective_action" | "inspection" | "general" | string;
  action_taken: string;
  operator_name: string;
  notes: string;
  timestamp: string;
  created_at: string;
};

export type Thresholds = {
  device_id: number;
  max_grain_temperature: number;
  max_ambient_humidity: number;
  min_battery_voltage: number;
  critical_temperature: number;
  critical_humidity: number;
};

export type WeeklyReport = {
  company_name: string;
  site_name: string;
  storage_unit_name: string;
  date_from: string;
  date_to: string;
  reading_count: number;
  max_grain_temperature: number | null;
  max_ambient_humidity: number | null;
  alerts_generated: number;
  alerts_resolved: number;
  approximate_hours_out_of_range: number;
  pilot_status: string;
  installation_count: number;
  maintenance_count: number;
  last_report_generated_at: string | null;
  operational_actions: OperationalLog[];
};

export type Pilot = {
  storage_unit_id: number;
  storage_unit_name: string;
  storage_unit_type: string;
  company_id: number;
  company_name: string;
  site_id: number;
  site_name: string;
  site_location: string | null;
  device_id: number | null;
  device_external_id: string | null;
  technician_user_id: number | null;
  technician_name: string | null;
  client_user_id: number | null;
  client_name: string | null;
  status: string;
  days_monitored: number;
  reading_count: number;
  alerts_generated: number;
  alerts_resolved: number;
  active_alerts: number;
  actions_registered: number;
  installation_count: number;
  maintenance_count: number;
  approximate_hours_out_of_range: number;
  last_reading_at: string | null;
  last_report_generated_at: string | null;
};

export type AppData = {
  me: User;
  companies: Company[];
  sites: Site[];
  storageUnits: StorageUnit[];
  devices: Device[];
  readings: Reading[];
  alerts: Alert[];
  activeAlerts: Alert[];
  logs: OperationalLog[];
  pilots: Pilot[];
  users: User[];
};

export type DemoSimulation = {
  storage_unit_id: number;
  device_id: number;
  device_external_id: string;
  reading: Reading;
  alerts: Alert[];
};

export type NotificationPreference = {
  id: number;
  company_id: number;
  user_id: number;
  channel: "whatsapp" | "telegram" | "push" | string;
  destination: string | null;
  minimum_severity: "all" | "technical" | "warning" | "critical" | string;
  enabled: boolean;
  created_at: string;
  updated_at: string;
};

export type NotificationEvent = {
  id: number;
  company_id: number;
  user_id: number | null;
  alert_id: number | null;
  channel: string;
  destination: string | null;
  status: "pending" | "sent" | "skipped" | "failed" | string;
  message: string;
  provider_message_id: string | null;
  error: string | null;
  created_at: string;
  sent_at: string | null;
};

export type NotificationDelivery = {
  id: number;
  alert_id: number | null;
  user_id: number | null;
  channel: string;
  destination: string | null;
  severity: string;
  status: "dry_run" | "pending" | "sent" | "skipped" | "failed" | string;
  dry_run: boolean;
  payload_preview: string;
  provider_response: string | null;
  error: string | null;
  created_at: string;
  updated_at: string;
};

export type AiAlertRecommendation = {
  alert_id: number;
  source: "rules" | "openai" | string;
  risk_level: string;
  summary: string;
  recommended_actions: string[];
  client_message: string;
  technical_notes: string[];
};

export type ViewKey = "dashboard" | "demo" | "pilots" | "sites" | "alerts" | "logs" | "thresholds" | "reports" | "users" | "notifications";
export type RiskStatus = "normal" | "warning" | "critical" | "technical";
