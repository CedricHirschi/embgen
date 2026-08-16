from embgen.plugin import Generator


class PluginNoSchemaGenerator(Generator):
    def generate(self, input: str) -> str:
        return "Hello, world!"
