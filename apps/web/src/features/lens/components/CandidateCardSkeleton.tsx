import { Skeleton } from "@/components/ui/skeleton";
import { Card } from "@/components/ui/card";

interface CandidateCardSkeletonProps {
  compact?: boolean;
}

export function CandidateCardSkeleton({ compact = false }: CandidateCardSkeletonProps) {
  return (
    <Card className={compact ? "p-3" : "p-4"}>
      <div className="flex items-start gap-3">
        <Skeleton className="w-12 h-12 rounded-full flex-shrink-0" />
        <div className="flex-1 min-w-0 space-y-2">
          <div className="flex items-center gap-2">
            <Skeleton className="h-4 w-32" />
            <Skeleton className="h-4 w-16 rounded-full" />
          </div>
          <Skeleton className="h-3 w-24" />
          {!compact && <Skeleton className="h-3 w-full" />}
          <div className="flex items-center gap-4">
            <Skeleton className="h-3 w-20" />
            <Skeleton className="h-3 w-16" />
          </div>
        </div>
        <Skeleton className="w-8 h-8 rounded-full flex-shrink-0" />
      </div>
    </Card>
  );
}
