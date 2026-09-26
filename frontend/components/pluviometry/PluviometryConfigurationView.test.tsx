import { renderToStaticMarkup } from "react-dom/server";
import { afterEach, describe, expect, it, vi } from "vitest";
import { createAdminDevice, createAdminStorageUnit, getAdminDevices, getSites, getStorageUnits, updateAdminDevice, updateSite } from "@/lib/api";
import type { BoundaryGeoJson, Site, StorageUnit } from "@/lib/types";
import { ConfigurationAccessDenied } from "./PluviometryConfigurationView";
import { PluviometryMapContent } from "./PluviometryMapView";
import { boundaryStatus, closePolygon, geometryPositions, municipalityLabel, parcelAppearsOutside, pointInsideBoundary } from "./configuration-model";

const polygon: BoundaryGeoJson = { type: "Polygon", coordinates: [[[-66.2, -17.4], [-66.1, -17.4], [-66.1, -17.3], [-66.2, -17.4]]] };
const multipolygon: BoundaryGeoJson = { type: "MultiPolygon", coordinates: [[[[-66.2, -17.4], [-66.1, -17.4], [-66.1, -17.3], [-66.2, -17.4]]]] };
const site: Site = { id: 3, company_id: 2, name: "Demo Quillacollo", location: "Quillacollo", municipality: "Quillacollo", latitude: -17.39, longitude: -66.28, timezone: "America/La_Paz", boundary_geojson: polygon, created_at: "2026-09-25T00:00:00Z" };
const parcel: StorageUnit = { id: 7, company_id: 2, site_id: 3, name: "Parcela QA DEMO", unit_type: "field", operation_type: "field", capacity_tons: null, surface_hectares: 1.2, location: null, crop_type: "Maíz", boundary_geojson: polygon, is_active: true, assigned_technician_id: null, assigned_client_id: null, last_report_generated_at: null, created_at: "2026-09-25T00:00:00Z", updated_at: null };

afterEach(() => vi.unstubAllGlobals());

