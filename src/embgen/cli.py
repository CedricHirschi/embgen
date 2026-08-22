import argparse
import logging
from pathlib import Path
from typing import Any

from pydantic import ValidationError
from rich.panel import Panel
from rich.table import Table
from rich_argparse import RichHelpFormatter

from .common import console, print_validation_error, setup_logging
from .generator import Generator
from .plugins.discover import PluginDiscovery

log = logging.getLogger(__name__)


INTERNAL_PLUGINS_DIR = Path(__file__).parents[2] / "plugins"


def parse_context(context_args: list[str] | None) -> dict[str, Any] | None:
    """Parse a list of KEY=VAL strings into a dictionary."""
    if not context_args:
        return None
    context: dict[str, Any] = {}
    for item in context_args:
        if "=" not in item:
            raise ValueError(f"Invalid context format: '{item}'. Expected KEY=VALUE.")
        key, val = item.split("=", 1)
        context[key.strip()] = val.strip()
    return context


def get_config_arg(configs: list[Path]) -> Path | list[Path]:
    """Unwrap single-item list so single files support multi-document parsing."""
    return configs[0] if len(configs) == 1 else configs


def do_list(args: argparse.Namespace) -> None:
    plugins = PluginDiscovery(args.plugins_dir).discover_plugins()
    if len(plugins) == 0:
        console.print("[yellow]No plugins found[/]")
        return

    table = Table(title="Discovered Plugins", border_style="dim")
    table.add_column("ID", style="bold green")
    table.add_column("Version", style="cyan")
    table.add_column("Description")
    table.add_column("Author", style="dim magenta")

    for plugin_path, plugin in plugins.items():
        table.add_row(
            plugin.id,
            str(plugin.version),
            plugin.description,
            plugin.contact.author + " <" + plugin.contact.email + ">",
        )
    console.print(table)


def do_generate(args: argparse.Namespace) -> None:
    gen = Generator(args.output_dir, args.plugins_dir, log_fail=False)

    context = parse_context(args.context)
    config = get_config_arg(args.configs)

    try:
        if args.dry_run:
            console.print("[yellow]Dry run mode enabled. No files will be written.[/]")
            files = gen.generate(
                plugin_id=args.plugin,
                config=config,
                all=args.all,
                template=args.template,
                context=context,
                env=not args.no_env,
            )

        else:
            files = gen.run(
                plugin_id=args.plugin,
                config=config,
                all=args.all,
                template=args.template,
                context=context,
                env=not args.no_env,
            )

        for file in files:
            dest = (args.output_dir / file.path).resolve().as_posix()
            console.print(
                f"[bold green]Generated[/] file {dest} ({len(file.content)} bytes)"
            )
    except ValidationError as e:
        console.print(f"[bold red]Generation failed[/] for plugin '{args.plugin}':")
        print_validation_error(e)
        exit(1)


def do_validate(args: argparse.Namespace) -> None:
    gen = Generator(args.output_dir, args.plugins_dir, log_fail=False)

    context = parse_context(args.context)
    config = get_config_arg(args.configs)

    try:
        gen.generate(
            plugin_id=args.plugin,
            config=config,
            all=args.all,
            template=args.template,
            context=context,
            env=not args.no_env,
        )
        console.print(
            f"[bold green]Validation successful[/] for plugin '{args.plugin}'"
        )
    except ValidationError as e:
        console.print(f"[bold red]Validation failed[/] for plugin '{args.plugin}':")
        print_validation_error(e)
        exit(1)


