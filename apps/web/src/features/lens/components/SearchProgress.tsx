import { CheckCircle2, Circle, Loader2, XCircle } from 'lucide-react';
import { Card } from '@/components/ui/card';
import { Progress } from '@/components/ui/progress';
import { cn } from '@/lib/utils';

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
  { id: 'parsing_brief', label: 'Interpretando brief' },
  { id: 'building_queries', label: 'Construyendo consultas' },
  { id: 'step1_hashtag_search', label: 'Buscando por hashtags' },
  { id: 'step2_keyword_search', label: 'Buscando por keywords' },
  { id: 'step3_profile_enrichment', label: 'Enriqueciendo perfiles' },
  { id: 'step4_scoring', label: 'Puntuando candidatos' },
  { id: 'inserting_candidates', label: 'Guardando resultados' },
];

function getStepStatus(phaseId: string, currentStep: string, completedSteps: string[], isComplete: boolean) {
  if (isComplete || completedSteps.includes(phaseId)) return 'completed';
  if (currentStep === phaseId) return 'running';
  return 'waiting';
}

function getCurrentLabel(step: string, hashtag?: string) {
  const phase = PHASES.find((item) => item.id === step);
  if (phase) return hashtag && step.includes('hashtag') ? `${phase.label}: ${hashtag}` : phase.label;
  if (step.startsWith('querying_instagram')) return `Buscando en Instagram${hashtag ? `: ${hashtag}` : ''}`;
  if (step.startsWith('querying_tiktok')) return `Buscando en TikTok${hashtag ? `: ${hashtag}` : ''}`;
  if (step.startsWith('querying_youtube')) return `Buscando en YouTube${hashtag ? `: ${hashtag}` : ''}`;
  if (step === 'completed') return 'Búsqueda completada';
  if (step === 'failed') return 'La búsqueda falló';
  if (step === 'cancelled') return 'Seguimiento detenido';
  return 'Procesando discovery';
}

export function SearchProgress({ progress, className }: SearchProgressProps) {
  const isComplete = progress.current_step === 'completed';
  const isFailed = progress.current_step === 'failed';
  const isCancelled = progress.current_step === 'cancelled';
  const completedSet = new Set(progress.completed_steps || []);
  const completedCount = PHASES.filter((phase) => completedSet.has(phase.id)).length;
  const pct = isComplete ? 100 : Math.max(5, Math.round((completedCount / PHASES.length) * 100));
  const currentLabel = getCurrentLabel(progress.current_step, progress.current_hashtag);

  return (
    <Card className={cn('border-divider bg-surface-sunken p-4 shadow-none', className)} aria-live="polite">
      <div className="space-y-3">
        <div className="flex items-center gap-2">
          {isComplete ? <CheckCircle2 className="h-4 w-4 shrink-0 text-success" aria-hidden="true" /> : isFailed ? <XCircle className="h-4 w-4 shrink-0 text-destructive" aria-hidden="true" /> : isCancelled ? <Circle className="h-4 w-4 shrink-0 text-warning" aria-hidden="true" /> : <Loader2 className="h-4 w-4 shrink-0 animate-spin text-primary" aria-hidden="true" />}
          <span className="text-sm font-medium text-foreground">{currentLabel}</span>
        </div>
        <Progress value={pct} className="h-1.5" aria-label={`Progreso de búsqueda: ${pct}%`} />
        <div className="flex items-center justify-between gap-3">
          <div className="flex flex-wrap items-center gap-1.5" aria-label="Fases de discovery">
            {PHASES.map((phase) => {
              const status = getStepStatus(phase.id, progress.current_step, progress.completed_steps || [], isComplete);
              return <span key={phase.id} title={phase.label} className={cn('flex items-center gap-1', status === 'running' ? 'text-primary' : status === 'completed' ? 'text-success' : 'text-muted-foreground')} aria-label={`${phase.label}: ${status === 'completed' ? 'completado' : status === 'running' ? 'en curso' : 'pendiente'}`}>
                {status === 'completed' ? <CheckCircle2 className="h-3 w-3" aria-hidden="true" /> : status === 'running' ? <Loader2 className="h-3 w-3 animate-spin" aria-hidden="true" /> : <Circle className="h-3 w-3" aria-hidden="true" />}
              </span>;
            })}
          </div>
          <span className="shrink-0 text-xs text-muted-foreground">{progress.candidates_found} candidatos</span>
        </div>
      </div>
    </Card>
  );
}
