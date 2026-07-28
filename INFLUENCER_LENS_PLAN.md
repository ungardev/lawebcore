# Influencer Lens — Plan de Implementación

> **Proyecto:** Influencer Lens · La Web Figital Agency
> **Demo:** Julio 28, 2026 · 2:00 PM (Nestlé Venezuela / Purina Dog Chow)
> **Cliente:** Ungar Villamizar · CEO La Web Figital Agency
> **Usuario demo:** Purina Dog Chow Venezuela — Instagram influencers perros — Madres 25-45 Caracas — $3,000 USD

---

## Estado Actual ✅

El pipeline de discovery funciona correctamente:
- 15 candidatos VE insertados en DB
- Chat responde con resumen de top 10
- worker.py usa el patrón v4 (sync calls)
- geo_boost filtra por Venezuela
- API keys activas (rotar post-demo)

**Bugs pendientes:**
- Decimales largos en MatchScoreCircle (ej: `83.38999938964844`)
- Sin tier badges
- Sin bandera VE
- Sin propuesta PDF descargable

---

## Decisiones Tomadas

| # | Decisión | Respuesta |
|---|-----------|-----------|
| 1 | Orden de ejecución | Solo Bloque A ahora (1h), demo-ready |
| 2 | PDF sin saved | Bloqueado si 0 saved — solo aparece con ≥1 |
| 3 | Detección tiendas | Estricto: 'tienda', 'shop', 'ventas', 'pedidos', 'catálogo', 'mayor y detal', 'envíos', 'mercado libre', 'delivery' |
| 4 | Audience gender | Soporta female/male/all (ya existe en schema) |
| 5 | Formato PDF | Top 10 por match_score con status='saved' |

---

## Brief Template — Guía Definitiva

```yaml
product_name: "Purina Dog Chow"
brand_id: "f0000000-0000-0000-0000-000000000002"
industry: "mascotas"
niches: ["mascotas", "perros", "pet care"]

audience_gender: "female"       # female | male | all
audience_age_min: 25
audience_age_max: 45
audience_countries: ["VE"]
audience_cities: ["Caracas", "Valencia", "Maracaibo", "Mérida", "Barquisimeto"]

platforms: ["instagram"]
budget_usd: 3000
tone: ["emocional", "familiar", "authentic"]

hashtags:
  # Producto (alta conversión)
  - "purinaVE"
  - "dogchowVE"
  # Temáticos (engagement)
  - "amorporruno"
  - "mascotasVE"
  - "perrosVE"
  - "mascotasVenezuela"
  # Audiencia (target)
  - "mamapower"
  - "vzla"
  - "venezuela"
  # Genéricos (alcance)
  - "doglover"
  - "petlovers"

additional_context: |
  Campaña para madres dueñas de perros en principales ciudades de Venezuela.
  Solo creadoras de contenido individuales, NO tiendas ni marcas comerciales.
  Engagement real mayor a 0.5%. Audiencias confirmadas en VE.
```

---

## BLOQUES DE IMPLEMENTACIÓN

### BLOQUE A — Quick Wins UI + PDF (ANTES de la demo) ⚡
**Tiempo estimado: 80 minutos**

#### A1. `apps/web/src/lib/format.ts` (NUEVO)
```typescript
export function formatScore(score: number): string {
  return `${Math.round(score)}`;
}

export function formatEngagement(er: number | null): string {
  if (er == null) return "—";
  return `${(er * 100).toFixed(1)}%`;
}

export function formatFollowers(n: number | null): string {
  if (n == null) return "—";
  if (n >= 1000) return `${(n / 1000).toFixed(1)}K`;
  return String(n);
}

export function classifyTier(followers: number | null): "NANO" | "MICRO" | "MID" | "MACRO" | null {
  if (followers == null) return null;
  if (followers < 10_000) return "NANO";
  if (followers < 100_000) return "MICRO";
  if (followers < 500_000) return "MID";
  return "MACRO";
}

export function isTienda(bio: string | null): boolean {
  if (!bio) return false;
  const lower = bio.toLowerCase();
  const patrones = [
    "tienda", "shop", "ventas", "pedidos", "catálogo",
    "mayor y detal", "envíos", "mercado libre",
    "delivery", "pedidos ya", "comprar aquí", "adquirir",
  ];
  return patrones.some(p => lower.includes(p));
}
```

