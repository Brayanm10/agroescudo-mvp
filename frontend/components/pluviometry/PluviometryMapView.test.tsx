import { renderToStaticMarkup } from "react-dom/server";
import { afterEach, describe, expect, it, vi } from "vitest";
import { getPluviometryMapSnapshot } from "@/lib/api";
import type { PluviometryMapSnapshot, PluviometrySite } from "@/lib/types";
import { PluviometryMapContent } from "./PluviometryMapView";
import { buildSatelliteStyle, MapPopupCard, RainGaugeMap } from "./RainGaugeMap";
import {
  locatedDevices,
  mapViewport,
  parcelFeatureCollection,
  pluviometryQueryPath,
  popupFields,
  rainGaugeDetailPath,
  resolveSelectedSite,
  siteFeatureCollection,
  STATUS_PRESENTATION
} from "./map-model";

const sites: PluviometrySite[] = [
  { id: 12, name: "Predio Quillacollo", latitude: -17.39, longitude: -66.16, timezone: "America/La_Paz", rain_gauge_count: 2 },
  { id: 18, name: "Predio Sacaba", latitude: null, longitude: null, timezone: "America/La_Paz", rain_gauge_count: 0 }
];

const snapshot: PluviometryMapSnapshot = {
  site: {
    id: 12,
    name: "Predio Quillacollo",
    latitude: -17.39,
    longitude: -66.16,
    timezone: "America/La_Paz",
    boundary_geojson: { type: "Polygon", coordinates: [[[-66.2, -17.42], [-66.1, -17.42], [-66.2, -17.42]]] }
  },
  parcels: [{
    id: 48,
    name: "Parcela Norte",
    surface_hectares: 4.8,
    boundary_geojson: { type: "MultiPolygon", coordinates: [[[[-66.18, -17.4], [-66.14, -17.4], [-66.18, -17.4]]]] }
  }],
  devices: [
    {
      id: 71,
      device_id: "PLUV-001",
      name: "Pluviómetro P-01",
      storage_unit_id: 48,
      parcel_name: "Parcela Norte",
      latitude: -17.39,
      longitude: -66.16,
      status: "online",
      last_seen_at: "2026-09-24T12:00:00Z",
      latest: { temperature_c: 23.4, humidity_pct: 71, wind_speed_kmh: null, wind_direction_deg: 45, battery_pct: 86 },
      rain_today_mm: 17.6
    },
    {
      id: 72,
      device_id: "PLUV-002",
      name: "Pluviómetro sin coordenadas",
      storage_unit_id: 48,
      parcel_name: "Parcela Norte",
      latitude: null,
      longitude: null,
      status: "offline",
      last_seen_at: null,
      latest: { temperature_c: null, humidity_pct: null, wind_speed_kmh: null, wind_direction_deg: null, battery_pct: null },
      rain_today_mm: null
    }
  ]
};

afterEach(() => vi.unstubAllGlobals());

