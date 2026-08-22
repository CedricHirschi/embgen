"""Configuration loader module using anyconfig."""

from pathlib import Path
from typing import Any, Generic, Sequence

import anyconfig

from .plugin import SchemaT


class Loader(Generic[SchemaT]):
    """Loads configuration files (YAML, JSON, TOML, etc.) into Pydantic Schemas via anyconfig.

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
        """
        return self.schema_class.model_validate(data)

    def load(
        self,
        path: Path | str,
        *,
        template: bool = False,
        context: dict[str, Any] | None = None,
        **options: Any,
    ) -> SchemaT:
        """Load a configuration file and validate it against the schema.

        Args:
            path: Path to the configuration file (.yml, .yaml, .json, .toml, etc.).
            template: Whether to compile and render as a Jinja2 template prior to parsing.
            context: Template variables context if `template` is True.
            **options: Additional backend options passed to `anyconfig.load()`.

        Returns:
            The validated schema model.
        """
        target_path = Path(path)
        if not target_path.exists():
            raise FileNotFoundError(f"File not found: {target_path.as_posix()}")
        if not target_path.is_file():
            raise IsADirectoryError(f"Path is not a file: {target_path.as_posix()}")

        opts = dict(options)
        if "ac_parser" not in opts and target_path.suffix:
            ext = target_path.suffix.lower()
            if ext in {".yaml", ".yml"}:
                opts["ac_parser"] = "yaml"
            elif ext in {".json", ".jsn", ".js"}:
                opts["ac_parser"] = "json"
            else:
                opts["ac_parser"] = ext.lstrip(".")

        try:
            data = anyconfig.load(
                target_path,
                ac_template=template,
                ac_context=context,
                **opts,
            )
        except (
            anyconfig.UnknownFileTypeError,
            anyconfig.UnknownParserTypeError,
            anyconfig.UnknownProcessorTypeError,
        ) as e:
            raise ValueError(
                f"Unsupported configuration file type for {target_path}: {e}"
            ) from e

        return self.load_dict(data)

    def load_multi(
        self,
        paths: Sequence[Path | str],
        *,
        merge_strategy: str = anyconfig.MS_DICTS,
        template: bool = False,
        context: dict[str, Any] | None = None,
        **options: Any,
    ) -> SchemaT:
        """Load and merge multiple configuration files (e.g. base + overlay) into a single schema.

        Args:
            paths: A list of paths to load and merge in order.
            merge_strategy: anyconfig merge strategy (e.g., anyconfig.MS_DICTS or MS_DICTS_AND_LISTS).
            template: Whether to render templates.
            context: Template context dictionary.
            **options: Additional backend options passed to `anyconfig.load()`.

        Returns:
            The validated merged schema model.
        """
        resolved_paths = [Path(p) for p in paths]
        for p in resolved_paths:
            if not p.exists():
                raise FileNotFoundError(f"File not found: {p.as_posix()}")

        try:
            data = anyconfig.load(
                resolved_paths,
                ac_merge=merge_strategy,
                ac_template=template,
                ac_context=context,
                **options,
            )
        except (
            anyconfig.UnknownFileTypeError,
            anyconfig.UnknownParserTypeError,
            anyconfig.UnknownProcessorTypeError,
        ) as e:
            raise ValueError(f"Unsupported configuration file type: {e}") from e

        return self.load_dict(data)

    def load_string(
        self,
        content: str,
        format: str,
        *,
        template: bool = False,
        context: dict[str, Any] | None = None,
        **options: Any,
    ) -> SchemaT:
        """Load configuration from a raw string.

        Args:
            content: The configuration file content string.
            format: Format type (e.g., 'yaml', 'json', 'toml').
            template: Whether to evaluate as a Jinja2 template.
            context: Template context dictionary.
            **options: Additional backend options passed to `anyconfig.loads()`.

        Returns:
            The validated schema model.
        """
        parser_type = format.lstrip(".").lower()
        if parser_type == "yml":
            parser_type = "yaml"

        try:
            data = anyconfig.loads(
                content,
                ac_parser=parser_type,
                ac_template=template,
                ac_context=context,
                **options,
            )
        except (
            anyconfig.UnknownParserTypeError,
            anyconfig.UnknownProcessorTypeError,
            anyconfig.UnknownFileTypeError,
        ) as e:
            raise ValueError(f"Unsupported format '{format}': {e}") from e

        return self.load_dict(data)
