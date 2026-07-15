$ErrorActionPreference = "Stop"
Set-StrictMode -Version Latest

$Root = Resolve-Path (Join-Path $PSScriptRoot "..")
$SourceDir = Join-Path $Root "docs\source"
$DistDir = Join-Path $Root "dist\docs"
$MergedMarkdown = Join-Path $DistDir "AgroEscudo_Documento_Maestro_2026.md"
$HtmlOut = Join-Path $DistDir "AgroEscudo_Documento_Maestro_2026.html"
$PdfOut = Join-Path $DistDir "AgroEscudo_Documento_Maestro_2026.pdf"
$HashOut = Join-Path $DistDir "AgroEscudo_Documento_Maestro_2026.sha256"
$LogOut = Join-Path $DistDir "build_documentation.log"

New-Item -ItemType Directory -Force -Path $DistDir | Out-Null

function Write-Log {
    param([string]$Message)
    $line = "[$(Get-Date -Format 'yyyy-MM-dd HH:mm:ss')] $Message"
    $line | Tee-Object -FilePath $LogOut -Append
}

if (Test-Path $LogOut) {
    Remove-Item $LogOut -Force
}

Write-Log "AgroEscudo master documentation build started."
Write-Log "Root: $Root"

$RequiredFiles = @(
    "00_INVENTARIO_REAL.md",
    "01_ARQUITECTURA_GENERAL.md",
    "02_ESTRUCTURA_REPOSITORIO.md",
    "03_BACKEND.md",
    "04_BASE_DE_DATOS.md",
    "05_FRONTEND_WEB.md",
    "06_APP_FLUTTER.md",
    "07_LANDING.md",
    "08_HARDWARE_FIRMWARE.md",
    "09_CLAVES_Y_APROVISIONAMIENTO.md",
    "10_PROTOCOLO_LORA.md",
    "11_DESPLIEGUE.md",
    "12_MANUAL_USUARIO.md",
    "13_OPERACION_Y_MANTENIMIENTO.md",
    "14_SEGURIDAD.md",
    "15_PRUEBAS.md",
    "16_AUDITORIA_FINAL.md",
    "17_FALTANTES_PARA_FINAL.md",
    "18_GUIA_RAPIDA.md"
)

foreach ($file in $RequiredFiles) {
    $path = Join-Path $SourceDir $file
    if (-not (Test-Path $path)) {
        throw "Missing required documentation source: $file"
    }
}
Write-Log "All required source files exist."

$SensitivePatterns = @(
    "admin123",
    "tecnico123",
    "cliente123",
    "secret-token",
    "sk-[A-Za-z0-9_-]{20,}",
    "xox[baprs]-[A-Za-z0-9-]{10,}",
    "AIza[0-9A-Za-z_-]{20,}",
    "postgresql\+psycopg://[^<\s]+:[^<\s]+@",
    "DATABASE_URL\s*=\s*postgresql\+psycopg://[^<\s]+:[^<\s]+@",
    "JWT_SECRET\s*=\s*(?!<JWT_SECRET>|change-me|CAMBIAR|$).{12,}",
    "WHATSAPP_ACCESS_TOKEN\s*=\s*\S+",
    "TELEGRAM_BOT_TOKEN\s*=\s*\S+",
    "OPENAI_API_KEY\s*=\s*\S+",
    "NODE_AES_KEY\s*=\s*\S+",
    "GATEWAY_HMAC_SECRET\s*=\s*\S+"
)

$sensitiveHits = @()
foreach ($file in $RequiredFiles) {
    $path = Join-Path $SourceDir $file
    $content = Get-Content $path -Raw
    foreach ($pattern in $SensitivePatterns) {
        if ($content -match $pattern) {
            $sensitiveHits += "$file :: $pattern"
        }
    }
}

if ($sensitiveHits.Count -gt 0) {
    $sensitiveHits | ForEach-Object { Write-Log "Sensitive pattern hit: $_" }
    throw "Sensitive-looking content found. Review docs/source before building."
}
Write-Log "Sensitive pattern scan passed."

$header = @"
# AgroEscudo - Documento Maestro 2026

