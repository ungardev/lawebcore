-- Migration: 00104_discovery_run_partial_status
-- Desc: Adds 'partial' status to discovery_run_status enum.
--        The worker uses status='partial' when a run completes with degraded
--        enrichment (e.g. budget exhausted mid-run, max calls reached).
--        Without this, the CHECK constraint rejects the value and the run
--        status update silently fails.
BEGIN;

ALTER TYPE discovery_run_status ADD VALUE IF NOT EXISTS 'partial';

COMMIT;
