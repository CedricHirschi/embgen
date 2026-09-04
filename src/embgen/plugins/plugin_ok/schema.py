from embgen.plugin import Schema


class PluginOkSchema(Schema):
    name: str
    greetings: list[str]
