from embgen.plugin import Generator


class PluginOkGenerator(Generator):
    def generate(self, input: str) -> str:
        return "Hello, world!"