Estado: documento tecnico consolidado  
Generado: $(Get-Date -Format 'yyyy-MM-dd HH:mm:ss')  
Clasificacion: listo para demo comercial controlada; piloto comercial sujeto a verificacion de P0.

> Este documento distingue evidencia confirmada, configuracion no verificada y pendientes. No contiene secretos reales.

---

"@

Set-Content -Path $MergedMarkdown -Value $header -Encoding UTF8
foreach ($file in $RequiredFiles) {
    Add-Content -Path $MergedMarkdown -Value "`n`n---`n`n" -Encoding UTF8
    Add-Content -Path $MergedMarkdown -Value (Get-Content (Join-Path $SourceDir $file) -Raw) -Encoding UTF8
}
Write-Log "Merged Markdown created: $MergedMarkdown"

$HtmlScript = Join-Path $DistDir "_build_master_html.py"
@'
from __future__ import annotations

import html
from pathlib import Path

root = Path(__file__).resolve().parent
md_path = root / "AgroEscudo_Documento_Maestro_2026.md"
html_path = root / "AgroEscudo_Documento_Maestro_2026.html"

text = md_path.read_text(encoding="utf-8")
lines = text.splitlines()

def inline(value: str) -> str:
    value = html.escape(value)
    value = value.replace("`", "")
    return value

out: list[str] = []
out.append("""<!doctype html>
<html lang="es">
<head>
<meta charset="utf-8">
<title>AgroEscudo - Documento Maestro 2026</title>
<style>
@page { margin: 26mm 18mm; }
body { font-family: Inter, Arial, Helvetica, sans-serif; color: #1f2937; background: #ffffff; line-height: 1.55; }
h1 { color: #064e3b; font-size: 30px; margin: 34px 0 14px; border-bottom: 3px solid #d99a00; padding-bottom: 8px; }
h2 { color: #065f46; font-size: 22px; margin: 28px 0 10px; }
h3 { color: #047857; font-size: 17px; margin: 20px 0 8px; }
p { margin: 7px 0; }
blockquote { border-left: 4px solid #d99a00; padding: 8px 14px; background: #f8faf9; color: #374151; }
code, pre { font-family: Consolas, Menlo, monospace; }
pre { background: #f4f7f5; border: 1px solid #dde7e2; border-radius: 8px; padding: 12px; white-space: pre-wrap; font-size: 12px; }
table { border-collapse: collapse; width: 100%; margin: 12px 0 18px; font-size: 12px; }
th { background: #064e3b; color: white; text-align: left; }
th, td { border: 1px solid #dde7e2; padding: 7px 8px; vertical-align: top; }
tr:nth-child(even) td { background: #f8faf9; }
hr { border: 0; height: 1px; background: #dde7e2; margin: 28px 0; }
.mermaid-note { color: #64748b; font-size: 12px; margin-bottom: 4px; }
</style>
</head>
<body>
""")

i = 0
in_code = False
code_lang = ""
code_buf: list[str] = []
in_ul = False

def close_ul():
    global in_ul
    if in_ul:
        out.append("</ul>")
        in_ul = False

