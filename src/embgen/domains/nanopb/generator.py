from datetime import datetime
from pathlib import Path
from typing import Any, cast
from jinja2 import Template
from .. import DomainGenerator, BaseConfig
from .models import NanoPBConfig


class NanoPBGenerator(DomainGenerator):
    @property
    def name(self) -> str:
        return "nanopb"

    @property
    def description(self) -> str:
        return "Generate NanoPB methods"

    def detect(self, data: dict[str, Any]) -> bool:
        return "methods" in data

    def validate(self, data: dict[str, Any]) -> BaseConfig:
        return cast(BaseConfig, NanoPBConfig.model_validate(data))

    def render(self, config: Any, template: Template) -> str:  # type: ignore
        config: NanoPBConfig = config  # type: narrow
        return template.render(
            config=config,
            name=config.name,
            file=config.file,
            output_filename=config.output_filename,
            support_file=config.support_output_filename,
            methods=sorted(config.methods, key=lambda c: c.name),
            max_count=config.max_count if config.max_count is not None else 40,
            generated_on=datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        )

    def post_generate(
        self, config: BaseConfig, output: Path, generated_extensions: set[str]
    ) -> list[str]:
        config = cast(NanoPBConfig, config)
        result: list[str] = []

        return result
