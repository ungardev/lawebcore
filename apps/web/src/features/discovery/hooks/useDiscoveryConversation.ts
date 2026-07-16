import { useCallback, useRef, useState } from 'react';
import { discoveryApi } from '../api/discoveryApi';
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
      const conv = await discoveryApi.conversations.create(initialBrief);
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
      const conv = await discoveryApi.conversations.get(conversationId);
      setConversation(conv);

      const mappedTurns: ChatTurn[] = (conv.messages ?? []).map((m: DiscoveryMessage) => ({
        id: m.id,
        role: m.role as 'user' | 'assistant',
        content: m.content,
        isLoading: false,
      }));
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
      const result = await discoveryApi.conversations.sendMessage(conversation.id, content);
      await loadConversation(conversation.id);
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
    await discoveryApi.candidates.save(candidateId);
  }, []);

  const dismissCandidate = useCallback(async (candidateId: string) => {
    await discoveryApi.candidates.dismiss(candidateId);
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
