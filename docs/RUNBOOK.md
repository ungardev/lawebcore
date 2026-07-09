# Runbook - La Web Core

> Guia operativa para despliegue, monitoreo, troubleshooting y mantenimiento.

---

## Despliegue a produccion

### Pre-requisitos
1. Proyecto Supabase creado en [supabase.com](https://supabase.com) (region recomendada: South America - Sao Paulo)
2. Proyecto en [railway.app](https://railway.app) conectado al repo
3. Proyecto en [vercel.com](https://vercel.com) conectado al repo
4. Cuenta en [openai.com](https://openai.com) (o Anthropic) con API key

### Paso 1: Base de datos (Supabase)
```bash
# Conectar a la DB remota
psql "$DATABASE_URL_SYNC" -f supabase/migrations/00000000000001_extensions.sql
psql "$DATABASE_URL_SYNC" -f supabase/migrations/00000000000002_enums.sql
# ... aplicar 03 al 11 en orden ...
psql "$DATABASE_URL_SYNC" -f supabase/seed.sql
psql "$DATABASE_URL_SYNC" -f supabase/seed_excel_data.sql
```

O via Supabase CLI (preferido):
```bash
supabase link --project-ref <your-ref>
supabase db push
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
   - `VITE_SUPABASE_URL`: URL del proyecto Supabase
   - `VITE_SUPABASE_ANON_KEY`: anon key
   - `VITE_APP_NAME`: "La Web Core"

### Paso 4: Crear primer usuario admin
1. Registrar usuario via Supabase Auth (ej: `admin@lawebfigital.com`)
2. En SQL Editor de Supabase, ejecutar:
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
- Supabase: tab "Logs" del proyecto

### Metricas clave a observar
- API latency p95, p99
- Error rate (5xx)
- DB connections activas
- Redis memory
- LLM API spend (OpenAI/Anthropic)

---

## Troubleshooting comun

### "Invalid token" al hacer login
- Verificar que `SUPABASE_JWT_SECRET` en el backend coincida con el del proyecto Supabase
- Verificar que `SUPABASE_URL` y `SUPABASE_ANON_KEY` esten correctos en el frontend

### RLS denegando acceso a datos propios
- Verificar que el usuario tenga al menos un rol en `user_roles`
- Verificar la policy RLS de la tabla especifica (`SELECT * FROM pg_policies WHERE tablename = 'X'`)
- Probar con `SET LOCAL role authenticated; SET LOCAL request.jwt.claims TO '{"sub": "...", ...}';` en psql

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

### Backup diario de DB (Supabase)
Supabase Cloud hace backups automaticos diarios en planes Pro+. Para Point-in-time Recovery:
- Dashboard > Database > Backups > Enable PITR

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
- Cada 90 dias rotar `SUPABASE_SERVICE_ROLE_KEY`, `SUPABASE_JWT_SECRET`
- Cada 180 dias rotar `OPENAI_API_KEY`, `HYPEAUDITOR_API_KEY`
- Usar Railway secrets (no commitear .env)

### Auditoria
- Toda accion queda en `audit_logs`
- Admin puede ver en `/audit` (futuro modulo)

---

## Contacto operativo

- **Owner**: equipo de Producto La Web
- **Tech Lead**: Dainer Calderon
- **Soporte**: admin@lawebfigital.com