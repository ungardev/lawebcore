import { ExternalLink } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { cn } from '@/lib/utils';
import { classifyTier, formatEngagement, formatFollowers, getTierColor, isTienda } from '@/lib/format';
import type { DiscoveryCandidate } from '../types/discovery';
import { MatchScoreCircle } from './MatchScoreCircle';
import { PlatformBadge } from './PlatformBadge';

interface CandidateCardProps {
  candidate: DiscoveryCandidate;
  onSave?: (id: string) => void;
  onDismiss?: (id: string) => void;
  compact?: boolean;
}

export function CandidateCard({ candidate, onSave, onDismiss, compact }: CandidateCardProps) {
  const tier = candidate.tier ?? classifyTier(candidate.followers);
  return (
    <article className={cn('rounded-md border border-divider bg-panel-raised p-4 transition-colors hover:border-primary/35', compact ? 'p-3' : 'p-4')}>
      <div className="flex items-start gap-3">
        {candidate.avatar_url ? <img src={candidate.avatar_url} alt={candidate.handle} className="h-12 w-12 shrink-0 rounded-md object-cover" /> : <div className="flex h-12 w-12 shrink-0 items-center justify-center rounded-md border border-divider bg-surface-raised text-xs text-muted-foreground">{candidate.handle.slice(0, 2).toUpperCase()}</div>}
        <div className="min-w-0 flex-1">
          <div className="flex flex-wrap items-center gap-2"><span className="text-sm font-semibold text-foreground">{candidate.full_name || candidate.handle}</span><PlatformBadge platform={candidate.platform} />{tier && <span className={cn('rounded border px-1.5 py-0.5 text-[10px] font-semibold', getTierColor(tier))}>{tier}</span>}{candidate.country === 'VE' && <span className="text-sm" title="Venezuela" aria-label="Venezuela">🇻🇪</span>}{isTienda(candidate.bio) && <span className="rounded border border-warning/30 bg-warning/10 px-1.5 py-0.5 text-[10px] font-medium text-warning">Tienda</span>}</div>
          {candidate.url ? <a href={candidate.url} target="_blank" rel="noopener noreferrer" className="mt-1 inline-flex items-center gap-1 text-xs text-muted-foreground hover:text-primary hover:underline">@{candidate.handle}<ExternalLink className="h-3 w-3" aria-hidden="true" /></a> : <p className="mt-1 text-xs text-muted-foreground">@{candidate.handle}</p>}
          {!compact && candidate.bio && <p className="mt-2 line-clamp-2 text-xs leading-5 text-muted-foreground">{candidate.bio}</p>}
          <div className="mt-3 flex flex-wrap items-center gap-x-4 gap-y-1 text-xs text-muted-foreground"><span>{formatFollowers(candidate.followers)} seguidores</span><span>{formatEngagement(candidate.engagement_rate)} engagement</span>{candidate.city && <span>{candidate.city}</span>}</div>
        </div>
        <div className="shrink-0 text-center"><MatchScoreCircle score={candidate.match_score ?? candidate.niche_relevance ?? 0} size="sm" /><span className="mt-1 block text-[9px] uppercase tracking-wide text-muted-foreground">afinidad</span></div>
      </div>
      {candidate.rationale && !compact && <p className="mt-3 border-t border-divider pt-3 text-xs leading-5 text-muted-foreground">{candidate.rationale}</p>}
      {(onSave || onDismiss) && <div className="mt-3 flex gap-2 border-t border-divider pt-3">{onSave && <Button type="button" size="sm" onClick={() => onSave(candidate.id)} className="flex-1 text-xs">Guardar</Button>}{onDismiss && <Button type="button" size="sm" variant="outline" onClick={() => onDismiss(candidate.id)} className="flex-1 text-xs">Descartar</Button>}</div>}
    </article>
  );
}
