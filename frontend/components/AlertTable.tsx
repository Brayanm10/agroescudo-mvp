import { CheckCircle2, ShieldCheck } from "lucide-react";
import { formatDateTime } from "@/lib/format";
import type { Alert, Device, StorageUnit } from "@/lib/types";
import { StatusBadge } from "./StatusBadge";

function severityToStatus(severity: string) {
  if (severity === "critical") return "critical" as const;
  if (severity === "warning") return "warning" as const;
  if (severity === "technical") return "technical" as const;
  return "normal" as const;
}

export function AlertTable({
  alerts,
  devices,
  storageUnits,
  onAcknowledge,
  onResolve,
  busyAlertId
}: {
  alerts: Alert[];
  devices: Device[];
  storageUnits: StorageUnit[];
  onAcknowledge?: (alert: Alert) => void;
  onResolve?: (alert: Alert) => void;
  busyAlertId?: number | null;
}) {
  return (
    <div className="overflow-hidden rounded-panel border border-slate-200/80 bg-white shadow-panel">
      <div className="overflow-x-auto">
        <table className="min-w-full divide-y divide-slate-200 text-sm">
          <thead className="table-head">
            <tr>
              <th className="px-5 py-3.5">Estado</th>
              <th className="px-5 py-3.5">Alerta</th>
              <th className="px-5 py-3.5">Unidad</th>
              <th className="px-5 py-3.5">Device</th>
              <th className="px-5 py-3.5">Fecha</th>
              <th className="px-5 py-3.5 text-right">Acciones</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-slate-100">
            {alerts.map((alert) => {
              const device = devices.find((item) => item.id === alert.device_id);
              const unit = storageUnits.find((item) => item.id === alert.storage_unit_id);
              const busy = busyAlertId === alert.id;
              return (
                <tr
                  key={alert.id}
                  className={`transition hover:bg-slate-50 ${alert.severity === "critical" && alert.is_active ? "bg-red-50/80 shadow-[inset_4px_0_0_#dc2626]" : ""}`}
                >
                  <td className="px-5 py-4">
                    <StatusBadge status={severityToStatus(alert.severity)} />
                  </td>
                  <td className="px-5 py-4">
                    <p className="font-bold text-slate-950">{alert.title}</p>
                    <p className="mt-1 max-w-xl text-xs leading-5 text-slate-500">{alert.message}</p>
                  </td>
                  <td className="px-5 py-4 font-semibold text-slate-700">{unit?.name || `#${alert.storage_unit_id}`}</td>
                  <td className="px-5 py-4 text-slate-700">{device?.external_id || `#${alert.device_id}`}</td>
                  <td className="px-5 py-4 text-slate-600">{formatDateTime(alert.created_at)}</td>
                  <td className="px-5 py-4">
                    <div className="flex justify-end gap-2">
                      {onAcknowledge ? (
                        <button
                          type="button"
                          disabled={busy || !!alert.acknowledged_at}
                          onClick={() => onAcknowledge(alert)}
                          className="btn-secondary px-2.5 py-1.5 text-xs"
                        >
                          <CheckCircle2 className="mr-1 inline" size={14} aria-hidden="true" />
                          Ack
                        </button>
                      ) : null}
                      {onResolve ? (
                        <button
                          type="button"
                          disabled={busy || !alert.is_active}
                          onClick={() => onResolve(alert)}
                          className="btn-primary px-2.5 py-1.5 text-xs"
                        >
                          <ShieldCheck className="mr-1 inline" size={14} aria-hidden="true" />
                          Resolve
                        </button>
                      ) : null}
                    </div>
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>
    </div>
  );
}
