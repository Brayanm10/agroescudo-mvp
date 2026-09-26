import { describe, expect, it } from "vitest";
import {
  allowedViewsForRole,
  canAccessPluviometry,
  PLUVIOMETRY_LABEL,
  PLUVIOMETRY_ROUTE
} from "./navigation";

describe("pluviometry navigation", () => {
  for (const role of ["admin", "technician", "client"] as const) {
    it(`is available to ${role} only with the company feature`, () => {
      expect(canAccessPluviometry(role, ["PLUVIOMETRY"])).toBe(true);
      expect(allowedViewsForRole(role, ["PLUVIOMETRY"])).toContain("pluviometry");
      expect(canAccessPluviometry(role, [])).toBe(false);
      expect(allowedViewsForRole(role, [])).not.toContain("pluviometry");
      expect(PLUVIOMETRY_LABEL).toBe("Pluviometría");
      expect(PLUVIOMETRY_ROUTE).toBe("/pluviometria");
    });
  }

  it("does not authorize unknown roles", () => {
    expect(canAccessPluviometry("auditor", ["PLUVIOMETRY"])).toBe(false);
  });

  it("keeps feature administration restricted to ADMIN navigation", () => {
    expect(allowedViewsForRole("admin", [])).toContain("companies");
    expect(allowedViewsForRole("technician", [])).not.toContain("companies");
    expect(allowedViewsForRole("client", [])).not.toContain("companies");
  });
});
