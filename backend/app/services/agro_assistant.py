from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from statistics import fmean

import httpx
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import assigned_storage_unit_ids, require_storage_unit_access
from app.core.config import settings
from app.models import (
    AiConversation,
    AiUsage,
    Alert,
    Device,
    OperationalLog,
    SensorReading,
    StorageUnit,
    User,
    utc_now,
)
from app.schemas import AgroAssistantMessageIn, AgroAssistantMessageOut

CONTEXT_DAYS = 30
MAX_CONTEXT_READINGS = 3000


@dataclass
class UnitSituation:
    unit: StorageUnit
    active_alerts: list[Alert]
    devices: list[Device]
    offline_devices: list[Device]
    readings: list[SensorReading]
    score: int

    @property
    def latest(self) -> SensorReading | None:
        return self.readings[0] if self.readings else None

    @property
    def critical_count(self) -> int:
        return sum(alert.severity == "critical" for alert in self.active_alerts)


def answer_agro_assistant(db: Session, user: User, payload: AgroAssistantMessageIn) -> AgroAssistantMessageOut:
    unit_ids = assigned_storage_unit_ids(db, user)
    if payload.storage_unit_id is not None:
        require_storage_unit_access(db, user, payload.storage_unit_id)
        unit_ids = [payload.storage_unit_id]

    units = list(db.scalars(select(StorageUnit).where(StorageUnit.id.in_(unit_ids))).all()) if unit_ids else []
    active_alerts = _active_alerts(db, unit_ids)
    devices = _devices(db, unit_ids)
    readings = _recent_readings(db, unit_ids)
    logs = _recent_logs(db, unit_ids)
    situations = _unit_situations(units, active_alerts, devices, readings)
    priority = situations[0] if situations else None
    latest = readings[0] if readings else None
    disconnected = [device for device in devices if _is_offline(device.last_seen_at)]
    previous = _previous_conversation(db, user, payload.conversation_id, payload.storage_unit_id)

    facts = _verified_facts(situations, active_alerts, latest, devices, disconnected, readings, logs)
    risk_level = _risk_level(units, active_alerts, latest, disconnected)
    interpretation = _interpretation(risk_level, priority)
    actions = _recommended_actions(active_alerts, latest, disconnected, logs)
    rules_answer = _rules_answer(
        payload.message,
        user,
        situations,
        active_alerts,
        readings,
        logs,
        interpretation,
        actions,
        previous,
    )
    answer = rules_answer
    source = "rules"
    tokens_in = 0
    tokens_out = 0

    if settings.ai_enabled and settings.agro_assistant_llm_enabled and settings.ai_provider.lower() == "gemini":
        try:
            answer, tokens_in, tokens_out = _answer_with_gemini(
                question=payload.message,
                previous=previous,
                facts=facts,
                interpretation=interpretation,
                actions=actions,
                role=user.role,
            )
            source = "gemini"
        except (httpx.HTTPError, KeyError, TypeError, ValueError):
            answer = rules_answer
            source = "rules_fallback"

    conversation = AiConversation(
        company_id=user.company_id,
        user_id=user.id,
        storage_unit_id=payload.storage_unit_id,
        source=source,
        question=payload.message,
        answer=answer,
    )
    db.add(conversation)
    db.flush()
    db.add(
        AiUsage(
            conversation_id=conversation.id,
            user_id=user.id,
            provider=source,
            tokens_in=tokens_in,
            tokens_out=tokens_out,
            tool_name="agro_assistant_contextual_v1",
        )
    )

    return AgroAssistantMessageOut(
        source=source,
        answer=answer,
        facts=facts,
        interpretation=interpretation,
        recommended_actions=actions,
        conversation_id=conversation.id,
        risk_level=risk_level,
        suggested_questions=_suggested_questions(risk_level, readings, logs),
        context_window=f"{CONTEXT_DAYS}d",
    )


