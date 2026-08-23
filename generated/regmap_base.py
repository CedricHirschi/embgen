from enum import Enum
from typing import Optional


class Access(str, Enum):
    RO = "r"
    RW = "rw"
    WO = "w"


Value = int | bool | Enum


class RegisterMapInterface:
    def read(self, address: int, offset: int, width: int, reset: int) -> int:
        raise NotImplementedError(
            "RegisterMapInterface.read must be implemented in subclass"
        )

    def write(self, address: int, offset: int, width: int, value: int) -> None:
        raise NotImplementedError(
            "RegisterMapInterface.write must be implemented in subclass"
        )


class RegisterMap:
    _access: Access = Access.RW


class Register:
    _address: int

    _access: Access = Access.RW


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

    def _value_to_int(self, val: Value) -> int:
        if isinstance(val, bool):
            return int(val)
        elif isinstance(val, Enum):
            return val.value
        elif isinstance(val, int):
            return val
        else:
            raise ValueError(
                f"Invalid value type: {type(val)}. Expected int, bool, or Enum."
            )

    def _to_value(self, raw: int) -> Value:
        if self._enum is not None:
            try:
                return self._enum(raw)
            except ValueError:
                raise ValueError(
                    f"Raw value {raw} does not correspond to any enum in {self._enum}"
                )
        elif isinstance(self._reset, bool):
            return bool(raw)
        elif isinstance(self._reset, int):
            return raw
        else:
            raise ValueError(
                f"Invalid reset type: {type(self._reset)}. Expected int, bool, or Enum."
            )

    @property
    def value(self) -> Value:
        if self._access not in (Access.RO, Access.RW):
            raise ValueError(
                f"Cannot read value of BitField with access type {self._access}"
            )

        raw = self._intf.read(
            self._register_address,
            self._offset,
            self._width,
            self._value_to_int(self._reset),
        )
        return self._to_value(raw)

    @value.setter
    def value(self, val: Value) -> None:
        if self._access not in (Access.WO, Access.RW):
            raise ValueError(
                f"Cannot write value of BitField with access type {self._access}"
            )

        raw = self._value_to_int(val)
        self._intf.write(self._register_address, self._offset, self._width, raw)
