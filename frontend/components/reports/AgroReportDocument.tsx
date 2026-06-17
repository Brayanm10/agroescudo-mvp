import {
  Circle,
  Document,
  Font,
  Image,
  Line,
  Page,
  Path,
  Polyline,
  StyleSheet,
  Svg,
  Text,
  View
} from "@react-pdf/renderer";
import type { Alert, Device, OperationalLog, Reading, StorageUnit, WeeklyReport } from "@/lib/types";

Font.registerHyphenationCallback((word) => [word]);

export type AgroReportPdfData = {
  report: WeeklyReport;
  storageUnit: StorageUnit;
  device?: Device;
  readings: Reading[];
  alerts: Alert[];
  logs: OperationalLog[];
  generatedAt: string;
  logoUrl?: string;
  shieldUrl?: string;
  whiteShieldUrl?: string;
};

const colors = {
  green950: "#022C22",
  green900: "#064E3B",
  green800: "#065F46",
  green700: "#047857",
  amber: "#D99A00",
  text: "#334155",
  muted: "#64748B",
  line: "#DDE7E2",
  page: "#F8FAF9",
  red: "#B91C1C"
};

const styles = StyleSheet.create({
  page: {
    padding: 34,
    fontFamily: "Helvetica",
    color: colors.text,
    backgroundColor: "#FFFFFF"
  },
  cover: {
    padding: 42,
    fontFamily: "Helvetica",
    color: colors.green900,
    backgroundColor: "#FFFFFF"
  },
  circuitLayer: {
    position: "absolute",
    left: 0,
    right: 0,
    top: 0,
    bottom: 0
  },
  coverLogo: {
    width: 230,
    objectFit: "contain"
  },
  headerLogo: {
    width: 150,
    objectFit: "contain"
  },
  fallbackBrand: {
    flexDirection: "row",
    alignItems: "center",
    gap: 10
  },
  brandShield: {
    width: 46,
    height: 46,
    objectFit: "contain"
  },
  brandName: {
    fontSize: 22,
    color: colors.green900,
    fontWeight: 700
  },
  brandTag: {
    marginTop: 3,
    fontSize: 7.5,
    color: colors.amber,
    fontWeight: 700
  },
  coverFrame: {
    minHeight: 700,
    borderWidth: 1,
    borderColor: colors.line,
    borderRadius: 18,
    padding: 28
  },
  coverTop: {
    flexDirection: "row",
    alignItems: "center",
    justifyContent: "space-between"
  },
  coverKicker: {
    marginTop: 86,
    fontSize: 12,
    color: colors.green700,
    fontWeight: 700,
    textTransform: "uppercase",
    letterSpacing: 0.8
  },
  coverTitle: {
    marginTop: 13,
    maxWidth: 390,
    fontSize: 38,
    lineHeight: 1.05,
    color: colors.green900,
    fontWeight: 700
  },
  coverSubtitle: {
    marginTop: 15,
    maxWidth: 360,
    fontSize: 13,
    lineHeight: 1.45,
    color: colors.text
  },
  coverMetaGrid: {
    marginTop: 46,
    flexDirection: "row",
    flexWrap: "wrap",
    gap: 11
  },
  coverMetaCard: {
    width: "48.5%",
    minHeight: 66,
    borderWidth: 1,
    borderColor: colors.line,
    borderRadius: 12,
    padding: 12,
    backgroundColor: "#FFFFFF"
  },
  metaLabel: {
    fontSize: 7.8,
    color: colors.green800,
    fontWeight: 700,
    textTransform: "uppercase",
    letterSpacing: 0.5
  },
  metaValue: {
    marginTop: 7,
    fontSize: 10.3,
    lineHeight: 1.3,
    color: colors.text,
    fontWeight: 700
  },
  header: {
    marginBottom: 20,
    paddingBottom: 12,
    borderBottomWidth: 1,
    borderBottomColor: colors.line,
    flexDirection: "row",
    alignItems: "center",
    justifyContent: "space-between"
  },
  headerTitle: {
    fontSize: 9.5,
    color: colors.green900,
    fontWeight: 700,
    textTransform: "uppercase",
    letterSpacing: 0.45
  },
  headerMeta: {
    marginTop: 4,
    fontSize: 8.3,
    color: colors.muted
  },
  footer: {
    position: "absolute",
    left: 34,
    right: 34,
    bottom: 22,
    paddingTop: 8,
    borderTopWidth: 1,
    borderTopColor: colors.line,
    flexDirection: "row",
    justifyContent: "space-between",
    color: colors.muted,
    fontSize: 8
  },
  eyebrow: {
    fontSize: 9,
    color: colors.amber,
    fontWeight: 700,
    textTransform: "uppercase",
    letterSpacing: 0.65
  },
  sectionTitle: {
    fontSize: 18,
    color: colors.green900,
    fontWeight: 700
  },
  accent: {
    width: 46,
    height: 2,
    marginTop: 8,
    marginBottom: 14,
    backgroundColor: colors.amber
  },
  card: {
    borderWidth: 1,
    borderColor: colors.line,
    borderRadius: 10,
    padding: 14,
    backgroundColor: "#FFFFFF"
  },
  tintedCard: {
    borderWidth: 1,
    borderColor: colors.line,
    borderRadius: 10,
    padding: 14,
    backgroundColor: colors.page
  },
  kpiGrid: {
    flexDirection: "row",
    flexWrap: "wrap",
    gap: 10,
    marginTop: 16
  },
  kpiCard: {
    width: "31.8%",
    minHeight: 76,
    borderWidth: 1,
    borderColor: colors.line,
    borderRadius: 10,
    padding: 12,
    backgroundColor: "#FFFFFF"
  },
  kpiLabel: {
    fontSize: 7.8,
    color: colors.muted,
    textTransform: "uppercase",
    letterSpacing: 0.35,
    fontWeight: 700
  },
  kpiValue: {
    marginTop: 8,
    fontSize: 18,
    color: colors.green900,
    fontWeight: 700
  },
  bodyText: {
    fontSize: 10.5,
    lineHeight: 1.55,
    color: colors.text
  },
  noteText: {
    marginTop: 7,
    fontSize: 8.2,
    lineHeight: 1.35,
    color: colors.muted
  },
  twoColumn: {
    flexDirection: "row",
    gap: 14
  },
  column: {
    flex: 1
  },
  table: {
    borderWidth: 1,
    borderColor: colors.line,
    borderRadius: 8,
    overflow: "hidden"
  },
  tableRow: {
    flexDirection: "row",
    borderBottomWidth: 1,
    borderBottomColor: colors.line,
    minHeight: 38
  },
  tableHeader: {
    minHeight: 30,
    backgroundColor: colors.page
  },
  tableCell: {
    paddingVertical: 7,
    paddingHorizontal: 6,
    fontSize: 7.6,
    lineHeight: 1.35,
    color: colors.text,
    borderRightWidth: 1,
    borderRightColor: colors.line
  },
  tableCellLast: {
    paddingVertical: 7,
    paddingHorizontal: 6,
    fontSize: 7.6,
    lineHeight: 1.35,
    color: colors.text
  },
  tableHeadText: {
    color: colors.green900,
    fontSize: 7.4,
    fontWeight: 700,
    textTransform: "uppercase",
    letterSpacing: 0.15
  },
  emptyTableCell: {
    width: "100%",
    padding: 12,
    fontSize: 9,
    lineHeight: 1.4,
    color: colors.muted
  },
  badge: {
    alignSelf: "flex-start",
    paddingVertical: 4,
    paddingHorizontal: 9,
    borderRadius: 999,
    borderWidth: 1,
    fontSize: 8,
    fontWeight: 700,
    textTransform: "uppercase",
    letterSpacing: 0.25
  },
  recommendation: {
    marginBottom: 9,
    paddingLeft: 10,
    borderLeftWidth: 2,
    borderLeftColor: colors.amber,
    fontSize: 10.5,
    lineHeight: 1.45,
    color: colors.text
  },
  chartBox: {
    marginTop: 12,
    borderWidth: 1,
    borderColor: colors.line,
    borderRadius: 10,
    padding: 12,
    backgroundColor: colors.page
  }
});

