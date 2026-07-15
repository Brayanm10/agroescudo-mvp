"""Configure AgroEscudo external integrations in Render without revealing secrets.

The script reads the ignored local credential form, validates complete provider
groups, updates individual Render environment variables, and optionally triggers
a deploy. Dry-run is the default and never calls the Render API.
"""

from __future__ import annotations

import argparse
import base64
import json
import re
import shutil
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable
from urllib.error import HTTPError, URLError
from urllib.parse import quote
from urllib.request import Request, urlopen


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_CREDENTIALS = ROOT / "tmp" / "AGROESCUDO_CREDENCIALES_PENDIENTES.txt"
RENDER_API_BASE = "https://api.render.com/v1"

PLACEHOLDER_MARKERS = (
    "cambiar",
    "changeme",
    "change-me",
    "placeholder",
    "demo_",
    "_demo",
    "tu_dominio",
    "tu-dominio",
    "your_",
    "example.com",
    "xxxxx",
)


@dataclass(frozen=True)
class ProviderResult:
    name: str
    configured: bool
    variables: dict[str, str]
    errors: tuple[str, ...] = ()


class RenderApiError(RuntimeError):
    def __init__(self, action: str, status: int | None = None) -> None:
        detail = f" (HTTP {status})" if status else ""
        super().__init__(f"Render rechazo la operacion '{action}'{detail}.")
        self.status = status


def load_credentials(path: Path) -> dict[str, str]:
    if not path.exists():
        raise FileNotFoundError(f"No existe el archivo de credenciales: {path}")

    values: dict[str, str] = {}
    for raw_line in path.read_text(encoding="utf-8-sig").splitlines():
        line = raw_line.strip()
        if not line or line.startswith(("#", "[")) or "=" not in line:
            continue
        key, value = line.split("=", 1)
        key = key.strip()
        if re.fullmatch(r"[A-Z][A-Z0-9_]*", key):
            values[key] = value.strip().strip('"').strip("'")
    return values


def is_real(value: str | None) -> bool:
    if not value or not value.strip():
        return False
    normalized = value.strip()
    lowered = normalized.lower()
    if normalized == "591" or lowered.endswith("/591"):
        return False
    return not any(marker in lowered for marker in PLACEHOLDER_MARKERS)


def complete_group(
    values: dict[str, str],
    name: str,
    required: Iterable[str],
    mapped: dict[str, str],
) -> ProviderResult:
    required_keys = tuple(required)
    present = [key for key in required_keys if is_real(values.get(key))]
    if not present:
        return ProviderResult(name=name, configured=False, variables={})
    missing = tuple(key for key in required_keys if not is_real(values.get(key)))
    if missing:
        return ProviderResult(
            name=name,
            configured=False,
            variables={},
            errors=(f"configuracion parcial; falta: {', '.join(missing)}",),
        )
    return ProviderResult(name=name, configured=True, variables=mapped)


def firebase_provider(values: dict[str, str]) -> ProviderResult:
    project_id = values.get("FIREBASE_PROJECT_ID")
    service_path = values.get("FIREBASE_SERVICE_ACCOUNT_JSON_PATH")
    google_path = values.get("GOOGLE_SERVICES_JSON_PATH")
    any_present = any(is_real(value) for value in (project_id, service_path, google_path))
    if not any_present:
        return ProviderResult("Firebase FCM", False, {})

    errors: list[str] = []
    if not is_real(project_id):
        errors.append("falta FIREBASE_PROJECT_ID")

    service_json: dict[str, object] | None = None
    service_file = Path(service_path).expanduser() if is_real(service_path) else None
    if not service_file or not service_file.is_file():
        errors.append("FIREBASE_SERVICE_ACCOUNT_JSON_PATH no apunta a un archivo")
    else:
        try:
            service_json = json.loads(service_file.read_text(encoding="utf-8"))
            if service_json.get("type") != "service_account":
                errors.append("el JSON de backend no es una service account")
            if project_id and service_json.get("project_id") != project_id:
                errors.append("FIREBASE_PROJECT_ID no coincide con la service account")
        except (OSError, json.JSONDecodeError):
            errors.append("la service account no contiene JSON valido")

    google_file = Path(google_path).expanduser() if is_real(google_path) else None
    if not google_file or not google_file.is_file():
        errors.append("GOOGLE_SERVICES_JSON_PATH no apunta a un archivo")
    else:
        try:
            google_json = json.loads(google_file.read_text(encoding="utf-8"))
            clients = google_json.get("client", [])
            packages = {
                item.get("client_info", {}).get("android_client_info", {}).get("package_name")
                for item in clients
                if isinstance(item, dict)
            }
            if "com.agroescudo.mobile" not in packages:
                errors.append("google-services.json no pertenece a com.agroescudo.mobile")
            if project_id and google_json.get("project_info", {}).get("project_id") != project_id:
                errors.append("FIREBASE_PROJECT_ID no coincide con google-services.json")
        except (OSError, json.JSONDecodeError):
            errors.append("google-services.json no contiene JSON valido")

    if errors or service_json is None:
        return ProviderResult("Firebase FCM", False, {}, tuple(errors))

    raw_json = json.dumps(service_json, separators=(",", ":"), ensure_ascii=True).encode("utf-8")
    return ProviderResult(
        "Firebase FCM",
        True,
        {
            "FCM_ENABLED": "true",
            "FIREBASE_PROJECT_ID": project_id or "",
            "FIREBASE_SERVICE_ACCOUNT_JSON": base64.b64encode(raw_json).decode("ascii"),
        },
    )


