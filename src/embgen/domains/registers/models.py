"""Register map domain models."""

from enum import Enum as BaseEnum
from typing import Optional

from pydantic import BaseModel

from ...models import Enum


class Access(BaseEnum):
    """Register access type."""

    RO = "ro"
    RW = "rw"
    WO = "wo"
    RWC = "rw1c"
    WOS = "wosc"
    ROLH = "rolh"

    def __str__(self) -> str:
        return self.name

    def __repr__(self) -> str:
        return "Access." + str(self)


class BitField(BaseModel):
    """A bitfield within a register."""

    name: str
    description: Optional[str] = None
    reset: int
    width: int
    offset: int
    enums: Optional[list[Enum]] = None


class Register(BaseModel):
    """A hardware register definition."""

    name: str
    description: Optional[str] = None
    address: int
    access: Access = Access.RW
    bitfields: list[BitField]


class RegistersConfig(BaseModel):
    """Top-level register map configuration."""

    name: str
    file: Optional[str] = None
    regmap: list[Register]

    @property
    def output_filename(self) -> str:
        return self.file or self.name.lower()
