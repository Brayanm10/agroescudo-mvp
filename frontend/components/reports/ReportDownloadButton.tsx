"use client";

import { Download, FileText } from "lucide-react";
import { useState } from "react";
import { getWeeklyReportPdf } from "@/lib/api";
import type { Alert, Device, OperationalLog, Reading, StorageUnit, WeeklyReport } from "@/lib/types";

type Props = {
  token: string;
  storageUnit: StorageUnit | null;
  device?: Device;
  readings: Reading[];
  alerts: Alert[];
  logs: OperationalLog[];
  report?: WeeklyReport | null;
  className?: string;
  compact?: boolean;
};

function safeFilePart(value: string) {
  return value
    .normalize("NFD")
    .replace(/[\u0300-\u036f]/g, "")
    .toLowerCase()
    .replace(/[^a-z0-9]+/g, "-")
    .replace(/^-+|-+$/g, "")
    .slice(0, 60) || "storage-unit";
}

function fileDate() {
  return new Date().toISOString().slice(0, 10);
}

function triggerDownload(blob: Blob, fileName: string) {
  const url = URL.createObjectURL(blob);
  const anchor = document.createElement("a");
  anchor.href = url;
  anchor.download = fileName;
  document.body.appendChild(anchor);
  anchor.click();
  anchor.remove();
  URL.revokeObjectURL(url);
}

export function ReportDownloadButton({
  token,
  storageUnit,
  device,
  readings,
  alerts,
  logs,
  report,
  className = "",
  compact = false
}: Props) {
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function downloadReport() {
    if (!storageUnit || loading) return;
    setLoading(true);
    setError(null);
    try {
      const blob = await getWeeklyReportPdf(token, storageUnit.id);
      triggerDownload(blob, `agroescudo-reporte-${safeFilePart(storageUnit.name)}-${fileDate()}.pdf`);
    } catch (err) {
      setError(err instanceof Error ? err.message : "No se pudo generar el PDF.");
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className={compact ? "inline-flex flex-col items-start gap-2" : "flex flex-col items-start gap-2"}>
      <button
        type="button"
        onClick={downloadReport}
        disabled={!storageUnit || loading}
        className={`btn-primary ${compact ? "px-3 py-2 text-xs" : ""} ${className}`}
      >
        {loading ? <FileText className="mr-2 animate-pulse" size={16} aria-hidden="true" /> : <Download className="mr-2" size={16} aria-hidden="true" />}
        {loading ? "Generando PDF..." : "Descargar reporte PDF"}
      </button>
      {error ? <p className="max-w-sm rounded-lg border border-red-200 bg-red-50 px-3 py-2 text-xs font-semibold text-red-800">{error}</p> : null}
    </div>
  );
}
