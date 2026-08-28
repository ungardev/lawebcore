# MASTER OPTIMIZATION PROMPT — LENS BY LAWEBCORE
> **For:** Claude Code Opus 5 (Anthropic)
> **From:** La Web Figital Agency
> **Date:** 2026-07-30
> **Repo:** `github.com/ungardev/lawebcore` (public, analyze directly)
> **Goal:** Transform Lens into the world's most elegant, powerful, and cost-efficient influencer discovery tool — Apple-grade quality.

---

## MISSION

You are optimizing **La Web Core** — the internal platform of **La Web Figital Agency** (Venezuela). The flagship module is **Lens** (renamed from "Influencer Lens" by agency decision on 2026-07-30).

**The vision:** A super elite top-tier tool that appears to be made by Apple. Help clients perfect their sales processes and campaign management with surgical precision. Exploit every tool (Apify, Meta Graph API, TikTok Research API) for maximum data quality at minimum cost.

**The monorepo constraint:** Keep the existing monorepo structure (apps/api, apps/web, packages/discovery, packages/shared-core, packages/shared-ai). Do not break apart the monorepo. You MUST work within it and make it shine.

**This prompt is your complete context.** You will analyze the live repository at `github.com/ungardev/lawebcore` directly. Everything you need is there. The prompt below tells you WHAT to optimize and WHY. You figure out HOW by studying the code.

---

## PHASE 0 — REPOSITORY ANALYSIS (MANDATORY FIRST STEP)

Before proposing or implementing anything, you MUST perform exhaustive analysis of the entire repository. Read every file listed below in full. Do not skip any.

### 0.1 File Inventory — READ ALL OF THESE

