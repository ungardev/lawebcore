import { INFLUENCER_TIERS } from '@/lib/utils';

interface TierSlidersProps {
  postsPerTier: Record<string, number>;
  onChange: (tier: string, value: number) => void;
}

const TIER_INFO: Record<string, { label: string; range: string }> = {
  NANO: { label: 'Nano', range: '< 10K seg.' },
  MICRO: { label: 'Micro', range: '10K–100K' },
  MID: { label: 'Mid', range: '100K–500K' },
  MACRO: { label: 'Macro', range: '> 500K' },
  MEGA: { label: 'Mega', range: '> 1M' },
  MIX: { label: 'Mix', range: 'Varios' },
};

export function TierSliders({ postsPerTier, onChange }: TierSlidersProps) {
  const activeTiers = INFLUENCER_TIERS.filter((t) => t !== 'MIX');

  return (
    <div className="space-y-3">
      {activeTiers.map((tier) => {
        const info = TIER_INFO[tier] || { label: tier, range: '' };
        const value = postsPerTier[tier] ?? 0;
        const max = tier === 'NANO' ? 200 : tier === 'MICRO' ? 50 : 20;

        return (
          <div key={tier} className="flex items-center gap-3">
            <div className="w-24 flex-shrink-0">
              <span className="text-sm font-medium">{info.label}</span>
              <p className="text-xs text-muted-foreground">{info.range}</p>
            </div>
            <input
              type="range"
              min={0}
              max={max}
              value={value}
              onChange={(e) => onChange(tier, parseInt(e.target.value))}
              className="flex-1 accent-primary"
            />
            <div className="w-12 text-right">
              <span className="text-sm font-bold font-mono">{value}</span>
            </div>
          </div>
        );
      })}
    </div>
  );
}
