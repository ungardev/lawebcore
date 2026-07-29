import { CheckCircle2, Circle, Loader2 } from "lucide-react";
import { Progress } from "@/components/ui/progress";
import { Card } from "@/components/ui/card";
import { cn } from "@/lib/utils";

export interface RunProgress {
  current_step: string;
  completed_steps: string[];
  current_hashtag?: string;
  candidates_found: number;
  platforms?: string[];
  total_queries?: number;
  completed_at?: string;
}

interface SearchProgressProps {
  progress: RunProgress;
  className?: string;
}

const STEP_LABELS: Record<string, string> = {
  parsing_brief: "Parseando brief...",
  building_queries: "Construyendo queries...",
  step1_hashtag_search: "Buscando hashtags...",
  step2_keyword_search: "Buscando por keywords...",
  step3_profile_enrichment: "Enriqueciendo perfiles...",
  step4_engagement_analytics: "Analizando engagement...",
  step5_scoring: "Rankeando candidatos...",
  querying_instagram_hashtag_search: "Buscando en Instagram...",
  querying_tiktok_hashtag_search: "Buscando en TikTok...",
  querying_youtube_channel_search: "Buscando en YouTube...",
  inserting_candidates: "Guardando candidatos...",
  completed: "Completado",
};

const ALL_STEPS = [
  "parsing_brief",
  "building_queries",
  "querying_instagram_hashtag_search",
  "querying_tiktok_hashtag_search",
  "querying_youtube_channel_search",
  "inserting_candidates",
  "completed",
];

function getStepLabel(step: string, hashtag?: string): string {
  if (STEP_LABELS[step]) return STEP_LABELS[step];
  if (step.startsWith("querying_instagram")) {
    return `Buscando en Instagram${hashtag ? ` (${hashtag})` : ""}...`;
  }
  if (step.startsWith("querying_tiktok")) {
    return `Buscando en TikTok${hashtag ? ` (${hashtag})` : ""}...`;
  }
  if (step.startsWith("querying_youtube")) {
    return `Buscando en YouTube${hashtag ? ` (${hashtag})` : ""}...`;
  }
  return step;
}

export function SearchProgress({ progress, className }: SearchProgressProps) {
  const currentLabel = getStepLabel(progress.current_step, progress.current_hashtag);
  const completedSet = new Set(progress.completed_steps || []);
  const isComplete = progress.current_step === "completed";

  const completedCount = completedSet.size;
  const totalSteps = ALL_STEPS.length;
  const pct = isComplete
    ? 100
    : Math.max(5, Math.round((completedCount / totalSteps) * 100));

  return (
    <Card className={cn("border-divider bg-surface-sunken p-4 shadow-none", className)}>
      <div className="space-y-3">
        <div className="flex items-center gap-2">
          {!isComplete ? (
            <Loader2 className="h-4 w-4 shrink-0 animate-spin text-primary" aria-hidden="true" />
          ) : (
            <CheckCircle2 className="h-4 w-4 shrink-0 text-success" aria-hidden="true" />
          )}
          <span className="text-sm font-medium text-foreground">
            {currentLabel}
          </span>
        </div>

        <Progress value={pct} className="h-1.5" aria-label={`Progreso de búsqueda: ${pct}%`} />

        <div className="flex items-center justify-between">
          <div className="flex items-center gap-1.5 flex-wrap">
            {ALL_STEPS.slice(0, -1).map((step) => {
              const done = completedSet.has(step) || isComplete;
              const active = progress.current_step === step && !isComplete;
              return (
                <div
                  key={step}
                  className={cn(
                    "flex items-center gap-0.5",
                    active ? "text-primary" : done ? "text-green-600" : "text-muted-foreground",
                  )}
                  title={getStepLabel(step)}
                >
                  {done ? (
                    <CheckCircle2 className="w-3 h-3" />
                  ) : active ? (
                    <Loader2 className="w-3 h-3 animate-spin" />
                  ) : (
                    <Circle className="w-3 h-3" />
                  )}
                </div>
              );
            })}
          </div>
          {progress.candidates_found > 0 && (
            <span className="text-xs text-muted-foreground">
              {progress.candidates_found} candidatos
            </span>
          )}
        </div>
      </div>
    </Card>
  );
}
