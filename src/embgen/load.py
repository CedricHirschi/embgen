import json
from pathlib import Path
from typing import Generic

import yaml

from .plugin import SchemaT


class Loader(Generic[SchemaT]):
    EXTENSIONS = {".json": json.loads, ".yaml": yaml.safe_load, ".yml": yaml.safe_load}

    def __init__(self, schema_class: type[SchemaT]):
        self.schema_class = schema_class

    def load(self, path: Path) -> SchemaT:
        if not path.exists():
            raise FileNotFoundError(f"File not found: {path.as_posix()}")
        elif not path.is_file():
            raise IsADirectoryError(f"Path is not a file: {path.as_posix()}")

        path_ext = path.suffix.lower()

        if path_ext not in self.EXTENSIONS:
            raise ValueError(f"Unsupported file extension: {path_ext}")

        ext_loader = self.EXTENSIONS[path_ext]

        if not callable(ext_loader) and ext_loader not in dir(self):
            raise NotImplementedError(f"Loader for {path_ext} is not implemented")

        content = path.read_text(encoding="utf-8")
        data = ext_loader(content)
        return self.schema_class.model_validate(data)
