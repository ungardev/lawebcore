"""Enrichment Field Names Guard — Regression test for run 10a59ecf.

Ref:
- docs/FIXES_RUN_10a59ecf_LENS_03-09-26.md (Claude Code Fable 5.1)
- docs/LENS_BUG_REPORT_10a59ecf_03-09-26.md

El bloque de merge de enrichment (worker.py:1244-1258) ha regresado a
camelCase tres veces:
  Regresion #0  (agosto): merge escribia followersCount
  BUG #1        (27-ago): merge bylellama follower_count — FIX #1 en 2446e75
  run 10a59ecf  (03-sep): merge vuelve a followersCount — revertido en 4f87a6b

test_dual_names_guard.py NO lo detecta porque cubre escritura dual en search
steps, no lectura de claves inexistentes en el bloque de merge.

Esta prueba deriva las claves validas DIRECTAMENTE del normalizador
(_normalize_user), asi que si alguien cambia el normalizador o el merge,
la prueba lo detecta en cualquier direccion sin necesidad de mantener
listas a mano.
"""

import re
from pathlib import Path

from discovery.tools.hikerapi_client import HikerAPIClient


def _extract_merge_keys_from_worker() -> set[str]:
    """Extrae las claves que el bloque de merge lee via e.get().

    Usa regex que apunta directo al dict dentro de profiles[handle].update({...}).
    El patron captura solo el contenido entre las llaves exteriores del dict.
    """
    src = Path("apps/api/app/workers/worker.py").read_text(encoding="utf-8")
    m = re.search(r'profiles\[handle\]\.update\(\{(.+?)\n\s*\}\)\s*\n', src, re.DOTALL)
    if not m:
        raise AssertionError("bloque de merge no encontrado en worker.py")
    content = m.group(1)
    return set(re.findall(r'e\.get\("([^"]+)"', content))


def test_enrichment_merge_reads_only_normalizer_output_keys():
    """El merge de enrichment solo puede leer claves que _normalize_user() emite.

    Si el merge lee una clave que no existe en la salida del normalizador,
    e.get() devuelve None y el perfil se descarta con MISSING_FOLLOWER_FIELD.
    Esta prueba existe porque el bloque de merge ha regresado a camelCase
    tres veces (Regresion #0, BUG #1, run 10a59ecf).
    """
    normalizer_output = HikerAPIClient()._normalize_user({"username": "x"})
    valid_keys = set(normalizer_output.keys())

    read_keys = _extract_merge_keys_from_worker()

    known_extra_keys = {
        "about",  # se procesa fuera del merge (about_data = e.get("about"))
        # FIX N-3 (04-sep-2026): latestPosts NO viene del normalizador — lo
        # agrega _enrich_one vía get_user_medias (/gql/user/medias) antes del
        # merge. El scoring calcula ER real desde esta clave.
        "latestPosts",
    }
    invalid = read_keys - valid_keys - known_extra_keys
    assert not invalid, (
        f"El merge lee claves que _normalize_user() no emite: {invalid}. "
        f"Estas llegan como None y el perfil se descarta. "
        f"Claves validas del normalizador: {valid_keys}"
    )


def test_enriched_profile_preserves_follower_count():
    """Un perfil enriquecido con follower_count=5000 debe conservar ese valor.

    El bug original (run 10a59ecf) hacia que todos los perfiles enriquecidos
    terminaran con follower_count=None porque el merge leia followersCount
    (inexistente) en lugar de follower_count.
    """
    client = HikerAPIClient()
    mock_user = {
        "username": "test_user",
        "follower_count": 15000,
        "following_count": 500,
        "media_count": 120,
        "pk": "12345",
    }
    normalized = client._normalize_user(mock_user)

    assert normalized.get("follower_count") == 15000
    assert normalized.get("following_count") == 500
    assert normalized.get("posts_count") == 120
    assert normalized.get("username") == "test_user"


def test_enrichment_merge_includes_all_critical_fields():
    """Verifica que las claves criticas del normalizador se lean en el merge.

    El merge debe leer todas las claves que el normalizador provee y que
    son necesarias para el scoring.
    """
    read_keys = _extract_merge_keys_from_worker()

    critical_keys_from_enrichment = {
        "follower_count", "following_count", "posts_count",
        "is_business", "is_verified", "full_name",
    }
    missing = critical_keys_from_enrichment - read_keys
    assert not missing, (
        f"El merge no lee claves criticas que el normalizador provee: {missing}. "
        f"Estos datos se pierden y el scoring funciona con datos faltantes."
    )


def test_normalizer_does_not_emit_engagement_rate():
    """ER no viene de HikerAPI. Si algún día lo emite, el merge tiene que enterarse.

    El normalizador _normalize_user() no emite engagement_rate. El ER se calcula
    en worker.py:1438 a partir de datos de engagement reales del profile scraper.
    Si el normalizador empezara a emitir engagement_rate, habría que revisar el
    merge (worker.py:1244) y el cálculo en worker.py:1438 antes de consumirlo.
    """
    out = HikerAPIClient()._normalize_user({"username": "x"})
    assert "engagement_rate" not in out, (
        "El normalizador ahora emite engagement_rate: revisar el merge en worker.py:1244 "
        "y el cálculo de ER en worker.py:1438 antes de consumirlo."
    )
