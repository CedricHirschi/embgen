from enum import Enum as BaseEnum
from typing import Literal, Optional

from pydantic import model_validator

from embgen.common import StrictModel
from embgen.plugin import Schema

RegmapExtension = Literal[".md", ".rdl", ".py"]


class Access(BaseEnum):
    """Register access type."""

    RO = "r"
    RW = "rw"
    WO = "w"

    def __str__(self) -> str:
        return self.name

    def __repr__(self) -> str:
        return "Access." + str(self)


class Enum(StrictModel):
    """Enumeration value used in both commands and registers."""

    name: str
    description: str | None = None
    value: int


class BitField(StrictModel):
    name: str
    description: Optional[str] = None
    reset: int | bool | Enum | str
    width: int = 1
    offset: Optional[int] = None
    enums: Optional[list[Enum]] = None
    access: Access = Access.RW
    access_hw: Optional[Access] = None

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
        elif isinstance(self.reset, str):
            raise ValueError(
                f"BitField {self.name} has a string reset but no enums defined. Either define enums on the bitfield or use an int/bool reset."
            )
        return self


class Register(StrictModel):
    name: str
    description: Optional[str] = None
    address: Optional[int] = None
    bitfields: list[BitField]
    access: Access = Access.RW
    access_hw: Optional[Access] = None

    # regtool specific fields (See https://opentitan.org/book/util/reggen/index.html)
    hwqe: bool = False  # If hardware uses 'q' enable signal, which is latched signal of software write pulse
    hwext: bool = False  # If the register is stored outside of the register module


class RegmapSchema(Schema):
    name: str
    description: Optional[str] = None
    width: int = 32
    access_separate: bool = False
    access: Access = Access.RW
    access_hw: Optional[Access] = None

    registers: list[Register]

    extensions: list[RegmapExtension]
    base_file: str = "..regmap_base"
