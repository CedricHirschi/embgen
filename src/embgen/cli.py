"""Command-line interface for embgen."""

import argparse
import logging
import sys
import time
from pathlib import Path

from rich.logging import RichHandler

from .domains import (
    discover_domains,
    detect_domain,
    DomainGenerator,
    get_builtin_domains_path,
)
from .core import parse_and_render, parse_yaml
from .templates import discover_templates, MultifileGroup


def get_template_args(
    generator: DomainGenerator,
) -> tuple[
    dict[str, tuple[str, str]],  # Single templates: ext -> (description, filename)
    dict[str, MultifileGroup],  # Multifile groups: group_name -> MultifileGroup
]:
    """
    Discover available templates for a generator.

    Returns:
        Tuple of (single_templates, multifile_groups).
    """
    return discover_templates(generator.templates_path)


def add_template_flags(
    parser: argparse.ArgumentParser,
    single_templates: dict[str, tuple[str, str]],
    multifile_groups: dict[str, MultifileGroup],
) -> tuple[list[str], list[str]]:
    """Add template output flags to a parser.

    Returns:
        Tuple of (single_template_extensions, multifile_group_names).
    """
    group = parser.add_argument_group("output", "Output formats to generate")

    added_shorts: list[str] = []

    # Add single template flags
    for ext, (desc, _) in single_templates.items():
        # Generate unique short flag
        short = desc.lower().replace(" ", "")[0]
        i = 1
        while (short in added_shorts or short in ("o", "d", "h", "i")) and i < len(
            desc
        ):
            short = desc.lower().replace(" ", "")[i]
            i += 1
        added_shorts.append(short)

        group.add_argument(
            f"-{short}",
            f"--{ext}",
            action="store_true",
            help=f"Generate {desc} output",
        )

    # Add multifile group flags
    for group_name, mf_group in multifile_groups.items():
        # Generate unique short flag
        desc = mf_group.description
        short = group_name[0]
        i = 1
        while (short in added_shorts or short in ("o", "d", "h", "i")) and i < len(
            group_name
        ):
            short = group_name[i]
            i += 1
        added_shorts.append(short)

        # Build help text listing output files
        output_files = []
        for t in mf_group.templates:
            if t.suffix:
                output_files.append(f".{t.output_ext} (#{t.suffix})")
            else:
                output_files.append(f".{t.output_ext}")
        outputs_str = ", ".join(output_files)

        group.add_argument(
            f"-{short}",
            f"--{group_name}-multi",
            action="store_true",
            dest=f"{group_name}_multi",
            help=f"Generate {desc} outputs ({outputs_str})",
        )

    return list(single_templates.keys()), list(multifile_groups.keys())


