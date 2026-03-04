import { Badge } from "@/components/ui/badge";

interface DataflowStatusBadgeProps {
  state: "enabled" | "disabled";
}

export function DataflowStatusBadge({ state }: DataflowStatusBadgeProps) {
  const variant = state === "enabled" ? "default" : "secondary";
  const displayText = state.charAt(0).toUpperCase() + state.slice(1);

  return (
    <Badge variant={variant} className={state === "enabled" ? "bg-green-600" : "bg-gray-400"}>
      {displayText}
    </Badge>
  );
}
