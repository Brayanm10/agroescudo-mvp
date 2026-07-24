"use client";

import { FormEvent, useMemo, useState } from "react";
import { Bot, LoaderCircle, Send, UserCircle } from "lucide-react";
import { formatDateTime, formatNumber } from "@/lib/format";
import { askAgroAssistant } from "@/lib/api";
import type { AppData, ViewKey } from "@/lib/types";

type ChatMessage = {
  id: number;
  role: "assistant" | "user";
  text: string;
};

const suggestions = [
  "Que silo necesita atencion?",
  "Que hago ante una alerta critica?",
  "Hay sensores desconectados?",
  "Como descargo el reporte?",
  "Como registro mantenimiento?",
  "Como cambio mi contrasena?"
];

export function SupportChatbot({
  data,
  token,
  onNavigate
}: {
  data: AppData;
  token: string;
  onNavigate?: (view: ViewKey) => void;
}) {
  const [input, setInput] = useState("");
  const [busy, setBusy] = useState(false);
  const [messages, setMessages] = useState<ChatMessage[]>(() => [
    {
      id: 1,
      role: "assistant",
      text: openingMessage(data)
    }
  ]);
  const context = useMemo(() => buildSupportContext(data), [data]);

  async function submit(event?: FormEvent<HTMLFormElement>, forcedQuestion?: string) {
    event?.preventDefault();
    const question = (forcedQuestion ?? input).trim();
    if (!question || busy) return;
    const userMessage = { id: Date.now(), role: "user" as const, text: question };
    setMessages((current) => [
      ...current,
      userMessage
    ]);
    setInput("");
    setBusy(true);
    try {
      const response = await askAgroAssistant(token, question);
      const answer = [
        response.answer,
        response.facts.length ? `\nDatos verificados:\n${response.facts.map((fact) => `- ${fact}`).join("\n")}` : ""
      ].filter(Boolean).join("");
      setMessages((current) => [...current, { id: Date.now() + 1, role: "assistant", text: answer }]);
    } catch {
      const fallback = answerQuestion(question, data, context);
      setMessages((current) => [
        ...current,
        { id: Date.now() + 1, role: "assistant", text: `${fallback}\n\nEl servicio avanzado no esta disponible; respuesta generada con reglas locales.` }
      ]);
    } finally {
      setBusy(false);
    }
  }

  function quickAction(view: ViewKey) {
    onNavigate?.(view);
  }

  return (
    <section className="panel overflow-hidden">
      <div className="border-b border-slate-200 bg-gradient-to-br from-emerald-50 to-white p-5">
        <div className="flex items-start justify-between gap-4">
          <div>
            <p className="section-kicker">Chat de ayuda</p>
            <h2 className="section-title">Asistente operativo AgroEscudo</h2>
            <p className="section-subtitle">
              Responde con reglas del sistema y datos visibles para tu rol. No inventa datos ni diagnostica hongos.
            </p>
          </div>
          <div className="rounded-2xl bg-emerald-700 p-3 text-white shadow-soft">
            <Bot size={24} aria-hidden="true" />
          </div>
        </div>
        <div className="mt-4 flex flex-wrap gap-2">
          {suggestions.map((item) => (
            <button
              key={item}
              type="button"
              onClick={() => submit(undefined, item)}
              className="rounded-full border border-emerald-100 bg-white px-3 py-1.5 text-xs font-bold text-emerald-800 shadow-soft transition hover:bg-emerald-50"
            >
              {item}
            </button>
          ))}
        </div>
      </div>

      <div className="max-h-[430px] space-y-3 overflow-y-auto bg-slate-50/80 p-5">
        {messages.map((message) => (
          <div key={message.id} className={`flex gap-3 ${message.role === "user" ? "justify-end" : "justify-start"}`}>
            {message.role === "assistant" ? (
              <div className="mt-1 flex h-8 w-8 shrink-0 items-center justify-center rounded-full bg-emerald-700 text-white">
                <Bot size={16} aria-hidden="true" />
              </div>
            ) : null}
            <div
              className={`max-w-[82%] rounded-2xl px-4 py-3 text-sm leading-6 shadow-soft ${
                message.role === "user"
                  ? "bg-emeraldDeep text-white"
                  : "border border-slate-200 bg-white text-slate-700"
              }`}
            >
              <p className="whitespace-pre-line">{message.text}</p>
            </div>
            {message.role === "user" ? (
              <div className="mt-1 flex h-8 w-8 shrink-0 items-center justify-center rounded-full bg-slate-200 text-slate-600">
                <UserCircle size={16} aria-hidden="true" />
              </div>
            ) : null}
          </div>
        ))}
      </div>

      <div className="border-t border-slate-200 bg-white p-4">
        <div className="mb-3 flex flex-wrap gap-2">
          {onNavigate ? (
            <>
              <button type="button" onClick={() => quickAction("alerts")} className="btn-secondary py-2 text-xs">Ver alertas</button>
              <button type="button" onClick={() => quickAction("reports")} className="btn-secondary py-2 text-xs">Ir a reportes</button>
              {data.me.role !== "client" ? <button type="button" onClick={() => quickAction("logs")} className="btn-secondary py-2 text-xs">Registrar bitacora</button> : null}
            </>
          ) : null}
        </div>
        <form onSubmit={submit} className="flex gap-2">
          <input
            value={input}
            onChange={(event) => setInput(event.target.value)}
            className="input"
            placeholder="Escribe una pregunta operativa..."
          />
          <button type="submit" className="btn-primary shrink-0" disabled={!input.trim() || busy}>
            {busy ? <LoaderCircle className="mr-2 animate-spin" size={16} aria-hidden="true" /> : <Send className="mr-2" size={16} aria-hidden="true" />}
            {busy ? "Analizando..." : "Enviar"}
          </button>
        </form>
      </div>
    </section>
  );
}

