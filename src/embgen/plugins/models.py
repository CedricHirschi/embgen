from typing import Any

from pydantic import ValidationInfo, model_validator

from ..common import StrictModel
from ..plugin import Generator, Schema


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
    schema_class: type[Schema]

    @model_validator(mode="before")
    @classmethod
    def _inject_classes(cls, data: Any, info: ValidationInfo) -> Any:
        generator_class = (info.context or {}).get("generator_class")
        if generator_class is None:
            raise ValueError("generator_class must be provided via validation context")
        schema_class = (info.context or {}).get("schema_class")
        if schema_class is None:
            raise ValueError("schema_class must be provided via validation context")
        if isinstance(data, dict):
            return {
                **data,
                "generator_class": generator_class,
                "schema_class": schema_class,
            }
        return data
