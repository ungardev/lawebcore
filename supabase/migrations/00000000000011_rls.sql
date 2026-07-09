-- =================================================================
-- LA WEB CORE - Migration 0011: Row Level Security (RLS)
-- =================================================================
-- Defense in depth: defense at the DB level, not just backend.
-- RLS policies enforce visibility per business unit, role, and ownership.

-- ---------- Helper: get current user's roles + BUs ----------
CREATE OR REPLACE FUNCTION public.current_user_role_codes()
RETURNS TEXT[] LANGUAGE sql STABLE SECURITY DEFINER AS $$
  SELECT COALESCE(
    ARRAY_AGG(DISTINCT r.code),
    ARRAY[]::TEXT[]
  )
  FROM user_roles ur
  JOIN roles r ON r.id = ur.role_id
  WHERE ur.user_id = auth.uid()
    AND (ur.expires_at IS NULL OR ur.expires_at > NOW());
$$;

CREATE OR REPLACE FUNCTION public.current_user_bu_ids()
RETURNS UUID[] LANGUAGE sql STABLE SECURITY DEFINER AS $$
  SELECT COALESCE(
    ARRAY_AGG(DISTINCT ur.business_unit_id) FILTER (WHERE ur.business_unit_id IS NOT NULL),
    ARRAY[]::UUID[]
  )
  FROM user_roles ur
  WHERE ur.user_id = auth.uid();
$$;

CREATE OR REPLACE FUNCTION public.is_admin_general()
RETURNS BOOLEAN LANGUAGE sql STABLE SECURITY DEFINER AS $$
  SELECT 'admin_general' = ANY(public.current_user_role_codes());
$$;

-- ---------- Enable RLS on all tables ----------
ALTER TABLE business_units          ENABLE ROW LEVEL SECURITY;
ALTER TABLE users                   ENABLE ROW LEVEL SECURITY;
ALTER TABLE roles                   ENABLE ROW LEVEL SECURITY;
ALTER TABLE permissions             ENABLE ROW LEVEL SECURITY;
ALTER TABLE role_permissions        ENABLE ROW LEVEL SECURITY;
ALTER TABLE user_roles              ENABLE ROW LEVEL SECURITY;
ALTER TABLE teams                   ENABLE ROW LEVEL SECURITY;
ALTER TABLE team_members            ENABLE ROW LEVEL SECURITY;

ALTER TABLE clients                 ENABLE ROW LEVEL SECURITY;
ALTER TABLE brands                  ENABLE ROW LEVEL SECURITY;
ALTER TABLE brand_contacts          ENABLE ROW LEVEL SECURITY;
ALTER TABLE client_contracts        ENABLE ROW LEVEL SECURITY;

ALTER TABLE influencers             ENABLE ROW LEVEL SECURITY;
ALTER TABLE influencer_social_accounts ENABLE ROW LEVEL SECURITY;
ALTER TABLE influencer_metrics_snapshot ENABLE ROW LEVEL SECURITY;

ALTER TABLE campaigns               ENABLE ROW LEVEL SECURITY;
ALTER TABLE campaign_status_history ENABLE ROW LEVEL SECURITY;
ALTER TABLE campaign_influencers    ENABLE ROW LEVEL SECURITY;
ALTER TABLE campaign_links          ENABLE ROW LEVEL SECURITY;
ALTER TABLE campaign_documents      ENABLE ROW LEVEL SECURITY;

ALTER TABLE kpi_definitions         ENABLE ROW LEVEL SECURITY;
ALTER TABLE campaign_kpi_values     ENABLE ROW LEVEL SECURITY;
ALTER TABLE benchmarks              ENABLE ROW LEVEL SECURITY;
ALTER TABLE insights                ENABLE ROW LEVEL SECURITY;
ALTER TABLE winning_formats         ENABLE ROW LEVEL SECURITY;

ALTER TABLE budgets                 ENABLE ROW LEVEL SECURITY;
ALTER TABLE budget_items            ENABLE ROW LEVEL SECURITY;
ALTER TABLE tasks                   ENABLE ROW LEVEL SECURITY;
ALTER TABLE forms                   ENABLE ROW LEVEL SECURITY;
ALTER TABLE form_submissions        ENABLE ROW LEVEL SECURITY;
ALTER TABLE automations             ENABLE ROW LEVEL SECURITY;
ALTER TABLE automation_logs         ENABLE ROW LEVEL SECURITY;

