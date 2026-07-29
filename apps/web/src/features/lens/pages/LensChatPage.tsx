import { useEffect, useRef, useState } from 'react';
import { useNavigate, useParams } from 'react-router-dom';
import { DollarSign, MessageSquare, Send, Sparkles, TrendingUp, Wand2 } from 'lucide-react';
import { Dialog, DialogContent } from '@/components/ui/dialog';
import { Button } from '@/components/ui/button';
import { Textarea } from '@/components/ui/textarea';
import { cn } from '@/lib/utils';
import { toast } from 'sonner';
import { lensApi } from '../api/lensApi';
import { useDiscoveryConversation } from '../hooks/useDiscoveryConversation';
import { ActionChips } from '../components/ActionChips';
import { BriefConfirmCard } from '../components/BriefConfirmCard';
import { BriefWizard } from '../components/BriefWizard';
import { ChatMessage } from '../components/ChatMessage';
import { LensEmptyState } from '../components/LensEmptyState';
import type { BriefStructured, DiscoveryConversation } from '../types/discovery';

const WELCOME = `Puedo ayudarte a descubrir creadores, revisar campañas y preparar una búsqueda con datos reales de la agencia.

Describe el producto, la audiencia y el territorio que quieres analizar. Cuando falten datos, te pediré lo necesario antes de ejecutar el discovery.`;

