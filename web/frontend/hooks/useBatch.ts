import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { apiClient } from "@/lib/api";
import {
  BatchStatusResponse,
  BatchCreateRequest,
  FileUploadResponse,
} from "@/lib/types/batch";

export function useBatches() {
  return useQuery({
    queryKey: ["batches"],
    queryFn: async () => {
      return apiClient.get<BatchStatusResponse[]>("/api/batches");
    },
  });
}

export function useBatch(batchId: string | number) {
  return useQuery({
    queryKey: ["batches", batchId],
    queryFn: async () => {
      return apiClient.get<BatchStatusResponse>(`/api/batches/${batchId}`);
    },
    refetchInterval: (query) => {
      const data = query.state.data;
      // Poll every 5 seconds if batch is active/processing
      if (data && ["active", "processing", "queued"].includes(data.status)) {
        return 5000;
      }
      return false;
    },
  });
}

export function useCreateBatch() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async (request: BatchCreateRequest) => {
      return apiClient.post<BatchStatusResponse>(
        `/api/datasets/${request.dataset_id}/batches`,
        request
      );
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["batches"] });
    },
  });
}

export function useCompleteBatch() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async ({ batchId, abort }: { batchId: string; abort?: boolean }) => {
      return apiClient.post<BatchStatusResponse>(
        `/api/batches/${batchId}/complete`,
        { abort }
      );
    },
    onSuccess: (_, variables) => {
      queryClient.invalidateQueries({ queryKey: ["batches", variables.batchId] });
      queryClient.invalidateQueries({ queryKey: ["batches"] });
    },
  });
}

export function useUploadFile() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async ({
      batchId,
      file,
    }: {
      batchId: string;
      file: File;
    }) => {
      return apiClient.uploadFile<FileUploadResponse>(
        `/api/batches/${batchId}/files`,
        file
      );
    },
    onSuccess: (_, variables) => {
      queryClient.invalidateQueries({ queryKey: ["batches", variables.batchId] });
      queryClient.invalidateQueries({ queryKey: ["batches"] });
    },
  });
}
