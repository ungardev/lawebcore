-- =================================================================
-- LA WEB CORE - Migration 0009: AI / Knowledge Base / RAG
-- =================================================================

-- ---------- AI Prompts (templates versionados) ----------
CREATE TABLE ai_prompts (
  id              UUID PRIMARY KEY DEFAULT extensions.uuid_generate_v4(),
  code            TEXT NOT NULL,               -- 'brief_generator_v1'
  version         INTEGER NOT NULL DEFAULT 1,
  name            TEXT NOT NULL,
  description     TEXT,
  system_prompt   TEXT NOT NULL,
  user_template   TEXT NOT NULL,
  model_provider  TEXT NOT NULL DEFAULT 'openai',
  model_name      TEXT NOT NULL DEFAULT 'gpt-4o-mini',
  temperature     NUMERIC(3, 2) NOT NULL DEFAULT 0.7,
  max_tokens      INTEGER NOT NULL DEFAULT 2000,
  is_active       BOOLEAN NOT NULL DEFAULT TRUE,
  created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  updated_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  UNIQUE (code, version)
);

-- ---------- Documents (indice para RAG) ----------
CREATE TABLE documents (
  id              UUID PRIMARY KEY DEFAULT extensions.uuid_generate_v4(),
  campaign_id     UUID REFERENCES campaigns(id) ON DELETE SET NULL,
  brand_id        UUID REFERENCES brands(id) ON DELETE SET NULL,
  client_id       UUID REFERENCES clients(id) ON DELETE SET NULL,
  title           TEXT NOT NULL,
  description     TEXT,
  doc_type        TEXT NOT NULL,               -- 'brief', 'contract', 'report', 'presentation', 'other'
  source          TEXT NOT NULL,               -- 'upload', 'external_link', 'drive_sync'
  source_url      TEXT,
  storage_path    TEXT,                        -- path en Supabase Storage
  file_name       TEXT,
  mime_type       TEXT,
  file_size_bytes BIGINT,
  status          TEXT NOT NULL DEFAULT 'pending',  -- 'pending', 'processing', 'indexed', 'failed'
  chunk_count     INTEGER NOT NULL DEFAULT 0,
  metadata        JSONB NOT NULL DEFAULT '{}'::jsonb,
  uploaded_by     UUID REFERENCES users(id) ON DELETE SET NULL,
  indexed_at      TIMESTAMPTZ,
  created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  updated_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_documents_campaign ON documents(campaign_id);
CREATE INDEX idx_documents_status ON documents(status);
CREATE INDEX idx_documents_type ON documents(doc_type);

-- ---------- Document Chunks (vectores para RAG) ----------
CREATE TABLE document_chunks (
  id              UUID PRIMARY KEY DEFAULT extensions.uuid_generate_v4(),
  document_id     UUID NOT NULL REFERENCES documents(id) ON DELETE CASCADE,
  chunk_index     INTEGER NOT NULL,
  content         TEXT NOT NULL,
  content_tokens  INTEGER,
  embedding       extensions.vector(1536),     -- OpenAI text-embedding-3-small
  metadata        JSONB NOT NULL DEFAULT '{}'::jsonb,
  created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  UNIQUE (document_id, chunk_index)
);

CREATE INDEX idx_document_chunks_doc ON document_chunks(document_id);
-- IVFFlat index for vector similarity search (created after rows exist for performance)
-- CREATE INDEX idx_document_chunks_embedding ON document_chunks USING ivfflat (embedding extensions.vector_cosine_ops) WITH (lists = 100);

COMMENT ON TABLE document_chunks IS 'Chunks de documentos con embeddings para busqueda semantica (RAG).';

-- ---------- AI Conversations (chat sessions) ----------
CREATE TABLE ai_conversations (
  id              UUID PRIMARY KEY DEFAULT extensions.uuid_generate_v4(),
  user_id         UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
  title           TEXT,
  context_type    TEXT,                        -- 'campaign', 'client', 'brand', 'global'
  context_id      UUID,                        -- id del objeto de contexto
  system_prompt_code TEXT,                     -- referencia a ai_prompts
  is_archived     BOOLEAN NOT NULL DEFAULT FALSE,
  created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  updated_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_ai_conversations_user ON ai_conversations(user_id, updated_at DESC);

-- ---------- AI Messages (mensajes del chat) ----------
CREATE TABLE ai_messages (
  id              UUID PRIMARY KEY DEFAULT extensions.uuid_generate_v4(),
  conversation_id UUID NOT NULL REFERENCES ai_conversations(id) ON DELETE CASCADE,
  role            TEXT NOT NULL,               -- 'user', 'assistant', 'system'
  content         TEXT NOT NULL,
  model_provider  TEXT,
  model_name      TEXT,
  tokens_input    INTEGER,
  tokens_output   INTEGER,
  cost_usd        NUMERIC(10, 6),
  latency_ms      INTEGER,
  metadata        JSONB NOT NULL DEFAULT '{}'::jsonb,
  created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_ai_messages_conversation ON ai_messages(conversation_id, created_at);

-- ---------- AI Jobs (queue de jobs async) ----------
CREATE TABLE ai_jobs (
  id              UUID PRIMARY KEY DEFAULT extensions.uuid_generate_v4(),
  job_type        ai_job_type NOT NULL,
  status          ai_job_status NOT NULL DEFAULT 'PENDING',
  payload         JSONB NOT NULL DEFAULT '{}'::jsonb,
  result          JSONB,
  error           TEXT,
  attempts        INTEGER NOT NULL DEFAULT 0,
  max_attempts    INTEGER NOT NULL DEFAULT 3,
  scheduled_for   TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  started_at      TIMESTAMPTZ,
  completed_at    TIMESTAMPTZ,
  user_id         UUID REFERENCES users(id) ON DELETE SET NULL,
  campaign_id     UUID REFERENCES campaigns(id) ON DELETE SET NULL,
  created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  updated_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_ai_jobs_status ON ai_jobs(status, scheduled_for);
CREATE INDEX idx_ai_jobs_campaign ON ai_jobs(campaign_id);

-- ---------- Notifications ----------
CREATE TABLE notifications (
  id              UUID PRIMARY KEY DEFAULT extensions.uuid_generate_v4(),
  user_id         UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
  title           TEXT NOT NULL,
  body            TEXT,
  category        TEXT,                        -- 'campaign', 'task', 'kpi', 'ai', 'system'
  severity        TEXT NOT NULL DEFAULT 'info',  -- 'info', 'success', 'warning', 'error'
  link            TEXT,
  is_read         BOOLEAN NOT NULL DEFAULT FALSE,
  read_at         TIMESTAMPTZ,
  metadata        JSONB NOT NULL DEFAULT '{}'::jsonb,
  created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_notifications_user_unread ON notifications(user_id, is_read, created_at DESC);

CREATE TRIGGER trg_documents_updated_at BEFORE UPDATE ON documents
  FOR EACH ROW EXECUTE FUNCTION public.set_updated_at();
CREATE TRIGGER trg_ai_conversations_updated_at BEFORE UPDATE ON ai_conversations
  FOR EACH ROW EXECUTE FUNCTION public.set_updated_at();
CREATE TRIGGER trg_ai_jobs_updated_at BEFORE UPDATE ON ai_jobs
  FOR EACH ROW EXECUTE FUNCTION public.set_updated_at();
CREATE TRIGGER trg_ai_prompts_updated_at BEFORE UPDATE ON ai_prompts
  FOR EACH ROW EXECUTE FUNCTION public.set_updated_at();

-- ---------- Function: vector similarity search ----------
CREATE OR REPLACE FUNCTION public.match_document_chunks(
  query_embedding extensions.vector(1536),
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