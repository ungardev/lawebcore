// Sentiment Analysis types

export interface SentimentDistribution {
  positivo: number;
  neutro: number;
  negativo: number;
  total: number;
  confianza_promedio: number;
  comentarios: Array<{
    index: number;
    sentiment: 'POSITIVO' | 'NEUTRO' | 'NEGATIVO' | 'SIN_DATOS';
    confidence: number;
  }>;
}

export interface SentimentAnalyzeResponse {
  publicacion_id: string;
  distribution: SentimentDistribution;
  analyzed_at: string;
}

export interface SentimentAggregateResponse {
  campaign_id: string;
  total_publicaciones: number;
  analizadas: number;
  pendientes: number;
  totales: {
    positivo: number;
    neutro: number;
    negativo: number;
    total: number;
  };
  por_publicacion: Array<{
    publicacion_id: string;
    analizado: boolean;
    positivo?: number;
    neutro?: number;
    negativo?: number;
  }>;
}

export interface SentimentReanalyzeResponse {
  campaign_id: string;
  queued: number;
  job_id: string;
  message: string;
}
