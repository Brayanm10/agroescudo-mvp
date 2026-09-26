"use client";

import { useEffect, useRef, useState } from "react";
import type { GeoJSONSource, Map as MapLibreMap, Marker, StyleSpecification } from "maplibre-gl";
import "maplibre-gl/dist/maplibre-gl.css";
import { CloudRain, MapPinned } from "lucide-react";
import type { PluviometryMapSnapshot, RainGaugeMapDevice } from "@/lib/types";
import { formatDateTimeInTimeZone } from "@/lib/format";
import {
  mapViewport,
  locatedDevices,
  parcelFeatureCollection,
  popupFields,
  siteFeatureCollection,
  STATUS_PRESENTATION
} from "./map-model";

export const BOLIVIA_INITIAL_VIEW = {
  center: [-64.68, -16.29] as [number, number],
  zoom: 4.6
};

export function buildSatelliteStyle(apiKey: string): StyleSpecification {
  return {
    version: 8,
    sources: {
      satellite: {
        type: "raster",
        url: `https://api.maptiler.com/tiles/satellite-v2/tiles.json?key=${encodeURIComponent(apiKey)}`
      }
    },
    layers: [{ id: "satellite-base", type: "raster", source: "satellite" }]
  };
}

type Props = {
  snapshot: PluviometryMapSnapshot | null;
  apiKey?: string | null;
  onOpenDevice?: (deviceId: number) => void;
};

