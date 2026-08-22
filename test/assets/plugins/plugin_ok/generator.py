from pathlib import Path

from embgen.plugin import GeneratedFile, Generator

from .schema import PluginOkSchema


class PluginOkGenerator(Generator[PluginOkSchema]):
    def generate(self, input: PluginOkSchema) -> list[GeneratedFile]:
        content = "Hmm, how should I greet you? How about:\n\n"
        for greeting in input.greetings:
            content += f"{greeting.capitalize()}, {input.name}!\n"

        return [GeneratedFile(path=Path("output.txt"), content=content)]