export function LensChatPage() {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const [input, setInput] = useState('');
  const [conversations, setConversations] = useState<DiscoveryConversation[]>([]);
  const [totalCost, setTotalCost] = useState(0);
  const [showWizard, setShowWizard] = useState(false);
  const [wizardBrief, setWizardBrief] = useState<Partial<BriefStructured> | undefined>();
  const [wizardLoading, setWizardLoading] = useState(false);
  const bottomRef = useRef<HTMLDivElement>(null);

  const {
    conversation,
    turns,
    isLoading,
    error,
    pendingBrief,
    startConversation,
    loadConversation,
    sendMessage,
    confirmBrief,
    saveCandidate,
    dismissCandidate,
  } = useDiscoveryConversation();

  useEffect(() => {
    lensApi.conversations.list({ limit: 20 }).then((data) => setConversations(Array.isArray(data) ? data : [])).catch(() => setConversations([]));
  }, []);

  useEffect(() => {
    if (id) {
      loadConversation(id).catch(() => navigate('/influencer-lens'));
    } else if (conversations.length > 0) {
      navigate(`/influencer-lens/${conversations[0].id}`, { replace: true });
    }
  }, [conversations, id, loadConversation, navigate]);

  useEffect(() => {
    setTotalCost(turns.reduce((sum, turn) => sum + (turn.cost_usd ?? 0), 0));
  }, [turns]);

  const handleSend = async (text?: string) => {
    const message = (text ?? input).trim();
    if (!message || isLoading) return;
    if (!conversation) {
      const newConversation = await startConversation(message);
      navigate(`/influencer-lens/${newConversation.id}`);
      setInput('');
      return;
    }
    if (!text) setInput('');
    await sendMessage(message);
  };

  const handleNewConversation = async () => {
    const newConversation = await startConversation();
    setConversations((previous) => [newConversation, ...previous]);
    navigate(`/influencer-lens/${newConversation.id}`);
  };

  const handleWizardSubmit = async (brief: Partial<BriefStructured>) => {
    setWizardLoading(true);
    try {
      const run = await lensApi.search.createRun({
        product_name: brief.product_name ?? undefined,
        industry: brief.industry ?? undefined,
        niches: brief.niches ?? [],
        audience_gender: brief.audience_gender ?? 'all',
        audience_age_min: brief.audience_age_min ?? 25,
        audience_age_max: brief.audience_age_max ?? 45,
        audience_countries: brief.audience_countries ?? ['VE'],
        audience_cities: brief.audience_cities ?? [],
        platforms: brief.platforms ?? ['instagram'],
        tone: brief.tone ?? [],
        hashtags: brief.hashtags ?? [],
      });
      toast.success('Búsqueda iniciada');
      setShowWizard(false);
      navigate(`/influencer-lens/search?runId=${run.id}`);
    } catch {
      toast.error('No se pudo iniciar la búsqueda. Revisa los datos e intenta de nuevo.');
    } finally {
      setWizardLoading(false);
    }
  };

  return (
    <div className="flex h-full min-h-0 flex-col overflow-hidden">
      <header className="flex shrink-0 flex-col gap-4 border-b border-divider pb-4 md:flex-row md:items-end md:justify-between">
        <div>
          <div className="flex items-center gap-3">
            <span className="flex h-9 w-9 items-center justify-center rounded-md border border-primary/25 bg-primary/10 text-primary"><Sparkles className="h-4 w-4" aria-hidden="true" /></span>
            <div>
              <p className="text-eyebrow text-muted-foreground">Inteligencia / discovery</p>
              <h1 className="mt-1 text-2xl font-semibold tracking-tight text-foreground">Influencer Lens</h1>
            </div>
          </div>
          <div className="mt-3 flex flex-wrap items-center gap-2 text-xs text-muted-foreground">
            <span className="inline-flex items-center gap-1.5 text-success"><span className="h-1.5 w-1.5 rounded-full bg-success" aria-hidden="true" />Servicio online</span>
            <span>·</span>
            <span>Datos propios + Apify</span>
            {totalCost > 0 && <span className="inline-flex items-center gap-1 rounded border border-divider bg-surface-sunken px-2 py-1 font-mono text-[10px]"><DollarSign className="h-3 w-3" aria-hidden="true" />${totalCost.toFixed(4)} sesión</span>}
          </div>
        </div>
        <Button onClick={() => { setWizardBrief(undefined); setShowWizard(true); }} className="w-full gap-2 md:w-auto">
          <Wand2 className="h-4 w-4" aria-hidden="true" />
          Nueva búsqueda
        </Button>
      </header>

      <div className="flex min-h-0 flex-1 gap-4 overflow-hidden lg:grid-cols-[15rem_minmax(0,1fr)] xl:grid-cols-[17rem_minmax(0,1fr)]">
        <aside className="flex min-h-0 flex-col overflow-hidden rounded-lg border border-divider bg-panel" aria-label="Conversaciones del Lens">
          <div className="flex items-center justify-between border-b border-divider px-4 py-3">
            <div><p className="text-eyebrow text-muted-foreground">Sesiones</p><p className="mt-1 text-xs font-medium text-foreground">Conversaciones</p></div>
            <span className="font-mono text-[10px] text-muted-foreground">{conversations.length}</span>
          </div>
          <div className="min-h-0 flex-1 space-y-1 overflow-y-auto p-2">
            {conversations.length === 0 ? <p className="px-3 py-5 text-center text-xs text-muted-foreground">Sin conversaciones guardadas.</p> : conversations.map((item) => (
              <button key={item.id} type="button" onClick={() => navigate(`/influencer-lens/${item.id}`)} className={cn('w-full rounded-md border px-3 py-3 text-left transition-colors focus-ring', item.id === id ? 'border-primary/30 bg-primary/10' : 'border-transparent hover:border-divider hover:bg-surface-raised')}>
                <span className="block truncate text-xs font-medium text-foreground">{item.accumulated_brief?.slice(0, 42) || 'Nueva búsqueda'}</span>
                <span className="mt-1 block text-[10px] text-muted-foreground">{formatDate(item.last_message_at)} · {item.message_count} mensajes</span>
              </button>
            ))}
          </div>
          <div className="border-t border-divider p-2">
            <Button variant="ghost" size="sm" onClick={handleNewConversation} className="w-full justify-start gap-2 text-xs text-muted-foreground"><MessageSquare className="h-3.5 w-3.5" aria-hidden="true" />Abrir conversación vacía</Button>
          </div>
        </aside>

        <section className="flex h-full min-h-0 min-w-0 flex-col overflow-hidden rounded-lg border border-divider bg-panel" aria-label="Conversación con Influencer Lens">
          {!conversation && !isLoading ? (
            <div className="flex flex-1 flex-col items-center justify-center px-6 py-10 text-center">
              <LensEmptyState variant="no_conversations" />
              <Button onClick={handleNewConversation} className="mt-1 gap-2"><MessageSquare className="h-4 w-4" aria-hidden="true" />Iniciar búsqueda asistida</Button>
            </div>
          ) : (
            <>
              <div className="flex items-center justify-between border-b border-divider bg-surface-sunken px-5 py-3">
                <div className="flex items-center gap-2 text-xs"><span className="h-1.5 w-1.5 rounded-full bg-success" aria-hidden="true" /><span className="font-medium text-foreground">Lens operativo</span></div>
                <span className="font-mono text-[10px] text-muted-foreground">CHAT / DISCOVERY</span>
              </div>
              <div className="min-h-0 flex-1 space-y-4 overflow-y-auto overscroll-contain p-4 md:p-6">
                {turns.length === 0 && <div className="max-w-2xl border-l-2 border-primary/40 pl-4 text-sm leading-6 text-muted-foreground whitespace-pre-wrap">{WELCOME}</div>}
                {turns.map((turn) => <ChatMessage key={turn.id} turn={turn} onSaveCandidate={saveCandidate} onDismissCandidate={dismissCandidate} />)}
                {isLoading && <div className="flex items-center gap-2 text-xs text-muted-foreground"><span className="flex gap-1" aria-hidden="true"><span className="h-1.5 w-1.5 animate-pulse rounded-full bg-primary" /><span className="h-1.5 w-1.5 animate-pulse rounded-full bg-primary [animation-delay:150ms]" /><span className="h-1.5 w-1.5 animate-pulse rounded-full bg-primary [animation-delay:300ms]" /></span>Procesando solicitud…</div>}
                {error && <p className="rounded-md border border-destructive/30 bg-destructive/10 px-3 py-2 text-xs text-destructive">{error}</p>}
                <div ref={bottomRef} />
              </div>
              {pendingBrief && <div className="border-t border-divider p-4"><BriefConfirmCard brief={pendingBrief} onConfirm={confirmBrief} onEdit={() => { setWizardBrief(pendingBrief); setShowWizard(true); }} isLoading={isLoading} /></div>}
              <div className="border-t border-divider bg-surface-sunken p-4">
                <ActionChips onSend={handleSend} disabled={isLoading} />
                <div className="flex items-end gap-2 rounded-md border border-divider bg-background p-2 transition-colors focus-within:border-primary/60 focus-within:ring-2 focus-within:ring-primary/10">
                  <Textarea value={input} onChange={(event) => setInput(event.target.value)} onKeyDown={(event) => { if (event.key === 'Enter' && !event.shiftKey) { event.preventDefault(); handleSend(); } }} placeholder="Describe el producto, audiencia o campaña…" rows={2} className="min-h-12 resize-none border-0 bg-transparent px-2 py-1 shadow-none focus-visible:ring-0" disabled={isLoading} aria-label="Mensaje para Influencer Lens" />
                  <Button onClick={() => handleSend()} disabled={isLoading || !input.trim()} size="icon" className="mb-0.5 shrink-0" aria-label="Enviar mensaje"><Send className="h-4 w-4" aria-hidden="true" /></Button>
                </div>
                <p className="mt-2 px-1 text-[10px] text-muted-foreground">Enter para enviar · Shift+Enter para una nueva línea</p>
              </div>
            </>
          )}
        </section>
      </div>

      <Dialog open={showWizard} onOpenChange={setShowWizard}>
        <DialogContent className="max-h-[min(48rem,92dvh)] max-w-3xl overflow-y-auto p-0">
          <BriefWizard onSubmit={handleWizardSubmit} onCancel={() => setShowWizard(false)} initialBrief={wizardBrief} isSubmitting={wizardLoading} />
        </DialogContent>
      </Dialog>
    </div>
  );
}

function formatDate(value: string) {
  return new Date(value).toLocaleDateString('es-ES', { day: '2-digit', month: 'short' });
}
