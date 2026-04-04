"use client";

import React, { useRef, useState } from "react";
import { FileText, Layers, Upload } from "lucide-react";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Textarea } from "@/components/ui/textarea";
import type { ErdInputMode } from "@/lib/types/schema_wizard";

interface Step1ErdProps {
  onSubmit: (formData: FormData) => Promise<void>;
  isAnalyzing: boolean;
}

const MODES: { id: ErdInputMode; label: string; recommended?: boolean; icon: React.ReactNode; desc: string }[] = [
  {
    id: "file",
    label: "샘플 데이터 파일",
    recommended: true,
    icon: <Upload className="h-4 w-4" />,
    desc: "JSON/CSV 파일 업로드 → 에이전트가 ERD 자동 생성",
  },
  {
    id: "domain",
    label: "도메인 텍스트",
    icon: <Layers className="h-4 w-4" />,
    desc: "도메인 설명 입력 → AI가 엔티티 구조 생성",
  },
  {
    id: "mermaid",
    label: "Mermaid ERD",
    icon: <FileText className="h-4 w-4" />,
    desc: "Mermaid erDiagram 직접 입력 → 파서가 엔티티 추출",
  },
];

export function Step1Erd({ onSubmit, isAnalyzing }: Step1ErdProps) {
  const [mode, setMode] = useState<ErdInputMode>("file");
  const [file, setFile] = useState<File | null>(null);
  const [domainText, setDomainText] = useState("");
  const [mermaidText, setMermaidText] = useState("");
  const [dragActive, setDragActive] = useState(false);
  const fileInputRef = useRef<HTMLInputElement>(null);

  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault();
    setDragActive(false);
    const dropped = e.dataTransfer.files[0];
    if (dropped) setFile(dropped);
  };

  const handleSubmit = () => {
    const fd = new FormData();
    const stepData: Record<string, string> = { mode };
    if (mode === "domain") stepData.domain_description = domainText;
    if (mode === "mermaid") stepData.mermaid_erd = mermaidText;
    fd.append("step_data", JSON.stringify(stepData));
    if (mode === "file" && file) fd.append("file", file);
    onSubmit(fd);
  };

  const canSubmit =
    !isAnalyzing &&
    ((mode === "file" && !!file) ||
      (mode === "domain" && domainText.trim().length > 0) ||
      (mode === "mermaid" && mermaidText.trim().length > 0));

  return (
    <Card>
      <CardHeader>
        <CardTitle>Phase 1: ERD 설계</CardTitle>
        <CardDescription>
          데이터 엔티티 구조를 정의합니다. 아래 3가지 입력 방식 중 하나를 선택하세요.
        </CardDescription>
      </CardHeader>
      <CardContent className="space-y-5">
        {/* Mode selector */}
        <div className="grid grid-cols-3 gap-3">
          {MODES.map((m) => (
            <button
              key={m.id}
              type="button"
              onClick={() => setMode(m.id)}
              className={`relative flex flex-col items-start gap-1 rounded-lg border-2 p-3 text-left transition-colors ${
                mode === m.id
                  ? "border-primary bg-primary/5"
                  : "border-muted hover:border-muted-foreground/40"
              }`}
            >
              {m.recommended && (
                <Badge className="absolute right-2 top-2 bg-primary text-[10px]">추천</Badge>
              )}
              <div className="flex items-center gap-1.5 font-medium text-sm">
                {m.icon} {m.label}
              </div>
              <p className="text-xs text-muted-foreground">{m.desc}</p>
            </button>
          ))}
        </div>

        {/* Input area */}
        {mode === "file" && (
          <div
            className={`rounded-lg border-2 border-dashed p-8 text-center transition-colors ${
              dragActive ? "border-primary bg-primary/5" : "border-muted-foreground/25"
            }`}
            onDragEnter={(e) => { e.preventDefault(); setDragActive(true); }}
            onDragLeave={() => setDragActive(false)}
            onDragOver={(e) => e.preventDefault()}
            onDrop={handleDrop}
          >
            <Upload className="mx-auto mb-3 h-10 w-10 text-muted-foreground" />
            {file ? (
              <div className="space-y-2">
                <p className="font-medium text-sm">{file.name}</p>
                <Button variant="ghost" size="sm" onClick={() => setFile(null)}>파일 변경</Button>
              </div>
            ) : (
              <div className="space-y-2">
                <p className="text-sm text-muted-foreground">파일을 드래그하거나</p>
                <Button variant="outline" size="sm" onClick={() => fileInputRef.current?.click()}>
                  파일 선택
                </Button>
                <input
                  ref={fileInputRef}
                  type="file"
                  accept=".json,.csv"
                  className="hidden"
                  onChange={(e) => e.target.files?.[0] && setFile(e.target.files[0])}
                />
                <p className="text-xs text-muted-foreground">JSON, CSV 지원</p>
              </div>
            )}
          </div>
        )}

        {mode === "domain" && (
          <div className="space-y-2">
            <label className="text-sm font-medium">도메인 설명</label>
            <Textarea
              rows={4}
              placeholder="예: B2C 이커머스 — 고객, 주문, 상품, 이벤트 데이터를 포함합니다."
              value={domainText}
              onChange={(e) => setDomainText(e.target.value)}
            />
          </div>
        )}

        {mode === "mermaid" && (
          <div className="space-y-2">
            <label className="text-sm font-medium">Mermaid ERD</label>
            <Textarea
              rows={10}
              className="font-mono text-xs"
              placeholder={`erDiagram\n  CUSTOMERS {\n    string customer_id PK\n    string email\n  }\n  ORDERS {\n    string order_id PK\n    string customer_id FK\n    datetime created_at\n  }\n  ORDERS }o--|| CUSTOMERS : "belongs_to"`}
              value={mermaidText}
              onChange={(e) => setMermaidText(e.target.value)}
            />
          </div>
        )}

        <Button onClick={handleSubmit} disabled={!canSubmit} className="w-full">
          {isAnalyzing ? "에이전트 분석 중..." : "AI 분석 실행"}
        </Button>
      </CardContent>
    </Card>
  );
}
