"""Configuration loader module supporting YAML, JSON, TOML, HJSON, in-file includes, env vars, and multi-document YAML."""

import json
import logging
import os
import tomllib
from collections.abc import Sequence
from pathlib import Path
from typing import Any, Generic

import hjson
import yaml
from jinja2 import Environment
from pydantic import ValidationError

from .common import log_validation_error
from .plugin import SchemaT

log = logging.getLogger(__name__)


def deep_merge(base: Any, override: Any) -> Any:
    """Recursively merge two dictionaries (or return override for non-dicts).

    Args:
        base: The base dictionary or value.
        override: The overriding dictionary or value.

    Returns:
        The merged dictionary or value.
    """
    if isinstance(base, dict) and isinstance(override, dict):
        merged = dict(base)
        for key, val in override.items():
            if key in merged:
                merged[key] = deep_merge(merged[key], val)
            else:
                merged[key] = val
        return merged
    return override


def _create_yaml_loader(base_dir: Path, visited: set[Path]) -> type[yaml.SafeLoader]:
    """Create a scoped, thread-safe PyYAML SafeLoader with !include and !inc support."""

    class ScopedYamlLoader(yaml.SafeLoader):
        pass

    def include_constructor(loader: yaml.SafeLoader, node: yaml.Node) -> Any:
        filename = loader.construct_scalar(node)
        target_path = (base_dir / str(filename)).resolve()

        if target_path in visited:
            raise ValueError(f"Cyclic include detected: {target_path.as_posix()}")
        if not target_path.exists():
            raise FileNotFoundError(
                f"Included file not found: {target_path.as_posix()}"
            )

        new_visited = visited | {target_path}
        with open(target_path, "r", encoding="utf-8") as f:
            sub_loader_cls = _create_yaml_loader(target_path.parent, new_visited)
            return yaml.load(f, Loader=sub_loader_cls)

    ScopedYamlLoader.add_constructor("!include", include_constructor)
    ScopedYamlLoader.add_constructor("!inc", include_constructor)
    return ScopedYamlLoader


def resolve_includes(
    data: Any,
    base_dir: Path,
    visited: set[Path] | None = None,
) -> Any:
    """Recursively resolves $ref and $include references in parsed dictionary/list data.

    Args:
        data: The parsed data (dictionary, list, or scalar).
        base_dir: Directory against which relative paths are resolved.
        visited: Set of already visited absolute paths to detect cycles.

    Returns:
        The data structure with all includes/refs resolved.
    """
    if visited is None:
        visited = set()

    if isinstance(data, dict):
        ref_path_str: str | None = None
        if "$include" in data and len(data) == 1:
            ref_path_str = str(data["$include"])
        elif (
            "$ref" in data and len(data) == 1 and not str(data["$ref"]).startswith("#")
        ):
            ref_path_str = str(data["$ref"])

        if ref_path_str is not None:
            target_path = (base_dir / ref_path_str).resolve()
            if target_path in visited:
                raise ValueError(f"Cyclic include detected: {target_path.as_posix()}")

            if not target_path.exists():
                raise FileNotFoundError(
                    f"Included file not found: {target_path.as_posix()}"
                )

            new_visited = visited | {target_path}
            content = target_path.read_text(encoding="utf-8")
            sub_data = _parse_content(
                content, target_path.suffix, target_path.parent, new_visited
            )
            return resolve_includes(sub_data, target_path.parent, new_visited)

        return {k: resolve_includes(v, base_dir, visited) for k, v in data.items()}

    if isinstance(data, list):
        return [resolve_includes(item, base_dir, visited) for item in data]

    return data


def _render_template(
    content: str, context: dict[str, Any] | None = None, env: bool = True
) -> str:
    """Render a Jinja2 template with context and optional environment variables."""
    merged_context: dict[str, Any] = {}
    if env:
        merged_context.update(os.environ)
    if context:
        merged_context.update(context)

    jinja_env = Environment(autoescape=False)
    return jinja_env.from_string(content).render(merged_context)


def _parse_content(
    content: str,
    format: str,
    base_dir: Path,
    visited: set[Path] | None = None,
) -> Any:
    """Parse raw configuration content into Python data structures.

    Args:
        content: The raw string content to parse.
        format: Format string/extension (.yaml, .json, .toml, .hjson).
        base_dir: Directory for relative in-file includes.
        visited: Set of visited paths for include cycle detection.

    Returns:
        Parsed Python object (dict, list, etc.).
    """
    fmt = format.lstrip(".").lower()
    if visited is None:
        visited = set()

    if fmt in {"yaml", "yml"}:
        loader_cls = _create_yaml_loader(base_dir, visited)
        return yaml.load(content, Loader=loader_cls)
    elif fmt in {"json", "jsn", "js"}:
        return json.loads(content)
    elif fmt == "toml":
        return tomllib.loads(content)
    elif fmt == "hjson":
        return hjson.loads(content)
    else:
        raise ValueError(f"Unsupported configuration format: '{format}'")


