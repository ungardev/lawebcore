-- Migration: 00106_discovery_run_explored_status
-- Desc: Adds 'explored' status to discovery_run_status enum for Hito 24 (Modo Explorar).
--        In explore mode, the pipeline skips enrichment and returns discovery results
--        with rough geo+niche scores. The analyst then selects handles for analyze mode.

ALTER TYPE discovery_run_status ADD VALUE IF NOT EXISTS 'explored';
