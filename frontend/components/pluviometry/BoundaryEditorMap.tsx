"use client";

import { useEffect, useRef, useState } from "react";
import type { MouseEvent as ReactMouseEvent } from "react";
import type { GeoJSONSource, Map as MapLibreMap, MapMouseEvent } from "maplibre-gl";
import "maplibre-gl/dist/maplibre-gl.css";
import type { BoundaryGeoJson, Device, GeoJsonPosition, StorageUnit } from "@/lib/types";
import { buildSatelliteStyle, BOLIVIA_INITIAL_VIEW } from "./RainGaugeMap";
import type { MapCameraCommand, MapMode } from "./location-assistant";

type Props = {
  siteBoundary: BoundaryGeoJson | null;
  parcels: StorageUnit[];
  selectedParcelId: number | null;
  draftBoundary: BoundaryGeoJson | null;
  draftVertices: GeoJsonPosition[];
  drawing: boolean;
  onAddVertex: (position: GeoJsonPosition) => void;
  devices?: Device[];
  provisionalLocation?: GeoJsonPosition | null;
  selectingLocation?: boolean;
  onSelectLocation?: (position: GeoJsonPosition) => void;
  apiKey?: string | null;
  mapMode?: MapMode;
  cameraCommand?: MapCameraCommand | null;
};

const emptyCollection = { type: "FeatureCollection" as const, features: [] };

function featureCollection(boundaries: Array<{ id: number | string; geometry: BoundaryGeoJson | null | undefined }>) {
  return {
    type: "FeatureCollection" as const,
    features: boundaries.flatMap(({ id, geometry }) => geometry ? [{ type: "Feature" as const, id, properties: { id }, geometry }] : [])
  };
}

export function BoundaryEditorMap({ siteBoundary, parcels, selectedParcelId, draftBoundary, draftVertices, drawing, onAddVertex, devices = [], provisionalLocation = null, selectingLocation = false, onSelectLocation, apiKey, mapMode = "satellite", cameraCommand = null }: Props) {
  const containerRef = useRef<HTMLDivElement | null>(null);
  const mapRef = useRef<MapLibreMap | null>(null);
  const clickRef = useRef(onAddVertex);
  const locationRef = useRef(onSelectLocation);
  const selectingRef = useRef(selectingLocation);
  const modeRef = useRef<MapMode>(mapMode);
  const [ready, setReady] = useState(false);
  const [failed, setFailed] = useState(false);
  const mapKey = (apiKey === undefined ? process.env.NEXT_PUBLIC_MAPTILER_KEY : apiKey)?.trim();
  clickRef.current = onAddVertex;
  locationRef.current = onSelectLocation;
  selectingRef.current = selectingLocation;

  useEffect(() => {
    if (!mapKey || !containerRef.current || mapRef.current) return;
    let cancelled = false;
    void import("maplibre-gl").then((maplibregl) => {
      if (cancelled || !containerRef.current) return;
      maplibregl.setWorkerUrl("/maplibre/maplibre-gl-worker.mjs");
      const map = new maplibregl.Map({ container: containerRef.current, style: configurationMapStyle(mapKey, modeRef.current), ...BOLIVIA_INITIAL_VIEW, dragRotate: false, pitchWithRotate: false });
      map.addControl(new maplibregl.NavigationControl({ showCompass: true, showZoom: true, visualizePitch: false }), "top-right");
      map.on("click", (event: MapMouseEvent) => selectingRef.current ? locationRef.current?.([event.lngLat.lng, event.lngLat.lat]) : clickRef.current([event.lngLat.lng, event.lngLat.lat]));
      map.once("load", () => {
        if (cancelled) return;
        addSourcesAndLayers(map);
        setReady(true);
      });
      mapRef.current = map;
    }).catch(() => setFailed(true));
    return () => { cancelled = true; mapRef.current?.remove(); mapRef.current = null; };
  }, [mapKey]);

  useEffect(() => {
    const map = mapRef.current;
    if (!map || !mapKey || modeRef.current === mapMode) return;
    modeRef.current = mapMode;
    setReady(false);
    map.setStyle(configurationMapStyle(mapKey, mapMode));
    map.once("style.load", () => {
      addSourcesAndLayers(map);
      setReady(true);
    });
  }, [mapKey, mapMode]);

  useEffect(() => {
    const map = mapRef.current;
    if (!ready || !map) return;
    setSource(map, "config-site", featureCollection([{ id: "site", geometry: siteBoundary }]));
    setSource(map, "config-parcels", featureCollection(parcels.filter((parcel) => parcel.id !== selectedParcelId).map((parcel) => ({ id: parcel.id, geometry: parcel.boundary_geojson }))));
    setSource(map, "config-selected", featureCollection(parcels.filter((parcel) => parcel.id === selectedParcelId).map((parcel) => ({ id: parcel.id, geometry: parcel.boundary_geojson }))));
    setSource(map, "config-draft", featureCollection([{ id: "draft", geometry: draftBoundary }]));
    setSource(map, "config-draft-line", draftVertices.length > 1 ? {
      type: "Feature", properties: {}, geometry: { type: "LineString", coordinates: draftVertices }
    } : emptyCollection);
    setSource(map, "config-draft-points", {
      type: "FeatureCollection", features: draftVertices.map((coordinates, index) => ({ type: "Feature", properties: { index }, geometry: { type: "Point", coordinates } }))
    });
    setSource(map, "config-devices", { type: "FeatureCollection", features: devices.filter((device) => device.latitude != null && device.longitude != null).map((device) => ({ type: "Feature", properties: { id: device.id, active: device.is_active }, geometry: { type: "Point", coordinates: [device.longitude!, device.latitude!] } })) });
    setSource(map, "config-provisional", provisionalLocation ? { type: "Feature", properties: {}, geometry: { type: "Point", coordinates: provisionalLocation } } : emptyCollection);
    map.getCanvas().style.cursor = drawing || selectingLocation ? "crosshair" : "grab";

  }, [devices, draftBoundary, draftVertices, drawing, parcels, provisionalLocation, ready, selectedParcelId, selectingLocation, siteBoundary]);

  useEffect(() => {
    const map = mapRef.current;
    if (!ready || !map || !cameraCommand) return;
    if (cameraCommand.kind === "bounds") map.fitBounds(cameraCommand.bounds, { padding: 64, maxZoom: cameraCommand.maxZoom ?? 16, duration: cameraCommand.source === "initial" ? 0 : 700 });
    else map.flyTo({ center: [cameraCommand.center[0], cameraCommand.center[1]], zoom: cameraCommand.zoom, duration: cameraCommand.source === "initial" ? 0 : 700, essential: true });
  }, [cameraCommand, ready]);

  if (!mapKey || failed) return <div className="flex min-h-[28rem] items-center justify-center rounded-2xl border border-dashed border-slate-300 bg-slate-50 p-6 text-center text-sm text-slate-600">Configura MapTiler para utilizar el editor cartográfico.</div>;
  function captureMapPoint(event: ReactMouseEvent<HTMLButtonElement>) {
    const map = mapRef.current;
    if (!map) return;
    const rect = event.currentTarget.getBoundingClientRect();
    const coordinate = map.unproject([event.clientX - rect.left, event.clientY - rect.top]);
    const position: GeoJsonPosition = [coordinate.lng, coordinate.lat];
    if (selectingLocation) onSelectLocation?.(position); else onAddVertex(position);
  }
  return <div className="relative min-h-[28rem] overflow-hidden rounded-2xl bg-slate-200 lg:min-h-[38rem]" role="region" aria-label="Editor cartográfico de límites"><div ref={containerRef} className="absolute inset-0" style={{ position: "absolute", inset: 0 }} />{(drawing || selectingLocation) && ready ? <button type="button" className="absolute inset-0 z-10 cursor-crosshair bg-transparent" aria-label={selectingLocation ? "Área de selección: haz clic para ubicar el pluviómetro" : "Área de dibujo: haz clic para agregar un vértice"} onClick={captureMapPoint} /> : null}{!ready ? <div className="absolute inset-0 flex items-center justify-center bg-slate-900/15"><span className="rounded-full bg-white px-4 py-2 text-xs font-bold">Cargando mapa</span></div> : null}</div>;
}

