import { useQuery } from '@tanstack/react-query'
import { useEffect, useRef, useState } from 'react'
import { lensApi } from '../api/lensApi'
import type { DiscoveryRunStatus, RunProgress } from '../types/discovery'

/**
 * Estados TERMINALES que el worker puede emitir (source of truth:
 * packages/shared-core/shared_core/observability.py::RunStatus).
 *
 * FIX B-FE-7/B-FE-15 (04-sep-2026): el hook solo detenía el polling en
 * 'completed' | 'partial' | 'failed' | 'cancelled' — estados legacy que el
 * backend JAMÁS emite (salvo 'failed'). Un run exitoso termina en
 * 'delivered' → el polling giraba infinito y los candidatos jamás se
 * fetcheaban: la UI nunca mostraba resultados aunque el pipeline entregara.
 *
 * Test de contrato FE↔BE: apps/api/tests/test_status_enum_parity.py
 */
export const TERMINAL_RUN_STATUSES: DiscoveryRunStatus[] = [
  'delivered',
  'degraded',
  'empty',
  'inconsistent',
  'aborted_budget',
  'failed',
]

/** Estados terminales con candidatos que vale la pena fetchar. */
export const CANDIDATE_RUN_STATUSES: DiscoveryRunStatus[] = ['delivered', 'degraded']

export function useRunPolling(runId: string | null) {
  const [candidates, setCandidates] = useState<import('../types/discovery').DiscoveryCandidate[]>([])
  const [isPolling, setIsPolling] = useState(false)
  const [progress, setProgress] = useState<RunProgress | null>(null)
  const [runStatus, setRunStatus] = useState<DiscoveryRunStatus | null>(null)
  const generationRef = useRef(0)

  useEffect(() => {
    if (!runId) {
      setCandidates([])
      setIsPolling(false)
      setProgress(null)
      setRunStatus(null)
      return
    }
    const gen = ++generationRef.current
    setIsPolling(true)
    setCandidates([])
    setProgress(null)
    setRunStatus(null)

    return () => {
      if (generationRef.current === gen) {
        generationRef.current = gen + 1
        setIsPolling(false)
      }
    }
  }, [runId])

  const query = useQuery({
    queryKey: ['discovery-run', runId],
    queryFn: () => lensApi.search.getRun(runId!),
    enabled: !!runId,
    refetchInterval: (query) => {
      const status = query.state.data?.status as DiscoveryRunStatus | undefined
      if (status && TERMINAL_RUN_STATUSES.includes(status)) return false
      return 2500
    },
    refetchIntervalInBackground: false,
  })

  useEffect(() => {
    if (!query.data) return
    const gen = generationRef.current
    const status = query.data.status as DiscoveryRunStatus
    const metadata = query.data.metadata as Record<string, unknown> | undefined

    if (gen === generationRef.current) {
      setRunStatus(status)
    }

    if (metadata) {
      const runProgress: RunProgress = {
        current_step: (metadata.current_step as string) || 'running',
        completed_steps: (metadata.completed_steps as string[]) || [],
        current_hashtag: metadata.current_hashtag as string | undefined,
        candidates_found: (metadata.candidates_found as number) || 0,
      }
      if (gen === generationRef.current) {
        setProgress(runProgress)
      }
    }

    if (CANDIDATE_RUN_STATUSES.includes(status)) {
      lensApi.search.getCandidates(runId!, { limit: 20 })
        .then((cands) => {
          if (gen === generationRef.current) {
            setCandidates(cands)
            setIsPolling(false)
          }
        })
        .catch(() => {
          if (gen === generationRef.current) setIsPolling(false)
        })
    } else if (TERMINAL_RUN_STATUSES.includes(status)) {
      // empty / aborted_budget / failed / inconsistent: sin candidatos que
      // fetchar. El worker deja un mensaje asistente con la causa real; el
      // hook de conversación recarga el chat al detectar el fin del polling.
      if (gen === generationRef.current) setIsPolling(false)
    }
  }, [query.data, runId])

  const stopPolling = () => {
    ++generationRef.current
    setIsPolling(false)
  }

  return { candidates, isPolling, stopPolling, progress, runStatus, runError: query.data?.error ?? null }
}
