"use client";

import { AlertTriangle, CheckCircle2, Circle, Loader2, XCircle } from "lucide-react";
import { cn } from "@/lib/utils";
import type { ChecklistItem, ChecklistStatus } from "@/lib/types/schema_wizard";

interface SchemaChecklistProps {
  items: ChecklistItem[];
  title?: string;
}

const STATUS_CONFIG: Record<
  ChecklistStatus,
  { icon: React.ReactNode; labelClass: string; bg: string }
> = {
  pending: {
    icon: <Circle className="h-4 w-4 text-muted-foreground" />,
    labelClass: "text-muted-foreground",
    bg: "",
  },
  analyzing: {
    icon: <Loader2 className="h-4 w-4 animate-spin text-blue-500" />,
    labelClass: "text-blue-700",
    bg: "bg-blue-50",
  },
  passed: {
    icon: <CheckCircle2 className="h-4 w-4 text-green-500" />,
    labelClass: "text-green-800",
    bg: "bg-green-50",
  },
  warning: {
    icon: <AlertTriangle className="h-4 w-4 text-yellow-500" />,
    labelClass: "text-yellow-800",
    bg: "bg-yellow-50",
  },
  failed: {
    icon: <XCircle className="h-4 w-4 text-red-500" />,
    labelClass: "text-red-800",
    bg: "bg-red-50",
  },
};

export function SchemaChecklist({ items, title = "검수 항목" }: SchemaChecklistProps) {
  return (
    <div className="rounded-lg border bg-white p-4 shadow-sm">
      <h3 className="mb-3 text-sm font-semibold text-gray-700">{title}</h3>
      <ul className="space-y-2">
        {items.map((item) => {
          const cfg = STATUS_CONFIG[item.status];
          return (
            <li
              key={item.id}
              className={cn(
                "flex items-start gap-2 rounded-md px-2 py-1.5 text-sm transition-colors",
                cfg.bg
              )}
            >
              <span className="mt-0.5 flex-shrink-0">{cfg.icon}</span>
              <div className="min-w-0 flex-1">
                <p className={cn("font-medium leading-snug", cfg.labelClass)}>
                  {item.label}
                </p>
                {item.detail && (
                  <p className="mt-0.5 text-xs text-muted-foreground">{item.detail}</p>
                )}
              </div>
            </li>
          );
        })}
        {items.length === 0 && (
          <li className="text-xs text-muted-foreground">분석 시작 전입니다.</li>
        )}
      </ul>

      {/* Summary badge row */}
      {items.length > 0 && (
        <div className="mt-3 flex gap-2 text-xs text-muted-foreground">
          {(["passed", "warning", "failed"] as ChecklistStatus[]).map((s) => {
            const count = items.filter((i) => i.status === s).length;
            if (count === 0) return null;
            const color =
              s === "passed" ? "text-green-600" : s === "warning" ? "text-yellow-600" : "text-red-600";
            const label = s === "passed" ? "통과" : s === "warning" ? "주의" : "실패";
            return (
              <span key={s} className={cn("font-medium", color)}>
                {label} {count}
              </span>
            );
          })}
        </div>
      )}
    </div>
  );
}
