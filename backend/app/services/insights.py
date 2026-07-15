from __future__ import annotations

from datetime import datetime, timedelta, timezone
from statistics import mean
from typing import Literal

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import Alert, Device, OperationalLog, SensorReading, StorageUnit, ThresholdConfig, utc_now
from app.schemas import InsightEvidenceOut, StorageUnitInsightOut

Period = Literal["24h", "7d", "30d"]


def period_start(period: Period) -> datetime:
    now = datetime.now(timezone.utc)
    if period == "24h":
        return now - timedelta(hours=24)
    if period == "7d":
        return now - timedelta(days=7)
    return now - timedelta(days=30)


def build_storage_unit_insight(db: Session, storage_unit: StorageUnit, period: Period) -> StorageUnitInsightOut:
    start = period_start(period)
    readings = list(
        db.scalars(
            select(SensorReading)
            .where(
                SensorReading.storage_unit_id == storage_unit.id,
                SensorReading.timestamp >= start,
            )
            .order_by(SensorReading.timestamp.asc())
        ).all()
    )
    alerts = list(
        db.scalars(
            select(Alert)
            .where(Alert.storage_unit_id == storage_unit.id, Alert.created_at >= start)
            .order_by(Alert.created_at.desc())
        ).all()
    )
    active_alerts = [alert for alert in alerts if alert.is_active]
    devices = list(db.scalars(select(Device).where(Device.storage_unit_id == storage_unit.id)).all())
    logs = list(
        db.scalars(
            select(OperationalLog)
            .where(OperationalLog.storage_unit_id == storage_unit.id, OperationalLog.timestamp >= start)
            .order_by(OperationalLog.timestamp.desc())
        ).all()
    )
    thresholds = _thresholds(db, storage_unit.id)

    status = _status(readings, active_alerts, devices)
    confidence: Literal["high", "medium", "low"] = "high" if len(readings) >= 12 else "medium" if len(readings) >= 3 else "low"
    evidence: list[InsightEvidenceOut] = [
        InsightEvidenceOut(label="Lecturas del periodo", value=str(len(readings))),
        InsightEvidenceOut(label="Alertas activas", value=str(len(active_alerts))),
        InsightEvidenceOut(label="Acciones en bitacora", value=str(len(logs))),
    ]
    recommendations = _recommendations(storage_unit, readings, active_alerts, devices, thresholds)
    summary = _summary(storage_unit, readings, active_alerts, devices, thresholds)

    if readings:
        latest = readings[-1]
        evidence.extend(
            [
                InsightEvidenceOut(label="Ultima temperatura grano", value=f"{latest.grain_temperature:.1f} C"),
                InsightEvidenceOut(label="Ultima humedad", value=f"{latest.ambient_humidity:.1f}%"),
                InsightEvidenceOut(label="Ultima bateria", value=f"{latest.battery_voltage:.2f} V"),
            ]
        )

    return StorageUnitInsightOut(
        storage_unit_id=storage_unit.id,
        storage_unit_name=storage_unit.name,
        period=period,
        status=status,
        confidence=confidence,
        data_points=len(readings),
        summary=summary,
        recommendations=recommendations,
        evidence=evidence,
        generated_at=utc_now(),
    )


def _thresholds(db: Session, storage_unit_id: int) -> dict[str, float]:
    configs = db.scalars(
        select(ThresholdConfig).where(
            ThresholdConfig.storage_unit_id == storage_unit_id,
            ThresholdConfig.is_active.is_(True),
        )
    ).all()
    return {config.metric: config.value for config in configs}


def _status(
    readings: list[SensorReading],
    active_alerts: list[Alert],
    devices: list[Device],
) -> Literal["normal", "attention", "critical", "offline", "insufficient_data"]:
    if any(alert.severity == "critical" for alert in active_alerts):
        return "critical"
    if any(alert.severity in {"warning", "technical"} for alert in active_alerts):
        return "attention"
    if not readings:
        if devices and all(not device.last_seen_at for device in devices):
            return "offline"
        return "insufficient_data"
    latest = readings[-1]
    if (datetime.now(timezone.utc) - latest.timestamp.astimezone(timezone.utc)).total_seconds() > 24 * 3600:
        return "offline"
    return "normal"


