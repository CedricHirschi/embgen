from regmap import (
    ExampleRegisters,
    ExampleRegistersEnums,
    RegisterMapInterface,
)

enums = ExampleRegistersEnums()
intf = RegisterMapInterface()
regmap = ExampleRegisters(intf=intf)
