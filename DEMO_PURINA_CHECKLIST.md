# DEMO EXECUTION CHECKLIST — Purina Dog Chow × Influencer Lens
**Fecha:** Martes 28 Julio 2026
**Cliente:** Nestlé Venezuela / Purina Dog Chow
**URL:** https://lawebcore-production.up.railway.app
**Repo:** `Lawebfigitalagency/lawebcore` @ `2c63397`

---

## FASE 0 — Verificación Pre-Demo (30 min antes)

### 0.1 Verificar que CEO instaló los actores faltantes (esperado: 7:30am)
WhatsApp a Jhon Da Silva: "¿Pudiste instalar los actors en console.apify.com?"
- [ ] `apify~instagram-hashtag-scraper` — 200 OK (ya estaba)
- [ ] `apify~instagram-search-scraper` — 200 OK (ya estaba)
- [ ] `easyapi~instagram-profile-engagement-analytics` — verificar instalación
- [ ] `bebity~instagram-profile-analytics` — verificar instalación (opcional)

### 0.2 Verificar Railway deploy
```bash
curl -I https://lawebcore-production.up.railway.app/api/v1/health
```
Esperado: `200 OK`
- [ ] Railway OK

### 0.3 Verificar que el nuevo código está deployado
Revisar Railway logs → buscar `2c63397` o buscar en logs:
```
grep "INSTAGRAM_HASHTAG_SCRAPER" /dev/null  # busca en logs el actor ID corregido
```
O verificar que los logs muestran `apify~instagram-hashtag-scraper` (con tilde).

---

## FASE 1 — Warm-up del Sistema (45 min antes)

### 1.1 Health check completo
```bash
curl -s https://lawebcore-production.up.railway.app/api/v1/health | python3 -m json.tool
```
Esperado: `{"status":"ok", "workers":...}`

### 1.2 Login como CEO admin
```python
# POST /auth/v1/token?grant_type=password
# Body: {"email": "ungar.villamizar@hacemosloquenosgusta.com", "password": "TuPasswordSegura2026!"}
```
JWT guardado para usar en todos los requests.

### 1.3 Limpiar runs anteriores (opcional pero recomendado)
```bash
# GET /api/v1/discovery/runs para ver runs activos
# DELETE o marcar como obsolete si hay runs failed pegados
```

---

## FASE 2 — Ejecución del Pipeline (30 min antes)

### 2.1 Trigger pipeline Purina desde Postman/Thunder Client

**POST** `https://lawebcore-production.up.railway.app/api/v1/discovery/search`

**Headers:**
```
Authorization: Bearer <JWT>  ← usar token del login en 1.2
Content-Type: application/json
```

**Body:**
```json
{
  "product_name": "Purina Dog Chow",
  "industry": "pet_food",
  "niches": ["mascotas", "perros"],
  "audience_countries": ["VE"],
  "audience_cities": ["Caracas", "Valencia"],
  "platforms": ["instagram"],
  "audience_gender": "all",
  "audience_age_min": 18,
  "audience_age_max": 45,
  "budget_usd": 5000,
  "tone": "warm and authentic"
}
```

**Respuesta esperada:** `201 Created` con `{"id": "uuid", "status": "queued"}`

Guardar el `run_id`Returned.

### 2.2 Monitorear progreso en Railway logs
```bash
# Railway dashboard → production app → logs
# Buscar:
#   - "step1_keyword_discovery_done"
#   - "step2_hashtag_deep_dive_done"
#   - "step3_profile_enrichment_done"
#   - "step4_analytics_done" O "step4_analytics_skipped"
#   - "candidates_filtered"
#   - "discovery_run_completed"
```

**Timeline esperado:**
- STEP 1 (keywords): 30-60s
- STEP 2 (hashtags): 60-120s
- STEP 3 (enrichment): 90-180s
- STEP 4 (analytics): 60-120s (puede ser SKIPPED si actor no está)
- Scoring + insert: 30-60s
- **Total: 5-10 minutos**

### 2.3 Polling del run status
**GET** `https://lawebcore-production.up.railway.app/api/v1/discovery/runs/{run_id}`

Buscar en respuesta:
```json
{
  "status": "completed",
  "total_candidates": > 0,
  "actual_cost_usd": < 5.00
}
```

---

## FASE 3 — Verificación de Resultados (10 min antes)

