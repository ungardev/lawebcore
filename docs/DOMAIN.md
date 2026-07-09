# Dominio - La Web Core

> Glosario de terminos del dominio de marketing de La Web Figital Agency.
> Cada termino aqui mapea a una tabla o columna del modelo de datos.

---

## Jerarquia comercial

- **Cliente (corporate)**: empresa que contrata a la agencia. Ej: NESTLE, PEPSICO, POLAR, MOVILNET, LA MONTSERRATINA.
- **Marca**: producto o sub-marca del cliente. Un cliente tiene N marcas. Ej: NESTLE tiene OREO, DOLCE GUSTO, NESTEA, NIDO.
- **Contacto de marca**: persona del cliente que recibe las propuestas y aprueba.
- **Contrato**: master agreement entre la agencia y el cliente (retainer o project-based).

## Campanas

- **Campana**: unidad minima de trabajo. Tiene cliente, marca, objetivo, duracion, presupuesto, status.
- **Objetivo de campana**: el "para que" de la campana. Valores validos:
  - `AWARENESS`: dar a conocer
  - `CONSIDERACION`: que la audiencia considere la marca
  - `CONVERSION`: que compren/contraten
  - `GESTION_DE_CRISIS`: manejar crisis reputacional
  - `BRANDING`: construir/reforzar marca
  - `LANZAMIENTO`: lanzar producto nuevo
  - `RETENCION`: fidelizar clientes existentes
- **Status de campana** (pipeline kanban):
  ```
  BRIEF → CONTACTANDO → PLAN_DE_CUENTAS → PULL → CAMPAÑA INTERNA → REPORTE → TERMINADA
                                                                              → CANCELADA
  ```
- **Tipo de campana** (campaign_type):
  - `influencers`: campana centrada eninfluencers
  - `paid_media`: campana de medios pagados
  - `evento`: evento fisico o hibrido
  - `mixto`: combinacion

## Influencers

- **Influencer**: persona externa con audiencia en redes. Tabla maestra.
- **Tier**: nivel basado en tamano de audiencia:
  - `NANO`: < 10K seguidores
  - `MICRO`: 10K - 100K
  - `MID`: 100K - 500K
  - `MACRO`: > 500K
  - `MEGA`: celebridades
  - `MIX`: combinacion de tiers en una campana
- **Nicho**: vertical de contenido del influencer (lifestyle, food, fitness, etc.)
- **Status individual en campana**: `PROPUESTO → CONTACTADO → CONFIRMADO → CONTRATADO → CONTENIDO_ENTREGADO → PAGADO`

## KPIs

- **KPI Definition**: catalogo reutilizable de metricas. Codigos canonicos:
  - `reach`: alcance total
  - `engagement`: interacciones totales
  - `engagement_rate`: ER = engagement / reach
  - `views`: visualizaciones
  - `retention`: % de retencion promedio
  - `videos_count`: numero de piezas
  - `cost_per_engagement`: CPE
- **KPI Value**: instancia concreta de un KPI para una campana en un periodo
- **Benchmark**: valor esperado (p25/p50/p75) por segmento (industry/brand/tier/objective)
- **Insight**: observacion cualitativa o cuantitativa sobre una campana
- **Formato ganador**: formato de contenido que mejor rendimiento tuvo en una campana (POV, storytelling, etc.)

## Operaciones

- **Budget**: presupuesto total de una campana, desglosado por categoria
  - Categorias: talento, produccion, medios, contingencia
- **Task**: tarea asignable a un usuario, opcionalmente ligada a una campana
- **Form**: formulario dinamico (ej: formulario de PULL, reporte de microinfluencer)
- **Form Submission**: respuesta enviada a un form
- **Automation**: regla IF-THEN (trigger + actions) que se ejecuta automaticamente

## Pipeline / Workflow

- **Trigger**: evento que dispara una automation
  - `status_change`: cambio de status de campana
  - `kpi_threshold`: KPI supera o cae debajo de umbral
  - `form_submitted`: nueva respuesta a un form
- **Action**: lo que hace la automation
  - `notify_user`: enviar notificacion
  - `send_email`: enviar email
  - `create_task`: crear tarea
  - `webhook`: llamar webhook externo
  - `ai_generate`: generar contenido con IA

## Inteligencia Artificial

- **AI Prompt**: template versionado (code + version) de prompt LLM
- **Document**: archivo indexado para RAG (brief, contrato, reporte, presentacion)
- **Document Chunk**: fragmento de documento con embedding vectorial
- **AI Conversation**: sesion de chat del usuario con el asistente
- **AI Message**: mensaje individual (user/assistant/system)
- **AI Job**: tarea async de IA (embedding, generacion, forecast, etc.)

## Business Units (BUs)

Areas/departamentos de la agencia:
- `MARKETING`: planificacion estrategica
- `CREATIVIDAD`: diseno, copy, produccion
- `INFLUENCERS`: gestion deinfluencers
- `ANALYTICS`: medicion y reportes
- `CUENTAS`: account management
- `FINANZAS`: presupuestos y operaciones
- `DIRECCION`: admin general
- `NEW_BIZ`: nuevos negocios

## Auditoria

- **Audit Log**: registro inmutable de toda accion del sistema (create, update, delete, status_change, export, etc.)

## Estados del Excel original

El Excel `HISTORIAL DE CAMPAÑAS - LA WEB.xlsx` usa algunas etiquetas de status que el sistema canonicaliza asi:

| Excel | Sistema |
|---|---|
| BRIEF | BRIEF |
| CONTACTANDO | CONTACTANDO |
| PLAN DE CUENTAS | PLAN_DE_CUENTAS |
| PULL | PULL |
| CAMPANA INTERNA | CAMPAÑA INTERNA |
| REPORTE | REPORTE |
| TERMINADA | TERMINADA |

## Tipos de link en campana

- `BRIEF`: documento del brief
- `DOCUMENTO_INDUCCION`: induccion al influencer/equipo
- `CONTRATO`: contrato firmado
- `HOOK`: propuesta de gancho creativo
- `AUTOMATIZACION`: link a automatizacion (Make, Zapier, n8n)
- `FORMULARIO`: formulario (Google Forms, Typeform, etc.)
- `PULL`: pull deinfluencers (Excel, sheet)
- `PLAN_DE_CUENTAS`: plan de cuentas
- `CAMPANA_INTERNA`: carpeta de campana interna
- `DRIVE`: carpeta de Google Drive
- `REPORTE`: reporte de campana
- `CANVA`: presentacion de Canva
- `TRELLO`: tablero de Trello
- `HYPEAUDITOR`: reporte de HypeAuditor
- `OTRO`: cualquier otro