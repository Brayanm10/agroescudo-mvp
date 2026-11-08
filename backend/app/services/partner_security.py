"""Small confidential-client service, shared SQL quotas and encrypted cursors."""
import base64
import hashlib
import hmac
import json
import math
import secrets
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone

from cryptography.fernet import Fernet, InvalidToken
from fastapi import Depends, Request, Security
from fastapi.security import OAuth2
from fastapi.openapi.models import OAuthFlows as OAuthFlowsModel
from sqlalchemy import select, update
from sqlalchemy.orm import Session

from app.core.config import settings
from app.db.session import get_db
from app.partner_models import PartnerBucket, PartnerClient, PartnerCredential, PartnerToken

SCOPES = {'storage_units:read', 'readings:read', 'alerts:read'}
oauth = OAuth2(flows=OAuthFlowsModel(clientCredentials={
    'tokenUrl': '/api/v1/partner/oauth/token',
    'scopes': {s: s for s in sorted(SCOPES)},
}), auto_error=False, scheme_name='PartnerClientCredentials')


def now():
    return datetime.now(timezone.utc)


def aware(value):
    return value.replace(tzinfo=timezone.utc) if value.tzinfo is None else value.astimezone(timezone.utc)


class PartnerError(Exception):
    def __init__(self, status, code, message='Solicitud no disponible.', headers=None):
        self.status, self.code, self.message, self.headers = status, code, message, headers or {}


def db_dependency(request: Request, db: Session = Depends(get_db)):
    existing = getattr(request.state, 'partner_db', None)
    request.state.partner_db = existing if existing is not None else db
    return request.state.partner_db


def digest(value):
    return hashlib.sha256(value.encode()).hexdigest()


def secret_hash(value):
    salt = secrets.token_bytes(16)
    hashed = hashlib.scrypt(value.encode(), salt=salt, n=16384, r=8, p=1)
    return 'scrypt$'+salt.hex()+'$'+hashed.hex()


def verify_secret(value, stored):
    try:
        _, salt, expected = stored.split('$')
        actual = hashlib.scrypt(value.encode(), salt=bytes.fromhex(salt), n=16384, r=8, p=1)
        return hmac.compare_digest(actual.hex(), expected)
    except (ValueError, TypeError):
        return False


def key():
    return (settings.partner_signing_key or settings.secret_key).encode()


def public_id(kind, internal_id):
    return kind+'_'+hmac.new(key(), f'partner-id:{kind}:{internal_id}'.encode(), hashlib.sha256).hexdigest()[:32]


def quota(db, bucket_key, per_minute, burst):
    """Atomic compare-and-swap token bucket stored in the shared database.

    PostgreSQL writers serialize on the row; version predicate also protects
    SQLite and independent worker sessions. No process-local permission cache.
    """
    dialect = db.get_bind().dialect.name
    if dialect == 'postgresql':
        from sqlalchemy.dialects.postgresql import insert
    elif dialect == 'sqlite':
        from sqlalchemy.dialects.sqlite import insert
    else:
        raise PartnerError(503, 'SERVICE_UNAVAILABLE')
    timestamp = now()
    db.execute(insert(PartnerBucket).values(key=bucket_key, balance=float(burst), updated_at=timestamp, version=0).on_conflict_do_nothing(index_elements=['key']))
    for _ in range(8):
        row = db.execute(select(PartnerBucket.balance, PartnerBucket.updated_at, PartnerBucket.version).where(PartnerBucket.key == bucket_key).with_for_update()).one()
        # Capture time after waiting for the lock; concurrent requests must not
        # move a shared bucket's clock backwards and mint additional credits.
        timestamp = max(now(), aware(row.updated_at))
        balance = min(float(burst), row.balance + max(0, (timestamp-aware(row.updated_at)).total_seconds())*per_minute/60)
        allowed = balance >= 1
        changed = db.execute(update(PartnerBucket).where(PartnerBucket.key == bucket_key, PartnerBucket.version == row.version).values(balance=balance-1 if allowed else balance, updated_at=timestamp, version=row.version+1))
        if changed.rowcount:
            db.commit()
            if not allowed:
                raise PartnerError(429, 'RATE_LIMITED', headers={'Retry-After': str(max(1, math.ceil((1-balance)*60/per_minute)))})
            return
        db.rollback()
    raise PartnerError(503, 'SERVICE_UNAVAILABLE')


def valid_until(value, timestamp):
    return value is None or aware(value) > timestamp


