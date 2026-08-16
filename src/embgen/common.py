import logging

from pydantic import BaseModel, ConfigDict, ValidationError


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


def log_validation_error(
    log: logging.Logger, error: ValidationError, level: int = logging.ERROR
) -> None:
    errors = error.errors()
    log.log(level, f"{len(errors)} validation errors:")
    for err in errors:
        err_type = err["type"]
        err_url = "/" + "/".join(err["loc"]) if err["loc"] else ""
        err_msg = err["msg"]
        err_help = f"(See {err['url']})" if err.get("url") else ""
        log.log(level, f"  {err_url}: {err_type}: {err_msg} {err_help}")
