#!/usr/bin/env python3
"""AgroEscudo - generador de lluvia SINTETICA usando la API IoT v4 EXISTENTE.

Por defecto solo imprime JSON: NO escribe en la base de datos.
Al usar --send, requiere confirmacion explicita y credenciales de un GATEWAY DEMO
aprovisionado separadamente. Nunca utiliza la contrasena de un usuario web.
"""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
import hmac
import json
import os
import secrets
import sys
import time
import urllib.error
import urllib.request
import uuid

API_DEFAULT = "https://agroescudo-api.onrender.com"
SCENARIOS = ("seco", "ligera", "moderada", "intensa")
CYCLE = ("seco", "ligera", "moderada", "intensa", "moderada", "ligera")
CHANNELS = (
    ("rain_1", "RAIN_DELTA_MM", "mm"),
    ("ambient_temp_1", "AMBIENT_TEMPERATURE_C", "degC"),
    ("ambient_rh_1", "AMBIENT_RELATIVE_HUMIDITY_PCT", "percent"),
    ("wind_speed_1", "WIND_SPEED_KMH", "km/h"),
    ("wind_direction_1", "WIND_DIRECTION_DEG", "degree"),
    ("battery_1", "BATTERY_PERCENT", "percent"),
)


def rain_mm(scenario: str, counter: int) -> float:
    """mm por intervalo; nunca mm acumulados. Semilla reproducible por indice."""
    if scenario == "seco":
        return 0.0
    if scenario == "ligera":
        return 0.2 if counter % 3 == 0 else 0.0
    if scenario == "moderada":
        return (1 + counter % 2) * 0.2
    if scenario == "intensa":
        return (3 + counter % 3) * 0.2
    raise ValueError("Escenario no soportado")


def build_batch(
    *, gateway_id: str, device_id: str, boot_id: int, sequence: int,
    scenario: str, timestamp_utc: int | None = None,
) -> dict:
    if not device_id.startswith("DEMO-"):
        raise ValueError("Solo se permiten dispositivos DEMO- separados de sensores reales")
    if scenario not in SCENARIOS:
        raise ValueError("Escenario invalido")
    ts = timestamp_utc if timestamp_utc is not None else int(time.time())
    sent_at = datetime.fromtimestamp(ts, timezone.utc).isoformat().replace("+00:00", "Z")
    rain = rain_mm(scenario, sequence)
    values = (
        rain, round(23 + (sequence % 7) * 0.15, 2),
        65 + min(25, SCENARIOS.index(scenario) * 7) + (sequence % 4),
        4.5 + (sequence % 5) * 1.5,
        float((347 + 5 * sequence) % 360),
        max(60.0, 91.0 - sequence * 0.04),
    )
    metrics = [
        {"channel_key": channel, "metric_code": metric, "raw_value": value,
         "unit": unit, "quality": "VALID"}
        for (channel, metric, unit), value in zip(CHANNELS, values)
    ]
    return {
        "gateway_id": gateway_id,
        "firmware_version": "DEMO-SIM-PC-1.0",
        "sent_at": sent_at,
        "batch_id": "demo-" + uuid.uuid4().hex,
        "protocol_version": 4,
        "events": [{
            "device_id": device_id,
            "boot_id": boot_id,
            "sequence": sequence,
            "sample_counter": sequence,
            "timestamp_utc": ts,
            "time_quality": "NTP_SYNCED",
            "firmware_version": "DEMO-SIM-PC-1.0",
            "protocol_version": 4,
            "capabilities_version": 1,
            "sensor_profile": "rain_gauge",
            "sensor_status_flags": 0,
            "metrics": metrics,
        }],
    }


def signed_headers(body: bytes, *, gateway_id: str, gateway_secret: str, timestamp: int | None = None) -> dict[str, str]:
    ts = str(timestamp if timestamp is not None else int(time.time()))
    nonce = "demo-" + uuid.uuid4().hex
    digest = hashlib.sha256(body).hexdigest()
    message = f"{gateway_id}{ts}{nonce}{digest}".encode("utf-8")
    signature = hmac.new(gateway_secret.encode("utf-8"), message, hashlib.sha256).hexdigest()
    return {
        "Content-Type": "application/json",
        "X-Agro-Gateway-ID": gateway_id,
        "X-Agro-Timestamp": ts,
        "X-Agro-Nonce": nonce,
        "X-Agro-Signature": signature,
    }


