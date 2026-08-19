import { useState } from 'react'
import { Bookmark, BookmarkCheck, ExternalLink, X, BadgeCheck, Check } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { cn } from '@/lib/utils'
import {
  classifyTier,
  formatEngagement,
  formatFollowers,
  formatNumber,
  getTierColor,
  getCredibilityLabel,
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
  selectionMode?: boolean
  selected?: boolean
  onToggleSelect?: (handle: string) => void
}

export function CandidateCard({ candidate, onSave, onDismiss, compact, selectionMode, selected, onToggleSelect }: CandidateCardProps) {
  const [imgFailed, setImgFailed] = useState(false)
  const tier = candidate.tier ?? classifyTier(candidate.followers)
  const avatarUrl = candidate.avatar_url
    || (candidate.platform === 'instagram' && candidate.handle
      ? `https://instagram.com/${candidate.handle}/profile_picture`
      : null)
  const showInitials = !avatarUrl || imgFailed
  const score = candidate.match_score ?? candidate.niche_relevance ?? 0
  const isSaved = candidate.status === 'saved'
  const displayName = candidate.full_name && candidate.full_name !== candidate.handle
    ? candidate.full_name
    : null
  const credibility = getCredibilityLabel(candidate.audience_credibility)
  const rawPayload = candidate.raw_payload as Record<string, unknown> | null
  const postsAnalyzed = rawPayload?.posts_analyzed as number | null

  return (
    <article
      className={cn(
        'group relative overflow-hidden rounded-lg border bg-card text-card-foreground transition-[border-color,box-shadow,transform] duration-200 hover:-translate-y-px hover:border-primary/35 hover:shadow-soft',
        compact ? 'p-3' : 'p-4',
        selected && 'border-primary/60 bg-primary/5 ring-1 ring-primary/30',
      )}
    >
      {selectionMode && onToggleSelect && (
        <button
          type="button"
          onClick={() => onToggleSelect(candidate.handle)}
          className={cn(
            'absolute left-2 top-2 z-10 flex h-5 w-5 items-center justify-center rounded border-2 transition-colors',
            selected
              ? 'border-primary bg-primary text-background'
              : 'border-muted-foreground/40 bg-background hover:border-primary/60',
          )}
          aria-label={selected ? `Deseleccionar @${candidate.handle}` : `Seleccionar @${candidate.handle}`}
        >
          {selected && <Check className="h-3 w-3" aria-hidden="true" />}
        </button>
      )}
      <div className="flex items-start gap-3">
        {showInitials ? (
          <div
            className="relative flex h-12 w-12 shrink-0 items-center justify-center rounded-lg border border-divider bg-surface-raised text-sm font-semibold text-muted-foreground"
            aria-hidden="true"
          >
            {candidate.handle.slice(0, 2).toUpperCase()}
            {candidate.is_verified && (
              <BadgeCheck className="absolute -bottom-1 -right-1 h-4 w-4 fill-primary text-background" aria-hidden="true" />
            )}
          </div>
        ) : (
          <div className="relative shrink-0">
            <img
              src={avatarUrl ?? undefined}
              alt={displayName || `Avatar de @${candidate.handle}`}
              className="h-12 w-12 rounded-lg border border-divider object-cover"
              onError={() => setImgFailed(true)}
            />
            {candidate.is_verified && (
              <BadgeCheck className="absolute -bottom-1 -right-1 h-4 w-4 fill-primary text-background" aria-hidden="true" />
            )}
          </div>
        )}

        <div className="min-w-0 flex-1">
          <div className="flex items-center gap-1.5">
            {candidate.url ? (
              <a
                href={candidate.url}
                target="_blank"
                rel="noopener noreferrer"
                className="inline-flex max-w-full items-center gap-1.5 text-sm font-semibold text-foreground transition-colors hover:text-primary focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-focus focus-visible:ring-offset-2"
              >
                <span className="truncate">@{candidate.handle}</span>
                <PlatformIcon platform={candidate.platform} size="sm" />
                <ExternalLink className="h-3.5 w-3.5 shrink-0 text-muted-foreground" aria-hidden="true" />
                <span className="sr-only">Abrir perfil</span>
              </a>
            ) : (
              <span className="inline-flex max-w-full items-center gap-1.5 text-sm font-semibold text-foreground">
                <span className="truncate">@{candidate.handle}</span>
                <PlatformIcon platform={candidate.platform} size="sm" />
              </span>
            )}
          </div>

          {displayName && (
            <p className="mt-0.5 truncate text-xs text-muted-foreground">
              {displayName}
            </p>
          )}

          <div className="mt-2 flex flex-wrap items-center gap-1.5">
            {tier && (
              <span
                className={cn(
                  'rounded border px-1.5 py-0.5 text-[10px] font-semibold uppercase tracking-wide',
                  getTierColor(tier),
                )}
              >
                {tier}
              </span>
            )}
            {candidate.is_verified && (
              <span className="flex items-center gap-0.5 rounded border border-info/30 bg-info/10 px-1.5 py-0.5 text-[10px] font-medium text-info">
                <BadgeCheck className="h-3 w-3" aria-hidden="true" />
                Verificado
              </span>
            )}
            {candidate.is_creator && (
              <span className="flex items-center gap-0.5 rounded border border-success/30 bg-success/10 px-1.5 py-0.5 text-[10px] font-medium text-success">
                <BadgeCheck className="h-3 w-3" aria-hidden="true" />
                Creator
              </span>
            )}
            {candidate.country && <CountryFlag countryCode={candidate.country} size="sm" />}
            {candidate.city && (
              <span className="rounded border border-info/30 bg-info/10 px-1.5 py-0.5 text-[10px] font-medium text-info">
                📍 {candidate.city}
              </span>
            )}
            {!candidate.city && candidate.country === 'VE' && (
              <span className="rounded border border-info/30 bg-info/10 px-1.5 py-0.5 text-[10px] font-medium text-info">
                📍 Venezuela
              </span>
            )}
            {(() => {
              const followers = candidate.followers ?? 0;
              const er = candidate.engagement_rate ?? 0;
              const TIER_ER_BENCHMARKS: Record<string, number> = {
                NANO: 0.08,
                MICRO: 0.05,
                MID: 0.03,
                MACRO: 0.015,
              };
              const tierKey = tier as string;
              const benchmark = TIER_ER_BENCHMARKS[tierKey] ?? 0.03;
              const isRising = er > benchmark && followers > 0 && followers < 100_000;
              return isRising ? (
                <span className="rounded border border-success/30 bg-success/10 px-1.5 py-0.5 text-[10px] font-medium text-success">
                  🆕 Rising star
                </span>
              ) : null;
            })()}
            {isTienda(candidate.bio) && (
              <span className="rounded border border-warning/30 bg-warning/10 px-1.5 py-0.5 text-[10px] font-medium text-warning">
                Tienda
              </span>
            )}
          </div>
        </div>

        <div className="flex shrink-0 flex-col items-center gap-1">
          <MatchScoreCircle
            score={score}
            size="md"
            breakdown={{
              niche: candidate.niche_relevance,
              geo: candidate.geo_relevance,
              engagement: candidate.audience_relevance,
              commercial: candidate.content_quality,
            }}
          />
          <span className="text-[9px] font-medium uppercase tracking-[0.12em] text-muted-foreground">
            afinidad
          </span>
        </div>
      </div>

      {!compact && candidate.bio && (
        <p className="mt-4 line-clamp-2 text-xs leading-5 text-muted-foreground">
          {candidate.bio}
        </p>
      )}

      <div className="mt-4 grid grid-cols-4 divide-x border-y border-divider py-3">
        <Metric label="Seguidores" value={formatFollowers(candidate.followers)} />
        <Metric label="Engagement" value={formatEngagement(candidate.engagement_rate)} />
        <Metric label="Posts" value={formatNumber(candidate.posts_count)} />
        <Metric label="Credibilidad" value={credibility.label} valueColor={credibility.color} />
      </div>

      {!compact && (candidate.avg_likes != null || candidate.avg_comments != null) && (
        <div className="mt-2 grid grid-cols-2 divide-x border-b border-divider py-2">
          {candidate.avg_likes != null && (
            <Metric label="Prom. Likes" value={formatNumber(candidate.avg_likes)} />
          )}
          {candidate.avg_comments != null && (
            <Metric label="Prom. Comentarios" value={formatNumber(candidate.avg_comments)} />
          )}
        </div>
      )}

      {!compact && candidate.rationale && (
        <p className="mt-4 border-l-2 border-primary/40 pl-3 text-xs leading-5 text-muted-foreground">
          {candidate.rationale}
        </p>
      )}

      {(onSave || onDismiss) && (
        <div className="mt-4 flex gap-2">
          {onSave && (
            <Button
              type="button"
              size="sm"
              variant={isSaved ? 'secondary' : 'default'}
              onClick={() => onSave(candidate.id)}
              className="flex-1 gap-1.5 text-xs"
              aria-pressed={isSaved}
            >
              {isSaved ? <BookmarkCheck className="h-3.5 w-3.5" aria-hidden="true" /> : <Bookmark className="h-3.5 w-3.5" aria-hidden="true" />}
              {isSaved ? 'Guardado' : 'Guardar'}
            </Button>
          )}
          {onDismiss && (
            <Button
              type="button"
              size="sm"
              variant="ghost"
              onClick={() => onDismiss(candidate.id)}
              className="flex-1 gap-1.5 text-xs text-muted-foreground hover:text-foreground"
            >
              <X className="h-3.5 w-3.5" aria-hidden="true" />
              Descartar
            </Button>
          )}
        </div>
      )}
    </article>
  )
}

function Metric({ label, value, valueColor }: { label: string; value: string; valueColor?: string }) {
  return (
    <div className="min-w-0 px-2 first:pl-0 last:pr-0">
      <p className="truncate text-[10px] uppercase tracking-[0.1em] text-muted-foreground">{label}</p>
      <p className={cn("mt-1 truncate text-sm font-semibold text-foreground", valueColor)}>
        {value}
      </p>
    </div>
  )
}
