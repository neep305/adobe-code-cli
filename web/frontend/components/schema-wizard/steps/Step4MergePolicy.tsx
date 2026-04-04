"use client";

import React, { useState } from "react";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import type { EntityDefinition } from "@/lib/types/schema_wizard";

interface Step4MergePolicyProps {
  entities: EntityDefinition[];
  agentOutput: Record<string, unknown>;
  onSubmit: (formData: FormData) => Promise<void>;
  isAnalyzing: boolean;
}

const POLICIES = [
  { value: "timestamp-based", label: "Timestamp 기반", desc: "최신 업데이트 우선 — B2C/실시간 기본값" },
  { value: "data-source-priority", label: "소스 우선순위", desc: "CRM > Web 등 소스 우선순위 지정 — B2B" },
  { value: "last-write-wins", label: "Last Write Wins", desc: "마지막 쓰기 타임스탬프 기준 전역 적용" },
  { value: "data-source-specific", label: "필드별 정책", desc: "필드마다 다른 소스 규칙 — 복잡한 멀티소스" },
];

export function Step4MergePolicy({ entities, agentOutput, onSubmit, isAnalyzing }: Step4MergePolicyProps) {
  const agentPolicies = (agentOutput.merge_policies as Record<string, { policy: string; description: string }>) ?? {};

  const [policyOverrides, setPolicyOverrides] = useState<Record<string, string>>(() =>
    Object.fromEntries(
      entities.map((e) => [e.name, agentPolicies[e.name]?.policy ?? "timestamp-based"])
    )
  );
  const [sourcePriority, setSourcePriority] = useState<string>("");

  const needsSourcePriority = Object.values(policyOverrides).includes("data-source-priority");

  const handleSubmit = () => {
    const fd = new FormData();
    const payload: Record<string, unknown> = { merge_policy_overrides: policyOverrides };
    if (sourcePriority.trim()) {
      payload.source_priority = sourcePriority.split(",").map((s) => s.trim()).filter(Boolean);
    }
    fd.append("step_data", JSON.stringify(payload));
    onSubmit(fd);
  };

  return (
    <Card>
      <CardHeader>
        <CardTitle>Phase 4: Merge Policy</CardTitle>
        <CardDescription>
          여러 소스에서 동일 고객 데이터가 충돌할 때 적용할 통합 정책을 선택합니다.
        </CardDescription>
      </CardHeader>
      <CardContent className="space-y-4">
        {entities.map((entity) => {
          const agentRec = agentPolicies[entity.name]?.policy;
          const current = policyOverrides[entity.name] ?? "timestamp-based";
          return (
            <div key={entity.name} className="rounded-lg border p-3 space-y-2">
              <div className="flex items-center justify-between">
                <span className="font-semibold">{entity.name}</span>
                {agentRec && (
                  <Badge variant="outline" className="text-xs">AI 추천: {agentRec}</Badge>
                )}
              </div>
              <div className="grid grid-cols-2 gap-2">
                {POLICIES.map((p) => (
                  <button
                    key={p.value}
                    type="button"
                    onClick={() => setPolicyOverrides((prev) => ({ ...prev, [entity.name]: p.value }))}
                    className={`rounded-lg border-2 p-2 text-left transition-colors ${
                      current === p.value ? "border-primary bg-primary/5" : "border-muted"
                    }`}
                  >
                    <p className="text-xs font-medium">{p.label}</p>
                    <p className="text-[10px] text-muted-foreground">{p.desc}</p>
                  </button>
                ))}
              </div>
            </div>
          );
        })}

        {needsSourcePriority && (
          <div className="space-y-1">
            <label className="text-sm font-medium">소스 우선순위 (쉼표 구분)</label>
            <input
              className="w-full rounded border px-3 py-2 text-sm"
              placeholder="예: CRM, Marketing Automation, Web"
              value={sourcePriority}
              onChange={(e) => setSourcePriority(e.target.value)}
            />
          </div>
        )}

        <Button onClick={handleSubmit} disabled={isAnalyzing || entities.length === 0} className="w-full">
          {isAnalyzing ? "분석 중..." : "AI 검수 실행"}
        </Button>
      </CardContent>
    </Card>
  );
}
