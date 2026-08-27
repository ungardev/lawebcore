"""Comentario model — individual comment for sentiment analysis."""

import uuid
from datetime import datetime

from sqlalchemy import Numeric, String, Text, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, UUIDMixin


class Comentario(Base, UUIDMixin):
    __tablename__ = "comentarios"

    publicacion_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), nullable=False
    )
    autor_handle: Mapped[str | None] = mapped_column(String(100))
    texto: Mapped[str] = mapped_column(Text, nullable=False)
    sentimiento: Mapped[str | None] = mapped_column(String(20))
    confianza: Mapped[float | None] = mapped_column(Numeric(3, 2))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False  # noqa: F821
    )
