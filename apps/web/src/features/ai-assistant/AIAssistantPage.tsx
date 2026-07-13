import { useState, useRef, useEffect } from 'react';
import { Send, Sparkles, Loader2, Database, ChevronDown, ChevronUp, RefreshCw, BrainCircuit } from 'lucide-react';
import { aiApi } from '@/lib/api';
import { Card } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { cn } from '@/lib/utils';
import { toast } from 'sonner';

interface MessageSource {
  type: string;
  id: string;
  similarity: number;
  excerpt: string;
}

interface Message {
  id: string;
  role: 'user' | 'assistant';
  content: string;
  sources?: MessageSource[];
  usedRag?: boolean;
}

const SOURCE_TYPE_LABELS: Record<string, string> = {
  publicacion: 'Publicación',
  influencer_score: 'Score Influencer',
  benchmark: 'Benchmark LWFA',
  documento: 'Documento',
  unknown: 'Fuente',
};

function SourceCard({ source }: { source: MessageSource }) {
  const [expanded, setExpanded] = useState(false);
  const label = SOURCE_TYPE_LABELS[source.type] || SOURCE_TYPE_LABELS.unknown;

  return (
    <div className="border border-border rounded-lg p-2 text-xs">
      <div className="flex items-center justify-between gap-2">
        <div className="flex items-center gap-1.5">
          <span className="font-medium text-foreground">{label}</span>
          <span className="text-muted-foreground">#{source.id.slice(0, 8)}</span>
          <span className={cn(
            "text-[10px] px-1.5 py-0.5 rounded",
            source.similarity >= 0.8 ? 'bg-emerald-100 text-emerald-700' :
            source.similarity >= 0.7 ? 'bg-amber-100 text-amber-700' :
            'bg-slate-100 text-slate-600'
          )}>
            {(source.similarity * 100).toFixed(0)}%
          </span>
        </div>
        <button
          onClick={() => setExpanded(!expanded)}
          className="text-muted-foreground hover:text-foreground"
        >
          {expanded ? <ChevronUp className="w-3 h-3" /> : <ChevronDown className="w-3 h-3" />}
        </button>
      </div>
      {expanded && (
        <p className="mt-1.5 text-muted-foreground leading-relaxed">{source.excerpt || source.excerpt}</p>
      )}
    </div>
  );
}

function SourcesSection({ sources }: { sources: MessageSource[] }) {
  const [expanded, setExpanded] = useState(false);

  if (!sources || sources.length === 0) return null;

  return (
    <div className="mt-3 pt-3 border-t border-border/40">
      <button
        onClick={() => setExpanded(!expanded)}
        className="flex items-center gap-1.5 text-xs font-semibold text-muted-foreground hover:text-foreground mb-2"
      >
        <BrainCircuit className="w-3 h-3" />
        Fuentes ({sources.length})
        {expanded ? <ChevronUp className="w-3 h-3" /> : <ChevronDown className="w-3 h-3" />}
      </button>
      {expanded && (
        <div className="space-y-1">
          {sources.map((s, i) => (
            <SourceCard key={i} source={s} />
          ))}
        </div>
      )}
    </div>
  );
}

export function AIAssistantPage() {
  const [messages, setMessages] = useState<Message[]>([
    {
      id: 'welcome',
      role: 'assistant',
      content: 'Hola! Soy el asistente IA de La Web Core, potenciado con RAG sobre tu base de conocimiento de campañas, influencers y benchmarks. Puedo responder preguntas como:\n\n• "¿Cuál es el mejor influencer NANO para la campaña OREO?"\n• "¿Cuál fue el ER promedio de la campaña #PorFinIlimitados?"\n• "¿Qué benchmark usa un creador MICRO en Venezuela?"\n\nLos datos se actualizan automaticamente cuando cargas publicaciones. Que necesitas saber?',
    },
  ]);
  const [input, setInput] = useState('');
  const [conversationId, setConversationId] = useState<string | undefined>();
  const [loading, setLoading] = useState(false);
  const [reindexing, setReindexing] = useState(false);
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
        sources: resp.sources as MessageSource[],
        usedRag: resp.used_rag,
      };
      setMessages((m) => [...m, aiMsg]);
    } catch {
      const errMsg: Message = {
        id: `e-${Date.now()}`,
        role: 'assistant',
        content: 'Disculpa, hubo un error. Verifica que el backend esté corriendo y que las API keys estén configuradas.',
      };
      setMessages((m) => [...m, errMsg]);
    } finally {
      setLoading(false);
    }
  };

  const handleReindex = async () => {
    setReindexing(true);
    try {
      const { api } = await import('@/lib/api');
      await api.post('/api/v1/ai/index/reindex', { full: true });
      toast.success('Índice RAG actualizado');
    } catch {
      toast.error('Error al re-indexar. Intenta de nuevo.');
    } finally {
      setReindexing(false);
    }
  };

  return (
    <div className="flex flex-col h-[calc(100vh-80px)] md:h-[calc(100vh-100px)]">
      <div className="mb-4 flex items-start justify-between gap-4">
        <div>
          <h1 className="text-2xl md:text-3xl font-bold flex items-center gap-2">
            <Sparkles className="w-6 md:w-7 text-foreground" />
            Asistente IA
          </h1>
          <p className="text-sm md:text-base text-muted-foreground hidden sm:block">
            Consulta la base de conocimiento de La Web Core
          </p>
        </div>
        <Button
          variant="outline"
          size="sm"
          onClick={handleReindex}
          disabled={reindexing}
          className="flex-shrink-0 gap-1.5 text-xs"
          title="Re-indexar datos P.I.A.R. en el vector store"
        >
          {reindexing ? <RefreshCw className="w-3 h-3 animate-spin" /> : <Database className="w-3 h-3" />}
          Re-indexar RAG
        </Button>
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
                {m.role === 'assistant' && m.usedRag && (
                  <div className="flex items-center gap-1 mb-2">
                    <span className="text-[10px] px-1.5 py-0.5 rounded bg-gradient-to-r from-pink-500/20 to-blue-500/20 text-foreground font-medium border border-[#EC4899]/30">
                      RAG activo
                    </span>
                  </div>
                )}
                <p className="text-sm whitespace-pre-wrap">{m.content}</p>
                {m.sources && m.sources.length > 0 && (
                  <SourcesSection sources={m.sources} />
                )}
              </div>
            </div>
          ))}
          {loading && (
            <div className="flex justify-start">
              <div className="bg-muted rounded-2xl px-4 py-3 flex items-center gap-2">
                <Loader2 className="w-4 h-4 animate-spin text-muted-foreground" />
                <span className="text-xs text-muted-foreground">Pensando...</span>
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
            placeholder="Pregunta sobre campañas, marcas, influencers, benchmarks..."
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
