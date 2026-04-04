"use client";

import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import type { EntityDefinition } from "@/lib/types/schema_wizard";

interface Step2XdmClassProps {
  entities: EntityDefinition[];
  agentOutput: Record<string, unknown>;
  onSubmit: (formData: FormData) => Promise<void>;
  isAnalyzing: boolean;
}

const CLASS_OPTIONS = [
  { value: "profile", label: "Profile", color: "bg-blue-100 text-blue-800", desc: "고객 속성 (상태)" },
  { value: "experienceevent", label: "ExperienceEvent", color: "bg-purple-100 text-purple-800", desc: "시점 기반 이벤트" },
  { value: "custom", label: "Custom", color: "bg-gray-100 text-gray-700", desc: "상품/계정 등 기타" },
];

export function Step2XdmClass({ entities, agentOutput, onSubmit, isAnalyzing }: Step2XdmClassProps) {
  const agentClasses = (agentOutput.entity_classes as Record<string, { class: string; uri: string }>) ?? {};

  const [overrides, setOverrides] = React.useState<Record<string, string>>(() =>
    Object.fromEntries(entities.map((e) => [e.name, agentClasses[e.name]?.class ?? e.xdm_class_hint]))
  );

  const handleSubmit = () => {
    const fd = new FormData();
    fd.append("step_data", JSON.stringify({ entity_class_overrides: overrides }));
    onSubmit(fd);
  };

  return (
    <Card>
      <CardHeader>
        <CardTitle>Phase 2: XDM 클래스 선택</CardTitle>
        <CardDescription>
          각 엔티티의 XDM 클래스를 확인하고 수정하세요. 에이전트가 추천한 값이 기본 설정됩니다.
        </CardDescription>
      </CardHeader>
      <CardContent className="space-y-4">
        {entities.length === 0 && (
          <p className="text-sm text-muted-foreground">Phase 1을 먼저 완료하세요.</p>
        )}
        {entities.map((entity) => {
          const agentRec = agentClasses[entity.name]?.class;
          const current = overrides[entity.name] ?? entity.xdm_class_hint;
          return (
            <div key={entity.name} className="rounded-lg border p-3">
              <div className="mb-2 flex items-center justify-between">
                <span className="font-semibold">{entity.name}</span>
                {agentRec && (
                  <Badge variant="outline" className="text-xs">
                    AI 추천: {agentRec}
                  </Badge>
                )}
              </div>
              <div className="flex gap-2">
                {CLASS_OPTIONS.map((opt) => (
                  <button
                    key={opt.value}
                    type="button"
                    onClick={() => setOverrides((prev) => ({ ...prev, [entity.name]: opt.value }))}
                    className={`flex flex-col items-center rounded-md border-2 px-3 py-2 text-xs transition-colors ${
                      current === opt.value ? "border-primary" : "border-transparent"
                    } ${opt.color}`}
                  >
                    <span className="font-medium">{opt.label}</span>
                    <span className="text-[10px] opacity-70">{opt.desc}</span>
                  </button>
                ))}
              </div>
            </div>
          );
        })}

        <Button onClick={handleSubmit} disabled={isAnalyzing || entities.length === 0} className="w-full">
          {isAnalyzing ? "분석 중..." : "AI 검수 실행"}
        </Button>
      </CardContent>
    </Card>
  );
}

import React from "react";
