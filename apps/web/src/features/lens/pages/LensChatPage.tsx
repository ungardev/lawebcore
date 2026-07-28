import { useEffect, useRef, useState } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { Send, Sparkles, Plus, MessageSquare, DollarSign, TrendingUp, Wand2 } from 'lucide-react';
import { useDiscoveryConversation } from '../hooks/useDiscoveryConversation';
import { ChatMessage } from '../components/ChatMessage';
import { BriefConfirmCard } from '../components/BriefConfirmCard';
import { LensEmptyState } from '../components/LensEmptyState';
import { ActionChips } from '../components/ActionChips';
import { CostBadge } from '../components/CostBadge';
import { BriefWizard } from '../components/BriefWizard';
import { Dialog, DialogContent } from '@/components/ui/dialog';
import { Card } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { lensApi } from '../api/lensApi';
import { toast } from 'sonner';
import { cn } from '@/lib/utils';
import type { BriefStructured, DiscoveryConversation } from '../types/discovery';

const WELCOME = `Soy Influencer Lens, el cerebro AI de La Web Core — la plataforma de gestión de campañas de La Web Figital Agency.

Somos la agencia AI #1 en Venezuela. Puedo ayudarte a:

• Descubrir influencers ideales para cualquier marca o campaña
• Analizar el rendimiento de tus campañas activas
• Proyectar escenarios de alcance y engagement
• Gestionar tu cartera de creadores

También ejecuto herramientas en tiempo real: busco en la base de datos, consulto APIs de scraping (Apify), rankeo prospectos con scoring de afinidad, y proyecto escenarios de alcance.

Describe lo que necesitas en lenguaje natural y ve cómo trabajo.`;

