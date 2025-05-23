from typing import Literal

from pydantic import BaseModel

from app.__about__ import __version__ as current_version
from app.config.base import get_settings

__all__ = ("SystemHealth",)

settings = get_settings()


class SystemHealth(BaseModel):
    database_status: Literal["online", "offline"]
    app: str = settings.app.NAME
    version: str = current_version
