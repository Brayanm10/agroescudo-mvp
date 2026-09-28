import { renderToStaticMarkup } from "react-dom/server";
import { afterEach, describe, expect, it, vi } from "vitest";
import type { BoundaryGeoJson } from "@/lib/types";
import { SearchFeedback } from "./LocationAssistant";
import { cameraTargetForBoundary, cameraTargetForResult, initialCameraTarget, loadLastSessionSearch, parseCoordinateQuery, requestCurrentPosition, saveLastSessionSearch, searchMapTilerLocations } from "./location-assistant";

const parcelBoundary: BoundaryGeoJson = { type: "Polygon", coordinates: [[[-66.30, -17.40], [-66.25, -17.40], [-66.25, -17.35], [-66.30, -17.40]]] };
const siteBoundary: BoundaryGeoJson = { type: "Polygon", coordinates: [[[-66.40, -17.50], [-66.10, -17.50], [-66.10, -17.20], [-66.40, -17.50]]] };

afterEach(() => vi.unstubAllGlobals());

describe("location assistant", () => {
  it("searches a Bolivian place by name with MapTiler", async () => {
    const fetchMock = vi.fn().mockResolvedValue(new Response(JSON.stringify({ features: [{ id: "place.1", text: "Quillacollo", place_name: "Quillacollo, Cochabamba, Bolivia", center: [-66.2814, -17.3928], bbox: [-66.35, -17.45, -66.20, -17.30], context: [{ text: "Cochabamba" }, { text: "Bolivia" }] }] }), { status: 200 }));
    vi.stubGlobal("fetch", fetchMock);
    const results = await searchMapTilerLocations("Quillacollo, Cochabamba", "public-key");
    expect(results[0]).toMatchObject({ primary: "Quillacollo", center: [-66.2814, -17.3928], source: "maptiler" });
    expect(fetchMock.mock.calls[0][0]).toContain("api.maptiler.com/geocoding/Quillacollo%2C%20Cochabamba.json");
  });

  it("detects valid coordinates and rejects values outside geographic ranges", async () => {
    const fetchMock = vi.fn();
    vi.stubGlobal("fetch", fetchMock);
    await expect(searchMapTilerLocations("-17.3928, -66.2814", "public-key")).resolves.toMatchObject([{ center: [-66.2814, -17.3928], source: "coordinates" }]);
    expect(parseCoordinateQuery("-91, -66")).toBeNull();
    expect(fetchMock).not.toHaveBeenCalled();
  });

  it("converts a selected geocoder result into a fitBounds camera target", () => {
    expect(cameraTargetForResult({ id: "q", primary: "Quillacollo", secondary: "Cochabamba, Bolivia", context: [], center: [-66.28, -17.39], bbox: [-66.35, -17.45, -66.20, -17.30], source: "maptiler" })).toMatchObject({ kind: "bounds", bounds: [[-66.35, -17.45], [-66.20, -17.30]] });
  });

  it("uses browser geolocation after a granted permission", async () => {
    const geolocation = { getCurrentPosition: (success: PositionCallback) => success({ coords: { latitude: -17.39, longitude: -66.28 } } as GeolocationPosition) } as Geolocation;
    await expect(requestCurrentPosition(geolocation)).resolves.toMatchObject({ center: [-66.28, -17.39], source: "geolocation" });
  });

  it("returns a friendly message when geolocation is denied", async () => {
    const geolocation = { getCurrentPosition: (_success: PositionCallback, error: PositionErrorCallback) => error({ code: 1 } as GeolocationPositionError) } as Geolocation;
    await expect(requestCurrentPosition(geolocation)).rejects.toThrow("Permiso de ubicación denegado");
  });

  it("builds independent centering targets for the site and parcel", () => {
    expect(cameraTargetForBoundary(siteBoundary)).toMatchObject({ kind: "bounds", bounds: [[-66.40, -17.50], [-66.10, -17.20]] });
    expect(cameraTargetForBoundary(parcelBoundary)).toMatchObject({ kind: "bounds", bounds: [[-66.30, -17.40], [-66.25, -17.35]] });
  });

  it("renders compact loading, empty and error feedback", () => {
    expect(renderToStaticMarkup(<SearchFeedback state="loading" message={null} hasResults={false} />)).toContain("Buscando ubicación");
    expect(renderToStaticMarkup(<SearchFeedback state="empty" message="Sin resultados" hasResults={false} />)).toContain("Sin resultados");
    expect(renderToStaticMarkup(<SearchFeedback state="error" message="Error de red" hasResults={false} />)).toContain("Error de red");
  });

  it("returns an empty result set without treating it as persisted data", async () => {
    const fetchMock = vi.fn().mockResolvedValue(new Response(JSON.stringify({ features: [] }), { status: 200 }));
    vi.stubGlobal("fetch", fetchMock);
    await expect(searchMapTilerLocations("Lugar inexistente", "public-key")).resolves.toEqual([]);
    expect(fetchMock).toHaveBeenCalledTimes(1);
    expect(fetchMock.mock.calls[0][1]).toMatchObject({ method: "GET" });
  });

  it("keeps the map fallback usable when geocoding is unavailable", async () => {
    await expect(searchMapTilerLocations("Montero", null)).rejects.toThrow("falta la configuración de mapas");
    expect(initialCameraTarget({})).toEqual({ kind: "center", center: [-64.7, -16.7], zoom: 5 });
  });

  it("uses the required initial priority without modifying geometry", () => {
    const search = { id: "s", primary: "Sacaba", secondary: "Cochabamba, Bolivia", context: [], center: [-66.04, -17.40] as [number, number], bbox: null, source: "maptiler" as const };
    const target = initialCameraTarget({ parcelBoundary, siteBoundary, siteCenter: [-66.2, -17.3], lastSearch: search });
    expect(target).toEqual(cameraTargetForBoundary(parcelBoundary));
    expect(target).not.toHaveProperty("boundary_geojson");
  });

  it("keeps only the last camera search in session storage", () => {
    const values = new Map<string, string>();
    const storage = { getItem: (key: string) => values.get(key) ?? null, setItem: (key: string, value: string) => values.set(key, value) };
    const search = { id: "session", primary: "Montero", secondary: "Santa Cruz, Bolivia", context: ["Montero", "Santa Cruz", "Bolivia"], center: [-63.25, -17.34] as [number, number], bbox: null, source: "maptiler" as const };
    saveLastSessionSearch(storage, search);
    expect(loadLastSessionSearch(storage)).toEqual(search);
    expect([...values.values()][0]).not.toContain("boundary_geojson");
  });
});