function openingMessage(data: AppData) {
  const context = buildSupportContext(data);
  if (context.criticalAlerts > 0) {
    return `Hay ${context.criticalAlerts} alerta(s) critica(s) activa(s). Te puedo guiar para revisar el silo afectado, registrar una accion y descargar evidencia.`;
  }
  if (context.disconnectedDevices > 0) {
    return `Detecto ${context.disconnectedDevices} sensor(es) sin sincronizacion reciente. Puedo ayudarte a priorizar revision tecnica.`;
  }
  return "Estoy listo para ayudarte con alertas, silos, sensores, reportes, soporte y mantenimiento.";
}

function buildSupportContext(data: AppData) {
  const latest = data.readings[0] ?? null;
  const cutoffMs = Date.now() - 24 * 60 * 60 * 1000;
  const disconnectedDevices = data.devices.filter((device) => {
    const latestReading = data.readings.find((reading) => reading.device_id === device.id);
    const lastSync = device.last_seen_at || latestReading?.timestamp || null;
    return !lastSync || new Date(lastSync).getTime() < cutoffMs;
  });
  const criticalAlerts = data.activeAlerts.filter((alert) => alert.severity === "critical");
  const priorityInsight = data.insights
    .slice()
    .sort((a, b) => {
      const weight: Record<string, number> = { critical: 4, attention: 3, offline: 2, insufficient_data: 1, normal: 0 };
      return (weight[b.status] ?? 0) - (weight[a.status] ?? 0);
    })[0] ?? null;

  return {
    latest,
    disconnectedDevices: disconnectedDevices.length,
    criticalAlerts: criticalAlerts.length,
    activeAlerts: data.activeAlerts.length,
    storageUnits: data.storageUnits.length,
    reportsReady: data.storageUnits.length > 0,
    priorityInsight
  };
}

