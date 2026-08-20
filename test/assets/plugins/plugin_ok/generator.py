from pathlib import Path

from embgen.plugin import GeneratedFile, Generator

from .schema import PluginOkSchema


class PluginOkGenerator(Generator[PluginOkSchema]):
    def generate(self, input: PluginOkSchema) -> list[GeneratedFile]:
        return [GeneratedFile(path=Path("output.txt"), content="Hello, world!")]
