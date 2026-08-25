# Data Contract LENS Discovery — Anexo al Hub

**Versión:** 1.0
**Fecha:** 2026-08-26
**Estándar padre:** `13_data_contract_hub.md` v1.0
**Aplica a:** `packages/discovery/` y `apps/api/app/workers/`

## Reglas Fundamentales

1. **NULL ≠ 0.** Campo ausente se escribe como SQL NULL, no como 0.
2. **Una sola convención:** snake_case inglés para todos los campos de dominio.
3. **Una sola forma por campo:** no dual-name (no `followersCount` Y `follower_count`).
4. **raw_data obligatorio:** payload crudo del proveedor en JSONB.
5. **source_id obligatorio:** identificador del proveedor.
6. **fetched_at obligatorio:** timestamp UTC de cuándo se pagó la llamada.

## Tabla de Campos Normalizados

| Campo | Tipo | Nullable | Fuente | Notas |
|-------|------|----------|--------|-------|
| `username` | str | NO | raw | Handle de Instagram |
| `full_name` | str | YES | raw | Nombre completo |
| `biography` | str | YES | raw | Bio del perfil (antes "bio") |
| `avatar_url` | str | YES | raw | URL de avatar |
| `follower_count` | int | YES | enriched | NULL si ausente |
| `following_count` | int | YES | enriched | NULL si ausente |
| `posts_count` | int | YES | enriched | NULL si ausente |
| `is_business` | bool | NO | raw | default False |
| `is_verified` | bool | NO | raw | default False |
| `is_private` | bool | NO | raw | default False |
| `country` | str | YES | derived | Código ISO de 2 letras |
| `location_name` | str | YES | raw | Ubicación declarada |
| `raw_data` | JSONB | NO | — | Payload crudo |
| `source_id` | str | NO | — | "hikerapi" |
| `fetched_at` | TIMESTAMPTZ | NO | — | UTC timestamp |

## Campos Deprecados (no usar en código nuevo)

| CampoViejo | CampoNuevo | Notas |
|-------------|------------|-------|
| `followersCount` | `follower_count` | Remover en Hito 31.3 |
| `followsCount` | `following_count` | Remover en Hito 31.3 |
| `postsCount` | `posts_count` | Remover en Hito 31.3 |
| `isBusinessAccount` | `is_business` | Remover en Hito 31.3 |
| `verified` | `is_verified` | Remover en Hito 31.3 |
| `bio` | `biography` | Remover en Hito 31.3 |
| `profilePicUrl` | `avatar_url` | Remover en Hito 31.3 |
| `profilePicUrlHD` | `avatar_url` | Remover en Hito 31.3 |

## Ventana de Compatibilidad (Hito 31.3)

Durante la transición, usar `LegacyCompatReader` que acepta ambas convenciones:

```python
from shared_core.observability import ContractViolationLedger

reader = LegacyCompatReader(ledger=ContractViolationLedger())
followers = reader.read_followers(profile)  # Acepta followersCount y follower_count
```

Si recibe formato legacy, emite `contract.violation` y cuenta la violación.

**Retirar** `LegacyCompatReader` cuando `contract.violation == 0` por 7 días consecutivos.

## Contrato de Enrichment

1. Si `follower_count` es `None` después de enrichment → registrar `MISSING_FOLLOWER_FIELD` en `drop_ledger`
2. No fabricar `0` para campos ausentes
3. Si enrichment falla → el perfil se marca con `enrichment_failed` y se continúa sin métricas

## Emisión de Eventos

Cada anomalía de contrato emite:

```python
logger.info(
    RunEvent.CONTRACT_VIOLATION.value,
    field=nombre_campo,
    expected=snake_case,
    received=formato_legacy,
    username=username,
)
```
