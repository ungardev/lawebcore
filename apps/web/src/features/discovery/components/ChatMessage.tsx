import { Loader2 } from 'lucide-react';
import { cn } from '@/lib/utils';
import type { ChatTurn } from '../types/discovery';

interface ChatMessageProps {
  turn: ChatTurn;
}

export function ChatMessage({ turn }: ChatMessageProps) {
  const isUser = turn.role === 'user';

  return (
    <div className={cn('flex', isUser ? 'justify-end' : 'justify-start')}>
      <div
        className={cn(
          'max-w-[85%] md:max-w-[80%] rounded-2xl px-4 py-3',
          isUser ? 'bg-primary text-primary-foreground' : 'bg-muted text-foreground',
        )}
      >
        <div className="flex items-start gap-2">
          {!isUser && (
            <span className="text-[10px] px-1.5 py-0.5 rounded bg-gradient-to-r from-pink-500/20 to-blue-500/20 text-foreground font-medium border border-pink-500/30 mt-0.5">
              IA
            </span>
          )}
          <p className="text-sm whitespace-pre-wrap flex-1">{turn.content}</p>
          {turn.isLoading && <Loader2 className="w-4 h-4 animate-spin flex-shrink-0 mt-0.5" />}
        </div>

        {turn.isError && (
          <p className="text-xs text-red-400 mt-1">Error al procesar. Intenta de nuevo.</p>
        )}
      </div>
    </div>
  );
}
