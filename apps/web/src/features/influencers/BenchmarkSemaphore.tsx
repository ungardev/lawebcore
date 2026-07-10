import { cn } from '@/lib/utils';

interface BenchmarkSemaphoreProps {
  retention: 'green' | 'yellow' | 'red' | undefined;
  engagement: 'green' | 'yellow' | 'red' | undefined;
  viralidad: 'green' | 'yellow' | 'red' | undefined;
  className?: string;
}

const COLOR_MAP = {
  green: 'bg-emerald-400',
  yellow: 'bg-amber-400',
  red: 'bg-red-400',
};

const LABEL_MAP: Record<string, string> = {
  retention: 'Retención',
  engagement: 'Engagement',
  viralidad: 'Viralidad',
};

export function BenchmarkSemaphore({ retention, engagement, viralidad, className }: BenchmarkSemaphoreProps) {
  const signals = [
    { key: 'retention', value: retention, color: retention ? COLOR_MAP[retention] : 'bg-slate-200' },
    { key: 'engagement', value: engagement, color: engagement ? COLOR_MAP[engagement] : 'bg-slate-200' },
    { key: 'viralidad', value: viralidad, color: viralidad ? COLOR_MAP[viralidad] : 'bg-slate-200' },
  ];

  return (
    <div className={cn('flex items-center gap-1.5', className)} title="Semáforo de benchmark">
      {signals.map((s) => (
        <div key={s.key} className="relative group">
          <div className={cn('w-2.5 h-2.5 rounded-full', s.color)} />
          <div className="absolute bottom-full left-1/2 -translate-x-1/2 mb-1 hidden group-hover:block z-10">
            <div className="bg-slate-900 text-white text-xs rounded px-2 py-1 whitespace-nowrap">
              {LABEL_MAP[s.key]}: {s.value ?? 'N/A'}
            </div>
          </div>
        </div>
      ))}
    </div>
  );
}
