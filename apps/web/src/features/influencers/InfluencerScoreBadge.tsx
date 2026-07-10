import { cn } from '@/lib/utils';
import { InfluencerScore } from '@/types/piar';

interface InfluencerScoreBadgeProps {
  score: InfluencerScore | null;
  size?: 'sm' | 'md' | 'lg';
  showLabel?: boolean;
  className?: string;
}

const DECISION_CONFIG: Record<string, { color: string; bg: string; label: string }> = {
  ESCALAR: { color: 'text-emerald-700', bg: 'bg-emerald-50 border-emerald-300', label: 'Escalar' },
  OPTIMIZAR: { color: 'text-amber-700', bg: 'bg-amber-50 border-amber-300', label: 'Optimizar' },
  DESCARTAR: { color: 'text-red-700', bg: 'bg-red-50 border-red-300', label: 'Descartar' },
  DATOS_INSUFICIENTES: { color: 'text-slate-600', bg: 'bg-slate-50 border-slate-300', label: 'Sin datos' },
};

const SIZE_MAP = {
  sm: { outer: 'w-10 h-10', text: 'text-xs font-bold', inner: 'w-7 h-7 text-xs' },
  md: { outer: 'w-14 h-14', text: 'text-sm font-bold', inner: 'w-10 h-10 text-sm' },
  lg: { outer: 'w-18 h-18', text: 'text-base font-bold', inner: 'w-13 h-13 text-base' },
};

function getScoreColor(score: number | null): string {
  if (score === null) return 'text-slate-400';
  if (score >= 2.5) return 'text-emerald-600';
  if (score >= 1.8) return 'text-amber-600';
  return 'text-red-600';
}

function getRingColor(decision: string): string {
  if (decision === 'ESCALAR') return 'ring-emerald-400';
  if (decision === 'OPTIMIZAR') return 'ring-amber-400';
  if (decision === 'DESCARTAR') return 'ring-red-400';
  return 'ring-slate-300';
}

export function InfluencerScoreBadge({ score, size = 'md', showLabel = false, className }: InfluencerScoreBadgeProps) {
  if (!score) {
    return (
      <div className={cn('flex items-center gap-1.5', className)}>
        <div className="w-10 h-10 rounded-full border-2 border-slate-200 bg-slate-50 flex items-center justify-center">
          <span className="text-xs text-slate-400">—</span>
        </div>
        {showLabel && <span className="text-xs text-slate-500">Sin datos</span>}
      </div>
    );
  }

  const config = DECISION_CONFIG[score.decision] ?? DECISION_CONFIG['DATOS_INSUFICIENTES'];
  const sizes = SIZE_MAP[size];
  const scoreColor = getScoreColor(score.score_final);

  return (
    <div className={cn('flex items-center gap-1.5', className)}>
      <div
        className={cn(
          'rounded-full border-2 flex flex-col items-center justify-center relative group cursor-default',
          sizes.outer,
          getRingColor(score.decision),
          'ring-2',
        )}
        title={
          `Score: ${score.score_final?.toFixed(2) ?? 'N/A'} / 3.0\n` +
          `Decisión: ${config.label}\n` +
          `Publicaciones: ${score.publicaciones_count}\n` +
          `Sub-tier: ${score.subtier ?? 'N/A'}\n` +
          `Retention: ${score.score_retention?.toFixed(1) ?? 'N/A'} pts\n` +
          `Engagement: ${score.score_engagement?.toFixed(1) ?? 'N/A'} pts\n` +
          `Viralidad: ${score.score_viralidad?.toFixed(1) ?? 'N/A'} pts\n` +
          `ER vistas: ${score.er_vistas ? (score.er_vistas * 100).toFixed(2) + '%' : 'N/A'}\n` +
          `V/F: ${score.vf_ratio?.toFixed(3) ?? 'N/A'}\n` +
          `Seguidores: ${score.followers?.toLocaleString() ?? 'N/A'}`
        }
      >
        <div className={cn('flex flex-col items-center justify-center', sizes.inner)}>
          <span className={cn('font-bold', sizes.text, scoreColor)}>
            {score.score_final?.toFixed(1) ?? '—'}
          </span>
        </div>
        <div className="absolute inset-0 rounded-full bg-black/0 group-hover:bg-black/5 transition-colors" />
      </div>
      {showLabel && (
        <div className="flex flex-col">
          <span className={cn('text-xs font-semibold', config.color)}>{config.label}</span>
          {score.subtier && <span className="text-xs text-muted-foreground">{score.subtier}</span>}
        </div>
      )}
    </div>
  );
}
