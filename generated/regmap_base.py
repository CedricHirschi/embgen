from enum import Enum
from typing import Optional


class Access(str, Enum):
    RO = "r"
    RW = "rw"
    WO = "w"


Value = int | bool | Enum


class RegisterMapInterface:
    memory: dict[int, dict[int, int]] = {}

    def read(self, address: int, offset: int, width: int, reset: Value) -> int:
        raise NotImplementedError(
            "RegisterMapInterface.read must be implemented in subclass"
        )

    def write(self, address: int, offset: int, width: int, value: Value) -> None:
        raise NotImplementedError(
            "RegisterMapInterface.write must be implemented in subclass"
        )


class RegisterMap:
    access: Access = Access.RW
    access_hw: Optional[Access] = None


class Register:
    address: int

    access: Access = Access.RW
    access_hw: Optional[Access] = None


class BitField:
    _register_address: int
    _offset: int
    _width: int = 1

    _enum: Optional[type[Enum]] = None

    _reset: Value = 0

    _access: Access = Access.RW
    _access_hw: Optional[Access] = None

    def __init__(self, intf: RegisterMapInterface):
        self._intf = intf

    @property
    def value(self) -> Value:
        if self._access not in (Access.WO, Access.RW):
            raise ValueError(
                f"Cannot read value of BitField with access type {self._access}"
            )

        raise NotImplementedError(
            "BitField.value getter must be implemented in subclass"
        )

    @value.setter
    def value(self, val: Value) -> None:
        if self._access not in (Access.RO, Access.RW):
            raise ValueError(
                f"Cannot write value of BitField with access type {self._access}"
            )

        raise NotImplementedError(
            "BitField.value setter must be implemented in subclass"
        )
