"use client";

import { useDatasets } from "@/hooks/useDataset";
import { DashboardLayout } from "@/components/dashboard-layout";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Alert, AlertDescription } from "@/components/ui/alert";
import { Badge } from "@/components/ui/badge";
import { formatDistanceToNow } from "date-fns";
import { Database } from "lucide-react";

function DatasetStateBadge({ state }: { state: string }) {
  const variantMap: Record<string, string> = {
    ACTIVE: "bg-green-100 text-green-800",
    DRAFT: "bg-gray-100 text-gray-700",
    INACTIVE: "bg-red-100 text-red-700",
  };
  const cls = variantMap[state] ?? "bg-gray-100 text-gray-700";
  return (
    <span className={`px-2 py-0.5 rounded-full text-xs font-medium ${cls}`}>
      {state}
    </span>
  );
}

export default function DatasetsPage() {
  const { data, isLoading, error } = useDatasets();

  return (
    <DashboardLayout>
      <div className="space-y-6">
        <div>
          <h1 className="text-3xl font-bold">Datasets</h1>
          <p className="text-gray-500 mt-2">
            Manage your Adobe Experience Platform datasets
          </p>
        </div>

        {error && (
          <Alert variant="destructive">
            <AlertDescription>
              Failed to load datasets:{" "}
              {error instanceof Error ? error.message : "Unknown error"}
            </AlertDescription>
          </Alert>
        )}

        {isLoading ? (
          <Card>
            <CardContent className="py-8">
              <p className="text-center text-gray-500">Loading datasets...</p>
            </CardContent>
          </Card>
        ) : data && data.datasets.length > 0 ? (
          <>
            <p className="text-sm text-gray-500">{data.total} dataset(s) found</p>
            <div className="grid gap-4">
              {data.datasets.map((dataset) => (
                <Card key={dataset.id} className="hover:shadow-md transition-shadow">
                  <CardHeader>
                    <div className="flex items-center justify-between">
                      <div className="flex items-center gap-3">
                        <Database className="h-5 w-5 text-gray-400" />
                        <CardTitle className="text-lg">{dataset.name}</CardTitle>
                      </div>
                      <DatasetStateBadge state={dataset.state} />
                    </div>
                  </CardHeader>
                  <CardContent>
                    {dataset.description && (
                      <p className="text-sm text-gray-500 mb-3">{dataset.description}</p>
                    )}
                    <div className="grid grid-cols-2 md:grid-cols-4 gap-4 text-sm">
                      <div>
                        <p className="text-gray-500">AEP Dataset ID</p>
                        <p className="font-medium font-mono text-xs truncate">
                          {dataset.aep_dataset_id}
                        </p>
                      </div>
                      <div>
                        <p className="text-gray-500">Schema</p>
                        <p className="font-medium">
                          {dataset.schema_name ?? "—"}
                        </p>
                      </div>
                      <div className="flex flex-col gap-1">
                        <p className="text-gray-500">Flags</p>
                        <div className="flex gap-1 flex-wrap">
                          {dataset.profile_enabled && (
                            <Badge variant="outline" className="text-xs">Profile</Badge>
                          )}
                          {dataset.identity_enabled && (
                            <Badge variant="outline" className="text-xs">Identity</Badge>
                          )}
                          {!dataset.profile_enabled && !dataset.identity_enabled && (
                            <span className="text-gray-400 text-xs">None</span>
                          )}
                        </div>
                      </div>
                      <div>
                        <p className="text-gray-500">Created</p>
                        <p className="font-medium">
                          {formatDistanceToNow(new Date(dataset.created_at), {
                            addSuffix: true,
                          })}
                        </p>
                      </div>
                    </div>
                  </CardContent>
                </Card>
              ))}
            </div>
          </>
        ) : (
          <Card>
            <CardContent className="py-12">
              <div className="flex flex-col items-center gap-2 text-gray-500">
                <Database className="h-8 w-8" />
                <p>No datasets found</p>
                <p className="text-sm">
                  Use the CLI to create datasets and they will appear here.
                </p>
              </div>
            </CardContent>
          </Card>
        )}
      </div>
    </DashboardLayout>
  );
}
