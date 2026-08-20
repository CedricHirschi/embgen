import argparse
import logging
from pathlib import Path

from rich.table import Table

from .common import console, setup_logging
from .plugins.discover import PluginDiscovery

log = logging.getLogger(__name__)


def do_list(plugins_dir: Path) -> None:
    plugins = PluginDiscovery(plugins_dir).discover_plugins()
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
            plugin_path.as_posix(), plugin.id, str(plugin.version), plugin.description
        )
    console.print(table)


def main() -> None:
    setup_logging()

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
