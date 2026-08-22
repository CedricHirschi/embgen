import logging

from pydantic import BaseModel, ConfigDict, ValidationError
from rich.console import Console
from rich.logging import RichHandler
from rich.traceback import install as install_traceback


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


def log_validation_error(
    log: logging.Logger, error: ValidationError, level: int = logging.ERROR
) -> None:
    errors = error.errors()
    log.log(level, f"{len(errors)} validation errors:")
    for err in errors:
        err_type = err["type"]
        err_url = "/" + "/".join(err["loc"]) if err["loc"] else ""  # type: ignore
        err_msg = err["msg"]
        err_help = f"(See {err['url']})" if err.get("url") else ""  # type: ignore
        log.log(level, f"  {err_url}: {err_type}: {err_msg} {err_help}")


console = Console()


def print_validation_error(error: ValidationError) -> None:
    errors = error.errors()
    console.print(f"[red]{len(errors)}[/] validation errors:")
    for err in errors:
        err_type = err["type"]
        err_url = "/" + "/".join(err["loc"]) if err["loc"] else ""  # type: ignore
        err_msg = err["msg"]
        err_help = f"(See {err['url']})" if err.get("url") else ""  # type: ignore
        console.print(f"[blue]  {err_url}[/]: {err_type}: {err_msg} {err_help}")


def setup_logging(level: int | str = logging.INFO) -> logging.Logger:
    logging.basicConfig(
        level=level,
        format="%(message)s",
        datefmt="[%X]",
        handlers=[RichHandler(console=console)],
    )
    install_traceback()

    return logging.getLogger()
