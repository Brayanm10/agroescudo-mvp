import { notFound } from "next/navigation";
import { AuthenticatedAppShell } from "@/components/auth/AuthenticatedAppShell";
import { RainGaugeHistoryView } from "@/components/pluviometry/RainGaugeHistoryView";

export default async function RainGaugeDetailPage({ params }: { params: Promise<{ deviceId: string }> }) {
  const { deviceId: rawDeviceId } = await params;
  const deviceId = Number(rawDeviceId);
  if (!Number.isInteger(deviceId) || deviceId <= 0) notFound();
  return (
    <AuthenticatedAppShell>
      <RainGaugeHistoryView deviceId={deviceId} />
    </AuthenticatedAppShell>
  );
}
