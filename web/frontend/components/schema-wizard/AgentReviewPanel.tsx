"use client";

import { AlertCircle, Bot, ChevronDown, ChevronUp } from "lucide-react";
import { useState } from "react";
import { Alert, AlertDescription } from "@/components/ui/alert";
import { Badge } from "@/components/ui/badge";
import { cn } from "@/lib/utils";

interface AgentReviewPanelProps {
  confidence: number;
  warnings: string[];
  recommendations: Record<string, unknown>;
  isAnalyzing: boolean;
  progressPercent?: number;
}

export function AgentReviewPanel({
  confidence,
  warnings,
  recommendations,
  isAnalyzing,
  progressPercent = 0,
}: AgentReviewPanelProps) {
  const [expanded, setExpanded] = useState(false);

  const confidenceBadge = () => {
    if (isAnalyzing) return <Badge className="bg-blue-500">분석 중...</Badge>;
    if (confidence >= 0.7) return <Badge className="bg-green-500">높음 ({Math.round(confidence * 100)}%)</Badge>;
    if (confidence >= 0.5) return <Badge className="bg-yellow-500">보통 ({Math.round(confidence * 100)}%)</Badge>;
    return <Badge className="bg-red-500">낮음 ({Math.round(confidence * 100)}%)</Badge>;
  };

  const recEntries = Object.entries(recommendations).slice(0, 10);

  return (
    <div className="rounded-lg border bg-white shadow-sm">
      {/* Header */}
      <div className="flex items-center justify-between px-4 py-3">
        <div className="flex items-center gap-2">
          <Bot className="h-4 w-4 text-primary" />
          <span className="text-sm font-semibold">에이전트 분석 결과</span>
        </div>
        {confidenceBadge()}
      </div>

      {/* Progress bar (visible while analyzing) */}
      {isAnalyzing && (
        <div className="px-4 pb-2">
          <div className="h-1.5 w-full overflow-hidden rounded-full bg-muted">
            <div
              className="h-full animate-pulse bg-primary transition-all duration-500"
              style={{ width: `${Math.max(progressPercent, 15)}%` }}
            />
          </div>
          <p className="mt-1 text-xs text-muted-foreground">에이전트 분석 진행 중...</p>
        </div>
      )}

      {/* Warnings */}
      {warnings.length > 0 && (
        <div className="space-y-1 px-4 pb-2">
          {warnings.map((w, i) => (
            <Alert key={i} variant="destructive" className="py-2">
              <AlertCircle className="h-3.5 w-3.5" />
              <AlertDescription className="text-xs">{w}</AlertDescription>
            </Alert>
          ))}
        </div>
      )}

      {/* Recommendations toggle */}
      {recEntries.length > 0 && (
        <>
          <button
            type="button"
            onClick={() => setExpanded((v) => !v)}
            className="flex w-full items-center justify-between border-t px-4 py-2 text-xs text-muted-foreground hover:bg-muted/30"
          >
            <span>추천 결과 상세 ({recEntries.length}개 항목)</span>
            {expanded ? <ChevronUp className="h-3.5 w-3.5" /> : <ChevronDown className="h-3.5 w-3.5" />}
          </button>

          {expanded && (
            <div className="max-h-64 overflow-y-auto border-t px-4 py-3">
              <dl className="space-y-2 text-xs">
                {recEntries.map(([key, val]) => (
                  <div key={key}>
                    <dt className="font-medium text-gray-700">{key}</dt>
                    <dd className={cn("mt-0.5 rounded bg-muted px-2 py-1 font-mono text-gray-600")}>
                      {typeof val === "object"
                        ? JSON.stringify(val, null, 2)
                        : String(val)}
                    </dd>
                  </div>
                ))}
              </dl>
            </div>
          )}
        </>
      )}
    </div>
  );
}