function answerQuestion(question: string, data: AppData, context: ReturnType<typeof buildSupportContext>) {
  const normalized = normalize(question);
  const role = data.me.role;

  if (matches(normalized, ["alerta", "critica", "riesgo", "atencion"])) {
    if (context.criticalAlerts > 0) {
      const alert = data.activeAlerts.find((item) => item.severity === "critical") ?? data.activeAlerts[0];
      const unit = data.storageUnits.find((item) => item.id === alert?.storage_unit_id);
      return [
        `Prioridad: ${unit?.name || "silo con alerta activa"}.`,
        `Motivo: ${alert?.title || "alerta critica"} - ${alert?.message || "condicion fuera de rango"}.`,
        role === "client"
          ? "Accion sugerida: inspecciona el area, solicita apoyo tecnico y descarga el reporte como evidencia."
          : "Accion sugerida: inspeccionar fisicamente, registrar accion correctiva y resolver solo cuando se valide la condicion."
      ].join("\n");
    }
    return "No hay alertas criticas activas visibles para tu rol. Mantener monitoreo y revisar el historial si necesitas evidencia del periodo.";
  }

  if (matches(normalized, ["silo", "unidad", "galpon", "almacen", "atencion"])) {
    if (context.priorityInsight) {
      const recommendation = context.priorityInsight.recommendations[0] || "Revisar tendencia y bitacora antes de tomar accion.";
      return [
        `Silo: ${context.priorityInsight.storage_unit_name}.`,
        `Estado: ${context.priorityInsight.status}.`,
        `Motivo: ${context.priorityInsight.summary}`,
        `Accion sugerida: ${recommendation}`
      ].join("\n");
    }
    return "No hay suficiente informacion para priorizar un silo. Revisa si existen lecturas recientes o sensores activos.";
  }

  if (matches(normalized, ["sensor", "desconectado", "conexion", "lectura", "gateway", "wifi", "lora"])) {
    if (context.disconnectedDevices > 0) {
      return `Hay ${context.disconnectedDevices} sensor(es) sin sincronizacion reciente. Revisa energia, bateria, antena, conectividad del gateway y que la API este disponible.`;
    }
    if (context.latest) {
      return `Ultima lectura visible: ${formatDateTime(context.latest.timestamp)}. Temperatura grano ${formatNumber(context.latest.grain_temperature, " C")}, humedad ${formatNumber(context.latest.ambient_humidity, "%")}, bateria ${formatNumber(context.latest.battery_voltage, " V", 2)}.`;
    }
    return "Todavia no hay lecturas visibles. Verifica que el dispositivo este registrado, activo y enviando con su token correcto.";
  }

  if (matches(normalized, ["bateria", "voltaje", "nodo"])) {
    const lowBattery = data.readings.find((reading) => reading.battery_voltage !== null && reading.battery_voltage < 3.5);
    if (lowBattery) {
      const unit = data.storageUnits.find((item) => item.id === lowBattery.storage_unit_id);
      return `Bateria baja detectada en ${unit?.name || "un sensor"}: ${formatNumber(lowBattery.battery_voltage, " V", 2)}. Programa revision tecnica del nodo y registra mantenimiento.`;
    }
    return "No veo bateria baja en las lecturas cargadas. Mantener revision preventiva en mantenimiento.";
  }

  if (matches(normalized, ["humedad", "condensacion", "aireacion", "ventilacion"])) {
    const humidityValues = data.readings.map((reading) => reading.ambient_humidity).filter((value): value is number => value !== null);
    const maxHumidity = humidityValues.length ? Math.max(...humidityValues) : null;
    if (maxHumidity === null) return "No hay datos de humedad suficientes para emitir una recomendacion.";
    if (maxHumidity >= 75) return `Humedad maxima reciente: ${formatNumber(maxHumidity, "%")}. Revisa ventilacion, aireacion y posibles puntos de condensacion.`;
    return `Humedad maxima reciente: ${formatNumber(maxHumidity, "%")}. No se observa humedad alta en los datos cargados.`;
  }

  if (matches(normalized, ["temperatura", "calor", "termica", "grano"])) {
    const temperatureValues = data.readings.map((reading) => reading.grain_temperature).filter((value): value is number => value !== null);
    const maxTemperature = temperatureValues.length ? Math.max(...temperatureValues) : null;
    if (maxTemperature === null) return "No hay datos de temperatura suficientes para emitir una recomendacion.";
    if (maxTemperature >= 32) return `Temperatura maxima de grano: ${formatNumber(maxTemperature, " C")}. Inspecciona el punto monitoreado y verifica acumulacion termica.`;
    return `Temperatura maxima de grano: ${formatNumber(maxTemperature, " C")}. No se observa temperatura alta en los datos cargados.`;
  }

  if (matches(normalized, ["reporte", "pdf", "descargar", "evidencia"])) {
    if (!context.reportsReady) return "No hay silos disponibles para generar reporte. Primero debe existir una unidad monitoreada.";
    return "Para descargar evidencia, entra a Reportes, selecciona el silo y usa Descargar reporte PDF. El reporte incluye periodo, metricas, alertas, bitacora y recomendaciones.";
  }

  if (matches(normalized, ["mantenimiento", "bitacora", "accion", "correctiva", "instalacion"])) {
    if (role === "client") {
      return "Como cliente puedes revisar bitacora y solicitar soporte. El registro tecnico lo realiza AgroEscudo para mantener trazabilidad.";
    }
    return "Ve a Bitacora o Mantenimiento, selecciona el silo, registra operador, accion tomada, notas y fecha. Usa textos concretos y verificables.";
  }

  if (matches(normalized, ["contrasena", "password", "perfil", "cuenta"])) {
    return "Abre el menu de cuenta en el header. En Mi perfil puedes actualizar contacto y preferencias; en Cambiar contrasena debes usar clave actual, nueva clave y confirmacion.";
  }

  if (matches(normalized, ["usuario", "empresa", "crear", "asignar", "admin"])) {
    if (role !== "admin") return "Tu rol no administra usuarios ni empresas. Solicita el cambio al administrador AgroEscudo.";
    return "Como admin, crea empresa, registra silo, crea sensor, crea usuario cliente o tecnico y asigna storage units desde Usuarios y accesos.";
  }

  return [
    "Puedo ayudarte con alertas, sensores, silos, reportes, mantenimiento, perfil y soporte.",
    "No tengo datos suficientes para responder eso con precision. Reformula con el silo, sensor o alerta que quieres revisar."
  ].join("\n");
}

function normalize(value: string) {
  return value
    .toLowerCase()
    .normalize("NFD")
    .replace(/[\u0300-\u036f]/g, "");
}

function matches(value: string, keywords: string[]) {
  return keywords.some((keyword) => value.includes(keyword));
}
