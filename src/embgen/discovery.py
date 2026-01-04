"""Domain discovery and auto-detection logic.

This module provides the functionality to automatically detect which domain a YAML
configuration file belongs to, and to discover all available domain generators.
It handles both built-in domains (shipped with embgen) and user-defined domains
(loaded from a custom directory).

The discovery process works by:

1. Looking for domain packages in the built-in domains directory
2. Optionally searching user-defined domains from EMBGEN_DOMAINS_DIR environment variable
3. Attempting to auto-detect the correct domain from YAML content using each domain's detector

Key Functions:

- `detect_domain`: Auto-detect which domain a YAML file belongs to
- `discover_domains`: Find all available domain generators

Example:
    ```python
    from embgen.discovery import detect_domain, discover_domains

    # Discover all available domains
    domains = discover_domains()
    print(f"Available domains: {list(domains.keys())}")

    # Auto-detect domain from YAML content
    with open("config.yml") as f:
        data = yaml.safe_load(f)
    domain_name, generator = detect_domain(data)
    print(f"Detected domain: {domain_name}")
    ```
"""

from __future__ import annotations

import importlib
import importlib.util
import os
import sys
from pathlib import Path
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from .domains import DomainGenerator

# Environment variable for user domains directory
EMBGEN_DOMAINS_DIR_ENV = "EMBGEN_DOMAINS_DIR"

# Path to built-in domains directory
BUILTIN_DOMAINS_PATH = Path(__file__).parent / "domains"


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
            Can also be set via `EMBGEN_DOMAINS_DIR` environment variable.

    Returns:
        Dict mapping domain name to generator instance.
        User domains override built-in domains with the same name.
    """
    # Discover built-in domains
    domains = _discover_domains_in_path(BUILTIN_DOMAINS_PATH, "embgen.domains")

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
    """Auto-detect domain from YAML content.

    Args:
        data: Parsed YAML data.
        extra_domains_dir: Optional path to additional user domains directory.

    Returns:
        The detected DomainGenerator, or None if no domain matches.
    """
    for generator in discover_domains(extra_domains_dir).values():
        if generator.detect(data):
            return generator
    return None