### 3.1 Verificar candidatos en DB
**GET** `https://lawebcore-production.up.railway.app/api/v1/discovery/runs/{run_id}/candidates?min_score=15&limit=20`

**Respuesta esperada:** Lista de 5-20 candidatos con:
```json
{
  "handle": "nombre_perfil",
  "followers": 5000-100000,
  "engagement_rate": 0.02-0.10,
  "match_score": 15-85,
  "country": "VE",
  "rationale": "Perfil MICRO de mascotas en VE. ER 3.2%, 12,500 seguidores..."
}
```

### 3.2 Verificar métricas agregadas
**GET** `https://lawebcore-production.up.railway.app/api/v1/discovery/metrics`

Esperado: `avg_cost_per_run` mostrar el costo real de esta ejecución.

### 3.3 Verificar logs de cada STEP en Railway
Buscar en Railway logs:
```
[Step 1] step1_keyword_discovery_done  users_found=N
[Step 2] step2_hashtag_deep_dive_done  hashtags_scraped=N  total_posts=N
[Step 3] step3_profile_enrichment_done  enriched=N
[Step 4] step4_analytics_done O step4_analytics_skipped
```

---

## FASE 4 — BACKUP: Script Standalone (si pipeline falla)

**Si después de 12 min el pipeline no completa**, ejecutar script de respaldo:

```bash
cd /mnt/c/Users/Dainer/Documents/proyectoslaweb/lawebcore

# Obtener DATABASE_URL desde Railway vars
export DATABASE_URL="postgresql://..."   # desde Railway env vars
export APIFY_API_KEY="<APIFY_API_KEY>"  # desde Railway env vars

python scripts/extract_purina_real_apify.py
```

**Resultado:** 15-18 candidatos en `discovery_candidates` en ~5 min.

---

## FASE 5 — Demo en Vivo con Nestlé

### Qué mostrar:
1. **Brief input** — pantalla del JSON con Purina Dog Chow
2. **Pipeline en ejecución** — Railway logs en tiempo real (si hay projector)
3. **Resultados** — Lista de candidatos en Influencer Lens UI
   - Top 5 candidatos con handle, followers, ER, match_score
   - Explicar LWFA Scoring: ICA, Geo-Foco, Velocity, Business Intent
4. **Costo real** — Mostrar `actual_cost_usd` del run = ~$0.50-$3.00
5. **Comparativa** — "Sin el sistema: $200-500 en herramientas. Con Influencer Lens: $0.50"

### Qué decir:
> "En 5 minutos encontramos 18 perfiles nano y micro en Venezuela con engagement rate real verificado — sin herramientas externas, sin Excel, sin intuición."

---

## ESCENARIOS DE FALLO Y RESPUESTA

| Problema | Causa | Respuesta |
|---|---|---|
| 404 en STEP 2 | Actor ID mal | Commit `2c63397` ya lo corrige — esperar redeploy |
| STEP 4 falla con 404 | Actor no instalado | Normal — STEP 4 es opcional; pipeline usa datos de STEP 3 |
| Pipeline timeout (>15 min) | Redis/ARQ lento | Usar script standalone como backup |
| 0 candidatos | Todos los perfiles filtrados | Reducir MIN_SCORE a 5 en worker.py línea 324 |
| Railway down | Deploy fallido | Railway dashboard → restart |
| Apify rate limit | Demasiadas llamadas | Esperar 5 min, reintentar |

---

## COMANDOS ÚTILES DURANTE DEMO

```bash
# Health check rápido
curl -s https://lawebcore-production.up.railway.app/api/v1/health

# Ver último run
curl -s "https://lawebcore-production.up.railway.app/api/v1/discovery/runs?order=created_at.desc&limit=1" \
  -H "Authorization: Bearer <JWT>"

# Ver candidatos del último run
RUN_ID="<uuid_del_ultimo_run>"
curl -s "https://lawebcore-production.up.railway.app/api/v1/discovery/runs/$RUN_ID/candidates?min_score=10&limit=10" \
  -H "Authorization: Bearer <JWT>"
```

---

## CONTACTO DE EMERGENCIA

- **Jhon Da Silva (CEO Apify):** +57 XXX XXX XXXX — tiene las credenciales de Apify
- **Dainer Ungar:** 0414 XXX XXXX — tiene credenciales Railway + Supabase
- **Repo:** `Lawebfigitalagency/lawebcore` — `2c63397`
