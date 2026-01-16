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

    # Meta field: Which numbers to generate for this register
    # Example: Register 'data' has numbers 0 to 15
    # This would generate registers data0, data1, ..., data15
    numbers: Optional[list[int]] = None


class RegisterGroup(BaseModel):
    """A group of identical registers with different indices (from 'numbers' expansion).

    This represents the original register definition before expansion,
    allowing templates to generate a single base class/struct with array access.
    """

    name: str  # Base name (e.g., "DATA")
    description: Optional[str] = None
    base_address: int  # Starting address
    access: Access = Access.RW
    bitfields: list[BitField]
    numbers: list[int]  # The indices (e.g., [0, 1, 2, ..., 15])


class RegistersConfig(BaseModel):
    """Top-level register map configuration."""

    name: str
    file: Optional[str] = None
    regmap: list[Register]
    register_groups: list[RegisterGroup] = []  # Groups of numbered registers

    @property
    def output_filename(self) -> str:
        return self.file or self.name.lower()
