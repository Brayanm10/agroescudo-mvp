from __future__ import annotations

from datetime import datetime
from pathlib import Path

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_LEFT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import cm
from reportlab.platypus import (
    Image,
    KeepTogether,
    PageBreak,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)


ROOT = Path(__file__).resolve().parents[1]
OUT_DIR = ROOT / "output" / "pdf"
OUT_DIR.mkdir(parents=True, exist_ok=True)
PDF_PATH = OUT_DIR / "AgroEscudo_Auditoria_Final_Control_Center_V1.pdf"
LOGO = ROOT / "frontend" / "public" / "brand" / "logo-horizontal-transparent.png"
SHIELD = ROOT / "frontend" / "public" / "brand" / "shield-transparent.png"

GREEN_DARK = colors.HexColor("#064B35")
GREEN = colors.HexColor("#047857")
AMBER = colors.HexColor("#C89116")
TEXT = colors.HexColor("#24342F")
MUTED = colors.HexColor("#60746C")
LINE = colors.HexColor("#DDE7E2")
SOFT = colors.HexColor("#F8FAF9")
RED = colors.HexColor("#B42318")


def p(text: str, style: ParagraphStyle) -> Paragraph:
    return Paragraph(text, style)


styles = getSampleStyleSheet()
styles.add(
    ParagraphStyle(
        name="CoverTitle",
        parent=styles["Title"],
        fontName="Helvetica-Bold",
        fontSize=28,
        leading=32,
        textColor=GREEN_DARK,
        alignment=TA_CENTER,
        spaceAfter=10,
    )
)
styles.add(
    ParagraphStyle(
        name="CoverSub",
        parent=styles["Normal"],
        fontName="Helvetica",
        fontSize=12,
        leading=18,
        textColor=MUTED,
        alignment=TA_CENTER,
    )
)
styles.add(
    ParagraphStyle(
        name="H1",
        parent=styles["Heading1"],
        fontName="Helvetica-Bold",
        fontSize=18,
        leading=23,
        textColor=GREEN_DARK,
        spaceBefore=10,
        spaceAfter=8,
    )
)
styles.add(
    ParagraphStyle(
        name="H2",
        parent=styles["Heading2"],
        fontName="Helvetica-Bold",
        fontSize=12,
        leading=16,
        textColor=GREEN_DARK,
        spaceBefore=8,
        spaceAfter=6,
    )
)
styles.add(
    ParagraphStyle(
        name="Body",
        parent=styles["BodyText"],
        fontName="Helvetica",
        fontSize=9.2,
        leading=14,
        textColor=TEXT,
        spaceAfter=6,
    )
)
styles.add(
    ParagraphStyle(
        name="Small",
        parent=styles["BodyText"],
        fontName="Helvetica",
        fontSize=7.8,
        leading=10,
        textColor=MUTED,
    )
)
styles.add(
    ParagraphStyle(
        name="Kicker",
        parent=styles["BodyText"],
        fontName="Helvetica-Bold",
        fontSize=7.5,
        leading=9,
        textColor=AMBER,
        uppercase=True,
        spaceAfter=3,
    )
)
styles.add(
    ParagraphStyle(
        name="TableCell",
        parent=styles["BodyText"],
        fontName="Helvetica",
        fontSize=7.7,
        leading=10,
        textColor=TEXT,
    )
)
styles.add(
    ParagraphStyle(
        name="TableHead",
        parent=styles["BodyText"],
        fontName="Helvetica-Bold",
        fontSize=7.4,
        leading=9,
        textColor=colors.white,
    )
)


def make_table(rows: list[list[str]], widths: list[float], header: bool = True) -> Table:
    converted = []
    for row_index, row in enumerate(rows):
        style = styles["TableHead"] if header and row_index == 0 else styles["TableCell"]
        converted.append([p(str(cell), style) for cell in row])
    table = Table(converted, colWidths=widths, hAlign="LEFT", repeatRows=1 if header else 0)
    table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), GREEN_DARK if header else colors.white),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.white if header else TEXT),
                ("GRID", (0, 0), (-1, -1), 0.4, LINE),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("LEFTPADDING", (0, 0), (-1, -1), 6),
                ("RIGHTPADDING", (0, 0), (-1, -1), 6),
                ("TOPPADDING", (0, 0), (-1, -1), 6),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
                ("BACKGROUND", (0, 1), (-1, -1), colors.white),
                ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, SOFT]),
            ]
        )
    )
    return table


