import type { CanonicalMetricSeries } from "@/lib/types";

export type CompassDirection = "N" | "NE" | "E" | "SE" | "S" | "SO" | "O" | "NO";

const DIRECTIONS: CompassDirection[] = ["N", "NE", "E", "SE", "S", "SO", "O", "NO"];

export function normalizeDegrees(degrees: number) {
  return ((degrees % 360) + 360) % 360;
}

export function degreesToCompass(degrees: number): CompassDirection {
  return DIRECTIONS[Math.round(normalizeDegrees(degrees) / 45) % DIRECTIONS.length];
}

export function oppositeCompassDirection(direction: CompassDirection): CompassDirection {
  return DIRECTIONS[(DIRECTIONS.indexOf(direction) + 4) % DIRECTIONS.length];
}

export function windDirectionPresentation(degrees: number | null) {
  if (degrees == null || !Number.isFinite(degrees)) return null;
  const normalized = normalizeDegrees(degrees);
  const from = degreesToCompass(normalized);
  return {
    degrees: normalized,
    from,
    to: oppositeCompassDirection(from),
    arrowRotation: normalizeDegrees(normalized + 180)
  };
}

export function circularMeanDegrees(
  points: CanonicalMetricSeries["points"]
): number | null {
  let sinTotal = 0;
  let cosTotal = 0;
  let weightTotal = 0;
  for (const point of points) {
    if (point.value == null || !Number.isFinite(point.value)) continue;
    const weight = Math.max(point.sample_count, 1);
    const radians = normalizeDegrees(point.value) * Math.PI / 180;
    sinTotal += Math.sin(radians) * weight;
    cosTotal += Math.cos(radians) * weight;
    weightTotal += weight;
  }
  if (!weightTotal) return null;
  const sinMean = sinTotal / weightTotal;
  const cosMean = cosTotal / weightTotal;
  if (Math.abs(sinMean) < 1e-12 && Math.abs(cosMean) < 1e-12) {
    for (let index = points.length - 1; index >= 0; index -= 1) {
      const fallback = windDirectionPresentation(points[index].value);
      if (fallback) return fallback.degrees;
    }
    return null;
  }
  return normalizeDegrees(Math.atan2(sinMean, cosMean) * 180 / Math.PI);
}

export function formatWindDirection(degrees: number | null, decimals = 0) {
  const direction = windDirectionPresentation(degrees);
  return direction ? `${direction.from} · ${direction.degrees.toFixed(decimals)}°` : "—";
}