**Backend (Python):**
- `apps/api/app/workers/worker.py` — 821 lines. The ARQ worker + 4-layer discovery pipeline. Your primary target for optimization.
- `packages/discovery/discovery/orchestrator.py` — 598 lines. LangGraph state machine. Study the step transitions.
- `packages/discovery/discovery/tools/apify_client.py` — 813 lines. All Apify logic. Cache keys, TTLs, actor selection, async patterns.
- `packages/discovery/discovery/result_ranker.py` — 431 lines. LWFA scoring (KPI #1 ICA, #2 Geo-Foco, #3 Velocity, #4 Business Intent).
- `packages/discovery/discovery/query_builder.py` — 147 lines. Default VE queries, niche keyword groups.
- `packages/discovery/discovery/tools/geo_boost.py` — composite_score() formula used by worker.py.
- `packages/discovery/discovery/schemas.py` — All Pydantic models (BriefStructured, DiscoveryPlan, etc.).
- `packages/discovery/discovery/memory.py` — Conversation state persistence.
- `packages/discovery/discovery/brief_parser.py` — DeepSeek brief parsing.
- `packages/discovery/discovery/tools/meta_client.py` — Meta Graph API (268 lines, deferred).
- `packages/shared-ai/shared_ai/deepseek_client.py` — 118 lines. DeepSeek-V3 with cache mode.
- `packages/shared-ai/shared_ai/embeddings.py` — fastembed setup.
- `packages/shared-core/shared_core/config.py` — All env vars.
- `packages/shared-core/shared_core/db.py` — SQLAlchemy async session.

**Frontend (React/TypeScript):**
- `apps/web/src/features/lens/pages/LensChatPage.tsx` — 199 lines. Main AI chat UI.
- `apps/web/src/features/lens/hooks/useDiscoveryConversation.ts` — 253 lines. Conversation state + polling.
- `apps/web/src/features/lens/components/SearchProgress.tsx` — 121 lines. Progress display (4 phases).
- `apps/web/src/features/lens/components/CandidateCard.tsx` — 34 lines. Candidate card (AFINIDAD label).
- `apps/web/src/features/lens/components/BriefWizard.tsx` — Multi-step brief wizard.
- `apps/web/src/features/lens/components/HashtagChips.tsx` — Hashtag input with paste/comma support.
- `apps/web/src/features/lens/api/lensApi.ts` — Type-safe API client for lens endpoints.
- `apps/web/src/features/lens/types/discovery.ts` — TypeScript types for discovery.
- `apps/web/src/index.css` — 224 lines. All CSS design tokens.
- `apps/web/tailwind.config.js` — 126 lines. Tailwind theme config.
- `apps/web/src/components/layout/Sidebar.tsx` — Navigation sidebar.
- `apps/web/src/components/layout/AppLayout.tsx` — Main layout.

**Database:**
- `supabase/migrations/00000000000019_discovery_foundation.sql` — Creates discovery tables.
- `supabase/migrations/00000000000021_discovery_recovery.sql` — Idempotent recovery of 0019.
- `supabase/migrations/00000000000026_atomic_discovery_metadata.sql` — Atomic JSONB merge RPC.
- `supabase/migrations/00000000000027_rls_discovery_tables.sql` — RLS policies.
- `supabase/migrations/00000000000028_discovery_tier_persistence.sql` — Tier persistence.
- `supabase/schema.sql` — Full consolidated schema (960 lines).

**Documentation (read for context):**
- `docs/DISCOVERY_ARCHITECTURE.md` — 474 lines. Complete discovery spec.
- `docs/CREDENCIALES_Y_SUSCRIPCIONES.md` — Subscriptions and costs.
- `docs/ROADMAP.md` — Sprint plan.
- `docs/ENGINEERING_STATE.md` — Tech debt and current state.
- `INFLUENCER_LENS_PLAN.md` — Detailed lens plan.

### 0.2 Document All Inconsistencies

From your analysis, document:
1. **Scoring formula mismatch** — `worker.py` uses `composite_score()` from `geo_boost.py` (ER×100 + GEO×30 + Business×20 + Verified×10 + Nicho×25). `result_ranker.py` has canonical `calculate_lwfa_composite()` with different weights (0.25*ER + 0.18*BI + 0.15*ICA + 0.12*Vel + 0.12*Geo + 0.10*Clips + 0.08*Consistency). These produce DIFFERENT scores. Which is correct?
2. **Font inconsistency** — `tailwind.config.js` declares `font-display: Montserrat`. `index.css` imports `Instrument Serif` and defines `.font-display` to use it. Neither is consistently used.
3. **Color token conflict** — `success`, `warning`, `info` declared twice in `tailwind.config.js` (HSL vars first, then hex overrides — hex wins).
4. **`exclude_handles` not wired to Apify** — Schema and orchestrator have it, but Apify client doesn't receive it.
5. **Orchestrator state in-memory** — `DiscoveryOrchestrator.state` dict is lost on restart.
6. **Cities comma input bug** — trailing comma disappears in `BriefWizard.tsx` cities field.
7. **Dark mode abrupt** — primary switches purple→blue with no transition.

---

## PHASE 1 — COST OPTIMIZATION & APIFY HACKING (P0 — CRITICAL)

### 1.1 Cut Apify Cost by 70%+

**Current state:** $3.30/campaign. **Target:** $0.30–$0.80/campaign.

**Concrete tactics (implement ALL of these):**

1. **Parallelize STEP 1 + STEP 2** — Currently sequential. Use `asyncio.gather()` to run `scrape_hashtags_all_sync()` and `search_users_by_keywords_sync()` concurrently. Both hit different actors and are independent.

2. **Pass all hashtags in ONE call** — `instagram-hashtag-scraper` accepts an array of hashtags. Currently you might be calling it per-hashtag. Verify the current implementation. If it's one call per hashtag, refactor to batch.

3. **Smart early-exit on geo filter** — After STEP 1+2, immediately apply `country_boost() >= 1.0` filter BEFORE enrichment. Only enrich profiles that already pass VE filter. This reduces STEP 3 from 150 → ~30-50 profiles.

4. **Skip STEP 4 engagement analytics for small runs** — If candidate pool after STEP 3 is <20, skip the expensive `analyze_profile_engagement()` call. Compute velocity from STEP 3 posts directly.

5. **Adaptive cache TTL** — Same hashtag in same niche within 24h is likely identical. Use TTL=6h for niche-stable hashtags (pet food, fashion) and TTL=30min for volatile niches (news, trends).

6. **Pre-warm cache for top 20 hashtags** — Add a midnight cron job (`@app.on_event("startup")` + `asyncio.create_task`) that pre-fetches top 20 VE hashtags. When real user runs a campaign, cache is already warm.

7. **run_id namespace verification** — Verify that `_build_cache_key()` is called with `run_id` on ALL sync methods (STEP 1, 2, 3). Currently STEP 1+2 have it. Verify STEP 3.

8. **DeepSeek batch scoring** — Instead of calling `composite_score()` per candidate in Python, batch all candidates into a single DeepSeek call with a prompt that returns JSON array of scores. Reduces LLM overhead.

### 1.2 Maximize Apify Data Quality

**For each actor, verify the input fields:**

```
instagram-hashtag-scraper:
  hashtags: [list of hashtags without #]
  resultsLimit: 50
  # Verify: are you getting ownerUsername, likesCount, commentsCount,
  #         timestamp, locationName for geo triangulation?

instagram-search-scraper:
  searchType: "user"
  searchQueries: [list of keywords]
  resultsLimit: 30 per keyword
  # Verify: are you getting biography, externalUrl, isBusinessAccount,
  #         isVerified, followersCount for business intent?

instagram-profile-scraper:
  usernames: [list without @]
  resultsType: "details"
  includeAboutSection: true
  # Verify: latestPosts with engagement metrics

engagement-analytics:
  postsToAnalyze: 30 (not 50 — reduce cost)
```

**New data quality tactics:**

1. **Cross-reference boost** — If a profile appears in both STEP 1 (hashtag) AND STEP 2 (keyword), boost its `match_score` by 1.3x. Implement in the merge step before scoring.

2. **Geo triangulation** — Weight geo signal: `(geotag_count × 0.5) + (bio_ve_keywords × 0.3) + (caption_es_pct × 0.2)`. Currently it's binary (>=1.0 or 0). Make it continuous.

3. **Bot/outlier filter** — Reject profiles with ER > 30% (likely purchased engagement) or < 0.5% (inactive/bots). Add this filter BEFORE enrichment.

4. **Comment sentiment ICA** — For top 5 candidates, run DeepSeek sentiment on top 10 comments to compute a more accurate ICA score.

### 1.3 Prepare Meta Graph API Abstraction

**Do NOT implement Meta yet** (approval pending 2-6 weeks). But prepare the foundation:

1. Create `packages/discovery/discovery/data_providers/base.py`:
```python
from abc import ABC, abstractmethod
from typing import Any

class DataProvider(ABC):
    @abstractmethod
    async def search_by_hashtags(self, hashtags: list[str], **kwargs) -> list[dict]: pass

    @abstractmethod
    async def search_by_keywords(self, keywords: list[str], **kwargs) -> list[dict]: pass

    @abstractmethod
    async def enrich_profiles(self, handles: list[str], **kwargs) -> list[dict]: pass
```

2. Create `packages/discovery/discovery/data_providers/apify_provider.py` — wrap existing `apify_client` methods.

3. Create `packages/discovery/discovery/data_providers/meta_provider.py` — stub for Meta Graph API.

4. In `worker.py`, inject `DataProvider` as a dependency. Switch provider based on `brief.platforms` and credential availability.

---

## PHASE 2 — INTELLIGENCE & AI EFFICIENCY (P2)

### 2.1 Minimal-Cost Intelligence

1. **Single LLM call per brief** — Combine brief parsing + niche detection + initial candidate ranking into ONE DeepSeek call with a well-structured prompt that returns both `BriefStructured` JSON AND top 5 candidate handles.

2. **Use `deepseek-v4-flash` for all calls** — Reserve `deepseek-reasoner` (R1) for complex multi-step reasoning only (1% of calls). **Nota de pricing:** DeepSeek-V4-Flash tiene precio ×2 en horario pico UTC 01:00-04:00 y 06:00-10:00 (lunes a viernes). Para Venezuela (UTC-4) eso es 21:00-00:00 y 02:00-06:00. Las corridas de prueba nocturnas caen en tarifa peak ($0.44/1M input, $1.32/1M output). Ejecutar pruebas en horario off-peak para ahorrar.

3. **Prompt compression** — Strip whitespace, use Spanish abbreviations, reuse system prompt across calls. Cache the compressed prompt.

4. **Batch embeddings** — Embed 100 niche keywords once, store in Redis with 7-day TTL, reuse across all briefs.

5. **Rule-based tier classification** — Deterministic: `followers → tier` mapping (no LLM needed). Store result in Redis.

6. **Rule + embedding for geo** — Rules for hard cases (city name in bio). Embeddings for ambiguous (es-VE vs es-MX caption). Use the existing `fastembed` setup.

### 2.2 Brief Parser Optimization

Current: single DeepSeek call to parse free text.

Improvement:
1. Extract `product_name`, `industry`, `audience_countries` via regex first (free, instant).
2. Only call DeepSeek if regex misses >2 fields.
3. Cache parsed briefs by `(product_keywords_hash, audience_keywords_hash)` — same product in same country within 24h = cache hit.

### 2.3 Feedback Loop Architecture

1. Create `discovery_feedback` table:
```sql
CREATE TABLE discovery_feedback (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  run_id UUID REFERENCES discovery_runs(id),
  candidate_id UUID REFERENCES discovery_candidates(id),
  action TEXT CHECK (action IN ('saved', 'dismissed', 'contacted', 'won', 'lost')),
  notes TEXT,
  created_at TIMESTAMPTZ DEFAULT NOW()
);
```

2. In `CandidateCard.tsx`, fire `POST /lens/discovery/candidates/{id}/feedback` on save/dismiss.

3. Daily cron job re-weights scoring formula based on saved/dismissed patterns:
   - If user dismisses all MICRO_BAJO → reduce tier weight
   - If user saves all with ICA > 50 → increase ICA weight
   - Write new weights to a `scoring_weights` config table

4. Add `weighted_lwfa_score()` that reads from `scoring_weights` table.

---

## PHASE 3 — PERFORMANCE & SCALABILITY (P0)

### 3.1 Reduce Pipeline Time

**Current:** ~60-120s for full 4-layer pipeline. **Target:** <30s.

**Implement ALL of these:**

1. **Parallelize STEP 1 + STEP 2** — `asyncio.gather()`.
2. **Streaming results** — Return candidates as they pass STEP 3 (enrichment). Don't wait for all 150. Stream via Server-Sent Events (SSE) orpolling-optimized.
3. **Reduce `MAX_HANDLES_TO_ENRICH`** from 150 to 60 — only top geo-filtered from STEP 1+2.
4. **Skip STEP 4 analytics** for small runs (< 20 candidates).
5. **Increase `APIFY_SEMAPHORE`** from 3 to 5 — allows more parallel Apify calls.
6. **ARQ job prioritization** — For future: paid users get higher `queue_priority` in ARQ.

### 3.2 Database Optimization

**Add indexes (new migration 0029):**
```sql
CREATE INDEX idx_discovery_candidates_run_match
  ON discovery_candidates(run_id, match_score DESC);

CREATE INDEX idx_discovery_candidates_handle_platform
  ON discovery_candidates(platform, handle);

CREATE INDEX idx_discovery_runs_status_started
  ON discovery_runs(status, started_at DESC);

CREATE INDEX idx_discovery_messages_conversation
  ON discovery_messages(conversation_id, created_at);

CREATE INDEX idx_api_costs_provider_occurred
  ON api_costs(provider, occurred_at DESC);
```

**Add materialized view (new migration 0030):**
```sql
CREATE MATERIALIZED VIEW mv_discovery_candidates_enriched AS
SELECT
  c.*,
  r.brief_parsed->>'product_name' AS product_name,
  r.status AS run_status,
  COUNT(*) OVER (PARTITION BY c.handle) AS appearances
FROM discovery_candidates c
JOIN discovery_runs r ON c.run_id = r.id
WITH DATA;

CREATE UNIQUE INDEX ON mv_discovery_candidates_enriched(id);
-- Refresh daily or on-demand
```

### 3.3 Railway Ecosystem Evaluation

**Current:** API + ARQ worker in same service (child process).

**Evaluate and recommend:**
1. **Split services** — As scale grows, separate:
   - `lawebcore-api` (FastAPI only) — $5/mo
   - `lawebcore-worker` (ARQ only) — $5/mo
   - `lawebcore-redis` (Redis) — $5/mo
   - Railway Postgres (separate from Supabase if needed) — $5/mo
2. **Connection pooling** — SQLAlchemy async pool size (currently default 5). Set to 20.
3. **Health checks** — Verify worker has separate health endpoint (`STANDALONE_WORKER=true` mode).
4. **Graceful shutdown** — Handle SIGTERM in worker, finish in-flight jobs.
5. **Cost monitoring** — Railway metrics dashboard + custom Prometheus counters for Apify/LLM costs.

---

## PHASE 4 — APPLE-GRADE UI/UX (P1 — CRITICAL)

### 4.1 Design System Unification

**Fix inconsistencies FIRST (no new design until these are resolved):**

1. **Remove Montserrat dead code** — Remove `font-display: ['Montserrat', ...]` from `tailwind.config.js`. Replace with:
   ```js
   fontFamily: {
     sans: ['Inter', '-apple-system', 'BlinkMacSystemFont', 'Segoe UI', 'sans-serif'],
     display: ['Instrument Serif', 'Georgia', 'serif'],  // ← Instrument Serif only
     mono: ['ui-monospace', ...],
   }
   ```

2. **Verify Instrument Serif import** in `index.css` — It should be there. If not, add:
   ```css
   @import url('https://fonts.googleapis.com/css2?family=Instrument+Serif:ital@0;1&display=swap');
   ```

3. **Standardize `.font-display` usage** — Search the codebase for all `font-display` usages. Ensure they use Instrument Serif, not Montserrat.

4. **Standardize shadows** — Reduce to 3:
   ```js
   boxShadow: {
     xs: '0 1px 2px rgba(0,0,0,0.05)',
     md: '0 4px 12px rgba(0,0,0,0.08)',
     xl: '0 12px 40px rgba(0,0,0,0.12)',
   }
   ```

5. **Standardize radii** — Apple-like progression:
   ```js
   borderRadius: {
     sm: '6px',
     md: '10px',
     lg: '16px',
     xl: '24px',
     full: '9999px',
   }
   ```

### 4.2 Apple Design Principles

Apply these to EVERY component you touch:

1. **Generous whitespace** — Increase padding 1.5x on panels, cards, buttons.
2. **Subtle borders** — `border-[rgba(0,0,0,0.06)]` in light mode, `rgba(255,255,255,0.08)` in dark.
3. **Micro-animations** — 200ms ease-out on hover, 150ms on active. Spring on focus.
4. **Sticky headers** — `position: sticky; top: 0;` on all table/list headers.
5. **Skeleton loaders** — Add shimmer animation to all async content (CandidateCardSkeleton already exists — use it).
6. **Empty states with personality** — SVG illustrations + Spanish micro-copy.
7. **Focus rings** — Apple-style: `box-shadow: 0 0 0 4px rgba(168,85,247,0.15)`.
8. **Floating elements** — Chat input should be a floating pill at bottom: `bg-white/80 backdrop-blur-xl rounded-full`.
9. **Loading with percentage** — Never show "Loading…", show progress %.
10. **Dark mode** — Smooth 300ms transition on primary color switch (purple → blue).

### 4.3 Component Overhauls

#### `LensChatPage.tsx` (HIGHEST PRIORITY)

**Current issues:**
- Flat header, no large title
- No avatar icons in conversations sidebar
- Basic textarea border
- No floating chat input

**Apple redesign:**
```tsx
// 1. Large title header (Apple style)
<div className="mb-6">
  <p className="text-eyebrow text-muted-foreground">Inteligencia / discovery</p>
  <h1 className="font-display text-4xl italic tracking-tight text-foreground">
    Lens
  </h1>
  <p className="mt-1 font-display italic text-lg text-muted-foreground">
    Descubre influencers excepcionales
  </p>
</div>

// 2. Conversations: add avatar from brief keywords
// Extract first letter of product_name as avatar, colored by hash

// 3. Chat input: floating pill at bottom
<div className="fixed bottom-6 left-1/2 -translate-x-1/2 w-full max-w-2xl px-4">
  <div className="flex items-end gap-2 rounded-full border border-divider bg-white/90
                  backdrop-blur-xl px-4 py-3 shadow-xl transition-shadow
                  focus-within:shadow-2xl focus-within:border-primary/30">
    <Textarea className="min-h-[48px] resize-none border-0 bg-transparent
                         shadow-none focus-visible:ring-0" />
    <Button size="icon" className="rounded-full shrink-0 h-10 w-10">
      <Send className="h-4 w-4" />
    </Button>
  </div>
</div>

// 4. Messages: chat bubble design
// User: brand gradient 10% alpha, rounded-2xl, aligned right
// Assistant: panel-raised, rounded-2xl, aligned left
// Tool results: inset border, bg-surface-sunken
```

#### `CandidateCard.tsx`

**Already fixed:** "MATCH" → "AFINIDAD"

**Apple redesign:**
```tsx
// 1. AFINIDAD label: keep, already done

// 2. Avatar: rounded-full, 80px, with subtle ring
// Add online indicator dot (green, positioned bottom-right of avatar)

// 3. Two-column layout on desktop:
// [Avatar+Info 65%] | [Score Circle + Actions 35%]

// 4. Tier badge: Apple-style capsule
<span className={cn(
  "inline-flex items-center rounded-full border px-2.5 py-0.5 text-[10px] font-semibold",
  tier === 'NANO' && "border-blue-200 bg-blue-50 text-blue-700",
  tier === 'MICRO' && "border-purple-200 bg-purple-50 text-purple-700",
  tier === 'MID' && "border-pink-200 bg-pink-50 text-pink-700",
  tier === 'MACRO' && "border-orange-200 bg-orange-50 text-orange-700",
)}>
  {tier}
</span>

// 5. MatchScoreCircle: Apple Watch activity ring style
// Concentric circles with gradient stroke
// Animated on mount (draw from 0 to score over 800ms)

// 6. Actions: "Guardar" → "Guardar" with checkmark icon
// "Descartar" → minimal gray, appears on hover only
```

#### `SearchProgress.tsx`

**Already refactored** to 4 real phases. Polish further:
```tsx
// 1. Circular progress ring (Apple Watch style)
// Animated arc that fills as phases complete

// 2. Real-time ETA
// Track average duration per phase. Show "≈ 45s restantes"

// 3. Cancel button
// Small "Cancelar" link during active search

// 4. Phase labels: keep in Spanish
// "Buscar candidatos por hashtags" / "Buscar por keywords" /
// "Enriquecer perfiles con datos reales" / "Puntuar y filtrar candidatos"
```

#### `BriefWizard.tsx`

**Fix trailing-comma cities bug** — use the same pattern as `HashtagChips`:
1. Maintain local `useState` for cities
2. On comma/enter, commit to array
3. Backspace on empty removes last chip

**Polish step transitions:**
```tsx
// Animate between steps
<div className="transition-all duration-300 ease-out"
     key={currentStep}>
  {children}
</div>
```

#### `LensEmptyState.tsx`

Add Apple-style SVG illustrations:
```tsx
// Inline SVG line-art illustrations
// "No conversations" → stylized chat bubble with sparkles
// "No results" → magnifying glass over map
// "No candidates" → person with target/dart
// Use brand colors, stroke-based, minimal
```

### 4.4 New Components to Build

| Component | Purpose | Priority |
|---|---|---|
| `ProgressRing.tsx` | Apple Watch-style circular progress | P1 |
| `GlassPanel.tsx` | Reusable glassmorphism panel | P2 |
| `AvatarStack.tsx` | Overlapping avatars for candidate previews | P2 |
| `Pill.tsx` | Unified tag/badge/chip component | P1 |
| `EmptyStateIllustration.tsx` | SVG illustrations collection | P2 |
| `CommandPalette.tsx` | Extend GlobalSearchDialog with ⌘K | P3 |
| `SkeletonCard.tsx` | Shimmer card for async content | P2 |

---

## PHASE 5 — REFACTOR & BEST PRACTICES (P3)

### 5.1 Code Quality

1. **Type safety** — Add Zod schemas for all API responses in web. Every `lensApi` response should be typed.

2. **Error boundaries** — Wrap each feature route in React ErrorBoundary:
   ```tsx
   <ErrorBoundary fallback={<SomethingWentWrong onRetry={refetch} />}>
     <CandidateList />
   </ErrorBoundary>
   ```

3. **Logging** — Replace `console.log` in web with `loglevel` or `consola`.

4. **Hook extraction** — Split `useDiscoveryConversation.ts` (253 lines) into:
   - `useConversationPolling.ts` — polling logic only
   - `useConversationMessages.ts` — message state
   - `useDiscoveryActions.ts` — save/dismiss actions

5. **Component library** — Extract `Panel`, `Card`, `Button` variants into `apps/web/src/components/ui/` (already exists, but populate it properly).

6. **Test coverage** — Minimum 60% on:
   - `query_builder.py` — all branches
   - `result_ranker.py` — all scoring functions
   - `orchestrator.py` — step transitions
   - `brief_parser.py` — parsing logic

### 5.2 Backend Refactor

1. **Move worker into packages/discovery** — `packages/discovery/worker.py` as single source of truth. `apps/api/app/workers/worker.py` becomes thin wrapper that imports from it.

2. **Separate concerns:**
   ```
   packages/discovery/discovery/
     pipeline/         # 4-step execution (step1, step2, step3, step4)
     scoring/         # LWFA, ICA, geo_foco, velocity, business_intent
     providers/       # data_providers/ (apify, meta, tiktok)
     orchestration/   # orchestrator.py (moves here)
   ```

3. **OpenAPI spec** — Add examples to all Pydantic models. Generate OpenAPI spec.

4. **Request ID middleware** — Add `X-Request-ID` header tracing to all requests.

5. **Retry policy** — All external API calls (Apify, DeepSeek, Meta) use `tenacity` with exponential backoff:
   ```python
   @retry(stop=stop_after_attempt(3),
          wait=wait_exponential(multiplier=2, min=4, max=30))
   ```

6. **Native async for DeepSeek** — Replace `asyncio.to_thread(client.invoke, messages)` with proper async client from `langchain-deepseek` or direct REST.

### 5.3 Database Migrations

1. **Consolidate 0019 + 0021** — Both deal with discovery foundation. 0019 fails, 0021 recovers it idempotently. Create clean `0032_discovery_foundation_clean.sql`.

2. **Migration 0029** — New indexes (Phase 3.2)

3. **Migration 0030** — Materialized view `mv_discovery_candidates_enriched` (Phase 3.2)

4. **Migration 0031** — `discovery_feedback` table (Phase 2.3)

---

## PHASE 6 — OBSERVABILITY & RELIABILITY (P3)

### 6.1 Prometheus Metrics

Add to `apps/api/app/main.py` or a new `apps/api/app/core/metrics.py`:

```python
from prometheus_client import Counter, Histogram, Gauge

# Pipeline metrics
lens_pipeline_duration = Histogram(
    'lens_pipeline_duration_seconds',
    'Lens pipeline duration by step',
    ['step'],
    buckets=[5, 10, 20, 30, 60, 120]
)

lens_candidates_total = Counter(
    'lens_candidates_total',
    'Total candidates discovered',
    ['status']  # completed, failed, partial
)

lens_apify_cost_usd = Counter(
    'lens_apify_cost_usd_total',
    'Total Apify cost in USD',
    ['actor']
)

lens_deepseek_tokens = Counter(
    'lens_deepseek_tokens_total',
    'Total DeepSeek tokens',
    ['type']  # input, output
)

lens_cache_hits = Counter(
    'lens_cache_hits_total',
    'Cache hits by layer',
    ['layer']  # search, profiles
)

lens_active_runs = Gauge(
    'lens_active_runs',
    'Currently running discovery runs'
)
```

Instrument `worker.py`:
- Start/end of each STEP
- Apify API calls (before/after with cost)
- DeepSeek calls (token counts)
- Cache hits/misses

### 6.2 Sentry Integration

Already present. Add breadcrumbs in pipeline:
```python
import sentry_sdk

sentry_sdk.add_breadcrumb(
    category="discovery",
    message=f"STEP {n} started for run {run_id}",
    data={"brief_parsed": brief.dict()}
)
```

### 6.3 SLOs

Define and track:
| SLO | Target |
|---|---|
| Pipeline success rate | > 95% |
| P95 pipeline duration | < 60s |
| Apify cost per campaign | < $1 (with cache) |
| DeepSeek cost per campaign | < $0.50 |
| Cache hit rate | > 60% |

---

## DELIVERABLE FORMAT

For EVERY finding, use this structure:

```markdown
## [P0] [COST] Parallelize STEP 1 and STEP 2

**Problem:** Steps 1 and 2 run sequentially, adding 30-60s to total pipeline time.
**Current code:** `worker.py` lines 160-180 (STEP 1) → lines 180-250 (STEP 2)
**Impact:** $0 wasted on idle time; 30-50% faster for user
**Proposed solution:**
  - Wrap both calls in `asyncio.gather()`
  - Merge results deduplicating by handle
  - Increase semaphore to 5
**Effort:** 2h
**Risk:** Low (stateless change)
**Files:** `apps/api/app/workers/worker.py`, `packages/discovery/discovery/tools/apify_client.py`
```

---

## PRIORITY ORDER

| Priority | Phase | Why |
|---|---|---|
| 🔴 P0 | Phase 1 (Cost) | Directly reduces $ cost per campaign |
| 🔴 P0 | Phase 3 (Performance) | Faster = better UX + lower ARQ resource cost |
| 🟠 P1 | Phase 4 (Apple UI) | Brand-defining; CEO mandate |
| 🟡 P2 | Phase 2 (AI) | Better quality candidates |
| 🟢 P3 | Phase 5 (Refactor) | Sustainability and testability |
| 🟢 P3 | Phase 6 (Observability) | Post-launch debugging |

---

## HARD CONSTRAINTS

- **DO NOT** break the monorepo. Keep `apps/api`, `apps/web`, `packages/*`.
- **DO NOT** replace Apify with another data source.
- **DO NOT** add OpenAI or Anthropic (DeepSeek only).
- **DO NOT** implement ML for historical learning before having real saved/dismissed data.
- **DO** maintain all existing API contracts (breaking changes require deprecation period).
- **DO** follow existing code style (type hints, snake_case Python, camelCase TS).
- **DO** add tests for every logic change.
- **DO** update `PROJECT_STATUS_2026-07-30.md` when making structural changes.

---

## SUCCESS METRICS

Measure improvements against these:

| Metric | Before | After (Target) |
|---|---|---|
| Cost per campaign | $3.30 | < $0.80 |
| Pipeline duration (P95) | ~90s | < 30s |
| Cache hit rate | ~20% | > 60% |
| Apify data quality score | ?? | Establish baseline, then improve 20% |
| UI/UX NPS (internal) | ?? | Establish baseline |
| Test coverage | 0% | > 60% on critical paths |

---

## FINAL OUTPUT REQUIREMENTS

When you complete the analysis and planning, deliver:

1. **Executive Summary** (max 1 page) — What changed, what improved, what remains.

2. **Top 10 Quick Wins** — Each < 4h effort, immediately actionable.

3. **Top 5 Strategic Initiatives** — Each 1-2 weeks effort, highest impact.

4. **Complete Roadmap** — Phased plan with effort estimates for every initiative.

5. **Risk Register** — Every major change rated High/Med/Low with mitigation.

6. **Implementation Order** — Numbered list of all changes in execution sequence.

7. **Files to Modify** — Per-initiative list of exact file paths and line ranges.

8. **Test Plan** — What to test for each initiative.

---

**The goal:** When the La Web Figital Agency team shows Lens to a client, the client says:
> "Esto parece hecho por Apple. ¿Cómo es posible que una agencia en Venezuela haya construido algo así?"

Execute accordingly.
