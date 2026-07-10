import { useQuery } from '@tanstack/react-query';
import { influencersApi } from '@/lib/api';
import { Card } from '@/components/ui/card';
import { Input } from '@/components/ui/input';
import { Search } from 'lucide-react';
import { useState } from 'react';
import { ResponsiveTable } from '@/components/data-table/ResponsiveTable';
import { InfluencerScoreBadge } from './InfluencerScoreBadge';
import { InfluencerScore } from '@/types/piar';

const TIER_COLORS: Record<string, string> = {
  NANO: 'bg-slate-100 text-slate-700',
  MICRO: 'bg-blue-100 text-blue-700',
  MID: 'bg-purple-100 text-purple-700',
  MACRO: 'bg-amber-100 text-amber-700',
  MEGA: 'bg-rose-100 text-rose-700',
  MIX: 'bg-pink-100 text-pink-700',
};

interface InfluencerWithScore {
  id: string;
  full_name: string;
  primary_handle?: string;
  primary_tier: string;
  status: string;
  country: string;
  content_niches: string[];
  score?: InfluencerScore;
}

export function InfluencersPage() {
  const [search, setSearch] = useState('');
  const [tier, setTier] = useState('');
  const [decision, setDecision] = useState('');

  const useScoring = decision !== '';

  const { data: influencers, isLoading } = useQuery({
    queryKey: ['influencers', { search, tier, decision, useScoring }],
    queryFn: () => {
      if (useScoring) {
        return influencersApi.listWithScores({
          search: search || undefined,
          tier: tier || undefined,
          decision: decision || undefined,
        }) as Promise<InfluencerWithScore[]>;
      }
      return influencersApi.list({ search: search || undefined, tier: tier || undefined }) as Promise<InfluencerWithScore[]>;
    },
  });

  return (
    <div className="space-y-4 md:space-y-6">
      <div>
        <h1 className="text-2xl md:text-3xl font-bold">Influencers</h1>
        <p className="text-sm md:text-base text-muted-foreground">{influencers?.length ?? 0} influencers en la base</p>
      </div>

      <Card className="p-3 md:p-4">
        <div className="flex flex-col sm:flex-row gap-2 sm:gap-3 mb-4">
          <div className="relative flex-1">
            <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-muted-foreground" />
            <Input placeholder="Buscar..." value={search} onChange={(e) => setSearch(e.target.value)} className="pl-9" />
          </div>
          <select value={tier} onChange={(e) => setTier(e.target.value)} className="h-9 px-3 rounded-md border border-input bg-transparent text-sm w-full sm:w-auto">
            <option value="">Todos los tiers</option>
            <option value="NANO">Nano (&lt;10K)</option>
            <option value="MICRO">Micro (10-100K)</option>
            <option value="MID">Mid (100-500K)</option>
            <option value="MACRO">Macro (&gt;500K)</option>
            <option value="MEGA">Mega</option>
          </select>
          <select value={decision} onChange={(e) => setDecision(e.target.value)} className="h-9 px-3 rounded-md border border-input bg-transparent text-sm w-full sm:w-auto">
            <option value="">Todos los scores</option>
            <option value="ESCALAR">Escalar</option>
            <option value="OPTIMIZAR">Optimizar</option>
            <option value="DESCARTAR">Descartar</option>
            <option value="DATOS_INSUFICIENTES">Sin datos</option>
          </select>
        </div>

        <ResponsiveTable
          data={influencers || []}
          keyExtractor={(inf) => inf.id}
          loading={isLoading}
          emptyMessage="No hay influencers"
          columns={[
            { key: 'full_name', label: 'Nombre', render: (inf: InfluencerWithScore) => <span className="font-medium">{inf.full_name}</span> },
            { key: 'handle', label: 'Handle', render: (inf: InfluencerWithScore) => <span className="text-sm text-muted-foreground">{inf.primary_handle || '—'}</span> },
            { key: 'tier', label: 'Tier', render: (inf: InfluencerWithScore) => <span className="inline-flex items-center gap-1"><span className={`px-2 py-0.5 rounded text-xs font-medium ${TIER_COLORS[inf.primary_tier] || ''}`}>{inf.primary_tier}</span></span> },
            { key: 'country', label: 'Pais', render: (inf: InfluencerWithScore) => inf.country },
            {
              key: 'niches',
              label: 'Nichos',
              render: (inf: InfluencerWithScore) => (
                <div className="flex gap-1 flex-wrap">
                  {(inf.content_niches || []).slice(0, 3).map((n: string) => (
                    <span key={n} className="text-xs bg-muted px-1.5 py-0.5 rounded">{n}</span>
                  ))}
                </div>
              ),
            },
            ...(useScoring
              ? [{
                  key: 'score' as const,
                  label: 'Score',
                  render: (inf: InfluencerWithScore) => (
                    <InfluencerScoreBadge score={inf.score ?? null} size="sm" showLabel />
                  ),
                }]
              : []),
            { key: 'status', label: 'Estado', render: (inf: InfluencerWithScore) => inf.status },
          ]}
          cardFields={[
            { key: 'full_name', label: '', primary: true, render: (inf: InfluencerWithScore) => <span className="font-medium">{inf.full_name}</span> },
            { key: 'handle', label: 'Handle', render: (inf: InfluencerWithScore) => <span className="text-sm text-muted-foreground">{inf.primary_handle || '—'}</span> },
            { key: 'tier', label: 'Tier', render: (inf: InfluencerWithScore) => <span className={`px-2 py-0.5 rounded text-xs font-medium ${TIER_COLORS[inf.primary_tier] || ''}`}>{inf.primary_tier}</span> },
            { key: 'country', label: 'Pais', render: (inf: InfluencerWithScore) => inf.country },
            { key: 'status', label: 'Estado', render: (inf: InfluencerWithScore) => inf.status },
          ]}
        />
      </Card>
    </div>
  );
}
