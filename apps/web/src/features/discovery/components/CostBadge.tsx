import { cn } from '@/lib/utils';

interface CostBadgeProps {
  costUsd: number | null;
  size?: 'sm' | 'md';
  className?: string;
}

export function CostBadge({ costUsd, size = 'sm', className }: CostBadgeProps) {
  if (costUsd == null) return null;

  return (
    <span
      className={cn(
        'inline-flex items-center rounded-md font-mono font-medium',
        size === 'sm' ? 'px-1.5 py-0.5 text-[10px]' : 'px-2 py-1 text-xs',
        'bg-emerald-500/10 text-emerald-600 border border-emerald-500/20',
        className,
      )}
    >
      ${costUsd.toFixed(4)}
    </span>
  );
}