def _summary(
    storage_unit: StorageUnit,
    readings: list[SensorReading],
    active_alerts: list[Alert],
    devices: list[Device],
    thresholds: dict[str, float],
) -> str:
    if not readings:
        if devices:
            return f"No hay lecturas recientes suficientes para evaluar {storage_unit.name} con confianza."
        return f"{storage_unit.name} no tiene dispositivos registrados para emitir una lectura operativa."

    latest = readings[-1]
    if any(alert.severity == "critical" for alert in active_alerts):
        return f"{storage_unit.name} requiere atencion inmediata por alerta critica activa."
    if active_alerts:
        return f"{storage_unit.name} tiene condiciones en atencion y debe mantenerse bajo seguimiento operativo."

    grain_threshold = thresholds.get("grain_temperature")
    humidity_threshold = thresholds.get("ambient_humidity")
    if grain_threshold is not None and latest.grain_temperature > grain_threshold:
        return f"{storage_unit.name} supero el umbral de temperatura de grano configurado."
    if humidity_threshold is not None and latest.ambient_humidity > humidity_threshold:
        return f"{storage_unit.name} supero el umbral de humedad ambiental configurado."
    return f"{storage_unit.name} se mantiene dentro de condiciones operativas aceptables con la evidencia disponible."


def _recommendations(
    storage_unit: StorageUnit,
    readings: list[SensorReading],
    active_alerts: list[Alert],
    devices: list[Device],
    thresholds: dict[str, float],
) -> list[str]:
    if not readings:
        return ["No hay suficientes lecturas recientes para emitir una recomendacion confiable."]

    latest = readings[-1]
    recommendations: list[str] = []
    if any(alert.severity == "critical" for alert in active_alerts):
        recommendations.append("Priorizar intervencion operativa y registrar la accion correctiva en bitacora.")
    if any("humidity" in alert.alert_type for alert in active_alerts):
        recommendations.append("Revisar ventilacion, aireacion y posibles puntos de condensacion.")
    if any("temperature" in alert.alert_type or "environment" in alert.alert_type for alert in active_alerts):
        recommendations.append("Inspeccionar fisicamente el punto monitoreado y verificar acumulacion termica.")
    if any("battery" in alert.alert_type for alert in active_alerts):
        recommendations.append("Programar revision tecnica del nodo y validar alimentacion.")

    grain_threshold = thresholds.get("grain_temperature")
    humidity_threshold = thresholds.get("ambient_humidity")
    if grain_threshold is not None and latest.grain_temperature > grain_threshold:
        recommendations.append(f"La temperatura del grano ({latest.grain_temperature:.1f} C) supera el umbral configurado de {grain_threshold:.1f} C.")
    if humidity_threshold is not None and latest.ambient_humidity > humidity_threshold:
        recommendations.append(f"La humedad relativa ({latest.ambient_humidity:.1f}%) supera el umbral configurado de {humidity_threshold:.1f}%.")

    trend = _trend(readings, "grain_temperature")
    if trend is not None and abs(trend) >= 2:
        direction = "subio" if trend > 0 else "bajo"
        recommendations.append(f"La temperatura del grano {direction} {abs(trend):.1f} C durante el periodo analizado.")

    if latest.battery_voltage < thresholds.get("battery_voltage", 3.5):
        recommendations.append("La bateria esta por debajo del minimo operativo; programar revision tecnica del sensor.")

    if not recommendations:
        recommendations.append("Operacion estable. Mantener monitoreo y revisar reporte semanal.")
    return recommendations[:5]


def _trend(readings: list[SensorReading], field: str) -> float | None:
    if len(readings) < 4:
        return None
    midpoint = len(readings) // 2
    first = [getattr(reading, field) for reading in readings[:midpoint]]
    second = [getattr(reading, field) for reading in readings[midpoint:]]
    if not first or not second:
        return None
    return mean(second) - mean(first)
