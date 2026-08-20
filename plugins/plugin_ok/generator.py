from embgen.plugin import Generator

from .schema import PluginOkSchema


class PluginOkGenerator(Generator[PluginOkSchema]):
    def generate(self, input: PluginOkSchema) -> str:
        return "Hello, world!"
