import asyncio
import uuid

from discovery.schemas import BriefStructured, AudienceGender, Platform, DiscoverySearchRequest
from discovery.memory import conversation_memory
from app.workers.worker import discovery_run_task

USER_ID = uuid.UUID("75f40617-281c-498f-84b5-c80e2a7fe8bd")

HASHTAGS = [
    # Brand (3)
    "#DogChow", "#Purina", "#purinavenezuela",
    # Nicho VE (5)
    "#perrosdeVenezuela", "#dogsofvenezuela", "#mascotasVE",
    "#petloversVzla", "#perrosVE",
    # Lifestyle (9)
    "#doglover", "#cachorros", "#goldenretriever",
    "#labrador", "#perrosfelices", "#doglife", "#petlife",
    "#adopcionresponsable", "#rescatedogs",
]

async def run():
    brief = BriefStructured(
        product_name="Purina Dog Chow",
        industry="pet_food",
        niches=["mascotas", "perros", "pet_care", "dog_care"],
        hashtags=HASHTAGS,
        audience_gender=AudienceGender.ALL,
        audience_age_min=22,
        audience_age_max=55,
        audience_countries=["VE"],
        platforms=[Platform.INSTAGRAM],
        exclude_stores=True,
        analyze_with_ai=True,
    )
    search_req = DiscoverySearchRequest(
        product_name=brief.product_name,
        industry=brief.industry,
        niches=brief.niches,
        hashtags=brief.hashtags,
        audience_gender=brief.audience_gender,
        audience_age_min=brief.audience_age_min,
        audience_age_max=brief.audience_age_max,
        audience_countries=brief.audience_countries,
        platforms=brief.platforms,
        exclude_stores=brief.exclude_stores,
        analyze_with_ai=True,
    )
    run_result = await conversation_memory.launch_discovery_run(
        brief=search_req, created_by=USER_ID
    )
    run_id = str(run_result["id"])
    print(f"Run created: {run_id}", flush=True)
    print(f"Hashtags: {len(HASHTAGS)} ({HASHTAGS})", flush=True)
    await discovery_run_task(None, run_id)
    print(f"Run completed: {run_id}", flush=True)

if __name__ == "__main__":
    asyncio.run(run())