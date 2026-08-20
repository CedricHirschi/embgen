from pathlib import Path
from pprint import pformat

from embgen.common import setup_logging
from embgen.plugins.discover import PluginDiscovery

PLUGINS_DIR = Path(__file__).parents[2] / "test" / "assets" / "plugins"


log = setup_logging("DEBUG")


discovery = PluginDiscovery(PLUGINS_DIR)

plugins = discovery.discover_plugins()

for plugin_dir, plugin in plugins.items():
    log.info(plugin_dir)
    log.info(pformat(plugin.model_dump(), sort_dicts=False))
    log.info(f"Is valid: {discovery.is_valid_plugin_dir(plugin_dir)}")