def build_provider_results(values: dict[str, str]) -> list[ProviderResult]:
    gemini = complete_group(
        values,
        "Gemini",
        ("GEMINI_API_KEY",),
        {
            "AI_ENABLED": "true",
            "AGRO_ASSISTANT_LLM_ENABLED": "true",
            "AI_PROVIDER": "gemini",
            "GEMINI_API_KEY": values.get("GEMINI_API_KEY", ""),
            "GEMINI_MODEL": values.get("GEMINI_MODEL") or "gemini-2.5-flash",
        },
    )
    telegram = complete_group(
        values,
        "Telegram",
        ("TELEGRAM_BOT_TOKEN",),
        {
            "TELEGRAM_ENABLED": "true",
            "TELEGRAM_BOT_TOKEN": values.get("TELEGRAM_BOT_TOKEN", ""),
        },
    )
    if is_real(values.get("WHATSAPP_ACCESS_TOKEN")) or is_real(values.get("WHATSAPP_PHONE_NUMBER_ID")):
        whatsapp = complete_group(
            values,
            "WhatsApp Cloud API",
            ("WHATSAPP_ACCESS_TOKEN", "WHATSAPP_PHONE_NUMBER_ID", "WHATSAPP_TEMPLATE_ALERT_NAME"),
            {
                "WHATSAPP_ENABLED": "true",
                "WHATSAPP_ACCESS_TOKEN": values.get("WHATSAPP_ACCESS_TOKEN", ""),
                "WHATSAPP_PHONE_NUMBER_ID": values.get("WHATSAPP_PHONE_NUMBER_ID", ""),
                "WHATSAPP_TEMPLATE_ALERT_NAME": values.get("WHATSAPP_TEMPLATE_ALERT_NAME", ""),
                "WHATSAPP_TEMPLATE_LANGUAGE": values.get("WHATSAPP_TEMPLATE_LANGUAGE") or "es",
            },
        )
    else:
        whatsapp = ProviderResult("WhatsApp Cloud API", False, {})

    resend_present = is_real(values.get("EMAIL_API_KEY")) or is_real(values.get("EMAIL_FROM"))
    gmail_present = is_real(values.get("SMTP_USERNAME")) or is_real(values.get("SMTP_PASSWORD_APP"))
    if resend_present:
        email = complete_group(
            values,
            "Correo Resend",
            ("EMAIL_API_KEY", "EMAIL_FROM"),
            {
                "EMAIL_ENABLED": "true",
                "EMAIL_PROVIDER": "resend",
                "EMAIL_API_KEY": values.get("EMAIL_API_KEY", ""),
                "EMAIL_FROM": values.get("EMAIL_FROM", ""),
                "EMAIL_REPLY_TO": values.get("EMAIL_REPLY_TO", ""),
            },
        )
    elif gmail_present:
        email = complete_group(
            values,
            "Correo Gmail",
            ("SMTP_USERNAME", "SMTP_PASSWORD_APP"),
            {
                "EMAIL_ENABLED": "true",
                "EMAIL_PROVIDER": "gmail",
                "EMAIL_FROM": values.get("EMAIL_FROM") or values.get("SMTP_USERNAME", ""),
                "EMAIL_REPLY_TO": values.get("EMAIL_REPLY_TO") or values.get("SMTP_USERNAME", ""),
                "SMTP_HOST": "smtp.gmail.com",
                "SMTP_PORT": "587",
                "SMTP_USERNAME": values.get("SMTP_USERNAME", ""),
                "SMTP_PASSWORD": values.get("SMTP_PASSWORD_APP", ""),
                "SMTP_USE_TLS": "true",
            },
        )
    else:
        email = ProviderResult("Correo", False, {})

    storage = complete_group(
        values,
        "Storage S3/R2",
        ("S3_ENDPOINT_URL", "S3_BUCKET", "S3_ACCESS_KEY_ID", "S3_SECRET_ACCESS_KEY"),
        {
            "STORAGE_PROVIDER": "s3",
            "S3_ENDPOINT_URL": values.get("S3_ENDPOINT_URL", ""),
            "S3_BUCKET": values.get("S3_BUCKET", ""),
            "S3_ACCESS_KEY_ID": values.get("S3_ACCESS_KEY_ID", ""),
            "S3_SECRET_ACCESS_KEY": values.get("S3_SECRET_ACCESS_KEY", ""),
            "S3_PUBLIC_BASE_URL": values.get("S3_PUBLIC_BASE_URL", ""),
        },
    )
    sentry = complete_group(
        values,
        "Sentry",
        ("SENTRY_DSN",),
        {
            "SENTRY_ENABLED": "true",
            "SENTRY_DSN": values.get("SENTRY_DSN", ""),
        },
    )
    return [gemini, telegram, whatsapp, email, firebase_provider(values), storage, sentry]


