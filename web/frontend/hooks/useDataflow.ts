import { useQuery } from "@tanstack/react-query";
import { apiClient } from "@/lib/api";
import {
  DataflowListResponse,
  DataflowResponse,
  DataflowRunResponse,
  DataflowHealthResponse,
} from "@/lib/types/dataflow";

export function useDataflows(limit?: number, state?: "enabled" | "disabled") {
  return useQuery({
    queryKey: ["dataflows", { limit, state }],
    queryFn: async () => {
      const params = new URLSearchParams();
      if (limit) params.append("limit", limit.toString());
      if (state) params.append("state", state);
      
      const query = params.toString();
      const url = `/api/dataflows${query ? `?${query}` : ""}`;
      
      return apiClient.get<DataflowListResponse>(url);
    },
  });
}

export function useDataflow(flowId: string) {
  return useQuery({
    queryKey: ["dataflows", flowId],
    queryFn: async () => {
      return apiClient.get<DataflowResponse>(`/api/dataflows/${flowId}`);
    },
    enabled: !!flowId,
  });
}

export function useDataflowRuns(flowId: string, days?: number) {
  return useQuery({
    queryKey: ["dataflows", flowId, "runs", days],
    queryFn: async () => {
      const params = new URLSearchParams();
      if (days) params.append("days", days.toString());
      
      const query = params.toString();
      const url = `/api/dataflows/${flowId}/runs${query ? `?${query}` : ""}`;
      
      return apiClient.get<DataflowRunResponse[]>(url);
    },
    enabled: !!flowId,
    refetchInterval: (query) => {
      const data = query.state.data;
      // Poll every 30 seconds if there are active runs
      if (data && data.some(run => ["pending", "inProgress"].includes(run.status))) {
        return 30000;
      }
      return false;
    },
  });
}

export function useDataflowHealth(flowId: string, days: number = 7) {
  return useQuery({
    queryKey: ["dataflows", flowId, "health", days],
    queryFn: async () => {
      const url = `/api/dataflows/${flowId}/health?days=${days}`;
      return apiClient.get<DataflowHealthResponse>(url);
    },
    enabled: !!flowId,
  });
}
