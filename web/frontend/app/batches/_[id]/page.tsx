"use client";

import { use } from "react";
import { useBatch } from "@/hooks/useBatch";
import { useBatchWebSocket } from "@/hooks/useBatchWebSocket";
import { DashboardLayout } from "@/components/dashboard-layout";
import { ProtectedRoute } from "@/components/protected-route";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Alert, AlertDescription } from "@/components/ui/alert";
import { Badge } from "@/components/ui/badge";
import { BatchStatusBadge } from "@/components/batch/batch-status-badge";
import { BatchProgressBar } from "@/components/batch/batch-progress-bar";
import { BatchMetricsCard } from "@/components/batch/batch-metrics-card";
import Link from "next/link";
import { ArrowLeft, Wifi, WifiOff } from "lucide-react";

// Required for static export - generates no static paths by default
// Pages will be rendered client-side when accessed
export function generateStaticParams() {
  return [];
}

export default function BatchDetailPage({
  params,
}: {
  params: Promise<{ id: string }>;
}) {
  const { id } = use(params);
  const { data: batch, isLoading, error } = useBatch(id);
  const { isConnected, error: wsError } = useBatchWebSocket(id);

  return (
    <ProtectedRoute>
      <DashboardLayout>
        <div className="space-y-6">
          {/* Header */}
          <div className="flex items-center justify-between">
            <div className="flex items-center space-x-4">
              <Link
                href="/batches"
                className="text-gray-500 hover:text-gray-700"
              >
                <ArrowLeft className="h-6 w-6" />
              </Link>
              <div>
                <h1 className="text-3xl font-bold">Batch Details</h1>
                {batch && (
                  <p className="text-gray-500 mt-1 font-mono text-sm">
                    {batch.aep_batch_id}
                  </p>
                )}
              </div>
            </div>
            <div className="flex items-center space-x-2">
              {isConnected ? (
                <Badge variant="success" className="flex items-center gap-1">
                  <Wifi className="h-3 w-3" />
                  Live Updates
                </Badge>
              ) : (
                <Badge variant="outline" className="flex items-center gap-1">
                  <WifiOff className="h-3 w-3" />
                  Polling
                </Badge>
              )}
            </div>
          </div>

          {error && (
            <Alert variant="destructive">
              <AlertDescription>
                Failed to load batch: {error instanceof Error ? error.message : "Unknown error"}
              </AlertDescription>
            </Alert>
          )}

          {wsError && (
            <Alert>
              <AlertDescription>
                WebSocket error: {wsError}. Falling back to polling.
              </AlertDescription>
            </Alert>
          )}

          {isLoading ? (
            <Card>
              <CardContent className="py-8">
                <p className="text-center text-gray-500">Loading batch details...</p>
              </CardContent>
            </Card>
          ) : batch ? (
            <div className="grid gap-6 lg:grid-cols-3">
              {/* Status Card */}
              <div className="lg:col-span-2 space-y-6">
                <Card>
                  <CardHeader>
                    <div className="flex items-center justify-between">
                      <CardTitle>Status</CardTitle>
                      <BatchStatusBadge status={batch.status} />
                    </div>
                  </CardHeader>
                  <CardContent className="space-y-4">
                    <BatchProgressBar
                      status={batch.status}
                      progressPercent={batch.progress_percent}
                      filesUploaded={batch.files_uploaded}
                      filesCount={batch.files_count}
                    />

                    <div className="grid grid-cols-2 gap-4 text-sm pt-4 border-t">
                      <div>
                        <p className="text-gray-500">Dataset</p>
                        <p className="font-medium">{batch.dataset_name ?? `ID: ${batch.dataset_id}`}</p>
                      </div>
                      <div>
                        <p className="text-gray-500">Dataset ID</p>
                        <p className="font-medium">{batch.dataset_id}</p>
                      </div>
                    </div>

                    {batch.error_message && (
                      <Alert variant="destructive">
                        <AlertDescription>{batch.error_message}</AlertDescription>
                      </Alert>
                    )}
                  </CardContent>
                </Card>

                {/* Errors */}
                {batch.errors && batch.errors.length > 0 && (
                  <Card>
                    <CardHeader>
                      <CardTitle>Errors</CardTitle>
                    </CardHeader>
                    <CardContent>
                      <div className="space-y-2">
                        {batch.errors.map((error, idx) => (
                          <div
                            key={idx}
                            className="p-3 bg-red-50 rounded-md border border-red-200"
                          >
                            <p className="font-medium text-red-900">{error.code}</p>
                            <p className="text-sm text-red-700">{error.message}</p>
                          </div>
                        ))}
                      </div>
                    </CardContent>
                  </Card>
                )}
              </div>

              {/* Metrics Card */}
              <div>
                <BatchMetricsCard
                  recordsProcessed={batch.records_processed}
                  recordsFailed={batch.records_failed}
                  durationSeconds={batch.duration_seconds}
                  createdAt={batch.created_at}
                  completedAt={batch.completed_at}
                />
              </div>
            </div>
          ) : (
            <Card>
              <CardContent className="py-8">
                <p className="text-center text-gray-500">Batch not found</p>
              </CardContent>
            </Card>
          )}
        </div>
      </DashboardLayout>
    </ProtectedRoute>
  );
}
