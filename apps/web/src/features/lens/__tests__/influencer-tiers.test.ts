import { describe, expect, it } from 'vitest';
import { INFLUENCER_SUBTIERS } from '../../../lib/utils';

describe('INFLUENCER_SUBTIERS parity', () => {
  const EXPECTED_SUBTIERS = [
    'NANO_BAJO',
    'NANO_ALTO',
    'MICRO_BAJO',
    'MICRO_MEDIO',
    'MICRO_ALTO',
    'MID_BAJO',
    'MID_ALTO',
    'MACRO_BAJO',
    'MACRO_ALTO',
  ] as const;

  it('INFLUENCER_SUBTIERS should have exactly 9 sub-tier values', () => {
    expect(INFLUENCER_SUBTIERS).toHaveLength(9);
  });

  it('INFLUENCER_SUBTIERS should contain all expected sub-tier names', () => {
    for (const tier of EXPECTED_SUBTIERS) {
      expect(INFLUENCER_SUBTIERS).toContain(tier);
    }
  });

  it('INFLUENCER_SUBTIERS should match TIER_BENCHMARKS keys in result_ranker.py', () => {
    const expectedTiers = new Set(EXPECTED_SUBTIERS.map((t) => t));
    const actualTiers = new Set(INFLUENCER_SUBTIERS);
    expect(actualTiers).toEqual(expectedTiers);
  });
});
