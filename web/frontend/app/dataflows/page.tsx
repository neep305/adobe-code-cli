"use client";

import { useState, Suspense } from "react";
import { useSearchParams, useRouter } from "next/navigation";
import { useDataflows, useDataflow, useDataflowRuns, useDataflowHealth } from "@/hooks/useDataflow";
import { DashboardLayout } from "@/components/dashboard-layout";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Alert, AlertDescription } from "@/components/ui/alert";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { DataflowStatusBadge } from "@/components/dataflow/dataflow-status-badge";
import { DataflowHealthBadge } from "@/components/dataflow/dataflow-health-badge";
import { formatDistanceToNow, format } from "date-fns";
import Link from "next/link";
import { ArrowLeft, RefreshCw, Activity, Clock, CheckCircle, XCircle, AlertTriangle } from "lucide-react";

/* ─────────────────── Helpers ─────────────────── */

function formatDuration(seconds: number): string {
  if (seconds < 60) return `${Math.round(seconds)}s`;
  if (seconds < 3600) return `${Math.round(seconds / 60)}m`;
  const h = Math.floor(seconds / 3600);
  const m = Math.round((seconds % 3600) / 60);
  return `${h}h ${m}m`;
}

function RunStatusBadge({ status }: { status: string }) {
  const config: Record<string, { label: string; className: string }> = {
    success: { label: "Success", className: "bg-green-600 hover:bg-green-700" },
    failed: { label: "Failed", className: "bg-red-600 hover:bg-red-700" },
    inProgress: { label: "In Progress", className: "bg-primary hover:bg-primary/90" },
    pending: { label: "Pending", className: "bg-yellow-600 hover:bg-yellow-700" },
    cancelled: { label: "Cancelled", className: "bg-gray-500 hover:bg-gray-600" },
  };
  const c = config[status] ?? { label: status, className: "bg-gray-400" };
  return <Badge variant="default" className={c.className}>{c.label}</Badge>;
}

/* ─────────────────── Dataflow Detail ─────────────────── */