def status_card(title: str, value: str, note: str, color=GREEN) -> Table:
    data = [
        [p(title.upper(), styles["Kicker"])],
        [p(f"<font color='{color.hexval()}'><b>{value}</b></font>", ParagraphStyle("Value", parent=styles["Body"], fontSize=18, leading=21))],
        [p(note, styles["Small"])],
    ]
    t = Table(data, colWidths=[5.1 * cm])
    t.setStyle(
        TableStyle(
            [
                ("BOX", (0, 0), (-1, -1), 0.6, LINE),
                ("BACKGROUND", (0, 0), (-1, -1), colors.white),
                ("LEFTPADDING", (0, 0), (-1, -1), 10),
                ("RIGHTPADDING", (0, 0), (-1, -1), 10),
                ("TOPPADDING", (0, 0), (-1, -1), 7),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 7),
            ]
        )
    )
    return t


def header_footer(canvas, doc):
    canvas.saveState()
    width, height = A4
    canvas.setStrokeColor(LINE)
    canvas.setLineWidth(0.6)
    canvas.line(1.5 * cm, height - 1.35 * cm, width - 1.5 * cm, height - 1.35 * cm)
    canvas.line(1.5 * cm, 1.25 * cm, width - 1.5 * cm, 1.25 * cm)
    canvas.setFont("Helvetica-Bold", 8)
    canvas.setFillColor(GREEN_DARK)
    canvas.drawString(1.5 * cm, height - 1.05 * cm, "AgroEscudo - Auditoria final Control Center V1.0")
    canvas.setFont("Helvetica", 7)
    canvas.setFillColor(MUTED)
    canvas.drawRightString(width - 1.5 * cm, height - 1.05 * cm, "Documento tecnico para cierre de piloto comercial")
    canvas.drawString(1.5 * cm, 0.85 * cm, "Confidencial - Uso interno y presentacion de piloto")
    canvas.drawRightString(width - 1.5 * cm, 0.85 * cm, f"Pagina {doc.page}")
    canvas.restoreState()


