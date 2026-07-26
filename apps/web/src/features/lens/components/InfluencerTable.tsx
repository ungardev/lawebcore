import { Card } from '@/components/ui/card';
import { PlatformBadge } from './PlatformBadge';
import { MatchScoreCircle } from './MatchScoreCircle';
import type { DiscoveryCandidate } from '../types/discovery';

interface InfluencerCardProps {
  candidates: DiscoveryCandidate[];
  onSave?: (id: string) => void;
  onDismiss?: (id: string) => void;
}

function formatFollowers(n: number | null): string {
  if (n === null) return '—';
  if (n >= 1_000_000) return `${(n / 1_000_000).toFixed(1)}M`;
  if (n >= 1_000) return `${(n / 1_000).toFixed(0)}K`;
  return n.toString();
}

function formatER(r: number | null): string {
  if (r === null) return '—';
  if (r > 1) return `${r.toFixed(1)}%`;
  return `${(r * 100).toFixed(1)}%`;
}

export function InfluencerTable({ candidates, onSave, onDismiss }: InfluencerCardProps) {
  if (!candidates.length) return null;

  return (
    <Card className="overflow-hidden mt-3">
      <div className="px-4 py-2 border-b bg-muted/30 flex items-center justify-between">
        <p className="text-xs font-semibold text-foreground">Candidatos encontrados ({candidates.length})</p>
        <div className="flex gap-3 text-[10px] text-muted-foreground">
          <span>ER</span>
          <span>Score</span>
          <span>Alcance</span>
        </div>
      </div>
      <div className="divide-y divide-border/50">
        {candidates.map((c) => (
          <div key={c.id} className="flex items-center gap-3 px-4 py-2.5 hover:bg-muted/30 transition-colors">
            <div className="w-8 h-8 rounded-full bg-primary/10 flex items-center justify-center flex-shrink-0 overflow-hidden">
              {c.avatar_url ? (
                <img src={c.avatar_url} alt={c.handle} className="w-full h-full object-cover" />
              ) : (
                <span className="text-xs font-bold text-primary">{c.handle?.[0]?.toUpperCase()}</span>
              )}
            </div>
            <div className="flex-1 min-w-0">
              <div className="flex items-center gap-1.5">
                <p className="text-sm font-semibold truncate">{c.handle}</p>
                {c.platform && <PlatformBadge platform={c.platform} size="xs" />}
                {c.country && (
                  <span className="text-[10px] text-muted-foreground">{c.country}</span>
                )}
              </div>
              <p className="text-[10px] text-muted-foreground truncate">
                {c.full_name || '—'} · {c.bio?.slice(0, 60) || 'Sin bio'}
              </p>
            </div>
            <div className="flex items-center gap-3 flex-shrink-0">
              <div className="text-right">
                <p className="text-xs font-medium">{formatER(c.engagement_rate)}</p>
                <p className="text-[10px] text-muted-foreground">ER</p>
              </div>
              {c.match_score != null && (
                <MatchScoreCircle score={c.match_score} size="sm" />
              )}
              <div className="text-right">
                <p className="text-xs font-medium">{formatFollowers(c.followers)}</p>
                <p className="text-[10px] text-muted-foreground">seguidores</p>
              </div>
              <div className="flex gap-1">
                {onSave && (
                  <button
                    onClick={() => onSave(c.id)}
                    className="px-2 py-1 text-[10px] rounded bg-emerald-500/10 text-emerald-600 hover:bg-emerald-500/20 transition-colors font-medium"
                  >
                    Guardar
                  </button>
                )}
                {onDismiss && (
                  <button
                    onClick={() => onDismiss(c.id)}
                    className="px-2 py-1 text-[10px] rounded bg-red-500/10 text-red-500 hover:bg-red-500/20 transition-colors"
                  >
                    Descartar
                  </button>
                )}
              </div>
            </div>
          </div>
        ))}
      </div>
    </Card>
  );
}
