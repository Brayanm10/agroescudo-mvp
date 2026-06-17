from __future__ import annotations

import json

import httpx
from sqlalchemy.orm import Session

from app.core.config import settings
from app.models import Alert, Device, SensorReading, StorageUnit
from app.schemas import AiAlertRecommendationOut


def build_alert_recommendation(db: Session, alert: Alert) -> AiAlertRecommendationOut:
    reading = db.get(SensorReading, alert.reading_id) if alert.reading_id else None
    device = db.get(Device, alert.device_id)
    storage_unit = db.get(StorageUnit, alert.storage_unit_id)
    fallback = _rule_based(alert, reading, device, storage_unit)

    if not settings.ai_enabled or not settings.openai_api_key:
        return fallback

    try:
        payload = _call_openai(alert, reading, device, storage_unit)
        return AiAlertRecommendationOut(alert_id=alert.id, source="openai", **payload)
    except Exception:
        return fallback


def _rule_based(
    alert: Alert,
    reading: SensorReading | None,
    device: Device | None,
    storage_unit: StorageUnit | None,
) -> AiAlertRecommendationOut:
    actions: list[str] = []
    notes: list[str] = []
    if "humidity" in alert.alert_type:
        actions.append("Revisar ventilacion, aireacion y posibles puntos de condensacion.")
    if "temperature" in alert.alert_type or "environment" in alert.alert_type:
        actions.append("Inspeccionar fisicamente el punto monitoreado y verificar acumulacion termica.")
    if "battery" in alert.alert_type:
        actions.append("Programar revision tecnica del nodo y validar alimentacion.")
    if alert.severity == "critical":
        actions.insert(0, "Priorizar intervencion operativa y registrar accion correctiva.")
    if not actions:
        actions.append("Evaluar condicion operativa y documentar seguimiento.")

    if reading is not None:
        notes.append(
            f"Ultima lectura asociada: grano {reading.grain_temperature:.1f} C, "
            f"humedad {reading.ambient_humidity:.1f}%, bateria {reading.battery_voltage:.2f} V."
        )
    if device is not None:
        notes.append(f"Dispositivo: {device.external_id}.")

    unit_name = storage_unit.name if storage_unit is not None else "unidad monitoreada"
    return AiAlertRecommendationOut(
        alert_id=alert.id,
        source="rules",
        risk_level=alert.severity,
        summary=f"{alert.title} en {unit_name}. {alert.message}",
        recommended_actions=actions,
        client_message=f"AgroEscudo detecto una condicion {alert.severity} en {unit_name}. El equipo debe revisar la alerta y registrar la accion tomada.",
        technical_notes=notes,
    )


def _call_openai(
    alert: Alert,
    reading: SensorReading | None,
    device: Device | None,
    storage_unit: StorageUnit | None,
) -> dict:
    context = {
        "alert": {
            "type": alert.alert_type,
            "severity": alert.severity,
            "title": alert.title,
            "message": alert.message,
        },
        "storage_unit": storage_unit.name if storage_unit else None,
        "device": device.external_id if device else None,
        "reading": {
            "grain_temperature": reading.grain_temperature,
            "ambient_temperature": reading.ambient_temperature,
            "ambient_humidity": reading.ambient_humidity,
            "battery_voltage": reading.battery_voltage,
            "signal_quality": reading.signal_quality,
        }
        if reading
        else None,
    }
    schema = {
        "type": "json_schema",
        "name": "agroescudo_alert_recommendation",
        "schema": {
            "type": "object",
            "additionalProperties": False,
            "properties": {
                "risk_level": {"type": "string"},
                "summary": {"type": "string"},
                "recommended_actions": {"type": "array", "items": {"type": "string"}},
                "client_message": {"type": "string"},
                "technical_notes": {"type": "array", "items": {"type": "string"}},
            },
            "required": ["risk_level", "summary", "recommended_actions", "client_message", "technical_notes"],
        },
    }
    response = httpx.post(
        "https://api.openai.com/v1/responses",
        headers={"Authorization": f"Bearer {settings.openai_api_key}"},
        json={
            "model": settings.openai_model,
            "input": [
                {
                    "role": "system",
                    "content": "Eres un asistente operativo agroindustrial. No inventes datos. Da recomendaciones concretas y sobrias.",
                },
                {
                    "role": "user",
                    "content": f"Genera recomendacion para esta alerta AgroEscudo: {json.dumps(context, ensure_ascii=False)}",
                },
            ],
            "text": {"format": schema},
        },
        timeout=20,
    )
    response.raise_for_status()
    data = response.json()
    text = data.get("output_text")
    if not text:
        for item in data.get("output", []):
            for content in item.get("content", []):
                if content.get("type") in {"output_text", "text"}:
                    text = content.get("text")
                    break
    if not text:
        raise ValueError("OpenAI response did not include output text")
    return json.loads(text)
