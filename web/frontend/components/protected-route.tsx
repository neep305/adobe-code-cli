"use client";

// No authentication needed for local CLI tool
// This component now just passes through children
export function ProtectedRoute({ children }: { children: React.ReactNode }) {
  return <>{children}</>;
}
