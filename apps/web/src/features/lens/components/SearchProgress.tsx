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

const PHASES = [
  { id: "step1_hashtag_search", label: "Buscar candidatos por hashtags" },
  { id: "step2_keyword_search", label: "Buscar por keywords" },
  { id: "step3_profile_enrichment", label: "Enriquecer perfiles con datos reales" },
  { id: "step4_scoring", label: "Puntuar y filtrar candidatos" },
];

function getStepStatus(
  phaseId: string,
  currentStep: string,
  completedSteps: string[],
  isComplete: boolean,
): "completed" | "running" | "waiting" {
  if (isComplete || completedSteps.includes(phaseId)) return "completed";
  if (currentStep === phaseId) return "running";
  return "waiting";
}

export function SearchProgress({ progress, className }: SearchProgressProps) {
  const isComplete = progress.current_step === "completed";
  const completedSet = new Set(progress.completed_steps || []);
  const pct = isComplete
    ? 100
    : Math.max(
        5,
        Math.round((completedSet.size / PHASES.length) * 100),
      );

  const runningPhase = PHASES.find((p) => p.id === progress.current_step);
  const runningLabel = runningPhase?.label ?? "Procesando...";

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
            {isComplete ? "Búsqueda completada" : runningLabel}
          </span>
        </div>

        <Progress value={pct} className="h-1.5" aria-label={`Progreso de búsqueda: ${pct}%`} />

        <div className="flex items-center justify-between">
          <div className="flex items-center gap-1.5 flex-wrap">
            {PHASES.map((phase) => {
              const status = getStepStatus(
                phase.id,
                progress.current_step,
                progress.completed_steps || [],
                isComplete,
              );
              return (
                <div
                  key={phase.id}
                  className={cn(
                    "flex items-center gap-1",
                    status === "running"
                      ? "text-primary"
                      : status === "completed"
                      ? "text-green-600"
                      : "text-muted-foreground",
                  )}
                  title={phase.label}
                >
                  {status === "completed" ? (
                    <CheckCircle2 className="w-3 h-3" />
                  ) : status === "running" ? (
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
