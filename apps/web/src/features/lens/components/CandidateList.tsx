import { useState } from 'react';
import { FileSpreadsheet } from 'lucide-react';
import { Button } from '@/components/ui/button';
import type { DiscoveryCandidate, Platform } from '../types/discovery';
import { CandidateCard } from './CandidateCard';
import { PlatformBadge } from './PlatformBadge';
import { lensApi } from '../api/lensApi';

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
          <Button
            type="button"
            size="sm"
            variant={platformFilter === 'all' ? 'default' : 'outline'}
            onClick={() => setPlatformFilter('all')}
            className="h-8 text-xs"
          >
            Todos ({candidates.length})
          </Button>
          {ALL_PLATFORMS.filter((p) => candidates.some((c) => c.platform === p)).map((platform) => (
            <Button
              key={platform}
              type="button"
              size="sm"
              variant={platformFilter === platform ? 'default' : 'outline'}
              onClick={() => setPlatformFilter(platform)}
              className="h-8 gap-1 text-xs"
            >
              <PlatformBadge platform={platform} size="sm" />
              ({candidates.filter((c) => c.platform === platform).length})
            </Button>
          ))}
          <div className="h-4 w-px bg-divider" />
          {ALL_TIERS.filter((t) => candidates.some((c) => c.tier === t)).map((tier) => (
            <Button
              key={tier}
              type="button"
              size="sm"
              variant={tierFilter === tier ? 'default' : 'outline'}
              onClick={() => setTierFilter(tierFilter === tier ? 'all' : tier)}
              className="h-8 text-xs font-medium"
            >
              {tier}
            </Button>
          ))}
        </div>

        {savedCount > 0 && runId ? (
          <Button asChild size="sm" className="gap-1.5 text-xs"><a href={lensApi.search.getProposalUrl(runId)} download>
            <FileSpreadsheet className="w-3.5 h-3.5" />
            Descargar CSV ({savedCount})
          </a></Button>
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
        <>
          {candidates.length > 0 && candidates.length < 15 && !isLoading && (
            <div className="rounded-md border border-warning/30 bg-warning/10 px-4 py-3 text-xs text-warning">
              <strong>Solo {candidates.length} candidatos.</strong> Para ver más resultados intenta ampliar hashtags o palabras clave en el brief.
            </div>
          )}
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
        </>
      )}
    </div>
  );
}
