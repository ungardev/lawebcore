# Plan — Continuación en Casa

**Última actualización:** sábado 19 julio 2026, ~02:45 VET
**Usuario:** Dainer Ungar — CEO La Web Figital Agency
**Deadline:** Lunes 21 julio 2026, 9:00 AM Caracas

---

## Lo que se hizo (sesión anterior)

### Fixes aplicados y commiteados (commit `2051ca4`)

1. **`preload-demo` 500修复 — causa raíz: 409 Conflict por FK violada**
   - El endpoint usaba UUIDs fake para `user_id` (`00000000-0000-0000-0000-000000000000`) que no existen en la tabla `users`
   - Fix: ahora hace `SELECT id FROM users LIMIT 1` dinámico antes de insertar las conversaciones
   - También envolvió cada `insert` en try/except con `logger.warning` para no morir en una conversación individual

2. **`enrich-influencers` 500修复 — causa raíz: `profiles is None` antes de iterar**
   - Apify retorna `None` cuando no encuentra un handle → `for profile in profiles` crashea con `TypeError`
   - Fix: `if profiles is None: continue` + logging + error result appendado a la lista
   - También redujo `batch_size` de 5 a 3 para evitar timeouts de Railway (60s)
   - Todo el endpoint ahora es try/except completo → nunca más 500, solo respuestas con `success: false` y `error` en el result

3. **Push a GitHub → Railway redeploy automático** (~3 min)

---

## Lo que hay que hacer (continuar en casa)

### 1. Esperar redeploy de Railway (~3-5 min desde el push)

Verificar que Railway terminó el redeploy:
```bash
curl https://lawebcore-api-production.up.railway.app/api/v1/health
```
Debe responder `200 OK`.

### 2. Correr los 3 admin endpoints en orden

```bash
# 2a. Seed RAG knowledge base (ya funcionaba, pero se puede repetir)
curl -X POST https://lawebcore-api-production.up.railway.app/api/v1/admin/seed-rag \
  -H "X-Admin-Token: laweb-admin-token-2026" \
  -H "Content-Type: application/json"

# 2b. Preload demo conversations (AHORA DEBE FUNCIONAR)
curl -X POST https://lawebcore-api-production.up.railway.app/api/v1/admin/preload-demo \
  -H "X-Admin-Token: laweb-admin-token-2026" \
  -H "Content-Type: application/json"

# 2c. Enrich influencers (verificar que no crashea, puede tomar varios minutos)
curl -X POST https://lawebcore-api-production.up.railway.app/api/v1/admin/enrich-influencers \
  -H "X-Admin-Token: laweb-admin-token-2026" \
  -H "Content-Type: application/json" \
  -d '{"all_active": true}'
```

### 3. Verificar enrichment en Supabase

Después de que `enrich-influencers` termine (puede tardar 5-10 min), verificar que los campos se actualizaron:

```sql
SELECT id, full_name, primary_handle, followers, engagement_rate, audience_credibility
FROM influencers
WHERE status = 'active'
ORDER BY followers DESC NULLS LAST
LIMIT 20;
```

Si `followers` y `engagement_rate` tienen valores reales (no null), el enrichment funcionó.

### 4. Verificar demo conversations en el frontend

1. Ir a https://lawebcore.vercel.app/influencer-lens
2. En el sidebar de conversaciones, deberían aparecer 3 conversaciones demo:
   - "Brief Purina Dog Chow — Amor Perruno"
   - "Analisis Campaña Activa — #DogChowVenezuela"
   - "Proyeccion Q4 — Nueva Campana"
3. Hacer clic en cada una y verificar que se ven los mensajes con tool_calls y reasoning visibles

### 5. Verificar RAG funcionando

En Influencer Lens, hacer una pregunta que requiera la knowledge base:

```
Pregunta: "¿Cuál fue el caso de éxito de Purina Dog Chow en 2025?"
```

Debería citar información del documento "Caso de Éxito — Campaña Purina Dog Chow VE 2025" (Amor Perruno, 2.3M reach, ER 6.8%).

---

## Posibles problemas y soluciones rápidas

### Railway redeploy falla o no termina
- Ir a https://railway.app/dashboard → proyecto `lawebcore-api` → Deploys
- Hacer click en el deploy activo → "Redeploy"

### Apify API key no funciona (enrich devuelve todos failed)
- Verificar en Railway: Variables de entorno → `APIFY_API_KEY`
- Si está vacío o es incorrecto, añadir la API key de Apify
- Redeploy después de actualizar

### Demo conversations no aparecen en el sidebar
- Puede ser problema de cache del frontend
- Hacer hard refresh: `Ctrl+Shift+R` o `Cmd+Shift+R`
- O ir a https://lawebcore.vercel.app y hacer logout/login

### Frontend no conecta con API
- Verificar que `NEXT_PUBLIC_API_BASE_URL` en Vercel apunta a `https://lawebcore-api-production.up.railway.app`
- En Vercel → Settings → Environment Variables

---

## Estado actual conocido

| Componente | Estado |
|---|---|
| Railway API (health) | ✅ 200 OK |
| Vercel Frontend | ✅ 200 OK |
| `/admin/seed` (49 influencers) | ✅ Funciona |
| `/admin/seed-rag` (16 chunks) | ✅ Funciona |
| `/admin/preload-demo` | 🔧 Fixeado (commiteado, redeploy en curso) |
| `/admin/enrich-influencers` | 🔧 Fixeado (commiteado, redeploy en curso) |
| Demo conversations visibles en frontend | ⏳ Esperando preload-demo |
| 49 influencers con datos de Apify | ⏳ Esperando enrich |
| RAG knowledge base queries | ⏳ Esperando seed-rag + fix |

---

## Checklist final para el pitch (lunes 9am)

- [ ] Demo conversations visibles en sidebar de Influencer Lens
- [ ] Al hacer clic en cada conversación, se ven los mensajes con tool_calls y reasoning
- [ ] 49 influencers enrichnecidos con datos reales de Instagram (followers, ER)
- [ ] Al hacer una pregunta sobre Purina Dog Chow, el RAG cita documentos de la knowledge base
- [ ] Thinking indicator (pulsing dots) aparece mientras espera respuesta
- [ ] Cost badge muestra USD por cada turno
- [ ] InfluencerTable muestra los 10 mejores influencers con MatchScoreCircle
- [ ] No hay errores 500 en la consola del navegador
- [ ] El logo de La Web Figital Agency se ve en el sidebar
- [ ] Footer dice "v1.0 — Purina Demo" (o sin footer si se quitó)
