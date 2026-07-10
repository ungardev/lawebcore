import { useQuery } from '@tanstack/react-query';
import { influencersApi } from '@/lib/api';
import { Card } from '@/components/ui/card';
import { Table, TableHeader, TableBody, TableRow, TableHead, TableCell } from '@/components/ui/table';
import { Badge } from '@/components/ui/badge';
import { Input } from '@/components/ui/input';
import { Search } from 'lucide-react';
import { useState } from 'react';
import { ResponsiveTable } from '@/components/data-table/ResponsiveTable';

const TIER_COLORS: Record<string, string> = {
  NANO: 'bg-slate-100 text-slate-700',
  MICRO: 'bg-blue-100 text-blue-700',
  MID: 'bg-purple-100 text-purple-700',
  MACRO: 'bg-amber-100 text-amber-700',
  MEGA: 'bg-rose-100 text-rose-700',
  MIX: 'bg-pink-100 text-pink-700',
};

export function InfluencersPage() {
  const [search, setSearch] = useState('');
  const [tier, setTier] = useState('');
  const { data: influencers, isLoading } = useQuery({
    queryKey: ['influencers', { search, tier }],
    queryFn: () => influencersApi.list({ search: search || undefined, tier: tier || undefined }),
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
        </div>

        <ResponsiveTable
          data={influencers || []}
          keyExtractor={(inf) => inf.id}
          loading={isLoading}
          emptyMessage="No hay influencers"
          columns={[
            { key: 'full_name', label: 'Nombre', render: (inf: any) => <span className="font-medium">{inf.full_name}</span> },
            { key: 'handle', label: 'Handle', render: (inf: any) => <span className="text-sm text-muted-foreground">{inf.primary_handle || '—'}</span> },
            { key: 'tier', label: 'Tier', render: (inf: any) => <Badge variant="outline" className={TIER_COLORS[inf.primary_tier]}>{inf.primary_tier}</Badge> },
            { key: 'country', label: 'Pais', render: (inf: any) => inf.country },
            {
              key: 'niches',
              label: 'Nichos',
              render: (inf: any) => (
                <div className="flex gap-1 flex-wrap">
                  {inf.content_niches.slice(0, 3).map((n: string) => (
                    <Badge key={n} variant="outline" className="text-xs">{n}</Badge>
                  ))}
                </div>
              ),
            },
            { key: 'status', label: 'Estado', render: (inf: any) => inf.status },
          ]}
          cardFields={[
            { key: 'full_name', label: '', primary: true, render: (inf: any) => <span className="font-medium">{inf.full_name}</span> },
            { key: 'handle', label: 'Handle', render: (inf: any) => <span className="text-sm text-muted-foreground">{inf.primary_handle || '—'}</span> },
            { key: 'tier', label: 'Tier', render: (inf: any) => <Badge variant="outline" className={TIER_COLORS[inf.primary_tier]}>{inf.primary_tier}</Badge> },
            { key: 'country', label: 'Pais', render: (inf: any) => inf.country },
            { key: 'status', label: 'Estado', render: (inf: any) => inf.status },
          ]}
        />
      </Card>
    </div>
  );
}
