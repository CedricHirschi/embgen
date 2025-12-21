"""Shared template utilities."""

from pathlib import Path

from jinja2 import Environment, FileSystemLoader


FILE_TYPES = {
    "md": "Markdown",
    "py": "Python",
    "yml": "YAML",
    "json": "JSON",
    "tex": "LaTeX",
    "typ": "Typst",
    "h": "C Header",
    "rs": "Rust",
    "txt": "Text",
    "html": "HTML",
}


def file_type(extension: str) -> str:
    """Get human-readable file type from extension."""
    if extension in FILE_TYPES:
        return FILE_TYPES[extension]
    return "Unknown"


def get_env(templates_path: Path) -> Environment:
    """Create a Jinja2 environment for a given templates directory."""
    return Environment(
        loader=FileSystemLoader(templates_path), trim_blocks=True, lstrip_blocks=True
    )
