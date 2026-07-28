export function formatScore(score: number): string {
  if (score == null || isNaN(score)) return "—";
  return `${Math.round(score)}`;
}

export function formatEngagement(er: number | null): string {
  if (er == null) return "—";
  return `${(er * 100).toFixed(1)}%`;
}

export function formatFollowers(n: number | null): string {
  if (n == null) return "—";
  if (n >= 1_000_000) return `${(n / 1_000_000).toFixed(1)}M`;
  if (n >= 1_000) return `${(n / 1_000).toFixed(1)}K`;
  return String(n);
}

export function classifyTier(
  followers: number | null,
): "NANO" | "MICRO" | "MID" | "MACRO" | null {
  if (followers == null) return null;
  if (followers < 10_000) return "NANO";
  if (followers < 100_000) return "MICRO";
  if (followers < 500_000) return "MID";
  return "MACRO";
}

const TIENDA_PATTERNS = [
  "tienda",
  "shop",
  "ventas",
  "pedidos",
  "catálogo",
  "mayor y detal",
  "envíos",
  "mercado libre",
  "delivery",
  "comprar aquí",
  "adquirir",
  "whatsapp",
  "telf",
  "Teléfono",
];

export function isTienda(bio: string | null): boolean {
  if (!bio) return false;
  const lower = bio.toLowerCase();
  return TIENDA_PATTERNS.some((p) => lower.includes(p));
}

export function getTierColor(tier: string | null): string {
  switch (tier) {
    case "MACRO":
      return "bg-purple-100 text-purple-700 border-purple-200";
    case "MID":
      return "bg-blue-100 text-blue-700 border-blue-200";
    case "MICRO":
      return "bg-green-100 text-green-700 border-green-200";
    case "NANO":
      return "bg-yellow-100 text-yellow-700 border-yellow-200";
    default:
      return "bg-gray-100 text-gray-700 border-gray-200";
  }
}

export function getTierLabel(tier: string | null): string {
  if (!tier) return "—";
  const labels: Record<string, string> = {
    MACRO: "Macro",
    MID: "Mid",
    MICRO: "Micro",
    NANO: "Nano",
  };
  return labels[tier] ?? tier;
}
