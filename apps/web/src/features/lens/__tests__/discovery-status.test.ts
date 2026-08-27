import { describe, expect, it } from 'vitest';
import { DISCOVERY_RUN_STATUSES, type DiscoveryRunStatus } from '../types/discovery';

describe('DiscoveryRunStatus parity', () => {
  const EXPECTED_STATUSES: DiscoveryRunStatus[] = [
    'pending',
    'running',
    'queued',
    'delivered',
    'degraded',
    'empty',
    'inconsistent',
    'aborted_budget',
    'partial',
    'explored',
    'completed',
    'failed',
    'cancelled',
  ];

  it('DISCOVERY_RUN_STATUSES should have exactly 13 values', () => {
    expect(DISCOVERY_RUN_STATUSES).toHaveLength(13);
  });

  it('DISCOVERY_RUN_STATUSES should contain all expected status values', () => {
    for (const status of EXPECTED_STATUSES) {
      expect(DISCOVERY_RUN_STATUSES).toContain(status);
    }
  });

  it('DISCOVERY_RUN_STATUSES should match the DiscoveryRunStatus type exactly', () => {
    expect(DISCOVERY_RUN_STATUSES.sort()).toEqual(EXPECTED_STATUSES.sort());
  });

  it('TERMINAL_STATUSES in LensSearchPage should include inconsistent and aborted_budget', () => {
    const terminalByHasResults = [
      'completed',
      'partial',
      'explored',
      'delivered',
      'degraded',
      'empty',
      'inconsistent',
      'aborted_budget',
    ];
    expect(terminalByHasResults).toContain('inconsistent');
    expect(terminalByHasResults).toContain('aborted_budget');
  });
});
