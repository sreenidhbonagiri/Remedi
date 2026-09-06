from __future__ import annotations

from typing import TYPE_CHECKING

from sqlalchemy import Boolean, Float, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base

if TYPE_CHECKING:
    from app.models.program import Program


class Medication(Base):
    __tablename__ = "medications"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(255), index=True)
    generic_name: Mapped[str] = mapped_column(String(255), default="", index=True)
    strength: Mapped[str] = mapped_column(String(128), default="")
    form: Mapped[str] = mapped_column(String(64), default="")
    program_id: Mapped[int] = mapped_column(ForeignKey("programs.id"))
    ndc: Mapped[str] = mapped_column(String(32), default="", index=True)
    cash_price: Mapped[float | None] = mapped_column(Float, nullable=True, default=None)
    te_code: Mapped[str] = mapped_column(String(8), default="")
    is_generic: Mapped[bool] = mapped_column(Boolean, default=False)

    program: Mapped[Program] = relationship(back_populates="medications")
