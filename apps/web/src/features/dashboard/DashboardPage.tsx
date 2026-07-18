import { useQuery } from '@tanstack/react-query';
import { useNavigate } from 'react-router-dom';
import { Sparkles, Megaphone, Building2, Users, DollarSign, Eye, ArrowRight, MessageSquare, ChevronRight } from 'lucide-react';
import { dashboardApi } from '@/lib/api';
import { lensApi } from '@/features/lens/api/lensApi';
import { Card } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { formatCurrency, formatNumber } from '@/lib/utils';
import type { DiscoveryConversation } from '@/features/lens/types/discovery';

function KpiCard({ title, value, icon, subtitle }: { title: string; value: string | number; icon: React.ReactNode; subtitle?: string }) {
  return (
    <Card className="p-4 flex items-center gap-4">
      <div className="w-10 h-10 rounded-xl bg-primary/10 flex items-center justify-center text-primary flex-shrink-0">
        {icon}
      </div>
      <div>
        <p className="text-2xl font-bold">{value}</p>
        <p className="text-xs text-muted-foreground">{title}</p>
        {subtitle && <p className="text-[10px] text-muted-foreground/70">{subtitle}</p>}
      </div>
    </Card>
  );
}

function CTACard({ title, description, icon, to, accent }: { title: string; description: string; icon: React.ReactNode; to: string; accent: string }) {
  const navigate = useNavigate();
  return (
    <button
      onClick={() => navigate(to)}
      className="text-left w-full p-5 rounded-2xl border bg-card hover:bg-muted/60 transition-all group"
    >
      <div className={`w-10 h-10 rounded-xl ${accent} flex items-center justify-center text-white mb-3`}>
        {icon}
      </div>
      <p className="font-semibold text-foreground mb-1">{title}</p>
      <p className="text-xs text-muted-foreground leading-relaxed">{description}</p>
      <div className="mt-3 flex items-center gap-1 text-xs text-primary font-medium opacity-0 group-hover:opacity-100 transition-opacity">
        Ir <ArrowRight className="w-3 h-3" />
      </div>
    </button>
  );
}

export function DashboardPage() {
  const navigate = useNavigate();
  const { data: summary, isLoading } = useQuery({
    queryKey: ['dashboard-summary'],
    queryFn: () => dashboardApi.summary({}),
  });

  const { data: recentConversations } = useQuery<DiscoveryConversation[]>({
    queryKey: ['lens-conversations-recent'],
    queryFn: () => lensApi.conversations.list({ limit: 5 }),
  });

  return (
    <div className="space-y-6 md:space-y-8">
      <div className="flex flex-col sm:flex-row sm:items-start sm:justify-between gap-3">
        <div>
          <h1 className="text-2xl md:text-3xl font-bold">Bienvenido</h1>
          <p className="text-sm md:text-base text-muted-foreground">La Web Core — AI Marketing OS de La Web Figital Agency</p>
        </div>
        <div className="flex items-center gap-2 bg-emerald-500/10 text-emerald-600 px-3 py-1.5 rounded-full text-xs font-medium">
          <span className="w-2 h-2 rounded-full bg-emerald-500 animate-pulse" />
          Sistema activo
        </div>
      </div>

      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-3 md:gap-4">
        <CTACard
          title="Abrir Influencer Lens"
          description="Busca, descubre y evalua influencers con inteligencia artificial para tus campañas."
          icon={<Sparkles className="w-5 h-5" />}
          to="/influencer-lens"
          accent="bg-gradient-to-br from-blue-600 to-blue-800"
        />
        <CTACard
          title="Gestionar Campanas"
          description="Crea y administra tus campañas de influencer marketing. Ve el pipeline de ejecucion."
          icon={<Megaphone className="w-5 h-5" />}
          to="/campaigns"
          accent="bg-gradient-to-br from-pink-500 to-rose-600"
        />
        <CTACard
          title="Administrar Clientes"
          description="Consulta y gestiona tus clientes, marcas y contactos comerciales."
          icon={<Building2 className="w-5 h-5" />}
          to="/clients"
          accent="bg-gradient-to-br from-amber-500 to-orange-600"
        />
      </div>

      <div>
        <h2 className="text-lg font-semibold mb-3">Resumen ejecutivo</h2>
        <div className="grid grid-cols-2 lg:grid-cols-4 gap-3 md:gap-4">
          <KpiCard
            title="Campanas activas"
            value={isLoading ? '—' : (summary?.active_campaigns ?? '—')}
            icon={<Megaphone className="w-5 h-5" />}
            subtitle={`${summary?.total_campaigns ?? 0} totales`}
          />
          <KpiCard
            title="Influencers"
            value={isLoading ? '—' : formatNumber(summary?.total_influencers)}
            icon={<Users className="w-5 h-5" />}
          />
          <KpiCard
            title="Reach total"
            value={isLoading ? '—' : formatNumber(summary?.total_reach)}
            icon={<Eye className="w-5 h-5" />}
          />
          <KpiCard
            title="Budget total"
            value={isLoading ? '—' : formatCurrency(summary?.total_budget_usd ? Number(summary.total_budget_usd) : 0)}
            icon={<DollarSign className="w-5 h-5" />}
          />
        </div>
      </div>

      {recentConversations && recentConversations.length > 0 && (
        <div>
          <div className="flex items-center justify-between mb-3">
            <h2 className="text-lg font-semibold">Conversaciones recientes del Lens</h2>
            <Button variant="ghost" size="sm" onClick={() => navigate('/influencer-lens')} className="text-xs gap-1">
              Ver todas <ChevronRight className="w-3 h-3" />
            </Button>
          </div>
          <Card className="divide-y">
            {recentConversations.map((conv) => (
              <button
                key={conv.id}
                onClick={() => navigate(`/influencer-lens/${conv.id}`)}
                className="w-full text-left px-4 py-3 hover:bg-muted/50 transition-colors flex items-center gap-3"
              >
                <MessageSquare className="w-4 h-4 text-primary flex-shrink-0" />
                <div className="flex-1 min-w-0">
                  <p className="text-sm font-medium truncate">
                    {conv.accumulated_brief?.slice(0, 60) || 'Nueva busqueda'}
                  </p>
                  <p className="text-xs text-muted-foreground">
                    {new Date(conv.last_message_at).toLocaleDateString('es-ES', { day: 'numeric', month: 'short', hour: '2-digit', minute: '2-digit' })}
                  </p>
                </div>
                <ChevronRight className="w-4 h-4 text-muted-foreground flex-shrink-0" />
              </button>
            ))}
          </Card>
        </div>
      )}
    </div>
  );
}
