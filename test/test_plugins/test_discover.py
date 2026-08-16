from embgen.plugins.discover import discover_plugins

from ..common import PLUGINS_DIR


def test_discover_ok_plugin():
    plugins = discover_plugins(PLUGINS_DIR)
    assert len(plugins) >= 1

    assert PLUGINS_DIR / "plugin_ok" in plugins

    plugin = plugins[PLUGINS_DIR / "plugin_ok"]
    assert plugin.id == "plugin_ok"
    assert plugin.version == "1.0.0"
    assert plugin.description == "A demo plugin that is correctly configured"
    assert plugin.contact.author == "Cedric Hirschi"
    assert plugin.contact.email == "cedr02@live.com"
    assert plugin.contact.repository == "https://github.com/CedricHirschi/embgen"
    assert plugin.generator_class is not None
    assert plugin.schema_class is not None


def test_discover_no_manifest_plugin():
    plugins = discover_plugins(PLUGINS_DIR)

    assert PLUGINS_DIR / "plugin_no_manifest" not in plugins


def test_discover_no_generator_plugin():
    plugins = discover_plugins(PLUGINS_DIR)

    assert PLUGINS_DIR / "plugin_no_generator" not in plugins


def test_discover_no_schema_plugin():
    plugins = discover_plugins(PLUGINS_DIR)

    assert PLUGINS_DIR / "plugin_no_schema" not in plugins


def test_discover_invalid_manifest_plugin():
    plugins = discover_plugins(PLUGINS_DIR)

    assert PLUGINS_DIR / "plugin_invalid_manifest" not in plugins
