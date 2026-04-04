"use client";

import { useEffect } from "react";
import { useRouter } from "next/navigation";
import { useAuth } from "@/lib/auth";
import { useOnboardingStatus } from "@/hooks/useOnboarding";

export default function Home() {
  const router = useRouter();
  const { isAuthenticated, isLoading: authLoading } = useAuth();
  const { data: onboarding, isLoading: onboardingLoading } = useOnboardingStatus();

  useEffect(() => {
    if (authLoading) return;

    if (!isAuthenticated) {
      router.push("/login");
      return;
    }

    // Wait for onboarding status before deciding destination
    if (onboardingLoading) return;

    if (onboarding && onboarding.overall_progress >= 1) {
      router.push("/analyze");
    } else {
      router.push("/onboarding");
    }
  }, [isAuthenticated, authLoading, onboarding, onboardingLoading, router]);

  return (
    <div className="flex min-h-screen items-center justify-center bg-muted">
      <p className="text-muted-foreground">Loading...</p>
    </div>
  );
}