function textOrFallback(value?: string | number | null) {
  if (value === null || value === undefined || value === "") return "Dato no disponible";
  return String(value);
}

function formatDate(value?: string | null) {
  if (!value) return "Dato no disponible";
  return new Intl.DateTimeFormat("es-BO", { dateStyle: "medium" }).format(new Date(value));
}

function formatDateTime(value?: string | null) {
  if (!value) return "Dato no disponible";
  return new Intl.DateTimeFormat("es-BO", { dateStyle: "short", timeStyle: "short" }).format(new Date(value));
}

function formatNumber(value?: number | null, suffix = "", digits = 1) {
  if (value === null || value === undefined || Number.isNaN(value)) return "Dato no disponible";
  return `${value.toFixed(digits)}${suffix}`;
}

function slugStatus(data: AgroReportPdfData) {
  if (data.alerts.some((alert) => alert.severity === "critical")) return "Crítico";
  if (data.alerts.length || data.report.alerts_generated > 0) return "Alerta";
  return "Normal";
}

function statusColor(status: string) {
  if (status === "Crítico") return { color: colors.red, borderColor: "#FECACA", backgroundColor: "#FEF2F2" };
  if (status === "Alerta") return { color: "#92400E", borderColor: "#FDE68A", backgroundColor: "#FFFBEB" };
  return { color: colors.green700, borderColor: "#BBF7D0", backgroundColor: "#ECFDF5" };
}

