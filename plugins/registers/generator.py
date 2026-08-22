from pathlib import Path

from embgen.plugin import GeneratedFile, Generator

from .schema import RegmapSchema


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

    def generate(self, input: RegmapSchema) -> list[GeneratedFile]:
        result = []

        for ext in input.extensions:
            match ext:
                case ".md":
                    content = self._generate_md(input)
                    result.append(
                        GeneratedFile(path=Path("regmap.md"), content=content)
                    )
        return result