def build_story() -> list:
    story = []
    if LOGO.exists():
        img = Image(str(LOGO), width=9.5 * cm, height=2.1 * cm)
        img.hAlign = "CENTER"
        story.append(Spacer(1, 1.4 * cm))
        story.append(img)
    elif SHIELD.exists():
        img = Image(str(SHIELD), width=3 * cm, height=3 * cm)
        img.hAlign = "CENTER"
        story.append(Spacer(1, 1.4 * cm))
        story.append(img)
    story.append(Spacer(1, 1.1 * cm))
    story.append(p("Auditoria Final y Estado de Preparacion", styles["CoverTitle"]))
    story.append(p("AgroEscudo Control Center V1.0 P0", styles["CoverTitle"]))
    story.append(p("Backend FastAPI, dashboard web Next.js, app Flutter Android, IoT ingestion, reportes PDF, RBAC, Control Center y preparacion para piloto B2B.", styles["CoverSub"]))
    story.append(Spacer(1, 1.2 * cm))
    story.append(
        make_table(
            [
                ["Campo", "Detalle"],
                ["Fecha de emision", datetime.now().strftime("%d/%m/%Y %H:%M")],
                ["Preparado por", "AgroEscudo - revision tecnica asistida por Codex"],
                ["Alcance", "Auditoria final de repositorio local y artefactos de release P0"],
                ["Estado general", "Listo para smoke de piloto, con credenciales externas pendientes"],
            ],
            [5 * cm, 11 * cm],
        )
    )
    story.append(PageBreak())

    story.append(p("1. Resumen ejecutivo", styles["H1"]))
    story.append(
        p(
            "AgroEscudo ya cuenta con una base tecnica coherente para piloto comercial de 60 a 90 dias: backend con autenticacion, RBAC, ingestion IoT, alertas, bitacora, reportes PDF, Control Center, Centro de Servicio, Academia, AgroAsistente por reglas, dashboard web y APK Android conectado a la API publica.",
            styles["Body"],
        )
    )
    story.append(
        p(
            "El sistema todavia requiere credenciales productivas y smoke manual en entorno real antes de declararse produccion. Las funciones que dependen de terceros - Resend, S3, FCM, WhatsApp, Telegram y Sentry - quedaron preparadas, pero marcadas como REQUIERE CREDENCIAL.",
            styles["Body"],
        )
    )
    story.append(Spacer(1, 0.2 * cm))
    story.append(
        Table(
            [[
                status_card("Backend", "78 passed", "pytest completo verificado"),
                status_card("Frontend", "Build OK", "Next.js genera / y /control-room"),
                status_card("Mobile", "APK OK", "51.38 MB, API Render"),
            ]],
            colWidths=[5.3 * cm, 5.3 * cm, 5.3 * cm],
        )
    )
    story.append(Spacer(1, 0.4 * cm))
    story.append(
        Table(
            [[
                status_card("Riesgo principal", "Credenciales", "Falta conectar proveedores reales", AMBER),
                status_card("Smoke real", "Pendiente", "Android, Render/Vercel y cliente externo", AMBER),
                status_card("Secretos", "Sin tokens reales", "Busqueda encontro placeholders", GREEN),
            ]],
            colWidths=[5.3 * cm, 5.3 * cm, 5.3 * cm],
        )
    )

    story.append(p("2. Que se implemento", styles["H1"]))
    implemented = [
        ["Area", "Implementacion"],
        ["Backend", "Migracion P0, modelos de sesiones, auditoria, signup, invitaciones, verificacion, reset password, Control Center, servicio, educacion y asistente por reglas."],
        ["Seguridad", "JWT con jti, logout/logout-all, tokens hasheados, RBAC existente por storage unit, auditoria sin secretos y validaciones de entorno demo/produccion."],
        ["Web", "Dashboard consume Control Center; login incluye crear cuenta, invitacion, recuperacion, verificacion y solicitud demo; Sala de Control fullscreen en /control-room."],
        ["Mobile", "APK release generado contra https://agroescudo-api.onrender.com; analyze sin issues; API_BASE_URL obligatorio en release."],
        ["IoT", "Se mantiene POST /api/readings y batch /api/iot/v1/ingest/batch. Firmware/documentacion Arduino preparada con placeholders de provisionamiento."],
        ["Documentacion", "Auditoria, plan, variables, endpoints, seguridad, checklist piloto, roadmap, notas de release y reporte de pruebas."],
    ]
    story.append(make_table(implemented, [4 * cm, 12.5 * cm]))

    story.append(p("3. Arquitectura actual", styles["H1"]))
    story.append(
        make_table(
            [
                ["Componente", "Tecnologia", "Estado"],
                ["Backend API", "FastAPI, SQLAlchemy 2.0, Alembic, ReportLab", "Operativo local; preparado para Render y PostgreSQL."],
                ["Base de datos", "SQLite local / PostgreSQL produccion", "SQLite verificado; PostgreSQL previsto en Render/Neon."],
                ["Frontend web", "Next.js, React, TypeScript, Tailwind, Recharts", "Build OK; listo para Vercel con NEXT_PUBLIC_API_URL."],
                ["Mobile Android", "Flutter", "APK release generado contra API Render."],
                ["IoT", "ESP32/LoRa/WiFi + endpoint batch HMAC", "Codigo/documentacion preparado; prueba fisica pendiente."],
                ["Reportes", "PDF backend ReportLab y PDF web existente", "Reporte semanal y documentos tecnicos disponibles."],
            ],
            [4 * cm, 5.5 * cm, 7 * cm],
        )
    )

    story.append(p("4. Endpoints y modulos principales", styles["H1"]))
    story.append(
        make_table(
            [
                ["Modulo", "Endpoints clave"],
                ["Auth", "/api/auth/login, /api/me, /api/auth/signup/company, /api/auth/invites/accept, /api/auth/email/verify, /api/auth/password/reset, /api/auth/logout"],
                ["Operacion", "/api/companies, /api/sites, /api/storage-units, /api/devices, /api/readings, /api/alerts, /api/operational-logs"],
                ["Control Center", "GET /api/control-center/summary"],
                ["Servicio", "GET/POST /api/service-cases, events, maintenance-reports, photos, signature"],
                ["Educacion", "GET /api/education/articles, POST /api/education/articles/{id}/complete"],
                ["Asistente", "POST /api/agro-assistant/messages con reglas deterministicas P0"],
                ["IoT", "POST /api/readings y POST /api/iot/v1/ingest/batch"],
                ["Reportes", "GET /api/reports/weekly y /api/reports/weekly/pdf"],
            ],
            [4 * cm, 12.5 * cm],
        )
    )

    story.append(PageBreak())
    story.append(p("5. Pruebas y evidencia", styles["H1"]))
    story.append(
        make_table(
            [
                ["Prueba", "Comando", "Resultado"],
                ["Backend", "py -3.13 -m pytest -p no:cacheprovider", "78 passed, 148 warnings conocidos."],
                ["Migracion", "py -3.13 -m alembic upgrade head", "Migracion 202607030001 aplicada."],
                ["Seed", "py -3.13 -m app.seed", "Empresa piloto, 3 storage units, 3 devices, usuarios y thresholds."],
                ["Frontend", "npm.cmd run build", "Build OK; rutas /, /_not-found, /control-room."],
                ["Flutter analyze", "flutter analyze", "No issues found."],
                ["APK release", "flutter build apk --release --dart-define=API_BASE_URL=https://agroescudo-api.onrender.com", "APK 51.38 MB generado."],
            ],
            [3.2 * cm, 7 * cm, 6.3 * cm],
        )
    )
    story.append(p("Artefacto APK", styles["H2"]))
    story.append(
        make_table(
            [
                ["Campo", "Valor"],
                ["Ruta", "dist/AgroEscudo-MVP-release.apk"],
                ["Tamano", "51.38 MB"],
                ["SHA-256", "9F2FAE364C0ACF45E46B951E79A1CCDE45FA141CE1DC5EC25EB06636E4D9569F"],
                ["API configurada", "https://agroescudo-api.onrender.com"],
            ],
            [4 * cm, 12.5 * cm],
        )
    )

    story.append(p("6. Credenciales y configuracion pendiente", styles["H1"]))
    story.append(
        p(
            "Estas variables no deben subirse al repositorio. Deben cargarse en Render, Vercel, Android build o gestor seguro segun corresponda.",
            styles["Body"],
        )
    )
    creds = [
        ["Area", "Variables", "Estado / accion"],
        ["Backend", "DATABASE_URL", "Usar PostgreSQL productivo Neon/Supabase/Render. No SQLite en demo/produccion."],
        ["Backend", "JWT_SECRET", "Generar secreto largo unico. No usar change-me-in-production."],
        ["CORS", "CORS_ORIGINS", "Configurar dominio Vercel final, sin wildcard en produccion."],
        ["Email Resend", "EMAIL_ENABLED, EMAIL_FROM, EMAIL_API_KEY, EMAIL_REPLY_TO", "REQUIERE CREDENCIAL. Habilitar cuando haya cuenta Resend validada."],
        ["Storage S3", "STORAGE_PROVIDER=s3, S3_ENDPOINT_URL, S3_BUCKET, S3_ACCESS_KEY_ID, S3_SECRET_ACCESS_KEY", "REQUIERE CREDENCIAL para fotos, firmas y archivos persistentes."],
        ["WhatsApp", "WHATSAPP_ENABLED, WHATSAPP_ACCESS_TOKEN, WHATSAPP_PHONE_NUMBER_ID, WHATSAPP_TEMPLATE_ALERT_NAME", "Mantener dry-run hasta aprobar Meta Cloud API."],
        ["Telegram", "TELEGRAM_ENABLED, TELEGRAM_BOT_TOKEN", "Crear bot y cargar chat_id por usuario."],
        ["FCM", "FCM_ENABLED, FIREBASE_PROJECT_ID, FIREBASE_SERVICE_ACCOUNT_FILE", "Opcional para push; no usar Firebase como base de datos."],
        ["Sentry", "SENTRY_ENABLED, SENTRY_DSN, RELEASE_VERSION", "Opcional para observabilidad."],
        ["Mobile", "API_BASE_URL", "Compilar release con URL publica Render."],
        ["Firmware", "WIFI_PASSWORD, GATEWAY_SECRET, NODE_SECRET_*", "Son placeholders. Provisionar por sitio y no hardcodear secretos reales."],
    ]
    story.append(make_table(creds, [3.4 * cm, 6.2 * cm, 6.9 * cm]))

    story.append(PageBreak())
    story.append(p("7. Hallazgos de seguridad", styles["H1"]))
    story.append(
        make_table(
            [
                ["Hallazgo", "Estado", "Accion"],
                ["Secretos reales en repositorio", "No encontrados en busqueda rapida", "Mantener .env, APK, keystores y builds fuera de Git."],
                ["Placeholders de firmware", "Encontrados", "Reemplazar por provisionamiento seguro antes de campo."],
                ["JWT y sesiones", "Implementado", "Configurar JWT_SECRET fuerte y probar logout en nube."],
                ["RBAC", "Implementado y probado en backend existente", "Hacer smoke manual con admin, tecnico y cliente."],
                ["S3/Email externos", "Preparados", "Cargar credenciales y probar con datos no sensibles."],
                ["Smoke fisico IoT", "Pendiente", "Probar ESP32, LoRa, gateway, duplicados y perdida de conexion."],
            ],
            [5 * cm, 4.2 * cm, 7.3 * cm],
        )
    )

    story.append(p("8. Lo que falta para estar bien conformado", styles["H1"]))
    remaining = [
        ["Prioridad", "Pendiente", "Resultado esperado"],
        ["Alta", "Cargar credenciales reales en Render/Vercel: DATABASE_URL, JWT_SECRET, CORS_ORIGINS, PUBLIC_APP_URL.", "Backend publico estable y seguro."],
        ["Alta", "Configurar Resend o mantener EMAIL_ENABLED=false hasta tener dominio/cuenta.", "Signup, invitaciones y reset por correo real."],
        ["Alta", "Configurar S3 compatible para fotos y firmas.", "Evidencia de mantenimiento persistente, no dependiente del filesystem efimero."],
        ["Alta", "Smoke manual: admin, tecnico, cliente, PDF, Control Room, APK Android, alertas.", "Checklist de piloto firmado."],
        ["Media", "Activar WhatsApp/Telegram reales cuando haya tokens y templates.", "Notificacion externa a responsables."],
        ["Media", "Prueba fisica firmware LoRa/WiFi con nodos reales.", "Confirmacion end-to-end sensor -> gateway -> API -> alerta -> dashboard."],
        ["Media", "Crear commit y tag agroescudo-control-center-v1.0.0.", "Release versionada y recuperable."],
        ["Baja", "Pulir pantallas dedicadas para signup/invitacion/reset.", "Mejor UX comercial fuera del panel de login."],
    ]
    story.append(make_table(remaining, [2.3 * cm, 7 * cm, 7.2 * cm]))

    story.append(p("9. Checklist final recomendado", styles["H1"]))
    checklist = [
        "1. Crear backup de base productiva antes de migrar.",
        "2. Configurar variables Render y ejecutar migraciones.",
        "3. Configurar Vercel con NEXT_PUBLIC_API_URL apuntando a Render.",
        "4. Instalar APK en Android real y probar los tres roles.",
        "5. Verificar /control-room con sesion admin.",
        "6. Simular o recibir lectura critica y validar alerta.",
        "7. Registrar accion correctiva y mantenimiento.",
        "8. Descargar PDF semanal y revisar contenido.",
        "9. Validar que cliente no ve datos ajenos.",
        "10. Crear commit, tag y guardar SHA del APK entregado.",
    ]
    for item in checklist:
        story.append(p(item, styles["Body"]))

    story.append(Spacer(1, 0.5 * cm))
    story.append(
        p(
            "<b>Conclusion:</b> AgroEscudo esta tecnicamente encaminado para piloto comercial P0. No debe declararse produccion final hasta completar credenciales externas, smoke manual de nube, prueba Android real y validacion fisica IoT.",
            styles["Body"],
        )
    )
    return story


def main() -> None:
    doc = SimpleDocTemplate(
        str(PDF_PATH),
        pagesize=A4,
        rightMargin=1.5 * cm,
        leftMargin=1.5 * cm,
        topMargin=1.7 * cm,
        bottomMargin=1.5 * cm,
        title="AgroEscudo Auditoria Final Control Center V1.0",
        author="AgroEscudo",
    )
    doc.build(build_story(), onFirstPage=header_footer, onLaterPages=header_footer)
    print(PDF_PATH)


if __name__ == "__main__":
    main()
