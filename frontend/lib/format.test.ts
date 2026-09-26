import { describe, expect, it } from "vitest";
import {
  formatChartTimeInTimeZone,
  formatDateTimeInTimeZone,
  parseUtcTimestamp
} from "./format";

describe("formateo operacional por timezone IANA", () => {
  it("convierte UTC a la hora del predio incluso si SQLite omite el sufijo Z", () => {
    expect(formatChartTimeInTimeZone("2026-09-26T05:40:15", "America/La_Paz")).toBe("01:40");
    expect(formatChartTimeInTimeZone("2026-09-26T05:40:15Z", "America/La_Paz")).toBe("01:40");
    expect(formatDateTimeInTimeZone("2026-09-26T05:40:15Z", "America/La_Paz")).toContain("1:40 a. m.");
  });

  it("respeta medianoche local del predio", () => {
    expect(formatChartTimeInTimeZone("2026-09-26T04:00:00Z", "America/La_Paz")).toBe("00:00");
  });

  it("ubica el instante anterior en el día local previo", () => {
    expect(formatChartTimeInTimeZone("2026-09-26T03:59:59Z", "America/La_Paz", {
      day: "2-digit",
      month: "2-digit",
      year: "numeric",
      hour: "2-digit",
      minute: "2-digit",
      second: "2-digit",
      hourCycle: "h23"
    })).toBe("25/09/2026, 23:59:59");
  });

  it("preserva el instante UTC original", () => {
    expect(parseUtcTimestamp("2026-09-26T05:40:15").toISOString()).toBe("2026-09-26T05:40:15.000Z");
  });
});