describe("PluviometryConfigurationView", () => {
  it("shows the configuration access only when the caller enables admin controls", () => {
    const common = { sites: [{ id: 3, name: site.name, latitude: site.latitude ?? null, longitude: site.longitude ?? null, timezone: site.timezone ?? "America/La_Paz", rain_gauge_count: 0 }], selectedSiteId: 3, snapshot: null, sitesLoading: false, mapLoading: false, error: null, onSelectSite: () => undefined, onOpenDevice: () => undefined };
    expect(renderToStaticMarkup(<PluviometryMapContent {...common} canConfigure />)).toContain("/pluviometria/configuracion");
    expect(renderToStaticMarkup(<PluviometryMapContent {...common} canConfigure={false} />)).not.toContain("/pluviometria/configuracion");
  });

  it("renders no editing controls for a non-admin direct URL", () => {
    const markup = renderToStaticMarkup(<ConfigurationAccessDenied />);
    expect(markup).toContain("reservada para administración");
    expect(markup).not.toContain("Guardar predio");
    expect(markup).not.toContain("Nueva parcela");
  });

  it("starts and closes a valid three-vertex drawing", () => {
    const result = closePolygon([[-66.2, -17.4], [-66.1, -17.4], [-66.1, -17.3]]);
    expect(result?.type).toBe("Polygon");
    expect(result?.coordinates[0][0]).toEqual(result?.coordinates[0].at(-1));
  });

  it("keeps an incomplete drawing unpersistable so it can be cancelled", () => {
    expect(closePolygon([[-66.2, -17.4], [-66.1, -17.4]])).toBeNull();
    expect(closePolygon([])).toBeNull();
  });

  it("preserves existing MultiPolygon geometry for visualization", () => {
    expect(geometryPositions(multipolygon)).toHaveLength(4);
    expect(boundaryStatus(multipolygon)).toBe("Límite definido");
  });

  it("represents a site without boundary and without municipality honestly", () => {
    expect(boundaryStatus(null)).toBe("Límite no definido");
    expect(municipalityLabel(null)).toBe("Sin municipio registrado");
  });

  it("warns when a parcel is clearly outside the site", () => {
    const outside: BoundaryGeoJson = { type: "Polygon", coordinates: [[[-65, -16], [-64.9, -16], [-64.9, -15.9], [-65, -16]]] };
    expect(parcelAppearsOutside(outside, polygon)).toBe(true);
  });

  it("does not warn for vertices inside the site", () => {
    const inside: BoundaryGeoJson = { type: "Polygon", coordinates: [[[-66.18, -17.39], [-66.12, -17.39], [-66.12, -17.35], [-66.18, -17.39]]] };
    expect(parcelAppearsOutside(inside, polygon)).toBe(false);
  });

  it("accepts a gauge point inside a Polygon and rejects an exterior point", () => {
    expect(pointInsideBoundary([-66.16, -17.38], polygon)).toBe(true);
    expect(pointInsideBoundary([-65, -16], polygon)).toBe(false);
  });

  it("does not invent containment when the parcel has no valid Polygon", () => {
    expect(pointInsideBoundary([-65, -16], null)).toBe(true);
    expect(pointInsideBoundary([-65, -16], multipolygon)).toBe(true);
  });

  it("loads real sites and parcels through scoped endpoints", async () => {
    const fetchMock = vi.fn()
      .mockResolvedValueOnce(new Response(JSON.stringify([site]), { status: 200 }))
      .mockResolvedValueOnce(new Response(JSON.stringify([parcel]), { status: 200 }));
    vi.stubGlobal("fetch", fetchMock);
    await expect(getSites("token")).resolves.toEqual([site]);
    await expect(getStorageUnits("token", site.id)).resolves.toEqual([parcel]);
    expect(fetchMock.mock.calls[1][0]).toContain("/api/storage-units?site_id=3");
  });

  it("sends an explicit PATCH only when saving the site", async () => {
    const fetchMock = vi.fn().mockResolvedValue(new Response(JSON.stringify({ ...site, boundary_geojson: multipolygon }), { status: 200 }));
    vi.stubGlobal("fetch", fetchMock);
    await updateSite("token", site.id, { boundary_geojson: multipolygon });
    expect(fetchMock).toHaveBeenCalledWith(expect.stringContaining("/api/sites/3"), expect.objectContaining({ method: "PATCH", body: JSON.stringify({ boundary_geojson: multipolygon }) }));
  });

  it("creates a field parcel associated with the selected site and persists geometry", async () => {
    const fetchMock = vi.fn().mockResolvedValue(new Response(JSON.stringify(parcel), { status: 200 }));
    vi.stubGlobal("fetch", fetchMock);
    await createAdminStorageUnit("token", { company_id: 2, site_id: 3, name: parcel.name, unit_type: "field", operation_type: "field", capacity_tons: null, boundary_geojson: polygon });
    const body = JSON.parse(fetchMock.mock.calls[0][1].body as string);
    expect(body).toMatchObject({ site_id: 3, operation_type: "field", boundary_geojson: polygon });
  });

  it("installs through the canonical admin device endpoint with the rain template", async () => {
    const created = { id: 9, company_id: 2, site_id: 3, storage_unit_id: 7, external_id: "PLUV-QA-003", name: "P-03 QA DEMO", device_type: "rain_gauge", latitude: -17.38, longitude: -66.16, template_code: "RAIN_GAUGE_BASE", expected_reading_interval_minutes: 15, operational_status: "awaiting_first_reading", is_active: true, created_at: "2026-09-25T00:00:00Z", last_seen_at: null, updated_at: null, api_key: "secret" };
    const fetchMock = vi.fn().mockResolvedValue(new Response(JSON.stringify(created), { status: 201 }));
    vi.stubGlobal("fetch", fetchMock);
    await createAdminDevice("token", { company_id: 2, site_id: 3, storage_unit_id: 7, external_id: "PLUV-QA-003", name: "P-03 QA DEMO", device_type: "rain_gauge", latitude: -17.38, longitude: -66.16, expected_reading_interval_minutes: 15, template_code: "RAIN_GAUGE_BASE", is_active: true });
    expect(fetchMock.mock.calls[0][0]).toContain("/api/admin/devices");
    expect(JSON.parse(fetchMock.mock.calls[0][1].body as string)).toMatchObject({ device_type: "rain_gauge", template_code: "RAIN_GAUGE_BASE", expected_reading_interval_minutes: 15 });
  });

  it("loads and edits installed devices without sending a mutable physical id", async () => {
    const device = { id: 9, company_id: 2, site_id: 3, storage_unit_id: 7, external_id: "PLUV-QA-003", name: "P-03", device_type: "rain_gauge", is_active: true, created_at: "2026-09-25T00:00:00Z", last_seen_at: null, updated_at: null };
    const fetchMock = vi.fn()
      .mockResolvedValueOnce(new Response(JSON.stringify([device]), { status: 200 }))
      .mockResolvedValueOnce(new Response(JSON.stringify({ ...device, name: "P-03 editado" }), { status: 200 }));
    vi.stubGlobal("fetch", fetchMock);
    await expect(getAdminDevices("token")).resolves.toHaveLength(1);
    await updateAdminDevice("token", 9, { name: "P-03 editado", expected_reading_interval_minutes: 30 });
    expect(JSON.parse(fetchMock.mock.calls[1][1].body as string)).not.toHaveProperty("external_id");
  });

  it("surfaces a save error instead of treating it as persisted", async () => {
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue(new Response(JSON.stringify({ detail: "GeoJSON inválido" }), { status: 422, headers: { "Content-Type": "application/json" } })));
    await expect(updateSite("token", site.id, { boundary_geojson: polygon })).rejects.toMatchObject({ status: 422 });
  });
});
