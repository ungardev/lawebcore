import { cn } from '@/lib/utils';
import { ExternalLink } from 'lucide-react';
import { formatEngagement, formatFollowers, isTienda, classifyTier, getTierColor } from '@/lib/format';
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
  return (
    <div className={cn(
      'rounded-xl border bg-card text-card-foreground',
      'hover:shadow-md transition-shadow',
      compact ? 'p-3' : 'p-4'
    )}>
      <div className="flex items-start gap-3">
        {candidate.avatar_url ? (
          <img
            src={candidate.avatar_url}
            alt={candidate.handle}
            className="w-12 h-12 rounded-full object-cover flex-shrink-0"
          />
        ) : (
          <div className="w-12 h-12 rounded-full bg-muted flex items-center justify-center text-muted-foreground text-xs flex-shrink-0">
            {candidate.handle.slice(0, 2).toUpperCase()}
          </div>
        )}

        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2 flex-wrap">
            <span className="font-medium text-sm">
              {candidate.full_name || candidate.handle}
            </span>
            <PlatformBadge platform={candidate.platform} />
            {candidate.tier && (
              <span
                className={cn(
                  "text-[10px] px-1.5 py-0.5 rounded-full font-semibold border",
                  getTierColor(candidate.tier)
                )}
                title={
                  candidate.tier === 'NANO' ? '<10K seguidores · micro-influencer local' :
                  candidate.tier === 'MICRO' ? '10K–100K seguidores · alcance medio' :
                  candidate.tier === 'MID' ? '100K–500K seguidores · macro-influencer' :
                  '500K+ seguidores · mega-influencer'
                }
              >
                {candidate.tier}
              </span>
            )}
            {candidate.country === "VE" && (
              <span className="text-sm" title="Venezuela">
                🇻🇪
              </span>
            )}
            {isTienda(candidate.bio) && (
              <span className="text-[10px] px-1.5 py-0.5 rounded-full font-medium bg-orange-100 text-orange-700 border border-orange-200">
                Tienda
              </span>
            )}
          </div>
          {candidate.url ? (
            <a
              href={candidate.url}
              target="_blank"
              rel="noopener noreferrer"
              className="text-xs text-muted-foreground hover:text-primary hover:underline inline-flex items-center gap-1"
            >
              @{candidate.handle}
              <ExternalLink className="w-3 h-3" />
            </a>
          ) : (
            <p className="text-xs text-muted-foreground">@{candidate.handle}</p>
          )}

          {!compact && candidate.bio && (
            <p className="text-xs text-muted-foreground mt-1 line-clamp-2">{candidate.bio}</p>
          )}

          <div className="flex items-center gap-4 mt-2 text-xs text-muted-foreground">
            <span>{formatFollowers(candidate.followers)} seguidores</span>
            <span>{formatEngagement(candidate.engagement_rate)} engagement</span>
            {candidate.city && <span>{candidate.city}</span>}
          </div>
        </div>

        <div className="flex-shrink-0">
          <MatchScoreCircle score={candidate.match_score ?? candidate.niche_relevance ?? 0} size="sm" />
        </div>
      </div>

      {candidate.rationale && !compact && (
        <p className="text-xs text-foreground/70 mt-2 italic">"{candidate.rationale}"</p>
      )}

      {(onSave || onDismiss) && (
        <div className="flex gap-2 mt-3">
          {onSave && (
            <button
              onClick={() => onSave(candidate.id)}
              className="flex-1 text-xs py-1.5 rounded-md bg-primary text-primary-foreground hover:opacity-90 transition-opacity"
            >
              Guardar
            </button>
          )}
          {onDismiss && (
            <button
              onClick={() => onDismiss(candidate.id)}
              className="flex-1 text-xs py-1.5 rounded-md border border-border hover:bg-muted transition-colors"
            >
              Descartar
            </button>
          )}
        </div>
      )}
    </div>
  );
}
