"use client";

import { FormEvent, useEffect, useState } from "react";
import type { ReactNode } from "react";
import type { LucideIcon } from "lucide-react";
import {
  Activity,
  AlertTriangle,
  ArrowRight,
  Battery,
  BellRing,
  Bot,
  Building2,
  CalendarDays,
  CheckCircle2,
  Clock3,
  GraduationCap,
  Headphones,
  ClipboardList,
  Eye,
  Factory,
  FileText,
  Gauge,
  LockKeyhole,
  MapPinned,
  MoreVertical,
  Radio,
  PlayCircle,
  Presentation,
  Rocket,
  Save,
  Send,
  Server,
  Sparkles,
  Thermometer,
  Trash2,
  UserPlus,
  Wrench,
  Wifi,
  X
} from "lucide-react";
import { AlertTable } from "@/components/AlertTable";
import { AppLayout } from "@/components/AppLayout";
import { ChangePasswordView } from "@/components/account/ChangePasswordView";
import { PreferencesView } from "@/components/account/PreferencesView";
import { ProfileView } from "@/components/account/ProfileView";
import { EmptyState } from "@/components/EmptyState";
import { ErrorState } from "@/components/ErrorState";
import { LoadingState } from "@/components/LoadingState";
import { ReadingChart } from "@/components/ReadingChart";
import { StatCard } from "@/components/StatCard";
import { StatusBadge } from "@/components/StatusBadge";
import { SupportChatbot } from "@/components/SupportChatbot";
import { ReportDownloadButton } from "@/components/reports/ReportDownloadButton";
import {
  ApiError,
  acknowledgeAlert,
  activateAdminCompany,
  activateAdminDevice,
  activateAdminStorageUnit,
  activateAdminUser,
  assignAdminUserStorageUnits,
  createInstallationChecklist,
  createAdminCompany,
  createAdminDevice,
  createAdminStorageUnit,
  createAdminUser,
  createOperationalLog,
  createPilot,
  deactivateAdminCompany,
  deactivateAdminDevice,
  deactivateAdminStorageUnit,
  deactivateAdminUser,
  deletePilotOperationalData,
  acceptInvite,
  forgotPassword,
  getIntegrationStatus,
  getNotificationDeliveries,
  getThresholds,
  getWeeklyReport,
  loadAppData,
  login,
  previewInvite,
  requestDemo,
  resetAdminUserPassword,
  resetPassword,
  resolveAlert,
  resetAdminDeviceApiKey,
  simulateCriticalDemoReading,
  signupCompany,
  testAdminNotification,
  updateAdminCompany,
  updateAdminDevice,
  updateAdminStorageUnit,
  updateAdminUser,
  updateThresholds,
  verifyEmail
} from "@/lib/api";
import { formatDateTime, formatNumber, statusFromAlerts } from "@/lib/format";
import type { Alert, AppData, Company, Device, DeviceWithApiKey, NotificationDelivery, OperationalLog, Pilot, Reading, StorageUnit, StorageUnitInsight, Thresholds, User, UserRole, ViewKey, WeeklyReport } from "@/lib/types";

const TOKEN_KEY = "agroescudo_token";

function clearStoredSession() {
  window.localStorage.removeItem(TOKEN_KEY);
  window.sessionStorage.removeItem(TOKEN_KEY);
}

function loginErrorMessage(err: unknown) {
  if (err instanceof ApiError) {
    if (err.status === 401) return "Credenciales incorrectas. Verifica correo y contraseña.";
    if (err.status === 0) return err.message;
  }
  return "No se pudo iniciar sesión. Intenta nuevamente.";
}

function allowedViewsForRole(role: UserRole): ViewKey[] {
  const accountViews: ViewKey[] = ["profile", "changePassword", "preferences"];
  if (role === "admin") return ["dashboard", "companies", "sensors", "alerts", "logs", "history", "reports", "support", "users", "thresholds", "notifications", ...accountViews];
  if (role === "technician") return ["sites", "sensors", "alerts", "maintenance", "logs", "support", ...accountViews];
  return ["dashboard", "sites", "alerts", "history", "reports", "support", ...accountViews];
}

function defaultViewForRole(role: UserRole): ViewKey {
  if (role === "technician") return "sites";
  return "dashboard";
}

function canAcknowledge(role: UserRole) {
  return role === "admin" || role === "technician";
}

function canResolve(role: UserRole) {
  return role === "admin";
}

function canCreateOperationalLog(role: UserRole) {
  return role === "admin" || role === "technician";
}

function canEditThresholds(role: UserRole) {
  return role === "admin";
}

function isStrongPassword(value: string) {
  return value.length >= 8 && /[A-Za-z]/.test(value) && /[0-9]/.test(value);
}

function roleExperience(role: UserRole) {
  if (role === "admin") {
    return {
      eyebrow: "Vista ejecutiva",
      title: "Operacion postcosecha bajo control",
      copy: "Estado consolidado de empresas, sitios, unidades monitoreadas, dispositivos y alertas que requieren atencion operativa."
    };
  }
  if (role === "technician") {
    return {
      eyebrow: "Dashboard tecnico",
      title: "Sensores, alertas y mantenimiento",
      copy: "Prioriza estado de nodos, bateria, senal, ultima lectura y acciones tecnicas registradas en campo."
    };
  }
  return {
    eyebrow: "Portal cliente",
    title: "Estado operativo de tu silo",
    copy: "Consulta condiciones actuales, alertas, bitacora y reportes descargables sin modificar configuracion tecnica."
  };
}

function readingForDevice(data: AppData, device: Device) {
  return data.readings.find((reading) => reading.device_id === device.id) || null;
}

function lastDeviceSync(data: AppData, device: Device) {
  const reading = readingForDevice(data, device);
  return device.last_seen_at || reading?.timestamp || null;
}

function disconnectedDevices(data: AppData) {
  const cutoffMs = Date.now() - 24 * 60 * 60 * 1000;
  return data.devices.filter((device) => {
    const lastSync = lastDeviceSync(data, device);
    return !lastSync || new Date(lastSync).getTime() < cutoffMs;
  });
}

function storageRisk(data: AppData, unit: StorageUnit): "critical" | "warning" | "offline" | "normal" {
  const activeAlerts = data.activeAlerts.filter((alert) => alert.storage_unit_id === unit.id);
  if (activeAlerts.some((alert) => alert.severity === "critical")) return "critical";
  if (activeAlerts.some((alert) => alert.severity === "warning" || alert.severity === "technical")) return "warning";
  const devices = data.devices.filter((device) => device.storage_unit_id === unit.id);
  if (devices.length && devices.every((device) => disconnectedDevices(data).some((item) => item.id === device.id))) return "offline";
  return "normal";
}

function stateStyles(state: "critical" | "warning" | "offline" | "normal") {
  if (state === "critical") return "border-red-200 bg-red-50 text-red-800";
  if (state === "warning") return "border-amber-200 bg-amber-50 text-amber-800";
  if (state === "offline") return "border-slate-200 bg-slate-100 text-slate-600";
  return "border-emerald-200 bg-emerald-50 text-emerald-800";
}

function stateLabel(state: "critical" | "warning" | "offline" | "normal") {
  if (state === "critical") return "Critico";
  if (state === "warning") return "Atencion";
  if (state === "offline") return "Sin conexion";
  return "Normal";
}

export default function Home() {
  const [token, setToken] = useState<string | null>(null);
  const [data, setData] = useState<AppData | null>(null);
  const [view, setView] = useState<ViewKey>("dashboard");
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [loginNotice, setLoginNotice] = useState<string | null>(null);
  const [busyAlertId, setBusyAlertId] = useState<number | null>(null);

  useEffect(() => {
    const stored = window.localStorage.getItem(TOKEN_KEY);
    if (!stored) {
      setLoading(false);
      return;
    }
    setToken(stored);
    refresh(stored);
  }, []);

  async function refresh(currentToken = token) {
    if (!currentToken) return;
    setLoading(true);
    setError(null);
    try {
      const appData = await loadAppData(currentToken);
      setData(appData);
      const allowed = allowedViewsForRole(appData.me.role);
      setView((current) => allowed.includes(current) ? current : defaultViewForRole(appData.me.role));
    } catch (err) {
      if (err instanceof ApiError && err.status === 401) {
        clearStoredSession();
        setToken(null);
        setData(null);
        setView("dashboard");
        setLoginNotice("Sesión vencida. Inicia sesión nuevamente.");
        return;
      }
      setError(err instanceof Error ? err.message : "No se pudo cargar la API.");
    } finally {
      setLoading(false);
    }
  }

  async function handleLogin(email: string, password: string) {
    setError(null);
    setLoginNotice(null);
    const response = await login(email, password);
    window.localStorage.setItem(TOKEN_KEY, response.access_token);
    setToken(response.access_token);
    await refresh(response.access_token);
  }

  function logout() {
    clearStoredSession();
    setToken(null);
    setData(null);
    setView("dashboard");
    setError(null);
    setLoginNotice(null);
  }

  async function mutateAlert(alert: Alert, action: "ack" | "resolve") {
    if (!token) return;
    setBusyAlertId(alert.id);
    try {
      if (action === "ack") {
        await acknowledgeAlert(token, alert.id);
      } else {
        await resolveAlert(token, alert.id);
      }
      await refresh(token);
    } catch (err) {
      setError(err instanceof Error ? err.message : "No se pudo actualizar la alerta.");
    } finally {
      setBusyAlertId(null);
    }
  }

  if (!token) {
    return <LoginScreen onLogin={handleLogin} initialMessage={loginNotice} />;
  }

  if (loading && !data) {
    return <FullScreenShell><LoadingState /></FullScreenShell>;
  }

  if (!data) {
    return (
      <FullScreenShell>
        <ErrorState message={error || "No se pudo cargar AgroEscudo."} onRetry={() => refresh()} />
      </FullScreenShell>
    );
  }

  const allowedViews = allowedViewsForRole(data.me.role);
  const viewAllowed = allowedViews.includes(view);
  const canAck = canAcknowledge(data.me.role);
  const canClose = canResolve(data.me.role);
  const canLog = canCreateOperationalLog(data.me.role);

  return (
    <AppLayout current={view} onChange={setView} allowedViews={allowedViews} user={data.me} onLogout={logout} onRefresh={() => refresh()}>
      {error ? <div className="mb-4"><ErrorState message={error} onRetry={() => refresh()} /></div> : null}
      {loading ? <div className="mb-4"><LoadingState label="Actualizando datos" /></div> : null}
      {!viewAllowed ? <UnauthorizedState /> : null}
      {viewAllowed && view === "dashboard" ? (
        <DashboardView
          data={data}
          onAcknowledge={canAck ? (alert) => mutateAlert(alert, "ack") : undefined}
          onResolve={canClose ? (alert) => mutateAlert(alert, "resolve") : undefined}
          busyAlertId={busyAlertId}
          onNavigate={setView}
          canCreateLog={canLog}
        />
      ) : null}
      {viewAllowed && view === "demo" ? <DemoGuidedView data={data} token={token} onNavigate={setView} onRefresh={() => refresh(token)} /> : null}
      {viewAllowed && view === "pilots" ? <PilotsView data={data} token={token} onChanged={() => refresh(token)} /> : null}
      {viewAllowed && view === "companies" ? <AdminCompaniesAndSitesView data={data} token={token} onChanged={() => refresh(token)} /> : null}
      {viewAllowed && view === "storage" ? <StorageUnitsAdminView data={data} token={token} onChanged={() => refresh(token)} /> : null}
      {viewAllowed && view === "sensors" ? (
        data.me.role === "admin" ? <SensorsAdminView data={data} token={token} onChanged={() => refresh(token)} /> : <DevicesStatusView data={data} />
      ) : null}
      {viewAllowed && view === "sites" ? <SitesView data={data} token={token} onOpenLogs={() => setView("logs")} canCreateLog={canLog} /> : null}
      {viewAllowed && view === "alerts" ? (
        <AlertsView
          data={data}
          onAcknowledge={canAck ? (alert) => mutateAlert(alert, "ack") : undefined}
          onResolve={canClose ? (alert) => mutateAlert(alert, "resolve") : undefined}
          busyAlertId={busyAlertId}
        />
      ) : null}
      {viewAllowed && view === "logs" ? <LogsView data={data} token={token} onChanged={() => refresh(token)} canCreateLog={canLog} /> : null}
      {viewAllowed && view === "maintenance" ? <MaintenanceView data={data} token={token} onChanged={() => refresh(token)} canCreateLog={canLog} /> : null}
      {viewAllowed && view === "history" ? <HistoryView data={data} /> : null}
      {viewAllowed && view === "thresholds" ? (
        canEditThresholds(data.me.role) ? <ThresholdsView devices={data.devices} token={token} /> : <UnauthorizedState />
      ) : null}
      {viewAllowed && view === "reports" ? <ReportsView data={data} token={token} /> : null}
      {viewAllowed && view === "users" ? <UsersAdminView data={data} token={token} onChanged={() => refresh(token)} /> : null}
      {viewAllowed && view === "notifications" ? <NotificationsAdminView data={data} token={token} /> : null}
      {viewAllowed && view === "support" ? <SupportView data={data} token={token} onNavigate={setView} /> : null}
      {viewAllowed && view === "profile" ? <ProfileView data={data} token={token} onChanged={() => refresh(token)} /> : null}
      {viewAllowed && view === "changePassword" ? <ChangePasswordView token={token} /> : null}
      {viewAllowed && view === "preferences" ? <PreferencesView data={data} token={token} onChanged={() => refresh(token)} /> : null}
    </AppLayout>
  );
}

function FullScreenShell({ children }: { children: ReactNode }) {
  return <main className="min-h-screen bg-field p-6">{children}</main>;
}

function UnauthorizedState() {
  return (
    <section className="panel max-w-3xl p-6">
      <p className="section-kicker">Acceso restringido</p>
      <h2 className="section-title">No tienes permisos para esta seccion.</h2>
      <p className="section-subtitle">
        Tu rol puede consultar informacion operativa, pero esta vista contiene configuracion tecnica o administrativa.
      </p>
    </section>
  );
}

function LoginScreen({
  onLogin,
  initialMessage
}: {
  onLogin: (email: string, password: string) => Promise<void>;
  initialMessage?: string | null;
}) {
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState<string | null>(initialMessage || null);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    setError(initialMessage || null);
  }, [initialMessage]);

  async function submit(event: FormEvent) {
    event.preventDefault();
    setLoading(true);
    setError(null);
    try {
      await onLogin(email, password);
    } catch (err) {
      setError(loginErrorMessage(err));
    } finally {
      setLoading(false);
    }
  }

  return (
    <main className="brand-grid min-h-screen overflow-hidden bg-emeraldInk p-4 text-slate-950">
      <div className="absolute inset-0 bg-[radial-gradient(circle_at_18%_18%,rgba(4,120,87,0.42),transparent_34rem),radial-gradient(circle_at_82%_20%,rgba(212,154,0,0.2),transparent_26rem),linear-gradient(135deg,rgba(2,44,34,0.2),rgba(2,44,34,0.92))]" />
      <section className="relative mx-auto grid min-h-[calc(100vh-2rem)] w-full max-w-6xl items-center gap-6 lg:grid-cols-[1.08fr_0.92fr]">
        <div className="hidden min-h-[660px] overflow-hidden rounded-[22px] border border-white/10 bg-emeraldDeep shadow-glow lg:block">
          <div className="relative h-full min-h-[640px]">
            <img src="/brand/logo-vertical-campo.png" alt="AgroEscudo campo" className="absolute inset-0 h-full w-full object-cover" />
            <div className="absolute inset-0 bg-gradient-to-t from-emeraldInk/96 via-emeraldInk/66 to-emeraldInk/24" />
            <div className="absolute inset-0 bg-[linear-gradient(90deg,rgba(2,44,34,0.72),rgba(2,44,34,0.18)_55%,rgba(2,44,34,0.42))]" />
            <div className="absolute left-6 top-6 rounded-full border border-white/15 bg-white/10 px-3 py-1.5 text-xs font-bold uppercase tracking-[0.14em] text-emerald-50 backdrop-blur">
              Protección operativa
            </div>
            <div className="absolute bottom-0 left-0 right-0 p-8 text-white">
              <div className="max-w-2xl rounded-2xl border border-white/15 bg-emeraldInk/60 p-5 shadow-glow backdrop-blur-sm">
                <p className="section-kicker text-amber-200">Plataforma agtech B2B</p>
                <h1 className="mt-3 max-w-lg text-4xl font-black leading-[1.05] tracking-tight drop-shadow-[0_2px_10px_rgba(0,0,0,0.45)]">Monitoreo premium para riesgo postcosecha.</h1>
                <p className="mt-4 max-w-xl text-sm leading-6 text-emerald-50">
                  Control de silos, galpones y centros de acopio con sensores IoT, alertas, bitácora y trazabilidad operativa.
                </p>
                <div className="mt-6 grid max-w-xl grid-cols-3 gap-2 text-center text-[10px] font-black uppercase tracking-[0.14em] text-emerald-50">
                  <span className="rounded-lg border border-white/15 bg-white/15 px-2 py-2 backdrop-blur">IoT</span>
                  <span className="rounded-lg border border-white/15 bg-white/15 px-2 py-2 backdrop-blur">Alertas</span>
                  <span className="rounded-lg border border-white/15 bg-white/15 px-2 py-2 backdrop-blur">Bitácora</span>
                </div>
              </div>
            </div>
          </div>
        </div>
        <div className="brand-surface mx-auto w-full max-w-md rounded-[22px] border border-white/80 p-7 shadow-glow backdrop-blur">
          <div className="flex items-center gap-4 rounded-2xl border border-slate-200 bg-white p-4 shadow-soft">
            <img src="/brand/shield-transparent.png" alt="" className="h-16 w-16 shrink-0 object-contain" />
            <div>
              <p className="text-3xl font-black leading-none tracking-tight text-emeraldDeep">AgroEscudo</p>
              <p className="mt-1 text-[10px] font-black uppercase tracking-[0.16em] text-amber-700">Datos que protegen</p>
            </div>
          </div>
          <div className="mt-7">
            <p className="section-kicker">Acceso seguro</p>
            <h2 className="mt-2 text-2xl font-black tracking-tight text-slate-950">Centro operativo AgroEscudo</h2>
            <p className="mt-2 text-sm leading-6 text-slate-500">Ingresa para revisar alertas, lecturas, umbrales y acciones de campo.</p>
          </div>
          <form id="agroescudo-login-form" onSubmit={submit} className="mt-6 space-y-4">
            <label className="block">
              <span className="text-xs font-black uppercase tracking-[0.14em] text-slate-500">Email</span>
              <input
                value={email}
                onChange={(event) => setEmail(event.target.value)}
                className="input mt-1.5"
              />
            </label>
            <label className="block">
              <span className="text-xs font-black uppercase tracking-[0.14em] text-slate-500">Password</span>
              <input
                type="password"
                value={password}
                onChange={(event) => setPassword(event.target.value)}
                className="input mt-1.5"
              />
            </label>
            {error ? (
              <div className="rounded-lg border border-red-200 bg-red-50 p-3 text-sm font-medium text-red-800">
                <p className="whitespace-pre-line">{error}</p>
                <button
                  type="button"
                  onClick={() => {
                    const form = document.querySelector<HTMLFormElement>("#agroescudo-login-form");
                    form?.requestSubmit();
                  }}
                  className="mt-3 rounded-lg bg-red-700 px-3 py-2 text-xs font-black text-white transition hover:bg-red-800"
                >
                  Reintentar conexión
                </button>
              </div>
            ) : null}
            <button
              type="submit"
              disabled={loading}
              className="btn-primary w-full py-3"
            >
              <LockKeyhole className="mr-2" size={17} aria-hidden="true" />
              {loading ? "Ingresando..." : "Ingresar al dashboard"}
            </button>
          </form>
          <div className="mt-6 rounded-xl border border-slate-200 bg-white/70 p-3">
            <div className="grid grid-cols-3 gap-2 text-center text-[10px] font-black uppercase tracking-[0.12em] text-slate-500">
              <span className="rounded-lg bg-emerald-50 px-2 py-2 text-emerald-800">Control</span>
              <span className="rounded-lg bg-amber-50 px-2 py-2 text-amber-800">Alertas</span>
              <span className="rounded-lg bg-slate-100 px-2 py-2 text-slate-700">Trazabilidad</span>
            </div>
          </div>
          <PublicAccessPanel onLogin={onLogin} />
        </div>
      </section>
    </main>
  );
}

type PublicMode = "signup" | "invite" | "forgot" | "reset" | "verify" | "demo";

