from regmap import (  # type: ignore
    ExampleRegisters,
    ExampleRegistersEnums,
    RegisterMapInterface,
)


class MemoryInterface(RegisterMapInterface):
    def __init__(self):
        self.memory: dict[int, dict[int, int]] = {}

    def read(self, address: int, offset: int, width: int, reset: int) -> int:
        if address not in self.memory:
            print(f"> init  {address=}")
            self.memory[address] = {}
        if offset not in self.memory[address]:
            print(f"> init  {address=}, {offset=}")
            self.memory[address][offset] = reset
        print(f"> read  {address=}, {offset=}, {width=}, {reset=}")
        return self.memory[address][offset]

    def write(self, address: int, offset: int, width: int, value: int) -> None:
        if address not in self.memory:
            print(f"> init  {address=}")
            self.memory[address] = {}

        # Validate value against width
        max_value = (1 << width) - 1
        if value < 0:
            raise ValueError(f"Value {value} cannot be negative")
        if value > max_value:
            raise ValueError(
                f"Value {value} exceeds maximum {max_value} for width {width}"
            )

        self.memory[address][offset] = value
        print(f"> write {address=}, {offset=}, {width=}, {value=}")


enums = ExampleRegistersEnums()
intf = MemoryInterface()
regmap = ExampleRegisters(intf=intf)

print("\nSetting values...")
regmap.control.enable = True
print(f"Read back enable: {regmap.control.enable}")

print("\nSetting enum mode...")
regmap.control.mode = ExampleRegistersEnums.ControlMode.SHUTDOWN
print(f"Read back mode: {regmap.control.mode}")

print("\nReading read-only status...")
print(f"Read back ready: {regmap.status.ready}")

print("\nTesting read-only protection on status.ready...")
try:
    regmap.status.ready = True
except ValueError as e:
    print(f"Caught expected error on read-only write: {e}")
