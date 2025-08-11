from __future__ import annotations

from typing import TYPE_CHECKING
from uuid import UUID  # noqa: TC003

from advanced_alchemy.base import UUIDAuditBase
from sqlalchemy import ForeignKey, String
from sqlalchemy.ext.associationproxy import AssociationProxy, association_proxy
from sqlalchemy.orm import Mapped, mapped_column, relationship

if TYPE_CHECKING:
    from .todo_tag import TodoTag
    from .user import User


class Tag(UUIDAuditBase):
    __tablename__ = "tag"
    __table_args__ = ({"comment": "Tags for todos"},)

    name: Mapped[str] = mapped_column(
        String(length=100), index=True, nullable=False)
    color: Mapped[str | None] = mapped_column(
        String(length=100), nullable=True)

    user_id: Mapped[UUID] = mapped_column(
        ForeignKey("user_account.id", ondelete="CASCADE"), nullable=False
    )  # Assuming user_account table

    # ORM Relationship to UserModel
    user: Mapped[User] = relationship(
        back_populates="tags", lazy="joined"
    )
    tag_todos: Mapped[list[TodoTag]] = relationship(
        back_populates="tag", lazy="selectin", uselist=True, cascade="all, delete-orphan"
    )
    todos: AssociationProxy[list[User]] = association_proxy(
        "tag_todos", "todo",
    )