def _active_alerts(db: Session, unit_ids: list[int]) -> list[Alert]:
    if not unit_ids:
        return []
    return list(
        db.scalars(
            select(Alert)
            .where(Alert.storage_unit_id.in_(unit_ids), Alert.is_active.is_(True))
            .order_by(Alert.created_at.desc())
            .limit(100)
        ).all()
    )


def _devices(db: Session, unit_ids: list[int]) -> list[Device]:
    if not unit_ids:
        return []
    return list(db.scalars(select(Device).where(Device.storage_unit_id.in_(unit_ids), Device.is_active.is_(True))).all())


def _recent_readings(db: Session, unit_ids: list[int]) -> list[SensorReading]:
    if not unit_ids:
        return []
    since = utc_now() - timedelta(days=CONTEXT_DAYS)
    return list(
        db.scalars(
            select(SensorReading)
            .where(SensorReading.storage_unit_id.in_(unit_ids), SensorReading.timestamp >= since)
            .order_by(SensorReading.timestamp.desc())
            .limit(MAX_CONTEXT_READINGS)
        ).all()
    )


def _recent_logs(db: Session, unit_ids: list[int]) -> list[OperationalLog]:
    if not unit_ids:
        return []
    since = utc_now() - timedelta(days=CONTEXT_DAYS)
    return list(
        db.scalars(
            select(OperationalLog)
            .where(OperationalLog.storage_unit_id.in_(unit_ids), OperationalLog.timestamp >= since)
            .order_by(OperationalLog.timestamp.desc())
            .limit(40)
        ).all()
    )


def _unit_situations(
    units: list[StorageUnit],
    alerts: list[Alert],
    devices: list[Device],
    readings: list[SensorReading],
) -> list[UnitSituation]:
    result: list[UnitSituation] = []
    for unit in units:
        unit_alerts = [item for item in alerts if item.storage_unit_id == unit.id]
        unit_devices = [item for item in devices if item.storage_unit_id == unit.id]
        unit_readings = [item for item in readings if item.storage_unit_id == unit.id]
        offline = [item for item in unit_devices if _is_offline(item.last_seen_at)]
        critical = sum(item.severity == "critical" for item in unit_alerts)
        score = critical * 100 + (len(unit_alerts) - critical) * 30 + len(offline) * 15 + (10 if not unit_readings else 0)
        result.append(UnitSituation(unit, unit_alerts, unit_devices, offline, unit_readings, score))
    return sorted(
        result,
        key=lambda item: (
            item.score,
            _as_utc(item.latest.timestamp) if item.latest else datetime.min.replace(tzinfo=timezone.utc),
        ),
        reverse=True,
    )


def _verified_facts(
    situations: list[UnitSituation],
    active_alerts: list[Alert],
    latest: SensorReading | None,
    devices: list[Device],
    disconnected: list[Device],
    readings: list[SensorReading],
    logs: list[OperationalLog],
) -> list[str]:
    facts = [
        f"Unidades visibles: {len(situations)}.",
        f"Dispositivos activos: {len(devices)}; sin conexion reciente: {len(disconnected)}.",
        f"Alertas activas: {len(active_alerts)}; criticas: {sum(alert.severity == 'critical' for alert in active_alerts)}.",
        f"Evidencia de {CONTEXT_DAYS} dias: {len(readings)} lecturas y {len(logs)} registros de bitacora.",
    ]
    if situations:
        priority = situations[0]
        facts.append(
            f"Mayor prioridad: {priority.unit.name}; {priority.critical_count} alerta(s) critica(s), "
            f"{len(priority.active_alerts)} activa(s) y {len(priority.offline_devices)} nodo(s) sin conexion."
        )
    if latest is None:
        facts.append("No hay lecturas recientes disponibles para el contexto consultado.")
        return facts

    facts.append(f"Ultima lectura recibida: {_as_utc(latest.timestamp).strftime('%d/%m/%Y %H:%M UTC')}.")
    metrics = [
        _metric_fact("Temperatura de grano", latest.grain_temperature, "C", 1),
        _metric_fact("Temperatura ambiente", latest.ambient_temperature, "C", 1),
        _metric_fact("Humedad ambiente", latest.ambient_humidity, "%", 1),
        _metric_fact("Nivel estimado", latest.level_percent, "%", 1),
        _metric_fact("Humedad de suelo", latest.soil_moisture_percent, "%", 1),
        _metric_fact("Bateria", latest.battery_voltage, "V", 2),
    ]
    facts.extend(item for item in metrics if item)
    trend = _trend_summary(readings)
    if trend:
        facts.append(trend)
    return facts