#### A2. `apps/web/src/features/lens/components/MatchScoreCircle.tsx`
- Línea 55: `{clampedScore}` → `{Math.round(clampedScore)}`
- Score circle muestra número entero (83 en vez de 83.389...)

#### A3. `apps/web/src/features/lens/components/CandidateCard.tsx`
**Imports a agregar:**
```typescript
import { classifyTier, isTienda } from '../lib/format';
```

**Badge tiers** (después de `<PlatformBadge platform={candidate.platform} />`):
```tsx
{candidate.tier && (
  <span className="text-[10px] px-1.5 py-0.5 rounded-full font-medium bg-brand-purple/10 text-brand-purple border border-brand-purple/20">
    {candidate.tier}
  </span>
)}
{candidate.country === 'VE' && <span className="text-sm">🇻🇪</span>}
{isTienda(candidate.bio) && (
  <span className="text-[10px] px-1.5 py-0.5 rounded-full font-medium bg-orange-100 text-orange-700 border border-orange-200">
    Tienda
  </span>
)}
```

**Followers formatting:**
```tsx
<span>{formatFollowers(candidate.followers)}</span>
```

**Engagement formatting:**
```tsx
<span>{formatEngagement(candidate.engagement_rate)}</span>
```

**Score (usa MatchScoreCircle):** Ya formateado en el componente.

#### A4. `apps/web/src/components/ui/badge.tsx`
Agregar variantes para tier y tienda si no existen.

#### A5. `apps/web/src/features/lens/types/discovery.ts`
```typescript
// En DiscoveryCandidate, agregar:
tier?: 'NANO' | 'MICRO' | 'MID' | 'MACRO' | null;
```

#### A6. `apps/api/app/api/v1/discovery.py`
**Función helper `_serialize_candidate` (antes del endpoint):**
```python
def _tier_from_followers(followers: int) -> str | None:
    if not followers:
        return None
    if followers < 10_000:
        return "NANO"
    if followers < 100_000:
        return "MICRO"
    if followers < 500_000:
        return "MID"
    return "MACRO"

_TIENDA_PATTERNS = ["tienda", "shop", "ventas", "pedidos", "catálogo",
                    "mayor y detal", "envíos", "mercado libre", "delivery",
                    "comprar aquí", "adquirir"]

def _is_tienda(bio: str) -> bool:
    if not bio:
        return False
    return any(p in bio.lower() for p in _TIENDA_PATTERNS)

def _serialize_candidate(c: dict) -> dict:
    followers = c.get("followers") or c.get("followersCount") or 0
    bio = c.get("bio") or c.get("biography") or ""
    tier = _tier_from_followers(followers)
    return {
        "id": str(c.get("id", "")),
        "platform": c.get("platform", "instagram"),
        "handle": c.get("handle", ""),
        "full_name": c.get("full_name") or c.get("fullName"),
        "avatar_url": c.get("avatar_url") or c.get("profilePicUrl"),
        "followers": int(followers),
        "engagement_rate": round(c.get("engagement_rate") or 0, 4),
        "match_score": round(c.get("match_score") or 0, 1),
        "tier": tier,
        "niche_relevance": round(c.get("niche_relevance") or 0, 2),
        "geo_relevance": round(c.get("geo_relevance") or 0, 2),
        "audience_relevance": round(c.get("audience_relevance") or 0, 2),
        "content_quality": round(c.get("content_quality") or 0, 2),
        "status": c.get("status", "new"),
        "estimated_cost": int(c.get("estimated_cost") or 0),
        "expected_reach": int(c.get("expected_reach") or 0),
        "expected_engagement": int(c.get("expected_engagement") or 0),
        "rationale": c.get("rationale"),
        "country": c.get("country"),
        "city": c.get("city"),
        "bio": bio[:300] if bio else None,
        "is_tienda": _is_tienda(bio),
    }
```

**Endpoint `/runs/{run_id}/candidates`** — usar la helper:
```python
@router.get("/runs/{run_id}/candidates")
async def list_run_candidates(run_id: str, ...):
    rows = await supabase_rest.select(
        table="discovery_candidates",
        select="*",
        filters=[f"run_id=eq.{run_id}"],
        order="match_score.desc",
        limit=limit,
        offset=offset,
    )
    return [_serialize_candidate(r) for r in rows]
```

