"use client";

import { DashboardLayout } from "@/components/dashboard-layout";
import { ProtectedRoute } from "@/components/protected-route";
import { Card, CardContent } from "@/components/ui/card";

export default function DatasetsPage() {
  return (
    <ProtectedRoute>
      <DashboardLayout>
        <div className="space-y-6">
          <div>
            <h1 className="text-3xl font-bold">Datasets</h1>
            <p className="text-gray-500 mt-2">
              Manage your Adobe Experience Platform datasets
            </p>
          </div>

          <Card>
            <CardContent className="py-12">
              <p className="text-center text-gray-500">
                Dataset management coming soon...
              </p>
            </CardContent>
          </Card>
        </div>
      </DashboardLayout>
    </ProtectedRoute>
  );
}
