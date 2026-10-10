from __future__ import annotations

import math


MAIZE_A = 312.40
MAIZE_B = 16.958
MAIZE_C = 30.205


def dry_basis_to_wet_basis_pct(moisture_dry_basis: float) -> float:
    """Convert a decimal dry-basis moisture ratio to wet-basis percent."""
    value = float(moisture_dry_basis)
    if not math.isfinite(value) or value < 0:
        raise ValueError("Dry-basis moisture must be finite and non-negative.")
    return (value / (1.0 + value)) * 100.0


def calculate_maize_emc_wb(temperature_c: float, relative_humidity_pct: float) -> float:
    """Return maize equilibrium moisture content as wet-basis percent."""
    temperature = float(temperature_c)
    humidity = float(relative_humidity_pct)
    if not math.isfinite(temperature) or not math.isfinite(humidity):
        raise ValueError("Temperature and relative humidity must be finite.")
    if not 0 < humidity < 100:
        raise ValueError("Relative humidity must be strictly between 0 and 100 percent.")
    if temperature + MAIZE_C <= 0:
        raise ValueError("Temperature is outside the valid Modified Chung-Pfost domain.")
    argument = -((temperature + MAIZE_C) * math.log(humidity / 100.0)) / MAIZE_A
    if argument <= 0:
        raise ValueError("Inputs are outside the valid Modified Chung-Pfost domain.")
    moisture_dry_basis = -math.log(argument) / MAIZE_B
    if moisture_dry_basis <= 0 or not math.isfinite(moisture_dry_basis):
        raise ValueError("Calculated dry-basis moisture is invalid.")
    return dry_basis_to_wet_basis_pct(moisture_dry_basis)


def apply_emc_offset(raw_emc_wb: float, offset_pp: float | None) -> float:
    value = float(raw_emc_wb) + (float(offset_pp) if offset_pp is not None else 0.0)
    return min(100.0, max(0.0, value))
