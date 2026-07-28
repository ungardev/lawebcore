"""Generador de propuestas CSV para campaigns de influencers."""
import csv
import io
from datetime import datetime


def generate_proposal_csv(candidates: list[dict], product_name: str = "Influencer Proposal") -> bytes:
    """Genera un CSV con los top candidatos para propuesta comercial."""
    output = io.StringIO()
    writer = csv.writer(output)

    writer.writerow([
        "#",
        "Handle",
        "Nombre completo",
        "Seguidores",
        "ER (%)",
        "Score",
        "Tier",
        "País",
        "Ciudad",
        "¿Tienda?",
        "Alcance esperado",
        "Engagement esperado",
        "Rationale",
    ])

    for i, c in enumerate(candidates[:10], 1):
        er_pct = f"{(c.get("engagement_rate", 0) or 0) * 100:.1f}"
        followers = c.get("followers", 0) or 0
        match_score = c.get("match_score", 0) or 0
        tier = c.get("tier", "—") or "—"
        city = c.get("city") or "—"
        bio_preview = (c.get("bio") or "")[:80].replace("\n", " ").strip()

        writer.writerow([
            i,
            c.get("handle", ""),
            c.get("full_name") or "—",
            f"{followers:,}",
            er_pct,
            f"{match_score:.1f}",
            tier,
            c.get("country", "VE") or "VE",
            city,
            "Sí" if c.get("is_tienda") else "No",
            c.get("expected_reach", 0) or 0,
            c.get("expected_engagement", 0) or 0,
            bio_preview,
        ])

    writer.writerow([])
    writer.writerow([f"Generado por Influencer Lens · La Web Figital Agency · {datetime.now().strftime('%d/%m/%Y %H:%M')}"])
    writer.writerow([f"Producto: {product_name} · Total candidatos: {len(candidates)}"])

    return output.getvalue().encode("utf-8")
