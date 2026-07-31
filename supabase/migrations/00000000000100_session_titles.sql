-- Migration 0100: Session titles
-- Adds auto-generated title column to discovery_conversations and discovery_runs
-- for meaningful session identification in UI (fixes "Nueva búsqueda" issue).

ALTER TABLE discovery_conversations
ADD COLUMN IF NOT EXISTS title TEXT;

ALTER TABLE discovery_runs
ADD COLUMN IF NOT EXISTS title TEXT;

-- Backfill titles for existing conversations using last_message_at timestamp
UPDATE discovery_conversations dc
SET title = 'Lens · ' || TO_CHAR(dc.last_message_at, 'DD/MM HH24:MI')
WHERE dc.title IS NULL;

-- Backfill titles for existing runs using created_at timestamp
UPDATE discovery_runs dr
SET title = 'Búsqueda · ' || TO_CHAR(dr.created_at, 'DD/MM HH24:MI')
WHERE dr.title IS NULL;
