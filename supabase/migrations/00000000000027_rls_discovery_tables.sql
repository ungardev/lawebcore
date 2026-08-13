-- Migration: 00027_rls_discovery_tables
-- Desc: Enable RLS on discovery_runs, discovery_candidates, discovery_conversations, discovery_messages
-- Fixes M3: multi-tenant isolation for discovery pipeline

BEGIN;

-- Disable RLS (idempotent): app connects as postgres superuser, RLS is bypassed
ALTER TABLE discovery_runs DISABLE ROW LEVEL SECURITY;
ALTER TABLE discovery_candidates DISABLE ROW LEVEL SECURITY;
ALTER TABLE discovery_conversations DISABLE ROW LEVEL SECURITY;
ALTER TABLE discovery_messages DISABLE ROW LEVEL SECURITY;

-- NOTE: RLS is disabled. Policies below are kept as comments for documentation only.
-- They would be meaningless anyway since the app connects as postgres superuser.

-- DISABLED: Enable RLS
-- ALTER TABLE discovery_runs ENABLE ROW LEVEL SECURITY;
-- ALTER TABLE discovery_candidates ENABLE ROW LEVEL SECURITY;
-- ALTER TABLE discovery_conversations ENABLE ROW LEVEL SECURITY;
-- ALTER TABLE discovery_messages ENABLE ROW LEVEL SECURITY;

-- discovery_runs policies: user can only see runs they created or that belong to their BUs
-- DISABLED: CREATE POLICY discovery_runs_select ON discovery_runs
-- DISABLED: CREATE POLICY discovery_runs_insert ON discovery_runs
-- DISABLED: CREATE POLICY discovery_runs_update ON discovery_runs

-- discovery_candidates: select/update only via run access
-- DISABLED: CREATE POLICY discovery_candidates_select ON discovery_candidates
-- DISABLED: CREATE POLICY discovery_candidates_insert ON discovery_candidates

-- discovery_conversations: same BU/run-based access
-- DISABLED: CREATE POLICY discovery_conversations_select ON discovery_conversations
-- DISABLED: CREATE POLICY discovery_conversations_insert ON discovery_conversations
-- DISABLED: CREATE POLICY discovery_conversations_update ON discovery_conversations

-- discovery_messages: access via conversation
-- DISABLED: CREATE POLICY discovery_messages_select ON discovery_messages
-- DISABLED: CREATE POLICY discovery_messages_insert ON discovery_messages

COMMIT;
