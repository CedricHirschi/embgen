from enum import StrEnum
from typing import Optional, Union

from pydantic import BaseModel, Field, model_validator, computed_field

from ...models import BaseConfig


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


class Enum(BaseModel):
    name: str
    description: Optional[str] = None
    value: int


class Argument(BaseModel):
    name: str
    name_method: Optional[str] = None
    description: str
    type: Optional[ArgumentType] = None
    enums: Optional[list[Enum]] = None
    default: Optional[Union[list[int], int, bool, Enum, str]] = None

    @model_validator(mode="after")
    def validate_default(self) -> "Argument":
        if self.enums is not None:
            if isinstance(self.default, str):
                for enum in self.enums:
                    if enum.name == self.default:
                        self.default = enum
                        break
        return self

    @computed_field
    @property
    def type_python(self) -> Optional[str]:
        if self.enums is not None:
            assert self.name_method is not None, (
                "name_method must be populated for arguments with enums"
            )
            return f"{self.name_method.capitalize()}{self.name.capitalize()}"

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

        if self.type is not None:
            return type_map[self.type]

        return "Any"


class Method(BaseModel):
    name: str
    description: Optional[str] = None
    args: list[Argument] = Field(default_factory=list)
    returns: Optional[list[Argument]] = Field(default_factory=list)

    # Populate name_method for each argument
    @model_validator(mode="after")
    def populate_name_method(self) -> "Method":
        for arg in self.args:
            arg.name_method = self.name
        return self


class JSONRPCConfig(BaseConfig):
    prefix: str = ""
    methods: list[Method]
