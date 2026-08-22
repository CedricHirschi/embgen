from pathlib import Path
from typing import Sequence

from .load import Loader
from .plugin import GeneratedFile
from .plugins.discover import PluginDiscovery
from .plugins.models import Plugin


class Generator:
    def __init__(self, output_dir: Path, plugin_dirs: list[Path]) -> None:
        self.output_dir = output_dir
        self.plugin_dirs = plugin_dirs

        self.plugins: dict[str, Plugin] = {}
        for plugin_dir in self.plugin_dirs:
            plugins = PluginDiscovery(plugin_dir).discover_plugins()
            for plugin in plugins.values():
                if plugin.id in self.plugins:
                    raise ValueError(f"Duplicate plugin ID: {plugin.id}")

                self.plugins[plugin.id] = plugin

    def generate(
        self,
        plugin_id: str,
        config: Path | str | dict | Sequence[Path | str],
        format: str | None = None,
        all: bool = False,
        template: bool = False,
        context: dict | None = None,
        env: bool = True,
    ) -> list[GeneratedFile]:
        if plugin_id not in self.plugins:
            raise ValueError(f"Plugin ID not found: {plugin_id}")

        loader = Loader(self.plugins[plugin_id].schema_class)

        if isinstance(config, Path) or (
            isinstance(config, str) and Path(config).exists()
        ):
            if all:
                config_data = loader.load_all(
                    config, template=template, context=context, env=env
                )
            else:
                config_data = loader.load(
                    config, template=template, context=context, env=env
                )
        elif isinstance(config, str):
            if format is None:
                raise ValueError("Format must be specified when loading from a string")
            if all:
                config_data = loader.load_all_string(
                    config, template=template, context=context, env=env
                )
            else:
                config_data = loader.load_string(
                    config, format=format, template=template, context=context, env=env
                )
        elif isinstance(config, dict):
            config_data = loader.load_dict(config)
        elif isinstance(config, Sequence):
            if all:
                raise ValueError("Cannot use 'all' with a multi-file config")
            config_data = loader.load_multi(
                config, template=template, context=context, env=env
            )
        else:
            raise ValueError(
                f"Invalid config type: {type(config).__name__}. Must be Path, str, dict, or Sequence."
            )

        generator = self.plugins[plugin_id].generator_class()

        files: list[GeneratedFile] = []
        if isinstance(config_data, list):
            for item in config_data:
                files.extend(generator.generate(item))
        else:
            files = generator.generate(config_data)

        return files

    def write(self, files: list[GeneratedFile]) -> None:
        for file in files:
            output_path = self.output_dir / file.path
            output_path.parent.mkdir(parents=True, exist_ok=True)

            if isinstance(file.content, bytes):
                output_path.write_bytes(file.content)
            else:
                output_path.write_text(file.content, encoding="utf-8")

    def run(
        self,
        plugin_id: str,
        config: Path | str | dict | Sequence[Path | str],
        format: str | None = None,
        all: bool = False,
        template: bool = False,
        context: dict | None = None,
        env: bool = True,
    ) -> list[GeneratedFile]:
        files = self.generate(
            plugin_id=plugin_id,
            config=config,
            format=format,
            all=all,
            template=template,
            context=context,
            env=env,
        )
        self.write(files)
        return files