#### A7. `apps/api/app/services/pdf_generator.py` (NUEVO)
```python
"""Generador de propuestas PDF para campaigns de influencers."""
from datetime import datetime
from io import BytesIO
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib.units import cm
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, Image
from reportlab.lib.enums import TA_CENTER, TA_LEFT

def generate_proposal_pdf(candidates: list[dict], product_name: str, brand: str = "Nestlé Venezuela") -> bytes:
    buffer = BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=A4, rightMargin=2*cm, leftMargin=2*cm)
    styles = getSampleStyleSheet()
    story = []

    # Portada
    title_style = styles['Title']
    title_style.fontSize = 28
    title_style.textColor = colors.HexColor('#1a1a2e')
    story.append(Paragraph(f"Propuesta de Influencers<br/>{product_name}", title_style))
    story.append(Spacer(1, 0.5*cm))
    story.append(Paragraph(f"<b>{brand}</b>", styles['Normal']))
    story.append(Paragraph(f"Generado: {datetime.now().strftime('%d/%m/%Y')}", styles['Normal']))
    story.append(Spacer(1, 2*cm))

    # Tabla top 10
    data = [["#", "Handle", "Seguidores", "ER", "Score", "Tier", "Ciudad"]]
    for i, c in enumerate(candidates[:10], 1):
        er_pct = f"{(c.get('engagement_rate', 0) * 100):.1f}%"
        data.append([
            str(i),
            c.get('handle', ''),
            f"{c.get('followers', 0):,}",
            er_pct,
            f"{c.get('match_score', 0):.0f}",
            c.get('tier', '—'),
            c.get('city') or '—',
        ])

    t = Table(data, colWidths=[1*cm, 4*cm, 3*cm, 2*cm, 2*cm, 2*cm, 3*cm])
    t.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), colors.HexColor('#6c47ff')),
        ('TEXTCOLOR', (0,0), (-1,0), colors.white),
        ('FONTNAME', (0,0), (-1,0), 'Helvetica-Bold'),
        ('FONTSIZE', (0,0), (-1,-1), 9),
        ('ALIGN', (0,0), (-1,-1), 'CENTER'),
        ('GRID', (0,0), (-1,-1), 0.5, colors.HexColor('#e0e0e0')),
        ('ROWBACKGROUNDS', (0,1), (-1,-1), [colors.white, colors.HexColor('#f5f5ff')]),
        ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
    ]))
    story.append(t)
    story.append(Spacer(1, 1*cm))

    # Nota
    note = styles['Normal']
    note.fontSize = 8
    note.textColor = colors.grey
    story.append(Paragraph(
        f"Total candidatos: {len(candidates)}. Datos de Instagram vía Apify. "
        f"Scores basados en engagement, geolocalización VE y relevancia de nicho.",
        note
    ))

    doc.build(story)
    return buffer.getvalue()
```

#### A8. `apps/api/app/api/v1/discovery.py` — Endpoint PDF
```python
from app.services.pdf_generator import generate_proposal_pdf

@router.get("/runs/{run_id}/proposal.pdf")
async def download_proposal_pdf(run_id: str):
    candidates = await supabase_rest.select(
        table="discovery_candidates",
        select="*",
        filters=[f"run_id=eq.{run_id}", "status=eq.saved"],
        order="match_score.desc",
        limit=10,
    )
    if not candidates:
        raise HTTPException(
            status_code=400,
            detail="No hay candidatos guardados. Guarda al menos 1 candidato primero."
        )

    run = await supabase_rest.select_one(
        table="discovery_runs", select="product_name,brief_parsed",
        filters=[f"id=eq.{run_id}"]
    )
    product_name = (run or {}).get("product_name", "Influencer Proposal")

    pdf_bytes = generate_proposal_pdf(
        [_serialize_candidate(c) for c in candidates],
        product_name=product_name,
        brand="Nestlé Venezuela / Purina",
    )

    from fastapi.responses import StreamingResponse
    import io
    return StreamingResponse(
        io.BytesIO(pdf_bytes),
        media_type="application/pdf",
        headers={
            "Content-Disposition": f"attachment; filename=propuesta_{run_id[:8]}.pdf"
        }
    )
```

