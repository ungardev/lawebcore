"""LangGraph Orchestrator — state machine for conversational discovery."""

import asyncio
from typing import Any
from uuid import UUID

import structlog

logger = structlog.get_logger(__name__)

from discovery.brief_parser import brief_parser_agent
from discovery.query_builder import query_builder
from discovery.result_ranker import result_ranker
from discovery.schemas import (
    BriefStructured,
    CandidateMetrics,
    CandidateWithScore,
    ConversationStep,
    DiscoveryRunResponse,
    DiscoverySearchRequest,
    DiscoveryPlan,
    MessageCreate,
    MessageResponse,
    Platform,
)
from discovery.tools import apify_client, meta_client, metricool_client, tiktok_client, youtube_client
from shared_core.supabase_rest import supabase_rest

_AFFIRMATIVE_KEYWORDS = {
    "si", "sí", "sii", "siii", "siiii", "confirmo", "confirmar", "confirmado",
    "perfecto", "perfecta", "correcto", "correcta", "dale", "adelante", "vamos",
    "venga", "go", "launch", "ejecuta", "ejecutar", "lanzar", "lanza",
    "arranca", "arrancalo", "arráncalo", "manos a la obra",
    "todo bien", "todo ok", "todo correcto", "esta bien", "está bien",
    "estoy de acuerdo", "de acuerdo", "ok", "okay", "k",
    "si por favor", "si dale", "genial", "excelente", "buenisimo",
    "buenísimo", "bueno", "vamos a ello", "manos a la obra",
    "yes", "yeah", "yep", "yup", "sure", "correct", "perfect",
    "great", "let's do it", "do it", "run it", "launch", "execute",
    "proceed", "ready", "let's go", "lets go",
}


class ConversationState:
    def __init__(self):
        self.step: ConversationStep = ConversationStep.START
        self.brief_structured: BriefStructured | None = None
        self.accumulated_brief: str = ""
        self.discovery_run_id: UUID | None = None
        self.candidates: list[CandidateWithScore] = []
        self.messages: list[MessageResponse] = []
        self.pending_refinements: list[str] = []


