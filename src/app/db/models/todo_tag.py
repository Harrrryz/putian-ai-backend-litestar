from __future__ import annotations

from typing import TYPE_CHECKING
from uuid import UUID  # noqa: TC003

from advanced_alchemy.base import UUIDAuditBase
from sqlalchemy import ForeignKey
from sqlalchemy.ext.associationproxy import AssociationProxy, association_proxy
from sqlalchemy.orm import Mapped, mapped_column, relationship

if TYPE_CHECKING:
    from .tag import Tag
    from .todo import Todo


class TodoTag(UUIDAuditBase):
    """Todo Tag."""

    __tablename__ = "user_account_todo_tag"
    __table_args__ = {"comment": "Links a user to a specific todo tag."}
    todo_id: Mapped[UUID] = mapped_column(ForeignKey(
        "todo.id", ondelete="cascade"), nullable=False)
    tag_id: Mapped[UUID] = mapped_column(ForeignKey(
        "tag.id", ondelete="cascade"), nullable=False)

    # -----------
    # ORM Relationships
    # ------------
    todo: Mapped[Todo] = relationship(
        back_populates="todo_tags", innerjoin=True, uselist=False, lazy="joined")
    tag: Mapped[Tag] = relationship(
        back_populates="tag_todos", innerjoin=True, uselist=False, lazy="joined")

    todo_item: AssociationProxy[str] = association_proxy("todo", "item")
    tag_name: AssociationProxy[str] = association_proxy("tag", "name")
    tag_color: AssociationProxy[str | None] = association_proxy("tag", "color")
