"use client";

import { FormEvent, useRef, useState } from "react";
import { Crosshair, LoaderCircle, LocateFixed, Map, Satellite, Search } from "lucide-react";
import type { LocationSearchResult, MapMode } from "./location-assistant";
import { requestCurrentPosition, searchMapTilerLocations } from "./location-assistant";

type Props = {
  apiKey?: string | null;
  mapMode: MapMode;
  hasSiteTarget: boolean;
  hasParcelTarget: boolean;
  onMapModeChange: (mode: MapMode) => void;
  onSelectResult: (result: LocationSearchResult) => void;
  onCenterSite: () => void;
  onCenterParcel: () => void;
};

export type SearchUiState = "idle" | "loading" | "results" | "empty" | "error";

export function LocationAssistant({ apiKey, mapMode, hasSiteTarget, hasParcelTarget, onMapModeChange, onSelectResult, onCenterSite, onCenterParcel }: Props) {
  const [query, setQuery] = useState("");
  const [results, setResults] = useState<LocationSearchResult[]>([]);
  const [state, setState] = useState<SearchUiState>("idle");
  const [message, setMessage] = useState<string | null>(null);
  const [context, setContext] = useState<LocationSearchResult | null>(null);
  const controllerRef = useRef<AbortController | null>(null);

  async function submitSearch(event: FormEvent) {
    event.preventDefault();
    controllerRef.current?.abort();
    const controller = new AbortController();
    controllerRef.current = controller;
    setState("loading"); setMessage(null); setResults([]);
    try {
      const items = await searchMapTilerLocations(query, apiKey, controller.signal);
      setResults(items); setState(items.length ? "results" : "empty");
      if (!items.length) setMessage("No encontramos resultados. Prueba con municipio y departamento.");
    } catch (reason) {
      if (reason instanceof DOMException && reason.name === "AbortError") return;
      setState("error"); setMessage(reason instanceof Error ? reason.message : "No se pudo completar la búsqueda.");
    }
  }

  function choose(result: LocationSearchResult) {
    setContext(result); setResults([]); setState("idle"); setMessage(null); onSelectResult(result);
  }

  async function useMyLocation() {
    setState("loading"); setMessage("Solicitando permiso de ubicación…"); setResults([]);
    try {
      const result = await requestCurrentPosition(typeof navigator === "undefined" ? undefined : navigator.geolocation);
      choose(result);
    } catch (reason) {
      setState("error"); setMessage(reason instanceof Error ? reason.message : "No se pudo obtener tu ubicación.");
    }
  }

  return (
    <div className="mb-3 space-y-3 rounded-2xl border border-slate-200 bg-slate-50 p-3" aria-label="Asistente de ubicación">
      <div className="flex flex-col gap-2 lg:flex-row lg:items-start">
        <div className="relative min-w-0 flex-1">
          <form className="flex min-w-0 gap-2" onSubmit={submitSearch}>
            <label className="sr-only" htmlFor="location-search">Buscar lugar, municipio o coordenadas</label>
            <div className="relative min-w-0 flex-1"><Search className="pointer-events-none absolute left-3 top-1/2 -translate-y-1/2 text-slate-400" size={17} /><input id="location-search" className="input w-full pl-9" value={query} onChange={(event) => setQuery(event.target.value)} placeholder="Buscar lugar, municipio o coordenadas..." autoComplete="off" /></div>
            <button type="submit" className="btn-primary shrink-0" disabled={!query.trim() || state === "loading"}>{state === "loading" ? <LoaderCircle className="animate-spin" size={17} /> : "Buscar"}</button>
          </form>
          {results.length ? <div className="absolute z-30 mt-2 max-h-56 w-full overflow-y-auto rounded-xl border border-slate-200 bg-white p-1 shadow-xl" role="listbox" aria-label="Resultados de ubicación">{results.map((result) => <button key={result.id} type="button" role="option" onClick={() => choose(result)} className="block w-full rounded-lg px-3 py-2 text-left hover:bg-emerald-50"><strong className="block text-sm text-slate-950">{result.primary}</strong><span className="mt-0.5 block text-xs leading-5 text-slate-500">{result.secondary}</span></button>)}</div> : null}
        </div>
        <div className="flex flex-wrap gap-2">
          <button type="button" className="btn-secondary gap-1.5" onClick={useMyLocation} disabled={state === "loading"}><LocateFixed size={16} />Usar mi ubicación</button>
          <div className="inline-flex rounded-xl border border-slate-200 bg-white p-1" aria-label="Tipo de mapa">
            <button type="button" aria-pressed={mapMode === "satellite"} className={`rounded-lg px-3 py-2 text-xs font-black ${mapMode === "satellite" ? "bg-slate-900 text-white" : "text-slate-600"}`} onClick={() => onMapModeChange("satellite")}><span className="inline-flex items-center gap-1"><Satellite size={14} />Satélite</span></button>
            <button type="button" aria-pressed={mapMode === "hybrid"} className={`rounded-lg px-3 py-2 text-xs font-black ${mapMode === "hybrid" ? "bg-slate-900 text-white" : "text-slate-600"}`} onClick={() => onMapModeChange("hybrid")}><span className="inline-flex items-center gap-1"><Map size={14} />Híbrido</span></button>
          </div>
        </div>
      </div>
      <div className="flex flex-col gap-2 sm:flex-row sm:items-center sm:justify-between">
        <SearchFeedback state={state} message={message} hasResults={results.length > 0} />
        <div className="flex flex-wrap gap-2">
          <button type="button" className="btn-secondary gap-1.5" disabled={!hasSiteTarget} onClick={onCenterSite}><Crosshair size={15} />Centrar en predio</button>
          <button type="button" className="btn-secondary gap-1.5" disabled={!hasParcelTarget} onClick={onCenterParcel}><Crosshair size={15} />Centrar en parcela</button>
        </div>
      </div>
      {context ? <div className="rounded-xl bg-white px-3 py-2 text-xs text-slate-600" role="status"><span className="font-black text-slate-900">Ubicación aproximada:</span><span className="ml-2">{context.context.length ? context.context.join(" · ") : `${context.primary} · ${context.secondary}`}</span><span className="ml-1 text-slate-400">(orientativa, no se guarda)</span></div> : null}
    </div>
  );
}

export function SearchFeedback({ state, message, hasResults }: { state: SearchUiState; message: string | null; hasResults: boolean }) {
  if (state === "loading") return <p className="text-xs font-bold text-slate-500" role="status">{message ?? "Buscando ubicación…"}</p>;
  if ((state === "error" || state === "empty") && message) return <p className={`text-xs font-bold ${state === "error" ? "text-rose-700" : "text-amber-700"}`} role="alert">{message}</p>;
  if (hasResults) return <p className="text-xs text-slate-500" role="status">Selecciona un resultado para centrar el mapa.</p>;
  return <p className="text-xs text-slate-500">La búsqueda orienta el mapa y no modifica predios, parcelas ni dispositivos.</p>;
}
