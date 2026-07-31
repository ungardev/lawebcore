import type { ReactNode } from 'react';
import { useQuery } from '@tanstack/react-query';
import { useNavigate } from 'react-router-dom';
import {
  ArrowUpRight,
  Building2,
  ChevronRight,
  CircleAlert,
  DollarSign,
  Eye,
  History,
  Megaphone,
  MessageSquare,
  Search,
  Sparkles,
  TrendingUp,
  Users,
} from 'lucide-react';
import { Button } from '@/components/ui/button';
import { dashboardApi } from '@/lib/api';
import { lensApi } from '@/features/lens/api/lensApi';
import { formatCurrency, formatNumber } from '@/lib/utils';
import type { DiscoveryConversation } from '@/features/lens/types/discovery';

const PIPELINE_STAGES = ['BRIEF', 'CONTACTANDO', 'PLAN DE CUENTAS', 'PULL', 'CAMPAÑA INTERNA', 'REPORTE'] as const;
const STATUS_DB_MAP: Record<string, string> = {
  'PLAN DE CUENTAS': 'PLAN_DE_CUENTAS',
  BRIEF: 'BRIEF',
  CONTACTANDO: 'CONTACTANDO',
  PULL: 'PULL',
  'CAMPAÑA INTERNA': 'CAMPAÑA INTERNA',
  REPORTE: 'REPORTE',
};