def _metric_fact(label: str, value: float | None, unit: str, decimals: int) -> str | None:
    return None if value is None else f"{label}: {value:.{decimals}f} {unit}."


def _risk_level(
    units: list[StorageUnit],
    active_alerts: list[Alert],
    latest: SensorReading | None,
    disconnected: list[Device],
) -> str:
    if not units or latest is None:
        return "insufficient_data"
    if any(alert.severity == "critical" for alert in active_alerts):
        return "critical"
    if active_alerts or disconnected:
        return "attention"
    return "stable"


def _interpretation(risk_level: str, priority: UnitSituation | None) -> str:
    name = priority.unit.name if priority else "la operacion visible"
    if risk_level == "critical":
        return f"{name} concentra el mayor riesgo y requiere seguimiento inmediato con evidencia en bitacora."
    if risk_level == "attention":
        return f"{name} requiere vigilancia preventiva por alertas o perdida de continuidad de datos."
    if risk_level == "stable":
        return "Las unidades visibles no presentan alertas activas ni interrupciones recientes."
    return "No existe evidencia reciente suficiente para evaluar la operacion con confianza."


def _recommended_actions(
    active_alerts: list[Alert],
    latest: SensorReading | None,
    disconnected: list[Device],
    logs: list[OperationalLog],
) -> list[str]:
    actions: list[str] = []
    alert_types = {alert.alert_type.lower() for alert in active_alerts}
    if any(alert.severity == "critical" for alert in active_alerts):
        actions.append("Priorizar inspeccion fisica y documentar una accion correctiva.")
    if any("humidity" in value for value in alert_types):
        actions.append("Revisar ventilacion, aireacion y posibles puntos de condensacion.")
    if any("temperature" in value or "environment" in value for value in alert_types):
        actions.append("Verificar acumulacion termica en el punto monitoreado.")
    if any("battery" in value for value in alert_types) or (latest and latest.battery_voltage is not None and latest.battery_voltage < 3.5):
        actions.append("Programar revision de bateria y alimentacion del nodo.")
    if any("level" in value or "distance" in value for value in alert_types):
        actions.append("Validar distancia ultrasónica y calibracion de vacio/lleno antes de decidir.")
    if any("soil" in value for value in alert_types):
        actions.append("Confirmar humedad de suelo con inspeccion de campo y calibracion vigente.")
    if disconnected:
        actions.append("Verificar energia, antena LoRa, gateway y ultima sincronizacion.")
    if active_alerts and not logs:
        actions.append("Registrar responsable, hallazgo, accion y resultado en bitacora.")
    if not actions:
        actions.append("Mantener monitoreo y registrar cualquier intervencion relevante.")
    return list(dict.fromkeys(actions))[:5]


