"""LangGraph Orchestrator — máquina de estados para discovery conversacional IA."""

import asyncio
from typing import Any
from uuid import UUID

from app.discovery.brief_parser import brief_parser_agent
from app.discovery.query_builder import query_builder, SearchQuery
from app.discovery.result_ranker import result_ranker
from app.discovery.schemas import (
    BriefStructured,
    CandidateMetrics,
    CandidateWithScore,
    ConversationStep,
    DiscoveryRunResponse,
    DiscoverySearchRequest,
    MessageCreate,
    MessageResponse,
)
from app.discovery.tools import apify_client, meta_client, metricool_client, tiktok_client, youtube_client


class ConversationState:
    """Estado en memoria de una conversación (guardado en DB por memory.py)."""

    def __init__(self):
        self.step: ConversationStep = ConversationStep.START
        self.brief_structured: BriefStructured | None = None
        self.accumulated_brief: str = ""
        self.discovery_run_id: UUID | None = None
        self.candidates: list[CandidateWithScore] = []
        self.messages: list[MessageResponse] = []
        self.pending_refinements: list[str] = []


class DiscoveryOrchestrator:
    """Orquestador LangGraph-style para el flujo de discovery conversacional."""

    def __init__(self):
        self.state: dict[UUID, ConversationState] = {}

    async def create_conversation(self, conversation_id: UUID, initial_brief: str | None = None) -> dict[str, Any]:
        """Crea una conversación nueva y procesa el brief inicial si se provee."""
        state = ConversationState()
        self.state[conversation_id] = state

        if initial_brief:
            state.accumulated_brief = initial_brief
            return await self._process_message(conversation_id, initial_brief)

        state.step = ConversationStep.START
        return {
            "conversation_id": str(conversation_id),
            "step": state.step.value,
            "message": "Hola, soy tu asistente de discovery de influencers. Cuéntame sobre la campaña que quieres planificar. ¿Qué producto, marca o servicio quieres promover?",
            "candidates": [],
        }

    async def process_message(
        self, conversation_id: UUID, message: MessageCreate
    ) -> dict[str, Any]:
        """Procesa un mensaje del usuario dentro de una conversación existente."""
        if conversation_id not in self.state:
            raise ValueError(f"Conversation {conversation_id} not found")

        state = self.state[conversation_id]
        state.accumulated_brief += f"\n\nUsuario: {message.content}"

        return await self._process_message(conversation_id, message.content)

    async def _process_message(
        self, conversation_id: UUID, content: str
    ) -> dict[str, Any]:
        """Máquina de estados que procesa cada mensaje."""
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
        """Estado inicial: parsear el primer brief."""
        state = self.state[conversation_id]

        try:
            brief = await brief_parser_agent.parse(content)
        except Exception:
            brief = BriefStructured(additional_context=content[:500])

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
        """Brief confirmado → delegar ejecución al worker."""
        state = self.state[conversation_id]

        if any(kw in content.lower() for kw in ["sí", "si", "correcto", "perfecto", "adelante", "sí está"]):
            state.step = ConversationStep.SEARCHING
            return {
                "conversation_id": str(conversation_id),
                "step": state.step.value,
                "message": "Buscando candidatos en todas las plataformas... Te aviso cuando tenga resultados.",
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
        """Refinando criterios del brief."""
        state = self.state[conversation_id]

        try:
            new_brief = await brief_parser_agent.parse(
                state.accumulated_brief + "\n\nUsuario refina: " + content
            )
            state.brief_structured = new_brief
        except Exception:
            pass

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
        """Usuario revisando candidatos."""
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
        """Ejecuta la búsqueda de candidatos en todas las plataformas."""
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

        queries = query_builder.build(brief)
        all_candidates: list[CandidateWithScore] = []

        for platform, platform_queries in queries.items():
            for q in platform_queries:
                try:
                    candidates = await self._execute_query(platform, q)
                    for raw in candidates:
                        metrics = self._raw_to_candidate_metrics(raw, platform)
                        score = result_ranker.rank(metrics, brief)
                        all_candidates.append(
                            CandidateWithScore(
                                id=UUID("00000000-0000-0000-0000-000000000001"),
                                metrics=metrics,
                                score=score,
                            )
                        )
                except Exception:
                    pass

        unique_by_handle = {}
        for c in all_candidates:
            key = f"{c.metrics.platform.value}:{c.metrics.handle}"
            if key not in unique_by_handle or c.score.match_score > unique_by_handle[key].score.match_score:
                unique_by_handle[key] = c

        top_candidates = sorted(
            unique_by_handle.values(),
            key=lambda x: x.score.match_score,
            reverse=True,
        )[:20]

        state.candidates = top_candidates
        state.step = ConversationStep.CANDIDATES_REVIEW

        candidates_text = self._candidates_to_text(top_candidates)

        return {
            "conversation_id": str(conversation_id),
            "step": state.step.value,
            "message": (
                f"Encontré {len(top_candidates)} candidatos que encajan con tu brief.\n\n"
                f"{candidates_text}\n\n"
                f"¿Quieres aprobar algunos, ver más detalles, o hacer otra búsqueda?"
            ),
            "candidates": [c.model_dump() for c in top_candidates],
            "run_summary": {
                "total_found": len(all_candidates),
                "top_score": top_candidates[0].score.match_score if top_candidates else 0,
                "platforms_queried": [p.value for p in queries.keys()],
            },
        }

    async def _execute_query(
        self, platform: Any, query: SearchQuery
    ) -> list[dict[str, Any]]:
        """Ejecuta una query en la plataforma correspondiente."""
        if platform.value == "instagram":
            if query.query_type == "hashtag_search":
                return await apify_client.search_instagram_by_hashtag(
                    hashtag=query.params["hashtag"],
                    country=query.params.get("country", "VE"),
                    min_followers=query.params.get("min_followers", 1000),
                    max_followers=query.params.get("max_followers", 10_000_000),
                )
        elif platform.value == "tiktok":
            if query.query_type == "hashtag_search":
                return await tiktok_client.search_content(
                    query=query.params["hashtag"],
                    country=query.params.get("country", "VE"),
                    max_count=50,
                )
        elif platform.value == "youtube":
            channels = await youtube_client.search_channels(
                query=query.params.get("query", ""),
                region=query.params.get("region", "VE"),
                max_results=20,
            )
            return channels
        return []

    def _raw_to_candidate_metrics(
        self, raw: dict[str, Any], platform: Any
    ) -> CandidateMetrics:
        """Convierte el payload raw de cada fuente a CandidateMetrics."""
        from app.discovery.schemas import Platform

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
        """Convierte un BriefStructured a texto legible."""
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

    def _candidates_to_text(self, candidates: list[CandidateWithScore]) -> str:
        """Convierte una lista de candidatos a texto legible."""
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
