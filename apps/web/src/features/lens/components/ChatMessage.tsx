import { Loader2 } from 'lucide-react';
import { cn } from '@/lib/utils';
import type { ChatTurn } from '../types/discovery';
import { ThinkingBlock } from './ThinkingBlock';
import { ToolCallBlock } from './ToolCallBlock';
import { CandidateCard } from './CandidateCard';
import { SearchProgress } from './SearchProgress';
import { CostBadge } from './CostBadge';

interface ChatMessageProps {
  turn: ChatTurn;
  onSaveCandidate?: (id: string) => void;
  onDismissCandidate?: (id: string) => void;
}

export function ChatMessage({ turn, onSaveCandidate, onDismissCandidate }: ChatMessageProps) {
  const isUser = turn.role === 'user';

  return (
    <div className={cn('flex', isUser ? 'justify-end' : 'justify-start')}>
      <div
        className={cn(
          'max-w-[90%] md:max-w-[85%] rounded-2xl px-4 py-3',
          isUser ? 'bg-primary text-primary-foreground' : 'bg-muted text-foreground',
        )}
      >
        <div className="flex items-start gap-2">
          {!isUser && (
            <span className="text-[10px] px-1.5 py-0.5 rounded bg-gradient-to-r from-pink-500/20 to-blue-500/20 text-foreground font-medium border border-pink-500/30 mt-0.5">
              IA
            </span>
          )}
          <div className="flex-1 min-w-0">
            {isUser ? (
              <p className="text-sm whitespace-pre-wrap">{turn.content}</p>
            ) : (
              <>
                {turn.isLoading && !turn.content && !turn.reasoning ? (
                  <div className="flex items-center gap-2 text-sm text-muted-foreground">
                    <Loader2 className="w-4 h-4 animate-spin" />
                    Pensando...
                  </div>
                ) : (
                  <>
                    {turn.content && (
                      <p className="text-sm whitespace-pre-wrap">{turn.content}</p>
                    )}
                    {turn.reasoning && (
                      <ThinkingBlock
                        reasoning={turn.reasoning}
                        latency_ms={turn.latency_ms}
                      />
                    )}
                    {turn.tool_calls && turn.tool_calls.length > 0 && (
                      <ToolCallBlock
                        tool_calls={turn.tool_calls}
                        tool_results={turn.tool_results}
                      />
                    )}
                    {turn.candidates && turn.candidates.length > 0 && (
                      <div className="mt-3 space-y-3">
                        <p className="text-xs font-semibold text-foreground">
                          {turn.candidates.length} candidatos encontrados
                        </p>
                        <div className="grid gap-3">
                          {turn.candidates.map((c) => (
                            <CandidateCard
                              key={c.id}
                              candidate={c}
                              onSave={onSaveCandidate}
                              onDismiss={onDismissCandidate}
                            />
                          ))}
                        </div>
                      </div>
                    )}

                    {turn.progress && !turn.candidates && (
                      <div className="mt-3">
                        <SearchProgress
                          progress={turn.progress}
                        />
                      </div>
                    )}

                    <div className="flex items-center justify-between mt-2">
                      {!turn.progress && !turn.candidates && (
                        <p className="text-xs text-muted-foreground">
                          {turn.content ? '' : 'Procesando...'}
                        </p>
                      )}
                      <CostBadge
                        cost_usd={turn.cost_usd}
                        latency_ms={turn.latency_ms}
                      />
                    </div>
                  </>
                )}
              </>
            )}
          </div>
          {turn.isLoading && !isUser && <Loader2 className="w-4 h-4 animate-spin flex-shrink-0 mt-0.5" />}
        </div>

        {turn.isError && (
          <p className="text-xs text-red-400 mt-2">Error al procesar. Intenta de nuevo.</p>
        )}
      </div>
    </div>
  );
}
