import { Badge } from "@/components/ui/badge";

interface DataflowHealthBadgeProps {
  status: "excellent" | "good" | "poor" | "critical";
}

const healthConfig = {
  excellent: {
    label: "Excellent",
    className: "bg-green-600 hover:bg-green-700",
  },
  good: {
    label: "Good",
    className: "bg-primary hover:bg-primary/90",
  },
  poor: {
    label: "Poor",
    className: "bg-yellow-600 hover:bg-yellow-700",
  },
  critical: {
    label: "Critical",
    className: "bg-red-600 hover:bg-red-700",
  },
};

export function DataflowHealthBadge({ status }: DataflowHealthBadgeProps) {
  const config = healthConfig[status];

  return (
    <Badge variant="default" className={config.className}>
      {config.label}
    </Badge>
  );
}