while i < len(lines):
    line = lines[i]
    stripped = line.strip()
    if stripped.startswith("```"):
        if not in_code:
            close_ul()
            in_code = True
            code_lang = stripped[3:].strip()
            code_buf = []
        else:
            if code_lang == "mermaid":
                out.append('<div class="mermaid-note">Diagrama Mermaid incluido como fuente verificable.</div>')
            out.append("<pre><code>" + html.escape("\n".join(code_buf)) + "</code></pre>")
            in_code = False
            code_lang = ""
            code_buf = []
        i += 1
        continue
    if in_code:
        code_buf.append(line)
        i += 1
        continue

    if stripped == "":
        close_ul()
        i += 1
        continue

    if stripped == "---":
        close_ul()
        out.append("<hr>")
        i += 1
        continue

    if stripped.startswith("|") and i + 1 < len(lines) and set(lines[i + 1].strip().replace("|", "").replace("-", "").replace(":", "").replace(" ", "")) == set():
        close_ul()
        headers = [inline(c.strip()) for c in stripped.strip("|").split("|")]
        i += 2
        rows: list[list[str]] = []
        while i < len(lines) and lines[i].strip().startswith("|"):
            rows.append([inline(c.strip()) for c in lines[i].strip().strip("|").split("|")])
            i += 1
        out.append("<table><thead><tr>" + "".join(f"<th>{h}</th>" for h in headers) + "</tr></thead><tbody>")
        for row in rows:
            out.append("<tr>" + "".join(f"<td>{cell}</td>" for cell in row) + "</tr>")
        out.append("</tbody></table>")
        continue

    if stripped.startswith("#"):
        close_ul()
        level = min(len(stripped) - len(stripped.lstrip("#")), 3)
        title = stripped[level:].strip()
        out.append(f"<h{level}>{inline(title)}</h{level}>")
        i += 1
        continue

    if stripped.startswith("- "):
        if not in_ul:
            out.append("<ul>")
            in_ul = True
        out.append(f"<li>{inline(stripped[2:])}</li>")
        i += 1
        continue

    if stripped.startswith(">"):
        close_ul()
        out.append("<blockquote>" + inline(stripped.lstrip("> ").strip()) + "</blockquote>")
        i += 1
        continue

    close_ul()
    out.append("<p>" + inline(stripped) + "</p>")
    i += 1

close_ul()
out.append("</body></html>")
html_path.write_text("\n".join(out), encoding="utf-8")
'@ | Set-Content -Path $HtmlScript -Encoding UTF8

py -3.13 $HtmlScript
Write-Log "HTML created: $HtmlOut"

$PdfScript = Join-Path $DistDir "_build_master_pdf.py"
@'
from __future__ import annotations

from pathlib import Path
from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_LEFT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.platypus import (
    SimpleDocTemplate,
    Paragraph,
    Spacer,
    PageBreak,
    Table,
    TableStyle,
    Preformatted,
    KeepTogether,
)

root = Path(__file__).resolve().parent
source_root = root.parent.parent / "docs" / "source"
pdf_path = root / "AgroEscudo_Documento_Maestro_2026.pdf"

files = [
    "00_INVENTARIO_REAL.md",
    "01_ARQUITECTURA_GENERAL.md",
    "02_ESTRUCTURA_REPOSITORIO.md",
    "03_BACKEND.md",
    "04_BASE_DE_DATOS.md",
    "05_FRONTEND_WEB.md",
    "06_APP_FLUTTER.md",
    "07_LANDING.md",
    "08_HARDWARE_FIRMWARE.md",
    "09_CLAVES_Y_APROVISIONAMIENTO.md",
    "10_PROTOCOLO_LORA.md",
    "11_DESPLIEGUE.md",
    "12_MANUAL_USUARIO.md",
    "13_OPERACION_Y_MANTENIMIENTO.md",
    "14_SEGURIDAD.md",
    "15_PRUEBAS.md",
    "16_AUDITORIA_FINAL.md",
    "17_FALTANTES_PARA_FINAL.md",
    "18_GUIA_RAPIDA.md",
]

styles = getSampleStyleSheet()
styles.add(ParagraphStyle("CoverTitle", fontName="Helvetica-Bold", fontSize=30, leading=34, textColor=colors.HexColor("#064e3b"), alignment=TA_CENTER, spaceAfter=14))
styles.add(ParagraphStyle("CoverSubtitle", fontName="Helvetica", fontSize=13, leading=18, textColor=colors.HexColor("#374151"), alignment=TA_CENTER, spaceAfter=8))
styles.add(ParagraphStyle("H1Agro", fontName="Helvetica-Bold", fontSize=20, leading=24, textColor=colors.HexColor("#064e3b"), spaceBefore=12, spaceAfter=8))
styles.add(ParagraphStyle("H2Agro", fontName="Helvetica-Bold", fontSize=15, leading=19, textColor=colors.HexColor("#065f46"), spaceBefore=10, spaceAfter=6))
styles.add(ParagraphStyle("H3Agro", fontName="Helvetica-Bold", fontSize=12, leading=15, textColor=colors.HexColor("#047857"), spaceBefore=8, spaceAfter=4))
styles.add(ParagraphStyle("BodyAgro", fontName="Helvetica", fontSize=9, leading=12, textColor=colors.HexColor("#1f2937"), spaceAfter=5))
styles.add(ParagraphStyle("BulletAgro", fontName="Helvetica", fontSize=9, leading=12, leftIndent=10, firstLineIndent=-6, spaceAfter=3))
styles.add(ParagraphStyle("SmallAgro", fontName="Helvetica", fontSize=7.5, leading=10, textColor=colors.HexColor("#374151")))
styles.add(ParagraphStyle("TableHeaderAgro", fontName="Helvetica-Bold", fontSize=7.5, leading=10, textColor=colors.white))

