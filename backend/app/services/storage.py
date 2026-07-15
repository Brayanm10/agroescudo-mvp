import hashlib
from io import BytesIO
from pathlib import Path
from uuid import uuid4

from fastapi import UploadFile
from sqlalchemy.orm import Session

from app.core.config import settings
from app.models import StoredFile, User


class StorageConfigurationError(RuntimeError):
    pass


async def store_upload(db: Session, *, file: UploadFile, user: User, prefix: str = "service") -> StoredFile:
    content = await file.read()
    checksum = hashlib.sha256(content).hexdigest()
    content_type = file.content_type or "application/octet-stream"
    safe_name = Path(file.filename or "archivo.bin").name
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
        company_id=user.company_id,
        uploaded_by_id=user.id,
        storage_provider=settings.storage_provider.lower(),
        bucket=bucket,
        object_key=object_key,
        original_filename=safe_name,
        content_type=content_type,
        size_bytes=len(content),
        checksum_sha256=checksum,
    )
    db.add(stored)
    db.flush()
    return stored