def build_environment(values: dict[str, str], providers: list[ProviderResult]) -> dict[str, str]:
    environment: dict[str, str] = {}
    for provider in providers:
        if provider.configured:
            environment.update(provider.variables)

    notification_names = {"Telegram", "WhatsApp Cloud API", "Firebase FCM"}
    if any(provider.configured and provider.name in notification_names for provider in providers):
        environment["NOTIFICATIONS_DRY_RUN"] = "false"

    public_values = {
        "SUPPORT_EMAIL": values.get("SUPPORT_EMAIL"),
        "SUPPORT_WHATSAPP": values.get("SUPPORT_WHATSAPP"),
        "PUBLIC_WHATSAPP_URL": values.get("PUBLIC_WHATSAPP_URL"),
    }
    for key, value in public_values.items():
        if is_real(value):
            environment[key] = value or ""
    return environment


def api_request(api_key: str, method: str, path: str, payload: dict[str, str] | None = None) -> object:
    body = json.dumps(payload).encode("utf-8") if payload is not None else None
    request = Request(
        f"{RENDER_API_BASE}{path}",
        data=body,
        method=method,
        headers={
            "Accept": "application/json",
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
            "User-Agent": "AgroEscudo-Integration-Configurator/1.0",
        },
    )
    try:
        with urlopen(request, timeout=30) as response:
            raw = response.read()
            return json.loads(raw) if raw else {}
    except HTTPError as exc:
        raise RenderApiError(path, exc.code) from None
    except (URLError, TimeoutError):
        raise RenderApiError(path) from None


def install_google_services(values: dict[str, str]) -> None:
    source_value = values.get("GOOGLE_SERVICES_JSON_PATH")
    if not is_real(source_value):
        return
    source = Path(source_value).expanduser()
    destination = ROOT / "mobile" / "android" / "app" / "google-services.json"
    destination.parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(source, destination)
    print("  [OK] google-services.json instalado en mobile/android/app (ignorado por Git).")


def print_report(providers: list[ProviderResult], environment: dict[str, str]) -> None:
    print("Proveedores detectados:")
    for provider in providers:
        if provider.errors:
            print(f"  [INVALIDO] {provider.name}: {'; '.join(provider.errors)}")
        elif provider.configured:
            print(f"  [LISTO]    {provider.name}")
        else:
            print(f"  [OMITIDO]  {provider.name}")
    print(f"\nVariables preparadas para Render: {len(environment)}")
    for key in sorted(environment):
        print(f"  - {key}: SET")


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Valida y activa integraciones de AgroEscudo en Render sin mostrar secretos."
    )
    parser.add_argument("--credentials", type=Path, default=DEFAULT_CREDENTIALS)
    parser.add_argument("--apply", action="store_true", help="Actualiza Render. Sin esta opcion solo valida.")
    parser.add_argument("--no-deploy", action="store_true", help="Actualiza variables sin disparar deploy.")
    args = parser.parse_args()

    try:
        values = load_credentials(args.credentials.resolve())
    except (FileNotFoundError, OSError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2

    providers = build_provider_results(values)
    environment = build_environment(values, providers)
    print_report(providers, environment)

    errors = [error for provider in providers for error in provider.errors]
    if errors:
        print("\nNo se aplicaron cambios: corrige las configuraciones parciales.", file=sys.stderr)
        return 2
    if not environment:
        print("\nNo hay integraciones completas para aplicar.", file=sys.stderr)
        return 2
    if not args.apply:
        print("\nDRY-RUN correcto. Usa --apply cuando las credenciales sean definitivas.")
        return 0

    api_key = values.get("RENDER_API_KEY")
    service_id = values.get("RENDER_SERVICE_ID")
    if not is_real(api_key) or not is_real(service_id):
        print("ERROR: RENDER_API_KEY y RENDER_SERVICE_ID son obligatorios para --apply.", file=sys.stderr)
        return 2

    print("\nValidando servicio Render...")
    try:
        api_request(api_key or "", "GET", f"/services/{quote(service_id or '', safe='')}")
        print("  [OK] Servicio accesible.")
        for key, value in sorted(environment.items()):
            api_request(
                api_key or "",
                "PUT",
                f"/services/{quote(service_id or '', safe='')}/env-vars/{quote(key, safe='')}",
                {"value": value},
            )
            print(f"  [OK] {key}")
        install_google_services(values)
        if not args.no_deploy:
            result = api_request(
                api_key or "",
                "POST",
                f"/services/{quote(service_id or '', safe='')}/deploys",
                {"clearCache": "do_not_clear"},
            )
            deploy_id = result.get("id") if isinstance(result, dict) else None
            print(f"  [OK] Deploy solicitado{f' ({deploy_id})' if deploy_id else ''}.")
    except RenderApiError as exc:
        print(f"ERROR: {exc} No se mostraron secretos ni cuerpo de respuesta.", file=sys.stderr)
        return 1

    print("\nConfiguracion aplicada. Verifica /health, /api/health/db y el panel de integraciones.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
