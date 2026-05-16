import re
from enum import StrEnum
from typing import Optional, Union

from pydantic import BaseModel, Field, model_validator, computed_field

from ...models import BaseConfig


def _class_name(value: str) -> str:
    return "".join(
        part[:1].upper() + part[1:]
        for part in re.split(r"[^0-9A-Za-z]+", value)
        if part
    )


def _snake_name(value: str) -> str:
    return re.sub(r"[^0-9A-Za-z]+", "_", value).strip("_").lower()


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
    enum_name: Optional[str] = None
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
    def enum_python_name(self) -> Optional[str]:
        if self.enums is not None:
            assert self.name_method is not None, (
                "name_method must be populated for arguments with enums"
            )
            if self.enum_name is not None:
                return _class_name(self.enum_name)
            return f"{_class_name(self.name_method)}{_class_name(self.name)}"

        return None

    @computed_field
    @property
    def type_python(self) -> Optional[str]:
        if self.enums is not None:
            return self.enum_python_name

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

    @computed_field
    @property
    def enum_proto_name(self) -> Optional[str]:
        if self.enums is not None:
            assert self.name_method is not None, (
                "name_method must be populated for arguments with enums"
            )
            if self.enum_name is not None:
                return _class_name(self.enum_name)
            return f"{_snake_name(self.name_method)}_{_snake_name(self.name)}"

        return None

    @computed_field
    @property
    def type_proto(self) -> str:
        if self.enums is not None:
            assert self.enum_proto_name is not None
            return self.enum_proto_name

        type_map = {
            ArgumentType.UINT8: "uint32",
            ArgumentType.UINT16: "uint32",
            ArgumentType.UINT32: "uint32",
            ArgumentType.UINT64: "uint64",
            ArgumentType.INT8: "int32",
            ArgumentType.INT16: "int32",
            ArgumentType.INT32: "int32",
            ArgumentType.INT64: "int64",
            ArgumentType.FLOAT16: "float",
            ArgumentType.FLOAT32: "float",
            ArgumentType.FLOAT64: "double",
            ArgumentType.BOOL: "bool",
            ArgumentType.BYTES: "bytes",
        }

        assert self.type is not None, (
            "type must be populated for arguments without enums"
        )
        return type_map[self.type]

    @computed_field
    @property
    def name_python(self) -> str:
        return _snake_name(self.name)

    @computed_field
    @property
    def default_python(self) -> Optional[str]:
        if self.default is None:
            return None

        if self.enums is not None:
            assert isinstance(self.default, Enum), (
                "enum defaults must be resolved to Enum model values"
            )
            assert self.enum_python_name is not None
            return f"{self.enum_python_name}.{self.default.name}"

        if self.type == ArgumentType.BYTES:
            if isinstance(self.default, str):
                return repr(self.default.encode())
            if isinstance(self.default, list):
                return f"bytes({self.default!r})"

        return repr(self.default)

    @computed_field
    @property
    def default_doc(self) -> Optional[str]:
        if self.default is None:
            return None

        if isinstance(self.default, Enum):
            return self.default.name

        return str(self.default)


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
        for ret in self.returns or []:
            ret.name_method = self.name
        return self

    @computed_field
    @property
    def name_python(self) -> str:
        return _snake_name(self.name)


class NanoPBConfig(BaseConfig):
    prefix: str = ""
    methods: list[Method]
    max_count: Optional[int] = None
