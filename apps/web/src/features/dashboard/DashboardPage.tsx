import { useQuery } from '@tanstack/react-query';
import { useNavigate } from 'react-router-dom';
import {
  Sparkles,
  Megaphone,
  Building2,
  Users,
  DollarSign,
  Eye,
  ArrowUpRight,
  MessageSquare,
  TrendingUp,
  Zap,
  ChevronRight,
} from 'lucide-react';
import { dashboardApi } from '@/lib/api';
import { lensApi } from '@/features/lens/api/lensApi';
import { formatCurrency, formatNumber } from '@/lib/utils';
import type { DiscoveryConversation } from '@/features/lens/types/discovery';

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

  const { data: statusCounts } = useQuery({
    queryKey: ['dashboard-by-status'],
    queryFn: () => dashboardApi.byStatus(),
  });

  const activeCount = summary?.active_campaigns ?? 0;
  const totalCampaigns = summary?.total_campaigns ?? 0;
  const totalInfluencers = summary?.total_influencers ?? 0;
  const totalReach = Number(summary?.total_reach ?? 0);
  const totalBudget = Number(summary?.total_budget_usd ?? 0);
  const totalClients = summary?.total_clients ?? 0;

  const STATUS_DB_MAP: Record<string, string> = {
    'PLAN DE CUENTAS': 'PLAN_DE_CUENTAS',
    'BRIEF': 'BRIEF',
    'CONTACTANDO': 'CONTACTANDO',
    'PULL': 'PULL',
    'CAMPAÑA INTERNA': 'CAMPAÑA INTERNA',
    'REPORTE': 'REPORTE',
  };

  const getStatusCount = (label: string) => {
    const dbStatus = STATUS_DB_MAP[label] ?? label;
    return statusCounts?.find((s: { status: string; count: number }) => s.status === dbStatus)?.count ?? 0;
  };

  return (
    <div className="mx-auto max-w-[1400px] px-6 py-8">
      <section className="relative overflow-hidden rounded-3xl border border-border/60 bg-card p-8 shadow-soft md:p-10">
        <div className="relative flex flex-col gap-6 md:flex-row md:items-end md:justify-between">
          <div className="max-w-2xl">
            <div className="mb-4 inline-flex items-center gap-2 rounded-full border border-border/60 bg-background/70 px-3 py-1 text-xs text-muted-foreground backdrop-blur">
              <span className="relative flex h-2 w-2">
                <span className="absolute inline-flex h-full w-full animate-ping rounded-full bg-brand-purple opacity-60" />
                <span className="relative inline-flex h-2 w-2 rounded-full bg-gradient-brand" />
              </span>
              Lens AI está listo · sincronizando {activeCount} campañas
            </div>

            <h1 className="font-bold text-5xl leading-[1.02] tracking-tight text-foreground md:text-6xl">
              Tu próxima <span className="text-gradient-brand">campaña</span> empieza aquí.
            </h1>

            <p className="mt-4 text-base text-muted-foreground md:text-lg">
              {isLoading ? (
                <span className="inline-block h-4 w-72 animate-pulse rounded bg-muted" />
              ) : (
                <>
                  <span className="font-semibold text-foreground">{activeCount}</span> campañas activas
                  {totalInfluencers ? (
                    <>
                      {' · '}
                      <span className="font-semibold text-foreground">{formatNumber(totalInfluencers)}</span> influencers en cartera
                    </>
                  ) : null}
                  {totalBudget ? (
                    <>
                      {' · '}
                      <span className="font-semibold text-foreground">{formatCurrency(totalBudget)}</span> en juego
                    </>
                  ) : null}
                </>
              )}
            </p>
          </div>

          <div className="flex flex-wrap gap-2">
            <button
              onClick={() => navigate('/influencer-lens')}
              className="group inline-flex items-center gap-2 rounded-xl bg-gradient-brand px-4 py-2.5 text-sm font-semibold text-white shadow-glow transition-transform hover:-translate-y-0.5"
            >
              <Sparkles className="h-4 w-4" />
              Abrir Influencer Lens
              <ArrowUpRight className="h-3.5 w-3.5 transition-transform group-hover:translate-x-0.5 group-hover:-translate-y-0.5" />
            </button>
            <button
              onClick={() => navigate('/campaigns')}
              className="inline-flex items-center gap-2 rounded-xl border border-border bg-background px-4 py-2.5 text-sm font-semibold text-foreground transition-colors hover:bg-muted"
            >
              Nueva campaña
            </button>
          </div>
        </div>
      </section>

      <section className="mt-6 grid gap-4 md:grid-cols-3">
        <QuickCard
          onClick={() => navigate('/influencer-lens')}
          icon={<Sparkles className="h-5 w-5" />}
          title="Abrir Influencer Lens"
          copy="Busca, descubre y evalúa influencers con inteligencia artificial para tus campañas."
          tone="pink"
        />
        <QuickCard
          onClick={() => navigate('/campaigns')}
          icon={<Megaphone className="h-5 w-5" />}
          title="Gestionar campañas"
          copy="Crea y administra tus campañas de influencer marketing. Ve el pipeline de ejecución."
          tone="purple"
        />
        <QuickCard
          onClick={() => navigate('/clients')}
          icon={<Building2 className="h-5 w-5" />}
          title="Administrar clientes"
          copy="Consulta y gestiona tus clientes, marcas y contactos comerciales."
          tone="blue"
        />
      </section>

      <section className="mt-10">
        <div className="mb-4 flex items-baseline justify-between">
          <h2 className="font-bold text-2xl tracking-tight text-foreground">Resumen ejecutivo</h2>
          <span className="text-xs text-muted-foreground">Actualizado hace instantes</span>
        </div>
        <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-4">
          <Kpi
            icon={<Megaphone className="h-4 w-4" />}
            label="Campañas activas"
            value={String(activeCount)}
            sub={`${totalCampaigns} totales`}
            trend="+1"
          />
          <Kpi
            icon={<Users className="h-4 w-4" />}
            label="Influencers"
            value={formatNumber(totalInfluencers)}
            sub="en cartera"
            trend="+0"
          />
          <Kpi
            icon={<Eye className="h-4 w-4" />}
            label="Reach total"
            value={formatNumber(totalReach)}
            sub="últimos 30 días"
            trend="+0"
          />
          <Kpi
            icon={<DollarSign className="h-4 w-4" />}
            label="Budget total"
            value={formatCurrency(totalBudget)}
            sub="en ejecución"
            trend="+$0"
          />
        </div>
      </section>

      <section className="mt-10 grid gap-6 lg:grid-cols-3">
        <div className="lg:col-span-2">
          <div className="mb-4 flex items-center justify-between">
            <h2 className="font-bold text-2xl tracking-tight text-foreground">
              Conversaciones recientes del Lens
            </h2>
            <button
              onClick={() => navigate('/influencer-lens')}
              className="inline-flex items-center gap-1 text-xs font-medium text-brand-purple hover:text-brand-pink"
            >
              Ver todas <ChevronRight className="h-3.5 w-3.5" />
            </button>
          </div>
          <div className="overflow-hidden rounded-2xl border border-border/60 bg-card shadow-soft">
            {Array.isArray(recentConversations) && recentConversations.length > 0 ? (
              recentConversations.map((conv: DiscoveryConversation, i: number) => (
                <button
                  key={conv.id}
                  onClick={() => navigate(`/influencer-lens/${conv.id}`)}
                  className={`group flex w-full items-center gap-4 px-5 py-4 text-left transition-colors hover:bg-muted/50 ${
                    i !== recentConversations.length - 1 ? 'border-b border-border/60' : ''
                  }`}
                >
                  <div className="flex h-10 w-10 shrink-0 items-center justify-center rounded-xl bg-gradient-brand-soft text-brand-purple">
                    <MessageSquare className="h-4 w-4" />
                  </div>
                  <div className="min-w-0 flex-1">
                    <p className="truncate text-sm font-semibold text-foreground">
                      {conv.accumulated_brief?.slice(0, 80) || 'Nueva búsqueda'}
                    </p>
                    <p className="text-xs text-muted-foreground">
                      {new Date(conv.last_message_at).toLocaleDateString('es-ES', {
                        day: 'numeric',
                        month: 'short',
                        hour: '2-digit',
                        minute: '2-digit',
                      })}
                    </p>
                  </div>
                  <ChevronRight className="h-4 w-4 text-muted-foreground transition-transform group-hover:translate-x-0.5" />
                </button>
              ))
            ) : (
              <div className="flex flex-col items-center justify-center py-12 text-center">
                <MessageSquare className="h-8 w-8 text-muted-foreground/40 mb-3" />
                <p className="text-sm text-muted-foreground">Sin conversaciones aún</p>
                <button
                  onClick={() => navigate('/influencer-lens')}
                  className="mt-3 text-xs font-medium text-brand-purple hover:text-brand-pink"
                >
                  Iniciar primera búsqueda
                </button>
              </div>
            )}
          </div>
        </div>

        <div>
          <div className="mb-4 flex items-center justify-between">
            <h2 className="font-bold text-2xl tracking-tight text-foreground">Top creadores</h2>
            <TrendingUp className="h-4 w-4 text-brand-purple" />
          </div>
          <div className="space-y-3">
            {Array.isArray(recentConversations) && recentConversations.length > 0 ? (
              recentConversations.slice(0, 4).map((conv) => (
                <div
                  key={conv.id}
                  className="flex items-center gap-3 rounded-2xl border border-border/60 bg-card p-3 shadow-soft transition-all hover:-translate-y-0.5 hover:shadow-elevated"
                >
                  <div className="relative">
                    <div className="flex h-11 w-11 items-center justify-center rounded-full bg-gradient-brand text-sm font-bold text-white">
                      {conv.accumulated_brief?.[0]?.toUpperCase() || '?'}
                    </div>
                    <div className="absolute -bottom-0.5 -right-0.5 rounded-full bg-emerald-500 px-1.5 py-0.5 text-[8px] font-bold text-white ring-2 ring-card">
                      85
                    </div>
                  </div>
                  <div className="min-w-0 flex-1">
                    <p className="truncate text-sm font-semibold text-foreground">
                      {conv.accumulated_brief?.slice(0, 30) || 'Nueva búsqueda'}
                    </p>
                    <p className="truncate text-[11px] text-muted-foreground">
                      Lens AI · pendiente
                    </p>
                  </div>
                  <Zap className="h-3.5 w-3.5 text-brand-pink" />
                </div>
              ))
            ) : (
              <div className="flex flex-col items-center justify-center rounded-2xl border border-border/60 bg-card p-6 text-center shadow-soft">
                <Sparkles className="h-6 w-6 text-brand-purple/60 mb-2" />
                <p className="text-xs text-muted-foreground">Sin datos aún</p>
                <p className="mt-1 text-[10px] text-muted-foreground/70">
                  Las búsquedas del Lens aparecerán aquí
                </p>
              </div>
            )}
          </div>
        </div>
      </section>

      <section className="mt-10 mb-8">
        <div className="mb-4 flex items-center justify-between">
          <h2 className="font-bold text-2xl tracking-tight text-foreground">Pipeline en vivo</h2>
          <button
            onClick={() => navigate('/campaigns/kanban')}
            className="inline-flex items-center gap-1 text-xs font-medium text-brand-purple hover:text-brand-pink"
          >
            Ver kanban completo <ChevronRight className="h-3.5 w-3.5" />
          </button>
        </div>
        <div className="grid gap-3 md:grid-cols-3 lg:grid-cols-6">
          {(['BRIEF', 'CONTACTANDO', 'PLAN DE CUENTAS', 'PULL', 'CAMPAÑA INTERNA', 'REPORTE'] as const).map((s) => (
            <div key={s} className="rounded-xl border border-border/60 bg-card p-4 shadow-soft">
              <span className="inline-block rounded-md border border-border/60 bg-muted/50 px-2 py-0.5 text-[10px] font-semibold text-muted-foreground">
                {s}
              </span>
              <p className="mt-3 text-3xl font-bold tracking-tight text-foreground">{getStatusCount(s)}</p>
              <p className="text-[11px] text-muted-foreground">campañas</p>
            </div>
          ))}
        </div>
      </section>

      <p className="mt-12 text-center text-xs text-muted-foreground">
        {totalClients > 0 ? `${totalClients} clientes corporativos · ` : ''}La Web Figital Agency © {new Date().getFullYear()}
      </p>
    </div>
  );
}

