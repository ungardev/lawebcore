import { DollarSign, Clock, Zap } from 'lucide-react';
import { cn } from '@/lib/utils';

interface CostBadgeProps {
  cost_usd?: number | null;
  latency_ms?: number | null;
  tokens?: number | null;
  showLabels?: boolean;
}

export function CostBadge({ cost_usd, latency_ms, tokens, showLabels = false }: CostBadgeProps) {
  const hasCost = cost_usd != null && cost_usd > 0;
  const hasLatency = latency_ms != null;

  if (!hasCost && !hasLatency) return null;

  return (
    <div className="flex items-center gap-2 text-[10px] text-muted-foreground/60">
      {hasCost && (
        <div className="flex items-center gap-0.5">
          <DollarSign className="w-3 h-3" />
          <span>${cost_usd!.toFixed(4)}</span>
          {tokens != null && <span className="text-muted-foreground/40">({tokens.toLocaleString()} tok)</span>}
        </div>
      )}
      {hasLatency && (
        <div className="flex items-center gap-0.5">
          <Clock className="w-3 h-3" />
          <span>
            {latency_ms! < 1000
              ? `${latency_ms}ms`
              : `${(latency_ms! / 1000).toFixed(1)}s`}
          </span>
        </div>
      )}
    </div>
  );
}

interface ThinkingIndicatorProps {
  className?: string;
}

export function ThinkingIndicator({ className }: ThinkingIndicatorProps) {
  return (
    <div className={cn('flex items-center gap-1.5 text-xs text-muted-foreground', className)}>
      <Zap className="w-3 h-3 text-blue-500 animate-pulse" />
      <span className="text-blue-500 font-medium">Procesando</span>
      <div className="flex gap-0.5">
        <span className="w-1.5 h-1.5 rounded-full bg-blue-400 animate-bounce [animation-delay:0ms]" />
        <span className="w-1.5 h-1.5 rounded-full bg-blue-400 animate-bounce [animation-delay:150ms]" />
        <span className="w-1.5 h-1.5 rounded-full bg-blue-400 animate-bounce [animation-delay:300ms]" />
      </div>
    </div>
  );
}
