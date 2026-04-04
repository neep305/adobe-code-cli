"use client";

import React, { useState } from "react";
import { AlertTriangle } from "lucide-react";
import { Alert, AlertDescription } from "@/components/ui/alert";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import type { EntityDefinition } from "@/lib/types/schema_wizard";

interface Step6TypePreprocessingProps {
  entities: EntityDefinition[];
  agentOutput: Record<string, unknown>;
  onSubmit: (formData: FormData) => Promise<void>;
  isAnalyzing: boolean;
}

const XDM_TYPES = ["string", "integer", "number", "boolean", "object", "array", "date", "date-time"];
const XDM_FORMATS = ["", "email", "uri", "date", "date-time", "uuid"];

export function Step6TypePreprocessing({ entities, agentOutput, onSubmit, isAnalyzing }: Step6TypePreprocessingProps) {
  const fieldTypes = (agentOutput.field_types as Record<string, { type: string; format: string | null }>) ?? {};
  const epochFields = (agentOutput.epoch_fields as string[]) ?? [];
  const phoneFields = (agentOutput.phone_fields as string[]) ?? [];
  const boolFields = (agentOutput.bool_variant_fields as string[]) ?? [];

  const [overrides, setOverrides] = useState<Record<string, { type: string; format: string }>>(() => {
    const init: Record<string, { type: string; format: string }> = {};
    for (const entity of entities) {
      for (const field of entity.fields) {
        const key = `${entity.name}.${field.name}`;
        const detected = fieldTypes[key] ?? { type: field.xdm_type ?? "string", format: field.xdm_format ?? "" };
        init[key] = { type: detected.type, format: detected.format ?? "" };
      }
    }
    return init;
  });

  const update = (key: string, prop: "type" | "format", val: string) => {
    setOverrides((prev) => ({ ...prev, [key]: { ...prev[key], [prop]: val } }));
  };

  const handleSubmit = () => {
    const fd = new FormData();
    fd.append("step_data", JSON.stringify({ type_overrides: overrides }));
    onSubmit(fd);
  };

  return (
    <Card>
      <CardHeader>
        <CardTitle>Phase 6: 타입 & 전처리</CardTitle>
        <CardDescription>
          필드 타입을 확인하고 전처리가 필요한 필드를 식별합니다.
        </CardDescription>
      </CardHeader>
      <CardContent className="space-y-4">
        {/* Preprocessing alerts */}
        {epochFields.length > 0 && (
          <Alert>
            <AlertTriangle className="h-4 w-4" />
            <AlertDescription className="text-xs">
              <span className="font-semibold">epoch timestamp 변환 필요:</span>{" "}
              {epochFields.join(", ")} — ISO 8601로 변환 후 ingestion
            </AlertDescription>
          </Alert>
        )}
        {phoneFields.length > 0 && (
          <Alert>
            <AlertTriangle className="h-4 w-4" />
            <AlertDescription className="text-xs">
              <span className="font-semibold">Phone E.164 정규화 필요:</span>{" "}
              {phoneFields.join(", ")}
            </AlertDescription>
          </Alert>
        )}
        {boolFields.length > 0 && (
          <Alert>
            <AlertTriangle className="h-4 w-4" />
            <AlertDescription className="text-xs">
              <span className="font-semibold">Boolean variant 변환 필요:</span>{" "}
              {boolFields.join(", ")} — yes/no, 0/1 등을 true/false로 변환
            </AlertDescription>
          </Alert>
        )}

        {/* Field type table */}
        {entities.map((entity) => (
          <div key={entity.name} className="space-y-2">
            <p className="font-semibold text-sm">{entity.name}</p>
            <div className="rounded-lg border overflow-hidden">
              <table className="w-full text-xs">
                <thead className="bg-muted/50">
                  <tr>
                    <th className="px-3 py-2 text-left font-medium">필드명</th>
                    <th className="px-3 py-2 text-left font-medium">XDM 타입</th>
                    <th className="px-3 py-2 text-left font-medium">포맷</th>
                    <th className="px-3 py-2 text-left font-medium">전처리</th>
                  </tr>
                </thead>
                <tbody>
                  {entity.fields.map((field) => {
                    const key = `${entity.name}.${field.name}`;
                    const current = overrides[key] ?? { type: field.xdm_type, format: "" };
                    const needsPrep =
                      epochFields.includes(key) || phoneFields.includes(key) || boolFields.includes(key);
                    return (
                      <tr key={key} className="border-t">
                        <td className="px-3 py-1.5 font-mono">{field.name}</td>
                        <td className="px-3 py-1.5">
                          <select
                            className="rounded border text-xs px-1.5 py-0.5"
                            value={current.type}
                            onChange={(e) => update(key, "type", e.target.value)}
                          >
                            {XDM_TYPES.map((t) => <option key={t} value={t}>{t}</option>)}
                          </select>
                        </td>
                        <td className="px-3 py-1.5">
                          <select
                            className="rounded border text-xs px-1.5 py-0.5"
                            value={current.format}
                            onChange={(e) => update(key, "format", e.target.value)}
                          >
                            {XDM_FORMATS.map((f) => <option key={f} value={f}>{f || "없음"}</option>)}
                          </select>
                        </td>
                        <td className="px-3 py-1.5">
                          {needsPrep && (
                            <Badge className="bg-yellow-100 text-yellow-800 text-[10px]">전처리 필요</Badge>
                          )}
                        </td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </div>
          </div>
        ))}

        <Button onClick={handleSubmit} disabled={isAnalyzing || entities.length === 0} className="w-full">
          {isAnalyzing ? "분석 중..." : "AI 검수 실행"}
        </Button>
      </CardContent>
    </Card>
  );
}