#### A9. `apps/web/src/features/lens/api/lensApi.ts`
```typescript
proposal: {
  getPdfUrl: (runId: string) => `/lens/discovery/runs/${runId}/proposal.pdf`,
  checkSavedCount: async (runId: string) => {
    const { data } = await api.get(`/lens/discovery/runs/${runId}/candidates`, {
      params: { status_filter: 'saved', limit: 1 }
    });
    return Array.isArray(data) ? data.length : 0;
  },
},
```

#### A10. `apps/web/src/features/lens/components/CandidateList.tsx`
```tsx
// Agregar al header cuando hay candidatos:
const savedCount = candidates.filter(c => c.status === 'saved').length;

{savedCount > 0 && (
  <a
    href={lensApi.proposal.getPdfUrl(runId)}
    target="_blank"
    rel="noreferrer"
    className="flex items-center gap-2 px-3 py-1.5 rounded-lg bg-brand-purple text-white text-xs font-medium hover:opacity-90 transition-opacity"
  >
    <Download className="w-3.5 h-3.5" />
    Descargar propuesta PDF ({savedCount})
  </a>
)}
{candidates.length > 0 && savedCount === 0 && (
  <span className="text-xs text-muted-foreground">
    Guarda al menos 1 candidato para descargar propuesta
  </span>
)}
```

#### A11. `apps/web/src/features/lens/components/SearchProgress.tsx`
Actualizar STEP_LABELS:
```typescript
const STEP_LABELS: Record<string, string> = {
  step1_hashtag_search: "Buscando hashtags...",
  step2_keyword_search: "Buscando por keywords...",
  step3_profile_enrichment: "Enriqueciendo perfiles...",
  step4_engagement_analytics: "Analizando engagement...",
  step5_scoring: "Rankeando candidatos...",
  inserting_candidates: "Guardando candidatos...",
  completed: "Completado",
};
```

---

### BLOQUE B — Brief Wizard + Hashtags (90 min)

**Objetivo:** Reemplazar el textarea libre por un wizard visual de 6 pasos.

#### B1. `packages/discovery/discovery/schemas.py` — BriefStructured
```python
# En BriefStructured, agregar:
hashtags: list[str] = Field(default_factory=list, description="Hashtags personalizados para la búsqueda")
```

#### B2. `packages/discovery/discovery/query_builder.py`
```python
def build(self, brief: BriefStructured) -> DiscoveryPlan:
    # Usar hashtags del brief si existen, si no defaults
    hashtags = brief.hashtags if brief.hashtags else self._default_hashtags_for_vertical(brief.industry)
    keywords = brief.keywords if brief.keywords else self._default_keywords_for_vertical(brief.industry)
    # ...
```

#### B3. `apps/web/src/features/lens/components/BriefWizard.tsx` (NUEVO)
Componente React de 6 pasos:
1. **Producto** — input text para product_name, industry
2. **Nicho** — tag picker con sugerencias por industry
3. **Audiencia** — gender toggle, age range slider, countries multi-select, cities
4. **Hashtags** — `<HashtagChips />` con chips dinámicos + sugerencias
5. **Plataformas** — checkbox (Instagram, TikTok, YouTube)
6. **Review** — preview del brief estructurado

#### B4. `apps/web/src/features/lens/components/HashtagChips.tsx` (NUEVO)
- Input para agregar hashtag
- Chips con X para remover
- Sugerencias filtradas por industry (mascotas → ["purinaVE", "dogchowVE", "amorporruno", ...])

#### B5. `apps/web/src/features/lens/components/HashtagSuggestions.tsx` (NUEVO)
```typescript
const SUGGESTIONS_BY_INDUSTRY: Record<string, string[]> = {
  mascotas: ["purinaVE", "dogchowVE", "amorporruno", "mascotasVE", "perrosVE",
             "mascotasVenezuela", "dogChow", "purina", "petlovers", "doglover",
             "vzla", "venezuela", "adopcionvzla", "rescateanimalvzla"],
  belleza: ["makeupve", "skincareve", "bellezavzla", "makeuplover", ...],
  food: ["foodpornvzla", "gastronomiave", ...],
  // etc.
};
```

#### B6. `apps/web/src/features/lens/components/BriefConfirmCard.tsx`
- Mostrar sección de hashtags si `brief.hashtags?.length > 0`
- Agregar botón "Editar brief" que abre el wizard

#### B7. `apps/web/src/features/lens/pages/LensChatPage.tsx`
- Reemplazar textarea libre por `<BriefWizard />` con trigger de botón "Nueva búsqueda"
- Mantener textarea libre como fallback

