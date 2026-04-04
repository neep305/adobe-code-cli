"use client";

import { useState } from "react";
import { useSchemas, useSchema } from "@/hooks/useSchema";
import { DashboardLayout } from "@/components/dashboard-layout";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Alert, AlertDescription } from "@/components/ui/alert";
import { Badge } from "@/components/ui/badge";
import { formatDistanceToNow } from "date-fns";
import { SchemaCreateWizard } from "@/components/schemas/schema-create-wizard";
import { Button } from "@/components/ui/button";
import { FileJson, ChevronDown, ChevronRight, Layers, Copy, Check } from "lucide-react";

function ClassBadge({ classId }: { classId: string }) {
  const label = classId.includes("ExperienceEvent") || classId.includes("experienceevent")
    ? "Experience Event"
    : classId.includes("IndividualProfile") ||
        classId.includes("/xdm/context/profile")
    ? "Individual Profile"
    : classId.includes("Record")
    ? "Record"
    : "Custom";

  const cls =
    label === "Experience Event"
      ? "bg-primary/15 text-primary"
      : label === "Individual Profile"
      ? "bg-purple-100 text-purple-800"
      : "bg-gray-100 text-gray-700";

  return (
    <span className={`px-2 py-0.5 rounded-full text-xs font-medium ${cls}`}>
      {label}
    </span>
  );
}

function SchemaDetailPanel({ schemaId }: { schemaId: number }) {
  const { data, isLoading } = useSchema(schemaId);
  const [copied, setCopied] = useState(false);

  if (isLoading) return <p className="text-sm text-gray-500 py-2">Loading definition...</p>;
  if (!data) return null;

  const jsonStr = JSON.stringify(data.definition, null, 2);

  const copyJson = () => {
    navigator.clipboard.writeText(jsonStr).catch(() => {});
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  return (
    <div className="mt-4 border-t pt-4 space-y-2">
      <div className="flex items-center justify-between">
        <p className="text-sm font-medium text-gray-700">XDM JSON Structure</p>
        <button
          onClick={copyJson}
          className="flex items-center gap-1 text-xs text-muted-foreground hover:text-foreground transition-colors"
        >
          {copied ? (
            <Check className="h-3.5 w-3.5 text-emerald-500" />
          ) : (
            <Copy className="h-3.5 w-3.5" />
          )}
          {copied ? "Copied!" : "Copy JSON"}
        </button>
      </div>
      <pre className="text-xs font-mono bg-gray-50 border rounded-md p-3 overflow-x-auto max-h-96 overflow-y-auto text-gray-700 leading-relaxed whitespace-pre">
        {jsonStr}
      </pre>
    </div>
  );
}

function SchemaCard({ schema }: { schema: { id: number; aep_schema_id: string; name: string; title: string; description?: string; class_id: string; dataset_count: number; created_at: string } }) {
  const [expanded, setExpanded] = useState(false);

  return (
    <Card className="hover:shadow-md transition-shadow">
      <CardHeader>
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-3">
            <FileJson className="h-5 w-5 text-gray-400" />
            <div>
              <CardTitle className="text-lg">{schema.title}</CardTitle>
              <p className="text-xs text-gray-400 font-mono mt-0.5">{schema.name}</p>
            </div>
          </div>
          <ClassBadge classId={schema.class_id} />
        </div>
      </CardHeader>
      <CardContent>
        {schema.description && (
          <p className="text-sm text-gray-500 mb-3">{schema.description}</p>
        )}
        <div className="grid grid-cols-2 md:grid-cols-3 gap-4 text-sm">
          <div>
            <p className="text-gray-500">AEP Schema ID</p>
            <p className="font-medium font-mono text-xs truncate">{schema.aep_schema_id}</p>
          </div>
          <div>
            <p className="text-gray-500">Datasets</p>
            <p className="font-medium">{schema.dataset_count}</p>
          </div>
          <div>
            <p className="text-gray-500">Created</p>
            <p className="font-medium">
              {formatDistanceToNow(new Date(schema.created_at), { addSuffix: true })}
            </p>
          </div>
        </div>

        <button
          onClick={() => setExpanded((v) => !v)}
          className="mt-4 flex items-center gap-1 text-sm text-primary hover:text-primary/80"
        >
          {expanded ? (
            <ChevronDown className="h-4 w-4" />
          ) : (
            <ChevronRight className="h-4 w-4" />
          )}
          {expanded ? "Hide fields" : "Show fields"}
        </button>

        {expanded && <SchemaDetailPanel schemaId={schema.id} />}
      </CardContent>
    </Card>
  );
}

export default function SchemasPage() {
  const { data, isLoading, error } = useSchemas();

  return (
    <DashboardLayout>
      <div className="space-y-6">
        <div>
          <h1 className="text-3xl font-bold">Schemas</h1>
          <p className="text-gray-500 mt-2">
            Build XDM drafts from sample data and manage them in the list. Review before registering in AEP.
          </p>
        </div>

        <SchemaCreateWizard />

        {error && (
          <Alert variant="destructive">
            <AlertDescription>
              Failed to load schemas:{" "}
              {error instanceof Error ? error.message : "Unknown error"}
            </AlertDescription>
          </Alert>
        )}

        {isLoading ? (
          <Card>
            <CardContent className="py-8">
              <p className="text-center text-gray-500">Loading schemas...</p>
            </CardContent>
          </Card>
        ) : data && data.schemas.length > 0 ? (
          <>
            <p className="text-sm text-gray-500">{data.total} schema(s)</p>
            <div className="grid gap-4">
              {data.schemas.map((schema) => (
                <SchemaCard key={schema.id} schema={schema} />
              ))}
            </div>
          </>
        ) : (
          <Card>
            <CardContent className="py-12">
              <div className="flex flex-col items-center gap-4 text-gray-500">
                <Layers className="h-8 w-8" />
                <p>No schemas yet</p>
                <p className="text-sm text-center max-w-md">
                  Upload CSV/JSON in <strong>Schema draft</strong> below, or use the CLI{" "}
                  <code className="bg-gray-100 px-1 rounded">aep schema create</code>.
                </p>
                <Button
                  type="button"
                  onClick={() =>
                    document.getElementById("schema-wizard")?.scrollIntoView({ behavior: "smooth" })
                  }
                >
                  Create a schema
                </Button>
              </div>
            </CardContent>
          </Card>
        )}
      </div>
    </DashboardLayout>
  );
}
