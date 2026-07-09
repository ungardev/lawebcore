import { useQuery } from '@tanstack/react-query';
import { Link } from 'react-router-dom';
import { Plus, Search } from 'lucide-react';
import { useState } from 'react';
import { campaignsApi, clientsApi, brandsApi } from '@/lib/api';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Card } from '@/components/ui/card';
import { Table, TableHeader, TableBody, TableRow, TableHead, TableCell } from '@/components/ui/table';
import { Badge } from '@/components/ui/badge';
import { CAMPAIGN_STATUSES, STATUS_COLORS, OBJECTIVE_COLORS, formatCurrency } from '@/lib/utils';

export function CampaignsListPage() {
  const [search, setSearch] = useState('');
  const [statusFilter, setStatusFilter] = useState<string>('');

  const { data: campaigns, isLoading } = useQuery({
    queryKey: ['campaigns', { search, statusFilter }],
    queryFn: () => campaignsApi.list({ search: search || undefined, status: statusFilter || undefined }),
  });

  const { data: clients } = useQuery({ queryKey: ['clients'], queryFn: () => clientsApi.list() });
  const { data: brands } = useQuery({ queryKey: ['brands'], queryFn: () => brandsApi.list() });

  const clientMap = new Map((clients || []).map((c) => [c.id, c]));
  const brandMap = new Map((brands || []).map((b) => [b.id, b]));

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold">Campanas</h1>
          <p className="text-muted-foreground">{campaigns?.length ?? 0} campanas registradas</p>
        </div>
        <Button asChild>
          <Link to="/campaigns/kanban">
            <Plus className="w-4 h-4 mr-2" />
            Ver Pipeline
          </Link>
        </Button>
      </div>

      <Card className="p-4">
        <div className="flex gap-3 mb-4">
          <div className="relative flex-1">
            <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-muted-foreground" />
            <Input placeholder="Buscar campana..." value={search} onChange={(e) => setSearch(e.target.value)} className="pl-9" />
          </div>
          <select
            value={statusFilter}
            onChange={(e) => setStatusFilter(e.target.value)}
            className="h-9 px-3 rounded-md border border-input bg-transparent text-sm"
          >
            <option value="">Todos los status</option>
            {CAMPAIGN_STATUSES.map((s) => (
              <option key={s} value={s}>{s.replace(/_/g, ' ')}</option>
            ))}
          </select>
        </div>

        <Table>
          <TableHeader>
            <TableRow>
              <TableHead>Codigo</TableHead>
              <TableHead>Nombre</TableHead>
              <TableHead>Cliente / Marca</TableHead>
              <TableHead>Objetivo</TableHead>
              <TableHead>Tiers</TableHead>
              <TableHead className="text-right"># Inf.</TableHead>
              <TableHead className="text-right">Budget</TableHead>
              <TableHead>Status</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {isLoading && (
              <TableRow><TableCell colSpan={8} className="text-center text-muted-foreground py-8">Cargando...</TableCell></TableRow>
            )}
            {campaigns?.map((c) => {
              const client = clientMap.get(c.client_id);
              const brand = brandMap.get(c.brand_id);
              return (
                <TableRow key={c.id} className="cursor-pointer hover:bg-accent">
                  <TableCell className="font-mono text-xs">
                    <Link to={`/campaigns/${c.id}`}>{c.code}</Link>
                  </TableCell>
                  <TableCell className="font-medium">
                    <Link to={`/campaigns/${c.id}`}>{c.name}</Link>
                  </TableCell>
                  <TableCell>
                    <div className="text-sm">{client?.name || '—'}</div>
                    <div className="text-xs text-muted-foreground">{brand?.name || '—'}</div>
                  </TableCell>
                  <TableCell>
                    <Badge variant="outline" className={OBJECTIVE_COLORS[c.objective]}>{c.objective}</Badge>
                  </TableCell>
                  <TableCell>
                    <div className="flex gap-1 flex-wrap">
                      {c.influencer_tiers.map((t) => (
                        <Badge key={t} variant="outline" className="text-xs">{t}</Badge>
                      ))}
                    </div>
                  </TableCell>
                  <TableCell className="text-right">{c.num_influencers}</TableCell>
                  <TableCell className="text-right">{formatCurrency(c.budget_total, c.budget_currency)}</TableCell>
                  <TableCell>
                    <Badge variant="outline" className={STATUS_COLORS[c.status]}>{c.status.replace(/_/g, ' ')}</Badge>
                  </TableCell>
                </TableRow>
              );
            })}
            {!isLoading && campaigns?.length === 0 && (
              <TableRow><TableCell colSpan={8} className="text-center text-muted-foreground py-8">No hay campanas</TableCell></TableRow>
            )}
          </TableBody>
        </Table>
      </Card>
    </div>
  );
}