-- Migration: 00110_discovery_run_hito30_statuses
-- Desc: El Hito 30 introduce RunStatus (observability.py:72-83) con 6 estados
--       que el tipo discovery_run_status no conoce. Sin esto, el UPDATE del
--       estado terminal falla en la base y la corrida queda colgada en 'running'.
--       Ref: docs/FIXES_FRONTEND_LENS_C0-C2_27-08-26.md (Issue C-0)
--
-- IMPORTANTE: ALTER TYPE ... ADD VALUE no puede ejecutarse dentro de un bloque
-- de transacción en Postgres. Cada ADD VALUE corre fuera de transacción.

ALTER TYPE discovery_run_status ADD VALUE IF NOT EXISTS 'queued';
ALTER TYPE discovery_run_status ADD VALUE IF NOT EXISTS 'delivered';
ALTER TYPE discovery_run_status ADD VALUE IF NOT EXISTS 'degraded';
ALTER TYPE discovery_run_status ADD VALUE IF NOT EXISTS 'empty';
ALTER TYPE discovery_run_status ADD VALUE IF NOT EXISTS 'inconsistent';
ALTER TYPE discovery_run_status ADD VALUE IF NOT EXISTS 'aborted_budget';
