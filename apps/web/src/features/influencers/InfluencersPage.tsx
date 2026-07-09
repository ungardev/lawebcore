import { useQuery } from '@tanstack/react-query';
import { influencersApi } from '@/lib/api';
import { Card } from '@/components/ui/card';
import { Table, TableHeader, TableBody, TableRow, TableHead, TableCell } from '@/components/ui/table';
import { Badge } from '@/components/ui/badge';
import { Input } from '@/components/ui/input';
import { Search } from 'lucide-react';
import { useState } from 'react';

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
  const { data: influencers } = useQuery({
    queryKey: ['influencers', { search, tier }],
    queryFn: () => influencersApi.list({ search: search || undefined, tier: tier || undefined }),
  });

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-3xl font-bold">Influencers</h1>
        <p className="text-muted-foreground">{influencers?.length ?? 0} influencers en la base</p>
      </div>

      <Card className="p-4">
        <div className="flex gap-3 mb-4">
          <div className="relative flex-1">
            <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-muted-foreground" />
            <Input placeholder="Buscar..." value={search} onChange={(e) => setSearch(e.target.value)} className="pl-9" />
          </div>
          <select value={tier} onChange={(e) => setTier(e.target.value)} className="h-9 px-3 rounded-md border border-input bg-transparent text-sm">
            <option value="">Todos los tiers</option>
            <option value="NANO">Nano (&lt;10K)</option>
            <option value="MICRO">Micro (10-100K)</option>
            <option value="MID">Mid (100-500K)</option>
            <option value="MACRO">Macro (&gt;500K)</option>
            <option value="MEGA">Mega</option>
          </select>
        </div>

        <Table>
          <TableHeader>
            <TableRow>
              <TableHead>Nombre</TableHead>
              <TableHead>Handle</TableHead>
              <TableHead>Tier</TableHead>
              <TableHead>Pais</TableHead>
              <TableHead>Nichos</TableHead>
              <TableHead>Estado</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {influencers?.map((inf) => (
              <TableRow key={inf.id}>
                <TableCell className="font-medium">{inf.full_name}</TableCell>
                <TableCell className="text-sm text-muted-foreground">{inf.primary_handle || '—'}</TableCell>
                <TableCell>
                  <Badge variant="outline" className={TIER_COLORS[inf.primary_tier]}>{inf.primary_tier}</Badge>
                </TableCell>
                <TableCell>{inf.country}</TableCell>
                <TableCell>
                  <div className="flex gap-1 flex-wrap">
                    {inf.content_niches.slice(0, 3).map((n) => (
                      <Badge key={n} variant="outline" className="text-xs">{n}</Badge>
                    ))}
                  </div>
                </TableCell>
                <TableCell>{inf.status}</TableCell>
              </TableRow>
            ))}
          </TableBody>
        </Table>
      </Card>
    </div>
  );
}