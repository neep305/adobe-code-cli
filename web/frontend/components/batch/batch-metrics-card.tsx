import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { formatDistanceToNow } from "date-fns";

interface BatchMetricsCardProps {
  recordsProcessed: number;
  recordsFailed: number;
  sizeBytes: number;
  createdAt: string;
  completedAt?: string;
}

function formatBytes(bytes: number): string {
  if (bytes === 0) return "0 Bytes";
  const k = 1024;
  const sizes = ["Bytes", "KB", "MB", "GB"];
  const i = Math.floor(Math.log(bytes) / Math.log(k));
  return Math.round((bytes / Math.pow(k, i)) * 100) / 100 + " " + sizes[i];
}

export function BatchMetricsCard({
  recordsProcessed,
  recordsFailed,
  sizeBytes,
  createdAt,
  completedAt,
}: BatchMetricsCardProps) {
  const successRate = recordsProcessed > 0
    ? ((recordsProcessed - recordsFailed) / recordsProcessed * 100).toFixed(1)
    : "0.0";

  return (
    <Card>
      <CardHeader>
        <CardTitle>Metrics</CardTitle>
      </CardHeader>
      <CardContent className="space-y-4">
        <div className="grid grid-cols-2 gap-4">
          <div>
            <p className="text-sm font-medium text-gray-500">Records Processed</p>
            <p className="text-2xl font-bold">{recordsProcessed.toLocaleString()}</p>
          </div>
          <div>
            <p className="text-sm font-medium text-gray-500">Records Failed</p>
            <p className="text-2xl font-bold text-red-600">
              {recordsFailed.toLocaleString()}
            </p>
          </div>
          <div>
            <p className="text-sm font-medium text-gray-500">Success Rate</p>
            <p className="text-2xl font-bold text-green-600">{successRate}%</p>
          </div>
          <div>
            <p className="text-sm font-medium text-gray-500">Size</p>
            <p className="text-2xl font-bold">{formatBytes(sizeBytes)}</p>
          </div>
        </div>
        <div className="border-t pt-4">
          <div className="space-y-2 text-sm">
            <div className="flex justify-between">
              <span className="text-gray-500">Created</span>
              <span className="font-medium">
                {formatDistanceToNow(new Date(createdAt), { addSuffix: true })}
              </span>
            </div>
            {completedAt && (
              <div className="flex justify-between">
                <span className="text-gray-500">Completed</span>
                <span className="font-medium">
                  {formatDistanceToNow(new Date(completedAt), { addSuffix: true })}
                </span>
              </div>
            )}
          </div>
        </div>
      </CardContent>
    </Card>
  );
}
