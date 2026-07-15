import hashlib
import hmac
import base64
from datetime import datetime, timedelta, timezone
from typing import Any

from cryptography.fernet import Fernet
from jose import jwt
from passlib.context import CryptContext

from app.core.config import settings

ALGORITHM = "HS256"
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def hash_secret(raw_secret: str) -> str:
    return hmac.new(
        settings.secret_key.encode("utf-8"),
        raw_secret.encode("utf-8"),
        hashlib.sha256,
    ).hexdigest()


def _fernet() -> Fernet:
    key = base64.urlsafe_b64encode(hashlib.sha256(settings.secret_key.encode("utf-8")).digest())
    return Fernet(key)


def encrypt_secret(raw_secret: str) -> str:
    return _fernet().encrypt(raw_secret.encode("utf-8")).decode("utf-8")


def decrypt_secret(encrypted_secret: str) -> str:
    return _fernet().decrypt(encrypted_secret.encode("utf-8")).decode("utf-8")


def verify_secret(raw_secret: str, hashed_secret: str) -> bool:
    return hmac.compare_digest(hash_secret(raw_secret), hashed_secret)


def hash_password(raw_password: str) -> str:
    return pwd_context.hash(raw_password)


def verify_password(raw_password: str, hashed_password: str) -> bool:
    return pwd_context.verify(raw_password, hashed_password)


def validate_password_strength(raw_password: str) -> None:
    if len(raw_password) < 8:
        raise ValueError("La contraseña debe tener al menos 8 caracteres.")
    if not any(char.isalpha() for char in raw_password):
        raise ValueError("La contraseña debe incluir al menos una letra.")
    if not any(char.isdigit() for char in raw_password):
        raise ValueError("La contraseña debe incluir al menos un numero.")


def create_access_token(subject: str, expires_delta: timedelta | None = None, jti: str | None = None) -> str:
    expire = datetime.now(timezone.utc) + (
        expires_delta or timedelta(minutes=settings.access_token_expire_minutes)
    )
    payload: dict[str, Any] = {"sub": subject, "exp": expire}
    if jti:
        payload["jti"] = jti
    return jwt.encode(payload, settings.secret_key, algorithm=ALGORITHM)
