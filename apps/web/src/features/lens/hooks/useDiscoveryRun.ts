import { useCallback, useState } from 'react';
import { lensApi } from '../api/lensApi';
import type { DiscoveryCandidate, DiscoveryRun, Platform } from '../types/discovery';

export function useDiscoveryRun() {
  const [run, setRun] = useState<DiscoveryRun | null>(null);
  const [candidates, setCandidates] = useState<DiscoveryCandidate[]>([]);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

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
      const [loadedRun, loadedCandidates] = await Promise.all([
        lensApi.search.getRun(runId),
        lensApi.search.getCandidates(runId, { limit: 50 }),
      ]);
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

  const pollRun = useCallback(async (runId: string, intervalMs = 3000, maxAttempts = 60) => {
    let attempts = 0;
    while (attempts < maxAttempts) {
      const { run: currentRun, candidates: currentCandidates } = await loadRun(runId);
      if (currentRun.status === 'completed' || currentRun.status === 'failed' || currentRun.status === 'partial') {
        return { run: currentRun, candidates: currentCandidates };
      }
      await new Promise((resolve) => setTimeout(resolve, intervalMs));
      attempts++;
    }
    throw new Error('Timeout esperando resultados');
  }, [loadRun]);

  return {
    run,
    candidates,
    isLoading,
    error,
    createRun,
    loadRun,
    pollRun,
    saveCandidate: lensApi.candidates.save,
    dismissCandidate: lensApi.candidates.dismiss,
  };
}
