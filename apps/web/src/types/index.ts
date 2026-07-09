// Shared TypeScript types

export interface User {
  id: string;
  email: string;
  full_name: string;
  avatar_url?: string;
  job_title?: string;
  primary_bu_id?: string;
  status: string;
  last_login_at?: string;
  created_at: string;
}

export interface Client {
  id: string;
  code: string;
  name: string;
  legal_name?: string;
  industry?: string;
  website?: string;
  logo_url?: string;
  is_active: boolean;
  created_at: string;
}

export interface Brand {
  id: string;
  client_id: string;
  code: string;
  name: string;
  category?: string;
  logo_url?: string;
  is_active: boolean;
  created_at: string;
}

export interface Influencer {
  id: string;
  full_name: string;
  email?: string;
  country: string;
  primary_tier: 'NANO' | 'MICRO' | 'MID' | 'MACRO' | 'MEGA' | 'MIX';
  primary_handle?: string;
  avatar_url?: string;
  bio?: string;
  content_niches: string[];
  languages: string[];
  status: string;
  tags: string[];
  created_at: string;
}

export interface Campaign {
  id: string;
  code: string;
  client_id: string;
  brand_id: string;
  name: string;
  campaign_type?: string;
  objective:
    | 'AWARENESS'
    | 'CONSIDERACION'
    | 'CONVERSION'
    | 'GESTION_DE_CRISIS'
    | 'BRANDING'
    | 'LANZAMIENTO'
    | 'RETENCION';
  influencer_tiers: string[];
  start_date?: string;
  end_date?: string;
  budget_total?: number | string;
  budget_currency: string;
  num_influencers: number;
  status: string;
  owner_user_id?: string;
  tags: string[];
  created_at: string;
  updated_at: string;
}

export interface CampaignLink {
  id: string;
  campaign_id: string;
  link_type: string;
  title: string;
  url: string;
  description?: string;
}

export interface CampaignKPI {
  kpi_code: string;
  kpi_name: string;
  category: string;
  value: number;
  source: string;
  recorded_at: string;
}

export interface Insight {
  id: string;
  campaign_id: string;
  insight_type: string;
  title: string;
  description: string;
  is_winning_format: boolean;
  generated_by_ai: boolean;
  created_at: string;
}

export interface CampaignDetail extends Campaign {
  brand?: Brand;
  client?: Client;
  kpis?: CampaignKPI[];
  links?: CampaignLink[];
  insights?: Insight[];
}

export interface DashboardKPIs {
  total_campaigns: number;
  active_campaigns: number;
  completed_campaigns: number;
  total_clients: number;
  total_brands: number;
  total_influencers: number;
  total_budget_usd: number | string;
  total_reach: number;
  avg_engagement_rate: number | string | null;
}