def _rules_answer(
    question: str,
    user: User,
    situations: list[UnitSituation],
    active_alerts: list[Alert],
    readings: list[SensorReading],
    logs: list[OperationalLog],
    interpretation: str,
    actions: list[str],
    previous: AiConversation | None,
) -> str:
    normalized = _effective_question(question, previous)
    priority = situations[0] if situations else None
    latest = readings[0] if readings else None
    critical = [alert for alert in active_alerts if alert.severity == "critical"]

    if _has(normalized, "tendencia", "subiendo", "bajando", "evolucion", "historico"):
        return _trend_answer(readings)
    if _has(normalized, "compar", "cual esta peor", "prioridad", "que silo", "cual silo", "necesita atencion"):
        return _priority_answer(situations, actions)
    if _has(normalized, "nivel", "distancia", "lleno", "vacio"):
        return _metric_answer(readings, "level_percent", "nivel estimado", "%", "La altura ocupada es estimada y no equivale a toneladas.")
    if _has(normalized, "suelo", "riego", "humedad de suelo"):
        return _metric_answer(readings, "soil_moisture_percent", "humedad de suelo", "%", "Confirma la calibracion del CampoSensor antes de decidir.")
    if _has(normalized, "temperatura", "calor", "termica", "grano"):
        return _metric_answer(readings, "grain_temperature", "temperatura de grano", "C", "Revisa tendencia y alerta asociada, no solo un punto aislado.")
    if _has(normalized, "humedad", "condensacion", "aireacion", "ventilacion"):
        return _metric_answer(readings, "ambient_humidity", "humedad ambiente", "%", "Ante valores altos revisa ventilacion y condensacion.")
    if _has(normalized, "bateria", "voltaje", "energia"):
        return _metric_answer(readings, "battery_voltage", "bateria", "V", "Por debajo de 3.5 V programa revision tecnica.")
    if _has(normalized, "desconect", "sin lectura", "gateway", "lora", "conexion"):
        offline = [device for situation in situations for device in situation.offline_devices]
        if offline:
            names = ", ".join(device.name for device in offline[:5])
            return f"Hay {len(offline)} dispositivo(s) sin conexion reciente: {names}. Verifica energia, antena LoRa, gateway, internet y ultima sincronizacion."
        return "No se identifican dispositivos sin conexion reciente en las unidades visibles."
    if _has(normalized, "reporte", "pdf", "descarg", "diario", "semanal", "mensual"):
        period = "mensual" if "mensual" in normalized else "diario" if "diario" in normalized else "semanal"
        return (
            f"En Reportes selecciona la unidad, el nodo y el periodo {period}. Puedes descargar el informe completo "
            "o una bitacora PDF. Incluye metricas, alertas, acciones, tendencias y recomendaciones del rango."
        )
    if _has(normalized, "bitacora", "ultima accion", "que hicieron", "registro"):
        if not logs:
            return "No hay acciones de bitacora en los ultimos 30 dias para este contexto."
        latest_log = logs[0]
        return f"Ultimo registro: {_as_utc(latest_log.timestamp).strftime('%d/%m/%Y %H:%M')} por {latest_log.operator_name}. Accion: {latest_log.action_taken}."
    if _has(normalized, "mantenimiento", "accion correctiva", "instalacion"):
        if user.role == "client":
            return "Puedes consultar evidencia y solicitar soporte. El registro tecnico debe realizarlo un tecnico o administrador para conservar trazabilidad."
        return "Registra unidad, nodo, hallazgo verificable, accion ejecutada, responsable, fecha, evidencia y resultado de validacion posterior."
    if _has(normalized, "contrasena", "password", "cuenta", "perfil"):
        return "Abre Cuenta y selecciona Cambiar contrasena. Si no recuerdas la clave, cierra sesion y usa Olvide password."
    if _has(normalized, "alerta", "critica", "que hago", "riesgo"):
        if critical:
            alert = critical[0]
            unit = next((item.unit for item in situations if item.unit.id == alert.storage_unit_id), None)
            return f"Alerta critica en {unit.name if unit else 'una unidad visible'}: {alert.message} Accion inmediata: {actions[0]}"
        if active_alerts:
            return f"Hay {len(active_alerts)} alerta(s) preventiva(s) activas. {actions[0]}"
        return "No hay alertas activas visibles. Mantener monitoreo y revisar tendencias del periodo."
    if _has(normalized, "resumen", "estado", "como estamos", "situacion") or not normalized:
        return _overview_answer(interpretation, priority, readings, actions)
    if latest is None:
        return f"{interpretation} Verifica dispositivo, gateway y ultima sincronizacion antes de tomar una decision."
    return _overview_answer(interpretation, priority, readings, actions)


