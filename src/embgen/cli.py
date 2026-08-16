import argparse
import logging
from pathlib import Path

from rich.console import Console
from rich.logging import RichHandler
from rich.table import Table
from rich.traceback import install as install_traceback

from .plugins.discover import discover_plugins

log = logging.getLogger(__name__)
console = Console()


def do_list(plugins_dir: Path) -> None:
    plugins = discover_plugins(plugins_dir)
    if len(plugins) == 0:
        log.warning("No plugins found")
        return

    table = Table(title="Plugins")
    table.add_column("Path", justify="left")
    table.add_column("ID", justify="left")
    table.add_column("Version", justify="left")
    table.add_column("Description", justify="left")
    for plugin_path, plugin in plugins.items():
        table.add_row(
            plugin_path.as_posix(), plugin.id, plugin.version, plugin.description
        )
    console.print(table)


def main() -> None:
    logging.basicConfig(
        level=logging.INFO,
        format="%(message)s",
        datefmt="[%X]",
        handlers=[RichHandler(console=console)],
    )
    install_traceback()

    parse = argparse.ArgumentParser()
    parse.add_argument("--plugins-dir", type=Path, default=Path("plugins"))
    parse.add_argument("--verbose", action="store_true")

    # Add subcommands
    subcommands = parse.add_subparsers(dest="subcommand", required=True)
    subcommands.add_parser("list")

    args = parse.parse_args()

    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)

    try:
        if args.subcommand == "list":
            do_list(args.plugins_dir)
        else:
            parse.print_help()
    except Exception as e:
        raise RuntimeError(
            f"Error occured executing '{args.subcommand}' subcommand"
        ) from e


if __name__ == "__main__":
    main()
