from __future__ import annotations

import argparse
from datetime import datetime
from pathlib import Path

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import cm
from reportlab.platypus import (
    Image,
    PageBreak,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)


ROOT = Path(__file__).resolve().parents[1]
OUTPUT_DIR = ROOT / "output" / "pdf"
DEFAULT_OUTPUT = OUTPUT_DIR / "AgroEscudo_Auditoria_Final_Sentinel_v0.2.pdf"
LOGO = ROOT / "frontend" / "public" / "brand" / "logo-horizontal-transparent.png"
SHIELD = ROOT / "frontend" / "public" / "brand" / "shield-transparent.png"

GREEN_DARK = colors.HexColor("#064B35")
GREEN = colors.HexColor("#047857")
AMBER = colors.HexColor("#C89116")
INK = colors.HexColor("#24342F")
MUTED = colors.HexColor("#64746E")
LINE = colors.HexColor("#DDE7E2")
SOFT = colors.HexColor("#F7FAF8")
RED = colors.HexColor("#B42318")
WHITE = colors.white


styles = getSampleStyleSheet()
styles.add(
    ParagraphStyle(
        name="AE-Cover",
        parent=styles["Title"],
        fontName="Helvetica-Bold",
        fontSize=28,
        leading=33,
        alignment=TA_CENTER,
        textColor=GREEN_DARK,
        spaceAfter=10,
    )
)
styles.add(
    ParagraphStyle(
        name="AE-CoverSub",
        parent=styles["Normal"],
        fontName="Helvetica",
        fontSize=11.5,
        leading=17,
        alignment=TA_CENTER,
        textColor=MUTED,
    )
)
styles.add(
    ParagraphStyle(
        name="AE-H1",
        parent=styles["Heading1"],
        fontName="Helvetica-Bold",
        fontSize=18,
        leading=23,
        textColor=GREEN_DARK,
        spaceBefore=6,
        spaceAfter=9,
    )
)
styles.add(
    ParagraphStyle(
        name="AE-H2",
        parent=styles["Heading2"],
        fontName="Helvetica-Bold",
        fontSize=11.5,
        leading=15,
        textColor=GREEN_DARK,
        spaceBefore=7,
        spaceAfter=5,
    )
)
styles.add(
    ParagraphStyle(
        name="AE-Body",
        parent=styles["BodyText"],
        fontName="Helvetica",
        fontSize=9,
        leading=13.5,
        textColor=INK,
        spaceAfter=6,
    )
)
styles.add(
    ParagraphStyle(
        name="AE-Small",
        parent=styles["BodyText"],
        fontName="Helvetica",
        fontSize=7.5,
        leading=10,
        textColor=MUTED,
    )
)
styles.add(
    ParagraphStyle(
        name="AE-Kicker",
        parent=styles["BodyText"],
        fontName="Helvetica-Bold",
        fontSize=7.3,
        leading=9,
        textColor=AMBER,
        spaceAfter=3,
    )
)
styles.add(
    ParagraphStyle(
        name="AE-Cell",
        parent=styles["BodyText"],
        fontName="Helvetica",
        fontSize=7.7,
        leading=10.3,
        textColor=INK,
    )
)
styles.add(
    ParagraphStyle(
        name="AE-CellHead",
        parent=styles["BodyText"],
        fontName="Helvetica-Bold",
        fontSize=7.6,
        leading=9.5,
        textColor=WHITE,
    )
)
styles.add(
    ParagraphStyle(
        name="AE-CardValue",
        parent=styles["BodyText"],
        fontName="Helvetica-Bold",
        fontSize=16,
        leading=19,
        textColor=GREEN_DARK,
    )
)


def paragraph(text: str, style: str = "AE-Body") -> Paragraph:
    return Paragraph(text, styles[style])