def send_batch(api_url: str, batch: dict, gateway_id: str, gateway_secret: str) -> str:
    body = json.dumps(batch, separators=(",", ":")).encode("utf-8")
    headers = signed_headers(body, gateway_id=gateway_id, gateway_secret=gateway_secret)
    req = urllib.request.Request(api_url.rstrip("/") + "/api/iot/v1/ingest/batch",
                                 data=body, headers=headers, method="POST")
    with urllib.request.urlopen(req, timeout=20) as response:
        if response.status != 200:
            raise RuntimeError(f"HTTP {response.status}")
        payload = json.load(response)
    results = payload.get("results", [])
    if len(results) != 1:
        raise RuntimeError("Respuesta de lote inesperada")
    state = results[0].get("status", "")
    if state not in {"accepted", "duplicate"}:
        raise RuntimeError(f"Lectura NO aceptada por backend: {state} / {results[0].get('detail', '')}")
    return state


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--device-id", default="DEMO-PLUV-SYA-01")
    parser.add_argument("--scenario", choices=(*SCENARIOS, "auto"), default="auto")
    parser.add_argument("--count", type=int, default=5)
    parser.add_argument("--interval", type=float, default=60.0, help="Segundos reales entre mediciones")
    parser.add_argument("--api-url", default=API_DEFAULT)
    parser.add_argument("--send", action="store_true", help="Habilitar envio real, de forma explicita")
    parser.add_argument("--confirm-demo-device", action="store_true",
                        help="Confirma que dispositivo/gateway DEMO existen y NO tienen mediciones reales")
    args = parser.parse_args()
    if args.count < 1 or args.interval < 1:
        parser.error("--count y --interval deben ser positivos, intervalo minimo 1 s")
    if not args.device_id.startswith("DEMO-"):
        parser.error("El ID del dispositivo debe comenzar por DEMO-")
    if args.send and not args.confirm_demo_device:
        parser.error("--send requiere --confirm-demo-device para evitar escribir en sensores reales")
    if args.send and not args.api_url.startswith("https://"):
        parser.error("La API de envio debe usar HTTPS; no se permite HTTP sin TLS")
    gateway_id = os.getenv("AGRO_DEMO_GATEWAY_ID", "DEMO-GW-SYA-01")
    gateway_secret = os.getenv("AGRO_DEMO_GATEWAY_SECRET", "")
    if args.send and (not gateway_secret or not gateway_id.startswith("DEMO-")):
        parser.error("Define AGRO_DEMO_GATEWAY_ID=DEMO-... y AGRO_DEMO_GATEWAY_SECRET dedicado")
    boot_id = secrets.randbits(31)
    for seq in range(args.count):
        scenario = CYCLE[seq % len(CYCLE)] if args.scenario == "auto" else args.scenario
        batch = build_batch(gateway_id=gateway_id, device_id=args.device_id,
                            boot_id=boot_id, sequence=seq, scenario=scenario)
        event = batch["events"][0]
        print(f"[SIMULADO] {scenario}: {event['metrics'][0]['raw_value']} mm/intervalo; "
              f"device={args.device_id} sequence={seq}", flush=True)
        if args.send:
            try:
                # Reintentos conservan el mismo boot+seq, usan batch_id/nonce nuevos.
                for attempt in range(1, 4):
                    if attempt > 1:
                        time.sleep(min(2 ** attempt, 10))
                        batch["batch_id"] = "demo-" + uuid.uuid4().hex
                        batch["sent_at"] = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
                    try:
                        status = send_batch(args.api_url, batch, gateway_id, gateway_secret)
                        print("API ->", status, flush=True)
                        break
                    except (urllib.error.URLError, OSError, ValueError, RuntimeError) as exc:
                        print(f"Intento {attempt}/3 fallido: {type(exc).__name__}: {exc}", file=sys.stderr)
                        if attempt == 3:
                            print("STOP: lectura no confirmada; se detiene para evitar una serie con huecos.", file=sys.stderr)
                            return 2
            except KeyboardInterrupt:
                return 130
        else:
            print(json.dumps(batch, ensure_ascii=False, indent=2))
        if seq != args.count - 1:
            time.sleep(args.interval)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
