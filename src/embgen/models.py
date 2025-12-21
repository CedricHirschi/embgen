"""Base models shared across all domains."""

from typing import Optional

from pydantic import BaseModel


class Enum(BaseModel):
    """Enumeration value used in both commands and registers."""

    name: str
    description: Optional[str] = None
    value: int
