"""Validate AgroEscudo deployment variables without printing secret values."""

from __future__ import annotations

import argparse
import os
import re
from pathlib import Path


PLACEHOLDERS = {"", "changeme", "change-me-in-production", "secret", "default", "tu_token", "your_key"}


def load_env(path: Path | None) -> dict[str, str]:
    values = dict(os.environ)
    if not path or not path.exists():
        return values
    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        values.setdefault(key.strip(), value.strip().strip('"').strip("'"))
    return values


def enabled(values: dict[str, str], key: str) -> bool:
    return values.get(key, "false").strip().lower() in {"1", "true", "yes", "on"}


def missing_or_placeholder(value: str | None) -> bool:
    if value is None or value.strip().lower() in PLACEHOLDERS:
        return True
    lowered = value.lower()
    return any(marker in lowered for marker in ("<tu_", "tu-", "example.com", "xxxxx", "replace_me"))


def classify(values: dict[str, str], key: str, *, required: bool, secret: bool = False) -> tuple[str, str]:
    value = values.get(key)
    if missing_or_placeholder(value):
        return ("MISSING" if required else "OPTIONAL", "valor no configurado")
    if key.endswith("URL") or key in {"API_URL", "PUBLIC_APP_URL", "S3_ENDPOINT_URL"}:
        if not re.match(r"^https?://", value or ""):
            return "INVALID", "debe comenzar con http:// o https://"
    if key == "JWT_SECRET" and len(value or "") < 32:
        return "INVALID", "debe tener al menos 32 caracteres"
    return "SET", "secreto presente" if secret else "configurado"


def main() -> int:
    parser = argparse.ArgumentParser(description="Audita variables de AgroEscudo sin revelar secretos.")
    parser.add_argument("--env-file", type=Path, default=None)
    parser.add_argument("--environment", choices=["local", "demo", "production"], default=None)
    args = parser.parse_args()
    values = load_env(args.env_file)
    environment = args.environment or values.get("ENVIRONMENT", "local").lower()

    checks: list[tuple[str, bool, bool]] = [
        ("DATABASE_URL", environment in {"demo", "production"}, True),
        ("JWT_SECRET", environment in {"demo", "production"}, True),
        ("CORS_ORIGINS", environment == "production", False),
        ("API_URL", environment in {"demo", "production"}, False),
        ("PUBLIC_APP_URL", environment in {"demo", "production"}, False),
    ]

    conditional = {
        "EMAIL_ENABLED": [("EMAIL_FROM", False), ("EMAIL_API_KEY", True)],
        "TELEGRAM_ENABLED": [("TELEGRAM_BOT_TOKEN", True)],
        "WHATSAPP_ENABLED": [
            ("WHATSAPP_ACCESS_TOKEN", True),
            ("WHATSAPP_PHONE_NUMBER_ID", False),
            ("WHATSAPP_TEMPLATE_ALERT_NAME", False),
        ],
        "FCM_ENABLED": [("FIREBASE_PROJECT_ID", False), ("FIREBASE_SERVICE_ACCOUNT_JSON", True)],
        "SENTRY_ENABLED": [("SENTRY_DSN", True)],
    }
    for flag, variables in conditional.items():
        active = enabled(values, flag)
        print(f"{flag:<38} {'ENABLED' if active else 'DISABLED'}")
        for key, secret in variables:
            checks.append((key, active, secret))

    ai_active = enabled(values, "AI_ENABLED") and enabled(values, "AGRO_ASSISTANT_LLM_ENABLED")
    provider = values.get("AI_PROVIDER", "rules").lower()
    print(f"{'AI_PROVIDER':<38} {provider} ({'ENABLED' if ai_active else 'DISABLED'})")
    if ai_active and provider == "gemini":
        checks.append(("GEMINI_API_KEY", True, True))
    elif ai_active and provider == "openai":
        checks.append(("OPENAI_API_KEY", True, True))

    storage_s3 = values.get("STORAGE_PROVIDER", "local").lower() == "s3"
    print(f"{'STORAGE_PROVIDER':<38} {'s3' if storage_s3 else 'local'}")
    for key, secret in [
        ("S3_ENDPOINT_URL", False),
        ("S3_BUCKET", False),
        ("S3_ACCESS_KEY_ID", True),
        ("S3_SECRET_ACCESS_KEY", True),
    ]:
        checks.append((key, storage_s3, secret))

    failed = False
    print(f"{'VARIABLE':<38} {'STATUS':<10} DETAIL")
    print("-" * 78)
    for key, required, secret in checks:
        status, detail = classify(values, key, required=required, secret=secret)
        if status in {"MISSING", "INVALID"}:
            failed = True
        print(f"{key:<38} {status:<10} {detail}")

    print("\nResultado:", "NO LISTO" if failed else "LISTO para la configuracion seleccionada")
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