ALTER TABLE documents               ENABLE ROW LEVEL SECURITY;
ALTER TABLE document_chunks         ENABLE ROW LEVEL SECURITY;
ALTER TABLE ai_conversations        ENABLE ROW LEVEL SECURITY;
ALTER TABLE ai_messages             ENABLE ROW LEVEL SECURITY;
ALTER TABLE ai_jobs                 ENABLE ROW LEVEL SECURITY;
ALTER TABLE ai_prompts              ENABLE ROW LEVEL SECURITY;
ALTER TABLE notifications           ENABLE ROW LEVEL SECURITY;

ALTER TABLE dashboards              ENABLE ROW LEVEL SECURITY;
ALTER TABLE widgets                 ENABLE ROW LEVEL SECURITY;
ALTER TABLE scheduled_reports       ENABLE ROW LEVEL SECURITY;
ALTER TABLE audit_logs              ENABLE ROW LEVEL SECURITY;
ALTER TABLE integrations            ENABLE ROW LEVEL SECURITY;
ALTER TABLE webhooks                ENABLE ROW LEVEL SECURITY;
ALTER TABLE exports                 ENABLE ROW LEVEL SECURITY;

-- =================================================================
-- Policies: identity
-- =================================================================

-- business_units: visible to all authenticated
CREATE POLICY bu_read ON business_units FOR SELECT TO authenticated
  USING (is_active = TRUE);
CREATE POLICY bu_admin_all ON business_units FOR ALL TO authenticated
  USING (public.is_admin_general()) WITH CHECK (public.is_admin_general());

-- users: read own + same BU; admin sees all
CREATE POLICY users_read_self ON users FOR SELECT TO authenticated
  USING (id = auth.uid() OR public.is_admin_general());
CREATE POLICY users_read_same_bu ON users FOR SELECT TO authenticated
  USING (
    primary_bu_id IN (SELECT UNNEST(public.current_user_bu_ids()))
    OR public.is_admin_general()
  );
CREATE POLICY users_update_self ON users FOR UPDATE TO authenticated
  USING (id = auth.uid()) WITH CHECK (id = auth.uid());
CREATE POLICY users_admin_all ON users FOR ALL TO authenticated
  USING (public.is_admin_general()) WITH CHECK (public.is_admin_general());

-- roles / permissions: read for all authenticated, write only admin
CREATE POLICY roles_read ON roles FOR SELECT TO authenticated USING (TRUE);
CREATE POLICY roles_admin ON roles FOR ALL TO authenticated
  USING (public.is_admin_general()) WITH CHECK (public.is_admin_general());

CREATE POLICY perms_read ON permissions FOR SELECT TO authenticated USING (TRUE);
CREATE POLICY perms_admin ON permissions FOR ALL TO authenticated
  USING (public.is_admin_general()) WITH CHECK (public.is_admin_general());

CREATE POLICY rp_read ON role_permissions FOR SELECT TO authenticated USING (TRUE);
CREATE POLICY rp_admin ON role_permissions FOR ALL TO authenticated
  USING (public.is_admin_general()) WITH CHECK (public.is_admin_general());

-- user_roles: read own; admin/PM read in BU
CREATE POLICY ur_read_self ON user_roles FOR SELECT TO authenticated
  USING (user_id = auth.uid() OR public.is_admin_general());
CREATE POLICY ur_admin ON user_roles FOR ALL TO authenticated
  USING (public.is_admin_general()) WITH CHECK (public.is_admin_general());

-- teams: members see their team
CREATE POLICY teams_read ON teams FOR SELECT TO authenticated
  USING (
    public.is_admin_general()
    OR id IN (SELECT team_id FROM team_members WHERE user_id = auth.uid())
  );
CREATE POLICY teams_admin ON teams FOR ALL TO authenticated
  USING (public.is_admin_general()) WITH CHECK (public.is_admin_general());

