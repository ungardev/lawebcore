-- =================================================================
-- LA WEB CORE - Seed data: Business Units, Roles, Permissions
-- =================================================================
-- This file seeds the system with the foundational data.
-- The Excel historical data is loaded via scripts/etl_excel.py

-- =================================================================
-- Business Units (areas / departamentos de la agencia)
-- =================================================================
INSERT INTO business_units (id, code, name, description) VALUES
  ('00000000-0000-0000-0000-000000000001', 'MARKETING',  'Marketing & Estrategia',         'Planificacion estrategica y conceptual de campanas'),
  ('00000000-0000-0000-0000-000000000002', 'CREATIVIDAD','Creatividad & Contenido',       'Diseno, copy, produccion de contenido'),
  ('00000000-0000-0000-0000-000000000003', 'INFLUENCERS','Influencers & Talento',         'Gestion deinfluencers, PULL, contratos y liaison'),
  ('00000000-0000-0000-0000-000000000004', 'ANALYTICS',  'Analytics & KPIs',              'Medicion, benchmarks, insights, reportes'),
  ('00000000-0000-0000-0000-000000000005', 'CUENTAS',    'Cuentas & Cliente',             'Relacion con clientes y account management'),
  ('00000000-0000-0000-0000-000000000006', 'FINANZAS',   'Finanzas & Operaciones',        'Presupuestos, contratos, facturacion, margen'),
  ('00000000-0000-0000-0000-000000000007', 'DIRECCION',  'Direccion General',             'Admin General y decisiones estrategicas'),
  ('00000000-0000-0000-0000-000000000008', 'NEW_BIZ',    'New Business',                  'Prospeccion y desarrollo de nuevos clientes')
ON CONFLICT (id) DO NOTHING;

-- =================================================================
-- Roles del sistema
-- =================================================================
INSERT INTO roles (id, code, name, description, is_system) VALUES
  ('10000000-0000-0000-0000-000000000001', 'admin_general',     'Administrador General',     'Acceso total al sistema, todas las BUs', TRUE),
  ('10000000-0000-0000-0000-000000000002', 'director_bu',       'Director de BU',            'Direccion de un area, aprueba presupuestos y campanas', TRUE),
  ('10000000-0000-0000-0000-000000000003', 'project_manager',   'Project Manager',           'Gestiona campanas de inicio a fin, asigna tareas', TRUE),
  ('10000000-0000-0000-0000-000000000004', 'account_manager',   'Account Manager',           'Relacion con clientes, briefs, feedback', TRUE),
  ('10000000-0000-0000-0000-000000000005', 'analista',          'Analista de Datos',          'Carga KPIs, genera reportes, benchmarks', TRUE),
  ('10000000-0000-0000-0000-000000000006', 'creativo',          'Creativo / Disenador',      'Sube assets, participa en campanas', TRUE),
  ('10000000-0000-0000-0000-000000000007', 'influencer_liaison','Influencer Liaison',        'Contacto, contratacion y gestion deinfluencers', TRUE),
  ('10000000-0000-0000-0000-000000000008', 'finance',           'Finanzas',                  'Presupuestos, facturas, pagos, margen', TRUE),
  ('10000000-0000-0000-0000-000000000009', 'cliente_externo',   'Cliente Externo',           'Vista de solo lectura sobre sus propias campanas', TRUE),
  ('10000000-0000-0000-0000-000000000010', 'viewer',            'Visualizador',              'Solo lectura, sin edicion', TRUE)
ON CONFLICT (id) DO NOTHING;