function QuickCard({
  onClick,
  icon,
  title,
  copy,
  tone,
}: {
  onClick: () => void;
  icon: React.ReactNode;
  title: string;
  copy: string;
  tone: 'pink' | 'purple' | 'blue';
}) {
  const tones = {
    pink: 'from-brand-pink to-brand-purple',
    purple: 'from-brand-purple to-brand-blue',
    blue: 'from-brand-blue to-brand-purple',
  };
  return (
    <button
      onClick={onClick}
      className="group relative overflow-hidden rounded-2xl border border-border/60 bg-card p-6 text-left shadow-soft transition-all hover:-translate-y-1 hover:shadow-elevated"
    >
      <div
        className={`mb-4 inline-flex h-11 w-11 items-center justify-center rounded-xl bg-gradient-to-br ${tones[tone]} text-white shadow-glow`}
      >
        {icon}
      </div>
      <h3 className="font-bold text-xl tracking-tight text-foreground">{title}</h3>
      <p className="mt-2 text-sm leading-relaxed text-muted-foreground">{copy}</p>
      <div className="mt-4 inline-flex items-center gap-1 text-xs font-medium text-brand-purple opacity-0 transition-opacity group-hover:opacity-100">
        Abrir <ArrowUpRight className="h-3 w-3" />
      </div>
    </button>
  );
}

function Kpi({
  icon,
  label,
  value,
  sub,
  trend,
}: {
  icon: React.ReactNode;
  label: string;
  value: string;
  sub: string;
  trend: string;
}) {
  return (
    <div className="rounded-2xl border border-border/60 bg-card p-5 shadow-soft">
      <div className="flex items-center justify-between">
        <div className="flex h-9 w-9 items-center justify-center rounded-lg bg-gradient-brand-soft text-brand-purple">
          {icon}
        </div>
        <span className="rounded-full bg-emerald-50 px-2 py-0.5 text-[10px] font-semibold text-emerald-700 ring-1 ring-emerald-200">
          {trend}
        </span>
      </div>
      <p className="mt-4 font-bold text-4xl tracking-tight text-foreground">{value}</p>
      <p className="mt-1 text-sm font-medium text-foreground">{label}</p>
      <p className="text-xs text-muted-foreground">{sub}</p>
    </div>
  );
}