class DiscoveryOrchestrator:
    def __init__(self):
        self.state: dict[UUID, ConversationState] = {}

    async def create_conversation(self, conversation_id: UUID, initial_brief: str | None = None) -> dict[str, Any]:
        state = ConversationState()
        self.state[conversation_id] = state

        if initial_brief:
            state.accumulated_brief = initial_brief
            return await self._process_message(conversation_id, initial_brief)

        state.step = ConversationStep.START
        return {
            "conversation_id": str(conversation_id),
            "step": state.step.value,
            "message": "Soy Influencer Lens, el cerebro estratégico de La Web Figital Agency. Llevo 12 años haciendo influencer marketing en Latam — sé exactamente qué creators funcionan en Venezuela y por qué.\n\nCuéntame sobre la campaña que quieres planificar. ¿Qué producto o marca? ¿Qué mercado? ¿Tienes ya un presupuesto en mente?",
            "candidates": [],
        }

    async def process_message(
        self, conversation_id: UUID, message: MessageCreate
    ) -> dict[str, Any]:
        if conversation_id not in self.state:
            raise ValueError(f"Conversation {conversation_id} not found")

        state = self.state[conversation_id]
        state.accumulated_brief += f"\n\nUsuario: {message.content}"

        return await self._process_message(conversation_id, message.content)

    async def _process_message(
        self, conversation_id: UUID, content: str
    ) -> dict[str, Any]:
        state = self.state[conversation_id]

        if state.step == ConversationStep.START:
            return await self._step_start(conversation_id, content)

        elif state.step == ConversationStep.BRIEF:
            return await self._step_brief(conversation_id, content)

        elif state.step == ConversationStep.REFINING:
            return await self._step_refining(conversation_id, content)

        elif state.step == ConversationStep.CANDIDATES_REVIEW:
            return await self._step_candidates_review(conversation_id, content)

        else:
            return {
                "conversation_id": str(conversation_id),
                "step": state.step.value,
                "message": "La conversación ha terminado. ¿Quieres hacer otra búsqueda?",
                "candidates": [],
            }

    async def _step_start(
        self, conversation_id: UUID, content: str
    ) -> dict[str, Any]:
        state = self.state[conversation_id]

        try:
            brief = await brief_parser_agent.parse(content)
        except Exception as e:
            logger.error(
                "brief_parser_failed",
                error=str(e),
                exc_info=True,
                conversation_id=str(conversation_id),
                content_preview=content[:200],
            )
            brief = self._build_fallback_brief(content)

        state.brief_structured = brief
        state.step = ConversationStep.BRIEF

        confirmation = self._brief_to_text(brief)

        return {
            "conversation_id": str(conversation_id),
            "step": state.step.value,
            "message": (
                f"Entendí tu brief. Déjame confirmar:\n\n{confirmation}\n\n"
                f"¿Está correcto o quieres ajustar algo? "
                f"(país, plataformas, presupuesto, tono, etc.)"
            ),
            "brief": state.brief_structured.model_dump() if state.brief_structured else None,
            "candidates": [],
        }

    async def _step_brief(
        self, conversation_id: UUID, content: str
    ) -> dict[str, Any]:
        state = self.state[conversation_id]

        if any(kw in content.lower() for kw in _AFFIRMATIVE_KEYWORDS):
            if not state.brief_structured or not state.brief_structured.niches:
                logger.warning(
                    "brief_structured_empty_reparsing",
                    conversation_id=str(conversation_id),
                    accumulated_brief_preview=state.accumulated_brief[:200],
                )
                try:
                    state.brief_structured = await brief_parser_agent.parse(
                        state.accumulated_brief
                    )
                    logger.info(
                        "brief_reparsed_successfully",
                        conversation_id=str(conversation_id),
                        niches=state.brief_structured.niches,
                        platforms=[p.value for p in state.brief_structured.platforms] if state.brief_structured.platforms else [],
                    )
                except Exception as e:
                    logger.error(
                        "brief_reparse_failed_using_fallback",
                        conversation_id=str(conversation_id),
                        error=str(e),
                        exc_info=True,
                    )
                    state.brief_structured = self._build_fallback_brief(state.accumulated_brief)

            state.step = ConversationStep.SEARCHING
            return {
                "conversation_id": str(conversation_id),
                "step": state.step.value,
                "message": "Buscando candidatos reales en Instagram, TikTok y YouTube usando Apify... Te aviso cuando tenga resultados. Esto puede tomar entre 30 segundos y 2 minutos.",
                "brief": state.brief_structured.model_dump() if state.brief_structured else None,
                "candidates": [],
                "pending_discovery": True,
            }

        state.step = ConversationStep.REFINING
        state.pending_refinements.append(content)
        return {
            "conversation_id": str(conversation_id),
            "step": state.step.value,
            "message": "Perfecto, dime qué quieres ajustar y continuamos.",
            "candidates": [],
        }

    async def _step_refining(
        self, conversation_id: UUID, content: str
    ) -> dict[str, Any]:
        state = self.state[conversation_id]

        if any(kw in content.lower() for kw in _AFFIRMATIVE_KEYWORDS):
            if not state.brief_structured or not state.brief_structured.niches:
                try:
                    state.brief_structured = await brief_parser_agent.parse(
                        state.accumulated_brief
                    )
                except Exception as e:
                    logger.error(
                        "brief_reparse_failed_using_fallback",
                        conversation_id=str(conversation_id),
                        error=str(e),
                        exc_info=True,
                    )
                    state.brief_structured = self._build_fallback_brief(state.accumulated_brief)

            state.step = ConversationStep.SEARCHING
            return {
                "conversation_id": str(conversation_id),
                "step": state.step.value,
                "message": "Buscando candidatos reales en Instagram, TikTok y YouTube usando Apify... Te aviso cuando tenga resultados. Esto puede tomar entre 30 segundos y 2 minutos.",
                "brief": state.brief_structured.model_dump() if state.brief_structured else None,
                "candidates": [],
                "pending_discovery": True,
            }

        try:
            new_brief = await brief_parser_agent.parse(
                state.accumulated_brief + "\n\nUsuario refina: " + content
            )
            state.brief_structured = new_brief
        except Exception as e:
            logger.error(
                "brief_parser_refine_failed",
                error=str(e),
                exc_info=True,
                conversation_id=str(conversation_id),
            )

        confirmation = self._brief_to_text(state.brief_structured)
        return {
            "conversation_id": str(conversation_id),
            "step": ConversationStep.REFINING.value,
            "message": (
                f"Brief actualizado:\n\n{confirmation}\n\n"
                f"¿Confirmas para ejecutar la búsqueda?"
            ),
            "brief": state.brief_structured.model_dump() if state.brief_structured else None,
            "candidates": [],
        }

    async def _step_candidates_review(
        self, conversation_id: UUID, content: str
    ) -> dict[str, Any]:
        state = self.state[conversation_id]

        if any(kw in content.lower() for kw in ["otra búsqueda", "nueva búsqueda", "reiniciar"]):
            state.step = ConversationStep.START
            state.candidates = []
            state.brief_structured = None
            state.accumulated_brief = ""
            return {
                "conversation_id": str(conversation_id),
                "step": state.step.value,
                "message": "Perfecto, empecemos de nuevo. ¿Qué campaña quieres planificar?",
                "candidates": [],
            }

        return {
            "conversation_id": str(conversation_id),
            "step": state.step.value,
            "message": "Revisa los candidatos arriba. ¿Quieres aprobar algunos, buscar más, o empezar una nueva búsqueda?",
            "candidates": [c.model_dump() for c in state.candidates],
        }

    async def _execute_discovery(
        self, conversation_id: UUID
    ) -> dict[str, Any]:
        state = self.state[conversation_id]
        brief = state.brief_structured

        if not brief:
            return {
                "conversation_id": str(conversation_id),
                "step": state.step.value,
                "message": "No tengo un brief válido. ¿Podrías describir la campaña de nuevo?",
                "candidates": [],
            }

        state.step = ConversationStep.SEARCHING

        plan: DiscoveryPlan = query_builder.build(brief)

        return {
            "conversation_id": str(conversation_id),
            "step": state.step.value,
            "message": (
                f"Ejecutando pipeline de 4 capas con {len(plan.keyword_queries)} keywords "
                f"y {len(plan.hashtag_queries)} hashtags... "
                f"El worker procesará todo y te notificaré cuando esté listo."
            ),
            "candidates": [],
            "pending_discovery": True,
            "run_summary": {
                "keywords_count": len(plan.keyword_queries),
                "hashtags_count": len(plan.hashtag_queries),
                "enrichment_batch_size": plan.enrichment_batch_size,
                "analytics_top_n": plan.analytics_top_n,
            },
        }

    def _raw_to_candidate_metrics(
        self, raw: dict[str, Any], platform: Any
    ) -> CandidateMetrics:
        from discovery.schemas import Platform

        p = Platform(platform.value) if isinstance(platform, Any) else platform

        if p == Platform.INSTAGRAM:
            return CandidateMetrics(
                platform=p,
                handle=raw.get("username", raw.get("handle", "")),
                full_name=raw.get("fullName", raw.get("full_name", "")),
                bio=raw.get("biography", raw.get("bio", "")),
                avatar_url=raw.get("profilePicUrlHD", raw.get("avatar_url", "")),
                followers=raw.get("followersCount", raw.get("followers", 0)),
                following=raw.get("followsCount", raw.get("following", 0)),
                posts_count=raw.get("postsCount", raw.get("posts_count", 0)),
                engagement_rate=raw.get("avgLikesPercent", raw.get("engagement_rate", 0)),
                url=raw.get("url", f"https://instagram.com/{raw.get('username', '')}"),
                raw_payload=raw,
            )
        elif p == Platform.TIKTOK:
            return CandidateMetrics(
                platform=p,
                handle=raw.get("author", {}).get("uniqueId", raw.get("handle", "")),
                full_name=raw.get("author", {}).get("nickname", ""),
                followers=raw.get("stats", {}).get("followerCount", 0),
                avg_views=raw.get("stats", {}).get("videoView", 0),
                posts_count=raw.get("videoCount", 0),
                engagement_rate=raw.get("engagement_rate", 0.05),
                url=raw.get("shareUrl", ""),
                raw_payload=raw,
            )
        elif p == Platform.YOUTUBE:
            snippet = raw.get("snippet", {})
            stats = raw.get("channel_details", {}).get("statistics", {})
            return CandidateMetrics(
                platform=p,
                handle=snippet.get("channelTitle", ""),
                full_name=snippet.get("channelTitle", ""),
                bio=snippet.get("description", ""),
                followers=int(stats.get("subscriberCount", 0)),
                posts_count=int(stats.get("videoCount", 0)),
                engagement_rate=0.02,
                avatar_url=snippet.get("thumbnails", {}).get("high", {}).get("url", ""),
                url=f"https://youtube.com/channel/{raw.get('id', '')}",
                raw_payload=raw,
            )
        return CandidateMetrics(platform=p, handle="unknown", raw_payload=raw)

    def _brief_to_text(self, brief: BriefStructured | None) -> str:
        if not brief:
            return "Brief no disponible."

        parts = []
        if brief.product_name:
            parts.append(f"**Producto:** {brief.product_name}")
        if brief.industry:
            parts.append(f"**Industria:** {brief.industry}")
        if brief.niches:
            parts.append(f"**Nichos:** {', '.join(brief.niches)}")
        if brief.audience_countries:
            parts.append(f"**Países:** {', '.join(brief.audience_countries)}")
        if brief.audience_cities:
            parts.append(f"**Ciudades:** {', '.join(brief.audience_cities)}")
        parts.append(f"**Género objetivo:** {brief.audience_gender.value}")
        parts.append(f"**Edad:** {brief.audience_age_min}-{brief.audience_age_max}")
        if brief.platforms:
            parts.append(f"**Plataformas:** {', '.join(p.value for p in brief.platforms)}")
        if brief.budget_usd:
            parts.append(f"**Presupuesto:** ${brief.budget_usd:,.0f} USD")
        if brief.tone:
            parts.append(f"**Tono:** {', '.join(brief.tone)}")
        if brief.additional_context:
            parts.append(f"**Contexto adicional:** {brief.additional_context[:100]}")

        return "\n".join(parts)

    def _build_fallback_brief(self, accumulated_text: str) -> BriefStructured:
        text_lower = accumulated_text.lower()
        niches = []
        if any(w in text_lower for w in ["perro", "perros", "mascota", "mascotas", "dog", "cat", "gato", "pet"]):
            niches.extend(["mascotas", "perros", "pet_care"])
        if any(w in text_lower for w in ["cafe", "coffee"]):
            niches.extend(["cafe", "coffee", "foodie"])
        if any(w in text_lower for w in ["moda", "fashion", "ropa"]):
            niches.extend(["moda", "fashion", "lifestyle"])
        if any(w in text_lower for w in ["belleza", "beauty", "skincare", "cosmético"]):
            niches.extend(["belleza", "beauty", "skincare"])
        if not niches:
            niches = ["lifestyle", "general"]
        platforms = [Platform.INSTAGRAM]
        if "tiktok" in text_lower or "tik tok" in text_lower:
            platforms.append(Platform.TIKTOK)
        if "youtube" in text_lower or "yt" in text_lower:
            platforms.append(Platform.YOUTUBE)
        countries = ["VE"]
        if "colombia" in text_lower:
            countries.append("CO")
        if "méxico" in text_lower or "mexico" in text_lower:
            countries.append("MX")
        cities = []
        for c, kws in [
            ("Caracas", ["caracas"]),
            ("Valencia", ["valencia"]),
            ("Maracaibo", ["maracaibo"]),
            ("Bogotá", ["bogota", "bogotá"]),
        ]:
            if any(k in text_lower for k in kws):
                cities.append(c)
        budget = None
        import re
        budget_match = re.search(r"\$?\s*(\d{1,3}(?:[.,]\d{3})*)\s*(?:usd|dólares|dolares)?", text_lower)
        if budget_match:
            try:
                budget = float(budget_match.group(1).replace(",", ""))
            except ValueError:
                pass
        return BriefStructured(
            product_name=None,
            industry="pet_food" if any(w in text_lower for w in ["perro", "perros", "mascota", "pet"]) else "general",
            niches=niches,
            audience_gender="female" if any(w in text_lower for w in ["mujer", "mama", "mamá", "dueña", "female"]) else "all",
            audience_age_min=25,
            audience_age_max=45,
            audience_countries=countries,
            audience_cities=cities if cities else None,
            budget_usd=budget,
            tone=["emocional"],
            platforms=platforms,
            additional_context=accumulated_text[:500],
        )

    def _candidates_to_text(self, candidates: list[CandidateWithScore]) -> str:
        lines = []
        for i, c in enumerate(candidates[:5], 1):
            m = c.metrics
            s = c.score
            lines.append(
                f"**{i}. @{m.handle}** ({m.platform.value}) "
                f"| Score: {s.match_score:.0f}/100 "
                f"| Followers: {m.followers or 'N/A':,} "
                f"| ER: {(m.engagement_rate or 0):.2%} "
                f"| Costo est.: ${s.estimated_cost or 'N/A'} "
                f"| Reach est.: {s.expected_reach or 'N/A':,}"
            )
        return "\n".join(lines) if lines else "No se encontraron candidatos."


orchestrator = DiscoveryOrchestrator()
