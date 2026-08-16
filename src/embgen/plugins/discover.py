import logging
import sys
from importlib.util import module_from_spec, spec_from_file_location
from pathlib import Path

import yaml
from pydantic import ValidationError

from ..common import log_validation_error
from ..plugin import Generator, Schema
from .models import Plugin

log = logging.getLogger(__name__)


def _load_plugin_file_class(file: Path, base_class: type) -> type:
    if not file.exists():
        raise FileNotFoundError(f"{file.as_posix()} not found")
    module_name = f"embgen._plugins.{file.parent.name}"
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


def load_plugin(dir: Path) -> Plugin:
    embgen_file = dir / "embgen.yml"
    if not embgen_file.exists():
        raise FileNotFoundError(f"{embgen_file.as_posix()} not found")
    embgen_config = yaml.safe_load(embgen_file.read_text())

    generator_class = _load_plugin_file_class(dir / "generator.py", Generator)
    schema_class = _load_plugin_file_class(dir / "schema.py", Schema)

    return Plugin.model_validate(
        embgen_config,
        context={"generator_class": generator_class, "schema_class": schema_class},
    )


def discover_plugins(dir: Path) -> dict[Path, Plugin]:
    dir = dir.resolve().absolute()

    log.debug(f"Discovering plugins in {dir.as_posix()}")

    if not dir.is_dir():
        raise NotADirectoryError(
            f"{dir.as_posix()} is not a directory or does not exist"
        )

    result = {}

    for dir in dir.glob("*"):
        if not dir.is_dir():
            continue

        try:
            plugin = load_plugin(dir)
        except FileNotFoundError as e:
            log.warning(f"Incomplete plugin {dir.as_posix()}: {e}")
            continue
        except ValidationError as e:
            log.warning(f"Invalid embgen.yml in {dir.as_posix()}")
            log_validation_error(log, e, logging.WARNING)
            continue
        except Exception as e:
            log.warning(f"Error loading plugin {dir.as_posix()}: {e}")
            continue

        result[dir] = plugin

    return result
