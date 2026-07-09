import axios, { type AxiosInstance } from 'axios';
import { supabase } from './supabase';

const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000';

export const api: AxiosInstance = axios.create({
  baseURL: `${API_URL}/api/v1`,
  timeout: 30_000,
  headers: { 'Content-Type': 'application/json' },
});

// Attach Supabase JWT to every request
api.interceptors.request.use(async (config) => {
  const { data } = await supabase.auth.getSession();
  const token = data.session?.access_token;
  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

// Handle 401 -> redirect to login
api.interceptors.response.use(
  (r) => r,
  (error) => {
    if (error.response?.status === 401) {
      window.location.href = '/login';
    }
    return Promise.reject(error);
  },
);

// ---- Typed API methods ----

import type { Campaign, CampaignDetail, DashboardKPIs, Client, Brand, Influencer } from '@/types';

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
  create: async (data: Partial<Influencer>) =>
    (await api.post<Influencer>('/influencers', data)).data,
};

export const aiApi = {
  chat: async (data: { conversation_id?: string; message: string; context_type?: string; context_id?: string }) =>
    (await api.post('/ai/chat', data)).data,
  generate: async (data: { prompt_code: string; campaign_id: string; extra_context?: Record<string, unknown> }) =>
    (await api.post('/ai/generate', data)).data,
};