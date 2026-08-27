"""Publicacion model — metrics per influencer post."""

import uuid
from datetime import datetime

from sqlalchemy import BigInteger, Integer, Numeric, String, Text, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TimestampMixin, UUIDMixin


class Publicacion(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "publicaciones"

    campaign_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), nullable=False
    )
    influencer_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True)
    )

    fecha_publicacion: Mapped[datetime] = mapped_column(nullable=False)

    vistas: Mapped[int | None] = mapped_column(BigInteger)
    alcance: Mapped[int | None] = mapped_column(BigInteger)
    likes: Mapped[int | None] = mapped_column(Integer)
    comentarios: Mapped[int | None] = mapped_column(Integer)
    compartidos: Mapped[int | None] = mapped_column(Integer)
    guardados: Mapped[int | None] = mapped_column(Integer)

    er_alcance: Mapped[float | None] = mapped_column(Numeric(8, 6))
    er_vistas: Mapped[float | None] = mapped_column(Numeric(8, 6))
    retencion: Mapped[float | None] = mapped_column(Numeric(6, 4))

    sentimiento_positivo: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    sentimiento_neutro: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    sentimiento_negativo: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    url_publicacion: Mapped[str | None] = mapped_column(Text)
    plataforma: Mapped[str] = mapped_column(String(20), default="instagram", nullable=False)
    formato: Mapped[str | None] = mapped_column(String(20))
    source: Mapped[str] = mapped_column(String(20), default="SHEETS", nullable=False)
