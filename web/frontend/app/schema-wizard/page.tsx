"use client";

import React, { useEffect, useState } from "react";
import { CheckCircle, Download, Upload } from "lucide-react";
import { Alert, AlertDescription } from "@/components/ui/alert";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { DashboardLayout } from "@/components/dashboard-layout";
import { WizardStepper } from "@/components/schema-wizard/WizardStepper";
import { SchemaChecklist } from "@/components/schema-wizard/SchemaChecklist";
import { AgentReviewPanel } from "@/components/schema-wizard/AgentReviewPanel";
import { Step1Erd } from "@/components/schema-wizard/steps/Step1Erd";
import { Step2XdmClass } from "@/components/schema-wizard/steps/Step2XdmClass";
import { Step3Identity } from "@/components/schema-wizard/steps/Step3Identity";
import { Step4MergePolicy } from "@/components/schema-wizard/steps/Step4MergePolicy";
import { Step5FieldGroup } from "@/components/schema-wizard/steps/Step5FieldGroup";
import { Step6TypePreprocessing } from "@/components/schema-wizard/steps/Step6TypePreprocessing";
import { useSchemaWizard } from "@/hooks/useSchemaWizard";
import type { ChecklistItem, FinalizeResult, StepResult } from "@/lib/types/schema_wizard";

