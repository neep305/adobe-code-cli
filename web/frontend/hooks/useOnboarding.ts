import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { apiClient } from "@/lib/api";
import { normalizeOnboardingStatus } from "@/lib/normalize-onboarding-status";
import { OnboardingStatus } from "@/lib/types/onboarding";

export function useOnboardingStatus() {
  return useQuery({
    queryKey: ["onboarding", "status"],
    queryFn: async () => {
      const raw = await apiClient.get<OnboardingStatus>("/api/onboarding/status");
      return normalizeOnboardingStatus(raw);
    },
    staleTime: 0,
    refetchInterval: 10000,
  });
}

export function useUpdateOnboardingProgress() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async ({ step_key, completed }: { step_key: string; completed: boolean }) => {
      const raw = await apiClient.put<OnboardingStatus>("/api/onboarding/progress", {
        step_key,
        completed,
      });
      return normalizeOnboardingStatus(raw);
    },
    onSuccess: (data) => {
      // PUT returns full OnboardingStatus; avoid invalidate+refetch racing with browser-cached GET.
      queryClient.setQueryData(["onboarding", "status"], data);
    },
  });
}
