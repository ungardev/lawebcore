"""Seed lists of influencers by niche for fallback discovery.

When hashtag scraping returns no results (due to Instagram restrictions),
we fall back to curated seed lists of known influencers.
"""

SEED_INFLUENCERS: dict[str, dict[str, list[str]]] = {
    "fitness": {
        "VE": [
            "jorgecremas",
            "gymvirtual",
            "fitnessvzl",
            "entrenavirtual",
            "mujeresfitness_vzla",
            "calistenia_venezuela",
            "fitnesscaracas",
            "gimnasio_ccs",
            "entrenadorpersonal_ccs",
            "vidafitnessvzla",
            "rutina_fit_ve",
            "fitness_maracaibo",
            "deportevzla",
            "sportlife_venezuela",
            "entrenamientovzla",
            "gimnasios_venezuela",
            "fitness_galaxy_ve",
            "mujeresentrenando_ve",
            "crossfit_venezuela",
            "running_venezuela",
            "culturismo_vzla",
            "powerlifting_ve",
            "yogavenezuela_oficial",
            "pilates_venezuela",
            "funcionaltraining_ve",
            "bienestar_vzla",
            "saludfitness_vzla",
            "nutricion_deportiva_ve",
            "suplementos_vzla",
            "fitness_madrid_ve",
        ],
        "CO": [
            "gymvirtual_co",
            "fitnesscolombia",
            "entrenamientocolombia",
        ],
        "MX": [
            "gymvirtual_mx",
            "fitnessmexico",
        ],
    },
    "moda": {
        "VE": [
            "moda_venezuela",
            "tendencias_vzla",
            "outfit_vzla",
            "fashion_venezuela",
        ],
    },
    "belleza": {
        "VE": [
            "belleza_vzla",
            "makeup_venezuela",
            "skincare_vzla",
        ],
    },
    "tecnologia": {
        "VE": [
            "tech_venezuela",
            "tecnologia_vzla",
        ],
    },
    "comida": {
        "VE": [
            "comida_venezuela",
            "gastronomia_vzla",
            "recetas_venezolanas",
        ],
    },
}


def get_seed_handles(niches: list[str], country: str = "VE") -> list[str]:
    """Returns seed Instagram handles for given niches and country.

    Falls back to VE handles if specific country has no seeds.
    """
    handles: set[str] = set()

    for niche in niches:
        niche_lower = niche.lower()
        if niche_lower in SEED_INFLUENCERS:
            niche_dict = SEED_INFLUENCERS[niche_lower]
            if country in niche_dict:
                handles.update(niche_dict[country])
            if "VE" in niche_dict:
                handles.update(niche_dict["VE"])

    if not handles:
        if "fitness" in SEED_INFLUENCERS:
            handles.update(SEED_INFLUENCERS["fitness"].get("VE", []))

    return list(handles)
