-- Migration: 00107_budget_transactions
-- G12 — Tabla ledger para reconciliación Redis↔DB de costos.
-- Cada evento de costo se registra aquí como source of truth.
-- La reconciliación se hace con: SUM(amount) WHERE provider='hikerapi' AND created_at > period_start

BEGIN;

CREATE TABLE IF NOT EXISTS budget_transactions (
    id UUID PRIMARY KEY DEFAULT extensions.uuid_generate_v4(),
    run_id UUID REFERENCES discovery_runs(id) ON DELETE SET NULL,
    provider TEXT NOT NULL,  -- 'hikerapi', 'deepseek', 'apify'
    operation TEXT NOT NULL, -- 'discovery_pipeline', 'enrichment', 'scoring'
    amount_usd NUMERIC(12, 6) NOT NULL,  -- positivo = gasto, negativo = reversa
    request_count INTEGER NOT NULL DEFAULT 1,
    balance_after_usd NUMERIC(12, 6),  -- saldo después de esta transacción (para auditoría)
    metadata JSONB DEFAULT '{}'::jsonb,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

COMMENT ON TABLE budget_transactions IS 'Ledger inmutable de transacciones de costo. La suma de amount_usd por provider = costo real del período.';

CREATE INDEX idx_budget_tx_provider ON budget_transactions(provider, created_at DESC);
CREATE INDEX idx_budget_tx_run ON budget_transactions(run_id) WHERE run_id IS NOT NULL;
CREATE INDEX idx_budget_tx_month ON budget_transactions(date_trunc('month', created_at), provider);

-- Trigger para impedir DELETE/UPDATE (solo INSERT allowed = ledger inmutable)
CREATE OR REPLACE FUNCTION budget_tx_prevent_modification()
RETURNS TRIGGER AS $$
BEGIN
    RAISE EXCEPTION 'budget_transactions es inmutable: DELETE y UPDATE no permitidos. Solo INSERT.';
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER budget_tx_immutable
    BEFORE UPDATE OR DELETE ON budget_transactions
    FOR EACH ROW EXECUTE FUNCTION budget_tx_prevent_modification();

COMMIT;
