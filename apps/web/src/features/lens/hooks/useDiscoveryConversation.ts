import { useCallback, useRef, useState } from 'react';
import { lensApi } from '../api/lensApi';
import type { BriefStructured, ChatTurn, DiscoveryCandidate, DiscoveryConversation, DiscoveryMessage } from '../types/discovery';

export function useDiscoveryConversation() {
  const [conversation, setConversation] = useState<DiscoveryConversation | null>(null);
  const [turns, setTurns] = useState<ChatTurn[]>([]);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [pendingBrief, setPendingBrief] = useState<BriefStructured | null>(null);
  const abortRef = useRef<AbortController | null>(null);

  const startConversation = useCallback(async (initialBrief?: string) => {
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
    }
  }, []);

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
          if ((run.status as string) === 'completed' || (run.status as string) === 'partial') {
            candidates = await lensApi.search.getCandidates(conv.discovery_run_id, { limit: 20 });
          }
        } catch {
          // run not accessible or candidates failed
        }
      }

      const mappedTurns: ChatTurn[] = (conv.messages ?? []).map((m: DiscoveryMessage) => ({
        id: m.id,
        role: m.role as 'user' | 'assistant',
        content: m.content,
        reasoning: m.reasoning ?? null,
        tool_calls: (m.tool_calls as ChatTurn['tool_calls']) ?? null,
        tool_results: (m.tool_results as ChatTurn['tool_results']) ?? null,
        cost_usd: m.cost_usd ?? null,
        latency_ms: m.latency_ms ?? null,
        isLoading: false,
      }));

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
        pollRunStatus(result.discovery_run_id, conversation.id);
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
  }, [conversation]);

  async function pollRunStatus(runId: string, conversationId: string) {
    const maxAttempts = 40;
    const interval = 3000;

    for (let attempt = 0; attempt < maxAttempts; attempt++) {
      await new Promise((r) => setTimeout(r, interval));
      try {
        const run = await lensApi.search.getRun(runId);
        const metadata = (run.metadata || {}) as Record<string, unknown>;
        const progress = {
          current_step: (metadata.current_step as string) || "running",
          completed_steps: (metadata.completed_steps as string[]) || [],
          current_hashtag: metadata.current_hashtag as string | undefined,
          candidates_found: (metadata.candidates_found as number) || 0,
          platforms: metadata.platforms as string[] | undefined,
        };

        if ((run.status as string) === 'completed' || (run.status as string) === 'failed' || (run.status as string) === 'partial') {
          if ((run.status as string) === 'completed' || (run.status as string) === 'partial') {
            try {
              const candidates = await lensApi.search.getCandidates(runId, { limit: 20 });
              setTurns((prev) => {
                const lastIdx = prev.length - 1;
                if (lastIdx < 0) return prev;
                const last = prev[lastIdx];
                if (last.role !== 'assistant') return prev;
                return prev.map((t, i) =>
                  i === lastIdx ? { ...t, candidates, isLoading: false } : t,
                );
              });
            } catch {
              setTurns((prev) => {
                const lastIdx = prev.length - 1;
                if (lastIdx < 0) return prev;
                return prev.map((t, i) =>
                  i === lastIdx ? { ...t, isLoading: false } : t,
                );
              });
            }
          } else {
            setTurns((prev) => {
              const lastIdx = prev.length - 1;
              if (lastIdx < 0) return prev;
              return prev.map((t, i) =>
                i === lastIdx ? { ...t, isLoading: false } : t,
              );
            });
          }
          return;
        }

        setTurns((prev) => {
          const lastIdx = prev.length - 1;
          if (lastIdx < 0) return prev;
          const last = prev[lastIdx];
          if (last.role !== 'assistant') return prev;
          if (last.candidates && last.candidates.length > 0) return prev;
          return prev.map((t, i) =>
            i === lastIdx ? { ...t, progress, isLoading: true } : t,
          );
        });
      } catch {
        // keep polling
      }
    }
  }

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
        t.candidates
          ? { ...t, candidates: t.candidates.filter((c) => c.id !== candidateId) }
          : t,
      ),
    );
  }, []);

  return {
    conversation,
    turns,
    isLoading,
    error,
    pendingBrief,
    setPendingBrief,
    startConversation,
    loadConversation,
    sendMessage,
    confirmBrief,
    saveCandidate,
    dismissCandidate,
  };
}
