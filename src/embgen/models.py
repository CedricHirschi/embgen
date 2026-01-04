"""Base models shared across all domains.

This module contains:
    - Pydantic models for configuration validation (BaseConfig, Enum)
    - Dataclasses for internal data structures (TemplateInfo, MultifileGroup)
"""

from dataclasses import dataclass, field

from pydantic import BaseModel


# =============================================================================
# Pydantic Models (for config validation from YAML)
# =============================================================================


class BaseConfig(BaseModel):
    """Base configuration that all domain configs must extend.

    This provides the common fields that every domain needs:
        - name: The human-readable name for the generated code
        - file: Optional override for the output filename
    """

    name: str
    file: str | None = None

    @property
    def output_filename(self) -> str:
        """Get the output filename (defaults to lowercase name)."""
        return self.file or self.name.lower()


class Enum(BaseModel):
    """Enumeration value used in both commands and registers."""

    name: str
    description: str | None = None
    value: int


# =============================================================================
# Dataclasses (for internal data structures)
# =============================================================================


@dataclass
class TemplateInfo:
    """Information about a single template file."""

    filename: str  # Full template filename, e.g., "template.h.j2"
    output_ext: str  # Output file extension, e.g., "h"
    suffix: str | None = None  # Suffix for multifile output, e.g., "1", "2", or None


@dataclass
class MultifileGroup:
    """A group of templates that produce multiple output files."""

    group_name: str  # Group identifier, e.g., "c" for c_multi, "sv" for sv_multi
    description: str  # Human-readable description
    templates: list[TemplateInfo] = field(default_factory=list)

    @property
    def output_extensions(self) -> list[str]:
        """Get all output extensions for this group."""
        return [t.output_ext for t in self.templates]
