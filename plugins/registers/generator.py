from enum import Enum
from pathlib import Path

from embgen.plugin import GeneratedFile, Generator

from .schema import Access, RegmapSchema


class RegmapGenerator(Generator[RegmapSchema]):
    def _generate_md(self, input: RegmapSchema) -> str:
        c = f"# Register Map: {input.name}\n\n"

        if input.description:
            c += f"{input.description}\n\n"

        for register in input.registers:
            c += f"## Register: {register.name}\n\n"
            if register.description:
                c += f"{register.description}\n\n"
            c += f"- Address: 0x{register.address:X}\n"
            c += "- Bitfields:\n"
            for bitfield in register.bitfields:
                c += f"  - {bitfield.name} (offset: {bitfield.offset}, width: {bitfield.width}, reset: 0x{bitfield.reset:X})\n"
                if bitfield.description:
                    c += f"    - Description: {bitfield.description}\n"
            c += "\n"

        return c

    def _generate_rdl(self, input: RegmapSchema) -> str:
        c = ""

        c += f"addrmap {input.name} {{\n"
        c += f'    name = "{input.name}";\n'
        if input.description:
            c += f'    desc = "{input.description}";\n'
        c += "\n"

        c += f"    default regwidth = {input.width};\n"
        c += "    default sw = rw;\n"
        c += "    default hw = rw;\n\n"

        current_register_address = 0

        for register in input.registers:
            c += "    reg {\n"
            if register.description:
                c += f'        desc = "{register.description}";\n'
            c += "\n"

            added_defaults = False
            if register.access is not None and register.access != Access.RW:
                c += f"        default sw = {register.access.value};\n"
                added_defaults = True
            if register.access_hw is not None and register.access_hw != Access.RW:
                c += f"        default hw = {register.access_hw.value};\n"
                added_defaults = True
            if added_defaults:
                c += "\n"

            current_bitfield_offset = 0

            for bitfield in register.bitfields:
                c += "        field {\n"
                if bitfield.description:
                    c += f'            desc = "{bitfield.description}";\n'

                enum_name = None

                if bitfield.enums is not None:
                    enum_name = f"{register.name.lower()}_{bitfield.name.lower()}_e"
                    c += f"\n            enum {enum_name} {{\n"
                    for enum in bitfield.enums:
                        if enum.description is None:
                            c += f"                {enum.name} = {bitfield.width}'d{enum.value};\n"
                        else:
                            c += f"                {enum.name} = {bitfield.width}'d{enum.value} {{ "
                            c += f'desc = "{enum.description}";'
                            c += " };\n"
                    c += "            };\n\n"

                if bitfield.reset is not None:
                    if isinstance(bitfield.reset, int):
                        if bitfield.enums is None:
                            c += f"            reset = {bitfield.width}'d{bitfield.reset:d};\n"
                        else:
                            reset_name = None
                            for enum in bitfield.enums:
                                if enum.value == bitfield.reset:
                                    reset_name = enum.name
                                    break
                            if reset_name is not None:
                                c += f"            reset = {enum_name}::{reset_name};\n"
                            else:
                                c += f"            reset = {bitfield.width}'d{bitfield.reset:d};\n"
                    elif isinstance(bitfield.reset, Enum):
                        c += f"            reset = {bitfield.reset.name};\n"
                    elif isinstance(bitfield.reset, bool):
                        c += f"            reset = {bitfield.width}'d{'1' if bitfield.reset else '0'};\n"

                if bitfield.enums is not None:
                    c += f"            encode = {register.name.lower()}_{bitfield.name.lower()}_e;\n"

                offset = (
                    bitfield.offset
                    if bitfield.offset is not None
                    else current_bitfield_offset
                )
                msb = offset + bitfield.width - 1
                lsb = offset

                c += f"        }} {bitfield.name} [{msb}:{lsb}];\n\n"

            if register.address is not None:
                c += f"    }} {register.name} @ 0x{register.address:X};\n\n"
                current_register_address = register.address + (input.width // 8)
            else:
                c += f"    }} {register.name} @ 0x{current_register_address:X};\n\n"
                current_register_address += input.width // 8

        c += "};\n\n"

        return c

    def _generate_py(self, input: RegmapSchema) -> str:
        c = ""

        c += f"# Generated Register Map: {input.name}\n"
        if input.description:
            c += f"# Description: {input.description}\n"
        c += "# This file is auto-generated. Do not edit manually.\n\n"

        c += "from enum import Enum\n\n"

        c += f"from {input.base_file} import (\n"
        c += "    Access,\n    BitField,\n    Register,\n    RegisterMap,\n    RegisterMapInterface,\n    Value,\n"
        c += ")\n\n\n"

        enums_class_name = input.name.title().replace("_", "") + "Enums"
        if any(bf.enums is not None for reg in input.registers for bf in reg.bitfields):
            c += f"class {enums_class_name}:\n"
            c += '    """Enumeration classes for registers and bitfields"""\n\n'
            for register in input.registers:
                for bitfield in register.bitfields:
                    if bitfield.enums is not None:
                        enum_name = f"{register.name.title().replace('_', '')}{bitfield.name.title().replace('_', '')}"
                        c += f"    class {enum_name}(Enum):\n"
                        c += f'        """Enumeration for {register.name}.{bitfield.name}"""\n\n'
                        for enum in bitfield.enums:
                            if enum.description is None:
                                c += f"        {enum.name} = {enum.value}\n"
                            else:
                                c += f"        {enum.name} = {enum.value}  # {enum.description}\n"
                        c += "\n"
            c += "\n"

        c += f"class {input.name.title().replace('_', '')}(RegisterMap):\n"

        if input.description:
            c += f'    """{input.description}"""\n\n'

        added_defaults = False
        if input.access is not None and input.access != Access.RW:
            c += f"    sw = Access.{input.access.name}\n"
            added_defaults = True
        if input.access_hw is not None and input.access_hw != Access.RW:
            c += f"    hw = Access.{input.access_hw.name}\n"
            added_defaults = True
        if added_defaults:
            c += "\n"

        current_register_address = 0

        for register in input.registers:
            c += f"    class {register.name.title().replace('_', '')}(Register):\n"
            if register.description:
                c += f"        # {register.description}\n"

            if register.address is not None:
                c += f"        _address = 0x{register.address:X}\n\n"
                current_register_address = register.address + (input.width // 8)
            else:
                c += f"        _address = 0x{current_register_address:X}\n\n"
                current_register_address += input.width // 8

            added_defaults = False
            if register.access is not None and register.access != Access.RW:
                c += f"        _access = Access.{register.access.name}\n"
                added_defaults = True
            if register.access_hw is not None and register.access_hw != Access.RW:
                c += f"        _access_hw = Access.{register.access_hw.name}\n"
                added_defaults = True
            if added_defaults:
                c += "\n"

            current_bitfield_offset = 0

            for bitfield in register.bitfields:
                enum_name = None
                if bitfield.enums is not None:
                    enum_name = f"{register.name.title().replace('_', '')}{bitfield.name.title().replace('_', '')}"

                c += f"        class {bitfield.name.title().replace('_', '')}(BitField):\n"
                if bitfield.description:
                    c += f"            # {bitfield.description}\n"

                offset = (
                    bitfield.offset
                    if bitfield.offset is not None
                    else current_bitfield_offset
                )

                c += f"            _register_address = 0x{register.address:X}\n"
                c += f"            _offset = {offset}\n"
                if bitfield.width != 1:
                    c += f"            _width = {bitfield.width}\n"

                bf_access = bitfield.access
                if (bf_access is None or bf_access == Access.RW) and (
                    register.access is not None and register.access != Access.RW
                ):
                    bf_access = register.access

                if bf_access is not None and bf_access != Access.RW:
                    c += "\n"
                    c += f"            _access = Access.{bf_access.name}\n"

                bf_access_hw = bitfield.access_hw
                if (bf_access_hw is None or bf_access_hw == Access.RW) and (
                    register.access_hw is not None and register.access_hw != Access.RW
                ):
                    bf_access_hw = register.access_hw

                if bf_access_hw is not None and bf_access_hw != Access.RW:
                    if not (bf_access is not None and bf_access != Access.RW):
                        c += "\n"
                    c += f"            _access_hw = Access.{bf_access_hw.name}\n"

                if bitfield.enums is not None:
                    c += "\n"
                    c += f"            _enum = {enums_class_name}.{register.name.title().replace('_', '')}{bitfield.name.title().replace('_', '')}\n"

                if bitfield.reset is not None:
                    c += "\n"
                    if isinstance(bitfield.reset, int):
                        if bitfield.enums is None:
                            if bitfield.reset != 0:
                                c += f"            _reset = {bitfield.reset:d}\n"
                                c += "\n"
                        else:
                            reset_name = None
                            for enum in bitfield.enums:
                                if enum.value == bitfield.reset:
                                    reset_name = enum.name
                                    break
                            if reset_name is not None:
                                c += f"            _reset = {enums_class_name}.{enum_name}.{reset_name}\n"
                                c += "\n"
                            elif bitfield.reset != 0:
                                c += f"            _reset = {bitfield.reset:d}\n"
                                c += "\n"
                    elif isinstance(bitfield.reset, Enum):
                        c += f"            _reset = {enums_class_name}.{enum_name}.{bitfield.reset.name}\n"
                        c += "\n"
                    elif isinstance(bitfield.reset, bool):
                        c += f"            _reset = {'True' if bitfield.reset else 'False'}\n"
                        c += "\n"

            c += "        def __init__(self, intf: RegisterMapInterface):\n"
            for bitfield in register.bitfields:
                c += f"            self._{bitfield.name.lower()} = self.{bitfield.name.title().replace('_', '')}(intf)\n"

            for bitfield in register.bitfields:
                bf_name = bitfield.name.lower()
                c += "\n"
                c += "        @property\n"
                c += f"        def {bf_name}(self) -> Value:\n"
                c += f"            return self._{bf_name}.value\n\n"
                c += f"        @{bf_name}.setter\n"
                c += f"        def {bf_name}(self, val: Value) -> None:\n"
                c += f"            self._{bf_name}.value = val\n"
            c += "\n"

        c += "    def __init__(self, intf: RegisterMapInterface):\n"
        for register in input.registers:
            c += f"        self.{register.name.lower()} = self.{register.name.title().replace('_', '')}(intf)\n"

        c += "\n\n__all__ = [\n"
        c += f"    '{enums_class_name}',\n"
        c += f"    '{input.name.title().replace('_', '')}',\n"
        c += "    'RegisterMapInterface',\n"
        c += "]\n"

        return c

    def generate(self, input: RegmapSchema) -> list[GeneratedFile]:
        result = []

        for ext in input.extensions:
            match ext:
                case ".md":
                    content = self._generate_md(input)
                    result.append(
                        GeneratedFile(path=Path("regmap.md"), content=content)
                    )
                case ".rdl":
                    content = self._generate_rdl(input)
                    result.append(
                        GeneratedFile(path=Path("regmap.rdl"), content=content)
                    )
                case ".py":
                    content = self._generate_py(input)
                    result.append(
                        GeneratedFile(path=Path("regmap.py"), content=content)
                    )
        return result
