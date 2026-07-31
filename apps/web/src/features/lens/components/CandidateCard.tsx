import { useState } from 'react'
import { ExternalLink } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { cn } from '@/lib/utils'
import {
  classifyTier,
  formatEngagement,
  formatFollowers,
  getTierColor,
  isTienda,
} from '@/lib/format'
import type { DiscoveryCandidate } from '../types/discovery'
import { MatchScoreCircle } from './MatchScoreCircle'
import { PlatformIcon } from './PlatformIcon'
import { CountryFlag } from './CountryFlag'

interface CandidateCardProps {
  candidate: DiscoveryCandidate
  onSave?: (id: string) => void
  onDismiss?: (id: string) => void
  compact?: boolean
}

export function CandidateCard({ candidate, onSave, onDismiss, compact }: CandidateCardProps) {
  const [imgFailed, setImgFailed] = useState(false)
  const tier = candidate.tier ?? classifyTier(candidate.followers)
  const avatarUrl = candidate.avatar_url
    || (candidate.platform === 'instagram' && candidate.handle
      ? `https://instagram.com/${candidate.handle}/profile_picture`
      : null)
  const showInitials = !avatarUrl || imgFailed

  return (
    <article
      className={cn(
        'rounded-md border border-divider bg-panel-raised p-4 transition-colors hover:border-primary/35',
        compact ? 'p-3' : 'p-4',
      )}
    >
      <div className="flex items-start gap-3">
        {showInitials ? (
          <div className="flex h-12 w-12 shrink-0 items-center justify-center rounded-md border border-divider bg-surface-raised text-xs text-muted-foreground">
            {candidate.handle.slice(0, 2).toUpperCase()}
          </div>
        ) : (
          <img
            src={avatarUrl ?? undefined}
            alt={candidate.handle}
            className="h-12 w-12 shrink-0 rounded-md object-cover"
            onError={() => setImgFailed(true)}
          />
        )}
        <div className="min-w-0 flex-1">
          <div className="flex items-center gap-2">
            <span className="text-sm font-semibold text-foreground">
              {candidate.full_name || candidate.handle}
            </span>
            <PlatformIcon platform={candidate.platform} size="sm" />
            {tier && (
              <span
                className={cn(
                  'rounded border px-1.5 py-0.5 text-[10px] font-semibold',
                  getTierColor(tier),
                )}
              >
                {tier}
              </span>
            )}
            {candidate.country && (
              <CountryFlag countryCode={candidate.country} size="sm" />
            )}
            {isTienda(candidate.bio) && (
              <span className="rounded border border-warning/30 bg-warning/10 px-1.5 py-0.5 text-[10px] font-medium text-warning">
                Tienda
              </span>
            )}
          </div>
          {candidate.url ? (
            <a
              href={candidate.url}
              target="_blank"
              rel="noopener noreferrer"
              className="mt-0.5 inline-flex items-center gap-1 text-xs text-muted-foreground hover:text-primary hover:underline"
            >
              @{candidate.handle}
              <ExternalLink className="h-3 w-3" aria-hidden="true" />
            </a>
          ) : (
            <p className="mt-0.5 text-xs text-muted-foreground">@{candidate.handle}</p>
          )}
          {!compact && candidate.bio && (
            <p className="mt-2 line-clamp-2 text-xs leading-5 text-muted-foreground">
              {candidate.bio}
            </p>
          )}
          <div className="mt-2 flex flex-wrap items-center gap-x-3 gap-y-0.5 text-xs text-muted-foreground">
            <span>{formatFollowers(candidate.followers)}</span>
            <span className="text-muted-foreground/40">·</span>
            <span>{formatEngagement(candidate.engagement_rate)}</span>
            {candidate.city && (
              <>
                <span className="text-muted-foreground/40">·</span>
                <span>{candidate.city}</span>
              </>
            )}
          </div>
        </div>
        <div className="shrink-0 flex flex-col items-center gap-1">
          <MatchScoreCircle
            score={candidate.match_score ?? candidate.niche_relevance ?? 0}
            size="md"
            breakdown={{
              niche: candidate.niche_relevance,
              geo: candidate.geo_relevance,
              engagement: candidate.audience_relevance,
              commercial: candidate.content_quality,
            }}
          />
          <span className="text-[9px] uppercase tracking-widest font-medium text-muted-foreground">
            afinidad
          </span>
        </div>
      </div>
      {candidate.rationale && !compact && (
        <p className="mt-3 border-t border-divider pt-3 text-xs leading-5 text-muted-foreground">
          {candidate.rationale}
        </p>
      )}
      {(onSave || onDismiss) && (
        <div className="mt-3 flex gap-2 border-t border-divider pt-3">
          {onSave && (
            <Button
              type="button"
              size="sm"
              onClick={() => onSave(candidate.id)}
              className="flex-1 text-xs"
            >
              Guardar
            </Button>
          )}
          {onDismiss && (
            <Button
              type="button"
              size="sm"
              variant="outline"
              onClick={() => onDismiss(candidate.id)}
              className="flex-1 text-xs"
            >
              Descartar
            </Button>
          )}
        </div>
      )}
    </article>
  )
}
