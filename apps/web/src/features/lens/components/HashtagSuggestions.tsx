export interface HashtagSuggestionGroup {
  label: string;
  hashtags: string[];
}

// FIX coherencia backend (04-sep-2026): las sugerencias ahora son los mismos
// tags que VE_NICHE_HASHTAGS en packages/discovery/discovery/query_builder.py
// — los que el pipeline ya sabe que funcionan para cuentas venezolanas.
// Nota de ejecución: los hashtags del brief van PRIMEROS en la lista y solo
// los primeros 6 se buscan en Top + los primeros 4 en Recientes — elegir de
// estos grupos = elegir exactamente lo que el worker ejecutará.
export const HASHTAG_SUGGESTIONS: Record<string, HashtagSuggestionGroup[]> = {
  mascotas: [
    {
      label: "Comunidad VE · las ejecuta el pipeline",
      hashtags: ["mascotasvzla", "perrosvzla", "gatosvzla", "petloversvzla", "veterinariavzla", "cachorrosvzla", "amigospeludos"],
    },
    {
      label: "Adopción y rescate",
      hashtags: ["adoptavzla", "adopcionmascotas", "rescateanimalvzla", "rescatedemascotasvzla"],
    },
    {
      label: "Ciudades VE",
      hashtags: ["mascotascaracas", "perroscaracas", "gatoscaracas", "mascotasmaracaibo", "mascotasvalencia", "petloverscaracas"],
    },
    {
      label: "Globales del nicho",
      hashtags: ["dogsofinstagram", "instadog", "petlovers", "doglife", "catlovers"],
    },
  ],
  belleza: [
    {
      label: "Comunidad VE · las ejecuta el pipeline",
      hashtags: ["bellezavzla", "makeupvzla", "skincarevzla", "beautyve", "bellezacaracas", "makeupcaracas"],
    },
    {
      label: "Especialidad",
      hashtags: ["haircaracas", "nailsvzla", "cosmeticavzla", "makeupartist", "skincareaddict"],
    },
    {
      label: "Latam",
      hashtags: ["bellezalatina", "makeuplatino", "skincarelatino", "glowingskin"],
    },
  ],
  food: [
    {
      label: "Comunidad VE · las ejecuta el pipeline",
      hashtags: ["comidavzla", "foodve", "comidavenezolana", "gastronomiavzla", "foodcaracas", "comidacaracas"],
    },
    {
      label: "Temáticos VE",
      hashtags: ["arepavzla", "recetasvzla", "cocinavzla", "foodiesvzla", "foodpornvzla", "comidastipicasvzla"],
    },
    {
      label: "Globales",
      hashtags: ["foodie", "instafood", "foodporn", "yummy"],
    },
  ],
  moda: [
    {
      label: "Comunidad VE · las ejecuta el pipeline",
      hashtags: ["modavzla", "fashionve", "modacaracas", "fashioncaracas", "outfitvzla", "ropavzla"],
    },
    {
      label: "Estilo",
      hashtags: ["estilovzla", "tendenciasvzla", "fashionvzla", "modalatina", "streetwear"],
    },
  ],
  fitness: [
    {
      label: "Comunidad VE · las ejecuta el pipeline",
      hashtags: ["fitnessvzla", "gymvzla", "gymcaracas", "fitnesscaracas", "gimnasiovzla", "deportevzla"],
    },
    {
      label: "Entrenamiento",
      hashtags: ["entrenadorvzla", "fitve", "workoutvzla", "healthyvzla", "running", "yoga"],
    },
  ],
  tecnologia: [
    {
      label: "Comunidad VE · las ejecuta el pipeline",
      hashtags: ["techvzla", "tecnologiavzla", "techcaracas", "gadgetsvzla", "digitalvzla", "innovacionvzla"],
    },
    {
      label: "Globales",
      hashtags: ["techtok", "gadgets", "programacion", "apps"],
    },
  ],
  turismo: [
    {
      label: "Comunidad VE · las ejecuta el pipeline",
      hashtags: ["turismovzla", "viajesvzla", "turismocaracas", "viajescaracas", "viajesvenezuela", "destinosvzla"],
    },
    {
      label: "Experiencias",
      hashtags: ["exploravzla", "aventuravzla", "mochileros", "turismolatino", "viajeslatinos"],
    },
  ],
  entretenimiento: [
    {
      label: "Comunidad VE · las ejecuta el pipeline",
      hashtags: ["entretenimientovzla", "musicavzla", "cinevzla", "culturavzla", "artistasvzla", "entretenimientolatino"],
    },
  ],
  educacion: [
    {
      label: "Comunidad VE · las ejecuta el pipeline",
      hashtags: ["educacionvzla", "cursosvzla", "aprendizajevzla", "educacioncaracas", "universidadvzla", "educacionlatina"],
    },
  ],
  finanzas: [
    {
      label: "Comunidad VE · las ejecuta el pipeline",
      hashtags: ["finanzasvzla", "negociosvzla", "emprendedurismovzla", "inversionvzla", "negocioslatinos", "finanzaslatinas"],
    },
  ],
  hogar: [
    {
      label: "Comunidad VE · las ejecuta el pipeline",
      hashtags: ["hogarvzla", "decoracionvzla", "interiorismovzla", "casavzla", "hogarcaracas", "decoracioncaracas"],
    },
  ],
  deportes: [
    {
      label: "Comunidad VE · las ejecuta el pipeline",
      hashtags: ["deportesvzla", "futbolvzla", "beisbolvzla", "deportistasvzla", "ligavzla", "seleccionvzla"],
    },
  ],
  default: [
    {
      label: "Venezuela",
      hashtags: ["vzla", "venezuela", "caracas"],
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
