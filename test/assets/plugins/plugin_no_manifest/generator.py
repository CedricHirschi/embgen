from embgen.plugin import Generator


class PluginNoManifestGenerator(Generator):
    def generate(self, input: str) -> str:
        return "Hello, world!"
