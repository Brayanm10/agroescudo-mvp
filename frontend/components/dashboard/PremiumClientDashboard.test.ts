import { describe, expect, it } from "vitest";

import { countStates, unitFamily, unitState } from "./PremiumClientDashboard";
import type { AppData, StorageUnit } from "@/lib/types";

const storageUnit = {
  id: 1,
  operation_type: "storage"
} as StorageUnit;

function data(overrides: Partial<AppData> = {}): AppData {
  return {
    storageUnits: [storageUnit],
    devices: [],
    insights: [],
    ...overrides
  } as AppData;
}

describe("premium client dashboard model", () => {
  it("never marks a unit normal when insight data is absent", () => {
    expect(unitState(data(), storageUnit)).toBe("no_data");
  });

  it("maps backend attention and critical states", () => {
    expect(unitState(data({ insights: [{ storage_unit_id: 1, status: "attention" }] as AppData["insights"] }), storageUnit)).toBe("warning");
    expect(unitState(data({ insights: [{ storage_unit_id: 1, status: "critical" }] as AppData["insights"] }), storageUnit)).toBe("critical");
  });

  it("uses the device family when a CampoSensor is attached", () => {
    const fieldData = data({ devices: [{ storage_unit_id: 1, device_type: "field_sensor" }] as AppData["devices"] });
    expect(unitFamily(fieldData, storageUnit)).toBe("field");
  });

  it("keeps an empty operation distinct from a no-data unit", () => {
    expect(countStates(data({ storageUnits: [] }), [])).toEqual({ normal: 0, warning: 0, critical: 0, no_data: 0 });
  });
});
