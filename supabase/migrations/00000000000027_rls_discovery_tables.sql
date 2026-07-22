-- Migration: 00027_rls_discovery_tables
-- Desc: Enable RLS on discovery_runs, discovery_candidates, discovery_conversations, discovery_messages
-- Fixes M3: multi-tenant isolation for discovery pipeline

BEGIN;

-- Enable RLS
ALTER TABLE discovery_runs ENABLE ROW LEVEL SECURITY;
ALTER TABLE discovery_candidates ENABLE ROW LEVEL SECURITY;
ALTER TABLE discovery_conversations ENABLE ROW LEVEL SECURITY;
ALTER TABLE discovery_messages ENABLE ROW LEVEL SECURITY;

-- discovery_runs policies: user can only see runs they created or that belong to their BUs
CREATE POLICY discovery_runs_select ON discovery_runs
    FOR SELECT USING (
        created_by = auth.uid()
        OR brand_id IN (SELECT id FROM brands WHERE bu_id IN (SELECT unnest(current_user_bu_ids())))
    );

CREATE POLICY discovery_runs_insert ON discovery_runs
    FOR INSERT WITH CHECK (true);

CREATE POLICY discovery_runs_update ON discovery_runs
    FOR UPDATE USING (
        created_by = auth.uid()
        OR brand_id IN (SELECT id FROM brands WHERE bu_id IN (SELECT unnest(current_user_bu_ids())))
    );

-- discovery_candidates: select/update only via run access
CREATE POLICY discovery_candidates_select ON discovery_candidates
    FOR SELECT USING (
        EXISTS (
            SELECT 1 FROM discovery_runs dr
            WHERE dr.id = discovery_candidates.run_id
            AND (
                dr.created_by = auth.uid()
                OR dr.brand_id IN (SELECT id FROM brands WHERE bu_id IN (SELECT unnest(current_user_bu_ids())))
            )
        )
    );

CREATE POLICY discovery_candidates_insert ON discovery_candidates
    FOR INSERT WITH CHECK (true);

-- discovery_conversations: same BU/run-based access
CREATE POLICY discovery_conversations_select ON discovery_conversations
    FOR SELECT USING (
        user_id = auth.uid()
        OR discovery_run_id IN (
            SELECT dr.id FROM discovery_runs dr
            WHERE dr.created_by = auth.uid()
            OR dr.brand_id IN (SELECT id FROM brands WHERE bu_id IN (SELECT unnest(current_user_bu_ids())))
        )
    );

CREATE POLICY discovery_conversations_insert ON discovery_conversations
    FOR INSERT WITH CHECK (true);

CREATE POLICY discovery_conversations_update ON discovery_conversations
    FOR UPDATE USING (
        user_id = auth.uid()
        OR discovery_run_id IN (
            SELECT dr.id FROM discovery_runs dr
            WHERE dr.created_by = auth.uid()
        )
    );

-- discovery_messages: access via conversation
CREATE POLICY discovery_messages_select ON discovery_messages
    FOR SELECT USING (
        EXISTS (
            SELECT 1 FROM discovery_conversations dc
            WHERE dc.id = discovery_messages.conversation_id
            AND (
                dc.user_id = auth.uid()
                OR dc.discovery_run_id IN (
                    SELECT dr.id FROM discovery_runs dr
                    WHERE dr.created_by = auth.uid()
                )
            )
        )
    );

CREATE POLICY discovery_messages_insert ON discovery_messages
    FOR INSERT WITH CHECK (true);

COMMIT;