function PublicAccessPanel({ onLogin }: { onLogin: (email: string, password: string) => Promise<void> }) {
  const [mode, setMode] = useState<PublicMode | null>(null);
  const [busy, setBusy] = useState(false);
  const [message, setMessage] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [invitePreview, setInvitePreview] = useState<string | null>(null);

  async function run(action: () => Promise<string>) {
    setBusy(true);
    setError(null);
    setMessage(null);
    try {
      setMessage(await action());
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "No se pudo completar la solicitud.");
    } finally {
      setBusy(false);
    }
  }

  const buttonClass = "rounded-xl border border-slate-200 bg-white px-3 py-2 text-xs font-black text-slate-700 transition hover:border-emerald-200 hover:bg-emerald-50 hover:text-emerald-900";

  return (
    <div className="mt-5 rounded-2xl border border-slate-200 bg-white/80 p-4">
      <p className="text-[10px] font-black uppercase tracking-[0.16em] text-slate-500">Acceso piloto comercial</p>
      <div className="mt-3 grid grid-cols-2 gap-2">
        <button type="button" className={buttonClass} onClick={() => setMode(mode === "signup" ? null : "signup")}>Crear cuenta</button>
        <button type="button" className={buttonClass} onClick={() => setMode(mode === "invite" ? null : "invite")}>Tengo invitacion</button>
        <button type="button" className={buttonClass} onClick={() => setMode(mode === "forgot" ? null : "forgot")}>Olvide password</button>
        <button type="button" className={buttonClass} onClick={() => setMode(mode === "demo" ? null : "demo")}>Solicitar demo</button>
      </div>
      {mode === "forgot" ? (
        <button type="button" className="mt-2 text-xs font-bold text-emerald-800 underline" onClick={() => setMode("reset")}>Ya tengo token de recuperacion</button>
      ) : null}
      {mode === "signup" ? <SignupCompanyForm busy={busy} onSubmit={run} /> : null}
      {mode === "demo" ? <DemoRequestForm busy={busy} onSubmit={run} /> : null}
      {mode === "forgot" ? <ForgotPasswordForm busy={busy} onSubmit={run} /> : null}
      {mode === "reset" ? <ResetPasswordForm busy={busy} onSubmit={run} /> : null}
      {mode === "invite" ? <InviteAcceptForm busy={busy} onSubmit={run} onLogin={onLogin} preview={invitePreview} setPreview={setInvitePreview} /> : null}
      {mode === "verify" ? <VerifyEmailForm busy={busy} onSubmit={run} /> : null}
      {message ? (
        <div className="mt-3 whitespace-pre-line rounded-xl border border-emerald-200 bg-emerald-50 p-3 text-xs font-semibold leading-5 text-emerald-900">{message}</div>
      ) : null}
      {error ? (
        <div className="mt-3 whitespace-pre-line rounded-xl border border-red-200 bg-red-50 p-3 text-xs font-semibold leading-5 text-red-900">{error}</div>
      ) : null}
      {mode && mode !== "verify" ? (
        <button type="button" className="mt-3 text-xs font-bold text-slate-500 underline" onClick={() => setMode("verify")}>Verificar correo con token</button>
      ) : null}
    </div>
  );
}

function PublicField({ label, name, type = "text", required = false, placeholder }: { label: string; name: string; type?: string; required?: boolean; placeholder?: string }) {
  return (
    <label className="block">
      <span className="text-[10px] font-black uppercase tracking-[0.14em] text-slate-500">{label}{required ? " *" : ""}</span>
      <input name={name} type={type} required={required} placeholder={placeholder} className="input mt-1 h-10 text-sm" />
    </label>
  );
}

function formValue(data: FormData, key: string) {
  return String(data.get(key) || "").trim();
}

function SignupCompanyForm({ busy, onSubmit }: { busy: boolean; onSubmit: (action: () => Promise<string>) => void }) {
  return (
    <form
      className="mt-4 space-y-3"
      onSubmit={(event) => {
        event.preventDefault();
        const data = new FormData(event.currentTarget);
        onSubmit(async () => {
          const result = await signupCompany({
            responsible_name: formValue(data, "responsible_name"),
            work_email: formValue(data, "work_email"),
            phone: formValue(data, "phone") || null,
            commercial_name: formValue(data, "commercial_name"),
            legal_name: formValue(data, "legal_name") || null,
            tax_id: formValue(data, "tax_id") || null,
            sector: formValue(data, "sector") || "acopiador",
            city: formValue(data, "city") || null,
            department: formValue(data, "department") || null,
            estimated_sites: Number(formValue(data, "estimated_sites") || 0),
            estimated_storage_units: Number(formValue(data, "estimated_storage_units") || 0),
            use_case: formValue(data, "use_case") || null,
            password: formValue(data, "password"),
            language: "es",
            consent_terms: true,
            consent_privacy: true
          });
          return `${result.message}${result.verification_preview_token ? `\nToken local de verificacion: ${result.verification_preview_token}` : ""}`;
        });
      }}
    >
      <div className="grid gap-2 sm:grid-cols-2">
        <PublicField label="Responsable" name="responsible_name" required />
        <PublicField label="Email trabajo" name="work_email" type="email" required />
        <PublicField label="Empresa" name="commercial_name" required />
        <PublicField label="Telefono" name="phone" />
        <PublicField label="Ciudad" name="city" />
        <PublicField label="Departamento" name="department" />
        <PublicField label="Sitios" name="estimated_sites" type="number" />
        <PublicField label="Silos/Galpones" name="estimated_storage_units" type="number" />
      </div>
      <PublicField label="Password" name="password" type="password" required />
      <textarea name="use_case" className="input min-h-20 text-sm" placeholder="Caso de uso del piloto" />
      <button type="submit" disabled={busy} className="btn-primary w-full py-2">{busy ? "Enviando..." : "Enviar solicitud de cuenta"}</button>
    </form>
  );
}

function DemoRequestForm({ busy, onSubmit }: { busy: boolean; onSubmit: (action: () => Promise<string>) => void }) {
  return (
    <form className="mt-4 space-y-3" onSubmit={(event) => {
      event.preventDefault();
      const data = new FormData(event.currentTarget);
      onSubmit(async () => {
        const result = await requestDemo({
          name: formValue(data, "name"),
          company_name: formValue(data, "company_name"),
          position: formValue(data, "position") || null,
          email: formValue(data, "email"),
          phone: formValue(data, "phone") || null,
          city: formValue(data, "city") || null,
          interest: formValue(data, "interest") || null,
          consent: true
        });
        return result.message;
      });
    }}>
      <div className="grid gap-2 sm:grid-cols-2">
        <PublicField label="Nombre" name="name" required />
        <PublicField label="Empresa" name="company_name" required />
        <PublicField label="Email" name="email" type="email" required />
        <PublicField label="Telefono" name="phone" />
      </div>
      <textarea name="interest" className="input min-h-20 text-sm" placeholder="Que quieres monitorear en el piloto" />
      <button type="submit" disabled={busy} className="btn-primary w-full py-2">{busy ? "Enviando..." : "Solicitar demostracion"}</button>
    </form>
  );
}

function ForgotPasswordForm({ busy, onSubmit }: { busy: boolean; onSubmit: (action: () => Promise<string>) => void }) {
  return (
    <form className="mt-4 space-y-3" onSubmit={(event) => {
      event.preventDefault();
      const data = new FormData(event.currentTarget);
      onSubmit(async () => {
        const result = await forgotPassword(formValue(data, "email"));
        return `${result.message}${result.reset_preview_token ? `\nToken local de recuperacion: ${result.reset_preview_token}` : ""}`;
      });
    }}>
      <PublicField label="Email" name="email" type="email" required />
      <button type="submit" disabled={busy} className="btn-primary w-full py-2">{busy ? "Enviando..." : "Enviar recuperacion"}</button>
    </form>
  );
}

function ResetPasswordForm({ busy, onSubmit }: { busy: boolean; onSubmit: (action: () => Promise<string>) => void }) {
  return (
    <form className="mt-4 space-y-3" onSubmit={(event) => {
      event.preventDefault();
      const data = new FormData(event.currentTarget);
      onSubmit(async () => {
        const result = await resetPassword({ token: formValue(data, "token"), password: formValue(data, "password") });
        return result.message;
      });
    }}>
      <PublicField label="Token" name="token" required />
      <PublicField label="Nuevo password" name="password" type="password" required />
      <button type="submit" disabled={busy} className="btn-primary w-full py-2">{busy ? "Actualizando..." : "Actualizar password"}</button>
    </form>
  );
}

function InviteAcceptForm({
  busy,
  onSubmit,
  onLogin,
  preview,
  setPreview
}: {
  busy: boolean;
  onSubmit: (action: () => Promise<string>) => void;
  onLogin: (email: string, password: string) => Promise<void>;
  preview: string | null;
  setPreview: (value: string | null) => void;
}) {
  return (
    <form className="mt-4 space-y-3" onSubmit={(event) => {
      event.preventDefault();
      const data = new FormData(event.currentTarget);
      const token = formValue(data, "token");
      const fullName = formValue(data, "full_name");
      const password = formValue(data, "password");
      onSubmit(async () => {
        const result = await acceptInvite({ token, full_name: fullName, password });
        window.localStorage.setItem(TOKEN_KEY, result.access_token);
        await onLogin(formValue(data, "email"), password);
        return "Invitacion aceptada. Sesion iniciada.";
      });
    }}>
      <PublicField label="Token invitacion" name="token" required />
      <button type="button" disabled={busy} className="btn-secondary w-full py-2" onClick={async (event) => {
        const form = event.currentTarget.closest("form");
        const token = form ? formValue(new FormData(form), "token") : "";
        if (!token) return;
        try {
          const result = await previewInvite(token);
          setPreview(`${result.company_name} · ${result.email} · ${result.role}`);
        } catch (err) {
          setPreview(err instanceof ApiError ? err.message : "No se pudo validar la invitacion.");
        }
      }}>Previsualizar invitacion</button>
      {preview ? <p className="rounded-xl bg-slate-50 p-3 text-xs font-semibold text-slate-700">{preview}</p> : null}
      <PublicField label="Email invitado" name="email" type="email" required />
      <PublicField label="Nombre" name="full_name" required />
      <PublicField label="Password" name="password" type="password" required />
      <button type="submit" disabled={busy} className="btn-primary w-full py-2">{busy ? "Aceptando..." : "Aceptar invitacion"}</button>
    </form>
  );
}

function VerifyEmailForm({ busy, onSubmit }: { busy: boolean; onSubmit: (action: () => Promise<string>) => void }) {
  return (
    <form className="mt-4 space-y-3" onSubmit={(event) => {
      event.preventDefault();
      const data = new FormData(event.currentTarget);
      onSubmit(async () => {
        const result = await verifyEmail(formValue(data, "token"));
        return result.message;
      });
    }}>
      <PublicField label="Token verificacion" name="token" required />
      <button type="submit" disabled={busy} className="btn-primary w-full py-2">{busy ? "Verificando..." : "Verificar correo"}</button>
    </form>
  );
}

function DashboardView({
  data,
  onAcknowledge,
  onResolve,
  busyAlertId,
  onNavigate,
  canCreateLog
}: {
  data: AppData;
  onAcknowledge?: (alert: Alert) => void;
  onResolve?: (alert: Alert) => void;
  busyAlertId: number | null;
  onNavigate: (view: ViewKey) => void;
  canCreateLog: boolean;
}) {
  const latest = data.readings[0];
  const status = statusFromAlerts(data.activeAlerts);
  const criticalCount = data.activeAlerts.filter((alert) => alert.severity === "critical").length;
  const warningCount = data.activeAlerts.filter((alert) => alert.severity === "warning").length;
  const experience = roleExperience(data.me.role);
  const disconnected = disconnectedDevices(data);
  const criticalUnits = data.storageUnits
    .map((unit) => ({ unit, risk: storageRisk(data, unit), alerts: data.activeAlerts.filter((alert) => alert.storage_unit_id === unit.id) }))
    .filter((item) => item.risk === "critical" || item.risk === "warning" || item.risk === "offline")
    .slice(0, 5);
  const lastSync = data.readings[0]?.received_at || data.readings[0]?.timestamp || null;
  const recommendedActions = [
    criticalCount ? `Atender ${criticalCount} alerta(s) critica(s) antes de cierre de turno.` : null,
    disconnected.length ? `Revisar conexion de ${disconnected.length} sensor(es) sin sincronizacion reciente.` : null,
    warningCount ? `Programar inspeccion preventiva para ${warningCount} alerta(s) en atencion.` : null,
    data.logs.length ? null : "Registrar bitacora operativa cuando se ejecute una accion correctiva."
  ].filter(Boolean) as string[];

  return (
    <div className="space-y-6">
      <ControlCenterPanel data={data} onNavigate={onNavigate} />

      <section className="grid gap-4 xl:grid-cols-[1.2fr_0.9fr]">
        <div className="panel overflow-hidden">
          <div className="border-b border-slate-200 px-5 py-4">
            <p className="section-kicker">Prioridad operativa</p>
            <h2 className="section-title">Sitios que requieren atencion</h2>
          </div>
          <div className="divide-y divide-slate-200">
            {criticalUnits.length ? criticalUnits.map(({ unit, risk, alerts }) => {
              const site = data.sites.find((item) => item.id === unit.site_id);
              const deviceCount = data.devices.filter((device) => device.storage_unit_id === unit.id).length;
              return (
                <article key={unit.id} className="flex flex-wrap items-center justify-between gap-4 p-5">
                  <div>
                    <div className="flex flex-wrap items-center gap-2">
                      <h3 className="font-black text-slate-950">{unit.name}</h3>
                      <span className={`rounded-full border px-2.5 py-1 text-[10px] font-black uppercase tracking-[0.12em] ${stateStyles(risk)}`}>{stateLabel(risk)}</span>
                    </div>
                    <p className="mt-1 text-sm text-slate-500">{site?.name || "Sitio sin registrar"} · {deviceCount} dispositivo(s) · {alerts.length} alerta(s)</p>
                  </div>
                  <button type="button" onClick={() => onNavigate("sites")} className="btn-secondary">Revisar silo</button>
                </article>
              );
            }) : (
              <div className="p-5">
                <EmptyState title="Sin sitios criticos" message="No hay silos con estado critico, en atencion o sin conexion reciente." />
              </div>
            )}
          </div>
        </div>
        <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-1">
          <PriorityCard title="Alertas activas" value={data.activeAlerts.length.toString()} state={criticalCount ? "critical" : data.activeAlerts.length ? "warning" : "normal"} detail={criticalCount ? `${criticalCount} critica(s)` : "Sin criticos activos"} />
          <PriorityCard title="Sensores desconectados" value={disconnected.length.toString()} state={disconnected.length ? "offline" : "normal"} detail={disconnected.length ? "Sin lectura reciente" : "Sin desconexiones relevantes"} />
          <PriorityCard title="Ultima sincronizacion" value={lastSync ? formatDateTime(lastSync) : "Sin dato"} state={lastSync ? "normal" : "offline"} detail={latest ? `${formatNumber(latest.grain_temperature, " C")} / ${formatNumber(latest.ambient_humidity, "%")}` : "Esperando lectura"} />
        </div>
      </section>

      <section className={`relative overflow-hidden rounded-[18px] border p-6 shadow-panel ${
        status === "critical"
          ? "border-red-200 bg-red-50"
          : status === "warning"
            ? "border-amber-200 bg-amber-50"
            : "border-emerald-200 bg-emerald-50"
      }`}>
        <div className="pointer-events-none absolute right-0 top-0 h-32 w-32 rounded-bl-full bg-white/40" />
        <div className="flex flex-wrap items-center justify-between gap-5">
          <div>
            <p className="section-kicker">{experience.eyebrow}</p>
            <h2 className="mt-2 max-w-3xl text-3xl font-black leading-tight tracking-tight text-slate-950">{experience.title}</h2>
            <p className="mt-2 max-w-3xl text-sm leading-6 text-slate-600">
              {experience.copy}
            </p>
          </div>
          <div className="relative rounded-2xl border border-white/70 bg-white/80 p-4 shadow-soft">
            <p className="text-xs font-bold uppercase tracking-[0.14em] text-slate-500">Estado general</p>
            <div className="mt-3 flex items-center gap-3">
              <StatusBadge status={status} />
              <span className="text-sm font-semibold text-slate-700">{data.activeAlerts.length} alerta(s) activa(s)</span>
            </div>
          </div>
        </div>
      </section>

      <section className="panel p-5">
        <div className="flex flex-wrap items-start justify-between gap-4">
          <div>
            <p className="section-kicker">Siguiente mejor accion</p>
            <h2 className="section-title">Acciones recomendadas</h2>
          </div>
          {canCreateLog ? <button type="button" onClick={() => onNavigate("logs")} className="btn-primary">Registrar accion</button> : null}
        </div>
        <div className="mt-4 grid gap-3 lg:grid-cols-3">
          {(recommendedActions.length ? recommendedActions : ["Operacion estable. Mantener monitoreo y revisar reporte semanal."]).map((action) => (
            <div key={action} className="rounded-2xl border border-slate-200 bg-white p-4 text-sm font-semibold leading-6 text-slate-700 shadow-soft">
              {action}
            </div>
          ))}
        </div>
      </section>

      <InsightsPanel data={data} onNavigate={onNavigate} />
      <PilotOverview pilots={data.pilots} role={data.me.role} onNavigate={onNavigate} />
      <CommandCenter data={data} onNavigate={onNavigate} canCreateLog={canCreateLog} />
      {criticalCount > 0 ? (
        <section className="rounded-panel border border-red-300 bg-red-50 p-5 text-red-950 shadow-panel">
          <div className="flex items-start gap-3">
            <AlertTriangle size={24} aria-hidden="true" />
            <div>
              <p className="font-black">Riesgo critico activo</p>
              <p className="text-sm">Hay {criticalCount} alerta(s) critica(s) que requieren accion operativa inmediata.</p>
            </div>
          </div>
        </section>
      ) : null}
      <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
        <StatCard label="Empresas" value={data.companies.length} icon={Building2} />
        <StatCard label="Sitios monitoreados" value={data.sites.length} icon={MapPinned} />
        <StatCard label="Silos y galpones" value={data.storageUnits.length} icon={Factory} />
        <StatCard label="Dispositivos" value={data.devices.length} icon={Server} />
        <StatCard label="Alertas activas" value={data.activeAlerts.length} icon={AlertTriangle} tone={status === "critical" ? "critical" : status === "warning" ? "amber" : "emerald"} />
        <StatCard label="Alertas warning" value={warningCount} icon={Activity} detail="Condiciones preventivas activas" tone={warningCount ? "amber" : "neutral"} />
        <StatCard label="Ultima lectura" value={latest ? formatDateTime(latest.timestamp) : "Sin dato"} icon={Radio} />
        <StatCard label="Temp. grano actual" value={latest ? formatNumber(latest.grain_temperature, " C") : "Sin dato"} icon={Thermometer} />
      </div>
      <section className="space-y-3">
        <div className="mb-3 flex items-center justify-between">
          <div>
            <p className="section-kicker">Atencion ahora</p>
            <h2 className="section-title">Alertas recientes</h2>
          </div>
        </div>
        {data.alerts.length ? (
          <AlertTable
            alerts={data.alerts.slice(0, 8)}
            devices={data.devices}
            storageUnits={data.storageUnits}
            onAcknowledge={onAcknowledge}
            onResolve={onResolve}
            busyAlertId={busyAlertId}
          />
        ) : (
          <EmptyState title="Sin alertas registradas" message="Cuando un sensor supere umbrales, las alertas apareceran aqui." />
        )}
      </section>
    </div>
  );
}

