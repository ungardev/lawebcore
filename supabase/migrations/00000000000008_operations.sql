-- =================================================================
-- LA WEB CORE - Migration 0008: Operations, Workflows, Forms
-- =================================================================

-- ---------- Budgets (1:1 con campana) ----------
CREATE TABLE budgets (
  id              UUID PRIMARY KEY DEFAULT extensions.uuid_generate_v4(),
  campaign_id     UUID NOT NULL REFERENCES campaigns(id) ON DELETE CASCADE UNIQUE,
  total_planned   NUMERIC(15, 2) NOT NULL DEFAULT 0,
  total_committed NUMERIC(15, 2) NOT NULL DEFAULT 0,
  total_spent     NUMERIC(15, 2) NOT NULL DEFAULT 0,
  currency        TEXT NOT NULL DEFAULT 'USD',
  notes           TEXT,
  approved_by     UUID REFERENCES users(id) ON DELETE SET NULL,
  approved_at     TIMESTAMPTZ,
  created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  updated_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- ---------- Budget Items (desglose) ----------
CREATE TABLE budget_items (
  id              UUID PRIMARY KEY DEFAULT extensions.uuid_generate_v4(),
  budget_id       UUID NOT NULL REFERENCES budgets(id) ON DELETE CASCADE,
  category        TEXT NOT NULL,               -- 'talento', 'produccion', 'medios', 'contingencia'
  description     TEXT NOT NULL,
  planned_amount  NUMERIC(15, 2) NOT NULL DEFAULT 0,
  committed_amount NUMERIC(15, 2) NOT NULL DEFAULT 0,
  spent_amount    NUMERIC(15, 2) NOT NULL DEFAULT 0,
  vendor          TEXT,
  notes           TEXT,
  created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  updated_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_budget_items_budget ON budget_items(budget_id);

-- ---------- Tasks (tareas por campana) ----------
CREATE TABLE tasks (
  id              UUID PRIMARY KEY DEFAULT extensions.uuid_generate_v4(),
  campaign_id     UUID REFERENCES campaigns(id) ON DELETE CASCADE,
  business_unit_id UUID REFERENCES business_units(id) ON DELETE SET NULL,
  title           TEXT NOT NULL,
  description     TEXT,
  status          task_status NOT NULL DEFAULT 'PENDIENTE',
  priority        task_priority NOT NULL DEFAULT 'MEDIA',
  assignee_id     UUID REFERENCES users(id) ON DELETE SET NULL,
  created_by      UUID REFERENCES users(id) ON DELETE SET NULL,
  due_date        TIMESTAMPTZ,
  completed_at    TIMESTAMPTZ,
  trello_card_id  TEXT,                        -- sincronizacion con Trello
  tags            TEXT[] NOT NULL DEFAULT '{}',
  metadata        JSONB NOT NULL DEFAULT '{}'::jsonb,
  created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  updated_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_tasks_campaign ON tasks(campaign_id);
CREATE INDEX idx_tasks_assignee ON tasks(assignee_id);
CREATE INDEX idx_tasks_status ON tasks(status);
CREATE INDEX idx_tasks_due ON tasks(due_date);

-- ---------- Forms (formularios dinamicos) ----------
CREATE TABLE forms (
  id              UUID PRIMARY KEY DEFAULT extensions.uuid_generate_v4(),
  code            TEXT NOT NULL UNIQUE,        -- 'microinfluencer_report_v1'
  title           TEXT NOT NULL,
  description     TEXT,
  schema          JSONB NOT NULL,               -- definicion de campos
  is_active       BOOLEAN NOT NULL DEFAULT TRUE,
  target_tier     influencer_tier,             -- NULL = todos
  created_by      UUID REFERENCES users(id) ON DELETE SET NULL,
  created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  updated_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

COMMENT ON TABLE forms IS 'Definiciones de formularios dinamicos (PULL, Reporte de contenido, etc.)';

-- ---------- Form Submissions (respuestas) ----------
CREATE TABLE form_submissions (
  id              UUID PRIMARY KEY DEFAULT extensions.uuid_generate_v4(),
  form_id         UUID NOT NULL REFERENCES forms(id) ON DELETE CASCADE,
  campaign_id     UUID REFERENCES campaigns(id) ON DELETE SET NULL,
  influencer_id   UUID REFERENCES influencers(id) ON DELETE SET NULL,
  submitter_email TEXT,
  submitter_name  TEXT,
  payload         JSONB NOT NULL,               -- respuestas
  submitted_at    TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  processed       BOOLEAN NOT NULL DEFAULT FALSE,
  processed_at    TIMESTAMPTZ,
  processed_by    UUID REFERENCES users(id) ON DELETE SET NULL
);

CREATE INDEX idx_form_submissions_form ON form_submissions(form_id);
CREATE INDEX idx_form_submissions_campaign ON form_submissions(campaign_id);

-- ---------- Automations (reglas tipo IF-THEN) ----------
CREATE TABLE automations (
  id              UUID PRIMARY KEY DEFAULT extensions.uuid_generate_v4(),
  code            TEXT NOT NULL UNIQUE,
  name            TEXT NOT NULL,
  description     TEXT,
  trigger_type    TEXT NOT NULL,               -- 'status_change', 'kpi_threshold', 'form_submitted'
  trigger_config  JSONB NOT NULL DEFAULT '{}'::jsonb,
  conditions      JSONB NOT NULL DEFAULT '[]'::jsonb,  -- array de condiciones
  actions         JSONB NOT NULL DEFAULT '[]'::jsonb,  -- array de acciones
  is_active       BOOLEAN NOT NULL DEFAULT TRUE,
  last_run_at     TIMESTAMPTZ,
  run_count       INTEGER NOT NULL DEFAULT 0,
  created_by      UUID REFERENCES users(id) ON DELETE SET NULL,
  created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  updated_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- ---------- Automation Logs ----------
CREATE TABLE automation_logs (
  id              UUID PRIMARY KEY DEFAULT extensions.uuid_generate_v4(),
  automation_id   UUID NOT NULL REFERENCES automations(id) ON DELETE CASCADE,
  campaign_id     UUID REFERENCES campaigns(id) ON DELETE SET NULL,
  trigger_payload JSONB NOT NULL DEFAULT '{}'::jsonb,
  actions_executed JSONB NOT NULL DEFAULT '[]'::jsonb,
  status          TEXT NOT NULL,               -- 'success', 'partial', 'failed'
  error           TEXT,
  executed_at     TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_automation_logs_automation ON automation_logs(automation_id, executed_at DESC);

-- ---------- Triggers ----------
CREATE TRIGGER trg_budgets_updated_at BEFORE UPDATE ON budgets
  FOR EACH ROW EXECUTE FUNCTION public.set_updated_at();
CREATE TRIGGER trg_budget_items_updated_at BEFORE UPDATE ON budget_items
  FOR EACH ROW EXECUTE FUNCTION public.set_updated_at();
CREATE TRIGGER trg_tasks_updated_at BEFORE UPDATE ON tasks
  FOR EACH ROW EXECUTE FUNCTION public.set_updated_at();
CREATE TRIGGER trg_forms_updated_at BEFORE UPDATE ON forms
  FOR EACH ROW EXECUTE FUNCTION public.set_updated_at();
CREATE TRIGGER trg_automations_updated_at BEFORE UPDATE ON automations
  FOR EACH ROW EXECUTE FUNCTION public.set_updated_at();