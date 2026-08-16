import logging
import sys
from importlib.util import module_from_spec, spec_from_file_location
from pathlib import Path

import yaml
from pydantic import ValidationError

from ..common import log_validation_error
from ..generator import Generator
from .models import Plugin

log = logging.getLogger(__name__)


def load_plugin(dir: Path) -> Plugin:
    if not (embgen_file := dir / "embgen.yml").exists():
        raise FileNotFoundError(f"embgen.yml not found in {dir.as_posix()}")
    elif not (generator_file := dir / "generator.py").exists():
        raise FileNotFoundError(f"generator.py not found in {dir.as_posix()}")

    module_name = f"embgen._plugins.{dir.name}"
    spec = spec_from_file_location(module_name, generator_file)
    if spec is None or spec.loader is None:
        raise ImportError(f"Could not load {generator_file.as_posix()}")
    generator_module = module_from_spec(spec)
    sys.modules[module_name] = generator_module
    spec.loader.exec_module(generator_module)

    generator_classes = [
        cls
        for cls in generator_module.__dict__.values()
        if isinstance(cls, type) and issubclass(cls, Generator) and cls is not Generator
    ]
    if len(generator_classes) != 1:
        raise ValueError(
            f"Expected exactly one Generator subclass in {generator_file.as_posix()}, found {len(generator_classes)}"
        )
    generator_class = generator_classes[0]

    return Plugin.model_validate(
        yaml.safe_load(embgen_file.read_text()),
        context={"generator_class": generator_class},
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