CREATE POLICY tm_read ON team_members FOR SELECT TO authenticated
  USING (
    user_id = auth.uid()
    OR team_id IN (SELECT team_id FROM team_members WHERE user_id = auth.uid())
    OR public.is_admin_general()
  );

-- =================================================================
-- Policies: commercial hierarchy
-- =================================================================

CREATE POLICY clients_read ON clients FOR SELECT TO authenticated
  USING (deleted_at IS NULL);
CREATE POLICY clients_write ON clients FOR ALL TO authenticated
  USING (
    public.is_admin_general()
    OR 'admin_general' = ANY(public.current_user_role_codes())
    OR 'director_bu' = ANY(public.current_user_role_codes())
  )
  WITH CHECK (
    public.is_admin_general()
    OR 'director_bu' = ANY(public.current_user_role_codes())
  );

CREATE POLICY brands_read ON brands FOR SELECT TO authenticated
  USING (deleted_at IS NULL);
CREATE POLICY brands_write ON brands FOR ALL TO authenticated
  USING (
    public.is_admin_general()
    OR 'director_bu' = ANY(public.current_user_role_codes())
    OR 'project_manager' = ANY(public.current_user_role_codes())
  );

CREATE POLICY brand_contacts_read ON brand_contacts FOR SELECT TO authenticated USING (TRUE);
CREATE POLICY brand_contacts_write ON brand_contacts FOR ALL TO authenticated
  USING (public.is_admin_general() OR 'account_manager' = ANY(public.current_user_role_codes()));

CREATE POLICY contracts_read ON client_contracts FOR SELECT TO authenticated USING (TRUE);
CREATE POLICY contracts_write ON client_contracts FOR ALL TO authenticated
  USING (public.is_admin_general() OR 'finance' = ANY(public.current_user_role_codes()));

-- =================================================================
-- Policies: influencers
-- =================================================================

CREATE POLICY inf_read ON influencers FOR SELECT TO authenticated
  USING (deleted_at IS NULL);
CREATE POLICY inf_write ON influencers FOR ALL TO authenticated
  USING (
    public.is_admin_general()
    OR 'influencer_liaison' = ANY(public.current_user_role_codes())
    OR 'project_manager' = ANY(public.current_user_role_codes())
  );

CREATE POLICY social_read ON influencer_social_accounts FOR SELECT TO authenticated USING (TRUE);
CREATE POLICY social_write ON influencer_social_accounts FOR ALL TO authenticated
  USING (
    public.is_admin_general()
    OR 'influencer_liaison' = ANY(public.current_user_role_codes())
  );

CREATE POLICY metrics_read ON influencer_metrics_snapshot FOR SELECT TO authenticated USING (TRUE);
CREATE POLICY metrics_write ON influencer_metrics_snapshot FOR ALL TO authenticated
  USING (public.is_admin_general() OR 'analista' = ANY(public.current_user_role_codes()));

-- =================================================================
-- Policies: campaigns
-- =================================================================

-- Campaigns: client_externo solo ve sus campanas (read-only)
CREATE POLICY campaigns_read ON campaigns FOR SELECT TO authenticated
  USING (
    deleted_at IS NULL
    AND (
      public.is_admin_general()
      OR 'cliente_externo' != ALL(public.current_user_role_codes())
      OR EXISTS (
        SELECT 1 FROM brand_contacts bc
        JOIN brands b ON b.id = bc.brand_id
        WHERE b.id = campaigns.brand_id AND bc.email = (SELECT email FROM users WHERE id = auth.uid())
      )
    )
  );

CREATE POLICY campaigns_write ON campaigns FOR ALL TO authenticated
  USING (
    public.is_admin_general()
    OR 'project_manager' = ANY(public.current_user_role_codes())
    OR 'account_manager' = ANY(public.current_user_role_codes())
    OR owner_user_id = auth.uid()
  )
  WITH CHECK (
    public.is_admin_general()
    OR 'project_manager' = ANY(public.current_user_role_codes())
    OR 'account_manager' = ANY(public.current_user_role_codes())
    OR owner_user_id = auth.uid()
  );

