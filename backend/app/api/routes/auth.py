import json
import secrets
from datetime import timedelta

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.core.config import settings
from app.core.security import create_access_token, hash_password, hash_secret, verify_password, verify_secret
from app.db.session import get_db
from app.models import (
    Company,
    EmailVerificationToken,
    Lead,
    OrganizationRequest,
    PasswordResetToken,
    StorageUnit,
    User,
    UserInvite,
    UserSession,
    utc_now,
)
from app.schemas import (
    ChangePasswordIn,
    DemoRequestIn,
    EmailVerifyIn,
    GenericMessageOut,
    InviteAcceptIn,
    InvitePreviewIn,
    InvitePreviewOut,
    LoginRequest,
    PasswordForgotIn,
    PasswordForgotOut,
    PasswordResetPublicIn,
    SignupCompanyIn,
    SignupCompanyOut,
    TokenOut,
    UserOut,
    UserProfileUpdate,
)
from app.services.audit import record_audit_event
from app.services.email import EmailConfigurationError, send_transactional_email

router = APIRouter()


def _make_raw_token() -> str:
    return secrets.token_urlsafe(32)


def _create_user_session(db: Session, user: User) -> str:
    jti = secrets.token_urlsafe(24)
    expires_at = utc_now() + timedelta(minutes=settings.access_token_expire_minutes)
    db.add(UserSession(user_id=user.id, jti=jti, expires_at=expires_at))
    return jti


def _issue_token(db: Session, user: User) -> TokenOut:
    jti = _create_user_session(db, user)
    return TokenOut(access_token=create_access_token(str(user.id), jti=jti))


def _is_user_allowed_to_login(user: User) -> bool:
    return user.is_active and getattr(user, "status", "ACTIVE") == "ACTIVE"


def _as_utc_aware(value):
    if value is None or value.tzinfo is not None:
        return value
    return value.replace(tzinfo=utc_now().tzinfo)


@router.post("/auth/login", response_model=TokenOut)
def login(payload: LoginRequest, db: Session = Depends(get_db)) -> TokenOut:
    user = db.scalar(select(User).where(User.email == payload.email))
    if user is None or not verify_password(payload.password, user.hashed_password):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid email or password")
    if not _is_user_allowed_to_login(user):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Usuario desactivado. Contacta al administrador.")

    user.last_login_at = utc_now()
    user.last_seen_at = utc_now()
    token = _issue_token(db, user)
    record_audit_event(db, action="auth.login", summary="Inicio de sesion exitoso", user=user)
    db.commit()
    return token


@router.post("/auth/logout", response_model=GenericMessageOut)
def logout(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)) -> GenericMessageOut:
    sessions = list(db.scalars(select(UserSession).where(UserSession.user_id == current_user.id, UserSession.revoked_at.is_(None))).all())
    if sessions:
        sessions[-1].revoked_at = utc_now()
    record_audit_event(db, action="auth.logout", summary="Cierre de sesion", user=current_user)
    db.commit()
    return GenericMessageOut(message="Sesion cerrada.")


@router.post("/auth/logout-all", response_model=GenericMessageOut)
def logout_all(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)) -> GenericMessageOut:
    for session in db.scalars(select(UserSession).where(UserSession.user_id == current_user.id, UserSession.revoked_at.is_(None))).all():
        session.revoked_at = utc_now()
    record_audit_event(db, action="auth.logout_all", summary="Cierre de todas las sesiones", user=current_user)
    db.commit()
    return GenericMessageOut(message="Todas las sesiones fueron cerradas.")


