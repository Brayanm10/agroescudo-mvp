export type Company = {
  id: number;
  name: string;
  tax_id: string | null;
  type: string;
  city: string | null;
  contact_name: string | null;
  contact_email: string | null;
  contact_phone: string | null;
  is_active: boolean;
  approval_status?: string;
  approved_at?: string | null;
  approved_by_id?: number | null;
  rejection_reason?: string | null;
  created_at: string;
  updated_at: string | null;
};

export type User = {
  id: number;
  company_id: number | null;
  email: string;
  full_name: string;
  role: UserRole;
  is_active: boolean;
  status?: string;
  locale?: string;
  email_verified_at?: string | null;
  password_changed_at?: string | null;
  phone_whatsapp: string | null;
  telegram_chat_id: string | null;
  receives_alerts: boolean;
  language: string;
  timezone: string;
  created_at: string | null;
  updated_at: string | null;
  last_login_at: string | null;
  last_seen_at?: string | null;
  company: Company | null;
};

export type UserRole = "admin" | "technician" | "client" | string;

export type Site = {
  id: number;
  company_id: number;
  name: string;
  location: string | null;
  latitude?: number | null;
  longitude?: number | null;
  timezone?: string;
  address?: string | null;
  department?: string | null;
  municipality?: string | null;
  created_at: string;
};

export type StorageUnit = {
  id: number;
  company_id: number;
  site_id: number;
  name: string;
  unit_type: string;
  capacity_tons: number | null;
  location: string | null;
  crop_type: string | null;
  operation_type: "storage" | "field";
  surface_hectares: number | null;
  is_active: boolean;
  assigned_technician_id: number | null;
  assigned_client_id: number | null;
  last_report_generated_at: string | null;
  created_at: string;
  updated_at: string | null;
};

export type Device = {
  id: number;
  company_id: number;
  site_id: number;
  storage_unit_id: number;
  external_id: string;
  name: string;
  device_type: string;
  model_version?: string | null;
  physical_location?: string | null;
  installed_at?: string | null;
  empty_distance_cm?: number | null;
  full_distance_cm?: number | null;
  is_active: boolean;
  created_at: string;
  last_seen_at: string | null;
  updated_at: string | null;
};

export type DeviceWithApiKey = Device & {
  api_key: string;
};

export type Reading = {
  id: number;
  company_id: number;
  site_id: number;
  storage_unit_id: number;
  device_id: number;
  grain_temperature: number | null;
  ambient_temperature: number | null;
  ambient_humidity: number | null;
  battery_voltage: number | null;
  signal_quality: number | null;
  level_distance_cm: number | null;
  level_percent: number | null;
  soil_moisture_percent: number | null;
  soil_moisture_raw?: number | null;
  soil_temperature_c: number | null;
  sensor_status: number | null;
  timestamp: string;
  received_at: string;
  metrics: MetricValue[];
};

export type MetricValue = {
  variable_type: string;
  raw_value: number | null;
  calibrated_value: number | null;
  value: number | null;
  unit: string;
  is_calibrated: boolean;
  calibration_version: number | null;
  quality_status: string;
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
  metric: string | null;
  observed_value: number | null;
  threshold_value: number | null;
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
  min_level_percent: number | null;
  max_level_percent: number | null;
  min_soil_moisture_percent: number | null;
  max_soil_moisture_percent: number | null;
};

export type CalibrationMethod = "OFFSET" | "LINEAR_TWO_POINT" | "LEVEL_GEOMETRY";

export type CalibrationInput = {
  variable_type: string;
  method: CalibrationMethod;
  device_channel_id?: number | null;
  offset?: number | null;
  raw_value?: number | null;
  dry_raw?: number | null;
  wet_raw?: number | null;
  dry_percent?: number | null;
  wet_percent?: number | null;
  parameters?: Record<string, number | string | boolean | null>;
  reference_instrument?: string | null;
  notes?: string | null;
};

export type Calibration = {
  id: number;
  device_id: number;
  device_channel_id: number | null;
  variable_type: string;
  method: CalibrationMethod;
  offset: number | null;
  slope: number | null;
  intercept: number | null;
  dry_raw: number | null;
  wet_raw: number | null;
  dry_percent: number | null;
  wet_percent: number | null;
  parameters: Record<string, number | string | boolean | null>;
  calibration_version: number;
  is_active: boolean;
  calibrated_at: string;
  calibrated_by_user_id: number | null;
  calibrated_by_name: string | null;
  reference_instrument: string | null;
  notes: string | null;
  created_at: string;
};

