from embgen.plugin import Generator


class PluginInvalidManifestGenerator(Generator):
    def generate(self, input: str) -> str:
        return "Hello, world!"
