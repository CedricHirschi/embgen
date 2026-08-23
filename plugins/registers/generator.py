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
        return result