def scaffold_domain(name: str, location: Path) -> list[Path]:
    """Create a new domain scaffold with all required files.

    Args:
        name: Domain name (lowercase, no spaces).
        location: Parent directory where the domain folder will be created.

    Returns:
        List of created file paths.
    """
    domain_dir = location / name
    templates_dir = domain_dir / "templates"

    # Create directories
    domain_dir.mkdir(parents=True, exist_ok=True)
    templates_dir.mkdir(exist_ok=True)

    created_files: list[Path] = []

    # __init__.py
    init_content = f'''"""The {name} domain for embgen."""

from .generator import {name.capitalize()}Generator

generator = {name.capitalize()}Generator()
'''
    (domain_dir / "__init__.py").write_text(init_content)
    created_files.append(domain_dir / "__init__.py")

    # models.py
    models_content = f'''"""Data models for the {name} domain."""

from embgen.domains import BaseConfig


class {name.capitalize()}Config(BaseConfig):
    """Configuration for {name} generation.

    Customize this model with fields specific to your domain.
    Example YAML:
        name: My{name.capitalize()}
        file: my{name}  # optional output filename
        # Add your domain-specific fields here
    """

    # Add your domain-specific fields here
    # Example:
    # description: str | None = None
    # items: list[str] = []
'''
    (domain_dir / "models.py").write_text(models_content)
    created_files.append(domain_dir / "models.py")

    # generator.py
    generator_content = f'''"""Generator implementation for the {name} domain."""

from pathlib import Path
from typing import Any, cast

from jinja2 import Template

from embgen.domains import BaseConfig, DomainGenerator
from .models import {name.capitalize()}Config


class {name.capitalize()}Generator(DomainGenerator):
    """Generator for {name} domain."""

    @property
    def name(self) -> str:
        return "{name}"

    @property
    def description(self) -> str:
        return "Generate {name} outputs"

    def detect(self, data: dict[str, Any]) -> bool:
        """Detect if YAML data belongs to this domain.

        Customize this method to detect your domain's YAML structure.
        """
        # Example: check for a specific key
        return "{name}" in data or data.get("domain") == "{name}"

    def validate(self, data: dict[str, Any]) -> BaseConfig:
        """Parse and validate YAML into domain config."""
        return cast(BaseConfig, {name.capitalize()}Config.model_validate(data))

    def render(self, config: Any, template: Template) -> str:
        """Render config to a template."""
        cfg: {name.capitalize()}Config = config if isinstance(config, {name.capitalize()}Config) else {name.capitalize()}Config.model_validate(config)
        return template.render(config=cfg)

    @property
    def templates_path(self) -> Path:
        """Path to this domain's templates."""
        return Path(__file__).parent / "templates"

    def post_generate(
        self, config: BaseConfig, output: Path, generated_extensions: set[str]
    ) -> list[str]:
        """Optional: copy extra files after generation.

        Customize to copy additional files if needed.
        """
        return []
'''
    (domain_dir / "generator.py").write_text(generator_content)
    created_files.append(domain_dir / "generator.py")

    # Template files
    template_h = f"""// {{{{ config.name }}}} - Generated by embgen
// DO NOT EDIT - This file is auto-generated

#ifndef {{{{ config.output_filename | upper }}}}_H
#define {{{{ config.output_filename | upper }}}}_H

// Add your {name} domain header content here

#endif // {{{{ config.output_filename | upper }}}}_H
"""
    (templates_dir / "template.h.j2").write_text(template_h)
    created_files.append(templates_dir / "template.h.j2")

    template_py = f'''"""{{{{ config.name }}}} - Generated by embgen.

DO NOT EDIT - This file is auto-generated.
"""

# Add your {name} domain Python content here
'''
    (templates_dir / "template.py.j2").write_text(template_py)
    created_files.append(templates_dir / "template.py.j2")

    template_md = f"""# {{{{ config.name }}}}

> Generated by embgen - DO NOT EDIT

Add your {name} domain Markdown documentation here.
"""
    (templates_dir / "template.md.j2").write_text(template_md)
    created_files.append(templates_dir / "template.md.j2")

    return created_files


