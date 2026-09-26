import type {
  BoundaryGeoJson,
  GeoJsonPosition,
  PluviometryMapSnapshot,
  PluviometrySite,
  RainGaugeMapDevice,
  RainGaugeStatus
} from "@/lib/types";
import { formatWindDirection, windDirectionPresentation } from "./wind-direction";

export type GeoJsonFeature = {
  type: "Feature";
  geometry: BoundaryGeoJson;
  properties: { id: number; name: string };
};

export type GeoJsonFeatureCollection = {
  type: "FeatureCollection";
  features: GeoJsonFeature[];
};

export const STATUS_PRESENTATION: Record<RainGaugeStatus, { label: string; color: string; ring: string }> = {
  online: { label: "En línea", color: "#047857", ring: "#d1fae5" },
  delayed: { label: "Demorado", color: "#ca8a04", ring: "#fef9c3" },
  offline: { label: "Sin conexión", color: "#64748b", ring: "#e2e8f0" },
  critical: { label: "Crítico", color: "#dc2626", ring: "#fee2e2" }
};

export function resolveSelectedSite(sites: PluviometrySite[], requestedId: string | null): PluviometrySite | null {
  if (!sites.length) return null;
  const parsed = requestedId ? Number(requestedId) : Number.NaN;
  return sites.find((site) => site.id === parsed) ?? sites[0];
}

export function pluviometryQueryPath(siteId: number) {
  return `/pluviometria?predio=${siteId}`;
}

export function rainGaugeDetailPath(deviceId: number) {
  return `/pluviometria/pluviometros/${deviceId}`;
}

export function locatedDevices(snapshot: PluviometryMapSnapshot) {
  return snapshot.devices.filter((device) => device.latitude != null && device.longitude != null);
}

export function siteFeatureCollection(snapshot: PluviometryMapSnapshot): GeoJsonFeatureCollection {
  const geometry = snapshot.site.boundary_geojson;
  return {
    type: "FeatureCollection",
    features: geometry ? [{
      type: "Feature",
      geometry,
      properties: { id: snapshot.site.id, name: snapshot.site.name }
    }] : []
  };
}

export function parcelFeatureCollection(snapshot: PluviometryMapSnapshot): GeoJsonFeatureCollection {
  return {
    type: "FeatureCollection",
    features: snapshot.parcels.flatMap((parcel) => parcel.boundary_geojson ? [{
      type: "Feature" as const,
      geometry: parcel.boundary_geojson,
      properties: { id: parcel.id, name: parcel.name }
    }] : [])
  };
}

function geometryPositions(geometry: BoundaryGeoJson): GeoJsonPosition[] {
  return geometry.type === "Polygon" ? geometry.coordinates.flat() : geometry.coordinates.flat(2);
}

export type MapViewport =
  | { kind: "bounds"; coordinates: GeoJsonPosition[] }
  | { kind: "center"; center: [number, number]; zoom: number }
  | { kind: "bolivia" };

export function mapViewport(snapshot: PluviometryMapSnapshot): MapViewport {
  if (snapshot.site.boundary_geojson) {
    return { kind: "bounds", coordinates: geometryPositions(snapshot.site.boundary_geojson) };
  }
  const parcelCoordinates = snapshot.parcels.flatMap((parcel) =>
    parcel.boundary_geojson ? geometryPositions(parcel.boundary_geojson) : []
  );
  if (parcelCoordinates.length) return { kind: "bounds", coordinates: parcelCoordinates };
  const markers = snapshot.devices.flatMap((device) =>
    device.latitude == null || device.longitude == null
      ? []
      : [[device.longitude, device.latitude] as GeoJsonPosition]
  );
  if (markers.length) return { kind: "bounds", coordinates: markers };
  if (snapshot.site.latitude != null && snapshot.site.longitude != null) {
    return { kind: "center", center: [snapshot.site.longitude, snapshot.site.latitude], zoom: 13 };
  }
  return { kind: "bolivia" };
}

export function formattedMetric(value: number | null, suffix: string, decimals = 1) {
  return value == null ? "—" : `${value.toFixed(decimals)} ${suffix}`;
}

export function popupFields(device: RainGaugeMapDevice) {
  const direction = windDirectionPresentation(device.latest.wind_direction_deg);
  return [
    ["Lluvia hoy", formattedMetric(device.rain_today_mm, "mm")],
    ["Temperatura", formattedMetric(device.latest.temperature_c, "°C")],
    ["Humedad", formattedMetric(device.latest.humidity_pct, "%", 0)],
    ["Viento", formattedMetric(device.latest.wind_speed_kmh, "km/h")],
    ["Dirección", direction ? `${formatWindDirection(direction.degrees)} → ${direction.to}` : "—"]
  ] as const;
}
