import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { formatDistanceToNow } from "date-fns";

interface BatchMetricsCardProps {
  recordsProcessed?: number;
  recordsFailed?: number;
  createdAt: string;
  completedAt?: string;
  durationSeconds?: number;
}

function formatDuration(seconds: number): string {
  if (seconds < 60) return `${Math.round(seconds)}s`;
  if (seconds < 3600) return `${Math.round(seconds / 60)}m`;
  const h = Math.floor(seconds / 3600);
  const m = Math.round((seconds % 3600) / 60);
  return `${h}h ${m}m`;
}

export function BatchMetricsCard({
  recordsProcessed = 0,
  recordsFailed = 0,
  createdAt,
  completedAt,
  durationSeconds,
}: BatchMetricsCardProps) {
  const successRate =
    recordsProcessed > 0
      ? (((recordsProcessed - recordsFailed) / recordsProcessed) * 100).toFixed(1)
      : "0.0";

  return (
    <Card>
      <CardHeader>
        <CardTitle>Metrics</CardTitle>
      </CardHeader>
      <CardContent className="space-y-4">
        <div className="grid grid-cols-2 gap-4">
          <div>
            <p className="text-sm font-medium text-gray-500">Processed</p>
            <p className="text-2xl font-bold">{recordsProcessed.toLocaleString()}</p>
          </div>
          <div>
            <p className="text-sm font-medium text-gray-500">Failed</p>
            <p className="text-2xl font-bold text-red-600">
              {recordsFailed.toLocaleString()}
            </p>
          </div>
          <div>
            <p className="text-sm font-medium text-gray-500">Success Rate</p>
            <p className="text-2xl font-bold text-green-600">{successRate}%</p>
          </div>
          {durationSeconds !== undefined && (
            <div>
              <p className="text-sm font-medium text-gray-500">Duration</p>
              <p className="text-2xl font-bold">{formatDuration(durationSeconds)}</p>
            </div>
          )}
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