def main():
    """Main entry point for embgen CLI."""
    start_time = time.time()

    # Pre-parse to get domains-dir before loading domains
    pre_parser = argparse.ArgumentParser(add_help=False)
    pre_parser.add_argument("--domains-dir", type=Path, default=None)
    pre_args, _ = pre_parser.parse_known_args()

    domains_dir: Path | None = pre_args.domains_dir
    domains = discover_domains(domains_dir)

    # Build main parser
    ap = argparse.ArgumentParser(
        prog="embgen",
        description="Embedded code generator - Generate code from YAML definitions",
    )
    ap.add_argument("-d", "--debug", action="store_true", help="Enable debug logging")
    ap.add_argument(
        "--domains-dir",
        type=Path,
        default=None,
        metavar="PATH",
        help="Additional directory containing user domains (also: EMBGEN_DOMAINS_DIR env var)",
    )

    subparsers = ap.add_subparsers(dest="domain", help="Domain to generate")

    # Track templates per domain for later use
    domain_templates: dict[
        str, tuple[dict[str, tuple[str, str]], dict[str, MultifileGroup]]
    ] = {}

    # Auto-generate subcommand for each domain
    for name, generator in domains.items():
        single_templates, multifile_groups = get_template_args(generator)
        domain_templates[name] = (single_templates, multifile_groups)

        sub = subparsers.add_parser(name, help=generator.description)
        sub.add_argument("input", help="Input YAML file")
        sub.add_argument(
            "-o",
            "--output",
            default=Path.cwd() / "generated",
            help="Output directory (relative to invocation directory)",
        )
        add_template_flags(sub, single_templates, multifile_groups)

    # Auto-detect mode
    auto_sub = subparsers.add_parser(
        "auto", help="Auto-detect domain from YAML content"
    )
    auto_sub.add_argument("input", help="Input YAML file")
    auto_sub.add_argument(
        "-o",
        "--output",
        default=Path.cwd() / "generated",
        help="Output directory (relative to invocation directory)",
    )

    # For auto mode, we need to add all possible template flags
    all_single_templates: dict[str, tuple[str, str]] = {}
    all_multifile_groups: dict[str, MultifileGroup] = {}
    for single_templates, multifile_groups in domain_templates.values():
        all_single_templates.update(single_templates)
        all_multifile_groups.update(multifile_groups)
    add_template_flags(auto_sub, all_single_templates, all_multifile_groups)

    # New domain scaffolding subcommand
    new_sub = subparsers.add_parser("new", help="Create a new domain scaffold")
    new_sub.add_argument("name", help="Name of the new domain (lowercase, no spaces)")
    new_location_group = new_sub.add_mutually_exclusive_group()
    new_location_group.add_argument(
        "--builtin",
        action="store_true",
        help="Create in the embgen package (requires write access)",
    )
    new_location_group.add_argument(
        "--location",
        type=Path,
        default=None,
        metavar="PATH",
        help="Directory to create the domain in (default: current directory)",
    )

    # Parse arguments
    args = ap.parse_args()

    # Setup logging
    log = logging.getLogger("embgen")
    log_level = logging.DEBUG if args.debug else logging.INFO
    log.handlers = [RichHandler(rich_tracebacks=True, show_path=False, show_time=False)]
    log.setLevel(log_level)

    # Check if domain was specified
    if args.domain is None:
        ap.print_help()
        sys.exit(1)

    # Handle 'new' subcommand
    if args.domain == "new":
        domain_name = args.name.lower().replace(" ", "_").replace("-", "_")

        if args.builtin:
            location = get_builtin_domains_path()
        elif args.location:
            location = args.location
        else:
            location = Path.cwd()

        # Check if domain already exists
        target_dir = location / domain_name
        if target_dir.exists():
            log.error(f"Domain directory already exists: {target_dir}")
            sys.exit(1)

        log.info(f"Creating new domain '{domain_name}' in {location}")
        created = scaffold_domain(domain_name, location)

        for f in created:
            log.info(f"  Created: {f.relative_to(location)}")

        log.info(f"Domain '{domain_name}' scaffolded successfully!")
        log.info("Next steps:")
        log.info(f"  1. Edit {domain_name}/models.py to define your config schema")
        log.info(f"  2. Edit {domain_name}/generator.py to customize detection logic")
        log.info(f"  3. Edit templates in {domain_name}/templates/")

        if not args.builtin and not args.location:
            log.info(f"  4. Use --domains-dir {location} to load this domain")

        end_time = time.time()
        log.debug(f"Done after {end_time - start_time:.2f} seconds.")
        return

    # Handle auto-detect mode
    generator: DomainGenerator
    if args.domain == "auto":
        data = parse_yaml(args.input)
        detected = detect_domain(data, domains_dir)
        if detected is None:
            log.error(
                f"Could not auto-detect domain. Available: {list(domains.keys())}"
            )
            sys.exit(1)
        assert detected is not None  # Help type checker after sys.exit
        generator = detected
        log.info(f"Auto-detected domain: {generator.name}")
        single_templates, multifile_groups = domain_templates.get(
            generator.name, get_template_args(generator)
        )
    else:
        generator = domains[args.domain]
        single_templates, multifile_groups = domain_templates[args.domain]

    # Collect selected single template types
    selected_templates = {
        ext: template_name
        for ext, (_, template_name) in single_templates.items()
        if getattr(args, ext, False)
    }

    # Collect selected multifile groups
    selected_multifile = {
        group_name: mf_group
        for group_name, mf_group in multifile_groups.items()
        if getattr(args, f"{group_name}_multi", False)
    }

    if not selected_templates and not selected_multifile:
        log.error("No output formats specified. Use -h to see available formats.")
        sys.exit(1)

    # Run generation
    try:
        parse_and_render(
            generator, args.input, args.output, selected_templates, selected_multifile
        )
    except Exception as e:
        log.error(f"Generation failed: {e}")
        if args.debug:
            raise
        sys.exit(1)

    end_time = time.time()
    log.debug(f"Done after {end_time - start_time:.2f} seconds.")


if __name__ == "__main__":
    main()
