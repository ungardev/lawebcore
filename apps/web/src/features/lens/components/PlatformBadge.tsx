import type { Platform } from '../types/discovery';
import { cn } from '@/lib/utils';

const platformConfig: Record<Platform, { label: string; className: string }> = {
  instagram: { label: 'Instagram', className: 'bg-gradient-to-tr from-purple-500 via-pink-500 to-orange-400 text-white' },
  tiktok: { label: 'TikTok', className: 'bg-black text-white' },
  youtube: { label: 'YouTube', className: 'bg-red-600 text-white' },
  x: { label: 'X', className: 'bg-black text-white' },
  facebook: { label: 'Facebook', className: 'bg-blue-600 text-white' },
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
        'inline-flex items-center rounded-md font-medium',
        size === 'xs' ? 'px-1 py-px text-[9px]' : size === 'sm' ? 'px-1.5 py-0.5 text-[10px]' : 'px-2 py-1 text-xs',
        config.className,
        className,
      )}
    >
      {config.label}
    </span>
  );
}