---

### BLOQUE C — Nicho Inteligente (30 min)

#### C1. `packages/discovery/discovery/tools/niche_detector.py` (NUEVO)
```python
PET_KEYWORDS = ["perro", "dog", "mascota", "pet", "cachorro", "canino",
                "adopta", "rescate", "refugio", "animal", "peludo"]
FOOD_KEYWORDS = ["comida", "food", "receta", "gastronomia", "chef", ...]
BEAUTY_KEYWORDS = ["makeup", "skincare", "belleza", "cosmetico", ...]

def detect_niche_score(profile: dict, vertical: str = "mascotas") -> float:
    """Returns 0.0-1.0 based on how well profile matches vertical niche."""
    bio = (profile.get("bio") or profile.get("biography") or "").lower()
    username = (profile.get("username") or "").lower()
    keywords = {
        "mascotas": PET_KEYWORDS,
        "food": FOOD_KEYWORDS,
        "belleza": BEAUTY_KEYWORDS,
    }.get(vertical, [])

    if not keywords:
        return 0.5

    matches = sum(1 for kw in keywords if kw in bio + username)
    return min(1.0, matches / 3)
```

#### C2. `packages/discovery/discovery/tools/geo_boost.py` — composite_score
```python
def composite_score(profile: dict) -> float:
    # ... existente ...
    niche_score = detect_niche_score(profile, profile.get("vertical", "mascotas"))
    return (er * 100) + (geo * 30) + (20 if is_business else 0) + (10 if is_verified else 0) + (niche_score * 25)
```

#### C3. `apps/api/app/api/v1/discovery.py` — _serialize_candidate
```python
def _serialize_candidate(c: dict) -> dict:
    # ... existente ...
    result["niche_relevance"] = round(c.get("niche_relevance") or 0, 2)
    result["is_tienda"] = _is_tienda(bio)
    result["is_low_niche"] = detect_niche_score(c, "mascotas") < 0.2
    return result
```

---

### BLOQUE D — Demo Polish (30 min)

#### D1. `apps/web/src/features/lens/components/CandidateList.tsx`
Filtros por tier:
```tsx
const [tierFilter, setTierFilter] = useState<string>("all");
const filtered = tierFilter === "all" ? candidates : candidates.filter(c => c.tier === tierFilter);

<div className="flex gap-1">
  {["all","NANO","MICRO","MID","MACRO"].map(t => (
    <button key={t} onClick={() => setTierFilter(t)}
      className={`px-2 py-1 rounded text-xs ${tierFilter===t?"bg-brand-purple text-white":"bg-muted"}`}>
      {t === "all" ? "Todos" : t}
    </button>
  ))}
</div>
```

#### D2. `apps/web/src/features/lens/api/lensApi.ts` — search.createRun
```typescript
search: {
  createRun: async (brief: {
    // ... existente ...
    hashtags?: string[];  // AGREGAR
  }) => { ... }
}
```

#### D3. SearchProgress — Live progress
```typescript
// Polling cada 5 segundos mientras isLoading
const [progress, setProgress] = useState<RunProgress | null>(null);
useEffect(() => {
  if (!isLoading || !runId) return;
  const interval = setInterval(async () => {
    const run = await lensApi.search.getRun(runId);
    if (run.metadata?.current_step) {
      setProgress(run.metadata as RunProgress);
    }
  }, 5000);
  return () => clearInterval(interval);
}, [isLoading, runId]);
```

---

### BLOQUE E — Branding + Tier Badges (20 min)

#### E1. `apps/web/src/components/ui/badge.tsx`
```typescript
// Agregar variantes:
"tier-NANO" | "tier-MICRO" | "tier-MID" | "tier-MACRO" | "tienda"
```

#### E2. CandidateCard — mostrar badge completo
```tsx
<div className="flex items-center gap-1.5 flex-wrap">
  <PlatformBadge platform={candidate.platform} />
  {candidate.tier && <Badge variant={`tier-${candidate.tier}`}>{candidate.tier}</Badge>}
  {candidate.country === 'VE' && <span title="Venezuela">🇻🇪</span>}
  {candidate.is_tienda && <Badge variant="tienda">Tienda</Badge>}
  {candidate.is_low_niche && <Badge variant="outline">⚠️ Nicho bajo</Badge>}
</div>
```

---

## Archivos a Crear (NUEVOS)

