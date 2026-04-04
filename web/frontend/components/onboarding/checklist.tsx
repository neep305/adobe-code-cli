"use client";

import type { MouseEvent } from "react";
import { useRouter } from "next/navigation";
import { ChevronRight, Terminal } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Checkbox } from "@/components/ui/checkbox";
import { Progress } from "@/components/ui/progress";
import { useUpdateOnboardingProgress } from "@/hooks/useOnboarding";
import { goToOnboardingAction } from "@/lib/onboarding-nav";
import type { OnboardingPhaseSummary, OnboardingStatus, OnboardingStep, StepKey } from "@/lib/types/onboarding";
import { cn } from "@/lib/utils";

interface ChecklistProps {
  status: OnboardingStatus;
  selectedStepKey: StepKey;
  onSelectStep: (key: StepKey) => void;
}

function StepItem({
  step,
  index,
  isNext,
  isSelected,
  onSelect,
}: {
  step: OnboardingStep;
  index: number;
  isNext: boolean;
  isSelected: boolean;
  onSelect: () => void;
}) {
  const router = useRouter();
  const hasNavUrl = Boolean(step.action_url?.trim());
  const openAction = (e: MouseEvent) => {
    e.stopPropagation();
    goToOnboardingAction(step.action_url, router);
  };

  const shortLine = step.node_hint?.trim() || step.description;

  return (
    <div
      role="button"
      tabIndex={0}
      onClick={onSelect}
      onKeyDown={(e) => {
        if (e.key === "Enter" || e.key === " ") {
          e.preventDefault();
          onSelect();
        }
      }}
      className={cn(
        "flex items-start gap-3 p-3 rounded-lg border transition-colors text-left w-full cursor-pointer",
        isSelected && "border-blue-300 bg-blue-50/60 ring-1 ring-blue-200",
        !isSelected && isNext && "border-amber-200 bg-amber-50/50",
        !isSelected && !isNext && "border-transparent hover:bg-gray-50"
      )}
    >
      <div className="pt-0.5 shrink-0 pointer-events-none" onClick={(e) => e.stopPropagation()}>
        <Checkbox checked={step.completed} disabled aria-label={`${step.label} completion`} />
      </div>

      <div className="flex-1 min-w-0">
        <div className="flex items-center gap-2 flex-wrap">
          <span
            className={cn(
              "text-xs font-semibold",
              step.completed ? "text-emerald-700" : isNext ? "text-amber-900" : "text-gray-600"
            )}
          >
            {index + 1}. {step.label}
          </span>
          {step.cli_only && (
            <span className="flex items-center gap-0.5 text-[9px] font-bold text-violet-600 bg-violet-100 px-1.5 py-0.5 rounded">
              <Terminal className="w-2.5 h-2.5" />
              CLI
            </span>
          )}
          {isNext && (
            <span className="text-[9px] font-bold text-amber-800 bg-amber-100 px-1.5 py-0.5 rounded">NEXT</span>
          )}
        </div>
        {step.completed && step.resource_name && (
          <p className="text-[10px] text-gray-400 font-mono mt-0.5 truncate">{step.resource_name}</p>
        )}
        <p className="text-[10px] text-gray-500 mt-1 line-clamp-2 leading-snug">{shortLine}</p>
      </div>

      {!step.completed && hasNavUrl && (
        <button
          type="button"
          onClick={openAction}
          className="flex-shrink-0 mt-0.5 text-gray-400 hover:text-gray-600 transition-colors"
          title={step.action_label}
        >
          <ChevronRight className="w-4 h-4" />
        </button>
      )}
    </div>
  );
}

function PhaseBlock({
  phase,
  steps,
  nextStepKey,
  selectedStepKey,
  onSelectStep,
  globalIndexStart,
  isFirst,
}: {
  phase: OnboardingPhaseSummary;
  steps: OnboardingStep[];
  nextStepKey: StepKey | undefined;
  selectedStepKey: StepKey;
  onSelectStep: (key: StepKey) => void;
  globalIndexStart: number;
  isFirst: boolean;
}) {
  if (steps.length === 0) return null;
  const pct = Math.round(phase.progress * 100);
  return (
    <div className="space-y-1.5">
      <div
        className={cn(
          "pt-2 pb-0.5 border-gray-100",
          isFirst ? "pt-0 border-t-0" : "border-t"
        )}
      >
        <div className="flex items-center justify-between gap-2 px-0.5">
          <h3 className="text-[11px] font-bold uppercase tracking-wide text-gray-500">{phase.title}</h3>
          <span className="text-[10px] text-gray-400 tabular-nums">
            {phase.completed_count}/{phase.total_count} · {pct}%
          </span>
        </div>
      </div>
      {steps.map((step, i) => (
        <StepItem
          key={step.key}
          step={step}
          index={globalIndexStart + i}
          isNext={step.key === nextStepKey}
          isSelected={step.key === selectedStepKey}
          onSelect={() => onSelectStep(step.key)}
        />
      ))}
    </div>
  );
}

export function Checklist({ status, selectedStepKey, onSelectStep }: ChecklistProps) {
  const router = useRouter();
  const updateProgress = useUpdateOnboardingProgress();
  const progressPercent = Math.round(status.overall_progress * 100);
  const nextStep = status.steps.find((s) => !s.completed);

  const orderedPhases = [...status.phases].sort((a, b) => a.order - b.order);

  let runningIndex = 0;

  return (
    <div className="flex flex-col gap-4 h-full min-h-0">
      <div>
        <h2 className="text-base font-bold text-gray-900">AEP getting started</h2>
        <p className="text-xs text-gray-500 mt-0.5">
          Phases follow the platform journey: access → modeling → collection → profile → audiences → activation.
        </p>
      </div>

      <div className="space-y-1.5">
        <div className="flex justify-between text-xs text-gray-500">
          <span>
            {status.completed_count} / {status.total_count} complete
          </span>
          <span className="font-semibold text-gray-700">{progressPercent}%</span>
        </div>
        <Progress value={progressPercent} className="h-2" />
      </div>

      <div className="flex-1 flex flex-col gap-1 overflow-y-auto min-h-0">
        {orderedPhases.map((phase, phaseIdx) => {
          const phaseSteps = status.steps.filter((s) => s.phase_id === phase.id);
          const start = runningIndex;
          runningIndex += phaseSteps.length;
          return (
            <PhaseBlock
              key={phase.id}
              phase={phase}
              steps={phaseSteps}
              nextStepKey={nextStep?.key}
              selectedStepKey={selectedStepKey}
              onSelectStep={onSelectStep}
              globalIndexStart={start}
              isFirst={phaseIdx === 0}
            />
          );
        })}
      </div>

      {nextStep && (
        <Button
          type="button"
          disabled={updateProgress.isPending}
          onClick={() => {
            if (!nextStep.action_url?.trim() && nextStep.allow_manual_complete) {
              updateProgress.mutate({ step_key: nextStep.key, completed: true });
              return;
            }
            goToOnboardingAction(nextStep.action_url, router);
          }}
          className="w-full bg-amber-500 hover:bg-amber-600 text-white text-sm shrink-0"
        >
          {nextStep.action_label}
        </Button>
      )}

      {status.overall_progress >= 1 && (
        <div className="text-center py-2 shrink-0">
          <p className="text-sm font-semibold text-emerald-600">All steps complete</p>
          <button
            type="button"
            onClick={() => router.push("/analyze")}
            className="text-xs text-gray-400 hover:text-gray-600 mt-1"
          >
            Go to Analyze →
          </button>
        </div>
      )}
    </div>
  );
}
