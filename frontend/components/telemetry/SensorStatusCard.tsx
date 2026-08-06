import { AlertTriangle, CheckCircle2, Radio } from "lucide-react";
import type { DashboardMetric, SensorChannel } from "@/lib/types";

export function SensorStatusCard({
  channel,
  metric
}: {
  channel: SensorChannel;
  metric: DashboardMetric;
}) {
  const pendingCalibration = channel.calibration_required && metric.is_derived;
  const Icon = pendingCalibration ? AlertTriangle : channel.status === "ACTIVE" ? CheckCircle2 : Radio;
  return (
    <div className="rounded-lg border border-dashed border-slate-300 bg-white p-5">
      <div className="flex items-center gap-3">
        <span className="grid h-10 w-10 place-items-center rounded-lg bg-emerald-50 text-emerald-800">
          <Icon size={18} />
        </span>
        <div>
          <p className="font-bold text-slate-950">{metric.display_name_override || metric.display_name}</p>
          <p className="text-xs font-semibold text-slate-500">{channel.display_name} / {channel.status}</p>
        </div>
      </div>
      <p className="mt-3 text-sm leading-6 text-slate-600">
        {pendingCalibration
          ? "La métrica derivada aparecerá después de configurar la calibración y recibir una lectura válida."
          : "Canal configurado sin lecturas válidas en el periodo seleccionado."}
      </p>
    </div>
  );
}
