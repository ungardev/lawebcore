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

  const activeCount = summary?.active_campaigns ?? 0;
  const totalCampaigns = summary?.total_campaigns ?? 0;
  const totalInfluencers = summary?.total_influencers ?? 0;
  const totalReach = Number(summary?.total_reach ?? 0);
  const totalBudget = Number(summary?.total_budget_usd ?? 0);

  return (
    <div className="relative min-h-screen">
      <div className="mx-auto max-w-[1400px] px-6 py-8">
        <section className="relative overflow-hidden rounded-3xl border border-border/60 bg-card p-8 shadow-soft md:p-10">
          <div className="pointer-events-none absolute -right-24 -top-24 h-72 w-72 rounded-full bg-gradient-brand opacity-20 blur-3xl" />
          <div className="pointer-events-none absolute -bottom-24 left-1/3 h-72 w-72 rounded-full bg-brand-blue opacity-15 blur-3xl" />

          <div className="relative flex flex-col gap-6 md:flex-row md:items-end md:justify-between">
            <div className="max-w-2xl">
              <div className="mb-4 inline-flex items-center gap-2 rounded-full border border-border/60 bg-background/70 px-3 py-1 text-xs text-muted-foreground backdrop-blur">
                <span className="relative flex h-2 w-2">
                  <span className="absolute inline-flex h-full w-full animate-ping rounded-full bg-brand-purple opacity-60" />
                  <span className="relative inline-flex h-2 w-2 rounded-full bg-gradient-brand" />
                </span>
                Lens AI está listo · sincronizando {activeCount} campañas
              </div>

              <h1 className="font-display text-5xl leading-[1.02] tracking-tight text-foreground md:text-6xl">
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
            <h2 className="font-display text-2xl tracking-tight text-foreground">Resumen ejecutivo</h2>
            <span className="text-xs text-muted-foreground">Actualizado hace instantes</span>
          </div>
          <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-4">
            <Kpi
              icon={<Megaphone className="h-4 w-4" />}
              label="Campañas activas"
              value={String(activeCount)}
              sub={`${totalCampaigns} totales`}
            />
            <Kpi
              icon={<Users className="h-4 w-4" />}
              label="Influencers"
              value={formatNumber(totalInfluencers)}
              sub="en cartera"
            />
            <Kpi
              icon={<Eye className="h-4 w-4" />}
              label="Reach total"
              value={formatNumber(totalReach)}
              sub="últimos 30 días"
            />
            <Kpi
              icon={<DollarSign className="h-4 w-4" />}
              label="Budget total"
              value={formatCurrency(totalBudget)}
              sub="en ejecución"
            />
          </div>
        </section>

        {Array.isArray(recentConversations) && recentConversations.length > 0 && (
          <section className="mt-10 mb-8 grid gap-6 lg:grid-cols-3">
            <div className="lg:col-span-2">
              <div className="mb-4 flex items-center justify-between">
                <h2 className="font-display text-2xl tracking-tight text-foreground">
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
                {recentConversations.map((conv: DiscoveryConversation, i: number) => (
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
                ))}
              </div>
            </div>

            <aside className="rounded-2xl border border-border/60 bg-card p-6 shadow-soft">
              <div className="mb-3 inline-flex h-9 w-9 items-center justify-center rounded-lg bg-gradient-brand text-white shadow-glow">
                <TrendingUp className="h-4 w-4" />
              </div>
              <h3 className="font-display text-xl tracking-tight text-foreground">Optimiza tu próximo brief</h3>
              <p className="mt-2 text-sm leading-relaxed text-muted-foreground">
                Lens aprende de cada búsqueda. Añade objetivos de marca, KPIs y presupuesto para descubrir creadores con mejor fit.
              </p>
              <button
                onClick={() => navigate('/influencer-lens')}
                className="mt-4 inline-flex items-center gap-1.5 text-xs font-semibold text-brand-purple hover:text-brand-pink"
              >
                <Zap className="h-3.5 w-3.5" />
                Iniciar nueva búsqueda
              </button>
            </aside>
          </section>
        )}

        <p className="mt-12 text-center text-xs text-muted-foreground">
          La Web Figital Agency © {new Date().getFullYear()} · Powered by Lens AI
        </p>
      </div>
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
      <h3 className="font-display text-xl tracking-tight text-foreground">{title}</h3>
      <p className="mt-2 text-sm leading-relaxed text-muted-foreground">{copy}</p>
      <div className="mt-4 inline-flex items-center gap-1 text-xs font-medium text-brand-purple opacity-0 transition-opacity group-hover:opacity-100">
        Abrir <ArrowUpRight className="h-3 w-3" />
      </div>
      <div className="pointer-events-none absolute -bottom-16 -right-16 h-40 w-40 rounded-full bg-gradient-brand opacity-0 blur-3xl transition-opacity group-hover:opacity-30" />
    </button>
  );
}

function Kpi({
  icon,
  label,
  value,
  sub,
}: {
  icon: React.ReactNode;
  label: string;
  value: string;
  sub: string;
}) {
  return (
    <div className="rounded-2xl border border-border/60 bg-card p-5 shadow-soft transition-all hover:-translate-y-0.5 hover:shadow-elevated">
      <div className="flex items-center justify-between">
        <div className="flex h-9 w-9 items-center justify-center rounded-lg bg-gradient-brand-soft text-brand-purple">
          {icon}
        </div>
      </div>
      <p className="mt-4 font-display text-4xl tracking-tight text-foreground">{value}</p>
      <p className="mt-1 text-sm font-medium text-foreground">{label}</p>
      <p className="text-xs text-muted-foreground">{sub}</p>
    </div>
  );
}