export function DashboardPage() {
  const navigate = useNavigate();
  const { data: summary, isLoading: isSummaryLoading, isError: isSummaryError } = useQuery({
    queryKey: ['dashboard-summary'],
    queryFn: () => dashboardApi.summary({}),
    retry: 1,
  });
  const { data: recentConversations } = useQuery<DiscoveryConversation[]>({
    queryKey: ['lens-conversations-recent'],
    queryFn: () => lensApi.conversations.list({ limit: 5 }),
    retry: 1,
  });
  const { data: statusCounts } = useQuery({
    queryKey: ['dashboard-by-status'],
    queryFn: () => dashboardApi.byStatus(),
    retry: 1,
  });

  const activeCount = summary?.active_campaigns ?? 0;
  const totalCampaigns = summary?.total_campaigns ?? 0;
  const totalInfluencers = summary?.total_influencers ?? 0;
  const totalReach = Number(summary?.total_reach ?? 0);
  const totalBudget = Number(summary?.total_budget_usd ?? 0);
  const totalClients = summary?.total_clients ?? 0;
  const conversations = Array.isArray(recentConversations) ? recentConversations : [];
  const getStatusCount = (label: string) => {
    const dbStatus = STATUS_DB_MAP[label] ?? label;
    return statusCounts?.find((status: { status: string; count: number }) => status.status === dbStatus)?.count ?? 0;
  };
  const maxStageCount = Math.max(...PIPELINE_STAGES.map(getStatusCount), 1);

  return (
    <div className="space-y-7">
      <section className="flex flex-col gap-5 border-b border-divider pb-6 lg:flex-row lg:items-end lg:justify-between">
        <div className="min-w-0">
          <div className="mb-3 flex flex-wrap items-center gap-2 text-xs text-muted-foreground">
            <span className={`inline-flex items-center gap-2 rounded-full border px-2.5 py-1 ${isSummaryError ? 'border-warning/30 bg-warning/10 text-warning' : 'border-success/30 bg-success/10 text-success'}`}>
              <span className={`h-1.5 w-1.5 rounded-full ${isSummaryError ? 'bg-warning' : 'bg-success'}`} aria-hidden="true" />
              {isSummaryError ? 'Revisión de conexión requerida' : 'Operación sincronizada'}
            </span>
            <span>·</span>
            <span>P.I.A.R. / Resumen ejecutivo</span>
          </div>
          <h1 className="max-w-3xl text-3xl font-semibold tracking-tight text-foreground md:text-4xl">
            Control operativo de campañas e inteligencia de creadores.
          </h1>
          <p className="mt-3 max-w-2xl text-sm leading-6 text-muted-foreground">
            Una lectura rápida de la operación actual, el pipeline y las últimas búsquedas del Lens.
          </p>
        </div>
        <div className="flex shrink-0 flex-wrap gap-2">
          <Button variant="outline" onClick={() => navigate('/campaigns')} className="gap-2">
            <Megaphone className="h-4 w-4" aria-hidden="true" />
            Nueva campaña
          </Button>
          <Button onClick={() => navigate('/lens')} className="gap-2">
            <Search className="h-4 w-4" aria-hidden="true" />
            Buscar creadores
          </Button>
        </div>
      </section>

      <section aria-labelledby="metrics-title">
        <div className="mb-3 flex items-center justify-between">
          <div>
            <p className="text-eyebrow text-muted-foreground">Lectura de negocio</p>
            <h2 id="metrics-title" className="mt-1 text-sm font-semibold text-foreground">Indicadores operativos</h2>
          </div>
          <span className="text-xs text-muted-foreground">Actualizado hace instantes</span>
        </div>
        <div className="grid overflow-hidden rounded-lg border border-divider bg-panel sm:grid-cols-2 xl:grid-cols-4">
          <Metric icon={<Megaphone className="h-4 w-4" />} label="Campañas activas" value={isSummaryLoading ? '—' : String(activeCount)} detail={`${totalCampaigns} totales`} accent="blue" />
          <Metric icon={<Users className="h-4 w-4" />} label="Influencers" value={isSummaryLoading ? '—' : formatNumber(totalInfluencers)} detail="en cartera" accent="purple" />
          <Metric icon={<Eye className="h-4 w-4" />} label="Reach total" value={isSummaryLoading ? '—' : formatNumber(totalReach)} detail="últimos 30 días" accent="pink" />
          <Metric icon={<DollarSign className="h-4 w-4" />} label="Budget total" value={isSummaryLoading ? '—' : formatCurrency(totalBudget)} detail="en ejecución" accent="green" />
        </div>
      </section>

      <section className="grid gap-5 xl:grid-cols-[minmax(0,1.45fr)_minmax(18rem,0.75fr)]">
        <div className="overflow-hidden rounded-lg border border-divider bg-panel">
          <SectionHeader
            eyebrow="Actividad reciente"
            title="Conversaciones del Lens"
            actionLabel="Ver historial"
            onAction={() => navigate('/lens/runs')}
          />
          {conversations.length > 0 ? (
            <div className="divide-y divide-divider">
              {conversations.map((conversation) => (
                <button
                  key={conversation.id}
                  type="button"
                  onClick={() => navigate(`/lens/${conversation.id}`)}
                  className="group flex w-full items-center gap-3 px-5 py-4 text-left transition-colors hover:bg-surface-raised focus-ring"
                >
                  <span className="flex h-9 w-9 shrink-0 items-center justify-center rounded-md border border-primary/20 bg-primary/10 text-primary">
                    <MessageSquare className="h-4 w-4" aria-hidden="true" />
                  </span>
                  <span className="min-w-0 flex-1">
                    <span className="block truncate text-sm font-medium text-foreground">{conversation.title || conversation.accumulated_brief?.slice(0, 80) || 'Nueva búsqueda'}</span>
                    <span className="mt-1 block text-xs text-muted-foreground">{formatConversationDate(conversation.last_message_at)} · {conversation.message_count} mensajes</span>
                  </span>
                  <ChevronRight className="h-4 w-4 shrink-0 text-muted-foreground transition-transform group-hover:translate-x-0.5" aria-hidden="true" />
                </button>
              ))}
            </div>
          ) : (
            <EmptyPanel icon={<History className="h-5 w-5" />} title="Todavía no hay búsquedas" description="Inicia una búsqueda para comenzar a construir tu historial operativo."             actionLabel="Abrir Lens" onAction={() => navigate('/lens')} />
          )}
        </div>

        <div className="rounded-lg border border-divider bg-panel">
          <SectionHeader eyebrow="Capacidad operativa" title="Pipeline en vivo" actionLabel="Abrir pipeline" onAction={() => navigate('/campaigns/kanban')} />
          <div className="space-y-4 px-5 pb-5 pt-2">
            {PIPELINE_STAGES.map((stage) => {
              const count = getStatusCount(stage);
              const width = Math.max(4, Math.round((count / maxStageCount) * 100));
              return (
                <div key={stage}>
                  <div className="mb-1.5 flex items-center justify-between gap-3 text-xs">
                    <span className="truncate text-muted-foreground">{stage}</span>
                    <span className="font-mono font-semibold tabular-nums text-foreground">{count}</span>
                  </div>
                  <div className="h-1.5 overflow-hidden rounded-full bg-surface-raised">
                    <div className="h-full rounded-full bg-primary/75 transition-[width] duration-500" style={{ width: `${width}%` }} />
                  </div>
                </div>
              );
            })}
          </div>
        </div>
      </section>

      <section className="grid gap-5 lg:grid-cols-[minmax(0,1fr)_minmax(18rem,0.5fr)]">
        <div className="rounded-lg border border-divider bg-panel">
          <SectionHeader eyebrow="Atajos operativos" title="Siguiente acción" />
          <div className="grid divide-y divide-divider sm:grid-cols-3 sm:divide-x sm:divide-y-0">
            <ActionRow icon={<Sparkles className="h-4 w-4" />} title="Descubrir creadores" description="Busca por nicho, audiencia y territorio." onClick={() => navigate('/lens')} />
            <ActionRow icon={<Megaphone className="h-4 w-4" />} title="Revisar campañas" description="Comprueba el estado de la ejecución." onClick={() => navigate('/campaigns')} />
            <ActionRow icon={<Building2 className="h-4 w-4" />} title="Ver clientes" description="Accede a marcas y contactos activos." onClick={() => navigate('/clients')} />
          </div>
        </div>

        <div className="rounded-lg border border-divider bg-panel p-5">
          <div className="flex items-start gap-3">
            <div className="flex h-9 w-9 shrink-0 items-center justify-center rounded-md bg-success/10 text-success">
              <TrendingUp className="h-4 w-4" aria-hidden="true" />
            </div>
            <div className="min-w-0">
              <p className="text-eyebrow text-muted-foreground">Cobertura</p>
              <p className="mt-2 text-2xl font-semibold tracking-tight text-metric text-foreground">{totalClients}</p>
              <p className="mt-1 text-xs leading-5 text-muted-foreground">clientes corporativos con operación registrada en el hub.</p>
            </div>
          </div>
          {isSummaryError && (
            <div className="mt-4 flex items-start gap-2 border-t border-divider pt-4 text-xs text-warning">
              <CircleAlert className="mt-0.5 h-3.5 w-3.5 shrink-0" aria-hidden="true" />
              <span>No se pudieron actualizar todas las métricas. Revisa la conexión de datos.</span>
            </div>
          )}
        </div>
      </section>

      <p className="pb-3 text-center text-[11px] text-muted-foreground/70">La Web Figital Agency · P.I.A.R. · {new Date().getFullYear()}</p>
    </div>
  );
}