export function RainGaugeMap({ snapshot, apiKey, onOpenDevice }: Props) {
  const containerRef = useRef<HTMLDivElement | null>(null);
  const mapRef = useRef<MapLibreMap | null>(null);
  const moduleRef = useRef<typeof import("maplibre-gl") | null>(null);
  const markersRef = useRef<Marker[]>([]);
  const [initializationFailed, setInitializationFailed] = useState(false);
  const [mapLoadError, setMapLoadError] = useState(false);
  const [ready, setReady] = useState(false);
  const [selectedDevice, setSelectedDevice] = useState<RainGaugeMapDevice | null>(null);
  const mapTilerKey = (apiKey === undefined ? process.env.NEXT_PUBLIC_MAPTILER_KEY : apiKey)?.trim();

  useEffect(() => {
    if (!mapTilerKey || !containerRef.current || mapRef.current) return;
    let cancelled = false;

    void import("maplibre-gl")
      .then((maplibregl) => {
        if (cancelled || !containerRef.current || mapRef.current) return;
        maplibregl.setWorkerUrl("/maplibre/maplibre-gl-worker.mjs");
        const map = new maplibregl.Map({
          container: containerRef.current,
          style: buildSatelliteStyle(mapTilerKey),
          center: BOLIVIA_INITIAL_VIEW.center,
          zoom: BOLIVIA_INITIAL_VIEW.zoom,
          dragRotate: false,
          pitchWithRotate: false
        });
        map.addControl(new maplibregl.NavigationControl({
          showCompass: true,
          showZoom: true,
          visualizePitch: false
        }), "top-right");
        map.once("load", () => {
          if (!cancelled) setReady(true);
        });
        map.on("error", () => {
          if (!cancelled) setMapLoadError(true);
        });
        moduleRef.current = maplibregl;
        mapRef.current = map;
      })
      .catch(() => {
        if (!cancelled) setInitializationFailed(true);
      });

    return () => {
      cancelled = true;
      markersRef.current.forEach((marker) => marker.remove());
      markersRef.current = [];
      mapRef.current?.remove();
      mapRef.current = null;
      moduleRef.current = null;
    };
  }, [mapTilerKey]);

  useEffect(() => {
    const map = mapRef.current;
    const maplibregl = moduleRef.current;
    if (!ready || !map || !maplibregl || !snapshot) return;

    setGeoJsonSource(map, "site-boundary", siteFeatureCollection(snapshot));
    setGeoJsonSource(map, "parcel-boundaries", parcelFeatureCollection(snapshot));
    ensureBoundaryLayers(map);

    setSelectedDevice(null);
    markersRef.current.forEach((marker) => marker.remove());
    markersRef.current = locatedDevices(snapshot).flatMap((device) => {
      if (device.latitude == null || device.longitude == null) return [];
      const element = createMarkerElement(device);
      const coordinates: [number, number] = [device.longitude, device.latitude];
      const marker = new maplibregl.Marker({ element }).setLngLat(coordinates).addTo(map);
      element.addEventListener("click", () => setSelectedDevice(device));
      return [marker];
    });

    const viewport = mapViewport(snapshot);
    if (viewport.kind === "bounds") {
      const bounds = new maplibregl.LngLatBounds();
      viewport.coordinates.forEach((position) => bounds.extend([position[0], position[1]]));
      if (!bounds.isEmpty()) map.fitBounds(bounds, { padding: 64, maxZoom: 15, duration: 0 });
    } else if (viewport.kind === "center") {
      map.jumpTo({ center: viewport.center, zoom: viewport.zoom });
    } else {
      map.jumpTo(BOLIVIA_INITIAL_VIEW);
    }
  }, [onOpenDevice, ready, snapshot]);

  if (!mapTilerKey || initializationFailed) return <MapUnavailable />;

  return (
    <div
      className="relative h-[clamp(22rem,62vh,48rem)] min-h-[22rem] w-full overflow-hidden rounded-2xl bg-slate-200 sm:min-h-[30rem]"
      data-testid="rain-gauge-map"
      role="region"
      aria-label={snapshot ? `Mapa satelital de ${snapshot.site.name}` : "Mapa satelital de Bolivia"}
    >
      <div
        ref={containerRef}
        className="absolute inset-0"
        data-testid="maplibre-container"
        style={{ position: "absolute", inset: 0 }}
      />
      {selectedDevice ? (
        <MapPopupCard
          device={selectedDevice}
          isDemo={snapshot?.site.name.toLowerCase().includes("demo") ?? false}
          timeZone={snapshot?.site.timezone}
          onClose={() => setSelectedDevice(null)}
          onOpen={() => onOpenDevice?.(selectedDevice.id)}
        />
      ) : null}
      {!ready ? (
        <div className="pointer-events-none absolute inset-0 flex items-center justify-center bg-slate-900/15" aria-live="polite">
          <span className="rounded-full bg-white/95 px-4 py-2 text-xs font-bold text-slate-700 shadow-panel">Cargando mapa satelital</span>
        </div>
      ) : null}
      {mapLoadError ? (
        <p className="absolute bottom-3 left-3 z-20 rounded-lg bg-red-950/90 px-3 py-2 text-xs font-bold text-white" role="alert">
          Una capa del mapa no pudo cargarse. Revisa la conexión e inténtalo nuevamente.
        </p>
      ) : null}
    </div>
  );
}

function setGeoJsonSource(map: MapLibreMap, id: string, data: ReturnType<typeof siteFeatureCollection>) {
  const source = map.getSource(id) as GeoJSONSource | undefined;
  if (source) source.setData(data);
  else map.addSource(id, { type: "geojson", data });
}

function ensureBoundaryLayers(map: MapLibreMap) {
  if (!map.getLayer("site-outline")) {
    map.addLayer({ id: "site-outline", type: "line", source: "site-boundary", paint: { "line-color": "#f8fafc", "line-width": 3, "line-opacity": 0.95 } });
  }
  if (!map.getLayer("parcel-fill")) {
    map.addLayer({ id: "parcel-fill", type: "fill", source: "parcel-boundaries", paint: { "fill-color": "#10b981", "fill-opacity": 0.12 } });
  }
  if (!map.getLayer("parcel-outline")) {
    map.addLayer({ id: "parcel-outline", type: "line", source: "parcel-boundaries", paint: { "line-color": "#34d399", "line-width": 2, "line-opacity": 0.95 } });
  }
}

