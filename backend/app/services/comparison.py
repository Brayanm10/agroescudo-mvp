from __future__ import annotations

from datetime import datetime, timezone
from statistics import mean

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import Device, SensorReading
from app.schemas import ComparisonOut

VARIABLES: dict[str, tuple[str, str]] = {
    "grain_temperature": ("grain_temperature", "C"),
    "ambient_temperature": ("ambient_temperature", "C"),
    "ambient_humidity": ("ambient_humidity", "%"),
    "battery_voltage": ("battery_voltage", "V"),
    "level_distance_cm": ("level_distance_cm", "cm"),
    "level_percent": ("level_percent", "%"),
    "soil_moisture_percent": ("soil_moisture_percent", "%"),
    "soil_temperature_c": ("soil_temperature_c", "C"),
}
MIN_COMPARISON_POINTS = 3


def compare_device_periods(
    db: Session,
    device: Device,
    *,
    variable: str,
    period_a_from: datetime,
    period_a_to: datetime,
    period_b_from: datetime,
    period_b_to: datetime,
) -> ComparisonOut:
    if variable not in VARIABLES:
        raise ValueError("Variable no compatible para comparacion.")
    if period_a_from >= period_a_to or period_b_from >= period_b_to:
        raise ValueError("Cada periodo debe tener un inicio anterior a su fin.")
    attribute, unit = VARIABLES[variable]
    values_a = _period_values(db, device.id, attribute, period_a_from, period_a_to)
    values_b = _period_values(db, device.id, attribute, period_b_from, period_b_to)
    cadence = device.expected_reading_interval_minutes
    summary_a = _summary(values_a, period_a_from, period_a_to, cadence)
    summary_b = _summary(values_b, period_b_from, period_b_to, cadence)
    sufficient = len(values_a) >= MIN_COMPARISON_POINTS and len(values_b) >= MIN_COMPARISON_POINTS
    absolute = percentage = None
    note = (
        "Comparacion descriptiva. No atribuye causalidad a mantenimiento, calibracion ni decisiones operativas."
        if sufficient
        else f"Datos insuficientes: se requieren al menos {MIN_COMPARISON_POINTS} valores validos por periodo."
    )
    if sufficient:
        absolute = round(summary_b["average"] - summary_a["average"], 4)
        if summary_a["average"] != 0:
            percentage = round(absolute / abs(summary_a["average"]) * 100, 2)
    return ComparisonOut(
        device_id=device.id,
        variable=variable,
        unit=unit,
        period_a=summary_a,
        period_b=summary_b,
        absolute_difference=absolute,
        percentage_difference=percentage,
        sufficient_data=sufficient,
        note=note,
    )


def _period_values(
    db: Session,
    device_id: int,
    attribute: str,
    date_from: datetime,
    date_to: datetime,
) -> list[tuple[datetime, float]]:
    rows = db.scalars(
        select(SensorReading)
        .where(
            SensorReading.device_id == device_id,
            SensorReading.timestamp >= date_from,
            SensorReading.timestamp <= date_to,
        )
        .order_by(SensorReading.timestamp)
    ).all()
    return [
        (_aware(row.timestamp), float(value))
        for row in rows
        if (value := getattr(row, attribute)) is not None
    ]


def _summary(
    values: list[tuple[datetime, float]],
    date_from: datetime,
    date_to: datetime,
    cadence_minutes: int | None,
) -> dict[str, object]:
    points = [value for _, value in values]
    expected = (
        int((_aware(date_to) - _aware(date_from)).total_seconds() / 60 // cadence_minutes) + 1
        if cadence_minutes
        else None
    )
    return {
        "from": _aware(date_from),
        "to": _aware(date_to),
        "count": len(points),
        "minimum": round(min(points), 4) if points else None,
        "maximum": round(max(points), 4) if points else None,
        "average": round(mean(points), 4) if points else None,
        "first": round(points[0], 4) if points else None,
        "last": round(points[-1], 4) if points else None,
        "expected": expected,
        "coverage_percent": round(min(len(points) / expected * 100, 100), 2) if expected else None,
        "coverage_method": "configured_cadence" if expected else "not_calculable_without_cadence",
    }


def _aware(value: datetime) -> datetime:
    return value if value.tzinfo is not None else value.replace(tzinfo=timezone.utc)
