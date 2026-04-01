"use client";

import React, { useState } from "react";
import { Upload, AlertCircle, CheckCircle, Loader2 } from "lucide-react";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Textarea } from "@/components/ui/textarea";
import { Checkbox } from "@/components/ui/checkbox";
import { Alert, AlertDescription } from "@/components/ui/alert";
import { Badge } from "@/components/ui/badge";
import { DashboardLayout } from "@/components/dashboard-layout";
import MarkdownViewer from "@/components/analyze/markdown-viewer";
import { apiClient, ApiError } from "@/lib/api";

interface AgentResult {
  agent: string;
  status: string;
  confidence: number;
  execution_time?: number;
  metrics?: Record<string, any>;
}

interface AnalyzeResult {
  analysis_id: string;
  route: string;
  agents: string[];
  confidence: number;
  warnings: string[];
  json_path: string;
  md_path: string;
  agent_results: AgentResult[];
  created_at: string;
}

export default function AnalyzePage() {
  const [files, setFiles] = useState<File[]>([]);
  const [intent, setIntent] = useState("");
  const [verbose, setVerbose] = useState(false);
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState<AnalyzeResult | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [dragActive, setDragActive] = useState(false);

  const handleDrag = (e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    if (e.type === "dragenter" || e.type === "dragover") {
      setDragActive(true);
    } else if (e.type === "dragleave") {
      setDragActive(false);
    }
  };

  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    setDragActive(false);

    if (e.dataTransfer.files && e.dataTransfer.files.length > 0) {
      handleFileSelect(Array.from(e.dataTransfer.files));
    }
  };

  const handleFileSelect = (selectedFiles: File[]) => {
    const validExtensions = [".json", ".csv"];
    const invalidFiles = selectedFiles.filter((selectedFile) => {
      const extension = selectedFile.name.substring(selectedFile.name.lastIndexOf("."));
      return !validExtensions.includes(extension.toLowerCase());
    });

    if (invalidFiles.length > 0) {
      setError("Invalid file type. Please upload JSON or CSV files.");
      return;
    }

    setFiles((previousFiles) => {
      const merged = [...previousFiles, ...selectedFiles];
      const uniqueByName = new Map<string, File>();
      for (const file of merged) {
        uniqueByName.set(file.name, file);
      }
      return Array.from(uniqueByName.values());
    });
    setError(null);
  };

  const handleFileInput = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files && e.target.files.length > 0) {
      handleFileSelect(Array.from(e.target.files));
      e.target.value = "";
    }
  };

  const handleRemoveFile = (filename: string) => {
    setFiles((previousFiles) => previousFiles.filter((file) => file.name !== filename));
  };

  const handleClearFiles = () => {
    setFiles([]);
  };

  const handleSubmit = async () => {
    if (files.length === 0 || !intent.trim()) {
      setError("Please select files and provide analysis intent.");
      return;
    }

    setLoading(true);
    setError(null);
    setResult(null);

    try {
      const formData = new FormData();
      files.forEach((file) => {
        formData.append("files", file);
      });
      formData.append("intent", intent);
      formData.append("verbose", verbose.toString());

      const data = await apiClient.uploadFormData<AnalyzeResult>("/api/analyze/run", formData);
      setResult(data);
    } catch (err) {
      if (err instanceof ApiError) {
        setError(err.message);
      } else if (err instanceof Error) {
        setError(err.message);
      } else {
        setError("An error occurred");
      }
    } finally {
      setLoading(false);
    }
  };

  const getConfidenceBadge = (confidence: number) => {
    if (confidence >= 0.7) {
      return <Badge className="bg-green-500">High ({(confidence * 100).toFixed(0)}%)</Badge>;
    } else if (confidence >= 0.5) {
      return <Badge className="bg-yellow-500">Medium ({(confidence * 100).toFixed(0)}%)</Badge>;
    } else {
      return <Badge className="bg-red-500">Low ({(confidence * 100).toFixed(0)}%)</Badge>;
    }
  };

  return (
    <DashboardLayout>
      <div className="container mx-auto py-8 space-y-6">
        <div>
          <h1 className="text-3xl font-bold mb-2">Data Analysis</h1>
          <p className="text-muted-foreground">
            Upload your data file and describe what you want to analyze. Our AI agents will process and generate insights.
          </p>
        </div>

      {/* File Upload Card */}
      <Card>
        <CardHeader>
          <CardTitle>Upload Data File</CardTitle>
          <CardDescription>
            Upload one or more JSON and CSV files for a single merged analysis. Maximum size: 50MB per file.
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          <div
            className={`border-2 border-dashed rounded-lg p-8 text-center transition-colors ${
              dragActive ? "border-primary bg-primary/5" : "border-muted-foreground/25"
            }`}
            onDragEnter={handleDrag}
            onDragLeave={handleDrag}
            onDragOver={handleDrag}
            onDrop={handleDrop}
          >
            <Upload className="mx-auto h-12 w-12 text-muted-foreground mb-4" />
            <div className="space-y-2">
              <p className="text-sm text-muted-foreground">
                Drag and drop your file here, or
              </p>
              <label htmlFor="file-upload">
                <Button variant="outline" asChild>
                  <span>Browse Files</span>
                </Button>
                <input
                  id="file-upload"
                  type="file"
                  accept=".json,.csv"
                  multiple
                  onChange={handleFileInput}
                  className="hidden"
                />
              </label>
            </div>
            {files.length > 0 && (
              <div className="mt-4 space-y-3">
                <div className="flex items-center justify-center gap-2">
                  <CheckCircle className="h-5 w-5 text-green-500" />
                  <span className="text-sm font-medium">{files.length} file(s) selected</span>
                </div>
                <div className="flex flex-wrap justify-center gap-2">
                  {files.map((selectedFile) => (
                    <Badge key={selectedFile.name} variant="secondary" className="gap-2 px-3 py-1">
                      <span>{selectedFile.name}</span>
                      <button
                        type="button"
                        onClick={() => handleRemoveFile(selectedFile.name)}
                        className="text-xs font-semibold"
                        aria-label={`Remove ${selectedFile.name}`}
                      >
                        x
                      </button>
                    </Badge>
                  ))}
                </div>
                <div className="text-center">
                  <Button type="button" variant="ghost" size="sm" onClick={handleClearFiles}>
                    Clear all files
                  </Button>
                </div>
              </div>
            )}
          </div>

          {/* Intent Input */}
          <div className="space-y-2">
            <label htmlFor="intent" className="text-sm font-medium">
              Analysis Intent
            </label>
            <Textarea
              id="intent"
              placeholder="Describe what you want to analyze... (e.g., 'Analyze customer purchase patterns', 'Generate XDM schema for this data', 'Check data quality and suggest validation rules')"
              value={intent}
              onChange={(e) => setIntent(e.target.value)}
              rows={4}
              className="resize-none"
            />
          </div>

          {/* Verbose Checkbox */}
          <div className="flex items-center space-x-2">
            <Checkbox
              id="verbose"
              checked={verbose}
              onCheckedChange={(checked) => setVerbose(checked as boolean)}
            />
            <label
              htmlFor="verbose"
              className="text-sm font-medium leading-none peer-disabled:cursor-not-allowed peer-disabled:opacity-70"
            >
              Enable verbose logging (show detailed agent execution steps)
            </label>
          </div>

          {/* Submit Button */}
          <Button
            onClick={handleSubmit}
            disabled={loading || files.length === 0 || !intent.trim()}
            className="w-full"
          >
            {loading ? (
              <>
                <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                Analyzing...
              </>
            ) : (
              "Run Analysis"
            )}
          </Button>
        </CardContent>
      </Card>

      {/* Error Alert */}
      {error && (
        <Alert variant="destructive">
          <AlertCircle className="h-4 w-4" />
          <AlertDescription>{error}</AlertDescription>
        </Alert>
      )}

      {/* Result Display */}
      {result && (
        <div className="space-y-6">
          {/* Summary Card */}
          <Card>
            <CardHeader>
              <CardTitle>Analysis Results</CardTitle>
              <CardDescription>
                Generated at {new Date(result.created_at).toLocaleString()}
              </CardDescription>
            </CardHeader>
            <CardContent className="space-y-4">
              <div className="grid grid-cols-2 gap-4">
                <div>
                  <p className="text-sm font-medium text-muted-foreground">Route</p>
                  <p className="text-lg font-semibold capitalize">{result.route}</p>
                </div>
                <div>
                  <p className="text-sm font-medium text-muted-foreground">Confidence</p>
                  <div className="mt-1">{getConfidenceBadge(result.confidence)}</div>
                </div>
              </div>

              <div>
                <p className="text-sm font-medium text-muted-foreground mb-2">Agents Used</p>
                <div className="flex flex-wrap gap-2">
                  {result.agents.map((agent) => (
                    <Badge key={agent} variant="outline">
                      {agent}
                    </Badge>
                  ))}
                </div>
              </div>

              {result.warnings.length > 0 && (
                <Alert>
                  <AlertCircle className="h-4 w-4" />
                  <AlertDescription>
                    <ul className="list-disc list-inside space-y-1">
                      {result.warnings.map((warning, index) => (
                        <li key={index} className="text-sm">{warning}</li>
                      ))}
                    </ul>
                  </AlertDescription>
                </Alert>
              )}

              {/* Agent Results */}
              {verbose && result.agent_results.length > 0 && (
                <div>
                  <p className="text-sm font-medium text-muted-foreground mb-2">Agent Execution Details</p>
                  <div className="space-y-2">
                    {result.agent_results.map((agentResult, index) => (
                      <div key={index} className="border rounded-lg p-3">
                        <div className="flex items-center justify-between mb-2">
                          <span className="font-medium">{agentResult.agent}</span>
                          <Badge variant={agentResult.status === "success" ? "default" : "destructive"}>
                            {agentResult.status}
                          </Badge>
                        </div>
                        <div className="grid grid-cols-2 gap-2 text-sm text-muted-foreground">
                          <div>
                            <span>Confidence: </span>
                            <span className="font-medium">{(agentResult.confidence * 100).toFixed(0)}%</span>
                          </div>
                          {agentResult.execution_time && (
                            <div>
                              <span>Execution: </span>
                              <span className="font-medium">{agentResult.execution_time.toFixed(2)}s</span>
                            </div>
                          )}
                        </div>
                      </div>
                    ))}
                  </div>
                </div>
              )}
            </CardContent>
          </Card>

          {/* Markdown Viewer */}
          <Card>
            <CardHeader>
              <CardTitle>Analysis Report</CardTitle>
            </CardHeader>
            <CardContent>
              <MarkdownViewer analysisId={result.analysis_id} mdPath={result.md_path} />
            </CardContent>
          </Card>
        </div>
      )}
      </div>
    </DashboardLayout>
  );
}
