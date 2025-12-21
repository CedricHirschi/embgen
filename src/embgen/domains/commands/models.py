from enum import StrEnum
from typing import Any, Optional, Union

from pydantic import BaseModel, Field, field_validator, ValidationInfo, computed_field


class ArgumentType(StrEnum):
    UINT8 = "B"
    UINT16 = "H"
    UINT32 = "I"
    UINT64 = "Q"
    INT8 = "b"
    INT16 = "h"
    INT32 = "i"
    INT64 = "q"
    FLOAT16 = "e"
    FLOAT32 = "f"
    FLOAT64 = "d"
    BOOL = "?"
    BYTES = "s"


class Endianness(StrEnum):
    BIG = ">"
    LITTLE = "<"


class Enum(BaseModel):
    name: str
    description: Optional[str] = None
    value: int


class Argument(BaseModel):
    name: str
    description: str
    type: ArgumentType
    enums: Optional[list[Enum]] = None
    default: Optional[Union[list[int], int, bool, Enum]] = None

    # Convert default to Enum if enums are defined
    @field_validator("default", mode="before")
    @classmethod
    def validate_default_enum(cls, v: Any, values: ValidationInfo) -> Any:
        enums = values.data.get("enums")
        if enums is not None and isinstance(v, str):
            for enum in enums:
                if enum.name == v:
                    return enum
        return v

    @computed_field
    def type_python(self) -> str:
        """Get the Python type corresponding to the argument type."""
        type_map = {
            ArgumentType.UINT8: "int",
            ArgumentType.UINT16: "int",
            ArgumentType.UINT32: "int",
            ArgumentType.UINT64: "int",
            ArgumentType.INT8: "int",
            ArgumentType.INT16: "int",
            ArgumentType.INT32: "int",
            ArgumentType.INT64: "int",
            ArgumentType.FLOAT16: "float",
            ArgumentType.FLOAT32: "float",
            ArgumentType.FLOAT64: "float",
            ArgumentType.BOOL: "bool",
            ArgumentType.BYTES: "bytes",
        }
        return type_map[self.type]


class Command(BaseModel):
    name: str
    id: int
    description: Optional[str] = None
    args: list[Argument] = Field(default_factory=list)
    returns: Optional[list[Argument]] = Field(default_factory=list)


class CommandsConfig(BaseModel):
    name: str
    file: Optional[str] = None
    endianness: Endianness = Endianness.LITTLE
    commands: list[Command]

    @property
    def output_filename(self) -> str:
        return self.file or self.name.lower()
