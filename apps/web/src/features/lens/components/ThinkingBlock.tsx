import { useState } from 'react';
import { ChevronDown, ChevronRight, Sparkles } from 'lucide-react';
import { cn } from '@/lib/utils';

interface ThinkingBlockProps {
  reasoning: string;
  latency_ms?: number | null;
}

function formatMs(ms: number): string {
  if (ms < 1000) return `${ms}ms`;
  return `${(ms / 1000).toFixed(1)}s`;
}

export function ThinkingBlock({ reasoning, latency_ms }: ThinkingBlockProps) {
  const [expanded, setExpanded] = useState(true);

  return (
    <div className="mt-2 mb-1">
      <button
        onClick={() => setExpanded((p) => !p)}
        className="flex items-center gap-1.5 text-xs text-muted-foreground hover:text-foreground transition-colors mb-1"
      >
        {expanded ? (
          <ChevronDown className="w-3 h-3 text-blue-500" />
        ) : (
          <ChevronRight className="w-3 h-3 text-blue-500" />
        )}
        <Sparkles className="w-3 h-3 text-blue-500" />
        <span className="font-medium text-blue-600 dark:text-blue-400">Procesando</span>
        {latency_ms != null && (
          <span className="text-muted-foreground/60">· {formatMs(latency_ms)}</span>
        )}
      </button>
      {expanded && (
        <div className="pl-4 border-l-2 border-blue-500/30 space-y-1">
          {reasoning.split('\n').filter(Boolean).map((line, i) => (
            <p key={i} className={cn(
              'text-xs leading-relaxed',
              line.startsWith('→') || line.startsWith('•') || line.startsWith('-')
                ? 'text-blue-600/80 dark:text-blue-400/80'
                : 'text-muted-foreground'
            )}>
              {line.startsWith('→') || line.startsWith('•') || line.startsWith('-') ? line : `▸ ${line}`}
            </p>
          ))}
        </div>
      )}
    </div>
  );
}
