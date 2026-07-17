-- =================================================================
-- Migration 0023: Change document_chunks embedding from 1536 to 384 dims
-- Uses fastembed sentence-transformers/all-MiniLM-L6-v2 (384 dims)
-- WARNING: This drops all existing embeddings — re-index after applying
-- =================================================================

-- Drop existing IVFFlat index (if exists)
DROP INDEX IF EXISTS idx_document_chunks_embedding;

-- Change embedding column from vector(1536) to vector(384)
ALTER TABLE document_chunks DROP COLUMN embedding;
ALTER TABLE document_chunks ADD COLUMN embedding vector(384);

-- Recreate IVFFlat index for vector similarity search
CREATE INDEX idx_document_chunks_embedding
    ON document_chunks USING ivfflat (embedding vector_cosine_ops)
    WITH (lists = 100);

-- Update the match_document_chunks function signature
CREATE OR REPLACE FUNCTION public.match_document_chunks(
    query_embedding extensions.vector(384),
    match_threshold FLOAT DEFAULT 0.7,
    match_count INT DEFAULT 10,
    filter_campaign_id UUID DEFAULT NULL
)
RETURNS TABLE (
    id UUID,
    document_id UUID,
    content TEXT,
    similarity FLOAT,
    metadata JSONB
) LANGUAGE plpgsql AS $$
BEGIN
    RETURN QUERY
    SELECT
        dc.id,
        dc.document_id,
        dc.content,
        1 - (dc.embedding <=> query_embedding) AS similarity,
        dc.metadata
    FROM document_chunks dc
    JOIN documents d ON d.id = dc.document_id
    WHERE
        dc.embedding IS NOT NULL
        AND 1 - (dc.embedding <=> query_embedding) > match_threshold
        AND (filter_campaign_id IS NULL OR d.campaign_id = filter_campaign_id)
    ORDER BY dc.embedding <=> query_embedding
    LIMIT match_count;
END;
$$;

COMMENT ON COLUMN document_chunks.embedding IS '384-dim vector from fastembed all-MiniLM-L6-v2';