def esc(text: str) -> str:
    return (text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;"))

def clean_inline(text: str) -> str:
    return esc(text.replace("`", ""))

def footer(canvas, doc):
    canvas.saveState()
    width, height = A4
    canvas.setStrokeColor(colors.HexColor("#d9e5df"))
    canvas.line(18 * mm, 14 * mm, width - 18 * mm, 14 * mm)
    canvas.setFillColor(colors.HexColor("#064e3b"))
    canvas.setFont("Helvetica-Bold", 8)
    canvas.drawString(18 * mm, 9 * mm, "AgroEscudo")
    canvas.setFont("Helvetica", 8)
    canvas.setFillColor(colors.HexColor("#64748b"))
    canvas.drawRightString(width - 18 * mm, 9 * mm, f"Pagina {doc.page}")
    canvas.restoreState()

doc = SimpleDocTemplate(
    str(pdf_path),
    pagesize=A4,
    rightMargin=17 * mm,
    leftMargin=17 * mm,
    topMargin=18 * mm,
    bottomMargin=18 * mm,
)

story = []
story.append(Spacer(1, 42 * mm))
story.append(Paragraph("AgroEscudo", styles["CoverTitle"]))
story.append(Paragraph("Documento Maestro 2026", styles["CoverTitle"]))
story.append(Paragraph("Arquitectura, operacion, seguridad, IoT, despliegue y checklist para demo comercial controlada.", styles["CoverSubtitle"]))
story.append(Spacer(1, 8 * mm))
cover_table = Table([
    ["Clasificacion", "Listo para demo comercial controlada"],
    ["Alcance", "Backend, web, mobile, IoT, firmware, seguridad y operacion"],
    ["Nota", "Piloto comercial sujeto a verificacion de hardware, cloud y backup/restore"],
], colWidths=[42 * mm, 112 * mm])
cover_table.setStyle(TableStyle([
    ("BACKGROUND", (0, 0), (0, -1), colors.HexColor("#064e3b")),
    ("TEXTCOLOR", (0, 0), (0, -1), colors.white),
    ("TEXTCOLOR", (1, 0), (1, -1), colors.HexColor("#1f2937")),
    ("FONTNAME", (0, 0), (-1, -1), "Helvetica"),
    ("FONTNAME", (0, 0), (0, -1), "Helvetica-Bold"),
    ("FONTSIZE", (0, 0), (-1, -1), 9),
    ("GRID", (0, 0), (-1, -1), 0.4, colors.HexColor("#dde7e2")),
    ("VALIGN", (0, 0), (-1, -1), "TOP"),
    ("ROWBACKGROUNDS", (1, 0), (1, -1), [colors.white, colors.HexColor("#f8faf9")]),
    ("LEFTPADDING", (0, 0), (-1, -1), 8),
    ("RIGHTPADDING", (0, 0), (-1, -1), 8),
    ("TOPPADDING", (0, 0), (-1, -1), 7),
    ("BOTTOMPADDING", (0, 0), (-1, -1), 7),
]))
story.append(cover_table)
story.append(PageBreak())

def add_table(rows: list[list[str]]):
    if not rows:
        return
    max_cols = max(len(r) for r in rows)
    normalized = [r + [""] * (max_cols - len(r)) for r in rows]
    width = 176 * mm
    col_width = width / max_cols
    data = []
    for row_index, row in enumerate(normalized):
        style = styles["TableHeaderAgro"] if row_index == 0 else styles["SmallAgro"]
        data.append([Paragraph(clean_inline(cell), style) for cell in row])
    table = Table(data, colWidths=[col_width] * max_cols, repeatRows=1)
    table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#064e3b")),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("GRID", (0, 0), (-1, -1), 0.35, colors.HexColor("#dde7e2")),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#f8faf9")]),
        ("LEFTPADDING", (0, 0), (-1, -1), 4),
        ("RIGHTPADDING", (0, 0), (-1, -1), 4),
        ("TOPPADDING", (0, 0), (-1, -1), 4),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
    ]))
    story.append(table)
    story.append(Spacer(1, 5))

