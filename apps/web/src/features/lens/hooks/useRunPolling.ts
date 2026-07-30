import { useQuery } from '@tanstack/react-query'
import { useEffect, useRef, useState } from 'react'
import { lensApi } from '../api/lensApi'

export function useRunPolling(runId: string | null) {
  const [candidates, setCandidates] = useState<import('../types/discovery').DiscoveryCandidate[]>([])
  const [isPolling, setIsPolling] = useState(false)
  const generationRef = useRef(0)

  useEffect(() => {
    if (!runId) {
      setCandidates([])
      setIsPolling(false)
      return
    }
    const gen = ++generationRef.current
    setIsPolling(true)
    setCandidates([])

    return () => {
      ++generationRef.current
      setIsPolling(false)
    }
  }, [runId])

  const query = useQuery({
    queryKey: ['discovery-run', runId],
    queryFn: () => lensApi.search.getRun(runId!),
    enabled: !!runId,
    refetchInterval: (query) => {
      const status = query.state.data?.status as string | undefined
      if (status === 'completed' || status === 'partial' || status === 'failed' || status === 'cancelled') return false
      return 2500
    },
    refetchIntervalInBackground: false,
  })

  useEffect(() => {
    if (!query.data) return
    const gen = generationRef.current
    const status = query.data.status as string

    if (status === 'completed' || status === 'partial') {
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
    } else if (status === 'failed') {
      if (gen === generationRef.current) setIsPolling(false)
    }
  }, [query.data, runId])

  const stopPolling = () => {
    ++generationRef.current
    setIsPolling(false)
  }

  return { candidates, isPolling, stopPolling }
}
