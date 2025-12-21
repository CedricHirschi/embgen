from abc import ABC, abstractmethod
from pathlib import Path
from typing import Any, TypeVar
import importlib
import importlib.util
import os
import sys

from pydantic import BaseModel
from jinja2 import Template


# Environment variable for user domains directory
EMBGEN_DOMAINS_DIR_ENV = "EMBGEN_DOMAINS_DIR"


class BaseConfig(BaseModel):
    """All domain configs must have these fields."""

    name: str
    file: str | None = None

    @property
    def output_filename(self) -> str:
        return self.file or self.name.lower()


# TypeVar for subclass-specific config types (covariant for return types)
ConfigT = TypeVar("ConfigT", bound=BaseConfig)


class DomainGenerator(ABC):
    """Interface every domain must implement."""

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
        """Return True if this YAML data belongs to this domain."""
        ...

    @abstractmethod
    def validate(self, data: dict[str, Any]) -> BaseConfig:
        """Parse and validate YAML into domain config."""
        ...

    @abstractmethod
    def render(self, config: Any, template: Template) -> str:
        """Render config to a template."""
        ...

    @property
    def templates_path(self) -> Path:
        """Path to this domain's templates (auto-derived)."""
        return Path(__file__).parent / self.name / "templates"

    def post_generate(
        self, config: BaseConfig, output: Path, generated_extensions: set[str]
    ) -> list[str]:
        """Optional: copy extra files after generation.

        Args:
            config: The validated domain configuration.
            output: Path to the output directory.
            generated_extensions: Set of file extensions that were generated (e.g., {'h', 'py', 'md'}).

        Returns:
            List of extra filenames that were copied.
        """
        return []


def _discover_domains_in_path(
    domains_path: Path, package_name: str | None = None
) -> dict[str, DomainGenerator]:
    """Discover domain generators in a specific directory.

    Args:
        domains_path: Path to the domains directory.
        package_name: Package name for relative imports (None for external dirs).

    Returns:
        Dict mapping domain name to generator instance.
    """
    domains: dict[str, DomainGenerator] = {}

    if not domains_path.exists() or not domains_path.is_dir():
        return domains

    for item in domains_path.iterdir():
        if not item.is_dir() or not (item / "__init__.py").exists():
            continue
        if item.name.startswith("_"):
            continue

        try:
            if package_name:
                # Internal package import
                module = importlib.import_module(f".{item.name}", package_name)
            else:
                # External directory import
                spec = importlib.util.spec_from_file_location(
                    f"embgen_user_domain_{item.name}",
                    item / "__init__.py",
                    submodule_search_locations=[str(item)],
                )
                if spec is None or spec.loader is None:
                    continue
                module = importlib.util.module_from_spec(spec)
                sys.modules[spec.name] = module
                spec.loader.exec_module(module)

            if hasattr(module, "generator"):
                domains[module.generator.name] = module.generator
        except Exception:
            # Skip domains that fail to load
            pass

    return domains


def discover_domains(
    extra_domains_dir: Path | str | None = None,
) -> dict[str, DomainGenerator]:
    """Auto-discover all domain generators.

    Args:
        extra_domains_dir: Optional path to additional user domains directory.
            Can also be set via EMBGEN_DOMAINS_DIR environment variable.

    Returns:
        Dict mapping domain name to generator instance.
        User domains override built-in domains with the same name.
    """
    # Discover built-in domains
    builtin_path = Path(__file__).parent
    domains = _discover_domains_in_path(builtin_path, __package__)

    # Check for extra domains directory from argument or environment
    user_domains_path: Path | None = None
    if extra_domains_dir:
        user_domains_path = Path(extra_domains_dir)
    elif EMBGEN_DOMAINS_DIR_ENV in os.environ:
        user_domains_path = Path(os.environ[EMBGEN_DOMAINS_DIR_ENV])

    # Discover user domains (these override built-in domains)
    if user_domains_path:
        user_domains = _discover_domains_in_path(user_domains_path, None)
        domains.update(user_domains)

    return domains


def detect_domain(
    data: dict[str, Any], extra_domains_dir: Path | str | None = None
) -> DomainGenerator | None:
    """Auto-detect domain from YAML content."""
    for generator in discover_domains(extra_domains_dir).values():
        if generator.detect(data):
            return generator
    return None


def get_builtin_domains_path() -> Path:
    """Get the path to the built-in domains directory."""
    return Path(__file__).parent
