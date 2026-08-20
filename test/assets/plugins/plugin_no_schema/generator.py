from pathlib import Path

from embgen.plugin import GeneratedFile, Generator


class PluginNoSchemaGenerator(Generator):
    def generate(self, input: None) -> list[GeneratedFile]:  # type: ignore
        return [GeneratedFile(path=Path("output.txt"), content="Hello, world!")]