def _priority_answer(situations: list[UnitSituation], actions: list[str]) -> str:
    if not situations:
        return "No hay unidades asignadas para comparar."
    priority = situations[0]
    if priority.score == 0:
        return "No hay una unidad con riesgo activo. Todas las unidades con evidencia reciente aparecen estables."
    details = [
        f"Prioridad 1: {priority.unit.name}.",
        f"Tiene {priority.critical_count} alerta(s) critica(s), {len(priority.active_alerts)} activa(s) y {len(priority.offline_devices)} nodo(s) sin conexion.",
        f"Accion inmediata: {actions[0]}",
    ]
    if len(situations) > 1 and situations[1].score > 0:
        details.append(f"Segunda prioridad: {situations[1].unit.name}.")
    return " ".join(details)


def _overview_answer(
    interpretation: str,
    priority: UnitSituation | None,
    readings: list[SensorReading],
    actions: list[str],
) -> str:
    trend = _trend_summary(readings)
    priority_text = f" Prioridad actual: {priority.unit.name}." if priority and priority.score > 0 else ""
    trend_text = f" {trend}" if trend else ""
    return f"{interpretation}{priority_text}{trend_text} Siguiente paso: {actions[0]}"


def _metric_answer(readings: list[SensorReading], attribute: str, label: str, unit: str, caution: str) -> str:
    points = [(reading.timestamp, getattr(reading, attribute)) for reading in readings if getattr(reading, attribute) is not None]
    if not points:
        return f"No hay datos de {label} suficientes en los ultimos {CONTEXT_DAYS} dias."
    values = [float(value) for _, value in points]
    latest = values[0]
    trend = _single_trend(list(reversed(values)))
    return (
        f"{label.capitalize()}: actual {latest:.1f} {unit}, minimo {min(values):.1f}, maximo {max(values):.1f} "
        f"y promedio {fmean(values):.1f} en {len(values)} lectura(s). Tendencia: {trend}. {caution}"
    )


def _trend_answer(readings: list[SensorReading]) -> str:
    if len(readings) < 3:
        return "No hay suficientes lecturas para calcular una tendencia confiable. Se requieren al menos tres puntos."
    parts = []
    for attribute, label, unit in (
        ("grain_temperature", "temperatura de grano", "C"),
        ("ambient_humidity", "humedad ambiente", "%"),
        ("level_percent", "nivel", "%"),
        ("soil_moisture_percent", "humedad de suelo", "%"),
    ):
        values = [float(getattr(item, attribute)) for item in reversed(readings) if getattr(item, attribute) is not None]
        if len(values) >= 3:
            parts.append(f"{label}: {_single_trend(values)} (actual {values[-1]:.1f} {unit})")
    return "Tendencias de la evidencia disponible: " + "; ".join(parts) + "." if parts else "No hay series suficientes para calcular tendencias."


def _trend_summary(readings: list[SensorReading]) -> str | None:
    values = [float(item.grain_temperature) for item in reversed(readings) if item.grain_temperature is not None]
    if len(values) < 3:
        return None
    return f"Tendencia de temperatura de grano: {_single_trend(values)}."