export function LensChatPage() {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const [input, setInput] = useState('');
  const bottomRef = useRef<HTMLDivElement>(null);
  const [conversations, setConversations] = useState<DiscoveryConversation[]>([]);
  const [totalCost, setTotalCost] = useState(0);
  const [showWizard, setShowWizard] = useState(false);
  const [wizardBrief, setWizardBrief] = useState<Partial<BriefStructured> | undefined>(undefined);
  const [wizardLoading, setWizardLoading] = useState(false);

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
  }, [id]);

  useEffect(() => {
    const cost = turns.reduce((sum, t) => sum + (t.cost_usd ?? 0), 0);
    setTotalCost(cost);
  }, [turns]);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [turns]);

  const handleSend = async (text?: string) => {
    const message = (text ?? input).trim();
    if (!message || isLoading) return;

    if (!conversation) {
      const conv = await startConversation(message);
      navigate(`/influencer-lens/${conv.id}`);
      setInput('');
      return;
    }

    if (!text) setInput('');
    await sendMessage(message);
  };

  const handleNewConversation = async () => {
    const conv = await startConversation();
    setConversations((prev) => [conv, ...prev]);
    navigate(`/influencer-lens/${conv.id}`);
  };

  const handleWizardSubmit = async (brief: Partial<BriefStructured>) => {
    setWizardLoading(true);
    setShowWizard(false);
    try {
      const run = await lensApi.search.createRun({
        product_name: brief.product_name ?? undefined,
        industry: brief.industry ?? undefined,
        niches: brief.niches ?? [],
        hashtags: brief.hashtags ?? [],
        audience_gender: brief.audience_gender ?? 'all',
        audience_age_min: brief.audience_age_min ?? 25,
        audience_age_max: brief.audience_age_max ?? 45,
        audience_countries: brief.audience_countries ?? ['VE'],
        audience_cities: brief.audience_cities ?? [],
        platforms: brief.platforms ?? ['instagram'],
        tone: brief.tone ?? [],
      });
      toast.success('Búsqueda iniciada con wizard');
      navigate(`/influencer-lens/search?runId=${run.id}`);
    } catch {
      toast.error('Error al iniciar la búsqueda');
    } finally {
      setWizardLoading(false);
    }
  };

  const handleOpenWizard = (brief?: Partial<BriefStructured>) => {
    setWizardBrief(brief);
    setShowWizard(true);
  };

  return (
    <div className="flex flex-col h-[calc(100vh-64px)] px-6 py-4">
      <div className="mb-4 flex-shrink-0 flex flex-col gap-3 md:flex-row md:items-end md:justify-between">
        <div>
          <div className="flex items-center gap-3">
            <div className="relative flex h-9 w-9 items-center justify-center rounded-xl bg-gradient-brand text-white shadow-glow">
              <Sparkles className="h-5 w-5" />
            </div>
            <h1 className="text-2xl font-bold tracking-tight text-foreground md:text-3xl">Influencer Lens</h1>
          </div>
          <div className="flex items-center gap-3 mt-1.5">
            <span className="relative flex h-2 w-2">
              <span className="absolute inline-flex h-full w-full animate-ping rounded-full bg-emerald-400 opacity-60" />
              <span className="relative inline-flex h-2 w-2 rounded-full bg-emerald-500" />
            </span>
            <span className="text-xs font-medium text-foreground">Lens AI · online</span>
            <span className="text-muted-foreground">·</span>
            <p className="text-xs text-muted-foreground hidden md:block">
              El cerebro AI de La Web Figital Agency · Descubre creadores con datos reales de Apify.
            </p>
            {totalCost > 0 && (
              <div className="flex items-center gap-1 text-[10px] text-muted-foreground/60 bg-muted px-2 py-0.5 rounded-full">
                <DollarSign className="w-3 h-3" />
                <span>${totalCost.toFixed(4)} en uso</span>
              </div>
            )}
          </div>
        </div>
        <Button onClick={() => handleOpenWizard()} className="gap-2 rounded-xl bg-gradient-brand text-white shadow-glow hover:-translate-y-0.5 transition-transform">
          <Wand2 className="w-4 h-4" />
          Nueva búsqueda
        </Button>
      </div>

      <div className="grid gap-6 lg:grid-cols-[280px_1fr] flex-1 min-h-0">
        <div className="rounded-2xl border border-border/60 bg-card p-3 shadow-soft overflow-hidden flex flex-col">
          <div className="mb-2 flex items-center justify-between px-2 pt-1 flex-shrink-0">
            <h3 className="text-xs font-semibold uppercase tracking-[0.14em] text-muted-foreground">Conversaciones</h3>
            <span className="text-[10px] text-muted-foreground">{conversations.length}</span>
          </div>
          <div className="flex-1 overflow-y-auto space-y-1">
            {conversations.length === 0 ? (
              <div className="p-3 text-xs text-muted-foreground text-center">
                Sin conversaciones
              </div>
            ) : (
              conversations.map((conv) => (
                <button
                  key={conv.id}
                  onClick={() => navigate(`/influencer-lens/${conv.id}`)}
                  className={cn(
                    'w-full text-left px-3 py-2.5 rounded-xl text-sm transition-colors',
                    conv.id === id
                      ? 'bg-gradient-brand-soft ring-1 ring-brand-purple/30'
                      : 'hover:bg-muted/60',
                  )}
                >
                  <p className="text-[13px] font-semibold truncate">
                    {conv.accumulated_brief?.slice(0, 40) || 'Nueva búsqueda'}
                  </p>
                  <p className="text-[11px] text-muted-foreground mt-0.5">
                    {new Date(conv.last_message_at).toLocaleDateString('es-ES')}
                  </p>
                </button>
              ))
            )}
          </div>
        </div>

        <div className="flex flex-col overflow-hidden rounded-2xl border border-border/60 bg-card shadow-soft">
          {!conversation && !isLoading ? (
            <div className="flex-1 flex flex-col items-center justify-center p-8 min-h-[400px]">
              <LensEmptyState variant="no_conversations" />
              <Button onClick={handleNewConversation} className="mt-4 gap-2">
                <MessageSquare className="w-4 h-4" />
                Iniciar primera búsqueda
              </Button>
            </div>
          ) : (
            <>
              <div className="flex items-center justify-between border-b border-border/60 bg-muted/30 px-5 py-3">
                <div className="flex items-center gap-2">
                  <span className="relative flex h-2 w-2">
                    <span className="absolute inline-flex h-full w-full animate-ping rounded-full bg-emerald-400 opacity-60" />
                    <span className="relative inline-flex h-2 w-2 rounded-full bg-emerald-500" />
                  </span>
                  <span className="text-xs font-medium text-foreground">Lens AI · online</span>
                </div>
                <span className="text-[10px] text-muted-foreground">GPT-4 + Apify · v2.6</span>
              </div>

              <div className="flex-1 overflow-y-auto p-4 md:p-6 space-y-4">
                {turns.length === 0 && (
                  <div className="flex justify-start">
                    <div className="max-w-[85%] md:max-w-[80%] rounded-2xl px-4 py-3 bg-muted text-sm whitespace-pre-wrap">
                      {WELCOME}
                    </div>
                  </div>
                )}

                {turns.map((turn) => (
                  <ChatMessage
                    key={turn.id}
                    turn={turn}
                    onSaveCandidate={saveCandidate}
                    onDismissCandidate={dismissCandidate}
                  />
                ))}

                {isLoading && (
                  <div className="flex justify-start">
                    <div className="bg-muted rounded-2xl px-4 py-3 flex items-center gap-2">
                      <div className="w-2 h-2 rounded-full bg-muted-foreground animate-bounce" />
                      <div className="w-2 h-2 rounded-full bg-muted-foreground animate-bounce [animation-delay:0.15s]" />
                      <div className="w-2 h-2 rounded-full bg-muted-foreground animate-bounce [animation-delay:0.3s]" />
                    </div>
                  </div>
                )}

                {error && (
                  <div className="text-sm text-red-400 text-center py-2">
                    Error: {error}
                  </div>
                )}

                <div ref={bottomRef} />
              </div>

              {pendingBrief && (
                <div className="border-t p-4">
                  <BriefConfirmCard
                    brief={pendingBrief}
                    onConfirm={confirmBrief}
                    onEdit={() => handleOpenWizard(pendingBrief)}
                    isLoading={isLoading}
                  />
                </div>
              )}

              <div className="border-t p-4">
                <div className="flex flex-wrap gap-2 mb-3">
                  <Chip icon={<Sparkles className="h-3.5 w-3.5" />} label="Buscar creadores" />
                  <Chip icon={<TrendingUp className="h-3.5 w-3.5" />} label="Proyección 3 escenarios" />
                  <Chip icon={<MessageSquare className="h-3.5 w-3.5" />} label="Mis guardados" />
                </div>
                <div className="flex items-end gap-2 rounded-2xl border border-border bg-background p-2 focus-within:border-brand-purple/60 focus-within:shadow-glow transition-all">
                  <textarea
                    value={input}
                    onChange={(e) => setInput(e.target.value)}
                    onKeyDown={(e) => {
                      if (e.key === 'Enter' && !e.shiftKey) {
                        e.preventDefault();
                        handleSend();
                      }
                    }}
                    placeholder="Describe tu producto o campaña…"
                    rows={1}
                    className="flex-1 resize-none bg-transparent px-3 py-2 text-sm outline-none placeholder:text-muted-foreground"
                    disabled={isLoading}
                  />
                  <Button onClick={() => handleSend()} disabled={isLoading || !input.trim()} className="rounded-xl bg-gradient-brand text-white shadow-glow hover:-translate-y-0.5 transition-transform flex-shrink-0">
                    <Send className="w-4 h-4" />
                  </Button>
                </div>
                <p className="mt-2 px-1 text-[10px] text-muted-foreground">
                  Enter para enviar · Shift+Enter para nueva línea
                </p>
              </div>
            </>
          )}
        </div>
      </div>

      <Dialog open={showWizard} onOpenChange={setShowWizard}>
        <DialogContent className="max-w-2xl max-h-[90vh] overflow-y-auto p-0 gap-0">
          <BriefWizard
            onSubmit={handleWizardSubmit}
            onCancel={() => setShowWizard(false)}
            initialBrief={wizardBrief}
          />
        </DialogContent>
      </Dialog>
    </div>
  );
}

function Chip({ icon, label }: { icon: React.ReactNode; label: string }) {
  return (
    <button className="inline-flex items-center gap-1.5 rounded-full border border-border bg-card px-3 py-1.5 text-xs font-medium text-foreground transition-colors hover:border-brand-purple/50 hover:bg-gradient-brand-soft">
      {icon}
      {label}
    </button>
  );
}
