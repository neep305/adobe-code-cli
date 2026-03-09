import { Progress } from "@/components/ui/progress";
import { cn } from "@/lib/utils";

interface BatchProgressBarProps {
  status: string;
  progressPercent: number;
  filesUploaded: number;
  filesCount: number;
  className?: string;
}

export function BatchProgressBar({
  status,
  progressPercent,
  filesUploaded,
  filesCount,
  className,
}: BatchProgressBarProps) {
  const isComplete = status.toLowerCase() === "success";
  const isFailed = ["failed", "aborted"].includes(status.toLowerCase());

  return (
    <div className={cn("space-y-2", className)}>
      <div className="flex justify-between text-sm">
        <span className="text-gray-600">
          {filesUploaded} / {filesCount} files uploaded
        </span>
        <span className="font-medium">{Math.round(progressPercent)}%</span>
      </div>
      <Progress 
        value={progressPercent} 
        className={cn(
          "h-2",
          isFailed && "bg-red-100",
          isComplete && "bg-green-100"
        )}
      />
    </div>
  );
}
