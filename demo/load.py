from pathlib import Path

from embgen.common import setup_logging
from embgen.load import Loader
from embgen.plugin import Schema

PLUGINS_DIR = Path(__file__).parents[1] / "test" / "assets" / "plugins"


class DemoSchema(Schema):
    name: str
    greetings: list[str]


log = setup_logging("DEBUG")


loader = Loader[DemoSchema](DemoSchema)

schema = loader.load(PLUGINS_DIR / "plugin_ok" / "schema.yml")
log.info(f"Loaded schema: {schema}")
