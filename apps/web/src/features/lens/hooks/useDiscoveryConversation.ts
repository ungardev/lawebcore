import { useCallback, useEffect, useRef, useState } from 'react';
import { lensApi } from '../api/lensApi';
import { CANDIDATE_RUN_STATUSES, useRunPolling } from './useRunPolling';
import type { BriefStructured, ChatTurn, DiscoveryCandidate, DiscoveryConversation, DiscoveryMessage } from '../types/discovery';

export function useDiscoveryConversation() {
  const [conversation, setConversation] = useState<DiscoveryConversation | null>(null);
  const [turns, setTurns] = useState<ChatTurn[]>([]);
  const [isLoading, setIsLoading] = useState(false);
  const [isCreating, setIsCreating] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [pendingBrief, setPendingBrief] = useState<BriefStructured | null>(null);
  const [pollingRunId, setPollingRunId] = useState<string | null>(null);
  const { candidates: pollingCandidates, isPolling, progress: pollingProgress } = useRunPolling(pollingRunId);
  const wasPollingRef = useRef(false);

  useEffect(() => {
    if (!pollingCandidates.length) return;
    setTurns((prev) => {
      const lastIdx = prev.length - 1;
      if (lastIdx < 0) return prev;
      const last = prev[lastIdx];
      if (last.role !== 'assistant') return prev;
      return prev.map((t, i) =>
        i === lastIdx ? { ...t, candidates: pollingCandidates, isLoading: false } : t,
      );
    });
  }, [pollingCandidates]);

  useEffect(() => {
    if (!isPolling) return;
    setTurns((prev) => {
      const lastIdx = prev.length - 1;
      if (lastIdx < 0) return prev;
      const last = prev[lastIdx];
      if (last.role !== 'assistant') return prev;
      if (last.candidates && last.candidates.length > 0) return prev;
      return prev.map((t, i) =>
        i === lastIdx ? { ...t, isLoading: true } : t,
      );
    });
  }, [isPolling]);

  useEffect(() => {
    if (!pollingProgress) return;
    setTurns((prev) => {
      const lastIdx = prev.length - 1;
      if (lastIdx < 0) return prev;
      const last = prev[lastIdx];
      if (last.role !== 'assistant') return prev;
      return prev.map((t, i) =>
        i === lastIdx ? { ...t, progress: pollingProgress, isLoading: true } : t,
      );
    });
  }, [pollingProgress]);

  // FIX B-FE-7 (04-sep-2026): cuando el polling termina SIN candidatos
  // (empty / aborted_budget / failed / inconsistent), el worker dejó un
  // mensaje asistente con la causa real — recargar el chat para mostrarlo
  // en vez de dejar el spinner congelado.
  useEffect(() => {
    const wasPolling = wasPollingRef.current;
    wasPollingRef.current = isPolling;
    if (wasPolling && !isPolling && conversation && pollingCandidates.length === 0) {
      loadConversation(conversation.id).catch(() => {});
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [isPolling, pollingCandidates.length, conversation]);

  const startConversation = useCallback(async (initialBrief?: string) => {
    if (isCreating) throw new Error('Conversation creation already in progress');
    setIsCreating(true);
    setIsLoading(true);
    setError(null);
    try {
      const conv = await lensApi.conversations.create(initialBrief);
      setConversation(conv);
      setTurns([]);
      setPendingBrief(null);
      return conv;
    } catch (e) {
      setError((e as Error).message);
      throw e;
    } finally {
      setIsLoading(false);
      setIsCreating(false);
    }
  }, [isCreating]);

  /**
   * FIX UX wizard (04-sep-2026): el botón "Buscar candidatos" del BriefWizard
   * promete un click, pero el flujo del orquestador exige un segundo turno
   * afirmativo (START → parse → "¿correcto?" → BRIEF → lanzamiento). Esta
   * función crea la conversación con el brief y envía la confirmación
   * inmediatamente — UX de un click sin tocar el backend. Además ponia el
   * run en polling y recarga los mensajes para mostrar ambos turnos.
   */
  const startWizardSearch = useCallback(async (brief: Partial<BriefStructured>) => {
    if (isCreating) throw new Error('Conversation creation already in progress');
    setIsCreating(true);
    setIsLoading(true);
    setError(null);
    try {
      const briefJson = JSON.stringify(brief, null, 2);
      const briefMessage = `Brief: ${briefJson}\n\nBuscar ahora.`;
      const conv = await lensApi.conversations.create(briefMessage);
      setConversation(conv);
      setTurns([]);
      setPendingBrief(null);

      const result = await lensApi.conversations.sendMessage(
        conv.id,
        'Confirmo el brief. Buscar ahora.',
      );
      if (result.discovery_run_id) {
        setPollingRunId(result.discovery_run_id);
      }

      await loadConversation(conv.id);
      return conv;
    } catch (e) {
      setError((e as Error).message);
      throw e;
    } finally {
      setIsLoading(false);
      setIsCreating(false);
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [isCreating]);

  const loadConversation = useCallback(async (conversationId: string) => {
    setIsLoading(true);
    setError(null);
    try {
      const conv = await lensApi.conversations.get(conversationId);
      setConversation(conv);

      let candidates: DiscoveryCandidate[] | null = null;

      if (conv.discovery_run_id) {
        try {
          const run = await lensApi.search.getRun(conv.discovery_run_id);
          // FIX B-FE-7: los estados que el backend realmente emite con
          // candidatos son 'delivered'/'degraded' (antes: completed/partial/
          // explored — legacy que jamás llegó, por eso recargar la página
          // tampoco mostraba candidatos).
          if (CANDIDATE_RUN_STATUSES.includes(run.status)) {
            candidates = await lensApi.search.getCandidates(conv.discovery_run_id, { limit: 20 });
          }
        } catch {
          // run not accessible or candidates failed
        }
      }

      const mappedTurns: ChatTurn[] = (conv.messages ?? []).map((m: DiscoveryMessage) => {
        const isBriefJson = m.role === 'user' && typeof m.content === 'string' && m.content.startsWith('Brief:');
        return {
          id: m.id,
          role: m.role as 'user' | 'assistant',
          content: m.content,
          reasoning: m.reasoning ?? null,
          tool_calls: Array.isArray(m.tool_calls) ? (m.tool_calls as unknown as ChatTurn['tool_calls']) : null,
          tool_results: Array.isArray(m.tool_results) ? (m.tool_results as unknown as ChatTurn['tool_results']) : null,
          cost_usd: m.cost_usd ?? null,
          latency_ms: m.latency_ms ?? null,
          isLoading: false,
          brief_hidden: isBriefJson ? true : undefined,
        };
      });

      if (candidates && candidates.length > 0) {
        const lastAssistantIdx = [...mappedTurns].reverse().findIndex((t) => t.role === 'assistant');
        if (lastAssistantIdx !== -1) {
          const actualIdx = mappedTurns.length - 1 - lastAssistantIdx;
          mappedTurns[actualIdx] = { ...mappedTurns[actualIdx], candidates };
        }
      }

      setTurns(mappedTurns);
      setPendingBrief(null);
    } catch (e) {
      setError((e as Error).message);
      throw e;
    } finally {
      setIsLoading(false);
    }
  }, []);

  const sendMessage = useCallback(async (content: string) => {
    if (!conversation) return;

    const userTurn: ChatTurn = { id: `tmp-${Date.now()}`, role: 'user', content, isLoading: false };
    setTurns((prev) => [...prev, userTurn]);

    const loadingTurn: ChatTurn = { id: 'loading', role: 'assistant', content: '', isLoading: true };
    setTurns((prev) => [...prev, loadingTurn]);

    setIsLoading(true);
    setError(null);

    try {
      const result = await lensApi.conversations.sendMessage(conversation.id, content);

      if (result.discovery_run_id) {
        setPollingRunId(result.discovery_run_id);
      } else if (result.candidates && result.candidates.length > 0) {
        const assistantMsgId = result.assistant_message?.id;
        const latestMsg = await lensApi.conversations.get(conversation.id);
        const latestAssistantMsg = (latestMsg.messages ?? [])
          .filter((m: { role: string }) => m.role === 'assistant')
          .pop() as { id: string; content: string } | undefined;
        setTurns((prev) => {
          const filtered = prev.filter((t) => t.id !== 'loading');
          const assistantTurn: ChatTurn = {
            id: assistantMsgId || `assistant-${Date.now()}`,
            role: 'assistant',
            content: latestAssistantMsg?.content || '',
            candidates: result.candidates,
            isLoading: false,
          };
          return [...filtered, assistantTurn];
        });
      } else {
        await loadConversation(conversation.id);
      }

      return result;
    } catch (e) {
      setError((e as Error).message);
      setTurns((prev) => {
        const filtered = prev.filter((t) => t.id !== 'loading');
        return [
          ...filtered,
          {
            id: `error-${Date.now()}`,
            role: 'assistant',
            content: '',
            isError: true,
            isLoading: false,
          },
        ];
      });
      throw e;
    } finally {
      setIsLoading(false);
    }
  }, [conversation, loadConversation]);

  const confirmBrief = useCallback(async () => {
    if (!conversation || !pendingBrief) return;
    setIsLoading(true);
    try {
      await sendMessage(
        `Confirmo el brief: ${JSON.stringify(pendingBrief)}. Buscar ahora.`,
      );
      setPendingBrief(null);
    } finally {
      setIsLoading(false);
    }
  }, [conversation, pendingBrief, sendMessage]);

  const saveCandidate = useCallback(async (candidateId: string) => {
    await lensApi.candidates.save(candidateId);
  }, []);

  const dismissCandidate = useCallback(async (candidateId: string) => {
    await lensApi.candidates.dismiss(candidateId);
    setTurns((prev) =>
      prev.map((t) =>
        Array.isArray(t.candidates)
          ? { ...t, candidates: t.candidates.filter((c) => c.id !== candidateId) }
          : t,
      ),
    );
  }, []);

  const updatePendingBrief = useCallback((brief: BriefStructured | null) => {
    setPendingBrief(brief);
  }, []);

  const resetConversation = useCallback(() => {
    setConversation(null);
    setTurns([]);
    setPendingBrief(null);
    setError(null);
  }, []);

  return {
    conversation,
    turns,
    isLoading,
    isCreating,
    error,
    pendingBrief,
    setPendingBrief: updatePendingBrief,
    startConversation,
    startWizardSearch,
    loadConversation,
    sendMessage,
    confirmBrief,
    saveCandidate,
    dismissCandidate,
    resetConversation,
  };
}
