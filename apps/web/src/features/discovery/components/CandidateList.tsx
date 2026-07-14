import { useState } from 'react';
import type { DiscoveryCandidate, Platform } from '../types/discovery';
import { CandidateCard } from './CandidateCard';
import { PlatformBadge } from './PlatformBadge';
import { cn } from '@/lib/utils';

interface CandidateListProps {
  candidates: DiscoveryCandidate[];
  onSave?: (id: string) => void;
  onDismiss?: (id: string) => void;
  isLoading?: boolean;
}

const ALL_PLATFORMS: Platform[] = ['instagram', 'tiktok', 'youtube', 'x', 'facebook'];

export function CandidateList({ candidates, onSave, onDismiss, isLoading }: CandidateListProps) {
  const [platformFilter, setPlatformFilter] = useState<Platform | 'all'>('all');

  const filtered = platformFilter === 'all'
    ? candidates
    : candidates.filter((c) => c.platform === platformFilter);

  return (
    <div className="space-y-3">
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
