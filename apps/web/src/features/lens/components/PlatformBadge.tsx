import { Camera, Music2, Play, AtSign, Users } from 'lucide-react';
import type { LucideIcon } from 'lucide-react';
import type { Platform } from '../types/discovery';
import { cn } from '@/lib/utils';

const platformConfig: Record<Platform, { label: string; className: string }> = {
  instagram: { label: 'Instagram', className: 'border-brand-pink/25 bg-brand-pink/10 text-brand-pink' },
  tiktok: { label: 'TikTok', className: 'border-divider bg-surface-raised text-foreground' },
  youtube: { label: 'YouTube', className: 'border-destructive/25 bg-destructive/10 text-destructive' },
  x: { label: 'X', className: 'border-divider bg-surface-raised text-foreground' },
  facebook: { label: 'Facebook', className: 'border-info/25 bg-info/10 text-info' },
};

const platformIcons: Record<Platform, LucideIcon> = {
  instagram: Camera,
  tiktok: Music2,
  youtube: Play,
  x: AtSign,
  facebook: Users,
};

interface PlatformBadgeProps {
  platform: Platform;
  size?: 'xs' | 'sm' | 'md';
  icon?: boolean;
  className?: string;
}

export function PlatformBadge({ platform, size = 'sm', icon = false, className }: PlatformBadgeProps) {
  const config = platformConfig[platform] ?? { label: platform, className: 'bg-muted text-muted-foreground' };
  const Icon = platformIcons[platform];

  if (icon && Icon) {
    return (
      <span
        className={cn(
          'inline-flex items-center justify-center rounded',
          size === 'xs' ? 'w-4 h-4' : size === 'sm' ? 'w-5 h-5' : 'w-6 h-6',
          config.className,
          className,
        )}
        title={config.label}
      >
        <Icon className={cn(size === 'xs' ? 'w-2.5 h-2.5' : size === 'sm' ? 'w-3 h-3' : 'w-3.5 h-3.5')} />
      </span>
    );
  }

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