export type CalibrationStatus = {
  variable_type: string;
  status: string;
  calibration_version: number | null;
  calibrated_at: string | null;
  calibrated_by_name: string | null;
};

export type CalibrationPreview = {
  method: CalibrationMethod;
  variable_type: string;
  raw_value: number | null;
  calibrated_value: number | null;
  offset: number | null;
  slope: number | null;
  intercept: number | null;
  parameters: Record<string, number | string | boolean | null>;
};

export type DeviceSummary = {
  device: Device;
  latest_reading: Reading | null;
  active_alerts: number;
  calibration_status: "configured" | "pending" | "not_applicable";
  diagnostics: {
    signal_quality: number | null;
    snr_db: number | null;
    sensor_status: number | null;
    firmware_version: string | null;
  } | null;
  calibration: {
    empty_distance_cm: number | null;
    full_distance_cm: number | null;
  } | null;
  calibration_statuses: CalibrationStatus[];
};

export type ProductSummary = {
  storage_unit: StorageUnit;
  product_type: "silo_sensor" | "field_sensor";
  device_count: number;
  active_device_count: number;
  active_alerts: number;
  latest_reading: Reading | null;
  calibration_statuses: CalibrationStatus[];
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
  device_id: number | null;
  device_external_id: string | null;
  nodes: Array<{
    device_id: number;
    device_external_id: string;
    device_name: string;
    device_type: string;
    reading_count: number;
    max_grain_temperature: number | null;
    max_ambient_humidity: number | null;
    min_level_percent: number | null;
    max_level_percent: number | null;
    alerts_generated: number;
  }>;
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
  insights: StorageUnitInsight[];
  controlCenter: ControlCenterSummary | null;
};

export type InsightStatus = "normal" | "attention" | "critical" | "offline" | "insufficient_data" | string;

export type InsightEvidence = {
  label: string;
  value: string;
};

export type StorageUnitInsight = {
  storage_unit_id: number;
  storage_unit_name: string;
  period: string;
  status: InsightStatus;
  confidence: "high" | "medium" | "low" | number;
  data_points: number;
  summary: string;
  recommendations: string[];
  evidence: InsightEvidence[];
  generated_at: string;
};

export type InsightsResponse = {
  period: string;
  insights: StorageUnitInsight[];
};

export type ControlCenterBreakdownItem = {
  key: string;
  label: string;
  count: number;
  penalty: number;
  cap: number;
};

export type ControlCenterPriority = {
  type: string;
  severity: string;
  title: string;
  detail: string;
  storage_unit_id: number | null;
  alert_id: number | null;
};

export type ControlCenterSite = {
  site_id: number;
  site_name: string;
  status: "PROTEGIDA" | "ATENCION" | "CRITICA" | "SIN_DATOS" | string;
  score: number;
  storage_units: number;
  active_alerts: number;
};

export type ControlCenterDeviceHealth = {
  device_id: number;
  external_id: string;
  storage_unit_id: number;
  status: "online" | "offline" | string;
  last_seen_at: string | null;
  battery_voltage: number | null;
  signal_quality: number | null;
};

