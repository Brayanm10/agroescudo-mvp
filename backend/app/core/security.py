import hashlib
import hmac
from datetime import datetime, timedelta, timezone
from typing import Any

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


def verify_secret(raw_secret: str, hashed_secret: str) -> bool:
    return hmac.compare_digest(hash_secret(raw_secret), hashed_secret)


def hash_password(raw_password: str) -> str:
    return pwd_context.hash(raw_password)


def verify_password(raw_password: str, hashed_password: str) -> bool:
    return pwd_context.verify(raw_password, hashed_password)


def create_access_token(subject: str, expires_delta: timedelta | None = None) -> str:
    expire = datetime.now(timezone.utc) + (
        expires_delta or timedelta(minutes=settings.access_token_expire_minutes)
    )
    payload: dict[str, Any] = {"sub": subject, "exp": expire}
    return jwt.encode(payload, settings.secret_key, algorithm=ALGORITHM)
