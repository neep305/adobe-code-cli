"use client";

import React, { useState } from "react";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import type { EntityDefinition } from "@/lib/types/schema_wizard";

interface Step3IdentityProps {
  entities: EntityDefinition[];
  agentOutput: Record<string, unknown>;
  onSubmit: (formData: FormData) => Promise<void>;
  isAnalyzing: boolean;
}

const NAMESPACES = ["Email", "Phone", "ECID", "CRM_ID", "Cookie_ID", "Mobile_ID"];
const GRAPH_STRATEGIES = [
  { value: "email-based", label: "Email 기반", desc: "B2C 기본. 이메일로 크로스 디바이스 연결" },
  { value: "crm-based", label: "CRM 기반", desc: "B2B/엔터프라이즈. CRM_ID 우선" },
  { value: "device-graph", label: "Device Graph", desc: "익명 트래픽 중심. ECID 우선" },
  { value: "hybrid", label: "Hybrid (권장)", desc: "알려진 + 익명 모두 처리" },
];

export function Step3Identity({ entities, agentOutput, onSubmit, isAnalyzing }: Step3IdentityProps) {
  const agentIdentities = (agentOutput.identity_map as Record<string, { primary?: { field: string; namespace: string }; secondary?: { field: string; namespace: string }[] }>) ?? {};
  const agentGraphStrategy = (agentOutput.graph_strategy as string) ?? "hybrid";

  const [graphStrategy, setGraphStrategy] = useState(agentGraphStrategy);
  const [primaryOverrides, setPrimaryOverrides] = useState<Record<string, { field: string; namespace: string }>>(() =>
    Object.fromEntries(
      entities.map((e) => [
        e.name,
        agentIdentities[e.name]?.primary ?? { field: "", namespace: "Email" },
      ])
    )
  );

  const updatePrimary = (entityName: string, key: "field" | "namespace", value: string) => {
    setPrimaryOverrides((prev) => ({
      ...prev,
      [entityName]: { ...prev[entityName], [key]: value },
    }));
  };

  const handleSubmit = () => {
    const fd = new FormData();
    fd.append(
      "step_data",
      JSON.stringify({
        primary_identity_overrides: primaryOverrides,
        graph_strategy_override: graphStrategy,
      })
    );
    onSubmit(fd);
  };

  return (
    <Card>
      <CardHeader>
        <CardTitle>Phase 3: Identity 전략</CardTitle>
        <CardDescription>
          각 엔티티의 Primary Identity와 Identity Graph 전략을 설정합니다.
        </CardDescription>
      </CardHeader>
      <CardContent className="space-y-5">
        {/* Per-entity identity */}
        {entities.map((entity) => {
          const agentRec = agentIdentities[entity.name]?.primary;
          const current = primaryOverrides[entity.name] ?? { field: "", namespace: "Email" };
          return (
            <div key={entity.name} className="rounded-lg border p-3 space-y-2">
              <div className="flex items-center justify-between">
                <span className="font-semibold">{entity.name}</span>
                {agentRec && (
                  <Badge variant="outline" className="text-xs">
                    AI 추천: {agentRec.field} ({agentRec.namespace})
                  </Badge>
                )}
              </div>
              <div className="grid grid-cols-2 gap-2">
                <div className="space-y-1">
                  <label className="text-xs font-medium text-muted-foreground">Primary 필드</label>
                  <input
                    className="w-full rounded border px-2 py-1 text-sm"
                    value={current.field}
                    placeholder="예: email_address"
                    onChange={(e) => updatePrimary(entity.name, "field", e.target.value)}
                  />
                </div>
                <div className="space-y-1">
                  <label className="text-xs font-medium text-muted-foreground">Namespace</label>
                  <select
                    className="w-full rounded border px-2 py-1 text-sm"
                    value={current.namespace}
                    onChange={(e) => updatePrimary(entity.name, "namespace", e.target.value)}
                  >
                    {NAMESPACES.map((ns) => (
                      <option key={ns} value={ns}>{ns}</option>
                    ))}
                  </select>
                </div>
              </div>
              {agentIdentities[entity.name]?.secondary && (
                <p className="text-xs text-muted-foreground">
                  Secondary: {agentIdentities[entity.name]?.secondary?.map((s) => `${s.field}(${s.namespace})`).join(", ")}
                </p>
              )}
            </div>
          );
        })}

        {/* Graph strategy */}
        <div className="space-y-2">
          <label className="text-sm font-semibold">Identity Graph 전략</label>
          <div className="grid grid-cols-2 gap-2">
            {GRAPH_STRATEGIES.map((g) => (
              <button
                key={g.value}
                type="button"
                onClick={() => setGraphStrategy(g.value)}
                className={`rounded-lg border-2 p-3 text-left transition-colors ${
                  graphStrategy === g.value ? "border-primary bg-primary/5" : "border-muted"
                }`}
              >
                <p className="text-sm font-medium">{g.label}</p>
                <p className="text-xs text-muted-foreground">{g.desc}</p>
              </button>
            ))}
          </div>
        </div>

        <Button onClick={handleSubmit} disabled={isAnalyzing || entities.length === 0} className="w-full">
          {isAnalyzing ? "분석 중..." : "AI 검수 실행"}
        </Button>
      </CardContent>
    </Card>
  );
}
