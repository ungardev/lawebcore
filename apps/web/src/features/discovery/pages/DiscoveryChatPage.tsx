import { useEffect, useRef, useState } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { Send, Sparkles, Plus, MessageSquare } from 'lucide-react';
import { useDiscoveryConversation } from '../hooks/useDiscoveryConversation';
import { ChatMessage } from '../components/ChatMessage';
import { CandidateCard } from '../components/CandidateCard';
import { BriefConfirmCard } from '../components/BriefConfirmCard';
import { DiscoveryEmptyState } from '../components/DiscoveryEmptyState';
import { Card } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { discoveryApi } from '../api/discoveryApi';
import { cn } from '@/lib/utils';
import type { DiscoveryConversation } from '../types/discovery';

const WELCOME = `¡Hola! Soy el asistente de Discovery de P.I.A.R. Puedo ayudarte a descubrir influencers ideales para tus campañas.

Simplemente descríbeme tu producto o campaña en lenguaje natural. Por ejemplo:

• "Busco influencers de fitness en Colombia, presupuesto $2000 USD"
• "Necesito micro-influencers de comida mexicana en México DF"
• "Creatores de viaje y aventura en España, público femenino 25-35"

¿En qué puedo ayudarte?`;

export function DiscoveryChatPage() {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const [input, setInput] = useState('');
  const bottomRef = useRef<HTMLDivElement>(null);
  const [conversations, setConversations] = useState<DiscoveryConversation[]>([]);

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
    discoveryApi.conversations.list({ limit: 20 }).then(setConversations).catch(() => {});
  }, []);

  useEffect(() => {
    if (id) {
      loadConversation(id).catch(() => navigate('/influencer-search'));
    } else if (conversations.length > 0) {
      navigate(`/influencer-search/${conversations[0].id}`, { replace: true });
    }
  }, [id]);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [turns]);

  const handleSend = async () => {
    if (!input.trim() || isLoading) return;

    if (!conversation) {
      const conv = await startConversation(input);
      navigate(`/influencer-search/${conv.id}`);
      setInput('');
      return;
    }

    setInput('');
    await sendMessage(input);
  };

  const handleNewConversation = async () => {
    const conv = await startConversation();
    setConversations((prev) => [conv, ...prev]);
    navigate(`/influencer-search/${conv.id}`);
  };

  const allCandidates = turns.flatMap((t) => t.candidates ?? []);

  return (
    <div className="flex flex-col h-[calc(100vh-80px)] md:h-[calc(100vh-100px)]">
      <div className="mb-4 flex items-start justify-between gap-4">
        <div>
          <h1 className="text-2xl md:text-3xl font-bold flex items-center gap-2">
            <Sparkles className="w-6 md:w-7 text-primary" />
            Discovery
          </h1>
          <p className="text-sm md:text-base text-muted-foreground hidden sm:block">
            Descubre influencers ideales con lenguaje natural
          </p>
        </div>
        <Button onClick={handleNewConversation} size="sm" className="gap-1.5 flex-shrink-0">
          <Plus className="w-4 h-4" />
          Nueva búsqueda
        </Button>
      </div>

      <div className="flex flex-1 gap-4 overflow-hidden">
        <Card className="hidden lg:flex w-64 flex-col p-0 overflow-hidden flex-shrink-0">
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
                  onClick={() => navigate(`/influencer-search/${conv.id}`)}
                  className={cn(
                    'w-full text-left px-3 py-2 border-b border-border/50 hover:bg-muted transition-colors',
                    conv.id === id && 'bg-muted',
                  )}
                >
                  <p className="text-xs font-medium truncate">
                    {conv.accumulated_brief?.slice(0, 40) || 'Nueva búsqueda'}
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
              <DiscoveryEmptyState variant="no_conversations" />
              <Button onClick={handleNewConversation} className="mt-4 gap-2">
                <MessageSquare className="w-4 h-4" />
                Iniciar primera búsqueda
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
                  <div key={turn.id}>
                    <ChatMessage turn={turn} />
                    {turn.candidates && turn.candidates.length > 0 && (
                      <div className="mt-4 space-y-2">
                        <p className="text-xs text-muted-foreground font-medium px-1">
                          Candidatos encontrados ({turn.candidates.length})
                        </p>
                        {turn.candidates.map((c) => (
                          <CandidateCard
                            key={c.id}
                            candidate={c}
                            compact
                            onSave={saveCandidate}
                            onDismiss={dismissCandidate}
                          />
                        ))}
                      </div>
                    )}
                    {turn.run_summary && (
                      <div className="mt-2 px-1">
                        <p className="text-xs text-muted-foreground">
                          Búsqueda: {turn.run_summary.total_found} encontrados,
                          mejor score {turn.run_summary.top_score}/100,
                          plataformas: {turn.run_summary.platforms_queried.join(', ')}
                        </p>
                      </div>
                    )}
                  </div>
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

              <div className="border-t p-3 md:p-4 flex gap-2">
                <Input
                  value={input}
                  onChange={(e) => setInput(e.target.value)}
                  onKeyDown={(e) => e.key === 'Enter' && handleSend()}
                  placeholder="Describe tu producto o campaña..."
                  disabled={isLoading}
                />
                <Button onClick={handleSend} disabled={isLoading || !input.trim()} className="flex-shrink-0">
                  <Send className="w-4 h-4" />
                </Button>
              </div>
            </>
          )}
        </Card>
      </div>
    </div>
  );
}
