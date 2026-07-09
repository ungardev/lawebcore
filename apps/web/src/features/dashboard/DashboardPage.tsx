import { useQuery } from '@tanstack/react-query';
import { Megaphone, Building2, Tags, Users, DollarSign, Eye, TrendingUp } from 'lucide-react';
import { dashboardApi } from '@/lib/api';
import { KpiCard } from '@/components/data-table/KpiCard';
import { Card, CardHeader, CardTitle, CardContent } from '@/components/ui/card';
import { formatCurrency, formatNumber, formatPercent } from '@/lib/utils';
import { BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer, PieChart, Pie, Cell } from 'recharts';

const COLORS = ['#8b5cf6', '#ec4899', '#f59e0b', '#10b981', '#3b82f6', '#ef4444', '#06b6d4'];

export function DashboardPage() {
  const { data: summary } = useQuery({ queryKey: ['dashboard-summary'], queryFn: dashboardApi.summary });
  const { data: byStatus } = useQuery({ queryKey: ['dashboard-by-status'], queryFn: dashboardApi.byStatus });
  const { data: topClients } = useQuery({ queryKey: ['dashboard-top-clients'], queryFn: () => dashboardApi.topClients() });

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-3xl font-bold">Dashboard Ejecutivo</h1>
        <p className="text-muted-foreground">Vision integral de campanas, clientes y KPIs</p>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
        <KpiCard title="Campanas activas" value={summary?.active_campaigns ?? '—'} icon={<Megaphone className="w-4 h-4" />} hint={`${summary?.total_campaigns ?? 0} totales`} />
        <KpiCard title="Clientes" value={summary?.total_clients ?? '—'} icon={<Building2 className="w-4 h-4" />} />
        <KpiCard title="Marcas" value={summary?.total_brands ?? '—'} icon={<Tags className="w-4 h-4" />} />
        <KpiCard title="Influencers" value={formatNumber(summary?.total_influencers)} icon={<Users className="w-4 h-4" />} />
        <KpiCard title="Presupuesto total" value={formatCurrency(summary?.total_budget_usd ? Number(summary.total_budget_usd) : 0)} icon={<DollarSign className="w-4 h-4" />} />
        <KpiCard title="Reach total" value={formatNumber(summary?.total_reach)} icon={<Eye className="w-4 h-4" />} />
        <KpiCard title="ER promedio" value={summary?.avg_engagement_rate ? formatPercent(Number(summary.avg_engagement_rate)) : '—'} icon={<TrendingUp className="w-4 h-4" />} />
        <KpiCard title="Campanas terminadas" value={summary?.completed_campaigns ?? '—'} icon={<Megaphone className="w-4 h-4" />} />
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <Card>
          <CardHeader>
            <CardTitle>Campanas por Status</CardTitle>
          </CardHeader>
          <CardContent>
            <ResponsiveContainer width="100%" height={280}>
              <BarChart data={byStatus || []}>
                <XAxis dataKey="status" tick={{ fontSize: 11 }} angle={-15} textAnchor="end" height={70} />
                <YAxis />
                <Tooltip />
                <Bar dataKey="count" fill="#8b5cf6" radius={[4, 4, 0, 0]} />
              </BarChart>
            </ResponsiveContainer>
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle>Top Clientes</CardTitle>
          </CardHeader>
          <CardContent>
            <ResponsiveContainer width="100%" height={280}>
              <PieChart>
                <Pie data={topClients || []} dataKey="campaign_count" nameKey="name" cx="50%" cy="50%" outerRadius={90} label={(e) => e.name}>
                  {(topClients || []).map((_, i) => (
                    <Cell key={i} fill={COLORS[i % COLORS.length]} />
                  ))}
                </Pie>
                <Tooltip />
              </PieChart>
            </ResponsiveContainer>
          </CardContent>
        </Card>
      </div>
    </div>
  );
}