def do_info(args: argparse.Namespace) -> None:
    plugins = PluginDiscovery(args.plugins_dir).discover_plugins()
    for plugin in plugins.values():
        if plugin.id == args.plugin:
            break
    else:
        console.print(f"[bold red]Plugin '{args.plugin}' not found[/]")
        return

    info_text = (
        f"[bold cyan]ID:[/] {plugin.id}\n"
        f"[bold cyan]Version:[/] {plugin.version}\n"
        f"[bold cyan]Description:[/] {plugin.description}\n\n"
        f"[bold magenta]Contact Information:[/]\n"
        f"  - Author:     {plugin.contact.author}\n"
        f"  - Email:      [link=mailto:{plugin.contact.email}]{plugin.contact.email}[/]\n"
        f"  - Repository: {f'[link={plugin.contact.repository}]{plugin.contact.repository}[/]' if plugin.contact.repository else 'N/A'}"
    )
    console.print(Panel(info_text, title=f"Plugin: {plugin.id}", border_style="dim"))


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="embgen",
        description="Embedded code generator from YAML/JSON/TOML/HJSON definitions",
        formatter_class=RichHelpFormatter,
    )
    parser.add_argument(
        "--plugins-dir",
        type=Path,
        action="append",
        default=None,
        help="Directory to search for plugins (can be specified multiple times)",
    )
    parser.add_argument(
        "--no-internal-plugins",
        action="store_true",
        help="Disable loading of internal plugins",
    )
    parser.add_argument(
        "-v", "--verbose", action="store_true", help="Enable verbose debug logging"
    )
    parser.add_argument(
        "-q", "--quiet", action="store_true", help="Suppress all output except errors"
    )

    subparsers = parser.add_subparsers(dest="subcommand", required=True)

    # 1. 'list' subcommand
    subparsers.add_parser("list", help="List all discovered plugins")

    # 2. 'generate' subcommand
    gen_parser = subparsers.add_parser("generate", help="Generate code using a plugin")
    gen_parser.add_argument("plugin", type=str, help="Plugin ID")
    gen_parser.add_argument(
        "configs", type=Path, nargs="+", help="Config file(s) to load"
    )
    gen_parser.add_argument(
        "-o",
        "--output-dir",
        type=Path,
        default=Path("generated"),
        help="Output directory (default: ./generated)",
    )
    gen_parser.add_argument(
        "-a", "--all", action="store_true", help="Enable multi-document mode"
    )
    gen_parser.add_argument(
        "-t",
        "--template",
        action="store_true",
        help="Enable Jinja2 template rendering",
    )
    gen_parser.add_argument(
        "-c",
        "--context",
        action="append",
        metavar="KEY=VAL",
        help="Template context variable (KEY=VALUE)",
    )
    gen_parser.add_argument(
        "--no-env",
        action="store_true",
        help="Disable automatic environment variable injection",
    )
    gen_parser.add_argument(
        "-d",
        "--dry-run",
        action="store_true",
        help="Show generated files without writing them to disk",
    )

    # 3. 'validate' subcommand
    validate_parser = subparsers.add_parser(
        "validate", help="Validate a config file against a plugin schema"
    )
    validate_parser.add_argument("plugin", type=str, help="Plugin ID")
    validate_parser.add_argument(
        "configs", type=Path, nargs="+", help="Config file(s) to validate"
    )
    validate_parser.add_argument(
        "-o",
        "--output-dir",
        type=Path,
        default=Path("generated"),
        help="Output directory (default: ./generated)",
    )
    validate_parser.add_argument(
        "-a", "--all", action="store_true", help="Enable multi-document mode"
    )
    validate_parser.add_argument(
        "-t",
        "--template",
        action="store_true",
        help="Enable Jinja2 template rendering",
    )
    validate_parser.add_argument(
        "-c",
        "--context",
        action="append",
        metavar="KEY=VAL",
        help="Template context variable (KEY=VALUE)",
    )
    validate_parser.add_argument(
        "--no-env",
        action="store_true",
        help="Disable automatic environment variable injection",
    )

    # 4. 'info' subcommand
    info_parser = subparsers.add_parser(
        "info", help="Show detailed information about a plugin"
    )
    info_parser.add_argument("plugin", type=str, help="Plugin ID")

    return parser


def main() -> None:
    setup_logging()

    parser = build_parser()
    args = parser.parse_args()

    if args.plugins_dir is None:
        args.plugins_dir = [Path("plugins")]
    if not args.no_internal_plugins:
        args.plugins_dir.append(INTERNAL_PLUGINS_DIR)
    args.plugins_dir = list(set(p.resolve() for p in args.plugins_dir))

    if args.quiet and args.verbose:
        parser.error("Cannot use both quiet and verbose options together.")
    elif args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)
    elif args.quiet:
        logging.getLogger().setLevel(logging.ERROR)
        console.quiet = True

    if not args.plugins_dir:
        parser.error("No plugin directories specified.")

    try:
        if args.subcommand == "list":
            do_list(args)
        elif args.subcommand == "generate":
            do_generate(args)
        elif args.subcommand == "validate":
            do_validate(args)
        elif args.subcommand == "info":
            do_info(args)
        else:
            parser.print_help()
    except Exception as e:
        console.print(f"[bold red]Error:[/] {e}")


if __name__ == "__main__":
    main()
