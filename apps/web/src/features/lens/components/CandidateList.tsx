import { useState } from 'react';
import { Download, FileSpreadsheet } from 'lucide-react';
import type { DiscoveryCandidate, Platform } from '../types/discovery';
import { CandidateCard } from './CandidateCard';
import { PlatformBadge } from './PlatformBadge';
import { lensApi } from '../api/lensApi';
import { cn } from '@/lib/utils';

interface CandidateListProps {
  candidates: DiscoveryCandidate[];
  onSave?: (id: string) => void;
  onDismiss?: (id: string) => void;
  isLoading?: boolean;
  runId?: string;
}

const ALL_PLATFORMS: Platform[] = ['instagram', 'tiktok', 'youtube', 'x', 'facebook'];
const ALL_TIERS = ['NANO', 'MICRO', 'MID', 'MACRO'] as const;

export function CandidateList({ candidates, onSave, onDismiss, isLoading, runId }: CandidateListProps) {
  const [platformFilter, setPlatformFilter] = useState<Platform | 'all'>('all');
  const [tierFilter, setTierFilter] = useState<string>('all');

  const savedCount = candidates.filter((c) => c.status === 'saved').length;

  let filtered = candidates;
  if (platformFilter !== 'all') {
    filtered = filtered.filter((c) => c.platform === platformFilter);
  }
  if (tierFilter !== 'all') {
    filtered = filtered.filter((c) => c.tier === tierFilter);
  }

  return (
    <div className="space-y-3">
      <div className="flex items-center justify-between gap-2 flex-wrap">
        <div className="flex items-center gap-2 flex-wrap">
          <button
            onClick={() => setPlatformFilter('all')}
            className={cn(
              'text-xs px-2 py-1 rounded-md border transition-colors',
              platformFilter === 'all'
                ? 'bg-primary text-primary-foreground border-primary'
                : 'border-border hover:bg-muted',
            )}
          >
            Todos ({candidates.length})
          </button>
          {ALL_PLATFORMS.filter((p) => candidates.some((c) => c.platform === p)).map((platform) => (
            <button
              key={platform}
              onClick={() => setPlatformFilter(platform)}
              className={cn(
                'text-xs px-2 py-1 rounded-md border transition-colors flex items-center gap-1',
                platformFilter === platform
                  ? 'bg-primary text-primary-foreground border-primary'
                  : 'border-border hover:bg-muted',
              )}
            >
              <PlatformBadge platform={platform} size="sm" />
              ({candidates.filter((c) => c.platform === platform).length})
            </button>
          ))}
          <div className="w-px h-4 bg-border" />
          {ALL_TIERS.filter((t) => candidates.some((c) => c.tier === t)).map((tier) => (
            <button
              key={tier}
              onClick={() => setTierFilter(tierFilter === tier ? 'all' : tier)}
              className={cn(
                'text-xs px-2 py-1 rounded-md border transition-colors font-medium',
                tierFilter === tier
                  ? 'bg-brand-purple text-white border-brand-purple'
                  : 'border-border hover:bg-muted text-muted-foreground',
              )}
            >
              {tier}
            </button>
          ))}
        </div>

        {savedCount > 0 && runId ? (
          <a
            href={lensApi.search.getProposalUrl(runId)}
            download
            className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-brand-purple text-white text-xs font-medium hover:opacity-90 transition-opacity shadow-sm"
          >
            <FileSpreadsheet className="w-3.5 h-3.5" />
            Descargar CSV ({savedCount})
          </a>
        ) : candidates.length > 0 ? (
          <span className="text-[11px] text-muted-foreground">
            Guarda al menos 1 candidato para descargar propuesta CSV
          </span>
        ) : null}
      </div>

      {isLoading ? (
        <div className="space-y-3">
          {[1, 2, 3].map((i) => (
            <div key={i} className="h-28 rounded-xl bg-muted animate-pulse" />
          ))}
        </div>
      ) : filtered.length === 0 ? (
        <p className="text-sm text-muted-foreground text-center py-8">No hay candidatos para este filtro.</p>
      ) : (
        <div className="space-y-3">
          {filtered.map((candidate) => (
            <CandidateCard
              key={candidate.id}
              candidate={candidate}
              onSave={onSave}
              onDismiss={onDismiss}
            />
          ))}
        </div>
      )}
    </div>
  );
}
