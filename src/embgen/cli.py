"""Command-line interface for embgen."""

import argparse
import logging
import sys
import time
from pathlib import Path

from rich.logging import RichHandler

from .discovery import discover_domains, detect_domain, BUILTIN_DOMAINS_PATH
from .domains import DomainGenerator
from .generator import CodeGenerator
from .models import MultifileGroup
from .scaffold import scaffold_domain
from .templates import discover_templates


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

        # Build help text listing output files
        output_files = []
        for t in mf_group.templates:
            if t.suffix:
                output_files.append(f".{t.output_ext} (#{t.suffix})")
            else:
                output_files.append(f".{t.output_ext}")
        outputs_str = ", ".join(output_files)

        # Only add short flag if we found a unique one
        if short not in added_shorts and short not in ("o", "d", "h", "i"):
            added_shorts.append(short)
            group.add_argument(
                f"-{short}",
                f"--{group_name}-multi",
                action="store_true",
                dest=f"{group_name}_multi",
                help=f"Generate {desc} outputs ({outputs_str})",
            )
        else:
            # No unique short flag available, use long-form only
            group.add_argument(
                f"--{group_name}-multi",
                action="store_true",
                dest=f"{group_name}_multi",
                help=f"Generate {desc} outputs ({outputs_str})",
            )

    return list(single_templates.keys()), list(multifile_groups.keys())


def main(argv: list[str] | None = None) -> int:
    """Main entry point for embgen CLI.

    Args:
        argv: Command-line arguments. If None, uses sys.argv[1:].

    Returns:
        Exit code (0 for success, non-zero for failure).
    """
    start_time = time.time()

    # Pre-parse to get domains-dir before loading domains
    pre_parser = argparse.ArgumentParser(add_help=False)
    pre_parser.add_argument("--domains-dir", type=Path, default=None)
    pre_args, _ = pre_parser.parse_known_args(argv)

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
        single_templates, multifile_groups = discover_templates(
            generator.templates_path
        )
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
    args = ap.parse_args(argv)

    # Setup logging
    log = logging.getLogger("embgen")
    log_level = logging.DEBUG if args.debug else logging.INFO
    log.handlers = [RichHandler(rich_tracebacks=True, show_path=False, show_time=False)]
    log.setLevel(log_level)

    # Check if domain was specified
    if args.domain is None:
        ap.print_help()
        return 1

    # Handle 'new' subcommand
    if args.domain == "new":
        domain_name = args.name.lower().replace(" ", "_").replace("-", "_")

        if args.builtin:
            location = BUILTIN_DOMAINS_PATH
        elif args.location:
            location = args.location
        else:
            location = Path.cwd()

        # Check if domain already exists
        target_dir = location / domain_name
        if target_dir.exists():
            log.error(f"Domain directory already exists: {target_dir}")
            return 1

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
        return 0

    # Handle auto-detect mode
    generator: DomainGenerator
    if args.domain == "auto":
        code_gen = CodeGenerator(
            discover_domains(domains_dir).get("commands")
            or list(domains.values())[0],  # Temporary, will be replaced
            args.output,
        )
        data = code_gen.parse_yaml(args.input)
        detected = detect_domain(data, domains_dir)
        if detected is None:
            log.error(
                f"Could not auto-detect domain. Available: {list(domains.keys())}"
            )
            return 1
        assert detected is not None  # Narrow type for type checker
        generator = detected
        log.info(f"Auto-detected domain: {generator.name}")
        single_templates, multifile_groups = domain_templates.get(
            generator.name, discover_templates(generator.templates_path)
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
        return 1

    # Run generation using CodeGenerator
    try:
        code_gen = CodeGenerator(generator, args.output)
        code_gen.generate_from_file(
            args.input,
            templates=selected_templates,
            multifile_groups=selected_multifile,
        )
    except Exception as e:
        log.error(f"Generation failed: {e}")
        if args.debug:
            raise
        return 1

    end_time = time.time()
    log.debug(f"Done after {end_time - start_time:.2f} seconds.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
