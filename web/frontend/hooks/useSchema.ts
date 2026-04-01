import { useQuery } from "@tanstack/react-query";
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
