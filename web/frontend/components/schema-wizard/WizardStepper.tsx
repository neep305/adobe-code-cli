"use client";

import { Check } from "lucide-react";
import { cn } from "@/lib/utils";
import { PHASES } from "@/lib/types/schema_wizard";

interface WizardStepperProps {
  currentPhase: number;
  completedPhases: number[];
}

export function WizardStepper({ currentPhase, completedPhases }: WizardStepperProps) {
  return (
    <nav aria-label="Schema Design Progress" className="w-full">
      <ol className="flex items-center justify-between">
        {PHASES.map((phase, idx) => {
          const isCompleted = completedPhases.includes(phase.phase);
          const isCurrent = currentPhase === phase.phase;
          const isUpcoming = !isCompleted && !isCurrent;

          return (
            <li key={phase.phase} className="flex flex-1 items-center">
              {/* Step circle */}
              <div className="flex flex-col items-center">
                <div
                  className={cn(
                    "flex h-9 w-9 items-center justify-center rounded-full border-2 text-sm font-semibold transition-colors",
                    isCompleted && "border-primary bg-primary text-primary-foreground",
                    isCurrent && "border-primary bg-white text-primary shadow-md",
                    isUpcoming && "border-muted-foreground/30 bg-white text-muted-foreground"
                  )}
                  aria-current={isCurrent ? "step" : undefined}
                >
                  {isCompleted ? <Check className="h-4 w-4" /> : phase.phase}
                </div>
                <div className="mt-1 text-center">
                  <p
                    className={cn(
                      "text-xs font-medium",
                      isCurrent && "text-primary",
                      isCompleted && "text-primary",
                      isUpcoming && "text-muted-foreground"
                    )}
                  >
                    {phase.title}
                  </p>
                  <p className="hidden text-xs text-muted-foreground sm:block">
                    {phase.description}
                  </p>
                </div>
              </div>

              {/* Connector line between steps */}
              {idx < PHASES.length - 1 && (
                <div
                  className={cn(
                    "mx-2 mt-[-18px] h-0.5 flex-1",
                    completedPhases.includes(phase.phase + 1) || isCompleted
                      ? "bg-primary"
                      : "bg-muted-foreground/20"
                  )}
                />
              )}
            </li>
          );
        })}
      </ol>
    </nav>
  );
}
