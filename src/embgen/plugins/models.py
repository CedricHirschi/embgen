from typing import Any

from pydantic import ValidationInfo, model_validator

from ..common import StrictModel
from ..generator import Generator


class PluginContact(StrictModel):
    author: str
    email: str
    repository: str | None = None


class Plugin(StrictModel):
    id: str
    version: str
    description: str
    contact: PluginContact
    generator_class: type[Generator]

    @model_validator(mode="before")
    @classmethod
    def _inject_generator_class(cls, data: Any, info: ValidationInfo) -> Any:
        generator_class = (info.context or {}).get("generator_class")
        if generator_class is None:
            raise ValueError("generator_class must be provided via validation context")
        if isinstance(data, dict):
            return {**data, "generator_class": generator_class}
        return data
