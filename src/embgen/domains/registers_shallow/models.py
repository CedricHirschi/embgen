"""Register map domain models."""

from enum import Enum as BaseEnum
from typing import Literal, Optional, Union

from pydantic import BaseModel, Field, model_validator

from ...models import Enum, BaseConfig


class Access(BaseEnum):
    """Register access type."""

    RO = "ro"
    RW = "rw"
    WO = "wo"
    RWC = "rw1c"
    WOS = "wosc"
    ROLH = "rolh"
    HRO = "hro"
    HRW = "hrw"
    HWO = "hwo"

    def __str__(self) -> str:
        return self.name

    def __repr__(self) -> str:
        return "Access." + str(self)


class BitField(BaseModel):
    """A bitfield within a register."""

    name: str
    description: Optional[str] = None
    reset: Union[int, bool, Enum, str]
    width: int
    offset: int
    enums: Optional[list[Enum]] = None

    @model_validator(mode="after")
    def validate_reset(self) -> "BitField":
        if self.enums is not None:
            if isinstance(self.reset, str):
                found = False
                for enum in self.enums:
                    if enum.name == self.reset:
                        self.reset = enum.value
                        found = True
                        break

                if not found:
                    raise ValueError(
                        f"BitField {self.name} has invalid reset enum value: {self.reset}. Available enums: {[e.name for e in self.enums]}"
                    )
        return self


class Register(BaseModel):
    """A hardware register definition."""

    name: str
    description: Optional[str] = None
    address: int
    access: Access = Access.RW
    access_hw: Optional[Access] = None  # Separate hardware access type
    bitfields: list[BitField]

    # regtool specific fields (See https://opentitan.org/book/util/reggen/index.html)
    hwqe: bool = False  # If hardware uses ‘q’ enable signal, which is latched signal of software write pulse
    hwext: bool = False  # If the register is stored outside of the register module

    # Number of identical register instances to generate (indices 0..count-1)
    count: Optional[int] = Field(default=None, gt=0)

    # multireg-specific optional fields (passed through to hjson)
    cname: Optional[str] = None
    compact: Optional[bool] = None
    regwen_multi: bool = False


class RegisterGroup(BaseModel):
    """A group of identical registers with different indices (from 'count' expansion).

    This represents the original register definition before expansion,
    allowing templates to generate a single base class/struct with array access.
    """

    name: str  # Base name (e.g., "DATA")
    description: Optional[str] = None
    base_address: int  # Starting address
    access: Access = Access.RW
    access_hw: Optional[Access] = None  # Separate hardware access type
    bitfields: list[BitField]

    # regtool specific fields (See https://opentitan.org/book/util/reggen/index.html)
    hwqe: bool = False  # If hardware uses ‘q’ enable signal, which is latched signal of software write pulse
    hwext: bool = False  # If the register is stored outside of the register module

    count: int = Field(gt=0)

    # multireg-specific optional fields (passed through to hjson)
    cname: Optional[str] = None
    compact: Optional[bool] = None
    regwen_multi: bool = False


class LogicalInstance(BaseModel):
    """One logical multireg instance mapped to regtool physical layout."""

    index: int
    address: int
    bitfields: list[BitField]


class LogicalGroup(BaseModel):
    """Logical multireg group for indexed software access."""

    name: str
    description: Optional[str] = None
    access: Access = Access.RW
    count: int = Field(gt=0)
    template_bitfields: list[BitField]
    instances: list[LogicalInstance]
    # True when multiple logical instances share one physical register (compact packing)
    packed: bool = False
    # True when each instance maps to its own physical register with identical layout
    spread: bool = False


class HjsonEntry(BaseModel):
    """An ordered entry in the hjson register list."""

    kind: Literal["register", "multireg"]
    reg: Optional[Register] = None
    group: Optional[RegisterGroup] = None


class RegistersConfig(BaseConfig):
    """Top-level register map configuration."""

    width: int = 32
    regmap_shallow: list[Register]
    register_groups: list[RegisterGroup] = []  # Groups of numbered registers
    hjson_entries: list[HjsonEntry] = []
    logical_groups: list[LogicalGroup] = []
    access_separate: bool = False  # Separate hardware access methods

    @model_validator(mode="after")
    def check_access_separate(self) -> "RegistersConfig":
        if self.access_separate:
            for entry in self.hjson_entries:
                if entry.kind == "register" and entry.reg is not None:
                    reg = entry.reg
                elif entry.kind == "multireg" and entry.group is not None:
                    reg = entry.group
                else:
                    continue
                if reg.access_hw is None:
                    raise ValueError(
                        f"Register {reg.name} missing access_hw with access_separate=True"
                    )
        return self