describe("PluviometryMapView", () => {
  it("renders the real site selector and selected site", () => {
    const markup = renderToStaticMarkup(
      <PluviometryMapContent sites={sites} selectedSiteId={12} snapshot={snapshot} sitesLoading={false} mapLoading={false} error={null} onSelectSite={() => undefined} onOpenDevice={() => undefined} mapApiKey={null} />
    );
    expect(markup).toContain("Predio Quillacollo");
    expect(markup).toContain("Predio Sacaba");
    expect(markup).toContain("Parcelas autorizadas");
  });

  it("renders a professional empty state with zero authorized sites", () => {
    const markup = renderToStaticMarkup(
      <PluviometryMapContent sites={[]} selectedSiteId={null} snapshot={null} sitesLoading={false} mapLoading={false} error={null} onSelectSite={() => undefined} onOpenDevice={() => undefined} />
    );
    expect(markup).toContain("Sin predios disponibles");
  });

  it("resolves authorized query selection and falls back when it is unauthorized", () => {
    expect(resolveSelectedSite(sites, "18")?.id).toBe(18);
    expect(resolveSelectedSite(sites, "999")?.id).toBe(12);
    expect(pluviometryQueryPath(18)).toBe("/pluviometria?predio=18");
  });

  it("loads a site snapshot through the centralized API client", async () => {
    const fetchMock = vi.fn().mockResolvedValue(new Response(JSON.stringify(snapshot), { status: 200, headers: { "Content-Type": "application/json" } }));
    vi.stubGlobal("fetch", fetchMock);
    await expect(getPluviometryMapSnapshot("token", 12)).resolves.toEqual(snapshot);
    expect(fetchMock).toHaveBeenCalledWith("http://127.0.0.1:8010/api/pluviometry/sites/12/map", expect.objectContaining({ method: "GET" }));
  });

  it("transforms site and parcel Polygon/MultiPolygon GeoJSON", () => {
    expect(siteFeatureCollection(snapshot).features[0].geometry.type).toBe("Polygon");
    expect(parcelFeatureCollection(snapshot).features[0].geometry.type).toBe("MultiPolygon");
    expect(mapViewport(snapshot).kind).toBe("bounds");
  });

  it("creates markers only for devices with real coordinates", () => {
    expect(locatedDevices(snapshot).map((device) => device.id)).toEqual([71]);
  });

  it("defines distinct marker colors for every backend status", () => {
    expect(new Set(Object.values(STATUS_PRESENTATION).map((item) => item.color)).size).toBe(4);
    expect(STATUS_PRESENTATION.online.label).toBe("En línea");
    expect(STATUS_PRESENTATION.critical.color).toBe("#dc2626");
  });

  it("builds popup values without inventing missing metrics", () => {
    expect(popupFields(snapshot.devices[0])).toContainEqual(["Lluvia hoy", "17.6 mm"]);
    expect(popupFields(snapshot.devices[0])).toContainEqual(["Viento", "—"]);
    expect(popupFields(snapshot.devices[0])).toContainEqual(["Dirección", "NE · 45° → SO"]);
    expect(popupFields(snapshot.devices[1]).every(([, value]) => value === "—")).toBe(true);
  });

  it("renders the DEMO popup with wind origin and destination", () => {
    const markup = renderToStaticMarkup(
      <MapPopupCard device={snapshot.devices[0]} isDemo onClose={() => undefined} onOpen={() => undefined} />
    );
    expect(markup).toContain("DEMO · ubicación aproximada");
    expect(markup).toContain("NE · 45° → SO");
    expect(markup).toContain("Ver pluviómetro");
  });

  it("routes the popup action to the authenticated placeholder", () => {
    expect(rainGaugeDetailPath(71)).toBe("/pluviometria/pluviometros/71");
  });

  it("keeps the professional fallback without a MapTiler key while data remains available", () => {
    const markup = renderToStaticMarkup(<RainGaugeMap snapshot={snapshot} apiKey={null} />);
    expect(markup).toContain("Mapa no configurado");
    expect(markup).toContain("Los datos del predio siguen disponibles");
  });

  it("keeps MapTiler as the only base source", () => {
    const style = buildSatelliteStyle("public-test-key");
    expect(Object.keys(style.sources)).toEqual(["satellite"]);
    expect(style.sources.satellite).toMatchObject({
      type: "raster",
      url: "https://api.maptiler.com/tiles/satellite-v2/tiles.json?key=public-test-key"
    });
    expect(style.layers).toEqual([{ id: "satellite-base", type: "raster", source: "satellite" }]);
  });

  it("keeps the MapLibre container filling the map after MapLibre adds its relative-position class", () => {
    const markup = renderToStaticMarkup(<RainGaugeMap snapshot={snapshot} apiKey="public-test-key" />);
    expect(markup).toContain('style="position:absolute;inset:0"');
  });
});
