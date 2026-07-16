import { api } from '@/lib/api';
import type {
  BriefStructured,
  DiscoveryCandidate,
  DiscoveryConversation,
  DiscoveryMetrics,
  DiscoveryRun,
  Platform,
} from '../types/discovery';

export const discoveryApi = {
  conversations: {
    list: async (params?: { user_id?: string; status_filter?: string; limit?: number }) => {
      const { data } = await api.get<DiscoveryConversation[]>('/discovery/conversations', { params });
      return data;
    },
    get: async (conversationId: string) => {
      const { data } = await api.get<DiscoveryConversation>(`/discovery/conversations/${conversationId}`);
      return data;
    },
    create: async (initial_brief?: string) => {
      const { data } = await api.post<DiscoveryConversation>('/discovery/conversations', { initial_brief });
      return data;
    },
    sendMessage: async (
      conversationId: string,
      content: string,
    ): Promise<{
      user_message: { id: string; created_at: string };
      assistant_message: { id: string; created_at: string };
      candidates: DiscoveryCandidate[];
      run_summary?: { total_found: number; top_score: number; platforms_queried: Platform[] };
      discovery_run_id?: string;
    }> => {
      const { data } = await api.post(`/discovery/conversations/${conversationId}/messages`, { content });
      return data;
    },
  },

  search: {
    createRun: async (brief: {
      product_name?: string;
      brand_id?: string;
      industry?: string;
      niches?: string[];
      audience_gender?: string;
      audience_age_min?: number;
      audience_age_max?: number;
      audience_countries?: string[];
      audience_cities?: string[];
      budget_usd?: number;
      tone?: string[];
      platforms?: Platform[];
      max_candidates?: number;
    }) => {
      const { data } = await api.post<DiscoveryRun>('/discovery/search', brief);
      return data;
    },
    getRun: async (runId: string) => {
      const { data } = await api.get<DiscoveryRun>(`/discovery/runs/${runId}`);
      return data;
    },
    getCandidates: async (
      runId: string,
      params?: { status_filter?: string; min_score?: number; limit?: number; offset?: number },
    ) => {
      const { data } = await api.get<DiscoveryCandidate[]>(`/discovery/runs/${runId}/candidates`, { params });
      return data;
    },
  },

  candidates: {
    save: async (candidateId: string) => {
      const { data } = await api.post<{ influencer_id: string; candidate_id: string }>(
        `/discovery/candidates/${candidateId}/save`,
      );
      return data;
    },
    dismiss: async (candidateId: string, reason?: string) => {
      const { data } = await api.post<{ candidate_id: string; status: string }>(
        `/discovery/candidates/${candidateId}/dismiss`,
        { reason },
      );
      return data;
    },
  },

  costs: async (params?: { provider?: string }) => {
    const { data } = await api.get<Array<{ provider: string; cost_usd: number; request_count: number }>>(
      '/discovery/costs',
      { params },
    );
    return data;
  },

  metrics: async (): Promise<DiscoveryMetrics> => {
    const { data } = await api.get<DiscoveryMetrics>('/discovery/metrics');
    return data;
  },
};
