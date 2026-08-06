import type { ReactNode } from 'react';
import { useQuery } from '@tanstack/react-query';
import { useNavigate } from 'react-router-dom';
import {
  ChevronRight,
  CircleAlert,
  History,
  Loader2,
  MessageSquare,
  Search,
} from 'lucide-react';
import { Button } from '@/components/ui/button';
import { lensApi } from '@/features/lens/api/lensApi';
import type { DiscoveryConversation } from '@/features/lens/types/discovery';

export function DashboardPage() {
  const navigate = useNavigate();

  const {
    data: recentConversations,
    isLoading: isConversationsLoading,
    isError: isConversationsError,
  } = useQuery<DiscoveryConversation[]>({
    queryKey: ['lens-conversations-recent'],
    queryFn: () => lensApi.conversations.list({ limit: 5 }),
    retry: 1,
  });

  const conversations = Array.isArray(recentConversations) ? recentConversations : [];

  return (
    <div className="space-y-7">
      <section className="flex flex-col gap-5 border-b border-divider pb-6 lg:flex-row lg:items-end lg:justify-between">
        <div className="min-w-0">
          <div className="mb-3 flex flex-wrap items-center gap-2 text-xs text-muted-foreground">
            <span className={`inline-flex items-center gap-2 rounded-full border px-2.5 py-1 ${isConversationsError ? 'border-warning/30 bg-warning/10 text-warning' : 'border-success/30 bg-success/10 text-success'}`}>
              <span className={`h-1.5 w-1.5 rounded-full ${isConversationsError ? 'bg-warning' : 'bg-success'}`} aria-hidden="true" />
              {isConversationsError ? 'Actividad no disponible' : 'Operación sincronizada'}
            </span>
            <span>·</span>
            <span>P.I.A.R. / Home</span>
          </div>
          <h1 className="max-w-3xl text-3xl font-semibold tracking-tight text-foreground md:text-4xl">
            Descubre Influencers con Lens
          </h1>
          <p className="mt-3 max-w-2xl text-sm leading-6 text-muted-foreground">
            Una lectura rápida de las últimas búsquedas y actividad de descubrimiento.
          </p>
        </div>
        <div className="flex shrink-0 flex-wrap gap-2">
          <Button variant="outline" onClick={() => navigate('/lens/search')} className="gap-2">
            Búsqueda directa
          </Button>
          <Button onClick={() => navigate('/lens')} className="gap-2">
            <Search className="h-4 w-4" aria-hidden="true" />
            Abrir Lens
          </Button>
        </div>
      </section>

      <section aria-labelledby="conversations-title">
        <div className="mb-3 flex items-center justify-between">
          <div>
            <p className="text-eyebrow text-muted-foreground">Actividad reciente</p>
            <h2 id="conversations-title" className="mt-1 text-sm font-semibold text-foreground">Conversaciones del Lens</h2>
          </div>
          <Button variant="ghost" size="sm" onClick={() => navigate('/lens/runs')} className="h-8 gap-1 px-2 text-xs text-muted-foreground hover:text-foreground">
            Ver historial <ChevronRight className="h-3.5 w-3.5" aria-hidden="true" />
          </Button>
        </div>
        <div className="overflow-hidden rounded-lg border border-divider bg-panel">
          {isConversationsLoading ? (
            <div className="flex min-h-52 items-center justify-center gap-2 text-xs text-muted-foreground"><Loader2 className="h-4 w-4 animate-spin text-primary" aria-hidden="true" />Cargando actividad…</div>
          ) : isConversationsError ? (
            <div className="flex min-h-52 flex-col items-center justify-center px-6 py-10 text-center"><CircleAlert className="h-5 w-5 text-warning" aria-hidden="true" /><p className="mt-3 text-sm font-medium text-foreground">No se pudo cargar la actividad</p><p className="mt-1 max-w-xs text-xs leading-5 text-muted-foreground">Puedes abrir Lens y continuar con una nueva búsqueda.</p><Button size="sm" variant="link" onClick={() => navigate('/lens')} className="mt-2 text-xs text-primary">Abrir Lens</Button></div>
          ) : conversations.length > 0 ? (
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
            <EmptyPanel
              icon={<History className="h-5 w-5" />}
              title="Todavía no hay búsquedas"
              description="Inicia una búsqueda para comenzar a construir tu historial operativo."
              actionLabel="Abrir Lens"
              onAction={() => navigate('/lens')}
            />
          )}
        </div>
      </section>

      <p className="pb-3 text-center text-[11px] text-muted-foreground/70">La Web Figital Agency · P.I.A.R. · {new Date().getFullYear()}</p>
    </div>
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