-- =================================================================
-- Permissions (catalogo base)
-- =================================================================
INSERT INTO permissions (code, resource, action, description) VALUES
  -- campaigns
  ('campaigns.read',         'campaigns',         'read',    'Ver campanas'),
  ('campaigns.create',       'campaigns',         'create',  'Crear campanas'),
  ('campaigns.update',       'campaigns',         'update',  'Editar campanas'),
  ('campaigns.delete',       'campaigns',         'delete',  'Eliminar campanas'),
  ('campaigns.export',       'campaigns',         'export',  'Exportar campanas'),
  -- clients / brands
  ('clients.read',           'clients',           'read',    'Ver clientes'),
  ('clients.manage',         'clients',           'update',  'Gestionar clientes'),
  ('brands.read',            'brands',            'read',    'Ver marcas'),
  ('brands.manage',          'brands',            'update',  'Gestionar marcas'),
  -- influencers
  ('influencers.read',       'influencers',       'read',    'Ver influencers'),
  ('influencers.create',     'influencers',       'create',  'Crear influencers'),
  ('influencers.update',     'influencers',       'update',  'Editar influencers'),
  ('influencers.delete',     'influencers',       'delete',  'Eliminar influencers'),
  -- kpis
  ('kpis.read',              'kpis',              'read',    'Ver KPIs'),
  ('kpis.create',            'kpis',              'create',  'Registrar KPIs'),
  ('kpis.update',            'kpis',              'update',  'Editar KPIs'),
  ('kpis.export',            'kpis',              'export',  'Exportar KPIs'),
  -- budgets
  ('budgets.read',           'budgets',           'read',    'Ver presupuestos'),
  ('budgets.manage',         'budgets',           'update',  'Gestionar presupuestos'),
  -- tasks
  ('tasks.read',             'tasks',             'read',    'Ver tareas'),
  ('tasks.create',           'tasks',             'create',  'Crear tareas'),
  ('tasks.update',           'tasks',             'update',  'Editar tareas'),
  ('tasks.assign',           'tasks',             'assign',  'Asignar tareas'),
  -- workflows
  ('workflows.read',         'workflows',         'read',    'Ver workflows'),
  ('workflows.manage',       'workflows',         'update',  'Gestionar workflows'),
  -- ai
  ('ai.use',                 'ai',                'read',    'Usar asistente IA'),
  ('ai.manage',              'ai',                'update',  'Gestionar prompts y modelos IA'),
  -- admin
  ('users.read',             'users',             'read',    'Ver usuarios'),
  ('users.manage',           'users',             'update',  'Gestionar usuarios y roles'),
  ('integrations.manage',    'integrations',      'update',  'Gestionar integraciones'),
  ('audit.read',             'audit_logs',        'read',    'Ver logs de auditoria')
ON CONFLICT (code) DO NOTHING;

-- =================================================================
-- Role <-> Permissions (matriz base)
-- =================================================================

-- admin_general: ALL
INSERT INTO role_permissions (role_id, permission_id)
SELECT r.id, p.id
FROM roles r CROSS JOIN permissions p
WHERE r.code = 'admin_general'
ON CONFLICT DO NOTHING;

-- director_bu: todo menos audit, integrations, users.manage
INSERT INTO role_permissions (role_id, permission_id)
SELECT r.id, p.id
FROM roles r, permissions p
WHERE r.code = 'director_bu'
  AND p.code NOT IN ('users.manage', 'integrations.manage', 'audit.read')
ON CONFLICT DO NOTHING;

-- project_manager
INSERT INTO role_permissions (role_id, permission_id)
SELECT r.id, p.id
FROM roles r, permissions p
WHERE r.code = 'project_manager'
  AND p.code IN (
    'campaigns.read','campaigns.create','campaigns.update','campaigns.export',
    'clients.read','brands.read','brands.manage',
    'influencers.read','influencers.create','influencers.update',
    'kpis.read','kpis.create','kpis.update','kpis.export',
    'tasks.read','tasks.create','tasks.update','tasks.assign',
    'budgets.read',
    'workflows.read',
    'ai.use',
    'users.read'
  )
ON CONFLICT DO NOTHING;

-- account_manager
INSERT INTO role_permissions (role_id, permission_id)
SELECT r.id, p.id
FROM roles r, permissions p
WHERE r.code = 'account_manager'
  AND p.code IN (
    'campaigns.read','campaigns.create','campaigns.update','campaigns.export',
    'clients.read','clients.manage','brands.read','brands.manage',
    'influencers.read',
    'kpis.read','kpis.export',
    'tasks.read','tasks.create','tasks.update','tasks.assign',
    'ai.use',
    'users.read'
  )
ON CONFLICT DO NOTHING;

-- analista
INSERT INTO role_permissions (role_id, permission_id)
SELECT r.id, p.id
FROM roles r, permissions p
WHERE r.code = 'analista'
  AND p.code IN (
    'campaigns.read','campaigns.export',
    'clients.read','brands.read',
    'influencers.read',
    'kpis.read','kpis.create','kpis.update','kpis.export',
    'budgets.read',
    'workflows.read','workflows.manage',
    'ai.use'
  )
ON CONFLICT DO NOTHING;

-- creativo
INSERT INTO role_permissions (role_id, permission_id)
SELECT r.id, p.id
FROM roles r, permissions p
WHERE r.code = 'creativo'
  AND p.code IN (
    'campaigns.read',
    'clients.read','brands.read',
    'influencers.read',
    'tasks.read','tasks.update',
    'ai.use'
  )
ON CONFLICT DO NOTHING;

-- influencer_liaison
INSERT INTO role_permissions (role_id, permission_id)
SELECT r.id, p.id
FROM roles r, permissions p
WHERE r.code = 'influencer_liaison'
  AND p.code IN (
    'campaigns.read','campaigns.update',
    'clients.read','brands.read',
    'influencers.read','influencers.create','influencers.update','influencers.delete',
    'kpis.read',
    'tasks.read','tasks.create','tasks.update',
    'ai.use'
  )
ON CONFLICT DO NOTHING;