CREATE POLICY csh_read ON campaign_status_history FOR SELECT TO authenticated USING (TRUE);
CREATE POLICY csh_write ON campaign_status_history FOR INSERT TO authenticated WITH CHECK (TRUE);

CREATE POLICY ci_read ON campaign_influencers FOR SELECT TO authenticated USING (TRUE);
CREATE POLICY ci_write ON campaign_influencers FOR ALL TO authenticated
  USING (
    public.is_admin_general()
    OR 'project_manager' = ANY(public.current_user_role_codes())
    OR 'influencer_liaison' = ANY(public.current_user_role_codes())
  );

CREATE POLICY cl_read ON campaign_links FOR SELECT TO authenticated USING (TRUE);
CREATE POLICY cl_write ON campaign_links FOR ALL TO authenticated
  USING (
    public.is_admin_general()
    OR 'project_manager' = ANY(public.current_user_role_codes())
  );

CREATE POLICY cd_read ON campaign_documents FOR SELECT TO authenticated USING (TRUE);
CREATE POLICY cd_write ON campaign_documents FOR ALL TO authenticated
  USING (
    public.is_admin_general()
    OR 'project_manager' = ANY(public.current_user_role_codes())
    OR 'creativo' = ANY(public.current_user_role_codes())
  );

-- =================================================================
-- Policies: KPIs
-- =================================================================

CREATE POLICY kd_read ON kpi_definitions FOR SELECT TO authenticated USING (TRUE);
CREATE POLICY kd_write ON kpi_definitions FOR ALL TO authenticated
  USING (public.is_admin_general());

CREATE POLICY ckv_read ON campaign_kpi_values FOR SELECT TO authenticated USING (TRUE);
CREATE POLICY ckv_write ON campaign_kpi_values FOR ALL TO authenticated
  USING (
    public.is_admin_general()
    OR 'analista' = ANY(public.current_user_role_codes())
    OR 'project_manager' = ANY(public.current_user_role_codes())
  );

CREATE POLICY bm_read ON benchmarks FOR SELECT TO authenticated USING (TRUE);
CREATE POLICY bm_write ON benchmarks FOR ALL TO authenticated
  USING (public.is_admin_general() OR 'analista' = ANY(public.current_user_role_codes()));

CREATE POLICY insights_read ON insights FOR SELECT TO authenticated USING (TRUE);
CREATE POLICY insights_write ON insights FOR ALL TO authenticated USING (TRUE);

CREATE POLICY wf_read ON winning_formats FOR SELECT TO authenticated USING (TRUE);
CREATE POLICY wf_write ON winning_formats FOR ALL TO authenticated USING (TRUE);

-- =================================================================
-- Policies: operations
-- =================================================================

CREATE POLICY budgets_read ON budgets FOR SELECT TO authenticated USING (TRUE);
CREATE POLICY budgets_write ON budgets FOR ALL TO authenticated
  USING (public.is_admin_general() OR 'finance' = ANY(public.current_user_role_codes()));

CREATE POLICY bi_read ON budget_items FOR SELECT TO authenticated USING (TRUE);
CREATE POLICY bi_write ON budget_items FOR ALL TO authenticated
  USING (public.is_admin_general() OR 'finance' = ANY(public.current_user_role_codes()));

CREATE POLICY tasks_read ON tasks FOR SELECT TO authenticated
  USING (
    assignee_id = auth.uid()
    OR created_by = auth.uid()
    OR public.is_admin_general()
    OR 'project_manager' = ANY(public.current_user_role_codes())
  );
CREATE POLICY tasks_write ON tasks FOR ALL TO authenticated USING (TRUE);

CREATE POLICY forms_read ON forms FOR SELECT TO authenticated USING (TRUE);
CREATE POLICY forms_write ON forms FOR ALL TO authenticated
  USING (public.is_admin_general() OR 'project_manager' = ANY(public.current_user_role_codes()));

CREATE POLICY fs_read ON form_submissions FOR SELECT TO authenticated USING (TRUE);
CREATE POLICY fs_write ON form_submissions FOR INSERT TO authenticated WITH CHECK (TRUE);