class Loader(Generic[SchemaT]):
    """Loads configuration files (YAML, JSON, TOML, HJSON) into Pydantic Schemas.

    Args:
        schema_class: The Pydantic Schema model to validate and instantiate.
    """

    def __init__(self, schema_class: type[SchemaT]):
        self.schema_class = schema_class

    def load_dict(self, data: Any) -> SchemaT:
        """Validate and construct a schema instance from a raw dictionary or mapping.

        Args:
            data: The parsed dictionary or data object.

        Returns:
            The validated schema model.

        Raises:
            ValidationError: If data does not conform to the schema model.
        """
        try:
            return self.schema_class.model_validate(data)
        except ValidationError as e:
            log_validation_error(log, e)
            raise

    def load(
        self,
        path: Path | str,
        *,
        template: bool = False,
        context: dict[str, Any] | None = None,
        env: bool = True,
    ) -> SchemaT:
        """Load a configuration file and validate it against the schema.

        Args:
            path: Path to the configuration file (.yml, .yaml, .json, .toml, .hjson).
            template: Whether to compile and render as a Jinja2 template prior to parsing.
            context: Template variables context if `template` is True.
            env: Whether to automatically include os.environ in template context.

        Returns:
            The validated schema model.
        """
        target_path = Path(path)
        if not target_path.exists():
            raise FileNotFoundError(f"File not found: {target_path.as_posix()}")
        if not target_path.is_file():
            raise IsADirectoryError(f"Path is not a file: {target_path.as_posix()}")

        content = target_path.read_text(encoding="utf-8")
        return self.load_string(
            content,
            format=target_path.suffix,
            template=template,
            context=context,
            env=env,
            base_dir=target_path.parent,
        )

    def load_multi(
        self,
        paths: Sequence[Path | str],
        *,
        template: bool = False,
        context: dict[str, Any] | None = None,
        env: bool = True,
    ) -> SchemaT:
        """Load and merge multiple configuration files (e.g. base + overlay) into a single schema.

        Args:
            paths: A list of paths to load and merge in order.
            template: Whether to render templates.
            context: Template context dictionary.
            env: Whether to automatically include os.environ in template context.

        Returns:
            The validated merged schema model.
        """
        resolved_paths = [Path(p) for p in paths]
        for p in resolved_paths:
            if not p.exists():
                raise FileNotFoundError(f"File not found: {p.as_posix()}")
            if not p.is_file():
                raise IsADirectoryError(f"Path is not a file: {p.as_posix()}")

        merged_data: Any = {}
        for p in resolved_paths:
            content = p.read_text(encoding="utf-8")
            if template:
                content = _render_template(content, context, env)
            parsed = _parse_content(content, p.suffix, p.parent)
            resolved = resolve_includes(parsed, p.parent)
            merged_data = deep_merge(merged_data, resolved)

        return self.load_dict(merged_data)

    def load_string(
        self,
        content: str,
        format: str,
        *,
        template: bool = False,
        context: dict[str, Any] | None = None,
        env: bool = True,
        base_dir: Path | None = None,
    ) -> SchemaT:
        """Load configuration from a raw string.

        Args:
            content: The configuration file content string.
            format: Format type (e.g., 'yaml', 'json', 'toml', 'hjson').
            template: Whether to evaluate as a Jinja2 template.
            context: Template context dictionary.
            env: Whether to automatically include os.environ in template context.
            base_dir: Base directory for resolving relative in-file includes.

        Returns:
            The validated schema model.
        """
        base_path = base_dir or Path.cwd()
        raw_content = content
        if template:
            raw_content = _render_template(content, context, env)

        parsed = _parse_content(raw_content, format, base_path)
        resolved = resolve_includes(parsed, base_path)
        return self.load_dict(resolved)

    def load_all(
        self,
        path: Path | str,
        *,
        template: bool = False,
        context: dict[str, Any] | None = None,
        env: bool = True,
    ) -> list[SchemaT]:
        """Load a multi-document YAML configuration file and validate each document.

        Args:
            path: Path to the configuration file.
            template: Whether to compile and render as a Jinja2 template prior to parsing.
            context: Template variables context if `template` is True.
            env: Whether to automatically include os.environ in template context.

        Returns:
            A list of validated schema models.
        """
        target_path = Path(path)
        if not target_path.exists():
            raise FileNotFoundError(f"File not found: {target_path.as_posix()}")
        if not target_path.is_file():
            raise IsADirectoryError(f"Path is not a file: {target_path.as_posix()}")

        content = target_path.read_text(encoding="utf-8")
        return self.load_all_string(
            content,
            format=target_path.suffix,
            template=template,
            context=context,
            env=env,
            base_dir=target_path.parent,
        )

    def load_all_string(
        self,
        content: str,
        format: str = "yaml",
        *,
        template: bool = False,
        context: dict[str, Any] | None = None,
        env: bool = True,
        base_dir: Path | None = None,
    ) -> list[SchemaT]:
        """Load multiple configuration documents from a raw string.

        Args:
            content: The multi-document content string.
            format: Format type (defaults to 'yaml').
            template: Whether to evaluate as a Jinja2 template.
            context: Template context dictionary.
            env: Whether to automatically include os.environ in template context.
            base_dir: Base directory for resolving relative in-file includes.

        Returns:
            A list of validated schema models.
        """
        base_path = base_dir or Path.cwd()
        fmt = format.lstrip(".").lower()
        if fmt in {"yaml", "yml"}:
            rendered_content = content
            if template:
                rendered_content = _render_template(content, context, env)

            loader_cls = _create_yaml_loader(base_path, set())
            raw_docs = list(yaml.load_all(rendered_content, Loader=loader_cls))
            results: list[SchemaT] = []
            for doc in raw_docs:
                if doc is not None:
                    resolved_doc = resolve_includes(doc, base_path)
                    results.append(self.load_dict(resolved_doc))
            return results
        else:
            raise ValueError(
                f"Unsupported format for multi-document loading: '{format}'"
            )
