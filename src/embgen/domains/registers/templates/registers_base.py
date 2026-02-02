from enum import Enum as BaseEnum
from logging import Logger
from typing import Optional, Any, Protocol


class RegisterMapInterface(Protocol):
    """Interface for register map hardware access.

    Implement this protocol to provide custom hardware access behavior.
    The default implementation `Interface` provides an in-memory simulation.
    """

    def read(self, register_address: int, offset: int, reset_value: int) -> int:
        """Read a bitfield value from a register.

        Args:
            register_address: The address of the register.
            offset: The bit offset within the register.
            reset_value: The reset value to use if not previously written.

        Returns:
            The value read from the register at the given offset.
        """
        ...

    def write(self, register_address: int, offset: int, value: int) -> None:
        """Write a bitfield value to a register.

        Args:
            register_address: The address of the register.
            offset: The bit offset within the register.
            value: The value to write.
        """
        ...


class Interface(RegisterMapInterface):
    """Default hardware interface implementation (in-memory simulation)."""

    def __init__(self, log: Logger):
        self.memory: dict[int, dict[int, int]] = {}
        self.log: Logger = log

    def read(self, register_address: int, offset: int, reset_value: int) -> int:
        if register_address not in self.memory:
            self.log.debug(f"init  {register_address=}")
            self.memory[register_address] = {}
        if offset not in self.memory[register_address]:
            self.log.debug(f"init  {register_address=}, {offset=}")
            self.memory[register_address][offset] = reset_value
        self.log.debug(f"read  {register_address=}, {offset=}, {reset_value=}")
        return self.memory[register_address][offset]

    def write(self, register_address: int, offset: int, value: int) -> None:
        if register_address not in self.memory:
            self.log.debug(f"init  {register_address=}")
            self.memory[register_address] = {}
        self.memory[register_address][offset] = value
        self.log.debug(f"write {register_address=}, {offset=}, {value=}")

    def pull(self) -> dict[int, int]:
        result = {a: sum(v << o for o, v in r.items()) for a, r in self.memory.items()}
        return dict(sorted(result.items()))

    def push(self, memory: dict[int, dict[int, int]]) -> None:
        self.memory = memory

    def reset(self) -> None:
        self.memory = {}


class Access(BaseEnum):
    """Register access types."""

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


class BitField:
    """Base class for register bitfields."""

    _name: str = "BitField"
    _description: Optional[str] = None
    _reset: int = 0
    _value: int = _reset
    _width: int = -1
    _offset: int = -1
    _enums: Any = None
    _register_address: int = -1
    _interface: Optional[RegisterMapInterface] = None
    _access: Access = Access.RW

    def __init__(self) -> None:
        if hasattr(self, "_reset"):
            self._value = self._reset

    def __str__(self) -> str:
        return str(self.value)

    def __repr__(self) -> str:
        return f"{self._name}(value={self.value}, reset={self._reset}, width={self._width}, offset={self._offset}, access={self._access})"

    def _set_interface(
        self, register_address: int, interface: RegisterMapInterface, access: Access
    ) -> None:
        self._register_address = register_address
        self._interface = interface
        self._access = access

    @property
    def value(self) -> int | BaseEnum:
        if not self._interface:
            raise RuntimeError(f"Interface not set for bitfield {self._name}")

        if self._access not in [Access.RO, Access.RW, Access.ROLH]:
            raise RuntimeError(
                f"BitField {self._name} is not readable (access={self._access})"
            )

        raw_value = self._interface.read(
            self._register_address, self._offset, self._reset
        )
        if self._enums is not None:
            return self._enums(raw_value)
        return raw_value

    @value.setter
    def value(self, value: int | BaseEnum) -> None:
        if not self._interface:
            raise RuntimeError(f"Interface not set for bitfield {self._name}")

        if self._access not in [
            Access.WO,
            Access.RW,
            Access.RWC,
            Access.WOS,
            Access.ROLH,
        ]:
            raise RuntimeError(
                f"BitField {self._name} is not writable (access={self._access})"
            )

        if self._enums is not None:
            if not isinstance(value, BaseEnum):
                raise TypeError(
                    f"{value=} of BitField {self._name} must be of type {type(BaseEnum).__name__}, not {type(value).__name__}"
                )
            int_value = value.value
        else:
            if not isinstance(value, int):
                raise TypeError(
                    f"{value=} of BitField {self._name} must be an int when no enums are defined"
                )
            if value >= 2**self._width:
                raise ValueError(
                    f"{value=} exceeds width={self._width} of BitField {self._name} (max_value={2**self._width - 1})"
                )
            elif value < 0:
                raise ValueError(
                    f"{value=} of BitField {self._name} cannot be negative"
                )
            int_value = value

        self._interface.write(self._register_address, self._offset, int(int_value))

    @property
    def raw(self) -> int:
        """Read the raw bitfield value."""
        return (
            (self.value if isinstance(self.value, int) else self.value.value)
            & ((1 << self._width) - 1)
        ) << self._offset


class Register:
    """Base class for hardware registers."""

    _description: Optional[str] = None
    _address: int = -1
    _access: Access = Access.RW

    def __init__(self, interface: RegisterMapInterface) -> None:
        self._interface: RegisterMapInterface = interface

        for attr in self.__class__.__dict__.values():
            if isinstance(attr, BitField):
                attr._set_interface(self._address, interface, self._access)

    def __str__(self) -> str:
        return f"Register(address={self._address}, description={self._description})"

    def __repr__(self) -> str:
        return str(self)

    @property
    def raw(self) -> int:
        """Read the raw register value."""
        if not self._interface:
            raise RuntimeError(
                f"Interface not set for register at address {self._address}"
            )

        result = 0
        for _, attr_value in self.__class__.__dict__.items():
            if isinstance(attr_value, BitField):
                result |= attr_value.raw

        return result


class RegisterMap:
    """Base class for register maps."""

    def __str__(self) -> str:
        registers = self.__class__.__dict__["__annotations__"].keys()
        return f"{self.__class__.__name__}(registers=[{', '.join(registers)}])"

    def __repr__(self) -> str:
        return str(self)
