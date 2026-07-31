import { useState } from 'react'
import { cn } from '@/lib/utils'

interface ScoreBreakdown {
  niche?: number | null
  geo?: number | null
  engagement?: number | null
  commercial?: number | null
}

interface MatchScoreCircleProps {
  score: number
  size?: 'sm' | 'md' | 'lg'
  showLabel?: boolean
  breakdown?: ScoreBreakdown | null
}

export function MatchScoreCircle({
  score,
  size = 'md',
  showLabel = false,
  breakdown,
}: MatchScoreCircleProps) {
  const [showTooltip, setShowTooltip] = useState(false)
  const clampedScore = Math.max(0, Math.min(100, score))

  const scoreColor =
    clampedScore >= 80
      ? 'bg-success'
      : clampedScore >= 60
        ? 'bg-warning'
        : clampedScore >= 40
          ? 'bg-brand-pink'
          : 'bg-destructive'

  const sizeClasses = {
    sm: 'w-11 h-11 text-sm',
    md: 'w-14 h-14 text-lg',
    lg: 'w-20 h-20 text-2xl',
  }

  return (
    <div className="relative inline-flex items-center justify-center">
      <div
        className="relative"
        onMouseEnter={() => breakdown && setShowTooltip(true)}
        onMouseLeave={() => setShowTooltip(false)}
      >
        <div
          className={cn(
            'rounded-full flex items-center justify-center font-bold text-white ring-2 ring-white/20 shadow-sm',
            sizeClasses[size],
            scoreColor,
          )}
        >
          {Math.round(clampedScore)}
        </div>
        {showTooltip && breakdown && (
          <div className="absolute bottom-full left-1/2 z-50 mb-2 -translate-x-1/2 whitespace-nowrap rounded-md border border-divider bg-popover p-2 text-xs shadow-lg">
            <div className="mb-1 text-[10px] uppercase tracking-wide text-muted-foreground">
              Desglose de afinidad
            </div>
            {breakdown.niche != null && (
              <div>
                Nicho: <span className="font-medium">{Math.round(breakdown.niche)}</span>
              </div>
            )}
            {breakdown.geo != null && (
              <div>
                Geo: <span className="font-medium">{Math.round(breakdown.geo)}</span>
              </div>
            )}
            {breakdown.engagement != null && (
              <div>
                Engagement: <span className="font-medium">{Math.round(breakdown.engagement)}</span>
              </div>
            )}
            {breakdown.commercial != null && (
              <div>
                Comercial: <span className="font-medium">{Math.round(breakdown.commercial)}</span>
              </div>
            )}
            <div className="mt-1 border-t border-divider pt-1">
              Total: <span className="font-bold">{Math.round(clampedScore)}/100</span>
            </div>
          </div>
        )}
      </div>
      {showLabel && (
        <span className="absolute -bottom-4 text-[9px] text-muted-foreground">match</span>
      )}
    </div>
  )
}
