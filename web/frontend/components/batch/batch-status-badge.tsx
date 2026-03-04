import { Badge } from "@/components/ui/badge";

interface BatchStatusBadgeProps {
  status: string;
}

export function BatchStatusBadge({ status }: BatchStatusBadgeProps) {
  const statusLower = status.toLowerCase();

  const variant = (() => {
    if (statusLower === "success") return "success";
    if (statusLower === "failed" || statusLower === "aborted") return "destructive";
    if (statusLower === "active" || statusLower === "processing") return "info";
    if (statusLower === "queued") return "warning";
    return "default";
  })();

  return (
    <Badge variant={variant}>
      {status.charAt(0).toUpperCase() + status.slice(1)}
    </Badge>
  );
}
