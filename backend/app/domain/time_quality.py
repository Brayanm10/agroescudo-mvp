"""IoT wire time quality -> persisted uint8 code (no identity changes)."""


def persisted_time_quality(value: int | str) -> int:
    # V4 names documented in the HTTP contract; older gateways send numeric codes.
    if isinstance(value, bool):
        raise ValueError("time_quality debe ser un código numérico o SYNCED/NTP_SYNCED")
    if isinstance(value, str):
        token = value.strip().upper()
        if token in {"NTP_SYNCED", "SYNCED"}:
            return 2
        if not token.isascii() or not token.isdecimal():
            raise ValueError("time_quality no reconocido")
        value = int(token)
    if not isinstance(value, int) or not 0 <= value <= 255:
        raise ValueError("time_quality fuera del rango uint8 (0..255)")
    return value
