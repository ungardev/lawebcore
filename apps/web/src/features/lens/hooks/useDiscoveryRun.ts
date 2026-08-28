import { useCallback, useRef, useState } from 'react';
import { lensApi } from '../api/lensApi';
import type { DiscoveryCandidate, DiscoveryRun, Platform } from '../types/discovery';

/**
 * Estados en los que un run ya terminó y el polling debe detenerse.
 * Incluye los 6 valores añadidos por el Hito 30 (migración 110).
 * Debe mantenerse en sincronía con TERMINAL_STATUSES de LensSearchPage.tsx.
 */
const POLL_TERMINAL_STATUSES: readonly string[] = [
  'completed', 'failed', 'partial', 'explored',
  'delivered', 'degraded', 'empty', 'inconsistent', 'aborted_budget', 'cancelled',
];

export function useDiscoveryRun() {
  const [run, setRun] = useState<DiscoveryRun | null>(null);
  const [candidates, setCandidates] = useState<DiscoveryCandidate[]>([]);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const cancelledRef = useRef(false);

  const createRun = useCallback(async (brief: Parameters<typeof lensApi.search.createRun>[0]) => {
    setIsLoading(true);
    setError(null);
    try {
      const newRun = await lensApi.search.createRun(brief);
      setRun(newRun);
      return newRun;
    } catch (e) {
      setError((e as Error).message);
      throw e;
    } finally {
      setIsLoading(false);
    }
  }, []);

  const loadRun = useCallback(async (runId: string) => {
    setIsLoading(true);
    setError(null);
    try {
      const loadedRun = await lensApi.search.getRun(runId);
      const shouldLoadCandidates = ['completed', 'partial', 'explored'].includes(loadedRun.status);
      const loadedCandidates = shouldLoadCandidates
        ? await lensApi.search.getCandidates(runId, { limit: 50 })
        : [];
      setRun(loadedRun);
      setCandidates(loadedCandidates);
      return { run: loadedRun, candidates: loadedCandidates };
    } catch (e) {
      setError((e as Error).message);
      throw e;
    } finally {
      setIsLoading(false);
    }
  }, []);

  const pollRun = useCallback(async (runId: string, intervalMs = 3000, maxAttempts = 200) => {
    cancelledRef.current = false;
    let attempts = 0;
    while (attempts < maxAttempts) {
      if (cancelledRef.current) {
        return { run: null, candidates: [] };
      }
      const { run: currentRun, candidates: currentCandidates } = await loadRun(runId);
      if (cancelledRef.current) {
        return { run: null, candidates: [] };
      }
      if (POLL_TERMINAL_STATUSES.includes(currentRun.status)) {
        return { run: currentRun, candidates: currentCandidates };
      }
      await new Promise((resolve) => setTimeout(resolve, intervalMs));
      attempts++;
    }
    throw new Error('Timeout esperando resultados');
  }, [loadRun]);

  const cancelPoll = useCallback(() => {
    cancelledRef.current = true;
    setRun((previous) => previous ? { ...previous, status: 'cancelled' } : previous);
    setIsLoading(false);
  }, []);

  return {
    run,
    candidates,
    isLoading,
    error,
    createRun,
    loadRun,
    pollRun,
    cancelPoll,
    saveCandidate: lensApi.candidates.save,
    dismissCandidate: lensApi.candidates.dismiss,
  };
}
