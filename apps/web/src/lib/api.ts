import axios, { type AxiosInstance } from 'axios';
import { supabase } from './supabase';

const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000';

export const api: AxiosInstance = axios.create({
  baseURL: `${API_URL}/api/v1`,
  timeout: 30_000,
  headers: { 'Content-Type': 'application/json' },
});

api.interceptors.request.use(async (config) => {
  const { data } = await supabase.auth.getSession();
  const token = data.session?.access_token;
  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

api.interceptors.response.use(
  (r) => r,
  async (error) => {
    if (error.response?.status === 401) {
      const { data } = await supabase.auth.getSession();
      if (!data.session) {
        window.location.href = '/login';
      }
    }
    return Promise.reject(error);
  },
);

import type {
  Campaign,
  CampaignDetail,
  DashboardKPIs,
  Client,
  Brand,
  Influencer,
} from '@/types';
import type { Publicacion, ProjectionCalculateResponse as ProjResp, InfluencerScore } from '@/types/piar';

export const dashboardApi = {
  summary: async () => (await api.get<DashboardKPIs>('/dashboard/summary')).data,
  byStatus: async () => (await api.get('/dashboard/by-status')).data,
  topClients: async () => (await api.get('/dashboard/top-clients')).data,
};

export const campaignsApi = {
  list: async (params?: Record<string, string | number | boolean | undefined>) =>
    (await api.get<Campaign[]>('/campaigns', { params })).data,
  kanban: async (params?: Record<string, string | number | undefined>) =>
    (await api.get('/campaigns/kanban', { params })).data,
  get: async (id: string) => (await api.get<CampaignDetail>(`/campaigns/${id}`)).data,
  create: async (data: Partial<Campaign>) => (await api.post<Campaign>('/campaigns', data)).data,
  update: async (id: string, data: Partial<Campaign>) =>
    (await api.patch<Campaign>(`/campaigns/${id}`, data)).data,
  changeStatus: async (id: string, to_status: string, reason?: string) =>
    (await api.post<Campaign>(`/campaigns/${id}/status`, { to_status, reason })).data,
  delete: async (id: string) => api.delete(`/campaigns/${id}`),
};

export const clientsApi = {
  list: async (params?: Record<string, string | boolean | undefined>) =>
    (await api.get<Client[]>('/clients', { params })).data,
  create: async (data: Partial<Client>) => (await api.post<Client>('/clients', data)).data,
};

export const brandsApi = {
  list: async (params?: Record<string, string | boolean | undefined>) =>
    (await api.get<Brand[]>('/brands', { params })).data,
  create: async (data: Partial<Brand>) => (await api.post<Brand>('/brands', data)).data,
};

export const influencersApi = {
  list: async (params?: Record<string, string | number | undefined>) =>
    (await api.get<Influencer[]>('/influencers', { params })).data,
  listWithScores: async (params?: Record<string, string | number | undefined>) =>
    (await api.get<Array<Influencer & { score: InfluencerScore }>>('/scoring/influencers', { params })).data,
  getScore: async (influencerId: string, mode?: string) =>
    (await api.get<InfluencerScore>(`/scoring/influencers/${influencerId}/score`, { params: { mode } })).data,
  create: async (data: Partial<Influencer>) =>
    (await api.post<Influencer>('/influencers', data)).data,
};

export const publicacionesApi = {
  list: async (params?: { campaign_id?: string; influencer_id?: string; limit?: number }) => {
    const { data: res } = await api.get<Publicacion[]>('/publicaciones', { params: params as any });
    return res;
  },
  stats: async (campaignId: string) => {
    const { data } = await api.get(`/publicaciones/stats/${campaignId}`);
    return data;
  },
};

export const projectionsApi = {
  calculate: async (
    brand_id: string,
    posts_per_tier: Record<string, number>,
  ): Promise<ProjResp> => {
    const { data } = await api.post<ProjResp>('/projections/calculate', {
      brand_id,
      posts_per_tier,
    });
    return data;
  },
};

export const aiApi = {
  chat: async (data: { conversation_id?: string; message: string; context_type?: string; context_id?: string }) =>
    (await api.post('/ai/chat', data)).data,
  generate: async (data: { prompt_code: string; campaign_id: string; extra_context?: Record<string, unknown> }) =>
    (await api.post('/ai/generate', data)).data,
};

export interface ImportReport {
  inserted: number;
  updated: number;
  skipped: number;
  errors: Array<{ row: number; reason: string; data?: Record<string, unknown> }>;
  total_rows: number;
}

export const importsApi = {
  uploadCsv: async (formData: FormData): Promise<ImportReport> => {
    const { data } = await api.post<ImportReport>('/imports/csv', formData, {
      headers: { 'Content-Type': 'multipart/form-data' },
    });
    return data;
  },
  uploadJson: async (payload: unknown[], userEmail?: string): Promise<ImportReport> => {
    const { data } = await api.post<ImportReport>('/imports/json', payload, {
      headers: { 'X-User-Email': userEmail || '' },
    });
    return data;
  },
  getTemplate: async (): Promise<Blob> => {
    const response = await api.get('/imports/template', { responseType: 'blob' });
    return response.data;
  },
};
