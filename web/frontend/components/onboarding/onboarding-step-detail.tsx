"use client";

import { useRouter } from "next/navigation";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { useUpdateOnboardingProgress } from "@/hooks/useOnboarding";
import { goToOnboardingAction } from "@/lib/onboarding-nav";
import { ONBOARDING_STEP_GUIDES } from "@/lib/onboarding-step-guides";
import type { OnboardingStatus, OnboardingStep } from "@/lib/types/onboarding";

interface OnboardingStepDetailProps {
  step: OnboardingStep | null;
  stepIndex: number;
  status: OnboardingStatus;
}

export function OnboardingStepDetail({ step, stepIndex, status }: OnboardingStepDetailProps) {
  const router = useRouter();
  const updateProgress = useUpdateOnboardingProgress();

  if (!step) {
    return (
      <div className="flex h-full min-h-[480px] items-center justify-center rounded-xl border border-dashed border-gray-200 bg-gray-50/50 text-sm text-gray-500">
        Select a step on the left.
      </div>
    );
  }

  const guide = ONBOARDING_STEP_GUIDES[step.key];
  const hasNav = Boolean(step.action_url?.trim());
  const nextIncomplete = status.steps.find((s) => !s.completed);

  return (
    <div className="flex h-full min-h-[480px] flex-col rounded-xl border border-gray-200 bg-white shadow-sm overflow-hidden">
      <div className="border-b border-gray-100 bg-gray-50/80 px-6 py-4">
        <div className="flex flex-wrap items-center gap-2">
          <span className="text-xs font-semibold text-gray-400">Step {stepIndex + 1}</span>
          {step.completed ? (
            <Badge variant="secondary" className="bg-emerald-100 text-emerald-800 hover:bg-emerald-100">
              Done
            </Badge>
          ) : nextIncomplete?.key === step.key ? (
            <Badge className="bg-amber-500 text-white hover:bg-amber-500">Recommended</Badge>
          ) : (
            <Badge variant="outline" className="text-gray-600">
              Pending
            </Badge>
          )}
        </div>
        <h2 className="mt-2 text-lg font-bold text-gray-900">{step.label}</h2>
        <p className="mt-1 text-sm text-gray-600 leading-relaxed">{step.description}</p>
        {step.completed && step.resource_name && (
          <p className="mt-2 text-xs text-gray-400 font-mono truncate">{step.resource_name}</p>
        )}
      </div>

      <div className="flex-1 overflow-y-auto px-6 py-5 space-y-6">
        {guide.sections.map((section) => (
          <section key={section.title}>
            <h3 className="text-sm font-semibold text-gray-900 mb-2">{section.title}</h3>
            <ol className="list-decimal list-inside space-y-2 text-sm text-gray-700 leading-relaxed">
              {section.bullets.map((b, i) => (
                <li key={i} className="pl-1 marker:text-gray-400">
                  {b}
                </li>
              ))}
            </ol>
          </section>
        ))}
      </div>

      <div className="border-t border-gray-100 bg-gray-50/80 px-6 py-4 flex flex-col sm:flex-row gap-2 sm:items-center sm:justify-between">
        <div className="flex flex-wrap gap-2">
          {step.key === "source" && !step.completed && (
            <Button
              type="button"
              className="bg-amber-500 hover:bg-amber-600"
              disabled={updateProgress.isPending}
              onClick={() => updateProgress.mutate({ step_key: "source", completed: true })}
            >
              Confirm source connection
            </Button>
          )}
          {hasNav && (
            <Button
              type="button"
              variant={step.key === "source" && !step.completed ? "outline" : "default"}
              onClick={() => goToOnboardingAction(step.action_url, router)}
            >
              {step.action_label}
            </Button>
          )}
          {step.allow_manual_complete && !step.completed && step.key !== "source" && (
            <Button
              type="button"
              variant="outline"
              size="sm"
              disabled={updateProgress.isPending}
              onClick={() => updateProgress.mutate({ step_key: step.key, completed: true })}
            >
              {step.action_label?.trim() ? step.action_label : "Mark complete manually"}
            </Button>
          )}
          {step.allow_manual_complete && step.completed && step.manual_marked && (
            <Button
              type="button"
              variant="ghost"
              size="sm"
              className="text-gray-600"
              disabled={updateProgress.isPending}
              onClick={() => updateProgress.mutate({ step_key: step.key, completed: false })}
            >
              Clear manual completion
            </Button>
          )}
        </div>
        {status.overall_progress >= 1 && (
          <Button type="button" variant="link" className="text-emerald-700" onClick={() => router.push("/analyze")}>
            Go to Analyze →
          </Button>
        )}
      </div>
    </div>
  );
}
