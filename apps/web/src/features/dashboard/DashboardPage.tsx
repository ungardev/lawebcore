import { useQuery } from '@tanstack/react-query';
import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { Megaphone, Building2, Tags, Users, DollarSign, Eye, TrendingUp, Filter, MessageCircle, BarChart2, CheckCircle } from 'lucide-react';
import { dashboardApi, brandsApi, clientsApi } from '@/lib/api';
import { KpiCard } from '@/components/data-table/KpiCard';
import { Card, CardHeader, CardTitle, CardContent } from '@/components/ui/card';
import { formatCurrency, formatNumber, formatPercent } from '@/lib/utils';
import { BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer, PieChart, Pie, Cell, Sector } from 'recharts';
import { Brand, Client } from '@/types';

const COLORS = ['#8b5cf6', '#ec4899', '#f59e0b', '#10b981', '#3b82f6', '#ef4444', '#06b6d4'];

const renderPieLabel = (entry: any) => entry.name;

const renderActiveShape = (props: any) => {
  const { cx, cy, innerRadius, outerRadius, startAngle, endAngle, fill } = props;
  return (
    <Sector
      cx={cx}
      cy={cy}
      innerRadius={innerRadius}
      outerRadius={outerRadius + 10}
      startAngle={startAngle}
      endAngle={endAngle}
      fill={fill}
      style={{ filter: 'drop-shadow(0 3px 6px rgba(0,0,0,0.3))' }}
    />
  );
};

const renderActiveBar = (props: any) => {
  const { x, y, width, height, fill } = props;
  return (
    <rect
      x={x}
      y={y}
      width={width}
      height={height}
      fill={fill}
      fillOpacity={0.85}
      rx={4}
      ry={4}
    />
  );
};