| Archivo | Descripción |
|---------|-------------|
| `apps/web/src/lib/format.ts` | Helpers de formateo |
| `packages/discovery/discovery/tools/niche_detector.py` | Detector de nicho |
| `apps/api/app/services/pdf_generator.py` | Generador PDF |

## Archivos a Modificar

| Archivo | Cambios |
|---------|---------|
| `apps/web/src/features/lens/components/MatchScoreCircle.tsx` | Rounding de score |
| `apps/web/src/features/lens/components/CandidateCard.tsx` | format.ts + badges + VE flag + tienda |
| `apps/web/src/features/lens/components/CandidateList.tsx` | Tier filter + PDF button |
| `apps/web/src/features/lens/components/SearchProgress.tsx` | STEP_LABELS actualizado |
| `apps/web/src/features/lens/types/discovery.ts` | Agregar `tier` |
| `apps/web/src/features/lens/api/lensApi.ts` | PDF url helper |
| `apps/api/app/api/v1/discovery.py` | `_serialize_candidate` + `/proposal.pdf` |
| `packages/discovery/discovery/schemas.py` | Campo `hashtags` en BriefStructured |
| `packages/discovery/discovery/query_builder.py` | Usar `brief.hashtags` |
| `packages/discovery/discovery/tools/geo_boost.py` | Nicho score en composite |
| `apps/api/app/workers/worker.py` | Propagar tier en raw_payload |

---

## API Endpoints Clave

| Método | Path | Descripción |
|--------|------|-------------|
| GET | `/lens/discovery/runs/{id}/proposal.pdf` | PDF descargable (requiere ≥1 saved) |
| GET | `/lens/discovery/runs/{id}/candidates` | Lista de candidatos con tier + is_tienda |
| POST | `/lens/discovery/candidates/{id}/save` | Marcar candidato como saved |
| POST | `/lens/discovery/candidates/{id}/dismiss` | Descartar candidato |

---

## DB Schema — Notas

- `discovery_runs.brief_parsed` es JSONB — soporta nuevo campo `hashtags` sin migración
- `discovery_candidates` tiene campos: `match_score`, `niche_relevance`, `geo_relevance`, `engagement_rate`
- Nuevo campo `tier` se calcula on-the-fly en `_serialize_candidate`

---

## Timeline

```
[AHORA]    Bloque A: 80 min  → UI limpia + PDF descargable
[NOCHE]    Bloque B: 90 min  → Brief Wizard + Hashtag chips
[NOCHE]    Bloque C: 30 min  → Nicho inteligente
[NOCHE]    Bloque D: 30 min  → Filtros + Polish
[NOCHE]    Bloque E: 20 min  → Tier badges
─────────────────────────────────────────────
TOTAL:     4h 10min
```

---

## Vocabulario / Glosario

| Término | Significado |
|---------|-------------|
| **Tier** | Clasificación por seguidores: NANO (<10K), MICRO (<100K), MID (<500K), MACRO (≥500K) |
| **Tienda** | Cuenta comercial que vende productos (vs creador de contenido individual) |
| **VE Filter** | Filtrado estricto Venezuela: geo_score == 1.0 |
| **Composite Score** | Fórmula: ER×100 + GEO×30 + Business×20 + Verified×10 + Nicho×25 |
| **Pipeline v4** | Hashtag search (sync) → Keyword search (sync) → Profile enrichment (sync) → Scoring |

---

## Estado de Commits

| Hash | Descripción |
|------|-------------|
| 3391ab6 | fix(discovery): replicate extract_purina_real_apify.py v4 pattern |
| 566c9cb | fix(discovery): remove enhanceUserSearchWithFacebookPage field |
| e626d34 | fix(apify): searchType user (singular) |
| 568d17e | fix: add default uuid for discovery_candidates |
| 3ea488e | fix: add default uuid for discovery_runs |
| 2b56370 | fix: remove extra parenthesis syntax error worker.py |
| ... | Más commits previos |

---

## Credenciales (NO incluir en commits — usar variables de entorno)

| Servicio | Fuente |
|----------|--------|
| DeepSeek | `DEEPSEEK_API_KEY` env var |
| Apify | `APIFY_API_KEY` env var |
| Railway Postgres | `DATABASE_URL` env var |

---

*Documento creado: Julio 28, 2026 · La Web Figital Agency · Influencer Lens v2.6*