function severityLabel(severity?: string) {
  if (!severity) return "No registrada";
  if (severity === "critical") return "Crítica";
  if (severity === "warning") return "Preventiva";
  if (severity === "technical") return "Técnica";
  return severity;
}

function alertVariable(alert: Alert) {
  const type = alert.alert_type.toLowerCase();
  if (type.includes("humidity")) return "Humedad ambiente";
  if (type.includes("temperature") || type.includes("environment")) return "Temperatura / ambiente";
  if (type.includes("battery")) return "Batería";
  return "Variable no registrada";
}

function recommendedAction(alert: Alert) {
  const type = alert.alert_type.toLowerCase();
  if (type.includes("humidity")) return "Revisar ventilación, aireación y posibles puntos de condensación.";
  if (type.includes("temperature") || type.includes("environment")) return "Inspeccionar físicamente el punto monitoreado y verificar acumulación térmica.";
  if (type.includes("battery")) return "Programar revisión técnica del nodo.";
  return "Evaluar condición operativa y registrar acción en bitácora.";
}

function pilotStatusLabel(status: string) {
  const labels: Record<string, string> = {
    "pendiente de instalacion": "Pendiente de instalacion",
    instalado: "Instalado",
    "en monitoreo": "En monitoreo",
    "con alerta activa": "Con alerta activa",
    "reporte generado": "Reporte generado",
    "listo para evaluacion": "Listo para evaluacion"
  };
  return labels[status] || status;
}

function logCategoryLabel(category?: string) {
  const labels: Record<string, string> = {
    installation: "Instalacion",
    maintenance: "Mantenimiento",
    corrective_action: "Accion correctiva",
    inspection: "Inspeccion",
    general: "Registro general"
  };
  return category ? labels[category] || category : "Registro operativo";
}

function executiveSummary(data: AgroReportPdfData) {
  const status = slugStatus(data);
  if (!data.report.reading_count) {
    return "No se cuenta con evidencia suficiente para emitir una conclusión técnica del periodo. Se recomienda validar conectividad del dispositivo y continuidad de lecturas.";
  }
  if (status === "Crítico") {
    return "Durante el periodo analizado se identificaron condiciones fuera de rango que requieren seguimiento operativo, inspección física y registro de acciones correctivas.";
  }
  if (status === "Alerta") {
    return "Durante el periodo analizado se identificaron condiciones preventivas que requieren observación operativa y seguimiento en bitácora.";
  }
  return "Durante el periodo analizado, las condiciones registradas se mantuvieron dentro de rangos operativos aceptables.";
}

function sensorConsultation(data: AgroReportPdfData) {
  const latest = data.readings[0];
  const critical = data.alerts.filter((alert) => alert.severity === "critical" && alert.is_active);
  if (critical.length) {
    return `Asistente operativo basado en reglas del sistema: se detectan ${critical.length} alerta(s) crítica(s) activa(s). Priorizar intervención, inspección física y registro de acción correctiva.`;
  }
  if (!latest) {
    return "Asistente operativo basado en reglas del sistema: no hay lecturas recientes disponibles para emitir una recomendación técnica.";
  }
  if (latest.battery_voltage < 3.5) {
    return "Asistente operativo basado en reglas del sistema: el nodo reporta batería baja. Programar revisión técnica antes de depender del monitoreo continuo.";
  }
  if (latest.ambient_humidity > 75 || latest.grain_temperature > 32) {
    return "Asistente operativo basado en reglas del sistema: existen condiciones preventivas. Revisar humedad, temperatura y evolución del silo durante las próximas horas.";
  }
  return "Asistente operativo basado en reglas del sistema: el sensor se mantiene estable con la información disponible. Mantener rutina de revisión y bitácora.";
}

