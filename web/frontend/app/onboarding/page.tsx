"use client";

import { useEffect, useMemo, useState } from "react";
import { DashboardLayout } from "@/components/dashboard-layout";
import { Checklist } from "@/components/onboarding/checklist";
import { OnboardingStepDetail } from "@/components/onboarding/onboarding-step-detail";
import { PipelineMap } from "@/components/onboarding/pipeline-map";
import { Button } from "@/components/ui/button";
import { useOnboardingStatus } from "@/hooks/useOnboarding";
import type { StepKey } from "@/lib/types/onboarding";

export default function OnboardingPage() {
  const { data: status, isLoading, error } = useOnboardingStatus();
  const [viewMode, setViewMode] = useState<"guide" | "flow">("guide");
  const [selectedStepKey, setSelectedStepKey] = useState<StepKey | null>(null);

  useEffect(() => {
    if (!status) return;
    setSelectedStepKey((prev) => {
      if (prev && status.steps.some((s) => s.key === prev)) return prev;
      const fallback = status.steps.find((s) => !s.completed)?.key ?? status.steps[0]?.key;
      return fallback ?? null;
    });
  }, [status]);

  const selectedStep = useMemo(() => {
    if (!status || !selectedStepKey) return null;
    return status.steps.find((s) => s.key === selectedStepKey) ?? null;
  }, [status, selectedStepKey]);

  const selectedIndex = useMemo(() => {
    if (!status || !selectedStepKey) return 0;
    return status.steps.findIndex((s) => s.key === selectedStepKey);
  }, [status, selectedStepKey]);

  return (
    <DashboardLayout>
      <div className="mb-6 flex flex-col gap-3 sm:flex-row sm:items-end sm:justify-between">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Data pipeline onboarding</h1>
          <p className="text-sm text-gray-500 mt-1">
            Modular phases from platform access and data modeling through collection, profile readiness, audiences,
            and activation.
          </p>
        </div>
        <Button
          type="button"
          variant="outline"
          size="sm"
          className="shrink-0 self-start sm:self-auto"
          onClick={() => setViewMode((m) => (m === "guide" ? "flow" : "guide"))}
        >
          {viewMode === "guide" ? "View as flow" : "Back to guide"}
        </Button>
      </div>

      {isLoading && (
        <div className="flex items-center justify-center h-96 text-gray-400 text-sm">
          Loading onboarding status...
        </div>
      )}

      {error && (
        <div className="flex items-center justify-center h-96 text-red-400 text-sm">
          Could not load status. Check that the backend server is running.
        </div>
      )}

      {status && selectedStepKey && (
        <div className="flex gap-6 h-[calc(100vh-220px)] min-h-[560px]">
          <div className="w-80 flex-shrink-0 flex flex-col bg-white rounded-xl border border-gray-200 p-4 shadow-sm overflow-hidden max-h-[calc(100vh-220px)]">
            <Checklist
              status={status}
              selectedStepKey={selectedStepKey}
              onSelectStep={setSelectedStepKey}
            />
          </div>

          <div className="flex-1 min-w-0 min-h-0">
            {viewMode === "guide" ? (
              <OnboardingStepDetail step={selectedStep} stepIndex={selectedIndex} status={status} />
            ) : (
              <PipelineMap status={status} />
            )}
          </div>
        </div>
      )}
    </DashboardLayout>
  );
}
