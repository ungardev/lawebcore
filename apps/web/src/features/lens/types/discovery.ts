export type DiscoveryRunStatus = 'pending' | 'running' | 'completed' | 'failed' | 'cancelled' | 'partial';
export type CandidateStatus = 'new' | 'saved' | 'dismissed' | 'contacted' | 'replied' | 'won' | 'lost';
export type ConversationStep = 'start' | 'brief' | 'refining' | 'searching' | 'ranking' | 'candidates_review' | 'done';
export type Platform = 'instagram' | 'tiktok' | 'youtube' | 'x' | 'facebook';
export type AudienceGender = 'female' | 'male' | 'all';

export interface BriefStructured {
  product_name: string | null;
  brand_id: string | null;
  brand_name: string | null;
  industry: string | null;
  niches: string[];
  hashtags: string[];
  audience_gender: AudienceGender;
  audience_age_min: number;
  audience_age_max: number;
  audience_countries: string[];
  audience_cities: string[];
  tone: string[];
  platforms: Platform[];
  campaign_objective: string | null;
  campaign_name: string | null;
  budget_usd: number | null;
  budget_currency: string | null;
  kpis: string[];
  campaign_dates: Record<string, string> | null;
  key_themes: string[];
  competitor_brands: string[];
  influencer_preferences: Record<string, unknown> | null;
  additional_context: string;
  brief_source: string;
  source_document: Record<string, unknown> | null;
}

export interface CandidateMetrics {
  platform: Platform;
  platform_user_id: string | null;
  handle: string;
  url: string | null;
  full_name: string | null;
  bio: string | null;
  avatar_url: string | null;
  country: string | null;
  city: string | null;
  language_primary: string;
  followers: number | null;
  following: number | null;
  posts_count: number | null;
  avg_likes: number | null;
  avg_comments: number | null;
  avg_views: number | null;
  engagement_rate: number | null;
  audience_credibility: number | null;
  audience_quality: number | null;
  audience_gender_split: Record<string, number> | null;
  audience_age_buckets: Record<string, number> | null;
  audience_top_countries: Array<Record<string, unknown>> | null;
  audience_top_cities: Array<Record<string, unknown>> | null;
  audience_interests: string[];
  source_actor_run_id: string | null;
  raw_payload: Record<string, unknown>;
}

export interface MatchScoreResult {
  match_score: number;
  niche_relevance: number;
  geo_relevance: number;
  audience_relevance: number;
  content_quality: number;
  expected_reach: number | null;
  expected_engagement: number | null;
  roi_estimate: number | null;
  rationale: string;
}

export interface DiscoveryCandidate {
  id: string;
  platform: Platform;
  handle: string;
  url?: string | null;
  full_name: string | null;
  avatar_url: string | null;
  followers: number | null;
  engagement_rate: number | null;
  match_score: number | null;
  niche_relevance: number | null;
  geo_relevance: number | null;
  audience_relevance: number | null;
  content_quality: number | null;
  status: CandidateStatus;
  expected_reach: number | null;
  expected_engagement: number | null;
  rationale: string | null;
  country: string | null;
  city: string | null;
  bio: string | null;
  tier?: "NANO" | "MICRO" | "MID" | "MACRO" | null;
  is_tienda?: boolean;
}

export interface DiscoveryMessage {
  id: string;
  role: 'user' | 'assistant' | 'tool';
  content: string;
  tool_calls: Array<Record<string, unknown>> | null;
  tool_results: Array<Record<string, unknown>> | null;
  reasoning: string | null;
  cost_usd: number | null;
  latency_ms: number | null;
  created_at: string;
}

export interface DiscoveryConversation {
  id: string;
  current_step: ConversationStep | null;
  discovery_run_id: string | null;
  accumulated_brief: string | null;
  message_count: number;
  status: 'active' | 'completed' | 'abandoned';
  started_at: string;
  last_message_at: string;
  messages?: DiscoveryMessage[];
}

export interface DiscoveryRun {
  id: string;
  status: DiscoveryRunStatus;
  total_candidates: number;
  accepted: number;
  actual_cost_usd: number | null;
  estimated_cost_usd: number | null;
  error: string | null;
  started_at: string | null;
  completed_at: string | null;
  created_at: string;
  brief_text: string;
  brief_parsed: BriefStructured | null;
  metadata?: Record<string, unknown>;
}

export interface RunProgress {
  current_step: string;
  completed_steps: string[];
  current_hashtag?: string;
  candidates_found: number;
  platforms?: string[];
  total_queries?: number;
  completed_at?: string;
}

export interface DiscoveryRunSummary {
  total_found: number;
  top_score: number;
  platforms_queried: Platform[];
}

export interface ToolCall {
  id?: string;
  name: string;
  arguments?: Record<string, unknown>;
  status?: string;
}

export interface ToolResult {
  tool_call_id: string;
  success: boolean;
  output: unknown;
  error?: string;
}

export interface ChatTurn {
  id: string;
  role: 'user' | 'assistant';
  content: string;
  reasoning?: string | null;
  tool_calls?: ToolCall[] | null;
  tool_results?: ToolResult[] | null;
  cost_usd?: number | null;
  latency_ms?: number | null;
  candidates?: DiscoveryCandidate[];
  brief?: BriefStructured | null;
  run_summary?: DiscoveryRunSummary;
  progress?: RunProgress;
  isLoading?: boolean;
  isError?: boolean;
}

export interface ApiCostsResponse {
  provider: string;
  cost_usd: number;
  request_count: number;
}

export interface DiscoveryMetrics {
  total_runs: number;
  completed_runs: number;
  total_candidates_found: number;
  total_saved_as_influencers: number;
  avg_cost_per_run: number;
}
