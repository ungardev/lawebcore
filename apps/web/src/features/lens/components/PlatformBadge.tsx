import type { Platform } from '../types/discovery';
import { cn } from '@/lib/utils';

const platformConfig: Record<Platform, { label: string; className: string }> = {
  instagram: { label: 'Instagram', className: 'border-brand-pink/25 bg-brand-pink/10 text-brand-pink' },
  tiktok: { label: 'TikTok', className: 'border-divider bg-surface-raised text-foreground' },
  youtube: { label: 'YouTube', className: 'border-destructive/25 bg-destructive/10 text-destructive' },
  x: { label: 'X', className: 'border-divider bg-surface-raised text-foreground' },
  facebook: { label: 'Facebook', className: 'border-info/25 bg-info/10 text-info' },
};

interface PlatformBadgeProps {
  platform: Platform;
  size?: 'xs' | 'sm' | 'md';
  className?: string;
}

export function PlatformBadge({ platform, size = 'sm', className }: PlatformBadgeProps) {
  const config = platformConfig[platform] ?? { label: platform, className: 'bg-muted text-muted-foreground' };

  return (
    <span
      className={cn(
        'inline-flex items-center rounded border font-medium',
        size === 'xs' ? 'px-1 py-px text-[9px]' : size === 'sm' ? 'px-1.5 py-0.5 text-[10px]' : 'px-2 py-1 text-xs',
        config.className,
        className,
      )}
    >
      {config.label}
    </span>
  );
}
