import type { RiskStatus } from "@/lib/types";
import { statusLabel } from "@/lib/format";

type Props = {
  status: RiskStatus;
};

const styles: Record<RiskStatus, string> = {
  normal: "border-emerald-200 bg-emerald-50 text-emerald-800 shadow-[inset_0_1px_0_rgba(255,255,255,0.75)]",
  warning: "border-amber-200 bg-amber-50 text-amber-800 shadow-[inset_0_1px_0_rgba(255,255,255,0.75)]",
  critical: "border-red-200 bg-red-50 text-red-800 shadow-[inset_0_1px_0_rgba(255,255,255,0.75)]",
  technical: "border-slate-200 bg-slate-100 text-slate-700 shadow-[inset_0_1px_0_rgba(255,255,255,0.75)]"
};

export function StatusBadge({ status }: Props) {
  return (
    <span className={`inline-flex items-center gap-1.5 rounded-full border px-2.5 py-1 text-[11px] font-bold uppercase tracking-[0.1em] ${styles[status]}`}>
      <span className="h-1.5 w-1.5 rounded-full bg-current" />
      {statusLabel(status)}
    </span>
  );
}
