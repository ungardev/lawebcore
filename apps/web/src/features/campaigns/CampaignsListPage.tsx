import { useQuery } from '@tanstack/react-query';
import { Link, useNavigate, useSearchParams } from 'react-router-dom';
import { Plus, Search, X } from 'lucide-react';
import { useState } from 'react';
import { campaignsApi, clientsApi, brandsApi } from '@/lib/api';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Card } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { CAMPAIGN_STATUSES, STATUS_COLORS, OBJECTIVE_COLORS, formatCurrency } from '@/lib/utils';
import { ResponsiveTable } from '@/components/data-table/ResponsiveTable';
import { NewCampaignModal } from './components/NewCampaignModal';

export function CampaignsListPage() {
  const navigate = useNavigate();
  const [searchParams] = useSearchParams();
  const [search, setSearch] = useState('');
  const [statusFilter, setStatusFilter] = useState<string>(searchParams.get('status') || '');
  const [newCampaignOpen, setNewCampaignOpen] = useState(false);

  const { data: campaigns, isLoading } = useQuery({
    queryKey: ['campaigns', { search, statusFilter }],
    queryFn: () => campaignsApi.list({ search: search || undefined, status: statusFilter || undefined }),
  });

  const { data: clients } = useQuery({ queryKey: ['clients'], queryFn: () => clientsApi.list() });
  const { data: brands } = useQuery({ queryKey: ['brands'], queryFn: () => brandsApi.list() });

  const clientMap = new Map((clients || []).map((c) => [c.id, c]));
  const brandMap = new Map((brands || []).map((b) => [b.id, b]));

  return (
    <div className="space-y-4 md:space-y-6">
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-3">
        <div>
          <h1 className="text-2xl md:text-3xl font-bold">Campanas</h1>
          <p className="text-sm md:text-base text-muted-foreground">{campaigns?.length ?? 0} campanas registradas</p>
        </div>
        <div className="flex gap-2 w-full sm:w-auto">
          <Button variant="outline" asChild className="flex-1 sm:flex-none">
            <Link to="/campaigns/kanban">
              <Plus className="w-4 h-4 mr-2" />
              Pipeline
            </Link>
          </Button>
          <Button className="flex-1 sm:flex-none" onClick={() => setNewCampaignOpen(true)}>
            <Plus className="w-4 h-4 mr-2" />
            Nueva Campana
          </Button>
        </div>
      </div>

      <Card className="p-3 md:p-4">
        {statusFilter && (
          <div className="mb-3 flex items-center gap-2">
            <span className="text-xs bg-primary/10 text-primary px-2 py-1 rounded-md font-medium">
              Status: {statusFilter.replace(/_/g, ' ')}
            </span>
            <button
              onClick={() => { setStatusFilter(''); navigate('/campaigns'); }}
              className="text-muted-foreground hover:text-foreground transition-colors"
            >
              <X className="w-3 h-3" />
            </button>
          </div>
        )}
        <div className="flex flex-col sm:flex-row gap-2 sm:gap-3 mb-4">
          <div className="relative flex-1">
            <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-muted-foreground" />
            <Input placeholder="Buscar campana..." value={search} onChange={(e) => setSearch(e.target.value)} className="pl-9" />
          </div>
          <select
            value={statusFilter}
            onChange={(e) => setStatusFilter(e.target.value)}
            className="h-9 px-3 rounded-md border border-input bg-transparent text-sm w-full sm:w-auto"
          >
            <option value="">Todos los status</option>
            {CAMPAIGN_STATUSES.map((s) => (
              <option key={s} value={s}>{s.replace(/_/g, ' ')}</option>
            ))}
          </select>
        </div>

        <ResponsiveTable
          data={campaigns || []}
          keyExtractor={(c) => c.id}
          onRowClick={(c) => navigate(`/campaigns/${c.id}`)}
          loading={isLoading}
          emptyMessage="No hay campanas"
          columns={[
            { key: 'code', label: 'Codigo', render: (c: any) => <span className="font-mono text-xs">{c.code}</span> },
            { key: 'name', label: 'Nombre', render: (c: any) => <span className="font-medium">{c.name}</span> },
            {
              key: 'client_brand',
              label: 'Cliente / Marca',
              render: (c: any) => (
                <div>
                  <div className="text-sm">{clientMap.get(c.client_id)?.name || '—'}</div>
                  <div className="text-xs text-muted-foreground">{brandMap.get(c.brand_id)?.name || '—'}</div>
                </div>
              ),
            },
            {
              key: 'objective',
              label: 'Objetivo',
              render: (c: any) => <Badge variant="outline" className={OBJECTIVE_COLORS[c.objective]}>{c.objective}</Badge>,
            },
            {
              key: 'tiers',
              label: 'Tiers',
              render: (c: any) => (
                <div className="flex gap-1 flex-wrap">
                  {c.influencer_tiers.map((t: string) => (
                    <Badge key={t} variant="outline" className="text-xs">{t}</Badge>
                  ))}
                </div>
              ),
            },
            { key: 'num_inf', label: '# Inf.', className: 'text-right', render: (c: any) => c.num_influencers },
            {
              key: 'budget',
              label: 'Budget',
              className: 'text-right',
              render: (c: any) => formatCurrency(c.budget_total, c.budget_currency),
            },
            {
              key: 'status',
              label: 'Status',
              render: (c: any) => <Badge variant="outline" className={STATUS_COLORS[c.status]}>{c.status.replace(/_/g, ' ')}</Badge>,
            },
          ]}
          cardFields={[
            {
              key: 'name',
              label: '',
              primary: true,
              render: (c: any) => (
                <div>
                  <div className="font-medium">{c.name}</div>
                  <div className="text-xs text-muted-foreground font-mono">{c.code}</div>
                </div>
              ),
            },
            {
              key: 'client',
              label: 'Cliente',
              render: (c: any) => clientMap.get(c.client_id)?.name || '—',
            },
            {
              key: 'brand',
              label: 'Marca',
              render: (c: any) => brandMap.get(c.brand_id)?.name || '—',
            },
            {
              key: 'status',
              label: 'Status',
              render: (c: any) => <Badge variant="outline" className={STATUS_COLORS[c.status]}>{c.status.replace(/_/g, ' ')}</Badge>,
            },
            {
              key: 'budget',
              label: 'Budget',
              render: (c: any) => formatCurrency(c.budget_total, c.budget_currency),
            },
            {
              key: 'objective',
              label: 'Objetivo',
              render: (c: any) => <Badge variant="outline" className={OBJECTIVE_COLORS[c.objective]}>{c.objective}</Badge>,
            },
          ]}
        />
      </Card>

      <NewCampaignModal open={newCampaignOpen} onClose={() => setNewCampaignOpen(false)} />
    </div>
  );
}