-- finance
INSERT INTO role_permissions (role_id, permission_id)
SELECT r.id, p.id
FROM roles r, permissions p
WHERE r.code = 'finance'
  AND p.code IN (
    'campaigns.read','campaigns.export',
    'clients.read','brands.read',
    'budgets.read','budgets.manage',
    'kpis.read','kpis.export',
    'ai.use'
  )
ON CONFLICT DO NOTHING;

-- cliente_externo: solo lectura de lo suyo
INSERT INTO role_permissions (role_id, permission_id)
SELECT r.id, p.id
FROM roles r, permissions p
WHERE r.code = 'cliente_externo'
  AND p.code IN ('campaigns.read')
ON CONFLICT DO NOTHING;

-- viewer
INSERT INTO role_permissions (role_id, permission_id)
SELECT r.id, p.id
FROM roles r, permissions p
WHERE r.code = 'viewer'
  AND p.code IN (
    'campaigns.read',
    'clients.read','brands.read',
    'influencers.read',
    'kpis.read',
    'budgets.read'
  )
ON CONFLICT DO NOTHING;

-- =================================================================
-- KPI Definitions (las 7 que se observaron en el Excel)
-- =================================================================
INSERT INTO kpi_definitions (code, name, description, category, unit, format_hint, higher_is_better) VALUES
  ('reach',              'Reach',              'Alcance total de la campana',                       'ALCANCE',      'count',   'integer',  TRUE),
  ('engagement',         'Engagement',         'Total interacciones (likes+comments+shares+saves)', 'ENGAGEMENT',   'count',   'integer',  TRUE),
  ('engagement_rate',    'Engagement Rate',    'ER = engagement / reach',                          'ENGAGEMENT',   'percent', 'percent',  TRUE),
  ('views',              'Views',              'Visualizaciones totales',                           'ALCANCE',      'count',   'integer',  TRUE),
  ('retention',          'Retencion',          '% de retencion promedio de videos',                 'RETENCION',    'percent', 'percent',  TRUE),
  ('videos_count',       'Cantidad de Videos', 'Numero total de piezas publicadas',                 'ALCANCE',      'count',   'integer',  TRUE),
  ('cost_per_engagement','CPE',                'Costo por interaccion',                            'CONVERSION',   'usd',     'decimal2', FALSE)
ON CONFLICT (code) DO NOTHING;

-- =================================================================
-- AI Prompts base
-- =================================================================
INSERT INTO ai_prompts (code, version, name, description, system_prompt, user_template, model_provider, model_name, temperature) VALUES
  ('brief_generator_v1', 1, 'Generador de Briefs',
   'Genera un brief estructurado a partir de cliente, marca y objetivo',
   'Eres un estratega senior de marketing de La Web Figital Agency. Tu trabajo es generar briefs profesionales, claros y accionables.',
   'Genera un brief para:
Cliente: {{client}}
Marca: {{brand}}
Objetivo: {{objective}}
Tiers de influencer: {{tiers}}
Presupuesto: {{budget}}
Audiencia objetivo: {{audience}}

Estructura: 1) Contexto, 2) Objetivo y KPIs, 3) Audiencia, 4) Mensajes clave, 5) Mecanica, 6) Timeline sugerido, 7) Entregables esperados.',
   'deepseek', 'deepseek-chat', 0.7),

  ('post_mortem_v1', 1, 'Post-Mortem de Campana',
   'Genera el post-mortem ejecutivo de una campana a partir de sus KPIs',
   'Eres un analista senior de marketing. Sintetizas resultados de campanas en post-mortems ejecutivos claros.',
   'Genera el post-mortem de la campana:
Nombre: {{campaign_name}}
Cliente/Marca: {{client_brand}}
Objetivo: {{objective}}
Status: {{status}}
KPI values: {{kpis}}
Insights: {{insights}}
Formato ganador: {{winning_format}}

Estructura: 1) Resumen ejecutivo (3 lineas), 2) Resultado vs objetivo, 3) Top 3 wins, 4) Top 3 aprendizados, 5) Recomendaciones para la proxima.',
   'deepseek', 'deepseek-chat', 0.5),

  ('rag_system_v1', 1, 'RAG - Asistente La Web Core',
   'Prompt del sistema para el asistente IA conversacional con RAG',
   'Eres el asistente IA de La Web Core, la plataforma interna de La Web Figital Agency. Respondes con base en la base de conocimiento de la agencia (campanas, briefs, contratos, reportes, KPIs). Si no sabes algo, lo dices claramente. Citas siempre las fuentes con links. Hablas espanol profesional venezolano.',
   'Contexto de la conversacion: {{context}}
Historial: {{history}}
Pregunta del usuario: {{question}}
Fragmentos relevantes recuperados: {{chunks}}',
   'deepseek', 'deepseek-chat', 0.4)
 ON CONFLICT (code, version) DO NOTHING;