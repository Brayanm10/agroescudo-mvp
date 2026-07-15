"use client";

import { ChevronDown, KeyRound, LogOut, Settings2, UserCircle } from "lucide-react";
import type { LucideIcon } from "lucide-react";
import { useState } from "react";
import type { User, ViewKey } from "@/lib/types";

function roleLabel(role: string) {
  if (role === "admin") return "Admin AgroEscudo";
  if (role === "technician") return "Tecnico AgroEscudo";
  return "Cliente silo";
}

export function AccountMenu({
  user,
  onNavigate,
  onLogout
}: {
  user: User;
  onNavigate: (view: ViewKey) => void;
  onLogout: () => void;
}) {
  const [open, setOpen] = useState(false);

  function navigate(view: ViewKey) {
    setOpen(false);
    onNavigate(view);
  }

  return (
    <div className="relative">
      <button
        type="button"
        onClick={() => setOpen((value) => !value)}
        className="hidden min-w-[210px] items-center justify-between gap-3 rounded-xl border border-slate-200 bg-white px-3 py-2 text-left shadow-soft transition hover:border-emerald-200 hover:bg-emerald-50 sm:flex"
        aria-haspopup="menu"
        aria-expanded={open}
      >
        <span className="min-w-0">
          <span className="block truncate text-sm font-semibold text-slate-900">{user.full_name}</span>
          <span className="block truncate text-xs text-slate-500">{user.company?.name || user.email}</span>
          <span className="mt-1 block text-[10px] font-black uppercase tracking-[0.13em] text-emerald-700">{roleLabel(user.role)}</span>
        </span>
        <ChevronDown size={16} className="shrink-0 text-slate-400" aria-hidden="true" />
      </button>
      <button
        type="button"
        onClick={() => setOpen((value) => !value)}
        className="rounded-lg border border-slate-200 bg-white p-2.5 text-slate-600 shadow-soft transition hover:border-emerald-200 hover:bg-emerald-50 hover:text-emeraldDeep sm:hidden"
        aria-haspopup="menu"
        aria-expanded={open}
        title="Cuenta"
      >
        <UserCircle size={18} aria-hidden="true" />
      </button>
      {open ? (
        <div className="absolute right-0 z-30 mt-2 w-72 overflow-hidden rounded-2xl border border-slate-200 bg-white shadow-2xl" role="menu">
          <div className="border-b border-slate-100 p-4">
            <p className="truncate font-black text-slate-950">{user.full_name}</p>
            <p className="truncate text-sm text-slate-500">{user.email}</p>
          </div>
          <div className="p-2">
            <MenuButton icon={UserCircle} label="Mi perfil" onClick={() => navigate("profile")} />
            <MenuButton icon={KeyRound} label="Cambiar contrasena" onClick={() => navigate("changePassword")} />
            <MenuButton icon={Settings2} label="Preferencias" onClick={() => navigate("preferences")} />
          </div>
          <div className="border-t border-slate-100 p-2">
            <MenuButton icon={LogOut} label="Cerrar sesion" tone="danger" onClick={onLogout} />
          </div>
        </div>
      ) : null}
    </div>
  );
}

function MenuButton({
  icon: Icon,
  label,
  onClick,
  tone = "default"
}: {
  icon: LucideIcon;
  label: string;
  onClick: () => void;
  tone?: "default" | "danger";
}) {
  return (
    <button
      type="button"
      onClick={onClick}
      className={`flex w-full items-center gap-3 rounded-xl px-3 py-2 text-sm font-bold transition ${
        tone === "danger" ? "text-red-700 hover:bg-red-50" : "text-slate-700 hover:bg-emerald-50 hover:text-emeraldDeep"
      }`}
      role="menuitem"
    >
      <Icon size={17} aria-hidden="true" />
      {label}
    </button>
  );
}