function Metric({ icon, label, value, detail, accent }: { icon: ReactNode; label: string; value: string; detail: string; accent: 'blue' | 'purple' | 'pink' | 'green' }) {
  const accentClass = {
    blue: 'bg-primary/10 text-primary',
    purple: 'bg-brand-purple/10 text-brand-purple',
    pink: 'bg-brand-pink/10 text-brand-pink',
    green: 'bg-success/10 text-success',
  }[accent];

  return (
    <div className="border-b border-divider p-5 last:border-b-0 sm:nth-[n+3]:border-b-0 xl:border-b-0 xl:border-r xl:last:border-r-0">
      <div className="flex items-center justify-between gap-3">
        <span className={`flex h-8 w-8 items-center justify-center rounded-md ${accentClass}`}>{icon}</span>
        <span className="text-[10px] font-medium uppercase tracking-wide text-muted-foreground">P.I.A.R.</span>
      </div>
      <p className="mt-5 text-3xl font-semibold text-metric text-foreground">{value}</p>
      <p className="mt-1 text-sm font-medium text-foreground">{label}</p>
      <p className="mt-0.5 text-xs text-muted-foreground">{detail}</p>
    </div>
  );
}

function SectionHeader({ eyebrow, title, actionLabel, onAction }: { eyebrow: string; title: string; actionLabel?: string; onAction?: () => void }) {
  return (
    <div className="flex items-end justify-between gap-4 border-b border-divider px-5 py-4">
      <div>
        <p className="text-eyebrow text-muted-foreground">{eyebrow}</p>
        <h2 className="mt-1 text-sm font-semibold text-foreground">{title}</h2>
      </div>
      {actionLabel && onAction && (
        <Button variant="ghost" size="sm" onClick={onAction} className="h-8 shrink-0 gap-1 px-2 text-xs text-muted-foreground hover:text-foreground">
          {actionLabel}
          <ArrowUpRight className="h-3.5 w-3.5" aria-hidden="true" />
        </Button>
      )}
    </div>
  );
}

function ActionRow({ icon, title, description, onClick }: { icon: ReactNode; title: string; description: string; onClick: () => void }) {
  return (
    <button type="button" onClick={onClick} className="group flex items-start gap-3 px-5 py-5 text-left transition-colors hover:bg-surface-raised focus-ring">
      <span className="mt-0.5 text-primary">{icon}</span>
      <span className="min-w-0">
        <span className="block text-sm font-medium text-foreground">{title}</span>
        <span className="mt-1 block text-xs leading-5 text-muted-foreground">{description}</span>
      </span>
      <ArrowUpRight className="ml-auto h-4 w-4 shrink-0 text-muted-foreground opacity-0 transition-opacity group-hover:opacity-100" aria-hidden="true" />
    </button>
  );
}

function EmptyPanel({ icon, title, description, actionLabel, onAction }: { icon: ReactNode; title: string; description: string; actionLabel: string; onAction: () => void }) {
  return (
    <div className="flex min-h-52 flex-col items-center justify-center px-6 py-10 text-center">
      <span className="flex h-10 w-10 items-center justify-center rounded-md border border-divider bg-surface-raised text-muted-foreground">{icon}</span>
      <p className="mt-3 text-sm font-medium text-foreground">{title}</p>
      <p className="mt-1 max-w-xs text-xs leading-5 text-muted-foreground">{description}</p>
      <Button variant="link" size="sm" onClick={onAction} className="mt-2 h-8 px-1 text-xs text-primary">{actionLabel}</Button>
    </div>
  );
}

function formatConversationDate(value: string) {
  return new Date(value).toLocaleDateString('es-ES', {
    day: 'numeric',
    month: 'short',
    hour: '2-digit',
    minute: '2-digit',
  });
}
