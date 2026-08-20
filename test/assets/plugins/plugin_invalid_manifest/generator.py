from pathlib import Path

from embgen.plugin import GeneratedFile, Generator

from .schema import PluginInvalidManifestSchema


class PluginInvalidManifestGenerator(Generator[PluginInvalidManifestSchema]):
    def generate(self, input: PluginInvalidManifestSchema) -> list[GeneratedFile]:
        return [GeneratedFile(path=Path("output.txt"), content="Hello, world!")]