function ControlCenterPanel({ data, onNavigate }: { data: AppData; onNavigate: (view: ViewKey) => void }) {
  const summary = data.controlCenter;
  if (!summary) {
    return null;
  }

  const statusTone =
    summary.status === "CRITICA"
      ? "border-red-200 bg-red-50 text-red-950"
      : summary.status === "ATENCION"
        ? "border-amber-200 bg-amber-50 text-amber-950"
        : summary.status === "SIN_DATOS"
          ? "border-slate-200 bg-slate-50 text-slate-800"
          : "border-emerald-200 bg-emerald-50 text-emerald-950";
  const mainPenalty = [...summary.breakdown].sort((a, b) => b.penalty - a.penalty).slice(0, 4);
  const offline = summary.device_health.filter((device) => device.status === "offline").length;

  return (
    <section className="panel overflow-hidden">
      <div className="grid gap-0 xl:grid-cols-[0.8fr_1.2fr]">
        <div className={`relative border-b p-6 xl:border-b-0 xl:border-r ${statusTone}`}>
          <div className="pointer-events-none absolute -right-8 -top-8 h-32 w-32 rounded-full bg-white/40" />
          <p className="section-kicker">AgroEscudo Control Center</p>
          <div className="mt-4 flex items-end gap-4">
            <div>
              <p className="text-6xl font-black tracking-tight">{summary.score}</p>
              <p className="mt-1 text-xs font-black uppercase tracking-[0.18em] opacity-75">Indice operativo</p>
            </div>
            <div className="mb-2 rounded-2xl border border-white/60 bg-white/70 px-4 py-3 shadow-soft">
              <p className="text-sm font-black">{summary.status.replace("_", " ")}</p>
              <p className="text-xs opacity-70">{summary.formula_version}</p>
            </div>
          </div>
          <p className="mt-5 max-w-md text-sm leading-6 opacity-85">
            Puntaje calculado con alertas, horas fuera de rango, salud de dispositivos, bateria, mantenimiento y actividad operativa.
          </p>
          <div className="mt-5 grid grid-cols-3 gap-2">
            <MiniKpi label="Unidades" value={String(summary.kpis.storage_units ?? data.storageUnits.length)} />
            <MiniKpi label="Alertas" value={String(summary.kpis.active_alerts ?? data.activeAlerts.length)} />
            <MiniKpi label="Offline" value={String(offline)} />
          </div>
        </div>

        <div className="p-6">
          <div className="flex flex-wrap items-start justify-between gap-4">
            <div>
              <p className="section-kicker">Prioridades P0</p>
              <h2 className="section-title">Lo que puede afectar el piloto hoy</h2>
            </div>
            <button type="button" onClick={() => onNavigate("alerts")} className="btn-secondary">Ver alertas</button>
          </div>
          <div className="mt-4 grid gap-4 lg:grid-cols-2">
            <div className="rounded-2xl border border-slate-200 bg-white p-4 shadow-soft">
              <p className="text-xs font-black uppercase tracking-[0.16em] text-slate-500">Desglose del indice</p>
              <div className="mt-3 space-y-3">
                {mainPenalty.length ? mainPenalty.map((item) => (
                  <div key={item.key}>
                    <div className="mb-1 flex items-center justify-between text-xs font-bold text-slate-600">
                      <span>{item.label}</span>
                      <span>-{formatNumber(item.penalty)}</span>
                    </div>
                    <div className="h-2 overflow-hidden rounded-full bg-slate-100">
                      <div className="h-full rounded-full bg-emerald-700" style={{ width: `${Math.min(100, (item.penalty / item.cap) * 100)}%` }} />
                    </div>
                  </div>
                )) : <p className="text-sm text-slate-500">Sin penalizaciones activas.</p>}
              </div>
            </div>

            <div className="rounded-2xl border border-slate-200 bg-white p-4 shadow-soft">
              <p className="text-xs font-black uppercase tracking-[0.16em] text-slate-500">Sitios y sensores</p>
              <div className="mt-3 space-y-2">
                {summary.sites.slice(0, 3).map((site) => (
                  <div key={site.site_id} className="flex items-center justify-between gap-3 rounded-xl bg-slate-50 px-3 py-2">
                    <div>
                      <p className="text-sm font-black text-slate-900">{site.site_name}</p>
                      <p className="text-xs text-slate-500">{site.storage_units} unidad(es) · {site.active_alerts} alerta(s)</p>
                    </div>
                    <span className="rounded-full bg-white px-2.5 py-1 text-xs font-black text-emerald-800">{site.score}</span>
                  </div>
                ))}
                {summary.sites.length === 0 ? <p className="text-sm text-slate-500">Sin sitios para mostrar.</p> : null}
              </div>
            </div>
          </div>

          <div className="mt-4 grid gap-3 lg:grid-cols-3">
            {(summary.priorities.length ? summary.priorities.slice(0, 3) : [{ title: "Operacion sin prioridades criticas", detail: "Mantener monitoreo, bitacora y revision semanal.", severity: "normal", type: "system", storage_unit_id: null, alert_id: null }]).map((priority, index) => (
              <article key={`${priority.title}-${index}`} className="rounded-2xl border border-slate-200 bg-slate-50 p-4">
                <p className="text-[10px] font-black uppercase tracking-[0.16em] text-slate-500">{priority.severity}</p>
                <h3 className="mt-2 text-sm font-black text-slate-950">{priority.title}</h3>
                <p className="mt-2 text-sm leading-6 text-slate-600">{priority.detail}</p>
              </article>
            ))}
          </div>
        </div>
      </div>
    </section>
  );
}

function MiniKpi({ label, value }: { label: string; value: string }) {
  return (
    <div className="rounded-xl border border-white/60 bg-white/70 p-3 shadow-soft">
      <p className="text-lg font-black">{value}</p>
      <p className="text-[10px] font-black uppercase tracking-[0.14em] opacity-65">{label}</p>
    </div>
  );
}

function InsightsPanel({ data, onNavigate }: { data: AppData; onNavigate: (view: ViewKey) => void }) {
  const visibleInsights = data.insights.slice(0, 3);
  if (!visibleInsights.length) {
    return null;
  }
  return (
    <section className="panel p-5">
      <div className="flex flex-wrap items-start justify-between gap-4">
        <div>
          <p className="section-kicker">Analisis AgroEscudo</p>
          <h2 className="section-title">Lectura operativa por reglas</h2>
          <p className="section-subtitle">Resumen automatico basado en lecturas, alertas, bitacora y salud del dispositivo.</p>
        </div>
        <button type="button" onClick={() => onNavigate("history")} className="btn-secondary">Ver tendencias</button>
      </div>
      <div className="mt-4 grid gap-3 lg:grid-cols-3">
        {visibleInsights.map((insight) => (
          <article key={insight.storage_unit_id} className={`rounded-2xl border p-4 shadow-soft ${insightStyles(insight.status)}`}>
            <div className="flex items-start justify-between gap-3">
              <div>
                <p className="text-xs font-black uppercase tracking-[0.14em] opacity-75">{insight.storage_unit_name}</p>
                <h3 className="mt-2 text-lg font-black tracking-tight">{insightLabel(insight.status)}</h3>
              </div>
              <span className="rounded-full bg-white/70 px-2.5 py-1 text-[10px] font-black uppercase tracking-[0.12em]">
                {insightConfidenceLabel(insight.confidence)}
              </span>
            </div>
            <p className="mt-3 text-sm leading-6 opacity-85">{insight.summary}</p>
            {insight.recommendations[0] ? <p className="mt-3 text-sm font-black">Accion: {insight.recommendations[0]}</p> : null}
          </article>
        ))}
      </div>
    </section>
  );
}

function insightLabel(status: string) {
  if (status === "critical") return "Intervencion prioritaria";
  if (status === "attention") return "Seguimiento preventivo";
  if (status === "offline") return "Sensor sin continuidad";
  if (status === "insufficient_data") return "Datos insuficientes";
  return "Operacion estable";
}

function insightConfidenceLabel(confidence: StorageUnitInsight["confidence"]) {
  if (typeof confidence === "number" && Number.isFinite(confidence)) {
    return `${Math.round(Math.max(0, Math.min(1, confidence)) * 100)}%`;
  }
  if (confidence === "high") return "Confianza alta";
  if (confidence === "medium") return "Confianza media";
  return "Confianza baja";
}

function insightStyles(status: string) {
  if (status === "critical") return "border-red-200 bg-red-50 text-red-950";
  if (status === "attention") return "border-amber-200 bg-amber-50 text-amber-950";
  if (status === "offline" || status === "insufficient_data") return "border-slate-200 bg-slate-50 text-slate-800";
  return "border-emerald-200 bg-emerald-50 text-emerald-950";
}

function PriorityCard({
  title,
  value,
  detail,
  state
}: {
  title: string;
  value: string;
  detail: string;
  state: "critical" | "warning" | "offline" | "normal";
}) {
  return (
    <article className={`rounded-[18px] border p-5 shadow-soft ${stateStyles(state)}`}>
      <p className="text-[11px] font-black uppercase tracking-[0.15em] opacity-80">{title}</p>
      <p className="mt-2 text-2xl font-black tracking-tight">{value}</p>
      <p className="mt-1 text-sm font-semibold opacity-85">{detail}</p>
    </article>
  );
}

function DemoGuidedView({
  data,
  token,
  onNavigate,
  onRefresh
}: {
  data: AppData;
  token: string;
  onNavigate: (view: ViewKey) => void;
  onRefresh: () => Promise<void>;
}) {
  const [simulating, setSimulating] = useState(false);
  const [notice, setNotice] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const device = data.devices.find((item) => item.external_id === "SILO-001") || data.devices[0];
  const storageUnit = device ? data.storageUnits.find((item) => item.id === device.storage_unit_id) || null : null;
  const site = storageUnit ? data.sites.find((item) => item.id === storageUnit.site_id) : null;
  const pilot = storageUnit ? data.pilots.find((item) => item.storage_unit_id === storageUnit.id) : null;
  const readings = storageUnit ? data.readings.filter((item) => item.storage_unit_id === storageUnit.id) : [];
  const alerts = storageUnit ? data.alerts.filter((item) => item.storage_unit_id === storageUnit.id) : [];
  const logs = storageUnit ? data.logs.filter((item) => item.storage_unit_id === storageUnit.id) : [];
  const latest = readings[0];
  const criticalAlert = alerts.find((alert) => alert.severity === "critical" && alert.is_active);
  const correctiveLog = logs.find((log) => log.category === "corrective_action");

  async function simulateCriticalReading() {
    setSimulating(true);
    setNotice(null);
    setError(null);
    try {
      const result = await simulateCriticalDemoReading(token);
      setNotice(`Lectura critica registrada en ${result.device_external_id}. La evidencia operativa ya esta visible.`);
      await onRefresh();
    } catch (err) {
      setError(err instanceof Error ? err.message : "No se pudo ejecutar la simulacion.");
    } finally {
      setSimulating(false);
    }
  }

  return (
    <div className="space-y-5">
      <section className="relative overflow-hidden rounded-[22px] bg-gradient-to-br from-emeraldInk via-emeraldDeep to-emerald-800 p-6 text-white shadow-glow">
        <div className="pointer-events-none absolute inset-y-0 right-0 w-64 bg-[linear-gradient(135deg,transparent,rgba(212,154,0,0.12))]" />
        <div className="relative flex flex-wrap items-start justify-between gap-5">
          <div className="max-w-3xl">
            <div className="inline-flex items-center gap-2 rounded-full border border-amber-200/25 bg-white/10 px-3 py-1.5 text-[11px] font-black uppercase tracking-[0.16em] text-amber-100">
              <Presentation size={15} aria-hidden="true" />
              Solo admin · entorno controlado
            </div>
            <h2 className="mt-4 text-3xl font-black tracking-tight sm:text-4xl">Historia comercial en seis pasos</h2>
            <p className="mt-3 max-w-2xl text-sm leading-6 text-emerald-50/80">
              Presenta como AgroEscudo detecta riesgo postcosecha, coordina la respuesta tecnica y entrega evidencia lista para el cliente.
            </p>
          </div>
          <div className="rounded-2xl border border-white/15 bg-white/10 p-4 backdrop-blur">
            <div className="flex items-center gap-2 text-amber-100">
              <Clock3 size={18} aria-hidden="true" />
              <span className="text-sm font-black">Recorrido de 5 a 7 minutos</span>
            </div>
            <p className="mt-2 max-w-xs text-xs leading-5 text-emerald-50/70">Usa la simulacion solo durante una presentacion comercial local.</p>
          </div>
        </div>
      </section>

      {notice ? <div className="rounded-xl border border-emerald-200 bg-emerald-50 px-4 py-3 text-sm font-semibold text-emerald-900">{notice}</div> : null}
      {error ? <ErrorState message={error} onRetry={simulateCriticalReading} /> : null}

      <section className="panel overflow-hidden">
        <div className="flex flex-wrap items-center justify-between gap-3 border-b border-slate-200 bg-gradient-to-r from-white to-emerald-50/60 px-5 py-4">
          <div>
            <p className="section-kicker">Guion comercial</p>
            <h3 className="section-title">Del dato del silo a la evidencia operativa</h3>
            <p className="section-subtitle">{site?.name || "Centro de acopio"} / {storageUnit?.name || "Unidad monitoreada"}</p>
          </div>
          <StatusBadge status={criticalAlert ? "critical" : statusFromAlerts(data.activeAlerts)} />
        </div>
        <div className="grid gap-px bg-slate-200 md:grid-cols-2 xl:grid-cols-3">
          <DemoStep number="01" title="Sitio monitoreado" description={`${site?.name || "Sin sitio"}${site?.location ? ` · ${site.location}` : ""}`} detail="Contexto del cliente y almacenamiento bajo control." />
          <DemoStep number="02" title="Entrar al silo" description={storageUnit?.name || "Sin unidad asignada"} detail={`${storageUnit?.capacity_tons || 0} t de capacidad · nodo ${device?.external_id || "sin asignar"}.`} />
          <DemoStep number="03" title="Revisar ultima lectura" description={latest ? `${formatNumber(latest.grain_temperature, " C")} · ${formatNumber(latest.ambient_humidity, "%")}` : "Sin lecturas"} detail={latest ? formatDateTime(latest.timestamp) : "Simula una lectura para comenzar."} />
          <DemoStep number="04" title="Ver alerta critica" description={criticalAlert?.title || "Aun sin alerta critica activa"} detail={criticalAlert ? "La condicion fuera de rango queda registrada automaticamente." : "Ejecuta la simulacion para generar evidencia."} />
          <DemoStep number="05" title="Registrar accion" description={correctiveLog?.action_taken || "Accion correctiva pendiente"} detail={correctiveLog ? `Registrado por ${correctiveLog.operator_name}.` : "El tecnico documenta inspeccion, aireacion o mantenimiento."} />
          <DemoStep number="06" title="Descargar reporte PDF" description={pilot?.status ? pilotStatusLabel(pilot.status) : "Reporte semanal disponible"} detail="El cliente recibe trazabilidad, metricas y recomendaciones." />
        </div>
      </section>

      <section className="panel p-5">
        <div className="flex flex-wrap items-start justify-between gap-4">
          <div>
            <p className="section-kicker">Acciones de presentacion</p>
            <h3 className="section-title">Ejecuta el recorrido con un clic por momento</h3>
            <p className="section-subtitle">La lectura simulada se guarda como evidencia del piloto en el nodo SILO-001.</p>
          </div>
          <span className="rounded-full border border-amber-200 bg-amber-50 px-3 py-1 text-[10px] font-black uppercase tracking-[0.14em] text-amber-800">No usar en produccion</span>
        </div>
        <div className="mt-5 grid gap-3 sm:grid-cols-2 xl:grid-cols-4">
          <button type="button" onClick={simulateCriticalReading} disabled={simulating} className="btn-primary justify-center">
            <PlayCircle className="mr-2" size={17} aria-hidden="true" />
            {simulating ? "Simulando..." : "Simular lectura critica"}
          </button>
          <button type="button" onClick={() => onNavigate("alerts")} className="btn-secondary justify-center">
            <Eye className="mr-2" size={17} aria-hidden="true" />
            Ver alerta
          </button>
          <button type="button" onClick={() => onNavigate("logs")} className="btn-secondary justify-center">
            <ClipboardList className="mr-2" size={17} aria-hidden="true" />
            Registrar accion correctiva
          </button>
          <ReportDownloadButton
            token={token}
            storageUnit={storageUnit}
            device={device}
            readings={readings}
            alerts={alerts}
            logs={logs}
            compact
            className="w-full justify-center"
          />
        </div>
      </section>

      <section className="grid gap-4 md:grid-cols-3">
        <DemoEvidence icon={Radio} label="Lecturas del silo" value={readings.length.toString()} detail="Serie historica disponible para graficas." />
        <DemoEvidence icon={AlertTriangle} label="Alertas registradas" value={alerts.length.toString()} detail="Eventos trazables del periodo." />
        <DemoEvidence icon={FileText} label="Acciones documentadas" value={logs.length.toString()} detail="Bitacora operativa lista para reporte." />
      </section>
    </div>
  );
}

function DemoStep({ number, title, description, detail }: { number: string; title: string; description: string; detail: string }) {
  return (
    <article className="min-h-[176px] bg-white p-5">
      <p className="text-xs font-black tracking-[0.14em] text-amber-700">PASO {number}</p>
      <h4 className="mt-3 text-lg font-black tracking-tight text-slate-950">{title}</h4>
      <p className="mt-3 text-sm font-bold leading-5 text-emeraldDeep">{description}</p>
      <p className="mt-2 text-xs leading-5 text-slate-500">{detail}</p>
    </article>
  );
}

function DemoEvidence({ icon: Icon, label, value, detail }: { icon: LucideIcon; label: string; value: string; detail: string }) {
  return (
    <article className="panel flex items-start gap-4 p-4">
      <div className="flex h-10 w-10 shrink-0 items-center justify-center rounded-xl bg-emerald-50 text-emeraldDeep">
        <Icon size={18} aria-hidden="true" />
      </div>
      <div>
        <p className="text-xs font-bold uppercase tracking-[0.12em] text-slate-500">{label}</p>
        <p className="mt-1 text-2xl font-black tracking-tight text-slate-950">{value}</p>
        <p className="mt-1 text-xs leading-5 text-slate-500">{detail}</p>
      </div>
    </article>
  );
}

function pilotStatusLabel(status: string) {
  const labels: Record<string, string> = {
    "pendiente de instalacion": "Pendiente de instalacion",
    instalado: "Instalado",
    "en monitoreo": "En monitoreo",
    "con alerta activa": "Con alerta activa",
    "reporte generado": "Reporte generado",
    "listo para evaluacion": "Listo para evaluacion"
  };
  return labels[status] || status;
}

function pilotStatusClass(status: string) {
  if (status === "con alerta activa") return "border-red-200 bg-red-50 text-red-800";
  if (status === "pendiente de instalacion") return "border-amber-200 bg-amber-50 text-amber-800";
  if (status === "listo para evaluacion") return "border-emerald-200 bg-emerald-100 text-emerald-900";
  return "border-emerald-100 bg-emerald-50 text-emerald-800";
}

function PilotStatusBadge({ status }: { status: string }) {
  return (
    <span className={`inline-flex rounded-full border px-2.5 py-1 text-[10px] font-black uppercase tracking-[0.12em] ${pilotStatusClass(status)}`}>
      {pilotStatusLabel(status)}
    </span>
  );
}

function PilotOverview({ pilots, role, onNavigate }: { pilots: Pilot[]; role: UserRole; onNavigate: (view: ViewKey) => void }) {
  return (
    <section className="panel overflow-hidden">
      <div className="flex flex-wrap items-center justify-between gap-3 border-b border-slate-200 bg-gradient-to-r from-white to-emerald-50/60 px-5 py-4">
        <div>
          <p className="section-kicker">Implementacion en campo</p>
          <h2 className="section-title">{role === "client" ? "Estado de tu piloto" : "Estado de pilotos activos"}</h2>
          <p className="section-subtitle">Seguimiento operativo desde instalacion hasta evaluacion comercial.</p>
        </div>
        {role === "admin" ? (
          <button type="button" onClick={() => onNavigate("pilots")} className="btn-secondary">
            <Rocket className="mr-2" size={16} aria-hidden="true" />
            Gestionar pilotos
          </button>
        ) : null}
      </div>
      {pilots.length ? (
        <div className="grid gap-4 p-5 xl:grid-cols-3">
          {pilots.slice(0, 3).map((pilot) => (
            <article key={pilot.storage_unit_id} className="rounded-2xl border border-slate-200 bg-white p-4 shadow-soft">
              <div className="flex items-start justify-between gap-3">
                <div>
                  <p className="text-xs font-black uppercase tracking-[0.12em] text-emerald-700">{pilot.company_name}</p>
                  <h3 className="mt-1 text-lg font-black tracking-tight text-slate-950">{pilot.storage_unit_name}</h3>
                  <p className="mt-1 text-sm text-slate-500">{pilot.site_name}</p>
                </div>
                <PilotStatusBadge status={pilot.status} />
              </div>
              <div className="mt-4 grid grid-cols-3 gap-2 border-t border-slate-100 pt-4 text-center">
                <PilotMiniMetric label="Dias" value={String(pilot.days_monitored)} />
                <PilotMiniMetric label="Lecturas" value={String(pilot.reading_count)} />
                <PilotMiniMetric label="Alertas" value={String(pilot.active_alerts)} />
              </div>
              <div className="mt-3 flex items-center justify-between gap-2 text-xs text-slate-500">
                <span>{pilot.device_external_id || "Sin dispositivo"}</span>
                <span>{pilot.technician_name || "Tecnico pendiente"}</span>
              </div>
            </article>
          ))}
        </div>
      ) : (
        <div className="p-5"><EmptyState title="Sin pilotos configurados" message="El alta comercial crea cliente, sitio, unidad y dispositivo en un solo flujo." /></div>
      )}
    </section>
  );
}

