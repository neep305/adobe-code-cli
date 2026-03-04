"use client";

import { useBatches } from "@/hooks/useBatch";
import { DashboardLayout } from "@/components/dashboard-layout";
import { ProtectedRoute } from "@/components/protected-route";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Alert, AlertDescription } from "@/components/ui/alert";
import { BatchStatusBadge } from "@/components/batch/batch-status-badge";
import { formatDistanceToNow } from "date-fns";
import Link from "next/link";

export default function BatchesPage() {
  const { data: batches, isLoading, error } = useBatches();

  return (
    <ProtectedRoute>
      <DashboardLayout>
        <div className="space-y-6">
          <div>
            <h1 className="text-3xl font-bold">Batches</h1>
            <p className="text-gray-500 mt-2">
              Monitor your data ingestion batches and their status
            </p>
          </div>

          {error && (
            <Alert variant="destructive">
              <AlertDescription>
                Failed to load batches: {error instanceof Error ? error.message : "Unknown error"}
              </AlertDescription>
            </Alert>
          )}

          {isLoading ? (
            <Card>
              <CardContent className="py-8">
                <p className="text-center text-gray-500">Loading batches...</p>
              </CardContent>
            </Card>
          ) : batches && batches.length > 0 ? (
            <div className="grid gap-4">
              {batches.map((batch) => (
                <Link key={batch.id} href={`/batches/${batch.id}`}>
                  <Card className="hover:shadow-lg transition-shadow cursor-pointer">
                    <CardHeader>
                      <div className="flex items-center justify-between">
                        <CardTitle className="text-lg">
                          Batch {batch.aep_batch_id.slice(0, 8)}...
                        </CardTitle>
                        <BatchStatusBadge status={batch.status} />
                      </div>
                    </CardHeader>
                    <CardContent>
                      <div className="grid grid-cols-2 md:grid-cols-4 gap-4 text-sm">
                        <div>
                          <p className="text-gray-500">Format</p>
                          <p className="font-medium">{batch.format.toUpperCase()}</p>
                        </div>
                        <div>
                          <p className="text-gray-500">Files</p>
                          <p className="font-medium">
                            {batch.files_uploaded} / {batch.files_count}
                          </p>
                        </div>
                        <div>
                          <p className="text-gray-500">Records</p>
                          <p className="font-medium">
                            {batch.records_processed.toLocaleString()}
                          </p>
                        </div>
                        <div>
                          <p className="text-gray-500">Created</p>
                          <p className="font-medium">
                            {formatDistanceToNow(new Date(batch.created_at), {
                              addSuffix: true,
                            })}
                          </p>
                        </div>
                      </div>
                      {batch.error_message && (
                        <div className="mt-4 p-3 bg-red-50 rounded-md">
                          <p className="text-sm text-red-800">{batch.error_message}</p>
                        </div>
                      )}
                    </CardContent>
                  </Card>
                </Link>
              ))}
            </div>
          ) : (
            <Card>
              <CardContent className="py-8">
                <p className="text-center text-gray-500">No batches found</p>
              </CardContent>
            </Card>
          )}
        </div>
      </DashboardLayout>
    </ProtectedRoute>
  );
}