def authenticate_client(request, db, authorization):
    # Untrusted X-Forwarded-For is deliberately ignored. Uvicorn proxy trust is
    # an explicit deployment responsibility; peer limiter always applies.
    try:
        scheme, encoded = (authorization or '').split(' ', 1)
        if scheme.lower() != 'basic' or len(encoded) > 1024:
            raise ValueError()
        raw = base64.b64decode(encoded, validate=True).decode('utf-8')
        client_id, secret = raw.split(':', 1)
        # RFC 6749 §2.3.1: form-url-encoded components before Basic encoding.
        from urllib.parse import unquote_plus
        client_id, secret = unquote_plus(client_id), unquote_plus(secret)
        if not client_id or not secret or len(secret) > 256:
            raise ValueError()
    except (ValueError, UnicodeError):
        raise PartnerError(401, 'invalid_client', 'Credenciales de servicio inválidas.', {'WWW-Authenticate': 'Basic'})
    quota(db, 'auth-id:'+digest(client_id), settings.partner_auth_per_minute, settings.partner_auth_burst)
    client = db.scalar(select(PartnerClient).where(PartnerClient.client_id == client_id))
    timestamp = now()
    credentials = list(db.scalars(select(PartnerCredential).where(PartnerCredential.client_id == client.id, PartnerCredential.revoked_at.is_(None))).all()) if client else []
    # Bounded credential count is enforced by administrative provisioning.
    matched = next((c for c in credentials if valid_until(c.expires_at, timestamp) and verify_secret(secret, c.secret_hash)), None)
    if client is None or matched is None or not client.is_active or client.revoked_at or (client.is_demo and not settings.partner_sandbox):
        raise PartnerError(401, 'invalid_client', 'Credenciales de servicio inválidas.', {'WWW-Authenticate': 'Basic'})
    request.state.partner_client = client.client_id
    return client, matched


def issue_token(db, client, credential, scope):
    requested = set(scope.split()) if scope is not None else set(client.scopes.split())
    if not requested or not requested <= set(client.scopes.split()) or not requested <= SCOPES:
        raise PartnerError(400, 'invalid_scope', 'Scopes no autorizados.')
    raw = secrets.token_urlsafe(48)
    scope_text = ' '.join(sorted(requested))
    db.add(PartnerToken(client_id=client.id, credential_id=credential.id, token_hash=digest(raw), scopes=scope_text, expires_at=now()+timedelta(seconds=600)))
    db.commit()
    return {'access_token': raw, 'token_type': 'Bearer', 'expires_in': 600, 'scope': scope_text}


@dataclass
class Principal:
    client: PartnerClient
    token: PartnerToken


def principal(request: Request, db: Session = Depends(db_dependency), authorization: str | None = Security(oauth)):
    value = request.headers.get('authorization', '')
    parts = value.split(' ')
    if len(parts) != 2 or parts[0].lower() != 'bearer' or not (20 <= len(parts[1]) <= 256):
        raise PartnerError(401, 'UNAUTHORIZED', headers={'WWW-Authenticate': 'Bearer'})
    token = db.scalar(select(PartnerToken).where(PartnerToken.token_hash == digest(parts[1])))
    timestamp = now()
    client = db.get(PartnerClient, token.client_id) if token else None
    cred = db.get(PartnerCredential, token.credential_id) if token else None
    if not token or token.revoked_at or aware(token.expires_at) <= timestamp or not client or not client.is_active or client.revoked_at or not cred or cred.revoked_at or not valid_until(cred.expires_at, timestamp) or (client.is_demo and not settings.partner_sandbox):
        raise PartnerError(401, 'UNAUTHORIZED', headers={'WWW-Authenticate': 'Bearer'})
    request.state.partner_client = client.client_id
    quota(db, 'data:'+digest(client.client_id), settings.partner_requests_per_minute, settings.partner_burst)
    return Principal(client, token)


def require_scope(actor, scope):
    if scope not in actor.token.scopes.split() or scope not in actor.client.scopes.split():
        raise PartnerError(403, 'FORBIDDEN')


def cursor_encode(binding, position, snapshot):
    value = {'v': 1, 'binding': binding, 'position': position, 'snapshot': snapshot, 'expires': (now()+timedelta(minutes=15)).timestamp()}
    return Fernet(base64.urlsafe_b64encode(hashlib.sha256(key()+b'partner-cursor-v1').digest())).encrypt(json.dumps(value, separators=(',', ':')).encode()).decode()


def cursor_decode(cursor, binding):
    try:
        decoded = base64.b64decode(cursor.encode(), altchars=b'-_', validate=True)
        if base64.urlsafe_b64encode(decoded).decode() != cursor:
            raise ValueError()
        raw = Fernet(base64.urlsafe_b64encode(hashlib.sha256(key()+b'partner-cursor-v1').digest())).decrypt(cursor.encode(), ttl=900)
        data = json.loads(raw)
        if data['v'] != 1 or data['binding'] != binding or data['expires'] <= now().timestamp():
            raise ValueError()
        return data
    except (InvalidToken, ValueError, KeyError, TypeError, UnicodeError):
        raise PartnerError(400, 'INVALID_CURSOR')