function PilotMiniMetric({ label, value }: { label: string; value: string }) {
  return (
    <div className="rounded-xl bg-slate-50 px-2 py-2.5">
      <p className="text-base font-black text-slate-950">{value}</p>
      <p className="mt-0.5 text-[10px] font-bold uppercase tracking-[0.1em] text-slate-500">{label}</p>
    </div>
  );
}

function PilotsView({ data, token, onChanged }: { data: AppData; token: string; onChanged: () => void }) {
  const technicians = data.users.filter((user) => user.role === "technician");
  const [form, setForm] = useState({
    company_name: "",
    company_tax_id: "",
    site_name: "",
    site_location: "",
    storage_unit_name: "",
    storage_unit_type: "silo",
    capacity_tons: "",
    device_external_id: "",
    device_name: "",
    device_token: "",
    technician_user_id: technicians[0]?.id || 0,
    client_email: "",
    client_full_name: "",
    client_password: ""
  });
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [notice, setNotice] = useState<string | null>(null);

  function update(field: keyof typeof form, value: string | number) {
    setForm((current) => ({ ...current, [field]: value }));
  }

  async function submit(event: FormEvent) {
    event.preventDefault();
    if (!isStrongPassword(form.client_password)) {
      setError("El password inicial debe tener minimo 8 caracteres, una letra y un numero.");
      return;
    }
    setSaving(true);
    setError(null);
    setNotice(null);
    try {
      const pilot = await createPilot(token, {
        ...form,
        company_tax_id: form.company_tax_id || null,
        capacity_tons: form.capacity_tons ? Number(form.capacity_tons) : null,
        technician_user_id: Number(form.technician_user_id)
      });
      setNotice(`Piloto ${pilot.storage_unit_name} preparado correctamente.`);
      setForm((current) => ({
        ...current,
        company_name: "",
        company_tax_id: "",
        site_name: "",
        site_location: "",
        storage_unit_name: "",
        capacity_tons: "",
        device_external_id: "",
        device_name: "",
        device_token: "",
        client_email: "",
        client_full_name: "",
        client_password: ""
      }));
      onChanged();
    } catch (err) {
      setError(err instanceof Error ? err.message : "No se pudo preparar el piloto.");
    } finally {
      setSaving(false);
    }
  }

  return (
    <div className="space-y-5">
      <section className="overflow-hidden rounded-[20px] border border-emerald-900/10 bg-gradient-to-br from-emeraldInk via-emeraldDeep to-emerald-800 p-6 text-white shadow-glow">
        <p className="text-[11px] font-black uppercase tracking-[0.18em] text-amber-200">Alta comercial guiada</p>
        <h2 className="mt-2 text-3xl font-black tracking-tight">Prepara un piloto operativo completo.</h2>
        <p className="mt-2 max-w-3xl text-sm leading-6 text-emerald-50/80">Crea cliente, sitio, unidad monitoreada, nodo IoT y responsables sin fragmentar el proceso de implementacion.</p>
      </section>
      <div className="grid gap-5 xl:grid-cols-[520px_1fr]">
        <section className="panel p-5">
          <p className="section-kicker">Nuevo piloto</p>
          <h2 className="section-title">Configuracion inicial</h2>
          <p className="section-subtitle">Completa los datos esenciales para dejar el sitio listo para instalacion.</p>
          <form onSubmit={submit} className="mt-5 space-y-5">
            <PilotFormGroup title="Cliente y sitio">
              <Field label="Empresa / cliente"><input required value={form.company_name} onChange={(event) => update("company_name", event.target.value)} className="input" /></Field>
              <Field label="NIT opcional"><input value={form.company_tax_id} onChange={(event) => update("company_tax_id", event.target.value)} className="input" /></Field>
              <Field label="Sitio"><input required value={form.site_name} onChange={(event) => update("site_name", event.target.value)} className="input" /></Field>
              <Field label="Ubicacion"><input required value={form.site_location} onChange={(event) => update("site_location", event.target.value)} className="input" /></Field>
            </PilotFormGroup>
            <PilotFormGroup title="Activo y dispositivo">
              <Field label="Silo / galpon"><input required value={form.storage_unit_name} onChange={(event) => update("storage_unit_name", event.target.value)} className="input" /></Field>
              <Field label="Tipo de unidad">
                <select value={form.storage_unit_type} onChange={(event) => update("storage_unit_type", event.target.value)} className="input">
                  <option value="silo">Silo</option>
                  <option value="galpon">Galpon</option>
                  <option value="ambiente">Ambiente monitoreado</option>
                </select>
              </Field>
              <Field label="Capacidad toneladas"><input type="number" min="0" step="0.1" value={form.capacity_tons} onChange={(event) => update("capacity_tons", event.target.value)} className="input" /></Field>
              <Field label="ID dispositivo"><input required value={form.device_external_id} onChange={(event) => update("device_external_id", event.target.value)} className="input" /></Field>
              <Field label="Nombre dispositivo"><input required value={form.device_name} onChange={(event) => update("device_name", event.target.value)} className="input" /></Field>
              <Field label="Token dispositivo"><input required value={form.device_token} onChange={(event) => update("device_token", event.target.value)} className="input" /></Field>
            </PilotFormGroup>
            <PilotFormGroup title="Responsables">
              <Field label="Tecnico AgroEscudo">
                <select required value={form.technician_user_id} onChange={(event) => update("technician_user_id", Number(event.target.value))} className="input">
                  {technicians.map((technician) => <option key={technician.id} value={technician.id}>{technician.full_name}</option>)}
                </select>
              </Field>
              <Field label="Nombre usuario cliente"><input required value={form.client_full_name} onChange={(event) => update("client_full_name", event.target.value)} className="input" /></Field>
              <Field label="Email usuario cliente"><input required type="email" value={form.client_email} onChange={(event) => update("client_email", event.target.value)} className="input" /></Field>
              <Field label="Password inicial"><input required type="password" minLength={8} value={form.client_password} onChange={(event) => update("client_password", event.target.value)} className="input" placeholder="Minimo 8, letra y numero" /></Field>
            </PilotFormGroup>
            {error ? <p className="rounded-lg border border-red-200 bg-red-50 p-3 text-sm font-medium text-red-800">{error}</p> : null}
            {notice ? <p className="rounded-lg border border-emerald-200 bg-emerald-50 p-3 text-sm font-medium text-emerald-800">{notice}</p> : null}
            <button type="submit" disabled={saving || !technicians.length} className="btn-primary w-full">
              <Rocket className="mr-2" size={16} aria-hidden="true" />
              {saving ? "Preparando piloto..." : "Crear y asignar piloto"}
            </button>
          </form>
        </section>
        <section className="panel p-5">
          <p className="section-kicker">Cartera operativa</p>
          <h2 className="section-title">Pilotos configurados</h2>
          <p className="section-subtitle">Estado, responsables y evidencia generada en campo.</p>
          <div className="mt-5 space-y-3">
            {data.pilots.length ? data.pilots.map((pilot) => <PilotDetailCard key={pilot.storage_unit_id} pilot={pilot} token={token} onChanged={onChanged} />) : <EmptyState title="Sin pilotos" message="Completa el formulario para preparar la primera implementacion." />}
          </div>
        </section>
      </div>
    </div>
  );
}

function PilotFormGroup({ title, children }: { title: string; children: ReactNode }) {
  return (
    <fieldset className="grid gap-3 rounded-xl border border-slate-200 bg-slate-50/70 p-4 sm:grid-cols-2">
      <legend className="px-2 text-xs font-black uppercase tracking-[0.14em] text-emerald-800">{title}</legend>
      {children}
    </fieldset>
  );
}

function PilotDetailCard({ pilot, token, onChanged }: { pilot: Pilot; token: string; onChanged: () => void }) {
  const [clearing, setClearing] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function clearOperationalData() {
    const confirmed = window.confirm(
      `Se eliminaran lecturas, alertas y registros operativos de ${pilot.storage_unit_name}. La empresa, el sitio y el dispositivo se conservaran.`
    );
    if (!confirmed) return;
    setClearing(true);
    setError(null);
    try {
      await deletePilotOperationalData(token, pilot.storage_unit_id);
      onChanged();
    } catch (err) {
      setError(err instanceof Error ? err.message : "No se pudieron borrar los datos operativos.");
    } finally {
      setClearing(false);
    }
  }

  return (
    <article className="rounded-2xl border border-slate-200 bg-white p-4 shadow-soft">
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div>
          <p className="text-xs font-black uppercase tracking-[0.12em] text-emerald-700">{pilot.company_name}</p>
          <h3 className="mt-1 text-lg font-black tracking-tight text-slate-950">{pilot.storage_unit_name}</h3>
          <p className="mt-1 text-sm text-slate-500">{pilot.site_name} / {pilot.site_location || "Ubicacion pendiente"}</p>
        </div>
        <PilotStatusBadge status={pilot.status} />
      </div>
      <div className="mt-4 grid gap-2 sm:grid-cols-3 lg:grid-cols-6">
        <PilotMiniMetric label="Dias" value={String(pilot.days_monitored)} />
        <PilotMiniMetric label="Lecturas" value={String(pilot.reading_count)} />
        <PilotMiniMetric label="Alertas" value={String(pilot.alerts_generated)} />
        <PilotMiniMetric label="Resueltas" value={String(pilot.alerts_resolved)} />
        <PilotMiniMetric label="Acciones" value={String(pilot.actions_registered)} />
        <PilotMiniMetric label="Fuera rango" value={`${pilot.approximate_hours_out_of_range} h`} />
      </div>
      <div className="mt-4 grid gap-2 border-t border-slate-100 pt-3 text-xs text-slate-600 sm:grid-cols-3">
        <span><b>Device:</b> {pilot.device_external_id || "Pendiente"}</span>
        <span><b>Tecnico:</b> {pilot.technician_name || "Pendiente"}</span>
        <span><b>Cliente:</b> {pilot.client_name || "Pendiente"}</span>
      </div>
      <div className="mt-4 flex flex-wrap items-center justify-between gap-3 border-t border-slate-100 pt-3">
        <p className="text-xs leading-5 text-slate-500">Limpia la evidencia del piloto sin eliminar su infraestructura.</p>
        <button type="button" onClick={clearOperationalData} disabled={clearing} className="inline-flex items-center rounded-lg border border-red-200 bg-white px-3 py-2 text-xs font-black text-red-700 transition hover:bg-red-50 disabled:cursor-not-allowed disabled:opacity-60">
          <Trash2 className="mr-2" size={15} aria-hidden="true" />
          {clearing ? "Borrando..." : "Borrar datos operativos"}
        </button>
      </div>
      {error ? <p className="mt-3 rounded-lg border border-red-200 bg-red-50 p-3 text-xs font-semibold text-red-800">{error}</p> : null}
    </article>
  );
}

type CommandMode = "sensor" | "maintenance" | "help" | "education";

function sensorInsight(data: AppData) {
  const priorityInsight = data.insights
    .slice()
    .sort((a, b) => {
      const weight: Record<string, number> = { critical: 4, attention: 3, offline: 2, insufficient_data: 1, normal: 0 };
      return (weight[b.status] ?? 0) - (weight[a.status] ?? 0);
    })[0];
  if (priorityInsight?.summary) {
    const firstRecommendation = priorityInsight.recommendations[0];
    return firstRecommendation ? `${priorityInsight.summary} Accion sugerida: ${firstRecommendation}` : priorityInsight.summary;
  }
  const latest = data.readings[0];
  const critical = data.activeAlerts.filter((alert) => alert.severity === "critical");
  if (critical.length) {
    return `Atención prioritaria: ${critical.length} alerta(s) crítica(s) activa(s). Revisa el silo afectado, registra acción correctiva y valida ventilación o temperatura del grano.`;
  }
  if (!latest) {
    return "Todavía no hay lecturas recientes. Conecta un dispositivo o envía una lectura para activar el análisis operativo.";
  }
  if (latest.battery_voltage < 3.5) {
    return "El sensor reporta batería baja. Prioriza mantenimiento del nodo IoT antes de depender del monitoreo continuo.";
  }
  if (latest.ambient_humidity > 75 || latest.grain_temperature > 32) {
    return "El sensor muestra condiciones preventivas. Conviene revisar aireación, humedad ambiental y evolución térmica durante las próximas horas.";
  }
  return "Lectura estable con los datos actuales. Mantener monitoreo, bitácora semanal y revisión de umbrales por campaña.";
}

function CommandCenter({
  data,
  onNavigate,
  canCreateLog
}: {
  data: AppData;
  onNavigate: (view: ViewKey) => void;
  canCreateLog: boolean;
}) {
  const [mode, setMode] = useState<CommandMode>("sensor");
  const [openMode, setOpenMode] = useState<CommandMode | null>(null);
  const content: Record<CommandMode, { title: string; body: string; action: string; icon: LucideIcon; tone: string }> = {
    sensor: {
      title: "Consulta operativa del sensor",
      body: sensorInsight(data),
      action: "Abrir consulta",
      icon: Bot,
      tone: "from-emerald-900 to-emerald-700"
    },
    maintenance: {
      title: "Mantenimiento operativo",
      body: "Checklist técnico para revisar alimentación, batería, conexión, ubicación física del sensor y evidencia de visita.",
      action: "Ver checklist",
      icon: Wrench,
      tone: "from-slate-900 to-emerald-900"
    },
    help: {
      title: "Ayuda AgroEscudo",
      body: "Guía rápida para actuar ante alerta crítica, falta de lecturas, batería baja o dudas del piloto.",
      action: "Ver ayuda",
      icon: Headphones,
      tone: "from-emerald-800 to-slate-900"
    },
    education: {
      title: "Educación postcosecha",
      body: "Microguía operativa para interpretar temperatura, humedad, estado crítico y trazabilidad de bitácora.",
      action: "Abrir guía",
      icon: GraduationCap,
      tone: "from-amber-700 to-emerald-900"
    }
  };
  const current = content[mode];

  function openCommand(key: CommandMode) {
    setMode(key);
    setOpenMode(key);
  }

  return (
    <>
      <section className={`overflow-hidden rounded-[22px] bg-gradient-to-br ${current.tone} p-5 text-white shadow-glow`}>
        <div className="grid gap-5 xl:grid-cols-[1fr_1.1fr]">
          <div>
            <div className="inline-flex items-center gap-2 rounded-full border border-white/15 bg-white/10 px-3 py-1.5 text-xs font-black uppercase tracking-[0.16em] text-emerald-50">
              <Sparkles size={14} aria-hidden="true" />
              Asistente operativo
            </div>
            <p className="mt-3 text-xs font-semibold text-emerald-50/70">Basado en reglas del sistema y datos reales del sensor.</p>
            <h2 className="mt-3 text-3xl font-black tracking-tight">{current.title}</h2>
            <p className="mt-3 max-w-2xl text-sm leading-6 text-white/80">{current.body}</p>
            <button type="button" onClick={() => openCommand(mode)} className="mt-5 rounded-xl border border-white/20 bg-white px-4 py-2.5 text-sm font-black text-emeraldDeep shadow-soft transition hover:-translate-y-0.5 hover:bg-emerald-50 focus:outline-none focus-visible:ring-2 focus-visible:ring-white/80">
              {current.action}
            </button>
          </div>
          <div className="grid gap-3 sm:grid-cols-2">
            {([
              ["sensor", "Consulta sensor", Bot],
              ["maintenance", "Mantenimiento", Wrench],
              ["help", "Ayuda", Headphones],
              ["education", "Educación", GraduationCap]
            ] as Array<[CommandMode, string, LucideIcon]>).map(([key, label, Icon]) => (
              <button
                key={key}
                type="button"
                onClick={() => openCommand(key)}
                className={`group cursor-pointer rounded-2xl border p-4 text-left transition hover:-translate-y-0.5 focus:outline-none focus-visible:ring-2 focus-visible:ring-white/80 ${
                  mode === key
                    ? "border-white/70 bg-white text-emeraldDeep shadow-panel"
                    : "border-white/10 bg-white/10 text-white hover:bg-white/15"
                }`}
              >
                <div className={`flex h-10 w-10 items-center justify-center rounded-xl ${mode === key ? "bg-emerald-50 text-emeraldDeep" : "bg-white/10 text-white"}`}>
                  <Icon size={19} aria-hidden="true" />
                </div>
                <p className="mt-3 text-sm font-black">{label}</p>
                <p className={`mt-1 text-xs leading-5 ${mode === key ? "text-slate-600" : "text-white/65"}`}>
                  {key === "sensor" ? "Riesgo actual y recomendación." : key === "maintenance" ? "Checklist y registro." : key === "help" ? "Soporte ante incidentes." : "Guía operativa breve."}
                </p>
              </button>
            ))}
          </div>
        </div>
      </section>
      {openMode ? <CommandModal mode={openMode} data={data} onClose={() => setOpenMode(null)} onNavigate={onNavigate} canCreateLog={canCreateLog} /> : null}
    </>
  );
}

function CommandModal({
  mode,
  data,
  onClose,
  onNavigate,
  canCreateLog
}: {
  mode: CommandMode;
  data: AppData;
  onClose: () => void;
  onNavigate: (view: ViewKey) => void;
  canCreateLog: boolean;
}) {
  const latest = data.readings[0];
  const maxTemperature = data.readings.length ? Math.max(...data.readings.map((reading) => reading.grain_temperature)) : null;
  const maxHumidity = data.readings.length ? Math.max(...data.readings.map((reading) => reading.ambient_humidity)) : null;
  const criticalCount = data.activeAlerts.filter((alert) => alert.severity === "critical").length;
  const warningCount = data.activeAlerts.filter((alert) => alert.severity === "warning").length;
  const title = mode === "sensor"
    ? "Consulta operativa del sensor"
    : mode === "maintenance"
      ? "Checklist de mantenimiento"
      : mode === "help"
        ? "Ayuda operativa AgroEscudo"
        : "Educación postcosecha";

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-emeraldInk/75 p-4 backdrop-blur-sm" role="dialog" aria-modal="true" aria-label={title}>
      <div className="w-full max-w-2xl overflow-hidden rounded-[22px] border border-white/20 bg-white shadow-glow">
        <div className="flex items-start justify-between gap-4 border-b border-slate-200 bg-gradient-to-br from-emerald-50 to-white p-5">
          <div>
            <p className="section-kicker">Asistente operativo</p>
            <h3 className="mt-1 text-2xl font-black tracking-tight text-slate-950">{title}</h3>
            <p className="mt-2 text-sm leading-6 text-slate-600">Basado en reglas del sistema, alertas activas y lecturas cargadas.</p>
          </div>
          <button type="button" onClick={onClose} className="rounded-xl border border-slate-200 bg-white p-2 text-slate-600 shadow-soft transition hover:bg-slate-50 focus:outline-none focus-visible:ring-2 focus-visible:ring-emerald-700">
            <X size={18} aria-hidden="true" />
          </button>
        </div>
        <div className="space-y-4 p-5">
          {mode === "sensor" ? (
            <>
              <div className="grid gap-3 sm:grid-cols-2">
                <ReportItem label="Estado actual" value={criticalCount ? "Crítico" : warningCount ? "Alerta" : "Normal"} />
                <ReportItem label="Alertas activas" value={String(data.activeAlerts.length)} />
                <ReportItem label="Temp. máxima" value={maxTemperature === null ? "Sin dato" : formatNumber(maxTemperature, " C")} />
                <ReportItem label="Humedad máxima" value={maxHumidity === null ? "Sin dato" : formatNumber(maxHumidity, "%")} />
              </div>
              <div className="rounded-2xl border border-emerald-100 bg-emerald-50 p-4">
                <p className="text-xs font-black uppercase tracking-[0.14em] text-emerald-800">Recomendación inmediata</p>
                <p className="mt-2 text-sm leading-6 text-slate-700">{sensorInsight(data)}</p>
                <p className="mt-2 text-xs font-semibold text-slate-500">Última lectura: {latest ? formatDateTime(latest.timestamp) : "Sin lecturas recientes"}</p>
              </div>
            </>
          ) : null}
          {mode === "maintenance" ? (
            <>
              <div className="grid gap-2 sm:grid-cols-2">
                {[
                  "Revisar alimentación del nodo",
                  "Verificar batería",
                  "Revisar conexión y señal",
                  "Inspeccionar sensor de temperatura",
                  "Validar ubicación física del sensor",
                  "Limpiar caja si hay polvo o humedad",
                  "Registrar visita técnica"
                ].map((item) => (
                  <div key={item} className="flex items-center gap-2 rounded-xl border border-slate-200 bg-slate-50 p-3 text-sm font-semibold text-slate-700">
                    <ClipboardList size={16} className="text-emerald-700" aria-hidden="true" />
                    {item}
                  </div>
                ))}
              </div>
              {canCreateLog ? (
                <button type="button" onClick={() => { onClose(); onNavigate("logs"); }} className="btn-primary">
                  Registrar mantenimiento
                </button>
              ) : (
                <div className="rounded-xl border border-slate-200 bg-slate-50 p-3 text-sm font-semibold text-slate-600">
                  Tu rol puede revisar el checklist, pero el registro tecnico lo realiza AgroEscudo.
                </div>
              )}
            </>
          ) : null}
          {mode === "help" ? (
            <div className="space-y-3">
              {[
                ["Ante alerta crítica", "Inspeccionar físicamente el silo, activar aireación si corresponde y registrar acción correctiva."],
                ["Si no llegan lecturas", "Validar energía, señal, token del dispositivo y disponibilidad del backend."],
                ["Si hay batería baja", "Programar visita técnica y reemplazo o recarga del nodo IoT."],
                ["Soporte", "hola@agroescudo.com / documentar sitio, silo, device y condición observada."]
              ].map(([label, body]) => (
                <div key={label} className="rounded-xl border border-slate-200 bg-white p-4 shadow-soft">
                  <p className="font-black text-slate-950">{label}</p>
                  <p className="mt-1 text-sm leading-6 text-slate-600">{body}</p>
                </div>
              ))}
            </div>
          ) : null}
          {mode === "education" ? (
            <div className="grid gap-3">
              {[
                ["Temperatura alta", "Puede indicar acumulación térmica o foco de deterioro. Conviene inspeccionar el punto monitoreado."],
                ["Humedad alta", "Aumenta el riesgo de condensación, hongos y pérdida de calidad. Revisar ventilación y aireación."],
                ["Bitácora", "Convierte acciones operativas en evidencia trazable para seguimiento técnico y reportes."],
                ["Estado crítico", "Requiere intervención prioritaria y documentación de la acción correctiva."]
              ].map(([label, body]) => (
                <div key={label} className="rounded-xl border border-slate-200 bg-slate-50 p-4">
                  <p className="font-black text-emeraldDeep">{label}</p>
                  <p className="mt-1 text-sm leading-6 text-slate-600">{body}</p>
                </div>
              ))}
            </div>
          ) : null}
        </div>
      </div>
    </div>
  );
}