@router.post("/auth/signup/company", response_model=SignupCompanyOut, status_code=status.HTTP_201_CREATED)
def signup_company(payload: SignupCompanyIn, db: Session = Depends(get_db)) -> SignupCompanyOut:
    if not payload.consent_terms or not payload.consent_privacy:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Debes aceptar terminos y privacidad.")
    if db.scalar(select(User.id).where(User.email == payload.work_email)):
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Ya existe un usuario con ese correo.")

    company = Company(
        name=payload.commercial_name,
        tax_id=payload.tax_id,
        type=payload.sector or "agroindustria",
        city=payload.city,
        contact_name=payload.responsible_name,
        contact_email=payload.work_email,
        contact_phone=payload.phone,
        is_active=False,
        approval_status="PENDING_REVIEW",
    )
    db.add(company)
    db.flush()
    user = User(
        company_id=company.id,
        email=payload.work_email,
        full_name=payload.responsible_name,
        hashed_password=hash_password(payload.password),
        role="client",
        is_active=True,
        status="EMAIL_PENDING",
        language=payload.language,
        locale=payload.language,
        phone_whatsapp=payload.phone,
    )
    db.add(user)
    db.flush()
    request = OrganizationRequest(
        company_id=company.id,
        requester_user_id=user.id,
        responsible_name=payload.responsible_name,
        work_email=payload.work_email,
        phone=payload.phone,
        commercial_name=payload.commercial_name,
        legal_name=payload.legal_name,
        tax_id=payload.tax_id,
        sector=payload.sector,
        city=payload.city,
        department=payload.department,
        estimated_sites=payload.estimated_sites,
        estimated_storage_units=payload.estimated_storage_units,
        use_case=payload.use_case,
        language=payload.language,
        consent_terms=payload.consent_terms,
        consent_privacy=payload.consent_privacy,
        consent_marketing=payload.consent_marketing,
    )
    db.add(request)
    raw_token = _make_raw_token()
    db.add(EmailVerificationToken(user_id=user.id, token_hash=hash_secret(raw_token), expires_at=utc_now() + timedelta(hours=24)))

    try:
        email_result = send_transactional_email(
            to_email=user.email,
            subject="Verifica tu cuenta AgroEscudo",
            body=f"Verifica tu cuenta: {settings.public_app_url}/verify-email?token={raw_token}",
            preview_token=raw_token,
        )
    except EmailConfigurationError as exc:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=str(exc)) from exc

    record_audit_event(db, action="auth.signup_company", summary="Solicitud de organizacion creada", user=user, company_id=company.id, resource_type="organization_request", resource_id=request.id)
    db.commit()
    return SignupCompanyOut(
        request_id=request.id,
        company_id=company.id,
        user_id=user.id,
        status=request.status,
        email_required=True,
        verification_preview_token=email_result.preview_token,
        message="Solicitud recibida. Verifica tu correo para continuar.",
    )


@router.post("/auth/demo-request", response_model=GenericMessageOut, status_code=status.HTTP_201_CREATED)
def demo_request(payload: DemoRequestIn, db: Session = Depends(get_db)) -> GenericMessageOut:
    if not payload.consent:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Debes autorizar el contacto comercial.")
    db.add(
        Lead(
            name=payload.name,
            company_name=payload.company_name,
            position=payload.position,
            email=payload.email,
            phone=payload.phone,
            city=payload.city,
            interest=payload.interest,
            source="demo_request",
            consent=payload.consent,
        )
    )
    record_audit_event(db, action="auth.demo_request", summary="Solicitud de demostracion registrada", metadata={"email": payload.email, "company_name": payload.company_name})
    db.commit()
    return GenericMessageOut(message="Solicitud recibida. El equipo AgroEscudo te contactara.")


@router.post("/auth/invites/preview", response_model=InvitePreviewOut)
def invite_preview(payload: InvitePreviewIn, db: Session = Depends(get_db)) -> InvitePreviewOut:
    token_hash = hash_secret(payload.token)
    invite = db.scalar(select(UserInvite).where(UserInvite.token_hash == token_hash))
    if invite is None or invite.accepted_at is not None or _as_utc_aware(invite.expires_at) < utc_now():
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Invitacion no valida o expirada.")
    company = db.get(Company, invite.company_id)
    return InvitePreviewOut(
        email=invite.email,
        role=invite.role,
        company_name=company.name if company else "AgroEscudo",
        expires_at=invite.expires_at,
        status=invite.status,
    )


@router.post("/auth/invites/accept", response_model=TokenOut)
def invite_accept(payload: InviteAcceptIn, db: Session = Depends(get_db)) -> TokenOut:
    invite = db.scalar(select(UserInvite).where(UserInvite.token_hash == hash_secret(payload.token)))
    if invite is None or invite.accepted_at is not None or _as_utc_aware(invite.expires_at) < utc_now():
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Invitacion no valida o expirada.")
    user = db.scalar(select(User).where(User.email == invite.email))
    if user is None:
        user = User(
            company_id=invite.company_id,
            email=invite.email,
            full_name=payload.full_name,
            hashed_password=hash_password(payload.password),
            role=invite.role,
            is_active=True,
            status="ACTIVE",
            email_verified_at=utc_now(),
        )
        db.add(user)
        db.flush()
    else:
        user.company_id = invite.company_id
        user.full_name = payload.full_name
        user.hashed_password = hash_password(payload.password)
        user.role = invite.role
        user.is_active = True
        user.status = "ACTIVE"
        user.email_verified_at = utc_now()

    if invite.storage_unit_ids:
        storage_unit_ids = json.loads(invite.storage_unit_ids)
        for storage_unit in db.scalars(select(StorageUnit).where(StorageUnit.id.in_(storage_unit_ids))).all():
            if user.role == "technician":
                storage_unit.assigned_technician_id = user.id
            elif user.role == "client":
                storage_unit.assigned_client_id = user.id

    invite.accepted_at = utc_now()
    invite.status = "accepted"
    token = _issue_token(db, user)
    record_audit_event(db, action="auth.invite_accept", summary="Invitacion aceptada", user=user, resource_type="user_invite", resource_id=invite.id)
    db.commit()
    return token