export default function SchemaWizardPage() {
  const {
    session,
    currentResult,
    liveChecklist,
    isAnalyzing,
    isConnected,
    error,
    createSession,
    submitStep,
    finalizeSession,
    approveStep,
  } = useSchemaWizard();

  const [activePhase, setActivePhase] = useState(1);
  const [finalResult, setFinalResult] = useState<FinalizeResult | null>(null);
  const [finalizing, setFinalizing] = useState(false);
  const [stepError, setStepError] = useState<string | null>(null);

  // Create session on mount
  useEffect(() => {
    createSession().catch(() => {/* error shown by hook */});
  }, []);

  const completedPhases = session
    ? Object.entries(session.steps)
        .filter(([, s]) => s.status === "completed" || s.status === "approved")
        .map(([k]) => Number(k))
    : [];

  const activeStep = session?.steps[activePhase];
  const activeChecklist: ChecklistItem[] =
    isAnalyzing && activeStep?.phase === activePhase
      ? liveChecklist
      : activeStep?.checklist ?? [];

  const handleSubmitStep = async (phase: number, fd: FormData) => {
    setStepError(null);
    try {
      const result: StepResult = await submitStep(phase, fd);
      if (result.warnings.length > 0 && result.confidence < 0.5) {
        setStepError(result.warnings[0]);
      }
    } catch (err) {
      setStepError(err instanceof Error ? err.message : "단계 분석 실패");
    }
  };

  const handleApprove = (phase: number) => {
    approveStep(phase);
    setActivePhase(Math.min(phase + 1, 6));
  };

  const handleFinalize = async (uploadToAep: boolean) => {
    setFinalizing(true);
    setStepError(null);
    try {
      const result = await finalizeSession(uploadToAep);
      setFinalResult(result);
    } catch (err) {
      setStepError(err instanceof Error ? err.message : "스키마 생성 실패");
    } finally {
      setFinalizing(false);
    }
  };

  if (!session) {
    return (
      <DashboardLayout>
        <div className="flex items-center justify-center py-20">
          <div className="text-center space-y-3">
            <div className="h-8 w-8 animate-spin rounded-full border-4 border-primary border-t-transparent mx-auto" />
            <p className="text-muted-foreground">세션 초기화 중...</p>
          </div>
        </div>
      </DashboardLayout>
    );
  }

  return (
    <DashboardLayout>
      <div className="space-y-6">
        {/* Header */}
        <div className="flex items-start justify-between">
          <div>
            <h1 className="text-3xl font-bold">Schema Design Wizard</h1>
            <p className="text-muted-foreground mt-1">
              단계별 XDM 스키마 설계 — 에이전트가 각 Phase를 자동 검수합니다.
            </p>
          </div>
          <div className="flex items-center gap-2">
            <Badge variant="outline" className="text-xs">
              Session: {session.session_id.slice(0, 8)}...
            </Badge>
            <Badge
              variant="outline"
              className={isConnected ? "border-green-400 text-green-600" : "border-red-400 text-red-500"}
            >
              {isConnected ? "WS 연결됨" : "WS 연결 중..."}
            </Badge>
          </div>
        </div>

        {/* Stepper */}
        <WizardStepper currentPhase={activePhase} completedPhases={completedPhases} />

        {/* Phase navigation tabs */}
        <div className="flex gap-1 overflow-x-auto border-b pb-0">
          {[1, 2, 3, 4, 5, 6].map((p) => {
            const done = completedPhases.includes(p);
            return (
              <button
                key={p}
                type="button"
                onClick={() => setActivePhase(p)}
                className={`flex-shrink-0 border-b-2 px-4 py-2 text-sm font-medium transition-colors ${
                  activePhase === p
                    ? "border-primary text-primary"
                    : done
                    ? "border-transparent text-green-600 hover:text-primary"
                    : "border-transparent text-muted-foreground hover:text-gray-700"
                }`}
              >
                Phase {p} {done && <CheckCircle className="inline h-3.5 w-3.5 ml-1" />}
              </button>
            );
          })}
        </div>

        {/* Global error */}
        {(error || stepError) && (
          <Alert variant="destructive">
            <AlertDescription>{error ?? stepError}</AlertDescription>
          </Alert>
        )}

        {/* Two-column layout: step input (left) + checklist + agent panel (right) */}
        <div className="grid gap-6 lg:grid-cols-[1fr_340px]">
          {/* Left: step component */}
          <div>
            {activePhase === 1 && (
              <Step1Erd
                onSubmit={(fd) => handleSubmitStep(1, fd)}
                isAnalyzing={isAnalyzing}
              />
            )}
            {activePhase === 2 && (
              <Step2XdmClass
                entities={session.entities}
                agentOutput={session.steps[2]?.agent_output ?? {}}
                onSubmit={(fd) => handleSubmitStep(2, fd)}
                isAnalyzing={isAnalyzing}
              />
            )}
            {activePhase === 3 && (
              <Step3Identity
                entities={session.entities}
                agentOutput={session.steps[3]?.agent_output ?? {}}
                onSubmit={(fd) => handleSubmitStep(3, fd)}
                isAnalyzing={isAnalyzing}
              />
            )}
            {activePhase === 4 && (
              <Step4MergePolicy
                entities={session.entities}
                agentOutput={session.steps[4]?.agent_output ?? {}}
                onSubmit={(fd) => handleSubmitStep(4, fd)}
                isAnalyzing={isAnalyzing}
              />
            )}
            {activePhase === 5 && (
              <Step5FieldGroup
                entities={session.entities}
                agentOutput={session.steps[5]?.agent_output ?? {}}
                onSubmit={(fd) => handleSubmitStep(5, fd)}
                isAnalyzing={isAnalyzing}
              />
            )}
            {activePhase === 6 && (
              <Step6TypePreprocessing
                entities={session.entities}
                agentOutput={session.steps[6]?.agent_output ?? {}}
                onSubmit={(fd) => handleSubmitStep(6, fd)}
                isAnalyzing={isAnalyzing}
              />
            )}

            {/* Approve & Next button (after analysis completes) */}
            {activeStep?.status === "completed" && activePhase < 6 && (
              <div className="mt-4 flex justify-end gap-3">
                <Button
                  variant="outline"
                  onClick={() => setActivePhase(activePhase)}
                  size="sm"
                >
                  다시 분석
                </Button>
                <Button onClick={() => handleApprove(activePhase)}>
                  승인 & 다음 Phase →
                </Button>
              </div>
            )}

            {/* Finalize section after Phase 6 */}
            {activePhase === 6 && activeStep?.status === "completed" && !finalResult && (
              <div className="mt-4 space-y-3">
                <div className="rounded-lg border p-4 space-y-2">
                  <h3 className="font-semibold">스키마 생성</h3>
                  <p className="text-sm text-muted-foreground">
                    모든 Phase 설계 결과를 기반으로 XDM 스키마 JSON을 생성합니다.
                  </p>
                  <div className="flex gap-2">
                    <Button
                      variant="outline"
                      disabled={finalizing}
                      onClick={() => handleFinalize(false)}
                    >
                      <Download className="mr-2 h-4 w-4" />
                      {finalizing ? "생성 중..." : "로컬 JSON 생성"}
                    </Button>
                    <Button
                      disabled={finalizing}
                      onClick={() => handleFinalize(true)}
                    >
                      <Upload className="mr-2 h-4 w-4" />
                      {finalizing ? "업로드 중..." : "AEP에 업로드"}
                    </Button>
                  </div>
                </div>
              </div>
            )}
          </div>

          {/* Right: checklist + agent panel */}
          <div className="space-y-4">
            <SchemaChecklist
              items={activeChecklist}
              title={`Phase ${activePhase} 검수 항목`}
            />
            <AgentReviewPanel
              confidence={activeStep?.confidence ?? 0}
              warnings={activeStep?.warnings ?? []}
              recommendations={activeStep?.recommendations ?? {}}
              isAnalyzing={isAnalyzing}
            />
          </div>
        </div>

        {/* Final result */}
        {finalResult && (
          <Card>
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <CheckCircle className="h-5 w-5 text-green-500" />
                스키마 생성 완료
              </CardTitle>
              <CardDescription>
                {finalResult.schemas.length}개 XDM 스키마가 생성되었습니다.
              </CardDescription>
            </CardHeader>
            <CardContent className="space-y-4">
              {finalResult.uploaded_schema_ids.length > 0 && (
                <div>
                  <p className="text-sm font-medium mb-2">AEP 업로드 완료</p>
                  {finalResult.uploaded_schema_ids.map((id) => (
                    <Badge key={id} variant="outline" className="mr-1 text-xs">{id}</Badge>
                  ))}
                </div>
              )}
              <div>
                <p className="text-sm font-medium mb-2">생성된 파일</p>
                {finalResult.output_files.map((f) => (
                  <p key={f} className="text-xs font-mono text-muted-foreground">{f}</p>
                ))}
              </div>
              {finalResult.warnings.length > 0 && (
                <Alert>
                  <AlertDescription className="text-xs">
                    {finalResult.warnings.join(" | ")}
                  </AlertDescription>
                </Alert>
              )}
              {/* Schema JSON preview */}
              <div>
                <p className="text-sm font-medium mb-2">스키마 미리보기</p>
                <div className="max-h-80 overflow-y-auto rounded-lg bg-muted p-3">
                  <pre className="text-xs whitespace-pre-wrap">
                    {JSON.stringify(finalResult.schemas[0], null, 2)}
                  </pre>
                </div>
              </div>
            </CardContent>
          </Card>
        )}
      </div>
    </DashboardLayout>
  );
}
