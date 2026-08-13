# Runbook - La Web Core

> Guia operativa para despliegue, monitoreo, troubleshooting y mantenimiento.

---

## Despliegue a produccion

### Pre-requisitos
1. Railway PostgreSQL creado en [railway.app](https://railway.app) (region: cualquiera — luego se replica)
2. Proyecto en [railway.app](https://railway.app) conectado al repo (para API + workers)
3. Proyecto en [vercel.com](https://vercel.com) conectado al repo (para frontend)
4. Cuenta en [openai.com](https://openai.com) (o Anthropic) con API key

### Paso 1: Base de datos (Railway PostgreSQL)
```bash
# Conectar a la DB remota via psql
psql "$DATABASE_URL" -f supabase/migrations/00000000000001_extensions.sql
psql "$DATABASE_URL" -f supabase/migrations/00000000000002_enums.sql
# ... aplicar 03 al 11 en orden ...
psql "$DATABASE_URL" -f supabase/seed.sql
psql "$DATABASE_URL" -f supabase/seed_excel_data.sql
```

Tambien puedes aplicar todo de una vez con el schema consolidado:
```bash
psql "$DATABASE_URL" -f supabase/schema.sql
```

### Paso 2: Backend (Railway)
1. Crear servicio "api" en Railway apuntando a `apps/api/Dockerfile`
2. Crear servicio "workers" en Railway con mismo Dockerfile, comando: `arq app.worker.WorkerSettings`
3. Agregar Redis como add-on
4. Configurar variables de entorno (ver `.env.example`)
5. Primer deploy automatico via GitHub

### Paso 3: Frontend (Vercel)
1. Importar repo en Vercel
2. Root Directory: `apps/web`
3. Framework: Vite
4. Variables de entorno:
   - `VITE_API_URL`: URL publica de Railway (ej: `https://api.lawebcore.railway.app`)
   - `VITE_APP_NAME`: "La Web Core"

### Paso 4: Crear primer usuario admin
1. Obtener un token via `POST /api/v1/auth/login` con credenciales de ADMIN_TOKEN
2. EIseg SQL via psql (con `POSTGRES_URL`):
```sql
UPDATE users SET status = 'active', full_name = 'Admin General', job_title = 'Administrador' WHERE email = 'admin@tuemail.com';
INSERT INTO user_roles (user_id, role_id, granted_by)
SELECT id, (SELECT id FROM roles WHERE code = 'admin_general'), id FROM users WHERE email = 'admin@tuemail.com';
```
```sql
UPDATE users SET status = 'active', full_name = 'Admin General', job_title = 'Administrador' WHERE email = 'admin@lawebfigital.com';
INSERT INTO user_roles (user_id, role_id, granted_by)
SELECT id, (SELECT id FROM roles WHERE code = 'admin_general'), id FROM users WHERE email = 'admin@lawebfigital.com';
```

---

## Monitoreo

### Health checks
- API: `GET /api/v1/health` → 200 OK
- API + DB: `GET /api/v1/health/ready` → 200 OK con `db: ok`

### Logs
- Railway: tab "Logs" en cada servicio
- Vercel: tab "Logs" del deployment

### Metricas clave a observar
- API latency p95, p99
- Error rate (5xx)
- DB connections activas
- Redis memory
- LLM API spend (OpenAI/Anthropic)

---

## Troubleshooting comun

### "Invalid token" al hacer login
- Verificar que `ADMIN_TOKEN` en el backend sea correcto
- Verificar que el token enviado en el header `Authorization: Bearer <token>` sea valido

### RLS denegando acceso a datos propios
- La app conecta como `postgres` superuser, RLS esta deshabilitado por defecto en Railway
- Si RLS causa problemas: `ALTER TABLE <nombre> DISABLE ROW LEVEL SECURITY;`

### Embeddings no se generan
- Verificar `OPENAI_API_KEY` configurada
- Verificar que pgvector extension este habilitada
- Verificar que la tabla `document_chunks` tenga la columna `embedding` con tipo `vector(1536)`

### Workers no procesan jobs
- Verificar que el servicio "workers" este corriendo en Railway
- Verificar `ARQ_REDIS_URL` apunte al Redis interno de Railway
- Logs: `arq app.worker.WorkerSettings --verbose`

---

## Backup y recovery

### Backup diario de DB (Railway PostgreSQL)
Railway PostgreSQL hace backups automaticos. Para Point-in-time Recovery:
- Railway Dashboard > PostgreSQL > Backups > Enable PITR

### Backup manual
```bash
pg_dump "$DATABASE_URL_SYNC" > backup_$(date +%Y%m%d).sql
```

---

## Actualizaciones

### Aplicar nueva migracion
1. Crear archivo en `supabase/migrations/` con timestamp mayor al ultimo
2. Hacer PR, mergear a main
3. Railway re-deploya automaticamente
4. Aplicar manualmente la nueva migracion a la DB:
   ```bash
   psql "$DATABASE_URL_SYNC" -f supabase/migrations/00000000000012_nueva.sql
   ```

### Rollback
1. Revertir el PR en GitHub
2. Aplicar migracion de rollback (si existe)
3. Si es emergencia, restaurar backup `pg_dump`

---

## Seguridad

### Rotacion de secrets
- Cada 90 dias rotar `POSTGRES_SERVICE_KEY`
- Cada 180 dias rotar `OPENAI_API_KEY`, `HYPEAUDITOR_API_KEY`, `ADMIN_TOKEN`
- Usar Railway secrets (no commitear .env)

### Auditoria
- Toda accion queda en `audit_logs`
- Admin puede ver en `/audit` (futuro modulo)

---

## Contacto operativo

- **Owner**: equipo de Producto La Web
- **Tech Lead**: Dainer Calderon
- **Soporte**: admin@lawebfigital.com