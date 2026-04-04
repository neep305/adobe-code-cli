"use client";

import React, { useState } from "react";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import type { EntityDefinition } from "@/lib/types/schema_wizard";

interface Step5FieldGroupProps {
  entities: EntityDefinition[];
  agentOutput: Record<string, unknown>;
  onSubmit: (formData: FormData) => Promise<void>;
  isAnalyzing: boolean;
}

const STANDARD_FIELD_GROUPS = [
  "Personal Contact Details",
  "Demographic Details",
  "Loyalty Details",
  "Commerce Details",
  "Web Details",
  "Device Details",
  "Campaign Member Details",
];

export function Step5FieldGroup({ entities, agentOutput, onSubmit, isAnalyzing }: Step5FieldGroupProps) {
  const fgMap = (agentOutput.field_group_map as Record<string, { standard_fields: string[]; custom_fields: string[]; field_groups: string[] }>) ?? {};

  const [selectedFGs, setSelectedFGs] = useState<Record<string, string[]>>(() =>
    Object.fromEntries(entities.map((e) => [e.name, fgMap[e.name]?.field_groups ?? []]))
  );

  const toggleFG = (entityName: string, fg: string) => {
    setSelectedFGs((prev) => {
      const current = prev[entityName] ?? [];
      return {
        ...prev,
        [entityName]: current.includes(fg) ? current.filter((x) => x !== fg) : [...current, fg],
      };
    });
  };

  const handleSubmit = () => {
    const fd = new FormData();
    fd.append("step_data", JSON.stringify({ field_group_overrides: selectedFGs }));
    onSubmit(fd);
  };

  return (
    <Card>
      <CardHeader>
        <CardTitle>Phase 5: Field Group & 네임스페이스</CardTitle>
        <CardDescription>
          Adobe 표준 Field Group을 선택하고 커스텀 필드는 테넌트 네임스페이스로 분리합니다.
        </CardDescription>
      </CardHeader>
      <CardContent className="space-y-4">
        {entities.map((entity) => {
          const info = fgMap[entity.name];
          return (
            <div key={entity.name} className="rounded-lg border p-3 space-y-3">
              <span className="font-semibold">{entity.name}</span>

              {/* Field separation */}
              {info && (
                <div className="grid grid-cols-2 gap-3 text-xs">
                  <div>
                    <p className="font-medium text-green-700 mb-1">표준 XDM 필드 (root)</p>
                    <div className="flex flex-wrap gap-1">
                      {info.standard_fields.length > 0
                        ? info.standard_fields.map((f) => <Badge key={f} variant="outline" className="text-[10px]">{f}</Badge>)
                        : <span className="text-muted-foreground">없음</span>}
                    </div>
                  </div>
                  <div>
                    <p className="font-medium text-blue-700 mb-1">커스텀 필드 (_{"{tenant_id}"})</p>
                    <div className="flex flex-wrap gap-1">
                      {info.custom_fields.length > 0
                        ? info.custom_fields.map((f) => <Badge key={f} className="bg-blue-100 text-blue-800 text-[10px]">{f}</Badge>)
                        : <span className="text-muted-foreground">없음</span>}
                    </div>
                  </div>
                </div>
              )}

              {/* Field group selection */}
              <div>
                <p className="text-xs font-medium mb-2">Adobe 표준 Field Groups</p>
                <div className="flex flex-wrap gap-1.5">
                  {STANDARD_FIELD_GROUPS.map((fg) => {
                    const active = (selectedFGs[entity.name] ?? []).includes(fg);
                    return (
                      <button
                        key={fg}
                        type="button"
                        onClick={() => toggleFG(entity.name, fg)}
                        className={`rounded-full border px-2.5 py-0.5 text-xs transition-colors ${
                          active ? "border-primary bg-primary text-white" : "border-muted-foreground/30 hover:border-primary"
                        }`}
                      >
                        {fg}
                      </button>
                    );
                  })}
                </div>
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
