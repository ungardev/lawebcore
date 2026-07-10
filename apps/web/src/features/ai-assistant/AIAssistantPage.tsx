import { useState, useRef, useEffect } from 'react';
import { Send, Sparkles, Loader2 } from 'lucide-react';
import { aiApi } from '@/lib/api';
import { Card } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { cn } from '@/lib/utils';

interface Message {
  id: string;
  role: 'user' | 'assistant';
  content: string;
  sources?: Array<{ chunk_id: string; document_id: string; similarity: number; excerpt: string }>;
}

export function AIAssistantPage() {
  const [messages, setMessages] = useState<Message[]>([
    {
      id: 'welcome',
      role: 'assistant',
      content: 'Hola! Soy el asistente IA de La Web Core. Puedo ayudarte a buscar informacion en la base de conocimiento de campanas, briefs, contratos y reportes. Que necesitas saber?',
    },
  ]);
  const [input, setInput] = useState('');
  const [conversationId, setConversationId] = useState<string | undefined>();
  const [loading, setLoading] = useState(false);
  const bottomRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages]);

  const send = async () => {
    if (!input.trim() || loading) return;
    const userMsg: Message = { id: `u-${Date.now()}`, role: 'user', content: input };
    setMessages((m) => [...m, userMsg]);
    setInput('');
    setLoading(true);

    try {
      const resp = await aiApi.chat({
        conversation_id: conversationId,
        message: userMsg.content,
      });
      setConversationId(resp.conversation_id);
      const aiMsg: Message = {
        id: `a-${Date.now()}`,
        role: 'assistant',
        content: resp.message,
        sources: resp.sources,
      };
      setMessages((m) => [...m, aiMsg]);
    } catch (e) {
      const errMsg: Message = {
        id: `e-${Date.now()}`,
        role: 'assistant',
        content: 'Disculpa, hubo un error. Verifica que el backend este corriendo y que las API keys esten configuradas.',
      };
      setMessages((m) => [...m, errMsg]);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="flex flex-col h-[calc(100vh-80px)] md:h-[calc(100vh-100px)]">
      <div className="mb-4">
        <h1 className="text-2xl md:text-3xl font-bold flex items-center gap-2">
          <Sparkles className="w-6 md:w-7 text-purple-600" />
          Asistente IA
        </h1>
        <p className="text-sm md:text-base text-muted-foreground hidden sm:block">Consulta la base de conocimiento de La Web Core</p>
      </div>

      <Card className="flex-1 flex flex-col p-0 overflow-hidden">
        <div className="flex-1 overflow-y-auto p-4 md:p-6 space-y-4">
          {messages.map((m) => (
            <div key={m.id} className={cn('flex', m.role === 'user' ? 'justify-end' : 'justify-start')}>
              <div
                className={cn(
                  'max-w-[85%] md:max-w-[80%] rounded-2xl px-4 py-3',
                  m.role === 'user'
                    ? 'bg-primary text-primary-foreground'
                    : 'bg-muted text-foreground',
                )}
              >
                <p className="text-sm whitespace-pre-wrap">{m.content}</p>
                {m.sources && m.sources.length > 0 && (
                  <div className="mt-3 pt-3 border-t border-border/40 space-y-1">
                    <p className="text-xs font-semibold opacity-70">Fuentes ({m.sources.length}):</p>
                    {m.sources.slice(0, 3).map((s, i) => (
                      <p key={i} className="text-xs opacity-70 truncate">• {s.excerpt}</p>
                    ))}
                  </div>
                )}
              </div>
            </div>
          ))}
          {loading && (
            <div className="flex justify-start">
              <div className="bg-muted rounded-2xl px-4 py-3">
                <Loader2 className="w-4 h-4 animate-spin" />
              </div>
            </div>
          )}
          <div ref={bottomRef} />
        </div>

        <div className="border-t p-3 md:p-4 flex gap-2">
          <Input
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={(e) => e.key === 'Enter' && send()}
            placeholder="Pregunta sobre campanas, marcas, influencers..."
            disabled={loading}
          />
          <Button onClick={send} disabled={loading || !input.trim()} className="flex-shrink-0">
            <Send className="w-4 h-4" />
          </Button>
        </div>
      </Card>
    </div>
  );
}
