"use client";

import { useState, useEffect } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { apiClient, ApiError } from "@/lib/api";
import { DashboardLayout } from "@/components/dashboard-layout";
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card";
import { Alert, AlertDescription } from "@/components/ui/alert";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Badge } from "@/components/ui/badge";
import { CheckCircle, Trash2, Save, Eye, EyeOff, Settings, Info } from "lucide-react";

interface AEPConfigResponse {
  id: number;
  client_id: string;
  org_id: string;
  technical_account_id: string;
  sandbox_name: string;
  tenant_id: string | null;
  is_default: boolean;
  created_at: string;
  updated_at: string;
}

interface AEPConfigRequest {
  client_id: string;
  client_secret: string;
  org_id: string;
  technical_account_id: string;
  sandbox_name: string;
  tenant_id?: string;
  is_default: boolean;
}

const EMPTY_FORM: AEPConfigRequest = {
  client_id: "",
  client_secret: "",
  org_id: "",
  technical_account_id: "",
  sandbox_name: "prod",
  tenant_id: "",
  is_default: true,
};

export default function SettingsPage() {
  const queryClient = useQueryClient();
  const [form, setForm] = useState<AEPConfigRequest>(EMPTY_FORM);
  const [showSecret, setShowSecret] = useState(false);
  const [successMsg, setSuccessMsg] = useState<string | null>(null);
  const [errorMsg, setErrorMsg] = useState<string | null>(null);

  const { data: config, isLoading } = useQuery<AEPConfigResponse | null>({
    queryKey: ["settings", "aep"],
    queryFn: async () => {
      try {
        return await apiClient.get<AEPConfigResponse>("/api/settings/aep");
      } catch (err) {
        if (err instanceof ApiError && err.status === 404) return null;
        throw err;
      }
    },
  });

  useEffect(() => {
    if (config) {
      setForm({
        client_id: config.client_id,
        client_secret: "",
        org_id: config.org_id,
        technical_account_id: config.technical_account_id,
        sandbox_name: config.sandbox_name,
        tenant_id: config.tenant_id ?? "",
        is_default: config.is_default,
      });
    }
  }, [config]);

  const saveMutation = useMutation({
    mutationFn: async (data: AEPConfigRequest) => {
      return apiClient.put<AEPConfigResponse>("/api/settings/aep", data);
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["settings", "aep"] });
      setSuccessMsg("AEP credentials saved successfully.");
      setErrorMsg(null);
      setTimeout(() => setSuccessMsg(null), 4000);
    },
    onError: (err) => {
      setErrorMsg(err instanceof Error ? err.message : "Failed to save settings.");
      setSuccessMsg(null);
    },
  });

  const deleteMutation = useMutation({
    mutationFn: async () => {
      return apiClient.delete("/api/settings/aep");
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["settings", "aep"] });
      setForm(EMPTY_FORM);
      setSuccessMsg("AEP credentials deleted.");
      setErrorMsg(null);
      setTimeout(() => setSuccessMsg(null), 4000);
    },
    onError: (err) => {
      setErrorMsg(err instanceof Error ? err.message : "Failed to delete settings.");
    },
  });

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (!form.client_secret && !config) {
      setErrorMsg("Client Secret is required.");
      return;
    }
    saveMutation.mutate(form);
  };

  const handleDelete = () => {
    if (confirm("Are you sure you want to delete your AEP credentials?")) {
      deleteMutation.mutate();
    }
  };

  const field = (
    id: keyof AEPConfigRequest,
    label: string,
    placeholder: string,
    required = true,
    isSecret = false,
    hint?: string
  ) => (
    <div className="space-y-1">
      <Label htmlFor={id}>{label}{required && <span className="text-red-500 ml-1">*</span>}</Label>
      <div className="relative">
        <Input
          id={id}
          type={isSecret ? (showSecret ? "text" : "password") : "text"}
          placeholder={isSecret && config ? "Leave blank to keep existing secret" : placeholder}
          value={form[id] as string}
          onChange={(e) => setForm((prev) => ({ ...prev, [id]: e.target.value }))}
          required={required && !(isSecret && config)}
          className={isSecret ? "pr-10" : ""}
        />
        {isSecret && (
          <button
            type="button"
            className="absolute right-2 top-2.5 text-gray-400 hover:text-gray-600"
            onClick={() => setShowSecret((v) => !v)}
          >
            {showSecret ? <EyeOff className="w-4 h-4" /> : <Eye className="w-4 h-4" />}
          </button>
        )}
      </div>
      {hint && <p className="text-xs text-gray-500">{hint}</p>}
    </div>
  );

  return (
    <DashboardLayout>
      <div className="space-y-6 max-w-2xl">
        {/* Header */}
        <div>
          <div className="flex items-center gap-2">
            <Settings className="w-6 h-6" />
            <h1 className="text-3xl font-bold">Settings</h1>
          </div>
          <p className="text-gray-500 mt-2">
            Configure your Adobe Experience Platform credentials to enable data operations.
          </p>
        </div>

        {/* Status Banner */}
        {!isLoading && (
          <div className="flex items-center gap-2">
            {config ? (
              <>
                <CheckCircle className="w-4 h-4 text-green-600" />
                <span className="text-sm text-green-700 font-medium">AEP credentials configured</span>
                <Badge variant="outline" className="ml-2 text-xs">
                  {config.sandbox_name}
                </Badge>
              </>
            ) : (
              <>
                <Info className="w-4 h-4 text-yellow-600" />
                <span className="text-sm text-yellow-700 font-medium">AEP credentials not configured</span>
              </>
            )}
          </div>
        )}

        {/* Alerts */}
        {successMsg && (
          <Alert className="border-green-300 bg-green-50">
            <CheckCircle className="w-4 h-4 text-green-600" />
            <AlertDescription className="text-green-800">{successMsg}</AlertDescription>
          </Alert>
        )}
        {errorMsg && (
          <Alert variant="destructive">
            <AlertDescription>{errorMsg}</AlertDescription>
          </Alert>
        )}

        {/* AEP Credentials Form */}
        <Card>
          <CardHeader>
            <CardTitle>Adobe Experience Platform Credentials</CardTitle>
            <CardDescription>
              OAuth Server-to-Server credentials from your Adobe Developer Console project.
            </CardDescription>
          </CardHeader>
          <CardContent>
            {isLoading ? (
              <p className="text-center text-gray-500 py-4">Loading settings...</p>
            ) : (
              <form onSubmit={handleSubmit} className="space-y-4">
                {field(
                  "client_id",
                  "Client ID",
                  "e.g. abc123def456...",
                  true,
                  false,
                  "Found in Adobe Developer Console → Project → OAuth Server-to-Server"
                )}
                {field(
                  "client_secret",
                  "Client Secret",
                  "Enter your client secret",
                  !config,
                  true,
                  "Leave blank to keep the existing secret when updating"
                )}
                {field(
                  "org_id",
                  "Organization ID",
                  "e.g. XXXXXXXX@AdobeOrg",
                  true,
                  false,
                  "Your IMS Organization ID"
                )}
                {field(
                  "technical_account_id",
                  "Technical Account ID",
                  "e.g. XXXXXXXX@techacct.adobe.com",
                  true,
                  false
                )}
                {field(
                  "sandbox_name",
                  "Sandbox Name",
                  "prod",
                  true,
                  false,
                  "Default: prod"
                )}
                {field(
                  "tenant_id",
                  "Tenant ID",
                  "e.g. mytenant",
                  false,
                  false,
                  "Optional: your AEP tenant identifier"
                )}

                <div className="flex gap-3 pt-2">
                  <Button
                    type="submit"
                    disabled={saveMutation.isPending}
                    className="flex items-center gap-2"
                  >
                    <Save className="w-4 h-4" />
                    {saveMutation.isPending ? "Saving..." : config ? "Update Credentials" : "Save Credentials"}
                  </Button>
                  {config && (
                    <Button
                      type="button"
                      variant="destructive"
                      disabled={deleteMutation.isPending}
                      onClick={handleDelete}
                      className="flex items-center gap-2"
                    >
                      <Trash2 className="w-4 h-4" />
                      {deleteMutation.isPending ? "Deleting..." : "Delete"}
                    </Button>
                  )}
                </div>
              </form>
            )}
          </CardContent>
        </Card>

        {/* Help Card */}
        <Card className="bg-primary/5 border-primary/20">
          <CardHeader className="pb-2">
            <CardTitle className="text-sm text-primary flex items-center gap-2">
              <Info className="w-4 h-4" />
              Where to find your credentials
            </CardTitle>
          </CardHeader>
          <CardContent className="text-sm text-foreground/90 space-y-1">
            <p>1. Go to <strong>console.adobe.io</strong> and open your project.</p>
            <p>2. Navigate to <strong>OAuth Server-to-Server</strong> credentials.</p>
            <p>3. Copy the <strong>Client ID</strong>, <strong>Client Secret</strong>, and <strong>Technical Account ID</strong>.</p>
            <p>4. Your <strong>Organization ID</strong> is shown in the top right of the Adobe Admin Console.</p>
          </CardContent>
        </Card>
      </div>
    </DashboardLayout>
  );
}
