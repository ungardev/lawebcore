-- =================================================================
-- LA WEB CORE — Railway: Remaining migrations not covered by bootstrap
-- Apply AFTER all 5 bootstrap parts (p1-p5) complete successfully
-- =================================================================

-- 0020: Fix api_costs monthly index (IMMUTABLE wrapper)
CREATE OR REPLACE FUNCTION public.date_trunc_month_immutable(ts TIMESTAMPTZ)
RETURNS TIMESTAMPTZ LANGUAGE sql IMMUTABLE PARALLEL SAFE AS $$
  SELECT date_trunc('month', ts AT TIME ZONE 'UTC');
$$;

DROP INDEX IF EXISTS idx_api_costs_month;
CREATE INDEX idx_api_costs_month ON api_costs(public.date_trunc_month_immutable(occurred_at), provider);

-- 0023: Change document_chunks embedding from 1536 to 384 dims
-- WARNING: Drops all existing embeddings
DROP INDEX IF EXISTS idx_document_chunks_embedding;
ALTER TABLE document_chunks DROP COLUMN IF EXISTS embedding;
ALTER TABLE document_chunks ADD COLUMN embedding extensions.vector(384);
CREATE INDEX idx_document_chunks_embedding ON document_chunks USING ivfflat (embedding vector_cosine_ops) WITH (lists = 100);

CREATE OR REPLACE FUNCTION public.match_document_chunks(
    query_embedding extensions.vector(384), match_threshold FLOAT DEFAULT 0.7,
    match_count INT DEFAULT 10, filter_campaign_id UUID DEFAULT NULL
)
RETURNS TABLE (id UUID, document_id UUID, content TEXT, similarity FLOAT, metadata JSONB)
LANGUAGE plpgsql AS $$
BEGIN RETURN QUERY
    SELECT dc.id, dc.document_id, dc.content,
           1 - (dc.embedding <=> query_embedding) AS similarity, dc.metadata
    FROM document_chunks dc JOIN documents d ON d.id = dc.document_id
    WHERE dc.embedding IS NOT NULL
      AND 1 - (dc.embedding <=> query_embedding) > match_threshold
      AND (filter_campaign_id IS NULL OR d.campaign_id = filter_campaign_id)
    ORDER BY dc.embedding <=> query_embedding LIMIT match_count;
END; $$;

-- 0024: Enrichment columns on influencers
ALTER TABLE influencers ADD COLUMN IF NOT EXISTS platform TEXT;
ALTER TABLE influencers ADD COLUMN IF NOT EXISTS followers BIGINT;
ALTER TABLE influencers ADD COLUMN IF NOT EXISTS following BIGINT;
ALTER TABLE influencers ADD COLUMN IF NOT EXISTS posts_count INTEGER;
ALTER TABLE influencers ADD COLUMN IF NOT EXISTS avg_likes NUMERIC(12,2);
ALTER TABLE influencers ADD COLUMN IF NOT EXISTS avg_comments NUMERIC(12,2);
ALTER TABLE influencers ADD COLUMN IF NOT EXISTS engagement_rate NUMERIC(6,4);
ALTER TABLE influencers ADD COLUMN IF NOT EXISTS audience_credibility NUMERIC(5,2);
ALTER TABLE influencers ADD COLUMN IF NOT EXISTS profile_pic_url TEXT;
ALTER TABLE influencers ADD COLUMN IF NOT EXISTS enriched_at TIMESTAMPTZ;

-- Mark these as applied in schema_migrations
INSERT INTO schema_migrations (version, filename) VALUES
    ('20', '00000000000020_api_costs_index_fix.sql'),
    ('23', '00000000000023_embeddings_384.sql'),
    ('24', '00000000000024_enrichment_columns.sql')
ON CONFLICT (version) DO NOTHING;