export type ControlCenterSummary = {
  generated_at: string;
  score: number;
  status: "PROTEGIDA" | "ATENCION" | "CRITICA" | "SIN_DATOS";
  formula_version: string;
  breakdown: ControlCenterBreakdownItem[];
  kpis: Record<string, number | string | null>;
  priorities: ControlCenterPriority[];
  sites: ControlCenterSite[];
  device_health: ControlCenterDeviceHealth[];
  recent_alerts: Alert[];
  recent_activity: OperationalLog[];
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
  company_id: number | null;
  alert_id: number | null;
  incident_id: number | null;
  maintenance_id: number | null;
  user_id: number | null;
  channel: string;
  provider: string | null;
  destination: string | null;
  severity: string;
  status: "dry_run" | "pending" | "sent" | "skipped" | "failed" | string;
  dry_run: boolean;
  payload_preview: string;
  provider_response: string | null;
  error: string | null;
  attempted_at: string | null;
  sent_at: string | null;
  delivered_at: string | null;
  failed_at: string | null;
  error_code: string | null;
  error_message_sanitized: string | null;
  provider_message_id: string | null;
  retry_count: number;
  next_retry_at: string | null;
  idempotency_key: string | null;
  payload_version: string;
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

export type ViewKey =
  | "dashboard"
  | "demo"
  | "pilots"
  | "companies"
  | "storage"
  | "silos"
  | "fields"
  | "sensors"
  | "sites"
  | "alerts"
  | "logs"
  | "maintenance"
  | "installations"
  | "evidence"
  | "systemHealth"
  | "gateways"
  | "pilotMetrics"
  | "comparison"
  | "firmware"
  | "exports"
  | "history"
  | "thresholds"
  | "reports"
  | "users"
  | "notifications"
  | "support"
  | "profile"
  | "changePassword"
  | "preferences";
export type RiskStatus = "normal" | "warning" | "critical" | "technical";

export type MaintenanceRecord = {
  id: number;
  company_id: number;
  storage_unit_id: number;
  device_id: number;
  service_case_id: number | null;
  maintenance_type: string;
  status: string;
  effective_status: string;
  priority: string;
  scheduled_at: string | null;
  started_at: string | null;
  completed_at: string | null;
  technician_id: number | null;
  observations: string | null;
  diagnosis: string | null;
  action_taken: string | null;
  evidence_count: number;
  next_maintenance_at: string | null;
  created_at: string;
  updated_at: string;
};

export type InstallationChecklistRecord = {
  id: number;
  company_id: number;
  storage_unit_id: number;
  device_id: number;
  technician_id: number | null;
  status: string;
  checklist_version: string;
  responses: Record<string, unknown>;
  first_reading_id: number | null;
  test_alert_id: number | null;
  notes: string | null;
  validation_errors: string[];
  next_review_at: string | null;
  created_at: string;
  updated_at: string;
};

export type EvidenceFile = {
  id: number;
  company_id: number | null;
  storage_unit_id: number | null;
  entity_type: string | null;
  entity_id: number | null;
  file_type: string;
  original_filename: string;
  content_type: string;
  size_bytes: number;
  captured_at: string | null;
  description: string | null;
  is_sensitive: boolean;
  created_at: string;
};

export type DeviceQr = {
  device_id: number;
  public_token: string;
  qr_version: number;
  scan_path: string;
  created_at: string;
};

export type GatewayStatus = {
  id: number;
  company_id: number | null;
  site_id: number | null;
  storage_unit_id: number | null;
  gateway_id: string;
  name: string;
  status: string;
  effective_status: string;
  firmware_version: string | null;
  internet_status: string;
  local_queue_size: number;
  associated_devices_count: number;
  restart_count: number;
  last_restart_reason: string | null;
  last_error_code: string | null;
  last_error_at: string | null;
  last_seen_at: string | null;
  is_active: boolean;
};

export type SystemHealth = {
  generated_at: string;
  backend: Record<string, string>;
  database: Record<string, string>;
  gateways: Record<string, number>;
  devices: Record<string, number>;
  data: Record<string, number>;
  alerts: Record<string, number | null>;
  notifications: Record<string, number>;
};

export type PilotMetrics = {
  generated_at: string;
  company_id: number | null;
  storage_unit_id: number | null;
  period_from: string;
  period_to: string;
  data_availability: Record<string, number | boolean | string | null>;
  device_availability: Record<string, number | boolean | string | null>;
  operations: Record<string, number | string | null>;
  maintenance: Record<string, number | string | null>;
  quality: Record<string, number | string | null>;
};

export type DeviceComparison = {
  device_id: number;
  variable: string;
  unit: string;
  period_a: Record<string, number | string | null>;
  period_b: Record<string, number | string | null>;
  absolute_difference: number | null;
  percentage_difference: number | null;
  sufficient_data: boolean;
  note: string;
};

export type FirmwareRelease = {
  id: number;
  device_type: string;
  version: string;
  status: string;
  release_notes: string | null;
  checksum: string | null;
  released_at: string | null;
  created_by_id: number;
  is_recommended: boolean;
  is_mandatory: boolean;
  created_at: string;
  updated_at: string;
};

export type DeviceFirmwareStatus = {
  device_id: number;
  external_id: string;
  device_type: string;
  current_version: string | null;
  recommended_version: string | null;
  is_outdated: boolean | null;
  update_status: string;
  last_update_at: string | null;
};
