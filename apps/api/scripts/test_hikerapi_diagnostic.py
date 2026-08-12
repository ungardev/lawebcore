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


HASHTAGS = ["recetasvenezolanas", "cocinavenezolana"]


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
        else:
            print(f"  info=None, status={status}")
            continue

        if info.get("media_count", 0) < 50:
            print(f"  SKIPPED: media_count={info.get('media_count')} < 50 threshold")
            continue

        media_resp, media_status = await client._get_debug("/v2/hashtag/medias/top", params={"name": tag})
        print(f"  [/hashtag/medias/top] status={media_status}")
        if not media_resp:
            print(f"  media_resp=None")
            continue

        sections = media_resp.get("response", {}).get("sections", [])
        print(f"  sections count = {len(sections)}")
        if not sections:
            continue

        first_section = sections[0]
        print(f"  first section layout_type = {first_section.get('layout_type')}")
        print(f"  first section feed_type = {first_section.get('feed_type')}")
        layout = first_section.get("layout_content", {})
        print(f"  layout_content keys = {list(layout.keys())}")

        fill_items = layout.get("fill_items", [])
        print(f"  fill_items count = {len(fill_items)}")
        if fill_items:
            first_item_keys = list(fill_items[0].keys()) if isinstance(fill_items[0], dict) else type(fill_items[0]).__name__
            print(f"  fill_items[0] keys/type = {first_item_keys}")
            if isinstance(fill_items[0], dict) and "media" in fill_items[0]:
                media_keys = list(fill_items[0]["media"].keys())[:10] if isinstance(fill_items[0]["media"], dict) else "not a dict"
                print(f"  fill_items[0]['media'] keys (first 10) = {media_keys}")

        one_by_two = layout.get("one_by_two_item", {})
        if isinstance(one_by_two, dict):
            clips = one_by_two.get("clips", {})
            clips_items = clips.get("items", []) if isinstance(clips, dict) else []
            print(f"  one_by_two_item.clips.items count = {len(clips_items)}")

        raw_items = client._extract_media_items(media_resp)
        print(f"  _extract_media_items returned: {len(raw_items)} items")

    await client.close()
    print("\n" + "="*60)
    print("DIAGNOSTIC COMPLETE")
    print("="*60)


if __name__ == "__main__":
    asyncio.run(main())
