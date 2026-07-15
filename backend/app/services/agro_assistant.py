from __future__ import annotations

import httpx
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import require_storage_unit_access
from app.core.config import settings
from app.models import AiConversation, AiUsage, Alert, SensorReading, User
from app.schemas import AgroAssistantMessageIn, AgroAssistantMessageOut


def answer_agro_assistant(db: Session, user: User, payload: AgroAssistantMessageIn) -> AgroAssistantMessageOut:
    storage_unit_id = payload.storage_unit_id
    if storage_unit_id is not None:
        require_storage_unit_access(db, user, storage_unit_id)

    facts: list[str] = []
    actions: list[str] = []

    alert_stmt = select(Alert).where(Alert.is_active.is_(True))
    reading_stmt = select(SensorReading).order_by(SensorReading.timestamp.desc())
    if storage_unit_id is not None:
        alert_stmt = alert_stmt.where(Alert.storage_unit_id == storage_unit_id)
        reading_stmt = reading_stmt.where(SensorReading.storage_unit_id == storage_unit_id)
    elif user.company_id:
        alert_stmt = alert_stmt.where(Alert.company_id == user.company_id)
        reading_stmt = reading_stmt.where(SensorReading.company_id == user.company_id)

    active_alerts = list(db.scalars(alert_stmt.order_by(Alert.created_at.desc()).limit(5)).all())
    latest = db.scalar(reading_stmt.limit(1))

    if latest:
        facts.append(f"Ultima lectura: grano {latest.grain_temperature:.1f} C, humedad {latest.ambient_humidity:.1f}%, bateria {latest.battery_voltage:.2f} V.")
    else:
        facts.append("No hay lecturas recientes disponibles para el contexto consultado.")

    if active_alerts:
        facts.append(f"Alertas activas: {len(active_alerts)}.")
        if any(alert.severity == "critical" for alert in active_alerts):
            interpretation = "Hay riesgo operativo que requiere seguimiento inmediato."
            actions.append("Priorizar inspeccion fisica y documentar una accion correctiva.")
        else:
            interpretation = "La operacion requiere vigilancia preventiva."
            actions.append("Revisar ventilacion, aireacion y tendencias de las ultimas lecturas.")
    else:
        interpretation = "No se observan alertas activas en el contexto consultado."
        actions.append("Mantener monitoreo y registrar cualquier intervencion en bitacora.")

    if latest and latest.battery_voltage < 3.5:
        actions.append("Programar revision tecnica del nodo por bateria baja.")
    if latest and latest.ambient_humidity > 75:
        actions.append("Revisar ventilacion y posibles puntos de condensacion.")
    if latest and latest.grain_temperature > 32:
        actions.append("Verificar acumulacion termica en el punto monitoreado.")

    rules_answer = " ".join([interpretation, " ".join(actions[:3])])
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
            # Operational continuity matters more than the external model: rules remain available.
            answer = rules_answer
            source = "rules_fallback"

    conversation = AiConversation(
        company_id=user.company_id,
        user_id=user.id,
        storage_unit_id=storage_unit_id,
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