def table(rows: list[list[str]], widths: list[float], header: bool = True) -> Table:
    content = []
    for row_index, row in enumerate(rows):
        style = "AE-CellHead" if header and row_index == 0 else "AE-Cell"
        content.append([paragraph(str(cell), style) for cell in row])
    result = Table(content, colWidths=widths, repeatRows=1 if header else 0, hAlign="LEFT")
    result.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), GREEN_DARK if header else WHITE),
                ("ROWBACKGROUNDS", (0, 1), (-1, -1), [WHITE, SOFT]),
                ("GRID", (0, 0), (-1, -1), 0.45, LINE),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("LEFTPADDING", (0, 0), (-1, -1), 6),
                ("RIGHTPADDING", (0, 0), (-1, -1), 6),
                ("TOPPADDING", (0, 0), (-1, -1), 6),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
            ]
        )
    )
    return result


def card(label: str, value: str, note: str, color=GREEN_DARK) -> Table:
    content = [
        [paragraph(label.upper(), "AE-Kicker")],
        [Paragraph(f"<font color='{color.hexval()}'><b>{value}</b></font>", styles["AE-CardValue"])],
        [paragraph(note, "AE-Small")],
    ]
    result = Table(content, colWidths=[5.1 * cm])
    result.setStyle(
        TableStyle(
            [
                ("BOX", (0, 0), (-1, -1), 0.6, LINE),
                ("BACKGROUND", (0, 0), (-1, -1), WHITE),
                ("LEFTPADDING", (0, 0), (-1, -1), 10),
                ("RIGHTPADDING", (0, 0), (-1, -1), 10),
                ("TOPPADDING", (0, 0), (-1, -1), 8),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
            ]
        )
    )
    return result


def header_footer(canvas, document) -> None:
    canvas.saveState()
    width, height = A4
    canvas.setStrokeColor(LINE)
    canvas.setLineWidth(0.6)
    canvas.line(1.5 * cm, height - 1.3 * cm, width - 1.5 * cm, height - 1.3 * cm)
    canvas.line(1.5 * cm, 1.2 * cm, width - 1.5 * cm, 1.2 * cm)
    canvas.setFillColor(GREEN_DARK)
    canvas.setFont("Helvetica-Bold", 8)
    canvas.drawString(1.5 * cm, height - 1.0 * cm, "AgroEscudo - Auditoría final Sentinel v0.2")
    canvas.setFillColor(MUTED)
    canvas.setFont("Helvetica", 7)
    canvas.drawRightString(width - 1.5 * cm, height - 1.0 * cm, "Control postcosecha y respaldo GSM")
    canvas.drawString(1.5 * cm, 0.78 * cm, "Confidencial - Piloto comercial controlado")
    canvas.drawRightString(width - 1.5 * cm, 0.78 * cm, f"Página {document.page}")
    canvas.restoreState()


def cover(story: list, args: argparse.Namespace) -> None:
    story.append(Spacer(1, 1.2 * cm))
    if LOGO.exists():
        logo = Image(str(LOGO), width=10.2 * cm, height=2.25 * cm)
        logo.hAlign = "CENTER"
        story.append(logo)
    elif SHIELD.exists():
        shield = Image(str(SHIELD), width=3.3 * cm, height=3.3 * cm)
        shield.hAlign = "CENTER"
        story.append(shield)
    story.append(Spacer(1, 1.3 * cm))
    story.append(paragraph("AUDITORÍA DE RELEASE", "AE-Kicker"))
    story.append(paragraph("AgroEscudo Sentinel v0.2", "AE-Cover"))
    story.append(paragraph("Backend de decisión, trazabilidad central y respaldo GSM mediante ESP32 + SIM800L", "AE-CoverSub"))
    story.append(Spacer(1, 1.2 * cm))
    story.append(
        table(
            [
                ["Campo", "Resultado"],
                ["Fecha de emisión", datetime.now().strftime("%d/%m/%Y %H:%M")],
                ["Commit auditado", args.commit],
                ["API pública", args.api_status],
                ["Web pública", args.web_status],
                ["Dictamen", "Apto para piloto controlado, condicionado a prueba física GSM y aprovisionamiento real."],
            ],
            [4.2 * cm, 12.3 * cm],
        )
    )
    story.append(Spacer(1, 1.0 * cm))
    story.append(
        Table(
            [[
                card("Software", "Verificado", "Tests, builds y migración local"),
                card("Nube", args.cloud_label, "Render y Vercel"),
                card("Hardware", "Pendiente", "Prueba física SIM800L", AMBER),
            ]],
            colWidths=[5.3 * cm, 5.3 * cm, 5.3 * cm],
        )
    )
    story.append(PageBreak())


