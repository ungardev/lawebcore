"""
Diagnóstico directo de HikerAPI — imprime respuestas crudas para debuggear
por qué search_hashtag retorna 0 items.

Run from Railway shell:
    cd /app/apps/api && python3 scripts/test_hikerapi_diagnostic.py
"""
import asyncio
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

from discovery.tools.hikerapi_client import HikerAPIClient


HASHTAGS = ["recetasvenezolanas", "cocinavenezolana", "mascotas", "perros"]


async def main():
    api_key = os.getenv("HIKERAPI_API_KEY", "")
    if not api_key:
        print("ERROR: HIKERAPI_API_KEY not set")
        return

    client = HikerAPIClient(api_key=api_key)

    for tag in HASHTAGS:
        print(f"\n{'='*60}")
        print(f"HASHTAG: #{tag}")
        print('='*60)

        info, status = await client._get_debug("/v2/hashtag/by/name", params={"name": tag})
        print(f"[/hashtag/by/name] status={status}")
        if info:
            print(f"  media_count = {info.get('media_count')}")
            print(f"  id = {info.get('id')}")
            print(f"  keys = {list(info.keys())}")
        else:
            print(f"  info=None, status={status}")

        if info and info.get("media_count", 0) >= 50:
            media_resp, media_status = await client._get_debug("/v2/hashtag/medias/top", params={"name": tag})
            print(f"  [/hashtag/medias/top] status={media_status}")
            if media_resp:
                print(f"  response keys = {list(media_resp.keys())}")
                sections = media_resp.get("response", {}).get("sections", [])
                print(f"  sections count = {len(sections)}")
                if sections:
                    first_section = sections[0]
                    print(f"  first section keys = {list(first_section.keys())}")
                    layout = first_section.get("layout_content", {})
                    print(f"  layout_content keys = {list(layout.keys())}")
                    print(f"  layout_content medias count = {len(layout.get('medias', []))}")
                    print(f"  first layout key items: {list(layout.keys())[:3]}")
            else:
                print(f"  media_resp=None, status={media_status}")
        else:
            count = info.get("media_count", 0) if info else 0
            print(f"  SKIPPED: media_count={count} < 50 threshold")

    await client.close()
    print("\n" + "="*60)
    print("DIAGNOSTIC COMPLETE")
    print("="*60)


if __name__ == "__main__":
    asyncio.run(main())
