import type { LucideIcon } from "lucide-react";
import { Inbox } from "lucide-react";

type Props = {
  title: string;
  message: string;
  icon?: LucideIcon;
};

export function EmptyState({ title, message, icon: Icon = Inbox }: Props) {
  return (
    <div className="rounded-panel border border-dashed border-slate-300 bg-white/80 p-8 text-center shadow-soft">
      <div className="mx-auto flex h-12 w-12 items-center justify-center rounded-xl border border-slate-200 bg-slate-50 text-slate-400">
        <Icon size={24} aria-hidden="true" />
      </div>
      <p className="mt-3 text-sm font-semibold text-slate-900">{title}</p>
      <p className="mt-1 text-sm text-slate-500">{message}</p>
    </div>
  );
}