def build_story(args: argparse.Namespace) -> list:
    story: list = []
    cover(story, args)

    story.append(paragraph("1. Resumen ejecutivo", "AE-H1"))
    story.append(
        paragraph(
            "La release incorpora AgroEscudo Sentinel como canal de respaldo GSM gobernado por FastAPI. La plataforma decide cuándo notificar, conserva la política por empresa o silo y registra cada intento. El ESP32 no contiene reglas de negocio ni credenciales de usuario: consulta un trabajo, lo ejecuta y reporta un resultado limitado.",
        )
    )
    story.append(
        paragraph(
            "El resultado es adecuado para una prueba piloto supervisada. No se considera validada la entrega extremo a extremo hasta probar alimentación, antena, cobertura, saldo de la SIM, SMS y llamada en el lugar real.",
        )
    )
    story.append(
        Table(
            [[
                card("Backend", "145 passed", "Suite completa Pytest"),
                card("Web", "14 passed", "Test, lint y build"),
                card("Android", "APK OK", "68,92 MB contra Render"),
            ]],
            colWidths=[5.3 * cm, 5.3 * cm, 5.3 * cm],
        )
    )
    story.append(Spacer(1, 0.45 * cm))
    story.append(
        Table(
            [[
                card("Firmware", "Compila", "ESP32 Dev Module"),
                card("Migración", "Head", "202608090001"),
                card("Secretos", "Sin hallazgos", "Escaneo del diff", GREEN),
            ]],
            colWidths=[5.3 * cm, 5.3 * cm, 5.3 * cm],
        )
    )

    story.append(paragraph("2. Componentes entregados", "AE-H1"))
    story.append(
        table(
            [
                ["Componente", "Responsabilidad"],
                ["AlertContact", "Contacto E.164, alcance, prioridad, demora, severidad mínima y canales."],
                ["SentinelDevice", "Identidad del ESP32, token hasheado, estado, último poll, firmware y señal Wi-Fi."],
                ["SentinelJob", "Cola con idempotencia, disponibilidad, lease, expiración, intentos y resultado."],
                ["NotificationDelivery", "Evidencia auditable de cada SMS o llamada, con destino enmascarado."],
                ["Panel web", "Alta, prueba, activación, rotación y consulta de historial para administración."],
                ["Firmware", "HTTPS con CA, OLED, comandos AT para SIM800L y reporte de resultado."],
                ["PDF operativo", "Resumen de entregas Sentinel sin exponer teléfonos completos."],
            ],
            [4.2 * cm, 12.3 * cm],
        )
    )
    story.append(PageBreak())

    story.append(paragraph("3. Flujo técnico y estados honestos", "AE-H1"))
    story.append(
        table(
            [
                ["Paso", "Control"],
                ["1. Alerta", "La lectura supera el umbral y FastAPI crea una alerta no duplicada."],
                ["2. Política", "Se seleccionan contactos aplicables por empresa, silo y severidad."],
                ["3. Cola", "Se crea como máximo un job por alerta, contacto y canal."],
                ["4. Poll", "Un Sentinel activo se autentica y reclama un único job con lease."],
                ["5. Ejecución", "SIM800L intenta SMS o llamada; el ESP32 no reintenta indefinidamente."],
                ["6. Resultado", "El backend registra resultado, error, reintento o expiración."],
                ["7. Cierre", "Acknowledge/resolve cancela jobs futuros de la alerta."],
            ],
            [3.2 * cm, 13.3 * cm],
        )
    )
    story.append(paragraph("Significado de estados", "AE-H2"))
    story.append(
        table(
            [
                ["Estado", "Significado verificable"],
                ["submitted", "El módem aceptó el comando de SMS. No implica lectura humana."],
                ["attempted", "La llamada fue iniciada. No implica que una persona contestó."],
                ["failed", "La ejecución falló y conserva código técnico sin datos sensibles."],
                ["cancelled", "La alerta fue atendida antes de ejecutar el trabajo pendiente."],
                ["expired", "El trabajo perdió vigencia y no debe ejecutarse."],
            ],
            [3.2 * cm, 13.3 * cm],
        )
    )
    story.append(paragraph("4. Controles de seguridad", "AE-H1"))
    story.append(
        table(
            [
                ["Control", "Resultado"],
                ["Autenticación", "Token Sentinel independiente del JWT, mostrado una sola vez y almacenado como hash."],
                ["Transporte", "HTTPS con validación de CA. El firmware no usa conexión insegura."],
                ["RBAC", "Administración restringida a admin; contacto no puede salir del alcance autorizado."],
                ["Privacidad", "Teléfono completo solo en la ejecución necesaria; vistas, historial y PDF lo enmascaran."],
                ["Idempotencia", "Restricción por alerta, contacto y canal para evitar avisos duplicados."],
                ["Reintentos", "Backoff y máximo de intentos definidos en servidor; sin bucle infinito en ESP32."],
                ["Repositorio", ".env, secrets.h, APK, keystores y certificados privados ignorados."],
            ],
            [4.1 * cm, 12.4 * cm],
        )
    )
    story.append(PageBreak())

    story.append(paragraph("5. Evidencia reproducible", "AE-H1"))
    story.append(
        table(
            [
                ["Área", "Comando o evidencia", "Resultado"],
                ["Backend", "py -3.13 -m pytest -p no:cacheprovider", "145 passed"],
                ["Sentinel", "backend/tests/test_sentinel_v02.py", "12 passed"],
                ["Migración", "alembic current / heads", "202608090001 (head)"],
                ["Frontend", "npm run test; npm run lint; npm run build", "14 passed, lint y build OK"],
                ["Flutter", "flutter analyze; flutter test", "Sin issues; 3 passed"],
                ["APK", "flutter build apk --release --dart-define=API_BASE_URL=...", "68,92 MB"],
                ["Firmware", "platformio run -e arduino_sentinel_v02", "SUCCESS"],
                ["RAM / flash", "PlatformIO size", "15,3% / 85,4%"],
                ["Secretos", "Escaneo de archivos cambiados", "Sin firmas de alta confianza"],
            ],
            [3.1 * cm, 8.2 * cm, 5.2 * cm],
        )
    )
    story.append(paragraph("Artefacto Android", "AE-H2"))
    story.append(
        table(
            [
                ["Campo", "Valor"],
                ["Ruta", "dist/AgroEscudo-Sentinel-Piloto-release.apk"],
                ["API", "https://agroescudo-api.onrender.com"],
                ["SHA-256", args.apk_sha],
            ],
            [3.5 * cm, 13 * cm],
        )
    )
    story.append(paragraph("Advertencias no bloqueantes", "AE-H2"))
    story.append(
        paragraph(
            "Pytest reporta deprecaciones de librerías y una advertencia de orden de borrado por el ciclo companies/users en SQLite de prueba. Flutter informa dependencias más nuevas fuera de las restricciones actuales. Ninguna advertencia produjo fallos, pero deben vigilarse en mantenimiento técnico.",
        )
    )

    story.append(PageBreak())
    story.append(paragraph("6. Credenciales y configuración pendientes", "AE-H1"))
    story.append(
        table(
            [
                ["Ámbito", "Necesario", "Responsable"],
                ["Render", "DATABASE_URL, JWT_SECRET, CORS_ORIGINS, ENVIRONMENT=production", "Administrador de nube"],
                ["Vercel", "NEXT_PUBLIC_API_URL=https://agroescudo-api.onrender.com", "Administrador web"],
                ["Sentinel", "Wi-Fi, token único, CA raíz y URL pública", "Técnico instalador"],
                ["SIM", "SIM activa, saldo/plan, PIN y cobertura", "Responsable del piloto"],
                ["Contacto", "Nombre, teléfono E.164, consentimiento, alcance y severidad", "Cliente / admin"],
                ["Hardware", "Fuente de picos >=2 A, antena, masa común y niveles lógicos", "Técnico electrónico"],
            ],
            [3.1 * cm, 8.6 * cm, 4.8 * cm],
        )
    )
    story.append(paragraph("Variables operativas Sentinel", "AE-H2"))
    story.append(
        table(
            [
                ["Variable", "Valor inicial"],
                ["SENTINEL_POLL_AFTER_SECONDS", "60"],
                ["SENTINEL_LEASE_SECONDS", "150"],
                ["SENTINEL_OFFLINE_AFTER_SECONDS", "180"],
                ["SENTINEL_JOB_EXPIRY_MINUTES", "60"],
                ["SENTINEL_MAX_ATTEMPTS", "3"],
                ["SENTINEL_DEFAULT_RING_SECONDS", "25"],
            ],
            [8.5 * cm, 8 * cm],
        )
    )
    story.append(
        paragraph(
            "Nunca enviar tokens, contraseñas, API keys o certificados privados por Git. El token Sentinel se copia desde la interfaz únicamente al archivo local secrets.h del dispositivo que será provisionado.",
        )
    )

    story.append(PageBreak())
    story.append(paragraph("7. Runbook de puesta en marcha", "AE-H1"))
    story.append(
        table(
            [
                ["Orden", "Acción", "Evidencia esperada"],
                ["1", "Aplicar migración y consultar /api/health/db.", "Head correcto y database=postgresql."],
                ["2", "Crear organización, silo, usuarios y sensor.", "RBAC y lectura operativos."],
                ["3", "Crear Sentinel y guardar el token una vez.", "Equipo activo sin token visible después."],
                ["4", "Cargar firmware con Wi-Fi, CA, URL y token.", "Primer poll; equipo online."],
                ["5", "Registrar contacto y ejecutar pruebas controladas.", "SMS y llamada reales documentados."],
                ["6", "Simular alerta y comprobar idempotencia.", "Un job por contacto/canal."],
                ["7", "Reconocer o resolver alerta.", "Pendientes cancelados."],
                ["8", "Descargar PDF y guardar acta de prueba.", "Evidencia con teléfonos enmascarados."],
            ],
            [1.4 * cm, 8.1 * cm, 7 * cm],
        )
    )
    story.append(paragraph("8. Límites y decisión de salida", "AE-H1"))
    story.append(
        table(
            [
                ["Estado", "Condición"],
                ["VERIFICADO", "Código, pruebas automáticas, builds, migración local, APK y compilación firmware."],
                ["NO VERIFICADO", "Cobertura GSM, estabilidad eléctrica, SMS real, llamada real y recuperación en campo."],
                ["RECOMENDACIÓN", "Usar Render sin suspensión durante el piloto para evitar cold starts y pérdida de oportunidad."],
                ["SALIDA", "Nube desplegada + migración productiva + Sentinel online + prueba física documentada."],
            ],
            [3.4 * cm, 13.1 * cm],
        )
    )
    story.append(Spacer(1, 0.45 * cm))
    story.append(
        paragraph(
            "Conclusión: AgroEscudo Sentinel v0.2 está preparado para un piloto comercial controlado. La calidad de software está demostrada; la aprobación operativa final depende de completar y firmar la prueba física extremo a extremo en el sitio.",
        )
    )
    return story


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--commit", default="Pendiente de publicación")
    parser.add_argument("--api-status", default="Pendiente de verificación pública")
    parser.add_argument("--web-status", default="Pendiente de verificación pública")
    parser.add_argument("--cloud-label", default="Pendiente")
    parser.add_argument(
        "--apk-sha",
        default="A9E6D3B1C30EDE15CD24A057BE03450F0C78D37DCDE23D27B6FF86CC9BDA2257",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    args.output.parent.mkdir(parents=True, exist_ok=True)
    document = SimpleDocTemplate(
        str(args.output),
        pagesize=A4,
        rightMargin=1.5 * cm,
        leftMargin=1.5 * cm,
        topMargin=1.65 * cm,
        bottomMargin=1.5 * cm,
        title="AgroEscudo - Auditoría final Sentinel v0.2",
        author="AgroEscudo",
        subject="Evidencia técnica y preparación para piloto comercial",
    )
    document.build(build_story(args), onFirstPage=header_footer, onLaterPages=header_footer)
    print(args.output)


if __name__ == "__main__":
    main()