first_h1_seen = False

def parse_file(path: Path):
    global first_h1_seen
    lines = path.read_text(encoding="utf-8").splitlines()
    i = 0
    while i < len(lines):
        stripped = lines[i].strip()
        if not stripped:
            i += 1
            continue
        if stripped.startswith("```"):
            lang = stripped[3:].strip()
            i += 1
            buf = []
            while i < len(lines) and not lines[i].strip().startswith("```"):
                buf.append(lines[i])
                i += 1
            i += 1
            label = "Diagrama Mermaid" if lang == "mermaid" else "Bloque tecnico"
            story.append(Paragraph(label, styles["H3Agro"]))
            story.append(Preformatted("\n".join(buf[:80]), styles["SmallAgro"], maxLineLength=95))
            story.append(Spacer(1, 5))
            continue
        if stripped.startswith("|") and i + 1 < len(lines) and lines[i + 1].strip().startswith("|"):
            headers = [c.strip() for c in stripped.strip("|").split("|")]
            sep = lines[i + 1].strip()
            if set(sep.replace("|", "").replace("-", "").replace(":", "").replace(" ", "")) == set():
                i += 2
                rows = [headers]
                while i < len(lines) and lines[i].strip().startswith("|"):
                    rows.append([c.strip() for c in lines[i].strip().strip("|").split("|")])
                    i += 1
                add_table(rows)
                continue
        if stripped.startswith("# "):
            if first_h1_seen:
                story.append(PageBreak())
            first_h1_seen = True
            story.append(Paragraph(clean_inline(stripped[2:]), styles["H1Agro"]))
        elif stripped.startswith("## "):
            story.append(Paragraph(clean_inline(stripped[3:]), styles["H2Agro"]))
        elif stripped.startswith("### "):
            story.append(Paragraph(clean_inline(stripped[4:]), styles["H3Agro"]))
        elif stripped.startswith("- "):
            story.append(Paragraph("- " + clean_inline(stripped[2:]), styles["BulletAgro"]))
        elif stripped.startswith(">"):
            story.append(KeepTogether([
                Paragraph(clean_inline(stripped.lstrip("> ").strip()), styles["BodyAgro"]),
                Spacer(1, 3),
            ]))
        elif stripped == "---":
            story.append(Spacer(1, 4))
        else:
            story.append(Paragraph(clean_inline(stripped), styles["BodyAgro"]))
        i += 1

for name in files:
    parse_file(source_root / name)

doc.build(story, onFirstPage=footer, onLaterPages=footer)
'@ | Set-Content -Path $PdfScript -Encoding UTF8

py -3.13 $PdfScript
Write-Log "PDF created: $PdfOut"

$hash = Get-FileHash -Algorithm SHA256 $PdfOut
"$($hash.Hash)  $([System.IO.Path]::GetFileName($PdfOut))" | Set-Content -Path $HashOut -Encoding ASCII
Write-Log "SHA-256 created: $HashOut"

Remove-Item $HtmlScript, $PdfScript -Force
Write-Log "Temporary build scripts removed."
Write-Log "AgroEscudo master documentation build completed."

Write-Host ""
Write-Host "Generated files:"
Write-Host " - $MergedMarkdown"
Write-Host " - $HtmlOut"
Write-Host " - $PdfOut"
Write-Host " - $HashOut"
Write-Host " - $LogOut"