def _single_trend(values: list[float]) -> str:
    if len(values) < 3:
        return "datos insuficientes"
    window = max(1, min(len(values) // 3, 12))
    delta = fmean(values[-window:]) - fmean(values[:window])
    if abs(delta) < 0.5:
        return "estable"
    return f"ascendente (+{delta:.1f})" if delta > 0 else f"descendente ({delta:.1f})"


def _previous_conversation(
    db: Session,
    user: User,
    conversation_id: int | None,
    storage_unit_id: int | None,
) -> AiConversation | None:
    if conversation_id is None:
        return None
    conversation = db.get(AiConversation, conversation_id)
    if conversation is None or conversation.user_id != user.id or conversation.storage_unit_id != storage_unit_id:
        return None
    return conversation


def _effective_question(question: str, previous: AiConversation | None) -> str:
    normalized = _normalize(question)
    follow_up = len(normalized.split()) <= 5 or _has(normalized, "eso", "esa", "ese", "ahora", "y que", "por que")
    if previous is not None and follow_up:
        return f"{_normalize(previous.question)} {normalized}"
    return normalized


def _suggested_questions(risk_level: str, readings: list[SensorReading], logs: list[OperationalLog]) -> list[str]:
    values = ["Que unidad necesita atencion?", "Como evolucionaron temperatura y humedad?"]
    if risk_level == "critical":
        values.insert(0, "Que accion inmediata debo registrar?")
    if not logs:
        values.append("Como registro una accion correctiva?")
    values.append("Como genero el reporte mensual?")
    if any(item.level_percent is not None for item in readings):
        values.append("Cual es el nivel estimado del silo?")
    return values[:5]


def _normalize(value: str) -> str:
    return value.lower().translate(str.maketrans({"á": "a", "é": "e", "í": "i", "ó": "o", "ú": "u", "ñ": "n", "ü": "u"}))


def _has(value: str, *terms: str) -> bool:
    return any(term in value for term in terms)


def _is_offline(last_seen_at: datetime | None) -> bool:
    if last_seen_at is None:
        return True
    elapsed = utc_now() - _as_utc(last_seen_at)
    return elapsed.total_seconds() > settings.device_offline_after_minutes * 60


def _as_utc(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc)


def _answer_with_gemini(
    *,
    question: str,
    previous: AiConversation | None,
    facts: list[str],
    interpretation: str,
    actions: list[str],
    role: str,
) -> tuple[str, int, int]:
    if not settings.gemini_api_key:
        raise ValueError("GEMINI_API_KEY is not configured")

    previous_context = (
        f"Consulta anterior: {previous.question}\nRespuesta anterior: {previous.answer}"
        if previous is not None
        else "No existe una consulta anterior en esta conversacion."
    )
    prompt = "\n".join(
        [
            "Eres AgroAsistente, especialista operativo de AgroEscudo para postcosecha y monitoreo IoT.",
            "Responde en espanol claro, profesional y accionable, con maximo 180 palabras.",
            "Usa exclusivamente los hechos entregados. No inventes lecturas, diagnosticos, costos ni causas.",
            "Distingue hechos, interpretacion y siguiente accion. Considera la consulta anterior cuando sea seguimiento.",
            "Una alerta no reemplaza inspeccion humana ni diagnostico de laboratorio.",
            f"Rol del usuario: {role}.",
            previous_context,
            f"Pregunta actual: {question}",
            "Hechos verificados:",
            *[f"- {fact}" for fact in facts],
            f"Interpretacion del motor: {interpretation}",
            "Acciones autorizadas:",
            *[f"- {action}" for action in actions],
        ]
    )
    model = settings.gemini_model.strip()
    url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent"
    payload = {
        "contents": [{"role": "user", "parts": [{"text": prompt}]}],
        "generationConfig": {"temperature": 0.15, "maxOutputTokens": 420},
    }
    with httpx.Client(timeout=settings.ai_request_timeout_seconds) as client:
        response = client.post(
            url,
            headers={"x-goog-api-key": settings.gemini_api_key, "Content-Type": "application/json"},
            json=payload,
        )
        response.raise_for_status()
    data = response.json()
    parts = data["candidates"][0]["content"]["parts"]
    text = "\n".join(str(part.get("text", "")).strip() for part in parts if part.get("text")).strip()
    if not text:
        raise ValueError("Gemini returned an empty response")
    usage = data.get("usageMetadata") or {}
    return text, int(usage.get("promptTokenCount") or 0), int(usage.get("candidatesTokenCount") or 0)
