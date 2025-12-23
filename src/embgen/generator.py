"""Code generation orchestration."""

from __future__ import annotations

import logging
from datetime import datetime
from pathlib import Path
from typing import TYPE_CHECKING, Any

import yaml
from jinja2 import Environment

from .models import BaseConfig, MultifileGroup
from .templates import get_env

if TYPE_CHECKING:
    from .domains import DomainGenerator


class CodeGenerator:
    """Orchestrates code generation from YAML to output files.

    This class encapsulates the entire generation workflow:
    1. Parse and validate YAML input
    2. Set up Jinja2 environment
    3. Render templates to output files
    4. Run post-generation hooks

    Example:
        >>> from embgen.generator import CodeGenerator
        >>> from embgen.discovery import discover_domains
        >>>
        >>> generator = discover_domains()["commands"]
        >>> code_gen = CodeGenerator(generator, Path("output"))
        >>> filenames = code_gen.generate_from_file(
        ...     Path("config.yml"),
        ...     templates={"h": "template.h.j2", "py": "template.py.j2"}
        ... )
    """

    def __init__(self, generator: DomainGenerator, output_path: Path):
        """Initialize the code generator.

        Args:
            generator: The domain generator to use for validation and rendering.
            output_path: Path to the output directory.
        """
        self.generator = generator
        self.output_path = Path(output_path).resolve()
        self._env: Environment | None = None
        self._log = logging.getLogger("embgen")

    @property
    def env(self) -> Environment:
        """Get or create the Jinja2 environment."""
        if self._env is None:
            self._env = get_env(self.generator.templates_path)
            self._env.globals["generated_on"] = datetime.now().strftime(
                "%Y-%m-%d %H:%M:%S"
            )
        return self._env

    def parse_yaml(self, input_path: Path) -> dict[str, Any]:
        """Parse a YAML file and return the data as a dictionary.

        Args:
            input_path: Path to the YAML file.

        Returns:
            Parsed YAML data as a dictionary.

        Raises:
            FileNotFoundError: If the file doesn't exist or isn't a YAML file.
            RuntimeError: If parsing fails.
        """
        input_path = Path(input_path).resolve()

        if not input_path.exists():
            raise FileNotFoundError(f"Input file {input_path} does not exist")
        if not input_path.is_file():
            raise FileNotFoundError(f"Input file {input_path} is not a file")
        if input_path.suffix not in [".yml", ".yaml"]:
            raise FileNotFoundError(f"Input file {input_path} is not a YAML file")

        self._log.info(f"Loading YAML file from {input_path.as_posix()}")

        try:
            with open(input_path, "r") as file:
                data = yaml.safe_load(file)
        except Exception as e:
            raise RuntimeError("Failed to load YAML file") from e

        return data

    def validate(self, data: dict[str, Any]) -> BaseConfig:
        """Validate YAML data against the domain schema.

        Args:
            data: Parsed YAML data.

        Returns:
            Validated configuration object.

        Raises:
            RuntimeError: If validation fails.
        """
        self._log.debug(f"Validating {self.generator.name} configuration")

        try:
            return self.generator.validate(data)
        except Exception as e:
            self._log.error(f"Failed to validate {self.generator.name}: {e}")
            raise RuntimeError(f"Failed to validate {self.generator.name}") from e

    def ensure_output_dir(self) -> Path:
        """Ensure output directory exists, creating it if necessary.

        Returns:
            The resolved output path.

        Raises:
            FileNotFoundError: If the parent directory doesn't exist.
        """
        if not self.output_path.parent.exists():
            raise FileNotFoundError(
                f"Output directory {self.output_path.parent} does not exist"
            )
        if not self.output_path.parent.is_dir():
            raise FileNotFoundError(
                f"Output directory {self.output_path.parent} is not a directory"
            )
        if not self.output_path.exists():
            self._log.debug(f"Creating output directory {self.output_path}")
            self.output_path.mkdir(exist_ok=True, parents=True)

        return self.output_path

    def render_to_file(
        self,
        config: BaseConfig,
        template_name: str,
        output_ext: str,
        suffix: str | None = None,
    ) -> str:
        """Render a config to a template and write to file.

        Args:
            config: Validated configuration.
            template_name: Template filename.
            output_ext: Output file extension.
            suffix: Optional suffix for multifile outputs (e.g., "1", "2").

        Returns:
            The generated filename.
        """
        template = self.env.get_template(template_name)
        content = self.generator.render(config, template)

        if suffix:
            filename = f"{config.output_filename}_{suffix}.{output_ext}"
        else:
            filename = f"{config.output_filename}.{output_ext}"

        output_file = self.output_path / filename

        self._log.debug(f"Writing {output_ext} output to '{filename}'")
        with open(output_file, "w") as f:
            f.write(content)

        return filename

    def render_multifile_group(
        self,
        config: BaseConfig,
        multifile_group: MultifileGroup,
    ) -> list[str]:
        """Render all templates in a multifile group.

        Args:
            config: Validated configuration.
            multifile_group: The multifile group to render.

        Returns:
            List of generated filenames.
        """
        filenames = []
        ext_counts: dict[str, int] = {}

        for template_info in multifile_group.templates:
            suffix = template_info.suffix

            # Handle same-extension multifiles without explicit suffix
            if suffix is None:
                ext = template_info.output_ext
                same_ext_templates = [
                    t for t in multifile_group.templates if t.output_ext == ext
                ]

                if len(same_ext_templates) > 1:
                    if ext in ext_counts:
                        ext_counts[ext] += 1
                    else:
                        ext_counts[ext] = 1
                    suffix = str(ext_counts[ext])

            filename = self.render_to_file(
                config,
                template_info.filename,
                template_info.output_ext,
                suffix,
            )
            filenames.append(filename)

        return filenames

    def generate(
        self,
        config: BaseConfig,
        templates: dict[str, str] | None = None,
        multifile_groups: dict[str, MultifileGroup] | None = None,
    ) -> list[str]:
        """Generate output files from a validated configuration.

        Args:
            config: Validated configuration object.
            templates: Dict mapping output extension to template filename.
            multifile_groups: Optional dict of multifile groups to render.

        Returns:
            List of generated filenames.
        """
        if templates is None:
            templates = {}
        if multifile_groups is None:
            multifile_groups = {}

        self.ensure_output_dir()

        self._log.info(f"Writing outputs to {self.output_path.as_posix()}")
        filenames: list[str] = []
        generated_extensions: set[str] = set()

        # Render single-file templates
        for output_ext, template_name in templates.items():
            filename = self.render_to_file(config, template_name, output_ext)
            filenames.append(filename)
            generated_extensions.add(output_ext)

        # Render multifile groups
        for group_name, mf_group in multifile_groups.items():
            self._log.debug(f"Rendering multifile group '{group_name}'")
            mf_filenames = self.render_multifile_group(config, mf_group)
            filenames.extend(mf_filenames)
            generated_extensions.update(mf_group.output_extensions)

        # Run post-generation hook
        extra_files = self.generator.post_generate(
            config, self.output_path, generated_extensions
        )
        filenames.extend(extra_files)

        self._log.info(f"Wrote {len(filenames)} files: {', '.join(filenames)}")
        return filenames

    def generate_from_file(
        self,
        input_path: Path,
        templates: dict[str, str] | None = None,
        multifile_groups: dict[str, MultifileGroup] | None = None,
    ) -> list[str]:
        """Parse YAML file and generate output files.

        This is the main entry point for file-based generation.

        Args:
            input_path: Path to the input YAML file.
            templates: Dict mapping output extension to template filename.
            multifile_groups: Optional dict of multifile groups to render.

        Returns:
            List of generated filenames.
        """
        data = self.parse_yaml(input_path)
        config = self.validate(data)
        return self.generate(config, templates, multifile_groups)
