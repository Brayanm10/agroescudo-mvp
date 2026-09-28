import type { BoundaryGeoJson, GeoJsonPosition } from "@/lib/types";
import { geometryPositions } from "./configuration-model";

export type MapMode = "satellite" | "hybrid";

export type LocationSearchResult = {
  id: string;
  primary: string;
  secondary: string;
  context: string[];
  center: GeoJsonPosition;
  bbox: [number, number, number, number] | null;
  source: "coordinates" | "maptiler" | "geolocation";
};

export type MapCameraTarget =
  | { kind: "center"; center: GeoJsonPosition; zoom: number }
  | { kind: "bounds"; bounds: [[number, number], [number, number]]; maxZoom?: number };

export type MapCameraCommand = MapCameraTarget & { id: number; source: "initial" | "search" | "geolocation" | "site" | "parcel" };

type MapTilerFeature = {
  id?: string;
  text?: string;
  place_name?: string;
  center?: number[];
  bbox?: number[];
  context?: Array<{ text?: string }>;
};

const BOLIVIA_BBOX = "-69.65,-22.90,-57.45,-9.67";
const SESSION_SEARCH_KEY = "agroescudo:pluviometry:last-location-search";

export function loadLastSessionSearch(storage: Pick<Storage, "getItem"> | undefined): LocationSearchResult | null {
  if (!storage) return null;
  try {
    const value = JSON.parse(storage.getItem(SESSION_SEARCH_KEY) ?? "null") as Partial<LocationSearchResult> | null;
    if (!value || typeof value.id !== "string" || typeof value.primary !== "string" || typeof value.secondary !== "string" || !Array.isArray(value.context) || !Array.isArray(value.center) || value.center.length !== 2 || !value.center.every(Number.isFinite) || !["coordinates", "maptiler", "geolocation"].includes(value.source ?? "")) return null;
    return value as LocationSearchResult;
  } catch {
    return null;
  }
}

export function saveLastSessionSearch(storage: Pick<Storage, "setItem"> | undefined, result: LocationSearchResult) {
  storage?.setItem(SESSION_SEARCH_KEY, JSON.stringify(result));
}

export function parseCoordinateQuery(query: string): GeoJsonPosition | null {
  const match = query.trim().match(/^([+-]?\d+(?:\.\d+)?)\s*[,;]\s*([+-]?\d+(?:\.\d+)?)$/);
  if (!match) return null;
  const latitude = Number(match[1]);
  const longitude = Number(match[2]);
  if (!Number.isFinite(latitude) || !Number.isFinite(longitude) || latitude < -90 || latitude > 90 || longitude < -180 || longitude > 180) return null;
  return [longitude, latitude];
}

export function coordinateSearchResult(position: GeoJsonPosition, source: "coordinates" | "geolocation" = "coordinates"): LocationSearchResult {
  const [longitude, latitude] = position;
  return {
    id: `${source}:${latitude.toFixed(6)},${longitude.toFixed(6)}`,
    primary: source === "geolocation" ? "Mi ubicación aproximada" : "Coordenadas",
    secondary: `${latitude.toFixed(6)}, ${longitude.toFixed(6)}`,
    context: source === "geolocation" ? ["Ubicación proporcionada por el navegador"] : ["Punto ingresado manualmente"],
    center: position,
    bbox: null,
    source
  };
}

export function normalizeMapTilerFeatures(features: MapTilerFeature[]): LocationSearchResult[] {
  return features.flatMap((feature, index) => {
    if (!Array.isArray(feature.center) || feature.center.length < 2) return [];
    const longitude = Number(feature.center[0]);
    const latitude = Number(feature.center[1]);
    if (!Number.isFinite(longitude) || !Number.isFinite(latitude)) return [];
    const primary = feature.text?.trim() || feature.place_name?.split(",")[0]?.trim() || "Resultado";
    const secondary = feature.place_name?.split(",").map((part) => part.trim()).filter((part) => part && part.toLocaleLowerCase("es") !== primary.toLocaleLowerCase("es")).join(", ") || "Bolivia";
    const context = [primary, ...(feature.context ?? []).map((item) => item.text?.trim()).filter((item): item is string => Boolean(item))]
      .filter((item, itemIndex, values) => values.findIndex((value) => value.toLocaleLowerCase("es") === item.toLocaleLowerCase("es")) === itemIndex)
      .slice(0, 3);
    const bbox = Array.isArray(feature.bbox) && feature.bbox.length >= 4 && feature.bbox.slice(0, 4).every((value) => Number.isFinite(Number(value)))
      ? feature.bbox.slice(0, 4).map(Number) as [number, number, number, number]
      : null;
    return [{ id: feature.id ?? `maptiler:${index}:${longitude}:${latitude}`, primary, secondary, context, center: [longitude, latitude] as GeoJsonPosition, bbox, source: "maptiler" as const }];
  });
}

