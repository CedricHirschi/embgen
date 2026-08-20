from pathlib import Path

from embgen.plugin import GeneratedFile, Generator

from .schema import PluginNoManifestSchema


class PluginNoManifestGenerator(Generator[PluginNoManifestSchema]):
    def generate(self, input: PluginNoManifestSchema) -> list[GeneratedFile]:
        return [GeneratedFile(path=Path("output.txt"), content="Hello, world!")]