function SitesView({
  data,
  token,
  onOpenLogs,
  canCreateLog
}: {
  data: AppData;
  token: string;
  onOpenLogs: () => void;
  canCreateLog: boolean;
}) {
  const [selectedId, setSelectedId] = useState<number | null>(data.storageUnits[0]?.id ?? null);
  const selected = data.storageUnits.find((unit) => unit.id === selectedId) || data.storageUnits[0] || null;

  return (
    <div className="space-y-6">
      <section className="panel overflow-hidden">
        <div className="border-b border-slate-200/80 p-5">
          <p className="section-kicker">Red operativa</p>
          <h2 className="section-title">Sitios</h2>
          <p className="section-subtitle">Centros de acopio, plantas y almacenes que alimentan el monitoreo AgroEscudo.</p>
        </div>
        {data.sites.length ? (
          <div className="overflow-x-auto">
            <table className="min-w-full divide-y divide-slate-200 text-sm">
              <thead className="table-head">
                <tr>
                  <th className="px-4 py-3">Sitio</th>
                  <th className="px-4 py-3">Empresa</th>
                  <th className="px-4 py-3">Ubicacion</th>
                  <th className="px-4 py-3">Estado</th>
                  <th className="px-4 py-3">Unidades</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100">
                {data.sites.map((site) => {
                  const siteAlerts = data.activeAlerts.filter((alert) => alert.site_id === site.id);
                  const units = data.storageUnits.filter((unit) => unit.site_id === site.id);
                  return (
                    <tr key={site.id} className="transition hover:bg-slate-50">
                      <td className="px-4 py-3 font-semibold text-slate-950">{site.name}</td>
                      <td className="px-4 py-3 text-slate-700">{data.companies.find((company) => company.id === site.company_id)?.name || "Sin empresa"}</td>
                      <td className="px-4 py-3 text-slate-700">{site.location || "Sin ubicacion"}</td>
                      <td className="px-4 py-3"><StatusBadge status={statusFromAlerts(siteAlerts)} /></td>
                      <td className="px-4 py-3 text-slate-700">{units.length}</td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        ) : (
          <div className="p-4"><EmptyState title="Sin sitios" message="Crea sitios desde la API para iniciar el monitoreo." /></div>
        )}
      </section>
      <StorageUnitDetail data={data} token={token} selected={selected} onSelect={setSelectedId} onOpenLogs={onOpenLogs} canCreateLog={canCreateLog} />
    </div>
  );
}

function StorageUnitDetail({
  data,
  token,
  selected,
  onSelect,
  onOpenLogs,
  canCreateLog
}: {
  data: AppData;
  token: string;
  selected: StorageUnit | null;
  onSelect: (id: number) => void;
  onOpenLogs: () => void;
  canCreateLog: boolean;
}) {
  if (!selected) {
    return <EmptyState title="Sin silos o galpones" message="No hay storage units disponibles para inspeccionar." />;
  }

  const site = data.sites.find((item) => item.id === selected.site_id);
  const device = data.devices.find((item) => item.storage_unit_id === selected.id);
  const readings = data.readings.filter((reading) => reading.storage_unit_id === selected.id);
  const latest = readings[0];
  const alerts = data.activeAlerts.filter((alert) => alert.storage_unit_id === selected.id);
  const logs = data.logs.filter((log) => log.storage_unit_id === selected.id).slice(0, 5);
  const unitStatus = statusFromAlerts(alerts);
  const insight = data.insights.find((item) => item.storage_unit_id === selected.id);

  return (
    <section className="space-y-5">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div>
          <p className="section-kicker">Centro del producto</p>
          <h2 className="section-title">Detalle de silo / galpon</h2>
          <p className="section-subtitle">Lectura rapida de riesgo, sensores, alertas y acciones operativas.</p>
        </div>
        <select value={selected.id} onChange={(event) => onSelect(Number(event.target.value))} className="input max-w-xs">
          {data.storageUnits.map((unit) => <option key={unit.id} value={unit.id}>{unit.name}</option>)}
        </select>
      </div>
      <div className="grid gap-5 xl:grid-cols-[1.15fr_0.85fr]">
        <div className={`relative overflow-hidden rounded-[18px] border p-5 shadow-panel ${
          unitStatus === "critical" ? "border-red-200 bg-red-50" : unitStatus === "warning" ? "border-amber-200 bg-amber-50" : "border-emerald-200 bg-white"
        }`}>
          <div className="pointer-events-none absolute right-0 top-0 h-28 w-28 rounded-bl-full bg-white/50" />
          <div className="relative flex flex-wrap items-start justify-between gap-3">
            <div>
              <p className="section-kicker">Unidad monitoreada</p>
              <h3 className="mt-1 text-2xl font-black tracking-tight text-slate-950">{selected.name}</h3>
              <p className="mt-1 text-sm text-slate-600">{site?.name || "Sin sitio"} / {device?.external_id || "Sin device"}</p>
            </div>
            <StatusBadge status={unitStatus} />
          </div>
          <div className="relative mt-4 grid gap-3 sm:grid-cols-2">
            <Metric icon={Thermometer} label="Temp. grano" value={formatNumber(latest?.grain_temperature, " C")} />
            <Metric icon={Thermometer} label="Temp. ambiente" value={formatNumber(latest?.ambient_temperature, " C")} />
            <Metric icon={Activity} label="Humedad" value={formatNumber(latest?.ambient_humidity, "%")} />
            <Metric icon={Battery} label="Bateria" value={formatNumber(latest?.battery_voltage, " V", 2)} />
            <Metric icon={Wifi} label="Senal" value={latest ? `${latest.signal_quality} dBm` : "Sin dato"} />
            <Metric icon={Radio} label="Ultima lectura" value={latest ? formatDateTime(latest.timestamp) : "Sin dato"} />
          </div>
          {insight ? (
            <div className={`relative mt-5 rounded-2xl border p-4 text-sm leading-6 shadow-soft ${insightStyles(insight.status)}`}>
              <p className="text-xs font-black uppercase tracking-[0.14em] opacity-75">Consulta operativa</p>
              <p className="mt-2 font-bold">{insight.summary}</p>
              {insight.recommendations[0] ? <p className="mt-2 font-black">Recomendacion: {insight.recommendations[0]}</p> : null}
            </div>
          ) : null}
          {canCreateLog ? (
            <div className="relative mt-5 flex flex-wrap gap-2">
              <button type="button" onClick={onOpenLogs} className="btn-primary">
                <ClipboardList className="mr-2" size={16} aria-hidden="true" />
                Registrar accion
              </button>
              <button type="button" onClick={onOpenLogs} className="btn-secondary border-emerald-200 bg-white text-emeraldDeep">
                <Wrench className="mr-2" size={16} aria-hidden="true" />
                Mantenimiento
              </button>
            </div>
          ) : (
            <div className="relative mt-5 rounded-xl border border-emerald-100 bg-white/80 p-3 text-sm font-semibold text-slate-600">
              Vista cliente: consulta estado, alertas, bitacora y reporte sin modificar operacion tecnica.
            </div>
          )}
          <div className="relative mt-3">
            <ReportDownloadButton
              token={token}
              storageUnit={selected}
              device={device}
              readings={readings}
              alerts={data.alerts.filter((alert) => alert.storage_unit_id === selected.id)}
              logs={data.logs.filter((log) => log.storage_unit_id === selected.id)}
              compact
              className="bg-white text-emeraldDeep hover:bg-emerald-50"
            />
          </div>
        </div>
        <div className="panel p-5">
          <div className="flex items-center justify-between gap-3">
            <div>
              <p className="section-kicker">Riesgo operativo</p>
              <h3 className="font-bold text-slate-950">Alertas activas de la unidad</h3>
            </div>
            <span className="rounded-full bg-slate-100 px-3 py-1 text-xs font-bold text-slate-600">{alerts.length} activa(s)</span>
          </div>
          <div className="mt-3 space-y-2">
            {alerts.length ? alerts.map((alert) => (
              <div key={alert.id} className={`rounded-xl border p-3 shadow-soft ${alert.severity === "critical" ? "border-red-200 bg-red-50" : "border-slate-200 bg-slate-50"}`}>
                <div className="flex items-center justify-between gap-3">
                  <p className="font-semibold text-slate-950">{alert.title}</p>
                  <StatusBadge status={alert.severity === "critical" ? "critical" : alert.severity === "warning" ? "warning" : "technical"} />
                </div>
                <p className="mt-1 text-sm text-slate-500">{alert.message}</p>
              </div>
            )) : <EmptyState title="Unidad sin alertas activas" message="No hay condiciones fuera de rango en este momento." />}
          </div>
        </div>
      </div>
      {readings.length ? (
        <div className="grid gap-4 xl:grid-cols-2">
          <ReadingChart title="Temperatura de grano" readings={readings} metric="grain_temperature" color="#047857" unit=" C" />
          <ReadingChart title="Temperatura ambiente" readings={readings} metric="ambient_temperature" color="#2563eb" unit=" C" />
          <ReadingChart title="Humedad ambiente" readings={readings} metric="ambient_humidity" color="#d97706" unit="%" />
          <ReadingChart title="Voltaje de bateria" readings={readings} metric="battery_voltage" color="#475569" unit=" V" threshold={3.5} />
        </div>
      ) : (
        <EmptyState title="Sin lecturas para graficar" message="Cuando el dispositivo envie datos, las curvas apareceran aqui." />
      )}
      <section className="panel p-5">
        <p className="section-kicker">Trazabilidad</p>
        <h3 className="font-bold text-slate-950">Bitacora reciente</h3>
        <div className="mt-3 space-y-2">
          {logs.length ? logs.map((log) => <LogRow key={log.id} log={log} />) : <EmptyState title="Sin acciones registradas" message="Registra acciones correctivas desde la seccion Bitacora." />}
        </div>
      </section>
    </section>
  );
}

function Metric({ icon: Icon, label, value }: { icon: LucideIcon; label: string; value: string }) {
  return (
    <div className="metric-tile">
      <div className="flex items-center gap-2 text-xs font-semibold uppercase tracking-wide text-slate-500">
        <Icon size={15} aria-hidden="true" />
        {label}
      </div>
      <p className="mt-2 text-lg font-black tracking-tight text-slate-950">{value}</p>
    </div>
  );
}

function AlertsView({
  data,
  onAcknowledge,
  onResolve,
  busyAlertId
}: {
  data: AppData;
  onAcknowledge?: (alert: Alert) => void;
  onResolve?: (alert: Alert) => void;
  busyAlertId: number | null;
}) {
  const [status, setStatus] = useState("all");
  const [severity, setSeverity] = useState("all");
  const alerts = data.alerts.filter((alert) => {
    const statusOk = status === "all" || (status === "active" ? alert.is_active : !alert.is_active);
    const severityOk = severity === "all" || alert.severity === severity;
    return statusOk && severityOk;
  });

  return (
    <section className="space-y-4">
      <div className="flex flex-wrap items-end justify-between gap-3">
        <div>
          <p className="section-kicker">Gestion operativa</p>
          <h2 className="section-title">Alertas</h2>
          <p className="section-subtitle">Prioriza condiciones criticas, acknowledge y resolucion sin perder trazabilidad.</p>
        </div>
        <div className="flex flex-wrap gap-2 rounded-xl border border-slate-200 bg-white p-2 shadow-soft">
          <select value={status} onChange={(event) => setStatus(event.target.value)} className="input w-auto">
            <option value="all">Todos los estados</option>
            <option value="active">Activas</option>
            <option value="resolved">Resueltas</option>
          </select>
          <select value={severity} onChange={(event) => setSeverity(event.target.value)} className="input w-auto">
            <option value="all">Todas las severidades</option>
            <option value="critical">Critical</option>
            <option value="warning">Warning</option>
            <option value="technical">Tecnica</option>
          </select>
        </div>
      </div>
      {alerts.length ? (
        <AlertTable alerts={alerts} devices={data.devices} storageUnits={data.storageUnits} onAcknowledge={onAcknowledge} onResolve={onResolve} busyAlertId={busyAlertId} />
      ) : (
        <EmptyState title="Sin alertas para el filtro" message="Ajusta los filtros o espera nuevas lecturas fuera de rango." />
      )}
    </section>
  );
}

function LogsView({
  data,
  token,
  onChanged,
  canCreateLog
}: {
  data: AppData;
  token: string;
  onChanged: () => void;
  canCreateLog: boolean;
}) {
  const [storageUnitId, setStorageUnitId] = useState(data.storageUnits[0]?.id ?? 0);
  const [alertId, setAlertId] = useState("");
  const [operatorName, setOperatorName] = useState(data.me.full_name);
  const [category, setCategory] = useState<"maintenance" | "corrective_action" | "inspection" | "general">("corrective_action");
  const [actionTaken, setActionTaken] = useState("");
  const [notes, setNotes] = useState("");
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function submit(event: FormEvent) {
    event.preventDefault();
    setSaving(true);
    setError(null);
    try {
      await createOperationalLog(token, {
        storage_unit_id: storageUnitId,
        alert_id: alertId ? Number(alertId) : null,
        category,
        operator_name: operatorName,
        action_taken: actionTaken,
        notes,
        timestamp: new Date().toISOString()
      });
      setActionTaken("");
      setNotes("");
      setAlertId("");
      onChanged();
    } catch (err) {
      setError(err instanceof Error ? err.message : "No se pudo registrar la accion.");
    } finally {
      setSaving(false);
    }
  }

  return (
    <div className="space-y-5">
      {canCreateLog ? <InstallationChecklist data={data} token={token} onChanged={onChanged} /> : null}
      <div className={`grid gap-5 ${canCreateLog ? "xl:grid-cols-[430px_1fr]" : "xl:grid-cols-1"}`}>
      {canCreateLog ? (
        <section className="panel p-5">
          <p className="section-kicker">Bitacora operativa</p>
          <h2 className="section-title">Registrar accion manual</h2>
          <p className="section-subtitle">Documenta acciones correctivas y deja evidencia del seguimiento.</p>
          <form onSubmit={submit} className="mt-4 space-y-3">
            <Field label="Storage unit">
              <select value={storageUnitId} onChange={(event) => setStorageUnitId(Number(event.target.value))} className="input">
                {data.storageUnits.map((unit) => <option key={unit.id} value={unit.id}>{unit.name}</option>)}
              </select>
            </Field>
            <Field label="Alerta opcional">
              <select value={alertId} onChange={(event) => setAlertId(event.target.value)} className="input">
                <option value="">Sin alerta asociada</option>
                {data.alerts.map((alert) => <option key={alert.id} value={alert.id}>{alert.title}</option>)}
              </select>
            </Field>
            <Field label="Categoria">
              <select value={category} onChange={(event) => setCategory(event.target.value as typeof category)} className="input">
                <option value="corrective_action">Accion correctiva</option>
                <option value="maintenance">Mantenimiento</option>
                <option value="inspection">Inspeccion</option>
                <option value="general">Registro general</option>
              </select>
            </Field>
            <Field label="Operador">
              <input value={operatorName} onChange={(event) => setOperatorName(event.target.value)} className="input" />
            </Field>
            <Field label="Accion tomada">
              <input value={actionTaken} onChange={(event) => setActionTaken(event.target.value)} className="input" required />
            </Field>
            <Field label="Notas">
              <textarea value={notes} onChange={(event) => setNotes(event.target.value)} className="input min-h-24" />
            </Field>
            {error ? <p className="rounded-lg border border-red-200 bg-red-50 p-3 text-sm font-medium text-red-800">{error}</p> : null}
            <button type="submit" disabled={saving || !storageUnitId} className="btn-primary">
              <Save className="mr-2 inline" size={16} aria-hidden="true" />
              {saving ? "Guardando..." : "Guardar accion"}
            </button>
          </form>
        </section>
      ) : (
        <section className="panel p-5">
          <p className="section-kicker">Bitacora operativa</p>
          <h2 className="section-title">Historial de acciones</h2>
          <p className="section-subtitle">Vista de cliente en solo lectura. AgroEscudo registra las intervenciones tecnicas.</p>
        </section>
      )}
      <section className="panel p-5">
        <p className="section-kicker">Historial</p>
        <h2 className="section-title">Acciones registradas</h2>
        <div className="mt-4 space-y-2">
          {data.logs.length ? data.logs.map((log) => <LogRow key={log.id} log={log} />) : <EmptyState title="Sin bitacora" message="Las acciones operativas apareceran aqui." />}
        </div>
      </section>
      </div>
    </div>
  );
}

function InstallationChecklist({ data, token, onChanged }: { data: AppData; token: string; onChanged: () => void }) {
  const [open, setOpen] = useState(false);
  const [storageUnitId, setStorageUnitId] = useState(data.storageUnits[0]?.id ?? 0);
  const availableDevices = data.devices.filter((device) => device.storage_unit_id === storageUnitId);
  const [deviceId, setDeviceId] = useState(availableDevices[0]?.id ?? 0);
  const [physicalLocation, setPhysicalLocation] = useState("");
  const [observations, setObservations] = useState("");
  const [checks, setChecks] = useState({
    sensor_installed_correctly: false,
    connectivity_verified: false,
    initial_reading_registered: false,
    battery_verified: false
  });
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [notice, setNotice] = useState<string | null>(null);

  useEffect(() => {
    const nextDevice = data.devices.find((device) => device.storage_unit_id === storageUnitId);
    setDeviceId(nextDevice?.id ?? 0);
  }, [data.devices, storageUnitId]);

  async function submit(event: FormEvent) {
    event.preventDefault();
    setSaving(true);
    setError(null);
    setNotice(null);
    try {
      await createInstallationChecklist(token, {
        storage_unit_id: storageUnitId,
        device_id: deviceId,
        physical_location: physicalLocation,
        ...checks,
        observations,
        technician_name: data.me.full_name,
        timestamp: new Date().toISOString()
      });
      setNotice("Checklist de instalacion registrado en bitacora.");
      setPhysicalLocation("");
      setObservations("");
      setChecks({
        sensor_installed_correctly: false,
        connectivity_verified: false,
        initial_reading_registered: false,
        battery_verified: false
      });
      onChanged();
    } catch (err) {
      setError(err instanceof Error ? err.message : "No se pudo registrar la instalacion.");
    } finally {
      setSaving(false);
    }
  }

  return (
    <section className="panel overflow-hidden">
      <div className="flex flex-wrap items-center justify-between gap-3 bg-gradient-to-r from-emeraldInk to-emeraldDeep px-5 py-4 text-white">
        <div>
          <div className="flex items-center gap-2 text-xs font-black uppercase tracking-[0.16em] text-amber-200">
            <CheckCircle2 size={15} aria-hidden="true" />
            Instalacion en campo
          </div>
          <h2 className="mt-1 text-xl font-black tracking-tight">Checklist de instalacion</h2>
          <p className="mt-1 text-sm text-emerald-50/75">Registra la validacion inicial del nodo como evidencia del piloto.</p>
        </div>
        <button type="button" onClick={() => setOpen((current) => !current)} className="rounded-lg border border-white/20 bg-white px-4 py-2 text-sm font-black text-emeraldDeep shadow-soft transition hover:bg-emerald-50">
          {open ? "Cerrar checklist" : "Registrar instalacion"}
        </button>
      </div>
      {open ? (
        <form onSubmit={submit} className="grid gap-4 p-5 lg:grid-cols-[1fr_1.2fr]">
          <div className="space-y-3">
            <Field label="Silo / galpon">
              <select value={storageUnitId} onChange={(event) => setStorageUnitId(Number(event.target.value))} className="input">
                {data.storageUnits.map((unit) => <option key={unit.id} value={unit.id}>{unit.name}</option>)}
              </select>
            </Field>
            <Field label="Dispositivo">
              <select required value={deviceId} onChange={(event) => setDeviceId(Number(event.target.value))} className="input">
                {availableDevices.map((device) => <option key={device.id} value={device.id}>{device.external_id} / {device.name}</option>)}
              </select>
            </Field>
            <Field label="Ubicacion fisica">
              <input required value={physicalLocation} onChange={(event) => setPhysicalLocation(event.target.value)} className="input" placeholder="Ej. pared norte, acceso principal" />
            </Field>
            <Field label="Observaciones">
              <textarea value={observations} onChange={(event) => setObservations(event.target.value)} className="input min-h-24" placeholder="Condiciones de instalacion, fijacion y observaciones tecnicas." />
            </Field>
          </div>
          <div className="space-y-3">
            <div className="rounded-xl border border-slate-200 bg-slate-50 p-4">
              <p className="flex items-center gap-2 text-xs font-black uppercase tracking-[0.14em] text-emerald-800">
                <CalendarDays size={15} aria-hidden="true" />
                Validaciones obligatorias
              </p>
              <div className="mt-3 grid gap-2">
                {([
                  ["sensor_installed_correctly", "Sensor instalado correctamente"],
                  ["connectivity_verified", "Conectividad verificada"],
                  ["initial_reading_registered", "Lectura inicial registrada"],
                  ["battery_verified", "Bateria verificada"]
                ] as Array<[keyof typeof checks, string]>).map(([key, label]) => (
                  <label key={key} className="flex cursor-pointer items-center gap-3 rounded-lg border border-slate-200 bg-white px-3 py-3 text-sm font-semibold text-slate-700 transition hover:border-emerald-200">
                    <input type="checkbox" checked={checks[key]} onChange={(event) => setChecks((current) => ({ ...current, [key]: event.target.checked }))} className="h-4 w-4 accent-emerald-700" />
                    {label}
                  </label>
                ))}
              </div>
            </div>
            {error ? <p className="rounded-lg border border-red-200 bg-red-50 p-3 text-sm font-medium text-red-800">{error}</p> : null}
            {notice ? <p className="rounded-lg border border-emerald-200 bg-emerald-50 p-3 text-sm font-medium text-emerald-800">{notice}</p> : null}
            <button type="submit" disabled={saving || !deviceId} className="btn-primary">
              <Save className="mr-2" size={16} aria-hidden="true" />
              {saving ? "Registrando..." : "Guardar checklist de instalacion"}
            </button>
          </div>
        </form>
      ) : null}
    </section>
  );
}

function AdminCompaniesAndSitesView({ data, token, onChanged }: { data: AppData; token: string; onChanged: () => void }) {
  return (
    <section className="space-y-8">
      <div>
        <p className="section-kicker">Flujo operativo</p>
        <h2 className="section-title">Empresas, sitios y silos</h2>
        <p className="section-subtitle">Agrupa el alta de piloto en una secuencia comercial clara: cliente, sitio, silo, sensor y responsables.</p>
      </div>
      <PilotsView data={data} token={token} onChanged={onChanged} />
      <CompaniesAdminView data={data} token={token} onChanged={onChanged} />
      <StorageUnitsAdminView data={data} token={token} onChanged={onChanged} />
    </section>
  );
}

function DevicesStatusView({ data }: { data: AppData }) {
  return (
    <section className="space-y-5">
      <div>
        <p className="section-kicker">Inventario operativo</p>
        <h2 className="section-title">Dispositivos asignados</h2>
        <p className="section-subtitle">Consulta estado de sensores, ultima lectura, bateria y senal sin modificar configuracion critica.</p>
      </div>
      <div className="grid gap-4 xl:grid-cols-3">
        {data.devices.map((device) => {
          const unit = data.storageUnits.find((item) => item.id === device.storage_unit_id);
          const latest = readingForDevice(data, device);
          const lastSync = lastDeviceSync(data, device);
          const offline = disconnectedDevices(data).some((item) => item.id === device.id);
          return (
            <article key={device.id} className="panel p-5">
              <div className="flex items-start justify-between gap-3">
                <div>
                  <p className="section-kicker">{device.device_type || "sensor"}</p>
                  <h3 className="text-lg font-black text-slate-950">{device.external_id}</h3>
                  <p className="text-sm text-slate-500">{unit?.name || "Unidad no asignada"}</p>
                </div>
                <span className={`rounded-full border px-2.5 py-1 text-[10px] font-black uppercase tracking-[0.12em] ${stateStyles(offline ? "offline" : "normal")}`}>{offline ? "Sin conexion" : "Normal"}</span>
              </div>
              <div className="mt-4 grid grid-cols-2 gap-3">
                <Metric icon={Battery} label="Bateria" value={formatNumber(latest?.battery_voltage, " V", 2)} />
                <Metric icon={Wifi} label="Senal" value={latest ? `${latest.signal_quality} dBm` : "Sin dato"} />
                <Metric icon={Clock3} label="Ultima lectura" value={lastSync ? formatDateTime(lastSync) : "Sin dato"} />
                <Metric icon={Thermometer} label="Temp. grano" value={formatNumber(latest?.grain_temperature, " C")} />
              </div>
            </article>
          );
        })}
      </div>
    </section>
  );
}

function HistoryView({ data }: { data: AppData }) {
  const [storageUnitId, setStorageUnitId] = useState(data.storageUnits[0]?.id ?? 0);
  const selected = data.storageUnits.find((unit) => unit.id === storageUnitId) || data.storageUnits[0] || null;
  const readings = selected ? data.readings.filter((reading) => reading.storage_unit_id === selected.id) : data.readings;
  const alerts = selected ? data.alerts.filter((alert) => alert.storage_unit_id === selected.id) : data.alerts;

  return (
    <section className="space-y-5">
      <div className="flex flex-wrap items-end justify-between gap-3">
        <div>
          <p className="section-kicker">Analisis operativo</p>
          <h2 className="section-title">Historial y tendencias</h2>
          <p className="section-subtitle">Revisa comportamiento reciente de temperatura, humedad y eventos para decisiones de operacion.</p>
        </div>
        <select value={storageUnitId} onChange={(event) => setStorageUnitId(Number(event.target.value))} className="input max-w-xs">
          {data.storageUnits.map((unit) => <option key={unit.id} value={unit.id}>{unit.name}</option>)}
        </select>
      </div>
      {readings.length ? (
        <div className="grid gap-4 xl:grid-cols-2">
          <ReadingChart title="Tendencia temperatura grano" readings={readings} metric="grain_temperature" color="#047857" unit=" C" />
          <ReadingChart title="Tendencia temperatura ambiente" readings={readings} metric="ambient_temperature" color="#2563eb" unit=" C" />
          <ReadingChart title="Tendencia humedad ambiente" readings={readings} metric="ambient_humidity" color="#d97706" unit="%" />
          <ReadingChart title="Salud de bateria" readings={readings} metric="battery_voltage" color="#475569" unit=" V" threshold={3.5} />
        </div>
      ) : (
        <EmptyState title="Sin lecturas historicas" message="Cuando el sensor sincronice datos, el historial aparecera aqui." />
      )}
      <div className="panel overflow-hidden">
        <div className="border-b border-slate-200 px-5 py-4">
          <p className="section-kicker">Eventos</p>
          <h3 className="font-black text-slate-950">Alertas del periodo</h3>
        </div>
        <div className="p-5">
          {alerts.length ? (
            <AlertTable alerts={alerts.slice(0, 8)} devices={data.devices} storageUnits={data.storageUnits} />
          ) : (
            <EmptyState title="Sin eventos historicos" message="No hay alertas registradas para esta unidad." />
          )}
        </div>
      </div>
    </section>
  );
}

function MaintenanceView({ data, token, onChanged, canCreateLog }: { data: AppData; token: string; onChanged: () => void; canCreateLog: boolean }) {
  return (
    <section className="space-y-5">
      <div>
        <p className="section-kicker">Trabajo tecnico</p>
        <h2 className="section-title">Mantenimiento e intervenciones</h2>
        <p className="section-subtitle">Registra visitas, limpieza, bateria, conectividad e inspecciones de sensores asignados.</p>
      </div>
      <div className="grid gap-3 md:grid-cols-3">
        {["Verificar bateria y alimentacion", "Revisar conectividad LoRa/WiFi", "Validar ubicacion fisica del sensor"].map((item) => (
          <div key={item} className="rounded-2xl border border-emerald-100 bg-emerald-50 p-4 text-sm font-bold text-emerald-900">
            <CheckCircle2 className="mb-2" size={18} aria-hidden="true" />
            {item}
          </div>
        ))}
      </div>
      <LogsView data={data} token={token} onChanged={onChanged} canCreateLog={canCreateLog} />
    </section>
  );
}

function SupportView({ data, token, onNavigate }: { data: AppData; token: string; onNavigate: (view: ViewKey) => void }) {
  const critical = data.activeAlerts.filter((alert) => alert.severity === "critical");
  return (
    <section className="space-y-5">
      <div>
        <p className="section-kicker">Soporte AgroEscudo</p>
        <h2 className="section-title">Acompanamiento operativo</h2>
        <p className="section-subtitle">Guia rapida para interpretar alertas y coordinar acciones con el equipo tecnico.</p>
      </div>
      <div className="grid gap-4 lg:grid-cols-3">
        <div className="panel p-5">
          <Headphones className="text-emerald-700" size={24} aria-hidden="true" />
          <h3 className="mt-3 font-black text-slate-950">Contacto soporte</h3>
          <p className="mt-2 text-sm leading-6 text-slate-600">Canal operativo AgroEscudo para seguimiento de sensores, alertas y reportes del piloto.</p>
        </div>
        <div className="panel p-5">
          <AlertTriangle className={critical.length ? "text-red-600" : "text-amber-600"} size={24} aria-hidden="true" />
          <h3 className="mt-3 font-black text-slate-950">Ante alerta critica</h3>
          <p className="mt-2 text-sm leading-6 text-slate-600">Revisar el silo, activar ventilacion si corresponde y solicitar registro tecnico en bitacora.</p>
        </div>
        <div className="panel p-5">
          <FileText className="text-emerald-700" size={24} aria-hidden="true" />
          <h3 className="mt-3 font-black text-slate-950">Evidencia del piloto</h3>
          <p className="mt-2 text-sm leading-6 text-slate-600">Descarga el reporte semanal para compartir condiciones, alertas y acciones registradas.</p>
        </div>
      </div>
      <SupportChatbot data={data} token={token} onNavigate={onNavigate} />
    </section>
  );
}

function CompaniesAdminView({ data, token, onChanged }: { data: AppData; token: string; onChanged: () => void }) {
  const [form, setForm] = useState({ name: "", tax_id: "", type: "acopiador", city: "", contact_name: "", contact_email: "", contact_phone: "" });
  const [editing, setEditing] = useState<Record<number, Partial<Company>>>({});
  const [busy, setBusy] = useState(false);
  const [message, setMessage] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  async function run(action: () => Promise<unknown>, success: string) {
    setBusy(true);
    setError(null);
    setMessage(null);
    try {
      await action();
      setMessage(success);
      onChanged();
    } catch (err) {
      setError(err instanceof Error ? err.message : "No se pudo completar la operacion.");
    } finally {
      setBusy(false);
    }
  }

  async function submit(event: FormEvent) {
    event.preventDefault();
    await run(async () => {
      await createAdminCompany(token, {
        ...form,
        tax_id: form.tax_id || null,
        city: form.city || null,
        contact_name: form.contact_name || null,
        contact_email: form.contact_email || null,
        contact_phone: form.contact_phone || null
      });
      setForm({ name: "", tax_id: "", type: "acopiador", city: "", contact_name: "", contact_email: "", contact_phone: "" });
    }, "Empresa creada correctamente.");
  }

  return (
    <section className="space-y-5">
      <div>
        <p className="section-kicker">Flujo admin</p>
        <h2 className="section-title">Empresas cliente</h2>
        <p className="section-subtitle">Registra organizaciones reales del piloto con datos de contacto para soporte y notificaciones.</p>
      </div>
      {error ? <ErrorState message={error} /> : null}
      {message ? <p className="rounded-xl border border-emerald-200 bg-emerald-50 p-3 text-sm font-bold text-emerald-800">{message}</p> : null}
      <form onSubmit={submit} className="panel grid gap-4 p-5 lg:grid-cols-4">
        <Field label="Nombre *"><input required value={form.name} onChange={(event) => setForm({ ...form, name: event.target.value })} className="input" /></Field>
        <Field label="Tipo *">
          <select value={form.type} onChange={(event) => setForm({ ...form, type: event.target.value })} className="input">
            <option value="acopiador">Acopiador</option>
            <option value="agroindustria">Agroindustria</option>
            <option value="molino">Molino</option>
            <option value="cooperativa">Cooperativa</option>
          </select>
        </Field>
        <Field label="Ciudad"><input value={form.city} onChange={(event) => setForm({ ...form, city: event.target.value })} className="input" /></Field>
        <Field label="NIT / ID fiscal"><input value={form.tax_id} onChange={(event) => setForm({ ...form, tax_id: event.target.value })} className="input" /></Field>
        <Field label="Contacto"><input value={form.contact_name} onChange={(event) => setForm({ ...form, contact_name: event.target.value })} className="input" /></Field>
        <Field label="Email contacto"><input type="email" value={form.contact_email} onChange={(event) => setForm({ ...form, contact_email: event.target.value })} className="input" /></Field>
        <Field label="Telefono"><input value={form.contact_phone} onChange={(event) => setForm({ ...form, contact_phone: event.target.value })} className="input" /></Field>
        <div className="flex items-end"><button disabled={busy} type="submit" className="btn-primary h-12 w-full"><Building2 className="mr-2" size={16} />Crear empresa</button></div>
      </form>
      <div className="grid gap-4 xl:grid-cols-2">
        {data.companies.map((company) => {
          const draft = editing[company.id] || {};
          const value = (key: keyof Company) => String(draft[key] ?? company[key] ?? "");
          return (
            <article key={company.id} className="panel p-5">
              <div className="flex items-start justify-between gap-4">
                <div>
                  <p className="section-kicker">{company.type}</p>
                  <h3 className="text-xl font-black text-slate-950">{company.name}</h3>
                  <p className="text-sm text-slate-500">{company.city || "Ciudad no registrada"}</p>
                </div>
                <span className={`rounded-full px-2.5 py-1 text-[10px] font-black uppercase tracking-[0.12em] ${company.is_active ? "bg-emerald-50 text-emerald-800" : "bg-red-50 text-red-700"}`}>{company.is_active ? "Activa" : "Inactiva"}</span>
              </div>
              <div className="mt-4 grid gap-3 md:grid-cols-2">
                <Field label="Nombre *"><input value={value("name")} onChange={(event) => setEditing((current) => ({ ...current, [company.id]: { ...draft, name: event.target.value } }))} className="input" /></Field>
                <Field label="Tipo"><input value={value("type")} onChange={(event) => setEditing((current) => ({ ...current, [company.id]: { ...draft, type: event.target.value } }))} className="input" /></Field>
                <Field label="Contacto"><input value={value("contact_name")} onChange={(event) => setEditing((current) => ({ ...current, [company.id]: { ...draft, contact_name: event.target.value } }))} className="input" /></Field>
                <Field label="Telefono"><input value={value("contact_phone")} onChange={(event) => setEditing((current) => ({ ...current, [company.id]: { ...draft, contact_phone: event.target.value } }))} className="input" /></Field>
              </div>
              <div className="mt-4 flex flex-wrap gap-2">
                <button disabled={busy} type="button" className="btn-secondary" onClick={() => run(() => updateAdminCompany(token, company.id, draft), "Empresa actualizada.")}>Guardar cambios</button>
                <button disabled={busy} type="button" className="btn-secondary" onClick={() => run(() => company.is_active ? deactivateAdminCompany(token, company.id) : activateAdminCompany(token, company.id), company.is_active ? "Empresa desactivada." : "Empresa activada.")}>
                  {company.is_active ? "Desactivar" : "Activar"}
                </button>
              </div>
            </article>
          );
        })}
      </div>
    </section>
  );
}

function StorageUnitsAdminView({ data, token, onChanged }: { data: AppData; token: string; onChanged: () => void }) {
  const firstCompany = data.companies[0];
  const firstSite = data.sites.find((site) => site.company_id === firstCompany?.id) || data.sites[0];
  const technicians = data.users.filter((user) => user.role === "technician");
  const clients = data.users.filter((user) => user.role === "client");
  const [form, setForm] = useState({
    company_id: firstCompany?.id ?? 0,
    site_id: firstSite?.id ?? 0,
    name: "",
    unit_type: "silo",
    capacity_tons: "",
    crop_type: "",
    location: "",
    assigned_technician_id: technicians[0]?.id ?? 0,
    assigned_client_id: clients[0]?.id ?? 0
  });
  const [busy, setBusy] = useState(false);
  const [message, setMessage] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  async function run(action: () => Promise<unknown>, success: string) {
    setBusy(true);
    setError(null);
    setMessage(null);
    try {
      await action();
      setMessage(success);
      onChanged();
    } catch (err) {
      setError(err instanceof Error ? err.message : "No se pudo completar la operacion.");
    } finally {
      setBusy(false);
    }
  }

  async function submit(event: FormEvent) {
    event.preventDefault();
    await run(async () => {
      await createAdminStorageUnit(token, {
        company_id: form.company_id,
        site_id: form.site_id,
        name: form.name,
        unit_type: form.unit_type,
        capacity_tons: form.capacity_tons ? Number(form.capacity_tons) : null,
        crop_type: form.crop_type || null,
        location: form.location || null,
        assigned_technician_id: form.assigned_technician_id || null,
        assigned_client_id: form.assigned_client_id || null
      });
      setForm((current) => ({ ...current, name: "", capacity_tons: "", crop_type: "", location: "" }));
    }, "Silo/galpon creado correctamente.");
  }

  return (
    <section className="space-y-5">
      <div>
        <p className="section-kicker">Activo monitoreado</p>
        <h2 className="section-title">Silos, galpones y almacenes</h2>
        <p className="section-subtitle">Define el punto operativo del piloto y asigna tecnico y cliente responsable desde el inicio.</p>
      </div>
      {error ? <ErrorState message={error} /> : null}
      {message ? <p className="rounded-xl border border-emerald-200 bg-emerald-50 p-3 text-sm font-bold text-emerald-800">{message}</p> : null}
      <form onSubmit={submit} className="panel grid gap-4 p-5 lg:grid-cols-4">
        <Field label="Empresa *">
          <select value={form.company_id} onChange={(event) => {
            const companyId = Number(event.target.value);
            const site = data.sites.find((item) => item.company_id === companyId) || data.sites[0];
            setForm({ ...form, company_id: companyId, site_id: site?.id ?? 0 });
          }} className="input">
            {data.companies.filter((company) => company.is_active).map((company) => <option key={company.id} value={company.id}>{company.name}</option>)}
          </select>
        </Field>
        <Field label="Sitio *">
          <select value={form.site_id} onChange={(event) => setForm({ ...form, site_id: Number(event.target.value) })} className="input">
            {data.sites.filter((site) => site.company_id === form.company_id).map((site) => <option key={site.id} value={site.id}>{site.name}</option>)}
          </select>
        </Field>
        <Field label="Nombre *"><input required value={form.name} onChange={(event) => setForm({ ...form, name: event.target.value })} className="input" /></Field>
        <Field label="Tipo *">
          <select value={form.unit_type} onChange={(event) => setForm({ ...form, unit_type: event.target.value })} className="input">
            <option value="silo">Silo</option>
            <option value="galpon">Galpon</option>
            <option value="almacen">Almacen</option>
          </select>
        </Field>
        <Field label="Capacidad toneladas"><input type="number" value={form.capacity_tons} onChange={(event) => setForm({ ...form, capacity_tons: event.target.value })} className="input" /></Field>
        <Field label="Producto almacenado"><input value={form.crop_type} onChange={(event) => setForm({ ...form, crop_type: event.target.value })} className="input" /></Field>
        <Field label="Ubicacion fisica"><input value={form.location} onChange={(event) => setForm({ ...form, location: event.target.value })} className="input" /></Field>
        <div className="flex items-end"><button disabled={busy || !form.site_id} type="submit" className="btn-primary h-12 w-full"><Factory className="mr-2" size={16} />Crear unidad</button></div>
      </form>
      <div className="grid gap-4 xl:grid-cols-3">
        {data.storageUnits.map((unit) => (
          <article key={unit.id} className="panel p-5">
            <div className="flex items-start justify-between gap-3">
              <div>
                <p className="section-kicker">{unit.unit_type}</p>
                <h3 className="text-lg font-black text-slate-950">{unit.name}</h3>
                <p className="text-sm text-slate-500">{unit.crop_type || "Producto no registrado"} / {unit.location || "Ubicacion no registrada"}</p>
              </div>
              <span className={`rounded-full px-2.5 py-1 text-[10px] font-black uppercase tracking-[0.12em] ${unit.is_active ? "bg-emerald-50 text-emerald-800" : "bg-red-50 text-red-700"}`}>{unit.is_active ? "Activo" : "Inactivo"}</span>
            </div>
            <div className="mt-4 grid grid-cols-2 gap-3 text-sm">
              <div className="rounded-xl bg-slate-50 p-3"><p className="text-xs font-black uppercase tracking-[0.12em] text-slate-500">Capacidad</p><p className="font-black">{unit.capacity_tons ?? "N/D"} t</p></div>
              <div className="rounded-xl bg-slate-50 p-3"><p className="text-xs font-black uppercase tracking-[0.12em] text-slate-500">Sensores</p><p className="font-black">{data.devices.filter((device) => device.storage_unit_id === unit.id).length}</p></div>
            </div>
            <div className="mt-4 flex flex-wrap gap-2">
              <button disabled={busy} type="button" className="btn-secondary" onClick={() => run(() => unit.is_active ? deactivateAdminStorageUnit(token, unit.id) : activateAdminStorageUnit(token, unit.id), unit.is_active ? "Unidad desactivada." : "Unidad activada.")}>{unit.is_active ? "Desactivar" : "Activar"}</button>
            </div>
          </article>
        ))}
      </div>
    </section>
  );
}

function SensorsAdminView({ data, token, onChanged }: { data: AppData; token: string; onChanged: () => void }) {
  const [form, setForm] = useState({ storage_unit_id: data.storageUnits[0]?.id ?? 0, external_id: "", name: "", device_type: "esp32_lora_wifi_node" });
  const [apiKey, setApiKey] = useState<DeviceWithApiKey | null>(null);
  const [openActions, setOpenActions] = useState<number | null>(null);
  const [busy, setBusy] = useState(false);
  const [message, setMessage] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  async function run(action: () => Promise<unknown>, success: string) {
    setBusy(true);
    setError(null);
    setMessage(null);
    try {
      await action();
      setMessage(success);
      onChanged();
    } catch (err) {
      setError(err instanceof Error ? err.message : "No se pudo completar la operacion.");
    } finally {
      setBusy(false);
    }
  }

  async function submit(event: FormEvent) {
    event.preventDefault();
    await run(async () => {
      const created = await createAdminDevice(token, { ...form });
      setApiKey(created);
      setForm((current) => ({ ...current, external_id: "", name: "" }));
    }, "Sensor registrado. Copia la API key ahora; no se volvera a mostrar.");
  }

  return (
    <section className="space-y-5">
      <div>
        <p className="section-kicker">Telemetria IoT</p>
        <h2 className="section-title">Sensores y API keys</h2>
        <p className="section-subtitle">Registra nodos ESP32/LoRa/WiFi. La API key se muestra una sola vez al crear o resetear.</p>
      </div>
      {error ? <ErrorState message={error} /> : null}
      {message ? <p className="rounded-xl border border-emerald-200 bg-emerald-50 p-3 text-sm font-bold text-emerald-800">{message}</p> : null}
      {apiKey ? (
        <div className="rounded-2xl border border-amber-200 bg-amber-50 p-4 text-amber-950">
          <p className="text-xs font-black uppercase tracking-[0.14em]">API key del sensor</p>
          <p className="mt-2 break-all rounded-xl bg-white p-3 font-mono text-sm">{apiKey.api_key}</p>
          <p className="mt-2 text-sm font-semibold">Usala como device_token en el firmware para {apiKey.external_id}.</p>
        </div>
      ) : null}
      <form onSubmit={submit} className="panel grid gap-4 p-5 lg:grid-cols-4">
        <Field label="Silo/Galpon *">
          <select value={form.storage_unit_id} onChange={(event) => setForm({ ...form, storage_unit_id: Number(event.target.value) })} className="input">
            {data.storageUnits.filter((unit) => unit.is_active).map((unit) => <option key={unit.id} value={unit.id}>{unit.name}</option>)}
          </select>
        </Field>
        <Field label="Device ID *"><input required value={form.external_id} onChange={(event) => setForm({ ...form, external_id: event.target.value })} className="input" placeholder="SILO-004" /></Field>
        <Field label="Nombre *"><input required value={form.name} onChange={(event) => setForm({ ...form, name: event.target.value })} className="input" /></Field>
        <Field label="Tipo"><input value={form.device_type} onChange={(event) => setForm({ ...form, device_type: event.target.value })} className="input" /></Field>
        <div className="lg:col-span-4"><button disabled={busy || !form.storage_unit_id} type="submit" className="btn-primary"><Radio className="mr-2" size={16} />Registrar sensor</button></div>
      </form>
      <div className="panel overflow-hidden">
        <div className="border-b border-slate-200 px-5 py-4">
          <p className="section-kicker">Inventario tecnico</p>
          <h3 className="font-black text-slate-950">Sensores registrados</h3>
        </div>
        <div className="overflow-x-auto">
          <table className="min-w-full text-left text-sm">
            <thead className="bg-slate-50 text-[11px] font-black uppercase tracking-[0.13em] text-slate-500">
              <tr><th className="px-4 py-3">Device ID</th><th className="px-4 py-3">Silo/Galpon</th><th className="px-4 py-3">Tipo</th><th className="px-4 py-3">Ultima conexion</th><th className="px-4 py-3 text-right">Mas</th></tr>
            </thead>
            <tbody className="divide-y divide-slate-200">
              {data.devices.map((device) => {
                const unit = data.storageUnits.find((item) => item.id === device.storage_unit_id);
                return (
                  <tr key={device.id}>
                    <td className="px-4 py-3 font-black text-slate-950">{device.external_id}<p className="text-xs font-normal text-slate-500">{device.name}</p></td>
                    <td className="px-4 py-3">{unit?.name || "Sin unidad"}</td>
                    <td className="px-4 py-3">{device.device_type}</td>
                    <td className="px-4 py-3 text-slate-500">{device.last_seen_at ? formatDateTime(device.last_seen_at) : "Sin lecturas"}</td>
                    <td className="px-4 py-3 text-right">
                      <div className="relative inline-block">
                        <button
                          type="button"
                          disabled={busy}
                          onClick={() => setOpenActions((current) => current === device.id ? null : device.id)}
                          className="rounded-lg border border-slate-200 bg-white p-2 text-slate-600 shadow-soft transition hover:border-emerald-200 hover:text-emerald-700"
                          title="Acciones del sensor"
                        >
                          <MoreVertical size={18} aria-hidden="true" />
                        </button>
                        {openActions === device.id ? (
                          <div className="absolute right-0 z-20 mt-2 w-48 rounded-xl border border-slate-200 bg-white p-2 text-left shadow-panel">
                            <button
                              type="button"
                              disabled={busy}
                              className="w-full rounded-lg px-3 py-2 text-left text-sm font-bold text-slate-700 hover:bg-slate-50"
                              onClick={() => {
                                setOpenActions(null);
                                run(async () => setApiKey(await resetAdminDeviceApiKey(token, device.id)), "API key regenerada. Copiala ahora.");
                              }}
                            >
                              Reset API key
                            </button>
                            <button
                              type="button"
                              disabled={busy}
                              className="w-full rounded-lg px-3 py-2 text-left text-sm font-bold text-slate-700 hover:bg-slate-50"
                              onClick={() => {
                                setOpenActions(null);
                                run(() => device.is_active ? deactivateAdminDevice(token, device.id) : activateAdminDevice(token, device.id), device.is_active ? "Sensor desactivado." : "Sensor activado.");
                              }}
                            >
                              {device.is_active ? "Desactivar" : "Activar"}
                            </button>
                          </div>
                        ) : null}
                      </div>
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      </div>
    </section>
  );
}

function UsersAdminView({ data, token, onChanged }: { data: AppData; token: string; onChanged: () => void }) {
  const firstCompanyId = data.companies[0]?.id ?? 0;
  const [form, setForm] = useState({
    company_id: firstCompanyId || null,
    email: "",
    full_name: "",
    password: "",
    role: "client" as "admin" | "technician" | "client",
    phone_whatsapp: "",
    telegram_chat_id: "",
    receives_alerts: true,
    storage_unit_ids: [] as number[]
  });
  const [selectedUnits, setSelectedUnits] = useState<Record<number, number[]>>({});
  const [passwords, setPasswords] = useState<Record<number, string>>({});
  const [step, setStep] = useState<1 | 2 | 3>(1);
  const [fieldErrors, setFieldErrors] = useState<Record<string, string>>({});
  const [openUserActions, setOpenUserActions] = useState<number | null>(null);
  const [busy, setBusy] = useState(false);
  const [message, setMessage] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  async function run(action: () => Promise<unknown>, success: string) {
    setBusy(true);
    setError(null);
    setMessage(null);
    try {
      await action();
      setMessage(success);
      onChanged();
    } catch (err) {
      setError(err instanceof Error ? err.message : "No se pudo completar la operacion.");
    } finally {
      setBusy(false);
    }
  }

  async function submit(event: FormEvent) {
    event.preventDefault();
    const errors: Record<string, string> = {};
    if (!form.full_name.trim()) errors.full_name = "Ingresa el nombre del usuario.";
    if (!form.email.trim()) errors.email = "Ingresa un correo valido.";
    if (!isStrongPassword(form.password)) errors.password = "Minimo 8 caracteres, una letra y un numero.";
    if (form.role === "client" && !form.company_id) errors.company_id = "Selecciona una empresa para el cliente.";
    if (form.role !== "admin" && form.storage_unit_ids.length === 0) errors.storage_unit_ids = "Selecciona al menos un silo o galpon.";

    setFieldErrors(errors);
    if (Object.keys(errors).length) {
      setStep(errors.full_name || errors.email || errors.password ? 1 : errors.company_id || errors.storage_unit_ids ? 3 : 2);
      return;
    }
    await run(async () => {
      await createAdminUser(token, form);
      setForm({ company_id: firstCompanyId || null, email: "", full_name: "", password: "", role: "client", phone_whatsapp: "", telegram_chat_id: "", receives_alerts: true, storage_unit_ids: [] });
      setStep(1);
      setFieldErrors({});
    }, "Usuario creado correctamente.");
  }

  function nextStep() {
    if (step === 1) {
      const errors: Record<string, string> = {};
      if (!form.full_name.trim()) errors.full_name = "Ingresa el nombre del usuario.";
      if (!form.email.trim()) errors.email = "Ingresa un correo valido.";
      if (!isStrongPassword(form.password)) errors.password = "Minimo 8 caracteres, una letra y un numero.";
      setFieldErrors(errors);
      if (Object.keys(errors).length) return;
      setStep(2);
      return;
    }
    if (step === 2) {
      setFieldErrors({});
      setStep(3);
    }
  }

  function unitIdsFor(user: User) {
    if (selectedUnits[user.id]) return selectedUnits[user.id];
    return data.storageUnits
      .filter((unit) => unit.assigned_client_id === user.id || unit.assigned_technician_id === user.id)
      .map((unit) => unit.id);
  }

  return (
    <section className="space-y-5">
      <div>
        <p className="section-kicker">Administracion segura</p>
        <h2 className="section-title">Usuarios y accesos del piloto</h2>
        <p className="section-subtitle">Gestiona roles, activacion y asignacion de silos o galpones sin exponer configuracion tecnica al cliente.</p>
      </div>
      {error ? <ErrorState message={error} /> : null}
      {message ? <p className="rounded-xl border border-emerald-200 bg-emerald-50 p-3 text-sm font-bold text-emerald-800">{message}</p> : null}
      <form onSubmit={submit} className="panel p-5">
        <div className="mb-5 grid gap-2 sm:grid-cols-3">
          {[
            { id: 1, title: "Datos" },
            { id: 2, title: "Acceso" },
            { id: 3, title: "Asignacion" }
          ].map((item) => (
            <button
              key={item.id}
              type="button"
              onClick={() => setStep(item.id as 1 | 2 | 3)}
              className={`rounded-2xl border px-4 py-3 text-left transition ${step === item.id ? "border-emerald-300 bg-emerald-50 text-emerald-900" : "border-slate-200 bg-white text-slate-500 hover:border-emerald-200"}`}
            >
              <p className="text-[11px] font-black uppercase tracking-[0.15em]">Paso {item.id}</p>
              <p className="mt-1 font-black">{item.title}</p>
            </button>
          ))}
        </div>

        {step === 1 ? (
          <div className="grid gap-4 lg:grid-cols-2">
            <Field label="Nombre *" error={fieldErrors.full_name}>
              <input required value={form.full_name} onChange={(event) => setForm({ ...form, full_name: event.target.value })} className="input" />
            </Field>
            <Field label="Correo *" error={fieldErrors.email}>
              <input required type="email" value={form.email} onChange={(event) => setForm({ ...form, email: event.target.value })} className="input" />
            </Field>
            <Field label="Contraseña temporal *" error={fieldErrors.password}>
              <input required minLength={8} type="password" value={form.password} onChange={(event) => setForm({ ...form, password: event.target.value })} className="input" placeholder="Minimo 8, letra y numero" />
            </Field>
            <Field label="WhatsApp">
              <input value={form.phone_whatsapp} onChange={(event) => setForm({ ...form, phone_whatsapp: event.target.value })} className="input" placeholder="+591..." />
            </Field>
          </div>
        ) : null}

        {step === 2 ? (
          <div className="grid gap-3 md:grid-cols-3">
            {[
              { value: "client", label: "Cliente", detail: "Ve sus silos, alertas, historial y reportes." },
              { value: "technician", label: "Tecnico", detail: "Atiende sensores, mantenimiento, alertas y bitacora." },
              { value: "admin", label: "Administrador", detail: "Gestiona operacion, analisis y administracion." }
            ].map((roleOption) => (
              <label key={roleOption.value} className={`cursor-pointer rounded-2xl border p-4 transition ${form.role === roleOption.value ? "border-emerald-300 bg-emerald-50" : "border-slate-200 bg-white hover:border-emerald-200"}`}>
                <input
                  type="radio"
                  name="role"
                  value={roleOption.value}
                  checked={form.role === roleOption.value}
                  onChange={(event) => setForm({ ...form, role: event.target.value as typeof form.role, storage_unit_ids: event.target.value === "admin" ? [] : form.storage_unit_ids })}
                  className="sr-only"
                />
                <p className="font-black text-slate-950">{roleOption.label}</p>
                <p className="mt-2 text-sm leading-6 text-slate-500">{roleOption.detail}</p>
              </label>
            ))}
          </div>
        ) : null}

        {step === 3 ? (
          <div className="grid gap-4 lg:grid-cols-2">
            <Field label="Empresa" error={fieldErrors.company_id}>
              <select value={form.company_id ?? ""} onChange={(event) => setForm({ ...form, company_id: event.target.value ? Number(event.target.value) : null, storage_unit_ids: [] })} className="input">
                <option value="">Sin empresa interna</option>
                {data.companies.map((company) => <option key={company.id} value={company.id}>{company.name}</option>)}
              </select>
            </Field>
            <Field label="Silos o galpones permitidos" error={fieldErrors.storage_unit_ids}>
              <select
                multiple
                value={form.storage_unit_ids.map(String)}
                onChange={(event) => setForm({ ...form, storage_unit_ids: Array.from(event.target.selectedOptions).map((option) => Number(option.value)) })}
                className="input min-h-32"
                disabled={form.role === "admin"}
              >
                {data.storageUnits
                  .filter((unit) => form.role !== "client" || unit.company_id === form.company_id)
                  .map((unit) => <option key={unit.id} value={unit.id}>{unit.name}</option>)}
              </select>
            </Field>
            <label className="flex items-center gap-2 rounded-xl border border-slate-200 bg-white px-3 py-3 text-sm font-bold text-slate-700">
              <input type="checkbox" checked={form.receives_alerts} onChange={(event) => setForm({ ...form, receives_alerts: event.target.checked })} />
              Recibe alertas
            </label>
            <Field label="Telegram chat_id">
              <input value={form.telegram_chat_id} onChange={(event) => setForm({ ...form, telegram_chat_id: event.target.value })} className="input" />
            </Field>
          </div>
        ) : null}

        <div className="mt-5 flex flex-wrap justify-between gap-3 border-t border-slate-200 pt-4">
          <button type="button" disabled={step === 1 || busy} onClick={() => setStep((current) => (current === 3 ? 2 : 1))} className="btn-secondary">
            Atrás
          </button>
          {step < 3 ? (
            <button type="button" disabled={busy} onClick={nextStep} className="btn-primary">
              Continuar
            </button>
          ) : (
            <button disabled={busy} type="submit" className="btn-primary">
              <UserPlus size={16} aria-hidden="true" />
              Crear usuario
            </button>
          )}
        </div>
      </form>
      <div className="panel overflow-hidden">
        <div className="border-b border-slate-200 px-5 py-4">
          <p className="section-kicker">Control de acceso</p>
          <h3 className="font-black text-slate-950">Usuarios registrados</h3>
        </div>
        <div className="divide-y divide-slate-200">
          {data.users.map((user) => (
            <article key={user.id} className="grid gap-4 p-5 xl:grid-cols-[1.2fr_0.9fr_1.4fr_1fr]">
              <div>
                <div className="flex items-start justify-between gap-3">
                  <div>
                    <p className="font-black text-slate-950">{user.full_name}</p>
                    <p className="text-sm text-slate-500">{user.email}</p>
                  </div>
                  <div className="relative">
                    <button
                      type="button"
                      disabled={busy}
                      onClick={() => setOpenUserActions((current) => current === user.id ? null : user.id)}
                      className="rounded-lg border border-slate-200 bg-white p-2 text-slate-600 shadow-soft transition hover:border-emerald-200 hover:text-emerald-700"
                      title="Acciones de usuario"
                    >
                      <MoreVertical size={17} aria-hidden="true" />
                    </button>
                    {openUserActions === user.id ? (
                      <div className="absolute right-0 z-20 mt-2 w-44 rounded-xl border border-slate-200 bg-white p-2 text-left shadow-panel">
                        <button
                          type="button"
                          disabled={busy}
                          className="w-full rounded-lg px-3 py-2 text-left text-sm font-bold text-slate-700 hover:bg-slate-50"
                          onClick={() => {
                            setOpenUserActions(null);
                            run(() => user.is_active ? deactivateAdminUser(token, user.id) : activateAdminUser(token, user.id), user.is_active ? "Usuario desactivado." : "Usuario activado.");
                          }}
                        >
                          {user.is_active ? "Desactivar" : "Activar"}
                        </button>
                      </div>
                    ) : null}
                  </div>
                </div>
                <div className="mt-2 flex flex-wrap gap-2">
                  <span className="rounded-full bg-slate-100 px-2.5 py-1 text-[10px] font-black uppercase tracking-[0.12em] text-slate-700">{user.role}</span>
                  <span className={`rounded-full px-2.5 py-1 text-[10px] font-black uppercase tracking-[0.12em] ${user.is_active ? "bg-emerald-50 text-emerald-800" : "bg-red-50 text-red-700"}`}>
                    {user.is_active ? "Activo" : "Inactivo"}
                  </span>
                </div>
              </div>
              <div className="space-y-2">
                <Field label="Rol">
                  <select value={user.role} onChange={(event) => run(() => updateAdminUser(token, user.id, { role: event.target.value as UserRole }), "Rol actualizado.")} className="input">
                    <option value="admin">Admin</option>
                    <option value="technician">Tecnico</option>
                    <option value="client">Cliente</option>
                  </select>
                </Field>
              </div>
              <Field label="Asignacion storage units">
                <select
                  multiple
                  value={unitIdsFor(user).map(String)}
                  onChange={(event) => {
                    const ids = Array.from(event.target.selectedOptions).map((option) => Number(option.value));
                    setSelectedUnits((current) => ({ ...current, [user.id]: ids }));
                  }}
                  className="input min-h-28"
                  disabled={user.role === "admin"}
                >
                  {data.storageUnits
                    .filter((unit) => user.role !== "client" || unit.company_id === user.company_id)
                    .map((unit) => <option key={unit.id} value={unit.id}>{unit.name}</option>)}
                </select>
                <button type="button" disabled={busy || user.role === "admin"} onClick={() => run(() => assignAdminUserStorageUnits(token, user.id, unitIdsFor(user)), "Asignacion actualizada.")} className="btn-secondary mt-2">
                  Guardar asignacion
                </button>
              </Field>
              <div className="space-y-2">
                <Field label="Reset password">
                  <input type="password" minLength={8} value={passwords[user.id] || ""} onChange={(event) => setPasswords((current) => ({ ...current, [user.id]: event.target.value }))} className="input" placeholder="Minimo 8, letra y numero" />
                </Field>
                <button type="button" disabled={busy || !isStrongPassword(passwords[user.id] || "")} onClick={() => run(() => resetAdminUserPassword(token, user.id, passwords[user.id]), "Password actualizado.")} className="btn-secondary w-full">
                  Resetear password
                </button>
              </div>
            </article>
          ))}
        </div>
      </div>
    </section>
  );
}

function NotificationsAdminView({ data, token }: { data: AppData; token: string }) {
  const [deliveries, setDeliveries] = useState<NotificationDelivery[]>([]);
  const [integrationStatus, setIntegrationStatus] = useState<Awaited<ReturnType<typeof getIntegrationStatus>> | null>(null);
  const [channel, setChannel] = useState<"whatsapp" | "telegram">("telegram");
  const [userId, setUserId] = useState<number>(data.users.find((user) => user.role === "client")?.id ?? data.users[0]?.id ?? 0);
  const [destination, setDestination] = useState("");
  const [message, setMessage] = useState("Prueba AgroEscudo: alerta crítica registrada para seguimiento operativo.");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function load() {
    setLoading(true);
    setError(null);
    try {
      const [deliveryRows, statusResult] = await Promise.all([
        getNotificationDeliveries(token),
        getIntegrationStatus(token)
      ]);
      setDeliveries(deliveryRows);
      setIntegrationStatus(statusResult);
    } catch (err) {
      setError(err instanceof Error ? err.message : "No se pudieron cargar deliveries.");
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    load();
  }, [token]);

  async function submit(event: FormEvent) {
    event.preventDefault();
    setLoading(true);
    setError(null);
    try {
      await testAdminNotification(token, channel, {
        user_id: userId || null,
        destination: destination || null,
        message
      });
      await load();
    } catch (err) {
      setError(err instanceof Error ? err.message : "No se pudo registrar prueba de notificacion.");
    } finally {
      setLoading(false);
    }
  }

  return (
    <section className="space-y-5">
      <div>
        <p className="section-kicker">Auditoria comercial</p>
        <h2 className="section-title">Notificaciones WhatsApp y Telegram</h2>
        <p className="section-subtitle">Registra pruebas dry-run para validar el flujo sin enviar mensajes reales durante la demo.</p>
      </div>
      {error ? <ErrorState message={error} onRetry={load} /> : null}
      {integrationStatus ? (
        <div className="grid gap-3 sm:grid-cols-2 xl:grid-cols-5">
          {Object.entries(integrationStatus.services).map(([service, state]) => (
            <div key={service} className="panel flex items-center justify-between p-4">
              <div>
                <p className="text-[11px] font-black uppercase tracking-[0.12em] text-slate-500">{service}</p>
                <p className="mt-1 text-sm font-bold text-slate-950">{state.configured ? "Credencial lista" : "Falta configurar"}</p>
              </div>
              <span className={`h-3 w-3 rounded-full ${state.configured ? "bg-emerald-500" : "bg-amber-500"}`} aria-hidden="true" />
            </div>
          ))}
        </div>
      ) : null}
      <form onSubmit={submit} className="panel grid gap-4 p-5 lg:grid-cols-[0.7fr_1fr_1fr_2fr_auto]">
        <Field label="Canal">
          <select value={channel} onChange={(event) => setChannel(event.target.value as typeof channel)} className="input">
            <option value="telegram">Telegram</option>
            <option value="whatsapp">WhatsApp</option>
          </select>
        </Field>
        <Field label="Usuario">
          <select value={userId} onChange={(event) => setUserId(Number(event.target.value))} className="input">
            {data.users.map((user) => <option key={user.id} value={user.id}>{user.full_name} / {user.role}</option>)}
          </select>
        </Field>
        <Field label="Destino">
          <input value={destination} onChange={(event) => setDestination(event.target.value)} className="input" placeholder={channel === "telegram" ? "Chat ID" : "Telefono WhatsApp"} />
        </Field>
        <Field label="Mensaje">
          <input value={message} onChange={(event) => setMessage(event.target.value)} className="input" />
        </Field>
        <div className="flex items-end">
          <button disabled={loading} type="submit" className="btn-primary h-12">
            <Send className="mr-2" size={16} aria-hidden="true" />
            Probar
          </button>
        </div>
      </form>
      <div className="panel overflow-hidden">
        <div className="flex items-center justify-between border-b border-slate-200 px-5 py-4">
          <div>
            <p className="section-kicker">Deliveries</p>
            <h3 className="font-black text-slate-950">Historial dry-run y envios</h3>
          </div>
          <button type="button" onClick={load} className="btn-secondary">
            <BellRing className="mr-2" size={16} aria-hidden="true" />
            Actualizar
          </button>
        </div>
        {loading && !deliveries.length ? <LoadingState label="Cargando deliveries" /> : null}
        <div className="overflow-x-auto">
          <table className="min-w-full text-left text-sm">
            <thead className="bg-slate-50 text-[11px] font-black uppercase tracking-[0.13em] text-slate-500">
              <tr>
                <th className="px-4 py-3">Fecha</th>
                <th className="px-4 py-3">Canal</th>
                <th className="px-4 py-3">Estado</th>
                <th className="px-4 py-3">Destino</th>
                <th className="px-4 py-3">Mensaje</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-200">
              {deliveries.map((delivery) => (
                <tr key={delivery.id}>
                  <td className="px-4 py-3 text-slate-500">{formatDateTime(delivery.created_at)}</td>
                  <td className="px-4 py-3 font-bold text-slate-900">{delivery.channel}</td>
                  <td className="px-4 py-3">
                    <span className={`rounded-full px-2.5 py-1 text-[10px] font-black uppercase tracking-[0.12em] ${delivery.status === "dry_run" ? "bg-amber-50 text-amber-800" : delivery.status === "sent" ? "bg-emerald-50 text-emerald-800" : "bg-slate-100 text-slate-700"}`}>
                      {delivery.status}
                    </span>
                  </td>
                  <td className="px-4 py-3 text-slate-600">{delivery.destination || "No configurado"}</td>
                  <td className="max-w-xl px-4 py-3 text-slate-600">{delivery.payload_preview}</td>
                </tr>
              ))}
              {!deliveries.length && !loading ? (
                <tr>
                  <td colSpan={5} className="px-4 py-8">
                    <EmptyState title="Sin deliveries" message="Ejecuta una prueba dry-run o genera una alerta para ver evidencia aqui." />
                  </td>
                </tr>
              ) : null}
            </tbody>
          </table>
        </div>
      </div>
    </section>
  );
}

function ThresholdsView({ devices, token }: { devices: Device[]; token: string }) {
  const [deviceId, setDeviceId] = useState(devices[0]?.id ?? 0);
  const [thresholds, setThresholds] = useState<Thresholds | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const selectedDevice = devices.find((device) => device.id === deviceId);
  const fieldLabels: Record<keyof Omit<Thresholds, "device_id">, string> = {
    max_grain_temperature: "Temp. grano maxima",
    max_ambient_humidity: "Humedad ambiente maxima",
    min_battery_voltage: "Bateria minima",
    critical_temperature: "Temperatura critica",
    critical_humidity: "Humedad critica"
  };

  useEffect(() => {
    if (!deviceId) return;
    setLoading(true);
    setError(null);
    getThresholds(token, deviceId)
      .then(setThresholds)
      .catch((err) => setError(err instanceof Error ? err.message : "No se pudieron cargar umbrales."))
      .finally(() => setLoading(false));
  }, [deviceId, token]);

  async function submit(event: FormEvent) {
    event.preventDefault();
    if (!thresholds) return;
    setLoading(true);
    setError(null);
    try {
      const { device_id: _deviceId, ...payload } = thresholds;
      setThresholds(await updateThresholds(token, deviceId, payload));
    } catch (err) {
      setError(err instanceof Error ? err.message : "No se pudieron guardar umbrales.");
    } finally {
      setLoading(false);
    }
  }

  if (!devices.length) {
    return <EmptyState title="Sin devices" message="Registra dispositivos antes de configurar umbrales." />;
  }

  return (
    <section className="panel max-w-4xl p-6">
      <div className="flex items-start gap-3">
        <div className="flex h-11 w-11 items-center justify-center rounded-xl bg-emerald-50 text-emeraldDeep">
          <SlidersIcon />
        </div>
        <div>
          <p className="section-kicker">Configuracion tecnica</p>
          <h2 className="section-title">Umbrales por dispositivo</h2>
          <p className="section-subtitle">Define limites de temperatura, humedad y bateria para alertas automaticas.</p>
        </div>
      </div>
      <div className="mt-5">
        <Field label="Device">
          <select value={deviceId} onChange={(event) => setDeviceId(Number(event.target.value))} className="input">
            {devices.map((device) => <option key={device.id} value={device.id}>{device.external_id} / {device.name}</option>)}
          </select>
        </Field>
      </div>
      {selectedDevice ? (
        <p className="mt-3 inline-flex rounded-full border border-emerald-100 bg-emerald-50 px-3 py-1 text-xs font-bold text-emerald-800">
          Configurando {selectedDevice.external_id}
        </p>
      ) : null}
      {loading && !thresholds ? <div className="mt-4"><LoadingState label="Cargando umbrales" /></div> : null}
      {error ? <div className="mt-4"><ErrorState message={error} /></div> : null}
      {thresholds ? (
        <form onSubmit={submit} className="mt-5 grid gap-4 sm:grid-cols-2">
          {(["max_grain_temperature", "max_ambient_humidity", "min_battery_voltage", "critical_temperature", "critical_humidity"] as const).map((field) => (
            <Field key={field} label={fieldLabels[field]}>
              <input
                type="number"
                step="0.1"
                value={thresholds[field]}
                onChange={(event) => setThresholds({ ...thresholds, [field]: Number(event.target.value) })}
                className="input"
              />
            </Field>
          ))}
          <div className="sm:col-span-2">
            <button type="submit" disabled={loading} className="btn-primary">
              <Save className="mr-2" size={16} aria-hidden="true" />
              {loading ? "Guardando..." : "Guardar cambios"}
            </button>
          </div>
        </form>
      ) : null}
    </section>
  );
}

function SlidersIcon() {
  return <Gauge size={20} aria-hidden="true" />;
}

function ReportsView({ data, token }: { data: AppData; token: string }) {
  const storageUnits = data.storageUnits;
  const [storageUnitId, setStorageUnitId] = useState(storageUnits[0]?.id ?? 0);
  const [report, setReport] = useState<WeeklyReport | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const selectedStorageUnit = storageUnits.find((unit) => unit.id === storageUnitId) || null;
  const selectedDevice = selectedStorageUnit ? data.devices.find((device) => device.storage_unit_id === selectedStorageUnit.id) : undefined;
  const selectedReadings = selectedStorageUnit ? data.readings.filter((reading) => reading.storage_unit_id === selectedStorageUnit.id) : [];
  const selectedAlerts = selectedStorageUnit ? data.alerts.filter((alert) => alert.storage_unit_id === selectedStorageUnit.id) : [];
  const selectedLogs = selectedStorageUnit ? data.logs.filter((log) => log.storage_unit_id === selectedStorageUnit.id) : [];

  async function loadReport(id = storageUnitId) {
    if (!id) return;
    setLoading(true);
    setError(null);
    try {
      setReport(await getWeeklyReport(token, id));
    } catch (err) {
      setError(err instanceof Error ? err.message : "No se pudo generar reporte.");
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    loadReport(storageUnitId);
  }, [storageUnitId]);

  if (!storageUnits.length) {
    return <EmptyState title="Sin storage units" message="No hay unidades para generar reporte semanal." />;
  }

  return (
    <section className="space-y-4">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div>
          <p className="section-kicker">Reporte ejecutivo</p>
          <h2 className="section-title">Reporte semanal</h2>
          <p className="section-subtitle">Resumen listo para piloto comercial, seguimiento operativo y comite interno.</p>
        </div>
        <div className="flex flex-wrap items-center gap-2">
          <select value={storageUnitId} onChange={(event) => setStorageUnitId(Number(event.target.value))} className="input max-w-xs">
            {storageUnits.map((unit) => <option key={unit.id} value={unit.id}>{unit.name}</option>)}
          </select>
          <ReportDownloadButton
            token={token}
            storageUnit={selectedStorageUnit}
            device={selectedDevice}
            readings={selectedReadings}
            alerts={selectedAlerts}
            logs={selectedLogs}
            report={report}
          />
        </div>
      </div>
      <section className="overflow-hidden rounded-[22px] bg-gradient-to-br from-emeraldInk via-emeraldDeep to-emerald-800 p-5 text-white shadow-glow">
        <div className="flex flex-wrap items-center justify-between gap-5">
          <div className="max-w-2xl">
            <div className="inline-flex items-center gap-2 rounded-full border border-white/15 bg-white/10 px-3 py-1.5 text-xs font-black uppercase tracking-[0.16em] text-emerald-50">
              <Sparkles size={14} aria-hidden="true" />
              Estudio tecnico AgroEscudo
            </div>
            <h3 className="mt-3 text-2xl font-black tracking-tight">PDF premium para decisiones, mantenimiento y evidencia.</h3>
            <p className="mt-2 text-sm leading-6 text-white/75">Incluye portada corporativa, resumen, graficas, alertas, bitacora, consulta del sensor y recomendaciones operativas.</p>
          </div>
          <div className="grid gap-2 sm:grid-cols-3">
            <div className="rounded-2xl border border-white/10 bg-white/10 p-3">
              <Bot size={19} aria-hidden="true" />
              <p className="mt-2 text-sm font-black">Consulta sensor</p>
            </div>
            <div className="rounded-2xl border border-white/10 bg-white/10 p-3">
              <Wrench size={19} aria-hidden="true" />
              <p className="mt-2 text-sm font-black">Mantenimiento</p>
            </div>
            <div className="rounded-2xl border border-white/10 bg-white/10 p-3">
              <GraduationCap size={19} aria-hidden="true" />
              <p className="mt-2 text-sm font-black">Educacion</p>
            </div>
          </div>
        </div>
      </section>
      {!report && !loading && !error ? (
        <EmptyState title="Reporte listo para generar" message="Selecciona una unidad monitoreada para cargar el resumen y descargar el PDF tecnico." />
      ) : null}
      {loading ? <LoadingState label="Generando reporte" /> : null}
      {error ? <ErrorState message={error} onRetry={() => loadReport()} /> : null}
      {report ? (
        <div className="panel p-5">
          <div className="mb-5 flex flex-wrap items-start justify-between gap-3 border-b border-slate-200 pb-5">
            <div>
              <p className="section-kicker">AgroEscudo Weekly</p>
              <h3 className="text-2xl font-black tracking-tight text-slate-950">{report.storage_unit_name}</h3>
              <p className="mt-1 text-sm text-slate-500">{report.company_name} / {report.site_name}</p>
              <div className="mt-3"><PilotStatusBadge status={report.pilot_status} /></div>
            </div>
            <div className="rounded-xl bg-emerald-50 px-4 py-3 text-sm font-bold text-emerald-800">
              {formatDateTime(report.date_from)} - {formatDateTime(report.date_to)}
            </div>
          </div>
          <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
            <ReportItem label="Empresa" value={report.company_name} />
            <ReportItem label="Sitio" value={report.site_name} />
            <ReportItem label="Silo / galpon" value={report.storage_unit_name} />
            <ReportItem label="Rango" value={`${formatDateTime(report.date_from)} - ${formatDateTime(report.date_to)}`} />
            <ReportItem label="Lecturas" value={String(report.reading_count)} />
            <ReportItem label="Temp. maxima" value={formatNumber(report.max_grain_temperature, " C")} />
            <ReportItem label="Humedad maxima" value={formatNumber(report.max_ambient_humidity, "%")} />
            <ReportItem label="Alertas generadas" value={String(report.alerts_generated)} />
            <ReportItem label="Alertas resueltas" value={String(report.alerts_resolved)} />
            <ReportItem label="Horas fuera de rango" value={`${report.approximate_hours_out_of_range} h`} />
            <ReportItem label="Checklist instalacion" value={String(report.installation_count)} />
            <ReportItem label="Mantenimientos" value={String(report.maintenance_count)} />
            <ReportItem label="Ultimo reporte" value={report.last_report_generated_at ? formatDateTime(report.last_report_generated_at) : "Primer reporte"} />
          </div>
          <div className="mt-5">
            <p className="section-kicker">Evidencia operativa</p>
            <h3 className="font-bold text-slate-950">Acciones registradas</h3>
            <div className="mt-3 space-y-2">
              {report.operational_actions.length ? report.operational_actions.map((log) => <LogRow key={log.id} log={log} />) : <EmptyState title="Sin acciones en el periodo" message="No se registraron acciones operativas esta semana." />}
            </div>
          </div>
        </div>
      ) : null}
    </section>
  );
}

function Field({ label, children, error }: { label: string; children: ReactNode; error?: string | null }) {
  return (
    <label className="block">
      <span className="text-xs font-bold uppercase tracking-[0.12em] text-slate-500">{label}</span>
      <div className="mt-1">{children}</div>
      {error ? <p className="mt-1 text-xs font-bold text-red-700">{error}</p> : null}
    </label>
  );
}

function LogRow({ log }: { log: OperationalLog }) {
  const categoryLabels: Record<string, string> = {
    installation: "Instalacion",
    maintenance: "Mantenimiento",
    corrective_action: "Accion correctiva",
    inspection: "Inspeccion",
    general: "General"
  };
  return (
    <article className="rounded-xl border border-slate-200 bg-slate-50 p-4 shadow-soft">
      <div className="flex flex-wrap items-center justify-between gap-2">
        <div className="flex flex-wrap items-center gap-2">
          <p className="font-bold text-slate-950">{log.action_taken}</p>
          <span className="rounded-full border border-emerald-100 bg-emerald-50 px-2 py-1 text-[10px] font-black uppercase tracking-[0.1em] text-emerald-800">
            {categoryLabels[log.category] || log.category}
          </span>
        </div>
        <p className="rounded-full bg-white px-2.5 py-1 text-xs font-semibold text-slate-500">{formatDateTime(log.timestamp)}</p>
      </div>
      <p className="mt-1 text-sm text-slate-600">{log.operator_name}</p>
      {log.notes ? <p className="mt-2 whitespace-pre-line text-sm leading-6 text-slate-500">{log.notes}</p> : null}
    </article>
  );
}

function ReportItem({ label, value }: { label: string; value: string }) {
  return (
    <div className="metric-tile">
      <p className="text-[11px] font-bold uppercase tracking-[0.14em] text-slate-500">{label}</p>
      <p className="mt-2 font-black tracking-tight text-slate-950">{value}</p>
    </div>
  );
}