function buildRecommendations(data: AgroReportPdfData) {
  const alerts = data.alerts;
  const recommendations: string[] = [];

  if (!data.report.reading_count) {
    return ["No se cuenta con evidencia suficiente para emitir conclusión técnica."];
  }
  if (alerts.some((alert) => alert.severity === "critical")) {
    recommendations.push("Priorizar intervención operativa y documentar acción correctiva.");
  }
  if (alerts.some((alert) => alert.alert_type.toLowerCase().includes("humidity"))) {
    recommendations.push("Revisar ventilación, aireación y posibles puntos de condensación.");
  }
  if (alerts.some((alert) => alert.alert_type.toLowerCase().includes("temperature") || alert.alert_type.toLowerCase().includes("environment"))) {
    recommendations.push("Inspeccionar físicamente el punto monitoreado y verificar acumulación térmica.");
  }
  if (alerts.some((alert) => alert.alert_type.toLowerCase().includes("battery"))) {
    recommendations.push("Programar revisión técnica del nodo.");
  }
  if (!recommendations.length) {
    recommendations.push("Operación estable durante el periodo analizado con la información disponible.");
    recommendations.push("Mantener monitoreo semanal, bitácora operativa y revisión periódica de umbrales.");
  }
  return recommendations;
}

function isMostlyUppercase(text?: string | null) {
  if (!text) return false;
  const letters = text.match(/[A-Za-zÁÉÍÓÚÜÑáéíóúüñ]/g)?.join("") ?? "";
  return letters.length > 8 && letters === letters.toLocaleUpperCase("es-BO");
}

function hasInformalTone(log: OperationalLog) {
  const combined = `${log.action_taken} ${log.notes || ""}`;
  return isMostlyUppercase(combined) || /\b(xd|jaja|jeje|nose|no se|urgente+|okey)\b/i.test(combined) || /!{2,}|\?{2,}/.test(combined);
}

function normalizeOperatorText(value?: string | null) {
  if (!value) return "Dato no disponible";
  if (!isMostlyUppercase(value)) return value;
  const lower = value.toLocaleLowerCase("es-BO");
  return lower.charAt(0).toLocaleUpperCase("es-BO") + lower.slice(1);
}

function CircuitPattern() {
  return (
    <Svg style={styles.circuitLayer} viewBox="0 0 595 842">
      <Path d="M465 0 L540 75 L540 163" stroke="#C9DAD2" strokeWidth={0.8} fill="none" />
      <Path d="M524 0 L574 50 L574 250" stroke="#E0E8E4" strokeWidth={0.7} fill="none" />
      <Path d="M30 842 L30 738 L77 691" stroke="#C9DAD2" strokeWidth={0.8} fill="none" />
      <Path d="M0 61 L55 61 L88 29" stroke="#DCE8E2" strokeWidth={0.8} fill="none" />
      <Path d="M414 694 L518 590 L518 482" stroke="#DCE8E2" strokeWidth={0.7} fill="none" />
      <Path d="M470 760 L540 690 L540 620" stroke="#F1DCA3" strokeWidth={0.8} fill="none" />
      <Circle cx={540} cy={163} r={2.7} fill={colors.amber} />
      <Circle cx={574} cy={250} r={2.4} fill="#FFFFFF" stroke={colors.green800} strokeWidth={0.8} />
      <Circle cx={30} cy={738} r={2.7} fill={colors.green800} />
      <Circle cx={88} cy={29} r={2.7} fill={colors.green800} />
      <Circle cx={518} cy={482} r={2.7} fill="#FFFFFF" stroke={colors.amber} strokeWidth={0.9} />
      <Line x1={52} y1={790} x2={545} y2={790} stroke={colors.green900} strokeWidth={0.8} />
      <Line x1={52} y1={792} x2={545} y2={792} stroke={colors.amber} strokeWidth={0.45} />
    </Svg>
  );
}

function BrandLockup({ data, compact = false }: { data: AgroReportPdfData; compact?: boolean }) {
  return (
    <View style={styles.fallbackBrand}>
      {data.shieldUrl ? <Image src={data.shieldUrl} style={[styles.brandShield, compact ? { width: 38, height: 38 } : { width: 68, height: 68 }]} /> : null}
      <View>
        <Text style={[styles.brandName, compact ? { fontSize: 18 } : { fontSize: 30 }]}>AgroEscudo</Text>
        <Text style={styles.brandTag}>Datos que protegen. Decisiones que transforman.</Text>
      </View>
    </View>
  );
}

