export interface HashtagSuggestionGroup {
  label: string;
  hashtags: string[];
}

export const HASHTAG_SUGGESTIONS: Record<string, HashtagSuggestionGroup[]> = {
  mascotas: [
    {
      label: "🇻🇪 Producto Venezuela",
      hashtags: ["purinaVE", "dogchowVE", "purina", "dogchow"],
    },
    {
      label: "🐕 Temático perros",
      hashtags: [
        "amorporruno", "perrosVE", "mascotasVE", "mascotasVenezuela",
        "doglover", "petlovers", "doglife", "mascotavzla",
      ],
    },
    {
      label: "📍 Ciudades VE",
      hashtags: [
        "caracas", "maracaibo", "valencia", "vzla",
        "venezuela", "vzlan", "mascotasvzla",
      ],
    },
    {
      label: "🏠 Adopción y rescate",
      hashtags: [
        "adopcionvzla", "rescateanimalvzla", "adopta",
        "refugioanimal", "mascotasdevzla",
      ],
    },
  ],
  belleza: [
    {
      label: "🇻🇪 Venezuela",
      hashtags: ["bellezavzla", "makeupve", "skincareve", "vzla"],
    },
    {
      label: "💄 Makeup",
      hashtags: ["makeuplover", "makeupaddict", "beautyblogger", "makeupartist"],
    },
    {
      label: "✨ Skincare",
      hashtags: ["skincare", "skincareregimen", "glowingskin", "skincareaddict"],
    },
  ],
  food: [
    {
      label: "🇻🇪 Venezuela",
      hashtags: ["foodpornvzla", "gastronomiave", "comidavzla", "vzla"],
    },
    {
      label: "🍕 Food",
      hashtags: ["foodie", "foodporn", "instafood", "foodlover", "yummy"],
    },
  ],
  default: [
    {
      label: "🇻🇪 Venezuela",
      hashtags: ["vzla", "venezuela", "caracas"],
    },
    {
      label: "🔥 Generic",
      hashtags: ["trending", "viral", "explore"],
    },
  ],
};

export function getSuggestionsForIndustry(industry: string | null): HashtagSuggestionGroup[] {
  if (!industry) return HASHTAG_SUGGESTIONS["default"];
  const key = industry.toLowerCase();
  return HASHTAG_SUGGESTIONS[key] ?? HASHTAG_SUGGESTIONS["default"];
}

export function getAllSuggestions(industry: string | null): string[] {
  const groups = getSuggestionsForIndustry(industry);
  return groups.flatMap((g) => g.hashtags);
}
