import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { apiClient } from "@/lib/api";
import { SchemaDetailResponse, SchemaListResponse } from "@/lib/types/schema";

export function useSchemas() {
  return useQuery({
    queryKey: ["schemas"],
    queryFn: async () => {
      return apiClient.get<SchemaListResponse>("/api/schemas");
    },
  });
}

export function useSchema(schemaId: number | string) {
  return useQuery({
    queryKey: ["schemas", schemaId],
    queryFn: async () => {
      return apiClient.get<SchemaDetailResponse>(`/api/schemas/${schemaId}`);
    },
    enabled: !!schemaId,
  });
}

export function useGenerateSchema() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async (params: {
      file: File;
      title: string;
      description?: string;
      class_id?: string;
    }) => {
      const formData = new FormData();
      formData.append("file", params.file);
      formData.append("title", params.title);
      if (params.description) {
        formData.append("description", params.description);
      }
      if (params.class_id) {
        formData.append("class_id", params.class_id);
      }
      return apiClient.uploadFormData<SchemaDetailResponse>(
        "/api/schemas/generate",
        formData
      );
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["schemas"] });
      queryClient.invalidateQueries({ queryKey: ["onboarding", "status"] });
    },
  });
}
