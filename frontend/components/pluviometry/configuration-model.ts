import type { BoundaryGeoJson, GeoJsonPosition } from "@/lib/types";

export function closePolygon(vertices: GeoJsonPosition[]): BoundaryGeoJson | null {
  const unique = new Set(vertices.map(([longitude, latitude]) => `${longitude}:${latitude}`));
  if (vertices.length < 3 || unique.size < 3) return null;
  return { type: "Polygon", coordinates: [[...vertices, vertices[0]]] };
}

export function boundaryStatus(boundary: BoundaryGeoJson | null | undefined) {
  return boundary ? "Límite definido" : "Límite no definido";
}

export function geometryPositions(boundary: BoundaryGeoJson | null | undefined): GeoJsonPosition[] {
  if (!boundary) return [];
  return boundary.type === "Polygon"
    ? boundary.coordinates.flat()
    : boundary.coordinates.flat(2);
}

function pointInRing([x, y]: GeoJsonPosition, ring: GeoJsonPosition[]) {
  let inside = false;
  for (let current = 0, previous = ring.length - 1; current < ring.length; previous = current++) {
    const [xi, yi] = ring[current];
    const [xj, yj] = ring[previous];
    const intersects = yi > y !== yj > y && x < ((xj - xi) * (y - yi)) / (yj - yi) + xi;
    if (intersects) inside = !inside;
  }
  return inside;
}

export function pointInsideBoundary(position: GeoJsonPosition, boundary: BoundaryGeoJson | null | undefined) {
  if (!boundary || boundary.type !== "Polygon" || !boundary.coordinates[0]?.length) return true;
  return pointInRing(position, boundary.coordinates[0]);
}

export function parcelAppearsOutside(parcel: BoundaryGeoJson, site: BoundaryGeoJson | null | undefined) {
  if (!site) return false;
  const siteRings = site.type === "Polygon"
    ? [site.coordinates[0]]
    : site.coordinates.map((polygon) => polygon[0]);
  return geometryPositions(parcel).some((position) => !siteRings.some((ring) => pointInRing(position, ring)));
}

export function municipalityLabel(municipality: string | null | undefined) {
  return municipality?.trim() || "Sin municipio registrado";
}
