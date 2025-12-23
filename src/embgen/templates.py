"""Template utilities and discovery."""

import re
from pathlib import Path

from jinja2 import Environment, FileSystemLoader

from .models import MultifileGroup, TemplateInfo


# Human-readable names for file extensions
FILE_TYPES = {
    "md": "Markdown",
    "py": "Python",
    "yml": "YAML",
    "json": "JSON",
    "tex": "LaTeX",
    "typ": "Typst",
    "h": "C Header",
    "c": "C Source",
    "rs": "Rust",
    "txt": "Text",
    "html": "HTML",
    "sv": "SystemVerilog",
    "v": "Verilog",
    "vhd": "VHDL",
}


def file_type(extension: str) -> str:
    """Get human-readable file type from extension."""
    return FILE_TYPES.get(extension, "Unknown")


def get_env(templates_path: Path) -> Environment:
    """Create a Jinja2 environment for a given templates directory."""
    return Environment(
        loader=FileSystemLoader(templates_path),
        trim_blocks=True,
        lstrip_blocks=True,
    )


def parse_template_name(filename: str) -> tuple[str | None, str, str | None]:
    """Parse a template filename to extract multifile group, extension, and suffix.

    Template naming conventions:
    - Single file: template.{ext}.j2 -> (None, ext, None)
    - Multifile different exts: template.{group}_multi.{ext}.j2 -> (group, ext, None)
    - Multifile same ext: template.{group}_multi.{ext}.{suffix}.j2 -> (group, ext, suffix)

    Examples:
    - template.h.j2 -> (None, "h", None)
    - template.c_multi.h.j2 -> ("c", "h", None)
    - template.c_multi.c.j2 -> ("c", "c", None)
    - template.sv_multi.sv.1.j2 -> ("sv", "sv", "1")
    - template.sv_multi.sv.2.j2 -> ("sv", "sv", "2")

    Args:
        filename: The template filename.

    Returns:
        Tuple of (group_name, output_extension, suffix).
    """
    # Remove .j2 or .jinja extension
    if filename.endswith(".j2"):
        base = filename[:-3]
    elif filename.endswith(".jinja"):
        base = filename[:-6]
    else:
        return None, "", None

    # Check for multifile pattern: *_multi.{ext}[.{suffix}]
    multi_match = re.match(r"^(.+)\.(\w+)_multi\.(\w+)(?:\.(\w+))?$", base)
    if multi_match:
        group = multi_match.group(2)  # e.g., "c" or "sv"
        ext = multi_match.group(3)  # e.g., "h", "c", or "sv"
        suffix = multi_match.group(4)  # e.g., "1", "2", or None
        return group, ext, suffix

    # Single file template: template.{ext}
    parts = base.rsplit(".", 1)
    if len(parts) == 2:
        return None, parts[1], None

    return None, "", None


def discover_templates(
    templates_path: Path,
) -> tuple[
    dict[str, tuple[str, str]],  # Single templates: ext -> (description, filename)
    dict[str, MultifileGroup],  # Multifile groups: group_name -> MultifileGroup
]:
    """Discover all templates in a directory, grouping multifile templates.

    Args:
        templates_path: Path to the templates directory.

    Returns:
        Tuple of (single_templates, multifile_groups).
    """
    single_templates: dict[str, tuple[str, str]] = {}
    multifile_groups: dict[str, MultifileGroup] = {}

    if not templates_path.exists():
        return single_templates, multifile_groups

    for path in templates_path.iterdir():
        if not path.name.endswith((".j2", ".jinja")):
            continue

        group_name, ext, suffix = parse_template_name(path.name)

        if group_name is None:
            # Single file template
            desc = file_type(ext)
            single_templates[ext] = (desc, path.name)
        else:
            # Multifile template
            if group_name not in multifile_groups:
                desc = f"{group_name.upper()} Multi-file"
                multifile_groups[group_name] = MultifileGroup(
                    group_name=group_name,
                    description=desc,
                )
            multifile_groups[group_name].templates.append(
                TemplateInfo(filename=path.name, output_ext=ext, suffix=suffix)
            )

    # Sort templates within each multifile group for consistent ordering
    for group in multifile_groups.values():
        group.templates.sort(key=lambda t: (t.output_ext, t.suffix or ""))

    return single_templates, multifile_groups
