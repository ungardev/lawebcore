import { ArrowRight, CheckCircle2, XCircle, Loader2 } from 'lucide-react';
import { cn } from '@/lib/utils';
import type { ToolCall, ToolResult } from '../types/discovery';

interface ToolCallBlockProps {
  tool_calls: ToolCall[];
  tool_results?: ToolResult[] | null;
}

function formatArgs(args: Record<string, unknown>): string {
  const entries = Object.entries(args).filter(([, v]) => v !== undefined && v !== null);
  if (entries.length === 0) return '{}';
  if (entries.length <= 2 && entries.every(([, v]) => typeof v !== 'object')) {
    return entries.map(([k, v]) => `${k}: ${JSON.stringify(v)}`).join(', ');
  }
  return JSON.stringify(args, null, 2);
}

export function ToolCallBlock({ tool_calls, tool_results }: ToolCallBlockProps) {
  if (!tool_calls?.length) return null;

  return (
    <div className="mt-3 space-y-2">
      <p className="text-[10px] text-muted-foreground font-medium uppercase tracking-wider">Herramientas ejecutadas</p>
      {tool_calls.map((tc, i) => {
        const result = tool_results?.find((r) => r.tool_call_id === tc.id);
        const isLoading = !result;
        const isSuccess = result?.success;
        const isError = result && !result.success;

        return (
          <div key={tc.id || i} className="rounded-lg border bg-muted/40 overflow-hidden text-xs font-mono">
            <div className={cn(
              'flex items-center gap-2 px-3 py-2 border-b bg-muted/60',
              isSuccess && 'border-emerald-500/20',
              isError && 'border-red-500/20',
            )}>
              <ArrowRight className="w-3 h-3 text-primary flex-shrink-0" />
              <span className="text-primary font-semibold">{tc.name}</span>
              <span className="text-muted-foreground flex-1 truncate">
                {formatArgs(tc.arguments)}
              </span>
              {isLoading && <Loader2 className="w-3 h-3 animate-spin text-muted-foreground flex-shrink-0" />}
              {isSuccess && <CheckCircle2 className="w-3 h-3 text-emerald-500 flex-shrink-0" />}
              {isError && <XCircle className="w-3 h-3 text-red-500 flex-shrink-0" />}
            </div>
            {result && isSuccess && (
              <div className="px-3 py-2 text-muted-foreground">
                {typeof result.output === 'object' ? (
                  <span className="text-emerald-600 dark:text-emerald-400">
                    ✓ {Array.isArray(result.output)
                      ? `${(result.output as unknown[]).length} resultados`
                      : JSON.stringify(result.output).slice(0, 100)}
                  </span>
                ) : (
                  <span className="text-emerald-600 dark:text-emerald-400">✓ {String(result.output).slice(0, 120)}</span>
                )}
              </div>
            )}
            {result && isError && (
              <div className="px-3 py-2 text-red-500">
                ✗ {result.error || 'Error desconocido'}
              </div>
            )}
          </div>
        );
      })}
    </div>
  );
}
