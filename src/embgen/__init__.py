"""embgen - Embedded Code Generator.

A unified code generator for embedded systems that generates code from YAML definitions.

Example usage:
    >>> from embgen import CodeGenerator, discover_domains
    >>>
    >>> # Discover available domains
    >>> domains = discover_domains()
    >>>
    >>> # Create a generator for the commands domain
    >>> commands_gen = domains["commands"]
    >>> code_gen = CodeGenerator(commands_gen, Path("output"))
    >>>
    >>> # Generate files from YAML
    >>> filenames = code_gen.generate_from_file(
    ...     Path("config.yml"),
    ...     templates={"h": "template.h.j2", "py": "template.py.j2"}
    ... )
"""

from .discovery import (
    detect_domain,
    discover_domains,
    BUILTIN_DOMAINS_PATH,
    EMBGEN_DOMAINS_DIR_ENV,
)
from .domains import DomainGenerator
from .generator import CodeGenerator
from .models import BaseConfig, Enum, MultifileGroup, TemplateInfo
from .scaffold import scaffold_domain
from .templates import discover_templates, file_type, get_env

__all__ = [
    # Core classes
    "CodeGenerator",
    "DomainGenerator",
    # Models
    "BaseConfig",
    "Enum",
    "TemplateInfo",
    "MultifileGroup",
    # Discovery
    "discover_domains",
    "detect_domain",
    "BUILTIN_DOMAINS_PATH",
    "EMBGEN_DOMAINS_DIR_ENV",
    # Utilities
    "scaffold_domain",
    "discover_templates",
    "file_type",
    "get_env",
]