function DataflowDetail({ flowId }: { flowId: string }) {
  const router = useRouter();
  const [runDays, setRunDays] = useState(7);

  const { data: dataflow, isLoading: dfLoading, error: dfError } = useDataflow(flowId);
  const { data: runs, isLoading: runsLoading, refetch: refetchRuns } = useDataflowRuns(flowId, runDays);
  const { data: health, isLoading: healthLoading } = useDataflowHealth(flowId, runDays);

  if (dfLoading) {
    return <Card><CardContent className="py-12"><p className="text-center text-gray-500">Loading dataflow...</p></CardContent></Card>;
  }

  if (dfError || !dataflow) {
    return (
      <Alert variant="destructive">
        <AlertDescription>Failed to load dataflow: {dfError instanceof Error ? dfError.message : "Not found"}</AlertDescription>
      </Alert>
    );
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center gap-4">
        <Button variant="ghost" size="sm" onClick={() => router.push("/dataflows")}>
          <ArrowLeft className="w-4 h-4 mr-2" />Back
        </Button>
        <div className="flex-1">
          <div className="flex items-center gap-3">
            <h1 className="text-3xl font-bold">{dataflow.name}</h1>
            <DataflowStatusBadge state={dataflow.state} />
          </div>
          {dataflow.description && <p className="text-gray-500 mt-1">{dataflow.description}</p>}
        </div>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        <Card>
          <CardHeader className="pb-2"><CardTitle className="text-sm text-gray-500">Dataflow ID</CardTitle></CardHeader>
          <CardContent><p className="font-mono text-xs break-all">{dataflow.id}</p></CardContent>
        </Card>
        <Card>
          <CardHeader className="pb-2"><CardTitle className="text-sm text-gray-500">Sources / Targets</CardTitle></CardHeader>
          <CardContent><p className="font-medium">{dataflow.source_connection_ids.length} sources · {dataflow.target_connection_ids.length} targets</p></CardContent>
        </Card>
        <Card>
          <CardHeader className="pb-2"><CardTitle className="text-sm text-gray-500">Last Updated</CardTitle></CardHeader>
          <CardContent><p className="font-medium">{formatDistanceToNow(new Date(dataflow.updated_at), { addSuffix: true })}</p></CardContent>
        </Card>
      </div>

      {/* Health Analysis */}
      <Card>
        <CardHeader>
          <div className="flex items-center justify-between">
            <CardTitle className="flex items-center gap-2"><Activity className="w-5 h-5" />Health Analysis</CardTitle>
            <div className="flex items-center gap-2">
              {[7, 14, 30].map((d) => (
                <Button key={d} variant={runDays === d ? "default" : "outline"} size="sm" onClick={() => setRunDays(d)}>{d}d</Button>
              ))}
            </div>
          </div>
        </CardHeader>
        <CardContent>
          {healthLoading ? (
            <p className="text-center text-gray-500 py-4">Analyzing health...</p>
          ) : health ? (
            <div className="space-y-6">
              <div className="grid grid-cols-2 md:grid-cols-5 gap-4">
                <div className="text-center"><p className="text-2xl font-bold">{health.total_runs}</p><p className="text-sm text-gray-500">Total Runs</p></div>
                <div className="text-center"><p className="text-2xl font-bold text-green-600">{health.success_runs}</p><p className="text-sm text-gray-500">Successful</p></div>
                <div className="text-center"><p className="text-2xl font-bold text-red-600">{health.failed_runs}</p><p className="text-sm text-gray-500">Failed</p></div>
                <div className="text-center"><p className="text-2xl font-bold">{health.success_rate.toFixed(1)}%</p><p className="text-sm text-gray-500">Success Rate</p></div>
                <div className="text-center"><p className="text-2xl font-bold">{formatDuration(health.avg_duration_seconds)}</p><p className="text-sm text-gray-500">Avg Duration</p></div>
              </div>
              <div className="flex items-center gap-3">
                <span className="text-sm text-gray-500">Overall Health:</span>
                <DataflowHealthBadge status={health.health_status} />
              </div>
              {health.recommendations.length > 0 && (
                <div>
                  <h4 className="font-medium text-sm mb-2 flex items-center gap-2"><AlertTriangle className="w-4 h-4 text-yellow-600" />Recommendations</h4>
                  <ul className="space-y-1">
                    {health.recommendations.map((rec, i) => <li key={i} className="text-sm text-gray-600 flex items-start gap-2"><span className="mt-0.5 text-yellow-600">•</span>{rec}</li>)}
                  </ul>
                </div>
              )}
              {health.errors.length > 0 && (
                <div>
                  <h4 className="font-medium text-sm mb-2 flex items-center gap-2"><XCircle className="w-4 h-4 text-red-600" />Recurring Errors</h4>
                  <div className="space-y-2">
                    {health.errors.map((err, i) => (
                      <div key={i} className="bg-red-50 border border-red-200 rounded p-3 text-sm">
                        <div className="flex items-center justify-between">
                          <code className="text-red-700 font-mono text-xs">{err.code}</code>
                          <Badge variant="outline" className="text-red-600 border-red-300 text-xs">{err.count}x</Badge>
                        </div>
                        <p className="text-gray-700 mt-1">{err.message}</p>
                      </div>
                    ))}
                  </div>
                </div>
              )}
            </div>
          ) : (
            <p className="text-center text-gray-400 py-4">No health data available</p>
          )}
        </CardContent>
      </Card>

      {/* Execution History */}
      <Card>
        <CardHeader>
          <div className="flex items-center justify-between">
            <CardTitle className="flex items-center gap-2"><Clock className="w-5 h-5" />Execution History</CardTitle>
            <Button variant="outline" size="sm" onClick={() => refetchRuns()}><RefreshCw className="w-4 h-4 mr-2" />Refresh</Button>
          </div>
        </CardHeader>
        <CardContent>
          {runsLoading ? (
            <p className="text-center text-gray-500 py-4">Loading runs...</p>
          ) : runs && runs.length > 0 ? (
            <div className="space-y-3">
              {runs.map((run) => (
                <div key={run.id} className="border rounded-lg p-4">
                  <div className="flex items-center justify-between mb-2">
                    <div className="flex items-center gap-3">
                      {run.status === "success" ? <CheckCircle className="w-4 h-4 text-green-600" /> : run.status === "failed" ? <XCircle className="w-4 h-4 text-red-600" /> : <Activity className="w-4 h-4 text-primary" />}
                      <RunStatusBadge status={run.status} />
                      <span className="text-sm text-gray-500 font-mono">{run.id.slice(0, 8)}...</span>
                    </div>
                    <span className="text-sm text-gray-500">{format(new Date(run.created_at), "MMM d, HH:mm")}</span>
                  </div>
                  {run.metrics && (
                    <div className="grid grid-cols-2 md:grid-cols-4 gap-3 mt-2 text-sm">
                      <div><p className="text-gray-500 text-xs">Input Records</p><p className="font-medium">{run.metrics.input_record_count?.toLocaleString() ?? "—"}</p></div>
                      <div><p className="text-gray-500 text-xs">Output Records</p><p className="font-medium">{run.metrics.output_record_count?.toLocaleString() ?? "—"}</p></div>
                      <div><p className="text-gray-500 text-xs">Failed Records</p><p className="font-medium text-red-600">{run.metrics.failed_record_count?.toLocaleString() ?? "—"}</p></div>
                      <div><p className="text-gray-500 text-xs">Duration</p><p className="font-medium">{run.metrics.duration_ms ? formatDuration(run.metrics.duration_ms / 1000) : "—"}</p></div>
                    </div>
                  )}
                  {run.errors.length > 0 && (
                    <div className="mt-2 pt-2 border-t">
                      {run.errors.map((err, i) => <p key={i} className="text-xs text-red-600"><code className="font-mono">{err.code}</code>: {err.message}</p>)}
                    </div>
                  )}
                </div>
              ))}
            </div>
          ) : (
            <p className="text-center text-gray-400 py-6">No execution history found for the last {runDays} days</p>
          )}
        </CardContent>
      </Card>
    </div>
  );
}

