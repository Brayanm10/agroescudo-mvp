import type { UserRole, ViewKey } from "@/lib/types";

export const PLUVIOMETRY_ROUTE = "/pluviometria";
export const PLUVIOMETRY_LABEL = "Pluviometría";

const accountViews: ViewKey[] = ["profile", "changePassword", "preferences"];

export function allowedViewsForRole(role: UserRole, features: string[] = []): ViewKey[] {
  const hasPluviometry = features.includes("PLUVIOMETRY");
  if (role === "admin") {
    return [
      "dashboard", "demo", "pilots", "companies", "storage", "pluviometry", "sensors", "sites",
      "alerts", "logs", "maintenance", "installations", "evidence", "systemHealth", "gateways",
      "sentinel", "pilotMetrics", "comparison", "firmware", "exports", "history", "reports", "support",
      "users", "thresholds", "notifications", ...accountViews
    ].filter((view) => view !== "pluviometry" || hasPluviometry) as ViewKey[];
  }
  if (role === "technician") {
    return [
      "dashboard", "sites", "pluviometry", "sensors", "alerts", "maintenance", "installations", "evidence",
      "systemHealth", "gateways", "comparison", "firmware", "exports", "logs", "support", ...accountViews
    ].filter((view) => view !== "pluviometry" || hasPluviometry) as ViewKey[];
  }
  return ["dashboard", "sites", "pluviometry", "alerts", "reports", "support", ...accountViews]
    .filter((view) => view !== "pluviometry" || hasPluviometry) as ViewKey[];
}

export function defaultViewForRole(): ViewKey {
  return "dashboard";
}

export function canAccessPluviometry(role: UserRole, features: string[] = []) {
  return (role === "admin" || role === "technician" || role === "client") && features.includes("PLUVIOMETRY");
}