function setSource(map: MapLibreMap, id: string, data: object) {
  (map.getSource(id) as GeoJSONSource | undefined)?.setData(data as never);
}

function addSourcesAndLayers(map: MapLibreMap) {
  ["config-site", "config-parcels", "config-selected", "config-draft", "config-draft-line", "config-draft-points", "config-devices", "config-provisional"].forEach((id) => map.addSource(id, { type: "geojson", data: emptyCollection }));
  map.addLayer({ id: "config-site-fill", type: "fill", source: "config-site", paint: { "fill-color": "#f8fafc", "fill-opacity": 0.06 } });
  map.addLayer({ id: "config-site-line", type: "line", source: "config-site", paint: { "line-color": "#ffffff", "line-width": 4, "line-opacity": 0.95 } });
  map.addLayer({ id: "config-parcels-fill", type: "fill", source: "config-parcels", paint: { "fill-color": "#10b981", "fill-opacity": 0.1 } });
  map.addLayer({ id: "config-parcels-line", type: "line", source: "config-parcels", paint: { "line-color": "#6ee7b7", "line-width": 2 } });
  map.addLayer({ id: "config-selected-fill", type: "fill", source: "config-selected", paint: { "fill-color": "#fbbf24", "fill-opacity": 0.18 } });
  map.addLayer({ id: "config-selected-line", type: "line", source: "config-selected", paint: { "line-color": "#fbbf24", "line-width": 4 } });
  map.addLayer({ id: "config-draft-fill", type: "fill", source: "config-draft", paint: { "fill-color": "#22d3ee", "fill-opacity": 0.18 } });
  map.addLayer({ id: "config-draft-outline", type: "line", source: "config-draft", paint: { "line-color": "#22d3ee", "line-width": 4 } });
  map.addLayer({ id: "config-draft-line-layer", type: "line", source: "config-draft-line", paint: { "line-color": "#22d3ee", "line-width": 3, "line-dasharray": [2, 1] } });
  map.addLayer({ id: "config-draft-points-layer", type: "circle", source: "config-draft-points", paint: { "circle-radius": 6, "circle-color": "#f8fafc", "circle-stroke-width": 3, "circle-stroke-color": "#0891b2" } });
  map.addLayer({ id: "config-devices-layer", type: "circle", source: "config-devices", paint: { "circle-radius": 8, "circle-color": ["case", ["get", "active"], "#10b981", "#64748b"], "circle-stroke-width": 3, "circle-stroke-color": "#ffffff" } });
  map.addLayer({ id: "config-provisional-layer", type: "circle", source: "config-provisional", paint: { "circle-radius": 10, "circle-color": "#f97316", "circle-stroke-width": 4, "circle-stroke-color": "#ffffff" } });
}

function configurationMapStyle(apiKey: string, mode: MapMode) {
  return mode === "hybrid"
    ? `https://api.maptiler.com/maps/hybrid/style.json?key=${encodeURIComponent(apiKey)}`
    : buildSatelliteStyle(apiKey);
}