/* ─────────────────── Dataflow List ─────────────────── */

function DataflowList() {
  const { data: response, isLoading, error } = useDataflows();

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-3xl font-bold">Dataflows</h1>
        <p className="text-gray-500 mt-2">Monitor dataflow health and execution history</p>
      </div>

      {error && <Alert variant="destructive"><AlertDescription>Failed to load dataflows: {error instanceof Error ? error.message : "Unknown error"}</AlertDescription></Alert>}

      {isLoading ? (
        <Card><CardContent className="py-8"><p className="text-center text-gray-500">Loading dataflows...</p></CardContent></Card>
      ) : response && response.dataflows.length > 0 ? (
        <div className="grid gap-4">
          {response.dataflows.map((dataflow) => (
            <Link key={dataflow.id} href={`/dataflows?id=${dataflow.id}`}>
              <Card className="hover:shadow-lg transition-shadow cursor-pointer">
                <CardHeader>
                  <div className="flex items-center justify-between">
                    <CardTitle className="text-lg">{dataflow.name}</CardTitle>
                    <DataflowStatusBadge state={dataflow.state} />
                  </div>
                  {dataflow.description && <p className="text-sm text-gray-500 mt-2">{dataflow.description}</p>}
                </CardHeader>
                <CardContent>
                  <div className="grid grid-cols-2 md:grid-cols-4 gap-4 text-sm">
                    <div><p className="text-gray-500">ID</p><p className="font-medium font-mono text-xs">{dataflow.id.slice(0, 8)}...</p></div>
                    <div><p className="text-gray-500">Sources</p><p className="font-medium">{dataflow.source_connection_ids.length}</p></div>
                    <div><p className="text-gray-500">Targets</p><p className="font-medium">{dataflow.target_connection_ids.length}</p></div>
                    <div><p className="text-gray-500">Updated</p><p className="font-medium">{formatDistanceToNow(new Date(dataflow.updated_at), { addSuffix: true })}</p></div>
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
            <p className="text-center text-sm text-gray-400 mt-2">Dataflows will appear here once configured in Adobe Experience Platform</p>
          </CardContent>
        </Card>
      )}
    </div>
  );
}

/* ─────────────────── Page Router ─────────────────── */

function DataflowsPageInner() {
  const searchParams = useSearchParams();
  const flowId = searchParams.get("id");

  return (
    <DashboardLayout>
      {flowId ? <DataflowDetail flowId={flowId} /> : <DataflowList />}
    </DashboardLayout>
  );
}

export default function DataflowsPage() {
  return (
    <Suspense fallback={<DashboardLayout><div className="py-8 text-center text-gray-500">Loading...</div></DashboardLayout>}>
      <DataflowsPageInner />
    </Suspense>
  );
}
