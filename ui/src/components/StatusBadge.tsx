import { Badge } from "@/components/ui/badge"
import type { JobStatus } from "@/types"

interface StatusBadgeProps {
  status: JobStatus
}

const statusConfig: Record<JobStatus, { label: string; variant: "default" | "secondary" | "destructive" | "outline" | "success" | "warning" }> = {
  pending: { label: "Pending", variant: "secondary" },
  running: { label: "Running", variant: "warning" },
  succeeded: { label: "Succeeded", variant: "success" },
  failed: { label: "Failed", variant: "destructive" },
  cancelled: { label: "Cancelled", variant: "outline" },
}

export function StatusBadge({ status }: StatusBadgeProps) {
  const config = statusConfig[status] || { label: status, variant: "secondary" as const }

  return (
    <Badge variant={config.variant}>
      {config.label}
    </Badge>
  )
}