function ReportHeader({ data, title }: { data: AgroReportPdfData; title: string }) {
  return (
    <View style={styles.header} fixed>
      <BrandLockup data={data} compact />
      <View style={{ textAlign: "right" }}>
        <Text style={styles.headerTitle}>{title}</Text>
        <Text style={styles.headerMeta}>Monitoreo IoT, trazabilidad y gestión de riesgos</Text>
      </View>
    </View>
  );
}

function ReportFooter({ page }: { page: string }) {
  return (
    <View style={styles.footer} fixed>
      <Text>AgroEscudo / Evidencia operativa postcosecha</Text>
      <Text>{page}</Text>
    </View>
  );
}

function MetricCard({ label, value }: { label: string; value: string }) {
  return (
    <View style={styles.kpiCard}>
      <Text style={styles.kpiLabel}>{label}</Text>
      <Text style={styles.kpiValue}>{value}</Text>
    </View>
  );
}

function StatusBadge({ status }: { status: string }) {
  return <Text style={[styles.badge, statusColor(status)]}>{status}</Text>;
}

function MiniTrendChart({ readings, metric, color, label }: { readings: Reading[]; metric: "grain_temperature" | "ambient_humidity"; color: string; label: string }) {
  const series = readings
    .slice()
    .reverse()
    .slice(-16)
    .map((reading) => reading[metric]);

  if (!series.length) {
    return (
      <View style={styles.chartBox}>
        <Text style={styles.kpiLabel}>{label}</Text>
        <Text style={[styles.bodyText, { marginTop: 12 }]}>No hay datos suficientes para graficar este periodo.</Text>
      </View>
    );
  }

  const max = Math.max(...series);
  const min = Math.min(...series);
  const range = Math.max(max - min, 1);
  const width = 220;
  const height = 82;
  const points = series
    .map((value, index) => {
      const x = series.length === 1 ? 0 : (index / (series.length - 1)) * width;
      const y = height - ((value - min) / range) * height;
      return `${x.toFixed(1)},${y.toFixed(1)}`;
    })
    .join(" ");

  return (
    <View style={styles.chartBox}>
      <View style={{ flexDirection: "row", justifyContent: "space-between", marginBottom: 8 }}>
        <Text style={styles.kpiLabel}>{label}</Text>
        <Text style={[styles.kpiLabel, { color }]}>{formatNumber(max, metric === "ambient_humidity" ? "%" : " C")}</Text>
      </View>
      <Svg viewBox={`0 0 ${width} ${height}`} style={{ width: "100%", height }}>
        <Line x1={0} y1={height - 1} x2={width} y2={height - 1} stroke="#CBD5E1" strokeWidth={1} />
        <Line x1={0} y1={height / 2} x2={width} y2={height / 2} stroke="#E5E7EB" strokeWidth={0.8} />
        <Polyline points={points} fill="none" stroke={color} strokeWidth={2.3} />
        {series.map((value, index) => {
          const x = series.length === 1 ? 0 : (index / (series.length - 1)) * width;
          const y = height - ((value - min) / range) * height;
          return <Circle key={`${label}-${index}`} cx={x} cy={y} r={2.4} fill="#FFFFFF" stroke={color} strokeWidth={1.2} />;
        })}
      </Svg>
    </View>
  );
}

function DataTable({ columns, rows }: { columns: Array<{ label: string; width: string }>; rows: string[][] }) {
  return (
    <View style={styles.table}>
      <View style={[styles.tableRow, styles.tableHeader]}>
        {columns.map((column, index) => (
          <Text key={column.label} style={[index === columns.length - 1 ? styles.tableCellLast : styles.tableCell, styles.tableHeadText, { width: column.width }]}>
            {column.label}
          </Text>
        ))}
      </View>
      {!rows.length ? (
        <View style={[styles.tableRow, { borderBottomWidth: 0 }]}>
          <Text style={styles.emptyTableCell}>No registrado durante el periodo.</Text>
        </View>
      ) : rows.map((row, rowIndex) => (
        <View key={`row-${rowIndex}`} style={[styles.tableRow, rowIndex === rows.length - 1 ? { borderBottomWidth: 0 } : {}]}>
          {columns.map((column, index) => (
            <Text key={`${column.label}-${rowIndex}`} style={[index === columns.length - 1 ? styles.tableCellLast : styles.tableCell, { width: column.width }]}>
              {row[index] || "Dato no disponible"}
            </Text>
          ))}
        </View>
      ))}
    </View>
  );
}

