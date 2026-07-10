// P.I.A.R types — Publicaciones and Projections

export interface Publicacion {
  id: string;
  campaign_id: string;
  influencer_id: string | null;
  fecha_publicacion: string;
  vistas: number | null;
  alcance: number | null;
  likes: number | null;
  comentarios: number | null;
  compartidos: number | null;
  guardados: number | null;
  er_alcance: number | null;
  er_vistas: number | null;
  retencion: number | null;
  sentimiento_positivo: number;
  sentimiento_neutro: number;
  sentimiento_negativo: number;
  url_publicacion: string | null;
  plataforma: string;
  formato: string | null;
  source: string;
  created_at: string;
}

export interface ProjectionScenario {
  vistas_proyectadas: number;
  alcance_proyectado: number;
  engagement_proyectado: number;
  posts_virales_esperados: number;
}

export interface ProjectionTasaPromedio {
  er_promedio: number | null;
  retencion_promedio: number | null;
}

export interface ProjectionTierResult {
  tier: string;
  num_posts: number;
  fuente: string;
  num_campanas: number;
  tasas: ProjectionTasaPromedio;
  escenarios: {
    conservador: ProjectionScenario;
    base: ProjectionScenario;
    optimista: ProjectionScenario;
  };
}

export interface ProjectionTotal {
  conservador: { vistas: number; alcance: number; engagement: number; posts_virales: number };
  base: { vistas: number; alcance: number; engagement: number; posts_virales: number };
  optimista: { vistas: number; alcance: number; engagement: number; posts_virales: number };
}

export interface ProjectionCalculateResponse {
  brand_id: string;
  brand_name: string;
  client_id: string;
  industry: string | null;
  reference_date: string;
  calidad_creadores: {
    decision_dominante: string;
    score_promedio: number | null;
    ajuste_aplicado: string;
  } | null;
  resultados_por_tier: ProjectionTierResult[];
  total: ProjectionTotal;
}

export interface InfluencerScore {
  score_retention: number | null;
  score_engagement: number | null;
  score_viralidad: number | null;
  score_final: number | null;
  decision: 'ESCALAR' | 'OPTIMIZAR' | 'DESCARTAR' | 'DATOS_INSUFICIENTES';
  retention_avg: number | null;
  er_vistas: number | null;
  vf_ratio: number | null;
  followers: number | null;
  mode: 'BY_POST' | 'BY_WAVE' | 'BY_PROFILE';
  publicaciones_count: number;
  subtier: string | null;
  benchmark_status: Record<string, 'green' | 'yellow' | 'red'>;
}

export interface BenchmarkStatus {
  retention: 'green' | 'yellow' | 'red';
  engagement: 'green' | 'yellow' | 'red';
  viralidad: 'green' | 'yellow' | 'red';
}
