-- Hito 32.2: Deduplicación por handle
-- Paso 1: Detectar duplicados existentes
-- SELECT primary_handle, COUNT(*) FROM influencers GROUP BY primary_handle HAVING COUNT(*) > 1;

-- Paso 2: Agregar índice único (después de resolver duplicados)
CREATE UNIQUE INDEX IF NOT EXISTS idx_influencers_primary_handle_unique
    ON influencers(primary_handle)
    WHERE deleted_at IS NULL;