export async function searchMapTilerLocations(query: string, apiKey: string | null | undefined, signal?: AbortSignal): Promise<LocationSearchResult[]> {
  const trimmed = query.trim();
  if (!trimmed) return [];
  const coordinates = parseCoordinateQuery(trimmed);
  if (coordinates) return [coordinateSearchResult(coordinates)];
  if (!apiKey?.trim()) throw new Error("El buscador no está disponible porque falta la configuración de mapas.");
  const parameters = new URLSearchParams({ key: apiKey.trim(), language: "es", limit: "5", bbox: BOLIVIA_BBOX, autocomplete: "false" });
  const response = await fetch(`https://api.maptiler.com/geocoding/${encodeURIComponent(trimmed)}.json?${parameters}`, { method: "GET", signal });
  if (!response.ok) throw new Error(response.status === 403 ? "MapTiler rechazó la búsqueda. Revisa la restricción por dominio." : "No se pudo consultar el buscador de lugares.");
  const payload = await response.json() as { features?: MapTilerFeature[] };
  return normalizeMapTilerFeatures(payload.features ?? []);
}

export function requestCurrentPosition(geolocation: Geolocation | undefined): Promise<LocationSearchResult> {
  if (!geolocation) return Promise.reject(new Error("Tu navegador no ofrece acceso a ubicación."));
  return new Promise((resolve, reject) => {
    geolocation.getCurrentPosition(
      (position) => resolve(coordinateSearchResult([position.coords.longitude, position.coords.latitude], "geolocation")),
      (reason) => reject(new Error(reason.code === 1 ? "Permiso de ubicación denegado. Puedes buscar el lugar manualmente." : "No se pudo obtener tu ubicación. Intenta buscar el lugar manualmente.")),
      { enableHighAccuracy: true, timeout: 10000, maximumAge: 60000 }
    );
  });
}

export function cameraTargetForResult(result: LocationSearchResult): MapCameraTarget {
  return result.bbox
    ? { kind: "bounds", bounds: [[result.bbox[0], result.bbox[1]], [result.bbox[2], result.bbox[3]]], maxZoom: 15 }
    : { kind: "center", center: result.center, zoom: result.source === "geolocation" || result.source === "coordinates" ? 16 : 13 };
}

export function cameraTargetForBoundary(boundary: BoundaryGeoJson | null | undefined): MapCameraTarget | null {
  const positions = geometryPositions(boundary);
  if (!positions.length) return null;
  const [firstLongitude, firstLatitude] = positions[0];
  let west = firstLongitude, east = firstLongitude, south = firstLatitude, north = firstLatitude;
  positions.forEach(([longitude, latitude]) => { west = Math.min(west, longitude); east = Math.max(east, longitude); south = Math.min(south, latitude); north = Math.max(north, latitude); });
  return { kind: "bounds", bounds: [[west, south], [east, north]], maxZoom: 17 };
}

export function initialCameraTarget(input: { parcelBoundary?: BoundaryGeoJson | null; siteBoundary?: BoundaryGeoJson | null; siteCenter?: GeoJsonPosition | null; lastSearch?: LocationSearchResult | null }): MapCameraTarget {
  return cameraTargetForBoundary(input.parcelBoundary)
    ?? cameraTargetForBoundary(input.siteBoundary)
    ?? (input.siteCenter ? { kind: "center", center: input.siteCenter, zoom: 15 } : null)
    ?? (input.lastSearch ? cameraTargetForResult(input.lastSearch) : null)
    ?? { kind: "center", center: [-64.7, -16.7], zoom: 5 };
}
