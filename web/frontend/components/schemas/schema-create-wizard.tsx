"use client";

import { useRouter } from "next/navigation";
import { useCallback, useRef, useState } from "react";
import { Alert, AlertDescription } from "@/components/ui/alert";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";
import { useGenerateSchema } from "@/hooks/useSchema";
import { apiClient } from "@/lib/api";
import type { SchemaDetailResponse } from "@/lib/types/schema";
import {
  ArrowLeft,
  ArrowRight,
  Bot,
  ChevronDown,
  ChevronRight,
  Download,
  FileJson,
  Loader2,
  Sparkles,
  Upload,
} from "lucide-react";
import { DataMappingStep, MappingSummaryBadges } from "./data-mapping-step";
import type { FieldMapping } from "./data-mapping-step";

const PROFILE_CLASS = "https://ns.adobe.com/xdm/context/profile";
const EVENT_CLASS = "https://ns.adobe.com/xdm/context/experienceevent";

const STEPS = [
  { id: "upload", label: "Upload sample" },
  { id: "map", label: "Map fields" },
  { id: "generate", label: "Generate draft" },
  { id: "review", label: "Review before AEP" },
];

interface SuggestResponse {
  class_id: string;
  class_reasoning: string;
  description: string;
}

export function SchemaCreateWizard() {
  const router = useRouter();
  const fileRef = useRef<HTMLInputElement>(null);

  // Step 1: Upload
  const [file, setFile] = useState<File | null>(null);
  const [title, setTitle] = useState("");
  const [description, setDescription] = useState("");
  const [classId, setClassId] = useState(PROFILE_CLASS);

  // File preview
  const [previewHeaders, setPreviewHeaders] = useState<string[]>([]);
  const [previewRows, setPreviewRows] = useState<Array<Record<string, string>>>([]);
  const [showPreview, setShowPreview] = useState(false);

  // AI suggest
  const [isSuggesting, setIsSuggesting] = useState(false);
  const [classReasoning, setClassReasoning] = useState("");

  // Step 2: Mapping
  const [mappings, setMappings] = useState<FieldMapping[]>([]);

  // Step 3+: Result
  const [result, setResult] = useState<SchemaDetailResponse | null>(null);

  // Step state: 0=upload, 1=map, 2=generate, 3=review
  const [step, setStep] = useState(0);

  const generate = useGenerateSchema();

  const parseFileForPreview = (f: File) => {
    const reader = new FileReader();
    reader.onload = (e) => {
      const text = e.target?.result as string;
      if (!text) return;
      try {
        if (f.name.toLowerCase().endsWith(".json")) {
          const parsed = JSON.parse(text);
          const rows = Array.isArray(parsed) ? parsed.slice(0, 5) : [parsed];
          const headers = Object.keys(rows[0] || {});
          setPreviewHeaders(headers);
          setPreviewRows(
            rows.map((r: Record<string, unknown>) =>
              Object.fromEntries(headers.map((h) => [h, r[h] != null ? String(r[h]) : ""]))
            )
          );
        } else {
          const lines = text.replace(/\r/g, "").split("\n").filter(Boolean);
          if (lines.length < 2) return;
          const headers = lines[0].split(",").map((h) => h.trim().replace(/^"|"$/g, ""));
          setPreviewHeaders(headers);
          const dataRows = lines.slice(1, 6).map((line) => {
            const vals = line.split(",").map((v) => v.trim().replace(/^"|"$/g, ""));
            return Object.fromEntries(headers.map((h, i) => [h, vals[i] ?? ""]));
          });
          setPreviewRows(dataRows);
        }
      } catch {
        // ignore parse errors — preview is optional
      }
    };
    reader.readAsText(f);
  };

  const onPickFile = (e: React.ChangeEvent<HTMLInputElement>) => {
    const f = e.target.files?.[0];
    setFile(f ?? null);
    setResult(null);
    setMappings([]);
    setStep(0);
    setClassReasoning("");
    setPreviewHeaders([]);
    setPreviewRows([]);
    setShowPreview(false);
    if (f) {
      if (!title) {
        const base = f.name.replace(/\.(csv|json)$/i, "");
        setTitle(base.replace(/[-_]/g, " "));
      }
      parseFileForPreview(f);
    }
  };

  const suggestMetadata = async () => {
    if (!file || !title.trim() || isSuggesting) return;
    setIsSuggesting(true);
    setClassReasoning("");
    try {
      const formData = new FormData();
      formData.append("file", file);
      formData.append("title", title.trim());
      const res = await apiClient.uploadFormData<SuggestResponse>("/api/schemas/suggest", formData);
      setClassId(res.class_id);
      setClassReasoning(res.class_reasoning);
      setDescription(res.description);
    } catch {
      // silently ignore — user can set manually
    } finally {
      setIsSuggesting(false);
    }
  };

  const goToMapping = () => {
    if (!file || !title.trim()) return;
    setStep(1);
  };

  const onSubmit = () => {
    if (!file || !title.trim()) return;
    setStep(2);
    generate.mutate(
      {
        file,
        title: title.trim(),
        description: description.trim() || undefined,
        class_id: classId,
      },
      {
        onSuccess: (data) => {
          setResult(data);
          setStep(3);
        },
        onError: () => {
          setStep(1); // back to mapping on error
        },
      }
    );
  };

  const downloadJson = useCallback(() => {
    if (!result?.definition) return;
    const blob = new Blob([JSON.stringify(result.definition, null, 2)], {
      type: "application/json",
    });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = `${result.name || "schema"}-draft.json`;
    a.click();
    URL.revokeObjectURL(url);
  }, [result]);

  const activeStep = step;

  return (
    <Card id="schema-wizard" className="border-primary/20 scroll-mt-24">
      <CardHeader>
        <div className="flex items-center gap-2">
          <Bot className="h-5 w-5 text-primary" />
          <CardTitle>Schema draft (agent)</CardTitle>
        </div>
        <CardDescription>
          Upload a CSV or JSON sample, map your source fields to XDM, then generate and save a
          schema draft. Review carefully before Schema Registry registration in AEP.
        </CardDescription>
      </CardHeader>
      <CardContent className="space-y-6">
        {/* Step indicator */}
        <div className="flex flex-wrap gap-2">
          {STEPS.map((s, i) => (
            <div
              key={s.id}
              className={`flex items-center gap-2 rounded-full border px-3 py-1 text-xs font-medium transition-colors ${
                i < activeStep
                  ? "border-emerald-300 bg-emerald-50 text-emerald-700"
                  : i === activeStep
                  ? "border-primary bg-primary/10 text-primary"
                  : "border-gray-200 text-gray-400"
              }`}
            >
              <span className="tabular-nums">{i + 1}</span>
              {s.label}
            </div>
          ))}
        </div>

        {/* ── Step 0: Upload ── */}
        {step === 0 && (
          <div className="space-y-4">
            <div className="grid gap-4 md:grid-cols-2">
              {/* File picker */}
              <div className="space-y-2">
                <Label>Sample file (.csv / .json)</Label>
                <input
                  ref={fileRef}
                  type="file"
                  accept=".csv,.json"
                  className="hidden"
                  onChange={onPickFile}
                />
                <Button
                  type="button"
                  variant="outline"
                  className="w-full justify-start gap-2"
                  onClick={() => fileRef.current?.click()}
                >
                  <Upload className="h-4 w-4" />
                  {file ? file.name : "Choose file"}
                </Button>
                {/* Preview toggle */}
                {file && previewHeaders.length > 0 && (
                  <button
                    type="button"
                    onClick={() => setShowPreview((v) => !v)}
                    className="flex items-center gap-1 text-xs text-muted-foreground hover:text-foreground transition-colors"
                  >
                    {showPreview ? (
                      <ChevronDown className="h-3.5 w-3.5" />
                    ) : (
                      <ChevronRight className="h-3.5 w-3.5" />
                    )}
                    {showPreview ? "Hide preview" : "Show data preview"}
                    <span className="text-gray-400 ml-0.5">({previewHeaders.length} columns)</span>
                  </button>
                )}
              </div>

              <div className="space-y-2">
                <Label htmlFor="schema-title">Schema title</Label>
                <Input
                  id="schema-title"
                  value={title}
                  onChange={(e) => setTitle(e.target.value)}
                  placeholder="e.g. Customer Profile"
                />
              </div>
            </div>

            {/* ── Data preview table ── */}
            {showPreview && previewRows.length > 0 && (
              <div className="rounded-md border overflow-x-auto text-xs animate-in slide-in-from-top-1 duration-150">
                <table className="w-full">
                  <thead>
                    <tr className="bg-muted/50 border-b">
                      {previewHeaders.map((h) => (
                        <th
                          key={h}
                          className="px-3 py-2 text-left font-medium text-muted-foreground whitespace-nowrap"
                        >
                          {h}
                        </th>
                      ))}
                    </tr>
                  </thead>
                  <tbody>
                    {previewRows.map((row, i) => (
                      <tr key={i} className={i % 2 === 0 ? "" : "bg-muted/20"}>
                        {previewHeaders.map((h) => (
                          <td
                            key={h}
                            className="px-3 py-1.5 text-gray-600 font-mono max-w-[180px] truncate"
                            title={row[h] || ""}
                          >
                            {row[h] || <span className="text-gray-300">—</span>}
                          </td>
                        ))}
                      </tr>
                    ))}
                  </tbody>
                </table>
                <p className="text-muted-foreground text-xs px-3 py-1.5 border-t bg-muted/20">
                  Preview: first {previewRows.length} row(s)
                </p>
              </div>
            )}

            {/* ── XDM class + AI Suggest ── */}
            <div className="space-y-2">
              <Label htmlFor="schema-class">XDM class</Label>
              <div className="flex gap-2">
                <select
                  id="schema-class"
                  value={classId}
                  onChange={(e) => setClassId(e.target.value)}
                  className="flex h-10 flex-1 rounded-md border border-input bg-background px-3 py-2 text-sm ring-offset-background focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
                >
                  <option value={PROFILE_CLASS}>Individual Profile</option>
                  <option value={EVENT_CLASS}>Experience Event</option>
                </select>
                <Button
                  type="button"
                  variant="outline"
                  size="sm"
                  onClick={suggestMetadata}
                  disabled={!file || !title.trim() || isSuggesting}
                  className="gap-1.5 whitespace-nowrap h-10 px-3"
                >
                  {isSuggesting ? (
                    <Loader2 className="h-3.5 w-3.5 animate-spin" />
                  ) : (
                    <Sparkles className="h-3.5 w-3.5" />
                  )}
                  AI Suggest
                </Button>
              </div>
              {classReasoning && (
                <p className="text-xs text-muted-foreground bg-muted/40 rounded-md px-3 py-2 leading-relaxed">
                  {classReasoning}
                </p>
              )}
            </div>

            {/* ── Description + auto-fill ── */}
            <div className="space-y-2">
              <div className="flex items-center justify-between">
                <Label htmlFor="schema-desc">Description (optional)</Label>
                {file && title.trim() && (
                  <button
                    type="button"
                    onClick={suggestMetadata}
                    disabled={isSuggesting}
                    className="flex items-center gap-1 text-xs text-primary hover:text-primary/80 disabled:opacity-50 transition-colors"
                  >
                    {isSuggesting ? (
                      <Loader2 className="h-3 w-3 animate-spin" />
                    ) : (
                      <Sparkles className="h-3 w-3" />
                    )}
                    Auto-fill
                  </button>
                )}
              </div>
              <Textarea
                id="schema-desc"
                value={description}
                onChange={(e) => setDescription(e.target.value)}
                rows={2}
                placeholder="Short note on how this data is used. Use AI Suggest to auto-fill."
              />
            </div>

            <Button
              onClick={goToMapping}
              disabled={!file || !title.trim()}
              className="gap-2"
            >
              Map fields
              <ArrowRight className="h-4 w-4" />
            </Button>
          </div>
        )}

        {/* ── Step 1: Map fields ── */}
        {step === 1 && file && (
          <div className="space-y-4">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm font-medium text-foreground">
                  Map source columns to XDM fields
                </p>
                <p className="text-xs text-muted-foreground mt-0.5">
                  AI-detected types are pre-filled. Edit field names, types, formats, and identities
                  before generating.
                </p>
              </div>
              <Button
                type="button"
                variant="ghost"
                size="sm"
                onClick={() => setStep(0)}
                className="gap-1.5 text-xs text-muted-foreground"
              >
                <ArrowLeft className="h-3.5 w-3.5" />
                Back
              </Button>
            </div>

            <DataMappingStep file={file} onMappingsChange={setMappings} />

            <div className="flex gap-2">
              <Button
                onClick={onSubmit}
                disabled={mappings.length === 0 || generate.isPending}
                className="gap-2"
              >
                {generate.isPending ? (
                  <Loader2 className="h-4 w-4 animate-spin" />
                ) : (
                  <Bot className="h-4 w-4" />
                )}
                Generate schema draft
              </Button>
            </div>
          </div>
        )}

        {/* ── Step 2: Generating ── */}
        {step === 2 && (
          <div className="flex flex-col items-center gap-4 py-10 text-muted-foreground">
            <Loader2 className="h-8 w-8 animate-spin text-primary" />
            <div className="text-center">
              <p className="text-sm font-medium text-foreground">Generating XDM schema draft…</p>
              <p className="text-xs mt-1">AI is analyzing your field mappings and sample data.</p>
            </div>
          </div>
        )}

        {/* ── Step 3: Review ── */}
        {step === 3 && result && (
          <div className="space-y-4">
            {generate.isError && (
              <Alert variant="destructive">
                <AlertDescription>
                  {generate.error instanceof Error ? generate.error.message : "Generation failed."}
                </AlertDescription>
              </Alert>
            )}

            <Alert className="border-emerald-200 bg-emerald-50">
              <FileJson className="h-4 w-4 text-emerald-600" />
              <AlertDescription className="text-emerald-900">
                Draft saved (local ID:{" "}
                <code className="text-xs">{result.aep_schema_id}</code>). Register in AEP only
                after approval.
              </AlertDescription>
            </Alert>

            {mappings.length > 0 && (
              <div className="space-y-1.5">
                <p className="text-xs font-medium text-muted-foreground uppercase tracking-wide">
                  Mapped fields
                </p>
                <MappingSummaryBadges mappings={mappings} />
              </div>
            )}

            <div className="flex flex-wrap gap-2">
              <Button type="button" variant="outline" onClick={downloadJson} className="gap-2">
                <Download className="h-4 w-4" />
                Download JSON
              </Button>
              <Button type="button" variant="secondary" onClick={() => router.push(`/schemas`)}>
                View in list
              </Button>
              <Button
                type="button"
                variant="ghost"
                onClick={() => {
                  setStep(0);
                  setResult(null);
                  setMappings([]);
                  setFile(null);
                  setTitle("");
                  setDescription("");
                  setClassReasoning("");
                  setPreviewHeaders([]);
                  setPreviewRows([]);
                  setShowPreview(false);
                }}
                className="text-xs text-muted-foreground"
              >
                Start over
              </Button>
            </div>
          </div>
        )}
      </CardContent>
    </Card>
  );
}
