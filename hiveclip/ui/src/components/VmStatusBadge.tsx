import { Badge } from "./ui/badge";

const statusConfig: Record<string, { label: string; variant: "default" | "secondary" | "destructive" | "outline" }> = {
  provisioning: { label: "Provisioning", variant: "outline" },
  running: { label: "Running", variant: "default" },
  stopped: { label: "Stopped", variant: "secondary" },
  error: { label: "Error", variant: "destructive" },
};

export function VmStatusBadge({ status }: { status: string }) {
  const config = statusConfig[status] || { label: status, variant: "outline" as const };
  return <Badge variant={config.variant}>{config.label}</Badge>;
}