@router.post("/auth/email/verify", response_model=GenericMessageOut)
def verify_email(payload: EmailVerifyIn, db: Session = Depends(get_db)) -> GenericMessageOut:
    token = db.scalar(select(EmailVerificationToken).where(EmailVerificationToken.token_hash == hash_secret(payload.token)))
    if token is None or token.used_at is not None or _as_utc_aware(token.expires_at) < utc_now():
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Token de verificacion no valido o expirado.")
    user = db.get(User, token.user_id)
    if user is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Usuario no encontrado.")
    user.email_verified_at = utc_now()
    if user.status == "EMAIL_PENDING":
        user.status = "PENDING_APPROVAL"
    token.used_at = utc_now()
    record_audit_event(db, action="auth.email_verify", summary="Correo verificado", user=user)
    db.commit()
    return GenericMessageOut(message="Correo verificado. Tu organizacion queda pendiente de aprobacion.")


@router.post("/auth/password/forgot", response_model=PasswordForgotOut)
def forgot_password(payload: PasswordForgotIn, db: Session = Depends(get_db)) -> PasswordForgotOut:
    user = db.scalar(select(User).where(User.email == payload.email))
    preview_token = None
    if user is not None and user.is_active:
        raw_token = _make_raw_token()
        db.add(PasswordResetToken(user_id=user.id, token_hash=hash_secret(raw_token), expires_at=utc_now() + timedelta(hours=2)))
        try:
            result = send_transactional_email(
                to_email=user.email,
                subject="Recupera tu acceso AgroEscudo",
                body=f"Restablece tu password: {settings.public_app_url}/reset-password?token={raw_token}",
                preview_token=raw_token,
            )
            preview_token = result.preview_token
        except EmailConfigurationError as exc:
            raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=str(exc)) from exc
        record_audit_event(db, action="auth.password_forgot", summary="Solicitud de recuperacion de password", user=user)
    db.commit()
    return PasswordForgotOut(message="Si el correo existe, enviaremos instrucciones para recuperar el acceso.", reset_preview_token=preview_token)


@router.post("/auth/password/reset", response_model=GenericMessageOut)
def reset_password(payload: PasswordResetPublicIn, db: Session = Depends(get_db)) -> GenericMessageOut:
    token = db.scalar(select(PasswordResetToken).where(PasswordResetToken.token_hash == hash_secret(payload.token)))
    if token is None or token.used_at is not None or _as_utc_aware(token.expires_at) < utc_now():
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Token de recuperacion no valido o expirado.")
    user = db.get(User, token.user_id)
    if user is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Usuario no encontrado.")
    user.hashed_password = hash_password(payload.password)
    user.password_changed_at = utc_now()
    token.used_at = utc_now()
    for session in db.scalars(select(UserSession).where(UserSession.user_id == user.id, UserSession.revoked_at.is_(None))).all():
        session.revoked_at = utc_now()
    record_audit_event(db, action="auth.password_reset", summary="Password restablecido", user=user)
    db.commit()
    return GenericMessageOut(message="Password actualizado. Inicia sesion nuevamente.")


@router.get("/me", response_model=UserOut)
def me(current_user: User = Depends(get_current_user)) -> User:
    return current_user


@router.patch("/me", response_model=UserOut)
def update_me(
    payload: UserProfileUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> User:
    values = payload.model_dump(exclude_unset=True)
    for field, value in values.items():
        setattr(current_user, field, value)
        if field == "language":
            current_user.locale = value
    record_audit_event(db, action="profile.update", summary="Perfil actualizado", user=current_user)
    db.commit()
    db.refresh(current_user)
    return current_user


@router.post("/auth/change-password", response_model=UserOut)
def change_password(
    payload: ChangePasswordIn,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> User:
    if payload.new_password != payload.confirm_password:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="La confirmacion de contrasena no coincide.")
    if not verify_password(payload.current_password, current_user.hashed_password):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="La contrasena actual es incorrecta.")
    if verify_password(payload.new_password, current_user.hashed_password):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="La nueva contrasena debe ser distinta a la actual.")

    current_user.hashed_password = hash_password(payload.new_password)
    current_user.password_changed_at = utc_now()
    for session in db.scalars(select(UserSession).where(UserSession.user_id == current_user.id, UserSession.revoked_at.is_(None))).all():
        session.revoked_at = utc_now()
    record_audit_event(db, action="auth.change_password", summary="Password cambiado", user=current_user)
    db.commit()
    db.refresh(current_user)
    return current_user
