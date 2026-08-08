from __future__ import annotations

from datetime import datetime, timezone

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
    SensorReading,
    StorageUnit,
    User,
    utc_now,
)
from app.schemas import AgroAssistantMessageIn, AgroAssistantMessageOut


def answer_agro_assistant(db: Session, user: User, payload: AgroAssistantMessageIn) -> AgroAssistantMessageOut:
    unit_ids = assigned_storage_unit_ids(db, user)
    if payload.storage_unit_id is not None:
        require_storage_unit_access(db, user, payload.storage_unit_id)
        unit_ids = [payload.storage_unit_id]

    units = list(db.scalars(select(StorageUnit).where(StorageUnit.id.in_(unit_ids))).all()) if unit_ids else []
    units_by_id = {unit.id: unit for unit in units}
    active_alerts = _active_alerts(db, unit_ids)
    latest = _latest_reading(db, unit_ids)
    devices = _devices(db, unit_ids)
    disconnected = [device for device in devices if _is_offline(device.last_seen_at)]

    facts = _verified_facts(units, active_alerts, latest, devices, disconnected)
    interpretation = _interpretation(units, active_alerts, latest, disconnected)
    actions = _recommended_actions(active_alerts, latest, disconnected)
    rules_answer = _rules_answer(
        payload.message,
        user,
        units_by_id,
        active_alerts,
        latest,
        disconnected,
        interpretation,
        actions,
    )
    answer = rules_answer
    source = "rules"
    tokens_in = 0
    tokens_out = 0

    if settings.ai_enabled and settings.agro_assistant_llm_enabled and settings.ai_provider.lower() == "gemini":
        try:
            answer, tokens_in, tokens_out = _answer_with_gemini(
                question=payload.message,
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
            tool_name="agro_assistant_p0",
        )
    )

    return AgroAssistantMessageOut(
        source=source,
        answer=answer,
        facts=facts,
        interpretation=interpretation,
        recommended_actions=actions,
        conversation_id=conversation.id,
    )


def _active_alerts(db: Session, unit_ids: list[int]) -> list[Alert]:
    if not unit_ids:
        return []
    return list(
        db.scalars(
            select(Alert)
            .where(Alert.storage_unit_id.in_(unit_ids), Alert.is_active.is_(True))
            .order_by(Alert.created_at.desc())
            .limit(25)
        ).all()
    )


def _latest_reading(db: Session, unit_ids: list[int]) -> SensorReading | None:
    if not unit_ids:
        return None
    return db.scalar(
        select(SensorReading)
        .where(SensorReading.storage_unit_id.in_(unit_ids))
        .order_by(SensorReading.timestamp.desc())
        .limit(1)
    )


def _devices(db: Session, unit_ids: list[int]) -> list[Device]:
    if not unit_ids:
        return []
    return list(db.scalars(select(Device).where(Device.storage_unit_id.in_(unit_ids), Device.is_active.is_(True))).all())


def _verified_facts(
    units: list[StorageUnit],
    active_alerts: list[Alert],
    latest: SensorReading | None,
    devices: list[Device],
    disconnected: list[Device],
) -> list[str]:
    facts = [
        f"Unidades visibles: {len(units)}.",
        f"Dispositivos activos: {len(devices)}; sin conexion reciente: {len(disconnected)}.",
        f"Alertas activas: {len(active_alerts)}; criticas: {sum(alert.severity == 'critical' for alert in active_alerts)}.",
    ]
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
    available = [item for item in metrics if item]
    facts.extend(available or ["La ultima lectura no contiene metricas operativas utilizables."])
    return facts


def _metric_fact(label: str, value: float | None, unit: str, decimals: int) -> str | None:
    if value is None:
        return None
    return f"{label}: {value:.{decimals}f} {unit}."


def _interpretation(
    units: list[StorageUnit],
    active_alerts: list[Alert],
    latest: SensorReading | None,
    disconnected: list[Device],
) -> str:
    if not units:
        return "No hay unidades asignadas al usuario para emitir una evaluacion operativa."
    if any(alert.severity == "critical" for alert in active_alerts):
        return "Hay riesgo operativo que requiere seguimiento inmediato."
    if active_alerts:
        return "La operacion requiere vigilancia preventiva."
    if disconnected:
        return "Existen dispositivos sin conexion reciente y la continuidad del monitoreo debe verificarse."
    if latest is None:
        return "No existe evidencia reciente suficiente para evaluar la operacion."
    return "No se observan alertas activas en el contexto consultado."


