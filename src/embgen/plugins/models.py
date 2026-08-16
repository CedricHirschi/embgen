from ..common import StrictModel


class PluginContact(StrictModel):
    author: str
    email: str
    repository: str | None = None


class Plugin(StrictModel):
    id: str
    version: str
    description: str
    contact: PluginContact
