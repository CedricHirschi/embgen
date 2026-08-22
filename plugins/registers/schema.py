from typing import Literal, Optional

from embgen.common import StrictModel
from embgen.plugin import Schema

RegmapExtension = Literal[".md", ".h", ".py"]


class BitField(StrictModel):
    name: str
    description: Optional[str] = None
    reset: int
    width: int
    offset: int


class Register(StrictModel):
    name: str
    description: Optional[str] = None
    address: int
    bitfields: list[BitField]


class RegmapSchema(Schema):
    name: str
    description: Optional[str] = None

    extensions: list[RegmapExtension]
    registers: list[Register]
