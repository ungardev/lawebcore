CREATE TABLE IF NOT EXISTS discovery_run_events (
    id            BIGSERIAL PRIMARY KEY,
    run_id        UUID NOT NULL REFERENCES discovery_runs(id) ON DELETE CASCADE,
    ts            TIMESTAMPTZ NOT NULL DEFAULT now(),
    event         TEXT NOT NULL,
    stage         TEXT,
    reason_code   TEXT,
    username      TEXT,
    payload       JSONB NOT NULL DEFAULT '{}'::jsonb
);

CREATE INDEX IF NOT EXISTS idx_run_events_run
    ON discovery_run_events(run_id);

CREATE INDEX IF NOT EXISTS idx_run_events_reason
    ON discovery_run_events(reason_code)
    WHERE reason_code IS NOT NULL;

CREATE INDEX IF NOT EXISTS idx_run_events_event
    ON discovery_run_events(event);
