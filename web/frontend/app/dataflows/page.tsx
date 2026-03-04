"use client";

import { useDataflows } from "@/hooks/useDataflow";
import { DashboardLayout } from "@/components/dashboard-layout";
import { ProtectedRoute } from "@/components/protected-route";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Alert, AlertDescription } from "@/components/ui/alert";
import { DataflowStatusBadge } from "@/components/dataflow/dataflow-status-badge";
import { formatDistanceToNow } from "date-fns";
import Link from "next/link";

export default function DataflowsPage() {
  const { data: response, isLoading, error } = useDataflows();

  return (
    <ProtectedRoute>
      <DashboardLayout>
        <div className="space-y-6">
          <div>
            <h1 className="text-3xl font-bold">Dataflows</h1>
            <p className="text-gray-500 mt-2">
              Monitor dataflow health and execution history
            </p>
          </div>

          {error && (
            <Alert variant="destructive">
              <AlertDescription>
                Failed to load dataflows: {error instanceof Error ? error.message : "Unknown error"}
              </AlertDescription>
            </Alert>
          )}

          {isLoading ? (
            <Card>
              <CardContent className="py-8">
                <p className="text-center text-gray-500">Loading dataflows...</p>
              </CardContent>
            </Card>
          ) : response && response.dataflows.length > 0 ? (
            <div className="grid gap-4">
              {response.dataflows.map((dataflow) => (
                <Link key={dataflow.id} href={`/dataflows/${dataflow.id}`}>
                  <Card className="hover:shadow-lg transition-shadow cursor-pointer">
                    <CardHeader>
                      <div className="flex items-center justify-between">
                        <CardTitle className="text-lg">
                          {dataflow.name}
                        </CardTitle>
                        <DataflowStatusBadge state={dataflow.state} />
                      </div>
                      {dataflow.description && (
                        <p className="text-sm text-gray-500 mt-2">
                          {dataflow.description}
                        </p>
                      )}
                    </CardHeader>
                    <CardContent>
                      <div className="grid grid-cols-2 md:grid-cols-4 gap-4 text-sm">
                        <div>
                          <p className="text-gray-500">ID</p>
                          <p className="font-medium font-mono text-xs">
                            {dataflow.id.slice(0, 8)}...
                          </p>
                        </div>
                        <div>
                          <p className="text-gray-500">Sources</p>
                          <p className="font-medium">
                            {dataflow.source_connection_ids.length}
                          </p>
                        </div>
                        <div>
                          <p className="text-gray-500">Targets</p>
                          <p className="font-medium">
                            {dataflow.target_connection_ids.length}
                          </p>
                        </div>
                        <div>
                          <p className="text-gray-500">Updated</p>
                          <p className="font-medium">
                            {formatDistanceToNow(new Date(dataflow.updated_at), {
                              addSuffix: true,
                            })}
                          </p>
                        </div>
                      </div>
                    </CardContent>
                  </Card>
                </Link>
              ))}
            </div>
          ) : (
            <Card>
              <CardContent className="py-8">
                <p className="text-center text-gray-500">No dataflows found</p>
                <p className="text-center text-sm text-gray-400 mt-2">
                  Dataflows will appear here once configured in Adobe Experience Platform
                </p>
              </CardContent>
            </Card>
          )}
        </div>
      </DashboardLayout>
    </ProtectedRoute>
  );
}
