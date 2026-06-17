import type { LucideIcon } from "lucide-react";
import type { ReactNode } from "react";

type Props = {
  label: string;
  value: ReactNode;
  detail?: string;
  icon: LucideIcon;
  tone?: "neutral" | "emerald" | "amber" | "critical";
};

const tones = {
  neutral: "border-slate-200/80 bg-white text-slate-700 before:bg-slate-300",
  emerald: "border-emerald-200/80 bg-emerald-50 text-emerald-900 before:bg-emeraldTech",
  amber: "border-amber-200/80 bg-amber-50 text-amber-900 before:bg-amberValue",
  critical: "border-red-200/80 bg-red-50 text-red-900 before:bg-red-600"
};

export function StatCard({ label, value, detail, icon: Icon, tone = "neutral" }: Props) {
  return (
    <section className={`relative min-h-[148px] overflow-hidden rounded-panel border p-5 shadow-panel before:absolute before:left-0 before:top-0 before:h-1 before:w-full ${tones[tone]}`}>
      <div className="flex items-center justify-between gap-3">
        <div className="min-w-0">
          <p className="text-[11px] font-bold uppercase tracking-[0.14em] text-slate-500">{label}</p>
          <p className="mt-2 break-words text-2xl font-black tracking-tight text-slate-950">{value}</p>
        </div>
        <div className="flex h-11 w-11 shrink-0 items-center justify-center rounded-xl border border-white/70 bg-white/80 text-emeraldDeep shadow-soft">
          <Icon size={20} aria-hidden="true" />
        </div>
      </div>
      {detail ? <p className="mt-3 text-sm text-slate-600">{detail}</p> : null}
    </section>
  );
}
