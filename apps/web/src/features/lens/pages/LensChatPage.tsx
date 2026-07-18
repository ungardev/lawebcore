import { useEffect, useRef, useState } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { Send, Sparkles, Plus, MessageSquare, DollarSign } from 'lucide-react';
import { useDiscoveryConversation } from '../hooks/useDiscoveryConversation';
import { ChatMessage } from '../components/ChatMessage';
import { BriefConfirmCard } from '../components/BriefConfirmCard';
import { LensEmptyState } from '../components/LensEmptyState';
import { ActionChips } from '../components/ActionChips';
import { CostBadge } from '../components/CostBadge';
import { Card } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { lensApi } from '../api/lensApi';
import { cn } from '@/lib/utils';
import type { DiscoveryConversation } from '../types/discovery';

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
    lensApi.conversations.list({ limit: 20 }).then(setConversations).catch(() => {});
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

  return (
    <div className="flex flex-col h-[calc(100vh-80px)] md:h-[calc(100vh-100px)]">
      <div className="mb-3 flex items-start justify-between gap-4">
        <div>
          <h1 className="text-2xl md:text-3xl font-bold flex items-center gap-2">
            <Sparkles className="w-6 md:w-7 text-primary" />
            Influencer Lens
          </h1>
          <div className="flex items-center gap-3 mt-0.5">
            <p className="text-xs text-muted-foreground hidden sm:block">
              El cerebro AI de La Web Figital Agency
            </p>
            {totalCost > 0 && (
              <div className="flex items-center gap-1 text-[10px] text-muted-foreground/60 bg-muted px-2 py-0.5 rounded-full">
                <DollarSign className="w-3 h-3" />
                <span>${totalCost.toFixed(4)} en uso</span>
              </div>
            )}
          </div>
        </div>
        <Button onClick={handleNewConversation} size="sm" className="gap-1.5 flex-shrink-0">
          <Plus className="w-4 h-4" />
          Nueva busqueda
        </Button>
      </div>

      <div className="flex flex-1 gap-4 overflow-hidden">
        <Card className="hidden lg:flex w-56 flex-col p-0 overflow-hidden flex-shrink-0">
          <div className="p-3 border-b">
            <h2 className="text-sm font-semibold">Conversaciones</h2>
          </div>
          <div className="flex-1 overflow-y-auto">
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
                    'w-full text-left px-3 py-2 border-b border-border/50 hover:bg-muted transition-colors',
                    conv.id === id && 'bg-muted',
                  )}
                >
                  <p className="text-xs font-medium truncate">
                    {conv.accumulated_brief?.slice(0, 40) || 'Nueva busqueda'}
                  </p>
                  <p className="text-[10px] text-muted-foreground">
                    {new Date(conv.last_message_at).toLocaleDateString('es-ES')}
                  </p>
                </button>
              ))
            )}
          </div>
        </Card>

        <Card className="flex-1 flex flex-col p-0 overflow-hidden">
          {!conversation && !isLoading ? (
            <div className="flex-1 flex flex-col items-center justify-center p-6">
              <LensEmptyState variant="no_conversations" />
              <Button onClick={handleNewConversation} className="mt-4 gap-2">
                <MessageSquare className="w-4 h-4" />
                Iniciar primera busqueda
              </Button>
            </div>
          ) : (
            <>
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
                    onEdit={() => {}}
                    isLoading={isLoading}
                  />
                </div>
              )}

              <div className="border-t p-3 md:p-4 flex flex-col gap-2">
                <ActionChips onSend={(prompt) => handleSend(prompt)} disabled={isLoading} />
                <div className="flex gap-2">
                  <Input
                    value={input}
                    onChange={(e) => setInput(e.target.value)}
                    onKeyDown={(e) => e.key === 'Enter' && handleSend()}
                    placeholder="Describe tu producto o campaña..."
                    disabled={isLoading}
                  />
                  <Button onClick={() => handleSend()} disabled={isLoading || !input.trim()} className="flex-shrink-0">
                    <Send className="w-4 h-4" />
                  </Button>
                </div>
              </div>
            </>
          )}
        </Card>
      </div>
    </div>
  );
}
