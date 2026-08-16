import logging
from pathlib import Path

import yaml
from pydantic import ValidationError

from ..common import log_validation_error
from .models import Plugin

log = logging.getLogger(__name__)


def discover_plugins(dir: Path) -> dict[Path, Plugin]:
    log.debug(f"Discovering plugins in {dir.as_posix()}")

    if not dir.is_dir():
        raise NotADirectoryError

    result = {}

    for dir in dir.glob("*"):
        if not dir.is_dir():
            continue
        elif not (embgen_file := dir / "embgen.yml").exists():
            continue

        try:
            plugin = Plugin.model_validate(yaml.safe_load(embgen_file.read_text()))
        except ValidationError as e:
            log.warning(f"Invalid embgen.yml in {dir.as_posix()}")
            log_validation_error(log, e, logging.WARNING)
            continue

        result[dir] = plugin

    return result
