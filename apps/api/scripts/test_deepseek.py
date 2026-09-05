"""Smoke test: DeepSeek-V4-Flash conectado y funcionando coherentemente.

Verifica contra producción (1 llamada JSON + 2 de multi-turno, ~$0.001):
  1. Conectividad + auth (API key válida)
  2. Salida JSON estructurada (response_format=json_object)
  3. finish_reason=stop (sin truncamiento) + tokens/costo reportados
  4. Multi-turno coherente vía history (FIX R-1)

Uso:
    DEEPSEEK_API_KEY=sk-... python -m scripts.test_deepseek
"""

import asyncio
import os
import sys

from shared_ai.deepseek_client import DeepSeekClient

PRODUCT_CODE = "PILA-VERDE"


async def main() -> int:
    api_key = os.getenv("DEEPSEEK_API_KEY", "")
    if not api_key:
        print("ERROR: DEEPSEEK_API_KEY not set. Set the env var before running.")
        return 1

    client = DeepSeekClient(api_key=api_key)
    print("=" * 60)
    print("DEEPSEEK SMOKE TEST")
    print("=" * 60)
    failures = 0

    print("\n[1/3] complete_json — salida estructurada...")
    try:
        parsed = await client.complete_json(
            prompt='Devuelve un objeto JSON con exactamente dos claves: "ok" (boolean true) y "eco" (string "lens").',
            max_tokens=200,
        )
        if parsed.get("ok") is True and parsed.get("eco") == "lens":
            print(f"  OK: json_object mode funciona → {parsed}")
        else:
            print(f"  WARN: JSON válido pero contenido inesperado: {parsed}")
    except Exception as e:
        print(f"  FAIL: {e}")
        failures += 1

    print("\n[2/3] complete — métricas + finish_reason...")
    try:
        result = await client.complete(
            prompt="Responde solo con la palabra: listo",
            max_tokens=50,
        )
        print(f"  model={result.model} latency={result.latency_ms}ms tokens={result.tokens_used} cost=${result.cost_usd} finish={result.finish_reason}")
        if not result.content.strip():
            print("  FAIL: respuesta vacía")
            failures += 1
        elif result.finish_reason not in ("stop", None):
            print(f"  FAIL: finish_reason={result.finish_reason} (esperado stop)")
            failures += 1
        elif not result.tokens_used:
            print("  WARN: usage_metadata vacío — el proveedor no reportó tokens")
        else:
            print("  OK")
    except Exception as e:
        print(f"  FAIL: {e}")
        failures += 1

    print("\n[3/3] multi-turno coherente (history)...")
    try:
        turn1 = await client.complete(
            prompt=f"Memoriza este código de producto: {PRODUCT_CODE}. Responde solo: OK",
            max_tokens=50,
        )
        # El history real requiere el turno 1 como user + su respuesta como
        # assistant — exactamente el contrato que produce un chat.
        turn2 = await client.complete(
            prompt="¿Cuál es el código de producto que te di? Responde SOLO el código.",
            history=[
                {"role": "user", "content": f"Memoriza este código de producto: {PRODUCT_CODE}. Responde solo: OK"},
                {"role": "assistant", "content": turn1.content},
            ],
            max_tokens=100,
        )
        if PRODUCT_CODE.lower() in turn2.content.lower():
            print(f"  OK: recuerda '{PRODUCT_CODE}' → multi-turno coherente")
        else:
            print(f"  FAIL: esperaba '{PRODUCT_CODE}' en la respuesta, got: {turn2.content[:120]!r}")
            failures += 1
    except Exception as e:
        print(f"  FAIL: {e}")
        failures += 1

    print("\n" + "=" * 60)
    if failures:
        print(f"RESULTADO: {failures} test(s) FALLARON — revisa DEEPSEEK_API_KEY / red / modelo")
        return 1
    print("RESULTADO: TODO OK — DeepSeek conectado y coherente")
    return 0


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
