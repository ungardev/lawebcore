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

export function formatNumber(n: number | null): string {
  if (n == null) return "—";
  if (n >= 1_000_000) return `${(n / 1_000_000).toFixed(1)}M`;
  if (n >= 1_000) return `${(n / 1_000).toFixed(1)}K`;
  return String(n);
}

export function getCredibilityLabel(score: number | null): { label: string; color: string } {
  if (score == null) return { label: "—", color: "text-muted-foreground" };
  if (score >= 60) return { label: "Alta", color: "text-success" };
  if (score >= 40) return { label: "Media", color: "text-warning" };
  return { label: "Baja", color: "text-destructive" };
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
      return "border-brand-purple/30 bg-brand-purple/10 text-brand-purple";
    case "MID":
      return "border-info/30 bg-info/10 text-info";
    case "MICRO":
      return "border-success/30 bg-success/10 text-success";
    case "NANO":
      return "border-warning/30 bg-warning/10 text-warning";
    default:
      return "border-divider bg-surface-raised text-muted-foreground";
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
