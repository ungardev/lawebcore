import { cn } from '@/lib/utils';
import { Link } from 'react-router-dom';
import type { ReactNode } from 'react';

interface KpiCardProps {
  title: string;
  value: ReactNode;
  hint?: string;
  icon?: ReactNode;
  trend?: { value: number; positive: boolean };
  className?: string;
  to?: string;
}

export function KpiCard({ title, value, hint, icon, trend, className, to }: KpiCardProps) {
  const content = (
    <>
      <div className="flex items-start justify-between mb-2">
        <h3 className="text-sm font-medium text-muted-foreground">{title}</h3>
        {icon && <div className="text-muted-foreground">{icon}</div>}
      </div>
      <div className="text-2xl font-bold text-foreground">{value}</div>
      {hint && <p className="text-xs text-muted-foreground mt-1">{hint}</p>}
      {trend && (
        <p className={cn('text-xs mt-2 font-medium', trend.positive ? 'text-emerald-600' : 'text-rose-600')}>
          {trend.positive ? '+' : ''}
          {trend.value}%
        </p>
      )}
    </>
  );

  const cardClass = cn(
    'rounded-xl border bg-card p-5 shadow-sm',
    to && 'transition-all hover:border-primary/50 hover:shadow-md hover:-translate-y-0.5 cursor-pointer',
    className
  );

  if (to) {
    return (
      <Link to={to} className={cardClass}>
        {content}
      </Link>
    );
  }

  return <div className={cardClass}>{content}</div>;
}
