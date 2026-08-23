import hashlib
import logging
import sys
import types
from importlib.util import module_from_spec, spec_from_file_location
from pathlib import Path

import yaml
from pydantic import ValidationError

from ..common import log_validation_error
from ..plugin import Generator, Schema
from .models import Plugin

log = logging.getLogger(__name__)


class PluginDiscovery:
    def __init__(self, plugin_dirs: list[Path]):
        self.plugin_dirs = [
            plugin_dir.resolve().absolute() for plugin_dir in plugin_dirs
        ]

    @staticmethod
    def load_manifest(
        manifest_file: Path,
        generator_class: type[Generator],
        schema_class: type[Schema],
    ) -> Plugin:
        data = yaml.safe_load(manifest_file.read_text())

        return Plugin.model_validate(
            data,
            context={"generator_class": generator_class, "schema_class": schema_class},
        )

    @staticmethod
    def load_class_file(file: Path, base_class: type) -> type:
        dir_path = file.parent.resolve().absolute()
        dir_hash = hashlib.sha256(dir_path.as_posix().encode()).hexdigest()[:12]
        package_name = f"embgen._plugins.{file.parent.name}_{dir_hash}"
        module_name = f"{package_name}.{file.stem}"

        if package_name not in sys.modules:
            package_module = types.ModuleType(package_name)
            package_module.__path__ = [str(file.parent)]
            sys.modules[package_name] = package_module

        module = sys.modules.get(module_name)
        if module is None:
            spec = spec_from_file_location(module_name, file)
            if spec is None or spec.loader is None:
                raise ImportError(f"Could not load {file.as_posix()}")
            module = module_from_spec(spec)
            sys.modules[module_name] = module
            spec.loader.exec_module(module)

        classes = [
            cls
            for cls in module.__dict__.values()
            if isinstance(cls, type)
            and issubclass(cls, base_class)
            and cls is not base_class
        ]
        if len(classes) != 1:
            raise ValueError(
                f"Expected exactly one {base_class.__name__} subclass in {file.as_posix()}, found {len(classes)}"
            )

        return classes[0]

    @staticmethod
    def load_plugin(dir: Path) -> Plugin:
        manifest_file = dir / "embgen.yml"

        generator_class = PluginDiscovery.load_class_file(
            dir / "generator.py", Generator
        )
        schema_class = PluginDiscovery.load_class_file(dir / "schema.py", Schema)

        return PluginDiscovery.load_manifest(
            manifest_file,
            generator_class,  # type: ignore
            schema_class,  # type: ignore
        )

    @staticmethod
    def is_valid_plugin_manifest(
        manifest_file: Path,
        generator_class: type[Generator],
        schema_class: type[Schema],
    ) -> bool:
        try:
            data = yaml.safe_load(manifest_file.read_text())
            Plugin.model_validate(
                data,
                context={
                    "generator_class": generator_class,
                    "schema_class": schema_class,
                },
            )
        except ValidationError as e:
            log.debug(f"Invalid manifest in {manifest_file.as_posix()}:")
            log_validation_error(log, e, logging.DEBUG)
            return False

        return True

    @staticmethod
    def is_valid_plugin_generator(generator_file: Path) -> bool:
        try:
            PluginDiscovery.load_class_file(generator_file, Generator)
        except Exception as e:
            log.debug(f"Invalid generator in {generator_file.as_posix()}: {e}")
            return False

        return True

    @staticmethod
    def is_valid_plugin_schema(schema_file: Path) -> bool:
        try:
            PluginDiscovery.load_class_file(schema_file, Schema)
        except Exception as e:
            log.debug(f"Invalid schema in {schema_file.as_posix()}: {e}")
            return False

        return True

    @staticmethod
    def is_valid_plugin_dir(dir: Path) -> bool:
        manifest_file = dir / "embgen.yml"
        generator_file = dir / "generator.py"
        schema_file = dir / "schema.py"

        if not all(
            [manifest_file.exists(), generator_file.exists(), schema_file.exists()]
        ):
            log.debug(
                f"Invalid plugin directory {dir.as_posix()}: missing required files"
            )
            return False

        if not PluginDiscovery.is_valid_plugin_generator(generator_file):
            return False
        plugin_generator = PluginDiscovery.load_class_file(generator_file, Generator)

        if not PluginDiscovery.is_valid_plugin_schema(schema_file):
            return False
        plugin_schema = PluginDiscovery.load_class_file(schema_file, Schema)

        if not PluginDiscovery.is_valid_plugin_manifest(
            manifest_file,
            plugin_generator,  # type: ignore
            plugin_schema,  # type: ignore
        ):
            return False

        return True

    def discover_plugins(self) -> dict[Path, Plugin]:
        result = {}
        seen_ids: dict[str, Path] = {}

        for plugin_dir in self.plugin_dirs:
            log.debug(f"Discovering plugins in {plugin_dir.as_posix()}")

            if not plugin_dir.is_dir():
                raise NotADirectoryError(
                    f"{plugin_dir.as_posix()} is not a directory or does not exist"
                )

            for dir in plugin_dir.glob("*"):
                if not dir.is_dir():
                    continue

                try:
                    plugin = self.load_plugin(dir)
                except FileNotFoundError as e:
                    log.warning(f"Incomplete plugin {dir.as_posix()}: {e.filename}")
                    continue
                except ValidationError as e:
                    log.warning(f"Invalid embgen.yml in {dir.as_posix()}")
                    log_validation_error(log, e, logging.WARNING)
                    continue
                except Exception as e:
                    log.warning(f"Error loading plugin {dir.as_posix()}: {e}")
                    continue

                if plugin.id in seen_ids:
                    raise ValueError(
                        f"Duplicate plugin ID: '{plugin.id}' in {dir.as_posix()} "
                        f"(already discovered in {seen_ids[plugin.id].as_posix()})"
                    )
                seen_ids[plugin.id] = dir

                result[dir] = plugin
                log.debug(f"Discovered plugin '{plugin.id}' in {dir.as_posix()}")

        return result
