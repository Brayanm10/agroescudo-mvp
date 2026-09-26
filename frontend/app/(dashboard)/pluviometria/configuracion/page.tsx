"use client";

import { AuthenticatedAppShell } from "@/components/auth/AuthenticatedAppShell";
import { PluviometryConfigurationView } from "@/components/pluviometry/PluviometryConfigurationView";

export default function PluviometryConfigurationPage() {
  return <AuthenticatedAppShell>{({ token, user }) => <PluviometryConfigurationView token={token} role={user.role} />}</AuthenticatedAppShell>;
}
