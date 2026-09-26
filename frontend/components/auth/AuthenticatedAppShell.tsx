"use client";

import { useEffect } from "react";
import { useRouter } from "next/navigation";
import type { ReactNode } from "react";
import { AppLayout } from "@/components/AppLayout";
import { ErrorState } from "@/components/ErrorState";
import { LoadingState } from "@/components/LoadingState";
import { useAuthenticatedSession } from "@/hooks/useAuthenticatedSession";
import { getCurrentUser } from "@/lib/api";
import { allowedViewsForRole, canAccessPluviometry } from "@/lib/navigation";
import type { User, ViewKey } from "@/lib/types";

type ShellContext = { token: string; user: User };

export function AuthenticatedAppShell({ children }: { children: ReactNode | ((context: ShellContext) => ReactNode) }) {
  const router = useRouter();
  const { token, data: user, loading, error, refresh, logout } = useAuthenticatedSession(getCurrentUser);

  useEffect(() => {
    if (!loading && !token) router.replace("/");
  }, [loading, router, token]);

  if (loading || !token) {
    return <main className="min-h-screen bg-field p-6"><LoadingState label="Validando sesión" /></main>;
  }

  if (!user) {
    return (
      <main className="min-h-screen bg-field p-6">
        <ErrorState message={error || "No se pudo validar la sesión."} onRetry={refresh} />
      </main>
    );
  }

  if (!canAccessPluviometry(user.role, user.features)) {
    return (
      <main className="min-h-screen bg-field p-6">
        <ErrorState message={user.features?.includes("PLUVIOMETRY") ? "Tu rol no tiene acceso a Pluviometría." : "Módulo no habilitado para tu empresa."} onRetry={() => router.replace("/")} />
      </main>
    );
  }

  function navigate(view: ViewKey) {
    if (view === "pluviometry") return;
    router.push(view === "dashboard" ? "/" : `/?view=${view}`);
  }

  function handleLogout() {
    logout();
    router.replace("/");
  }

  return (
    <AppLayout
      current="pluviometry"
      onChange={navigate}
      allowedViews={allowedViewsForRole(user.role, user.features)}
      user={user}
      onLogout={handleLogout}
      onRefresh={refresh}
    >
      {error ? <div className="mb-4"><ErrorState message={error} onRetry={refresh} /></div> : null}
      {typeof children === "function" ? children({ token, user }) : children}
    </AppLayout>
  );
}
