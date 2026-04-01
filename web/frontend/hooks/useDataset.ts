import { useQuery } from "@tanstack/react-query";
import { apiClient } from "@/lib/api";
import { DatasetListResponse, DatasetResponse } from "@/lib/types/dataset";

export function useDatasets(state?: string) {
  return useQuery({
    queryKey: ["datasets", state],
    queryFn: async () => {
      const params = state ? `?state=${state}` : "";
      return apiClient.get<DatasetListResponse>(`/api/datasets${params}`);
    },
  });
}

export function useDataset(datasetId: number | string) {
  return useQuery({
    queryKey: ["datasets", datasetId],
    queryFn: async () => {
      return apiClient.get<DatasetResponse>(`/api/datasets/${datasetId}`);
    },
    enabled: !!datasetId,
  });
}