export function AgroReportDocument({ data }: { data: AgroReportPdfData }) {
  const status = slugStatus(data);
  const metrics = [
    ["Temperatura máxima de grano", formatNumber(data.report.max_grain_temperature, " C"), "C", data.report.max_grain_temperature ? "Vigilar evolución térmica." : "Dato no disponible"],
    ["Humedad ambiente máxima", formatNumber(data.report.max_ambient_humidity, "%"), "%", data.report.max_ambient_humidity ? "Revisar contra umbral configurado." : "Dato no disponible"],
    ["Número de lecturas", String(data.report.reading_count), "lecturas", "Volumen de evidencia del periodo."],
    ["Alertas generadas", String(data.report.alerts_generated), "alertas", data.report.alerts_generated ? "Requiere seguimiento." : "Sin eventos reportados."],
    ["Alertas resueltas", String(data.report.alerts_resolved), "alertas", "Cierre operativo documentado."],
    ["Horas fuera de rango", `${data.report.approximate_hours_out_of_range} h`, "horas", "Exposición aproximada al riesgo."],
    ["Acciones registradas", String(data.logs.length || data.report.operational_actions.length), "acciones", "Trazabilidad operativa."],
    ["Checklist instalacion", String(data.report.installation_count), "registros", "Evidencia de puesta en marcha."],
    ["Mantenimientos", String(data.report.maintenance_count), "registros", "Seguimiento tecnico documentado."]
  ];
  const alertRows = data.alerts.map((alert) => [
    formatDateTime(alert.created_at),
    `${alert.title}\n${alertVariable(alert)}`,
    severityLabel(alert.severity),
    alert.is_active ? "Activa" : "Resuelta",
    recommendedAction(alert)
  ]);
  const actionSource = data.report.operational_actions.length ? data.report.operational_actions : data.logs;
  const logRows = actionSource.map((log) => {
    const informal = hasInformalTone(log);
    const action = normalizeOperatorText(log.action_taken);
    const notes = log.notes ? `Notas: ${normalizeOperatorText(log.notes)}` : "Notas: No registradas.";
    const reviewNote = informal ? "\nNota: Registro ingresado por operador. Validar redacción antes de entregar a cliente externo." : "";
    return [
      formatDateTime(log.timestamp),
      log.operator_name || "Dato no disponible",
      `${logCategoryLabel(log.category)}\n${action}\n${notes}${reviewNote}`,
      log.alert_id ? `#${log.alert_id}` : "Sin alerta"
    ];
  });
  const recommendations = buildRecommendations(data);

  return (
    <Document title={`AgroEscudo - ${data.report.storage_unit_name}`} author="AgroEscudo">
      <Page size="A4" style={styles.cover}>
        <CircuitPattern />
        <View style={styles.coverFrame}>
          <View style={styles.coverTop}>
            <BrandLockup data={data} />
            <View style={{ alignItems: "flex-end" }}>
              <Text style={styles.eyebrow}>Reporte técnico</Text>
              <Text style={[styles.headerMeta, { marginTop: 6 }]}>Agri-tech IoT / Postcosecha</Text>
            </View>
          </View>
          <Text style={styles.coverKicker}>Monitoreo postcosecha</Text>
          <Text style={styles.coverTitle}>Reporte técnico de monitoreo postcosecha</Text>
          <Text style={styles.coverSubtitle}>Monitoreo IoT, trazabilidad operativa y gestión de riesgos para silos, galpones y centros de acopio.</Text>
          <View style={styles.coverMetaGrid}>
            <View style={styles.coverMetaCard}>
              <Text style={styles.metaLabel}>Cliente / institución</Text>
              <Text style={styles.metaValue}>{textOrFallback(data.report.company_name)}</Text>
            </View>
            <View style={styles.coverMetaCard}>
              <Text style={styles.metaLabel}>Sitio</Text>
              <Text style={styles.metaValue}>{textOrFallback(data.report.site_name)}</Text>
            </View>
            <View style={styles.coverMetaCard}>
              <Text style={styles.metaLabel}>Silo / galpón</Text>
              <Text style={styles.metaValue}>{textOrFallback(data.report.storage_unit_name)}</Text>
            </View>
            <View style={styles.coverMetaCard}>
              <Text style={styles.metaLabel}>Periodo analizado</Text>
              <Text style={styles.metaValue}>{formatDate(data.report.date_from)} - {formatDate(data.report.date_to)}</Text>
            </View>
            <View style={styles.coverMetaCard}>
              <Text style={styles.metaLabel}>Preparado por</Text>
              <Text style={styles.metaValue}>AgroEscudo / Versión MVP-1.0</Text>
            </View>
            <View style={styles.coverMetaCard}>
              <Text style={styles.metaLabel}>Estado general</Text>
              <View style={{ marginTop: 7 }}>
                <StatusBadge status={status} />
              </View>
            </View>
          </View>
          <View style={[styles.tintedCard, { marginTop: 12, borderLeftWidth: 4, borderLeftColor: colors.green700 }]}>
            <Text style={styles.metaLabel}>Estado del piloto</Text>
            <Text style={[styles.metaValue, { marginTop: 6 }]}>{pilotStatusLabel(data.report.pilot_status)}</Text>
          </View>
          <View style={[styles.tintedCard, { marginTop: 34, borderLeftWidth: 4, borderLeftColor: colors.amber }]}>
            <Text style={styles.metaLabel}>Resumen ejecutivo</Text>
            <Text style={[styles.bodyText, { marginTop: 8 }]}>{executiveSummary(data)}</Text>
          </View>
        </View>
        <View style={styles.footer} fixed>
          <Text>www.agroescudo.com / hola@agroescudo.com</Text>
          <Text>Portada</Text>
        </View>
      </Page>

      <Page size="A4" style={styles.page}>
        <CircuitPattern />
        <ReportHeader data={data} title="Resumen ejecutivo" />
        <Text style={styles.sectionTitle}>Resumen ejecutivo</Text>
        <View style={styles.accent} />
        <View style={styles.tintedCard}>
          <Text style={styles.bodyText}>{executiveSummary(data)}</Text>
        </View>
        <View style={[styles.card, { marginTop: 12, borderLeftWidth: 4, borderLeftColor: colors.amber }]}>
          <Text style={[styles.kpiLabel, { color: colors.green900 }]}>Consulta operativa del sensor</Text>
          <Text style={[styles.bodyText, { marginTop: 8 }]}>{sensorConsultation(data)}</Text>
        </View>
        <View style={[styles.tintedCard, { marginTop: 12, flexDirection: "row", justifyContent: "space-between" }]}>
          <View>
            <Text style={styles.kpiLabel}>Estado del piloto</Text>
            <Text style={[styles.metaValue, { marginTop: 5 }]}>{pilotStatusLabel(data.report.pilot_status)}</Text>
          </View>
          <View>
            <Text style={styles.kpiLabel}>Checklist instalacion</Text>
            <Text style={[styles.metaValue, { marginTop: 5 }]}>{data.report.installation_count}</Text>
          </View>
          <View>
            <Text style={styles.kpiLabel}>Mantenimientos</Text>
            <Text style={[styles.metaValue, { marginTop: 5 }]}>{data.report.maintenance_count}</Text>
          </View>
        </View>
        <View style={styles.kpiGrid}>
          <MetricCard label="Lecturas" value={String(data.report.reading_count)} />
          <MetricCard label="Temp. máxima" value={formatNumber(data.report.max_grain_temperature, " C")} />
          <MetricCard label="Humedad máxima" value={formatNumber(data.report.max_ambient_humidity, "%")} />
          <MetricCard label="Alertas generadas" value={String(data.report.alerts_generated)} />
          <MetricCard label="Alertas resueltas" value={String(data.report.alerts_resolved)} />
          <MetricCard label="Horas fuera rango" value={`${data.report.approximate_hours_out_of_range} h`} />
        </View>
        <View style={{ marginTop: 20 }}>
          <Text style={styles.sectionTitle}>Gráficas técnicas del periodo</Text>
          <View style={styles.accent} />
          <View style={styles.twoColumn}>
            <View style={styles.column}>
              <MiniTrendChart readings={data.readings} metric="grain_temperature" color={colors.green700} label="Temperatura de grano" />
            </View>
            <View style={styles.column}>
              <MiniTrendChart readings={data.readings} metric="ambient_humidity" color={colors.amber} label="Humedad ambiente" />
            </View>
          </View>
          <View style={[styles.tintedCard, { marginTop: 12 }]}>
            <Text style={styles.kpiLabel}>Seguimiento del piloto</Text>
            <Text style={[styles.bodyText, { marginTop: 7 }]}>Estado: {pilotStatusLabel(data.report.pilot_status)}</Text>
            <Text style={styles.bodyText}>Checklist de instalacion: {data.report.installation_count}</Text>
            <Text style={styles.bodyText}>Mantenimientos registrados: {data.report.maintenance_count}</Text>
            <Text style={styles.bodyText}>Ultimo reporte generado: {formatDateTime(data.report.last_report_generated_at)}</Text>
          </View>
        </View>
        <ReportFooter page="Pág. 1" />
      </Page>

      <Page size="A4" style={styles.page}>
        <CircuitPattern />
        <ReportHeader data={data} title="Métricas principales" />
        <Text style={styles.sectionTitle}>Métricas principales</Text>
        <View style={styles.accent} />
        <DataTable
          columns={[
            { label: "Métrica", width: "32%" },
            { label: "Valor", width: "17%" },
            { label: "Unidad", width: "14%" },
            { label: "Interpretación", width: "37%" }
          ]}
          rows={metrics}
        />
        <View style={{ marginTop: 20 }}>
          <Text style={styles.sectionTitle}>Contexto del activo monitoreado</Text>
          <View style={styles.accent} />
          <View style={styles.twoColumn}>
            <View style={styles.card}>
              <Text style={styles.kpiLabel}>Unidad</Text>
              <Text style={[styles.kpiValue, { fontSize: 14 }]}>{data.storageUnit.name}</Text>
              <Text style={[styles.bodyText, { marginTop: 8 }]}>Tipo: {textOrFallback(data.storageUnit.unit_type)}</Text>
              <Text style={styles.bodyText}>Capacidad: {data.storageUnit.capacity_tons ? `${data.storageUnit.capacity_tons} t` : "Dato no disponible"}</Text>
            </View>
            <View style={styles.card}>
              <Text style={styles.kpiLabel}>Dispositivo</Text>
              <Text style={[styles.kpiValue, { fontSize: 14 }]}>{data.device?.external_id || "Dato no disponible"}</Text>
              <Text style={[styles.bodyText, { marginTop: 8 }]}>Nombre: {data.device?.name || "Dato no disponible"}</Text>
              <Text style={styles.bodyText}>Estado: {data.device?.is_active ? "Activo" : "Dato no disponible"}</Text>
            </View>
          </View>
        </View>
        <ReportFooter page="Pág. 2" />
      </Page>

      <Page size="A4" style={styles.page}>
        <CircuitPattern />
        <ReportHeader data={data} title="Alertas y eventos" />
        <Text style={styles.sectionTitle}>Alertas generadas</Text>
        <View style={styles.accent} />
        <DataTable
          columns={[
            { label: "Fecha", width: "16%" },
            { label: "Evento", width: "30%" },
            { label: "Nivel", width: "12%" },
            { label: "Estado", width: "12%" },
            { label: "Recomendación", width: "30%" }
          ]}
          rows={alertRows}
        />
        <ReportFooter page="Pág. 3" />
      </Page>

      <Page size="A4" style={styles.page}>
        <CircuitPattern />
        <ReportHeader data={data} title="Bitácora operativa" />
        <Text style={styles.sectionTitle}>Bitácora de acciones</Text>
        <View style={styles.accent} />
        <DataTable
          columns={[
            { label: "Fecha", width: "17%" },
            { label: "Operador", width: "18%" },
            { label: "Registro operativo", width: "50%" },
            { label: "Alerta", width: "15%" }
          ]}
          rows={logRows}
        />
        <Text style={styles.noteText}>Las entradas de bitácora se muestran como evidencia registrada por el operador. Antes de entregar el reporte a un cliente externo, validar redacción y cierre operativo.</Text>
        <View style={{ marginTop: 20 }}>
          <Text style={styles.sectionTitle}>Conclusiones y recomendaciones</Text>
          <View style={styles.accent} />
          <View style={styles.card}>
            {recommendations.map((recommendation, index) => (
              <Text key={`recommendation-${index}`} style={styles.recommendation}>{recommendation}</Text>
            ))}
          </View>
        </View>
        <ReportFooter page="Pág. 4" />
      </Page>
    </Document>
  );
}