def _recommended_actions(
    active_alerts: list[Alert],
    latest: SensorReading | None,
    disconnected: list[Device],
) -> list[str]:
    actions: list[str] = []
    if any(alert.severity == "critical" for alert in active_alerts):
        actions.append("Priorizar inspeccion fisica y documentar una accion correctiva.")
    elif active_alerts:
        actions.append("Revisar la tendencia de las variables asociadas a las alertas activas.")
    if disconnected:
        actions.append("Verificar energia, bateria, antena LoRa y conectividad del gateway.")
    if latest and latest.battery_voltage is not None and latest.battery_voltage < 3.5:
        actions.append("Programar revision tecnica del nodo por bateria baja.")
    if latest and latest.ambient_humidity is not None and latest.ambient_humidity > 75:
        actions.append("Revisar ventilacion y posibles puntos de condensacion.")
    if latest and latest.grain_temperature is not None and latest.grain_temperature > 32:
        actions.append("Verificar acumulacion termica en el punto monitoreado.")
    if not actions:
        actions.append("Mantener monitoreo y registrar cualquier intervencion en bitacora.")
    return actions[:4]


def _rules_answer(
    question: str,
    user: User,
    units_by_id: dict[int, StorageUnit],
    active_alerts: list[Alert],
    latest: SensorReading | None,
    disconnected: list[Device],
    interpretation: str,
    actions: list[str],
) -> str:
    normalized = _normalize(question)
    critical = [alert for alert in active_alerts if alert.severity == "critical"]

    if any(term in normalized for term in ("que silo", "cual silo", "necesita atencion", "prioridad")):
        alert = (critical or active_alerts or [None])[0]
        if alert is None:
            return f"{interpretation} No hay un silo con alerta activa para priorizar."
        unit = units_by_id.get(alert.storage_unit_id)
        return (
            f"Prioridad operativa: {unit.name if unit else 'unidad con alerta activa'}. "
            f"{alert.title}: {alert.message} Accion inmediata: {actions[0]}"
        )
    if any(term in normalized for term in ("desconect", "sin lectura", "gateway", "lora", "conexion")):
        if disconnected:
            names = ", ".join(device.name for device in disconnected[:4])
            return f"Hay {len(disconnected)} dispositivo(s) sin conexion reciente: {names}. {actions[0]}"
        return "No se identifican dispositivos desconectados en las unidades visibles."
    if any(term in normalized for term in ("reporte", "pdf", "descarg")):
        return "Abre Reportes, selecciona el silo o parcela y pulsa Descargar reporte PDF. El documento incluye metricas, alertas y bitacora del periodo."
    if any(term in normalized for term in ("mantenimiento", "bitacora", "accion correctiva", "instalacion")):
        if user.role == "client":
            return "Puedes consultar la bitacora y solicitar soporte. El registro tecnico debe realizarlo un tecnico o administrador para conservar trazabilidad."
        return "Abre Mantenimiento o Bitacora, selecciona la unidad y registra hallazgo, accion ejecutada, responsable, fecha y evidencia."
    if any(term in normalized for term in ("contrasena", "password", "cuenta", "perfil")):
        return "Abre el menu de cuenta y selecciona Cambiar contrasena. Si no recuerdas la clave, cierra sesion y usa Olvide password."
    if any(term in normalized for term in ("alerta critica", "que hago", "riesgo")) and critical:
        alert = critical[0]
        unit = units_by_id.get(alert.storage_unit_id)
        return f"Alerta critica en {unit.name if unit else 'una unidad visible'}: {alert.message} {actions[0]}"
    if latest is None:
        return f"{interpretation} Verifica dispositivo, gateway y ultima sincronizacion antes de tomar una decision."
    return f"{interpretation} Accion recomendada: {' '.join(actions[:2])}"


def _normalize(value: str) -> str:
    return value.lower().translate(
        str.maketrans({"\u00e1": "a", "\u00e9": "e", "\u00ed": "i", "\u00f3": "o", "\u00fa": "u", "\u00f1": "n"})
    )


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
    facts: list[str],
    interpretation: str,
    actions: list[str],
    role: str,
) -> tuple[str, int, int]:
    if not settings.gemini_api_key:
        raise ValueError("GEMINI_API_KEY is not configured")

    prompt = "\n".join(
        [
            "Eres el asistente operativo de AgroEscudo para monitoreo postcosecha.",
            "Responde en espanol claro y profesional, con maximo 120 palabras.",
            "Usa exclusivamente los hechos entregados. No inventes lecturas, diagnosticos, costos ni causas.",
            "Separa brevemente: Situacion, interpretacion y accion recomendada.",
            "Ante riesgo critico indica inspeccion humana y registro en bitacora.",
            f"Rol del usuario: {role}.",
            f"Pregunta: {question}",
            "Hechos verificados:",
            *[f"- {fact}" for fact in facts],
            f"Interpretacion del motor de reglas: {interpretation}",
            "Acciones permitidas:",
            *[f"- {action}" for action in actions],
        ]
    )
    model = settings.gemini_model.strip()
    url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent"
    payload = {
        "contents": [{"role": "user", "parts": [{"text": prompt}]}],
        "generationConfig": {"temperature": 0.2, "maxOutputTokens": 300},
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
