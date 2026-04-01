"use client";

import { useState, useCallback, useRef, Suspense } from "react";
import { useSearchParams, useRouter } from "next/navigation";
import { useBatches, useBatch, useCreateBatch, useUploadFile, useCompleteBatch } from "@/hooks/useBatch";
import { useBatchWebSocket } from "@/hooks/useBatchWebSocket";
import { useDatasets } from "@/hooks/useDataset";
import { DashboardLayout } from "@/components/dashboard-layout";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Alert, AlertDescription } from "@/components/ui/alert";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { BatchStatusBadge } from "@/components/batch/batch-status-badge";
import { BatchProgressBar } from "@/components/batch/batch-progress-bar";
import { BatchMetricsCard } from "@/components/batch/batch-metrics-card";
import { formatDistanceToNow } from "date-fns";
import Link from "next/link";
import { Plus, X, Upload, CheckCircle, Loader2, ArrowLeft, Wifi, WifiOff } from "lucide-react";

/* ─────────────────── Create Batch Modal ─────────────────── */

interface CreateBatchModalProps {
  onClose: () => void;
}

function CreateBatchModal({ onClose }: CreateBatchModalProps) {
  const { data: datasetsResponse, isLoading: datasetsLoading } = useDatasets();
  const createBatch = useCreateBatch();
  const uploadFile = useUploadFile();
  const completeBatch = useCompleteBatch();

  type ModalStep = "select-dataset" | "upload-files" | "done";
  const [step, setStep] = useState<ModalStep>("select-dataset");
  const [selectedDatasetId, setSelectedDatasetId] = useState<number | null>(null);
  const [createdBatchId, setCreatedBatchId] = useState<string | null>(null);
  const [files, setFiles] = useState<File[]>([]);
  const [uploadProgress, setUploadProgress] = useState<Record<string, "pending" | "uploading" | "done" | "error">>({});
  const [isDragging, setIsDragging] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);
  const datasets = datasetsResponse?.datasets ?? [];

  const handleSelectDataset = async () => {
    if (!selectedDatasetId) return;
    try {
      const batch = await createBatch.mutateAsync({ dataset_id: selectedDatasetId });
      setCreatedBatchId(batch.aep_batch_id);
      setStep("upload-files");
      setError(null);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to create batch");
    }
  };

  const addFiles = (newFiles: FileList | null) => {
    if (!newFiles) return;
    const arr = Array.from(newFiles);
    setFiles((prev) => {
      const existing = new Set(prev.map((f) => f.name));
      return [...prev, ...arr.filter((f) => !existing.has(f.name))];
    });
  };

  const handleDrop = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    setIsDragging(false);
    addFiles(e.dataTransfer.files);
  }, []);

  const handleUploadAll = async () => {
    if (!createdBatchId || files.length === 0) return;
    setError(null);
    const init: Record<string, "pending" | "uploading" | "done" | "error"> = {};
    files.forEach((f) => { init[f.name] = "pending"; });
    setUploadProgress(init);

    for (const file of files) {
      setUploadProgress((prev) => ({ ...prev, [file.name]: "uploading" }));
      try {
        await uploadFile.mutateAsync({ batchId: createdBatchId, file });
        setUploadProgress((prev) => ({ ...prev, [file.name]: "done" }));
      } catch {
        setUploadProgress((prev) => ({ ...prev, [file.name]: "error" }));
      }
    }
    try {
      await completeBatch.mutateAsync({ batchId: createdBatchId });
      setStep("done");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to complete batch");
    }
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50">
      <div className="bg-white rounded-xl shadow-2xl w-full max-w-lg mx-4 relative">
        <div className="flex items-center justify-between p-6 border-b">
          <div>
            <h2 className="text-xl font-bold">Create New Batch</h2>
            <div className="flex items-center gap-2 mt-1">
              {(["select-dataset", "upload-files", "done"] as ModalStep[]).map((s, i) => (
                <span key={s} className="flex items-center gap-1">
                  {i > 0 && <span className="text-gray-300">›</span>}
                  <span className={`text-xs font-medium ${step === s ? "text-primary" : (i < ["select-dataset", "upload-files", "done"].indexOf(step)) ? "text-green-600" : "text-gray-400"}`}>
                    {s === "select-dataset" ? "Select Dataset" : s === "upload-files" ? "Upload Files" : "Complete"}
                  </span>
                </span>
              ))}
            </div>
          </div>
          <button onClick={onClose} className="text-gray-400 hover:text-gray-600"><X className="w-5 h-5" /></button>
        </div>

        <div className="p-6">
          {error && <Alert variant="destructive" className="mb-4"><AlertDescription>{error}</AlertDescription></Alert>}

          {step === "select-dataset" && (
            <div className="space-y-4">
              <p className="text-sm text-gray-600">Choose the dataset to ingest data into:</p>
              {datasetsLoading ? (
                <p className="text-center text-gray-500 py-4">Loading datasets...</p>
              ) : datasets.length === 0 ? (
                <p className="text-center text-gray-400 py-4">No datasets available</p>
              ) : (
                <div className="space-y-2 max-h-64 overflow-y-auto">
                  {datasets.map((ds) => (
                    <button key={ds.id} onClick={() => setSelectedDatasetId(ds.id)}
                      className={`w-full text-left px-4 py-3 rounded-lg border transition-colors ${selectedDatasetId === ds.id ? "border-primary bg-primary/5" : "border-gray-200 hover:border-gray-300 hover:bg-gray-50"}`}>
                      <div className="flex items-center justify-between">
                        <p className="font-medium text-sm">{ds.name}</p>
                        {ds.state && <Badge variant="outline" className="text-xs">{ds.state}</Badge>}
                      </div>
                      <p className="text-xs text-gray-500 mt-0.5 font-mono">{ds.aep_dataset_id?.slice(0, 12)}...</p>
                    </button>
                  ))}
                </div>
              )}
              <Button onClick={handleSelectDataset} disabled={!selectedDatasetId || createBatch.isPending} className="w-full">
                {createBatch.isPending ? <><Loader2 className="w-4 h-4 mr-2 animate-spin" />Creating Batch...</> : "Create Batch & Continue"}
              </Button>
            </div>
          )}

          {step === "upload-files" && (
            <div className="space-y-4">
              <p className="text-sm text-gray-600">Batch ID: <code className="font-mono text-xs bg-gray-100 px-1 py-0.5 rounded">{createdBatchId?.slice(0, 16)}...</code></p>
              <div onDrop={handleDrop} onDragOver={(e) => { e.preventDefault(); setIsDragging(true); }} onDragLeave={() => setIsDragging(false)} onClick={() => fileInputRef.current?.click()}
                className={`border-2 border-dashed rounded-lg p-8 text-center cursor-pointer transition-colors ${isDragging ? "border-primary bg-primary/5" : "border-gray-300 hover:border-gray-400"}`}>
                <Upload className="w-8 h-8 mx-auto text-gray-400 mb-2" />
                <p className="text-sm font-medium">Drag & drop files or click to browse</p>
                <p className="text-xs text-gray-500 mt-1">JSON, Parquet, or CSV files</p>
                <input ref={fileInputRef} type="file" multiple accept=".json,.parquet,.csv" className="hidden" onChange={(e) => addFiles(e.target.files)} />
              </div>
              {files.length > 0 && (
                <div className="space-y-1 max-h-40 overflow-y-auto">
                  {files.map((file) => {
                    const progress = uploadProgress[file.name];
                    return (
                      <div key={file.name} className="flex items-center justify-between text-sm px-3 py-2 bg-gray-50 rounded">
                        <span className="truncate max-w-xs">{file.name}</span>
                        <div className="flex items-center gap-2 ml-2">
                          <span className="text-xs text-gray-500">{(file.size / 1024).toFixed(1)} KB</span>
                          {progress === "uploading" && <Loader2 className="w-3 h-3 animate-spin text-primary" />}
                          {progress === "done" && <CheckCircle className="w-3 h-3 text-green-600" />}
                          {progress === "error" && <X className="w-3 h-3 text-red-600" />}
                          {!progress && <button onClick={(e) => { e.stopPropagation(); setFiles((prev) => prev.filter((f) => f.name !== file.name)); }} className="text-gray-400 hover:text-red-500"><X className="w-3 h-3" /></button>}
                        </div>
                      </div>
                    );
                  })}
                </div>
              )}
              <Button onClick={handleUploadAll} disabled={files.length === 0 || uploadFile.isPending || completeBatch.isPending} className="w-full">
                {uploadFile.isPending || completeBatch.isPending ? <><Loader2 className="w-4 h-4 mr-2 animate-spin" />Uploading...</> : <><Upload className="w-4 h-4 mr-2" />Upload {files.length} file{files.length !== 1 ? "s" : ""}</>}
              </Button>
            </div>
          )}

          {step === "done" && (
            <div className="text-center py-6 space-y-4">
              <CheckCircle className="w-16 h-16 text-green-500 mx-auto" />
              <div>
                <h3 className="text-lg font-bold text-green-700">Batch Submitted!</h3>
                <p className="text-sm text-gray-600 mt-1">Your batch is being processed. It may take a few minutes.</p>
              </div>
              <Button onClick={onClose}>Close</Button>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

/* ─────────────────── Batch Detail View ─────────────────── */

function BatchDetail({ id }: { id: string }) {
  const router = useRouter();
  const { data: batch, isLoading, error } = useBatch(id);
  const { isConnected, error: wsError } = useBatchWebSocket(id);

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div className="flex items-center space-x-4">
          <button onClick={() => router.push("/batches")} className="text-gray-500 hover:text-gray-700">
            <ArrowLeft className="h-6 w-6" />
          </button>
          <div>
            <h1 className="text-3xl font-bold">Batch Details</h1>
            {batch && <p className="text-gray-500 mt-1 font-mono text-sm">{batch.aep_batch_id}</p>}
          </div>
        </div>
        <div>
          {isConnected ? (
            <Badge variant="default" className="flex items-center gap-1 bg-green-500"><Wifi className="h-3 w-3" />Live Updates</Badge>
          ) : (
            <Badge variant="outline" className="flex items-center gap-1"><WifiOff className="h-3 w-3" />Polling</Badge>
          )}
        </div>
      </div>

      {error && <Alert variant="destructive"><AlertDescription>Failed to load batch: {error instanceof Error ? error.message : "Unknown error"}</AlertDescription></Alert>}
      {wsError && <Alert><AlertDescription>WebSocket error: {wsError}. Falling back to polling.</AlertDescription></Alert>}

      {isLoading ? (
        <Card><CardContent className="py-8"><p className="text-center text-gray-500">Loading batch details...</p></CardContent></Card>
      ) : batch ? (
        <div className="grid gap-6 lg:grid-cols-3">
          <div className="lg:col-span-2 space-y-6">
            <Card>
              <CardHeader>
                <div className="flex items-center justify-between">
                  <CardTitle>Status</CardTitle>
                  <BatchStatusBadge status={batch.status} />
                </div>
              </CardHeader>
              <CardContent className="space-y-4">
                <BatchProgressBar status={batch.status} progressPercent={batch.progress_percent} filesUploaded={batch.files_uploaded} filesCount={batch.files_count} />
                <div className="grid grid-cols-2 gap-4 text-sm pt-4 border-t">
                  <div><p className="text-gray-500">Dataset</p><p className="font-medium">{batch.dataset_name ?? `ID: ${batch.dataset_id}`}</p></div>
                  <div><p className="text-gray-500">Dataset ID</p><p className="font-medium">{batch.dataset_id}</p></div>
                </div>
                {batch.error_message && <Alert variant="destructive"><AlertDescription>{batch.error_message}</AlertDescription></Alert>}
              </CardContent>
            </Card>
            {batch.errors && batch.errors.length > 0 && (
              <Card>
                <CardHeader><CardTitle>Errors</CardTitle></CardHeader>
                <CardContent>
                  <div className="space-y-2">
                    {batch.errors.map((err, idx) => (
                      <div key={idx} className="p-3 bg-red-50 rounded-md border border-red-200">
                        <p className="font-medium text-red-900">{err.code}</p>
                        <p className="text-sm text-red-700">{err.message}</p>
                      </div>
                    ))}
                  </div>
                </CardContent>
              </Card>
            )}
          </div>
          <div>
            <BatchMetricsCard recordsProcessed={batch.records_processed} recordsFailed={batch.records_failed} durationSeconds={batch.duration_seconds} createdAt={batch.created_at} completedAt={batch.completed_at} />
          </div>
        </div>
      ) : (
        <Card><CardContent className="py-8"><p className="text-center text-gray-500">Batch not found</p></CardContent></Card>
      )}
    </div>
  );
}

/* ─────────────────── Batch List View ─────────────────── */

function BatchList({ onNewBatch }: { onNewBatch: () => void }) {
  const { data: batches, isLoading, error } = useBatches();

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold">Batches</h1>
          <p className="text-gray-500 mt-2">Monitor your data ingestion batches and their status</p>
        </div>
        <Button onClick={onNewBatch} className="flex items-center gap-2"><Plus className="w-4 h-4" />New Batch</Button>
      </div>

      {error && <Alert variant="destructive"><AlertDescription>Failed to load batches: {error instanceof Error ? error.message : "Unknown error"}</AlertDescription></Alert>}

      {isLoading ? (
        <Card><CardContent className="py-8"><p className="text-center text-gray-500">Loading batches...</p></CardContent></Card>
      ) : batches && batches.length > 0 ? (
        <div className="grid gap-4">
          {batches.map((batch) => (
            <Link key={batch.id} href={`/batches?id=${batch.id}`}>
              <Card className="hover:shadow-lg transition-shadow cursor-pointer">
                <CardHeader>
                  <div className="flex items-center justify-between">
                    <CardTitle className="text-lg">Batch {batch.aep_batch_id.slice(0, 8)}...</CardTitle>
                    <BatchStatusBadge status={batch.status} />
                  </div>
                </CardHeader>
                <CardContent>
                  <div className="grid grid-cols-2 md:grid-cols-4 gap-4 text-sm">
                    <div><p className="text-gray-500">Dataset</p><p className="font-medium">{batch.dataset_name ?? `Dataset ${batch.dataset_id}`}</p></div>
                    <div><p className="text-gray-500">Files</p><p className="font-medium">{batch.files_uploaded} / {batch.files_count}</p></div>
                    <div><p className="text-gray-500">Records</p><p className="font-medium">{(batch.records_processed ?? 0).toLocaleString()}</p></div>
                    <div><p className="text-gray-500">Created</p><p className="font-medium">{formatDistanceToNow(new Date(batch.created_at), { addSuffix: true })}</p></div>
                  </div>
                  {batch.error_message && <div className="mt-4 p-3 bg-red-50 rounded-md"><p className="text-sm text-red-800">{batch.error_message}</p></div>}
                </CardContent>
              </Card>
            </Link>
          ))}
        </div>
      ) : (
        <Card>
          <CardContent className="py-12 text-center">
            <p className="text-gray-500">No batches found</p>
            <p className="text-sm text-gray-400 mt-2">Create a new batch to start ingesting data</p>
            <Button className="mt-4" onClick={onNewBatch}><Plus className="w-4 h-4 mr-2" />Create Your First Batch</Button>
          </CardContent>
        </Card>
      )}
    </div>
  );
}

/* ─────────────────── Page Router ─────────────────── */

function BatchesPageInner() {
  const searchParams = useSearchParams();
  const batchId = searchParams.get("id");
  const [showCreateModal, setShowCreateModal] = useState(false);

  return (
    <DashboardLayout>
      {batchId ? (
        <BatchDetail id={batchId} />
      ) : (
        <BatchList onNewBatch={() => setShowCreateModal(true)} />
      )}
      {showCreateModal && <CreateBatchModal onClose={() => setShowCreateModal(false)} />}
    </DashboardLayout>
  );
}

export default function BatchesPage() {
  return (
    <Suspense fallback={<DashboardLayout><div className="py-8 text-center text-gray-500">Loading...</div></DashboardLayout>}>
      <BatchesPageInner />
    </Suspense>
  );
}
