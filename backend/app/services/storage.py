import hashlib
from io import BytesIO
from pathlib import Path
import re
from uuid import uuid4

from fastapi import UploadFile
from sqlalchemy.orm import Session

from app.core.config import settings
from app.models import StoredFile, User


class StorageConfigurationError(RuntimeError):
    pass


class InvalidUploadError(ValueError):
    pass


async def store_upload(
    db: Session,
    *,
    file: UploadFile,
    user: User,
    prefix: str = "service",
    company_id: int | None = None,
    storage_unit_id: int | None = None,
    entity_type: str | None = None,
    entity_id: int | None = None,
    file_type: str = "OTHER",
    description: str | None = None,
    captured_at=None,
    is_sensitive: bool = False,
) -> StoredFile:
    content = await file.read()
    if not content:
        raise InvalidUploadError("El archivo esta vacio.")
    if len(content) > settings.max_upload_bytes:
        raise InvalidUploadError(
            f"El archivo supera el limite de {settings.max_upload_bytes // (1024 * 1024)} MB."
        )
    checksum = hashlib.sha256(content).hexdigest()
    content_type = _detect_content_type(content)
    declared_type = (file.content_type or "").lower().split(";", 1)[0].strip()
    if declared_type and declared_type != "application/octet-stream" and declared_type != content_type:
        raise InvalidUploadError("El contenido real no coincide con el tipo MIME declarado.")
    safe_name = _safe_filename(file.filename or _default_filename(content_type))
    object_key = f"{prefix}/{uuid4().hex}-{safe_name}"

    if settings.storage_provider.lower() == "local":
        base_dir = Path("var/uploads")
        base_dir.mkdir(parents=True, exist_ok=True)
        (base_dir / object_key).parent.mkdir(parents=True, exist_ok=True)
        (base_dir / object_key).write_bytes(content)
        bucket = None
    elif settings.storage_provider.lower() == "s3":
        missing = [
            name
            for name, value in {
                "S3_ENDPOINT_URL": settings.s3_endpoint_url,
                "S3_BUCKET": settings.s3_bucket,
                "S3_ACCESS_KEY_ID": settings.s3_access_key_id,
                "S3_SECRET_ACCESS_KEY": settings.s3_secret_access_key,
            }.items()
            if not value
        ]
        if missing:
            raise StorageConfigurationError(f"REQUIERE CREDENCIAL: configura {', '.join(missing)}.")
        try:
            import boto3

            client = boto3.client(
                "s3",
                endpoint_url=settings.s3_endpoint_url,
                aws_access_key_id=settings.s3_access_key_id,
                aws_secret_access_key=settings.s3_secret_access_key,
            )
            client.upload_fileobj(
                BytesIO(content),
                settings.s3_bucket,
                object_key,
                ExtraArgs={"ContentType": content_type},
            )
            bucket = settings.s3_bucket
        except Exception as exc:  # pragma: no cover - provider errors depend on deployment
            raise StorageConfigurationError(f"No se pudo guardar el archivo en S3: {exc.__class__.__name__}.") from exc
    else:
        raise StorageConfigurationError("STORAGE_PROVIDER no soportado. Usa local o s3.")

    stored = StoredFile(
        company_id=company_id if company_id is not None else user.company_id,
        storage_unit_id=storage_unit_id,
        uploaded_by_id=user.id,
        entity_type=entity_type,
        entity_id=entity_id,
        file_type=file_type,
        storage_provider=settings.storage_provider.lower(),
        bucket=bucket,
        object_key=object_key,
        original_filename=safe_name,
        content_type=content_type,
        size_bytes=len(content),
        checksum_sha256=checksum,
        captured_at=captured_at,
        description=description,
        is_sensitive=is_sensitive,
    )
    db.add(stored)
    db.flush()
    return stored


def local_file_path(stored: StoredFile) -> Path:
    base_dir = Path("var/uploads").resolve()
    candidate = (base_dir / stored.object_key).resolve()
    if base_dir not in candidate.parents:
        raise StorageConfigurationError("Ruta de evidencia invalida.")
    return candidate


def create_download_url(stored: StoredFile) -> str | None:
    if stored.storage_provider != "s3":
        return None
    if not settings.s3_bucket:
        raise StorageConfigurationError("REQUIERE CREDENCIAL: configura S3_BUCKET.")
    try:
        import boto3

        client = boto3.client(
            "s3",
            endpoint_url=settings.s3_endpoint_url,
            aws_access_key_id=settings.s3_access_key_id,
            aws_secret_access_key=settings.s3_secret_access_key,
        )
        return client.generate_presigned_url(
            "get_object",
            Params={"Bucket": stored.bucket or settings.s3_bucket, "Key": stored.object_key},
            ExpiresIn=300,
        )
    except Exception as exc:  # pragma: no cover - depends on external provider
        raise StorageConfigurationError(
            f"No se pudo crear URL firmada: {exc.__class__.__name__}."
        ) from exc


def _detect_content_type(content: bytes) -> str:
    if content.startswith(b"\x89PNG\r\n\x1a\n"):
        return "image/png"
    if content.startswith(b"\xff\xd8\xff"):
        return "image/jpeg"
    if content.startswith(b"%PDF-"):
        return "application/pdf"
    if len(content) >= 12 and content[:4] == b"RIFF" and content[8:12] == b"WEBP":
        return "image/webp"
    if b"\x00" not in content[:4096]:
        try:
            content[:4096].decode("utf-8")
            return "text/plain"
        except UnicodeDecodeError:
            pass
    raise InvalidUploadError("Tipo de archivo no permitido. Usa PNG, JPEG, WEBP, PDF o texto.")


def _safe_filename(value: str) -> str:
    basename = Path(value).name
    stem = re.sub(r"[^A-Za-z0-9._-]+", "-", basename).strip(".-_")
    return (stem or "evidencia.bin")[:120]


def _default_filename(content_type: str) -> str:
    return {
        "image/png": "evidencia.png",
        "image/jpeg": "evidencia.jpg",
        "image/webp": "evidencia.webp",
        "application/pdf": "evidencia.pdf",
        "text/plain": "evidencia.txt",
    }.get(content_type, "evidencia.bin")