CREATE POLICY automations_read ON automations FOR SELECT TO authenticated USING (TRUE);
CREATE POLICY automations_write ON automations FOR ALL TO authenticated
  USING (public.is_admin_general());

CREATE POLICY alogs_read ON automation_logs FOR SELECT TO authenticated USING (TRUE);

-- =================================================================
-- Policies: AI
-- =================================================================

CREATE POLICY docs_read ON documents FOR SELECT TO authenticated USING (TRUE);
CREATE POLICY docs_write ON documents FOR ALL TO authenticated USING (TRUE);

CREATE POLICY chunks_read ON document_chunks FOR SELECT TO authenticated USING (TRUE);

CREATE POLICY aic_read ON ai_conversations FOR SELECT TO authenticated
  USING (user_id = auth.uid() OR public.is_admin_general());
CREATE POLICY aic_write ON ai_conversations FOR ALL TO authenticated
  USING (user_id = auth.uid()) WITH CHECK (user_id = auth.uid());

CREATE POLICY aim_read ON ai_messages FOR SELECT TO authenticated
  USING (
    conversation_id IN (SELECT id FROM ai_conversations WHERE user_id = auth.uid())
    OR public.is_admin_general()
  );
CREATE POLICY aim_write ON ai_messages FOR INSERT TO authenticated WITH CHECK (TRUE);

CREATE POLICY aij_read ON ai_jobs FOR SELECT TO authenticated
  USING (user_id = auth.uid() OR public.is_admin_general());
CREATE POLICY aij_write ON ai_jobs FOR ALL TO authenticated USING (TRUE);

CREATE POLICY prompts_read ON ai_prompts FOR SELECT TO authenticated USING (TRUE);
CREATE POLICY prompts_write ON ai_prompts FOR ALL TO authenticated
  USING (public.is_admin_general());

CREATE POLICY notif_read ON notifications FOR SELECT TO authenticated
  USING (user_id = auth.uid());
CREATE POLICY notif_write ON notifications FOR ALL TO authenticated USING (TRUE);

-- =================================================================
-- Policies: analytics, audit, integrations
-- =================================================================

CREATE POLICY dash_read ON dashboards FOR SELECT TO authenticated
  USING (user_id = auth.uid() OR is_shared = TRUE OR public.is_admin_general());
CREATE POLICY dash_write ON dashboards FOR ALL TO authenticated
  USING (user_id = auth.uid()) WITH CHECK (user_id = auth.uid());

CREATE POLICY widgets_read ON widgets FOR SELECT TO authenticated USING (TRUE);
CREATE POLICY widgets_write ON widgets FOR ALL TO authenticated
  USING (dashboard_id IN (SELECT id FROM dashboards WHERE user_id = auth.uid()));

CREATE POLICY sr_read ON scheduled_reports FOR SELECT TO authenticated USING (TRUE);
CREATE POLICY sr_write ON scheduled_reports FOR ALL TO authenticated
  USING (public.is_admin_general());

CREATE POLICY audit_read ON audit_logs FOR SELECT TO authenticated
  USING (public.is_admin_general());
CREATE POLICY audit_write ON audit_logs FOR INSERT TO authenticated WITH CHECK (TRUE);

CREATE POLICY integrations_read ON integrations FOR SELECT TO authenticated
  USING (public.is_admin_general());
CREATE POLICY integrations_write ON integrations FOR ALL TO authenticated
  USING (public.is_admin_general());

CREATE POLICY wh_read ON webhooks FOR SELECT TO authenticated USING (public.is_admin_general());
CREATE POLICY wh_write ON webhooks FOR ALL TO authenticated
  USING (public.is_admin_general());

CREATE POLICY exports_read ON exports FOR SELECT TO authenticated
  USING (user_id = auth.uid() OR public.is_admin_general());
CREATE POLICY exports_write ON exports FOR INSERT TO authenticated WITH CHECK (user_id = auth.uid());

-- =================================================================
-- Grants to authenticated role on base operations
-- =================================================================

GRANT USAGE ON ALL SEQUENCES IN SCHEMA public TO authenticated;
GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA public TO authenticated;
GRANT EXECUTE ON ALL FUNCTIONS IN SCHEMA public TO authenticated;