export function DashboardPage() {
  const navigate = useNavigate();
  const [brandFilter, setBrandFilter] = useState<string>('');
  const [clientFilter, setClientFilter] = useState<string>('');

  const handlePieClick = (data: any) => {
    if (data?.name) navigate(`/clients?search=${encodeURIComponent(data.name)}`);
  };

  const handleBarClick = (data: any) => {
    if (data?.status) navigate(`/campaigns?status=${encodeURIComponent(data.status)}`);
  };

  const renderStatusTick = (props: any) => {
    const { x, y, payload } = props;
    return (
      <text
        x={x}
        y={y + 10}
        textAnchor="end"
        fill="#8b5cf6"
        fontSize={12}
        fontWeight={500}
        style={{ cursor: 'pointer' }}
        onClick={() => navigate(`/campaigns?status=${encodeURIComponent(payload.value)}`)}
      >
        {String(payload.value).replace(/_/g, ' ')}
      </text>
    );
  };

  const { data: summary } = useQuery({ queryKey: ['dashboard-summary'], queryFn: dashboardApi.summary });
  const { data: byStatus } = useQuery({ queryKey: ['dashboard-by-status'], queryFn: dashboardApi.byStatus });
  const { data: topClients } = useQuery({ queryKey: ['dashboard-top-clients'], queryFn: () => dashboardApi.topClients() });
  const { data: brands } = useQuery({ queryKey: ['brands'], queryFn: () => brandsApi.list() });
  const { data: clients } = useQuery({ queryKey: ['clients'], queryFn: () => clientsApi.list() });

  const clientMap = new Map((clients || []).map((c: Client) => [c.id, c]));

  const hasFilter = Boolean(brandFilter || clientFilter);

  return (
    <div className="space-y-4 md:space-y-6">
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-3">
        <div>
          <h1 className="text-2xl md:text-3xl font-bold">Dashboard Ejecutivo</h1>
          <p className="text-sm md:text-base text-muted-foreground">Vision integral de campanas, clientes y KPIs</p>
        </div>
        {hasFilter && (
          <button
            onClick={() => { setBrandFilter(''); setClientFilter(''); }}
            className="text-xs text-primary hover:underline flex items-center gap-1"
          >
            <Filter className="w-3 h-3" />
            Limpiar filtro
          </button>
        )}
      </div>

      <Card className="p-3 md:p-4">
        <div className="flex flex-col sm:flex-row gap-2 sm:gap-3">
          <select
            value={clientFilter}
            onChange={(e) => { setClientFilter(e.target.value); setBrandFilter(''); }}
            className="h-9 px-3 rounded-md border border-input bg-transparent text-sm w-full sm:w-auto"
          >
            <option value="">Todas los clientes</option>
            {clients?.map((c: Client) => (
              <option key={c.id} value={c.id}>{c.name}</option>
            ))}
          </select>
          <select
            value={brandFilter}
            onChange={(e) => { setBrandFilter(e.target.value); setClientFilter(''); }}
            className="h-9 px-3 rounded-md border border-input bg-transparent text-sm w-full sm:w-auto"
          >
            <option value="">Todas las marcas</option>
            {brands?.map((b: Brand) => (
              <option key={b.id} value={b.id}>{b.name} ({clientMap.get(b.client_id)?.name || '—'})</option>
            ))}
          </select>
        </div>
      </Card>

      <div className="grid grid-cols-2 md:grid-cols-2 lg:grid-cols-4 gap-3 md:gap-4">
        <KpiCard title="Campanas activas" value={summary?.active_campaigns ?? '—'} icon={<Megaphone className="w-4 h-4" />} hint={`${summary?.total_campaigns ?? 0} totales`} to="/campaigns" />
        <KpiCard title="Clientes" value={summary?.total_clients ?? '—'} icon={<Building2 className="w-4 h-4" />} to="/clients" />
        <KpiCard title="Marcas" value={summary?.total_brands ?? '—'} icon={<Tags className="w-4 h-4" />} to="/brands" />
        <KpiCard title="Influencers" value={formatNumber(summary?.total_influencers)} icon={<Users className="w-4 h-4" />} to="/influencers" />
        <KpiCard title="Presupuesto total" value={formatCurrency(summary?.total_budget_usd ? Number(summary.total_budget_usd) : 0)} icon={<DollarSign className="w-4 h-4" />} to="/campaigns" />
        <KpiCard title="Reach total" value={formatNumber(summary?.total_reach)} icon={<Eye className="w-4 h-4" />} to="/campaigns" />
        <KpiCard title="ER promedio" value={summary?.avg_engagement_rate ? formatPercent(Number(summary.avg_engagement_rate)) : '—'} icon={<TrendingUp className="w-4 h-4" />} to="/campaigns" />
        <KpiCard title="Campanas terminadas" value={summary?.completed_campaigns ?? '—'} icon={<Megaphone className="w-4 h-4" />} to="/campaigns" />
        <KpiCard
          title="Sentimiento global"
          value={summary?.sentimiento_promedio != null ? (
            Number(summary.sentimiento_promedio) >= 0
              ? `+${(Number(summary.sentimiento_promedio) * 100).toFixed(0)}%`
              : `${(Number(summary.sentimiento_promedio) * 100).toFixed(0)}%`
          ) : '—'}
          icon={<MessageCircle className="w-4 h-4" />}
          hint={`${summary?.campanas_analizadas ?? 0} campanas analizadas`}
          to="/campaigns"
        />
        <KpiCard title="Pub. analizadas" value={summary?.publicaciones_analizadas ?? '—'} icon={<BarChart2 className="w-4 h-4" />} hint="con sentimiento" to="/campaigns" />
        <KpiCard title="Camp. analizadas" value={summary?.campanas_analizadas ?? '—'} icon={<CheckCircle className="w-4 h-4" />} hint="con sentimiento" to="/campaigns" />
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-4 md:gap-6">
        <Card>
          <CardHeader>
            <CardTitle>Campanas por Status</CardTitle>
          </CardHeader>
          <CardContent>
            <ResponsiveContainer width="100%" height={300} className="md:!h-[380px]">
              <BarChart data={byStatus || []} barCategoryGap="20%" barGap={4}>
                <XAxis
                  dataKey="status"
                  tick={renderStatusTick}
                  angle={-15}
                  textAnchor="end"
                  height={72}
                />
                <YAxis tick={{ fontSize: 12 }} />
                <Tooltip
                  cursor={{ fill: 'transparent' }}
                  contentStyle={{ borderRadius: 8, border: '1px solid hsl(var(--border))', fontSize: 12 }}
                />
                <Bar
                  dataKey="count"
                  fill="#8b5cf6"
                  radius={[6, 6, 0, 0]}
                  maxBarSize={60}
                  onClick={handleBarClick}
                  activeBar={renderActiveBar}
                  style={{ cursor: 'pointer' }}
                />
              </BarChart>
            </ResponsiveContainer>
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle>Top Clientes</CardTitle>
          </CardHeader>
          <CardContent>
            <ResponsiveContainer width="100%" height={300} className="md:!h-[380px]">
              <PieChart>
                <Pie
                  data={topClients || []}
                  dataKey="campaign_count"
                  nameKey="name"
                  cx="50%"
                  cy="50%"
                  outerRadius="78%"
                  innerRadius="30%"
                  paddingAngle={3}
                  minAngle={4}
                  labelLine={false}
                  label={renderPieLabel}
                  activeShape={renderActiveShape}
                  onClick={handlePieClick}
                  style={{ cursor: 'pointer' }}
                >
                  {(topClients || []).map((_: any, i: number) => (
                    <Cell key={i} fill={COLORS[i % COLORS.length]} stroke="none" />
                  ))}
                </Pie>
                <Tooltip
                  cursor={{ fill: 'transparent' }}
                  contentStyle={{ borderRadius: 8, border: '1px solid hsl(var(--border))', fontSize: 12 }}
                />
              </PieChart>
            </ResponsiveContainer>
          </CardContent>
        </Card>
      </div>
    </div>
  );
}
