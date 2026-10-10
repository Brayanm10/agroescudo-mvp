#!/usr/bin/env python3
"""Simulador AgroEscudo V4 pluviometría. Imprime JSON por defecto; --send es explícito.

No inicia sesión como usuario, ni usa credenciales humanas. Requiere un gateway
HMAC dedicado y un rain_gauge de demostración, ya aprovisionados por administrador.
"""
import argparse
import hashlib
import hmac
import json
import os
import random
import sys
import time
import urllib.error
import urllib.request
import uuid
from datetime import datetime, timezone

SCENARIOS = ("seco", "ligera", "moderada", "intensa")
RAIN = {"seco": (0, 0), "ligera": (0, 1), "moderada": (1, 2), "intensa": (2, 4)}


def make_event(device_id, scenario, boot_id, sequence):
    low, high = RAIN[scenario]
    tips = random.randint(low, high)
    if scenario == "ligera" and random.random() < 0.8:
        tips = 0
    rain_mm = round(tips * 0.2, 2)
    metrics = [
        ("rain_1", "RAIN_DELTA_MM", rain_mm, "mm"),
        ("ambient_temp_1", "AMBIENT_TEMPERATURE_C", round(random.uniform(19.5, 26.0), 2), "degC"),
        ("ambient_rh_1", "AMBIENT_RELATIVE_HUMIDITY_PCT", round(random.uniform(60, 95), 2), "percent"),
        ("battery_1", "BATTERY_PERCENT", round(random.uniform(78, 90), 2), "percent"),
    ]
    return {
        "device_id": device_id, "boot_id": boot_id, "sequence": sequence,
        "sample_counter": sequence, "timestamp_utc": int(time.time()),
        "time_quality": "NTP_SYNCED", "firmware_version": "sya-demo-1.0",
        "protocol_version": 4, "capabilities_version": 1,
        "sensor_profile": "rain_gauge", "sensor_status_flags": 0,
        "metrics": [
            {"channel_key": channel, "metric_code": code, "raw_value": value,
             "unit": unit, "quality": "VALID"}
            for channel, code, value, unit in metrics
        ],
    }


def signed_headers(gateway_id, secret, body):
    timestamp = str(int(time.time()))
    nonce = uuid.uuid4().hex
    digest = hashlib.sha256(body).hexdigest()
    message = (gateway_id + timestamp + nonce + digest).encode("utf-8")
    signature = hmac.new(secret.encode("utf-8"), message, hashlib.sha256).hexdigest()
    return {
        "Content-Type": "application/json",
        "X-Agro-Gateway-ID": gateway_id,
        "X-Agro-Timestamp": timestamp,
        "X-Agro-Nonce": nonce,
        "X-Agro-Signature": signature,
    }


def post_event(base_url, gateway_id, secret, payload, timeout=20):
    raw = json.dumps(payload, separators=(",", ":"), ensure_ascii=False).encode("utf-8")
    req = urllib.request.Request(
        base_url.rstrip("/") + "/api/iot/v1/ingest/batch",
        data=raw, method="POST",
        headers=signed_headers(gateway_id, secret, raw),
    )
    try:
        with urllib.request.urlopen(req, timeout=timeout) as response:
            doc = json.load(response)
    except (urllib.error.HTTPError, urllib.error.URLError, ValueError) as exc:
        print(f"Error de envío: {exc}", file=sys.stderr)
        return False
    results = doc.get("results", [])
    statuses = [r.get("status") for r in results]
    print("Respuesta del backend (estados):", statuses)
    return len(statuses) == 1 and statuses[0] in ("accepted", "duplicate")


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--count", type=int, default=5)
    parser.add_argument("--interval", type=float, default=60, help="Segundos entre muestras")
    parser.add_argument("--scenario", choices=(*SCENARIOS, "auto"), default="auto")
    parser.add_argument("--send", action="store_true", help="Envío HTTPS explícito; por defecto solo JSON")
    parser.add_argument("--base-url", default="https://agroescudo-api.onrender.com")
    args = parser.parse_args(argv)
    if args.count < 1 or args.interval < 0:
        parser.error("count >= 1 y interval >= 0")
    gateway = os.getenv("AGRO_DEMO_GATEWAY_ID", "GW-DEMO-SYA-01")
    device = os.getenv("AGRO_DEMO_DEVICE_ID", "PLUVIO-DEMO-SYA-01")
    secret = os.getenv("AGRO_DEMO_GATEWAY_SECRET", "")
    if args.send and (not secret or not args.base_url.startswith("https://")):
        parser.error("Para --send se requiere AGRO_DEMO_GATEWAY_SECRET y una URL HTTPS.")
    boot_id = random.SystemRandom().randint(1, 2**31 - 1)
    for seq in range(args.count):
        scene = SCENARIOS[(seq // 3) % 4] if args.scenario == "auto" else args.scenario
        now = datetime.now(timezone.utc).isoformat()
        event = make_event(device, scene, boot_id, seq)
        payload = {
            "gateway_id": gateway, "firmware_version": "sya-demo-1.0",
            "sent_at": now, "batch_id": uuid.uuid4().hex, "protocol_version": 4,
            "events": [event],
        }
        if args.send:
            # En caso de fallo, retentar misma lectura/evento, con nueva firma y batch_id.
            if not post_event(args.base_url, gateway, secret, payload):
                print("Detenido: no se avanzará la secuencia tras un error.", file=sys.stderr)
                return 1
        else:
            print(json.dumps({"mode": "SIMULADO / NO ENVIADO", "scenario": scene, "batch": payload},
                             ensure_ascii=False, indent=2))
        if seq < args.count - 1:
            time.sleep(args.interval)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
