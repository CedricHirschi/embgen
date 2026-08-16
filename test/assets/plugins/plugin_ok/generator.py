from embgen.generator import Generator


class PluginOkGenerator(Generator):
    def generate(self, input: str) -> str:
        return "Hello, world!"
