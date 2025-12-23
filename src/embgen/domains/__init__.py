"""Domain generator interface.

This module defines the abstract base class that all domain generators must implement.
The discovery and detection logic has been moved to embgen.discovery.
"""

from abc import ABC, abstractmethod
from pathlib import Path
from typing import Any

from jinja2 import Template

# Re-export BaseConfig from models for backwards compatibility
from ..models import BaseConfig

__all__ = ["DomainGenerator", "BaseConfig"]


class DomainGenerator(ABC):
    """Abstract base class that every domain generator must implement.

    A domain generator is responsible for:
    - Detecting if YAML data belongs to this domain
    - Validating YAML data into a typed configuration
    - Rendering configurations to Jinja2 templates
    - Optionally copying extra files after generation

    To create a new domain, subclass this and implement all abstract methods.
    """

    @property
    @abstractmethod
    def name(self) -> str:
        """Domain name for CLI subcommand (e.g., 'commands')."""
        ...

    @property
    @abstractmethod
    def description(self) -> str:
        """Help text for CLI."""
        ...

    @abstractmethod
    def detect(self, data: dict[str, Any]) -> bool:
        """Return True if this YAML data belongs to this domain.

        Used for auto-detection of domain from YAML content.

        Args:
            data: Parsed YAML data.

        Returns:
            True if this domain should handle this data.
        """
        ...

    @abstractmethod
    def validate(self, data: dict[str, Any]) -> BaseConfig:
        """Parse and validate YAML data into a domain-specific config.

        Args:
            data: Parsed YAML data.

        Returns:
            A validated configuration object (subclass of BaseConfig).

        Raises:
            ValidationError: If the data doesn't match the expected schema.
        """
        ...

    @abstractmethod
    def render(self, config: Any, template: Template) -> str:
        """Render a configuration to a Jinja2 template.

        Args:
            config: The validated configuration object.
            template: The Jinja2 template to render.

        Returns:
            The rendered template content as a string.
        """
        ...

    @property
    def templates_path(self) -> Path:
        """Path to this domain's templates directory.

        By default, looks for a 'templates' subdirectory in the domain's package.
        Override this if your templates are in a different location.
        """
        return Path(__file__).parent / self.name / "templates"

    def post_generate(
        self, config: BaseConfig, output: Path, generated_extensions: set[str]
    ) -> list[str]:
        """Hook called after all templates are rendered.

        Use this to copy additional static files (e.g., base classes, utilities)
        that should accompany the generated code.

        Args:
            config: The validated domain configuration.
            output: Path to the output directory.
            generated_extensions: Set of file extensions that were generated.

        Returns:
            List of extra filenames that were copied.
        """
        return []
