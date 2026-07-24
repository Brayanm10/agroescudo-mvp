from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError
from starlette.requests import Request

from app.api.routes import (
    admin,
    agro_assistant,
    ai,
    alerts,
    auth,
    companies,
    control_center,
    demo,
    device_qr,
    devices,
    education,
    evidence,
    exports,
    firmware,
    insights,
    installations,
    iot,
    maintenance,
    notifications,
    operations,
    operational_logs,
    pilots,
    readings,
    reports,
    service_cases,
    sites,
    storage_units,
    users,
)
from app.core.config import settings
from app.db.session import SessionLocal

app = FastAPI(title=settings.app_name)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router, prefix="/api", tags=["auth"])
app.include_router(admin.router, prefix="/api", tags=["admin"])
app.include_router(companies.router, prefix="/api", tags=["companies"])
app.include_router(sites.router, prefix="/api", tags=["sites"])
app.include_router(storage_units.router, prefix="/api", tags=["storage-units"])
app.include_router(device_qr.router, prefix="/api", tags=["device-qr"])
app.include_router(devices.router, prefix="/api", tags=["devices"])
app.include_router(iot.router, prefix="/api", tags=["iot"])
app.include_router(readings.router, prefix="/api", tags=["readings"])
app.include_router(alerts.router, prefix="/api", tags=["alerts"])
app.include_router(operational_logs.router, prefix="/api", tags=["operational-logs"])
app.include_router(reports.router, prefix="/api", tags=["reports"])
app.include_router(pilots.router, prefix="/api", tags=["pilots"])
app.include_router(users.router, prefix="/api", tags=["users"])
app.include_router(demo.router, prefix="/api", tags=["demo"])
app.include_router(notifications.router, prefix="/api", tags=["notifications"])
app.include_router(operations.router, prefix="/api", tags=["operations"])
app.include_router(ai.router, prefix="/api", tags=["ai"])
app.include_router(insights.router, prefix="/api", tags=["insights"])
app.include_router(control_center.router, prefix="/api", tags=["control-center"])
app.include_router(service_cases.router, prefix="/api", tags=["service-cases"])
app.include_router(maintenance.router, prefix="/api", tags=["maintenance"])
app.include_router(installations.router, prefix="/api", tags=["installations"])
app.include_router(evidence.router, prefix="/api", tags=["evidence"])
app.include_router(exports.router, prefix="/api", tags=["exports"])
app.include_router(firmware.router, prefix="/api", tags=["firmware"])
app.include_router(firmware.device_router, prefix="/api", tags=["firmware"])
app.include_router(agro_assistant.router, prefix="/api", tags=["agro-assistant"])
app.include_router(education.router, prefix="/api", tags=["education"])


@app.get("/health")
def health_check() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/api/health/db", response_model=None)
def database_health_check():
    try:
        with SessionLocal() as db:
            db.execute(text("SELECT 1"))
    except SQLAlchemyError as exc:
        return JSONResponse(
            status_code=503,
            content={
                "status": "error",
                "database": settings.database_backend,
                "detail": "Database connection failed. Check DATABASE_URL and run migrations.",
                "error": exc.__class__.__name__,
            },
        )
    return {"status": "ok", "database": settings.database_backend}


@app.exception_handler(SQLAlchemyError)
async def sqlalchemy_exception_handler(_request: Request, exc: SQLAlchemyError) -> JSONResponse:
    return JSONResponse(
        status_code=503,
        content={
            "detail": "Database unavailable. Check DATABASE_URL and run migrations.",
            "database": settings.database_backend,
            "error": exc.__class__.__name__,
        },
    )
