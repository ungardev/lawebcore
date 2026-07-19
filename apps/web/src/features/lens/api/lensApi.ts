import { api } from '@/lib/api';
import type {
  BriefStructured,
  DiscoveryCandidate,
  DiscoveryConversation,
  DiscoveryMetrics,
  DiscoveryRun,
  Platform,
  ToolCall,
  ToolResult,
} from '../types/discovery';

export const lensApi = {
  conversations: {
    list: async (params?: { user_id?: string; status_filter?: string; limit?: number }) => {
      const { data } = await api.get<DiscoveryConversation[]>('/lens/discovery/conversations', { params });
      return Array.isArray(data) ? data : [];
    },
    get: async (conversationId: string) => {
      const { data } = await api.get<DiscoveryConversation>(`/lens/discovery/conversations/${conversationId}`);
      return data;
    },
    create: async (initial_brief?: string) => {
      const { data } = await api.post<DiscoveryConversation>('/lens/discovery/conversations', { initial_brief });
      return data;
    },
    sendMessage: async (
      conversationId: string,
      content: string,
    ): Promise<{
      user_message: { id: string; created_at: string };
      assistant_message: {
        id: string;
        created_at: string;
        reasoning?: string | null;
        tool_calls?: ToolCall[] | null;
        tool_results?: ToolResult[] | null;
        cost_usd?: number | null;
        latency_ms?: number | null;
      };
      candidates: DiscoveryCandidate[];
      run_summary?: { total_found: number; top_score: number; platforms_queried: Platform[] };
      discovery_run_id?: string;
    }> => {
      const { data } = await api.post(`/lens/discovery/conversations/${conversationId}/messages`, { content });
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
      const { data } = await api.post<DiscoveryRun>('/lens/discovery/search', brief);
      return data;
    },
    getRun: async (runId: string) => {
      const { data } = await api.get<DiscoveryRun>(`/lens/discovery/runs/${runId}`);
      return data;
    },
    getCandidates: async (
      runId: string,
      params?: { status_filter?: string; min_score?: number; limit?: number; offset?: number },
    ) => {
      const { data } = await api.get<DiscoveryCandidate[]>(`/lens/discovery/runs/${runId}/candidates`, { params });
      return data;
    },
  },

  candidates: {
    save: async (candidateId: string) => {
      const { data } = await api.post<{ influencer_id: string; candidate_id: string }>(
        `/lens/discovery/candidates/${candidateId}/save`,
      );
      return data;
    },
    dismiss: async (candidateId: string, reason?: string) => {
      const { data } = await api.post<{ candidate_id: string; status: string }>(
        `/lens/discovery/candidates/${candidateId}/dismiss`,
        { reason },
      );
      return data;
    },
  },

  costs: async (params?: { provider?: string }) => {
    const { data } = await api.get<Array<{ provider: string; cost_usd: number; request_count: number }>>(
      '/lens/discovery/costs',
      { params },
    );
    return data;
  },

  metrics: async (): Promise<DiscoveryMetrics> => {
    const { data } = await api.get<DiscoveryMetrics>('/lens/discovery/metrics');
    return data;
  },

  enrichInfluencers: async (params?: { influencer_ids?: string[]; all_active?: boolean }) => {
    const { data } = await api.post<{
      total: number;
      enriched: number;
      failed: number;
      cost_usd: number;
      results: Array<{
        influencer_id: string;
        handle: string;
        success: boolean;
        followers: number | null;
        engagement_rate: number | null;
        error: string | null;
      }>;
    }>('/lens/discovery/enrich-influencers', params ?? {});
    return data;
  },

  preloadDemo: async () => {
    const { data } = await api.post<{ success: boolean; message: string; conversations: number }>(
      '/admin/preload-demo',
      {},
    );
    return data;
  },
};