function createMarkerElement(device: RainGaugeMapDevice) {
  const presentation = STATUS_PRESENTATION[device.status];
  const button = document.createElement("button");
  button.type = "button";
  button.className = "flex h-11 w-11 items-center justify-center rounded-full border-2 border-white shadow-lg focus:outline-none focus:ring-4";
  button.style.backgroundColor = presentation.color;
  button.style.boxShadow = `0 0 0 5px ${presentation.ring}, 0 6px 18px rgba(15, 23, 42, 0.35)`;
  button.setAttribute("aria-label", `${device.name}: ${presentation.label}`);
  button.dataset.status = device.status;
  button.innerHTML = '<svg aria-hidden="true" viewBox="0 0 24 24" width="22" height="22" fill="none" stroke="white" stroke-width="2"><path d="M12 2v6m0 0a4 4 0 1 0 0 8 4 4 0 1 0 0-8Zm-7 12h14"/></svg>';
  return button;
}

export function MapPopupCard({ device, isDemo, timeZone, onClose, onOpen }: { device: RainGaugeMapDevice; isDemo: boolean; timeZone?: string; onClose: () => void; onOpen: () => void }) {
  const presentation = STATUS_PRESENTATION[device.status];
  return (
    <article className="absolute left-3 top-3 z-20 w-[min(19rem,calc(100%-1.5rem))] rounded-xl border border-white/70 bg-white/95 p-4 text-slate-900 shadow-panel backdrop-blur" role="dialog" aria-label={`Información de ${device.name}`}>
      <button type="button" onClick={onClose} className="absolute right-2 top-2 rounded-md px-2 py-1 text-sm font-black text-slate-500 hover:bg-slate-100" aria-label="Cerrar popup">×</button>
      <h3 className="pr-7 text-base font-black">{device.name}</h3>
      {isDemo ? <span className="mt-1 inline-flex rounded-full bg-amber-100 px-2 py-0.5 text-[10px] font-black uppercase tracking-wide text-amber-900">DEMO · ubicación aproximada</span> : null}
      <p className="mt-1 text-xs text-slate-500">{device.parcel_name}</p>
      <p className="mt-2 text-xs font-black uppercase tracking-wide" style={{ color: presentation.color }}>{presentation.label}</p>
      <dl className="mt-3 grid grid-cols-2 gap-x-4 gap-y-2 text-xs">
        {popupFields(device).map(([label, value]) => (
          <div key={label}>
            <dt className="text-slate-500">{label}</dt>
            <dd className="font-bold text-slate-900">{value}</dd>
          </div>
        ))}
      </dl>
      <p className="mt-3 text-xs text-slate-500">{device.last_seen_at ? `Última lectura: ${formatDateTimeInTimeZone(device.last_seen_at, timeZone, { dateStyle: "short", timeStyle: "short" })}` : "Última lectura: Sin datos"}</p>
      <button type="button" onClick={onOpen} className="mt-3 w-full rounded-lg bg-emerald-700 px-3 py-2 text-sm font-bold text-white">Ver pluviómetro</button>
    </article>
  );
}

function MapUnavailable() {
  return (
    <div className="flex h-[clamp(22rem,62vh,48rem)] min-h-[22rem] w-full items-center justify-center rounded-2xl border border-dashed border-slate-300 bg-slate-50 px-6 text-center sm:min-h-[30rem]" data-testid="map-unavailable" role="status">
      <div className="max-w-lg">
        <div className="premium-empty-icon" aria-hidden="true"><MapPinned size={28} /></div>
        <h2 className="text-xl font-black tracking-tight text-slate-950">Mapa no configurado</h2>
        <p className="mt-2 text-sm leading-6 text-slate-500">La visualización cartográfica estará disponible cuando se complete la configuración del servicio de mapas.</p>
        <p className="mt-3 inline-flex items-center gap-2 text-xs font-bold text-emerald-800"><CloudRain size={15} /> Los datos del predio siguen disponibles.</p>
      </div>
    </div>
  );
}
