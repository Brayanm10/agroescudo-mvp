"use client";

import { AuthenticatedAppShell } from "@/components/auth/AuthenticatedAppShell";
import { PluviometryMapView } from "@/components/pluviometry/PluviometryMapView";

export default function PluviometryPage() {
  return (
    <AuthenticatedAppShell>
      {({ user }) => <PluviometryMapView role={user.role} />}
    </AuthenticatedAppShell>
  );
}
